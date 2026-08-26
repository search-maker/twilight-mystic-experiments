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
EXPECTED_KEY = "jerusalem-tishrei-direct-mystic-v2:diagnostic:2"
EXPECTED_ORDINAL = 2
CONSUMED_SMOKE_MAIN_SHA = "70913845f194b529b15a10c72d0ae8a9ec675ff1"
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
    "lanePreregistration": PACKAGE / "lane.preregistration.json",
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
EXPECTED_RUN_NAME = "run-name: MYSTIC batch v1 | key=${{ inputs.execution_key }} | auth=${{ inputs.authorization_ref }} | ordinal=${{ inputs.authorization_ordinal }}"

class RecoveryRefusal(RuntimeError):
    def __init__(self, code: str, reason: str, detail: Any | None = None) -> None:
        super().__init__(reason)
        self.code = code; self.reason = reason; self.detail = detail
    def as_dict(self) -> dict[str, Any]:
        return {"schemaVersion":1,"laneId":LANE_ID,"scientificPurpose":PURPOSE,"status":"REFUSED_BEFORE_SYNTAX_OR_SOLVER","code":self.code,"reason":self.reason,"detail":self.detail}


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RecoveryRefusal("json", f"cannot read JSON: {path}", str(exc)) from exc
    if not isinstance(value, dict):
        raise RecoveryRefusal("json-shape", f"expected object: {path}")
    return value


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def require_ancestor(root: Path, ancestor: str) -> None:
    proc = subprocess.run(["git", "merge-base", "--is-ancestor", ancestor, "HEAD"], cwd=root, text=True, capture_output=True)
    if proc.returncode != 0:
        raise RecoveryRefusal("smoke-checkpoint", "authorization does not descend from consumed recovery2 smoke checkpoint; recovery1 requires full ancestry checkout", {"ancestor":ancestor,"stderr":proc.stderr.strip(),"returnCode":proc.returncode})


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RecoveryRefusal("module", f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


def validate_prerequisites(args: argparse.Namespace) -> dict[str, Any]:
    root = args.repository_root.resolve()
    require_ancestor(root, CONSUMED_SMOKE_MAIN_SHA)
    paths = {k: root / v for k, v in PATHS.items()}
    for key, path in paths.items():
        if not path.is_file():
            raise RecoveryRefusal("missing-file", f"missing recovery dependency {key}", str(path))
    auth_path = root / args.authorization
    workflow_path = root / args.execution_workflow
    if not auth_path.is_file() or not workflow_path.is_file():
        raise RecoveryRefusal("missing-file", "authorization or recovery workflow missing")
    authorization = load(auth_path)
    lane = load(paths["lanePreregistration"])
    consumed = load(paths["sourceConsumedV2Authorization"])
    smoke = load(paths["smokeRecovery2Gate"])

    if args.execution_key != EXPECTED_KEY or args.authorization_ordinal != EXPECTED_ORDINAL:
        raise RecoveryRefusal("recovery-identity", "wrong recovery key or ordinal", {"key":args.execution_key,"ordinal":args.authorization_ordinal})
    if lane.get("laneId") != LANE_ID or lane.get("status") != "PREREGISTERED_RECOVERY_NO_EXECUTION":
        raise RecoveryRefusal("lane", "wrong recovery1 lane preregistration")
    future = lane.get("futureAuthorization") or {}
    if future.get("executionKey") != EXPECTED_KEY or future.get("authorizationOrdinal") != EXPECTED_ORDINAL:
        raise RecoveryRefusal("lane-identity", "recovery1 preregistered identity changed")
    correction = lane.get("recoveryCorrection") or {}
    if correction.get("category") != "workflow-checkout-ancestry-only" or "fetch-depth 0" not in str(correction.get("requiredChange", "")):
        raise RecoveryRefusal("lane-correction", "recovery1 correction is no longer checkout-ancestry-only")
    boundary = lane.get("claimBoundary") or {}
    if boundary.get("noParameterTuning") is not True or boundary.get("productionAuthorized") is not False or boundary.get("pandoraOpened") is not False:
        raise RecoveryRefusal("lane-boundary", "recovery1 claim boundary changed", boundary)

    required_consumed = {
        "authorized":False,"scientificExecution":False,"scientificDiagnostic":False,"consumed":True,
        "executionKey":"jerusalem-tishrei-direct-mystic-v2:diagnostic:1","authorizationOrdinal":1,
        "exactAuthorizationCommit":"f2e6fd8dc39b93704edb57d16558f5b6fdf7f4fd",
    }
    stale_consumed = {k:(consumed.get(k),v) for k,v in required_consumed.items() if consumed.get(k)!=v}
    note = str(consumed.get("note", ""))
    note_lower = note.lower()
    if (
        stale_consumed
        or str(SOURCE_FAILED_RUN_ID) not in note
        or "before duplicate-run audit, plan construction, syntax checks" not in note_lower
        or "mystic solver execution" not in note_lower
        or "zero scientific cases and zero configured photons executed" not in note_lower
    ):
        raise RecoveryRefusal("source-consumed", "authorization-1 is not exact consumed pre-solver archive", stale_consumed)

    if smoke.get("consumed") is not True or smoke.get("enabled") is not False or smoke.get("executionKey") != "jerusalem-tishrei-elevated-site-smoke-v2:infrastructure:3" or smoke.get("smokeOrdinal") != 3:
        raise RecoveryRefusal("smoke", "formal elevated-site smoke gate changed")
    smoke_note = str(smoke.get("note", ""))
    if str(SMOKE_RUN_ID) not in smoke_note or str(SMOKE_AUDIT_ARTIFACT_ID) not in smoke_note or SMOKE_AUDIT_DIGEST not in smoke_note:
        raise RecoveryRefusal("smoke-provenance", "formal smoke PASS provenance changed")

    extra_required = {
        "laneId":LANE_ID,
        "lanePreregistrationRawSha256":raw_sha256(paths["lanePreregistration"]),
        "recoveryExecutionGuardRawSha256":raw_sha256(Path(__file__)),
        "sourceConsumedV2AuthorizationRawSha256":raw_sha256(paths["sourceConsumedV2Authorization"]),
        "sourceV2LanePreregistrationRawSha256":raw_sha256(paths["sourceV2LanePreregistration"]),
        "sourceV2ExecutionGuardRawSha256":raw_sha256(paths["sourceV2ExecutionGuard"]),
        "sourceV2AuthorizationProposalBuilderRawSha256":raw_sha256(paths["sourceV2AuthorizationProposalBuilder"]),
        "sourceV2PlanRawSha256":raw_sha256(paths["sourceV2Plan"]),
        "sourceV2ExecutionWorkflowRawSha256":raw_sha256(paths["sourceV2ExecutionWorkflow"]),
        "genericExecutionAdapterRawSha256":raw_sha256(paths["genericExecutionAdapter"]),
        "elevationHelperRawSha256":raw_sha256(paths["elevationHelper"]),
        "elevationRepairValidatorRawSha256":raw_sha256(paths["elevationRepairValidator"]),
        "v1ExecutionGuardRawSha256":raw_sha256(paths["v1ExecutionGuard"]),
        "v1AuthorizationProposalBuilderRawSha256":raw_sha256(paths["v1AuthorizationProposalBuilder"]),
        "duplicateRunAuditRawSha256":raw_sha256(paths["duplicateRunAudit"]),
        "runtimeProbeRawSha256":raw_sha256(paths["runtimeProbe"]),
        "requiredSmokeRunId":SMOKE_RUN_ID,
        "requiredSmokeAuditArtifactId":SMOKE_AUDIT_ARTIFACT_ID,
        "requiredSmokeAuditArtifactDigest":SMOKE_AUDIT_DIGEST,
        "consumedSourceRunId":SOURCE_FAILED_RUN_ID,
        "consumedSourcePreflightArtifactId":SOURCE_PREFLIGHT_ARTIFACT_ID,
        "consumedSourcePreflightArtifactDigest":SOURCE_PREFLIGHT_DIGEST,
    }
    stale_extra = {k:(authorization.get(k),v) for k,v in extra_required.items() if authorization.get(k)!=v}
    if stale_extra:
        raise RecoveryRefusal("authorization-bindings", "recovery1 authorization provenance/dependency bindings are stale", stale_extra)

    workflow_text = workflow_path.read_text(encoding="utf-8")
    if EXPECTED_RUN_NAME not in workflow_text:
        raise RecoveryRefusal("run-name", "recovery1 workflow lost exact duplicate-audit one-shot title")
    marker = "- name: Check out exact one-purpose recovery1 scientific authorization commit"
    if marker not in workflow_text:
        raise RecoveryRefusal("checkout", "recovery1 preflight checkout marker missing")
    after = workflow_text.split(marker, 1)[1].split("- name:", 1)[0]
    if "fetch-depth: 0" not in after:
        raise RecoveryRefusal("checkout-depth", "recovery1 preflight does not fetch full ancestry")

    return {"requiredSmokeRunId":SMOKE_RUN_ID,"requiredSmokeAuditArtifactId":SMOKE_AUDIT_ARTIFACT_ID,"requiredSmokeAuditArtifactDigest":SMOKE_AUDIT_DIGEST,"consumedSourceRunId":SOURCE_FAILED_RUN_ID,"consumedSourcePreflightArtifactId":SOURCE_PREFLIGHT_ARTIFACT_ID,"consumedSourcePreflightArtifactDigest":SOURCE_PREFLIGHT_DIGEST}


def validate(args: argparse.Namespace) -> dict[str, Any]:
    prerequisites = validate_prerequisites(args)
    root = args.repository_root.resolve()
    v1 = load_module("tishrei_v1_execution_guard_for_recovery1", root / PATHS["v1ExecutionGuard"])
    v1.PURPOSE = PURPOSE
    try:
        report = v1.validate(args)
    except Exception as exc:
        if hasattr(exc, "as_dict"):
            raise RecoveryRefusal("v1-science-guard", "frozen v1 science guard rejected recovery1 authorization", exc.as_dict()) from exc
        raise
    report.update({"laneId":LANE_ID,"scientificPurpose":PURPOSE,"status":"AUTHORIZED_V2_RECOVERY1_AFTER_CONSUMED_PREFLIGHT_FAILURE",**prerequisites,"boundary":"one-purpose recovery1 authorization verified after full-ancestry checkout; source 12-case/240M science, F=3.14, AOD550=0.22 and reviewed 800 m atm_z_grid representation unchanged; success does not authorize production"})
    return report


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--repository-root",type=Path,default=Path(".")); p.add_argument("--application-root",type=Path,required=True); p.add_argument("--application-sha",required=True)
    for name in ("authorization","proposal","evidence","analysis-contract","proposal-adapter","execution-adapter","execution-workflow","runtime-lock","plan","analysis-driver","visibility-helper","derived-channels","executor","aggregate","audit","authorization-proposal-builder"):
        p.add_argument(f"--{name}",required=True)
    p.add_argument("--human-threshold",required=True); p.add_argument("--authorization-ref",required=True); p.add_argument("--execution-key",required=True); p.add_argument("--authorization-ordinal",type=int,required=True); p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    try:
        result=validate(args); args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(dump(result),encoding="utf-8"); print(dump(result),end=""); return 0
    except Exception as exc:
        report=exc.as_dict() if isinstance(exc,RecoveryRefusal) else RecoveryRefusal("unexpected",str(exc)).as_dict(); args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(dump(report),encoding="utf-8"); print(dump(report),end="",file=sys.stderr); return 2

if __name__ == "__main__":
    raise SystemExit(main())
