#!/usr/bin/env python3
"""Freeze the metadata-selected ARM ENA/SWS E0 successor case.

This tool is intentionally result-blind with respect to SWS/SASZE values. It
consumes only the sanitized query-only receipt, the zero-runtime stress receipt,
the already-frozen ordered 25-case manifest, and externally verified GitHub run
and artifact identities. It never contacts ARM, downloads native files, opens
radiance, authorizes Stage B, or changes the frozen E0 scientific semantics.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

QUERY_PURPOSE = "ARM_ENA_SWS_V1_E0_SUCCESSOR_QUERY_ONLY_AVAILABILITY_DISCOVERY"
FREEZE_PURPOSE = "ARM_ENA_SWS_V1_E0_SUCCESSOR_CASE_FREEZE_V1"
DATASTREAM = "enaswsC1.b1"
EXPECTED_MANIFEST_SHA256 = "8a0756be59dac59cd8ad4fab77e499ec19069e24d2d2a636fa4352713b550def"
EXPECTED_CASE_COUNT = 25
AUTHORIZED_QUERY_MAIN_SHA = "5f3e3de7395ce20d79a210066d0836515d35996f"
AUTHORIZED_QUERY_REF = "refs/heads/main"
AUTHORIZATION_COMMENT = 5592250337
FROZEN_E0_UNIVERSE_SHA256 = "87933189ff56322ce2b5d2821a1c2ab8094d0a472ef6c690cfbd90cd0451fa41"
FROZEN_E0_PROTOCOL = "ARM_ENA_SWS_V1_STAGE0_E0_RESULT_BLIND_V2"
FROZEN_E0_CONTROL_COMMENT = "5487647692"
FROZEN_E0_SOURCE_REF = "review/arm-ena-sws-v1-stage0"
FROZEN_E0_SOURCE_HEAD = "b8671665a2bf8fe9972b8cb48492abcfa6765140"
FILE_RE = re.compile(r"^enaswsC1\.b1\.(\d{8})\..*\.(?:nc|cdf)$", re.I)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ARTIFACT_DIGEST_RE = re.compile(r"^sha256:([0-9a-f]{64})$")

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
    "native_file_open_performed", "protected_sws_sasze_values_read",
    "stage_b_authorized", "mystic_science_authorized", "production_authorized",
)


class FreezeRefusal(RuntimeError):
    """Fail-closed refusal without protected-result interpretation."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    try:
        obj = json.loads(raw.decode("utf-8"))
    except Exception:
        raise FreezeRefusal(f"invalid UTF-8 JSON: {path.name}") from None
    if not isinstance(obj, dict):
        raise FreezeRefusal(f"JSON root must be an object: {path.name}")
    return obj, sha256_bytes(raw)


def load_manifest(path: Path) -> tuple[dict[str, Any], list[str]]:
    raw = path.read_bytes()
    if sha256_bytes(raw) != EXPECTED_MANIFEST_SHA256:
        raise FreezeRefusal("ordered-case manifest digest mismatch")
    try:
        obj = json.loads(raw.decode("utf-8"))
    except Exception:
        raise FreezeRefusal("ordered-case manifest is not valid UTF-8 JSON") from None
    if not isinstance(obj, dict):
        raise FreezeRefusal("ordered-case manifest root must be an object")
    if obj.get("schema") != 1 or obj.get("purpose") != QUERY_PURPOSE or obj.get("datastream") != DATASTREAM:
        raise FreezeRefusal("ordered-case manifest identity mismatch")
    cases = obj.get("ordered_case_ids")
    if not isinstance(cases, list) or len(cases) != EXPECTED_CASE_COUNT or len(set(cases)) != EXPECTED_CASE_COUNT:
        raise FreezeRefusal("ordered-case manifest cardinality/uniqueness mismatch")
    for case in cases:
        if not isinstance(case, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}_dusk", case):
            raise FreezeRefusal("ordered-case manifest contains malformed case ID")
    return obj, list(cases)


def _require_exact_keys(obj: dict[str, Any], keys: set[str], where: str) -> None:
    if set(obj) != keys:
        missing = sorted(keys - set(obj))
        extra = sorted(set(obj) - keys)
        raise FreezeRefusal(f"{where} key universe drift missing={missing} extra={extra}")


def _require_false(obj: dict[str, Any], keys: tuple[str, ...], where: str) -> None:
    for key in keys:
        if obj.get(key) is not False:
            raise FreezeRefusal(f"{where} forbidden activity/authority flag drift: {key}")


