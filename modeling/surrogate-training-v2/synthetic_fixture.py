#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

BOUNDARY = {
    "syntheticOnly": True,
    "scientificExecution": False,
    "observationallyValidated": False,
    "productionModelReady": False,
    "successDoesNotAuthorizeProduction": True,
}


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fake_hash(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def geometry(index: int) -> dict[str, float]:
    return {
        "sunDepressionDeg": 2.0 + 16.0 * ((index * 17) % 47) / 46.0,
        "targetAltitudeDeg": 5.0 + 75.0 * ((index * 23) % 47) / 46.0,
        "relativeAzimuthDeg": 180.0 * ((index * 29) % 47) / 46.0,
        "observerElevationM": 2500.0 * ((index * 31) % 47) / 46.0,
        "aod550": 0.05 + 0.35 * ((index * 37) % 47) / 46.0,
    }


def luminance(item: dict[str, float]) -> float:
    exponent = (
        2.8 - 0.31 * item["sunDepressionDeg"]
        + 0.006 * item["targetAltitudeDeg"]
        - 0.0015 * item["relativeAzimuthDeg"]
        - 0.9 * item["aod550"]
        + 0.00004 * item["observerElevationM"]
    )
    return math.exp(exponent)


def build(output_dir: Path, exact_main_sha: str = "e7c7b0e1bef4f8b3e3989e7ed445a008846ac914") -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    training_ids = [f"t1g{i:02d}" for i in range(1, 40)]
    holdout_ids = [f"t1g{i:02d}" for i in range(40, 49)]
    role_map = {item: "surrogate-training" for item in training_ids} | {item: "internal-holdout" for item in holdout_ids}
    records = []
    for index, geometry_id in enumerate(training_ids + holdout_ids, start=1):
        point = geometry(index)
        value = luminance(point)
        records.append({
            "geometryId": geometry_id,
            "geometry": point,
            "role": role_map[geometry_id],
            "classification": "PRECISION_TARGET_MET",
            "caseIds": [f"{geometry_id}-b1", f"{geometry_id}-b2"],
            "sourceBindings": {
                "manifestRawSha256": fake_hash("manifest"),
                "aggregateRawSha256": fake_hash("aggregate"),
                "auditRawSha256": fake_hash("audit"),
            },
            "statistics": {
                "meanCdM2": value,
                "sampleStdCdM2": value * 0.02,
                "relativeStandardErrorOfMean": 0.01414213562373095,
                "nodeMeanRadiance": [value * (0.75 + 0.02 * node) for node in range(15)],
            },
        })
    hard_ids = ["g02-early-near-low", "g03-early-perpendicular-high", "g04-mid-perpendicular", "g05-mid-opposite-low", "g06-late-opposite-high-aerosol"]
    soft_ids = ["g01-reference-bridge"]
    external = []
    for index, geometry_id in enumerate(hard_ids + soft_ids, start=60):
        point = geometry(index % 47 or 1)
        external.append({
            "geometryId": geometry_id,
            "geometry": point,
            "meanCdM2": luminance(point),
            "eligibleForTraining": False,
            "eligibleForHyperparameterSelection": False,
            "reportOnly": geometry_id in soft_ids,
        })
    dataset = {
        "schemaVersion": 2,
        "stageId": "twilight-surrogate-tier-1-analysis-v1",
        "status": "TIER_1_NUMERICAL_DATASET_COMPLETE",
        **BOUNDARY,
        "records": records,
        "trainingGeometryIds": training_ids,
        "internalHoldoutGeometryIds": holdout_ids,
        "hardExternalAnchorIds": hard_ids,
        "softDiagnosticIds": soft_ids,
    }
    design = {"schemaVersion": 1, "stageId": "surrogate-training-v2-frozen-role-map-v1", **BOUNDARY, "rolesByGeometryId": role_map}
    dataset_path = output_dir / "tier1-numerical-dataset.json"
    design_path = output_dir / "frozen-design.json"
    dataset_path.write_text(dump(dataset))
    design_path.write_text(dump(design))
    envelope = {
        "schemaVersion": 1,
        "stageId": "twilight-surrogate-tier-1-dataset-envelope-v1",
        "aggregatePassed": True,
        "independentAuditPassed": True,
        "precisionClassificationComplete": True,
        "provenanceValidated": True,
        **BOUNDARY,
        "exactMainSha": exact_main_sha,
        "datasetRawSha256": sha256(dataset_path),
        "bindings": {
            "manifestRawSha256": fake_hash("manifest"),
            "aggregateRawSha256": fake_hash("aggregate"),
            "independentAuditRawSha256": fake_hash("independent-audit"),
            "analysisRawSha256": fake_hash("analysis"),
            "designRawSha256": sha256(design_path),
        },
        "externalRecords": external,
    }
    envelope_path = output_dir / "dataset-envelope.json"
    envelope_path.write_text(dump(envelope))
    return {"dataset": dataset_path, "design": design_path, "envelope": envelope_path}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--main-sha", default="e7c7b0e1bef4f8b3e3989e7ed445a008846ac914")
    args = parser.parse_args()
    build(args.output_dir, args.main_sha)
