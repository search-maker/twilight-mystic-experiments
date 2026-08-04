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

STAGE_ID = "cross-geometry-selected-reference-confirmation-v1"
GENERIC_STAGE_ID = "mystic-batch-v1"
METHODS = ("reference-vroom", "alis")


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("cross_geometry_confirmation_convergence", path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load convergence module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def mean_vector(records: list[dict[str, Any]]) -> list[float]:
    vectors = [record.get("selectedNodeRadiance") for record in records]
    if not vectors or any(not isinstance(vector, list) or len(vector) != 15 for vector in vectors):
        raise ValueError("held-out records must contain 15-node spectra")
    return [sum(float(vector[index]) for vector in vectors) / len(vectors) for index in range(15)]


def exact_records(root: Path, manifest: dict[str, Any], manifest_hash: str, adapter_hash: str) -> dict[str, dict[str, Any]]:
    planned = {case["caseId"]: case for case in manifest["cases"]}
    paths = sorted(root.rglob("case-result.json"))
    if len(paths) != len(planned):
        raise ValueError(f"expected {len(planned)} case results, found {len(paths)}")
    found: dict[str, dict[str, Any]] = {}
    for path in paths:
        record = load(path)
        case_id = record.get("caseId")
        case = planned.get(case_id)
        if case is None or case_id in found:
            raise ValueError(f"unplanned or duplicate case: {case_id}")
        required = {
            "stageId": GENERIC_STAGE_ID,
            "status": "COMPLETED",
            "batchId": manifest["batchId"],
            "ordinal": case["ordinal"],
            "seed": case["seed"],
            "photonHistories": case["photonHistories"],
            "manifestRawSha256": manifest_hash,
            "adapterRawSha256": adapter_hash,
            "syntaxCheckCount": 1,
            "solverExecutionCount": 1,
            "scientificDiagnostic": True,
            "successDoesNotAuthorizeProduction": True,
        }
        stale = {key: (record.get(key), expected) for key, expected in required.items() if record.get(key) != expected}
        if stale:
            raise ValueError(f"case invariant failed for {case_id}: {stale}")
        syntax = record.get("syntax")
        solver = record.get("solver")
        if not isinstance(syntax, dict) or syntax.get("exitCode") != 0 or syntax.get("timedOut") is not False:
            raise ValueError(f"syntax failed for {case_id}")
        if not isinstance(solver, dict) or solver.get("exitCode") != 0 or solver.get("timedOut") is not False:
            raise ValueError(f"solver failed for {case_id}")
        value = record.get("selectedPhotopicContributionCdM2")
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)) or value <= 0:
            raise ValueError(f"invalid photopic value for {case_id}")
        found[case_id] = {**record, **case}
    return found


def source_summary(source_result: dict[str, Any], method: str) -> dict[str, Any]:
    group = source_result.get("groupId")
    if group in {"g01-reference-bridge", "g06-late-opposite-high-aerosol"}:
        if method == "reference-vroom":
            summary = source_result.get("vroomStatistics")
        else:
            selected = source_result.get("selectedAlisReferenceNm")
            matches = [candidate for candidate in source_result.get("candidateAlisReferences", []) if candidate.get("referenceNm") == selected]
            summary = matches[0].get("alisStatistics") if len(matches) == 1 else None
    else:
        summary = source_result.get("methodStatistics", {}).get(method)
    if not isinstance(summary, dict):
        raise ValueError(f"source method summary missing: {group} {method}")
    return summary


