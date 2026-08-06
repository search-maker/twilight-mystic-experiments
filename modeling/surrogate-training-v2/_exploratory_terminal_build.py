from __future__ import annotations

import copy
import importlib.util
import math
import statistics
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
analysis = _load("_exploratory_terminal_analysis")
inputs = _load("_exploratory_terminal_inputs")
Refusal = core.Refusal
module = core.module
load = core.load
raw_sha256 = core.raw_sha256
canonical_sha256 = core.canonical_sha256
MODEL_PATH = core.MODEL_PATH
SOURCE_DATASET_SHA256 = core.SOURCE_DATASET_SHA256
SOURCE_DATASET_RAW_SHA256 = core.SOURCE_DATASET_RAW_SHA256
OUTPUT_STAGE = core.OUTPUT_STAGE
OUTPUT_STATUS = core.OUTPUT_STATUS
TRAINING_IDS = core.TRAINING_IDS
HOLDOUT_IDS = core.HOLDOUT_IDS
WAVE3_TRAINING_IDS = core.WAVE3_TRAINING_IDS
ELIGIBLE = core.ELIGIBLE
EXHAUSTED = core.EXHAUSTED
_close = core._close
load_training_points = analysis.load_training_points
validate_source_dataset = inputs.validate_source_dataset
load_wave3_training_results = inputs.load_wave3_training_results

def updated_record(source: dict[str, Any], point: dict[str, Any], pair: dict[int, dict[str, Any]], source_binding: dict[str, Any]) -> dict[str, Any]:
    geometry_id = source["geometryId"]
    classification = point.get("classification")
    if classification not in ELIGIBLE | EXHAUSTED or point.get("blockCount") != 8:
        raise Refusal(f"terminal training point classification changed: {geometry_id}")
    values = point.get("valuesCdM2")
    nonzero = point.get("nonzeroBlockValuesCdM2")
    if not isinstance(values, list) or len(values) != 8 or not isinstance(nonzero, list):
        raise Refusal(f"terminal training point values incomplete: {geometry_id}")
    for offset, block in enumerate((7, 8), start=6):
        result = pair[block]
        if not _close(float(values[offset]), float(result["selectedPhotopicContributionCdM2"])):
            raise Refusal(f"terminal analysis/result value mismatch: {geometry_id} b{block}")
    source_stats = source.get("statistics")
    source_nodes = source_stats.get("nodeMeanRadiance") if isinstance(source_stats, dict) else None
    if not isinstance(source_nodes, list) or len(source_nodes) != 15 or source_stats.get("blockCount") != 6:
        raise Refusal(f"source b1-b6 training statistics changed: {geometry_id}")
    nodes7 = [float(value) for value in pair[7]["selectedNodeRadiance"]]
    nodes8 = [float(value) for value in pair[8]["selectedNodeRadiance"]]
    node_mean = [(6.0 * float(old) + left + right) / 8.0 for old, left, right in zip(source_nodes, nodes7, nodes8, strict=True)]
    parsed_values = [float(value) for value in values]
    mean = statistics.fmean(parsed_values)
    sample_std = statistics.stdev(parsed_values)
    zero_count = point.get("zeroHitBlockCount")
    if not isinstance(zero_count, int) or isinstance(zero_count, bool) or not 0 <= zero_count <= 8:
        raise Refusal(f"terminal zero-hit count invalid: {geometry_id}")
    rsem = point.get("relativeStandardErrorOfMean")
    rsem_status = point.get("relativeStandardErrorStatus")
    if zero_count:
        if rsem is not None or rsem_status != "NOT_COMPUTED_ZERO_HIT_PRESENT":
            raise Refusal(f"terminal zero-hit RSEM semantics changed: {geometry_id}")
        parsed_rsem: float | None = None
    else:
        if (
            isinstance(rsem, bool)
            or not isinstance(rsem, (int, float))
            or not math.isfinite(float(rsem))
            or rsem_status != "COMPUTED"
        ):
            raise Refusal(f"terminal RSEM missing: {geometry_id}")
        parsed_rsem = float(rsem)
    eligible = classification in ELIGIBLE
    if point.get("scientificallyEligible") is not eligible:
        raise Refusal(f"terminal point eligibility mismatch: {geometry_id}")
    exhausted_ids = set(source_binding["exhaustedGeometryIds"])
    if (geometry_id in exhausted_ids) is not (classification in EXHAUSTED):
        raise Refusal(f"terminal source binding/classification mismatch: {geometry_id}")
    record = copy.deepcopy(source)
    record["caseIds"] = list(source["caseIds"]) + [pair[7]["caseId"], pair[8]["caseId"]]
    record["classification"] = classification
    record["numericalStatus"] = point.get("numericalStatus")
    record["scientificallyEligible"] = eligible
    record["eligibleForProvisionalFit"] = eligible
    record["statistics"] = {
        "blockCount": 8,
        "valuesCdM2": parsed_values,
        "meanCdM2": mean,
        "sampleStdCdM2": sample_std,
        "relativeStandardErrorOfMean": parsed_rsem,
        "relativeStandardErrorStatus": rsem_status,
        "zeroHitBlockCount": zero_count,
        "zeroHitBlockFraction": float(point.get("zeroHitBlockFraction")),
        "nonzeroBlockValuesCdM2": [float(value) for value in nonzero],
        "nodeMeanRadiance": node_mean,
    }
    source_zero_ids = source.get("zeroHitCaseIds")
    if not isinstance(source_zero_ids, list) or any(not isinstance(case_id, str) for case_id in source_zero_ids):
        raise Refusal(f"source zero-hit case identities changed: {geometry_id}")
    if len(source_zero_ids) != len(set(source_zero_ids)) or any(case_id not in source["caseIds"] for case_id in source_zero_ids):
        raise Refusal(f"source zero-hit case identities invalid: {geometry_id}")
    wave3_zero_ids = [pair[block]["caseId"] for block in (7, 8) if pair[block].get("zeroHit")]
    combined_zero_ids = list(source_zero_ids) + wave3_zero_ids
    if len(combined_zero_ids) != len(set(combined_zero_ids)) or len(combined_zero_ids) != zero_count:
        raise Refusal(f"terminal zero-hit case identity/count mismatch: {geometry_id}")
    record["zeroHitCaseIds"] = combined_zero_ids
    bindings = dict(record.get("sourceBindings") or {})
    bindings["terminalSourceBindingSha256"] = source_binding["bindingSha256"]
    bindings["terminalAnalysisRawSha256"] = source_binding["analysisRawSha256"]
    bindings["wave3CaseResultContentSha256ByCaseId"] = {pair[block]["caseId"]: pair[block]["contentSha256"] for block in (7, 8)}
    record["sourceBindings"] = bindings
    return record


