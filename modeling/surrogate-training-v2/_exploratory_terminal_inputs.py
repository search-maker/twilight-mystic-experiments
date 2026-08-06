from __future__ import annotations

import importlib.util
import math
from pathlib import Path
from typing import Any

def _load(name: str):
    path = Path(__file__).with_name(name + ".py")
    spec = importlib.util.spec_from_file_location("exploratory_terminal_" + name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

core = _load("_exploratory_terminal_core")
Refusal = core.Refusal
canonical_sha256 = core.canonical_sha256
load = core.load
_close = core._close
_photopic = core._photopic
SOURCE_STAGE = core.SOURCE_STAGE
SOURCE_STATUS = core.SOURCE_STATUS
TRAINING_IDS = core.TRAINING_IDS
HOLDOUT_IDS = core.HOLDOUT_IDS
WAVE3_TRAINING_IDS = core.WAVE3_TRAINING_IDS
RESULT_STAGE = core.RESULT_STAGE

def validate_source_dataset(value: dict[str, Any]) -> list[dict[str, Any]]:
    seal = value.get("datasetSha256")
    payload = {key: item for key, item in value.items() if key != "datasetSha256"}
    if seal != canonical_sha256(payload):
        raise Refusal("source training dataset self-hash changed")
    expected = {
        "schemaVersion": 1,
        "stageId": SOURCE_STAGE,
        "status": SOURCE_STATUS,
        "trainingGeometryIds": list(TRAINING_IDS),
        "internalHoldoutGeometryIdsExcludedAndUnopened": list(HOLDOUT_IDS),
        "holdoutRecordCount": 0,
        "holdoutValuesIncluded": False,
    }
    stale = {key: (value.get(key), wanted) for key, wanted in expected.items() if value.get(key) != wanted}
    if stale:
        raise Refusal(f"source training dataset boundary changed: {stale}")
    rows = value.get("records")
    if not isinstance(rows, list) or len(rows) != len(TRAINING_IDS):
        raise Refusal("source training dataset must contain 39 records")
    ids = [row.get("geometryId") for row in rows if isinstance(row, dict)]
    if ids != list(TRAINING_IDS) or len(set(ids)) != len(TRAINING_IDS):
        raise Refusal("source training identities or order changed")
    if any(row.get("role") != "surrogate-training" for row in rows):
        raise Refusal("source training dataset contains a non-training record")
    return rows


def load_wave3_training_results(root: Path) -> dict[str, dict[int, dict[str, Any]]]:
    paths = sorted(root.rglob("case-result.json"))
    expected_count = 2 * len(WAVE3_TRAINING_IDS)
    if len(paths) != expected_count:
        raise Refusal(f"expected {expected_count} wave-three training results, found {len(paths)}")
    grouped: dict[str, dict[int, dict[str, Any]]] = {}
    for path in paths:
        row = load(path)
        geometry_id = row.get("groupId")
        block = row.get("block")
        if geometry_id not in WAVE3_TRAINING_IDS or block not in {7, 8}:
            raise Refusal(f"unplanned wave-three training result: {row.get('caseId')}")
        if block in grouped.setdefault(geometry_id, {}):
            raise Refusal(f"duplicate wave-three training block: {geometry_id} b{block}")
        payload = {key: item for key, item in row.items() if key != "contentSha256"}
        if row.get("contentSha256") != canonical_sha256(payload):
            raise Refusal(f"wave-three training result content hash changed: {row.get('caseId')}")
        nodes = row.get("selectedNodeRadiance")
        value = row.get("selectedPhotopicContributionCdM2")
        if (
            row.get("stageId") != RESULT_STAGE
            or row.get("status") != "COMPLETED"
            or row.get("role") != "surrogate-training"
            or row.get("syntaxCheckCount") != 1
            or row.get("solverExecutionCount") != 1
            or row.get("retryAllowed") is not False
            or row.get("resumeAllowed") is not False
            or row.get("fittingSurfaceExposed") is not False
            or not isinstance(nodes, list)
            or len(nodes) != 15
            or any(isinstance(node, bool) or not isinstance(node, (int, float)) or not math.isfinite(float(node)) or float(node) < 0 for node in nodes)
            or isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            or float(value) < 0
        ):
            raise Refusal(f"wave-three training execution proof changed: {row.get('caseId')}")
        parsed_nodes = [float(node) for node in nodes]
        if not _close(float(value), _photopic(parsed_nodes)):
            raise Refusal(f"wave-three photopic value differs from selected nodes: {row.get('caseId')}")
        zero_hit = float(value) == 0.0 and all(node == 0.0 for node in parsed_nodes)
        if row.get("zeroHit") is not zero_hit:
            raise Refusal(f"wave-three zero-hit semantics changed: {row.get('caseId')}")
        grouped[geometry_id][int(block)] = row
    if tuple(sorted(grouped)) != tuple(sorted(WAVE3_TRAINING_IDS)) or any(set(pair) != {7, 8} for pair in grouped.values()):
        raise Refusal("wave-three training result matrix incomplete")
    return grouped
