#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

STAGE_ID = "jerusalem-tishrei-elevated-site-smoke-v2-recovery2"
BATCH_ID = STAGE_ID
EXECUTION_KEY = "jerusalem-tishrei-elevated-site-smoke-v2:infrastructure:3"
SMOKE_ORDINAL = 3
CONSUMED_RECOVERY1_MAIN_SHA = "7f007e37ba33aba8fafa450418a10ef35eb3f72d"
RECOVERY1_RUN_ID = 33009947410
PACKAGE = Path("experiments/jerusalem-tishrei-elevated-site-smoke-v2-recovery2")
PATHS = {
    "gate": PACKAGE / "gate.smoke-recovery2.json",
    "gateProposal": PACKAGE / "gate_proposal.py",
    "guard": PACKAGE / "execution_guard.py",
    "workflow": Path(".github/workflows/jerusalem-tishrei-elevated-site-smoke-v2-recovery2.yml"),
    "sourceManifest": Path("experiments/jerusalem-tishrei-elevated-site-smoke-v2/manifest.smoke.json"),
    "sourceAdapter": Path("experiments/jerusalem-tishrei-elevated-site-smoke-v2/adapter.py"),
    "recovery2Executor": PACKAGE / "smoke_executor.py",
    "consumedRecovery1Gate": Path("experiments/jerusalem-tishrei-elevated-site-smoke-v2-recovery1/gate.smoke-recovery1.json"),
    "referenceVroomRunner": Path("experiments/reference-vroom-v1/runner.py"),
    "referenceVroomGrid": Path("experiments/reference-vroom-v1/wavelength-grid.dat"),
    "duplicateRunAudit": Path("experiments/mystic-batch-v1/duplicate_run_audit.py"),
    "runtimeLock": Path("experiments/mystic-batch-v1/runtime-lock.micromamba.json"),
    "runtimeProbe": Path("experiments/mystic-batch-v1/runtime_probe.py"),
}
EXPECTED_RUN_NAME = "run-name: MYSTIC batch v1 | key=${{ inputs.execution_key }} | auth=${{ inputs.gate_ref }} | ordinal=${{ inputs.smoke_ordinal }}"


class GuardError(RuntimeError):
    pass


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise GuardError(f"expected JSON object: {path}")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def require_ancestor(root: Path, ancestor: str) -> None:
    if subprocess.run(["git", "merge-base", "--is-ancestor", ancestor, "HEAD"], cwd=root, check=False).returncode != 0:
        raise GuardError(f"gate ref does not contain consumed recovery1 main {ancestor}")


