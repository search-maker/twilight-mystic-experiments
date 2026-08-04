#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

STAGE_ID = "twilight-surrogate-tier-1-mc-elevation-inventory-v1"
TOKENS = ("mc_elevation_file", "elevation_file")
MAX_TEXT_BYTES = 5_000_000
MAX_MATCHES = 500
REQUIRED_PRIMARY_EVIDENCE_PATHS = (
    "share/libRadtran/GUI/resources/html_doc/mc_elevation_file.html",
    "share/libRadtran/GUI/resources/html_doc/mc_panorama_view.html",
    "share/libRadtran/examples/UVSPEC_MC.INP",
    "share/libRadtran/examples/UVSPEC_MC_ELEV.DAT",
    "share/libRadtran/examples/mc_thermal_forward/MC_THERMAL_ELEVATION.INP",
    "share/libRadtran/examples/mc_thermal_forward/MC_THERMAL_ELEVATION_PAR.INP",
    "share/libRadtran/examples/mc_thermal_forward/MC_THERMAL_ELEVATION_HILL.DAT",
)
OPTIONAL_CONTEXT_EVIDENCE_PATHS = (
    "share/libRadtran/GUI/resources/html_doc/altitude.html",
    "share/libRadtran/GUI/resources/html_doc/zout.html",
    "share/libRadtran/GUI/resources/html_doc/mc_sensorposition.html",
    "share/libRadtran/GUI/resources/html_doc/mc_surfaceparallel.html",
    "share/libRadtran/GUI/resources/html_doc/mc_sample_grid.html",
    "share/libRadtran/GUI/resources/html_doc/mc_spherical.html",
    "share/libRadtran/GUI/resources/html_doc/mc_backward.html",
    "share/libRadtran/GUI/resources/html_doc/rte_solver.html",
)
PRIMARY_EVIDENCE_PATHS = REQUIRED_PRIMARY_EVIDENCE_PATHS + OPTIONAL_CONTEXT_EVIDENCE_PATHS


class InventoryError(RuntimeError):
    pass


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def raw_sha256(path: Path) -> str:
    return sha_bytes(path.read_bytes()).hexdigest() if False else hashlib.sha256(path.read_bytes()).hexdigest()


def text_matches(prefix: Path) -> list[dict[str, Any]]:
    roots = [prefix / "share" / "libRadtran", prefix / "conda-meta"]
    matches: list[dict[str, Any]] = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.stat().st_size > MAX_TEXT_BYTES:
                continue
            data = path.read_bytes()
            if b"\x00" in data[:4096]:
                continue
            text = data.decode("utf-8", errors="replace")
            for line_number, line in enumerate(text.splitlines(), start=1):
                if any(token in line for token in TOKENS):
                    matches.append({
                        "path": str(path.relative_to(prefix)),
                        "lineNumber": line_number,
                        "line": line[:2000],
                    })
                    if len(matches) >= MAX_MATCHES:
                        return matches
    return matches


def preserve_primary_evidence(prefix: Path, output_dir: Path) -> list[dict[str, Any]]:
    evidence_root = output_dir / "primary-evidence"
    records: list[dict[str, Any]] = []
    required = set(REQUIRED_PRIMARY_EVIDENCE_PATHS)
    for relative in PRIMARY_EVIDENCE_PATHS:
        source = prefix / relative
        record: dict[str, Any] = {
            "path": relative,
            "required": relative in required,
            "present": source.is_file(),
        }
        if source.is_file():
            target = evidence_root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            record.update({
                "sizeBytes": source.stat().st_size,
                "rawSha256": raw_sha256(source),
                "preservedPath": str(target.relative_to(output_dir)),
                "preservedRawSha256": raw_sha256(target),
            })
            if record["rawSha256"] != record["preservedRawSha256"]:
                raise InventoryError(f"primary evidence copy hash mismatch: {relative}")
        elif record["required"]:
            raise InventoryError(f"required primary evidence missing: {relative}")
        records.append(record)
    return records


def inventory(uvspec: Path, prefix: Path, output_dir: Path) -> dict[str, Any]:
    if not uvspec.is_file():
        raise InventoryError(f"uvspec missing: {uvspec}")
    if not prefix.is_dir():
        raise InventoryError(f"runtime prefix missing: {prefix}")
    output_dir.mkdir(parents=True, exist_ok=True)

    help_process = subprocess.run(
        [str(uvspec.resolve()), "-h"],
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )
    help_text = help_process.stdout + help_process.stderr
    (output_dir / "uvspec-help.txt").write_text(help_text)

    binary = uvspec.read_bytes()
    binary_tokens = {token: token.encode() in binary for token in TOKENS}
    matches = text_matches(prefix)
    (output_dir / "text-matches.json").write_text(dump(matches))
    primary_evidence = preserve_primary_evidence(prefix, output_dir)
    (output_dir / "primary-evidence-index.json").write_text(dump(primary_evidence))

    metadata_files = sorted((prefix / "conda-meta").glob("rubin-libradtran-*.json"))
    metadata_hashes = {str(path.relative_to(prefix)): raw_sha256(path) for path in metadata_files}

    result = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "PRIMARY_RUNTIME_EVIDENCE_PRESERVED_NO_SEMANTIC_VALIDATION",
        "scientificExecution": False,
        "scientificDatasetProduced": False,
        "syntaxCheckCount": 0,
        "solverExecutionCount": 0,
        "authorizationPermitted": False,
        "ordinal2ScientificDispatchPermitted": False,
        "uvspecSha256": raw_sha256(uvspec),
        "uvspecHelpExitCode": help_process.returncode,
        "uvspecHelpSha256": sha_bytes(help_text.encode()),
        "uvspecBinaryTokenPresence": binary_tokens,
        "installedTextMatchCount": len(matches),
        "installedTextMatches": matches,
        "requiredPrimaryEvidenceCount": len(REQUIRED_PRIMARY_EVIDENCE_PATHS),
        "requiredPrimaryEvidencePresentCount": sum(
            1 for row in primary_evidence if row["required"] and row["present"]
        ),
        "optionalContextEvidenceCount": len(OPTIONAL_CONTEXT_EVIDENCE_PATHS),
        "optionalContextEvidencePresentCount": sum(
            1 for row in primary_evidence if not row["required"] and row["present"]
        ),
        "primaryEvidence": primary_evidence,
        "packageMetadataRawSha256": metadata_hashes,
        "semanticConclusionPermitted": False,
        "requiredNextStep": "independently inspect preserved primary and context documentation before designing any separate constant-elevation mc_elevation_file compatibility probe",
        "boundary": "installed primary runtime evidence preservation only; no inferred format equivalence or observer semantics, no terrain model, scientific run, authorization, dispatch, training, or production use",
    }
    (output_dir / "inventory.json").write_text(dump(result))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--uvspec", type=Path, required=True)
    parser.add_argument("--prefix", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = inventory(args.uvspec, args.prefix, args.output_dir)
        print(dump(result), end="")
        return 0
    except Exception as exc:
        print(dump({"schemaVersion": 1, "stageId": STAGE_ID, "status": "REFUSED", "reason": str(exc)}), file=sys.stderr, end="")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
