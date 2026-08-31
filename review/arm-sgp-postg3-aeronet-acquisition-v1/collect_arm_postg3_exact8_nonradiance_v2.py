#!/usr/bin/env python3
"""Result-blind ARM SGP post-G3 exact-eight collector.

This collector is deliberately split at the SASZE holdout firewall:
- Non-SASZE ARM science/QC source files needed for G2/G4-G9 are copied byte-for-byte.
- SASZE VIS and filterbands source files are NEVER copied into the package.
- SASZE source files are opened only to read time coordinates and a strict allow-list of
  housekeeping/QC/calibration variables. Any variable with a protected photometric token
  is never read.

No SASZE radiance, irradiance, flux, luminance, brightness, detector signal/count, or
spectral science value is read or serialized by this program.
"""
from __future__ import annotations

import argparse
import csv
import fnmatch
import hashlib
import json
import math
import os
import shutil
import sys
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable


def _preload_vendor_path() -> None:
    raw = None
    for i, arg in enumerate(sys.argv[:-1]):
        if arg == "--python-packages":
            raw = sys.argv[i + 1]
            break
    candidates = []
    if raw:
        candidates.append(Path(raw))
    here = Path(__file__).resolve().parent
    candidates.extend([here / "python_packages", here.parent / "python_packages"])
    env = os.environ.get("ARM_PYTHON_PACKAGES")
    if env:
        candidates.insert(0, Path(env))
    for p in candidates:
        if p.is_dir():
            sys.path.insert(0, str(p.resolve()))
            break


_preload_vendor_path()
try:
    import numpy as np
    from netCDF4 import Dataset, num2date
except Exception as exc:
    raise SystemExit(
        "netCDF4/numpy are required. Run beside the existing ARM processor's python_packages "
        "directory or pass --python-packages PATH. Import failure: " + repr(exc)
    )

SCHEMA = 2
PACKAGE_PREFIX = "ARM_SGP_POSTG3_EXACT8_NATIVE_NONRADIANCE_V2"
BUFFER = timedelta(minutes=10)


@dataclass(frozen=True)
class Case:
    priority_order: int
    case_id: str
    utc_date: str
    t6: str
    t7: str
    t8: str


CASES = [
    Case(89, "2024-01-27_dusk", "20240128", "2024-01-28T00:17:28.689966Z", "2024-01-28T00:22:43.466171Z", "2024-01-28T00:27:56.939546Z"),
    Case(99, "2024-02-01_dusk", "20240202", "2024-02-02T00:22:33.308189Z", "2024-02-02T00:27:45.184510Z", "2024-02-02T00:32:55.905415Z"),
    Case(161, "2024-03-03_dusk", "20240304", "2024-03-04T00:52:46.844963Z", "2024-03-04T00:57:46.442131Z", "2024-03-04T01:02:45.857405Z"),
    Case(163, "2024-03-04_dusk", "20240305", "2024-03-05T00:53:41.973209Z", "2024-03-05T00:58:41.445655Z", "2024-03-05T01:03:40.768835Z"),
    Case(167, "2024-03-06_dusk", "20240307", "2024-03-07T00:55:31.759900Z", "2024-03-07T01:00:31.046107Z", "2024-03-07T01:05:30.248668Z"),
    Case(209, "2024-03-27_dusk", "20240328", "2024-03-28T01:14:18.800820Z", "2024-03-28T01:19:21.518147Z", "2024-03-28T01:24:24.898437Z"),
    Case(211, "2024-03-28_dusk", "20240329", "2024-03-29T01:15:12.205519Z", "2024-03-29T01:20:15.338576Z", "2024-03-29T01:25:19.174063Z"),
    Case(339, "2024-05-31_dusk", "20240601", "2024-06-01T02:12:47.082575Z", "2024-06-01T02:18:47.091164Z", "2024-06-01T02:24:51.346239Z"),
]

# No source variable containing one of these tokens may ever be read from SASZE.
PROTECTED_SASZE_TOKENS = (
    "radiance", "irradiance", "flux", "luminance", "brightness",
    "signal", "counts", "count_rate", "dn_", "raw_counts",
)