def build(
    repository_root: Path,
    source_dataset_path: Path,
    source_binding_path: Path,
    analysis_path: Path,
    results_root: Path,
    *,
    expected_source_dataset_sha256: str = SOURCE_DATASET_SHA256,
    expected_source_dataset_raw_sha256: str = SOURCE_DATASET_RAW_SHA256,
) -> dict[str, Any]:
    model = module(repository_root.resolve() / MODEL_PATH, "exploratory_terminal_dataset_model_contract")
    source_binding = load(source_binding_path)
    model.validate_source_binding(source_binding)
    if raw_sha256(source_dataset_path) != expected_source_dataset_raw_sha256:
        raise Refusal("exact b1-b6 source training dataset raw hash changed")
    source_rows = validate_source_dataset(
        load(source_dataset_path),
        expected_dataset_sha256=expected_source_dataset_sha256,
    )
    points = load_training_points(analysis_path, source_binding)
    results = load_wave3_training_results(results_root)
    output_rows: list[dict[str, Any]] = []
    for source in source_rows:
        geometry_id = source["geometryId"]
        if geometry_id in WAVE3_TRAINING_IDS:
            output_rows.append(updated_record(source, points[geometry_id], results[geometry_id], source_binding))
        else:
            output_rows.append(copy.deepcopy(source))
    exhausted_training = sorted(row["geometryId"] for row in output_rows if row.get("classification") in EXHAUSTED)
    expected_exhausted_training = sorted(gid for gid in source_binding["exhaustedGeometryIds"] if gid in TRAINING_IDS)
    if exhausted_training != expected_exhausted_training:
        raise Refusal("final training exhausted set does not match terminal source binding")
    value: dict[str, Any] = {
        "schemaVersion": 1,
        "stageId": OUTPUT_STAGE,
        "status": OUTPUT_STATUS,
        "sourceBindingSha256": source_binding["bindingSha256"],
        "sourceTrainingDatasetRawSha256": raw_sha256(source_dataset_path),
        "sourceTrainingDatasetSha256": expected_source_dataset_sha256,
        "terminalAnalysisRawSha256": raw_sha256(analysis_path),
        "trainingGeometryIds": list(TRAINING_IDS),
        "internalHoldoutGeometryIdsExcludedAndUnopened": list(HOLDOUT_IDS),
        "holdoutRecordCount": 0,
        "holdoutValuesIncluded": False,
        "records": output_rows,
    }
    value["datasetSha256"] = canonical_sha256(value)
    model.validate_training_dataset(value, source_binding)
    return value
