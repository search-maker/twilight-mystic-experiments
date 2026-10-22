#!/usr/bin/env python3
"""Hardened residual-blind executor for ARM SGP V2 SASZE anchor support.

This module preserves the frozen scientific gate in Issue #60 comment 5471264663
and only repairs mechanical indexing/provenance hazards in the first V2 runner:
- native time indices remain aligned with the radiance time axis even if a time
  coordinate contains masked/non-finite entries;
- masked/non-finite wavelength coordinates fail closed instead of being
  compressed and shifting the radiance pixel index;
- the native pixel nearest 464.020874 nm is selected independently in each
  contributing source file, so a harmless source-file wavelength-grid change
  is not promoted into a new scientific exclusion rule;
- duplicate native timestamps combine validity with logical OR.

No SASZE radiance magnitude is printed, persisted, ranked, or returned.
"""

from __future__ import annotations

import argparse
import csv
import json
import tempfile
from pathlib import Path
from typing import Any, Sequence

import netCDF4
import numpy as np

import audit_sasze_anchor_support_v2 as base


def decode_native_times_aligned(ds: netCDF4.Dataset) -> np.ndarray:
    """Return one epoch-second slot per native time-axis element; invalid slots are NaN."""
    if "time" in ds.variables:
        var = ds.variables["time"]
        units = getattr(var, "units", None)
        if units:
            raw = np.ma.asarray(var[:]).reshape(-1)
            data = np.asarray(np.ma.getdata(raw), dtype=float).reshape(-1)
            mask = np.asarray(np.ma.getmaskarray(raw), dtype=bool).reshape(-1) | ~np.isfinite(data)
            out = np.full(data.shape, np.nan, dtype=float)
            good = np.flatnonzero(~mask)
            if good.size:
                decoded = netCDF4.num2date(
                    data[good], units=units, calendar=getattr(var, "calendar", "standard")
                )
                out[good] = [base.decoded_datetime(value).timestamp() for value in decoded]
            return out

    if "base_time" in ds.variables and "time_offset" in ds.variables:
        base_raw = np.ma.asarray(ds.variables["base_time"][:]).squeeze()
        if np.asarray(np.ma.getmaskarray(base_raw)).any():
            return np.array([], dtype=float)
        base_value = float(np.asarray(np.ma.getdata(base_raw)).squeeze())
        if not np.isfinite(base_value):
            return np.array([], dtype=float)
        offsets = np.ma.asarray(ds.variables["time_offset"][:]).reshape(-1)
        data = np.asarray(np.ma.getdata(offsets), dtype=float).reshape(-1)
        mask = np.asarray(np.ma.getmaskarray(offsets), dtype=bool).reshape(-1) | ~np.isfinite(data)
        out = np.full(data.shape, np.nan, dtype=float)
        good = ~mask
        out[good] = base_value + data[good]
        return out

    return np.array([], dtype=float)


def strict_wavelength_nm(var: netCDF4.Variable) -> np.ndarray:
    """Preserve wavelength-axis indexing; never compress masked coordinates."""
    raw = np.ma.asarray(var[:]).reshape(-1)
    mask = np.asarray(np.ma.getmaskarray(raw), dtype=bool).reshape(-1)
    if mask.any():
        raise ValueError("MASKED_WAVELENGTH_COORDINATE")
    arr = np.asarray(np.ma.getdata(raw), dtype=float).reshape(-1)
    if arr.size == 0 or not np.all(np.isfinite(arr)):
        raise ValueError("INVALID_WAVELENGTH_COORDINATE")
    units = str(getattr(var, "units", "")).strip().lower().replace("µ", "u")
    if units in {"nm", "nanometer", "nanometers", "nanometre", "nanometres"}:
        return arr
    if units in {"um", "micron", "microns", "micrometer", "micrometers", "micrometre", "micrometres"}:
        return arr * 1000.0
    raise ValueError(f"unsupported wavelength units: {units!r}")


def read_timing_file(path: Path) -> base.TimingFile:
    """G0 timing requires readable native time only; wavelength is checked only if a file contributes."""
    try:
        with netCDF4.Dataset(path, "r") as ds:
            aligned = decode_native_times_aligned(ds)
            finite = aligned[np.isfinite(aligned)]
            if not finite.size:
                return base.TimingFile(path, np.array([], dtype=float), None, "NO_DECODABLE_NATIVE_TIMESTAMPS")
            return base.TimingFile(path, np.asarray(finite, dtype=float), None, None)
    except Exception as exc:
        return base.TimingFile(path, np.array([], dtype=float), None, f"{type(exc).__name__}:{exc}")