SASZE_EXACT_ALLOW = {
    "time", "time_bounds", "base_time", "time_offset", "wavelength",
    "integration_time_vis", "number_of_scans_vis",
    "integration_time_nir", "number_of_scans_nir",
    "integration_time", "number_of_scans",
    "collector_x_tilt", "collector_y_tilt",
    "collector_x_tilt_std", "collector_y_tilt_std",
    "bench_temperature_vis", "ad_temperature_vis",
    "bench_temperature_nir", "ad_temperature_nir",
    "bench_temperature", "ad_temperature",
    "solar_azimuth", "solar_zenith",
}
SASZE_ALLOW_TOKENS = (
    "status", "flag", "quality", "health", "tilt", "temperature",
    "integration_time", "number_of_scans", "exposure", "calibration",
    "responsivity", "serial_number",
)

RAW_COMPONENTS = [
    ("G2", "ARSCL_KAZR", ("sgparsclkazr1kolliasC1.c1*{d}*.nc", "sgparsclkazr1kolliasC1.c0*{d}*.nc", "sgparsclkazr1kolliasC1.c1*{d}*.cdf", "sgparsclkazr1kolliasC1.c0*{d}*.cdf"), (0,)),
    ("G2", "CEIL", ("sgpceilC1.b1*{d}*.nc", "sgpceilC1.b1*{d}*.cdf"), (0,)),
    ("G2", "MPL_FEATURE_SUPPORT", ("sgpmpl*{d}*.nc", "sgpmpl*{d}*.cdf", "sgp*feature*{d}*.nc", "sgp*feature*{d}*.cdf"), (0,)),
    ("G4", "HSRL", ("sgphsrlC1.a1*{d}*.nc", "sgphsrlC1.a1*{d}*.cdf"), (0,)),
    ("G5", "RLPROFBE_RAMAN", ("sgprlprofbeC1.c1*{d}*.nc", "sgprlprofbeC1.c1*{d}*.cdf"), (0,)),
    ("G6", "MFRSR_AOD", ("sgpmfrsr7nchaod1michC1.c1*{d}*.nc", "sgpmfrsr7nchaod1michC1.c1*{d}*.cdf"), (-1, 0)),
    ("G6", "CSPHOT", ("sgpcsphotaodfiltqav3C1.a1*{d}*.nc", "sgpcsphotaodfiltqav3C1.a1*{d}*.cdf"), (-1, 0)),
    ("G7", "SONDE", ("sgpsondewnpnC1.b1*{d}*.nc", "sgpsondewnpnC1.b1*{d}*.cdf"), (-1, 0, 1)),
    ("G8", "MFR_UP", ("sgpmfr10mC1.b1*{d}*.nc", "sgpmfr10mC1.b1*{d}*.cdf"), (-1, 0)),
    ("G8", "MFRSR_DOWN", ("sgpmfrsrC1.b1*{d}*.nc", "sgpmfrsrC1.b1*{d}*.cdf"), (-1, 0)),
    ("G8", "QCRAD_C2", ("sgpqcradbrs1longC1.c2*{d}*.nc", "sgpqcradbrs1longC1.c2*{d}*.cdf", "sgpqcrad*C1.c2*{d}*.nc", "sgpqcrad*C1.c2*{d}*.cdf"), (-1, 0)),
    ("G9", "GECOMI_OZONE", ("gecomiX1.a1*{d}*.nc", "gecomiX1.a1*{d}*.cdf"), (-1, 0)),
]


def parse_utc(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)


def date_shift(yyyymmdd: str, days: int) -> str:
    dt = datetime.strptime(yyyymmdd, "%Y%m%d") + timedelta(days=days)
    return dt.strftime("%Y%m%d")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def scalar(v: Any) -> Any:
    if isinstance(v, bytes):
        return v.decode("utf-8", errors="replace")
    if isinstance(v, np.generic):
        return scalar(v.item())
    if np.ma.isMaskedArray(v):
        return scalar(np.asarray(v.filled(np.nan)))
    if isinstance(v, np.ndarray):
        return [scalar(x) for x in v.tolist()]
    if isinstance(v, (list, tuple)):
        return [scalar(x) for x in v]
    if isinstance(v, float) and not math.isfinite(v):
        return None
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    return str(v)


