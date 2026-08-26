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


class ProposalError(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
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


def ensure_disabled(auth: dict[str, Any]) -> None:
    required = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "authorized": False,
        "infrastructureExecution": False,
        "scientificExecution": False,
        "scientificDiagnostic": False,
        "scientificUseProhibited": True,
        "successDoesNotAuthorizeScientificExecution": True,
        "successDoesNotAuthorizeProduction": True,
        "executionKey": None,
        "batchId": None,
        "exactAuthorizationParentCommit": None,
        "exactAuthorizationCommit": None,
        "smokeAuthorizationOrdinal": 0,
        "consumed": False,
    }
    stale = {k: (auth.get(k), v) for k, v in required.items() if auth.get(k) != v}
    if stale:
        raise ProposalError(f"active smoke authorization is not pristine disabled: {stale}")


def build(root: Path) -> dict[str, Any]:
    root = root.resolve()
    absolute = {k: root / v for k, v in PATHS.items()}
    for key, path in absolute.items():
        if not path.is_file():
            raise ProposalError(f"missing {key}: {path}")
    auth = load_json(absolute["authorization"])
    ensure_disabled(auth)
    smoke_adapter = load_module("smoke_authorization_adapter", absolute["adapter"])
    smoke = load_json(absolute["manifest"])
    smoke_adapter.validate_smoke_manifest(smoke)
    smoke_adapter.validate_consumed_v1(root, smoke)
    head = git(root, "rev-parse", "HEAD")
    ancestor = subprocess.run(["git", "merge-base", "--is-ancestor", REPAIR_MERGED_MAIN_SHA, head], cwd=root, check=False)
    if ancestor.returncode != 0:
        raise ProposalError("smoke package HEAD does not contain merged repair main SHA")
    proposed = {
        **auth,
        "authorized": True,
        "infrastructureExecution": True,
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
        "exactAuthorizationParentCommit": head,
        "exactAuthorizationCommit": None,
        "smokeAuthorizationOrdinal": SMOKE_AUTHORIZATION_ORDINAL,
        "consumed": False,
        "note": "Infrastructure smoke only. A future one-purpose commit may replace only authorization.smoke.json with this object; a separate first-attempt workflow_dispatch is still required. Smoke output is scientifically unusable by contract.",
    }
    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "PROPOSAL_ONLY_NOT_AUTHORIZATION",
        "executionAuthorizedByProposal": False,
        "sourceCommit": head,
        "repairMergedMainSha": REPAIR_MERGED_MAIN_SHA,
        "proposedAuthorization": proposed,
        "boundary": "hash proposal only; no syntax check, uvspec, MYSTIC, scientific authorization, or production authorization",
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repository-root", type=Path, default=Path("."))
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    try:
        result = build(args.repository_root)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        refusal = {"schemaVersion": 1, "stageId": STAGE_ID, "status": "REFUSED", "reason": str(exc)}
        print(json.dumps(refusal, indent=2, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
