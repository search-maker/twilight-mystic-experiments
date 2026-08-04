#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

STAGE_ID = "twilight-surrogate-tier-1-ordinal2-execution-v1"
EXECUTION_KEY = "twilight-surrogate-tier-1-v1:numerical:2"
AUTHORIZATION_ORDINAL = 2
EXPECTED_HEAD = "85248fcf7d0c3f1e1a79df69f362353998ca3e81"
EXPECTED_HISTORICAL_SOURCE_SHA = "999e47f4af4b5df6f85a6887fc105fc8f6e1a7cee89a3124f69ac8d8912c8e85"
EXPECTED_CURRENT_SOURCE_SHA = "64930cc40b6e4a37aa220520974d330fc1563796f466a649b2238131f2d69840"
EXPECTED_PACKAGE_SHA = "9090033a39a7e963ecabb31d5cbd264330c64ec1c4cb5f44be2e70f10cbc54c2"
EXPECTED_UVSPEC_SHA = "2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3"
EXPECTED_RUNTIME_LOCK_SHA = "3b5fbec964642b04c73a6423b3355dbcc4ba5e84f9614f6d74420491bacc20c5"
DECISION_COMMENT_ID = 5184173778
REVIEW_COMMENT_ID = 5184177959
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class GuardError(RuntimeError):
    pass


def load(path: Path) -> Any:
    return json.loads(path.read_text())


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def code_paths() -> dict[str, Path]:
    base = Path("experiments/mystic-batch-v1")
    return {
        "executionAdapterRawSha256": base / "twilight_surrogate_tier1_execution_adapter.py",
        "executionPlanRawSha256": base / "twilight_surrogate_tier1_execution_plan.py",
        "duplicateRunAuditRawSha256": base / "duplicate_run_audit.py",
        "runtimeProbeRawSha256": base / "runtime_probe.py",
        "runtimeLockRawSha256": base / "runtime-lock.micromamba.json",
        "executorRawSha256": base / "scientific_case_executor.py",
        "aggregateRawSha256": base / "scientific_aggregate.py",
        "auditRawSha256": base / "scientific_audit.py",
        "analysisDriverRawSha256": base / "twilight_surrogate_tier1_analysis.py",
        "ordinal2EvidenceBundleRawSha256": base / "twilight_surrogate_tier1_ordinal2_evidence_bundle.py",
        "ordinal2ExecutionGuardRawSha256": base / "twilight_surrogate_tier1_ordinal2_execution_guard.py",
        "ordinal2AuthorizationProposalCodeRawSha256": base / "twilight_surrogate_tier1_ordinal2_authorization_proposal.py",
        "ordinal2ExecutionWorkflowRawSha256": Path(".github/workflows/twilight-surrogate-tier-1-ordinal2-execution.yml"),
    }


def evidence_paths(root: Path) -> dict[str, Path]:
    return {
        "readinessDecisionRawSha256": root / "readiness-decision.json",
        "ordinal2ManifestRawSha256": root / "ordinal2-manifest.json",
        "ordinal2RecoveryReportRawSha256": root / "ordinal2-recovery-report.json",
        "sourceManifestRawSha256": root / "source-manifest.json",
        "ordinal1AuditRawSha256": root / "ordinal1-audit.json",
        "combinedProofReportRawSha256": root / "combined-proof.json",
        "sourceAuditReportRawSha256": root / "source-audit.json",
        "provenanceReportRawSha256": root / "provenance-report.json",
    }


def require(value: dict[str, Any], expected: dict[str, Any], label: str) -> None:
    stale = {key: (value.get(key), wanted) for key, wanted in expected.items() if value.get(key) != wanted}
    if stale:
        raise GuardError(f"{label} mismatch: {stale}")


def artifact(metadata: dict[str, Any], artifact_id: int, name: str, digest: str) -> None:
    rows = metadata.get("artifacts")
    if not isinstance(rows, list):
        raise GuardError("artifact metadata malformed")
    matches = [row for row in rows if row.get("id") == artifact_id]
    if len(matches) != 1:
        raise GuardError(f"artifact {artifact_id} not found exactly once")
    require(matches[0], {"name": name, "digest": digest, "expired": False}, f"artifact {artifact_id}")


