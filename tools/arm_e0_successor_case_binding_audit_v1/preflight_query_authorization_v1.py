#!/usr/bin/env python3
"""Zero-runtime pre-dispatch governance preflight for a future ARM query-only successor.

This is control-plane/result-blind only. It consumes a COMPLETE Issue #60
comments snapshot plus separately fresh issue-tail metadata and the planned exact
main SHA. It proves that the claimed Coordinator query-only authorization is the
latest ARM governance, is accepted by the exact current query-only stress
classifier, and explicitly binds the intended workflow_dispatch/main/attempt-1
identity. It never reads ARM credentials, queries/downloads ARM, opens native
data, or grants science authority.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[1]
STRESS_PATH = REPO_ROOT / "tools" / "arm_ena_sws_query_only_availability_v1" / "stress.py"
STRESS_SPEC = importlib.util.spec_from_file_location("arm_query_only_exact_stress_preflight", STRESS_PATH)
assert STRESS_SPEC and STRESS_SPEC.loader
S = importlib.util.module_from_spec(STRESS_SPEC)
STRESS_SPEC.loader.exec_module(S)

WORKFLOW_PATH = ".github/workflows/arm-ena-sws-query-only-availability-v1.yml"
PURPOSE = "ARM_ENA_SWS_QUERY_ONLY_SUCCESSOR_PREDISPATCH_GOVERNANCE_PREFLIGHT_V1"
STATUS = "QUERY_ONLY_SUCCESSOR_PREDISPATCH_GOVERNANCE_PASS"


class PreflightRefusal(RuntimeError):
    pass


def _first_nonempty(body: str) -> str:
    return next((line.strip() for line in str(body or "").splitlines() if line.strip()), "")


def _sha40(value: str, where: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-fA-F]{40}", value):
        raise PreflightRefusal(f"{where} must be exact 40-hex Git commit SHA")
    return value.lower()


def _positive_int(value: Any, where: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise PreflightRefusal(f"{where} must be positive integer")
    return value


def _canonical_rows(comments: Any) -> tuple[list[dict[str, Any]], str]:
    if not isinstance(comments, list) or not comments:
        raise PreflightRefusal("Issue #60 comments snapshot must be a nonempty list")
    out: list[dict[str, Any]] = []
    previous = 0
    for row in comments:
        if not isinstance(row, dict):
            raise PreflightRefusal("Issue #60 comments row must be an object")
        cid = row.get("id")
        if not isinstance(cid, int) or isinstance(cid, bool) or cid <= previous:
            raise PreflightRefusal("Issue #60 comment IDs must be positive and strictly increasing")
        previous = cid
        out.append({"id": cid, "body": str(row.get("body", ""))})
    canonical = json.dumps(out, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return out, hashlib.sha256(canonical).hexdigest()


def preflight(
    comments: Any,
    *,
    authorization_comment: int,
    authorization_title: str,
    exact_main_sha: str,
    expected_issue60_comment_count: int,
    expected_issue60_latest_comment_id: int,
) -> dict[str, Any]:
    main_sha = _sha40(exact_main_sha, "exact_main_sha")
    rows, ledger_sha = _canonical_rows(comments)
    expected_count = _positive_int(expected_issue60_comment_count, "expected_issue60_comment_count")
    expected_latest = _positive_int(expected_issue60_latest_comment_id, "expected_issue60_latest_comment_id")
    if len(rows) != expected_count:
        raise PreflightRefusal("Issue #60 comments snapshot count does not match fresh issue metadata")
    if rows[-1]["id"] != expected_latest:
        raise PreflightRefusal("Issue #60 comments snapshot tail does not match fresh latest-comment identity")
    _positive_int(authorization_comment, "authorization_comment")
    if not isinstance(authorization_title, str) or "\n" in authorization_title:
        raise PreflightRefusal("authorization_title must be one exact line")

    try:
        gov = S.audit_arm_governance(rows)
    except S.StressFailure as exc:
        raise PreflightRefusal(f"current exact stress governance audit refuses ledger: {exc}") from None

    arm_ids = gov.get("arm_relevant_comment_ids_after_baseline")
    if not isinstance(arm_ids, list) or not arm_ids:
        raise PreflightRefusal("no ARM-relevant governance exists after required baseline")
    if authorization_comment not in arm_ids:
        raise PreflightRefusal("claimed authorization is absent from exact ARM governance set")
    if authorization_comment != arm_ids[-1]:
        raise PreflightRefusal("claimed authorization is not the latest ARM-relevant governance")

    row = next((r for r in rows if r["id"] == authorization_comment), None)
    if row is None:
        raise PreflightRefusal("claimed authorization comment is absent from exact ledger")
    body = row["body"]
    actual_title = _first_nonempty(body)
    if actual_title != authorization_title:
        raise PreflightRefusal("authorization title does not match exact comment first line")
    upper = actual_title.upper()
    if not upper.startswith("COORDINATOR::ARM"):
        raise PreflightRefusal("authorization is not a direct COORDINATOR::ARM transition")
    required_title_markers = ("QUERY", "SUCCESSOR_AUTHORIZED", "ONE_SHOT", "ATTEMPT1")
    for marker in required_title_markers:
        if marker not in upper:
            raise PreflightRefusal(f"authorization title lacks required marker: {marker}")
    try:
        disposition = S._direct_arm_control_disposition(actual_title)
    except S.StressFailure as exc:
        raise PreflightRefusal(f"authorization title is ambiguous to current stress classifier: {exc}") from None
    if disposition != "allowed":
        raise PreflightRefusal("authorization title is adverse to current stress classifier")

    body_lower = body.lower()
    if WORKFLOW_PATH.lower() not in body_lower:
        raise PreflightRefusal("authorization body does not bind exact query-only workflow path")
    if "workflow_dispatch" not in body_lower:
        raise PreflightRefusal("authorization body does not bind workflow_dispatch event")
    if "main" not in body_lower or main_sha not in body_lower:
        raise PreflightRefusal("authorization body does not bind exact main SHA")
    if not re.search(r"\battempt\s*[_-]?\s*1\b|\battempt1\b", body_lower):
        raise PreflightRefusal("authorization body does not bind attempt 1")
    if not re.search(r"\bone[-_ ]shot\b", body_lower):
        raise PreflightRefusal("authorization body does not bind one-shot semantics")

    return {
        "schema": 1,
        "purpose": PURPOSE,
        "status": STATUS,
        "authorization_comment": authorization_comment,
        "authorization_title": actual_title,
        "exact_main_sha": main_sha,
        "workflow_path": WORKFLOW_PATH,
        "event_name": "workflow_dispatch",
        "run_attempt": 1,
        "one_shot": True,
        "issue60_comment_count": len(rows),
        "issue60_latest_comment_id": rows[-1]["id"],
        "issue60_ledger_sha256": ledger_sha,
        "latest_arm_relevant_comment_id": arm_ids[-1],
        "stress_classifier_disposition": "allowed",
        "arm_network_access_performed": False,
        "arm_credentials_read": False,
        "native_file_download_performed": False,
        "native_file_open_performed": False,
        "protected_sws_sasze_values_read": False,
        "e0_execution_authorized_by_this_receipt": False,
        "stage_b_authorized": False,
        "mystic_science_authorized": False,
        "production_authorized": False,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--issue60-comments", type=Path, required=True)
    p.add_argument("--authorization-comment", type=int, required=True)
    p.add_argument("--authorization-title", required=True)
    p.add_argument("--exact-main-sha", required=True)
    p.add_argument("--expected-issue60-comment-count", type=int, required=True)
    p.add_argument("--expected-issue60-latest-comment-id", type=int, required=True)
    a = p.parse_args()
    try:
        comments = json.loads(a.issue60_comments.read_text(encoding="utf-8"))
        out = preflight(
            comments,
            authorization_comment=a.authorization_comment,
            authorization_title=a.authorization_title,
            exact_main_sha=a.exact_main_sha,
            expected_issue60_comment_count=a.expected_issue60_comment_count,
            expected_issue60_latest_comment_id=a.expected_issue60_latest_comment_id,
        )
    except (OSError, json.JSONDecodeError, PreflightRefusal) as exc:
        raise SystemExit(f"REFUSAL: {exc}") from None
    print(json.dumps(out, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
