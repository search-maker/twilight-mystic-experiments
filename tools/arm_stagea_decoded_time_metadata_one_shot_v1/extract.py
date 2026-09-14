#!/usr/bin/env python3
"""ARM Stage-A decoded-time metadata one-shot extractor.

This executable is deliberately narrow. It may authenticate to ARM Live only when
run under a separately authorized workflow_dispatch. It downloads native files only
into a temporary directory, reads only native time-coordinate variables plus the
explicitly allowed HSRL header/QC-presence metadata, emits aggregate timing/provenance
rows, and deletes all native files before returning. It never reads SASZE radiance or
other science arrays and never runs any model/solver.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import os
import re
import shutil
import statistics
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable, Iterable

BASE_URL = "https://adc.arm.gov/armlive"
REQUEST_SHA256 = "5ec3fb6b052d886091a77704bf425abcb0d04ea4279727c3a37b4f5ab6e63318"
PRIORITY_SHA256 = "345d7023bb4e29e0cc7bb47f1eaaef33636e0bd1719d05e796e3d30cba310ae0"
EXPECTED_CASES = 20
WORKFLOW_PATH = ".github/workflows/arm-stagea-decoded-time-metadata-one-shot-v1.yml"
STREAMS = {
    "sgpsaszefilterbandsC1.a1": "sasze_filterbands",
    "sgphsrlC1.a1": "hsrl",
    "sgprlprofbeC1.c1": "rlprofbe",
    "sgparsclkazr1kolliasC1.c0": "arscl",
    "sgpceilC1.b1": "ceil",
}
QC_PRESENCE_NAMES = ("qc_level_backsct", "qc_aerosol_depol", "qc_volume_depol")
REQUIRED_COLUMNS = (
    "case_id", "stream", "core_start_utc", "core_end_utc", "source_files",
    "source_sha256s", "decoded_time_basis", "code_version", "sample_count_core",
    "left_bracket_utc", "right_bracket_utc", "left_bracket_delta_s",
    "right_bracket_delta_s", "median_positive_cadence_s", "max_gap_s",
    "duplicate_count", "nonfinite_or_masked_count", "continuity_pass", "failure_reason",
)
RECEIPT_KEYS = {
    "schema", "status", "authorization_comment_id", "workflow_path", "workflow_blob_sha",
    "main_sha", "event", "ref", "run_id", "run_attempt", "request_contract_sha256",
    "priority_ledger_sha256", "continuity_csv_sha256", "continuity_json_sha256",
    "row_count", "hsrl_code_version_set", "hsrl_allowed_header_binding_sha256s",
    "hsrl_qc_presence", "credential_values_logged", "raw_native_files_persisted",
    "raw_time_arrays_persisted", "science_arrays_read", "heldout_sws_sasze_radiance_opened",
    "stage_b_authorized", "mystic_science_authorized", "taylor_or_jerusalem_used",
    "production_authorized", "failure_reason",
}
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
NATIVE_FILE_RE = re.compile(r"^[A-Za-z0-9_.-]+\.(?:nc|cdf)$", re.I)


class ExtractionError(RuntimeError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def iso_z(epoch_s: float) -> str:
    x = dt.datetime.fromtimestamp(epoch_s, tz=dt.timezone.utc)
    return x.isoformat(timespec="microseconds").replace("+00:00", "Z")


def parse_z(value: str) -> dt.datetime:
    if not value.endswith("Z"):
        raise ExtractionError("priority timestamp is not UTC Z form")
    try:
        x = dt.datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ExtractionError("priority timestamp is invalid") from exc
    if x.utcoffset() != dt.timedelta(0):
        raise ExtractionError("priority timestamp is not UTC")
    return x


def _require_frozen_file(path: Path, expected_sha: str) -> bytes:
    raw = path.read_bytes()
    digest = sha256_bytes(raw)
    if digest != expected_sha:
        raise ExtractionError(f"frozen file digest mismatch for {path.name}: {digest}")
    return raw


def load_priority(path: Path) -> list[dict[str, str]]:
    raw = _require_frozen_file(path, PRIORITY_SHA256)
    rows = list(csv.DictReader(raw.decode("utf-8-sig").splitlines()))
    if len(rows) != EXPECTED_CASES:
        raise ExtractionError("priority ledger must contain exactly 20 rows")
    need = {"local_civil_date", "event", "t_minus6_utc", "t_minus8_utc"}
    if not rows or not need.issubset(rows[0]):
        raise ExtractionError("priority ledger identity/time columns missing")
    seen: set[str] = set()
    for row in rows:
        event = row["event"].strip().lower()
        if event not in {"dawn", "dusk"}:
            raise ExtractionError("unsupported priority event")
        case_id = f"{row['local_civil_date'].strip()}_{event}"
        if case_id in seen:
            raise ExtractionError("duplicate priority case")
        seen.add(case_id)
        parse_z(row["t_minus6_utc"])
        parse_z(row["t_minus8_utc"])
    return rows


def _case_core(row: dict[str, str]) -> tuple[str, dt.datetime, dt.datetime]:
    event = row["event"].strip().lower()
    case_id = f"{row['local_civil_date'].strip()}_{event}"
    a, b = parse_z(row["t_minus6_utc"]), parse_z(row["t_minus8_utc"])
    return case_id, min(a, b), max(a, b)


def _query_days(start: dt.datetime, end: dt.datetime) -> list[str]:
    days = {start.date() - dt.timedelta(days=1), start.date(), end.date(), end.date() + dt.timedelta(days=1)}
    return [x.isoformat() for x in sorted(days)]


def _json_filenames(obj: Any) -> list[str]:
    names: set[str] = set()
    def walk(v: Any) -> None:
        if isinstance(v, dict):
            for child in v.values(): walk(child)
        elif isinstance(v, list):
            for child in v: walk(child)
        elif isinstance(v, str):
            base = os.path.basename(v)
            if NATIVE_FILE_RE.fullmatch(base): names.add(base)
    walk(obj)
    return sorted(names)


def _query_payload(userpair: str, datastream: str, day: str, opener: Callable[..., Any] = urllib.request.urlopen) -> Any:
    next_day = (dt.date.fromisoformat(day) + dt.timedelta(days=1)).isoformat()
    params = urllib.parse.urlencode({"user": userpair, "ds": datastream, "start": day, "end": next_day, "wt": "json"})
    req = urllib.request.Request(BASE_URL + "/query?" + params, headers={"User-Agent": "arm-stagea-decoded-time-metadata-one-shot-v1/1"})
    try:
        with opener(req, timeout=120) as resp:
            body = resp.read()
    except Exception as exc:
        raise ExtractionError("ARM Live query transport failure: " + type(exc).__name__) from None
    try:
        return json.loads(body.decode("utf-8"))
    except Exception:
        raise ExtractionError("ARM Live query returned invalid JSON") from None


def query_native_names(userpair: str, datastream: str, start: dt.datetime, end: dt.datetime, opener: Callable[..., Any] = urllib.request.urlopen) -> list[str]:
    prefix = datastream + "."
    names: set[str] = set()
    for day in _query_days(start, end):
        payload = _query_payload(userpair, datastream, day, opener=opener)
        for name in _json_filenames(payload):
            if name.startswith(prefix) and NATIVE_FILE_RE.fullmatch(name):
                names.add(name)
    return sorted(names)


def download_native(userpair: str, filename: str, dest: Path, opener: Callable[..., Any] = urllib.request.urlopen) -> None:
    if os.path.basename(filename) != filename or not NATIVE_FILE_RE.fullmatch(filename):
        raise ExtractionError("unsafe native filename")
    params = urllib.parse.urlencode({"user": userpair, "file": filename})
    req = urllib.request.Request(BASE_URL + "/saveData?" + params, headers={"User-Agent": "arm-stagea-decoded-time-metadata-one-shot-v1/1"})
    try:
        with opener(req, timeout=300) as resp, dest.open("wb") as out:
            while True:
                chunk = resp.read(1024 * 1024)
                if not chunk: break
                out.write(chunk)
    except Exception as exc:
        try: dest.unlink()
        except FileNotFoundError: pass
        raise ExtractionError("ARM Live native transport failure: " + type(exc).__name__) from None
    if not dest.is_file() or dest.stat().st_size <= 0:
        raise ExtractionError("ARM Live native download produced empty file")


def _import_netcdf4():
    try:
        import netCDF4  # type: ignore
        import numpy as np  # type: ignore
    except Exception as exc:
        raise ExtractionError("netCDF4/numpy runtime dependency unavailable") from exc
    return netCDF4, np


def _as_scalar(value: Any) -> Any:
    try:
        if hasattr(value, "item"): return value.item()
    except Exception:
        pass
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _allowed_hsrl_header_binding(ds: Any) -> tuple[str, str, dict[str, bool]]:
    code_version = str(_as_scalar(ds.getncattr("code_version"))) if "code_version" in ds.ncattrs() else ""
    allowed: dict[str, str] = {}
    for name in sorted(ds.ncattrs()):
        low = name.lower()
        if name == "code_version" or any(k in low for k in ("calib", "provenance", "process", "version", "history", "source")):
            value = _as_scalar(ds.getncattr(name))
            if isinstance(value, (dict, list, tuple)):
                value = json.dumps(value, sort_keys=True, default=str)
            allowed[name] = str(value)
    qc = {name: name in ds.variables for name in QC_PRESENCE_NAMES}
    binding = {"global_attributes": allowed, "qc_variable_presence": qc}
    digest = sha256_bytes((json.dumps(binding, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8"))
    return code_version, digest, qc


def _masked_numeric_values(var: Any, np: Any) -> tuple[list[float], int]:
    arr = np.ma.asarray(var[:])
    mask = np.ma.getmaskarray(arr)
    data = np.asarray(arr.data, dtype=float).ravel()
    masked = np.asarray(mask, dtype=bool).ravel()
    bad = masked | ~np.isfinite(data)
    return [float(x) for x in data[~bad]], int(np.count_nonzero(bad))


def read_native_time_metadata(path: Path, stream: str) -> dict[str, Any]:
    netCDF4, np = _import_netcdf4()
    code_version = ""
    header_digest = ""
    qc_presence: dict[str, bool] = {}
    with netCDF4.Dataset(path, "r") as ds:
        if stream == "hsrl":
            code_version, header_digest, qc_presence = _allowed_hsrl_header_binding(ds)
        basis = ""
        invalid = 0
        epochs: list[float] = []
        if "time" in ds.variables and getattr(ds.variables["time"], "units", None):
            var = ds.variables["time"]
            vals, invalid = _masked_numeric_values(var, np)
            units = str(getattr(var, "units"))
            calendar = str(getattr(var, "calendar", "standard"))
            try:
                decoded = netCDF4.num2date(vals, units, calendar=calendar, only_use_cftime_datetimes=False, only_use_python_datetimes=True)
            except TypeError:
                decoded = netCDF4.num2date(vals, units, calendar=calendar)
            for x in decoded:
                if getattr(x, "tzinfo", None) is None:
                    x = x.replace(tzinfo=dt.timezone.utc)
                epochs.append(float(x.timestamp()))
            basis = "time units/calendar"
        elif "base_time" in ds.variables and "time_offset" in ds.variables:
            bvals, bad_b = _masked_numeric_values(ds.variables["base_time"], np)
            ovals, bad_o = _masked_numeric_values(ds.variables["time_offset"], np)
            invalid = bad_b + bad_o
            if len(bvals) != 1:
                raise ExtractionError("base_time is not a single finite scalar")
            epochs = [bvals[0] + x for x in ovals]
            basis = "base_time+time_offset epoch seconds"
        else:
            raise ExtractionError("native file lacks supported decoded sample-time coordinates")
    if not epochs:
        raise ExtractionError("native file has no finite decoded sample times")
    if any(not math.isfinite(x) for x in epochs):
        raise ExtractionError("nonfinite decoded epoch escaped filtering")
    return {
        "times_epoch": epochs,
        "invalid_count": invalid,
        "decoded_time_basis": basis,
        "code_version": code_version,
        "hsrl_header_binding_sha256": header_digest,
        "hsrl_qc_presence": qc_presence,
    }


def summarize_times(times: Iterable[float], core_start: float, core_end: float, invalid_count: int = 0) -> dict[str, Any]:
    vals = sorted(float(x) for x in times if math.isfinite(float(x)))
    if not vals:
        raise ExtractionError("no finite decoded sample times available")
    unique = sorted(set(vals))
    duplicate_count = len(vals) - len(unique)
    left_candidates = [x for x in unique if x <= core_start]
    right_candidates = [x for x in unique if x >= core_end]
    if not left_candidates or not right_candidates:
        raise ExtractionError("decoded sample times do not bracket the frozen core; no synthetic bracket may be fabricated")
    left, right = max(left_candidates), min(right_candidates)
    positive = [b - a for a, b in zip(unique, unique[1:]) if b > a]
    if not positive:
        raise ExtractionError("decoded sample-time cadence cannot be established")
    median = statistics.median(positive)
    max_gap = max(positive)
    sample_count = sum(core_start <= x <= core_end for x in vals)
    return {
        "sample_count_core": sample_count,
        "left_bracket_utc": iso_z(left),
        "right_bracket_utc": iso_z(right),
        "left_bracket_delta_s": core_start - left,
        "right_bracket_delta_s": right - core_end,
        "median_positive_cadence_s": median,
        "max_gap_s": max_gap,
        "duplicate_count": duplicate_count,
        "nonfinite_or_masked_count": invalid_count,
        "gap_pass": max_gap <= 2.0 * median + 1e-9,
    }


def _write_csv_json(out_dir: Path, rows: list[dict[str, str]]) -> tuple[Path, Path]:
    csv_path = out_dir / "stageA_actual_time_continuity_v2.csv"
    json_path = out_dir / "stageA_actual_time_continuity_v2.json"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=REQUIRED_COLUMNS, lineterminator="\n")
        w.writeheader(); w.writerows(rows)
    json_path.write_text(json.dumps(rows, indent=2, sort_keys=False, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    return csv_path, json_path


def _base_receipt(binding: dict[str, Any]) -> dict[str, Any]:
    obj = {
        "schema": 1,
        "status": "UNSET",
        "authorization_comment_id": int(binding["authorization_comment_id"]),
        "workflow_path": binding["workflow_path"],
        "workflow_blob_sha": binding["workflow_blob_sha"],
        "main_sha": binding["main_sha"],
        "event": binding["event"],
        "ref": binding["ref"],
        "run_id": str(binding["run_id"]),
        "run_attempt": int(binding["run_attempt"]),
        "request_contract_sha256": REQUEST_SHA256,
        "priority_ledger_sha256": PRIORITY_SHA256,
        "continuity_csv_sha256": None,
        "continuity_json_sha256": None,
        "row_count": 0,
        "hsrl_code_version_set": [],
        "hsrl_allowed_header_binding_sha256s": [],
        "hsrl_qc_presence": {name: False for name in QC_PRESENCE_NAMES},
        "credential_values_logged": False,
        "raw_native_files_persisted": False,
        "raw_time_arrays_persisted": False,
        "science_arrays_read": False,
        "heldout_sws_sasze_radiance_opened": False,
        "stage_b_authorized": False,
        "mystic_science_authorized": False,
        "taylor_or_jerusalem_used": False,
        "production_authorized": False,
        "failure_reason": None,
    }
    validate_receipt(obj, allow_unset=True)
    return obj


def validate_receipt(obj: dict[str, Any], *, allow_unset: bool = False) -> None:
    if set(obj) != RECEIPT_KEYS:
        raise ExtractionError("receipt key universe drift")
    if obj["request_contract_sha256"] != REQUEST_SHA256 or obj["priority_ledger_sha256"] != PRIORITY_SHA256:
        raise ExtractionError("receipt frozen identity drift")
    if obj["workflow_path"] != WORKFLOW_PATH or obj["event"] != "workflow_dispatch" or obj["ref"] != "refs/heads/main" or obj["run_attempt"] != 1:
        raise ExtractionError("receipt dispatch identity drift")
    if not HEX40.fullmatch(str(obj["workflow_blob_sha"])) or not HEX40.fullmatch(str(obj["main_sha"])):
        raise ExtractionError("receipt git identity malformed")
    for key in ("credential_values_logged", "raw_native_files_persisted", "raw_time_arrays_persisted", "science_arrays_read", "heldout_sws_sasze_radiance_opened", "stage_b_authorized", "mystic_science_authorized", "taylor_or_jerusalem_used", "production_authorized"):
        if obj[key] is not False:
            raise ExtractionError("forbidden receipt flag drift: " + key)
    valid_status = {"SUCCESS", "FAIL_CLOSED"} | ({"UNSET"} if allow_unset else set())
    if obj["status"] not in valid_status:
        raise ExtractionError("receipt status drift")
    if obj["status"] == "SUCCESS":
        if obj["row_count"] != 100 or not HEX64.fullmatch(str(obj["continuity_csv_sha256"])) or not HEX64.fullmatch(str(obj["continuity_json_sha256"])):
            raise ExtractionError("success receipt continuity identity drift")
        if obj["failure_reason"] is not None:
            raise ExtractionError("success receipt cannot carry failure reason")
    if obj["status"] == "FAIL_CLOSED" and not isinstance(obj["failure_reason"], str):
        raise ExtractionError("fail-closed receipt requires sanitized failure reason")


def _write_receipt(path: Path, obj: dict[str, Any]) -> None:
    validate_receipt(obj)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def run(priority: Path, request_contract: Path, out_dir: Path, binding_path: Path, *, opener: Callable[..., Any] = urllib.request.urlopen) -> int:
    _require_frozen_file(request_contract, REQUEST_SHA256)
    cases = load_priority(priority)
    binding = json.loads(binding_path.read_text(encoding="utf-8"))
    receipt = _base_receipt(binding)
    receipt_path = out_dir / "stageA_decoded_time_metadata_receipt_v1.json"
    uid = os.environ.get("ARM_USER_ID", "").strip()
    token = os.environ.get("ARM_ACCESS_TOKEN", "").strip()
    if not uid or not token:
        receipt["status"] = "FAIL_CLOSED"; receipt["failure_reason"] = "ARM_CREDENTIAL_ENV_UNAVAILABLE"
        _write_receipt(receipt_path, receipt); return 2
    userpair = uid + ":" + token
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str]] = []
    hsrl_versions: set[str] = set()
    hsrl_header_digests: set[str] = set()
    hsrl_qc_all = {name: True for name in QC_PRESENCE_NAMES}
    temp_root = Path(tempfile.mkdtemp(prefix="arm-stagea-time-only-"))
    try:
        for prow in cases:
            case_id, core_start_dt, core_end_dt = _case_core(prow)
            c0, c1 = core_start_dt.timestamp(), core_end_dt.timestamp()
            for datastream, stream in STREAMS.items():
                names = query_native_names(userpair, datastream, core_start_dt, core_end_dt, opener=opener)
                if not names:
                    raise ExtractionError(f"NO_NATIVE_FILES_{stream.upper()}")
                all_times: list[float] = []
                invalid_count = 0
                sources: list[str] = []
                hashes: list[str] = []
                bases: set[str] = set()
                versions: set[str] = set()
                for name in names:
                    dst = temp_root / name
                    download_native(userpair, name, dst, opener=opener)
                    digest = sha256_file(dst)
                    meta = read_native_time_metadata(dst, stream)
                    all_times.extend(meta["times_epoch"])
                    invalid_count += int(meta["invalid_count"])
                    bases.add(str(meta["decoded_time_basis"]))
                    sources.append(name); hashes.append(digest)
                    if stream == "hsrl":
                        version = str(meta["code_version"])
                        versions.add(version); hsrl_versions.add(version)
                        hd = str(meta["hsrl_header_binding_sha256"])
                        if hd: hsrl_header_digests.add(hd)
                        for q in QC_PRESENCE_NAMES:
                            hsrl_qc_all[q] = hsrl_qc_all[q] and bool(meta["hsrl_qc_presence"].get(q, False))
                    dst.unlink()
                summary = summarize_times(all_times, c0, c1, invalid_count=invalid_count)
                version_text = ";".join(sorted(versions)) if stream == "hsrl" else ""
                continuity_pass = bool(summary["gap_pass"]) and (stream != "hsrl" or versions == {"2.6.7"})
                reasons: list[str] = []
                if not summary["gap_pass"]: reasons.append("MAX_GAP_EXCEEDS_2X_MEDIAN")
                if stream == "hsrl" and versions != {"2.6.7"}: reasons.append("HSRL_CODE_VERSION_NOT_EXACT_2.6.7")
                row = {
                    "case_id": case_id,
                    "stream": stream,
                    "core_start_utc": core_start_dt.isoformat(timespec="microseconds").replace("+00:00", "Z"),
                    "core_end_utc": core_end_dt.isoformat(timespec="microseconds").replace("+00:00", "Z"),
                    "source_files": json.dumps(sources, separators=(",", ":")),
                    "source_sha256s": json.dumps(hashes, separators=(",", ":")),
                    "decoded_time_basis": ";".join(sorted(bases)),
                    "code_version": version_text,
                    "sample_count_core": str(summary["sample_count_core"]),
                    "left_bracket_utc": summary["left_bracket_utc"],
                    "right_bracket_utc": summary["right_bracket_utc"],
                    "left_bracket_delta_s": f"{summary['left_bracket_delta_s']:.6f}",
                    "right_bracket_delta_s": f"{summary['right_bracket_delta_s']:.6f}",
                    "median_positive_cadence_s": f"{summary['median_positive_cadence_s']:.6f}",
                    "max_gap_s": f"{summary['max_gap_s']:.6f}",
                    "duplicate_count": str(summary["duplicate_count"]),
                    "nonfinite_or_masked_count": str(summary["nonfinite_or_masked_count"]),
                    "continuity_pass": "PASS" if continuity_pass else "FAIL",
                    "failure_reason": ";".join(reasons),
                }
                rows.append(row)
                del all_times
        if len(rows) != 100:
            raise ExtractionError("ROW_COUNT_NOT_100")
        csv_path, json_path = _write_csv_json(out_dir, rows)
        receipt.update({
            "status": "SUCCESS",
            "continuity_csv_sha256": sha256_file(csv_path),
            "continuity_json_sha256": sha256_file(json_path),
            "row_count": len(rows),
            "hsrl_code_version_set": sorted(hsrl_versions),
            "hsrl_allowed_header_binding_sha256s": sorted(hsrl_header_digests),
            "hsrl_qc_presence": hsrl_qc_all,
            "failure_reason": None,
        })
        _write_receipt(receipt_path, receipt)
        return 0
    except ExtractionError as exc:
        for p in (out_dir / "stageA_actual_time_continuity_v2.csv", out_dir / "stageA_actual_time_continuity_v2.json"):
            try: p.unlink()
            except FileNotFoundError: pass
        receipt.update({
            "status": "FAIL_CLOSED",
            "continuity_csv_sha256": None,
            "continuity_json_sha256": None,
            "row_count": 0,
            "hsrl_code_version_set": sorted(hsrl_versions),
            "hsrl_allowed_header_binding_sha256s": sorted(hsrl_header_digests),
            "hsrl_qc_presence": hsrl_qc_all,
            "failure_reason": re.sub(r"[^A-Za-z0-9_.:-]+", "_", str(exc))[:240],
        })
        _write_receipt(receipt_path, receipt)
        return 2
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def _reject_explicit_credentials(argv: list[str]) -> None:
    for arg in argv:
        low = arg.lower()
        if low in {"--user", "--user-id", "--token", "--access-token"} or any(low.startswith(x + "=") for x in ("--user", "--user-id", "--token", "--access-token")):
            raise SystemExit("credential values are accepted from inherited environment only")


def main(argv: list[str] | None = None) -> int:
    argsv = list(sys.argv[1:] if argv is None else argv)
    _reject_explicit_credentials(argsv)
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--priority", type=Path, default=here / "ARM_SGP_C1_stageA_priority20.csv")
    ap.add_argument("--request-contract", type=Path, default=here / "request_contract.json")
    ap.add_argument("--binding", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    ns = ap.parse_args(argsv)
    return run(ns.priority, ns.request_contract, ns.output_dir, ns.binding)


if __name__ == "__main__":
    raise SystemExit(main())
