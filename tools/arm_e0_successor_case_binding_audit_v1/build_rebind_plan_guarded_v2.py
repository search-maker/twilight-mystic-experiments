#!/usr/bin/env python3
"""Guarded result-blind ARM E0 successor rebind planner v2.

This wrapper strengthens the existing v1 planner by binding the claimed future
query-only authorization to the exact ARM-relevant governance set recorded in
the same zero-runtime stress receipt. It performs no ARM access, credential
read, native download/opening, protected-value read, source rebind, or science
execution.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
V1_PATH = ROOT / "build_rebind_plan_v1.py"
SPEC = importlib.util.spec_from_file_location("arm_e0_successor_rebind_plan_v1", V1_PATH)
assert SPEC and SPEC.loader
P = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(P)

PURPOSE = "ARM_ENA_SWS_V1_E0_SUCCESSOR_RESULT_BLIND_REBIND_PLAN_V2"
STATUS = "RESULT_BLIND_SUCCESSOR_REBIND_PLAN_GUARDED_READY"

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
)


class GuardedPlanRefusal(RuntimeError):
    """Fail-closed refusal for governance/provenance drift."""


def _positive(value: Any, where: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise GuardedPlanRefusal(f"{where} must be positive integer")
    return value


def verify_query_authority_binding(
    stress_receipt: dict[str, Any],
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

    comment_id = _positive(query_authorization_comment, "query_authorization_comment")
    baseline = _positive(stress_receipt.get("baseline_coordinator_comment"), "baseline_coordinator_comment")
    latest = _positive(stress_receipt.get("issue60_latest_comment_id"), "issue60_latest_comment_id")
    ids = stress_receipt.get("arm_relevant_comment_ids_after_baseline")
    if not isinstance(ids, list) or not ids:
        raise GuardedPlanRefusal("stress receipt has no ARM-relevant governance after baseline")
    if any(not isinstance(x, int) or isinstance(x, bool) or x <= 0 for x in ids):
        raise GuardedPlanRefusal("ARM-relevant governance IDs must be positive integers")
    if ids != sorted(set(ids)):
        raise GuardedPlanRefusal("ARM-relevant governance IDs must be unique and increasing")
    if any(x <= baseline or x > latest for x in ids):
        raise GuardedPlanRefusal("ARM-relevant governance ID lies outside stress ledger bounds")
    if comment_id <= baseline or comment_id > latest:
        raise GuardedPlanRefusal("claimed query authorization lies outside stress ledger bounds")
    if comment_id not in ids:
        raise GuardedPlanRefusal("claimed query authorization is absent from stress ARM governance set")
    if comment_id != ids[-1]:
        raise GuardedPlanRefusal("claimed query authorization is not the latest ARM governance in stress receipt")
    if comment_id == P.LEGACY_AUTHORITY:
        raise GuardedPlanRefusal("legacy consumed E0 authority may not be reused")

    if not isinstance(query_authorization_title, str) or "\n" in query_authorization_title:
        raise GuardedPlanRefusal("query authorization title must be one exact line")
    upper = query_authorization_title.upper()
    if not upper.startswith("COORDINATOR::ARM"):
        raise GuardedPlanRefusal("query authorization must be a direct COORDINATOR::ARM transition")
    if "QUERY" not in upper or "AUTHORIZ" not in upper:
        raise GuardedPlanRefusal("query authorization title lacks explicit QUERY + AUTHORIZ semantics")
    if any(marker in upper for marker in ADVERSE_AUTH_TITLE_MARKERS):
        raise GuardedPlanRefusal("query authorization title carries adverse/false/reuse semantics")

    return {
        "schema": 1,
        "status": "QUERY_AUTHORITY_BOUND_TO_STRESS_LEDGER",
        "query_authorization_comment": comment_id,
        "query_authorization_title": query_authorization_title,
        "baseline_coordinator_comment": baseline,
        "issue60_latest_comment_id": latest,
        "latest_arm_relevant_comment_id": ids[-1],
        "query_authorization_is_latest_arm_governance": True,
        "query_authorization_present_in_stress_ledger": True,
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


def build_guarded_plan(**kwargs: Any) -> dict[str, Any]:
    proof = verify_query_authority_binding(
        kwargs["stress_receipt"],
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
    out["query_authorization_is_latest_arm_governance"] = True
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--query-receipt", type=Path, required=True)
    p.add_argument("--stress-receipt", type=Path, required=True)
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
        _manifest, cases = P.load_manifest(a.manifest)
        out = build_guarded_plan(
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
