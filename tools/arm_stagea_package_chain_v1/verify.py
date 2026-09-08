#!/usr/bin/env python3
"""Fail-closed composite verifier for the ARM Stage-A timing-only package.

This is control-plane/result-blind only. It composes the frozen Stage-A input lock,
decoded-time continuity verifier, and source-file/datastream binding on exact stable-
captured bytes. It never opens native ARM files or protected radiance and grants no
Stage-B, science, identity, seed, ordinal, or production authority.
"""

from __future__ import annotations

import argparse
import builtins
import csv
import hashlib
import io
import json
import os
import stat
import sys
import types
from pathlib import Path
from typing import Any

EXPECTED_INPUT_LOCK_GIT_BLOB_SHA1 = "9b3e32b319a1aa29f9de9b4e92ae94ecf3091929"
EXPECTED_CONTINUITY_IMPL_GIT_BLOB_SHA1 = "49818b96c8c172d68a4b8d5cdc4e542bc7933c69"
EXPECTED_SOURCE_BINDING_IMPL_GIT_BLOB_SHA1 = "d00895f21f61a3f8d9ad9921a3d50eb46f047b75"
EXPECTED_PRIORITY_NAME = "ARM_SGP_C1_stageA_priority20.csv"
EXPECTED_HISTORICAL_REQUEST_NAME = "ARM_SGP_C1_MINIMAL_NEXT_EXTRACT_REQUEST.md"
CONTINUITY_MODULE_NAME = "tools.arm_stagea_time_continuity_contract_v1.verify"
SOURCE_BINDING_MODULE_NAME = "tools.arm_stagea_source_file_binding_v1.verify"


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


def stable_capture_regular_file(path: Path) -> bytes:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise PackageChainError(f"cannot safely open package input {path.name!r}: {type(exc).__name__}") from exc
    try:
        with os.fdopen(fd, "rb", closefd=True) as fh:
            before = os.fstat(fh.fileno())
            if not stat.S_ISREG(before.st_mode):
                raise PackageChainError(f"package input is not a regular file: {path.name!r}")
            data = fh.read()
            after = os.fstat(fh.fileno())
    except PackageChainError:
        raise
    except OSError as exc:
        raise PackageChainError(f"cannot read package input {path.name!r}: {type(exc).__name__}") from exc
    before_id = (before.st_dev, before.st_ino, before.st_mode, before.st_size, before.st_mtime_ns)
    after_id = (after.st_dev, after.st_ino, after.st_mode, after.st_size, after.st_mtime_ns)
    if before_id != after_id or len(data) != before.st_size:
        raise PackageChainError(f"package input changed during stable capture: {path.name!r}")
    try:
        path_state = path.lstat()
    except OSError as exc:
        raise PackageChainError(f"cannot restat package input {path.name!r}: {type(exc).__name__}") from exc
    if (
        not stat.S_ISREG(path_state.st_mode)
        or path_state.st_dev != after.st_dev
        or path_state.st_ino != after.st_ino
        or path_state.st_size != after.st_size
        or path_state.st_mtime_ns != after.st_mtime_ns
    ):
        raise PackageChainError(f"package input path changed during stable capture: {path.name!r}")
    return data


def _component_source_paths() -> tuple[Path, Path]:
    repo_root = Path(__file__).resolve().parents[2]
    return (
        repo_root / "tools/arm_stagea_time_continuity_contract_v1/verify.py",
        repo_root / "tools/arm_stagea_source_file_binding_v1/verify.py",
    )


def _exec_captured_module(
    name: str,
    source_path: Path,
    source_bytes: bytes,
    *,
    continuity_override: types.ModuleType | None = None,
) -> types.ModuleType:
    module = types.ModuleType(name)
    module.__file__ = str(source_path)
    module.__package__ = name.rpartition(".")[0]
    if continuity_override is not None:
        original_import = builtins.__import__
        builtins_map = dict(vars(builtins))

        def captured_import(import_name, globals=None, locals=None, fromlist=(), level=0):
            if (
                level == 0
                and import_name == "tools.arm_stagea_time_continuity_contract_v1"
                and "verify" in tuple(fromlist or ())
            ):
                package = types.ModuleType(import_name)
                package.verify = continuity_override
                return package
            return original_import(import_name, globals, locals, fromlist, level)

        builtins_map["__import__"] = captured_import
        module.__dict__["__builtins__"] = builtins_map
    code = compile(source_bytes, str(source_path), "exec", dont_inherit=True)
    exec(code, module.__dict__)
    return module


