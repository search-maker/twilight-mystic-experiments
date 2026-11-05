#!/usr/bin/env python3
"""Source-locked, standard-library-only SG_088 optical/thermal retrospective QC.

Usage:
  python sg088_jun17_20_thermal_audit.py
  python sg088_jun17_20_thermal_audit.py --source /path/to/SG_June_2023.csv

Without --source: checks the 24-row extracted fixture only; NOT raw byte custody.
With --source: also checks original full-file MD5 and 24 exact source line
positions/fields. No model fitting, cloud threshold or simulation is performed.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
from statistics import mean

DIR = Path(__file__).resolve().parent
SOURCE_MD5 = "e39d6c8a63177b5f3412a09f8bd7a847"
COLUMNS = (
    "source_line_zero_based", "utc", "mag", "reported_mag_err",
    "tamb_c", "tsky_c", "thermal_contrast_c",
)
FLOAT_FIELDS = ("mag", "reported_mag_err", "tamb_c", "tsky_c")


def inspect_fixture(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        assert tuple(reader.fieldnames or ()) == COLUMNS, "schema mismatch"
        rows = list(reader)
    assert len(rows) == 24, "expected 24 source-located measurements"
    seen = set()
    byday = {}
    for row in rows:
        key = (row["source_line_zero_based"], row["utc"])
        assert key not in seen, "duplicate line/time identity"
        seen.add(key)
        assert row["utc"].endswith("+00:00"), "UTC offset missing"
        day, hour = row["utc"].split(" ", 1)
        byday.setdefault(day, []).append(row)
        for name in FLOAT_FIELDS:
            val = float(row[name])
            assert math.isfinite(val), (key, name)
        contrast = float(row["tamb_c"]) - float(row["tsky_c"])
        assert contrast > 0 and abs(contrast - float(row["thermal_contrast_c"])) < 1e-8, key
    assert list(byday) == ["2023-06-17", "2023-06-18", "2023-06-19", "2023-06-20"]
    assert all(len(a) == 6 for a in byday.values())
    for day, group in byday.items():
        assert [r["utc"][11:16] for r in group] == [
            "03:30", "03:35", "03:40", "03:45", "03:50", "03:55"
        ], day
    return rows


def verify_raw_archive(source: Path, fixture: list[dict]) -> None:
    raw = source.read_bytes()
    actual_hash = hashlib.md5(raw).hexdigest()  # archive's published checksum
    assert actual_hash == SOURCE_MD5, f"raw archive mismatch: {actual_hash}"
    source_lines = raw.decode("utf-8-sig").splitlines()
    original_header = source_lines[0]
    assert original_header == "time,battery,id,mag,mag_err,name,signal,tamb,tsky"
    for row in fixture:
        pos = int(row["source_line_zero_based"])
        assert 0 < pos < len(source_lines), (pos, len(source_lines))
        record = next(csv.DictReader(io.StringIO(original_header + "\n" + source_lines[pos] + "\n")))
        assert record["time"] == row["utc"], pos
        assert record["name"] == "SG_088", pos
        for orig, fixture_name in [
            ("mag", "mag"), ("mag_err", "reported_mag_err"),
            ("tamb", "tamb_c"), ("tsky", "tsky_c"),
        ]:
            assert math.isclose(float(record[orig]), float(row[fixture_name]),
                                rel_tol=0, abs_tol=1e-10), (pos, orig)


def calculate(rows: list[dict]) -> dict:
    byday = {}
    for row in rows:
        byday.setdefault(row["utc"][:10], []).append(row)
    mean_contrast = {
        day: mean(float(r["thermal_contrast_c"]) for r in group)
        for day, group in byday.items()
    }
    a, b = byday["2023-06-17"], byday["2023-06-18"]
    ratios = [
        10 ** (0.4 * (float(ra["mag"]) - float(rb["mag"])))
        for ra, rb in zip(a, b)
    ]
    assert len(ratios) == 6
    output = {
        "n": len(rows),
        "per_day_mean_thermal_contrast_C": mean_contrast,
        "mean_contrast_june17_minus_june18_C":
            mean_contrast["2023-06-17"] - mean_contrast["2023-06-18"],
        "six_slot_brightness_ratio_june18_over_june17": ratios,
        "june18_0350_to_0355_later_flux_ratio":
            10 ** (0.4 * (float(b[4]["mag"]) - float(b[5]["mag"]))),
        "june18_0350_to_0355_delta_thermal_contrast_C":
            float(b[5]["thermal_contrast_c"]) - float(b[4]["thermal_contrast_c"]),
        "classification": "RETROSPECTIVE_SOURCE_QC_NOT_MODEL_VALIDATION",
    }
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, help="original Zenodo CSV, raw bytes")
    parser.add_argument("--fixture", type=Path,
                        default=DIR / "sg088_jun17_20_thermal_24rows.csv")
    args = parser.parse_args()
    rows = inspect_fixture(args.fixture)
    if args.source:
        verify_raw_archive(args.source, rows)
    summary = calculate(rows)
    reference = json.loads(
        (DIR / "sg088_jun17_20_thermal_qc_findings_20261105.json").read_text(encoding="utf-8")
    )
    assert abs(summary["mean_contrast_june17_minus_june18_C"]
               - reference["computed_diff_mean_thermal_contrast_june17_minus_june18_C"]) < 1e-4
    for got, ref in zip(summary["six_slot_brightness_ratio_june18_over_june17"],
                        reference["moon_free_june17_vs_june18"]):
        assert abs(got - ref["ratio_june18_over_june17"]) < 1e-4
    print(json.dumps({"raw_archive_md5_verified": bool(args.source), **summary},
                     indent=2, sort_keys=True))
    print("PASS: 24-source-row thermal QC (NOT model scientific acceptance)")


if __name__ == "__main__":
    main()
