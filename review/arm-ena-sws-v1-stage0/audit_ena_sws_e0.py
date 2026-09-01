#!/usr/bin/env python3
"""Result-blind ARM ENA/SWS Stage-0 E0 structural/timing audit.

Frozen control: issue #60 comment 5487647692.

HOLDOUT FIREWALL
----------------
This program NEVER reads SWS radiance/signal/count/intensity/brightness values.
It may read native time and wavelength coordinates, source metadata/hashes, and
integer QC/QA fields that are structurally separate from protected photometric
arrays. If sample validity cannot be established from such a non-photometric
QC field, the event fails closed instead of reading the radiance value to learn
whether it is fill/missing.
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
from typing import Any, Iterable
from zoneinfo import ZoneInfo

import netCDF4
import numpy as np
import pandas as pd
import pvlib

UTC = dt.timezone.utc
LOCAL_TZ = ZoneInfo("Atlantic/Azores")
SITE_LAT = 39.0916
SITE_LON = -28.0257
SITE_ALT_M = 30.0
START_DATE = dt.date(2017, 4, 5)
END_DATE = dt.date(2019, 9, 27)
EXPECTED_EVENTS = 906
TARGET_ELEVATIONS = (-8.0, -7.0, -6.0)
TARGET_WAVELENGTH_NM = 550.0
PROTOCOL = "ARM_ENA_SWS_V1_STAGE0_E0_RESULT_BLIND"
CONTROL_COMMENT = "5487647692"
SWS_RE = re.compile(r"^enaswsC1\.b1\.(\d{8})\..*\.(?:nc|cdf)$", re.I)
SWS_AUX_RE = re.compile(r"^enaswsauxC1\.b1\.(\d{8})\..*\.(?:nc|cdf)$", re.I)
PROTECTED_RE = re.compile(
    r"(?:radiance|irradiance|luminance|brightness|intensity|signal|counts?|spectra|spectrum)", re.I
)
QC_NAME_RE = re.compile(r"^(?:qc_|quality_|qa_)", re.I)
QC_TEXT_RE = re.compile(r"(?:quality|qc\b|qa\b|validity|data[_ ]?quality)", re.I)


@dataclass(frozen=True)
class Event:
    case_id: str
    local_civil_date: str
    event: str
    t_minus8_utc: str
    t_minus7_utc: str
    t_minus6_utc: str


def dates(start: dt.date, end: dt.date) -> Iterable[dt.date]:
    cur = start
    while cur <= end:
        yield cur
        cur += dt.timedelta(days=1)


def iso_utc(value: pd.Timestamp | dt.datetime | float) -> str:
    if isinstance(value, (int, float, np.floating)):
        x = dt.datetime.fromtimestamp(float(value), UTC)
    else:
        x = value.to_pydatetime() if isinstance(value, pd.Timestamp) else value
        if x.tzinfo is None:
            x = x.replace(tzinfo=UTC)
        x = x.astimezone(UTC)
    return x.isoformat(timespec="microseconds").replace("+00:00", "Z")


def parse_utc(text: str) -> float:
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    x = dt.datetime.fromisoformat(text)
    if x.tzinfo is None:
        x = x.replace(tzinfo=UTC)
    return x.astimezone(UTC).timestamp()


def decoded_datetime(value: Any) -> dt.datetime:
    return dt.datetime(
        int(value.year), int(value.month), int(value.day), int(value.hour),
        int(value.minute), int(value.second), int(getattr(value, "microsecond", 0)), tzinfo=UTC,
    )


def spa_elevation(timestamp: pd.Timestamp) -> float:
    result = pvlib.solarposition.spa_python(
        pd.DatetimeIndex([timestamp.tz_convert("UTC")]),
        latitude=SITE_LAT, longitude=SITE_LON, altitude=SITE_ALT_M,
        pressure=0.0, temperature=12.0, delta_t=None, how="numpy",
    )
    return float(result.iloc[0]["elevation"])


def refine_crossing(left: pd.Timestamp, right: pd.Timestamp, target: float) -> pd.Timestamp:
    fl = spa_elevation(left) - target
    fr = spa_elevation(right) - target
    if fl * fr > 0:
        raise ValueError("root bracket does not straddle target")
    for _ in range(45):
        mid_ns = (left.value + right.value) // 2
        if mid_ns in (left.value, right.value):
            break
        mid = pd.Timestamp(mid_ns, tz="UTC")
        fm = spa_elevation(mid) - target
        if fl * fm <= 0:
            right, fr = mid, fm
        else:
            left, fl = mid, fm
    return pd.Timestamp((left.value + right.value) // 2, tz="UTC")


def build_events() -> list[Event]:
    out: list[Event] = []
    for local_date in dates(START_DATE, END_DATE):
        local_start = dt.datetime.combine(local_date, dt.time.min, tzinfo=LOCAL_TZ)
        local_end = local_start + dt.timedelta(days=1)
        grid = pd.date_range(
            pd.Timestamp(local_start.astimezone(UTC)),
            pd.Timestamp(local_end.astimezone(UTC)),
            freq="120s", inclusive="both",
        )
        pos = pvlib.solarposition.spa_python(
            grid, latitude=SITE_LAT, longitude=SITE_LON, altitude=SITE_ALT_M,
            pressure=0.0, temperature=12.0, delta_t=None, how="numpy",
        )
        elev = np.asarray(pos["elevation"], dtype=float)
        roots: dict[int, pd.Timestamp] = {}
        for target in TARGET_ELEVATIONS:
            f = elev - target
            candidates: list[pd.Timestamp] = []
            for i in range(len(grid) - 1):
                if not (np.isfinite(f[i]) and np.isfinite(f[i + 1])):
                    continue
                if elev[i + 1] >= elev[i]:
                    continue
                if f[i] == 0 or f[i + 1] == 0 or f[i] * f[i + 1] < 0:
                    candidates.append(refine_crossing(grid[i], grid[i + 1], target))
            unique = sorted({int(x.value): x for x in candidates}.values())
            if len(unique) != 1:
                raise RuntimeError(f"{local_date} target {target}: expected one dusk crossing, got {len(unique)}")
            roots[int(abs(target))] = unique[0]
        t8, t7, t6 = roots[8], roots[7], roots[6]
        if not (t6 < t7 < t8):
            raise RuntimeError(f"unexpected dusk order for {local_date}")
        out.append(Event(
            f"{local_date.isoformat()}_dusk", local_date.isoformat(), "dusk",
            iso_utc(t8), iso_utc(t7), iso_utc(t6),
        ))
    if len(out) != EXPECTED_EVENTS:
        raise RuntimeError(f"expected {EXPECTED_EVENTS} events, generated {len(out)}")
    return out


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def decode_times(ds: netCDF4.Dataset) -> np.ndarray:
    """One epoch-second slot per native row; invalid slots remain NaN."""
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
                vals = netCDF4.num2date(data[good], units=units, calendar=getattr(var, "calendar", "standard"))
                out[good] = [decoded_datetime(x).timestamp() for x in vals]
            return out
    if "base_time" in ds.variables and "time_offset" in ds.variables:
        base = np.ma.asarray(ds.variables["base_time"][:]).squeeze()
        if np.asarray(np.ma.getmaskarray(base)).any():
            return np.array([], dtype=float)
        base_value = float(np.asarray(np.ma.getdata(base)).squeeze())
        off = np.ma.asarray(ds.variables["time_offset"][:]).reshape(-1)
        data = np.asarray(np.ma.getdata(off), dtype=float).reshape(-1)
        mask = np.asarray(np.ma.getmaskarray(off), dtype=bool).reshape(-1) | ~np.isfinite(data)
        out = np.full(data.shape, np.nan, dtype=float)
        good = ~mask
        out[good] = base_value + data[good]
        return out
    return np.array([], dtype=float)


def wavelength_name(ds: netCDF4.Dataset) -> str | None:
    if "wavelength" in ds.variables:
        return "wavelength"
    found: list[str] = []
    for name, var in ds.variables.items():
        text = " ".join(str(getattr(var, a, "")) for a in ("standard_name", "long_name", "description"))
        if re.search(r"\bwavelength\b", text, re.I):
            found.append(name)
    return found[0] if len(found) == 1 else None


def wavelength_nm(var: netCDF4.Variable) -> np.ndarray:
    raw = np.ma.asarray(var[:])
    if raw.ndim != 1:
        raise ValueError(f"WAVELENGTH_NOT_1D:{raw.shape}")
    raw = raw.reshape(-1)
    if np.asarray(np.ma.getmaskarray(raw), dtype=bool).any():
        raise ValueError("MASKED_WAVELENGTH_COORDINATE")
    arr = np.asarray(np.ma.getdata(raw), dtype=float).reshape(-1)
    if arr.size == 0 or not np.all(np.isfinite(arr)):
        raise ValueError("INVALID_WAVELENGTH_COORDINATE")
    units = str(getattr(var, "units", "")).strip().lower().replace("µ", "u")
    if units in {"nm", "nanometer", "nanometers", "nanometre", "nanometres"}:
        return arr
    if units in {"um", "micron", "microns", "micrometer", "micrometers", "micrometre", "micrometres"}:
        return arr * 1000.0
    raise ValueError(f"UNSUPPORTED_WAVELENGTH_UNITS:{units!r}")


def semantic_text(name: str, var: netCDF4.Variable) -> str:
    return " ".join([name] + [str(getattr(var, a, "")) for a in ("long_name", "standard_name", "description", "comment", "units")])


def protected(name: str, var: netCDF4.Variable) -> bool:
    if QC_NAME_RE.search(name):
        return False
    return bool(PROTECTED_RE.search(semantic_text(name, var)))


def safe_qc(name: str, var: netCDF4.Variable) -> bool:
    if protected(name, var):
        return False
    text = semantic_text(name, var)
    if not (QC_NAME_RE.search(name) or QC_TEXT_RE.search(text)):
        return False
    return np.issubdtype(np.dtype(var.dtype), np.integer)


def index_files(root: Path, pattern: re.Pattern[str]) -> dict[str, list[Path]]:
    out: dict[str, list[Path]] = {}
    for path in root.rglob("*"):
        if path.is_file():
            m = pattern.match(path.name)
            if m:
                out.setdefault(m.group(1), []).append(path)
    for paths in out.values():
        paths.sort()
    return out


def needed_dates(event: Event) -> list[str]:
    out: set[str] = set()
    for text in (event.t_minus8_utc, event.t_minus7_utc, event.t_minus6_utc):
        center = dt.datetime.fromtimestamp(parse_utc(text), UTC)
        for shift in (-31, 0, 31):
            out.add((center + dt.timedelta(seconds=shift)).strftime("%Y%m%d"))
    return sorted(out)


def nearest_count(times: np.ndarray, center: float, window: float) -> tuple[float | None, int]:
    times = times[np.isfinite(times)]
    if not times.size:
        return None, 0
    delta = np.abs(times - center)
    return float(np.min(delta)), int(np.count_nonzero(delta <= window + 1e-9))


def qc_good(var: netCDF4.Variable, indices: np.ndarray, pixel: int, ntime: int, nwave: int) -> np.ndarray | None:
    dims = tuple(var.dimensions)
    if "time" not in dims or var.shape[dims.index("time")] != ntime:
        return None
    if dims == ("time",):
        subset = np.ma.asarray(var[indices]).reshape(-1)
    elif len(dims) == 2 and "wavelength" in dims:
        ta, wa = dims.index("time"), dims.index("wavelength")
        if var.shape[wa] != nwave:
            return None
        subset = np.ma.asarray(var[indices, pixel] if ta == 0 else var[pixel, indices]).reshape(-1)
    else:
        return None
    mask = np.asarray(np.ma.getmaskarray(subset), dtype=bool).reshape(-1)
    data = np.asarray(np.ma.getdata(subset)).reshape(-1)
    return (~mask) & (data == 0)


def file_validity(path: Path, centers: dict[str, float]) -> tuple[dict[str, dict[float, bool]], dict[str, Any]]:
    result: dict[str, dict[float, bool]] = {k: {} for k in centers}
    meta: dict[str, Any] = {"pixel": None, "wavelength_nm": None, "qc": [], "resolved": False, "reason": ""}
    with netCDF4.Dataset(path, "r") as ds:
        times = decode_times(ds)
        wname = wavelength_name(ds)
        if not times.size:
            meta["reason"] = "NO_NATIVE_TIME_AXIS"
            return result, meta
        if not wname:
            meta["reason"] = "NO_UNAMBIGUOUS_WAVELENGTH_COORDINATE"
            return result, meta
        grid = wavelength_nm(ds.variables[wname])
        pixel = int(np.argmin(np.abs(grid - TARGET_WAVELENGTH_NM)))
        meta["pixel"] = pixel
        meta["wavelength_nm"] = float(grid[pixel])
        qcs = [(name, var) for name, var in ds.variables.items() if safe_qc(name, var)]
        qcs = [(n, v) for n, v in qcs if tuple(v.dimensions) == ("time",) or (len(v.dimensions) == 2 and "time" in v.dimensions and "wavelength" in v.dimensions)]
        if not qcs:
            meta["reason"] = "NO_SAFE_QC_LAYOUT_FOR_NATIVE_SAMPLE_VALIDITY"
            return result, meta
        meta["qc"] = [n for n, _ in qcs]
        for anchor, center in centers.items():
            idx = np.flatnonzero(np.isfinite(times) & (np.abs(times - center) <= 30.0 + 1e-9))
            if not idx.size:
                continue
            masks = [m for _, var in qcs if (m := qc_good(var, idx, pixel, times.size, grid.size)) is not None]
            if not masks:
                continue
            good = np.logical_and.reduce(masks)
            for i, ok in zip(idx.tolist(), good.tolist()):
                stamp = float(times[i])
                result[anchor][stamp] = bool(result[anchor].get(stamp, False) or bool(ok))
        meta["resolved"] = True
    return result, meta


def merge(dest: dict[str, dict[float, bool]], src: dict[str, dict[float, bool]]) -> None:
    for anchor, samples in src.items():
        for stamp, ok in samples.items():
            dest[anchor][stamp] = bool(dest[anchor].get(stamp, False) or ok)


def audit(event: Event, root: Path, index: dict[str, list[Path]]) -> dict[str, Any]:
    centers = {"minus8": parse_utc(event.t_minus8_utc), "minus7": parse_utc(event.t_minus7_utc), "minus6": parse_utc(event.t_minus6_utc)}
    paths: list[Path] = []
    for d in needed_dates(event):
        paths.extend(index.get(d, []))
    paths = sorted(set(paths))
    row: dict[str, Any] = {
        **event.__dict__, "source_file_count": len(paths),
        "source_files": ";".join(str(p.relative_to(root)) for p in paths),
        "source_sha256": ";".join(f"{p.name}|{sha256_file(p)}" for p in paths),
        "target_wavelength_nm_requested": TARGET_WAVELENGTH_NM,
        "target_pixel_map": "", "qc_variables_used": "",
        "timing_pass": False, "validity_resolved_without_photometric_values": False,
        "validity_pass": False, "primary_holdout_eligible_after_e0": False,
        "disposition": "", "read_errors": "",
    }
    for a in centers:
        row[f"nearest_{a}_s"] = ""
        row[f"samples_within_5s_{a}"] = 0
        row[f"samples_within_30s_{a}"] = 0
        row[f"safe_qc_valid_samples_within_30s_{a}"] = ""
    if not paths:
        row["disposition"] = "SOURCE_FILE_MISSING"
        return row

    arrays: list[np.ndarray] = []
    try:
        for path in paths:
            with netCDF4.Dataset(path, "r") as ds:
                t = decode_times(ds)
            if not t.size or not np.isfinite(t).any():
                raise ValueError(f"{path.name}:NO_DECODABLE_NATIVE_TIMESTAMPS")
            arrays.append(t[np.isfinite(t)])
    except Exception as exc:
        row["read_errors"] = f"{type(exc).__name__}:{exc}"
        row["disposition"] = "UNREADABLE_OR_UNDECODABLE"
        return row

    all_times = np.unique(np.concatenate(arrays))
    timing_ok = True
    for a, center in centers.items():
        nearest, c5 = nearest_count(all_times, center, 5.0)
        _, c30 = nearest_count(all_times, center, 30.0)
        row[f"nearest_{a}_s"] = "" if nearest is None else f"{nearest:.6f}"
        row[f"samples_within_5s_{a}"] = c5
        row[f"samples_within_30s_{a}"] = c30
        timing_ok &= c5 >= 1 and c30 >= 10
    row["timing_pass"] = bool(timing_ok)
    if not timing_ok:
        row["disposition"] = "E0_TIMING_FAIL"
        return row

    validity: dict[str, dict[float, bool]] = {k: {} for k in centers}
    pixels: list[str] = []
    qc_names: set[str] = set()
    resolved = True
    try:
        for path in paths:
            partial, meta = file_validity(path, centers)
            merge(validity, partial)
            if meta["pixel"] is not None:
                pixels.append(f"{path.name}|{meta['pixel']}|{float(meta['wavelength_nm']):.9f}")
            qc_names.update(meta["qc"])
            with netCDF4.Dataset(path, "r") as ds:
                t = decode_times(ds)
            contributes = any(np.count_nonzero(np.isfinite(t) & (np.abs(t - c) <= 30.0 + 1e-9)) for c in centers.values())
            if contributes and not meta["resolved"]:
                resolved = False
    except Exception as exc:
        row["read_errors"] = f"{type(exc).__name__}:{exc}"
        row["disposition"] = "E0_VALIDITY_UNREADABLE"
        return row
    row["target_pixel_map"] = ";".join(pixels)
    row["qc_variables_used"] = ";".join(sorted(qc_names))
    row["validity_resolved_without_photometric_values"] = resolved
    if not resolved:
        row["disposition"] = "E0_VALIDITY_UNRESOLVED_NO_SAFE_QC"
        return row

    validity_ok = True
    for a in centers:
        count = sum(bool(x) for x in validity[a].values())
        row[f"safe_qc_valid_samples_within_30s_{a}"] = count
        validity_ok &= count >= 5
    row["validity_pass"] = bool(validity_ok)
    if not validity_ok:
        row["disposition"] = "E0_SAFE_QC_VALIDITY_FAIL"
        return row
    row["primary_holdout_eligible_after_e0"] = True
    row["disposition"] = "E0_PASS_BLIND_CANDIDATE"
    return row


def schema_report(root: Path, indices: list[tuple[str, dict[str, list[Path]]]]) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for kind, index in indices:
        seen: set[tuple[str, str]] = set()
        for day in sorted(index):
            for path in index[day]:
                try:
                    with netCDF4.Dataset(path, "r") as ds:
                        key = (str(getattr(ds, "dod_version", "")), str(getattr(ds, "process_version", "")))
                        if key in seen:
                            continue
                        seen.add(key)
                        vars_out = []
                        for name, var in ds.variables.items():
                            vars_out.append({
                                "name": name, "dtype": str(var.dtype), "dimensions": list(var.dimensions),
                                "shape": list(var.shape), "protected_photometric_values": protected(name, var),
                                "safe_qc_values_allowed": safe_qc(name, var),
                                "long_name": str(getattr(var, "long_name", "")),
                                "standard_name": str(getattr(var, "standard_name", "")),
                                "units": str(getattr(var, "units", "")),
                            })
                        records.append({
                            "kind": kind, "source_file": str(path.relative_to(root)), "source_sha256": sha256_file(path),
                            "dod_version": key[0], "process_version": key[1], "variables": vars_out,
                            "protected_variable_values_read": False,
                        })
                except Exception as exc:
                    records.append({"kind": kind, "source_file": str(path.relative_to(root)), "error": f"{type(exc).__name__}:{exc}", "protected_variable_values_read": False})
    return {"schema": 1, "protocol": PROTOCOL, "control_comment": CONTROL_COMMENT, "records": records, "protected_variable_values_read": False}


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive-root", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--events-only", action="store_true")
    args = ap.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    events = build_events()
    write_csv(args.output_dir / "ena_sws_e0_event_universe.csv", [e.__dict__ for e in events])
    if args.events_only:
        print(json.dumps({"event_count": len(events), "protected_variable_values_read": False}))
        return 0

    root = args.archive_root.resolve()
    sws = index_files(root, SWS_RE)
    aux = index_files(root, SWS_AUX_RE)
    (args.output_dir / "ena_sws_e0_schema_report.json").write_text(
        json.dumps(schema_report(root, [("sws", sws), ("swsaux", aux)]), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    rows = [audit(e, root, sws) for e in events]
    write_csv(args.output_dir / "ena_sws_e0_gate_ledger.csv", rows)
    dispositions: dict[str, int] = {}
    for row in rows:
        d = str(row["disposition"]); dispositions[d] = dispositions.get(d, 0) + 1
    summary = {
        "schema": 1, "protocol": PROTOCOL, "control_comment": CONTROL_COMMENT,
        "candidate_event_count": len(events),
        "sws_native_file_count": sum(len(x) for x in sws.values()),
        "swsaux_native_file_count": sum(len(x) for x in aux.values()),
        "disposition_counts": dispositions,
        "protected_variable_values_read": False, "stage_b_authorized": False,
    }
    (args.output_dir / "ena_sws_e0_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
