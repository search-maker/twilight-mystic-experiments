#!/usr/bin/env python3
"""Public ARM ENA site-completeness audit for the frozen live-25 set.

Documentary/availability triage only. No SWS photometric values are opened and
no native science disposition is inferred from presence/absence in these
quarterly metrics reports.
"""
from __future__ import annotations

import html.parser
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "public-completeness-output"
BASE = "https://site-completeness-ui.svcs.arm.gov/Metrics"
REPORTS = [
    ("FY2017_Q3", "2017", "3"),
    ("FY2018_Q3", "2018", "3"),
    ("FY2018_Q4", "2018", "4"),
    ("FY2019_Q1", "2019", "1"),
    ("FY2019_Q2", "2019", "2"),
    ("FY2019_Q3", "2019", "3"),
    ("FY2019_Q4", "2019", "4"),
]
STREAMS = [
    "enaswsC1.b1",
    "enaarsclkazr1kolliasC1.c1", "enaarsclkazr1kolliasC1.c0",
    "enaceilC1.b1", "enamplpolfsC1.b1",
    "enarlprofbeC1.c1", "enarlproffex1thorC1.c0",
    "enamfrsr7nchaod1michC1.c1", "enamfrsr7nchaod1michC1.c0",
    "enamfrsraod1michC1.c1", "enamfrsraod1michC1.c0",
    "enasondewnpnC1.b1",
    "enamfr10mC1.b1", "enamfrsrC1.b1",
    "enagndrad60sC1.b1", "enaskyrad60sC1.b1", "enasebsC1.b1",
]

class TableParser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_tr = False
        self.in_cell = False
        self.cell_parts: list[str] = []
        self.row: list[str] = []
        self.rows: list[list[str]] = []
        self.links: list[dict[str, str]] = []
    def handle_starttag(self, tag, attrs):
        if tag.lower() == "tr":
            self.in_tr = True; self.row = []
        elif tag.lower() in {"td", "th"} and self.in_tr:
            self.in_cell = True; self.cell_parts = []
        elif tag.lower() == "a":
            d = dict(attrs); href = d.get("href")
            if href:
                self.links.append({"href": href})
    def handle_endtag(self, tag):
        if tag.lower() in {"td", "th"} and self.in_cell:
            text = re.sub(r"\s+", " ", " ".join(self.cell_parts)).strip()
            self.row.append(text); self.in_cell = False; self.cell_parts = []
        elif tag.lower() == "tr" and self.in_tr:
            if self.row: self.rows.append(self.row)
            self.in_tr = False; self.row = []
    def handle_data(self, data):
        if self.in_cell:
            self.cell_parts.append(data)

def fetch(url: str) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "ena-sws-v1-public-completeness-audit/1"})
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read().decode("utf-8", errors="replace")
        return int(getattr(r, "status", 200)), raw

def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report_records = []
    stream_matrix = []
    discovered_links: list[dict[str, str]] = []
    for label, fy, q in REPORTS:
        url = f"{BASE}/{label}/qtr_report_ena_{fy}_{q}.html"
        try:
            status, raw = fetch(url)
            fetch_status = "OK"
        except Exception as exc:
            status, raw = 0, ""
            fetch_status = f"ERROR:{type(exc).__name__}:{str(exc)[:300]}"
        (OUT / f"{label}.html").write_text(raw, encoding="utf-8")
        parser = TableParser(); parser.feed(raw)
        normalized_rows = [[re.sub(r"\s+", " ", c).strip() for c in row] for row in parser.rows]
        full_text = "\n".join(" | ".join(r) for r in normalized_rows)
        for link in parser.links:
            href = urllib.parse.urljoin(url, link["href"])
            discovered_links.append({"report": label, "href": href})
        report_records.append({
            "report": label, "url": url, "http_status": status, "fetch_status": fetch_status,
            "row_count": len(normalized_rows), "link_count": len(parser.links),
            "contains_missing_keyword": "missing" in raw.lower(),
            "contains_daily_keyword": "daily" in raw.lower(),
        })
        for ds in STREAMS:
            matched = [r for r in normalized_rows if any(ds.lower() == c.lower() or ds.lower() in c.lower() for c in r)]
            stream_matrix.append({
                "report": label, "datastream": ds,
                "listed_in_quarter_report": bool(matched),
                "matching_rows": matched,
                "native_availability_not_inferred": True,
                "protected_sws_values_opened": False,
            })
        # retain text-only table for easy byte review
        (OUT / f"{label}_table.txt").write_text(full_text + "\n", encoding="utf-8")

    # Classify link targets without following them. This lets us see whether the
    # quarterly reports expose an exact-day/detail route before adding another fetch.
    for x in discovered_links:
        low = x["href"].lower()
        x["looks_like_detail_or_daily"] = any(t in low for t in ("daily", "missing", "detail", "day", "metric"))

    (OUT / "ena_live25_public_completeness_reports.json").write_text(
        json.dumps(report_records, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (OUT / "ena_live25_public_completeness_stream_matrix.json").write_text(
        json.dumps(stream_matrix, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (OUT / "ena_live25_public_completeness_links.json").write_text(
        json.dumps(discovered_links, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    listed = sorted({r["datastream"] for r in stream_matrix if r["listed_in_quarter_report"]})
    not_listed = sorted(set(STREAMS) - set(listed))
    detail_links = sorted({x["href"] for x in discovered_links if x["looks_like_detail_or_daily"]})
    summary = {
        "schema": 1,
        "protocol": "ARM_ENA_SWS_V1_LIVE25_PUBLIC_SITE_COMPLETENESS_DOCUMENTARY_AUDIT",
        "reports_requested": [x[0] for x in REPORTS],
        "reports_fetch_ok": [x["report"] for x in report_records if x["fetch_status"] == "OK"],
        "reports_fetch_error": [x for x in report_records if x["fetch_status"] != "OK"],
        "target_datastream_count": len(STREAMS),
        "target_datastreams_listed_in_at_least_one_report": listed,
        "target_datastreams_not_listed_in_any_report": not_listed,
        "detail_or_daily_link_candidates": detail_links,
        "absence_from_report_is_not_native_absence": True,
        "native_disposition_not_inferred": True,
        "science_gate_changed": False,
        "protected_sws_values_opened": False,
        "stage_b_authorized": False,
    }
    (OUT / "ena_live25_public_completeness_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
