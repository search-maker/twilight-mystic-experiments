#!/usr/bin/env python3
"""Stream ARM ENA SWS Stage-0 E0 without persisting protected radiance files.

This is transport + result-blind structural screening only. It queries ARM Live,
downloads the native calibrated SWS file(s) needed for one frozen dusk event,
runs audit_ena_sws_e0.py (which is forbidden to read protected photometric
values), records only hashes/metadata/QC/timing dispositions, and deletes the
native SWS payload before advancing to the next event.

Credentials come only from ARM_USER_ID / ARM_ACCESS_TOKEN (or explicit CLI
values) and are never printed or written to outputs. Raw SWS files are never
placed in the output directory or Git repository.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

BASE = "https://adc.arm.gov/armlive"
DATASTREAM = "enaswsC1.b1"
AUX_DATASTREAM = "enaswsauxC1.b1"
FILE_RE = re.compile(r"^enaswsC1\.b1\.(\d{8})\..*\.(?:nc|cdf)$", re.I)
AUX_RE = re.compile(r"^enaswsauxC1\.b1\.(\d{8})\..*\.(?:nc|cdf)$", re.I)


def load_e0(path: Path):
    spec = importlib.util.spec_from_file_location("ena_sws_e0", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import E0 auditor: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def json_filenames(obj: Any) -> list[str]:
    out: list[str] = []
    def walk(x: Any) -> None:
        if isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
        elif isinstance(x, str):
            name = os.path.basename(x)
            if name.lower().endswith((".nc", ".cdf")):
                out.append(name)
    walk(obj)
    return sorted(set(out))


def arm_json(userpair: str, ds: str, start: str, end: str) -> Any:
    q = urllib.parse.urlencode({"user": userpair, "ds": ds, "start": start, "end": end, "wt": "json"})
    req = urllib.request.Request(BASE + "/query?" + q, headers={"User-Agent": "arm-ena-sws-e0-result-blind/1"})
    with urllib.request.urlopen(req, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def download_native(userpair: str, filename: str, destination: Path) -> None:
    if not (FILE_RE.match(filename) or AUX_RE.match(filename)):
        raise RuntimeError(f"refusing unexpected ARM filename: {filename}")
    q = urllib.parse.urlencode({"user": userpair, "file": filename})
    req = urllib.request.Request(BASE + "/saveData?" + q, headers={"User-Agent": "arm-ena-sws-e0-result-blind/1"})
    with urllib.request.urlopen(req, timeout=600) as response, destination.open("wb") as fh:
        while True:
            block = response.read(8 * 1024 * 1024)
            if not block:
                break
            fh.write(block)


def iso_day(yyyymmdd: str) -> str:
    return f"{yyyymmdd[:4]}-{yyyymmdd[4:6]}-{yyyymmdd[6:8]}"


def plus_one_day(yyyymmdd: str) -> str:
    import datetime as dt
    x = dt.datetime.strptime(yyyymmdd, "%Y%m%d").date() + dt.timedelta(days=1)
    return x.strftime("%Y%m%d")


def query_day(userpair: str, ds: str, yyyymmdd: str, pattern: re.Pattern[str]) -> list[str]:
    payload = arm_json(userpair, ds, iso_day(yyyymmdd), iso_day(plus_one_day(yyyymmdd)))
    return [name for name in json_filenames(payload) if (m := pattern.match(name)) and m.group(1) == yyyymmdd]


def safe_schema_snapshot(e0, path: Path, kind: str) -> dict[str, Any]:
    """Header/schema only. Never reads values of protected photometric variables."""
    import netCDF4
    with netCDF4.Dataset(path, "r") as ds:
        vars_out = []
        for name, var in ds.variables.items():
            vars_out.append({
                "name": name,
                "dtype": str(var.dtype),
                "dimensions": list(var.dimensions),
                "shape": list(var.shape),
                "protected_photometric_values": bool(e0.protected(name, var)),
                "safe_qc_values_allowed": bool(e0.safe_qc(name, var)),
                "long_name": str(getattr(var, "long_name", "")),
                "standard_name": str(getattr(var, "standard_name", "")),
                "units": str(getattr(var, "units", "")),
            })
        return {
            "kind": kind,
            "source_file": path.name,
            "source_sha256": sha256_file(path),
            "dod_version": str(getattr(ds, "dod_version", "")),
            "process_version": str(getattr(ds, "process_version", "")),
            "variables": vars_out,
            "protected_variable_values_read": False,
        }


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True, allow_nan=False) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def read_done(path: Path) -> set[str]:
    done: set[str] = set()
    if not path.exists():
        return done
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and isinstance(obj.get("case_id"), str):
            done.add(obj["case_id"])
    return done


def row_without_raw_paths(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    if out.get("source_files"):
        out["source_files"] = ";".join(Path(x).name for x in str(out["source_files"]).split(";") if x)
    return out


def materialize_summary(e0, event_universe: list[Any], ledger_jsonl: Path, out_dir: Path, e0_sha: str, collector_sha: str) -> None:
    rows: list[dict[str, Any]] = []
    if ledger_jsonl.exists():
        for line in ledger_jsonl.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    dispositions: dict[str, int] = {}
    for row in rows:
        d = str(row.get("disposition", "UNKNOWN"))
        dispositions[d] = dispositions.get(d, 0) + 1
    summary = {
        "schema": 1,
        "protocol": e0.PROTOCOL,
        "control_comment": e0.CONTROL_COMMENT,
        "candidate_event_count": len(event_universe),
        "processed_event_count": len(rows),
        "remaining_event_count": len(event_universe) - len({r.get('case_id') for r in rows}),
        "disposition_counts": dispositions,
        "e0_auditor_sha256": e0_sha,
        "collector_sha256": collector_sha,
        "raw_sws_files_retained": False,
        "protected_variable_values_read": False,
        "stage_b_authorized": False,
    }
    (out_dir / "ena_sws_e0_stream_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--e0-script", type=Path, default=Path(__file__).with_name("audit_ena_sws_e0.py"))
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--user-id", default=None, help="prefer ARM_USER_ID env; value is never persisted")
    ap.add_argument("--access-token", default=None, help="prefer ARM_ACCESS_TOKEN env; value is never persisted")
    ap.add_argument("--start-case", default=None)
    ap.add_argument("--stop-after", type=int, default=None)
    ap.add_argument("--probe-aux-schema", action="store_true", help="download matching SWS AUX only for safe schema/header snapshot; never use it for eligibility")
    args = ap.parse_args()

    uid = (args.user_id or os.environ.get("ARM_USER_ID", "")).strip()
    token = (args.access_token or os.environ.get("ARM_ACCESS_TOKEN", "")).strip()
    if not uid or not token:
        raise SystemExit("ARM_USER_ID and ARM_ACCESS_TOKEN are required; they are never printed or saved")
    userpair = uid + ":" + token

    e0_path = args.e0_script.resolve()
    e0 = load_e0(e0_path)
    out_dir = args.output_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    ledger = out_dir / "ena_sws_e0_stream_ledger.jsonl"
    provenance = out_dir / "ena_sws_e0_stream_provenance.jsonl"
    schema = out_dir / "ena_sws_e0_stream_schema.jsonl"
    query_log = out_dir / "ena_sws_e0_query_manifest.jsonl"

    e0_sha = sha256_file(e0_path)
    collector_sha = sha256_file(Path(__file__).resolve())
    events = e0.build_events()
    done = read_done(ledger)
    started = args.start_case is None
    processed_this_run = 0

    universe_path = out_dir / "ena_sws_e0_event_universe.csv"
    e0.write_csv(universe_path, [x.__dict__ for x in events])

    for event in events:
        if not started:
            if event.case_id != args.start_case:
                continue
            started = True
        if event.case_id in done:
            continue
        if args.stop_after is not None and processed_this_run >= args.stop_after:
            break

        needed = e0.needed_dates(event)
        sws_names: list[str] = []
        query_errors: list[str] = []
        for day in needed:
            try:
                names = query_day(userpair, DATASTREAM, day, FILE_RE)
                sws_names.extend(names)
                append_jsonl(query_log, {
                    "case_id": event.case_id, "datastream": DATASTREAM, "date": day,
                    "start": iso_day(day), "end_exclusive": iso_day(plus_one_day(day)),
                    "filenames": names, "credentials_persisted": False,
                })
            except Exception as exc:
                query_errors.append(f"{day}:{type(exc).__name__}")
        sws_names = sorted(set(sws_names))

        if query_errors:
            row = {**event.__dict__, "disposition": "ARM_LIVE_QUERY_ERROR", "read_errors": " | ".join(query_errors),
                   "protected_variable_values_read": False, "raw_sws_files_retained": False}
            append_jsonl(ledger, row)
            processed_this_run += 1
            materialize_summary(e0, events, ledger, out_dir, e0_sha, collector_sha)
            continue
        if not sws_names:
            row = {**event.__dict__, "disposition": "SOURCE_FILE_MISSING", "read_errors": "",
                   "protected_variable_values_read": False, "raw_sws_files_retained": False}
            append_jsonl(ledger, row)
            processed_this_run += 1
            materialize_summary(e0, events, ledger, out_dir, e0_sha, collector_sha)
            continue

        with tempfile.TemporaryDirectory(prefix="ena_sws_e0_") as temp_name:
            temp_root = Path(temp_name)
            source_records = []
            try:
                for name in sws_names:
                    path = temp_root / name
                    download_native(userpair, name, path)
                    source_records.append({"filename": name, "size_bytes": path.stat().st_size, "sha256": sha256_file(path)})
                    append_jsonl(schema, safe_schema_snapshot(e0, path, "sws"))

                if args.probe_aux_schema:
                    aux_names: list[str] = []
                    for day in needed:
                        try:
                            aux_names.extend(query_day(userpair, AUX_DATASTREAM, day, AUX_RE))
                        except Exception:
                            pass
                    for name in sorted(set(aux_names)):
                        p = temp_root / name
                        download_native(userpair, name, p)
                        append_jsonl(schema, safe_schema_snapshot(e0, p, "swsaux"))
                        p.unlink(missing_ok=True)

                idx = e0.index_files(temp_root, e0.SWS_RE)
                row = row_without_raw_paths(e0.audit(event, temp_root, idx))
                row["protected_variable_values_read"] = False
                row["raw_sws_files_retained"] = False
                append_jsonl(ledger, row)
                append_jsonl(provenance, {
                    "case_id": event.case_id,
                    "source_files": source_records,
                    "e0_auditor_sha256": e0_sha,
                    "collector_sha256": collector_sha,
                    "protected_variable_values_read": False,
                    "raw_sws_files_retained": False,
                })
            except Exception as exc:
                append_jsonl(ledger, {
                    **event.__dict__, "disposition": "STREAM_AUDIT_ERROR",
                    "read_errors": f"{type(exc).__name__}:{exc}",
                    "protected_variable_values_read": False, "raw_sws_files_retained": False,
                })

        processed_this_run += 1
        materialize_summary(e0, events, ledger, out_dir, e0_sha, collector_sha)

    materialize_summary(e0, events, ledger, out_dir, e0_sha, collector_sha)
    print((out_dir / "ena_sws_e0_stream_summary.json").read_text(encoding="utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
