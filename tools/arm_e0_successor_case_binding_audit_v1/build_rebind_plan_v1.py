#!/usr/bin/env python3
"""Build a result-blind rebind plan for a future ARM ENA/SWS E0 successor.

The tool consumes only sanitized query-only/stress receipts, the already-frozen
25-case manifest, and externally supplied GitHub provenance. It never contacts
ARM, downloads or opens native data, reads credential values, opens protected
SWS/SASZE radiance, edits execution/science files, or grants scientific
execution authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

QUERY_PURPOSE = "ARM_ENA_SWS_V1_E0_SUCCESSOR_QUERY_ONLY_AVAILABILITY_DISCOVERY"
PLAN_PURPOSE = "ARM_ENA_SWS_V1_E0_SUCCESSOR_RESULT_BLIND_REBIND_PLAN_V1"
PLAN_STATUS = "RESULT_BLIND_SUCCESSOR_REBIND_PLAN_READY"
DATASTREAM = "enaswsC1.b1"
EXPECTED_MANIFEST_SHA256 = "8a0756be59dac59cd8ad4fab77e499ec19069e24d2d2a636fa4352713b550def"
EXPECTED_CASE_COUNT = 25
FROZEN_E0_UNIVERSE_SHA256 = "87933189ff56322ce2b5d2821a1c2ab8094d0a472ef6c690cfbd90cd0451fa41"
FROZEN_E0_PROTOCOL = "ARM_ENA_SWS_V1_STAGE0_E0_RESULT_BLIND_V2"
FROZEN_E0_SOURCE_REF = "review/arm-ena-sws-v1-stage0"
FROZEN_E0_SOURCE_HEAD = "b8671665a2bf8fe9972b8cb48492abcfa6765140"
LEGACY_CASE_ID = "2017-06-16_dusk"
LEGACY_AUTHORITY = 5575796491

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ARTIFACT_DIGEST_RE = re.compile(r"^sha256:([0-9a-f]{64})$")
FILE_RE = re.compile(r"^enaswsC1\.b1\.(\d{8})\..*\.(?:nc|cdf)$", re.I)
CASE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_dusk$")

QUERY_ALLOWED_KEYS = {
    "schema", "purpose", "status", "datastream", "ordered_case_manifest_sha256",
    "ordered_case_count", "checked_case_count", "checked_cases", "first_match",
    "query_error", "credentials_persisted", "native_file_download_performed",
    "native_file_open_performed", "protected_sws_sasze_values_read",
    "stage_b_authorized", "mystic_science_authorized", "production_authorized",
}
STRESS_ALLOWED_KEYS = {
    "schema", "status", "purpose", "workflow_sha256", "executable_sha256",
    "ordered_case_manifest_sha256", "event_name", "github_ref", "github_sha",
    "default_branch", "issue60_comment_count", "issue60_latest_comment_id",
    "issue60_ledger_sha256", "baseline_coordinator_comment",
    "arm_relevant_comment_ids_after_baseline", "write_quiet_begin_ids_after_baseline",
    "write_quiet_end_ids_after_baseline", "arm_network_access_performed",
    "arm_credentials_read", "native_file_download_performed", "native_file_open_performed",
    "protected_sws_sasze_values_read", "stage_b_authorized",
    "mystic_science_authorized", "production_authorized",
}
FORBIDDEN_FALSE_QUERY = (
    "credentials_persisted", "native_file_download_performed", "native_file_open_performed",
    "protected_sws_sasze_values_read", "stage_b_authorized",
    "mystic_science_authorized", "production_authorized",
)
FORBIDDEN_FALSE_STRESS = (
    "arm_network_access_performed", "arm_credentials_read", "native_file_download_performed",
    "native_file_open_performed", "protected_sws_sasze_values_read", "stage_b_authorized",
    "mystic_science_authorized", "production_authorized",
)

REBIND_SURFACES = (
    {
        "role": "portable_wrapper_case_binding",
        "path": "run_one_ena_sws_schema_probe_v3.py",
        "source": "frozen_execution_ref",
        "required_bindings": ("selected_case_id", "selected_date", "--start-case"),
    },
    {
        "role": "content_verifier_case_binding",
        "path": "tools/arm_ena_sws_e0_postartifact_v1/verify_oneevent_e0_artifact_v1.py",
        "source": "successor_package",
        "required_bindings": ("selected_case_id", "selected_date", "probe_case_id"),
    },
    {
        "role": "strict_verifier_case_binding",
        "path": "tools/arm_ena_sws_e0_postartifact_v1/verify_oneevent_e0_artifact_strict_v1.py",
        "source": "successor_package",
        "required_bindings": ("selected_case_id", "strict_content_verification"),
    },
    {
        "role": "authorized_run_envelope",
        "path": "tools/arm_ena_sws_e0_postartifact_v1/verify_authorized_run_envelope_v1.py",
        "source": "successor_package",
        "required_bindings": ("fresh_e0_authorization", "fresh_execution_ref", "fresh_execution_head", "fresh_run_attempt_1"),
    },
    {
        "role": "downloaded_zip_digest_gate",
        "path": "tools/arm_ena_sws_e0_postartifact_v1/verify_downloaded_artifact_zip_v1.py",
        "source": "successor_package",
        "required_bindings": ("fresh_e0_authorization", "fresh_execution_ref", "fresh_execution_head", "fresh_artifact_identity"),
    },
    {
        "role": "safe_extraction_gate",
        "path": "tools/arm_ena_sws_e0_postartifact_v1/extract_sanitized_artifact_zip_v1.py",
        "source": "successor_package",
        "required_bindings": ("fresh_e0_authorization", "fresh_execution_ref", "fresh_execution_head", "fresh_artifact_identity"),
    },
    {
        "role": "sanitized_ingest_pipeline",
        "path": "tools/arm_ena_sws_e0_postartifact_v1/run_sanitized_ingest_pipeline_v1.py",
        "source": "successor_package",
        "required_bindings": ("selected_case_id", "fresh_e0_authorization", "fresh_run_and_artifact_identity", "strict_cross_stage_provenance"),
    },
)


class PlanRefusal(RuntimeError):
    """Fail-closed refusal without protected-result interpretation."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_json(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    try:
        obj = json.loads(raw.decode("utf-8"))
    except Exception:
        raise PlanRefusal(f"invalid UTF-8 JSON: {path.name}") from None
    if not isinstance(obj, dict):
        raise PlanRefusal(f"JSON root must be an object: {path.name}")
    return obj, sha256_bytes(raw)