def validate_metadata(metadata_dir: Path) -> dict[str, Any]:
    specs = {
        "readiness": (30946826336, 8907433018, "twilight-surrogate-tier-1-ordinal2-atm-z-grid-readiness-v1", "sha256:1146005822c5fc7ef5ad17e27f9cc9b6d950baac38bdc9222e779d3adff9ceb0"),
        "combined": (30946822822, 8907417508, "twilight-surrogate-tier-1-atm-z-grid-combined-spectral-proof-v3", "sha256:4d41e0fab492010e45da37273de9826dfee874e88a79f239d4cecd9a29a8de89"),
        "source-audit": (30946825851, 8907419354, "twilight-surrogate-tier-1-libradtran-source-audit-v1", "sha256:4a7a673ec63416e4ecb7735f4e3f1b1e591c5a0fb657b2e6bae120c99f4a38ed"),
        "provenance": (30946822824, 8907428859, "twilight-surrogate-tier-1-libradtran-provenance-recovery-v1", "sha256:2428a148fbcac0e68fe9bec41ecf5f53b775373786f025da759297246e9b4467"),
    }
    result: dict[str, Any] = {}
    for label, (run_id, artifact_id, name, digest) in specs.items():
        run = load(metadata_dir / f"{label}-run.json")
        artifacts = load(metadata_dir / f"{label}-artifacts.json")
        require(run, {"id": run_id, "conclusion": "success", "head_sha": EXPECTED_HEAD}, f"{label} run")
        artifact(artifacts, artifact_id, name, digest)
        result[label] = {"runId": run_id, "artifactId": artifact_id, "artifactDigest": digest, "headSha": EXPECTED_HEAD}
    return result


def validate_comments(comments_path: Path) -> None:
    payload = load(comments_path)
    rows = payload if isinstance(payload, list) else payload.get("comments", [])
    by_id = {row.get("id"): row.get("body", "") for row in rows if isinstance(row, dict)}
    decision = by_id.get(DECISION_COMMENT_ID, "")
    review = by_id.get(REVIEW_COMMENT_ID, "")
    required_decision = (
        "DECISION: APPROVE_BOUNDED_PACKAGE_RUNTIME_EXCEPTION",
        EXPECTED_CURRENT_SOURCE_SHA,
        EXPECTED_HISTORICAL_SOURCE_SHA,
        EXPECTED_PACKAGE_SHA,
        EXPECTED_UVSPEC_SHA,
        EXPECTED_RUNTIME_LOCK_SHA,
        "does **not** itself authorize scientific execution",
        "one-file-only, one-commit, unmerged authorization PR",
    )
    missing = [token for token in required_decision if token not in decision]
    if missing:
        raise GuardError(f"owner provenance decision incomplete: {missing}")
    required_review = (
        "INDEPENDENT DECISION REVIEW — COMPLETE",
        "all six required acknowledgements are present",
        "does not authorize execution or dispatch",
    )
    missing = [token for token in required_review if token not in review]
    if missing:
        raise GuardError(f"independent provenance review incomplete: {missing}")


