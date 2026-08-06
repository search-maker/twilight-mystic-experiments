#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


class FinalModelRefusal(RuntimeError):
    pass


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_sha256(value: Any, label: str, length: int = 64) -> str:
    if (
        not isinstance(value, str)
        or len(value) != length
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise FinalModelRefusal(f"{label} must be lowercase hex length {length}")
    return value


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FinalModelRefusal(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise FinalModelRefusal(f"expected object: {path}")
    return value


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise FinalModelRefusal(f"module unavailable: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def validate_protocol(protocol: dict[str, Any]) -> None:
    expected = {
        "schemaVersion": 1,
        "stageId": "surrogate-training-v2-candidate-protocol-v1",
        "frozenBeforeInternalHoldout": True,
        "syntheticSuccessDoesNotSelectMysticModelFamily": True,
    }
    stale = {
        key: (protocol.get(key), value)
        for key, value in expected.items()
        if protocol.get(key) != value
    }
    if stale:
        raise FinalModelRefusal(f"candidate protocol changed: {stale}")
    candidates = protocol.get("candidates")
    if not isinstance(candidates, list) or len(candidates) != 3:
        raise FinalModelRefusal("candidate protocol must contain exactly three families")
    candidate_ids = [item.get("candidateId") for item in candidates if isinstance(item, dict)]
    if candidate_ids != [
        "transparent-log-mean-baseline",
        "fixed-basis-log-ridge",
        "local-log-idw",
    ]:
        raise FinalModelRefusal("candidate family ordering changed")
    boundary = protocol.get("productionBoundary")
    if not isinstance(boundary, dict) or boundary.get("productionPromotionAuthorized") is not False:
        raise FinalModelRefusal("candidate protocol production boundary changed")
    if protocol.get("evaluationOrder") != [
        "training-cross-validation",
        "freeze-model-and-thresholds",
        "internal-holdout-once",
        "hard-external-anchors",
        "g01-soft-diagnostic-report-only",
    ]:
        raise FinalModelRefusal("evaluation order changed")


def model_state_value(model: Any, artifact: dict[str, Any]) -> dict[str, Any]:
    value = {
        "schemaVersion": 1,
        "stageId": "surrogate-training-v2-serialized-model-state-v1",
        "status": "MODEL_STATE_FROZEN",
        "generatedModelHash": artifact["generatedModelHash"],
        "candidateId": model.candidate_id,
        "hyperparameters": model.hyperparameters,
        "normalizationConstants": {
            "minimums": model.lows,
            "maximums": model.highs,
        },
        "state": model.state,
        "residualRmse": model.residual_rmse,
        "featureList": artifact["featureList"],
        "targetTransformation": "natural-log",
        "trainingIds": artifact["trainingIds"],
        "holdoutIds": artifact["holdoutIds"],
        "anchorIds": artifact["anchorIds"],
        "softDiagnosticIds": artifact["softDiagnosticIds"],
        "internalHoldoutOpened": False,
        "productionModelReady": False,
        "productionPromotionAuthorized": False,
    }
    value["modelStateSha256"] = canonical_sha256(value)
    return value


def validate_partition(artifact: dict[str, Any], partitioned: Any) -> None:
    training_ids = sorted(item["geometryId"] for item in partitioned.training)
    holdout_ids = sorted(item["geometryId"] for item in partitioned.internal_holdout)
    hard_ids = sorted(item["geometryId"] for item in partitioned.hard_anchors)
    soft_ids = sorted(item["geometryId"] for item in partitioned.soft_diagnostics)
    if (len(training_ids), len(holdout_ids), len(hard_ids), len(soft_ids)) != (42, 6, 5, 1):
        raise FinalModelRefusal("final model partition cardinality changed")
    if set(training_ids) & set(holdout_ids):
        raise FinalModelRefusal("training and holdout partitions overlap")
    if set(training_ids) & (set(hard_ids) | set(soft_ids)):
        raise FinalModelRefusal("external anchors leaked into training")
    if artifact.get("trainingIds") != training_ids:
        raise FinalModelRefusal("frozen artifact training IDs changed")
    if artifact.get("holdoutIds") != holdout_ids:
        raise FinalModelRefusal("frozen artifact holdout IDs changed")
    if artifact.get("anchorIds") != hard_ids:
        raise FinalModelRefusal("frozen artifact hard-anchor IDs changed")
    if artifact.get("softDiagnosticIds") != soft_ids:
        raise FinalModelRefusal("frozen artifact soft-diagnostic IDs changed")
    if artifact.get("status") != "MODEL_FROZEN_BEFORE_INTERNAL_HOLDOUT":
        raise FinalModelRefusal("model was not frozen before holdout")
    if artifact.get("internalHoldoutOpened") is not False:
        raise FinalModelRefusal("holdout opened before artifact freeze")


def run_pipeline(
    dataset_path: Path,
    envelope_path: Path,
    design_path: Path,
    protocol_path: Path,
    output_dir: Path,
    *,
    expected_main_sha: str,
    repository_root: Path,
) -> dict[str, Path]:
    require_sha256(expected_main_sha, "expected main SHA", 40)
    repository_root = repository_root.resolve()
    model_dir = repository_root / "modeling/surrogate-training-v2"
    adapter_path = model_dir / "adapter.py"
    training_path = model_dir / "training.py"
    runtime_path = model_dir / "model_runtime.py"
    pipeline_path = model_dir / "final_model_pipeline.py"
    for path in (adapter_path, training_path, runtime_path, pipeline_path, protocol_path):
        if not path.is_file():
            raise FinalModelRefusal(f"required source missing: {path}")

    adapter = load_module(adapter_path, "surrogate_training_v2_final_adapter")
    training = load_module(training_path, "surrogate_training_v2_final_training")
    protocol = load_json(protocol_path)
    validate_protocol(protocol)
    partitioned = adapter.read_tier1_dataset(
        dataset_path,
        envelope_path,
        design_path,
        expected_main_sha=expected_main_sha,
    )
    source_code_hashes = {
        "adapterRawSha256": raw_sha256(adapter_path),
        "trainingRawSha256": raw_sha256(training_path),
        "runtimeRawSha256": raw_sha256(runtime_path),
        "pipelineRawSha256": raw_sha256(pipeline_path),
        "protocolRawSha256": raw_sha256(protocol_path),
    }
    model, artifact = training.freeze_artifact(protocol, partitioned, source_code_hashes)
    validate_partition(artifact, partitioned)
    state = model_state_value(model, artifact)

    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = output_dir / "frozen-model-artifact.json"
    state_path = output_dir / "model-state.json"
    artifact_path.write_text(dump(artifact), encoding="utf-8", newline="\n")
    state_path.write_text(dump(state), encoding="utf-8", newline="\n")

    artifact_raw_sha = raw_sha256(artifact_path)
    state_raw_sha = raw_sha256(state_path)
    holdout = training.open_internal_holdout_once(
        model, artifact, list(partitioned.internal_holdout)
    )
    if holdout.get("selectionForbidden") is not True or holdout.get("thresholdTuningForbidden") is not True:
        raise FinalModelRefusal("holdout selection boundary changed")
    if holdout.get("count") != 6:
        raise FinalModelRefusal("holdout count changed")
    external = training.evaluate_external(
        model,
        artifact,
        list(partitioned.hard_anchors),
        list(partitioned.soft_diagnostics),
    )
    if len(external.get("hardAnchors", [])) != 5 or len(external.get("softDiagnostics", [])) != 1:
        raise FinalModelRefusal("external evaluation cardinality changed")
    if external.get("softDiagnosticsReportOnly") is not True:
        raise FinalModelRefusal("soft diagnostic became a decision gate")
    if external.get("productionPromotionAuthorized") is not False:
        raise FinalModelRefusal("external evaluation authorized production")

    holdout_path = output_dir / "internal-holdout-evaluation.json"
    external_path = output_dir / "external-anchor-evaluation.json"
    holdout_path.write_text(dump(holdout), encoding="utf-8", newline="\n")
    external_path.write_text(dump(external), encoding="utf-8", newline="\n")

    package = {
        "schemaVersion": 1,
        "stageId": "surrogate-training-v2-final-model-package-v1",
        "status": "MODEL_TRAINED_AND_EVALUATED",
        "generatedModelHash": artifact["generatedModelHash"],
        "modelStateSha256": state["modelStateSha256"],
        "sourceDatasetHash": partitioned.source_dataset_hash,
        "exactScientificSourceMainSha": expected_main_sha,
        "selectedCandidate": artifact["candidateId"],
        "selectedModelFamily": artifact["modelFamily"],
        "selectedHyperparameters": artifact["hyperparameters"],
        "trainingGeometryCount": len(partitioned.training),
        "internalHoldoutGeometryCount": len(partitioned.internal_holdout),
        "hardAnchorCount": len(partitioned.hard_anchors),
        "softDiagnosticCount": len(partitioned.soft_diagnostics),
        "trainingIds": artifact["trainingIds"],
        "holdoutIds": artifact["holdoutIds"],
        "hardAnchorIds": artifact["anchorIds"],
        "softDiagnosticIds": artifact["softDiagnosticIds"],
        "trainingCrossValidation": artifact["selectedCrossValidation"],
        "internalHoldoutMetrics": {
            "meanAbsoluteLogError": holdout["meanAbsoluteLogError"],
            "maximumAbsoluteLogError": holdout["maximumAbsoluteLogError"],
        },
        "hardAnchorMetrics": {
            "meanAbsoluteLogError": sum(
                row["absoluteLogError"] for row in external["hardAnchors"]
            )
            / len(external["hardAnchors"]),
            "maximumAbsoluteLogError": max(
                row["absoluteLogError"] for row in external["hardAnchors"]
            ),
        },
        "softDiagnosticReportOnly": True,
        "bindings": {
            "datasetRawSha256": raw_sha256(dataset_path),
            "envelopeRawSha256": raw_sha256(envelope_path),
            "designRawSha256": raw_sha256(design_path),
            "protocolRawSha256": raw_sha256(protocol_path),
            "frozenArtifactRawSha256": artifact_raw_sha,
            "modelStateRawSha256": state_raw_sha,
            "holdoutEvaluationRawSha256": raw_sha256(holdout_path),
            "externalEvaluationRawSha256": raw_sha256(external_path),
            **source_code_hashes,
        },
        "evaluationOrderCompleted": [
            "training-cross-validation",
            "freeze-model-and-thresholds",
            "internal-holdout-once",
            "hard-external-anchors",
            "g01-soft-diagnostic-report-only",
        ],
        "modelUsableForPrediction": True,
        "internalHoldoutOpenedExactlyOnce": True,
        "holdoutUsedForSelection": False,
        "holdoutUsedForThresholdTuning": False,
        "externalAnchorsUsedForSelection": False,
        "observationallyValidated": False,
        "productionModelReady": False,
        "productionPromotionAuthorized": False,
        "tier2Authorized": False,
        "boundary": "trained and evaluated research surrogate; prediction runtime available; observational validation and production promotion remain separate",
    }
    package["modelPackageSha256"] = canonical_sha256(package)
    package_path = output_dir / "final-model-package.json"
    package_path.write_text(dump(package), encoding="utf-8", newline="\n")
    return {
        "artifact": artifact_path,
        "state": state_path,
        "holdout": holdout_path,
        "external": external_path,
        "package": package_path,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--envelope", type=Path, required=True)
    parser.add_argument("--design", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--expected-main-sha", required=True)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        outputs = run_pipeline(
            args.dataset,
            args.envelope,
            args.design,
            args.protocol,
            args.output_dir,
            expected_main_sha=args.expected_main_sha,
            repository_root=args.repository_root,
        )
        print(
            dump(
                {
                    "status": "SURROGATE_MODEL_TRAINED_AND_EVALUATED",
                    "outputs": {key: str(path) for key, path in outputs.items()},
                }
            ),
            end="",
        )
        return 0
    except Exception as exc:
        print(dump({"status": "REFUSED", "reason": str(exc)}), end="", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
