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

STAGE_ID = "cross-geometry-pilot-v1"
EXECUTION_KEY = "cross-geometry-pilot-v1:screening:1"
PACKAGE = Path("experiments/mystic-batch-v1")
PATHS = {
    "authorization": PACKAGE / "authorization.cross-geometry.json",
    "authorizationTemplate": PACKAGE / "authorization.cross-geometry-execution-template.json",
    "proposal": PACKAGE / "manifest.cross-geometry-pilot.proposal.json",
    "contract": PACKAGE / "cross-geometry-contract.json",
    "proposalTemplate": PACKAGE / "authorization.cross-geometry-template.json",
    "proposalAdapter": PACKAGE / "cross_geometry_adapter.py",
    "proposalValidator": PACKAGE / "cross_geometry_validate.py",
    "executionAdapter": PACKAGE / "cross_geometry_execution_adapter.py",
    "executionWorkflow": Path(".github/workflows/mystic-batch-v1-cross-geometry-execution.yml"),
    "runtimeLock": PACKAGE / "runtime-lock.micromamba.json",
    "plan": PACKAGE / "cross_geometry_execution_plan.py",
    "analysisDriver": PACKAGE / "cross_geometry_execution_analysis_driver.py",
    "executor": PACKAGE / "scientific_case_executor.py",
    "aggregate": PACKAGE / "scientific_aggregate.py",
    "audit": PACKAGE / "scientific_audit.py",
}


class ProposalFailure(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ProposalFailure(f"expected JSON object: {path}")
    return value


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ProposalFailure(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ensure_disabled(active: dict[str, Any], template: dict[str, Any]) -> None:
    if active != template:
        raise ProposalFailure("active authorization differs from disabled template")
    required = {
        "authorized": False,
        "scientificExecution": False,
        "scientificDiagnostic": False,
        "authorizationOrdinal": 0,
        "consumed": False,
        "exactAuthorizationParentCommit": None,
        "exactAuthorizationCommit": None,
    }
    stale = {key: (active.get(key), expected) for key, expected in required.items() if active.get(key) != expected}
    if stale:
        raise ProposalFailure(f"active authorization is not disabled: {stale}")


def build_proposal(repository_root: Path) -> dict[str, Any]:
    root = repository_root.resolve()
    absolute = {key: root / path for key, path in PATHS.items()}
    for key, path in absolute.items():
        if not path.is_file():
            raise ProposalFailure(f"missing {key}: {path}")

    active = load_json(absolute["authorization"])
    template = load_json(absolute["authorizationTemplate"])
    ensure_disabled(active, template)

    validator = load_module("cross_geometry_proposal_validator", absolute["proposalValidator"])
    validation = validator.validate(
        absolute["proposal"],
        absolute["contract"],
        absolute["proposalTemplate"],
        absolute["proposalAdapter"],
    )
    if validation.get("status") != "PROPOSAL_VALIDATED_NO_EXECUTION":
        raise ProposalFailure(f"proposal validation did not pass: {validation}")

    proposal = load_json(absolute["proposal"])
    if proposal.get("stageId") != STAGE_ID or proposal.get("proposalOnly") is not True or proposal.get("scientificExecution") is not False:
        raise ProposalFailure("source proposal execution boundary changed")
    source_commit = git(root, "rev-parse", "HEAD")
    proposed_authorization = {
        **template,
        "authorized": True,
        "scientificExecution": True,
        "scientificDiagnostic": True,
        "executionKey": EXECUTION_KEY,
        "batchId": proposal["batchId"],
        "proposalPath": PATHS["proposal"].as_posix(),
        "proposalRawSha256": raw_sha256(absolute["proposal"]),
        "contractRawSha256": raw_sha256(absolute["contract"]),
        "proposalAdapterRawSha256": raw_sha256(absolute["proposalAdapter"]),
        "proposalValidatorRawSha256": raw_sha256(absolute["proposalValidator"]),
        "executionAdapterRawSha256": raw_sha256(absolute["executionAdapter"]),
        "executionWorkflowRawSha256": raw_sha256(absolute["executionWorkflow"]),
        "runtimeLockRawSha256": raw_sha256(absolute["runtimeLock"]),
        "planRawSha256": raw_sha256(absolute["plan"]),
        "analysisDriverRawSha256": raw_sha256(absolute["analysisDriver"]),
        "executorRawSha256": raw_sha256(absolute["executor"]),
        "aggregateRawSha256": raw_sha256(absolute["aggregate"]),
        "auditRawSha256": raw_sha256(absolute["audit"]),
        "exactAuthorizationParentCommit": source_commit,
        "exactAuthorizationCommit": None,
        "authorizationOrdinal": 1,
        "consumed": False,
        "note": "Proposal only. A future one-purpose commit may replace only authorization.cross-geometry.json with this object; a separate reviewed workflow_dispatch is still required.",
    }
    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "PROPOSAL_ONLY_NOT_AUTHORIZATION",
        "executionAuthorizedByProposal": False,
        "sourceCommit": source_commit,
        "proposalValidation": validation,
        "proposedAuthorization": proposed_authorization,
        "boundary": "This artifact computes exact authorization inputs only. It performs no syntax check, uvspec process, MYSTIC solver, or workflow dispatch.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = build_proposal(args.repository_root)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump(result))
        print(dump(result), end="")
        return 0
    except Exception as exc:
        refusal = {"schemaVersion": 1, "stageId": STAGE_ID, "status": "REFUSED", "reason": str(exc)}
        print(dump(refusal), end="", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