def compare_manifests(source: dict[str, Any], recovered: dict[str, Any]) -> None:
    require(recovered, {"schemaVersion": 1, "stageId": "twilight-surrogate-tier-1-execution-v1", "proposalOnly": True, "scientificExecution": False, "successDoesNotAuthorizeProduction": True, "surrogateTrainingAutomaticallyAuthorized": False, "productionModelReady": False}, "ordinal-2 manifest")
    source_cases = source.get("cases", [])
    recovered_cases = recovered.get("cases", [])
    if len(source_cases) != 96 or len(recovered_cases) != 96:
        raise GuardError("manifest case count changed")
    if len(source.get("geometries", [])) != 48 or source.get("geometries") != recovered.get("geometries"):
        raise GuardError("manifest geometry set changed")
    immutable_top = (
        "batchId", "adapterId", "bindings", "externalValidationAnchorIds", "frozenInputs",
        "internalHoldoutGeometryIds", "limits", "runtime", "source", "sourcePilotManifestRawSha256",
        "sourceProposalStageId", "sourceTier1ProposalRawSha256", "trainingGeometryIds",
    )
    stale = [field for field in immutable_top if source.get(field) != recovered.get(field)]
    if stale:
        raise GuardError(f"manifest changed beyond recovery: {stale}")
    source_seeds: list[int] = []
    recovered_seeds: list[int] = []
    for before, after in zip(source_cases, recovered_cases):
        changed = {key for key in set(before) | set(after) if before.get(key) != after.get(key)}
        if changed != {"seed"}:
            raise GuardError(f"case changed beyond seed: {before.get('caseId')}: {changed}")
        source_seeds.append(before.get("seed"))
        recovered_seeds.append(after.get("seed"))
    if any(not isinstance(seed, int) for seed in source_seeds + recovered_seeds):
        raise GuardError("seed is not integer")
    if len(set(source_seeds)) != 96 or len(set(recovered_seeds)) != 96 or set(source_seeds) & set(recovered_seeds):
        raise GuardError("ordinal-2 fresh-seed governance failed")
    if sum(int(case.get("photonHistories", 0)) for case in recovered_cases) != 6_960_000_000:
        raise GuardError("photon accounting changed")
    if {case.get("alisSpectralImportanceSamplingNm") for case in recovered_cases} != {500.0, 550.0, 600.0}:
        raise GuardError("ALIS importance wavelength set changed")
    if any(case.get("role") not in {"surrogate-training", "internal-holdout"} for case in recovered_cases):
        raise GuardError("case role changed")
    if len(recovered.get("trainingGeometryIds", [])) != 39 or len(recovered.get("internalHoldoutGeometryIds", [])) != 9:
        raise GuardError("39/9 geometry role split changed")
    recovery = recovered.get("recovery", {})
    require(recovery, {"authorizationOrdinal": 2, "sourceAuthorizationOrdinal": 1, "executionKey": EXECUTION_KEY, "freshSeedsForAllCases": True, "firstAttemptOnly": True, "githubRerunPermitted": False, "scientificExecution": False, "executionAuthorized": False}, "manifest recovery")