def _fill_exclusions(var: netCDF4.Variable, raw: np.ndarray, valid: np.ndarray) -> np.ndarray:
    for attr in ("_FillValue", "missing_value"):
        if not hasattr(var, attr):
            continue
        values = np.asarray(getattr(var, attr)).reshape(-1)
        for value in values:
            try:
                fv = float(value)
            except Exception:
                continue
            if np.isnan(fv):
                valid &= ~np.isnan(raw)
            else:
                valid &= raw != fv
    return valid


def boolean_validity_for_file(
    path: Path, target_nm: float, centers: dict[str, float]
) -> tuple[dict[str, dict[float, bool]], tuple[int, float] | None]:
    """Return timestamp->valid booleans plus native pixel identity, never radiance values."""
    result: dict[str, dict[float, bool]] = {name: {} for name in centers}
    with netCDF4.Dataset(path, "r") as ds:
        times = decode_native_times_aligned(ds)
        if not times.size:
            return result, None

        anchor_indices: dict[str, np.ndarray] = {}
        contributes = False
        for name, center in centers.items():
            indices = np.flatnonzero(np.isfinite(times) & (np.abs(times - center) <= 30.0 + 1e-9))
            anchor_indices[name] = indices
            contributes = contributes or bool(indices.size)
        if not contributes:
            return result, None

        if "wavelength" not in ds.variables:
            raise ValueError(f"{path.name}:MISSING_WAVELENGTH_COORDINATE")
        grid = strict_wavelength_nm(ds.variables["wavelength"])
        pixel = int(np.argmin(np.abs(grid - target_nm)))
        pixel_wavelength = float(grid[pixel])

        if "zenith_radiance" not in ds.variables:
            raise ValueError(f"{path.name}:MISSING_ZENITH_RADIANCE_VARIABLE")
        var = ds.variables["zenith_radiance"]
        dims = tuple(var.dimensions)
        if "time" not in dims or "wavelength" not in dims:
            raise ValueError(f"{path.name}:UNEXPECTED_ZENITH_RADIANCE_DIMENSIONS:{dims}")
        time_axis = dims.index("time")
        wavelength_axis = dims.index("wavelength")
        if var.ndim != 2 or {time_axis, wavelength_axis} != {0, 1}:
            raise ValueError(f"{path.name}:UNSUPPORTED_ZENITH_RADIANCE_LAYOUT:{dims}")
        if var.shape[time_axis] != times.size:
            raise ValueError(f"{path.name}:TIME_AXIS_LENGTH_MISMATCH")
        if var.shape[wavelength_axis] != grid.size:
            raise ValueError(f"{path.name}:WAVELENGTH_AXIS_LENGTH_MISMATCH")

        for name, indices in anchor_indices.items():
            if not indices.size:
                continue
            subset = (
                np.ma.asarray(var[indices, pixel])
                if time_axis == 0
                else np.ma.asarray(var[pixel, indices])
            )
            mask = np.asarray(np.ma.getmaskarray(subset), dtype=bool).reshape(-1)
            raw = np.asarray(np.ma.getdata(subset), dtype=float).reshape(-1)
            valid = (~mask) & np.isfinite(raw)
            valid = _fill_exclusions(var, raw, valid)
            for idx, ok in zip(indices.tolist(), valid.tolist()):
                stamp = float(times[idx])
                result[name][stamp] = bool(result[name].get(stamp, False) or bool(ok))
            del raw, subset, mask, valid

        return result, (pixel, pixel_wavelength)


def merge_validity(dest: dict[str, dict[float, bool]], src: dict[str, dict[float, bool]]) -> None:
    for anchor, samples in src.items():
        for timestamp, valid in samples.items():
            dest[anchor][timestamp] = bool(dest[anchor].get(timestamp, False) or valid)


