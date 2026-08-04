#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import inspect
import json
import sys
from pathlib import Path
from typing import Any

STAGE_ID = "twilight-surrogate-tier-1-proposal-v1"
TIER_ID = "tier-1-provisional"
SOURCE_STAGE_ID = "cross-geometry-held-out-confirmation-timeout-continuation-v1"
SOURCE_ARTIFACT = "cross-geometry-timeout-continuation-v1-analysis"
SOURCE_WORKFLOW_PROFILES = {
    "MYSTIC held-out timeout continuation v1 scientific execution": {
        "stageId": "cross-geometry-held-out-confirmation-timeout-continuation-v1",
        "status": "TIMEOUT_CONTINUATION_ANALYZED",
        "artifact": "cross-geometry-timeout-continuation-v1-analysis",
        "workflowPath": ".github/workflows/mystic-batch-v1-cross-geometry-confirmation-timeout-continuation.yml",
        "events": {"workflow_dispatch"},
        "screeningComplete": True,
    },
    "MYSTIC g01 fixed precision diagnosis execution v1": {
        "stageId": "g01-fixed-precision-diagnosis-execution-v1",
        "status": "G01_FIXED_PRECISION_EXECUTION_ANALYZED",
        "artifact": "g01-fixed-precision-diagnosis-execution-v1-analysis",
        "workflowPath": ".github/workflows/mystic-batch-v1-cross-geometry-g01-precision-continuation.yml",
        "events": {"workflow_dispatch"},
        "screeningComplete": True,
    },
    "G01 precision artifact-only recovery": {
        "stageId": "g01-fixed-precision-diagnosis-execution-v1",
        "status": "G01_FIXED_PRECISION_EXECUTION_ANALYZED",
        "artifact": "cross-geometry-g01-precision-continuation-v1-recovery-analysis",
        "workflowPath": ".github/workflows/mystic-batch-v1-cross-geometry-g01-precision-recovery.yml",
        "events": {"push", "workflow_dispatch"},
        "screeningComplete": False,
        "classification": "G01_PERSISTENT_HIGH_VARIANCE",
    },
}

# Backward-compatible complete-source registry used by existing contracts and tests.
SOURCE_PROFILES = {
    "cross-geometry-held-out-confirmation-timeout-continuation-v1": {
        "status": "TIMEOUT_CONTINUATION_ANALYZED",
        "artifact": "cross-geometry-timeout-continuation-v1-analysis",
        "workflowName": "MYSTIC held-out timeout continuation v1 scientific execution",
        "workflowPath": ".github/workflows/mystic-batch-v1-cross-geometry-confirmation-timeout-continuation.yml",
    },
    "g01-fixed-precision-diagnosis-execution-v1": {
        "status": "G01_FIXED_PRECISION_EXECUTION_ANALYZED",
        "artifact": "g01-fixed-precision-diagnosis-execution-v1-analysis",
        "workflowName": "MYSTIC g01 fixed precision diagnosis execution v1",
        "workflowPath": ".github/workflows/mystic-batch-v1-cross-geometry-g01-precision-continuation.yml",
    },
}


