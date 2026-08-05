from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
from typing import Any


def _core():
    path = Path(__file__).with_name("review_core.py")
    spec = importlib.util.spec_from_file_location("wave1_v4_review_core", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_preregistration(root: Path | None = None) -> dict[str, Any]:
    c = _core()
    root = (root or c.repository_root()).resolve()
    plan, base, wave_v2, proposal, source_seeds, ordered = c.proposal(root)
    v3 = c.load_module(root / c.V3_PACKAGE_PATH, "tier1_wave1_v3_source_for_v4")
    v3_prereg = v3.build_preregistration(root)
    v3.validate_preregistration(v3_prereg, root)
    if v3_prereg.get("preregistrationSha256") != c.V3_PREREGISTRATION_SHA256:
        raise c.Refusal("consumed ordinal-9 preregistration binding changed")
    v2_prereg = wave_v2.build_preregistration(root)
    wave_v2.validate_preregistration(v2_prereg, root)
    source_records = {row["geometryId"]: row for row in proposal["sourceRecords"]}
    cases = []
    for case_ordinal, row in enumerate(base.wave_cases(proposal, c.WAVE, base.CONTINUATION_GEOMETRY_IDS), start=1):
        source = source_records[row["groupId"]]
        base_case_id = row["caseId"]
        cases.append({
            **copy.deepcopy(row),
            "caseId": base_case_id.replace("precision-continuation-v2", "precision-continuation-v4"),
            "baseCaseId": base_case_id,
            "caseOrdinal": case_ordinal,
            "replacementGeneration": 4,
            "geometry": copy.deepcopy(source["geometry"]),
            "preservedSourceCaseIds": list(source["caseIds"]),
            "preservedSourceValuesCdM2": list(source["valuesCdM2"]),
            "preservedZeroHitCaseIds": list(source["zeroHitCaseIds"]),
        })
    historical = set(wave_v2.ORDINAL1_SEEDS) | set(source_seeds) | set(wave_v2.CONSUMED_PROBE_SEEDS)
    ordinal8 = [row["seed"] for row in v2_prereg["cases"]]
    ordinal9 = [row["seed"] for row in v3_prereg["cases"]]
    replacement = [row["seed"] for row in cases]
    if len(historical) != 196 or set(replacement) & historical or set(replacement) & set(ordinal8) or set(replacement) & set(ordinal9):
        raise c.Refusal("replacement seed universe overlaps consumed evidence")
    if replacement != ordered:
        raise c.Refusal("case ordering and seed-plan ordering diverged")
    training_ids = sorted(row["geometryId"] for row in proposal["sourceRecords"] if row["role"] == "surrogate-training")
    holdout_ids = sorted(row["geometryId"] for row in proposal["sourceRecords"] if row["role"] == "internal-holdout")
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
        raise c.Refusal("frozen scientific scope changed")
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
        "consumedOrdinal8": copy.deepcopy(v3_prereg["consumedOrdinal8"]),
        "consumedOrdinal9": {
            "runId": c.CONSUMED_ORDINAL9_RUN,
            "preflightJobId": c.CONSUMED_ORDINAL9_JOB,
            "authorizationOrdinal": 9,
            "authorizationRef": c.CONSUMED_ORDINAL9_REF,
            "executionKey": c.CONSUMED_ORDINAL9_KEY,
            "runTitle": c.CONSUMED_ORDINAL9_TITLE,
            "failureStage": "freeze-case-matrix-shell-quoting",
            "syntaxChecks": 0,
            "solverExecutions": 0,
            "completedPhotonHistories": 0,
            "seedsConsumedOnDispatch": True,
        },
        "sourceBindings": {
            "v3PreregistrationSha256": c.V3_PREREGISTRATION_SHA256,
            "v3PackageRawSha256": c.raw_sha256(root / c.V3_PACKAGE_PATH),
            "v2BaseProposalSha256": proposal["proposalSha256"],
            "seedPlanPath": c.SEED_PLAN_PATH,
            "seedPlanRawSha256": c.raw_sha256(root / c.SEED_PLAN_PATH),
            "duplicateSearchSnapshotPath": c.DUPLICATE_SNAPSHOT_PATH,
            "duplicateSearchSnapshotRawSha256": c.raw_sha256(root / c.DUPLICATE_SNAPSHOT_PATH),
            "ordinal2Source": copy.deepcopy(proposal["source"]),
        },
        "wave": c.WAVE,
        "blocks": list(c.BLOCKS),
        "geometryIds": list(base.CONTINUATION_GEOMETRY_IDS),
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
            "preOrdinal8HistoricalSeedCount": len(historical),
            "preOrdinal8HistoricalSeedsSha256": c.canonical_sha256(sorted(historical)),
            "ordinal8WaveSeedCount": len(ordinal8),
            "ordinal8WaveSeedsSha256": c.canonical_sha256(ordinal8),
            "ordinal9WaveSeedCount": len(ordinal9),
            "ordinal9WaveSeedsSha256": c.canonical_sha256(ordinal9),
            "replacementWaveSeedCount": len(replacement),
            "replacementWaveSeedsSha256": c.canonical_sha256(replacement),
            "allReplacementSeedsUnique": len(set(replacement)) == c.CASE_COUNT,
            "historicalOverlap": [],
            "ordinal8Overlap": [],
            "ordinal9Overlap": [],
            "futureWaveOverlap": [],
            "seedsConsumedOnDispatchEvenOnPreflightFailure": True,
        },
        "thresholds": copy.deepcopy(v3_prereg["thresholds"]),
        "stoppingRule": copy.deepcopy(v3_prereg["stoppingRule"]),
        "classifications": copy.deepcopy(v3_prereg["classifications"]),
        "executionContract": {
            **copy.deepcopy(v3_prereg["executionContract"]),
            "matrixOutputWrittenByDedicatedPythonCli": True,
            "matrixOutputBashRegressionRequired": True,
            "nestedShellCommandSubstitutionForbidden": True,
        },
        "preservation": {
            **copy.deepcopy(v3_prereg["preservation"]),
            "ordinal9EvidenceImmutable": True,
            "ordinal9WorkflowNotRerun": True,
            "onlyWave1SeedsVersionedIdentityAndMatrixEmissionChange": True,
        },
        "surrogateTrainingAuthorized": False,
        "internalHoldoutOpeningAuthorized": False,
        "tier2Authorized": False,
        "productionPromotionAuthorized": False,
        "boundary": "review-only v4 replacement preparation; no identity allocation, authorization, dispatch, solver execution, fitting, holdout opening, Tier-2, or production action",
    }
    value["preregistrationSha256"] = c.canonical_sha256(value)
    return value