def audit_event(event: base.Event, archive_root: Path, file_index: dict[str, list[Path]]) -> dict[str, Any]:
    source_paths: list[Path] = []
    for date_key in base.dates_needed(event):
        source_paths.extend(file_index.get(date_key, []))
    source_paths = sorted(set(source_paths))
    centers = {
        "minus8": base.parse_utc(event.t_minus8_utc),
        "minus7": base.parse_utc(event.t_minus7_utc),
        "minus6": base.parse_utc(event.t_minus6_utc),
    }
    row: dict[str, Any] = {
        **event.__dict__,
        "source_files": ";".join(str(path.relative_to(archive_root)) for path in source_paths),
        "source_file_count": len(source_paths),
        "read_errors": "",
        "target_wavelength_nm_requested": f"{base.TARGET_WAVELENGTH_NM:.6f}",
        "target_pixel_index": "",
        "target_pixel_wavelength_nm": "",
        "target_pixel_map": "",
        "timing_pass": False,
        "validity_pass": False,
        "firewall_status": base.KNOWN_EXPOSED.get(event.case_id, "BLIND_ELIGIBLE"),
        "primary_holdout_eligible_after_g0": False,
        "disposition": "",
    }
    for name in centers:
        row[f"nearest_{name}_s"] = ""
        row[f"samples_within_5s_{name}"] = 0
        row[f"samples_within_30s_{name}"] = 0
        row[f"valid_464_samples_within_30s_{name}"] = ""

    if not source_paths:
        row["disposition"] = "SOURCE_FILE_MISSING"
        return row

    timing_files = [read_timing_file(path) for path in source_paths]
    errors = [f"{item.path.name}:{item.error}" for item in timing_files if item.error]
    if errors:
        row["read_errors"] = " | ".join(errors)
        row["disposition"] = "UNREADABLE_OR_UNDECODABLE"
        return row

    arrays = [item.times for item in timing_files if item.times.size]
    all_times = np.unique(np.concatenate(arrays)) if arrays else np.array([], dtype=float)
    if not all_times.size:
        row["disposition"] = "NO_NATIVE_TIMESTAMPS"
        return row

    timing_pass = True
    for name, center in centers.items():
        nearest, count5 = base.nearest_and_count(all_times, center, 5.0)
        _, count30 = base.nearest_and_count(all_times, center, 30.0)
        row[f"nearest_{name}_s"] = "" if nearest is None else f"{nearest:.6f}"
        row[f"samples_within_5s_{name}"] = count5
        row[f"samples_within_30s_{name}"] = count30
        if count5 < 1 or count30 < 10:
            timing_pass = False
    row["timing_pass"] = timing_pass
    if not timing_pass:
        row["disposition"] = "G0_V2_TIMING_FAIL"
        return row

    validity: dict[str, dict[float, bool]] = {name: {} for name in centers}
    pixel_records: list[tuple[str, int, float]] = []
    try:
        for path in source_paths:
            partial, pixel_meta = boolean_validity_for_file(path, base.TARGET_WAVELENGTH_NM, centers)
            merge_validity(validity, partial)
            if pixel_meta is not None:
                pixel_records.append((str(path.relative_to(archive_root)), pixel_meta[0], pixel_meta[1]))
    except Exception as exc:
        row["read_errors"] = f"{type(exc).__name__}:{exc}"
        row["disposition"] = "G0_V2_VALIDITY_UNREADABLE"
        return row

    if not pixel_records:
        row["disposition"] = "G0_V2_VALIDITY_UNREADABLE"
        row["read_errors"] = "NO_CONTRIBUTING_NATIVE_PIXEL"
        return row

    row["target_pixel_map"] = ";".join(
        f"{name}|{pixel}|{wavelength:.9f}" for name, pixel, wavelength in pixel_records
    )
    indices = {pixel for _, pixel, _ in pixel_records}
    wavelengths = {format(wavelength, ".9f") for _, _, wavelength in pixel_records}
    row["target_pixel_index"] = next(iter(indices)) if len(indices) == 1 else "PER_FILE"
    row["target_pixel_wavelength_nm"] = next(iter(wavelengths)) if len(wavelengths) == 1 else "PER_FILE"

    validity_pass = True
    for name in centers:
        count = sum(1 for ok in validity[name].values() if ok)
        row[f"valid_464_samples_within_30s_{name}"] = count
        if count < 5:
            validity_pass = False
    row["validity_pass"] = validity_pass
    if not validity_pass:
        row["disposition"] = "G0_V2_PIXEL_VALIDITY_FAIL"
        return row

    if event.case_id in base.KNOWN_EXPOSED:
        row["disposition"] = "EXPOSED_DEVELOPMENT_ONLY"
        return row

    row["primary_holdout_eligible_after_g0"] = True
    row["disposition"] = "G0_V2_PASS_BLIND_CANDIDATE"
    return row


