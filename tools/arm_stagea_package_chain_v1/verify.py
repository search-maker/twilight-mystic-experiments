#!/usr/bin/env python3
"""Fail-closed composite verifier for the ARM Stage-A timing-only package.

This is control-plane/result-blind only. It composes the frozen Stage-A input lock,
decoded-time continuity verifier, and source-file/datastream binding on the exact same
continuity bytes. It never opens native ARM files or protected radiance and grants no
Stage-B, science, identity, seed, ordinal, or production authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from tools.arm_stagea_source_file_binding_v1 import verify as source_binding
from tools.arm_stagea_time_continuity_contract_v1 import verify as continuity

EXPECTED_INPUT_LOCK_GIT_BLOB_SHA1 = "9b3e32b319a1aa29f9de9b4e92ae94ecf3091929"
EXPECTED_CONTINUITY_IMPL_GIT_BLOB_SHA1 = "49818b96c8c172d68a4b8d5cdc4e542bc7933c69"
EXPECTED_SOURCE_BINDING_IMPL_GIT_BLOB_SHA1 = "d00895f21f61a3f8d9ad9921a3d50eb46f047b75"
EXPECTED_PRIORITY_NAME = "ARM_SGP_C1_stageA_priority20.csv"
EXPECTED_HISTORICAL_REQUEST_NAME = "ARM_SGP_C1_MINIMAL_NEXT_EXTRACT_REQUEST.md"


class PackageChainError(ValueError):
    pass


def git_blob_sha1_bytes(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data, usedforsecurity=False).hexdigest()


def git_blob_sha1(path: Path) -> str:
    return git_blob_sha1_bytes(path.read_bytes())


def canonical_json_sha256(obj: Any) -> str:
    data = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def verify_component_implementation_pins() -> dict[str, str]:
    observed = {
        "continuity_verify_git_blob_sha1": git_blob_sha1(Path(continuity.__file__).resolve()),
        "source_binding_verify_git_blob_sha1": git_blob_sha1(Path(source_binding.__file__).resolve()),
    }
    expected = {
        "continuity_verify_git_blob_sha1": EXPECTED_CONTINUITY_IMPL_GIT_BLOB_SHA1,
        "source_binding_verify_git_blob_sha1": EXPECTED_SOURCE_BINDING_IMPL_GIT_BLOB_SHA1,
    }
    for key, wanted in expected.items():
        if observed[key] != wanted:
            raise PackageChainError(f"component implementation drift for {key}: {observed[key]} != {wanted}")
    return observed


def verify_input_lock(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    observed_blob = git_blob_sha1_bytes(data)
    if observed_blob != EXPECTED_INPUT_LOCK_GIT_BLOB_SHA1:
        raise PackageChainError(
            f"input lock git blob mismatch: {observed_blob} != {EXPECTED_INPUT_LOCK_GIT_BLOB_SHA1}"
        )
    try:
        obj = json.loads(data.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise PackageChainError("input lock JSON is invalid") from exc
    if not isinstance(obj, dict) or obj.get("schema") != 1:
        raise PackageChainError("input lock must be schema 1 object")

    files = obj.get("files")
    if not isinstance(files, list):
        raise PackageChainError("input lock files must be a list")
    by_name: dict[str, dict[str, Any]] = {}
    for item in files:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise PackageChainError("input lock files contain malformed entry")
        if item["name"] in by_name:
            raise PackageChainError(f"input lock duplicate file entry {item['name']!r}")
        by_name[item["name"]] = item

    priority = by_name.get(EXPECTED_PRIORITY_NAME)
    if priority is None:
        raise PackageChainError("input lock lacks frozen priority ledger entry")
    if priority.get("sha256") != continuity.EXPECTED_PRIORITY_SHA256:
        raise PackageChainError("input lock priority SHA-256 disagrees with continuity verifier")
    if priority.get("data_row_count") != continuity.EXPECTED_PRIORITY_ROWS:
        raise PackageChainError("input lock priority row count disagrees with continuity verifier")

    historical = by_name.get(EXPECTED_HISTORICAL_REQUEST_NAME)
    if historical is None or historical.get("active_execution_contract") is not False:
        raise PackageChainError("historical extract request must remain provenance-only")

    governance = obj.get("governance_supersession")
    if not isinstance(governance, dict):
        raise PackageChainError("input lock lacks governance supersession")
    if governance.get("protected_sasze_radiance_must_remain_sealed") is not True:
        raise PackageChainError("input lock must keep protected SASZE radiance sealed")
    if governance.get("historical_extract_request_may_authorize_radiance_opening") is not False:
        raise PackageChainError("historical extract request must not authorize radiance opening")

    safety = obj.get("safety_boundary")
    if not isinstance(safety, dict):
        raise PackageChainError("input lock lacks safety boundary")
    required_false = (
        "protected_results_opened",
        "heldout_sws_sasze_radiance_opened",
        "stage_b_authorized",
        "science_execution_authorized",
        "production_authorized",
    )
    for key in required_false:
        if safety.get(key) is not False:
            raise PackageChainError(f"input lock safety boundary requires {key}=false")
    if safety.get("result_blind") is not True or safety.get("missing_native_data_counts_as_pass") is not False:
        raise PackageChainError("input lock result-blind/missing-data boundary drifted")

    return {
        "input_lock_git_blob_sha1": observed_blob,
        "priority_csv_sha256": priority["sha256"],
        "priority_data_row_count": priority["data_row_count"],
        "historical_extract_request_active_execution_contract": False,
        "protected_sasze_radiance_must_remain_sealed": True,
    }


def build_package_receipt(
    *,
    input_lock_json: Path,
    priority_csv: Path,
    continuity_csv: Path,
    continuity_json: Path,
) -> dict[str, Any]:
    implementation_pins = verify_component_implementation_pins()
    lock_receipt = verify_input_lock(input_lock_json)

    before_hashes = {
        "priority_csv_sha256": continuity.sha256(priority_csv),
        "continuity_csv_sha256": continuity.sha256(continuity_csv),
        "continuity_json_sha256": continuity.sha256(continuity_json),
    }

    cases = continuity.load_priority_cases(priority_csv)
    csv_rows = continuity.load_csv_rows(continuity_csv)
    json_rows = continuity.load_json_rows(continuity_json)
    continuity.verify_json_equivalence(csv_rows, json_rows)
    continuity_receipt = continuity.verify_rows(csv_rows, cases)

    source_binding_receipt = source_binding.verify_source_file_bindings(csv_rows)

    after_hashes = {
        "priority_csv_sha256": continuity.sha256(priority_csv),
        "continuity_csv_sha256": continuity.sha256(continuity_csv),
        "continuity_json_sha256": continuity.sha256(continuity_json),
    }
    if after_hashes != before_hashes:
        raise PackageChainError("Stage-A timing package input bytes changed during verification")

    priority_sha = before_hashes["priority_csv_sha256"]
    continuity_csv_sha = before_hashes["continuity_csv_sha256"]
    continuity_json_sha = before_hashes["continuity_json_sha256"]
    continuity_receipt.update(
        {
            "priority_csv_sha256": priority_sha,
            "continuity_csv_sha256": continuity_csv_sha,
            "continuity_json_sha256": continuity_json_sha,
        }
    )
    if priority_sha != lock_receipt["priority_csv_sha256"]:
        raise PackageChainError("priority CSV does not match frozen input lock")

    # v1 source binding receipt predates an input digest; bind it here to the exact
    # same CSV bytes that were already passed through the continuity verifier.
    source_binding_receipt = dict(source_binding_receipt)
    source_binding_receipt["continuity_csv_sha256"] = continuity_csv_sha

    if continuity_receipt.get("artifact_contract_valid") is not True:
        raise PackageChainError("continuity component did not return artifact_contract_valid=true")
    if source_binding_receipt.get("source_file_binding_valid") is not True:
        raise PackageChainError("source-binding component did not return source_file_binding_valid=true")

    # The exact component implementations are pinned, but also refuse any runtime
    # receipt that weakens the established result-blind boundary. This catches
    # accidental monkeypatching/wrapper substitution and makes the composite
    # contract self-contained for downstream receipt consumers.
    required_false = (
        "scientific_pass_inferred",
        "missing_native_data_counts_as_pass",
        "protected_results_opened",
        "heldout_sws_sasze_radiance_opened",
        "heldout_radiance_opening_authorized",
        "stage_b_authorized",
        "science_execution_authorized",
        "production_authorized",
    )
    for component_name, component_receipt in (
        ("continuity", continuity_receipt),
        ("source_file_binding", source_binding_receipt),
    ):
        for key in required_false:
            if component_receipt.get(key) is not False:
                raise PackageChainError(
                    f"{component_name} component boundary requires {key}=false"
                )
    if source_binding_receipt.get("upstream_continuity_contract_pass_inferred") is not False:
        raise PackageChainError(
            "source-binding component must not independently infer upstream continuity PASS"
        )

    case_continuity = continuity_receipt.get("case_continuity")
    if not isinstance(case_continuity, dict) or len(case_continuity) != continuity.EXPECTED_PRIORITY_ROWS:
        raise PackageChainError("continuity receipt case coverage drifted")
    if any(value not in {"PASS", "FAIL"} for value in case_continuity.values()):
        raise PackageChainError("continuity receipt contains unsupported case status")
    case_pass_count = continuity_receipt.get("case_pass_count")
    case_fail_count = continuity_receipt.get("case_fail_count")
    if not isinstance(case_pass_count, int) or not isinstance(case_fail_count, int):
        raise PackageChainError("continuity receipt case counts must be integers")
    if case_pass_count + case_fail_count != continuity.EXPECTED_PRIORITY_ROWS:
        raise PackageChainError("continuity receipt case counts do not cover frozen 20 cases")
    if case_pass_count != sum(value == "PASS" for value in case_continuity.values()):
        raise PackageChainError("continuity receipt PASS count disagrees with case map")
    if case_fail_count != sum(value == "FAIL" for value in case_continuity.values()):
        raise PackageChainError("continuity receipt FAIL count disagrees with case map")

    return {
        "schema": 1,
        "stagea_timing_package_contract_valid": True,
        "result_blind": True,
        "same_continuity_csv_bound_across_components": True,
        "input_lock": lock_receipt,
        "component_implementation_pins": implementation_pins,
        "inputs": {
            "priority_csv_sha256": priority_sha,
            "continuity_csv_sha256": continuity_csv_sha,
            "continuity_json_sha256": continuity_json_sha,
        },
        "component_receipt_sha256": {
            "continuity": canonical_json_sha256(continuity_receipt),
            "source_file_binding": canonical_json_sha256(source_binding_receipt),
        },
        "continuity_artifact_contract_valid": True,
        "source_file_binding_valid": True,
        "case_continuity": case_continuity,
        "case_pass_count": case_pass_count,
        "case_fail_count": case_fail_count,
        "scientific_pass_inferred": False,
        "missing_native_data_counts_as_pass": False,
        "protected_results_opened": False,
        "heldout_sws_sasze_radiance_opened": False,
        "heldout_radiance_opening_authorized": False,
        "stage_b_authorized": False,
        "science_execution_authorized": False,
        "production_authorized": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-lock-json", required=True, type=Path)
    parser.add_argument("--priority-csv", required=True, type=Path)
    parser.add_argument("--continuity-csv", required=True, type=Path)
    parser.add_argument("--continuity-json", required=True, type=Path)
    parser.add_argument("--receipt-json", type=Path)
    args = parser.parse_args(argv)

    try:
        receipt = build_package_receipt(
            input_lock_json=args.input_lock_json,
            priority_csv=args.priority_csv,
            continuity_csv=args.continuity_csv,
            continuity_json=args.continuity_json,
        )
    except (
        PackageChainError,
        continuity.ContractError,
        source_binding.SourceBindingError,
        OSError,
    ) as exc:
        print(f"ARM_STAGEA_PACKAGE_CHAIN_FAIL: {exc}", file=sys.stderr)
        return 2

    text = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.receipt_json:
        args.receipt_json.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