def load_proposal_module(path: Path):
    spec = importlib.util.spec_from_file_location("tishrei_recovery2_gate_proposal", path)
    if spec is None or spec.loader is None:
        raise GuardError(f"cannot load gate proposal module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate(root: Path, gate_ref: str, execution_key: str, ordinal: int) -> dict[str, Any]:
    root = root.resolve()
    expected_context = {"GITHUB_ACTIONS": "true", "GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_RUN_ATTEMPT": "1"}
    stale_context = {k: (os.getenv(k), v) for k, v in expected_context.items() if os.getenv(k) != v}
    if stale_context:
        raise GuardError(f"not exact first-attempt workflow_dispatch context: {stale_context}")
    if execution_key != EXECUTION_KEY or ordinal != SMOKE_ORDINAL:
        raise GuardError("wrong recovery2 execution key/ordinal")
    require_ancestor(root, CONSUMED_RECOVERY1_MAIN_SHA)
    paths = {k: root / p for k, p in PATHS.items()}
    for key, path in paths.items():
        if not path.is_file():
            raise GuardError(f"missing {key}: {path}")

    gp = load_proposal_module(paths["gateProposal"])
    gp.validate_source_manifest(paths["sourceManifest"])
    gp.validate_consumed_recovery1(paths["consumedRecovery1Gate"])
    gp.validate_vroom_correction(paths["recovery2Executor"], paths["referenceVroomRunner"], paths["referenceVroomGrid"])
    if EXPECTED_RUN_NAME not in paths["workflow"].read_text(encoding="utf-8"):
        raise GuardError("recovery2 workflow run-name mismatch")

    gate = load(paths["gate"])
    required = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "enabled": True,
        "infrastructureExecution": True,
        "scientificExecution": False,
        "scientificDiagnostic": False,
        "scientificUseProhibited": True,
        "successDoesNotAuthorizeScientificExecution": True,
        "successDoesNotAuthorizeProduction": True,
        "executionKey": EXECUTION_KEY,
        "batchId": BATCH_ID,
        "sourceSmokeManifestRawSha256": sha256(paths["sourceManifest"]),
        "sourceSmokeAdapterRawSha256": sha256(paths["sourceAdapter"]),
        "recovery2SmokeExecutorRawSha256": sha256(paths["recovery2Executor"]),
        "consumedRecovery1GateRawSha256": sha256(paths["consumedRecovery1Gate"]),
        "referenceVroomRunnerRawSha256": sha256(paths["referenceVroomRunner"]),
        "referenceVroomGridRawSha256": sha256(paths["referenceVroomGrid"]),
        "duplicateRunAuditRawSha256": sha256(paths["duplicateRunAudit"]),
        "gateProposalRawSha256": sha256(paths["gateProposal"]),
        "executionGuardRawSha256": sha256(paths["guard"]),
        "executionWorkflowRawSha256": sha256(paths["workflow"]),
        "runtimeLockRawSha256": sha256(paths["runtimeLock"]),
        "runtimeProbeRawSha256": sha256(paths["runtimeProbe"]),
        "smokeOrdinal": SMOKE_ORDINAL,
        "consumed": False,
        "exactGateCommit": None,
    }
    stale = {k: (gate.get(k), v) for k, v in required.items() if gate.get(k) != v}
    if stale:
        raise GuardError(f"recovery2 gate disabled/stale: {stale}")

    head = git(root, "rev-parse", "HEAD")
    parent = git(root, "rev-parse", "HEAD^")
    if head != gate_ref:
        raise GuardError(f"gate ref mismatch: HEAD={head}, input={gate_ref}")
    if gate.get("exactGateParentCommit") != parent:
        raise GuardError("recovery2 gate parent mismatch")
    changed = git(root, "diff", "--name-only", parent, head).splitlines()
    if changed != [PATHS["gate"].as_posix()]:
        raise GuardError(f"one-purpose recovery2 gate commit must change exactly the gate file: {changed}")

    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "ENABLED_INFRASTRUCTURE_RECOVERY2_ONLY",
        "infrastructureOnly": True,
        "scientificUseProhibited": True,
        "successDoesNotAuthorizeScientificExecution": True,
        "batchId": BATCH_ID,
        "executionKey": EXECUTION_KEY,
        "gateRef": head,
        "gateParentCommit": parent,
        "smokeOrdinal": ordinal,
        "caseCount": 2,
        "configuredPhotonHistoriesSum": 20000,
        "methods": ["reference-vroom", "alis"],
        "recovery1RunId": RECOVERY1_RUN_ID,
        "boundary": "recovery2 guard verified before duplicate audit, syntax check, or solver; only VROOM structural output interpretation changed; no scientific use or scientific execution follows from smoke success",
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repository-root", type=Path, default=Path("."))
    p.add_argument("--gate-ref", required=True)
    p.add_argument("--execution-key", required=True)
    p.add_argument("--smoke-ordinal", type=int, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    try:
        report = validate(args.repository_root, args.gate_ref, args.execution_key, args.smoke_ordinal)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        report = {"schemaVersion": 1, "stageId": STAGE_ID, "status": "REFUSED_BEFORE_RECOVERY2_SMOKE_EXECUTION", "reason": str(exc)}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