def _write_fixture(path: Path, times: np.ndarray, wavelengths: np.ndarray, masked_time_index: int | None = None) -> None:
    with netCDF4.Dataset(path, "w") as ds:
        ds.createDimension("time", len(times))
        ds.createDimension("wavelength", len(wavelengths))
        tv = ds.createVariable("time", "f8", ("time",), fill_value=-9999.0)
        tv.units = "seconds since 1970-01-01 00:00:00 UTC"
        tdata = np.asarray(times, dtype=float).copy()
        if masked_time_index is not None:
            tdata[masked_time_index] = -9999.0
        tv[:] = tdata
        wv = ds.createVariable("wavelength", "f8", ("wavelength",), fill_value=-9999.0)
        wv.units = "nm"
        wv[:] = wavelengths
        rv = ds.createVariable("zenith_radiance", "f8", ("time", "wavelength"), fill_value=-9999.0)
        data = np.ones((len(times), len(wavelengths)), dtype=float)
        data[:, :] = 1.0
        rv[:] = data


def self_test() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        a = root / "sgpsaszevisC1.a1.19700101.000000.nc"
        b = root / "sgpsaszevisC1.a1.19700101.120000.nc"
        block1 = np.concatenate([np.arange(970.0, 1031.0, 2.0), np.arange(1070.0, 1131.0, 2.0)])
        block2 = np.arange(1170.0, 1231.0, 2.0)
        _write_fixture(a, block1, np.array([463.7, 464.018, 465.0]), masked_time_index=1)
        _write_fixture(b, block2, np.array([463.8, 464.024, 465.1]))
        event = base.Event(
            case_id="1970-01-01_dawn",
            local_civil_date="1970-01-01",
            event="dawn",
            t_minus8_utc=base.iso_utc(1000.0),
            t_minus7_utc=base.iso_utc(1100.0),
            t_minus6_utc=base.iso_utc(1200.0),
        )
        row = audit_event(event, root, {"19700101": [a, b]})
        if row["disposition"] != "G0_V2_PASS_BLIND_CANDIDATE":
            raise RuntimeError(f"self-test differing-grid/aligned-time failure: {row['disposition']} {row['read_errors']}")
        if row["target_pixel_wavelength_nm"] != "PER_FILE":
            raise RuntimeError("self-test failed to preserve per-file native pixel identity")

        bad = root / "masked_wavelength.nc"
        _write_fixture(bad, np.arange(970.0, 1031.0, 2.0), np.array([463.7, -9999.0, 465.0]))
        try:
            with netCDF4.Dataset(bad, "r") as ds:
                strict_wavelength_nm(ds.variables["wavelength"])
        except ValueError as exc:
            if "MASKED_WAVELENGTH_COORDINATE" not in str(exc):
                raise
        else:
            raise RuntimeError("self-test expected masked wavelength refusal")

    print("ARM_V2_ANCHOR_SUPPORT_HARDENED_SELF_TEST_PASS")


OUTPUT_FIELDS = list(base.OUTPUT_FIELDS)
if "target_pixel_map" not in OUTPUT_FIELDS:
    insert_at = OUTPUT_FIELDS.index("valid_464_samples_within_30s_minus8")
    OUTPUT_FIELDS.insert(insert_at, "target_pixel_map")


def write_audit(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=OUTPUT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def run(archive_root: Path, output_dir: Path) -> int:
    archive_root = archive_root.resolve()
    if not archive_root.is_dir():
        raise SystemExit(f"archive root is not a directory: {archive_root}")
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    events = base.build_event_universe()
    events_path = output_dir / "arm_sgp_v2_exact_event_universe.csv"
    audit_path = output_dir / "arm_sgp_v2_sasze_anchor_support_audit.csv"
    summary_path = output_dir / "arm_sgp_v2_sasze_anchor_support_summary.json"
    base.write_event_universe(events_path, events)
    file_index = base.index_vis_files(archive_root)
    rows = [audit_event(event, archive_root, file_index) for event in events]
    write_audit(audit_path, rows)
    base.write_summary(summary_path, events_path, audit_path, rows)

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["executor"] = "audit_sasze_anchor_support_v2_hardened.py"
    summary["mechanical_hardening"] = {
        "native_time_axis_alignment_preserved": True,
        "masked_wavelength_coordinate_refused": True,
        "per_source_file_nearest_native_pixel": True,
        "duplicate_timestamp_validity_combiner": "logical_or",
        "scientific_thresholds_changed": False,
        "radiance_magnitudes_opened": False,
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(summary_path.read_text(encoding="utf-8"))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-root", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        self_test()
        return 0
    if args.archive_root is None or args.output_dir is None:
        parser.error("--archive-root and --output-dir are required unless --self-test is used")
    return run(args.archive_root, args.output_dir)


if __name__ == "__main__":
    raise SystemExit(main())
