#!/usr/bin/env python3
"""Live zero-ARM-runtime pre-dispatch gate for a future ARM query-only successor.

This wrapper closes the stale-snapshot gap around preflight_query_authorization_v1.
It reads only GitHub control-plane state, double-reads the default-branch tip,
Issue #60 metadata, and the complete Issue #60 {id,body} ledger before delegating
the exact governance/body binding to v1. It refuses ARM credentials and never
contacts ARM, downloads native data, opens protected SWS/SASZE values, or grants
science/execution authority.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
V1_PATH = ROOT / "preflight_query_authorization_v1.py"
V1_SPEC = importlib.util.spec_from_file_location("arm_query_only_successor_preflight_v1_live", V1_PATH)
assert V1_SPEC and V1_SPEC.loader
V1 = importlib.util.module_from_spec(V1_SPEC)
V1_SPEC.loader.exec_module(V1)

REPO = "search-maker/twilight-mystic-experiments"
ISSUE = 60
API_ROOT = f"https://api.github.com/repos/{REPO}"
REPO_URL = API_ROOT
MAIN_REF_URL = f"{API_ROOT}/git/ref/heads/main"
ISSUE_URL = f"{API_ROOT}/issues/{ISSUE}"
COMMENTS_URL = f"{ISSUE_URL}/comments"
PURPOSE = "ARM_ENA_SWS_QUERY_ONLY_SUCCESSOR_LIVE_PREDISPATCH_GOVERNANCE_PREFLIGHT_V2"
STATUS = "QUERY_ONLY_SUCCESSOR_LIVE_PREDISPATCH_GOVERNANCE_PASS"


class LivePreflightRefusal(RuntimeError):
    pass


def _github_json(url: str, token: str) -> Any:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "arm-query-only-successor-live-predispatch-v2",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise LivePreflightRefusal(f"GitHub control-plane read failed: {type(exc).__name__}") from None


def _complete_issue_comments(token: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    page = 1
    while True:
        batch = _github_json(f"{COMMENTS_URL}?per_page=100&page={page}", token)
        if not isinstance(batch, list):
            raise LivePreflightRefusal("Issue #60 comments response is not a list")
        rows.extend(batch)
        if len(batch) < 100:
            break
        page += 1
        if page > 100:
            raise LivePreflightRefusal("Issue #60 pagination exceeded bounded maximum")
    if not rows:
        raise LivePreflightRefusal("Issue #60 complete comments snapshot is empty")
    return rows


def _repo_default_branch(obj: Any) -> str:
    if not isinstance(obj, dict) or obj.get("default_branch") != "main":
        raise LivePreflightRefusal("repository default branch is not exact main")
    return "main"


def _main_sha(obj: Any) -> str:
    try:
        sha = obj["object"]["sha"]
    except (KeyError, TypeError):
        raise LivePreflightRefusal("main ref response lacks commit SHA") from None
    try:
        return V1._sha40(sha, "live main ref SHA")
    except V1.PreflightRefusal as exc:
        raise LivePreflightRefusal(str(exc)) from None


def _issue_meta(obj: Any) -> tuple[int, str]:
    if not isinstance(obj, dict):
        raise LivePreflightRefusal("Issue #60 metadata response is not an object")
    count = obj.get("comments")
    updated_at = obj.get("updated_at")
    if not isinstance(count, int) or isinstance(count, bool) or count <= 0:
        raise LivePreflightRefusal("Issue #60 comments count is not positive integer")
    if not isinstance(updated_at, str) or not updated_at.strip():
        raise LivePreflightRefusal("Issue #60 updated_at is missing")
    return count, updated_at


def _canonical_snapshot(rows: Any, where: str) -> tuple[list[dict[str, Any]], str]:
    try:
        return V1._canonical_rows(rows)
    except V1.PreflightRefusal as exc:
        raise LivePreflightRefusal(f"{where}: {exc}") from None


def live_preflight(*, authorization_comment: int, authorization_title: str, token: str) -> dict[str, Any]:
    if os.environ.get("ARM_USER_ID") or os.environ.get("ARM_ACCESS_TOKEN"):
        raise LivePreflightRefusal("live pre-dispatch gate refuses ARM credentials")
    if not isinstance(token, str) or not token.strip():
        raise LivePreflightRefusal("GITHUB_TOKEN is required for live GitHub control-plane readback")

    repo_before = _github_json(REPO_URL, token)
    _repo_default_branch(repo_before)
    main_before = _main_sha(_github_json(MAIN_REF_URL, token))
    issue_count_before, issue_updated_before = _issue_meta(_github_json(ISSUE_URL, token))

    comments_before_raw = _complete_issue_comments(token)
    comments_after_raw = _complete_issue_comments(token)
    comments_before, ledger_before = _canonical_snapshot(comments_before_raw, "first complete Issue #60 snapshot invalid")
    comments_after, ledger_after = _canonical_snapshot(comments_after_raw, "second complete Issue #60 snapshot invalid")

    issue_count_after, issue_updated_after = _issue_meta(_github_json(ISSUE_URL, token))
    repo_after = _github_json(REPO_URL, token)
    _repo_default_branch(repo_after)
    main_after = _main_sha(_github_json(MAIN_REF_URL, token))

    if main_before != main_after:
        raise LivePreflightRefusal("default-branch main moved during live pre-dispatch readback")
    if issue_count_before != issue_count_after or issue_updated_before != issue_updated_after:
        raise LivePreflightRefusal("Issue #60 metadata changed during live pre-dispatch readback")
    if ledger_before != ledger_after or comments_before != comments_after:
        raise LivePreflightRefusal("Issue #60 complete {id,body} ledger changed between live snapshots")
    comments = comments_after
    if len(comments) != issue_count_after:
        raise LivePreflightRefusal("complete Issue #60 snapshot count disagrees with stable live issue metadata")
    latest_id = comments[-1].get("id")
    if not isinstance(latest_id, int) or isinstance(latest_id, bool) or latest_id <= 0:
        raise LivePreflightRefusal("complete Issue #60 snapshot lacks a valid latest comment identity")

    try:
        base = V1.preflight(
            comments,
            authorization_comment=authorization_comment,
            authorization_title=authorization_title,
            exact_main_sha=main_after,
            expected_current_main_sha=main_after,
            expected_issue60_comment_count=issue_count_after,
            expected_issue60_latest_comment_id=latest_id,
        )
    except V1.PreflightRefusal as exc:
        raise LivePreflightRefusal(f"bound v1 preflight refusal: {exc}") from None

    out = dict(base)
    out.update({
        "schema": 2,
        "purpose": PURPOSE,
        "status": STATUS,
        "github_control_plane_read_performed": True,
        "live_main_double_read_stable": True,
        "live_issue_metadata_double_read_stable": True,
        "live_issue_ledger_double_read_stable": True,
        "live_issue_ledger_sha256": ledger_after,
        "issue60_updated_at": issue_updated_after,
        "live_default_branch": "main",
        "arm_network_access_performed": False,
        "arm_credentials_read": False,
        "native_file_download_performed": False,
        "native_file_open_performed": False,
        "protected_sws_sasze_values_read": False,
        "e0_execution_authorized_by_this_receipt": False,
        "stage_b_authorized": False,
        "mystic_science_authorized": False,
        "production_authorized": False,
    })
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--authorization-comment", type=int, required=True)
    p.add_argument("--authorization-title", required=True)
    a = p.parse_args()
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    try:
        out = live_preflight(
            authorization_comment=a.authorization_comment,
            authorization_title=a.authorization_title,
            token=token,
        )
    except LivePreflightRefusal as exc:
        raise SystemExit(f"REFUSAL: {exc}") from None
    print(json.dumps(out, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
