#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any

STAGE_ID = "g01-fixed-precision-diagnosis-proposal-v1"
SOURCE_STAGE_ID = "cross-geometry-held-out-confirmation-timeout-continuation-v1"
SOURCE_RUN_ID = 30875148389
SOURCE_WORKFLOW_NAME = "MYSTIC held-out timeout continuation v1 scientific execution"
SOURCE_WORKFLOW_PATH = ".github/workflows/mystic-batch-v1-cross-geometry-confirmation-timeout-continuation.yml"
ANALYSIS_ARTIFACT = "cross-geometry-timeout-continuation-v1-analysis"
PREFLIGHT_ARTIFACT = "cross-geometry-timeout-continuation-v1-preflight"
GROUP_ID = "g01-reference-bridge"
SELECTED_REFERENCE_NM = 600.0
TARGET_RSEM = 0.08
FROZEN_REFERENCE_MAX_RSEM = 0.10
RATIO_INTERVAL = [0.5, 2.0]
MIN_NODE_AGREEMENT = 0.80
NEW_SEEDS = [84601, 84602, 84603, 84604]
NEW_BLOCKS = [5, 6, 7, 8]
PHOTONS_PER_BLOCK = 50_000_000


class DiagnosisError(RuntimeError):
    pass


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise DiagnosisError(f"expected JSON object: {path}")
    return value


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_by_name(listing: dict[str, Any], name: str, run_id: int) -> dict[str, Any]:
    artifacts = listing.get("artifacts")
    if not isinstance(artifacts, list):
        raise DiagnosisError("source artifact listing missing")
    matches = [item for item in artifacts if isinstance(item, dict) and item.get("name") == name]
    if len(matches) != 1:
        raise DiagnosisError(f"expected exactly one {name} artifact, found {len(matches)}")
    artifact = matches[0]
    if artifact.get("expired") is not False:
        raise DiagnosisError(f"source artifact expired: {name}")
    artifact_id = artifact.get("id")
    digest = artifact.get("digest")
    if not isinstance(artifact_id, int) or artifact_id < 1:
        raise DiagnosisError(f"source artifact ID invalid: {name}")
    if not isinstance(digest, str) or not digest.startswith("sha256:") or len(digest) != 71:
        raise DiagnosisError(f"source artifact digest invalid: {name}")
    workflow_run = artifact.get("workflow_run")
    if isinstance(workflow_run, dict) and workflow_run.get("id") not in {None, run_id}:
        raise DiagnosisError(f"source artifact belongs to another run: {name}")
    return artifact


def find_one(root: Path, filename: str) -> Path:
    matches = list(root.rglob(filename))
    if len(matches) != 1:
        raise DiagnosisError(f"expected exactly one {filename}, found {len(matches)}")
    return matches[0]


def method_summary(values: list[float]) -> dict[str, Any]:
    if len(values) < 2 or any(not math.isfinite(value) or value <= 0 for value in values):
        raise DiagnosisError("positive finite independent values required")
    mean = statistics.fmean(values)
    sample_std = statistics.stdev(values)
    cv = sample_std / mean
    return {
        "blockCount": len(values),
        "valuesCdM2": values,
        "meanCdM2": mean,
        "sampleStandardDeviationCdM2": sample_std,
        "coefficientOfVariation": cv,
        "relativeStandardErrorOfMean": cv / math.sqrt(len(values)),
    }


def validate_source_run(source_run: dict[str, Any]) -> tuple[int, str]:
    expected = {
        "id": SOURCE_RUN_ID,
        "status": "completed",
        "conclusion": "success",
        "event": "workflow_dispatch",
        "run_attempt": 1,
        "head_branch": "main",
        "name": SOURCE_WORKFLOW_NAME,
        "path": SOURCE_WORKFLOW_PATH,
    }
    stale = {key: (source_run.get(key), value) for key, value in expected.items() if source_run.get(key) != value}
    if stale:
        raise DiagnosisError(f"source run mismatch: {stale}")
    head_sha = source_run.get("head_sha")
    if not isinstance(head_sha, str) or len(head_sha) != 40:
        raise DiagnosisError("source run head SHA invalid")
    return SOURCE_RUN_ID, head_sha