def validate_preregistration(value: dict[str, Any], root: Path | None = None) -> None:
    c = _core()
    if not isinstance(value, dict):
        raise c.Refusal("v4 preregistration missing")
    payload = {key: item for key, item in value.items() if key != "preregistrationSha256"}
    if value.get("preregistrationSha256") != c.canonical_sha256(payload) or value != build_preregistration(root):
        raise c.Refusal("v4 preregistration differs from frozen generation")


def authorization_template(preregistration: dict[str, Any], root: Path | None = None) -> dict[str, Any]:
    c = _core()
    validate_preregistration(preregistration, root)
    value = {
        "schemaVersion": 1,
        "stageId": "tier1-precision-continuation-wave1-authorization-template-v4",
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
    snapshot = c.load_json(root / c.DUPLICATE_SNAPSHOT_PATH)
    if snapshot.get("realOrdinalCollisionMatches") != [] or snapshot.get("candidateAllocated") is not False:
        raise c.Refusal("ordinal-10 collision review did not pass")
    value = {
        "schemaVersion": 1,
        "stageId": "tier1-precision-continuation-wave1-v4-candidate-review",
        "status": "READY_FOR_REVIEW_NOT_AUTHORIZATION",
        "sourceMainSha": c.SOURCE_MAIN_SHA,
        "candidateIdentity": copy.deepcopy(preregistration["candidateIdentity"]),
        "preregistrationSha256": preregistration["preregistrationSha256"],
        "caseCount": c.CASE_COUNT,
        "geometryCount": c.GEOMETRY_COUNT,
        "maximumConfiguredPhotonHistories": c.MAX_CONFIGURED_PHOTON_HISTORIES,
        "replacementSeedSha256": preregistration["seedProof"]["replacementWaveSeedsSha256"],
        "historicalOverlap": [],
        "ordinal8Overlap": [],
        "ordinal9Overlap": [],
        "futureWaveOverlap": [],
        "matrixRegressionRequired": True,
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
        "status": "DETERMINISTIC_REVIEW_ARTIFACTS_GENERATED",
        "sourceMainSha": c.SOURCE_MAIN_SHA,
        "fileHashes": hashes,
        "authorizationAllocated": False,
        "dispatchEnabled": False,
        "scientificExecution": False,
    }
    report["reportSha256"] = c.canonical_sha256(report)
    (output_dir / "generation-report.json").write_text(c.dump(report), encoding="utf-8", newline="\n")
    return report
