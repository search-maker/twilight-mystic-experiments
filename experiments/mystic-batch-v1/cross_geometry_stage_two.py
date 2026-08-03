#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

STAGE_ID = "cross-geometry-stage-two-v1"
SOURCE_STAGE_ID = "cross-geometry-pilot-v1"
EXPANDABLE = {"NEEDS_MORE_BLOCKS", "SCREENING_DISCREPANCY"}

SEEDS = {
    "g01-reference-bridge": {"reference-vroom": [78301, 78302], "alis": [78401, 78402]},
    "g02-early-near-low": {"reference-vroom": [78311, 78312], "alis": [78411, 78412]},
    "g03-early-perpendicular-high": {"reference-vroom": [78321, 78322], "alis": [78421, 78422]},
    "g04-mid-perpendicular": {"reference-vroom": [78331, 78332], "alis": [78431, 78432]},
    "g05-mid-opposite-low": {"reference-vroom": [78341, 78342], "alis": [78441, 78442]},
    "g06-late-opposite-high-aerosol": {"reference-vroom": [78351, 78352], "alis": [78451, 78452]}
}


class StageTwoRefusal(RuntimeError):
    pass


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise StageTwoRefusal(f"expected object: {path}")
    return value


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(source_manifest_path: Path, source_analysis_path: Path) -> dict[str, Any]:
    manifest = load(source_manifest_path)
    analysis = load(source_analysis_path)
    if manifest.get("stageId") != SOURCE_STAGE_ID or manifest.get("proposalOnly") is not True or manifest.get("scientificExecution") is not False:
        raise StageTwoRefusal("source manifest is not the disabled pilot proposal")
    if analysis.get("stageId") != SOURCE_STAGE_ID or analysis.get("status") != "SCREENING_ANALYZED" or analysis.get("screeningOnly") is not True:
        raise StageTwoRefusal("source analysis is not a screening result")
    results = analysis.get("geometryResults")
    if not isinstance(results, list):
        raise StageTwoRefusal("geometry results missing")
    result_by_group: dict[str, dict[str, Any]] = {}
    for result in results:
        if not isinstance(result, dict) or not isinstance(result.get("groupId"), str) or result["groupId"] in result_by_group:
            raise StageTwoRefusal("invalid or duplicate geometry result")
        result_by_group[result["groupId"]] = result
    geometry_ids = [geometry["geometryId"] for geometry in manifest["geometries"]]
    if set(result_by_group) != set(geometry_ids):
        raise StageTwoRefusal("analysis geometry set does not match source manifest")
    structural = sorted(group for group, result in result_by_group.items() if result.get("classification") == "STRUCTURAL_OR_EXECUTION_FAILURE")
    if structural:
        raise StageTwoRefusal(f"structural failures require technical diagnosis, not automatic expansion: {structural}")
    selected = sorted(group for group, result in result_by_group.items() if result.get("classification") in EXPANDABLE)
    if not selected:
        return {
            "schemaVersion": 1,
            "stageId": STAGE_ID,
            "status": "NO_EXPANSION_RECOMMENDED",
            "proposalOnly": True,
            "scientificExecution": False,
            "successDoesNotAuthorizeProduction": True,
            "sourceManifestRawSha256": raw_sha256(source_manifest_path),
            "sourceAnalysisRawSha256": raw_sha256(source_analysis_path),
            "selectedGeometryIds": [],
            "cases": [],
            "boundary": "screening agreement recommends no stage-two proposal; this is not final scientific acceptance"
        }
    geometries = [geometry for geometry in manifest["geometries"] if geometry["geometryId"] in selected]
    source_seeds = {case["seed"] for case in manifest["cases"]}
    cases: list[dict[str, Any]] = []
    ordinal = 1
    for group_id in selected:
        for method, label in (("reference-vroom", "vroom"), ("alis", "alis")):
            reserved = SEEDS[group_id][method]
            if source_seeds.intersection(reserved):
                raise StageTwoRefusal(f"reserved stage-two seed collides with pilot: {group_id}/{method}")
            for block, seed in zip((3, 4), reserved):
                cases.append({
                    "ordinal": ordinal,
                    "caseId": f"cg2-{group_id.split('-', 1)[0]}-{label}-b{block}",
                    "groupId": group_id,
                    "method": method,
                    "block": block,
                    "seed": seed,
                    "photonHistories": 20_000_000
                })
                ordinal += 1
    configured = sum(case["photonHistories"] for case in cases)
    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "batchId": "cross-geometry-stage-two-screening-v1",
        "mode": "scientific-proposal",
        "proposalOnly": True,
        "scientificExecution": False,
        "successDoesNotAuthorizeProduction": True,
        "adapterId": manifest["adapterId"],
        "sourceManifestRawSha256": raw_sha256(source_manifest_path),
        "sourceAnalysisRawSha256": raw_sha256(source_analysis_path),
        "selectedGeometryIds": selected,
        "runtime": manifest["runtime"],
        "limits": {
            "maximumCases": 24,
            "maximumParallel": min(6, len(cases)),
            "maximumConfiguredMcPhotonsSum": configured,
            "perCaseTimeoutSeconds": manifest["limits"]["perCaseTimeoutSeconds"]
        },
        "frozenInputs": manifest["frozenInputs"],
        "geometries": geometries,
        "cases": cases,
        "boundary": "proposal for fresh blocks 3-4 only at noisy or discrepant pilot geometries; no automatic authorization or scientific acceptance"
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--source-analysis", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = build(args.source_manifest, args.source_analysis)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump(result))
        print(dump(result), end="")
        return 0
    except Exception as exc:
        print(dump({"status": "REFUSED", "stageId": STAGE_ID, "reason": str(exc)}), end="", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
