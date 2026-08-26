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

STAGE_ID = "jerusalem-tishrei-elevated-site-smoke-v2"
BATCH_ID = "jerusalem-tishrei-elevated-site-smoke-v2"
EXECUTION_KEY = "jerusalem-tishrei-elevated-site-smoke-v2:infrastructure:1"
SMOKE_AUTHORIZATION_ORDINAL = 1
REPAIR_MERGED_MAIN_SHA = "13fe2e18a7754b893eba31328f90b179fc018499"
PACKAGE = Path("experiments/jerusalem-tishrei-elevated-site-smoke-v2")
PATHS = {
    "authorization": PACKAGE / "authorization.smoke.json",
    "manifest": PACKAGE / "manifest.smoke.json",
    "adapter": PACKAGE / "adapter.py",
    "smokeExecutor": PACKAGE / "smoke_executor.py",
    "executionGuard": PACKAGE / "execution_guard.py",
    "executionWorkflow": Path(".github/workflows/jerusalem-tishrei-elevated-site-smoke-v2.yml"),
    "runtimeLock": Path("experiments/mystic-batch-v1/runtime-lock.micromamba.json"),
    "runtimeProbe": Path("experiments/mystic-batch-v1/runtime_probe.py"),
    "sourceScientificManifest": Path("experiments/jerusalem-tishrei-direct-mystic-v1/manifest.proposal.json"),
    "sourceConsumedV1Authorization": Path("experiments/jerusalem-tishrei-direct-mystic-v1/authorization.cross-geometry.json"),
    "repairedScientificExecutionAdapter": Path("experiments/jerusalem-tishrei-direct-mystic-v1/execution_adapter.py"),
}


