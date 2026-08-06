#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import importlib.util
from pathlib import Path
from typing import Any


def _core():
    path = Path(__file__).with_name("core.py")
    spec = importlib.util.spec_from_file_location("wave2_v1_core", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_preregistration(root: Path | None = None) -> dict[str, Any]:
    c = _core()
    root = (root or c.repository_root()).resolve()
    state = c.proposal(root)
    base = state["base"]
    proposal = state["proposal"]
    descriptor = state["descriptor"]
    plan = state["plan"]
    source_records = {row["geometryId"]: row for row in proposal["sourceRecords"]}
    cases = []
    for case_ordinal, row in enumerate(
        base.wave_cases(proposal, c.WAVE, c.ACTIVE_GEOMETRY_IDS), start=1
    ):
        source = source_records[row["groupId"]]
        base_case_id = row["caseId"]
        cases.append(
            {
                **copy.deepcopy(row),
                "caseId": base_case_id.replace(
                    "precision-continuation-v2",
                    "precision-continuation-wave2-v1",
                ),
                "baseCaseId": base_case_id,
                "caseOrdinal": case_ordinal,
                "waveGeneration": 1,
                "geometry": copy.deepcopy(source["geometry"]),
                "preservedSourceCaseIds": list(source["caseIds"]),
                "preservedSourceValuesCdM2": list(source["valuesCdM2"]),
                "preservedZeroHitCaseIds": list(source["zeroHitCaseIds"]),
                "sourceWave1SalvageDescriptorSha256": descriptor["descriptorSha256"],
            }
        )
    training_ids = sorted(
        gid for gid in c.ACTIVE_GEOMETRY_IDS if source_records[gid]["role"] == "surrogate-training"
    )
    holdout_ids = sorted(
        gid for gid in c.ACTIVE_GEOMETRY_IDS if source_records[gid]["role"] == "internal-holdout"
    )
    if (
        len(cases) != c.CASE_COUNT
        or len({row["caseId"] for row in cases}) != c.CASE_COUNT
        or len({row["groupId"] for row in cases}) != c.GEOMETRY_COUNT
        or {row["block"] for row in cases} != set(c.BLOCKS)
        or len(training_ids) != c.TRAINING_GEOMETRY_COUNT
        or len(holdout_ids) != c.HOLDOUT_GEOMETRY_COUNT
        or sum(row["role"] == "surrogate-training" for row in cases) != c.TRAINING_CASE_COUNT
        or sum(row["role"] == "internal-holdout" for row in cases) != c.HOLDOUT_CASE_COUNT
        or sum(row["photonHistories"] for row in cases) != c.MAX_CONFIGURED_PHOTON_HISTORIES
    ):
        raise c.Refusal("frozen wave-two scientific scope changed")
    value = {
        "schemaVersion": 1,
        "stageId": c.STAGE_ID,
        "status": "PREPARATION_ONLY_NOT_AUTHORIZED",
        "sourceMainSha": c.SOURCE_MAIN_SHA,
        "proposalOnly": True,
        "scientificExecution": False,
        "authorizationEnabled": False,
        "authorizationOrdinal": None,
        "authorizationRef": None,
        "executionKey": None,
        "dispatchEnabled": False,
        "workflowDispatchEnabled": False,
        "solverExecutionAuthorized": False,
        "githubRerunAllowed": False,
        "candidateIdentity": copy.deepcopy(plan["candidateIdentity"]),
        "consumedOrdinal11": copy.deepcopy(descriptor["scientificSource"]),
        "sourceBindings": {
            "sourceSalvageDescriptorPath": c.SOURCE_DESCRIPTOR_PATH,
            "sourceSalvageDescriptorRawSha256": c.raw_sha256(root / c.SOURCE_DESCRIPTOR_PATH),
            "sourceSalvageDescriptorSha256": descriptor["descriptorSha256"],
            "sourceSalvageRunId": c.SOURCE_SALVAGE_RUN_ID,
            "sourceSalvageArtifactId": c.SOURCE_SALVAGE_ARTIFACT_ID,
            "sourceSalvageArtifactDigest": c.SOURCE_SALVAGE_ARTIFACT_DIGEST,
            "sourceAggregateRawSha256": c.SOURCE_AGGREGATE_RAW_SHA256,
            "sourceAuditRawSha256": c.SOURCE_AUDIT_RAW_SHA256,
            "sourceAnalysisRawSha256": c.SOURCE_ANALYSIS_RAW_SHA256,
            "sourceSalvageReportRawSha256": c.SOURCE_SALVAGE_REPORT_RAW_SHA256,
            "seedPlanPath": c.SEED_PLAN_PATH,
            "seedPlanRawSha256": c.raw_sha256(root / c.SEED_PLAN_PATH),
            "duplicateSearchSnapshotPath": c.DUPLICATE_SNAPSHOT_PATH,
            "duplicateSearchSnapshotRawSha256": c.raw_sha256(root / c.DUPLICATE_SNAPSHOT_PATH),
            "v2BaseProposalSha256": proposal["proposalSha256"],
            "ordinal2Source": copy.deepcopy(proposal["source"]),
        },
        "wave": c.WAVE,
        "blocks": list(c.BLOCKS),
        "geometryIds": list(c.ACTIVE_GEOMETRY_IDS),
        "geometryCount": c.GEOMETRY_COUNT,
        "trainingGeometryIds": training_ids,
        "internalHoldoutGeometryIds": holdout_ids,
        "roleCounts": {
            "surrogateTrainingGeometries": c.TRAINING_GEOMETRY_COUNT,
            "internalHoldoutGeometries": c.HOLDOUT_GEOMETRY_COUNT,
            "surrogateTrainingCases": c.TRAINING_CASE_COUNT,
            "internalHoldoutCases": c.HOLDOUT_CASE_COUNT,
        },
        "caseCount": c.CASE_COUNT,
        "maximumConfiguredPhotonHistories": c.MAX_CONFIGURED_PHOTON_HISTORIES,
        "cases": cases,
        "seedProof": {
            "preOrdinal8HistoricalSeedCount": len(state["historicalSeeds"]),
            "preOrdinal8HistoricalSeedsSha256": c.canonical_sha256(sorted(state["historicalSeeds"])),
            "ordinal8WaveSeedCount": len(state["ordinal8"]),
            "ordinal8WaveSeedsSha256": c.canonical_sha256(state["ordinal8"]),
            "ordinal9WaveSeedCount": len(state["ordinal9"]),
            "ordinal9WaveSeedsSha256": c.canonical_sha256(state["ordinal9"]),
            "ordinal10WaveSeedCount": len(state["ordinal10"]),
            "ordinal10WaveSeedsSha256": c.canonical_sha256(state["ordinal10"]),
            "ordinal11WaveSeedCount": len(state["ordinal11"]),
            "ordinal11WaveSeedsSha256": c.canonical_sha256(state["ordinal11"]),
            "preservedFutureSeedCount": len(state["preservedFuture"]),
            "preservedFutureSeedsSha256": c.canonical_sha256(state["preservedFuture"]),
            "wave2SeedCount": len(state["ordered"]),
            "wave2SeedsSha256": c.canonical_sha256(state["ordered"]),
            "allWave2SeedsUnique": len(set(state["ordered"])) == c.CASE_COUNT,
            "historicalOverlap": [],
            "ordinal8Overlap": [],
            "ordinal9Overlap": [],
            "ordinal10Overlap": [],
            "ordinal11Overlap": [],
            "preservedFutureOverlap": [],
            "seedsConsumedOnDispatchEvenOnPreflightFailure": True,
        },
        "sourceWave1ClassificationCounts": copy.deepcopy(descriptor["classificationCounts"]),
        "sourceWave1NextGeometryIds": list(descriptor["nextWaveGeometryIds"]),
        "thresholds": {
            "targetRelativeStandardErrorOfMean": base.TARGET_RSEM,
            "acceptedMaximumRelativeStandardErrorOfMean": base.ACCEPTED_MAX_RSEM,
        },
        "stoppingRule": {
            "waveBoundaryBlocks": list(c.BLOCKS),
            "nextWaveOnlyForAdaptiveContinuationRequired": True,
            "zeroHitOrdinaryRsemForbidden": True,
            "zeroHitRemainsAdaptiveUntilEightBlockCap": True,
            "maximumTotalBlocks": base.MAX_TOTAL_BLOCKS,
            "unresolvedAtMaximumClassification": [
                "PRECISION_CONTINUATION_EXHAUSTED",
                "PRECISION_CONTINUATION_EXHAUSTED_ZERO_HIT",
            ],
            "automaticNextWave": False,
        },
        "executionContract": {
            "caseJobs": c.CASE_COUNT,
            "failFast": False,
            "maximumParallelCases": 8,
            "syntaxChecksPerCase": 1,
            "solverExecutionsPerCaseMaximum": 1,
            "retryAllowed": False,
            "resumeAllowed": False,
            "githubRerunAllowed": False,
            "aggregateOnlyAfterAllCases": True,
            "independentAuditRequired": True,
            "analysisRequired": True,
            "sourceWave1SalvageMustBeReverified": True,
        },
        "preservation": {
            "ordinal11EvidenceImmutable": True,
            "ordinal11WorkflowNotRerun": True,
            "ordinal11IdentityNeverReused": True,
            "ordinal11SeedsNeverReused": True,
            "b1ThroughB4EvidenceImmutable": True,
            "physicalInputsUnchanged": True,
            "geometryRolesUnchanged": True,
            "photonHistoriesPerBlockUnchanged": True,
            "thresholdsUnchanged": True,
            "stoppingRuleUnchanged": True,
            "zeroHitTreatmentUnchanged": True,
            "onlyActiveSetBlocksSeedsAndFreshIdentityMayChange": True,
        },
        "surrogateTrainingAuthorized": False,
        "internalHoldoutOpeningAuthorized": False,
        "tier2Authorized": False,
        "productionPromotionAuthorized": False,
        "boundary": "review-only wave-two preparation; no identity allocation, authorization, dispatch, solver execution, fitting, holdout opening, Tier-2, or production action",
    }
    value["preregistrationSha256"] = c.canonical_sha256(value)
    return value


def validate_preregistration(value: dict[str, Any], root: Path | None = None) -> None:
    c = _core()
    if not isinstance(value, dict):
        raise c.Refusal("wave-two preregistration missing")
    payload = {key: item for key, item in value.items() if key != "preregistrationSha256"}
    if value.get("preregistrationSha256") != c.canonical_sha256(payload) or value != build_preregistration(root):
        raise c.Refusal("wave-two preregistration differs from frozen generation")


def authorization_template(preregistration: dict[str, Any], root: Path | None = None) -> dict[str, Any]:
    c = _core()
    validate_preregistration(preregistration, root)
    value = {
        "schemaVersion": 1,
        "stageId": "tier1-precision-continuation-wave2-authorization-template-v1",
        "status": "DISABLED_TEMPLATE_NOT_AUTHORIZATION",
        "preregistrationSha256": preregistration["preregistrationSha256"],
        "wave": c.WAVE,
        "blocks": list(c.BLOCKS),
        "caseCount": c.CASE_COUNT,
        "enabled": False,
        "authorizationOrdinal": None,
        "authorizationRef": None,
        "authorizationCommit": None,
        "executionKey": None,
        "dispatch": False,
        "workflowDispatchEnabled": False,
        "runAttempt": None,
        "automaticDispatch": False,
        "githubRerunAllowed": False,
        "solverExecutionAuthorized": False,
    }
    value["templateSha256"] = c.canonical_sha256(value)
    return value


def candidate_review(preregistration: dict[str, Any], root: Path | None = None) -> dict[str, Any]:
    c = _core()
    root = (root or c.repository_root()).resolve()
    validate_preregistration(preregistration, root)
    snapshot = c.duplicate_snapshot(root)
    value = {
        "schemaVersion": 1,
        "stageId": "tier1-precision-continuation-wave2-v1-candidate-review",
        "status": "READY_FOR_REVIEW_NOT_AUTHORIZATION",
        "sourceMainSha": c.SOURCE_MAIN_SHA,
        "candidateIdentity": copy.deepcopy(preregistration["candidateIdentity"]),
        "preregistrationSha256": preregistration["preregistrationSha256"],
        "duplicateSnapshotSha256": snapshot["snapshotSha256"],
        "sourceSalvageDescriptorSha256": preregistration["sourceBindings"]["sourceSalvageDescriptorSha256"],
        "caseCount": c.CASE_COUNT,
        "geometryCount": c.GEOMETRY_COUNT,
        "maximumConfiguredPhotonHistories": c.MAX_CONFIGURED_PHOTON_HISTORIES,
        "wave2SeedSha256": preregistration["seedProof"]["wave2SeedsSha256"],
        "historicalOverlap": [],
        "ordinal8Overlap": [],
        "ordinal9Overlap": [],
        "ordinal10Overlap": [],
        "ordinal11Overlap": [],
        "preservedFutureOverlap": [],
        "authorizationAllocated": False,
        "dispatchEnabled": False,
        "scientificExecution": False,
        "surrogateTrainingAuthorized": False,
        "internalHoldoutOpeningAuthorized": False,
        "tier2Authorized": False,
        "productionPromotionAuthorized": False,
    }
    value["packetSha256"] = c.canonical_sha256(value)
    return value


def write_generated(root: Path, output_dir: Path) -> dict[str, Any]:
    c = _core()
    prereg = build_preregistration(root)
    values = {
        "preregistration.json": prereg,
        "authorization.template.json": authorization_template(prereg, root),
        "candidate-review.json": candidate_review(prereg, root),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for name, value in values.items():
        path = output_dir / name
        path.write_text(c.dump(value), encoding="utf-8", newline="\n")
        hashes[name] = c.raw_sha256(path)
    report = {
        "schemaVersion": 1,
        "stageId": "tier1-precision-continuation-wave2-v1-generation-report",
        "status": "DETERMINISTIC_REVIEW_ARTIFACTS_GENERATED",
        "sourceMainSha": c.SOURCE_MAIN_SHA,
        "fileHashes": hashes,
        "authorizationAllocated": False,
        "dispatchEnabled": False,
        "scientificExecution": False,
        "surrogateTrainingAuthorized": False,
        "internalHoldoutOpeningAuthorized": False,
        "tier2Authorized": False,
        "productionPromotionAuthorized": False,
    }
    report["reportSha256"] = c.canonical_sha256(report)
    (output_dir / "generation-report.json").write_text(
        c.dump(report), encoding="utf-8", newline="\n"
    )
    return report


def main() -> int:
    c = _core()
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(c.dump(write_generated(c.repository_root(), args.output_dir)), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