def attrs(obj: Any) -> dict[str, Any]:
    return {name: scalar(obj.getncattr(name)) for name in obj.ncattrs()}


def is_protected_sasze_var(name: str) -> bool:
    low = name.lower()
    return any(tok in low for tok in PROTECTED_SASZE_TOKENS)


def is_allowed_sasze_var(name: str) -> bool:
    low = name.lower()
    if is_protected_sasze_var(name):
        return False
    if low in SASZE_EXACT_ALLOW:
        return True
    if low.startswith("qc_") or low.endswith("_qc"):
        return True
    return any(tok in low for tok in SASZE_ALLOW_TOKENS)


def decode_time(ds: Dataset) -> list[datetime]:
    if "time" not in ds.variables:
        raise ValueError("missing time variable")
    tv = ds.variables["time"]
    units = getattr(tv, "units", None)
    if not units:
        raise ValueError("time variable has no units")
    vals = np.ma.asarray(tv[:])
    arr = vals.filled(np.nan).astype(float).ravel() if np.ma.isMaskedArray(vals) else np.asarray(vals, dtype=float).ravel()
    cal = getattr(tv, "calendar", "standard")
    out: list[datetime] = []
    for x in arr:
        if not math.isfinite(float(x)):
            out.append(datetime.min.replace(tzinfo=timezone.utc))
            continue
        d = num2date(float(x), units, calendar=cal, only_use_cftime_datetimes=False, only_use_python_datetimes=True)
        if getattr(d, "tzinfo", None) is None:
            d = d.replace(tzinfo=timezone.utc)
        out.append(d.astimezone(timezone.utc))
    return out


def iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def safe_source_metadata(ds: Dataset) -> dict[str, Any]:
    variables = {}
    protected_names = []
    for name, var in ds.variables.items():
        if is_protected_sasze_var(name):
            protected_names.append(name)
            continue
        if not is_allowed_sasze_var(name):
            continue
        variables[name] = {
            "dtype": str(var.dtype),
            "dimensions": list(var.dimensions),
            "shape": list(var.shape),
            "attributes": attrs(var),
        }
    protected_name_hash = hashlib.sha256("\n".join(sorted(protected_names)).encode("utf-8")).hexdigest()
    return {
        "global_attributes": attrs(ds),
        "allowed_variable_metadata": variables,
        "excluded_protected_variable_count": len(protected_names),
        "excluded_protected_variable_names_sha256": protected_name_hash,
        "protected_variable_values_read": False,
    }


def _window_indices(times: list[datetime], start: datetime, end: datetime) -> list[int]:
    invalid = datetime.min.replace(tzinfo=timezone.utc)
    return [i for i, t in enumerate(times) if t != invalid and start <= t <= end]


def read_allowed_variable(var: Any, time_indices: list[int]) -> Any:
    dims = list(var.dimensions)
    if "time" not in dims:
        size = int(np.prod(var.shape)) if var.shape else 1
        if size > 4096:
            return {"data_omitted": True, "reason": "non_time_variable_too_large", "element_count": size}
        return scalar(var[...])
    axis = dims.index("time")
    if not time_indices:
        return []
    lo, hi = min(time_indices), max(time_indices)
    sl = [slice(None)] * len(dims)
    sl[axis] = slice(lo, hi + 1)
    block = np.ma.asarray(var[tuple(sl)])
    rel = np.asarray([i - lo for i in time_indices], dtype=int)
    return scalar(np.take(block, rel, axis=axis))


