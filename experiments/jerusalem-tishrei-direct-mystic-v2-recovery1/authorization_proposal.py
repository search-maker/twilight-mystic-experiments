#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

LANE_ID = "jerusalem-tishrei-direct-mystic-v2-recovery1"
PURPOSE = LANE_ID
EXECUTION_KEY = "jerusalem-tishrei-direct-mystic-v2:diagnostic:2"
AUTHORIZATION_ORDINAL = 2
SOURCE_FAILED_RUN_ID = 33014861225
SOURCE_PREFLIGHT_ARTIFACT_ID = 9624060978
SOURCE_PREFLIGHT_DIGEST = "sha256:d9aee0802ecc87ea101972e5248559cd7611ce8791e82e8f86016aca23711919"
SMOKE_RUN_ID = 33011713466
SMOKE_AUDIT_ARTIFACT_ID = 9622825000
SMOKE_AUDIT_DIGEST = "sha256:bd13fae624385476c73094e8d3a0019d403689bbfba640248c0173f1451598de"
PACKAGE = Path("experiments/jerusalem-tishrei-direct-mystic-v2-recovery1")
V2_PACKAGE = Path("experiments/jerusalem-tishrei-direct-mystic-v2")
V1_PACKAGE = Path("experiments/jerusalem-tishrei-direct-mystic-v1")
PATHS = {
    "authorization": PACKAGE / "authorization.scientific.json",
    "lanePreregistration": PACKAGE / "lane.preregistration.json",
    "recoveryGuard": PACKAGE / "execution_guard.py",
    "recoveryPlan": PACKAGE / "execution_plan.py",
    "recoveryWorkflow": Path(".github/workflows/jerusalem-tishrei-direct-mystic-v2-recovery1-execution.yml"),
    "sourceConsumedV2Authorization": V2_PACKAGE / "authorization.scientific.json",
    "sourceV2LanePreregistration": V2_PACKAGE / "lane.preregistration.json",
    "sourceV2ExecutionGuard": V2_PACKAGE / "execution_guard.py",
    "sourceV2AuthorizationProposalBuilder": V2_PACKAGE / "authorization_proposal.py",
    "sourceV2Plan": V2_PACKAGE / "execution_plan.py",
    "sourceV2ExecutionWorkflow": Path(".github/workflows/jerusalem-tishrei-direct-mystic-v2-execution.yml"),
    "smokeRecovery2Gate": Path("experiments/jerusalem-tishrei-elevated-site-smoke-v2-recovery2/gate.smoke-recovery2.json"),
    "genericExecutionAdapter": Path("experiments/mystic-batch-v1/cross_geometry_execution_adapter.py"),
    "elevationHelper": Path("experiments/mystic-batch-v1/twilight_surrogate_tier1_execution_adapter.py"),
    "elevationRepairValidator": V1_PACKAGE / "validate_elevation_repair_v2.py",
    "v1ExecutionGuard": V1_PACKAGE / "execution_guard.py",
    "v1AuthorizationProposalBuilder": V1_PACKAGE / "authorization_proposal.py",
    "duplicateRunAudit": Path("experiments/mystic-batch-v1/duplicate_run_audit.py"),
    "runtimeProbe": Path("experiments/mystic-batch-v1/runtime_probe.py"),
}

