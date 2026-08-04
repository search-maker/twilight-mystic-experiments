#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

STAGE_ID = "twilight-surrogate-tier-1-analysis-v1"
DATASET_STATUS = "TIER_1_NUMERICAL_DATASET_COMPLETE"
EXPECTED_GEOMETRY_COUNT = 48
TRAINING_ROLE = "surrogate-training"
HOLDOUT_ROLE = "internal-holdout"
ALLOWED_ROLES = {TRAINING_ROLE, HOLDOUT_ROLE}


class DatasetRefusal(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise DatasetRefusal(f"expected JSON object: {path}")
    return value


def require_exact(value: dict[str, Any], expected: dict[str, Any], label: str) -> None:
    changed = {key: (value.get(key), wanted) for key, wanted in expected.items() if value.get(key) != wanted}
    if changed:
        raise DatasetRefusal(f"{label} boundary changed: {changed}")


def require_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
        raise DatasetRefusal(f"{label} must be lowercase raw sha256")
    return value


def require_git_sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 40 or any(ch not in "0123456789abcdef" for ch in value):
        raise DatasetRefusal(f"{label} must be lowercase 40-character git sha")
    return value


def finite_number(value: Any, label: str, *, positive: bool = False, nonnegative: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise DatasetRefusal(f"{label} must be finite")
    number = float(value)
    if positive and number <= 0:
        raise DatasetRefusal(f"{label} must be positive")
    if nonnegative and number < 0:
        raise DatasetRefusal(f"{label} must be non-negative")
    return number


@dataclass(frozen=True)
class PartitionedDataset:
    source_dataset_hash: str
    exact_main_sha: str
    training: tuple[dict[str, Any], ...]
    internal_holdout: tuple[dict[str, Any], ...]
    hard_anchors: tuple[dict[str, Any], ...]
    soft_diagnostics: tuple[dict[str, Any], ...]
    excluded_ids: tuple[str, ...]
    provenance: dict[str, Any]


def _validate_record(record: dict[str, Any], expected_role_by_id: dict[str, str]) -> tuple[str, str]:
    geometry_id = record.get("geometryId")
    if not isinstance(geometry_id, str) or not geometry_id:
        raise DatasetRefusal("geometryId missing")
    role = record.get("role")
    if role not in ALLOWED_ROLES or expected_role_by_id.get(geometry_id) != role:
        raise DatasetRefusal(f"role changed or invalid for {geometry_id}")
    if record.get("classification") == "ADAPTIVE_CONTINUATION_REQUIRED":
        raise DatasetRefusal(f"adaptive continuation geometry forbidden: {geometry_id}")
    case_ids = record.get("caseIds")
    if not isinstance(case_ids, list) or len(case_ids) != 2 or len(set(case_ids)) != 2 or any(not isinstance(item, str) or not item for item in case_ids):
        raise DatasetRefusal(f"case IDs missing or duplicated for {geometry_id}")
    source_bindings = record.get("sourceBindings")
    if not isinstance(source_bindings, dict):
        raise DatasetRefusal(f"source bindings missing for {geometry_id}")
    for key in ("manifestRawSha256", "aggregateRawSha256", "auditRawSha256"):
        require_sha256(source_bindings.get(key), f"{geometry_id}.{key}")
    geometry = record.get("geometry")
    if not isinstance(geometry, dict):
        raise DatasetRefusal(f"geometry missing for {geometry_id}")
    for key in ("sunDepressionDeg", "targetAltitudeDeg", "relativeAzimuthDeg", "observerElevationM", "aod550"):
        finite_number(geometry.get(key), f"{geometry_id}.{key}", nonnegative=True)
    statistics = record.get("statistics")
    if not isinstance(statistics, dict):
        raise DatasetRefusal(f"statistics missing for {geometry_id}")
    finite_number(statistics.get("meanCdM2"), f"{geometry_id}.meanCdM2", positive=True)
    finite_number(statistics.get("sampleStdCdM2"), f"{geometry_id}.sampleStdCdM2", nonnegative=True)
    finite_number(statistics.get("relativeStandardErrorOfMean"), f"{geometry_id}.rsem", nonnegative=True)
    nodes = statistics.get("nodeMeanRadiance")
    if not isinstance(nodes, list) or len(nodes) != 15:
        raise DatasetRefusal(f"node radiance missing for {geometry_id}")
    for index, node in enumerate(nodes):
        finite_number(node, f"{geometry_id}.node[{index}]", positive=True)
    return geometry_id, role


def read_tier1_dataset(dataset_path: Path, envelope_path: Path, design_path: Path, *, expected_main_sha: str) -> PartitionedDataset:
    dataset, envelope, design = load_object(dataset_path), load_object(envelope_path), load_object(design_path)
    require_exact(dataset, {"schemaVersion": 2, "stageId": STAGE_ID, "status": DATASET_STATUS}, "dataset")
    require_exact(envelope, {
        "schemaVersion": 1,
        "stageId": "twilight-surrogate-tier-1-dataset-envelope-v1",
        "aggregatePassed": True,
        "independentAuditPassed": True,
        "precisionClassificationComplete": True,
        "provenanceValidated": True,
        "scientificExecution": True,
        "productionModelReady": False,
    }, "envelope")
    require_git_sha(expected_main_sha, "expected main sha")
    if envelope.get("exactMainSha") != expected_main_sha:
        raise DatasetRefusal("exact main SHA mismatch")
    if envelope.get("datasetRawSha256") != sha256_file(dataset_path):
        raise DatasetRefusal("dataset hash mismatch")
    bindings = envelope.get("bindings")
    if not isinstance(bindings, dict):
        raise DatasetRefusal("provenance bindings missing")
    for key in ("manifestRawSha256", "aggregateRawSha256", "independentAuditRawSha256", "analysisRawSha256", "designRawSha256"):
        require_sha256(bindings.get(key), key)
    if bindings["designRawSha256"] != sha256_file(design_path):
        raise DatasetRefusal("design hash mismatch")
    expected_roles = design.get("rolesByGeometryId")
    if not isinstance(expected_roles, dict) or len(expected_roles) != EXPECTED_GEOMETRY_COUNT:
        raise DatasetRefusal("frozen role map missing")
    records = dataset.get("records")
    if not isinstance(records, list) or len(records) != EXPECTED_GEOMETRY_COUNT:
        raise DatasetRefusal("geometry count mismatch")
    names = ("trainingGeometryIds", "internalHoldoutGeometryIds", "hardExternalAnchorIds", "softDiagnosticIds")
    values = [dataset.get(name) for name in names]
    for name, ids in zip(names, values, strict=True):
        if not isinstance(ids, list) or any(not isinstance(item, str) or not item for item in ids) or len(ids) != len(set(ids)):
            raise DatasetRefusal(f"{name} missing or duplicated")
    training_ids, holdout_ids, hard_anchor_ids, soft_ids = values
    partitions = [set(item) for item in values]
    for index, left in enumerate(partitions):
        for right in partitions[index + 1:]:
            if left & right:
                raise DatasetRefusal("dataset partitions overlap")
    if (set(hard_anchor_ids) | set(soft_ids)) & (set(training_ids) | set(holdout_ids)):
        raise DatasetRefusal("anchor or diagnostic appears inside fit/evaluation data")
    ids: set[str] = set()
    all_case_ids: set[str] = set()
    by_id: dict[str, dict[str, Any]] = {}
    for raw in records:
        if not isinstance(raw, dict):
            raise DatasetRefusal("record must be object")
        geometry_id, role = _validate_record(raw, expected_roles)
        if geometry_id in ids:
            raise DatasetRefusal(f"duplicate geometry ID: {geometry_id}")
        ids.add(geometry_id)
        for case_id in raw["caseIds"]:
            if case_id in all_case_ids:
                raise DatasetRefusal(f"duplicate case ID: {case_id}")
            all_case_ids.add(case_id)
        if role == TRAINING_ROLE and geometry_id not in set(training_ids):
            raise DatasetRefusal(f"training role/list mismatch: {geometry_id}")
        if role == HOLDOUT_ROLE and geometry_id not in set(holdout_ids):
            raise DatasetRefusal(f"holdout role/list mismatch: {geometry_id}")
        by_id[geometry_id] = raw
    if ids != set(training_ids) | set(holdout_ids):
        raise DatasetRefusal("record IDs differ from training plus holdout IDs")
    anchors = envelope.get("externalRecords")
    if not isinstance(anchors, list):
        raise DatasetRefusal("external records missing")
    external_by_id = {item.get("geometryId"): item for item in anchors if isinstance(item, dict)}
    if len(external_by_id) != len(anchors) or set(external_by_id) != set(hard_anchor_ids) | set(soft_ids):
        raise DatasetRefusal("external record IDs mismatch or duplicated")
    for anchor_id, item in external_by_id.items():
        finite_number(item.get("meanCdM2"), f"{anchor_id}.meanCdM2", positive=True)
        geometry = item.get("geometry")
        if not isinstance(geometry, dict):
            raise DatasetRefusal(f"external geometry missing: {anchor_id}")
        for key in ("sunDepressionDeg", "targetAltitudeDeg", "relativeAzimuthDeg", "observerElevationM", "aod550"):
            finite_number(geometry.get(key), f"{anchor_id}.{key}", nonnegative=True)
        if item.get("eligibleForTraining") is not False or item.get("eligibleForHyperparameterSelection") is not False:
            raise DatasetRefusal(f"external record eligibility invalid: {anchor_id}")
    return PartitionedDataset(
        source_dataset_hash=sha256_file(dataset_path), exact_main_sha=expected_main_sha,
        training=tuple(by_id[item] for item in training_ids),
        internal_holdout=tuple(by_id[item] for item in holdout_ids),
        hard_anchors=tuple(external_by_id[item] for item in hard_anchor_ids),
        soft_diagnostics=tuple(external_by_id[item] for item in soft_ids),
        excluded_ids=tuple(sorted(set(hard_anchor_ids) | set(soft_ids))),
        provenance={"envelopeHash": sha256_file(envelope_path), "bindings": bindings},
    )
