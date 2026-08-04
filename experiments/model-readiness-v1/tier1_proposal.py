#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

STAGE_ID = "twilight-surrogate-tier-1-proposal-v1"
SOURCE_STAGE_ID = "cross-geometry-held-out-confirmation-timeout-continuation-v1"
SOURCE_ARTIFACT = "cross-geometry-timeout-continuation-v1-analysis"
TIER_ID = "tier-1-provisional"


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
    analysis: dict[str, Any], source_run: dict[str, Any], source_artifacts: dict[str, Any]
) -> dict[str, Any]:
    required_analysis = {
        "schemaVersion": 1,
        "stageId": SOURCE_STAGE_ID,
        "status": "TIMEOUT_CONTINUATION_ANALYZED",
        "computationalReferenceScreeningComplete": True,
        "noAutomaticAdditionalBlocks": True,
        "screeningOnly": True,
        "successDoesNotAuthorizeProduction": True,
    }
    stale = {
        key: (analysis.get(key), expected)
        for key, expected in required_analysis.items()
        if analysis.get(key) != expected
    }
    if stale:
        raise ProposalError(f"source analysis is not complete and eligible: {stale}")

    required_run = {
        "status": "completed",
        "conclusion": "success",
        "event": "workflow_dispatch",
        "run_attempt": 1,
        "head_branch": "main",
        "name": "MYSTIC held-out timeout continuation v1 scientific execution",
        "path": ".github/workflows/mystic-batch-v1-cross-geometry-confirmation-timeout-continuation.yml",
    }
    stale = {
        key: (source_run.get(key), expected)
        for key, expected in required_run.items()
        if source_run.get(key) != expected
    }
    if stale:
        raise ProposalError(f"source run boundary changed: {stale}")
    run_id = source_run.get("id")
    if not isinstance(run_id, int) or run_id < 1:
        raise ProposalError("source run ID missing")
    head_sha = source_run.get("head_sha")
    if not isinstance(head_sha, str) or len(head_sha) != 40:
        raise ProposalError("source run head SHA invalid")

    artifacts = source_artifacts.get("artifacts")
    if not isinstance(artifacts, list):
        raise ProposalError("source artifact list missing")
    matches = [item for item in artifacts if isinstance(item, dict) and item.get("name") == SOURCE_ARTIFACT]
    if len(matches) != 1:
        raise ProposalError(f"expected one source analysis artifact, found {len(matches)}")
    artifact = matches[0]
    if artifact.get("expired") is not False:
        raise ProposalError("source analysis artifact is expired")
    digest = artifact.get("digest")
    if not isinstance(digest, str) or not digest.startswith("sha256:") or len(digest) != 71:
        raise ProposalError("source analysis artifact digest invalid")
    workflow_run = artifact.get("workflow_run")
    if isinstance(workflow_run, dict) and workflow_run.get("id") not in (None, run_id):
        raise ProposalError("source artifact belongs to another run")
    artifact_id = artifact.get("id")
    if not isinstance(artifact_id, int) or artifact_id < 1:
        raise ProposalError("source artifact ID invalid")
    return {
        "runId": run_id,
        "headSha": head_sha,
        "artifactId": artifact_id,
        "artifactName": SOURCE_ARTIFACT,
        "artifactDigest": digest,
    }


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
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    dataset = load(dataset_path)
    readiness = load(readiness_path)
    analysis = load(analysis_path)
    source = validate_source(analysis, load(source_run_path), load(source_artifacts_path))

    reference_contract = load_module("reference_dataset_contract", reference_contract_path)
    training_design = load_module("training_design", training_design_code_path)
    anchors = reference_contract.validate(dataset, readiness)
    full_design = training_design.build(training_design.load(training_design_spec_path), importance_policy_path)

    if anchors.get("status") != "REFERENCE_ANCHORS_VALIDATED" or anchors.get("anchorCount") != 6:
        raise ProposalError("reference anchor contract did not validate exactly six anchors")
    if anchors.get("trainingAutomaticallyAuthorized") is not False:
        raise ProposalError("reference anchor contract authorized training")

    tiers = full_design.get("executionTiers")
    if not isinstance(tiers, list):
        raise ProposalError("training design tiers missing")
    matches = [tier for tier in tiers if isinstance(tier, dict) and tier.get("tierId") == TIER_ID]
    if len(matches) != 1:
        raise ProposalError("tier-1 summary missing or duplicated")
    tier = matches[0]
    geometry_ids = tier.get("geometryIds")
    case_ids = tier.get("caseIds")
    if not isinstance(geometry_ids, list) or not isinstance(case_ids, list):
        raise ProposalError("tier-1 IDs missing")
    geometry_set = set(geometry_ids)
    case_set = set(case_ids)
    geometries = [item for item in full_design.get("geometries", []) if item.get("geometryId") in geometry_set]
    cases = [item for item in full_design.get("cases", []) if item.get("caseId") in case_set]
    if len(geometries) != 48 or len(cases) != 96:
        raise ProposalError(f"tier-1 size changed: {len(geometries)} geometries, {len(cases)} cases")
    if {item.get("geometryId") for item in geometries} != geometry_set:
        raise ProposalError("tier-1 geometry universe mismatch")
    if {item.get("caseId") for item in cases} != case_set:
        raise ProposalError("tier-1 case universe mismatch")
    if any(item.get("executionTierId") != TIER_ID for item in geometries + cases):
        raise ProposalError("non-tier-1 object selected")
    photon_sum = sum(int(item.get("photonHistories", -1)) for item in cases)
    if photon_sum != tier.get("configuredMcPhotonsSum") or photon_sum != 6_960_000_000:
        raise ProposalError(f"tier-1 photon sum changed: {photon_sum}")
    if [item.get("ordinal") for item in cases] != list(range(1, 97)):
        raise ProposalError("tier-1 case ordinals changed")
    if len({item.get("seed") for item in cases}) != 96:
        raise ProposalError("tier-1 seeds are not unique")

    anchor_ids = sorted(item["groupId"] for item in anchors["anchors"])
    if anchor_ids != sorted(full_design.get("externalValidationAnchorIds", [])):
        raise ProposalError("validated anchor IDs differ from frozen design")
    training_ids = [item for item in full_design.get("trainingGeometryIds", []) if item in geometry_set]
    holdout_ids = [item for item in full_design.get("internalHoldoutGeometryIds", []) if item in geometry_set]
    if set(training_ids) & set(holdout_ids) or set(training_ids) | set(holdout_ids) != geometry_set:
        raise ProposalError("tier-1 training and holdout partition invalid")

    bindings = {
        "sourceAnalysisRawSha256": raw_sha256(analysis_path),
        "sourceDatasetRawSha256": raw_sha256(dataset_path),
        "sourceReadinessRawSha256": raw_sha256(readiness_path),
        "referenceContractRawSha256": raw_sha256(reference_contract_path),
        "trainingDesignCodeRawSha256": raw_sha256(training_design_code_path),
        "trainingDesignSpecRawSha256": raw_sha256(training_design_spec_path),
        "importancePolicyRawSha256": raw_sha256(importance_policy_path),
    }
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
        "geometryCount": len(geometries),
        "caseCount": len(cases),
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
        "geometries": geometries,
        "cases": cases,
        "adaptiveContinuation": full_design.get("adaptiveContinuation"),
        "surrogateTrainingAutomaticallyAuthorized": False,
        "productionModelReady": False,
        "boundary": "tier-1 proposal only; six computational anchors are excluded from fitting; separate one-purpose authorization and observation validation remain required",
    }
    tier_readiness = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "TIER_1_PROPOSAL_READY_PENDING_SEPARATE_AUTHORIZATION",
        "referenceAnchorCount": 6,
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
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--readiness", type=Path, required=True)
    parser.add_argument("--analysis", type=Path, required=True)
    parser.add_argument("--source-run", type=Path, required=True)
    parser.add_argument("--source-artifacts", type=Path, required=True)
    parser.add_argument("--reference-contract", type=Path, required=True)
    parser.add_argument("--training-design-code", type=Path, required=True)
    parser.add_argument("--training-design-spec", type=Path, required=True)
    parser.add_argument("--importance-policy", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
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
        )
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "validated-reference-anchors.json").write_text(dump(anchors))
        (args.output_dir / "tier-1-scientific-proposal.json").write_text(dump(proposal))
        (args.output_dir / "tier-1-readiness.json").write_text(dump(readiness))
        print(dump(readiness), end="")
        return 0
    except Exception as exc:
        print(dump({"schemaVersion": 1, "stageId": STAGE_ID, "status": "REFUSED", "reason": str(exc)}), file=sys.stderr, end="")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