def validate_evidence(evidence_dir: Path, metadata_dir: Path, comments_path: Path) -> dict[str, Any]:
    paths = evidence_paths(evidence_dir)
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise GuardError(f"evidence files missing: {missing}")
    metadata = validate_metadata(metadata_dir)
    validate_comments(comments_path)
    decision = load(evidence_dir / "readiness-decision.json")
    report = load(evidence_dir / "ordinal2-recovery-report.json")
    recovered = load(evidence_dir / "ordinal2-manifest.json")
    source = load(evidence_dir / "source-manifest.json")
    ordinal1 = load(evidence_dir / "ordinal1-audit.json")
    proof = load(evidence_dir / "combined-proof.json")
    source_audit = load(evidence_dir / "source-audit.json")
    provenance = load(evidence_dir / "provenance-report.json")
    compare_manifests(source, recovered)
    require(decision, {"schemaVersion": 1, "stageId": "twilight-surrogate-tier-1-ordinal2-readiness-v1", "status": "ORDINAL_2_ATM_Z_GRID_RECOVERY_READY_PENDING_SEPARATE_AUTHORIZATION_AND_SOURCE_PROVENANCE_DECISION", "geometryCount": 48, "caseCount": 96, "configuredMcPhotonsSum": 6_960_000_000, "freshSeedCount": 96, "syntaxCheckCount": 1, "solverExecutionCount": 0, "observerElevationRepresentation": "atm_z_grid", "authorizationPermitted": False, "ordinal2ScientificDispatchPermitted": False, "githubRerunPermitted": False, "scientificExecution": False, "scientificDatasetProduced": False, "surrogateTrainingAuthorized": False, "tier2Authorized": False, "productionModelReady": False}, "readiness decision")
    require(report, {"schemaVersion": 1, "stageId": "twilight-surrogate-tier-1-ordinal2-recovery-v2", "status": "ORDINAL_2_RECOVERY_FROZEN_WITH_ATM_Z_GRID_PENDING_SEPARATE_AUTHORIZATION", "executionKey": EXECUTION_KEY, "authorizationOrdinal": 2, "geometryCount": 48, "caseCount": 96, "configuredMcPhotonsSum": 6_960_000_000, "freshSeedCount": 96, "sourceSeedOverlapCount": 0, "observerElevationRepresentation": "atm_z_grid", "localSurfaceZoutKm": 0.0, "executionAuthorized": False, "authorizationPermitted": False, "ordinal2ScientificDispatchPermitted": False, "githubRerunPermitted": False, "scientificExecution": False, "surrogateTrainingAuthorized": False, "productionModelReady": False}, "recovery report")
    if report.get("recoveredManifestRawSha256") != raw_sha256(evidence_dir / "ordinal2-manifest.json") or report.get("sourceManifestRawSha256") != raw_sha256(evidence_dir / "source-manifest.json") or report.get("ordinal1AuditRawSha256") != raw_sha256(evidence_dir / "ordinal1-audit.json"):
        raise GuardError("recovery report hash binding changed")
    require(ordinal1, {"schemaVersion": 1, "stageId": "twilight-surrogate-tier-1-ordinal1-failure-audit-v2", "status": "ORDINAL_1_UNIFORMLY_FAILED_BEFORE_SCIENTIFIC_RESULT", "sourceAuthorizationOrdinal": 1, "authorizationConsumed": True, "validScientificCaseResultCount": 0, "caseCountFailed": 96, "caseCountCompleted": 0, "completedConfiguredMcPhotonsSum": 0, "githubRerunPermitted": False}, "ordinal-1 audit")
    require(proof, {"schemaVersion": 1, "stageId": "twilight-surrogate-tier-1-atm-z-grid-combined-spectral-proof-v3", "status": "ATM_Z_GRID_ELEVATED_SITE_EQUIVALENCE_AND_MYSTIC_ACCEPTANCE_PROOF_PASSED", "proofPassed": True, "profileEquivalenceDecision": True, "opticalPropertyEquivalenceDecision": True, "deterministicControlDecision": True, "threeHeightStructuralProfileDecision": True, "mysticProbeDecision": True, "deterministicSolverExecutionCount": 6, "mysticSolverExecutionCount": 1, "maximumPermittedMysticSolverExecutionCount": 1, "authorizationPermitted": False, "ordinal2ScientificDispatchPermitted": False, "scientificExecution": False, "scientificDatasetProduced": False, "surrogateTrainingUsePermitted": False, "githubRerunPermitted": False, "frozenTier1InvariantsChanged": False}, "combined proof")
    candidate = proof.get("candidateRepresentation", {})
    require(candidate, {"atmosphereFileRemainsProfileSource": True, "atmZGridBottomIsSiteAltitude": True, "originalAtmosphereLevelsAboveSitePreservedExactly": True, "explicitAltitudeForbidden": True, "mcElevationFileForbidden": True, "localSurfaceZoutKm": 0.0}, "combined proof representation")
    runtime = proof.get("runtime", {})
    require(runtime, {"uvspecSha256": EXPECTED_UVSPEC_SHA, "runtimeLockRawSha256": EXPECTED_RUNTIME_LOCK_SHA}, "combined proof runtime")
    require(source_audit, {"schemaVersion": 1, "stageId": "twilight-surrogate-tier-1-libradtran-source-audit-v1", "status": "REMOTE_SOURCE_ARCHIVE_DRIFT_DETECTED", "expectedSourceArchiveSha256": EXPECTED_HISTORICAL_SOURCE_SHA, "observedSourceArchiveSha256": EXPECTED_CURRENT_SOURCE_SHA, "exactHistoricalSourceArchiveRecovered": False, "sourceEvidenceAccepted": False, "expectedHashChangedToMakeCiGreen": False, "currentOfficialHashPromotedToExpected": False, "authorizationPermitted": False, "ordinal2ScientificDispatchPermitted": False, "scientificExecution": False, "solverExecutionCount": 0}, "source audit")
    require(provenance, {"schemaVersion": 1, "stageId": "twilight-surrogate-tier-1-libradtran-provenance-recovery-v1", "status": "PACKAGE_PROVENANCE_BOUND_EXACT_HISTORICAL_SOURCE_NOT_RECOVERED", "packageProvenanceDecision": True, "provenanceGatePassed": False, "exactHistoricalSourceArchiveRecovered": False, "sourceEvidenceAccepted": False, "sourceHashChangePermitted": False, "authorizationPermitted": False, "ordinal2ScientificDispatchPermitted": False, "scientificExecution": False, "surrogateTrainingUsePermitted": False, "githubRerunPermitted": False, "frozenTier1InvariantsChanged": False}, "provenance report")
    package = provenance.get("package", {})
    require(package, {"packageArchiveSha256": EXPECTED_PACKAGE_SHA, "installedUvspecSha256": EXPECTED_UVSPEC_SHA, "packagedUvspecSha256": EXPECTED_UVSPEC_SHA, "embeddedRecipeSourceSha256": EXPECTED_HISTORICAL_SOURCE_SHA, "installedUvspecMatchesFrozenIdentity": True, "decision": True}, "package provenance")
    return {"metadata": metadata, "hashes": {key: raw_sha256(path) for key, path in paths.items()}}


