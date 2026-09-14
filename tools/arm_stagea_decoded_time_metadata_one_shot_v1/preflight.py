#!/usr/bin/env python3
"""Credential-free live governance fence for Stage-A decoded-time metadata one-shot."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any

REPO = "search-maker/twilight-mystic-experiments"
ISSUE = 60
WORKFLOW_PATH = ".github/workflows/arm-stagea-decoded-time-metadata-one-shot-v1.yml"
REQUEST_SHA256 = "5ec3fb6b052d886091a77704bf425abcb0d04ea4279727c3a37b4f5ab6e63318"
AUTH_TITLE = "COORDINATOR::ARM_STAGEA_DECODED_TIME_METADATA_ONE_SHOT_V1_AUTHORIZED"
REVOKE_TITLE = "COORDINATOR::ARM_STAGEA_DECODED_TIME_METADATA_ONE_SHOT_V1_REVOKED"
EXPECTED_SCOPE = "DECODED_TIME_METADATA_ONLY"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
WQ_BASELINE_COMMENT = 5590748165
_HISTORICAL_WQ_CORRECTION_BEGIN = 5613910902
_HISTORICAL_WQ_PROSE_END = 5614235428
_HISTORICAL_WQ_CANONICAL_END = 5618881442

class Refusal(RuntimeError): pass


def git_blob_sha1(path: Path) -> str:
    raw = path.read_bytes()
    hdr = f"blob {len(raw)}\0".encode("ascii")
    return hashlib.sha1(hdr + raw).hexdigest()


def _request_json(url: str, token: str) -> Any:
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json", "User-Agent": "arm-stagea-decoded-time-preflight-v1"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as exc:
        raise Refusal("GITHUB_CONTROL_READ_FAILED_" + type(exc).__name__) from None


def read_complete_comments(token: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    page = 1
    while True:
        url = f"https://api.github.com/repos/{REPO}/issues/{ISSUE}/comments?per_page=100&page={page}"
        obj = _request_json(url, token)
        if not isinstance(obj, list): raise Refusal("ISSUE_COMMENTS_NOT_LIST")
        for x in obj:
            if not isinstance(x, dict) or not isinstance(x.get("id"), int) or not isinstance(x.get("created_at"), str) or not isinstance(x.get("body"), str):
                raise Refusal("ISSUE_COMMENT_SCHEMA_DRIFT")
            rows.append({"id": int(x["id"]), "created_at": x["created_at"], "body": x["body"], "author_association": x.get("author_association")})
        if len(obj) < 100: break
        page += 1
        if page > 100: raise Refusal("ISSUE_COMMENT_PAGINATION_LIMIT")
    rows.sort(key=lambda x: (x["created_at"], x["id"], x["body"]))
    if len({x["id"] for x in rows}) != len(rows): raise Refusal("DUPLICATE_COMMENT_ID")
    return rows


def ledger_digest(rows: list[dict[str, Any]]) -> str:
    payload = [{"created_at": x["created_at"], "id": x["id"], "body": x["body"]} for x in rows]
    raw = (json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def stable_ledger(token: str) -> tuple[list[dict[str, Any]], str]:
    a = read_complete_comments(token); b = read_complete_comments(token)
    da, db = ledger_digest(a), ledger_digest(b)
    if da != db or len(a) != len(b): raise Refusal("ISSUE_LEDGER_NOT_STABLE_ACROSS_COMPLETE_READS")
    return a, da


def _first_line(body: str) -> str:
    return body.splitlines()[0].strip() if body.splitlines() else ""


def _parse_literal_bindings(body: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in body.splitlines()[1:]:
        s = line.strip()
        if not s or s.startswith("#"): continue
        if "=" not in s: continue
        k, v = s.split("=", 1); k = k.strip(); v = v.strip()
        if k in out and out[k] != v: raise Refusal("DUPLICATE_CONFLICTING_BINDING_" + re.sub(r"\W+", "_", k))
        out[k] = v
    return out


def find_authorization(rows: list[dict[str, Any]], workflow_blob_sha: str, main_sha: str, expected_comment: int | None = None) -> dict[str, Any]:
    stagea = [x for x in rows if _first_line(x["body"]) in {AUTH_TITLE, REVOKE_TITLE}]
    if not stagea: raise Refusal("NO_DIRECT_STAGEA_AUTHORIZATION")
    latest = stagea[-1]
    title = _first_line(latest["body"])
    if title != AUTH_TITLE: raise Refusal("LATEST_STAGEA_DIRECT_CLAIM_NOT_AUTHORIZED")
    if latest.get("author_association") != "OWNER": raise Refusal("AUTHORIZATION_NOT_OWNER")
    if expected_comment is not None and latest["id"] != expected_comment: raise Refusal("AUTHORIZATION_CONTINUITY_CHANGED")
    b = _parse_literal_bindings(latest["body"])
    exact = {
        "workflow_path": WORKFLOW_PATH,
        "workflow_blob_sha": workflow_blob_sha,
        "main_sha": main_sha,
        "event": "workflow_dispatch",
        "ref": "refs/heads/main",
        "run_attempt": "1",
        "one_shot": "true",
        "request_contract_sha256": REQUEST_SHA256,
        "protected_scope": EXPECTED_SCOPE,
    }
    for k, v in exact.items():
        if b.get(k) != v: raise Refusal("AUTHORIZATION_BINDING_MISMATCH_" + k.upper())
    if not HEX40.fullmatch(workflow_blob_sha) or not HEX40.fullmatch(main_sha): raise Refusal("MALFORMED_GIT_IDENTITY")
    return {"id": latest["id"], "created_at": latest["created_at"], "title": title}


def _field(line: str, key: str) -> str | None:
    m = re.search(rf"(?:^|[|\s]){re.escape(key)}=([^|\s]+)", line, flags=re.I)
    return m.group(1) if m else None


def _is_write_quiet_event(first: str, event: str) -> bool:
    upper = str(first or "").strip().upper()
    return re.match(rf"^(?:[A-Z0-9_]+::)?{re.escape(event)}(?:\s|\||$)", upper) is not None


def _exact_historical_wq_correction_matches(*, cid: int, begin_id: int, first: str, closed_begins: dict[int, tuple[int, str, str]]) -> bool:
    if cid != _HISTORICAL_WQ_CANONICAL_END or begin_id != _HISTORICAL_WQ_CORRECTION_BEGIN:
        return False
    prior = closed_begins.get(begin_id)
    if prior is None or prior[0] != _HISTORICAL_WQ_PROSE_END:
        return False
    prior_first, prior_body = prior[1], prior[2]
    expected_binding = re.compile(rf"(?im)^\s*Exact matching closure for BEGIN\s+`?{begin_id}`?\s+only\.(?=\s|$)")
    if expected_binding.search(prior_body) is None:
        return False
    corrected_without_begin = re.sub(rf"\s*\|\s*begin={begin_id}(?=\s*\|)", "", first, count=1, flags=re.I)
    return corrected_without_begin == prior_first


def reject_unmatched_write_quiet(rows: list[dict[str, Any]]) -> None:
    open_begins: dict[int, str | None] = {}
    closed_begins: dict[int, tuple[int, str, str]] = {}
    for row in rows:
        cid = int(row["id"])
        if cid <= WQ_BASELINE_COMMENT:
            continue
        body = str(row["body"])
        first = _first_line(body)
        if _is_write_quiet_event(first, "WRITE_QUIET_BEGIN"):
            if cid in open_begins:
                raise Refusal("DUPLICATE_WRITE_QUIET_BEGIN")
            open_begins[cid] = _field(first, "stage")
        if not _is_write_quiet_event(first, "WRITE_QUIET_END"):
            continue
        raw_comment = _field(first, "beginComment")
        raw_short = _field(first, "begin")
        if raw_comment is not None and raw_short is not None and raw_comment != raw_short:
            raise Refusal("WRITE_QUIET_END_CONFLICTING_BEGIN_BINDINGS")
        line_begin = raw_comment or raw_short
        body_begins = re.findall(r"(?im)^\s*Exact matching closure for BEGIN\s+`?(\d+)`?\s+only\.(?=\s|$)", body)
        if len(body_begins) > 1:
            raise Refusal("WRITE_QUIET_END_DUPLICATE_BODY_BINDINGS")
        body_begin = body_begins[0] if body_begins else None
        if line_begin is not None and body_begin is not None and line_begin != body_begin:
            raise Refusal("WRITE_QUIET_END_CONFLICTING_LINE_BODY_BINDINGS")
        raw_begin = line_begin or body_begin
        if raw_begin is None or not raw_begin.isdigit():
            raise Refusal("WRITE_QUIET_END_LACKS_EXACT_BEGIN_BINDING")
        begin_id = int(raw_begin)
        if begin_id not in open_begins:
            if _exact_historical_wq_correction_matches(cid=cid, begin_id=begin_id, first=first, closed_begins=closed_begins):
                continue
            raise Refusal("WRITE_QUIET_END_REFERENCES_NO_OPEN_BEGIN")
        begin_stage = open_begins[begin_id]
        end_stage = _field(first, "stage")
        if begin_stage and end_stage and begin_stage != end_stage:
            raise Refusal("WRITE_QUIET_STAGE_MISMATCH")
        del open_begins[begin_id]
        closed_begins[begin_id] = (cid, first, body)
    if open_begins:
        raise Refusal("UNMATCHED_CURRENT_WRITE_QUIET_" + str(sorted(open_begins)[-1]))


def require_live_main(token: str, expected_sha: str) -> None:
    obj = _request_json(f"https://api.github.com/repos/{REPO}/branches/main", token)
    if not isinstance(obj, dict) or not isinstance(obj.get("commit"), dict):
        raise Refusal("MAIN_BRANCH_SCHEMA_DRIFT")
    observed = str(obj["commit"].get("sha", ""))
    if observed != expected_sha:
        raise Refusal("LIVE_MAIN_SHA_CHANGED")


def build_receipt(mode: str, expected_comment: int | None = None) -> dict[str, Any]:
    if os.environ.get("ARM_USER_ID") or os.environ.get("ARM_ACCESS_TOKEN"):
        raise Refusal("PREFLIGHT_REFUSES_ARM_CREDENTIALS")
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token: raise Refusal("GITHUB_TOKEN_REQUIRED")
    if os.environ.get("GITHUB_EVENT_NAME") != "workflow_dispatch": raise Refusal("EVENT_NOT_WORKFLOW_DISPATCH")
    if os.environ.get("GITHUB_REF") != "refs/heads/main" or os.environ.get("GITHUB_REF_TYPE") != "branch": raise Refusal("REF_NOT_DEFAULT_MAIN_BRANCH")
    if os.environ.get("GITHUB_RUN_ATTEMPT") != "1": raise Refusal("RUN_ATTEMPT_NOT_ONE")
    main_sha = os.environ.get("GITHUB_SHA", "").strip()
    if not HEX40.fullmatch(main_sha): raise Refusal("GITHUB_SHA_MALFORMED")
    default_branch = os.environ.get("GITHUB_EVENT_REPOSITORY_DEFAULT_BRANCH", "main")
    if default_branch != "main": raise Refusal("DEFAULT_BRANCH_NOT_MAIN")
    workflow = Path(WORKFLOW_PATH)
    if not workflow.is_file(): raise Refusal("WORKFLOW_BYTES_NOT_PRESENT")
    workflow_blob_sha = git_blob_sha1(workflow)
    require_live_main(token, main_sha)
    rows, digest = stable_ledger(token)
    reject_unmatched_write_quiet(rows)
    auth = find_authorization(rows, workflow_blob_sha, main_sha, expected_comment=expected_comment)
    return {
        "schema": 1,
        "status": "STAGEA_DECODED_TIME_METADATA_LIVE_GOVERNANCE_PASS",
        "mode": mode,
        "authorization_comment_id": auth["id"],
        "authorization_title": auth["title"],
        "workflow_path": WORKFLOW_PATH,
        "workflow_blob_sha": workflow_blob_sha,
        "main_sha": main_sha,
        "event": "workflow_dispatch",
        "ref": "refs/heads/main",
        "run_id": os.environ.get("GITHUB_RUN_ID", ""),
        "run_attempt": 1,
        "request_contract_sha256": REQUEST_SHA256,
        "protected_scope": EXPECTED_SCOPE,
        "issue60_comment_count": len(rows),
        "issue60_atomic_digest_sha256": digest,
        "arm_credentials_read": False,
        "arm_network_access_performed": False,
        "native_data_opened": False,
        "science_arrays_read": False,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("pre", "post"), default="pre")
    ap.add_argument("--authorization-comment", type=int)
    ap.add_argument("--output", type=Path, required=True)
    ns = ap.parse_args(argv)
    if ns.mode == "post" and ns.authorization_comment is None:
        raise SystemExit("post mode requires --authorization-comment")
    try:
        obj = build_receipt(ns.mode, ns.authorization_comment)
    except Refusal as exc:
        print("REFUSAL:" + str(exc), file=sys.stderr)
        return 2
    ns.output.parent.mkdir(parents=True, exist_ok=True)
    ns.output.write_text(json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(obj["status"])
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
