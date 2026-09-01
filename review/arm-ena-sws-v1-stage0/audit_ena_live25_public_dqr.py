#!/usr/bin/env python3
"""Public, result-blind ARM DQR audit for the ENA/SWS V1 live-25 set.

This script reads no SWS photometric values and requires no ARM Data Center
credential. It queries ARM's public DQR web service for documented missing,
incorrect, and suspect intervals on streams required by frozen E0/E2-E6.

IMPORTANT: absence of a public DQR is NOT native-data PASS evidence. This audit
is documentary triage only. Native gates remain governed by their frozen
NetCDF/QC evaluators.
"""
from __future__ import annotations

import csv
import datetime as dt
import importlib.util
import json
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
LIVE25 = HERE / "ena_sws_e4_e7_25_live_cases.json"
FAST_UNIVERSE = HERE / "generate_ena_event_universe_fast.py"
OUT = HERE / "public-dqr-output"
DQR_BASE = "https://dqr-web-service.arm.gov/dqr_full"
ASSESSMENT = "incorrect,missing,suspect"
QUERY_START = "20160101"
QUERY_END = "20200101"
QUERY_TIMEOUT_SECONDS = 30

STREAMS: dict[str, list[str]] = {
    "E0_SWS_STRUCTURAL": ["enaswsC1.b1"],
    "E2_ARSCL": ["enaarsclkazr1kolliasC1.c1", "enaarsclkazr1kolliasC1.c0"],
    "E2_CEIL": ["enaceilC1.b1"],
    "E2_E3_RAMAN": ["enarlprofbeC1.c1", "enarlproffex1thorC1.c0"],
    "E4_MFRSR_AOD": [
        "enamfrsr7nchaod1michC1.c1", "enamfrsr7nchaod1michC1.c0",
        "enamfrsraod1michC1.c1", "enamfrsraod1michC1.c0",
    ],
    "E5_SONDE": ["enasondewnpnC1.b1"],
    "E6_MFR_UP": ["enamfr10mC1.b1"],
    "E6_MFRSR_DOWN": ["enamfrsrC1.b1"],
    "E6_GNDRAD": ["enagndrad60sC1.b1"],
    "E6_SKYRAD": ["enaskyrad60sC1.b1"],
    "E6_SEBS": ["enasebsC1.b1"],
}

UTC = dt.timezone.utc


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def parse_iso(text: str) -> dt.datetime:
    return dt.datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(UTC)


def parse_dqr_time(value: Any, *, is_end: bool) -> dt.datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if len(text) == 8 and text.isdigit():
        x = dt.datetime.strptime(text, "%Y%m%d").replace(tzinfo=UTC)
        return x + (dt.timedelta(days=1) if is_end else dt.timedelta())
    if len(text) == 10 and text[4] == "-" and text[7] == "-":
        x = dt.datetime.strptime(text, "%Y-%m-%d").replace(tzinfo=UTC)
        return x + (dt.timedelta(days=1) if is_end else dt.timedelta())
    for candidate in (text, text.replace("Z", "+00:00")):
        try:
            x = dt.datetime.fromisoformat(candidate)
            if x.tzinfo is None:
                x = x.replace(tzinfo=UTC)
            return x.astimezone(UTC)
        except ValueError:
            pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y%m%d.%H%M%S", "%Y%m%d %H:%M:%S"):
        try:
            return dt.datetime.strptime(text, fmt).replace(tzinfo=UTC)
        except ValueError:
            pass
    return None


def overlap(a0: dt.datetime, a1: dt.datetime, b0: dt.datetime | None, b1: dt.datetime | None) -> bool | None:
    if b0 is None or b1 is None or b1 < b0:
        return None
    return max(a0, b0) <= min(a1, b1)


def query_dqr(datastream: str) -> tuple[str, Any]:
    url = f"{DQR_BASE}/{datastream}/{QUERY_START}/{QUERY_END}/{ASSESSMENT}"
    req = urllib.request.Request(url, headers={"User-Agent": "ena-sws-v1-public-dqr-audit/2"})
    try:
        with urllib.request.urlopen(req, timeout=QUERY_TIMEOUT_SECONDS) as response:
            raw = response.read().decode("utf-8")
            return "OK", json.loads(raw)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return "NO_DQR_FOUND_HTTP404", None
        body = exc.read().decode("utf-8", errors="replace")[:1000]
        return f"HTTP_{exc.code}", {"error_body_prefix": body}
    except Exception as exc:
        return "QUERY_ERROR", {"error_type": type(exc).__name__, "error": str(exc)[:500]}