def build_expected_authorization(root: Path, template: dict[str, Any], evidence: dict[str, Any], parent: str) -> dict[str, Any]:
    if not SHA_RE.fullmatch(parent):
        raise GuardError("exact authorization parent is not a commit SHA")
    metadata = evidence["metadata"]
    hashes = evidence["hashes"]
    auth = dict(template)
    auth.update({
        "authorized": True,
        "scientificExecution": True,
        "scientificDiagnostic": True,
        "executionKey": EXECUTION_KEY,
        "authorizationOrdinal": AUTHORIZATION_ORDINAL,
        "consumed": False,
        "exactAuthorizationParentCommit": parent,
        "exactAuthorizationCommit": None,
        "readinessRunId": metadata["readiness"]["runId"],
        "readinessArtifactId": metadata["readiness"]["artifactId"],
        "readinessArtifactDigest": metadata["readiness"]["artifactDigest"],
        "readinessHeadSha": metadata["readiness"]["headSha"],
        "combinedProofRunId": metadata["combined"]["runId"],
        "combinedProofArtifactId": metadata["combined"]["artifactId"],
        "combinedProofArtifactDigest": metadata["combined"]["artifactDigest"],
        "sourceAuditRunId": metadata["source-audit"]["runId"],
        "sourceAuditArtifactId": metadata["source-audit"]["artifactId"],
        "sourceAuditArtifactDigest": metadata["source-audit"]["artifactDigest"],
        "provenanceRunId": metadata["provenance"]["runId"],
        "provenanceArtifactId": metadata["provenance"]["artifactId"],
        "provenanceArtifactDigest": metadata["provenance"]["artifactDigest"],
        "provenanceDecisionCommentId": DECISION_COMMENT_ID,
        "provenanceReviewCommentId": REVIEW_COMMENT_ID,
        "note": "One-purpose ordinal-2 Tier-1 authorization. This file authorizes only the exact recovered 96-case manifest with fresh seeds; dispatch remains a separate reviewed action.",
    })
    auth.update(hashes)
    for field, relative in code_paths().items():
        path = root / relative
        if not path.is_file():
            raise GuardError(f"bound code file missing: {relative}")
        auth[field] = raw_sha256(path)
    return auth


