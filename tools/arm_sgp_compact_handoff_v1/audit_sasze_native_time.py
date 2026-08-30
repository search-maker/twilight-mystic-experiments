#!/usr/bin/env python3
"""Strict residual-blind SASZE native-time operability audit.

The primary Phase-0 held-out-observable gate is the calibrated full VIS stream
(`sgpsaszevisC1.a1`). NIR is an independently audited secondary spectral
extension. `sgpsaszefilterbandsC1.a1` is retained only as a daylight-derived
product/timing diagnostic: actual 2024 file evidence shows its time coordinate
continues through twilight while its derived band-radiance fields are daylight
gated. This script never reads any SASZE radiance/transmittance value.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any, Sequence

import netCDF4
import numpy as np

UTC = dt.timezone.utc
PRIMARY_STREAM = "sgpsaszevisC1.a1"
STREAMS: tuple[tuple[str, str, str], ...] = (
    (PRIMARY_STREAM, "PRIMARY_HELDOUT_SUPPORT", "CALIBRATED_FULL_SPECTRAL_RADIANCE"),
    ("sgpsaszenirC1.a1", "SECONDARY_SPECTRAL_EXTENSION", "CALIBRATED_FULL_SPECTRAL_RADIANCE"),
    (
        "sgpsaszefilterbandsC1.a1",
        "DAYLIGHT_DERIVED_DIAGNOSTIC",
        "DAYLIGHT_GATED_DERIVED_RADIANCE_NOT_TWILIGHT_GATE",
    ),
)
# Backward-compatible import used by older callers/self-tests.
STREAM = PRIMARY_STREAM
QC_VAR_RE = re.compile(r"(^qc_|_qc$|quality|flag|mask|status)", re.I)
AUDIT_VARS = {
    "integration_time", "integration_time_vis", "integration_time_nir",
    "number_of_scans", "number_of_scans_vis", "number_of_scans_nir",
    "shutter_state", "collector_x_tilt", "collector_y_tilt",
    "collector_x_tilt_std", "collector_y_tilt_std",
}
FIELDS = (
    "priority", "case_id", "event", "stream", "product_role", "product_semantics",
    "source_files", "core_start_utc", "core_end_utc",
    "decoded_sample_count_core", "first_sample_utc", "last_sample_utc",
    "nearest_sample_to_minus8_s", "nearest_sample_to_minus7_s", "nearest_sample_to_minus6_s",
    "median_positive_cadence_s", "max_internal_gap_s", "samples_within_5s_minus8",
    "samples_within_5s_minus7", "samples_within_5s_minus6", "distinct_integration_modes",
    "health_flag_names_present", "read_errors", "disposition",
)


def parse_utc(text: str) -> dt.datetime:
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    value = dt.datetime.fromisoformat(text)
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def iso_epoch(seconds: float | None) -> str:
    if seconds is None:
        return ""
    return dt.datetime.fromtimestamp(float(seconds), UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def decoded_datetime(value: Any) -> dt.datetime:
    return dt.datetime(
        int(value.year), int(value.month), int(value.day), int(value.hour), int(value.minute), int(value.second),
        int(getattr(value, "microsecond", 0)), tzinfo=UTC,
    )


def decode_native_times(ds: netCDF4.Dataset) -> np.ndarray:
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
                return np.asarray([decoded_datetime(x).timestamp() for x in decoded], dtype=float)
            return np.array([], dtype=float)
    if "base_time" in ds.variables and "time_offset" in ds.variables:
        base = np.ma.asarray(ds.variables["base_time"][:]).squeeze()
        offsets = np.ma.asarray(ds.variables["time_offset"][:])
        if np.ma.isMaskedArray(base) and bool(np.ma.getmaskarray(base)):
            return np.array([], dtype=float)
        vals = offsets.compressed() if np.ma.isMaskedArray(offsets) else np.asarray(offsets).ravel()
        vals = np.asarray(vals, dtype=float)
        vals = vals[np.isfinite(vals)]
        if vals.size:
            return float(base) + vals
        return np.array([], dtype=float)
    return np.array([], dtype=float)


def has_decodable_time_coordinate(ds: netCDF4.Dataset) -> bool:
    """Whether an empty native-time array is still structurally decodable."""
    if "time" in ds.variables and bool(getattr(ds.variables["time"], "units", None)):
        return True
    return "base_time" in ds.variables and "time_offset" in ds.variables


def load_cases(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    required = {"priority", "case_id", "event", "source_date_utc", "t_minus8_utc", "t_minus7_utc", "t_minus6_utc"}
    missing = required.difference(rows[0].keys() if rows else [])
    if missing:
        raise ValueError(f"priority CSV missing columns: {sorted(missing)}")
    return rows


def strict_gap_metrics(times: np.ndarray, core_start: float, core_end: float) -> tuple[float | None, float | None, bool]:
    """Return source-day median cadence, bracketing-segment max gap, bracket flag."""
    if times.size < 2:
        return None, None, False
    times = np.unique(times[np.isfinite(times)])
    positive = np.diff(times)
    positive = positive[positive > 0]
    cadence = float(np.median(positive)) if positive.size else None

    left_candidates = np.flatnonzero(times <= core_start)
    right_candidates = np.flatnonzero(times >= core_end)
    if left_candidates.size == 0 or right_candidates.size == 0:
        return cadence, None, False
    left = int(left_candidates[-1])
    right = int(right_candidates[0])
    if right <= left:
        return cadence, None, False
    segment = times[left : right + 1]
    gaps = np.diff(segment)
    gaps = gaps[gaps > 0]
    max_gap = float(np.max(gaps)) if gaps.size else None
    return cadence, max_gap, True


def collect_housekeeping(ds: netCDF4.Dataset, modes: set[str], health: set[str], errors: list[str], source: str) -> None:
    """Read timing/housekeeping metadata only; never touch radiance/transmittance."""
    for name, var in ds.variables.items():
        lname = name.lower()
        if name in AUDIT_VARS or "integration_time" in lname or "number_of_scans" in lname:
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
                errors.append(f"{source}:{name}:{type(exc).__name__}:{exc}")
        if QC_VAR_RE.search(name) or "satur" in lname or "health" in lname or "high_sza" in lname:
            health.add(name)


def stream_meta(stream: str) -> tuple[str, str]:
    for candidate, role, semantics in STREAMS:
        if candidate == stream:
            return role, semantics
    raise ValueError(f"unsupported SASZE stream: {stream}")


def matching_files(archive_root: Path, stream: str, source_date_utc: str) -> list[Path]:
    found: set[Path] = set()
    for ext in ("nc", "cdf"):
        found.update(p for p in archive_root.rglob(f"{stream}.{source_date_utc}.*.{ext}") if p.is_file())
    return sorted(found)


def audit_case(archive_root: Path, case: dict[str, str], stream: str = PRIMARY_STREAM) -> dict[str, Any]:
    role, semantics = stream_meta(stream)
    files = matching_files(archive_root, stream, case["source_date_utc"])
    t8 = parse_utc(case["t_minus8_utc"]).timestamp()
    t7 = parse_utc(case["t_minus7_utc"]).timestamp()
    t6 = parse_utc(case["t_minus6_utc"]).timestamp()
    core_start, core_end = sorted((t8, t6))

    chunks: list[np.ndarray] = []
    errors: list[str] = []
    modes: set[str] = set()
    health: set[str] = set()
    readable = 0
    unresolved_source_files = 0
    for path in files:
        try:
            with netCDF4.Dataset(path, "r") as ds:
                times = decode_native_times(ds)
                readable += 1
                if not times.size and not has_decodable_time_coordinate(ds):
                    unresolved_source_files += 1
                    errors.append(f"{path.name}:NO_DECODABLE_NATIVE_TIME_COORDINATE")
                elif times.size:
                    chunks.append(times[np.isfinite(times)])
                collect_housekeeping(ds, modes, health, errors, path.name)
        except Exception as exc:
            unresolved_source_files += 1
            errors.append(f"{path.name}:{type(exc).__name__}:{exc}")

    times = np.unique(np.concatenate(chunks)) if chunks else np.array([], dtype=float)
    core = times[(times >= core_start) & (times <= core_end)]
    cadence, max_gap, brackets = strict_gap_metrics(times, core_start, core_end)
    gap_ok = bool(cadence is not None and max_gap is not None and max_gap <= 2.0 * cadence + 1e-9)

    if not files:
        disposition = "SOURCE_FILE_MISSING"
    elif readable == 0 or unresolved_source_files > 0:
        # Fail closed even if another same-day file is readable/continuous. A
        # partially unresolved source set cannot prove observational absence or
        # continuity and therefore must never contribute to the all-20 HALT rule.
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
        "product_role": role, "product_semantics": semantics,
        "source_files": ";".join(str(p.relative_to(archive_root)) for p in files),
        "core_start_utc": iso_epoch(core_start), "core_end_utc": iso_epoch(core_end),
        "decoded_sample_count_core": int(core.size),
        "first_sample_utc": iso_epoch(float(times.min())) if times.size else "",
        "last_sample_utc": iso_epoch(float(times.max())) if times.size else "",
        "nearest_sample_to_minus8_s": nearest(t8), "nearest_sample_to_minus7_s": nearest(t7),
        "nearest_sample_to_minus6_s": nearest(t6),
        "median_positive_cadence_s": "" if cadence is None else f"{cadence:.6f}",
        "max_internal_gap_s": "" if max_gap is None else f"{max_gap:.6f}",
        "samples_within_5s_minus8": within(t8), "samples_within_5s_minus7": within(t7),
        "samples_within_5s_minus6": within(t6),
        "distinct_integration_modes": ";".join(sorted(modes)),
        "health_flag_names_present": ";".join(sorted(health)),
        "read_errors": " | ".join(errors), "disposition": disposition,
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def update_summary(path: Path, rows: list[dict[str, Any]]) -> None:
    summary = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    counts_by_stream: dict[str, dict[str, int]] = {}
    for row in rows:
        stream = str(row["stream"])
        disposition = str(row["disposition"])
        stream_counts = counts_by_stream.setdefault(stream, {})
        stream_counts[disposition] = stream_counts.get(disposition, 0) + 1

    primary_rows = [r for r in rows if r["stream"] == PRIMARY_STREAM]
    summary["sasze_gate_algorithm"] = "strict-primary-vis-source-day-cadence-edge-gap-partial-unreadable-failclosed-v3"
    summary["sasze_primary_gate_stream"] = PRIMARY_STREAM
    summary["sasze_secondary_stream"] = "sgpsaszenirC1.a1"
    summary["sasze_filterband_role"] = "DAYLIGHT_DERIVED_DIAGNOSTIC_NOT_TWILIGHT_HELDOUT_GATE"
    summary["sasze_gate_counts_by_stream"] = {
        stream: dict(sorted(counts.items())) for stream, counts in sorted(counts_by_stream.items())
    }
    summary["sasze_primary_gate_complete_readable"] = all(
        r["disposition"] not in {"SOURCE_FILE_MISSING", "UNREADABLE"} for r in primary_rows
    )
    summary["sasze_primary_survivor_case_ids"] = [
        r["case_id"] for r in primary_rows if r["disposition"] == "TWILIGHT_CONTIGUOUS"
    ]
    summary["sasze_all20_primary_vis_readably_absent_or_discontinuous"] = bool(primary_rows) and all(
        r["disposition"] in {"TWILIGHT_DISCONTINUOUS", "TWILIGHT_SAMPLES_ABSENT"} for r in primary_rows
    )
    path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-root", type=Path, required=True)
    parser.add_argument("--priority-csv", type=Path, default=Path(__file__).with_name("priority20_sasze_gate.csv"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--update-summary", type=Path)
    args = parser.parse_args(argv)

    archive_root = args.archive_root.resolve()
    cases = load_cases(args.priority_csv)
    rows = [audit_case(archive_root, case, stream) for case in cases for stream, _, _ in STREAMS]
    write_csv(args.output, rows)
    if args.update_summary:
        update_summary(args.update_summary, rows)

    primary_rows = [r for r in rows if r["stream"] == PRIMARY_STREAM]
    counts: dict[str, int] = {}
    for row in primary_rows:
        counts[row["disposition"]] = counts.get(row["disposition"], 0) + 1
    print(json.dumps({
        "primary_gate_stream": PRIMARY_STREAM,
        "primary_gate_counts": counts,
        "primary_survivors": [r["case_id"] for r in primary_rows if r["disposition"] == "TWILIGHT_CONTIGUOUS"],
        "audited_streams": [s for s, _, _ in STREAMS],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
