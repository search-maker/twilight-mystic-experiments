#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--work-root", type=Path, required=True)
    parser.add_argument("--review-root", type=Path, required=True)
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--base-sha", required=True)
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--run-attempt", type=int, required=True)
    args = parser.parse_args()

    package = args.repository_root / "modeling/surrogate-training-v2"
    artifacts = load_module(package / "_exploratory_terminal_artifacts.py", "terminal_artifacts")
    builder = load_module(package / "exploratory_terminal_training_dataset.py", "terminal_builder")
    model = load_module(package / "exploratory_noisy_label_training_exact.py", "terminal_model")
    inventory = artifacts.download_inputs(args.repository, args.token, args.work_root)
    source_binding_path = package / "evidence/ordinal13-terminal-source-binding.json"
    source_binding = builder.load(source_binding_path)
    dataset = builder.build(
        args.repository_root,
        Path(inventory["sourceDatasetPath"]),
        source_binding_path,
        Path(inventory["analysisPath"]),
        Path(inventory["resultsRoot"]),
    )
    frozen_model = model.run(dataset, source_binding)
    args.review_root.mkdir(parents=True, exist_ok=True)
    dataset_path = args.review_root / "terminal-training-only-dataset.json"
    model_path = args.review_root / "exploratory-training-only-model.json"
    dataset_path.write_text(json.dumps(dataset, indent=2, sort_keys=True) + "\n")
    model_path.write_text(json.dumps(frozen_model, indent=2, sort_keys=True) + "\n")

    ids = [row.get("geometryId") for row in dataset.get("records", [])]
    if ids != list(builder.TRAINING_IDS) or any(gid in ids for gid in builder.HOLDOUT_IDS):
        raise RuntimeError("real terminal training-only identity universe changed")
    exhausted = sorted(
        row["geometryId"] for row in dataset["records"]
        if not row.get("scientificallyEligible", False)
    )
    if exhausted != sorted(builder.WAVE3_TRAINING_IDS):
        raise RuntimeError("real terminal exhausted training set changed")
    if dataset.get("sourceTrainingDatasetRawSha256") != inventory["sourceTrainingDatasetRawSha256"]:
        raise RuntimeError("real terminal source dataset raw binding changed")
    if dataset.get("sourceTrainingDatasetSha256") != inventory["sourceTrainingDatasetSha256"]:
        raise RuntimeError("real terminal source dataset canonical binding changed")
    false_flags = (
        "internalHoldoutOpened", "holdoutValuesRead", "hardAnchorsOpened",
        "softDiagnosticsOpened", "scientificallyEligibleModelClaimed",
        "productionModelReady", "productionPromotionAuthorized", "tier2Authorized",
    )
    if any(frozen_model.get(key) is not False for key in false_flags):
        raise RuntimeError("real exploratory model boundary changed")

    public_inventory = {
        key: value for key, value in inventory.items()
        if key not in {"sourceDatasetPath", "resultsRoot", "analysisPath"}
    }
    report = {
        "schemaVersion": 1,
        "stageId": "surrogate-training-v2-exploratory-terminal-real-integration-v1",
        "status": "REAL_TERMINAL_TRAINING_ONLY_DATASET_AND_MODEL_FROZEN_HOLDOUT_UNOPENED",
        "headSha": args.head_sha,
        "baseSha": args.base_sha,
        "runId": args.run_id,
        "runAttempt": args.run_attempt,
        **public_inventory,
        "terminalSourceBindingSha256": dataset["sourceBindingSha256"],
        "trainingGeometryCount": len(ids),
        "terminalExhaustedTrainingGeometryIds": exhausted,
        "internalHoldoutGeometryIdsExcludedAndUnopened": list(builder.HOLDOUT_IDS),
        "holdoutRecordCount": dataset["holdoutRecordCount"],
        "holdoutValuesIncluded": dataset["holdoutValuesIncluded"],
        "datasetRawSha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        "datasetSha256": dataset["datasetSha256"],
        "modelRawSha256": hashlib.sha256(model_path.read_bytes()).hexdigest(),
        "modelHash": frozen_model["modelHash"],
        **{key: frozen_model[key] for key in false_flags},
    }
    report["reportSha256"] = builder.canonical_sha256(report)
    (args.review_root / "contract-review.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
