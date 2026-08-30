#!/usr/bin/env python3
"""Build a compact, residual-blind handoff from a local ARM order/archive.

The extractor is intentionally read-only with respect to the source archive.
It inventories and hashes every source file, deduplicates NetCDF schemas,
extracts quality metadata and small representative non-destructive samples,
and runs the frozen SASZE filterband native-time operability gate.

By default SASZE radiance/transmittance values are NOT exported. Their variable
metadata, wavelength coordinates, timing, QC/housekeeping, and file hashes are
retained so the held-out radiance remains unopened until Stage B.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import platform
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Sequence

import netCDF4
import numpy as np

UTC = dt.timezone.utc
ARM_NAME_RE = re.compile(r"^(?P<datastream>.+?)\.(?P<date>\d{8})\.(?P<time>\d{6})\.nc$", re.I)
DATE_TOKEN_RE = re.compile(r"(?<!\d)(20\d{6})(?!\d)")
VOLATILE_GLOBAL_ATTRS = {
    "time_coverage_start",
    "time_coverage_end",
    "history",
    "date_created",
    "date_modified",
    "process_version",
}
QUALITY_ATTR_TOKENS = ("qc", "quality", "dqr", "dqpr", "flag", "valid_", "missing_value", "fillvalue")
QC_VAR_RE = re.compile(r"(^qc_|_qc$|quality|flag|mask|status)", re.I)

FAMILY_PATTERNS: dict[str, tuple[str, ...]] = {
    "SASZE": ("sasze",),
    "HSRL": ("hsrl",),
    "RAMAN": ("rlprof", "raman"),
    "CSPHOT_AOD": ("csphot", "cspotaod", "aodcsp"),
    "MFRSR_AOD": ("aodmfrsr", "mfrsraod", "mfrsr"),
    "NIMFR_AOD": ("aodnimfr", "nimfraod", "nimfr"),
    "ARSCL": ("arscl",),
    "CEIL": ("ceil",),
    "SONDE": ("sonde", "interpsonde"),
    "SURFACE_ALBEDO": ("surfspecalb", "mfr", "qcrad"),
}

FAMILY_VAR_PATTERNS: dict[str, tuple[str, ...]] = {
    "SASZE": (
        "time", "wavelength", "integration", "number_of_scans", "scan", "shutter",
        "tilt", "temperature", "bench", "detector", "pressure", "humidity", "qc", "flag",
    ),
    "HSRL": (
        "time", "height", "range", "extinction", "backscatter", "depolar", "aerosol",
        "optical_depth", "od_aerosol", "cloud", "feature", "uncert", "qc", "flag",
    ),
    "RAMAN": (
        "time", "height", "range", "extinction", "backscatter", "depolar", "aerosol",
        "cloud", "feature", "uncert", "qc", "flag",
    ),
    "CSPHOT_AOD": ("time", "wavelength", "aod", "optical_depth", "angstrom", "qc", "flag"),
    "MFRSR_AOD": ("time", "wavelength", "aod", "optical_depth", "angstrom", "water_vapor", "qc", "flag"),
    "NIMFR_AOD": ("time", "wavelength", "aod", "optical_depth", "angstrom", "water_vapor", "qc", "flag"),
    "ARSCL": ("time", "height", "range", "cloud", "hydrometeor", "reflectivity", "mask", "qc", "flag"),
    "CEIL": ("time", "height", "range", "cloud", "backscatter", "base", "qc", "flag"),
    "SONDE": ("time", "height", "alt", "pres", "temp", "rh", "humidity", "wind", "qc", "flag"),
    "SURFACE_ALBEDO": ("time", "wavelength", "albedo", "irradiance", "flux", "precip", "qc", "flag"),
}

SASZE_PROTECTED_VALUE_RE = re.compile(r"radiance|transmittance", re.I)
SASZE_AUDIT_VARS = (
    "integration_time", "integration_time_vis", "integration_time_nir",
    "number_of_scans", "number_of_scans_vis", "number_of_scans_nir",
    "shutter_state", "collector_x_tilt", "collector_y_tilt",
    "collector_x_tilt_std", "collector_y_tilt_std",
)

INVENTORY_FIELDS = (
    "relative_path", "filename", "datastream", "file_date_utc", "size_bytes", "sha256",
    "is_netcdf", "netcdf_readable", "native_time_start_utc", "native_time_end_utc",
    "native_sample_count", "time_decode_method", "schema_signature", "error",
)

SASZE_GATE_FIELDS = (
    "priority", "case_id", "event", "stream", "source_files", "core_start_utc", "core_end_utc",
    "decoded_sample_count_core", "first_sample_utc", "last_sample_utc",
    "nearest_sample_to_minus8_s", "nearest_sample_to_minus7_s", "nearest_sample_to_minus6_s",
    "median_positive_cadence_s", "max_internal_gap_s", "samples_within_5s_minus8",
    "samples_within_5s_minus7", "samples_within_5s_minus6", "distinct_integration_modes",
    "health_flag_names_present", "read_errors", "disposition",
)


def utc_now_iso() -> str:
    return dt.datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def iso_utc(value: dt.datetime | None) -> str:
    if value is None:
        return ""
    return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def parse_utc(text: str) -> dt.datetime:
    text = text.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    value = dt.datetime.fromisoformat(text)
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def json_safe(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return [json_safe(x) for x in value.tolist()]
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, (list, tuple)):
        return [json_safe(x) for x in value]
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def canonical_json(value: Any) -> bytes:
    return json.dumps(json_safe(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def derive_datastream(path: Path) -> tuple[str, str]:
    match = ARM_NAME_RE.match(path.name)
    if match:
        return match.group("datastream"), match.group("date")
    date_match = DATE_TOKEN_RE.search(path.name)
    date = date_match.group(1) if date_match else ""
    if date_match:
        prefix = path.name[: max(0, date_match.start() - 1)].rstrip(".")
        return prefix or path.stem, date
    return path.stem, date


def family_for_datastream(datastream: str) -> str:
    lowered = datastream.lower().replace("_", "")
    for family, patterns in FAMILY_PATTERNS.items():
        if any(pattern.replace("_", "") in lowered for pattern in patterns):
            return family
    return "OTHER"


def attrs_dict(obj: Any) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name in sorted(getattr(obj, "ncattrs", lambda: [])()):
        try:
            out[name] = json_safe(obj.getncattr(name))
        except Exception as exc:  # pragma: no cover - defensive against malformed attrs
            out[name] = f"<ATTR_READ_ERROR:{type(exc).__name__}:{exc}>"
    return out


def variable_schema(var: netCDF4.Variable) -> dict[str, Any]:
    return {
        "dtype": str(var.dtype),
        "dimensions": list(var.dimensions),
        "shape": list(var.shape),
        "attrs": attrs_dict(var),
    }


def decoded_datetime(d: Any) -> dt.datetime:
    return dt.datetime(
        int(d.year), int(d.month), int(d.day), int(d.hour), int(d.minute), int(d.second),
        int(getattr(d, "microsecond", 0)), tzinfo=UTC,
    )


def decode_native_times(ds: netCDF4.Dataset) -> tuple[np.ndarray, str]:
    """Return epoch seconds from native sample coordinates, never global coverage attrs."""
    if "time" in ds.variables:
        var = ds.variables["time"]
        units = getattr(var, "units", None)
        if units:
            raw = np.ma.asarray(var[:])
            vals = raw.compressed() if np.ma.isMaskedArray(raw) else np.asarray(raw).ravel()
            vals = np.asarray(vals, dtype=float)
            vals = vals[np.isfinite(vals)]
            if vals.size:
                decoded = netCDF4.num2date(vals, units=units, calendar=getattr(var, "calendar", "standard"))
                return np.asarray([decoded_datetime(x).timestamp() for x in decoded], dtype=float), "time_units"
    if "base_time" in ds.variables and "time_offset" in ds.variables:
        base = np.ma.asarray(ds.variables["base_time"][:]).squeeze()
        offsets = np.ma.asarray(ds.variables["time_offset"][:])
        if np.ma.isMaskedArray(base) and bool(np.ma.getmaskarray(base)):
            return np.array([], dtype=float), "base_time_masked"
        vals = offsets.compressed() if np.ma.isMaskedArray(offsets) else np.asarray(offsets).ravel()
        vals = np.asarray(vals, dtype=float)
        vals = vals[np.isfinite(vals)]
        if vals.size:
            return float(base) + vals, "base_time_plus_offset"
    return np.array([], dtype=float), "none"


def summarize_netcdf(path: Path) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    with netCDF4.Dataset(path, "r") as ds:
        dims = {
            name: {"size": len(dim), "unlimited": bool(dim.isunlimited())}
            for name, dim in sorted(ds.dimensions.items())
        }
        globals_all = attrs_dict(ds)
        globals_nonvolatile = {k: v for k, v in globals_all.items() if k not in VOLATILE_GLOBAL_ATTRS}
        variables = {name: variable_schema(var) for name, var in sorted(ds.variables.items())}
        header = {
            "dimensions": dims,
            "global_attr_names": sorted(globals_all),
            "global_attrs_nonvolatile": globals_nonvolatile,
            "variables": variables,
        }
        schema_signature = sha256_bytes(canonical_json(header))
        times, method = decode_native_times(ds)
        finite = times[np.isfinite(times)]
        time_summary = {
            "native_time_start_utc": iso_utc(dt.datetime.fromtimestamp(float(np.min(finite)), UTC)) if finite.size else "",
            "native_time_end_utc": iso_utc(dt.datetime.fromtimestamp(float(np.max(finite)), UTC)) if finite.size else "",
            "native_sample_count": int(finite.size),
            "time_decode_method": method,
            "schema_signature": schema_signature,
        }
        quality_records: list[dict[str, Any]] = []
        global_quality = {
            k: v for k, v in globals_all.items()
            if any(token in k.lower() for token in QUALITY_ATTR_TOKENS)
        }
        if global_quality:
            quality_records.append({"scope": "global", "name": "<global>", "attrs": global_quality})
        for name, var in sorted(ds.variables.items()):
            var_attrs = attrs_dict(var)
            quality_attrs = {
                k: v for k, v in var_attrs.items()
                if any(token in k.lower() for token in QUALITY_ATTR_TOKENS)
                or k in {"flag_values", "flag_meanings", "flag_masks", "bit_1_description", "bit_2_description"}
            }
            if QC_VAR_RE.search(name) or quality_attrs:
                quality_records.append({
                    "scope": "variable",
                    "name": name,
                    "dtype": str(var.dtype),
                    "dimensions": list(var.dimensions),
                    "attrs": var_attrs,
                })
        return time_summary, header, quality_records


def spaced_indices(size: int, limit: int = 5) -> list[int]:
    if size <= 0:
        return []
    if size <= limit:
        return list(range(size))
    return sorted(set(int(round(x)) for x in np.linspace(0, size - 1, limit)))


def sample_variable(var: netCDF4.Variable, max_non_time: int = 5) -> dict[str, Any]:
    dims = list(var.dimensions)
    selectors: list[list[int]] = []
    for axis, dim in enumerate(dims):
        size = var.shape[axis]
        if dim.lower() == "time":
            selectors.append(spaced_indices(size, 3))
        else:
            selectors.append(spaced_indices(size, max_non_time))
    if not dims:
        raw = np.ma.asarray(var[...])
        return {"indices": [], "values": json_safe(raw.filled(np.nan) if np.ma.isMaskedArray(raw) else raw)}
    points: list[dict[str, Any]] = []
    # Cartesian product without importing itertools product for a tiny, bounded selection.
    index_tuples: list[tuple[int, ...]] = [()]
    for axis_indices in selectors:
        index_tuples = [base + (idx,) for base in index_tuples for idx in axis_indices]
    # Bound pathological dimensions deterministically.
    index_tuples = index_tuples[:375]
    for index_tuple in index_tuples:
        try:
            raw = var[index_tuple]
            masked = bool(np.ma.is_masked(raw))
            value = None if masked else json_safe(np.asarray(raw).item() if np.asarray(raw).shape == () else raw)
            points.append({"index": list(index_tuple), "value": value, "masked": masked})
        except Exception as exc:
            points.append({"index": list(index_tuple), "error": f"{type(exc).__name__}:{exc}"})
    return {"indices_by_dimension": {dim: sel for dim, sel in zip(dims, selectors)}, "points": points}


def representative_extract(path: Path, family: str, include_sasze_radiance: bool) -> dict[str, Any]:
    with netCDF4.Dataset(path, "r") as ds:
        chosen: dict[str, Any] = {}
        patterns = FAMILY_VAR_PATTERNS.get(family, ("time", "qc", "flag"))
        for name, var in sorted(ds.variables.items()):
            lname = name.lower()
            if family == "SASZE" and SASZE_PROTECTED_VALUE_RE.search(lname) and not include_sasze_radiance:
                continue
            if not any(pattern in lname for pattern in patterns):
                continue
            chosen[name] = {
                "dtype": str(var.dtype),
                "dimensions": list(var.dimensions),
                "units": json_safe(getattr(var, "units", "")),
                "long_name": json_safe(getattr(var, "long_name", "")),
                "attrs": attrs_dict(var),
                "sample": sample_variable(var),
            }
        times, method = decode_native_times(ds)
        finite = times[np.isfinite(times)]
        return {
            "family": family,
            "source_file": path.name,
            "native_time_decode_method": method,
            "native_time_start_utc": iso_utc(dt.datetime.fromtimestamp(float(np.min(finite)), UTC)) if finite.size else "",
            "native_time_end_utc": iso_utc(dt.datetime.fromtimestamp(float(np.max(finite)), UTC)) if finite.size else "",
            "sasze_radiance_values_included": bool(include_sasze_radiance and family == "SASZE"),
            "variables": chosen,
        }


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fields: Sequence[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(fields), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(json_safe(row), sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n")


def load_priority_cases(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    required = {"priority", "case_id", "event", "source_date_utc", "t_minus8_utc", "t_minus7_utc", "t_minus6_utc"}
    missing = required.difference(rows[0].keys() if rows else [])
    if missing:
        raise ValueError(f"priority CSV missing columns: {sorted(missing)}")
    return rows


def sasze_gate_for_case(archive_root: Path, case: dict[str, str]) -> dict[str, Any]:
    stream = "sgpsaszefilterbandsC1.a1"
    pattern = f"{stream}.{case['source_date_utc']}.*.nc"
    files = sorted(p for p in archive_root.rglob(pattern) if p.is_file())
    t8 = parse_utc(case["t_minus8_utc"]).timestamp()
    t7 = parse_utc(case["t_minus7_utc"]).timestamp()
    t6 = parse_utc(case["t_minus6_utc"]).timestamp()
    core_start, core_end = sorted((t8, t6))
    all_times: list[np.ndarray] = []
    errors: list[str] = []
    modes: set[str] = set()
    health_flags: set[str] = set()
    readable = 0

    for path in files:
        try:
            with netCDF4.Dataset(path, "r") as ds:
                times, _ = decode_native_times(ds)
                readable += 1
                if times.size:
                    all_times.append(times[np.isfinite(times)])
                for name, var in ds.variables.items():
                    lname = name.lower()
                    if name in SASZE_AUDIT_VARS or "integration_time" in lname or "number_of_scans" in lname:
                        try:
                            raw = np.ma.asarray(var[:])
                            values = raw.compressed() if np.ma.isMaskedArray(raw) else np.asarray(raw).ravel()
                            for value in values[:100000]:
                                if isinstance(value, np.generic):
                                    value = value.item()
                                if isinstance(value, (int, float, np.integer, np.floating)) and not np.isfinite(float(value)):
                                    continue
                                modes.add(f"{name}={value}")
                        except Exception as exc:
                            errors.append(f"{path.name}:{name}:{type(exc).__name__}:{exc}")
                    if QC_VAR_RE.search(name) or "satur" in lname or "health" in lname or "high_sza" in lname:
                        health_flags.add(name)
        except Exception as exc:
            errors.append(f"{path.name}:{type(exc).__name__}:{exc}")

    times = np.unique(np.concatenate(all_times)) if all_times else np.array([], dtype=float)
    core = times[(times >= core_start) & (times <= core_end)]
    positive_gaps = np.diff(core)
    positive_gaps = positive_gaps[positive_gaps > 0]
    cadence = float(np.median(positive_gaps)) if positive_gaps.size else None
    max_gap = float(np.max(positive_gaps)) if positive_gaps.size else None
    brackets = bool(core.size and core[0] <= core_start and core[-1] >= core_end)
    # A nearest native sample on each side is sufficient to bracket the exact crossing;
    # because core includes only [start,end], exact bracketing generally requires samples
    # at or very near both endpoints. Use the full time vector for strict side checks.
    if times.size:
        brackets = bool(np.any(times <= core_start) and np.any(times >= core_end))
    gap_ok = bool(cadence is not None and max_gap is not None and max_gap <= 2.0 * cadence + 1e-9)

    if not files:
        disposition = "SOURCE_FILE_MISSING"
    elif readable == 0:
        disposition = "UNREADABLE"
    elif core.size == 0:
        disposition = "TWILIGHT_SAMPLES_ABSENT"
    elif brackets and gap_ok:
        disposition = "TWILIGHT_CONTIGUOUS"
    else:
        disposition = "TWILIGHT_DISCONTINUOUS"

    def nearest(target: float) -> str:
        return "" if not times.size else f"{float(np.min(np.abs(times - target))):.6f}"

    def within(target: float) -> int:
        return 0 if not times.size else int(np.count_nonzero(np.abs(times - target) <= 5.0))

    return {
        "priority": case["priority"], "case_id": case["case_id"], "event": case["event"], "stream": stream,
        "source_files": ";".join(str(p.relative_to(archive_root)) for p in files),
        "core_start_utc": iso_utc(dt.datetime.fromtimestamp(core_start, UTC)),
        "core_end_utc": iso_utc(dt.datetime.fromtimestamp(core_end, UTC)),
        "decoded_sample_count_core": int(core.size),
        "first_sample_utc": iso_utc(dt.datetime.fromtimestamp(float(times.min()), UTC)) if times.size else "",
        "last_sample_utc": iso_utc(dt.datetime.fromtimestamp(float(times.max()), UTC)) if times.size else "",
        "nearest_sample_to_minus8_s": nearest(t8), "nearest_sample_to_minus7_s": nearest(t7),
        "nearest_sample_to_minus6_s": nearest(t6),
        "median_positive_cadence_s": "" if cadence is None else f"{cadence:.6f}",
        "max_internal_gap_s": "" if max_gap is None else f"{max_gap:.6f}",
        "samples_within_5s_minus8": within(t8), "samples_within_5s_minus7": within(t7),
        "samples_within_5s_minus6": within(t6),
        "distinct_integration_modes": ";".join(sorted(modes)),
        "health_flag_names_present": ";".join(sorted(health_flags)),
        "read_errors": " | ".join(errors), "disposition": disposition,
    }


def choose_representatives(records: list[dict[str, Any]], archive_root: Path) -> list[tuple[Path, str]]:
    by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        if not record.get("netcdf_readable"):
            continue
        family = family_for_datastream(str(record["datastream"]))
        if family != "OTHER":
            by_family[family].append(record)
    chosen: list[tuple[Path, str]] = []
    for family, group in sorted(by_family.items()):
        group.sort(key=lambda r: (r.get("native_time_start_utc", ""), r["relative_path"]))
        indices = spaced_indices(len(group), 3)
        for idx in indices:
            chosen.append((archive_root / group[idx]["relative_path"], family))
    return chosen


def output_manifest(output_root: Path, archive_root: Path, args: argparse.Namespace) -> dict[str, Any]:
    files = []
    for path in sorted(p for p in output_root.rglob("*") if p.is_file() and p.name != "handoff_manifest.json"):
        files.append({
            "relative_path": str(path.relative_to(output_root)).replace(os.sep, "/"),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        })
    return {
        "schema": "arm-sgp-compact-handoff-v1",
        "generated_utc": utc_now_iso(),
        "archive_root": str(archive_root.resolve()),
        "archive_modified": False,
        "date_start": args.start,
        "date_end": args.end,
        "sasze_radiance_values_exported": bool(args.include_sasze_radiance_sample),
        "python": sys.version,
        "platform": platform.platform(),
        "netCDF4_version": netCDF4.__version__,
        "numpy_version": np.__version__,
        "files": files,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-root", type=Path, required=True, help="Root of the preserved ARM order/archive")
    parser.add_argument("--output", type=Path, required=True, help="Fresh compact-handoff output directory")
    parser.add_argument("--start", default="2023-12-14")
    parser.add_argument("--end", default="2024-06-02")
    parser.add_argument("--priority-csv", type=Path, default=Path(__file__).with_name("priority20_sasze_gate.csv"))
    parser.add_argument("--include-sasze-radiance-sample", action="store_true", help="Stage-B only; default keeps held-out SASZE radiance values unopened")
    args = parser.parse_args(argv)

    archive_root = args.archive_root.resolve()
    output_root = args.output.resolve()
    if not archive_root.exists() or not archive_root.is_dir():
        parser.error(f"archive root does not exist or is not a directory: {archive_root}")
    if output_root == archive_root or archive_root in output_root.parents:
        parser.error("output must be outside the source archive; source bytes are read-only")
    output_root.mkdir(parents=True, exist_ok=True)

    start_date = dt.date.fromisoformat(args.start)
    end_date = dt.date.fromisoformat(args.end)
    if end_date < start_date:
        parser.error("--end precedes --start")

    inventory: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    headers: dict[str, dict[str, Any]] = {}
    quality_seen: dict[str, dict[str, Any]] = {}

    source_files = sorted(p for p in archive_root.rglob("*") if p.is_file())
    for index, path in enumerate(source_files, 1):
        rel = str(path.relative_to(archive_root)).replace(os.sep, "/")
        datastream, file_date = derive_datastream(path)
        record: dict[str, Any] = {
            "relative_path": rel, "filename": path.name, "datastream": datastream, "file_date_utc": file_date,
            "size_bytes": path.stat().st_size, "sha256": "", "is_netcdf": path.suffix.lower() == ".nc",
            "netcdf_readable": False, "native_time_start_utc": "", "native_time_end_utc": "",
            "native_sample_count": 0, "time_decode_method": "", "schema_signature": "", "error": "",
        }
        try:
            record["sha256"] = sha256_file(path)
        except Exception as exc:
            record["error"] = f"HASH:{type(exc).__name__}:{exc}"
            issues.append({"relative_path": rel, "kind": "HASH_ERROR", "detail": record["error"]})
            inventory.append(record)
            continue
        if record["is_netcdf"]:
            try:
                summary, header, quality_records = summarize_netcdf(path)
                record.update(summary)
                record["netcdf_readable"] = True
                signature = str(summary["schema_signature"])
                if signature not in headers:
                    headers[signature] = {
                        "schema_signature": signature, "datastream": datastream, "example_file": rel,
                        "header": header,
                    }
                for qrec in quality_records:
                    qkey = sha256_bytes(canonical_json({"datastream": datastream, **qrec}))
                    quality_seen.setdefault(qkey, {"datastream": datastream, "example_file": rel, **qrec})
            except Exception as exc:
                record["error"] = f"NETCDF:{type(exc).__name__}:{exc}"
                issues.append({"relative_path": rel, "kind": "NETCDF_UNREADABLE", "detail": record["error"]})
        inventory.append(record)
        if index % 250 == 0:
            print(f"scanned {index}/{len(source_files)} files", flush=True)

    write_csv(output_root / "archive_inventory.csv", inventory, INVENTORY_FIELDS)
    write_jsonl(output_root / "netcdf_headers.jsonl", headers[k] for k in sorted(headers))
    write_jsonl(output_root / "quality_metadata.jsonl", quality_seen[k] for k in sorted(quality_seen))
    write_csv(output_root / "issues.csv", issues, ("relative_path", "kind", "detail"))

    # Datastream/day availability from source filenames and readable native time coverage.
    day_map: dict[tuple[str, str], dict[str, Any]] = {}
    for rec in inventory:
        date = rec.get("file_date_utc", "")
        if not date:
            continue
        key = (str(rec["datastream"]), str(date))
        row = day_map.setdefault(key, {
            "datastream": key[0], "date_utc": key[1], "file_count": 0, "total_bytes": 0,
            "readable_netcdf_count": 0, "unreadable_netcdf_count": 0,
            "native_time_start_min_utc": "", "native_time_end_max_utc": "",
        })
        row["file_count"] += 1
        row["total_bytes"] += int(rec["size_bytes"])
        if rec["is_netcdf"]:
            if rec["netcdf_readable"]:
                row["readable_netcdf_count"] += 1
            else:
                row["unreadable_netcdf_count"] += 1
        start = str(rec.get("native_time_start_utc", ""))
        end = str(rec.get("native_time_end_utc", ""))
        if start and (not row["native_time_start_min_utc"] or start < row["native_time_start_min_utc"]):
            row["native_time_start_min_utc"] = start
        if end and (not row["native_time_end_max_utc"] or end > row["native_time_end_max_utc"]):
            row["native_time_end_max_utc"] = end
    daily_fields = (
        "datastream", "date_utc", "file_count", "total_bytes", "readable_netcdf_count",
        "unreadable_netcdf_count", "native_time_start_min_utc", "native_time_end_max_utc",
    )
    write_csv(output_root / "daily_availability.csv", (day_map[k] for k in sorted(day_map)), daily_fields)

    # Family/date matrix, explicitly retaining absent days across the requested science interval.
    family_day_counts: dict[tuple[str, str], int] = defaultdict(int)
    for rec in inventory:
        family = family_for_datastream(str(rec["datastream"]))
        if family == "OTHER" or not rec.get("file_date_utc"):
            continue
        family_day_counts[(family, str(rec["file_date_utc"]))] += 1
    matrix_rows = []
    current = start_date
    while current <= end_date:
        day = current.strftime("%Y%m%d")
        for family in sorted(FAMILY_PATTERNS):
            count = family_day_counts.get((family, day), 0)
            matrix_rows.append({"family": family, "date_utc": day, "file_count": count, "available": int(count > 0)})
        current += dt.timedelta(days=1)
    write_csv(output_root / "family_daily_availability.csv", matrix_rows, ("family", "date_utc", "file_count", "available"))

    # Small deterministic representative extracts. SASZE radiance remains protected by default.
    rep_rows = []
    for path, family in choose_representatives(inventory, archive_root):
        try:
            rec = representative_extract(path, family, args.include_sasze_radiance_sample)
            rec["relative_path"] = str(path.relative_to(archive_root)).replace(os.sep, "/")
            rec["source_sha256"] = next((r["sha256"] for r in inventory if r["relative_path"] == rec["relative_path"]), "")
            rep_rows.append(rec)
        except Exception as exc:
            issues.append({"relative_path": str(path.relative_to(archive_root)), "kind": "REPRESENTATIVE_EXTRACT_ERROR", "detail": f"{type(exc).__name__}:{exc}"})
    write_jsonl(output_root / "representative_extracts.jsonl", rep_rows)
    write_csv(output_root / "issues.csv", issues, ("relative_path", "kind", "detail"))

    # Frozen residual-blind SASZE native-time gate.
    priority_cases = load_priority_cases(args.priority_csv)
    gate_rows = [sasze_gate_for_case(archive_root, case) for case in priority_cases]
    write_csv(output_root / "stageA_sasze_twilight_operability_2024.csv", gate_rows, SASZE_GATE_FIELDS)

    # Human-readable compact summary.
    family_summary: dict[str, dict[str, int]] = defaultdict(lambda: {"files": 0, "readable_netcdf": 0})
    for rec in inventory:
        family = family_for_datastream(str(rec["datastream"]))
        if family == "OTHER":
            continue
        family_summary[family]["files"] += 1
        family_summary[family]["readable_netcdf"] += int(bool(rec["netcdf_readable"]))
    gate_counts: dict[str, int] = defaultdict(int)
    for row in gate_rows:
        gate_counts[str(row["disposition"])] += 1
    summary = {
        "schema": "arm-sgp-compact-handoff-summary-v1",
        "generated_utc": utc_now_iso(),
        "source_file_count": len(source_files),
        "source_total_bytes": sum(int(r["size_bytes"]) for r in inventory),
        "netcdf_unreadable_count": sum(1 for r in inventory if r["is_netcdf"] and not r["netcdf_readable"]),
        "family_summary": dict(sorted(family_summary.items())),
        "sasze_gate_counts": dict(sorted(gate_counts.items())),
        "sasze_gate_complete_readable": all(r["disposition"] not in {"SOURCE_FILE_MISSING", "UNREADABLE"} for r in gate_rows),
        "sasze_primary_survivor_case_ids": [r["case_id"] for r in gate_rows if r["disposition"] == "TWILIGHT_CONTIGUOUS"],
        "sasze_all20_readably_absent_or_discontinuous": bool(gate_rows) and all(
            r["disposition"] in {"TWILIGHT_DISCONTINUOUS", "TWILIGHT_SAMPLES_ABSENT"} for r in gate_rows
        ),
        "heldout_sasze_radiance_opened": bool(args.include_sasze_radiance_sample),
    }
    (output_root / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    manifest = output_manifest(output_root, archive_root, args)
    (output_root / "handoff_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    print(json.dumps(summary, indent=2, sort_keys=True))
    print(f"compact handoff written to: {output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