def extract_sasze_nonradiance(source: Path, case: Case, stream: str, out_path: Path) -> list[datetime]:
    t6, t8 = parse_utc(case.t6), parse_utc(case.t8)
    core_start, core_end = min(t6, t8), max(t6, t8)
    win_start, win_end = core_start - BUFFER, core_end + BUFFER
    source_sha = sha256_file(source)
    with Dataset(source, "r") as ds:
        times = decode_time(ds)
        indices = _window_indices(times, win_start, win_end)
        meta = safe_source_metadata(ds)
        data = {}
        # IMPORTANT: selection is made by name before any variable data access.
        for name, var in ds.variables.items():
            if not is_allowed_sasze_var(name):
                continue
            if is_protected_sasze_var(name):
                raise RuntimeError("internal firewall error: protected SASZE variable passed allow-list")
            data[name] = read_allowed_variable(var, indices)
        payload = {
            "schema": 2,
            "case_id": case.case_id,
            "priority_order": case.priority_order,
            "stream": stream,
            "source_filename": source.name,
            "source_size_bytes": source.stat().st_size,
            "source_sha256": source_sha,
            "source_path": str(source),
            "exact_t6_utc": case.t6,
            "exact_t7_utc": case.t7,
            "exact_t8_utc": case.t8,
            "extract_start_utc": iso(win_start),
            "extract_end_utc": iso(win_end),
            "selected_time_count": len(indices),
            "selected_times_utc": [iso(times[i]) for i in indices],
            "source_metadata": meta,
            "allowed_nonphotometric_data": data,
            "holdout_firewall": {
                "sasze_radiance_magnitudes_opened": False,
                "protected_photometric_values_opened": False,
                "protected_variable_values_read": False,
                "raw_sasze_source_copied": False,
            },
        }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    invalid = datetime.min.replace(tzinfo=timezone.utc)
    return [t for t in times if t != invalid]


def continuity_row(case: Case, stream: str, sources: list[Path], times: Iterable[datetime]) -> dict[str, Any]:
    vals = sorted(set(times))
    t6, t8 = parse_utc(case.t6), parse_utc(case.t8)
    start, end = min(t6, t8), max(t6, t8)
    core = [t for t in vals if start <= t <= end]
    before = [t for t in vals if t <= start]
    after = [t for t in vals if t >= end]
    positive = [(b - a).total_seconds() for a, b in zip(vals, vals[1:]) if b > a]
    med = float(np.median(np.asarray(positive))) if positive else None
    span = []
    if before and after:
        left, right = before[-1], after[0]
        span = [t for t in vals if left <= t <= right]
    gaps = [(b - a).total_seconds() for a, b in zip(span, span[1:]) if b > a]
    max_gap = max(gaps) if gaps else None
    bracketed = bool(before and after)
    continuity = bool(bracketed and med is not None and max_gap is not None and max_gap <= 2.0 * med)
    nearest_start = min((abs((t - start).total_seconds()) for t in vals), default=None)
    nearest_end = min((abs((t - end).total_seconds()) for t in vals), default=None)
    return {
        "case_id": case.case_id,
        "priority_order": case.priority_order,
        "stream": stream,
        "source_files": ";".join(p.name for p in sources),
        "source_file_count": len(sources),
        "core_start_utc": iso(start),
        "core_end_utc": iso(end),
        "native_timestamp_count_total": len(vals),
        "native_timestamp_count_core": len(core),
        "first_native_timestamp_utc": iso(vals[0]) if vals else "",
        "last_native_timestamp_utc": iso(vals[-1]) if vals else "",
        "nearest_offset_core_start_s": nearest_start,
        "nearest_offset_core_end_s": nearest_end,
        "median_positive_cadence_s": med,
        "max_gap_bracketing_core_s": max_gap,
        "bracketed_core": bracketed,
        "continuity_pass_mechanical": continuity,
        "radiance_magnitudes_opened": False,
    }


def matches(files: list[Path], patterns: Iterable[str]) -> list[Path]:
    out = []
    pats = [p.lower() for p in patterns]
    for f in files:
        n = f.name.lower()
        if any(fnmatch.fnmatch(n, p) for p in pats):
            out.append(f)
    return sorted(set(out))