def _load_verified_component_modules() -> tuple[types.ModuleType, types.ModuleType, dict[str, str]]:
    continuity_path, source_binding_path = _component_source_paths()
    continuity_bytes = stable_capture_regular_file(continuity_path)
    source_binding_bytes = stable_capture_regular_file(source_binding_path)
    observed = {
        "continuity_verify_git_blob_sha1": git_blob_sha1_bytes(continuity_bytes),
        "source_binding_verify_git_blob_sha1": git_blob_sha1_bytes(source_binding_bytes),
    }
    expected = {
        "continuity_verify_git_blob_sha1": EXPECTED_CONTINUITY_IMPL_GIT_BLOB_SHA1,
        "source_binding_verify_git_blob_sha1": EXPECTED_SOURCE_BINDING_IMPL_GIT_BLOB_SHA1,
    }
    for key, wanted in expected.items():
        if observed[key] != wanted:
            raise PackageChainError(f"component implementation drift for {key}: {observed[key]} != {wanted}")

    continuity_module = _exec_captured_module(
        CONTINUITY_MODULE_NAME,
        continuity_path,
        continuity_bytes,
    )
    source_binding_module = _exec_captured_module(
        SOURCE_BINDING_MODULE_NAME,
        source_binding_path,
        source_binding_bytes,
        continuity_override=continuity_module,
    )
    continuity_module.__verified_source_git_blob_sha1__ = observed["continuity_verify_git_blob_sha1"]
    source_binding_module.__verified_source_git_blob_sha1__ = observed["source_binding_verify_git_blob_sha1"]
    source_binding_module.__verified_continuity_module__ = continuity_module
    return continuity_module, source_binding_module, observed


# Import-time execution itself is fail-closed: both component source files are
# stable-captured and pin-verified before either component's code is executed.
continuity, source_binding, _INITIAL_COMPONENT_PINS = _load_verified_component_modules()


def verify_component_implementation_pins() -> dict[str, str]:
    global continuity, source_binding
    verified_continuity, verified_source_binding, observed = _load_verified_component_modules()
    continuity = verified_continuity
    source_binding = verified_source_binding
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


def load_priority_cases_bytes(data: bytes) -> dict[str, dict[str, str]]:
    digest = hashlib.sha256(data).hexdigest()
    if digest != continuity.EXPECTED_PRIORITY_SHA256:
        raise continuity.ContractError(f"priority CSV sha256 mismatch: {digest}")
    try:
        rows = list(csv.DictReader(io.StringIO(data.decode("utf-8-sig"))))
    except UnicodeDecodeError as exc:
        raise continuity.ContractError("priority CSV is not valid UTF-8") from exc
    if len(rows) != continuity.EXPECTED_PRIORITY_ROWS:
        raise continuity.ContractError(
            f"priority CSV must have exactly {continuity.EXPECTED_PRIORITY_ROWS} rows"
        )
    required = {"local_civil_date", "event", "t_minus6_utc", "t_minus8_utc"}
    if not rows or not required.issubset(rows[0]):
        raise continuity.ContractError("priority CSV missing required identity/time columns")
    out: dict[str, dict[str, str]] = {}
    for row in rows:
        event = row["event"].strip().lower()
        date = row["local_civil_date"].strip()
        if event not in {"dawn", "dusk"}:
            raise continuity.ContractError(f"priority row has unsupported event {event!r}")
        case_id = f"{date}_{event}"
        if case_id in out:
            raise continuity.ContractError(f"duplicate priority case {case_id}")
        t6 = continuity.parse_utc(row["t_minus6_utc"], f"{case_id}.t_minus6_utc")
        t8 = continuity.parse_utc(row["t_minus8_utc"], f"{case_id}.t_minus8_utc")
        out[case_id] = {
            "core_start_utc": min(t6, t8).isoformat(timespec="microseconds").replace("+00:00", "Z"),
            "core_end_utc": max(t6, t8).isoformat(timespec="microseconds").replace("+00:00", "Z"),
        }
    return out