class ProposalError(RuntimeError):
    pass


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ProposalError(f"expected JSON object: {path}")
    return value


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ProposalError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_source(
    analysis: dict[str, Any],
    source_run: dict[str, Any],
    source_artifacts: dict[str, Any],
) -> dict[str, Any]:
    workflow_name = source_run.get("name")
    profile = SOURCE_WORKFLOW_PROFILES.get(workflow_name)
    if profile is None:
        raise ProposalError(f"unsupported source workflow: {workflow_name}")
    stage = analysis.get("stageId")
    required_analysis = {
        "schemaVersion": 1,
        "stageId": profile["stageId"],
        "status": profile["status"],
        "computationalReferenceScreeningComplete": profile["screeningComplete"],
        "noAutomaticAdditionalBlocks": True,
        "screeningOnly": True,
        "successDoesNotAuthorizeProduction": True,
    }
    if profile.get("classification") is not None:
        required_analysis["classification"] = profile["classification"]
    stale = {
        key: (analysis.get(key), expected)
        for key, expected in required_analysis.items()
        if analysis.get(key) != expected
    }
    if stale:
        raise ProposalError(f"source analysis is not eligible: {stale}")
    required_run = {
        "status": "completed",
        "conclusion": "success",
        "run_attempt": 1,
        "head_branch": "main",
        "name": workflow_name,
        "path": profile["workflowPath"],
    }
    stale = {
        key: (source_run.get(key), expected)
        for key, expected in required_run.items()
        if source_run.get(key) != expected
    }
    if stale:
        raise ProposalError(f"source run boundary changed: {stale}")
    if source_run.get("event") not in profile["events"]:
        raise ProposalError(f"unsupported source event: {source_run.get('event')}")
    run_id = source_run.get("id")
    head_sha = source_run.get("head_sha")
    if not isinstance(run_id, int) or run_id < 1:
        raise ProposalError("source run ID invalid")
    if not isinstance(head_sha, str) or len(head_sha) != 40:
        raise ProposalError("source run head SHA invalid")
    artifacts = source_artifacts.get("artifacts")
    if not isinstance(artifacts, list):
        raise ProposalError("source artifact list missing")
    matches = [
        item
        for item in artifacts
        if isinstance(item, dict) and item.get("name") == profile["artifact"]
    ]
    if len(matches) != 1:
        raise ProposalError(f"expected one source analysis artifact, found {len(matches)}")
    artifact = matches[0]
    digest = artifact.get("digest")
    artifact_id = artifact.get("id")
    if (
        artifact.get("expired") is not False
        or not isinstance(digest, str)
        or not digest.startswith("sha256:")
        or len(digest) != 71
        or not isinstance(artifact_id, int)
        or artifact_id < 1
    ):
        raise ProposalError("source artifact invalid")
    workflow_run = artifact.get("workflow_run")
    if isinstance(workflow_run, dict) and workflow_run.get("id") not in (None, run_id):
        raise ProposalError("source artifact belongs to another run")
    return {
        "runId": run_id,
        "headSha": head_sha,
        "stageId": stage,
        "workflowName": workflow_name,
        "artifactId": artifact_id,
        "artifactName": profile["artifact"],
        "artifactDigest": digest,
    }


def validate_anchors(
    reference_contract: Any,
    dataset: dict[str, Any],
    readiness: dict[str, Any],
    analysis: dict[str, Any],
    pilot: dict[str, Any] | None,
) -> dict[str, Any]:
    parameter_count = len(inspect.signature(reference_contract.validate).parameters)
    if parameter_count >= 4:
        return reference_contract.validate(dataset, readiness, analysis, pilot)
    return reference_contract.validate(dataset, readiness)