def build(
    analysis_path: Path,
    readiness_path: Path,
    dataset_path: Path,
    preflight_root: Path,
    source_run_path: Path,
    source_artifacts_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    analysis = load(analysis_path)
    readiness = load(readiness_path)
    dataset = load(dataset_path)
    source_run = load(source_run_path)
    source_artifacts = load(source_artifacts_path)
    source_run_id, source_head_sha = validate_source_run(source_run)
    analysis_artifact = artifact_by_name(source_artifacts, ANALYSIS_ARTIFACT, source_run_id)
    preflight_artifact = artifact_by_name(source_artifacts, PREFLIGHT_ARTIFACT, source_run_id)

    required_analysis = {
        "schemaVersion": 1,
        "stageId": SOURCE_STAGE_ID,
        "status": "TIMEOUT_CONTINUATION_ANALYZED",
        "computationalReferenceScreeningComplete": False,
        "noAutomaticAdditionalBlocks": True,
        "screeningOnly": True,
        "successDoesNotAuthorizeProduction": True,
        "sourceFailedRunId": 30871800549,
        "preservedG01CaseResultCount": 4,
        "newCaseResultCount": 8,
        "newConfiguredMcPhotonsSum": 1_600_000_000,
    }
    stale = {key: (analysis.get(key), expected) for key, expected in required_analysis.items() if analysis.get(key) != expected}
    if stale:
        raise DiagnosisError(f"source analysis mismatch: {stale}")

    required_readiness = {
        "schemaVersion": 1,
        "status": "COMPUTATIONAL_REFERENCE_SCREENING_REQUIRES_DIAGNOSIS",
        "computationalReferenceScreeningComplete": False,
        "acceptedReferenceGeometryCount": 5,
        "heldOutConfirmationFailureCount": 1,
        "noAutomaticAdditionalBlocks": True,
        "productionModelReady": False,
        "observationValidationRequired": True,
        "surrogateTrainingAutomaticallyAuthorized": False,
    }
    stale = {key: (readiness.get(key), expected) for key, expected in required_readiness.items() if readiness.get(key) != expected}
    if stale:
        raise DiagnosisError(f"source readiness mismatch: {stale}")
    if readiness.get("technicalDiagnosisRequiredGeometryIds") != [GROUP_ID]:
        raise DiagnosisError("g01 must be the only diagnosis-required geometry")

    records = dataset.get("records")
    if dataset.get("status") != "INCOMPLETE_COMPUTATIONAL_REFERENCE_DATASET" or not isinstance(records, list):
        raise DiagnosisError("source dataset boundary changed")
    accepted_ids = sorted(item.get("groupId") for item in records if isinstance(item, dict))
    if len(accepted_ids) != 5 or GROUP_ID in accepted_ids:
        raise DiagnosisError("source dataset must contain exactly five accepted non-g01 records")

    geometry_results = analysis.get("geometryResults")
    if not isinstance(geometry_results, list):
        raise DiagnosisError("source geometry results missing")
    g01_matches = [item for item in geometry_results if isinstance(item, dict) and item.get("groupId") == GROUP_ID]
    g06_matches = [item for item in geometry_results if isinstance(item, dict) and item.get("groupId") == "g06-late-opposite-high-aerosol"]
    if len(g01_matches) != 1 or len(g06_matches) != 1:
        raise DiagnosisError("expected exact g01 and g06 source results")
    g01 = g01_matches[0]
    g06 = g06_matches[0]
    if g01.get("classification") != "HELD_OUT_CONFIRMATION_INCONCLUSIVE_PRECISION_CAP_REACHED":
        raise DiagnosisError("g01 source classification changed")
    if g01.get("nextAction") != "TECHNICAL_DIAGNOSIS_REQUIRED_NO_AUTOMATIC_MORE_BLOCKS":
        raise DiagnosisError("g01 next action changed")
    if g06.get("classification") != "HELD_OUT_CONFIRMATION_PASSED":
        raise DiagnosisError("g06 must already be passed")

    methods = g01.get("methodStatistics")
    if not isinstance(methods, dict):
        raise DiagnosisError("g01 method statistics missing")
    alis = methods.get("alis")
    vroom = methods.get("reference-vroom")
    if not isinstance(alis, dict) or not isinstance(vroom, dict):
        raise DiagnosisError("g01 ALIS or VROOM statistics missing")
    held_values = [float(value) for value in alis.get("valuesCdM2", [])]
    if len(held_values) != 4:
        raise DiagnosisError("g01 must contain four held-out ALIS values")
    held = method_summary(held_values)
    if abs(float(held["relativeStandardErrorOfMean"]) - float(alis.get("relativeStandardErrorOfMean"))) > 1e-15:
        raise DiagnosisError("g01 held-out ALIS RSEM did not reproduce")
    if not TARGET_RSEM < float(held["relativeStandardErrorOfMean"]) < FROZEN_REFERENCE_MAX_RSEM:
        raise DiagnosisError("g01 must be a marginal held-out precision miss")
    if float(vroom.get("relativeStandardErrorOfMean", math.inf)) > FROZEN_REFERENCE_MAX_RSEM:
        raise DiagnosisError("g01 frozen VROOM precision is not acceptable")
    mean_ratio = float(g01.get("meanRatioAlisToVroom"))
    node_agreement = float(g01.get("vroomPhotopicWeightFractionNodeRatioInsideInterval"))
    if not (RATIO_INTERVAL[0] <= mean_ratio <= RATIO_INTERVAL[1]):
        raise DiagnosisError("g01 integrated compatibility failed")
    if node_agreement < MIN_NODE_AGREEMENT:
        raise DiagnosisError("g01 node compatibility failed")

    source_final_path = find_one(preflight_root / "source-package", "final-convergence-analysis.json")
    source_final = load(source_final_path)
    source_g01 = [item for item in source_final.get("geometryResults", []) if isinstance(item, dict) and item.get("groupId") == GROUP_ID]
    if len(source_g01) != 1:
        raise DiagnosisError("source final-convergence g01 result missing")
    source_g01 = source_g01[0]
    if source_g01.get("selectedAlisReferenceNm") != SELECTED_REFERENCE_NM:
        raise DiagnosisError("g01 selected ALIS reference changed")
    candidates = source_g01.get("candidateAlisReferences")
    if not isinstance(candidates, list):
        raise DiagnosisError("g01 ALIS reference candidates missing")
    candidate_map = {float(item["referenceNm"]): item for item in candidates if isinstance(item, dict)}
    if set(candidate_map) != {500.0, 550.0, 600.0}:
        raise DiagnosisError("g01 ALIS candidate reference universe changed")
    selected_old = candidate_map[SELECTED_REFERENCE_NM]["alisStatistics"]
    if any(float(selected_old["relativeStandardErrorOfMean"]) >= float(candidate_map[reference]["alisStatistics"]["relativeStandardErrorOfMean"]) for reference in (500.0, 550.0)):
        raise DiagnosisError("600 nm is no longer the best prior precision candidate")

    case_paths = sorted((preflight_root / "source-g01").rglob("case-result.json"))
    if len(case_paths) != 4:
        raise DiagnosisError(f"expected four preserved g01 case results, found {len(case_paths)}")
    case_rows = [load(path) for path in case_paths]
    expected_ids = [f"cgc-g01-alis-r{index}" for index in range(1, 5)]
    if sorted(row.get("caseId") for row in case_rows) != expected_ids:
        raise DiagnosisError("preserved g01 case IDs changed")
    case_rows.sort(key=lambda row: row["caseId"])
    for index, row in enumerate(case_rows, start=1):
        required = {
            "status": "COMPLETED",
            "scientificDiagnostic": True,
            "successDoesNotAuthorizeProduction": True,
            "seed": 80600 + index,
            "photonHistories": PHOTONS_PER_BLOCK,
            "syntaxCheckCount": 1,
            "solverExecutionCount": 1,
        }
        stale = {key: (row.get(key), expected) for key, expected in required.items() if row.get(key) != expected}
        if stale:
            raise DiagnosisError(f"preserved g01 case invariant failed: {row.get('caseId')}: {stale}")
        syntax = row.get("syntax")
        solver = row.get("solver")
        if not isinstance(syntax, dict) or syntax.get("exitCode") != 0 or syntax.get("timedOut") is not False:
            raise DiagnosisError(f"preserved g01 syntax failed: {row.get('caseId')}")
        if not isinstance(solver, dict) or solver.get("exitCode") != 0 or solver.get("timedOut") is not False:
            raise DiagnosisError(f"preserved g01 solver failed: {row.get('caseId')}")
    raw_values = [float(row["selectedPhotopicContributionCdM2"]) for row in case_rows]
    if any(abs(left - right) > 1e-15 for left, right in zip(raw_values, held_values)):
        raise DiagnosisError("preserved g01 raw values differ from official analysis")

    nodes = case_rows[0].get("diagnosticNodesNm")
    if not isinstance(nodes, list) or len(nodes) != 15:
        raise DiagnosisError("g01 diagnostic node set invalid")
    node_cvs = []
    for index in range(15):
        values = [float(row["selectedNodeRadiance"][index]) for row in case_rows]
        mean = statistics.fmean(values)
        node_cvs.append(statistics.stdev(values) / mean)
    solver_seconds = [float(row["solver"]["elapsedSeconds"]) for row in case_rows]

    old_values = [float(value) for value in selected_old["valuesCdM2"]]
    selection = method_summary(old_values)
    diagnostic_combined = method_summary(old_values + held_values)
    observed_cv = float(held["coefficientOfVariation"])
    minimum_total_blocks = math.ceil((observed_cv / TARGET_RSEM) ** 2)
    recommended_total_blocks = 8
    expected_rsem_at_recommended_total = observed_cv / math.sqrt(recommended_total_blocks)

    diagnosis = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "G01_MONTE_CARLO_PRECISION_DIAGNOSED",
        "sourceRunId": source_run_id,
        "sourceRunHeadSha": source_head_sha,
        "sourceAnalysisArtifactId": analysis_artifact["id"],
        "sourceAnalysisArtifactDigest": analysis_artifact["digest"],
        "sourcePreflightArtifactId": preflight_artifact["id"],
        "sourcePreflightArtifactDigest": preflight_artifact["digest"],
        "sourceAnalysisRawSha256": raw_sha256(analysis_path),
        "sourceReadinessRawSha256": raw_sha256(readiness_path),
        "sourceDatasetRawSha256": raw_sha256(dataset_path),
        "sourceFinalConvergenceRawSha256": raw_sha256(source_final_path),
        "groupId": GROUP_ID,
        "failureMode": "MONTE_CARLO_PRECISION_ONLY",
        "structuralExecutionFailure": False,
        "methodCompatibilityPassed": True,
        "selectedAlisReferenceNm": SELECTED_REFERENCE_NM,
        "heldOutStatistics": held,
        "frozenVroomStatistics": vroom,
        "meanRatioAlisToVroom": mean_ratio,
        "vroomPhotopicWeightFractionNodeRatioInsideInterval": node_agreement,
        "selectionStatisticsDiagnosticOnly": selection,
        "selectionToHeldOutMeanRatio": float(held["meanCdM2"]) / float(selection["meanCdM2"]),
        "selectionPlusHeldOutStatisticsDiagnosticOnly": diagnostic_combined,
        "selectionDataExcludedFromAcceptanceDecision": True,
        "preservedHeldOutCaseIds": expected_ids,
        "preservedHeldOutSeeds": [80601, 80602, 80603, 80604],
        "solverElapsedSeconds": {"minimum": min(solver_seconds), "mean": statistics.fmean(solver_seconds), "maximum": max(solver_seconds)},
        "nodeCoefficientOfVariationRange": [min(node_cvs), max(node_cvs)],
        "broadSpectrumVarianceObserved": min(node_cvs) > 0.10,
        "singleBlockDeletionAuthorized": False,
        "targetRelativeStandardErrorOfMean": TARGET_RSEM,
        "minimumTotalBlocksAtObservedCvPlanningHeuristic": minimum_total_blocks,
        "recommendedFixedTotalBlocks": recommended_total_blocks,
        "recommendedAdditionalBlocks": 4,
        "expectedRsemAtRecommendedTotalPlanningHeuristic": expected_rsem_at_recommended_total,
        "planningHeuristicIsNotAcceptanceEvidence": True,
        "diagnosisConclusion": "600 nm remains the best prior ALIS importance reference; g01 agrees with frozen VROOM but four independent 50M held-out blocks are marginally underpowered for the fixed 8% RSEM gate",
        "boundary": "technical diagnosis only; no block is discarded, no threshold is relaxed, and no scientific execution is authorized",
    }

    new_cases = []
    for ordinal, (block, seed) in enumerate(zip(NEW_BLOCKS, NEW_SEEDS), start=1):
        new_cases.append({
            "ordinal": ordinal,
            "caseId": f"g01pd-alis-b{block}",
            "groupId": GROUP_ID,
            "method": "alis",
            "block": block,
            "seed": seed,
            "photonHistories": PHOTONS_PER_BLOCK,
            "alisSpectralImportanceSamplingNm": SELECTED_REFERENCE_NM,
            "purpose": "fixed-final-precision-diagnosis",
        })
    proposal = {
        "schemaVersion": 1,
        "stageId": "g01-fixed-precision-diagnosis-execution-v1",
        "batchId": "g01-fixed-precision-diagnosis-v1",
        "status": "PROPOSAL_ONLY_NOT_AUTHORIZATION",
        "mode": "scientific-proposal",
        "proposalOnly": True,
        "scientificExecution": False,
        "scientificDiagnostic": True,
        "successDoesNotAuthorizeProduction": True,
        "sourceRunId": source_run_id,
        "sourceAnalysisArtifactId": analysis_artifact["id"],
        "sourceAnalysisArtifactDigest": analysis_artifact["digest"],
        "diagnosisRawSha256": hashlib.sha256(dump(diagnosis).encode()).hexdigest(),
        "selectedGeometryIds": [GROUP_ID],
        "selectedAlisReferenceNm": SELECTED_REFERENCE_NM,
        "existingHeldOutBlocks": [1, 2, 3, 4],
        "newDiagnosticBlocks": NEW_BLOCKS,
        "cases": new_cases,
        "limits": {
            "maximumCases": 4,
            "maximumParallel": 4,
            "perCaseTimeoutSeconds": 900,
            "maximumPhotonHistoriesPerBlock": PHOTONS_PER_BLOCK,
            "maximumConfiguredMcPhotonsSum": 200_000_000,
        },
        "analysisPlan": {
            "combineOnlyPreservedHeldOutBlocksAndNewDiagnosticBlocks": True,
            "combinedAlisBlockCount": 8,
            "selectionDataExcludedFromAcceptanceDecision": True,
            "targetRelativeStandardErrorOfMean": TARGET_RSEM,
            "frozenReferenceMaximumRelativeStandardErrorOfMean": FROZEN_REFERENCE_MAX_RSEM,
            "integratedMeanRatioAlisToVroomClosedInterval": RATIO_INTERVAL,
            "minimumVroomPhotopicWeightFractionNodeRatioInsideInterval": MIN_NODE_AGREEMENT,
            "passClassification": "G01_FIXED_PRECISION_DIAGNOSIS_PASSED",
            "persistentVarianceClassification": "G01_PERSISTENT_HIGH_VARIANCE",
            "methodDiscrepancyClassification": "G01_METHOD_DISCREPANCY",
            "noAutomaticAdditionalBlocks": True,
        },
        "executionAuthorizedByProposal": False,
        "surrogateTrainingAutomaticallyAuthorized": False,
        "productionModelReady": False,
        "observationValidationRequired": True,
        "boundary": "one fixed four-block diagnostic proposal after precision-only diagnosis; separate one-purpose authorization and manual first-attempt dispatch required",
    }
    readiness_output = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "G01_FIXED_PRECISION_DIAGNOSIS_PROPOSED_PENDING_SEPARATE_AUTHORIZATION",
        "sourceRunId": source_run_id,
        "diagnosisComplete": True,
        "failureMode": "MONTE_CARLO_PRECISION_ONLY",
        "newCaseCount": 4,
        "newConfiguredMcPhotonsSum": 200_000_000,
        "scientificExecution": False,
        "executionAuthorized": False,
        "noAutomaticAdditionalBlocks": True,
        "surrogateTrainingAuthorized": False,
        "productionModelReady": False,
        "observationValidationRequired": True,
    }
    return diagnosis, proposal, readiness_output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--analysis", type=Path, required=True)
    parser.add_argument("--readiness", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--preflight-root", type=Path, required=True)
    parser.add_argument("--source-run", type=Path, required=True)
    parser.add_argument("--source-artifacts", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        diagnosis, proposal, readiness = build(args.analysis, args.readiness, args.dataset, args.preflight_root, args.source_run, args.source_artifacts)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "g01-precision-diagnosis.json").write_text(dump(diagnosis))
        (args.output_dir / "g01-fixed-diagnostic-proposal.json").write_text(dump(proposal))
        (args.output_dir / "g01-diagnosis-readiness.json").write_text(dump(readiness))
        print(dump(readiness), end="")
        return 0
    except Exception as exc:
        print(dump({"schemaVersion": 1, "stageId": STAGE_ID, "status": "REFUSED", "reason": str(exc)}), file=sys.stderr, end="")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
