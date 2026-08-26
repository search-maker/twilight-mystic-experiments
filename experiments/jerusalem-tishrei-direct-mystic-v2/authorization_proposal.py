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

LANE_ID = "jerusalem-tishrei-direct-mystic-v2"
PURPOSE = LANE_ID
EXECUTION_KEY = "jerusalem-tishrei-direct-mystic-v2:diagnostic:1"
AUTHORIZATION_ORDINAL = 1
CONSUMED_SMOKE_MAIN_SHA = "70913845f194b529b15a10c72d0ae8a9ec675ff1"
SMOKE_RUN_ID = 33011713466
SMOKE_AUDIT_ARTIFACT_ID = 9622825000
SMOKE_AUDIT_DIGEST = "sha256:bd13fae624385476c73094e8d3a0019d403689bbfba640248c0173f1451598de"
PACKAGE = Path("experiments/jerusalem-tishrei-direct-mystic-v2")
V1_PACKAGE = Path("experiments/jerusalem-tishrei-direct-mystic-v1")
PATHS = {
    "authorization": PACKAGE / "authorization.scientific.json",
    "lanePreregistration": PACKAGE / "lane.preregistration.json",
    "v2Guard": PACKAGE / "execution_guard.py",
    "v2Workflow": Path(".github/workflows/jerusalem-tishrei-direct-mystic-v2-execution.yml"),
    "sourceV1Authorization": V1_PACKAGE / "authorization.cross-geometry.json",
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


def require_ancestor(root: Path, ancestor: str) -> None:
    if subprocess.run(["git", "merge-base", "--is-ancestor", ancestor, "HEAD"], cwd=root, check=False).returncode != 0:
        raise ProposalError(f"HEAD does not contain required consumed smoke checkpoint {ancestor}")


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ProposalError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_lane(root: Path, paths: dict[str, Path]) -> None:
    prereg = load(paths["lanePreregistration"])
    if prereg.get("laneId") != LANE_ID or prereg.get("status") != "PREREGISTERED_NO_EXECUTION" or prereg.get("scientificExecution") is not False:
        raise ProposalError("v2 lane preregistration header changed")
    future = prereg.get("futureAuthorization") or {}
    if future.get("executionKey") != EXECUTION_KEY or future.get("authorizationOrdinal") != AUTHORIZATION_ORDINAL:
        raise ProposalError("v2 future authorization identity changed")
    source = prereg.get("sourceScientificPayload") or {}
    expected_source = {
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
    stale = {k: (source.get(k), v) for k, v in expected_source.items() if source.get(k) != v}
    if stale or source.get("methods") != {"reference-vroom": 6, "alis": 6}:
        raise ProposalError(f"source scientific payload changed: {stale}")
    failed = prereg.get("failedV1Authorization") or {}
    if failed.get("authorizationCommit") != "64e4515ebb2fb53c93490a6fe1370ceb7e782206" or failed.get("workflowRunId") != 33003385601 or failed.get("permanentlyConsumed") is not True:
        raise ProposalError("consumed v1 scientific provenance changed")
    smoke = prereg.get("requiredInfrastructureSmoke") or {}
    if smoke.get("workflowRunId") != SMOKE_RUN_ID or smoke.get("formalStatus") != "PASSED_AND_CONSUMED" or smoke.get("auditArtifactId") != SMOKE_AUDIT_ARTIFACT_ID or smoke.get("auditArtifactDigest") != SMOKE_AUDIT_DIGEST:
        raise ProposalError("required recovery2 smoke provenance changed")
    boundary = prereg.get("claimBoundary") or {}
    required_boundary = {
        "computationalDiagnosticOnly": True,
        "noParameterTuning": True,
        "measuredRealSkyValidated": False,
        "humanFirstSeeingValidated": False,
        "fullSpectrumLevelBValidated": False,
        "productionAuthorized": False,
        "pandoraOpened": False,
    }
    if any(boundary.get(k) != v for k, v in required_boundary.items()):
        raise ProposalError("v2 claim boundary changed")

    v1_auth = load(paths["sourceV1Authorization"])
    v1_required = {
        "authorized": False,
        "scientificExecution": False,
        "scientificDiagnostic": False,
        "consumed": True,
        "executionKey": "jerusalem-tishrei-direct-mystic-v1:diagnostic:1",
        "authorizationOrdinal": 1,
        "exactAuthorizationCommit": "64e4515ebb2fb53c93490a6fe1370ceb7e782206",
    }
    stale_v1 = {k: (v1_auth.get(k), v) for k, v in v1_required.items() if v1_auth.get(k) != v}
    if stale_v1 or "33003385601" not in str(v1_auth.get("note", "")):
        raise ProposalError(f"v1 authorization is not the consumed failed lane: {stale_v1}")

    smoke_gate = load(paths["smokeRecovery2Gate"])
    smoke_required = {
        "stageId": "jerusalem-tishrei-elevated-site-smoke-v2-recovery2",
        "enabled": False,
        "infrastructureExecution": False,
        "scientificExecution": False,
        "scientificDiagnostic": False,
        "scientificUseProhibited": True,
        "executionKey": "jerusalem-tishrei-elevated-site-smoke-v2:infrastructure:3",
        "smokeOrdinal": 3,
        "consumed": True,
    }
    stale_smoke = {k: (smoke_gate.get(k), v) for k, v in smoke_required.items() if smoke_gate.get(k) != v}
    note = str(smoke_gate.get("note", ""))
    if stale_smoke or str(SMOKE_RUN_ID) not in note or str(SMOKE_AUDIT_ARTIFACT_ID) not in note or SMOKE_AUDIT_DIGEST not in note:
        raise ProposalError(f"recovery2 smoke gate is not the consumed formal PASS: {stale_smoke}")

    repaired = (root / V1_PACKAGE / "execution_adapter.py").read_text(encoding="utf-8")
    for token in ("EXPECTED_AOD550 = 0.22", "EXPECTED_OBSERVER_ELEVATION_M = 800.0", "atm_z_grid", "zout 0.000000", "mc_elevation_file"):
        if token not in repaired:
            raise ProposalError(f"reviewed 800 m execution adapter lost token: {token}")


def build(repo_root: Path, application_root: Path) -> dict[str, Any]:
    root = repo_root.resolve()
    app = application_root.resolve()
    require_ancestor(root, CONSUMED_SMOKE_MAIN_SHA)
    paths = {k: root / v for k, v in PATHS.items()}
    for key, path in paths.items():
        if not path.is_file():
            raise ProposalError(f"missing {key}: {path}")
    validate_lane(root, paths)

    v1 = load_module("tishrei_v1_authorization_proposal_for_v2", paths["v1AuthorizationProposalBuilder"])
    v1.PURPOSE = PURPOSE
    v1.EXECUTION_KEY = EXECUTION_KEY
    v1.AUTHORIZATION_ORDINAL = AUTHORIZATION_ORDINAL
    v1.PATHS = dict(v1.PATHS)
    v1.PATHS["authorization"] = PATHS["authorization"]
    v1.PATHS["executionWorkflow"] = PATHS["v2Workflow"]
    v1.PATHS["authorizationProposalBuilder"] = PACKAGE / "authorization_proposal.py"

    report = v1.build(root, app)
    proposed = report.get("proposedAuthorization")
    if not isinstance(proposed, dict):
        raise ProposalError("v1 science validator did not return a proposed authorization")
    proposed.update(
        {
            "laneId": LANE_ID,
            "lanePreregistrationRawSha256": raw_sha256(paths["lanePreregistration"]),
            "v2ExecutionGuardRawSha256": raw_sha256(paths["v2Guard"]),
            "sourceV1AuthorizationRawSha256": raw_sha256(paths["sourceV1Authorization"]),
            "smokeRecovery2GateRawSha256": raw_sha256(paths["smokeRecovery2Gate"]),
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
            "note": "Proposal only for the separately preregistered v2 lane. Source 12-case/240M science is byte-for-byte the frozen v1 payload; execution uses the reviewed 800 m atm_z_grid/local-surface adapter and is contingent on consumed recovery2 smoke run 33011713466. A separate one-purpose authorization commit and separate first-attempt workflow_dispatch are still required. No parameter tuning, production authorization, real-sky validation, human-first-seeing validation, full-spectrum Level-B validation, or Pandora opening.",
        }
    )
    report.update(
        {
            "laneId": LANE_ID,
            "scientificPurpose": PURPOSE,
            "status": "V2_PROPOSAL_ONLY_NOT_AUTHORIZATION",
            "executionAuthorizedByProposal": False,
            "requiredSmokeRunId": SMOKE_RUN_ID,
            "proposedAuthorization": proposed,
            "boundary": "hash proposal only; source science unchanged; no syntax check, uvspec process, MYSTIC solver, dispatch, tuning, production claim, or Pandora",
        }
    )
    return report


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, default=Path("."))
    parser.add_argument("--application-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = build(args.repository_root, args.application_root)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump(result), encoding="utf-8")
        print(dump(result), end="")
        return 0
    except Exception as exc:
        report = {"schemaVersion": 1, "laneId": LANE_ID, "scientificPurpose": PURPOSE, "status": "REFUSED", "reason": str(exc)}
        print(dump(report), end="", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