def build(
    dataset_path: Path,
    readiness_path: Path,
    analysis_path: Path,
    source_run_path: Path,
    source_artifacts_path: Path,
    reference_contract_path: Path,
    training_design_code_path: Path,
    training_design_spec_path: Path,
    importance_policy_path: Path,
    source_pilot_manifest_path: Path | None = None,
):
    dataset = load(dataset_path)
    readiness = load(readiness_path)
    analysis = load(analysis_path)
    source = validate_source(analysis, load(source_run_path), load(source_artifacts_path))
    reference_contract = load_module("reference_dataset_contract", reference_contract_path)
    training_design = load_module("training_design", training_design_code_path)
    pilot = None if source_pilot_manifest_path is None else load(source_pilot_manifest_path)
    anchors = validate_anchors(reference_contract, dataset, readiness, analysis, pilot)
    full_design = training_design.build(
        training_design.load(training_design_spec_path), importance_policy_path
    )
    if (
        anchors.get("status") != "REFERENCE_ANCHORS_VALIDATED"
        or anchors.get("anchorCount") != 6
        or anchors.get("trainingAutomaticallyAuthorized") is not False
    ):
        raise ProposalError("reference anchors not valid")
    hard_ids = anchors.get("hardValidationAnchorIds")
    soft_ids = anchors.get("softDiagnosticAnchorIds")
    if hard_ids is None and soft_ids is None:
        hard_ids = sorted(item["groupId"] for item in anchors["anchors"])
        soft_ids = []
    if not isinstance(hard_ids, list) or not isinstance(soft_ids, list):
        raise ProposalError("reference anchor partition missing")
    if (len(hard_ids), len(soft_ids)) not in {(6, 0), (5, 1)}:
        raise ProposalError(f"unsupported hard/soft anchor partition: {len(hard_ids)}/{len(soft_ids)}")
    if set(hard_ids) & set(soft_ids):
        raise ProposalError("hard and soft anchor sets overlap")

    tiers = full_design.get("executionTiers")
    matches = [
        item for item in tiers if isinstance(item, dict) and item.get("tierId") == TIER_ID
    ] if isinstance(tiers, list) else []
    if len(matches) != 1:
        raise ProposalError("tier-1 summary missing/duplicated")
    tier = matches[0]
    geometry_ids = tier.get("geometryIds")
    case_ids = tier.get("caseIds")
    if not isinstance(geometry_ids, list) or not isinstance(case_ids, list):
        raise ProposalError("tier-1 IDs missing")
    geometry_set = set(geometry_ids)
    case_set = set(case_ids)
    geometries = [
        item for item in full_design.get("geometries", [])
        if item.get("geometryId") in geometry_set
    ]
    cases = [
        item for item in full_design.get("cases", [])
        if item.get("caseId") in case_set
    ]
    if len(geometries) != 48 or len(cases) != 96:
        raise ProposalError(
            f"tier-1 size changed: {len(geometries)} geometries, {len(cases)} cases"
        )
    if (
        {item.get("geometryId") for item in geometries} != geometry_set
        or {item.get("caseId") for item in cases} != case_set
        or any(item.get("executionTierId") != TIER_ID for item in geometries + cases)
    ):
        raise ProposalError("tier selection mismatch")
    photon_sum = sum(int(item.get("photonHistories", -1)) for item in cases)
    if photon_sum != tier.get("configuredMcPhotonsSum") or photon_sum != 6_960_000_000:
        raise ProposalError(f"tier-1 photon sum changed: {photon_sum}")
    if [item.get("ordinal") for item in cases] != list(range(1, 97)):
        raise ProposalError("tier-1 ordinals changed")
    if len({item.get("seed") for item in cases}) != 96:
        raise ProposalError("tier-1 seeds are not unique")

    anchor_ids = sorted(hard_ids + soft_ids)
    if anchor_ids != sorted(full_design.get("externalValidationAnchorIds", [])):
        raise ProposalError("anchor IDs differ from frozen design")
    training_ids = [
        item for item in full_design.get("trainingGeometryIds", []) if item in geometry_set
    ]
    holdout_ids = [
        item for item in full_design.get("internalHoldoutGeometryIds", [])
        if item in geometry_set
    ]
    if set(training_ids) & set(holdout_ids) or set(training_ids) | set(holdout_ids) != geometry_set:
        raise ProposalError("training/holdout partition invalid")

    bindings = {
        "sourceAnalysisRawSha256": raw_sha256(analysis_path),
        "sourceDatasetRawSha256": raw_sha256(dataset_path),
        "sourceReadinessRawSha256": raw_sha256(readiness_path),
        "referenceContractRawSha256": raw_sha256(reference_contract_path),
        "trainingDesignCodeRawSha256": raw_sha256(training_design_code_path),
        "trainingDesignSpecRawSha256": raw_sha256(training_design_spec_path),
        "importancePolicyRawSha256": raw_sha256(importance_policy_path),
    }
    if source_pilot_manifest_path is not None:
        bindings["sourcePilotManifestRawSha256"] = raw_sha256(source_pilot_manifest_path)

    proposal = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "batchId": "twilight-surrogate-space-filling-v1-tier-1",
        "status": "PROPOSAL_ONLY_NOT_AUTHORIZATION",
        "mode": "scientific-proposal",
        "proposalOnly": True,
        "scientificExecution": False,
        "successDoesNotAuthorizeProduction": True,
        "observationValidationRequired": True,
        "authorizationRequired": True,
        "source": source,
        "bindings": bindings,
        "executionTierId": TIER_ID,
        "purpose": tier.get("purpose"),
        "geometryCount": 48,
        "caseCount": 96,
        "configuredMcPhotonsSum": photon_sum,
        "method": "alis",
        "blocksPerGeometry": full_design.get("blocksPerGeometry"),
        "sampling": full_design.get("sampling"),
        "importanceSamplingPolicy": full_design.get("importanceSamplingPolicy"),
        "parameterRanges": full_design.get("parameterRanges"),
        "photonSchedule": full_design.get("photonSchedule"),
        "trainingGeometryIds": training_ids,
        "internalHoldoutGeometryIds": holdout_ids,
        "externalValidationAnchorIds": anchor_ids,
        "hardExternalValidationAnchorIds": sorted(hard_ids),
        "softDiagnosticAnchorIds": sorted(soft_ids),
        "referenceAnchorPolicy": {
            "allExcludedFromFitting": True,
            "hardAnchorsGateComputationalAcceptance": True,
            "softDiagnosticsAreReportOnly": True,
            "softDiagnosticsCannotCompensateForFailedPrecision": True,
        },
        "geometries": geometries,
        "cases": cases,
        "adaptiveContinuation": full_design.get("adaptiveContinuation"),
        "surrogateTrainingAutomaticallyAuthorized": False,
        "productionModelReady": False,
        "boundary": (
            "tier-1 proposal only; all six computational points are excluded from fitting; "
            "only hard anchors may gate computational model acceptance; soft diagnostics are "
            "report-only; separate one-purpose authorization and observation validation remain required"
        ),
    }
    tier_readiness = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "TIER_1_PROPOSAL_READY_PENDING_SEPARATE_AUTHORIZATION",
        "referenceAnchorCount": 6,
        "hardValidationAnchorCount": len(hard_ids),
        "softDiagnosticAnchorCount": len(soft_ids),
        "geometryCount": 48,
        "caseCount": 96,
        "configuredMcPhotonsSum": photon_sum,
        "scientificExecution": False,
        "executionAuthorized": False,
        "surrogateTrainingAuthorized": False,
        "productionModelReady": False,
        "observationValidationRequired": True,
        "sourceRunId": source["runId"],
        "sourceArtifactDigest": source["artifactDigest"],
    }
    return anchors, proposal, tier_readiness


def main() -> int:
    parser = argparse.ArgumentParser()
    for name in (
        "dataset",
        "readiness",
        "analysis",
        "source-run",
        "source-artifacts",
        "reference-contract",
        "training-design-code",
        "training-design-spec",
        "importance-policy",
        "output-dir",
    ):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--source-pilot-manifest", type=Path)
    args = parser.parse_args()
    try:
        anchors, proposal, readiness = build(
            args.dataset,
            args.readiness,
            args.analysis,
            args.source_run,
            args.source_artifacts,
            args.reference_contract,
            args.training_design_code,
            args.training_design_spec,
            args.importance_policy,
            args.source_pilot_manifest,
        )
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "validated-reference-anchors.json").write_text(dump(anchors))
        (args.output_dir / "tier-1-scientific-proposal.json").write_text(dump(proposal))
        (args.output_dir / "tier-1-readiness.json").write_text(dump(readiness))
        print(dump(readiness), end="")
        return 0
    except Exception as exc:
        print(
            dump(
                {
                    "schemaVersion": 1,
                    "stageId": STAGE_ID,
                    "status": "REFUSED",
                    "reason": str(exc),
                }
            ),
            file=sys.stderr,
            end="",
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