def copy_raw(source: Path, raw_dir: Path, copied_by_sha: dict[str, Path]) -> tuple[str, Path]:
    low = source.name.lower()
    if low.startswith("sgpsasze") or any(tok in low for tok in PROTECTED_SASZE_TOKENS):
        raise RuntimeError("holdout firewall: refusing to copy SASZE/protected raw source " + source.name)
    digest = sha256_file(source)
    if digest in copied_by_sha:
        return digest, copied_by_sha[digest]
    dst = raw_dir / source.name
    if dst.exists() and sha256_file(dst) != digest:
        dst = raw_dir / (digest[:12] + "__" + source.name)
    shutil.copy2(source, dst)
    copied_by_sha[digest] = dst
    return digest, dst


def scan_code_version(path: Path) -> str | None:
    try:
        with Dataset(path, "r") as ds:
            v = getattr(ds, "code_version", None)
            return None if v is None else str(scalar(v))
    except Exception:
        return None


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = sorted({k for r in rows for k in r}) if rows else []
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        if not fields:
            f.write("")
            return
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive-root", required=True, type=Path)
    ap.add_argument("--output-dir", type=Path, default=Path.cwd())
    ap.add_argument("--python-packages", type=Path, default=None, help="Handled before imports; retained in provenance.")
    args = ap.parse_args()
    root = args.archive_root.resolve()
    if not root.is_dir():
        raise SystemExit("archive root is not a directory: " + str(root))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    package_name = f"{PACKAGE_PREFIX}_{stamp}"
    stage = args.output_dir.resolve() / package_name
    raw_dir = stage / "raw_non_sasze"
    derived_dir = stage / "derived_sasze_nonradiance"
    stage.mkdir(parents=True, exist_ok=False)
    raw_dir.mkdir()
    derived_dir.mkdir()

    files = sorted(p for p in root.rglob("*") if p.is_file())
    netcdf_files = [p for p in files if p.suffix.lower() in (".nc", ".cdf")]
    manifest: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    copied_by_sha: dict[str, Path] = {}
    sasze_continuity: list[dict[str, Any]] = []

    for case in CASES:
        for gate, component, templates, shifts in RAW_COMPONENTS:
            pats = []
            for shift in shifts:
                d = date_shift(case.utc_date, shift)
                pats.extend(t.format(d=d).lower() for t in templates)
            found = matches(netcdf_files, pats)
            if not found:
                missing.append({
                    "case_id": case.case_id, "priority_order": case.priority_order,
                    "gate": gate, "component": component,
                    "patterns": ";".join(pats), "disposition": "NO_LOCAL_FILENAME_MATCH",
                })
                continue
            for src in found:
                digest, dst = copy_raw(src, raw_dir, copied_by_sha)
                code_version = scan_code_version(src) if component == "HSRL" else None
                manifest.append({
                    "case_id": case.case_id, "priority_order": case.priority_order,
                    "gate": gate, "component": component,
                    "source_filename": src.name, "source_path": str(src),
                    "source_size_bytes": src.stat().st_size, "source_sha256": digest,
                    "packaged_path": str(dst.relative_to(stage)).replace("\\", "/"),
                    "packaged_unchanged": True,
                    "code_version": code_version or "",
                    "hsrl_2_6_7_candidate": bool(component == "HSRL" and code_version == "2.6.7"),
                    "radiance_magnitudes_opened": False,
                })

        # SASZE firewall path: locate source files, but never copy them.
        for stream, prefixes in (
            ("FILTERBANDS", ("sgpsaszefilterbandsC1.a1",)),
            ("VIS_HOUSEKEEPING", ("sgpsaszevisC1.a1",)),
        ):
            pats = []
            for prefix in prefixes:
                pats.extend((f"{prefix}*{case.utc_date}*.nc".lower(), f"{prefix}*{case.utc_date}*.cdf".lower()))
            found = matches(netcdf_files, pats)
            if not found:
                missing.append({
                    "case_id": case.case_id, "priority_order": case.priority_order,
                    "gate": "SASZE_HK", "component": stream,
                    "patterns": ";".join(pats), "disposition": "NO_LOCAL_FILENAME_MATCH",
                })
                continue
            all_times: list[datetime] = []
            for src in found:
                src_digest = sha256_file(src)
                out = derived_dir / case.case_id / (stream.lower() + "__" + src.name + ".json")
                times = extract_sasze_nonradiance(src, case, stream, out)
                all_times.extend(times)
                manifest.append({
                    "case_id": case.case_id, "priority_order": case.priority_order,
                    "gate": "SASZE_HK", "component": stream,
                    "source_filename": src.name, "source_path": str(src),
                    "source_size_bytes": src.stat().st_size, "source_sha256": src_digest,
                    "packaged_path": str(out.relative_to(stage)).replace("\\", "/"),
                    "packaged_unchanged": False,
                    "code_version": "",
                    "hsrl_2_6_7_candidate": False,
                    "radiance_magnitudes_opened": False,
                    "raw_sasze_source_copied": False,
                    "derived_nonphotometric_extract_only": True,
                })
            sasze_continuity.append(continuity_row(case, stream, found, all_times))

    write_csv(stage / "collection_manifest.csv", manifest)
    write_csv(stage / "missing_patterns.csv", missing)
    write_csv(stage / "sasze_time_continuity.csv", sasze_continuity)

    summary = {
        "schema": SCHEMA,
        "package": package_name,
        "created_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "archive_root": str(root),
        "case_ids": [c.case_id for c in CASES],
        "indexed_file_count": len(files),
        "indexed_netcdf_cdf_count": len(netcdf_files),
        "manifest_rows": len(manifest),
        "unique_raw_non_sasze_files": len(copied_by_sha),
        "missing_component_rows": len(missing),
        "sasze_continuity_rows": len(sasze_continuity),
        "holdout_firewall": {
            "sasze_vis_raw_copied": False,
            "sasze_nir_raw_copied": False,
            "sasze_filterbands_raw_copied": False,
            "sasze_radiance_magnitudes_opened": False,
            "protected_photometric_values_opened": False,
            "sasze_source_values_allowed_only_by_strict_nonphotometric_allowlist": True,
            "protected_sasze_tokens": list(PROTECTED_SASZE_TOKENS),
        },
        "scientific_gate_pass_claimed": False,
        "note": "Collection/evidence transport only. HSRL 2.6.7 and all G2/G4-G9/SASZE health gates remain downstream decisions.",
    }
    (stage / "collection_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (stage / "README.txt").write_text(
        "ARM SGP POST-G3 EXACT-EIGHT NATIVE NON-RADIANCE V2\n\n"
        "This package is result-blind. Non-SASZE G2/G4-G9 native files are preserved byte-for-byte.\n"
        "SASZE VIS/filterbands raw files are NOT packaged. Only time and strict allow-listed housekeeping/QC/calibration data are read into derived JSON.\n"
        "No SASZE radiance magnitude/protected photometric value is read or serialized.\n"
        "Use sasze_time_continuity.csv for result-blind native timestamp continuity evidence; it is not a scientific sky-radiance result.\n",
        encoding="utf-8",
    )

    member_rows = []
    for p in sorted(x for x in stage.rglob("*") if x.is_file()):
        member_rows.append({
            "path": str(p.relative_to(stage)).replace("\\", "/"),
            "size_bytes": p.stat().st_size,
            "sha256": sha256_file(p),
        })
    write_csv(stage / "package_member_hashes.csv", member_rows)
    zip_path = args.output_dir.resolve() / (package_name + ".zip")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(x for x in stage.rglob("*") if x.is_file()):
            z.write(p, str(p.relative_to(stage)).replace("\\", "/"))
    zip_sha = sha256_file(zip_path)
    print(json.dumps({
        "status": "DONE_RESULT_BLIND_NONRADIANCE",
        "zip": str(zip_path),
        "size_bytes": zip_path.stat().st_size,
        "sha256": zip_sha,
        "manifest_rows": len(manifest),
        "missing_component_rows": len(missing),
        "sasze_radiance_magnitudes_opened": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