class ProposalError(RuntimeError):
    pass


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ProposalError(f"expected JSON object: {path}")
    return value


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ProposalError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_recovery(root: Path, paths: dict[str, Path]) -> None:
    lane = load(paths["lanePreregistration"])
    if lane.get("laneId") != LANE_ID or lane.get("status") != "PREREGISTERED_RECOVERY_NO_EXECUTION" or lane.get("scientificExecution") is not False:
        raise ProposalError("recovery1 lane preregistration changed")
    future = lane.get("futureAuthorization") or {}
    if future.get("executionKey") != EXECUTION_KEY or future.get("authorizationOrdinal") != AUTHORIZATION_ORDINAL:
        raise ProposalError("recovery1 key/ordinal changed")
    source = lane.get("sourceScientificPayload") or {}
    required_source = {
        "caseCount": 12,
        "photonHistoriesPerCase": 20_000_000,
        "configuredPhotonHistoriesSum": 240_000_000,
        "geometryCount": 3,
        "fieldFactorBaseline": 3.14,
        "aod550": 0.22,
        "observerElevationM": 800,
        "surfaceAlbedo": 0.15,
        "mcSpherical": "1D",
        "atmosphere": "AFGLUS",
        "wavelengthDomainNm": [380, 780],
    }
    stale = {k: (source.get(k), v) for k, v in required_source.items() if source.get(k) != v}
    if stale or source.get("methods") != {"reference-vroom": 6, "alis": 6}:
        raise ProposalError(f"source science changed: {stale}")
    failed = lane.get("consumedScientificAuthorization1") or {}
    if failed.get("authorizationCommit") != "f2e6fd8dc39b93704edb57d16558f5b6fdf7f4fd" or failed.get("workflowRunId") != SOURCE_FAILED_RUN_ID or failed.get("permanentlyConsumed") is not True:
        raise ProposalError("source v2 authorization-1 provenance changed")
    if failed.get("syntaxChecksExecuted") != 0 or failed.get("solverExecutions") != 0 or failed.get("scientificCasesExecuted") != 0:
        raise ProposalError("source failure was not pre-solver only")
    correction = lane.get("recoveryCorrection") or {}
    if correction.get("category") != "workflow-checkout-ancestry-only" or "fetch-depth 0" not in str(correction.get("requiredChange", "")):
        raise ProposalError("recovery correction changed")
    if any(correction.get(k) is not False for k in ("sourceScienceChangeAllowed","physicalInputChangeAllowed","analysisChangeAllowed","executionAdapterChangeAllowed","caseMatrixChangeAllowed","photonCountChangeAllowed","fieldFactorChangeAllowed","aodChangeAllowed","elevationRepresentationChangeAllowed")):
        raise ProposalError("recovery1 permits a forbidden scientific change")
    boundary = lane.get("claimBoundary") or {}
    for k, v in {"computationalDiagnosticOnly":True,"noParameterTuning":True,"measuredRealSkyValidated":False,"humanFirstSeeingValidated":False,"fullSpectrumLevelBValidated":False,"productionAuthorized":False,"pandoraOpened":False}.items():
        if boundary.get(k) != v:
            raise ProposalError(f"claim boundary changed: {k}")

    consumed = load(paths["sourceConsumedV2Authorization"])
    required_consumed = {
        "authorized": False,
        "scientificExecution": False,
        "scientificDiagnostic": False,
        "consumed": True,
        "executionKey": "jerusalem-tishrei-direct-mystic-v2:diagnostic:1",
        "authorizationOrdinal": 1,
        "exactAuthorizationCommit": "f2e6fd8dc39b93704edb57d16558f5b6fdf7f4fd",
    }
    stale_consumed = {k: (consumed.get(k), v) for k, v in required_consumed.items() if consumed.get(k) != v}
    note = str(consumed.get("note", ""))
    note_lower = note.lower()
    if (
        stale_consumed
        or str(SOURCE_FAILED_RUN_ID) not in note
        or "before duplicate-run audit, plan construction, syntax checks" not in note_lower
        or "mystic solver execution" not in note_lower
        or "zero scientific cases and zero configured photons executed" not in note_lower
    ):
        raise ProposalError(f"scientific authorization-1 is not exact consumed pre-solver archive: {stale_consumed}")

    smoke = load(paths["smokeRecovery2Gate"])
    if smoke.get("consumed") is not True or smoke.get("enabled") is not False or smoke.get("executionKey") != "jerusalem-tishrei-elevated-site-smoke-v2:infrastructure:3" or smoke.get("smokeOrdinal") != 3:
        raise ProposalError("formal recovery2 smoke gate changed")
    smoke_note = str(smoke.get("note", ""))
    if str(SMOKE_RUN_ID) not in smoke_note or str(SMOKE_AUDIT_ARTIFACT_ID) not in smoke_note or SMOKE_AUDIT_DIGEST not in smoke_note:
        raise ProposalError("formal smoke PASS provenance changed")


