#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any


class ModelRuntimeRefusal(RuntimeError):
    pass


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ModelRuntimeRefusal(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ModelRuntimeRefusal(f"expected object: {path}")
    return value


def load_training(path: Path):
    spec = importlib.util.spec_from_file_location("surrogate_training_v2_runtime_training", path)
    if spec is None or spec.loader is None:
        raise ModelRuntimeRefusal("training implementation unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_model(
    package_path: Path,
    artifact_path: Path,
    state_path: Path,
    *,
    repository_root: Path,
):
    package = load_json(package_path)
    artifact = load_json(artifact_path)
    state = load_json(state_path)
    if package.get("status") != "MODEL_TRAINED_AND_EVALUATED":
        raise ModelRuntimeRefusal("model package is not trained and evaluated")
    package_seal = package.get("modelPackageSha256")
    package_payload = {
        key: value for key, value in package.items() if key != "modelPackageSha256"
    }
    if package_seal != canonical_sha256(package_payload):
        raise ModelRuntimeRefusal("model package hash changed")
    state_seal = state.get("modelStateSha256")
    state_payload = {key: value for key, value in state.items() if key != "modelStateSha256"}
    if state_seal != canonical_sha256(state_payload):
        raise ModelRuntimeRefusal("model state hash changed")
    bindings = package.get("bindings")
    if not isinstance(bindings, dict):
        raise ModelRuntimeRefusal("model package bindings missing")
    if bindings.get("frozenArtifactRawSha256") != raw_sha256(artifact_path):
        raise ModelRuntimeRefusal("frozen artifact bytes changed")
    if bindings.get("modelStateRawSha256") != raw_sha256(state_path):
        raise ModelRuntimeRefusal("model state bytes changed")
    if package.get("generatedModelHash") != artifact.get("generatedModelHash"):
        raise ModelRuntimeRefusal("artifact model hash differs from package")
    if state.get("generatedModelHash") != artifact.get("generatedModelHash"):
        raise ModelRuntimeRefusal("state model hash differs from artifact")
    if state.get("candidateId") != artifact.get("candidateId"):
        raise ModelRuntimeRefusal("state candidate differs from artifact")
    if package.get("modelUsableForPrediction") is not True:
        raise ModelRuntimeRefusal("model package is not prediction-enabled")
    if package.get("productionPromotionAuthorized") is not False:
        raise ModelRuntimeRefusal("runtime refuses production-authorized package")

    training_path = repository_root.resolve() / "modeling/surrogate-training-v2/training.py"
    if bindings.get("trainingRawSha256") != raw_sha256(training_path):
        raise ModelRuntimeRefusal("training implementation hash changed")
    training = load_training(training_path)
    constants = state.get("normalizationConstants")
    if not isinstance(constants, dict):
        raise ModelRuntimeRefusal("normalization constants missing")
    lows = constants.get("minimums")
    highs = constants.get("maximums")
    if not isinstance(lows, list) or not isinstance(highs, list) or len(lows) != 5 or len(highs) != 5:
        raise ModelRuntimeRefusal("normalization constants invalid")
    if any(
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(float(value))
        for value in lows + highs
    ):
        raise ModelRuntimeRefusal("normalization constants nonfinite")
    model = training.Model(
        state["candidateId"],
        state["hyperparameters"],
        [float(value) for value in lows],
        [float(value) for value in highs],
        state["state"],
        float(state["residualRmse"]),
    )
    return model, package, artifact, state


def predict(
    package_path: Path,
    artifact_path: Path,
    state_path: Path,
    request: dict[str, Any],
    *,
    repository_root: Path,
) -> dict[str, Any]:
    model, package, artifact, _ = load_model(
        package_path,
        artifact_path,
        state_path,
        repository_root=repository_root,
    )
    geometry = request.get("geometry")
    if not isinstance(geometry, dict):
        raise ModelRuntimeRefusal("prediction request geometry missing")
    required = (
        "sunDepressionDeg",
        "targetAltitudeDeg",
        "relativeAzimuthDeg",
        "observerElevationM",
        "aod550",
    )
    for key in required:
        value = geometry.get(key)
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(float(value))
        ):
            raise ModelRuntimeRefusal(f"prediction feature invalid: {key}")
    record = {
        "geometryId": request.get("geometryId", "prediction-request"),
        "geometry": geometry,
    }
    result = model.predict(record)
    if (
        not math.isfinite(float(result["predictionCdM2"]))
        or result["predictionCdM2"] <= 0
        or not math.isfinite(float(result["uncertaintyLog"]))
        or result["uncertaintyLog"] < 0
    ):
        raise ModelRuntimeRefusal("runtime produced invalid prediction")
    return {
        "schemaVersion": 1,
        "stageId": "surrogate-training-v2-prediction-v1",
        "status": "PREDICTION_COMPLETE",
        "modelPackageSha256": package["modelPackageSha256"],
        "generatedModelHash": artifact["generatedModelHash"],
        "geometryId": record["geometryId"],
        "geometry": geometry,
        **result,
        "observationallyValidated": False,
        "productionModelReady": False,
        "productionPromotionAuthorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        value = predict(
            args.package,
            args.artifact,
            args.state,
            load_json(args.request),
            repository_root=args.repository_root,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump(value), encoding="utf-8", newline="\n")
        print(dump(value), end="")
        return 0
    except Exception as exc:
        print(dump({"status": "REFUSED", "reason": str(exc)}), end="", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