def _require_exact_keys(obj: dict[str, Any], keys: set[str], where: str) -> None:
    if set(obj) != keys:
        missing = sorted(keys - set(obj))
        extra = sorted(set(obj) - keys)
        raise PlanRefusal(f"{where} key universe drift missing={missing} extra={extra}")


def _require_false(obj: dict[str, Any], keys: tuple[str, ...], where: str) -> None:
    for key in keys:
        if obj.get(key) is not False:
            raise PlanRefusal(f"{where} forbidden activity/authority flag drift: {key}")


def _positive_int(value: Any, where: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise PlanRefusal(f"{where} must be a positive integer")
    return value


def _sha256(value: Any, where: str) -> str:
    if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
        raise PlanRefusal(f"{where} must be 64 lowercase hex")
    return value


def _artifact_digest(value: Any, where: str) -> str:
    if not isinstance(value, str):
        raise PlanRefusal(f"{where} must be sha256:<64 lowercase hex>")
    match = ARTIFACT_DIGEST_RE.fullmatch(value)
    if match is None:
        raise PlanRefusal(f"{where} must be sha256:<64 lowercase hex>")
    return match.group(1)


def load_manifest(path: Path) -> tuple[dict[str, Any], list[str]]:
    raw = path.read_bytes()
    if sha256_bytes(raw) != EXPECTED_MANIFEST_SHA256:
        raise PlanRefusal("ordered-case manifest digest mismatch")
    try:
        obj = json.loads(raw.decode("utf-8"))
    except Exception:
        raise PlanRefusal("ordered-case manifest is not valid UTF-8 JSON") from None
    if not isinstance(obj, dict):
        raise PlanRefusal("ordered-case manifest root must be an object")
    if obj.get("schema") != 1 or obj.get("purpose") != QUERY_PURPOSE or obj.get("datastream") != DATASTREAM:
        raise PlanRefusal("ordered-case manifest identity mismatch")
    cases = obj.get("ordered_case_ids")
    if not isinstance(cases, list) or len(cases) != EXPECTED_CASE_COUNT or len(set(cases)) != EXPECTED_CASE_COUNT:
        raise PlanRefusal("ordered-case manifest cardinality/uniqueness mismatch")
    if any(not isinstance(case, str) or CASE_RE.fullmatch(case) is None for case in cases):
        raise PlanRefusal("ordered-case manifest contains malformed case ID")
    return obj, list(cases)


def validate_stress(
    receipt: dict[str, Any], *, dispatch_ref: str, dispatch_sha: str
) -> None:
    _require_exact_keys(receipt, STRESS_ALLOWED_KEYS, "stress receipt")
    if receipt.get("schema") != 1 or receipt.get("status") != "EXACT_EXECUTABLE_STRESS_PASS":
        raise PlanRefusal("stress receipt status/schema mismatch")
    if receipt.get("purpose") != QUERY_PURPOSE:
        raise PlanRefusal("stress receipt purpose mismatch")
    if receipt.get("ordered_case_manifest_sha256") != EXPECTED_MANIFEST_SHA256:
        raise PlanRefusal("stress receipt manifest identity mismatch")
    if receipt.get("event_name") != "workflow_dispatch":
        raise PlanRefusal("stress receipt was not produced under workflow_dispatch")
    if receipt.get("github_ref") != dispatch_ref or receipt.get("github_sha") != dispatch_sha:
        raise PlanRefusal("stress receipt dispatch identity mismatch")
    if receipt.get("default_branch") != "main":
        raise PlanRefusal("stress receipt default branch mismatch")
    for key in ("workflow_sha256", "executable_sha256", "issue60_ledger_sha256"):
        _sha256(receipt.get(key), f"stress receipt {key}")
    for key in ("issue60_comment_count", "issue60_latest_comment_id", "baseline_coordinator_comment"):
        _positive_int(receipt.get(key), f"stress receipt {key}")
    for key in (
        "arm_relevant_comment_ids_after_baseline",
        "write_quiet_begin_ids_after_baseline",
        "write_quiet_end_ids_after_baseline",
    ):
        values = receipt.get(key)
        if not isinstance(values, list) or any(
            not isinstance(x, int) or isinstance(x, bool) or x <= 0 for x in values
        ):
            raise PlanRefusal(f"stress receipt {key} must be a positive-integer list")
    _require_false(receipt, FORBIDDEN_FALSE_STRESS, "stress receipt")


def validate_query(receipt: dict[str, Any], ordered_cases: list[str]) -> dict[str, Any]:
    _require_exact_keys(receipt, QUERY_ALLOWED_KEYS, "query receipt")
    if receipt.get("schema") != 1 or receipt.get("purpose") != QUERY_PURPOSE or receipt.get("datastream") != DATASTREAM:
        raise PlanRefusal("query receipt identity mismatch")
    if receipt.get("ordered_case_manifest_sha256") != EXPECTED_MANIFEST_SHA256:
        raise PlanRefusal("query receipt manifest identity mismatch")
    if receipt.get("ordered_case_count") != EXPECTED_CASE_COUNT:
        raise PlanRefusal("query receipt ordered-case count mismatch")
    _require_false(receipt, FORBIDDEN_FALSE_QUERY, "query receipt")

    status = receipt.get("status")
    if status != "FIRST_NATIVE_FILENAME_RESOLVED":
        if status == "EXHAUSTED_25_NO_NATIVE_FILENAME_RESOLVED":
            raise PlanRefusal("query exhausted frozen 25 cases; no successor plan may be built")
        if status == "QUERY_ERROR_FAIL_CLOSED":
            raise PlanRefusal("query failed closed; no successor plan may be built")
        raise PlanRefusal("query receipt status is unrecognized")

    checked = receipt.get("checked_cases")
    count = receipt.get("checked_case_count")
    if not isinstance(checked, list) or not checked:
        raise PlanRefusal("first-match query receipt has no checked cases")
    if not isinstance(count, int) or isinstance(count, bool) or count != len(checked) or not (1 <= count <= EXPECTED_CASE_COUNT):
        raise PlanRefusal("query receipt checked-case count mismatch")
    for ordinal, row in enumerate(checked, start=1):
        if not isinstance(row, dict) or set(row) != {"ordinal", "case_id", "date", "match_count"}:
            raise PlanRefusal("query checked-case schema drift")
        expected_case = ordered_cases[ordinal - 1]
        if row.get("ordinal") != ordinal or row.get("case_id") != expected_case or row.get("date") != expected_case[:10]:
            raise PlanRefusal("query checked-case order/date drift")
        matches = row.get("match_count")
        if not isinstance(matches, int) or isinstance(matches, bool) or matches < 0:
            raise PlanRefusal("query checked-case match_count drift")
        if ordinal < count and matches != 0:
            raise PlanRefusal("query first-match ordering violated by earlier positive case")
        if ordinal == count and matches <= 0:
            raise PlanRefusal("query final checked case is not positive")

    if receipt.get("query_error") is not None:
        raise PlanRefusal("first-match query receipt unexpectedly contains query_error")
    match = receipt.get("first_match")
    if not isinstance(match, dict) or set(match) != {"ordinal", "case_id", "date", "filenames"}:
        raise PlanRefusal("query first_match schema drift")
    final = checked[-1]
    if match.get("ordinal") != count or match.get("case_id") != final["case_id"] or match.get("date") != final["date"]:
        raise PlanRefusal("query first_match identity drift from final checked case")
    names = match.get("filenames")
    if not isinstance(names, list) or not names or names != sorted(set(names)) or len(names) != final["match_count"]:
        raise PlanRefusal("query first_match filename set/count drift")
    yyyymmdd = str(match["date"]).replace("-", "")
    for name in names:
        m = FILE_RE.fullmatch(name) if isinstance(name, str) else None
        if m is None or Path(name).name != name or m.group(1) != yyyymmdd:
            raise PlanRefusal("query first_match contains unsafe/wrong-date filename")
    return match


def build_plan(
    *,
    query_receipt: dict[str, Any],
    query_receipt_sha256: str,
    stress_receipt: dict[str, Any],
    stress_receipt_sha256: str,
    ordered_cases: list[str],
    query_authorization_comment: int,
    query_authorization_title: str,
    query_dispatch_ref: str,
    query_dispatch_sha: str,
    query_workflow_run_id: int,
    query_run_attempt: int,
    query_artifact_id: int,
    query_artifact_digest: str,
    stress_artifact_id: int,
    stress_artifact_digest: str,
) -> dict[str, Any]:
    _positive_int(query_authorization_comment, "query_authorization_comment")
    if not isinstance(query_authorization_title, str) or not query_authorization_title.startswith("COORDINATOR::") or "\n" in query_authorization_title:
        raise PlanRefusal("query_authorization_title must be one exact single-line COORDINATOR:: title")
    if query_dispatch_ref != "refs/heads/main":
        raise PlanRefusal("query-only successor planning requires exact main dispatch ref")
    _sha256(query_dispatch_sha, "query_dispatch_sha")
    _positive_int(query_workflow_run_id, "query_workflow_run_id")
    if query_run_attempt != 1:
        raise PlanRefusal("only a fresh query attempt 1 is admissible")
    _positive_int(query_artifact_id, "query_artifact_id")
    _positive_int(stress_artifact_id, "stress_artifact_id")
    query_artifact_sha = _artifact_digest(query_artifact_digest, "query_artifact_digest")
    stress_artifact_sha = _artifact_digest(stress_artifact_digest, "stress_artifact_digest")
    _sha256(query_receipt_sha256, "query_receipt_sha256")
    _sha256(stress_receipt_sha256, "stress_receipt_sha256")

    validate_stress(stress_receipt, dispatch_ref=query_dispatch_ref, dispatch_sha=query_dispatch_sha)
    match = validate_query(query_receipt, ordered_cases)

    surfaces = [
        {
            "role": surface["role"],
            "path": surface["path"],
            "source": surface["source"],
            "required_bindings": list(surface["required_bindings"]),
        }
        for surface in REBIND_SURFACES
    ]
    return {
        "schema": 1,
        "purpose": PLAN_PURPOSE,
        "status": PLAN_STATUS,
        "result_blind": True,
        "plan_is_authorization": False,
        "query_authorization_comment": query_authorization_comment,
        "query_authorization_title": query_authorization_title,
        "query_workflow_run_id": query_workflow_run_id,
        "query_run_attempt": query_run_attempt,
        "query_dispatch_ref": query_dispatch_ref,
        "query_dispatch_sha": query_dispatch_sha,
        "query_artifact_id": query_artifact_id,
        "query_artifact_digest_sha256": query_artifact_sha,
        "query_receipt_sha256": query_receipt_sha256,
        "stress_artifact_id": stress_artifact_id,
        "stress_artifact_digest_sha256": stress_artifact_sha,
        "stress_receipt_sha256": stress_receipt_sha256,
        "query_workflow_sha256": stress_receipt["workflow_sha256"],
        "query_executable_sha256": stress_receipt["executable_sha256"],
        "query_issue60_ledger_sha256": stress_receipt["issue60_ledger_sha256"],
        "ordered_case_manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "selected_ordinal": match["ordinal"],
        "selected_case_id": match["case_id"],
        "selected_date": match["date"],
        "selected_native_filenames": list(match["filenames"]),
        "selection_rule": "first positive case in frozen ordered 25-case query-only manifest",
        "frozen_e0_source_ref": FROZEN_E0_SOURCE_REF,
        "frozen_e0_source_head": FROZEN_E0_SOURCE_HEAD,
        "frozen_e0_event_universe_sha256": FROZEN_E0_UNIVERSE_SHA256,
        "frozen_e0_protocol": FROZEN_E0_PROTOCOL,
        "legacy_case_id_must_not_be_fallback": LEGACY_CASE_ID,
        "legacy_authority_must_not_be_reused": LEGACY_AUTHORITY,
        "rebind_surface_count": len(surfaces),
        "rebind_surfaces": surfaces,
        "fresh_e0_execution_authorization_required": True,
        "fresh_e0_execution_ref_head_required": True,
        "fresh_e0_run_attempt_1_required": True,
        "automatic_rebind_application_performed": False,
        "arm_network_access_performed": False,
        "arm_credentials_read": False,
        "native_file_download_performed": False,
        "native_file_open_performed": False,
        "protected_sws_sasze_values_read": False,
        "heldout_radiance_opening_authorized": False,
        "stage_b_authorized": False,
        "mystic_science_authorized": False,
        "production_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--query-receipt", type=Path, required=True)
    parser.add_argument("--stress-receipt", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--query-authorization-comment", type=int, required=True)
    parser.add_argument("--query-authorization-title", required=True)
    parser.add_argument("--query-dispatch-ref", required=True)
    parser.add_argument("--query-dispatch-sha", required=True)
    parser.add_argument("--query-workflow-run-id", type=int, required=True)
    parser.add_argument("--query-run-attempt", type=int, required=True)
    parser.add_argument("--query-artifact-id", type=int, required=True)
    parser.add_argument("--query-artifact-digest", required=True)
    parser.add_argument("--stress-artifact-id", type=int, required=True)
    parser.add_argument("--stress-artifact-digest", required=True)
    args = parser.parse_args()

    try:
        query_receipt, query_receipt_sha = _read_json(args.query_receipt)
        stress_receipt, stress_receipt_sha = _read_json(args.stress_receipt)
        _manifest, ordered_cases = load_manifest(args.manifest)
        plan = build_plan(
            query_receipt=query_receipt,
            query_receipt_sha256=query_receipt_sha,
            stress_receipt=stress_receipt,
            stress_receipt_sha256=stress_receipt_sha,
            ordered_cases=ordered_cases,
            query_authorization_comment=args.query_authorization_comment,
            query_authorization_title=args.query_authorization_title,
            query_dispatch_ref=args.query_dispatch_ref,
            query_dispatch_sha=args.query_dispatch_sha,
            query_workflow_run_id=args.query_workflow_run_id,
            query_run_attempt=args.query_run_attempt,
            query_artifact_id=args.query_artifact_id,
            query_artifact_digest=args.query_artifact_digest,
            stress_artifact_id=args.stress_artifact_id,
            stress_artifact_digest=args.stress_artifact_digest,
        )
    except (OSError, PlanRefusal) as exc:
        raise SystemExit(f"REFUSAL: {exc}") from None
    print(json.dumps(plan, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