def validate_stress(receipt: dict[str, Any]) -> None:
    _require_exact_keys(receipt, STRESS_ALLOWED_KEYS, "stress receipt")
    if receipt.get("schema") != 1 or receipt.get("status") != "EXACT_EXECUTABLE_STRESS_PASS":
        raise FreezeRefusal("stress receipt status/schema mismatch")
    if receipt.get("purpose") != QUERY_PURPOSE:
        raise FreezeRefusal("stress receipt purpose mismatch")
    if receipt.get("ordered_case_manifest_sha256") != EXPECTED_MANIFEST_SHA256:
        raise FreezeRefusal("stress receipt manifest identity mismatch")
    if receipt.get("event_name") != "workflow_dispatch":
        raise FreezeRefusal("stress receipt was not produced under workflow_dispatch")
    if receipt.get("github_ref") != AUTHORIZED_QUERY_REF:
        raise FreezeRefusal("stress receipt dispatch ref mismatch")
    if receipt.get("github_sha") != AUTHORIZED_QUERY_MAIN_SHA:
        raise FreezeRefusal("stress receipt exact-main SHA mismatch")
    if receipt.get("default_branch") != "main":
        raise FreezeRefusal("stress receipt default branch mismatch")
    for key in ("workflow_sha256", "executable_sha256", "issue60_ledger_sha256"):
        value = receipt.get(key)
        if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
            raise FreezeRefusal(f"stress receipt {key} is not SHA-256")
    for key in ("issue60_comment_count", "issue60_latest_comment_id", "baseline_coordinator_comment"):
        value = receipt.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise FreezeRefusal(f"stress receipt {key} must be positive integer")
    if receipt.get("baseline_coordinator_comment") != 5590748165:
        raise FreezeRefusal("stress receipt governance baseline mismatch")
    for key in (
        "arm_relevant_comment_ids_after_baseline",
        "write_quiet_begin_ids_after_baseline",
        "write_quiet_end_ids_after_baseline",
    ):
        values = receipt.get(key)
        if not isinstance(values, list) or any(not isinstance(x, int) or isinstance(x, bool) or x <= 0 for x in values):
            raise FreezeRefusal(f"stress receipt {key} must be a positive-integer list")
    _require_false(receipt, FORBIDDEN_FALSE_STRESS, "stress receipt")


def validate_query(receipt: dict[str, Any], ordered_cases: list[str]) -> dict[str, Any]:
    _require_exact_keys(receipt, QUERY_ALLOWED_KEYS, "query receipt")
    if receipt.get("schema") != 1 or receipt.get("purpose") != QUERY_PURPOSE or receipt.get("datastream") != DATASTREAM:
        raise FreezeRefusal("query receipt identity mismatch")
    if receipt.get("ordered_case_manifest_sha256") != EXPECTED_MANIFEST_SHA256:
        raise FreezeRefusal("query receipt manifest identity mismatch")
    if receipt.get("ordered_case_count") != EXPECTED_CASE_COUNT:
        raise FreezeRefusal("query receipt ordered-case count mismatch")
    _require_false(receipt, FORBIDDEN_FALSE_QUERY, "query receipt")

    status = receipt.get("status")
    if status != "FIRST_NATIVE_FILENAME_RESOLVED":
        if status == "EXHAUSTED_25_NO_NATIVE_FILENAME_RESOLVED":
            raise FreezeRefusal("query exhausted frozen 25 cases; no E0 successor case may be frozen")
        if status == "QUERY_ERROR_FAIL_CLOSED":
            raise FreezeRefusal("query transport/contract failed closed; no E0 successor case may be frozen")
        raise FreezeRefusal("query receipt status is unrecognized")

    checked = receipt.get("checked_cases")
    if not isinstance(checked, list) or not checked:
        raise FreezeRefusal("first-match query receipt has no checked cases")
    count = receipt.get("checked_case_count")
    if not isinstance(count, int) or isinstance(count, bool) or count != len(checked) or not (1 <= count <= EXPECTED_CASE_COUNT):
        raise FreezeRefusal("query receipt checked-case count mismatch")
    for ordinal, row in enumerate(checked, start=1):
        if not isinstance(row, dict) or set(row) != {"ordinal", "case_id", "date", "match_count"}:
            raise FreezeRefusal("query checked-case schema drift")
        if row.get("ordinal") != ordinal or row.get("case_id") != ordered_cases[ordinal - 1]:
            raise FreezeRefusal("query checked-case order drift")
        if row.get("date") != ordered_cases[ordinal - 1][:10]:
            raise FreezeRefusal("query checked-case date drift")
        matches = row.get("match_count")
        if not isinstance(matches, int) or isinstance(matches, bool) or matches < 0:
            raise FreezeRefusal("query checked-case match_count drift")
        if ordinal < count and matches != 0:
            raise FreezeRefusal("query first-match ordering violated by earlier positive case")
        if ordinal == count and matches <= 0:
            raise FreezeRefusal("query final checked case is not positive")

    if receipt.get("query_error") is not None:
        raise FreezeRefusal("first-match query receipt unexpectedly contains query_error")
    match = receipt.get("first_match")
    if not isinstance(match, dict) or set(match) != {"ordinal", "case_id", "date", "filenames"}:
        raise FreezeRefusal("query first_match schema drift")
    final = checked[-1]
    if match.get("ordinal") != count or match.get("case_id") != final["case_id"] or match.get("date") != final["date"]:
        raise FreezeRefusal("query first_match identity drift from final checked case")
    names = match.get("filenames")
    if not isinstance(names, list) or not names or names != sorted(set(names)) or len(names) != final["match_count"]:
        raise FreezeRefusal("query first_match filename set/count drift")
    yyyymmdd = str(match["date"]).replace("-", "")
    for name in names:
        m = FILE_RE.fullmatch(name) if isinstance(name, str) else None
        if not m or Path(name).name != name or m.group(1) != yyyymmdd:
            raise FreezeRefusal("query first_match contains unsafe/wrong-date filename")
    return match


