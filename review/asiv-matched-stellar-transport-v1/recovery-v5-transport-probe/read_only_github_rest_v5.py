#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable

API_BASE = "https://api.github.com"
API_VERSION = "2022-11-28"
TRANSIENT_HTTP_STATUSES = {502, 503, 504}
MAX_ATTEMPTS = 8
BACKOFF_SECONDS = (2, 4, 8, 16, 30, 30, 30)
MAX_PAGES = 20
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def _validate_repo(repo: str) -> str:
    if not REPO_RE.fullmatch(repo):
        raise ValueError(f"invalid repository identity: {repo!r}")
    return repo


def _validate_positive_int(value: int, label: str) -> int:
    if not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return value


def _allowed_prefix(repo: str) -> str:
    return f"{API_BASE}/repos/{_validate_repo(repo)}/"


def _assert_allowed_url(url: str, repo: str) -> None:
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" or parts.netloc != "api.github.com":
        raise ValueError("read-only transport refuses non-api.github.com URL")
    if not url.startswith(_allowed_prefix(repo)):
        raise ValueError("read-only transport refuses URL outside exact repository")
    if parts.username or parts.password or parts.fragment:
        raise ValueError("read-only transport refuses credentialed or fragmented URL")


def _request(url: str, token: str) -> urllib.request.Request:
    if not token:
        raise ValueError("GITHUB_TOKEN is required")
    return urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": "starsvisibility-matched-stellar-readonly-v5",
        },
        method="GET",
    )


def _next_link(headers: Any) -> str | None:
    link = headers.get("Link") if headers is not None else None
    if not link:
        return None
    for part in str(link).split(","):
        bits = [x.strip() for x in part.split(";")]
        if len(bits) < 2 or 'rel="next"' not in bits[1:]:
            continue
        target = bits[0]
        if not (target.startswith("<") and target.endswith(">")):
            raise ValueError("malformed GitHub pagination Link target")
        return target[1:-1]
    return None


def get_json(
    url: str,
    *,
    repo: str,
    token: str,
    opener: Callable[..., Any] = urllib.request.urlopen,
    sleeper: Callable[[float], None] = time.sleep,
) -> tuple[Any, dict[str, Any]]:
    _assert_allowed_url(url, repo)
    attempts: list[dict[str, Any]] = []
    for attempt in range(1, MAX_ATTEMPTS + 1):
        req = _request(url, token)
        try:
            with opener(req, timeout=30) as response:
                status = int(getattr(response, "status", response.getcode()))
                raw = response.read()
                payload = json.loads(raw.decode("utf-8"))
                attempts.append({"attempt": attempt, "httpStatus": status, "transportError": None})
                return payload, {
                    "url": url,
                    "attempts": attempts,
                    "next": _next_link(response.headers),
                    "writeMethodPermitted": False,
                    "requestMethod": "GET",
                }
        except urllib.error.HTTPError as exc:
            status = int(exc.code)
            attempts.append({"attempt": attempt, "httpStatus": status, "transportError": "HTTPError"})
            if status not in TRANSIENT_HTTP_STATUSES or attempt == MAX_ATTEMPTS:
                raise
        except urllib.error.URLError:
            attempts.append({"attempt": attempt, "httpStatus": None, "transportError": "URLError"})
            if attempt == MAX_ATTEMPTS:
                raise
        delay = BACKOFF_SECONDS[attempt - 1]
        sleeper(delay)
    raise AssertionError("unreachable")


def get_paginated(
    url: str,
    *,
    repo: str,
    token: str,
    list_key: str,
    opener: Callable[..., Any] = urllib.request.urlopen,
    sleeper: Callable[[float], None] = time.sleep,
) -> tuple[list[Any], list[dict[str, Any]]]:
    rows: list[Any] = []
    audits: list[dict[str, Any]] = []
    current: str | None = url
    for _ in range(MAX_PAGES):
        if current is None:
            return rows, audits
        payload, audit = get_json(current, repo=repo, token=token, opener=opener, sleeper=sleeper)
        if not isinstance(payload, dict) or not isinstance(payload.get(list_key), list):
            raise ValueError(f"paginated response missing list key {list_key!r}")
        rows.extend(payload[list_key])
        audits.append(audit)
        nxt = audit.get("next")
        if nxt is not None:
            _assert_allowed_url(str(nxt), repo)
        current = str(nxt) if nxt is not None else None
    raise ValueError(f"pagination exceeded MAX_PAGES={MAX_PAGES}")


def fetch_run_bundle(
    repo: str,
    run_id: int,
    *,
    token: str,
    opener: Callable[..., Any] = urllib.request.urlopen,
    sleeper: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    repo = _validate_repo(repo)
    run_id = _validate_positive_int(run_id, "run_id")
    run_url = f"{API_BASE}/repos/{repo}/actions/runs/{run_id}"
    jobs_url = f"{run_url}/jobs?per_page=100"
    artifacts_url = f"{run_url}/artifacts?per_page=100"
    run, run_audit = get_json(run_url, repo=repo, token=token, opener=opener, sleeper=sleeper)
    jobs, jobs_audit = get_paginated(jobs_url, repo=repo, token=token, list_key="jobs", opener=opener, sleeper=sleeper)
    artifacts, artifacts_audit = get_paginated(artifacts_url, repo=repo, token=token, list_key="artifacts", opener=opener, sleeper=sleeper)
    return {
        "schemaVersion": 1,
        "transport": "python-urllib-direct-https-get",
        "repository": repo,
        "runId": run_id,
        "run": run,
        "jobs": jobs,
        "artifacts": artifacts,
        "audit": {
            "run": run_audit,
            "jobs": jobs_audit,
            "artifacts": artifacts_audit,
            "requestMethod": "GET",
            "writeMethodsPermitted": False,
            "maxAttemptsPerRequest": MAX_ATTEMPTS,
            "retryHttpStatuses": sorted(TRANSIENT_HTTP_STATUSES),
            "backoffSeconds": list(BACKOFF_SECONDS),
        },
    }


def fetch_pull_request(
    repo: str,
    pr_number: int,
    *,
    token: str,
    opener: Callable[..., Any] = urllib.request.urlopen,
    sleeper: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    repo = _validate_repo(repo)
    pr_number = _validate_positive_int(pr_number, "pr_number")
    url = f"{API_BASE}/repos/{repo}/pulls/{pr_number}"
    pull, audit = get_json(url, repo=repo, token=token, opener=opener, sleeper=sleeper)
    return {
        "schemaVersion": 1,
        "transport": "python-urllib-direct-https-get",
        "repository": repo,
        "prNumber": pr_number,
        "pullRequest": pull,
        "audit": audit,
    }


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only direct GitHub REST transport probe; GET only")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run-bundle")
    run.add_argument("--repository", required=True)
    run.add_argument("--run-id", required=True, type=int)
    run.add_argument("--output", required=True)
    pull = sub.add_parser("pull-request")
    pull.add_argument("--repository", required=True)
    pull.add_argument("--pr-number", required=True, type=int)
    pull.add_argument("--output", required=True)
    ns = parser.parse_args()
    token = os.environ.get("GITHUB_TOKEN", "")
    if ns.command == "run-bundle":
        payload = fetch_run_bundle(ns.repository, ns.run_id, token=token)
    elif ns.command == "pull-request":
        payload = fetch_pull_request(ns.repository, ns.pr_number, token=token)
    else:
        raise AssertionError(ns.command)
    _write_json(Path(ns.output), payload)


if __name__ == "__main__":
    main()
