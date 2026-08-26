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
CONSUMED_SMOKE_MAIN_SHA = "70913845f194b529b15a10c72d0ae8a9ec675ff1"
SMOKE_RUN_ID = 33011713466
SMOKE_AUDIT_ARTIFACT_ID = 9622825000
SMOKE_AUDIT_DIGEST = "sha256:bd13fae624385476c73094e8d3a0019d403689bbfba640248c0173f1451598de"
PACKAGE = Path("experiments/jerusalem-tishrei-direct-mystic-v2")
V1_PACKAGE = Path("experiments/jerusalem-tishrei-direct-mystic-v1")
PATHS = {
    "lanePreregistration": PACKAGE / "lane.preregistration.json",
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
EXPECTED_RUN_NAME = "run-name: MYSTIC batch v1 | key=${{ inputs.execution_key }} | auth=${{ inputs.authorization_ref }} | ordinal=${{ inputs.authorization_ordinal }}"


class V2Refusal(RuntimeError):
    def __init__(self, code: str, reason: str, detail: Any | None = None) -> None:
        super().__init__(reason)
        self.code = code
        self.reason = reason
        self.detail = detail

    def as_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": 1,
            "laneId": LANE_ID,
            "scientificPurpose": PURPOSE,
            "status": "REFUSED_BEFORE_SYNTAX_OR_SOLVER",
            "code": self.code,
            "reason": self.reason,
            "detail": self.detail,
        }


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise V2Refusal("json", f"cannot read JSON: {path}", str(exc)) from exc
    if not isinstance(value, dict):
        raise V2Refusal("json-shape", f"expected JSON object: {path}")
    return value


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def require_ancestor(root: Path, ancestor: str) -> None:
    if subprocess.run(["git", "merge-base", "--is-ancestor", ancestor, "HEAD"], cwd=root, check=False).returncode != 0:
        raise V2Refusal("smoke-checkpoint", "authorization does not descend from consumed recovery2 smoke checkpoint", ancestor)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise V2Refusal("module", f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_v2_prerequisites(args: argparse.Namespace) -> dict[str, Any]:
    root = args.repository_root.resolve()
    require_ancestor(root, CONSUMED_SMOKE_MAIN_SHA)
    paths = {k: root / v for k, v in PATHS.items()}
    for key, path in paths.items():
        if not path.is_file():
            raise V2Refusal("missing-file", f"missing v2 dependency {key}", str(path))

    auth_path = root / args.authorization
    workflow_path = root / args.execution_workflow
    execution_adapter_path = root / args.execution_adapter
    if not auth_path.is_file() or not workflow_path.is_file() or not execution_adapter_path.is_file():
        raise V2Refusal("missing-file", "authorization/workflow/execution adapter missing")
    authorization = load(auth_path)
    prereg = load(paths["lanePreregistration"])
    v1_auth = load(paths["sourceV1Authorization"])
    smoke_gate = load(paths["smokeRecovery2Gate"])

    if prereg.get("laneId") != LANE_ID or prereg.get("status") != "PREREGISTERED_NO_EXECUTION":
        raise V2Refusal("lane-preregistration", "wrong v2 preregistration")
    boundary = prereg.get("claimBoundary") or {}
    if boundary.get("noParameterTuning") is not True or boundary.get("productionAuthorized") is not False or boundary.get("pandoraOpened") is not False:
        raise V2Refusal("lane-boundary", "v2 no-tuning/production/Pandora boundary changed", boundary)

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
        raise V2Refusal("v1-consumed", "v1 authorization is not permanently consumed after the failed elevated-site run", stale_v1)

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
    smoke_note = str(smoke_gate.get("note", ""))
    if stale_smoke or str(SMOKE_RUN_ID) not in smoke_note or str(SMOKE_AUDIT_ARTIFACT_ID) not in smoke_note or SMOKE_AUDIT_DIGEST not in smoke_note:
        raise V2Refusal("smoke-prerequisite", "recovery2 smoke is not the exact consumed formal PASS", stale_smoke)

    extra_required = {
        "laneId": LANE_ID,
        "lanePreregistrationRawSha256": raw_sha256(paths["lanePreregistration"]),
        "v2ExecutionGuardRawSha256": raw_sha256(Path(__file__)),
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
    }
    stale_extra = {k: (authorization.get(k), v) for k, v in extra_required.items() if authorization.get(k) != v}
    if stale_extra:
        raise V2Refusal("v2-authorization-bindings", "v2 authorization smoke/repair/dependency bindings are stale", stale_extra)

    workflow_text = workflow_path.read_text(encoding="utf-8")
    if EXPECTED_RUN_NAME not in workflow_text:
        raise V2Refusal("run-name", "v2 workflow does not use the exact duplicate-audit one-shot title")
    repaired = execution_adapter_path.read_text(encoding="utf-8")
    for token in ("EXPECTED_AOD550 = 0.22", "EXPECTED_OBSERVER_ELEVATION_M = 800.0", "atm_z_grid", "zout 0.000000", "mc_elevation_file"):
        if token not in repaired:
            raise V2Refusal("elevation-repair", "reviewed 800 m execution adapter drifted", token)

    return {
        "requiredSmokeRunId": SMOKE_RUN_ID,
        "requiredSmokeAuditArtifactId": SMOKE_AUDIT_ARTIFACT_ID,
        "requiredSmokeAuditArtifactDigest": SMOKE_AUDIT_DIGEST,
        "smokeGateRawSha256": raw_sha256(paths["smokeRecovery2Gate"]),
        "lanePreregistrationRawSha256": raw_sha256(paths["lanePreregistration"]),
    }


def validate(args: argparse.Namespace) -> dict[str, Any]:
    prerequisites = validate_v2_prerequisites(args)
    root = args.repository_root.resolve()
    v1_guard_path = root / PATHS["v1ExecutionGuard"]
    v1 = load_module("tishrei_v1_execution_guard_for_v2", v1_guard_path)
    v1.PURPOSE = PURPOSE
    try:
        report = v1.validate(args)
    except Exception as exc:
        if hasattr(exc, "as_dict"):
            detail = exc.as_dict()
            raise V2Refusal("v1-science-guard", "frozen v1 science guard rejected the v2 authorization", detail) from exc
        raise
    report.update(
        {
            "laneId": LANE_ID,
            "scientificPurpose": PURPOSE,
            "status": "AUTHORIZED_V2_AFTER_FORMAL_SMOKE_PASS",
            **prerequisites,
            "boundary": "one-purpose v2 scientific authorization verified before syntax or solver; frozen 12-case/240M science, F=3.14, AOD550=0.22 and reviewed 800 m atm_z_grid repair preserved; success does not authorize production",
        }
    )
    return report


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, default=Path("."))
    parser.add_argument("--application-root", type=Path, required=True)
    parser.add_argument("--application-sha", required=True)
    for name in ("authorization", "proposal", "evidence", "analysis-contract", "proposal-adapter", "execution-adapter", "execution-workflow", "runtime-lock", "plan", "analysis-driver", "visibility-helper", "derived-channels", "executor", "aggregate", "audit", "authorization-proposal-builder"):
        parser.add_argument(f"--{name}", required=True)
    parser.add_argument("--human-threshold", required=True)
    parser.add_argument("--authorization-ref", required=True)
    parser.add_argument("--execution-key", required=True)
    parser.add_argument("--authorization-ordinal", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = validate(args)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump(result), encoding="utf-8")
        print(dump(result), end="")
        return 0
    except Exception as exc:
        report = exc.as_dict() if isinstance(exc, V2Refusal) else V2Refusal("unexpected", str(exc)).as_dict()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump(report), encoding="utf-8")
        print(dump(report), end="", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
