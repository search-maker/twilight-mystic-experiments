#!/usr/bin/env python3
"""Fetch a frozen NOAA HRRR-Smoke vertical diagnostic for Ann Arbor.

This script intentionally does not read Taylor SQM observations or any MYSTIC
outputs.  It retrieves only independent NOAA HRRR fields selected from the
public GRIB2 index metadata frozen in freeze.json.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import numpy as np
import pygrib
import requests

ROOT = Path(__file__).resolve().parent
FREEZE = json.loads((ROOT / "freeze.json").read_text(encoding="utf-8"))
OUT = ROOT / "output"
OUT.mkdir(parents=True, exist_ok=True)

LAT = float(FREEZE["site"]["latitude_deg"])
LON = float(FREEZE["site"]["longitude_deg"])
DATE = "20250808"
BASE = f"https://noaa-hrrr-bdp-pds.s3.amazonaws.com/hrrr.{DATE}/conus"
PRODUCT_STEM = {
    "nat": "wrfnatf00",
    "prs": "wrfprsf00",
    "sfc": "wrfsfcf00",
}
TARGET_VARS = {"MASSDEN", "HGT", "PRES", "AOTK", "COLMD"}
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "twilight-mystic-experiments-hrrr-profile-v1"})


@dataclass(frozen=True)
class IdxRecord:
    message_number: int
    start: int
    end: int | None
    raw: str
    variable: str
    level_desc: str


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch_text(url: str) -> str:
    r = SESSION.get(url, timeout=60)
    r.raise_for_status()
    return r.text


def parse_idx(text: str) -> list[IdxRecord]:
    rows = []
    prelim = []
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split(":")
        if len(parts) < 5:
            continue
        try:
            message_number = int(parts[0])
            start = int(parts[1])
        except ValueError:
            continue
        variable = parts[3].strip()
        level_desc = parts[4].strip()
        prelim.append((message_number, start, line, variable, level_desc))
    for i, item in enumerate(prelim):
        next_start = prelim[i + 1][1] if i + 1 < len(prelim) else None
        end = next_start - 1 if next_start is not None else None
        rows.append(IdxRecord(item[0], item[1], end, item[2], item[3], item[4]))
    return rows


def head_size(url: str) -> int:
    r = SESSION.head(url, timeout=60)
    r.raise_for_status()
    return int(r.headers["Content-Length"])


def fetch_message(url: str, rec: IdxRecord, file_size: int) -> bytes:
    end = rec.end if rec.end is not None else file_size - 1
    headers = {"Range": f"bytes={rec.start}-{end}"}
    r = SESSION.get(url, headers=headers, timeout=120)
    r.raise_for_status()
    if r.status_code != 206:
        raise RuntimeError(f"Range request was not honored for {url}: HTTP {r.status_code}")
    return r.content


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0088
    p1 = np.deg2rad(lat1)
    p2 = np.deg2rad(lat2)
    dp = p2 - p1
    dl = np.deg2rad(((lon2 - lon1 + 180.0) % 360.0) - 180.0)
    a = np.sin(dp / 2.0) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2.0) ** 2
    return 2.0 * r * np.arcsin(np.sqrt(a))


def open_grib_message(data: bytes):
    fd, name = tempfile.mkstemp(suffix=".grib2")
    os.close(fd)
    try:
        Path(name).write_bytes(data)
        handle = pygrib.open(name)
        try:
            msg = handle.message(1)
            # Materialize key values before closing the backing file.
            return msg, handle, name
        except Exception:
            handle.close()
            raise
    except Exception:
        try:
            os.unlink(name)
        except FileNotFoundError:
            pass
        raise


def safe_key(msg, key, default=None):
    try:
        return msg[key]
    except Exception:
        return default


def standard_altitude_m_from_pressure_hpa(p_hpa: float) -> float | None:
    if not (p_hpa and p_hpa > 0):
        return None
    # ISA tropospheric approximation; diagnostic fallback only.
    return 44330.0 * (1.0 - (p_hpa / 1013.25) ** 0.190263)


def should_extract(rec: IdxRecord, mass_levels: set[str]) -> bool:
    if rec.variable in {"AOTK", "COLMD"}:
        return True
    if rec.variable == "MASSDEN":
        return True
    if rec.variable in {"HGT", "PRES"} and rec.level_desc in mass_levels:
        return True
    return False


def cycle_hour(valid_time: str) -> str:
    return datetime.fromisoformat(valid_time.replace("Z", "+00:00")).strftime("%H")


def main() -> None:
    provenance = {
        "freeze_sha256": hashlib.sha256((ROOT / "freeze.json").read_bytes()).hexdigest(),
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "base": BASE,
        "site": FREEZE["site"],
        "valid_times_utc": FREEZE["valid_times_utc"],
        "selection_rule": "All MASSDEN records; HGT/PRES records on exactly matching level descriptions; all AOTK/COLMD records. No Taylor/MYSTIC values consulted.",
        "files": [],
    }
    inventory_rows: list[dict] = []
    point_rows: list[dict] = []

    for valid_time in FREEZE["valid_times_utc"]:
        hh = cycle_hour(valid_time)
        for product, stem in PRODUCT_STEM.items():
            filename = f"hrrr.t{hh}z.{stem}.grib2"
            grib_url = f"{BASE}/{filename}"
            idx_url = grib_url + ".idx"
            try:
                idx_text = fetch_text(idx_url)
            except Exception as exc:
                provenance["files"].append({
                    "valid_time_utc": valid_time,
                    "product": product,
                    "filename": filename,
                    "idx_url": idx_url,
                    "status": "IDX_FETCH_FAILED",
                    "error": repr(exc),
                })
                continue

            idx_path = OUT / f"{valid_time[11:13]}Z_{product}.idx"
            idx_path.write_text(idx_text, encoding="utf-8")
            records = parse_idx(idx_text)
            mass_levels = {r.level_desc for r in records if r.variable == "MASSDEN"}
            selected = [r for r in records if should_extract(r, mass_levels)]

            for r in records:
                if r.variable in TARGET_VARS:
                    inventory_rows.append({
                        "valid_time_utc": valid_time,
                        "product": product,
                        "message_number": r.message_number,
                        "start_byte": r.start,
                        "end_byte": r.end,
                        "variable": r.variable,
                        "level_desc": r.level_desc,
                        "selected_for_point_extraction": int(r in selected),
                        "raw_index_line": r.raw,
                    })

            if not selected:
                provenance["files"].append({
                    "valid_time_utc": valid_time,
                    "product": product,
                    "filename": filename,
                    "idx_url": idx_url,
                    "idx_sha256": sha256_bytes(idx_text.encode()),
                    "status": "NO_SELECTED_MESSAGES",
                })
                continue

            try:
                file_size = head_size(grib_url)
            except Exception as exc:
                provenance["files"].append({
                    "valid_time_utc": valid_time,
                    "product": product,
                    "filename": filename,
                    "idx_url": idx_url,
                    "idx_sha256": sha256_bytes(idx_text.encode()),
                    "status": "GRIB_HEAD_FAILED",
                    "error": repr(exc),
                })
                continue

            nearest_ij = None
            nearest_latlon = None
            selected_manifest = []
            for rec in selected:
                try:
                    data = fetch_message(grib_url, rec, file_size)
                    msg, handle, temp_name = open_grib_message(data)
                    try:
                        if nearest_ij is None:
                            lats, lons = msg.latlons()
                            d = haversine_km(LAT, LON, lats, lons)
                            flat = int(np.nanargmin(d))
                            nearest_ij = np.unravel_index(flat, d.shape)
                            nearest_latlon = (
                                float(lats[nearest_ij]),
                                float(lons[nearest_ij]),
                                float(d[nearest_ij]),
                            )
                        i, j = nearest_ij
                        values = msg.values
                        value = float(values[i, j])
                        type_of_level = str(safe_key(msg, "typeOfLevel", ""))
                        level = safe_key(msg, "level", None)
                        try:
                            level_num = float(level) if level is not None else None
                        except Exception:
                            level_num = None
                        approx_alt_m = None
                        if type_of_level == "isobaricInhPa" and level_num is not None:
                            approx_alt_m = standard_altitude_m_from_pressure_hpa(level_num)
                        row = {
                            "valid_time_utc": valid_time,
                            "product": product,
                            "variable_from_idx": rec.variable,
                            "level_desc_from_idx": rec.level_desc,
                            "message_number": rec.message_number,
                            "grib_short_name": str(safe_key(msg, "shortName", "")),
                            "grib_name": str(safe_key(msg, "name", "")),
                            "units": str(safe_key(msg, "units", "")),
                            "discipline": safe_key(msg, "discipline", None),
                            "parameter_category": safe_key(msg, "parameterCategory", None),
                            "parameter_number": safe_key(msg, "parameterNumber", None),
                            "type_of_level": type_of_level,
                            "level": level_num,
                            "standard_atmosphere_altitude_m_if_pressure_level": approx_alt_m,
                            "value": value,
                            "grid_latitude_deg": nearest_latlon[0],
                            "grid_longitude_deg_raw": nearest_latlon[1],
                            "grid_distance_km": nearest_latlon[2],
                            "message_sha256": sha256_bytes(data),
                            "raw_index_line": rec.raw,
                        }
                        point_rows.append(row)
                        selected_manifest.append({
                            "message_number": rec.message_number,
                            "variable": rec.variable,
                            "level_desc": rec.level_desc,
                            "message_sha256": row["message_sha256"],
                            "byte_count": len(data),
                        })
                    finally:
                        handle.close()
                        try:
                            os.unlink(temp_name)
                        except FileNotFoundError:
                            pass
                except Exception as exc:
                    point_rows.append({
                        "valid_time_utc": valid_time,
                        "product": product,
                        "variable_from_idx": rec.variable,
                        "level_desc_from_idx": rec.level_desc,
                        "message_number": rec.message_number,
                        "error": repr(exc),
                        "raw_index_line": rec.raw,
                    })

            provenance["files"].append({
                "valid_time_utc": valid_time,
                "product": product,
                "filename": filename,
                "grib_url": grib_url,
                "idx_url": idx_url,
                "idx_sha256": sha256_bytes(idx_text.encode()),
                "grib_content_length": file_size,
                "status": "PROCESSED",
                "massden_level_count": len(mass_levels),
                "selected_message_count": len(selected),
                "selected_messages": selected_manifest,
                "nearest_grid_point": None if nearest_latlon is None else {
                    "latitude_deg": nearest_latlon[0],
                    "longitude_deg_raw": nearest_latlon[1],
                    "distance_km": nearest_latlon[2],
                },
            })

    inv_fields = [
        "valid_time_utc", "product", "message_number", "start_byte", "end_byte",
        "variable", "level_desc", "selected_for_point_extraction", "raw_index_line",
    ]
    with (OUT / "filtered_inventory.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=inv_fields)
        w.writeheader()
        w.writerows(inventory_rows)

    # Point rows can contain error-only records, so take a stable union of keys.
    preferred = [
        "valid_time_utc", "product", "variable_from_idx", "level_desc_from_idx",
        "message_number", "grib_short_name", "grib_name", "units", "discipline",
        "parameter_category", "parameter_number", "type_of_level", "level",
        "standard_atmosphere_altitude_m_if_pressure_level", "value",
        "grid_latitude_deg", "grid_longitude_deg_raw", "grid_distance_km",
        "message_sha256", "error", "raw_index_line",
    ]
    all_keys = set().union(*(r.keys() for r in point_rows)) if point_rows else set(preferred)
    fields = [k for k in preferred if k in all_keys] + sorted(all_keys - set(preferred))
    with (OUT / "point_profile_raw.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(point_rows)

    (OUT / "provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # Human-readable summary deliberately reports retrieval structure only, not
    # any comparison to Taylor or MYSTIC.
    mass_rows = [r for r in point_rows if r.get("variable_from_idx") == "MASSDEN" and "value" in r]
    lines = [
        "# HRRR smoke-profile retrieval summary",
        "",
        f"Frozen site: {LAT:.6f}, {LON:.6f}",
        f"Valid times: {', '.join(FREEZE['valid_times_utc'])}",
        f"Successful MASSDEN point records: {len(mass_rows)}",
        "",
        "This is an independent NOAA HRRR-Smoke diagnostic. It is not CAMS and is not yet a complete aerosol-extinction profile for MYSTIC.",
        "",
    ]
    for t in FREEZE["valid_times_utc"]:
        rows = [r for r in mass_rows if r["valid_time_utc"] == t]
        lines.append(f"## {t}")
        lines.append(f"MASSDEN records: {len(rows)}")
        for product in PRODUCT_STEM:
            pr = [r for r in rows if r["product"] == product]
            if not pr:
                continue
            finite = [r for r in pr if math.isfinite(float(r["value"]))]
            if finite:
                peak = max(finite, key=lambda r: float(r["value"]))
                lines.append(
                    f"- {product}: {len(pr)} levels/records; maximum point value {float(peak['value']):.9g} {peak.get('units','')} at {peak.get('level_desc_from_idx','')}"
                )
        lines.append("")
    (OUT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {}
    for p in sorted(OUT.iterdir()):
        if p.is_file():
            manifest[p.name] = {
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                "bytes": p.stat().st_size,
            }
    (OUT / "SHA256SUMS.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print((OUT / "summary.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
