#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any

ADAPTER_PATH = "modeling/surrogate-training-v2/adapter.py"
TRAINING_PATH = "modeling/surrogate-training-v2/training.py"
HANDOFF_PATH = "modeling/surrogate-training-v2/continuation_handoff.py"
PROTOCOL_STAGE_ID = "surrogate-training-v2-candidate-protocol-v1"
EXPECTED_EVALUATION_ORDER = [
    "training-cross-validation",
    "freeze-model-and-thresholds",
    "internal-holdout-once",
    "hard-external-anchors",
    "g01-soft-diagnostic-report-only",
]


class ModelRunRefusal(RuntimeError):
    pass


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ModelRunRefusal(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ModelRunRefusal(f"expected object: {path}")
    return value


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ModelRunRefusal(f"module unavailable: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def validate_protocol(protocol: dict[str, Any], training: Any) -> None:
    expected = {
        "schemaVersion": 1,
        "stageId": PROTOCOL_STAGE_ID,
        "frozenBeforeInternalHoldout": True,
        "syntheticSuccessDoesNotSelectMysticModelFamily": True,
        "features": list(training.FEATURES),
        "targetTransformation": "natural-log-positive-photopic-luminance",
        "evaluationOrder": EXPECTED_EVALUATION_ORDER,
    }
    stale = {
        key: (protocol.get(key), value)
        for key, value in expected.items()
        if protocol.get(key) != value
    }
    if stale:
        raise ModelRunRefusal(f"candidate protocol changed: {stale}")
    candidates = protocol.get("candidates")
    if (
        not isinstance(candidates, list)
        or [candidate.get("candidateId") for candidate in candidates if isinstance(candidate, dict)]
        != [
            "transparent-log-mean-baseline",
            "fixed-basis-log-ridge",
            "local-log-idw",
        ]
    ):
        raise ModelRunRefusal("candidate family universe changed")
    production = protocol.get("productionBoundary")
    if not isinstance(production, dict) or production != {
        "productionPromotionAuthorized": False,
        "productionModelReady": False,
        "observationalValidationRequired": True,
        "calibrationObservationsForbidden": True,
        "validationObservationsForbidden": True,
    }:
        raise ModelRunRefusal("production boundary changed")


def _frozen_artifact(training: Any, model: Any, artifact: dict[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(artifact)
    value.pop("generatedModelHash", None)
    value["serializationVersion"] = 1
    value["modelState"] = copy.deepcopy(model.state)
    value["residualRmseLog"] = float(model.residual_rmse)
    value["internalHoldoutOpened"] = False
    value["hardAnchorsOpened"] = False
    value["generatedModelHash"] = training.sha256_text(training.dump(value))
    return value


def restore_model(training: Any, artifact: dict[str, Any]) -> Any:
    supplied = artifact.get("generatedModelHash")
    payload = {key: item for key, item in artifact.items() if key != "generatedModelHash"}
    if supplied != training.sha256_text(training.dump(payload)):
        raise ModelRunRefusal("serialized model artifact hash changed")
    if artifact.get("status") != "MODEL_FROZEN_BEFORE_INTERNAL_HOLDOUT":
        raise ModelRunRefusal("model was not frozen before holdout")
    state = artifact.get("modelState")
    if not isinstance(state, dict):
        raise ModelRunRefusal("serialized model state missing")
    residual = artifact.get("residualRmseLog")
    if isinstance(residual, bool) or not isinstance(residual, (int, float)) or not math.isfinite(float(residual)) or residual < 0:
        raise ModelRunRefusal("serialized residual RMSE invalid")
    return training.Model(
        candidate_id=artifact["candidateId"],
        hyperparameters=copy.deepcopy(artifact["hyperparameters"]),
        lows=[float(value) for value in artifact["normalizationConstants"]["minimums"]],
        highs=[float(value) for value in artifact["normalizationConstants"]["maximums"]],
        state=copy.deepcopy(state),
        residual_rmse=float(residual),
    )


def _prove_restoration(training: Any, original: Any, restored: Any, records: list[dict[str, Any]]) -> None:
    for record in records:
        left = original.predict(record)
        right = restored.predict(record)
        if left.keys() != right.keys():
            raise ModelRunRefusal("restored model prediction schema changed")
        for key in left:
            if isinstance(left[key], bool):
                if left[key] is not right[key]:
                    raise ModelRunRefusal(f"restored boolean prediction changed: {record['geometryId']} {key}")
            elif not math.isclose(float(left[key]), float(right[key]), rel_tol=1e-15, abs_tol=1e-15):
                raise ModelRunRefusal(f"restored prediction changed: {record['geometryId']} {key}")


def run(
    *,
    repository_root: Path,
    dataset_path: Path,
    envelope_path: Path,
    design_path: Path,
    protocol_path: Path,
    exact_main_sha: str,
    output_dir: Path,
) -> dict[str, Path]:
    repository_root = repository_root.resolve()
    adapter = load_module(repository_root / ADAPTER_PATH, "continuation_model_adapter")
    training = load_module(repository_root / TRAINING_PATH, "continuation_model_training")
    protocol = load_json(protocol_path)
    validate_protocol(protocol, training)
    partitioned = adapter.read_tier1_dataset(
        dataset_path,
        envelope_path,
        design_path,
        expected_main_sha=exact_main_sha,
    )
    if len(partitioned.training) != 39 or len(partitioned.internal_holdout) != 9:
        raise ModelRunRefusal("frozen 39/9 partition changed")
    source_hashes = {
        ADAPTER_PATH: raw_sha256(repository_root / ADAPTER_PATH),
        TRAINING_PATH: raw_sha256(repository_root / TRAINING_PATH),
        HANDOFF_PATH: raw_sha256(repository_root / HANDOFF_PATH),
        "modeling/surrogate-training-v2/continuation_training.py": raw_sha256(
            repository_root / "modeling/surrogate-training-v2/continuation_training.py"
        ),
        "modeling/surrogate-training-v2/candidate-protocol.json": raw_sha256(protocol_path),
    }
    model, base_artifact = training.freeze_artifact(
        protocol,
        partitioned,
        source_hashes,
    )
    artifact = _frozen_artifact(training, model, base_artifact)
    restored = restore_model(training, artifact)
    _prove_restoration(training, model, restored, list(partitioned.training))
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = output_dir / "model-artifact.json"
    artifact_path.write_text(dump(artifact), encoding="utf-8", newline="\n")

    selection = {
        "schemaVersion": 1,
        "stageId": "surrogate-training-v2-training-selection-v1",
        "status": "TRAINING_ONLY_SELECTION_COMPLETE_MODEL_FROZEN",
        "modelHash": artifact["generatedModelHash"],
        "trainingGeometryCount": len(partitioned.training),
        "trainingGeometryIds": sorted(record["geometryId"] for record in partitioned.training),
        "internalHoldoutGeometryIdsExcludedFromSelection": sorted(
            record["geometryId"] for record in partitioned.internal_holdout
        ),
        "hardAnchorIdsExcludedFromSelection": sorted(record["geometryId"] for record in partitioned.hard_anchors),
        "softDiagnosticIdsExcludedFromSelection": sorted(
            record["geometryId"] for record in partitioned.soft_diagnostics
        ),
        "selectedCandidate": copy.deepcopy(artifact["selectedCrossValidation"]),
        "allCandidateCrossValidation": copy.deepcopy(artifact["trainingCrossValidation"]),
        "internalHoldoutOpened": False,
        "thresholdTuningFromHoldoutForbidden": True,
    }
    selection["selectionSha256"] = canonical_sha256(selection)
    selection_path = output_dir / "training-selection.json"
    selection_path.write_text(dump(selection), encoding="utf-8", newline="\n")

    holdout = training.open_internal_holdout_once(
        restored,
        artifact,
        list(partitioned.internal_holdout),
    )
    if holdout.get("count") != 9 or holdout.get("selectionForbidden") is not True or holdout.get("thresholdTuningForbidden") is not True:
        raise ModelRunRefusal("internal holdout boundary changed")
    holdout["openedAfterModelArtifactRawSha256"] = raw_sha256(artifact_path)
    holdout["openedAfterSelectionRawSha256"] = raw_sha256(selection_path)
    holdout["internalHoldoutOpenedExactlyOnceByThisRun"] = True
    holdout["holdoutSha256"] = canonical_sha256(holdout)
    holdout_path = output_dir / "internal-holdout.json"
    holdout_path.write_text(dump(holdout), encoding="utf-8", newline="\n")

    external = training.evaluate_external(
        restored,
        artifact,
        list(partitioned.hard_anchors),
        list(partitioned.soft_diagnostics),
    )
    if len(external.get("hardAnchors", [])) != 5 or len(external.get("softDiagnostics", [])) != 1:
        raise ModelRunRefusal("external anchor universe changed")
    if external.get("softDiagnosticsReportOnly") is not True or external.get("productionPromotionAuthorized") is not False:
        raise ModelRunRefusal("external evaluation boundary changed")
    external["openedAfterInternalHoldoutRawSha256"] = raw_sha256(holdout_path)
    external["externalEvaluationSha256"] = canonical_sha256(external)
    external_path = output_dir / "external-evaluation.json"
    external_path.write_text(dump(external), encoding="utf-8", newline="\n")

    report = {
        "schemaVersion": 1,
        "stageId": "surrogate-training-v2-continuation-model-run-v1",
        "status": "MODEL_TRAINED_FROZEN_AND_EVALUATED_NOT_PRODUCTION_READY",
        "exactMainSha": exact_main_sha,
        "sourceDatasetRawSha256": raw_sha256(dataset_path),
        "sourceEnvelopeRawSha256": raw_sha256(envelope_path),
        "sourceDesignRawSha256": raw_sha256(design_path),
        "candidateProtocolRawSha256": raw_sha256(protocol_path),
        "modelArtifactRawSha256": raw_sha256(artifact_path),
        "modelHash": artifact["generatedModelHash"],
        "selectedCandidateId": artifact["candidateId"],
        "selectedHyperparameters": artifact["hyperparameters"],
        "trainingCrossValidationMeanAbsoluteLogError": artifact["selectedCrossValidation"]["meanAbsoluteLogError"],
        "trainingCrossValidationMaximumAbsoluteLogError": artifact["selectedCrossValidation"]["maximumAbsoluteLogError"],
        "internalHoldoutRawSha256": raw_sha256(holdout_path),
        "internalHoldoutMeanAbsoluteLogError": holdout["meanAbsoluteLogError"],
        "internalHoldoutMaximumAbsoluteLogError": holdout["maximumAbsoluteLogError"],
        "externalEvaluationRawSha256": raw_sha256(external_path),
        "trainingGeometryCount": 39,
        "internalHoldoutGeometryCount": 9,
        "hardAnchorCount": 5,
        "softDiagnosticCount": 1,
        "modelStateSerialized": True,
        "modelRestorationVerified": True,
        "internalHoldoutOpenedExactlyOnce": True,
        "holdoutUsedForSelection": False,
        "anchorsUsedForSelection": False,
        "observationallyValidated": False,
        "productionModelReady": False,
        "productionPromotionAuthorized": False,
        "tier2Authorized": False,
    }
    report["reportSha256"] = canonical_sha256(report)
    report_path = output_dir / "model-run-report.json"
    report_path.write_text(dump(report), encoding="utf-8", newline="\n")
    return {
        "model": artifact_path,
        "selection": selection_path,
        "holdout": holdout_path,
        "external": external_path,
        "report": report_path,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--envelope", type=Path, required=True)
    parser.add_argument("--design", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--exact-main-sha", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        run(
            repository_root=args.repository_root,
            dataset_path=args.dataset,
            envelope_path=args.envelope,
            design_path=args.design,
            protocol_path=args.protocol,
            exact_main_sha=args.exact_main_sha,
            output_dir=args.output_dir,
        )
        return 0
    except Exception as exc:
        print(dump({"status": "REFUSED", "reason": str(exc)}), end="")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
