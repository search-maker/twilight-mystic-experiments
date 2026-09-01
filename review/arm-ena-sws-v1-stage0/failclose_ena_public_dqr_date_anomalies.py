#!/usr/bin/env python3
"""Fail-close impossible ARM DQR interval dates in the ENA live25 documentary audit.

This is parser hygiene only. It never opens SWS photometric values and never
promotes a native science PASS/FAIL. A clearly impossible date (for example
2910-03-04) is retained as documentary evidence but cannot create an overlap.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "public-dqr-output"
MATRIX = OUT / "ena_live25_public_dqr_matrix.csv"
SUMMARY = OUT / "ena_live25_public_dqr_summary.json"


def year_of(value: str) -> int | None:
    text = (value or "").strip()
    if not text:
        return None
    try:
        return int(text[:4])
    except Exception:
        return None


def main() -> int:
    with MATRIX.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
        fields = list(rows[0].keys()) if rows else []

    anomalies = 0
    for row in rows:
        sy = year_of(row.get("dqr_start_raw", ""))
        ey = year_of(row.get("dqr_end_raw", ""))
        impossible = (
            (sy is not None and not 1900 <= sy <= 2100)
            or (ey is not None and not 1900 <= ey <= 2100)
        )
        if not impossible:
            continue
        anomalies += 1
        row["dqr_interval_parse_ok"] = "False"
        for key in (
            "overlap_e0_anchor_support", "overlap_twilight_core",
            "overlap_preceding_3h", "overlap_sonde_plusminus_6h",
            "overlap_broad_plusminus_6h",
        ):
            row[key] = "False"
        row["documentary_disposition"] = "DQR_INTERVAL_DATE_ANOMALY_UNRESOLVED"
        row["native_disposition_not_inferred"] = "True"
        row["science_gate_changed"] = "False"
        row["protected_sws_values_opened"] = "False"

    with MATRIX.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    any_cases: set[str] = set()
    core_cases: set[str] = set()
    counts: dict[str, int] = {}
    for row in rows:
        if not row.get("dqr_id"):
            continue
        flags = [
            row.get("overlap_e0_anchor_support") == "True",
            row.get("overlap_twilight_core") == "True",
            row.get("overlap_preceding_3h") == "True",
            row.get("overlap_sonde_plusminus_6h") == "True",
            row.get("overlap_broad_plusminus_6h") == "True",
        ]
        if any(flags):
            any_cases.add(row["case_id"])
            if flags[1]:
                core_cases.add(row["case_id"])
            a = row.get("assessment", "").lower()
            if a:
                counts[a] = counts.get(a, 0) + 1

    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    summary["schema"] = 3
    summary["date_anomaly_policy"] = "years outside 1900..2100 cannot create overlap; retained as unresolved documentary anomaly"
    summary["dqr_interval_date_anomaly_rows"] = anomalies
    summary["cases_with_any_public_dqr_overlap"] = sorted(any_cases)
    summary["cases_with_twilight_core_public_dqr_overlap"] = sorted(core_cases)
    summary["overlap_assessment_row_counts"] = counts
    summary["native_disposition_not_inferred"] = True
    summary["science_gate_changed"] = False
    summary["protected_sws_values_opened"] = False
    summary["stage_b_authorized"] = False
    SUMMARY.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"dqr_interval_date_anomaly_rows": anomalies, "summary": summary}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
