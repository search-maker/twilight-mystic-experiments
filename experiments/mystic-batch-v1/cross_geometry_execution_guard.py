#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

STAGE_ID = "cross-geometry-pilot-v1"
GENERIC_STAGE_ID = "mystic-batch-v1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._:-]{2,159}$")


class GuardRefusal(RuntimeError):
    def __init__(self, code: str, reason: str, detail: Any | None = None) -> None:
        super().__init__(reason)
        self.code = code
        self.reason = reason
        self.detail = detail

    def as_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": 1,
            "stageId": STAGE_ID,
            "status": "REFUSED_BEFORE_SYNTAX_OR_SOLVER",
            "code": self.code,
            "reason": self.reason,
            "detail": self.detail,
        }


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise GuardRefusal("invalid-json", f"cannot read JSON object: {path}", str(exc)) from exc
    if not isinstance(value, dict):
        raise GuardRefusal("invalid-json-object", f"expected JSON object: {path}")
    return value


def dump_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def require_int(value: Any, name: str, minimum: int = 0) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise GuardRefusal("invalid-integer", f"{name} must be an integer >= {minimum}", value)
    return value


def normalized_relative(path: Path, name: str) -> str:
    text = path.as_posix()
    if path.is_absolute() or ".." in path.parts or text.startswith("./"):
        raise GuardRefusal("invalid-path", f"{name} must be a normalized repository-relative path", text)
    return text


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GuardRefusal("module-load", f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_guard(
    repository_root: Path,
    authorization_path: Path,
    proposal_path: Path,
    contract_path: Path,
    proposal_template_path: Path,
    proposal_adapter_path: Path,
    proposal_validator_path: Path,
    execution_adapter_path: Path,
    execution_workflow_path: Path,
    runtime_lock_path: Path,
    plan_path: Path,
    analysis_driver_path: Path,
    executor_path: Path,
    aggregate_path: Path,
    audit_path: Path,
    authorization_ref: str,
    execution_key: str,
    authorization_ordinal: int,
    require_github_context: bool = True,
) -> dict[str, Any]:
    root = repository_root.resolve()
    path_map = {
        "authorization": authorization_path,
        "proposal": proposal_path,
        "contract": contract_path,
        "proposalTemplate": proposal_template_path,
        "proposalAdapter": proposal_adapter_path,
        "proposalValidator": proposal_validator_path,
        "executionAdapter": execution_adapter_path,
        "executionWorkflow": execution_workflow_path,
        "runtimeLock": runtime_lock_path,
        "plan": plan_path,
        "analysisDriver": analysis_driver_path,
        "executor": executor_path,
        "aggregate": aggregate_path,
        "audit": audit_path,
    }
    rel = {key: normalized_relative(value, key) for key, value in path_map.items()}
    abs_paths = {key: root / value for key, value in rel.items()}
    for key, path in abs_paths.items():
        if not path.is_file():
            raise GuardRefusal("missing-file", f"{key} file does not exist", str(path))

    if not ID_RE.fullmatch(execution_key):
        raise GuardRefusal("execution-key", "invalid execution key", execution_key)
    if authorization_ordinal < 1:
        raise GuardRefusal("authorization-ordinal", "authorization ordinal must be positive")
    if require_github_context:
        expected = {
            "GITHUB_ACTIONS": "true",
            "GITHUB_EVENT_NAME": "workflow_dispatch",
            "GITHUB_RUN_ATTEMPT": "1",
        }
        stale = {key: (os.getenv(key), value) for key, value in expected.items() if os.getenv(key) != value}
        if stale:
            raise GuardRefusal("github-context", "not exact first-attempt workflow_dispatch context", stale)

    proposal_validator = load_module("cross_geometry_proposal_validator", abs_paths["proposalValidator"])
    try:
        proposal_report = proposal_validator.validate(
            abs_paths["proposal"],
            abs_paths["contract"],
            abs_paths["proposalTemplate"],
            abs_paths["proposalAdapter"],
        )
    except Exception as exc:
        raise GuardRefusal("proposal-validation", "frozen proposal validation failed", str(exc)) from exc
    if proposal_report.get("status") != "PROPOSAL_VALIDATED_NO_EXECUTION":
        raise GuardRefusal("proposal-validation", "proposal validator returned wrong status", proposal_report)

    proposal = load_json(abs_paths["proposal"])
    contract = load_json(abs_paths["contract"])
    authorization = load_json(abs_paths["authorization"])
    if proposal.get("stageId") != STAGE_ID or proposal.get("proposalOnly") is not True:
        raise GuardRefusal("proposal-header", "wrong proposal header")
    if contract.get("stageId") != STAGE_ID or contract.get("screeningOnly") is not True:
        raise GuardRefusal("contract-header", "wrong screening contract header")

    required_auth = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "authorized": True,
        "scientificExecution": True,
        "scientificDiagnostic": True,
        "successDoesNotAuthorizeProduction": True,
        "executionKey": execution_key,
        "batchId": proposal.get("batchId"),
        "proposalPath": rel["proposal"],
        "proposalRawSha256": raw_sha256(abs_paths["proposal"]),
        "contractRawSha256": raw_sha256(abs_paths["contract"]),
        "proposalAdapterRawSha256": raw_sha256(abs_paths["proposalAdapter"]),
        "proposalValidatorRawSha256": raw_sha256(abs_paths["proposalValidator"]),
        "executionAdapterRawSha256": raw_sha256(abs_paths["executionAdapter"]),
        "executionWorkflowRawSha256": raw_sha256(abs_paths["executionWorkflow"]),
        "runtimeLockRawSha256": raw_sha256(abs_paths["runtimeLock"]),
        "planRawSha256": raw_sha256(abs_paths["plan"]),
        "analysisDriverRawSha256": raw_sha256(abs_paths["analysisDriver"]),
        "executorRawSha256": raw_sha256(abs_paths["executor"]),
        "aggregateRawSha256": raw_sha256(abs_paths["aggregate"]),
        "auditRawSha256": raw_sha256(abs_paths["audit"]),
        "authorizationOrdinal": authorization_ordinal,
        "consumed": False,
        "exactAuthorizationCommit": None,
    }
    stale_auth = {key: (authorization.get(key), expected) for key, expected in required_auth.items() if authorization.get(key) != expected}
    if stale_auth:
        raise GuardRefusal("authorization-stale", "authorization is missing, disabled, or stale", stale_auth)

    limits = proposal.get("limits")
    cases = proposal.get("cases")
    if not isinstance(limits, dict) or not isinstance(cases, list):
        raise GuardRefusal("proposal-shape", "proposal limits or cases missing")
    maximum_cases = require_int(limits.get("maximumCases"), "limits.maximumCases", 1)
    maximum_parallel = require_int(limits.get("maximumParallel"), "limits.maximumParallel", 1)
    maximum_photons = require_int(limits.get("maximumConfiguredMcPhotonsSum"), "limits.maximumConfiguredMcPhotonsSum", 1)
    timeout_seconds = require_int(limits.get("perCaseTimeoutSeconds"), "limits.perCaseTimeoutSeconds", 1)
    if len(cases) > maximum_cases or maximum_parallel > maximum_cases:
        raise GuardRefusal("proposal-limits", "case or parallel ceiling violated")
    photon_sum = sum(require_int(case.get("photonHistories"), "case.photonHistories", 1) for case in cases if isinstance(case, dict))
    if len(cases) != 24 or photon_sum != 480_000_000 or photon_sum > maximum_photons:
        raise GuardRefusal("proposal-accounting", "cross-geometry pilot accounting changed", {"caseCount": len(cases), "photons": photon_sum})

    head = git(root, "rev-parse", "HEAD")
    parent = git(root, "rev-parse", "HEAD^")
    if head != authorization_ref:
        raise GuardRefusal("authorization-ref", "checked-out HEAD is not supplied authorization ref", {"head": head, "input": authorization_ref})
    if authorization.get("exactAuthorizationParentCommit") != parent:
        raise GuardRefusal("authorization-parent", "authorization parent mismatch", {"actual": parent, "authorized": authorization.get("exactAuthorizationParentCommit")})
    changed = git(root, "diff", "--name-only", parent, head).splitlines()
    if changed != [rel["authorization"]]:
        raise GuardRefusal("one-purpose-commit", "authorization commit must change exactly the active authorization file", changed)

    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "genericStageId": GENERIC_STAGE_ID,
        "status": "AUTHORIZED",
        "batchId": proposal["batchId"],
        "executionKey": execution_key,
        "authorizationRef": head,
        "authorizationParentCommit": parent,
        "authorizationOrdinal": authorization_ordinal,
        "proposalPath": rel["proposal"],
        "proposalRawSha256": raw_sha256(abs_paths["proposal"]),
        "contractRawSha256": raw_sha256(abs_paths["contract"]),
        "caseCount": len(cases),
        "maximumParallel": maximum_parallel,
        "perCaseTimeoutSeconds": timeout_seconds,
        "configuredMcPhotonsSum": photon_sum,
        "boundary": "one-purpose cross-geometry authorization verified before syntax check or solver execution",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, default=Path("."))
    for name in (
        "authorization", "proposal", "contract", "proposal-template", "proposal-adapter", "proposal-validator",
        "execution-adapter", "execution-workflow", "runtime-lock", "plan", "analysis-driver", "executor", "aggregate", "audit",
    ):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--authorization-ref", required=True)
    parser.add_argument("--execution-key", required=True)
    parser.add_argument("--authorization-ordinal", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = validate_guard(
            args.repository_root, args.authorization, args.proposal, args.contract, args.proposal_template,
            args.proposal_adapter, args.proposal_validator, args.execution_adapter, args.execution_workflow,
            args.runtime_lock, args.plan, args.analysis_driver, args.executor, args.aggregate, args.audit,
            args.authorization_ref, args.execution_key, args.authorization_ordinal,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump_json(report))
        print(dump_json(report), end="")
        return 0
    except Exception as exc:
        refusal = exc.as_dict() if isinstance(exc, GuardRefusal) else GuardRefusal("unexpected-error", str(exc)).as_dict()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump_json(refusal))
        print(dump_json(refusal), end="", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
