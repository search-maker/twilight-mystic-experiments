#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

STAGE_ID = "jerusalem-tishrei-elevated-site-smoke-v2-recovery1"
BATCH_ID = "jerusalem-tishrei-elevated-site-smoke-v2-recovery1"
EXECUTION_KEY = "jerusalem-tishrei-elevated-site-smoke-v2:infrastructure:2"
SMOKE_ORDINAL = 2
CONSUMED_V2_MAIN_SHA = "3885f7c390653181aa86a428779867469c5b278c"
FAILED_V2_RUN_ID = 33007847279
PACKAGE = Path("experiments/jerusalem-tishrei-elevated-site-smoke-v2-recovery1")
PATHS = {
    "gate": PACKAGE / "gate.smoke-recovery1.json",
    "guard": PACKAGE / "execution_guard.py",
    "workflow": Path(".github/workflows/jerusalem-tishrei-elevated-site-smoke-v2-recovery1.yml"),
    "sourceManifest": Path("experiments/jerusalem-tishrei-elevated-site-smoke-v2/manifest.smoke.json"),
    "sourceAdapter": Path("experiments/jerusalem-tishrei-elevated-site-smoke-v2/adapter.py"),
    "sourceExecutor": Path("experiments/jerusalem-tishrei-elevated-site-smoke-v2/smoke_executor.py"),
    "sourceConsumedV2Gate": Path("experiments/jerusalem-tishrei-elevated-site-smoke-v2/authorization.smoke.json"),
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
        raise GuardError(f"checked-out gate ref does not contain required consumed-v2 main {ancestor}")


def validate_source(root: Path, paths: dict[str, Path]) -> None:
    manifest = load(paths["sourceManifest"])
    if manifest.get("stageId") != "jerusalem-tishrei-elevated-site-smoke-v2" or manifest.get("infrastructureOnly") is not True or manifest.get("scientificUseProhibited") is not True:
        raise GuardError("source smoke manifest boundary changed")
    cases = manifest.get("cases") or []
    if len(cases) != 2 or sum(int(c.get("photonHistories", 0)) for c in cases) != 20_000 or {c.get("method") for c in cases} != {"reference-vroom", "alis"}:
        raise GuardError("source smoke exact two-case/20k universe changed")
    consumed = load(paths["sourceConsumedV2Gate"])
    required = {
        "stageId": "jerusalem-tishrei-elevated-site-smoke-v2",
        "authorized": False,
        "infrastructureExecution": False,
        "scientificExecution": False,
        "scientificDiagnostic": False,
        "scientificUseProhibited": True,
        "consumed": True,
        "executionKey": "jerusalem-tishrei-elevated-site-smoke-v2:infrastructure:1",
        "smokeAuthorizationOrdinal": 1,
        "exactAuthorizationCommit": "3ec2a7bdacb4f00e49f5756ba339338b1e86769c",
    }
    stale = {k: (consumed.get(k), v) for k, v in required.items() if consumed.get(k) != v}
    if stale:
        raise GuardError(f"source smoke-v2 consumed gate changed: {stale}")
    note = str(consumed.get("note", ""))
    if str(FAILED_V2_RUN_ID) not in note or "duplicate_run_audit" not in note:
        raise GuardError("source smoke-v2 consumed gate lost failed-run/duplicate-audit provenance")
    workflow_text = paths["workflow"].read_text(encoding="utf-8")
    if EXPECTED_RUN_NAME not in workflow_text:
        raise GuardError("recovery workflow run-name does not exactly match the duplicate-audit marker template")
    audit_text = paths["duplicateRunAudit"].read_text(encoding="utf-8")
    if 'TITLE_PREFIX = "MYSTIC batch v1 "' not in audit_text or 'return f"{TITLE_PREFIX}| key={execution_key} | auth={authorization_ref} | ordinal={ordinal}"' not in audit_text:
        raise GuardError("shared duplicate-run title contract changed")
    executor_text = paths["sourceExecutor"].read_text(encoding="utf-8")
    if "scientificUseProhibited" not in executor_text or "allow-infrastructure-smoke" not in executor_text:
        raise GuardError("source smoke executor boundary changed")
    if "evaluatePointSourceVisibility" in executor_text or "derive_channels" in executor_text:
        raise GuardError("source smoke executor acquired scientific analysis")


def validate(root: Path, gate_ref: str, execution_key: str, ordinal: int) -> dict[str, Any]:
    root = root.resolve()
    expected_context = {"GITHUB_ACTIONS": "true", "GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_RUN_ATTEMPT": "1"}
    stale_context = {k: (os.getenv(k), v) for k, v in expected_context.items() if os.getenv(k) != v}
    if stale_context:
        raise GuardError(f"not exact first-attempt workflow_dispatch context: {stale_context}")
    if execution_key != EXECUTION_KEY or ordinal != SMOKE_ORDINAL:
        raise GuardError("wrong recovery execution key/ordinal")
    require_ancestor(root, CONSUMED_V2_MAIN_SHA)
    paths = {k: root / p for k, p in PATHS.items()}
    for key, path in paths.items():
        if not path.is_file():
            raise GuardError(f"missing {key}: {path}")
    validate_source(root, paths)
    gate = load(paths["gate"])
    required_gate = {
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
        "sourceSmokeExecutorRawSha256": sha256(paths["sourceExecutor"]),
        "sourceConsumedSmokeV2GateRawSha256": sha256(paths["sourceConsumedV2Gate"]),
        "duplicateRunAuditRawSha256": sha256(paths["duplicateRunAudit"]),
        "executionGuardRawSha256": sha256(paths["guard"]),
        "executionWorkflowRawSha256": sha256(paths["workflow"]),
        "runtimeLockRawSha256": sha256(paths["runtimeLock"]),
        "runtimeProbeRawSha256": sha256(paths["runtimeProbe"]),
        "smokeOrdinal": SMOKE_ORDINAL,
        "consumed": False,
        "exactGateCommit": None,
    }
    stale = {k: (gate.get(k), v) for k, v in required_gate.items() if gate.get(k) != v}
    if stale:
        raise GuardError(f"recovery gate disabled/stale: {stale}")
    head = git(root, "rev-parse", "HEAD")
    parent = git(root, "rev-parse", "HEAD^")
    if head != gate_ref:
        raise GuardError(f"gate ref mismatch: HEAD={head}, input={gate_ref}")
    if gate.get("exactGateParentCommit") != parent:
        raise GuardError("recovery gate parent mismatch")
    changed = git(root, "diff", "--name-only", parent, head).splitlines()
    if changed != [PATHS["gate"].as_posix()]:
        raise GuardError(f"one-purpose recovery gate commit must change exactly the gate file: {changed}")
    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "ENABLED_INFRASTRUCTURE_RECOVERY_ONLY",
        "infrastructureOnly": True,
        "scientificUseProhibited": True,
        "successDoesNotAuthorizeScientificExecution": True,
        "batchId": BATCH_ID,
        "executionKey": EXECUTION_KEY,
        "gateRef": head,
        "gateParentCommit": parent,
        "smokeOrdinal": ordinal,
        "caseCount": 2,
        "configuredPhotonHistoriesSum": 20_000,
        "methods": ["reference-vroom", "alis"],
        "failedSourceSmokeRunId": FAILED_V2_RUN_ID,
        "boundary": "one-purpose infrastructure recovery gate verified before duplicate audit, syntax check, or solver; no scientific use or scientific execution follows from recovery smoke success",
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
        report = {"schemaVersion": 1, "stageId": STAGE_ID, "status": "REFUSED_BEFORE_RECOVERY_SMOKE_EXECUTION", "reason": str(exc)}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
