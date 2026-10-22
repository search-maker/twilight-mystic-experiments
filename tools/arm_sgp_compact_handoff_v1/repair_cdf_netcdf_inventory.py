#!/usr/bin/env python3
"""Repair ARM `.cdf` NetCDF coverage in the compact handoff.

ARM still uses the `.cdf` suffix for some scientifically essential NetCDF
streams (notably SGP radiosondes in the 2023-2024 order).  The broad v1
extractor originally recognized only `.nc` as NetCDF, so those files were
hashed/inventoried but were not decoded for native time, headers, QC, or
representative values.

This additive post-pass is intentionally read-only with respect to the source
archive.  It reuses the v1 extractor's NetCDF readers and rewrites only the
compact handoff outputs.  SASZE radiance/transmittance remain protected because
representative_extract(..., include_sasze_radiance=False) is always used.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

import extract_arm_compact_handoff as base


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def recompute_daily_availability(inventory: list[dict[str, Any]], output: Path) -> None:
    day_map: dict[tuple[str, str], dict[str, Any]] = {}
    for rec in inventory:
        date = str(rec.get("file_date_utc", ""))
        if not date:
            continue
        key = (str(rec.get("datastream", "")), date)
        row = day_map.setdefault(key, {
            "datastream": key[0],
            "date_utc": key[1],
            "file_count": 0,
            "total_bytes": 0,
            "readable_netcdf_count": 0,
            "unreadable_netcdf_count": 0,
            "native_time_start_min_utc": "",
            "native_time_end_max_utc": "",
        })
        row["file_count"] += 1
        row["total_bytes"] += int(rec.get("size_bytes", 0) or 0)
        if as_bool(rec.get("is_netcdf")):
            if as_bool(rec.get("netcdf_readable")):
                row["readable_netcdf_count"] += 1
            else:
                row["unreadable_netcdf_count"] += 1
        start = str(rec.get("native_time_start_utc", ""))
        end = str(rec.get("native_time_end_utc", ""))
        if start and (not row["native_time_start_min_utc"] or start < row["native_time_start_min_utc"]):
            row["native_time_start_min_utc"] = start
        if end and (not row["native_time_end_max_utc"] or end > row["native_time_end_max_utc"]):
            row["native_time_end_max_utc"] = end

    fields = (
        "datastream", "date_utc", "file_count", "total_bytes", "readable_netcdf_count",
        "unreadable_netcdf_count", "native_time_start_min_utc", "native_time_end_max_utc",
    )
    base.write_csv(output / "daily_availability.csv", (day_map[k] for k in sorted(day_map)), fields)


def append_cdf_representatives(
    archive_root: Path,
    output: Path,
    inventory: list[dict[str, Any]],
    readable_cdf: list[dict[str, Any]],
    issues: list[dict[str, Any]],
) -> None:
    existing = read_jsonl(output / "representative_extracts.jsonl")
    existing_keys = {(str(r.get("relative_path", "")), str(r.get("family", ""))) for r in existing}

    by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for rec in readable_cdf:
        family = base.family_for_datastream(str(rec.get("datastream", "")))
        if family != "OTHER":
            by_family[family].append(rec)

    additions: list[dict[str, Any]] = []
    for family, group in sorted(by_family.items()):
        group.sort(key=lambda r: (str(r.get("native_time_start_utc", "")), str(r.get("relative_path", ""))))
        for idx in base.spaced_indices(len(group), 3):
            rec = group[idx]
            rel = str(rec["relative_path"])
            key = (rel, family)
            if key in existing_keys:
                continue
            path = archive_root / rel
            try:
                sample = base.representative_extract(path, family, False)
                sample["relative_path"] = rel
                sample["source_sha256"] = str(rec.get("sha256", ""))
                additions.append(sample)
                existing_keys.add(key)
            except Exception as exc:
                issues.append({
                    "relative_path": rel,
                    "kind": "REPRESENTATIVE_EXTRACT_ERROR",
                    "detail": f"{type(exc).__name__}:{exc}",
                })

    base.write_jsonl(output / "representative_extracts.jsonl", [*existing, *additions])


def update_summary(output: Path, inventory: list[dict[str, Any]], cdf_count: int, readable_count: int) -> None:
    path = output / "summary.json"
    summary = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    family_summary: dict[str, dict[str, int]] = defaultdict(lambda: {"files": 0, "readable_netcdf": 0})
    for rec in inventory:
        family = base.family_for_datastream(str(rec.get("datastream", "")))
        if family == "OTHER":
            continue
        family_summary[family]["files"] += 1
        family_summary[family]["readable_netcdf"] += int(as_bool(rec.get("netcdf_readable")))

    summary["family_summary"] = dict(sorted(family_summary.items()))
    summary["netcdf_unreadable_count"] = sum(
        1 for rec in inventory if as_bool(rec.get("is_netcdf")) and not as_bool(rec.get("netcdf_readable"))
    )
    summary["cdf_netcdf_file_count"] = cdf_count
    summary["cdf_netcdf_readable_count"] = readable_count
    summary["cdf_netcdf_compatibility"] = "arm-cdf-netcdf-postpass-v1"
    path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    archive_root = args.archive_root.resolve()
    output = args.output.resolve()
    inventory_path = output / "archive_inventory.csv"
    if not inventory_path.exists():
        parser.error(f"missing broad inventory: {inventory_path}")

    inventory: list[dict[str, Any]] = read_csv(inventory_path)
    headers = {str(r.get("schema_signature", "")): r for r in read_jsonl(output / "netcdf_headers.jsonl")}
    quality_rows = read_jsonl(output / "quality_metadata.jsonl")
    quality_by_key = {
        base.sha256_bytes(base.canonical_json({k: v for k, v in r.items() if k != "example_file"})): r
        for r in quality_rows
    }
    issues = read_csv(output / "issues.csv") if (output / "issues.csv").exists() else []

    cdf_rows = [rec for rec in inventory if Path(str(rec.get("filename", ""))).suffix.lower() == ".cdf"]
    readable_cdf: list[dict[str, Any]] = []

    for rec in cdf_rows:
        rel = str(rec["relative_path"])
        datastream = str(rec.get("datastream", ""))
        path = archive_root / rel
        rec["is_netcdf"] = True
        try:
            summary, header, qrecords = base.summarize_netcdf(path)
            rec.update(summary)
            rec["netcdf_readable"] = True
            rec["error"] = ""
            readable_cdf.append(rec)

            signature = str(summary["schema_signature"])
            headers.setdefault(signature, {
                "schema_signature": signature,
                "datastream": datastream,
                "example_file": rel,
                "header": header,
            })
            for qrec in qrecords:
                value = {"datastream": datastream, "example_file": rel, **qrec}
                key = base.sha256_bytes(base.canonical_json({"datastream": datastream, **qrec}))
                quality_by_key.setdefault(key, value)
        except Exception as exc:
            rec["netcdf_readable"] = False
            rec["error"] = f"NETCDF:{type(exc).__name__}:{exc}"
            issues.append({"relative_path": rel, "kind": "NETCDF_UNREADABLE", "detail": rec["error"]})

    base.write_csv(inventory_path, inventory, base.INVENTORY_FIELDS)
    base.write_jsonl(output / "netcdf_headers.jsonl", (headers[k] for k in sorted(headers)))
    base.write_jsonl(output / "quality_metadata.jsonl", (quality_by_key[k] for k in sorted(quality_by_key)))
    append_cdf_representatives(archive_root, output, inventory, readable_cdf, issues)
    base.write_csv(output / "issues.csv", issues, ("relative_path", "kind", "detail"))
    recompute_daily_availability(inventory, output)
    update_summary(output, inventory, len(cdf_rows), len(readable_cdf))

    print(json.dumps({
        "cdf_netcdf_file_count": len(cdf_rows),
        "cdf_netcdf_readable_count": len(readable_cdf),
        "cdf_netcdf_unreadable_count": len(cdf_rows) - len(readable_cdf),
        "readable_cdf_families": sorted({base.family_for_datastream(str(r.get("datastream", ""))) for r in readable_cdf}),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
