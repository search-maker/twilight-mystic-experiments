#!/usr/bin/env python3
"""Guarded result-blind ARM E0 successor rebind planner v2.

This wrapper strengthens the existing v1 planner by binding the claimed future
query-only authorization to the exact ARM-relevant governance set and complete
Issue #60 ledger hash recorded in the same zero-runtime stress receipt, while
also requiring compatibility with the exact current query-only stress title
classifier and exact authorization-body binding to the dispatch workflow/ref/SHA.
It performs no ARM access, credential read, native download/opening,
protected-value read, source rebind, or science execution.
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
V1_PATH = ROOT / "build_rebind_plan_v1.py"
STRESS_PATH = REPO_ROOT / "tools" / "arm_ena_sws_query_only_availability_v1" / "stress.py"

SPEC = importlib.util.spec_from_file_location("arm_e0_successor_rebind_plan_v1", V1_PATH)
assert SPEC and SPEC.loader
P = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(P)

STRESS_SPEC = importlib.util.spec_from_file_location("arm_query_only_exact_stress", STRESS_PATH)
assert STRESS_SPEC and STRESS_SPEC.loader
S = importlib.util.module_from_spec(STRESS_SPEC)
STRESS_SPEC.loader.exec_module(S)

PURPOSE = "ARM_ENA_SWS_V1_E0_SUCCESSOR_RESULT_BLIND_REBIND_PLAN_V2"
STATUS = "RESULT_BLIND_SUCCESSOR_REBIND_PLAN_GUARDED_READY"
WORKFLOW_PATH = ".github/workflows/arm-ena-sws-query-only-availability-v1.yml"

ADVERSE_AUTH_TITLE_MARKERS = (
    "NOT_AUTHORIZ",
    "UNAUTHORIZED",
    "AUTHORITY_REMAINS_FALSE",
    "AUTHORITY_FALSE",
    "REVOKED",
    "REFUSAL",
    "REFUSED",
    "CANCELLED",
    "CANCELED",
    "EXPIRED",
    "DO_NOT_USE",
    "SECOND_ATTEMPT",
    "REQUEST",
    "PENDING",
    "PROPOSED",
)
POSITIVE_AUTH_TITLE_MARKERS = (
    "AUTHORIZED",
    "AUTHORIZATION_GRANTED",
    "AUTHORITY_GRANTED",
)


class GuardedPlanRefusal(RuntimeError):
    """Fail-closed refusal for governance/provenance drift."""


def _positive(value: Any, where: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise GuardedPlanRefusal(f"{where} must be positive integer")
    return value


def _canonical_issue60_snapshot(snapshot: Any) -> tuple[list[dict[str, Any]], str]:
    if not isinstance(snapshot, list) or not snapshot:
        raise GuardedPlanRefusal("Issue #60 ledger snapshot must be a nonempty list")
    canonical_rows: list[dict[str, Any]] = []
    previous = 0
    for row in snapshot:
        if not isinstance(row, dict):
            raise GuardedPlanRefusal("Issue #60 ledger snapshot row must be an object")
        cid = row.get("id")
        if not isinstance(cid, int) or isinstance(cid, bool) or cid <= previous:
            raise GuardedPlanRefusal("Issue #60 ledger snapshot IDs must be positive and strictly increasing")
        previous = cid
        canonical_rows.append({"id": cid, "body": str(row.get("body", ""))})
    canonical = json.dumps(
        canonical_rows,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return canonical_rows, hashlib.sha256(canonical).hexdigest()


def _first_nonempty(body: str) -> str:
    return next((line.strip() for line in str(body or "").splitlines() if line.strip()), "")


def _has_binding_line(body: str, pattern: str) -> bool:
    return re.search(pattern, body, flags=re.IGNORECASE | re.MULTILINE) is not None


def _require_dispatch_identity_body_binding(body: str, dispatch_sha: str) -> None:
    bullet = r"\s*(?:[-*]\s*)?"
    workflow_value = re.escape(WORKFLOW_PATH)
    main_value = re.escape(dispatch_sha)
    required = (
        (rf"^{bullet}workflow\s*:\s*`?{workflow_value}`?\s*$", "exact query-only workflow path"),
        (rf"^{bullet}event\s*:\s*`?workflow_dispatch`?\s*$", "workflow_dispatch event"),
        (rf"^{bullet}(?:exact\s+)?main(?:\s+sha)?\s*[:=]\s*`?{main_value}`?\s*$", "exact dispatch main SHA"),
        (rf"^{bullet}attempt\s*[_-]?\s*1\s+only\s*$", "attempt 1 only"),
        (rf"^{bullet}one[-_ ]shot\s+only\s*$", "one-shot only semantics"),
    )
    for pattern, label in required:
        if not _has_binding_line(body, pattern):
            raise GuardedPlanRefusal(f"query authorization body does not bind {label}")


def _require_current_stress_classifier_acceptance(title: str) -> None:
    try:
        disposition = S._direct_arm_control_disposition(title)
    except S.StressFailure as exc:
        raise GuardedPlanRefusal(f"query authorization title is not admissible to current stress classifier: {exc}") from None
    if disposition != "allowed":
        raise GuardedPlanRefusal("query authorization title is adverse to current stress classifier")


def verify_query_authority_binding(
    stress_receipt: dict[str, Any],
    issue60_comments_snapshot: Any,
    *,
    query_authorization_comment: int,
    query_authorization_title: str,
    query_dispatch_ref: str,
    query_dispatch_sha: str,
) -> dict[str, Any]:
    """Bind the claimed query authority to the exact stress-ledger ARM fence."""
    try:
        P.validate_stress(
            stress_receipt,
            dispatch_ref=query_dispatch_ref,
            dispatch_sha=query_dispatch_sha,
        )
    except P.PlanRefusal as exc:
        raise GuardedPlanRefusal(f"stress receipt rejected by v1 validator: {exc}") from None

    if query_dispatch_ref != "refs/heads/main":
        raise GuardedPlanRefusal("query authorization binding requires main dispatch ref")

    rows, ledger_sha = _canonical_issue60_snapshot(issue60_comments_snapshot)
    expected_count = _positive(stress_receipt.get("issue60_comment_count"), "issue60_comment_count")
    expected_latest = _positive(stress_receipt.get("issue60_latest_comment_id"), "issue60_latest_comment_id")
    expected_ledger_sha = stress_receipt.get("issue60_ledger_sha256")
    if len(rows) != expected_count:
        raise GuardedPlanRefusal("Issue #60 ledger snapshot count differs from stress receipt")
    if rows[-1]["id"] != expected_latest:
        raise GuardedPlanRefusal("Issue #60 ledger snapshot latest ID differs from stress receipt")
    if ledger_sha != expected_ledger_sha:
        raise GuardedPlanRefusal("Issue #60 ledger snapshot hash differs from stress receipt")

    comment_id = _positive(query_authorization_comment, "query_authorization_comment")
    baseline = _positive(stress_receipt.get("baseline_coordinator_comment"), "baseline_coordinator_comment")
    ids = stress_receipt.get("arm_relevant_comment_ids_after_baseline")
    if not isinstance(ids, list) or not ids:
        raise GuardedPlanRefusal("stress receipt has no ARM-relevant governance after baseline")
    if any(not isinstance(x, int) or isinstance(x, bool) or x <= 0 for x in ids):
        raise GuardedPlanRefusal("ARM-relevant governance IDs must be positive integers")
    if ids != sorted(set(ids)):
        raise GuardedPlanRefusal("ARM-relevant governance IDs must be unique and increasing")
    if any(x <= baseline or x > expected_latest for x in ids):
        raise GuardedPlanRefusal("ARM-relevant governance ID lies outside stress ledger bounds")
    if comment_id <= baseline or comment_id > expected_latest:
        raise GuardedPlanRefusal("claimed query authorization lies outside stress ledger bounds")
    if comment_id not in ids:
        raise GuardedPlanRefusal("claimed query authorization is absent from stress ARM governance set")
    if comment_id != ids[-1]:
        raise GuardedPlanRefusal("claimed query authorization is not the latest ARM governance in stress receipt")
    if comment_id == P.LEGACY_AUTHORITY:
        raise GuardedPlanRefusal("legacy consumed E0 authority may not be reused")

    row = next((item for item in rows if item["id"] == comment_id), None)
    if row is None:
        raise GuardedPlanRefusal("claimed query authorization comment is absent from exact Issue #60 snapshot")
    body = row["body"]
    actual_title = _first_nonempty(body)
    if not isinstance(query_authorization_title, str) or "\n" in query_authorization_title:
        raise GuardedPlanRefusal("query authorization title must be one exact line")
    if actual_title != query_authorization_title:
        raise GuardedPlanRefusal("supplied query authorization title does not match exact stress-bound comment")
    upper = actual_title.upper()
    if not upper.startswith("COORDINATOR::ARM"):
        raise GuardedPlanRefusal("query authorization must be a direct COORDINATOR::ARM transition")
    if "QUERY" not in upper:
        raise GuardedPlanRefusal("query authorization title lacks explicit QUERY semantics")
    if any(marker in upper for marker in ADVERSE_AUTH_TITLE_MARKERS):
        raise GuardedPlanRefusal("query authorization title carries adverse/false/request/reuse semantics")
    if not any(marker in upper for marker in POSITIVE_AUTH_TITLE_MARKERS):
        raise GuardedPlanRefusal("query authorization title lacks explicit positive authorization semantics")
    _require_current_stress_classifier_acceptance(actual_title)
    _require_dispatch_identity_body_binding(body, query_dispatch_sha)

    return {
        "schema": 2,
        "status": "QUERY_AUTHORITY_BOUND_TO_EXACT_STRESS_LEDGER",
        "query_authorization_comment": comment_id,
        "query_authorization_title": actual_title,
        "baseline_coordinator_comment": baseline,
        "issue60_comment_count": expected_count,
        "issue60_latest_comment_id": expected_latest,
        "issue60_ledger_sha256": ledger_sha,
        "latest_arm_relevant_comment_id": ids[-1],
        "query_authorization_is_latest_arm_governance": True,
        "query_authorization_present_in_stress_ledger": True,
        "query_authorization_title_exactly_bound": True,
        "query_authorization_current_stress_classifier_compatible": True,
        "query_authorization_body_bound_to_dispatch_identity": True,
        "query_authorization_bound_workflow_path": WORKFLOW_PATH,
        "query_authorization_bound_event": "workflow_dispatch",
        "query_authorization_bound_main_sha": query_dispatch_sha,
        "query_authorization_bound_run_attempt": 1,
        "query_authorization_bound_one_shot": True,
        "legacy_authority_reused": False,
        "arm_network_access_performed": False,
        "arm_credentials_read": False,
        "native_file_download_performed": False,
        "native_file_open_performed": False,
        "protected_sws_sasze_values_read": False,
        "stage_b_authorized": False,
        "mystic_science_authorized": False,
        "production_authorized": False,
    }


def build_guarded_plan(*, issue60_comments_snapshot: Any, **kwargs: Any) -> dict[str, Any]:
    proof = verify_query_authority_binding(
        kwargs["stress_receipt"],
        issue60_comments_snapshot,
        query_authorization_comment=kwargs["query_authorization_comment"],
        query_authorization_title=kwargs["query_authorization_title"],
        query_dispatch_ref=kwargs["query_dispatch_ref"],
        query_dispatch_sha=kwargs["query_dispatch_sha"],
    )
    try:
        base = P.build_plan(**kwargs)
    except P.PlanRefusal as exc:
        raise GuardedPlanRefusal(f"v1 plan refused: {exc}") from None
    out = dict(base)
    out["schema"] = 2
    out["purpose"] = PURPOSE
    out["status"] = STATUS
    out["v1_plan_status"] = base["status"]
    out["query_authority_binding"] = proof
    out["query_authorization_bound_to_stress_ledger"] = True
    out["query_authorization_title_exactly_bound"] = True
    out["query_authorization_current_stress_classifier_compatible"] = True
    out["query_authorization_is_latest_arm_governance"] = True
    out["query_authorization_body_bound_to_dispatch_identity"] = True
    return out


def _read_json_any(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        raise GuardedPlanRefusal(f"invalid UTF-8 JSON: {path.name}") from None


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--query-receipt", type=Path, required=True)
    p.add_argument("--stress-receipt", type=Path, required=True)
    p.add_argument("--issue60-comments-snapshot", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--query-authorization-comment", type=int, required=True)
    p.add_argument("--query-authorization-title", required=True)
    p.add_argument("--query-dispatch-ref", required=True)
    p.add_argument("--query-dispatch-sha", required=True)
    p.add_argument("--query-workflow-run-id", type=int, required=True)
    p.add_argument("--query-run-attempt", type=int, required=True)
    p.add_argument("--query-artifact-id", type=int, required=True)
    p.add_argument("--query-artifact-digest", required=True)
    p.add_argument("--stress-artifact-id", type=int, required=True)
    p.add_argument("--stress-artifact-digest", required=True)
    a = p.parse_args()
    try:
        query, qsha = P._read_json(a.query_receipt)
        stress, ssha = P._read_json(a.stress_receipt)
        comments = _read_json_any(a.issue60_comments_snapshot)
        _manifest, cases = P.load_manifest(a.manifest)
        out = build_guarded_plan(
            issue60_comments_snapshot=comments,
            query_receipt=query,
            query_receipt_sha256=qsha,
            stress_receipt=stress,
            stress_receipt_sha256=ssha,
            ordered_cases=cases,
            query_authorization_comment=a.query_authorization_comment,
            query_authorization_title=a.query_authorization_title,
            query_dispatch_ref=a.query_dispatch_ref,
            query_dispatch_sha=a.query_dispatch_sha,
            query_workflow_run_id=a.query_workflow_run_id,
            query_run_attempt=a.query_run_attempt,
            query_artifact_id=a.query_artifact_id,
            query_artifact_digest=a.query_artifact_digest,
            stress_artifact_id=a.stress_artifact_id,
            stress_artifact_digest=a.stress_artifact_digest,
        )
    except (OSError, GuardedPlanRefusal) as exc:
        raise SystemExit(f"REFUSAL: {exc}") from None
    print(json.dumps(out, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