def build(repo_root: Path, application_root: Path) -> dict[str, Any]:
    root = repo_root.resolve(); app = application_root.resolve()
    paths = {k: root / v for k, v in PATHS.items()}
    for key, path in paths.items():
        if not path.is_file():
            raise ProposalError(f"missing {key}: {path}")
    validate_recovery(root, paths)

    v1 = load_module("tishrei_v1_authorization_proposal_for_recovery1", paths["v1AuthorizationProposalBuilder"])
    v1.PURPOSE = PURPOSE
    v1.EXECUTION_KEY = EXECUTION_KEY
    v1.AUTHORIZATION_ORDINAL = AUTHORIZATION_ORDINAL
    v1.PATHS = dict(v1.PATHS)
    v1.PATHS["authorization"] = PATHS["authorization"]
    v1.PATHS["executionWorkflow"] = PATHS["recoveryWorkflow"]
    v1.PATHS["plan"] = PATHS["recoveryPlan"]
    v1.PATHS["authorizationProposalBuilder"] = PACKAGE / "authorization_proposal.py"
    report = v1.build(root, app)
    proposed = report.get("proposedAuthorization")
    if not isinstance(proposed, dict):
        raise ProposalError("v1 science validator returned no proposed authorization")
    proposed.update({
        "laneId": LANE_ID,
        "lanePreregistrationRawSha256": raw_sha256(paths["lanePreregistration"]),
        "recoveryExecutionGuardRawSha256": raw_sha256(paths["recoveryGuard"]),
        "sourceConsumedV2AuthorizationRawSha256": raw_sha256(paths["sourceConsumedV2Authorization"]),
        "sourceV2LanePreregistrationRawSha256": raw_sha256(paths["sourceV2LanePreregistration"]),
        "sourceV2ExecutionGuardRawSha256": raw_sha256(paths["sourceV2ExecutionGuard"]),
        "sourceV2AuthorizationProposalBuilderRawSha256": raw_sha256(paths["sourceV2AuthorizationProposalBuilder"]),
        "sourceV2PlanRawSha256": raw_sha256(paths["sourceV2Plan"]),
        "sourceV2ExecutionWorkflowRawSha256": raw_sha256(paths["sourceV2ExecutionWorkflow"]),
        "genericExecutionAdapterRawSha256": raw_sha256(paths["genericExecutionAdapter"]),
        "elevationHelperRawSha256": raw_sha256(paths["elevationHelper"]),
        "elevationRepairValidatorRawSha256": raw_sha256(paths["elevationRepairValidator"]),
        "v1ExecutionGuardRawSha256": raw_sha256(paths["v1ExecutionGuard"]),
        "v1AuthorizationProposalBuilderRawSha256": raw_sha256(paths["v1AuthorizationProposalBuilder"]),
        "duplicateRunAuditRawSha256": raw_sha256(paths["duplicateRunAudit"]),
        "runtimeProbeRawSha256": raw_sha256(paths["runtimeProbe"]),
        "requiredSmokeRunId": SMOKE_RUN_ID,
        "requiredSmokeAuditArtifactId": SMOKE_AUDIT_ARTIFACT_ID,
        "requiredSmokeAuditArtifactDigest": SMOKE_AUDIT_DIGEST,
        "consumedSourceRunId": SOURCE_FAILED_RUN_ID,
        "consumedSourcePreflightArtifactId": SOURCE_PREFLIGHT_ARTIFACT_ID,
        "consumedSourcePreflightArtifactDigest": SOURCE_PREFLIGHT_DIGEST,
        "note": "Proposal only for scientific v2 recovery1. Authorization-1/run 33014861225 are consumed and may never be reused. Recovery1 changes only the workflow preflight checkout to full ancestry; source 12-case/240M science, F=3.14, AOD550=0.22, reviewed 800 m atm_z_grid representation, analysis, runtime, seeds and photon counts remain frozen. Separate one-purpose authorization and one-shot dispatch still required. No production, tuning, real-sky, human, full-spectrum-Level-B or Pandora claim."
    })
    report.update({
        "laneId": LANE_ID,
        "scientificPurpose": PURPOSE,
        "status": "RECOVERY1_PROPOSAL_ONLY_NOT_AUTHORIZATION",
        "executionAuthorizedByProposal": False,
        "sourceCommit": git(root, "rev-parse", "HEAD"),
        "consumedSourceRunId": SOURCE_FAILED_RUN_ID,
        "proposedAuthorization": proposed,
        "boundary": "proposal only; zero syntax checks, uvspec processes or solvers; recovery limited to checkout ancestry"
    })
    return report


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repository-root", type=Path, default=Path("."))
    p.add_argument("--application-root", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    try:
        result = build(args.repository_root, args.application_root)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump(result), encoding="utf-8")
        print(dump(result), end="")
        return 0
    except Exception as exc:
        print(dump({"schemaVersion":1,"laneId":LANE_ID,"scientificPurpose":PURPOSE,"status":"REFUSED","reason":str(exc)}), end="", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
