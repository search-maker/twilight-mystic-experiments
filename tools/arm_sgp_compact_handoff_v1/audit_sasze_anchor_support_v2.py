#!/usr/bin/env python3
"""Residual-blind exhaustive SASZE VIS anchor-support audit for ARM SGP V2.

Frozen protocol identity:
  ARM_SGP_REAL_SKY_VALIDATION_V2_EXHAUSTIVE_ANCHOR_SUPPORT
  Issue #60 comment 5471264663

The script enumerates all 344 dawn/dusk events from 2023-12-14 through
2024-06-02, computes geometric/unrefracted topocentric solar-center crossings
with NREL SPA (pvlib spa_python, geometric ``elevation`` output), audits only
native ``sgpsaszevisC1.a1`` timestamps for the frozen +/-5 s and +/-30 s
anchor-support rules, and only after a timing pass counts valid/non-fill samples
at the native wavelength pixel nearest 464.020874 nm.

No SASZE radiance magnitude is printed, persisted, summarized, ranked, or used
by any decision. The only allowed access to ``zenith_radiance`` is conversion
of the selected pixel samples directly to a boolean validity mask after timing
G0-V2 has already passed.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence
from zoneinfo import ZoneInfo

import netCDF4
import numpy as np
import pandas as pd
import pvlib

UTC = dt.timezone.utc
LOCAL_TZ = ZoneInfo("America/Chicago")
SITE_LAT = 36.607322
SITE_LON = -97.487643
SITE_ALT_M = 314.0
START_DATE = dt.date(2023, 12, 14)
END_DATE = dt.date(2024, 6, 2)
TARGET_ELEVATIONS = (-8.0, -7.0, -6.0)
TARGET_WAVELENGTH_NM = 464.020874
STREAM = "sgpsaszevisC1.a1"
PROTOCOL = "ARM_SGP_REAL_SKY_VALIDATION_V2_EXHAUSTIVE_ANCHOR_SUPPORT"
CONTROL_COMMENT = "5471264663"
KNOWN_EXPOSED = {"2024-02-08_dusk": "EXPOSED_DEVELOPMENT_ONLY"}
FILE_RE = re.compile(r"^sgpsaszevisC1\.a1\.(\d{8})\..*\.(?:nc|cdf)$", re.I)


@dataclass(frozen=True)
class Event:
    case_id: str
    local_civil_date: str
    event: str
    t_minus8_utc: str
    t_minus7_utc: str
    t_minus6_utc: str


@dataclass
class TimingFile:
    path: Path
    times: np.ndarray
    wavelength_nm: np.ndarray | None
    error: str | None


def iso_utc(ts: dt.datetime | pd.Timestamp | float) -> str:
    if isinstance(ts, (int, float, np.floating)):
        value = dt.datetime.fromtimestamp(float(ts), UTC)
    else:
        value = ts.to_pydatetime() if isinstance(ts, pd.Timestamp) else ts
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        value = value.astimezone(UTC)
    return value.isoformat(timespec="microseconds").replace("+00:00", "Z")


def parse_utc(text: str) -> float:
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    value = dt.datetime.fromisoformat(text)
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).timestamp()


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


def normalize_wavelength_nm(var: netCDF4.Variable) -> np.ndarray:
    values = np.ma.asarray(var[:])
    values = values.compressed() if np.ma.isMaskedArray(values) else np.asarray(values).ravel()
    arr = np.asarray(values, dtype=float)
    units = str(getattr(var, "units", "")).strip().lower().replace("µ", "u")
    if units in {"nm", "nanometer", "nanometers", "nanometre", "nanometres"}:
        return arr
    if units in {"um", "micron", "microns", "micrometer", "micrometers", "micrometre", "micrometres"}:
        return arr * 1000.0
    raise ValueError(f"unsupported wavelength units: {units!r}")


def spa_elevation(timestamp: pd.Timestamp) -> float:
    idx = pd.DatetimeIndex([timestamp.tz_convert("UTC")])
    result = pvlib.solarposition.spa_python(
        idx,
        latitude=SITE_LAT,
        longitude=SITE_LON,
        altitude=SITE_ALT_M,
        pressure=0.0,
        temperature=12.0,
        delta_t=None,
        how="numpy",
    )
    return float(result.iloc[0]["elevation"])


def refine_crossing(left: pd.Timestamp, right: pd.Timestamp, target: float) -> pd.Timestamp:
    f_left = spa_elevation(left) - target
    f_right = spa_elevation(right) - target
    if f_left == 0:
        return left
    if f_right == 0:
        return right
    if f_left * f_right > 0:
        raise ValueError("root bracket does not straddle target")
    for _ in range(45):
        mid_ns = (left.value + right.value) // 2
        if mid_ns == left.value or mid_ns == right.value:
            break
        mid = pd.Timestamp(mid_ns, tz="UTC")
        f_mid = spa_elevation(mid) - target
        if f_mid == 0:
            return mid
        if f_left * f_mid <= 0:
            right, f_right = mid, f_mid
        else:
            left, f_left = mid, f_mid
    return pd.Timestamp((left.value + right.value) // 2, tz="UTC")


def date_range_inclusive(start: dt.date, end: dt.date) -> Iterable[dt.date]:
    current = start
    while current <= end:
        yield current
        current += dt.timedelta(days=1)


def build_event_universe() -> list[Event]:
    events: list[Event] = []
    for local_date in date_range_inclusive(START_DATE, END_DATE):
        local_start = dt.datetime.combine(local_date, dt.time.min, tzinfo=LOCAL_TZ)
        local_end = local_start + dt.timedelta(days=1)
        start_utc = pd.Timestamp(local_start.astimezone(UTC))
        end_utc = pd.Timestamp(local_end.astimezone(UTC))
        grid = pd.date_range(start_utc, end_utc, freq="120s", inclusive="both")
        pos = pvlib.solarposition.spa_python(
            grid,
            latitude=SITE_LAT,
            longitude=SITE_LON,
            altitude=SITE_ALT_M,
            pressure=0.0,
            temperature=12.0,
            delta_t=None,
            how="numpy",
        )
        elevation = np.asarray(pos["elevation"], dtype=float)
        roots: dict[tuple[str, int], pd.Timestamp] = {}
        for target in TARGET_ELEVATIONS:
            f = elevation - target
            crossings: list[tuple[str, pd.Timestamp]] = []
            for i in range(len(grid) - 1):
                a, b = f[i], f[i + 1]
                if not (np.isfinite(a) and np.isfinite(b)):
                    continue
                if a == 0 or b == 0 or a * b < 0:
                    root = refine_crossing(grid[i], grid[i + 1], target)
                    direction = "dawn" if elevation[i + 1] > elevation[i] else "dusk"
                    crossings.append((direction, root))
            by_direction: dict[str, list[pd.Timestamp]] = {"dawn": [], "dusk": []}
            for direction, root in crossings:
                by_direction[direction].append(root)
            for direction in ("dawn", "dusk"):
                unique = sorted({int(x.value): x for x in by_direction[direction]}.values())
                if len(unique) != 1:
                    raise RuntimeError(
                        f"{local_date} target {target}: expected one {direction} crossing, got {len(unique)}"
                    )
                roots[(direction, int(abs(target)))] = unique[0]
        for direction in ("dawn", "dusk"):
            t8 = roots[(direction, 8)]
            t7 = roots[(direction, 7)]
            t6 = roots[(direction, 6)]
            if direction == "dawn" and not (t8 < t7 < t6):
                raise RuntimeError(f"unexpected dawn crossing order for {local_date}")
            if direction == "dusk" and not (t6 < t7 < t8):
                raise RuntimeError(f"unexpected dusk crossing order for {local_date}")
            case_id = f"{local_date.isoformat()}_{direction}"
            events.append(Event(
                case_id=case_id,
                local_civil_date=local_date.isoformat(),
                event=direction,
                t_minus8_utc=iso_utc(t8),
                t_minus7_utc=iso_utc(t7),
                t_minus6_utc=iso_utc(t6),
            ))
    if len(events) != 344:
        raise RuntimeError(f"expected 344 events, generated {len(events)}")
    return events


def write_event_universe(path: Path, events: list[Event]) -> None:
    fields = ["case_id", "local_civil_date", "event", "t_minus8_utc", "t_minus7_utc", "t_minus6_utc"]
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for event in events:
            writer.writerow(event.__dict__)


def index_vis_files(archive_root: Path) -> dict[str, list[Path]]:
    index: dict[str, list[Path]] = {}
    for path in archive_root.rglob("*"):
        if not path.is_file():
            continue
        match = FILE_RE.match(path.name)
        if match:
            index.setdefault(match.group(1), []).append(path)
    for paths in index.values():
        paths.sort()
    return index


def dates_needed(event: Event) -> list[str]:
    dates: set[str] = set()
    for text in (event.t_minus8_utc, event.t_minus7_utc, event.t_minus6_utc):
        center = dt.datetime.fromtimestamp(parse_utc(text), UTC)
        for shift in (-31, 0, 31):
            dates.add((center + dt.timedelta(seconds=shift)).strftime("%Y%m%d"))
    return sorted(dates)


def read_timing_file(path: Path) -> TimingFile:
    try:
        with netCDF4.Dataset(path, "r") as ds:
            times = decode_native_times(ds)
            if not times.size:
                return TimingFile(path, np.array([], dtype=float), None, "NO_DECODABLE_NATIVE_TIMESTAMPS")
            if "wavelength" not in ds.variables:
                return TimingFile(path, times, None, "MISSING_WAVELENGTH_COORDINATE")
            wavelength_nm = normalize_wavelength_nm(ds.variables["wavelength"])
            if wavelength_nm.size == 0 or not np.all(np.isfinite(wavelength_nm)):
                return TimingFile(path, times, None, "INVALID_WAVELENGTH_COORDINATE")
            return TimingFile(path, np.asarray(times, dtype=float), wavelength_nm, None)
    except Exception as exc:
        return TimingFile(path, np.array([], dtype=float), None, f"{type(exc).__name__}:{exc}")


def nearest_and_count(times: np.ndarray, center: float, half_window: float) -> tuple[float | None, int]:
    if not times.size:
        return None, 0
    delta = np.abs(times - center)
    return float(np.min(delta)), int(np.count_nonzero(delta <= half_window + 1e-9))


def exact_wavelength_grid(files: list[TimingFile]) -> np.ndarray:
    grids = [f.wavelength_nm for f in files if f.wavelength_nm is not None]
    if not grids:
        raise ValueError("NO_WAVELENGTH_GRID")
    reference = grids[0]
    for other in grids[1:]:
        if reference.shape != other.shape or not np.array_equal(reference, other):
            raise ValueError("WAVELENGTH_GRID_INCONSISTENT")
    return reference


def boolean_validity_for_file(path: Path, target_pixel: int, centers: dict[str, float]) -> dict[str, dict[float, bool]]:
    """Return timestamp->valid booleans only; never return a radiance magnitude."""
    result = {name: {} for name in centers}
    with netCDF4.Dataset(path, "r") as ds:
        times = decode_native_times(ds)
        if not times.size:
            return result
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
        for name, center in centers.items():
            indices = np.flatnonzero(np.abs(times - center) <= 30.0 + 1e-9)
            if indices.size == 0:
                continue
            if time_axis == 0:
                subset = np.ma.asarray(var[indices, target_pixel])
            else:
                subset = np.ma.asarray(var[target_pixel, indices])
            mask = np.ma.getmaskarray(subset).reshape(-1)
            raw = np.asarray(np.ma.getdata(subset)).reshape(-1)
            finite = np.isfinite(raw)
            valid = np.logical_and(~mask, finite)
            del raw, subset, mask, finite
            for idx, ok in zip(indices.tolist(), valid.tolist()):
                result[name][float(times[idx])] = bool(ok)
    return result


def merge_validity(dest: dict[str, dict[float, bool]], src: dict[str, dict[float, bool]]) -> None:
    for anchor, samples in src.items():
        for timestamp, valid in samples.items():
            dest[anchor][timestamp] = bool(dest[anchor].get(timestamp, False) or valid)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def audit_event(event: Event, archive_root: Path, file_index: dict[str, list[Path]]) -> dict[str, Any]:
    source_paths: list[Path] = []
    for date_key in dates_needed(event):
        source_paths.extend(file_index.get(date_key, []))
    source_paths = sorted(set(source_paths))
    centers = {
        "minus8": parse_utc(event.t_minus8_utc),
        "minus7": parse_utc(event.t_minus7_utc),
        "minus6": parse_utc(event.t_minus6_utc),
    }
    row: dict[str, Any] = {
        **event.__dict__,
        "source_files": ";".join(str(p.relative_to(archive_root)) for p in source_paths),
        "source_file_count": len(source_paths),
        "read_errors": "",
        "target_wavelength_nm_requested": f"{TARGET_WAVELENGTH_NM:.6f}",
        "target_pixel_index": "",
        "target_pixel_wavelength_nm": "",
        "timing_pass": False,
        "validity_pass": False,
        "firewall_status": KNOWN_EXPOSED.get(event.case_id, "BLIND_ELIGIBLE"),
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

    timing_files = [read_timing_file(p) for p in source_paths]
    errors = [f"{f.path.name}:{f.error}" for f in timing_files if f.error]
    if errors:
        row["read_errors"] = " | ".join(errors)
        row["disposition"] = "UNREADABLE_OR_UNDECODABLE"
        return row

    all_times = np.unique(np.concatenate([f.times for f in timing_files if f.times.size]))
    if not all_times.size:
        row["disposition"] = "NO_NATIVE_TIMESTAMPS"
        return row

    timing_pass = True
    for name, center in centers.items():
        nearest, count5 = nearest_and_count(all_times, center, 5.0)
        _, count30 = nearest_and_count(all_times, center, 30.0)
        row[f"nearest_{name}_s"] = "" if nearest is None else f"{nearest:.6f}"
        row[f"samples_within_5s_{name}"] = count5
        row[f"samples_within_30s_{name}"] = count30
        if count5 < 1 or count30 < 10:
            timing_pass = False
    row["timing_pass"] = timing_pass
    if not timing_pass:
        row["disposition"] = "G0_V2_TIMING_FAIL"
        return row

    try:
        grid = exact_wavelength_grid(timing_files)
    except Exception as exc:
        row["read_errors"] = str(exc)
        row["disposition"] = "G0_V2_WAVELENGTH_UNRESOLVED"
        return row
    pixel = int(np.argmin(np.abs(grid - TARGET_WAVELENGTH_NM)))
    pixel_wavelength = float(grid[pixel])
    row["target_pixel_index"] = pixel
    row["target_pixel_wavelength_nm"] = f"{pixel_wavelength:.9f}"

    validity: dict[str, dict[float, bool]] = {name: {} for name in centers}
    try:
        for path in source_paths:
            merge_validity(validity, boolean_validity_for_file(path, pixel, centers))
    except Exception as exc:
        row["read_errors"] = f"{type(exc).__name__}:{exc}"
        row["disposition"] = "G0_V2_VALIDITY_UNREADABLE"
        return row

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

    if event.case_id in KNOWN_EXPOSED:
        row["disposition"] = "EXPOSED_DEVELOPMENT_ONLY"
        return row

    row["primary_holdout_eligible_after_g0"] = True
    row["disposition"] = "G0_V2_PASS_BLIND_CANDIDATE"
    return row


OUTPUT_FIELDS = [
    "case_id", "local_civil_date", "event", "t_minus8_utc", "t_minus7_utc", "t_minus6_utc",
    "source_files", "source_file_count", "nearest_minus8_s", "nearest_minus7_s", "nearest_minus6_s",
    "samples_within_5s_minus8", "samples_within_5s_minus7", "samples_within_5s_minus6",
    "samples_within_30s_minus8", "samples_within_30s_minus7", "samples_within_30s_minus6",
    "timing_pass", "target_wavelength_nm_requested", "target_pixel_index", "target_pixel_wavelength_nm",
    "valid_464_samples_within_30s_minus8", "valid_464_samples_within_30s_minus7",
    "valid_464_samples_within_30s_minus6", "validity_pass", "firewall_status",
    "primary_holdout_eligible_after_g0", "read_errors", "disposition",
]


def write_audit(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=OUTPUT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_summary(path: Path, events_path: Path, audit_path: Path, rows: list[dict[str, Any]]) -> None:
    counts: dict[str, int] = {}
    for row in rows:
        d = str(row["disposition"])
        counts[d] = counts.get(d, 0) + 1
    blind_candidates = [str(r["case_id"]) for r in rows if r["disposition"] == "G0_V2_PASS_BLIND_CANDIDATE"]
    exposed = [str(r["case_id"]) for r in rows if r["disposition"] == "EXPOSED_DEVELOPMENT_ONLY"]
    summary = {
        "protocol": PROTOCOL,
        "control_comment": CONTROL_COMMENT,
        "site": {"latitude_deg": SITE_LAT, "longitude_deg": SITE_LON, "altitude_m": SITE_ALT_M},
        "date_universe": {"start": START_DATE.isoformat(), "end": END_DATE.isoformat(), "events": len(rows)},
        "solar_geometry": {
            "implementation": "pvlib.solarposition.spa_python / NREL SPA",
            "pvlib_version": pvlib.__version__,
            "coordinate": "geometric topocentric solar-center elevation",
            "output_column": "elevation",
            "pressure_pa": 0.0,
            "refraction": "disabled / not used",
            "delta_t": "pvlib spa.calculate_deltat via delta_t=None",
        },
        "g0_v2": {
            "stream": STREAM,
            "anchor_elevations_deg": [-8.0, -7.0, -6.0],
            "minimum_samples_within_5s_each_anchor": 1,
            "minimum_samples_within_30s_each_anchor": 10,
            "target_wavelength_nm": TARGET_WAVELENGTH_NM,
            "minimum_valid_target_pixel_samples_within_30s_each_anchor": 5,
            "radiance_magnitudes_opened": False,
        },
        "known_exposed_primary_exclusions": KNOWN_EXPOSED,
        "counts_by_disposition": dict(sorted(counts.items())),
        "blind_g0_v2_candidates": blind_candidates,
        "exposed_development_only_that_otherwise_reached_final_g0_state": exposed,
        "events_csv_sha256": sha256_file(events_path),
        "audit_csv_sha256": sha256_file(audit_path),
        "next_state": (
            "HALT_ARM_SASZE_V2_NO_ANCHOR_SUPPORTED_PRIMARY_EVENT"
            if not blind_candidates
            else "PROCEED_TO_INDEPENDENT_ATMOSPHERE_CLOUD_MOON_RANKING"
        ),
    }
    path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    archive_root = args.archive_root.resolve()
    if not archive_root.is_dir():
        raise SystemExit(f"archive root is not a directory: {archive_root}")
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    events = build_event_universe()
    events_path = output_dir / "arm_sgp_v2_exact_event_universe.csv"
    audit_path = output_dir / "arm_sgp_v2_sasze_anchor_support_audit.csv"
    summary_path = output_dir / "arm_sgp_v2_sasze_anchor_support_summary.json"
    write_event_universe(events_path, events)

    file_index = index_vis_files(archive_root)
    rows = [audit_event(event, archive_root, file_index) for event in events]
    write_audit(audit_path, rows)
    write_summary(summary_path, events_path, audit_path, rows)
    print(summary_path.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