def validate(
    root: Path,
    authorization_path: Path,
    template_path: Path,
    evidence_dir: Path,
    metadata_dir: Path,
    comments_path: Path,
    authorization_ref: str,
    execution_key: str,
    authorization_ordinal: int,
    require_context: bool = True,
    require_one_purpose: bool = True,
) -> dict[str, Any]:
    if require_context:
        expected_context = {"GITHUB_ACTIONS": "true", "GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_RUN_ATTEMPT": "1"}
        stale = {key: (os.getenv(key), wanted) for key, wanted in expected_context.items() if os.getenv(key) != wanted}
        if stale:
            raise GuardError(f"wrong GitHub context: {stale}")
    if execution_key != EXECUTION_KEY or authorization_ordinal != AUTHORIZATION_ORDINAL:
        raise GuardError("ordinal-2 execution key or ordinal changed")
    authorization = load(root / authorization_path)
    template = load(root / template_path)
    if not isinstance(authorization, dict) or not isinstance(template, dict) or authorization.keys() != template.keys():
        raise GuardError("authorization schema differs from disabled template")
    require(template, {"authorized": False, "scientificExecution": False, "scientificDiagnostic": False, "authorizationOrdinal": 0, "consumed": False, "exactAuthorizationParentCommit": None, "exactAuthorizationCommit": None}, "disabled template")
    evidence = validate_evidence(evidence_dir, metadata_dir, comments_path)
    parent = authorization.get("exactAuthorizationParentCommit")
    expected = build_expected_authorization(root, template, evidence, parent)
    stale = {key: (authorization.get(key), wanted) for key, wanted in expected.items() if authorization.get(key) != wanted}
    if stale:
        raise GuardError(f"authorization stale: {stale}")
    for key, value in authorization.items():
        if key.endswith("RawSha256") and (not isinstance(value, str) or not SHA256_RE.fullmatch(value)):
            raise GuardError(f"authorization hash invalid: {key}")
    head = git(root, "rev-parse", "HEAD")
    actual_parent = git(root, "rev-parse", "HEAD^")
    if head != authorization_ref:
        raise GuardError("authorization ref does not equal checked-out HEAD")
    if parent != actual_parent:
        raise GuardError("authorization parent does not equal checked-out parent")
    if require_one_purpose:
        changed = git(root, "diff", "--name-only", actual_parent, head).splitlines()
        if changed != [authorization_path.as_posix()]:
            raise GuardError(f"authorization commit is not one-purpose: {changed}")
    manifest = load(evidence_dir / "ordinal2-manifest.json")
    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "AUTHORIZED",
        "authorizationRef": head,
        "authorizationParentCommit": actual_parent,
        "authorizationOrdinal": AUTHORIZATION_ORDINAL,
        "executionKey": EXECUTION_KEY,
        "manifestRawSha256": raw_sha256(evidence_dir / "ordinal2-manifest.json"),
        "caseCount": len(manifest["cases"]),
        "geometryCount": len(manifest["geometries"]),
        "configuredMcPhotonsSum": sum(case["photonHistories"] for case in manifest["cases"]),
        "freshSeedCount": len({case["seed"] for case in manifest["cases"]}),
        "maximumParallel": manifest["limits"]["maximumParallel"],
        "scientificExecution": True,
        "scientificDiagnostic": True,
        "surrogateTrainingAuthorized": False,
        "tier2Authorized": False,
        "productionModelReady": False,
        "observationValidationRequired": True,
        "githubRerunPermitted": False,
        "boundary": "one-purpose ordinal-2 Tier-1 execution authorization; no model fitting, Tier-2, observation integration, or production use",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--authorization-template", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--metadata-dir", type=Path, required=True)
    parser.add_argument("--issue-comments", type=Path, required=True)
    parser.add_argument("--authorization-ref", required=True)
    parser.add_argument("--execution-key", required=True)
    parser.add_argument("--authorization-ordinal", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--contract-mode", action="store_true")
    args = parser.parse_args()
    root = args.repository_root.resolve()
    try:
        result = validate(
            root,
            args.authorization,
            args.authorization_template,
            args.evidence_dir,
            args.metadata_dir,
            args.issue_comments,
            args.authorization_ref,
            args.execution_key,
            args.authorization_ordinal,
            require_context=not args.contract_mode,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump(result))
        print(dump(result), end="")
        return 0
    except Exception as exc:
        refusal = {"schemaVersion": 1, "stageId": STAGE_ID, "status": "REFUSED_BEFORE_SYNTAX_OR_SOLVER", "reason": str(exc)}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump(refusal))
        print(dump(refusal), file=sys.stderr, end="")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