class GuardError(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise GuardError(f"expected JSON object: {path}")
    return value


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GuardError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate(root: Path, authorization_ref: str, execution_key: str, ordinal: int) -> dict[str, Any]:
    root = root.resolve()
    expected_context = {"GITHUB_ACTIONS": "true", "GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_RUN_ATTEMPT": "1"}
    stale_context = {k: (os.getenv(k), v) for k, v in expected_context.items() if os.getenv(k) != v}
    if stale_context:
        raise GuardError(f"not exact first-attempt workflow_dispatch context: {stale_context}")
    if execution_key != EXECUTION_KEY or ordinal != SMOKE_AUTHORIZATION_ORDINAL:
        raise GuardError("wrong infrastructure-smoke key/ordinal")

    absolute = {k: root / v for k, v in PATHS.items()}
    for key, path in absolute.items():
        if not path.is_file():
            raise GuardError(f"missing {key}: {path}")
    adapter = load_module("smoke_guard_adapter", absolute["adapter"])
    smoke = load_json(absolute["manifest"])
    adapter.validate_smoke_manifest(smoke)
    adapter.validate_consumed_v1(root, smoke)
    if smoke.get("infrastructureOnly") is not True or smoke.get("scientificUseProhibited") is not True or smoke.get("scientificExecution") is not False:
        raise GuardError("smoke scientific boundary changed")
    cases = smoke.get("cases") or []
    if len(cases) != 2 or sum(int(case.get("photonHistories", 0)) for case in cases) != 20000:
        raise GuardError("smoke case/photon accounting changed")
    if {case.get("method") for case in cases} != {"reference-vroom", "alis"}:
        raise GuardError("smoke method set changed")
    if any(case.get("photonHistories") != 10000 for case in cases):
        raise GuardError("smoke photons-per-case changed")
    if subprocess.run(["git", "merge-base", "--is-ancestor", REPAIR_MERGED_MAIN_SHA, "HEAD"], cwd=root, check=False).returncode != 0:
        raise GuardError("checked-out authorization ref does not contain merged elevation repair")

    authorization = load_json(absolute["authorization"])
    required_auth = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "authorized": True,
        "infrastructureExecution": True,
        "scientificExecution": False,
        "scientificDiagnostic": False,
        "scientificUseProhibited": True,
        "successDoesNotAuthorizeScientificExecution": True,
        "successDoesNotAuthorizeProduction": True,
        "executionKey": EXECUTION_KEY,
        "batchId": BATCH_ID,
        "smokeManifestPath": PATHS["manifest"].as_posix(),
        "smokeManifestRawSha256": raw_sha256(absolute["manifest"]),
        "adapterRawSha256": raw_sha256(absolute["adapter"]),
        "smokeExecutorRawSha256": raw_sha256(absolute["smokeExecutor"]),
        "executionGuardRawSha256": raw_sha256(absolute["executionGuard"]),
        "executionWorkflowRawSha256": raw_sha256(absolute["executionWorkflow"]),
        "runtimeLockRawSha256": raw_sha256(absolute["runtimeLock"]),
        "runtimeProbeRawSha256": raw_sha256(absolute["runtimeProbe"]),
        "sourceScientificManifestRawSha256": raw_sha256(absolute["sourceScientificManifest"]),
        "sourceConsumedV1AuthorizationRawSha256": raw_sha256(absolute["sourceConsumedV1Authorization"]),
        "repairedScientificExecutionAdapterRawSha256": raw_sha256(absolute["repairedScientificExecutionAdapter"]),
        "smokeAuthorizationOrdinal": SMOKE_AUTHORIZATION_ORDINAL,
        "consumed": False,
        "exactAuthorizationCommit": None,
    }
    stale = {k: (authorization.get(k), v) for k, v in required_auth.items() if authorization.get(k) != v}
    if stale:
        raise GuardError(f"smoke authorization disabled/stale: {stale}")

    head = git(root, "rev-parse", "HEAD")
    parent = git(root, "rev-parse", "HEAD^")
    if head != authorization_ref:
        raise GuardError(f"authorization ref mismatch: HEAD={head}, input={authorization_ref}")
    if authorization.get("exactAuthorizationParentCommit") != parent:
        raise GuardError("smoke authorization parent mismatch")
    changed = git(root, "diff", "--name-only", parent, head).splitlines()
    if changed != [PATHS["authorization"].as_posix()]:
        raise GuardError(f"smoke authorization commit must change exactly one file: {changed}")

    executor_text = absolute["smokeExecutor"].read_text(encoding="utf-8")
    if "scientificUseProhibited" not in executor_text or "allow-infrastructure-smoke" not in executor_text:
        raise GuardError("smoke executor scientific-use boundary changed")
    if "evaluatePointSourceVisibility" in executor_text or "derive_channels" in executor_text:
        raise GuardError("smoke executor acquired scientific analysis logic")

    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "AUTHORIZED_INFRASTRUCTURE_SMOKE_ONLY",
        "infrastructureOnly": True,
        "scientificUseProhibited": True,
        "successDoesNotAuthorizeScientificExecution": True,
        "batchId": BATCH_ID,
        "executionKey": EXECUTION_KEY,
        "authorizationRef": head,
        "authorizationParentCommit": parent,
        "smokeAuthorizationOrdinal": ordinal,
        "caseCount": 2,
        "configuredPhotonHistoriesSum": 20000,
        "methods": ["reference-vroom", "alis"],
        "repairMergedMainSha": REPAIR_MERGED_MAIN_SHA,
        "boundary": "one-purpose infrastructure-only smoke authorization verified; no scientific use or scientific authorization follows from success",
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repository-root", type=Path, default=Path("."))
    p.add_argument("--authorization-ref", required=True)
    p.add_argument("--execution-key", required=True)
    p.add_argument("--smoke-authorization-ordinal", type=int, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    try:
        report = validate(args.repository_root, args.authorization_ref, args.execution_key, args.smoke_authorization_ordinal)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        report = {"schemaVersion": 1, "stageId": STAGE_ID, "status": "REFUSED_BEFORE_SMOKE_EXECUTION", "reason": str(exc)}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
