#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

STAGE_ID = "twilight-surrogate-tier-1-mc-elevation-semantics-audit-v1"
DOCS = {
    "mc": "share/libRadtran/GUI/resources/html_doc/mc_elevation_file.html",
    "altitude": "share/libRadtran/GUI/resources/html_doc/altitude.html",
    "zout": "share/libRadtran/GUI/resources/html_doc/zout.html",
}


class AuditError(RuntimeError):
    pass


class Extractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text(path: Path) -> str:
    parser = Extractor()
    parser.feed(path.read_text(encoding="utf-8"))
    return re.sub(r"\s+", " ", " ".join(parser.parts)).strip().casefold()


def require(value: str, phrases: tuple[str, ...], label: str) -> None:
    missing = [phrase for phrase in phrases if phrase.casefold() not in value]
    if missing:
        raise AuditError(f"{label} documentation changed: {missing}")


def audit(root: Path) -> dict[str, Any]:
    inventory_path = root / "inventory.json"
    inventory = json.loads(inventory_path.read_text())
    if inventory.get("status") != "PRIMARY_RUNTIME_EVIDENCE_PRESERVED_NO_SEMANTIC_VALIDATION":
        raise AuditError("inventory status changed")
    if inventory.get("solverExecutionCount") != 0:
        raise AuditError("inventory solver boundary changed")
    rows = {row.get("path"): row for row in inventory.get("primaryEvidence", [])}
    paths: dict[str, Path] = {}
    hashes: dict[str, str] = {}
    for key, relative in DOCS.items():
        row = rows.get(relative)
        if not isinstance(row, dict) or row.get("present") is not True:
            raise AuditError(f"missing document: {relative}")
        path = root / row["preservedPath"]
        if not path.is_file() or sha(path) != row.get("rawSha256"):
            raise AuditError(f"document hash mismatch: {relative}")
        paths[key] = path
        hashes[relative] = sha(path)

    mc = text(paths["mc"])
    altitude = text(paths["altitude"])
    zout = text(paths["zout"])
    require(mc, (
        "define a mystic 2d elevation input file",
        "dx and dy are the size of the grid boxes in km",
        "elevation in km of each point",
        "minimum elevation must be larger than 0",
    ), "mc_elevation_file")
    require(altitude, (
        "set the bottom level in the model atmosphere",
        "the profiles of pressure, temperature, molecular absorbers, ice and water clouds are cut at the specified altitude",
        "altitude is very different from zout",
    ), "altitude")
    require(zout, (
        "zout does not restructure the atmosphere model",
        "if you want calculations done for e.g. an elevated site you have to restructure the atmosphere model",
        "by using altitude",
    ), "zout")
    if "restructure the atmosphere" in mc:
        raise AuditError("mc_elevation_file documentation changed")

    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "FORMAT_DEFINED_SITE_ALTITUDE_EQUIVALENCE_NOT_ESTABLISHED",
        "scientificExecution": False,
        "scientificDatasetProduced": False,
        "solverExecutionCount": 0,
        "authorizationPermitted": False,
        "ordinal2ScientificDispatchPermitted": False,
        "mcElevationFileFormatDefined": True,
        "siteAltitudeEquivalenceEstablished": False,
        "inventoryRawSha256": sha(inventory_path),
        "primaryDocumentRawSha256": hashes,
        "boundary": "documentation audit only; no scientific run, authorization, dispatch, model fitting, or production use",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = audit(args.inventory_dir)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump(result))
        print(dump(result), end="")
        return 0
    except Exception as exc:
        print(dump({"schemaVersion": 1, "stageId": STAGE_ID, "status": "REFUSED", "reason": str(exc)}), file=sys.stderr, end="")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
