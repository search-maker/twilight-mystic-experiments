#!/usr/bin/env python3
"""Summarize one-event ENA/SWS E0 schema probe without protected values.

Input is the ZIP produced by run_one_ena_sws_schema_probe.ps1, or its output
directory. The tool refuses raw .nc/.cdf members and refuses any probe that
does not attest protected_variable_values_read=false and raw retention=false.
It reports schema/QC/housekeeping names and the E0 disposition only; it does
not interpret SWS radiance or choose a science case.
"""
from __future__ import annotations

import argparse
import json
import re
import tempfile
import zipfile
from pathlib import Path
from typing import Any

HOUSEKEEPING_RE = re.compile(
    r"(?:shutter|dark|status|state|mode|lamp|temperature|integration|exposure|scan|view|zenith|health|error)",
    re.I,
)


def json_lines(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out = []
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        if raw.strip():
            value = json.loads(raw)
            if not isinstance(value, dict):
                raise ValueError(f"expected object in {path.name}")
            out.append(value)
    return out


def load_root(source: Path):
    if source.is_dir():
        return source, None
    if source.suffix.lower() != ".zip":
        raise ValueError("probe source must be a directory or .zip")
    z = zipfile.ZipFile(source, "r")
    names = z.namelist()
    bad = [n for n in names if Path(n).suffix.lower() in {".nc", ".cdf"}]
    if bad:
        z.close()
        raise ValueError(f"HOLDOUT FIREWALL: raw NetCDF/CDF present in probe ZIP: {bad[:5]}")
    temp = tempfile.TemporaryDirectory(prefix="ena_schema_probe_")
    z.extractall(temp.name)
    z.close()
    root = Path(temp.name)
    children = [p for p in root.iterdir()]
    if len(children) == 1 and children[0].is_dir():
        root = children[0]
    return root, temp


def ensure_false(value: Any, label: str) -> None:
    if value is not False:
        raise ValueError(f"HOLDOUT FIREWALL: {label} is not false")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("probe")
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()

    root, temp = load_root(Path(args.probe).resolve())
    try:
        summary_path = root / "ena_sws_e0_stream_summary.json"
        if not summary_path.exists():
            raise ValueError("probe summary missing")
        summary = json.loads(summary_path.read_text(encoding="utf-8-sig"))
        ensure_false(summary.get("protected_variable_values_read"), "summary.protected_variable_values_read")
        ensure_false(summary.get("raw_sws_files_retained"), "summary.raw_sws_files_retained")
        if int(summary.get("processed_event_count", -1)) != 1:
            raise ValueError("expected exactly one processed event")

        schema = json_lines(root / "ena_sws_e0_stream_schema.jsonl")
        ledger = json_lines(root / "ena_sws_e0_stream_ledger.jsonl")
        provenance = json_lines(root / "ena_sws_e0_stream_provenance.jsonl")
        queries = json_lines(root / "ena_sws_e0_query_manifest.jsonl")
        if len(ledger) != 1:
            raise ValueError(f"expected one ledger row, got {len(ledger)}")
        row = ledger[0]
        ensure_false(row.get("protected_variable_values_read"), "ledger.protected_variable_values_read")
        ensure_false(row.get("raw_sws_files_retained"), "ledger.raw_sws_files_retained")
        for i, record in enumerate(schema):
            ensure_false(record.get("protected_variable_values_read"), f"schema[{i}].protected_variable_values_read")

        by_kind: dict[str, dict[str, Any]] = {}
        for record in schema:
            kind = str(record.get("kind", "unknown"))
            group = by_kind.setdefault(kind, {
                "source_files": [], "dod_versions": set(), "process_versions": set(),
                "safe_qc_candidates": {}, "housekeeping_metadata_candidates": {},
                "protected_photometric_metadata_only": {}, "other_variables": {},
            })
            group["source_files"].append({"name": record.get("source_file"), "sha256": record.get("source_sha256")})
            group["dod_versions"].add(str(record.get("dod_version", "")))
            group["process_versions"].add(str(record.get("process_version", "")))
            for var in record.get("variables", []):
                name = str(var.get("name", ""))
                info = {
                    "dtype": var.get("dtype"), "dimensions": var.get("dimensions"), "shape": var.get("shape"),
                    "long_name": var.get("long_name"), "standard_name": var.get("standard_name"), "units": var.get("units"),
                }
                if bool(var.get("protected_photometric_values")):
                    group["protected_photometric_metadata_only"].setdefault(name, info)
                elif bool(var.get("safe_qc_values_allowed")):
                    group["safe_qc_candidates"].setdefault(name, info)
                elif HOUSEKEEPING_RE.search(" ".join([name, str(var.get('long_name','')), str(var.get('standard_name',''))])):
                    group["housekeeping_metadata_candidates"].setdefault(name, info)
                else:
                    group["other_variables"].setdefault(name, info)

        serializable = {}
        for kind, group in by_kind.items():
            serializable[kind] = {
                **group,
                "dod_versions": sorted(group["dod_versions"]),
                "process_versions": sorted(group["process_versions"]),
                "safe_qc_candidates": dict(sorted(group["safe_qc_candidates"].items())),
                "housekeeping_metadata_candidates": dict(sorted(group["housekeeping_metadata_candidates"].items())),
                "protected_photometric_metadata_only": dict(sorted(group["protected_photometric_metadata_only"].items())),
                "other_variables": dict(sorted(group["other_variables"].items())),
            }

        safe_qc_count = sum(len(g["safe_qc_candidates"]) for g in serializable.values())
        hk_count = sum(len(g["housekeeping_metadata_candidates"]) for g in serializable.values())
        validity_resolved = bool(row.get("validity_resolved_without_photometric_values", False))
        if validity_resolved:
            next_state = "SAFE_NONPHOTOMETRIC_VALIDITY_PATH_PRESENT__E0_CODE_MAY_BE_APPLIED_TO_BROAD_SCAN"
        elif safe_qc_count:
            next_state = "SAFE_QC_METADATA_EXISTS_BUT_E0_LAYOUT_OR_EVENT_VALIDITY_UNRESOLVED__DO_NOT_BROAD_SCAN_YET"
        elif hk_count:
            next_state = "NO_SAFE_QC_LAYOUT__HOUSEKEEPING_METADATA_EXISTS__FREEZE_ANY_HOUSEKEEPING_VALIDITY_RULE_BEFORE_VALUES_OR_BROAD_SCAN"
        else:
            next_state = "NO_SAFE_QC_OR_HOUSEKEEPING_PATH_FOUND__E0_FAILS_CLOSED_WITH_CURRENT_PRODUCT"

        result = {
            "schema": 1,
            "purpose": "ARM_ENA_SWS_V1_E0_SCHEMA_PROBE_SUMMARY_ONLY",
            "case_id": row.get("case_id"),
            "disposition": row.get("disposition"),
            "timing_pass": row.get("timing_pass"),
            "validity_resolved_without_photometric_values": validity_resolved,
            "validity_pass": row.get("validity_pass"),
            "target_pixel_map": row.get("target_pixel_map"),
            "qc_variables_used": row.get("qc_variables_used"),
            "safe_qc_candidate_count": safe_qc_count,
            "housekeeping_metadata_candidate_count": hk_count,
            "schema_by_kind": serializable,
            "query_record_count": len(queries),
            "provenance_record_count": len(provenance),
            "next_state": next_state,
            "protected_variable_values_read": False,
            "raw_sws_files_retained": False,
            "stage_b_authorized": False,
            "science_case_selected": False,
        }
        text = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
        if args.output:
            args.output.write_text(text, encoding="utf-8")
        print(text, end="")
        return 0
    finally:
        if temp is not None:
            temp.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