def analyze(
    manifest_path: Path,
    source_analysis_path: Path,
    cases_root: Path,
    summary_path: Path,
    audit_path: Path,
    convergence_module_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    manifest = load(manifest_path)
    source = load(source_analysis_path)
    summary = load(summary_path)
    audit = load(audit_path)
    if manifest.get("stageId") != STAGE_ID or manifest.get("scientificDiagnostic") is not True:
        raise ValueError("wrong promoted confirmation manifest")
    if source.get("stageId") != "cross-geometry-final-convergence-v1" or source.get("status") != "FINAL_CONVERGENCE_ANALYZED":
        raise ValueError("wrong source final-convergence analysis")
    if raw_sha256(source_analysis_path) != manifest.get("sourceFinalAnalysisRawSha256"):
        raise ValueError("source final analysis hash changed")
    expected_count = len(manifest["cases"])
    expected_photons = sum(case["photonHistories"] for case in manifest["cases"])
    if summary.get("stageId") != GENERIC_STAGE_ID or summary.get("classification") != "BATCH_NUMERICALLY_COMPLETE":
        raise ValueError("confirmation aggregate is incomplete")
    if (summary.get("caseCountCompleted"), summary.get("caseCountFailed")) != (expected_count, 0):
        raise ValueError("confirmation aggregate case accounting changed")
    if (summary.get("configuredMcPhotonsSum"), summary.get("completedConfiguredMcPhotonsSum")) != (expected_photons, expected_photons):
        raise ValueError("confirmation aggregate photon accounting changed")
    if audit.get("stageId") != GENERIC_STAGE_ID or audit.get("status") != "PASSED" or audit.get("caseResultCount") != expected_count:
        raise ValueError("confirmation independent audit failed")
    adapter_hash = summary.get("scientificAdapterRawSha256")
    if not isinstance(adapter_hash, str) or len(adapter_hash) != 64:
        raise ValueError("confirmation adapter hash missing")
    records = exact_records(cases_root, manifest, raw_sha256(manifest_path), adapter_hash)
    convergence = load_module(convergence_module_path)
    source_results = {item["groupId"]: item for item in source.get("geometryResults", [])}
    geometry_map = {item["geometryId"]: item for item in manifest.get("geometries", [])}
    by_request: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for case in manifest["cases"]:
        by_request.setdefault((case["groupId"], case["method"]), []).append(records[case["caseId"]])

    results: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []
    for group in manifest["selectedGeometryIds"]:
        source_result = source_results.get(group)
        if not isinstance(source_result, dict):
            raise ValueError(f"source result missing: {group}")
        methods: dict[str, dict[str, Any]] = {}
        origins: dict[str, str] = {}
        requested_methods: list[str] = []
        for method in METHODS:
            held_out = by_request.get((group, method), [])
            if held_out:
                if len(held_out) != 4:
                    raise ValueError(f"held-out request must contain four blocks: {group} {method}")
                values = [float(record["selectedPhotopicContributionCdM2"]) for record in held_out]
                methods[method] = convergence.method_summary(values, mean_vector(held_out), None)
                origins[method] = "held-out-confirmation"
                requested_methods.append(method)
            else:
                methods[method] = source_summary(source_result, method)
                origins[method] = "frozen-final-convergence-reference"
        decision = convergence.classify(methods, {
            "integratedMeanRatioAlisToVroomClosedInterval": [0.5, 2.0],
            "minimumVroomPhotopicWeightFractionNodeRatioInsideInterval": 0.80,
            "maximumRelativeStandardErrorOfMean": 1.0,
        })
        held_out_precise = all(methods[method]["relativeStandardErrorOfMean"] <= 0.08 for method in requested_methods)
        frozen_precise = all(methods[method]["relativeStandardErrorOfMean"] <= 0.10 for method in METHODS if method not in requested_methods)
        compatible = 0.5 <= decision["meanRatioAlisToVroom"] <= 2.0 and decision["vroomPhotopicWeightFractionNodeRatioInsideInterval"] >= 0.80
        if held_out_precise and frozen_precise and compatible:
            classification = "HELD_OUT_CONFIRMATION_PASSED"
            next_action = "REFERENCE_DATASET_ELIGIBLE_PENDING_OBSERVATION_VALIDATION"
        elif not held_out_precise or not frozen_precise:
            classification = "HELD_OUT_CONFIRMATION_INCONCLUSIVE_PRECISION_CAP_REACHED"
            next_action = "TECHNICAL_MONTE_CARLO_DIAGNOSIS_REQUIRED_NO_AUTOMATIC_MORE_BLOCKS"
        else:
            classification = "HELD_OUT_CONFIRMATION_DISCREPANCY"
            next_action = "TECHNICAL_METHOD_DIAGNOSIS_REQUIRED"
        result = {
            "groupId": group,
            "classification": classification,
            "requestedHeldOutMethods": requested_methods,
            "methodOrigins": origins,
            "methodStatistics": methods,
            "meanRatioAlisToVroom": decision["meanRatioAlisToVroom"],
            "vroomPhotopicWeightFractionNodeRatioInsideInterval": decision["vroomPhotopicWeightFractionNodeRatioInsideInterval"],
            "nodeMeanRatiosAlisToVroom": decision["nodeMeanRatiosAlisToVroom"],
            "heldOutTargetRelativeStandardErrorOfMean": 0.08,
            "frozenReferenceMaximumRelativeStandardErrorOfMean": 0.10,
            "noAutomaticAdditionalBlocks": True,
            "nextAction": next_action,
        }
        results.append(result)
        if classification == "HELD_OUT_CONFIRMATION_PASSED":
            accepted.append({
                "groupId": group,
                "geometry": geometry_map[group],
                "methodStatistics": methods,
                "methodOrigins": origins,
                "meanRatioAlisToVroom": decision["meanRatioAlisToVroom"],
                "nodeAgreementFraction": decision["vroomPhotopicWeightFractionNodeRatioInsideInterval"],
            })

    counts: dict[str, int] = {}
    for result in results:
        counts[result["classification"]] = counts.get(result["classification"], 0) + 1
    source_diagnosis = sorted(source.get("technicalDiagnosisRequiredGeometryIds", []))
    all_passed = len(accepted) == len(results)
    computational_complete = all_passed and not source_diagnosis
    status = "COMPUTATIONAL_REFERENCE_SCREENING_COMPLETE" if computational_complete else "COMPUTATIONAL_REFERENCE_SCREENING_REQUIRES_DIAGNOSIS"
    output = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "HELD_OUT_CONFIRMATION_ANALYZED",
        "screeningOnly": True,
        "successDoesNotAuthorizeProduction": True,
        "sourceRunId": manifest["sourceRunId"],
        "caseResultCount": expected_count,
        "configuredMcPhotonsSum": expected_photons,
        "geometryResults": results,
        "classificationCounts": counts,
        "sourceTechnicalDiagnosisRequiredGeometryIds": source_diagnosis,
        "computationalReferenceScreeningComplete": computational_complete,
        "noAutomaticAdditionalBlocks": True,
        "boundary": "held-out computational confirmation only; observational and physical validation remain required before production use",
    }
    readiness = {
        "schemaVersion": 1,
        "status": status,
        "computationalReferenceScreeningComplete": computational_complete,
        "acceptedReferenceGeometryCount": len(accepted),
        "heldOutConfirmationFailureCount": len(results) - len(accepted),
        "technicalDiagnosisRequiredGeometryIds": sorted(set(source_diagnosis + [item["groupId"] for item in results if item["classification"] != "HELD_OUT_CONFIRMATION_PASSED"])),
        "productionModelReady": False,
        "physicalValidationReady": False,
        "observationValidationRequired": True,
        "surrogateTrainingAutomaticallyAuthorized": False,
        "noAutomaticAdditionalBlocks": True,
    }
    dataset = {
        "schemaVersion": 1,
        "status": "AUDITED_COMPUTATIONAL_REFERENCE_DATASET" if accepted else "NO_ACCEPTED_HELD_OUT_REFERENCES",
        "sourceStageId": STAGE_ID,
        "screeningOnly": True,
        "observationValidationRequired": True,
        "records": accepted,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "held-out-confirmation-analysis.json").write_text(dump(output))
    (output_dir / "reference-readiness.json").write_text(dump(readiness))
    (output_dir / "audited-reference-dataset.json").write_text(dump(dataset))
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--source-final-analysis", type=Path, required=True)
    parser.add_argument("--cases-root", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--convergence-module", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = analyze(args.manifest, args.source_final_analysis, args.cases_root, args.summary, args.audit, args.convergence_module, args.output_dir)
        print(dump(result), end="")
        return 0
    except Exception as exc:
        print(dump({"status": "REFUSED", "stageId": STAGE_ID, "reason": str(exc)}), end="", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
