#!/usr/bin/env python3
"""Retrieve only missing non-radiance ARM evidence for the five live ARM-SGP V1 cases.

Result-blind transport only. This script NEVER queries or downloads any SASZE datastream.
Credentials are read from ARM_USER_ID and ARM_ACCESS_TOKEN and are never printed.
It queries ARM Live, downloads matching native files byte-for-byte, hashes them, and
creates a compact ZIP + manifest for downstream frozen G2/G4-G9 evaluation.
"""
from __future__ import annotations
import csv, hashlib, json, os, re, sys, urllib.parse, urllib.request, zipfile
from datetime import datetime, timedelta
from pathlib import Path

BASE = "https://adc.arm.gov/armlive"
CASES = {
    "2024-01-27_dusk": "20240128",
    "2024-02-01_dusk": "20240202",
    "2024-03-27_dusk": "20240328",
    "2024-03-28_dusk": "20240329",
    "2024-05-31_dusk": "20240601",
}
# gate, component, datastream(s), UTC-day offsets relative to the event UTC date
REQUESTS = [
    ("G2", "ARSCL_KAZR", ["sgparsclkazr1kolliasC1.c0", "sgparsclkazr1kolliasC1.c1"], [0]),
    ("G2", "CEIL", ["sgpceilC1.b1"], [0]),
    ("G4", "HSRL", ["sgphsrlC1.a1"], [0]),
    ("G5", "RLPROFBE_RAMAN", ["sgprlprofbeC1.c1"], [0]),
    ("G6", "MFRSR_AOD", ["sgpmfrsr7nchaod1michC1.c1"], [-1, 0]),
    ("G6", "CSPHOT", ["sgpcsphotaodfiltqav3C1.a1"], [-1, 0]),
    ("G7", "SONDE", ["sgpsondewnpnC1.b1"], [-1, 0, 1]),
    ("G8", "MFR_UP", ["sgpmfr10mC1.b1"], [-1, 0]),
    ("G8", "MFRSR_DOWN", ["sgpmfrsrC1.b1"], [-1, 0]),
    ("G8", "QCRAD_C2", ["sgpqcradbrs1longC1.c2", "sgpqcrad1longC1.c2"], [-1, 0]),
    ("G9", "GECOMI_OZONE", ["gecomiX1.a1"], [-1, 0]),
]
DATE_RE = re.compile(r"\.(20\d{6})\.")

def shift(d: str, n: int) -> str:
    return (datetime.strptime(d, "%Y%m%d") + timedelta(days=n)).strftime("%Y%m%d")

def iso_day(d: str) -> str:
    return datetime.strptime(d, "%Y%m%d").strftime("%Y-%m-%d")

def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()

def json_filenames(obj):
    out = []
    def walk(x):
        if isinstance(x, dict):
            for v in x.values(): walk(v)
        elif isinstance(x, list):
            for v in x: walk(v)
        elif isinstance(x, str) and x.lower().endswith((".nc", ".cdf")):
            out.append(os.path.basename(x))
    walk(obj)
    return sorted(set(out))

def request_json(userpair: str, ds: str, start: str, end: str):
    if "sasze" in ds.lower():
        raise RuntimeError("holdout firewall: SASZE query forbidden")
    q = urllib.parse.urlencode({"user": userpair, "ds": ds, "start": start, "end": end, "wt": "json"})
    with urllib.request.urlopen(BASE + "/query?" + q, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))

def download(userpair: str, filename: str, dst: Path):
    if "sasze" in filename.lower():
        raise RuntimeError("holdout firewall: SASZE download forbidden")
    q = urllib.parse.urlencode({"user": userpair, "file": filename})
    with urllib.request.urlopen(BASE + "/saveData?" + q, timeout=300) as r, dst.open("wb") as f:
        while True:
            b = r.read(8 * 1024 * 1024)
            if not b: break
            f.write(b)

def main():
    uid = os.environ.get("ARM_USER_ID", "").strip()
    token = os.environ.get("ARM_ACCESS_TOKEN", "").strip()
    if not uid or not token:
        raise SystemExit("Set ARM_USER_ID and ARM_ACCESS_TOKEN in the environment; credentials are never printed.")
    userpair = uid + ":" + token
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "ARM_SGP_POSTG3_LIVE5_AUTH_NONRADIANCE_V1")
    raw = out / "raw"; raw.mkdir(parents=True, exist_ok=True)
    rows, seen = [], {}
    for case_id, event_date in CASES.items():
        for gate, component, streams, offsets in REQUESTS:
            wanted_dates = {shift(event_date, n) for n in offsets}
            start = iso_day(min(wanted_dates)); end = iso_day(shift(max(wanted_dates), 1))
            for ds in streams:
                try:
                    payload = request_json(userpair, ds, start, end)
                    names = json_filenames(payload)
                except Exception as exc:
                    rows.append({"case_id":case_id,"gate":gate,"component":component,"datastream":ds,"filename":"","event_utc_date":event_date,"wanted_dates":";".join(sorted(wanted_dates)),"status":"QUERY_ERROR","size_bytes":"","sha256":"","note":type(exc).__name__})
                    continue
                matched = []
                for name in names:
                    m = DATE_RE.search(name)
                    if m and m.group(1) in wanted_dates:
                        matched.append(name)
                if not matched:
                    rows.append({"case_id":case_id,"gate":gate,"component":component,"datastream":ds,"filename":"","event_utc_date":event_date,"wanted_dates":";".join(sorted(wanted_dates)),"status":"NO_MATCH","size_bytes":"","sha256":"","note":"ARM Live query returned no filename on frozen dates"})
                for name in matched:
                    if name not in seen:
                        dst = raw / name
                        try:
                            download(userpair, name, dst)
                            seen[name] = (dst.stat().st_size, sha256(dst))
                        except Exception as exc:
                            rows.append({"case_id":case_id,"gate":gate,"component":component,"datastream":ds,"filename":name,"event_utc_date":event_date,"wanted_dates":";".join(sorted(wanted_dates)),"status":"DOWNLOAD_ERROR","size_bytes":"","sha256":"","note":type(exc).__name__})
                            continue
                    size, digest = seen[name]
                    rows.append({"case_id":case_id,"gate":gate,"component":component,"datastream":ds,"filename":name,"event_utc_date":event_date,"wanted_dates":";".join(sorted(wanted_dates)),"status":"DOWNLOADED","size_bytes":size,"sha256":digest,"note":"native payload not scientifically inspected"})
    fields = ["case_id","gate","component","datastream","filename","event_utc_date","wanted_dates","status","size_bytes","sha256","note"]
    with (out / "retrieval_manifest.csv").open("w", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
    summary = {"schema":1,"cases":list(CASES),"sasze_queried":False,"sasze_downloaded":False,"unique_native_files":len(seen),"manifest_rows":len(rows),"downloaded_rows":sum(r["status"]=="DOWNLOADED" for r in rows),"query_error_rows":sum(r["status"]=="QUERY_ERROR" for r in rows),"download_error_rows":sum(r["status"]=="DOWNLOAD_ERROR" for r in rows),"note":"Result-blind transport only; downstream must verify HSRL code_version=2.6.7 and all frozen QC/gates."}
    (out / "retrieval_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    zpath = out.with_suffix(".zip")
    with zipfile.ZipFile(zpath, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in sorted(out.rglob("*")):
            if p.is_file(): z.write(p, p.relative_to(out.parent))
    print(json.dumps(summary, indent=2, sort_keys=True))
    print("ZIP:", zpath)
    print("ZIP_SHA256:", sha256(zpath))
if __name__ == "__main__": main()