def _artifact_digest(value: str, where: str) -> str:
    m = ARTIFACT_DIGEST_RE.fullmatch(value)
    if not m:
        raise FreezeRefusal(f"{where} must be sha256:<64 lowercase hex>")
    return m.group(1)


def _positive_int(value: int, where: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise FreezeRefusal(f"{where} must be positive integer")
    return value


def build_freeze(
    *,
    query_receipt: dict[str, Any],
    query_receipt_sha256: str,
    stress_receipt: dict[str, Any],
    stress_receipt_sha256: str,
    ordered_cases: list[str],
    workflow_run_id: int,
    run_attempt: int,
    query_artifact_id: int,
    query_artifact_digest: str,
    stress_artifact_id: int,
    stress_artifact_digest: str,
) -> dict[str, Any]:
    validate_stress(stress_receipt)
    match = validate_query(query_receipt, ordered_cases)
    _positive_int(workflow_run_id, "workflow_run_id")
    if run_attempt != 1:
        raise FreezeRefusal("only fresh attempt 1 is admissible")
    _positive_int(query_artifact_id, "query_artifact_id")
    _positive_int(stress_artifact_id, "stress_artifact_id")
    query_artifact_sha = _artifact_digest(query_artifact_digest, "query artifact digest")
    stress_artifact_sha = _artifact_digest(stress_artifact_digest, "stress artifact digest")

    return {
        "schema": 1,
        "purpose": FREEZE_PURPOSE,
        "status": "E0_SUCCESSOR_CASE_FROZEN",
        "authorization_comment": AUTHORIZATION_COMMENT,
        "query_workflow_run_id": workflow_run_id,
        "query_run_attempt": run_attempt,
        "query_dispatch_ref": AUTHORIZED_QUERY_REF,
        "query_dispatch_sha": AUTHORIZED_QUERY_MAIN_SHA,
        "query_artifact_id": query_artifact_id,
        "query_artifact_digest_sha256": query_artifact_sha,
        "query_receipt_sha256": query_receipt_sha256,
        "stress_artifact_id": stress_artifact_id,
        "stress_artifact_digest_sha256": stress_artifact_sha,
        "stress_receipt_sha256": stress_receipt_sha256,
        "query_workflow_sha256": stress_receipt["workflow_sha256"],
        "query_executable_sha256": stress_receipt["executable_sha256"],
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
        "frozen_e0_control_comment": FROZEN_E0_CONTROL_COMMENT,
        "e0_scientific_semantics_change_authorized": False,
        "native_file_download_authorized": False,
        "native_file_opening_authorized": False,
        "protected_sws_sasze_values_read": False,
        "heldout_radiance_opening_authorized": False,
        "stage_b_authorized": False,
        "mystic_science_authorized": False,
        "production_authorized": False,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    default_manifest = Path(__file__).resolve().parents[1] / "arm_ena_sws_query_only_availability_v1" / "ordered_25_cases.json"
    ap.add_argument("--query-receipt", type=Path, required=True)
    ap.add_argument("--stress-receipt", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, default=default_manifest)
    ap.add_argument("--workflow-run-id", type=int, required=True)
    ap.add_argument("--run-attempt", type=int, required=True)
    ap.add_argument("--query-artifact-id", type=int, required=True)
    ap.add_argument("--query-artifact-digest", required=True)
    ap.add_argument("--stress-artifact-id", type=int, required=True)
    ap.add_argument("--stress-artifact-digest", required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args(argv)

    try:
        _, ordered_cases = load_manifest(args.manifest)
        query, query_sha = read_json(args.query_receipt)
        stress, stress_sha = read_json(args.stress_receipt)
        result = build_freeze(
            query_receipt=query,
            query_receipt_sha256=query_sha,
            stress_receipt=stress,
            stress_receipt_sha256=stress_sha,
            ordered_cases=ordered_cases,
            workflow_run_id=args.workflow_run_id,
            run_attempt=args.run_attempt,
            query_artifact_id=args.query_artifact_id,
            query_artifact_digest=args.query_artifact_digest,
            stress_artifact_id=args.stress_artifact_id,
            stress_artifact_digest=args.stress_artifact_digest,
        )
    except FreezeRefusal as exc:
        print(json.dumps({"status": "REFUSED", "reason": str(exc)}, sort_keys=True))
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "selected_ordinal": result["selected_ordinal"],
        "selected_case_id": result["selected_case_id"],
        "protected_sws_sasze_values_read": False,
        "stage_b_authorized": False,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