def load_continuity_csv_rows_bytes(data: bytes) -> list[dict[str, str]]:
    try:
        reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig")))
    except UnicodeDecodeError as exc:
        raise continuity.ContractError("continuity CSV is not valid UTF-8") from exc
    if reader.fieldnames is None:
        raise continuity.ContractError("continuity CSV has no header")
    missing = [column for column in continuity.REQUIRED_COLUMNS if column not in reader.fieldnames]
    if missing:
        raise continuity.ContractError(f"continuity CSV missing columns: {missing}")
    extra = [column for column in reader.fieldnames if column not in continuity.REQUIRED_COLUMNS]
    if extra:
        raise continuity.ContractError(f"continuity CSV has unexpected columns: {extra}")
    rows = list(reader)
    if len(rows) != continuity.EXPECTED_PRIORITY_ROWS * len(continuity.EXPECTED_STREAMS):
        raise continuity.ContractError("continuity CSV must contain exactly 100 rows (20 cases x 5 streams)")
    return rows


def load_continuity_json_rows_bytes(data: bytes) -> list[dict[str, Any]]:
    try:
        obj = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise continuity.ContractError("continuity JSON is invalid") from exc
    if isinstance(obj, dict):
        if set(obj) != {"rows"}:
            raise continuity.ContractError("continuity JSON object form may contain only 'rows'")
        obj = obj["rows"]
    if not isinstance(obj, list):
        raise continuity.ContractError("continuity JSON must be a row array or {'rows': [...]} object")
    if len(obj) != continuity.EXPECTED_PRIORITY_ROWS * len(continuity.EXPECTED_STREAMS):
        raise continuity.ContractError("continuity JSON must contain exactly 100 rows")
    if not all(isinstance(row, dict) for row in obj):
        raise continuity.ContractError("continuity JSON rows must be objects")
    return obj


def build_package_receipt(
    *,
    input_lock_json: Path,
    priority_csv: Path,
    continuity_csv: Path,
    continuity_json: Path,
) -> dict[str, Any]:
    implementation_pins = verify_component_implementation_pins()
    lock_receipt = verify_input_lock(input_lock_json)

    priority_bytes = stable_capture_regular_file(priority_csv)
    continuity_csv_bytes = stable_capture_regular_file(continuity_csv)
    continuity_json_bytes = stable_capture_regular_file(continuity_json)
    input_hashes = {
        "priority_csv_sha256": hashlib.sha256(priority_bytes).hexdigest(),
        "continuity_csv_sha256": hashlib.sha256(continuity_csv_bytes).hexdigest(),
        "continuity_json_sha256": hashlib.sha256(continuity_json_bytes).hexdigest(),
    }

    cases = load_priority_cases_bytes(priority_bytes)
    csv_rows = load_continuity_csv_rows_bytes(continuity_csv_bytes)
    json_rows = load_continuity_json_rows_bytes(continuity_json_bytes)
    continuity.verify_json_equivalence(csv_rows, json_rows)
    continuity_receipt = continuity.verify_rows(csv_rows, cases)
    source_binding_receipt = source_binding.verify_source_file_bindings(csv_rows)

    priority_sha = input_hashes["priority_csv_sha256"]
    continuity_csv_sha = input_hashes["continuity_csv_sha256"]
    continuity_json_sha = input_hashes["continuity_json_sha256"]
    continuity_receipt.update(
        {
            "priority_csv_sha256": priority_sha,
            "continuity_csv_sha256": continuity_csv_sha,
            "continuity_json_sha256": continuity_json_sha,
        }
    )
    if priority_sha != lock_receipt["priority_csv_sha256"]:
        raise PackageChainError("priority CSV does not match frozen input lock")

    source_binding_receipt = dict(source_binding_receipt)
    source_binding_receipt["continuity_csv_sha256"] = continuity_csv_sha

    if continuity_receipt.get("artifact_contract_valid") is not True:
        raise PackageChainError("continuity component did not return artifact_contract_valid=true")
    if source_binding_receipt.get("source_file_binding_valid") is not True:
        raise PackageChainError("source-binding component did not return source_file_binding_valid=true")

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
                raise PackageChainError(f"{component_name} component boundary requires {key}=false")
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
        "component_code_executed_from_verified_captured_bytes": True,
        "same_input_bytes_hashed_and_parsed": True,
        "same_continuity_csv_bound_across_components": True,
        "input_lock": lock_receipt,
        "component_implementation_pins": implementation_pins,
        "inputs": input_hashes,
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