def flatten_docs(datastream: str, payload: Any) -> list[dict[str, Any]]:
    if payload is None or not isinstance(payload, dict):
        return []
    root = payload.get(datastream)
    if not isinstance(root, dict):
        return []
    out: list[dict[str, Any]] = []
    for assessment, by_id in root.items():
        if not isinstance(by_id, dict):
            continue
        for dqr_id, doc in by_id.items():
            if not isinstance(doc, dict):
                continue
            dates = doc.get("dates") if isinstance(doc.get("dates"), list) else []
            if not dates:
                dates = [{}]
            for interval in dates:
                if not isinstance(interval, dict):
                    continue
                out.append({
                    "dqr_id": str(dqr_id),
                    "assessment": str(assessment),
                    "subject": str(doc.get("subject", "")),
                    "description": str(doc.get("description", "")),
                    "suggestions": doc.get("suggestions"),
                    "variables": doc.get("variables", []),
                    "start_raw": interval.get("start_date"),
                    "end_raw": interval.get("end_date"),
                })
    return out


def event_windows(event: dict[str, Any]) -> dict[str, tuple[dt.datetime, dt.datetime]]:
    t6 = parse_iso(event["t_minus6_utc"])
    t7 = parse_iso(event["t_minus7_utc"])
    t8 = parse_iso(event["t_minus8_utc"])
    core0, core1 = min(t6, t8), max(t6, t8)
    return {
        "E0_ANCHOR_SUPPORT": (core0 - dt.timedelta(seconds=31), core1 + dt.timedelta(seconds=31)),
        "TWILIGHT_CORE": (core0, core1),
        "E4_E6_PRECEDING_3H": (t6 - dt.timedelta(hours=3), t6),
        "E5_SONDE_PLUSMINUS_6H": (t7 - dt.timedelta(hours=6), t7 + dt.timedelta(hours=6)),
        "BROAD_DOCUMENTARY_PLUSMINUS_6H": (core0 - dt.timedelta(hours=6), core1 + dt.timedelta(hours=6)),
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    live = json.loads(LIVE25.read_text(encoding="utf-8"))
    live_ids = [x["case_id"] for x in live["cases"]]
    if len(live_ids) != 25 or len(set(live_ids)) != 25:
        raise RuntimeError("live25 identity/count mismatch")

    fast = load_module(FAST_UNIVERSE, "ena_fast_universe_for_dqr")
    generated = fast.generate_rows()
    all_events = {x["case_id"]: x for x in generated}
    if len(all_events) != 906:
        raise RuntimeError(f"frozen universe count mismatch: {len(all_events)}")
    missing = [x for x in live_ids if x not in all_events]
    if missing:
        raise RuntimeError(f"live25 cases absent from frozen universe: {missing}")

    family_by_ds = {ds: family for family, streams in STREAMS.items() for ds in streams}
    datastreams = list(family_by_ds)
    raw_receipts: dict[str, Any] = {}
    with ThreadPoolExecutor(max_workers=min(8, len(datastreams))) as pool:
        futures = {pool.submit(query_dqr, ds): ds for ds in datastreams}
        for future in as_completed(futures):
            ds = futures[future]
            try:
                status, payload = future.result()
            except Exception as exc:
                status, payload = "QUERY_ERROR", {"error_type": type(exc).__name__, "error": str(exc)[:500]}
            raw_receipts[ds] = {"family": family_by_ds[ds], "status": status, "payload": payload}

    docs_by_stream: dict[str, list[dict[str, Any]]] = {}
    query_unresolved: list[str] = []
    for ds in datastreams:
        receipt = raw_receipts[ds]
        status, payload = receipt["status"], receipt["payload"]
        if status not in {"OK", "NO_DQR_FOUND_HTTP404"}:
            query_unresolved.append(ds)
        docs_by_stream[ds] = flatten_docs(ds, payload) if status == "OK" else []

    (OUT / "ena_live25_public_dqr_raw.json").write_text(
        json.dumps(raw_receipts, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    fieldnames = [
        "case_id", "family", "datastream", "query_status", "dqr_id", "assessment",
        "subject", "variables", "dqr_start_raw", "dqr_end_raw", "dqr_interval_parse_ok",
        "overlap_e0_anchor_support", "overlap_twilight_core", "overlap_preceding_3h",
        "overlap_sonde_plusminus_6h", "overlap_broad_plusminus_6h",
        "documentary_disposition", "native_disposition_not_inferred",
        "science_gate_changed", "protected_sws_values_opened",
    ]
    rows: list[dict[str, Any]] = []
    cases_with_any_overlap: set[str] = set()
    cases_with_core_overlap: set[str] = set()
    assessment_counts: dict[str, int] = {}

    for cid in live_ids:
        windows = event_windows(all_events[cid])
        for family, streams in STREAMS.items():
            for ds in streams:
                qstatus = raw_receipts[ds]["status"]
                docs = docs_by_stream[ds]
                emitted = False
                for doc in docs:
                    start = parse_dqr_time(doc["start_raw"], is_end=False)
                    end = parse_dqr_time(doc["end_raw"], is_end=True)
                    overlaps = {
                        "e0": overlap(*windows["E0_ANCHOR_SUPPORT"], start, end),
                        "core": overlap(*windows["TWILIGHT_CORE"], start, end),
                        "pre3": overlap(*windows["E4_E6_PRECEDING_3H"], start, end),
                        "sonde": overlap(*windows["E5_SONDE_PLUSMINUS_6H"], start, end),
                        "broad": overlap(*windows["BROAD_DOCUMENTARY_PLUSMINUS_6H"], start, end),
                    }
                    if not any(v is True for v in overlaps.values()):
                        continue
                    emitted = True
                    cases_with_any_overlap.add(cid)
                    if overlaps["core"]:
                        cases_with_core_overlap.add(cid)
                    assessment = str(doc["assessment"]).lower()
                    assessment_counts[assessment] = assessment_counts.get(assessment, 0) + 1
                    rows.append({
                        "case_id": cid, "family": family, "datastream": ds, "query_status": qstatus,
                        "dqr_id": doc["dqr_id"], "assessment": assessment, "subject": doc["subject"],
                        "variables": ";".join(map(str, doc["variables"] or [])),
                        "dqr_start_raw": doc["start_raw"], "dqr_end_raw": doc["end_raw"],
                        "dqr_interval_parse_ok": start is not None and end is not None,
                        "overlap_e0_anchor_support": overlaps["e0"],
                        "overlap_twilight_core": overlaps["core"],
                        "overlap_preceding_3h": overlaps["pre3"],
                        "overlap_sonde_plusminus_6h": overlaps["sonde"],
                        "overlap_broad_plusminus_6h": overlaps["broad"],
                        "documentary_disposition": "KNOWN_DQR_OVERLAP_" + assessment.upper(),
                        "native_disposition_not_inferred": True,
                        "science_gate_changed": False,
                        "protected_sws_values_opened": False,
                    })
                if not emitted:
                    disposition = "DQR_QUERY_UNRESOLVED" if qstatus not in {"OK", "NO_DQR_FOUND_HTTP404"} else "NO_PUBLIC_DQR_OVERLAP_FOUND"
                    rows.append({
                        "case_id": cid, "family": family, "datastream": ds, "query_status": qstatus,
                        "dqr_id": "", "assessment": "", "subject": "", "variables": "",
                        "dqr_start_raw": "", "dqr_end_raw": "", "dqr_interval_parse_ok": "",
                        "overlap_e0_anchor_support": False, "overlap_twilight_core": False,
                        "overlap_preceding_3h": False, "overlap_sonde_plusminus_6h": False,
                        "overlap_broad_plusminus_6h": False,
                        "documentary_disposition": disposition,
                        "native_disposition_not_inferred": True,
                        "science_gate_changed": False,
                        "protected_sws_values_opened": False,
                    })

    with (OUT / "ena_live25_public_dqr_matrix.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "schema": 2,
        "protocol": "ARM_ENA_SWS_V1_LIVE25_PUBLIC_DQR_DOCUMENTARY_AUDIT",
        "event_time_source": "generate_ena_event_universe_fast.py frozen vectorized E0-equivalent generator",
        "case_count": 25,
        "datastream_count": len(datastreams),
        "query_start": QUERY_START,
        "query_end": QUERY_END,
        "assessment_query": ASSESSMENT,
        "query_timeout_seconds": QUERY_TIMEOUT_SECONDS,
        "query_unresolved_datastreams": sorted(query_unresolved),
        "cases_with_any_public_dqr_overlap": sorted(cases_with_any_overlap),
        "cases_with_twilight_core_public_dqr_overlap": sorted(cases_with_core_overlap),
        "overlap_assessment_row_counts": assessment_counts,
        "native_disposition_not_inferred": True,
        "absence_of_dqr_is_not_native_pass": True,
        "dqr_audit_is_documentary_only": True,
        "science_gate_changed": False,
        "protected_sws_values_opened": False,
        "stage_b_authorized": False,
    }
    (OUT / "ena_live25_public_dqr_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
