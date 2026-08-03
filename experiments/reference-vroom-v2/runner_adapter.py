#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
V1 = ROOT / "experiments/reference-vroom-v1"
V2_AUTH = HERE / "authorization.json"
V2_PREREG = HERE / "preregistration.json"
V2_EXECUTION = ROOT / ".github/workflows/reference-vroom-v2-execution.yml"
DUPLICATE_AUDIT = HERE / "duplicate_run_audit.py"
V1_AUTH = V1 / "authorization.json"
V1_EXECUTION = ROOT / ".github/workflows/reference-vroom-execution.yml"
V1_RUNNER = V1 / "runner.py"

STAGE = "reference-vroom-v2"
EXECUTION_KEY = "reference-vroom-v2"
AUTHORIZATION_PATH = "experiments/reference-vroom-v2/authorization.json"
EXPECTED_SOURCE_HASHES = {
    "exactSourceRunnerSha256": "462fad44ad9924a95dcc92544564467678d792afaacb26acf0264c25171f2af1",
    "exactSourceAuditSha256": "e12d7bef82fd4f725736fa7183f76993b73a98ace6271959729ff65c15784c10",
    "exactSourcePreregistrationRawSha256": "8fd87715eed5d192df2b7fe0718d4e94c1a2e8ad1a75f23fbf9d7a4522cfb5b6",
    "exactSourceCaseSetPayloadSha256": "89fe386f3e65f31d02025d9ecda02d97737dd82e13d224aefccec5c64ca0f101",
    "exactSourceAnalysisContractRawSha256": "b562b89a3cc0e867395829ac6a5201ca57d4e4325fb55da5e0050399a847e7c1",
    "exactSourceFrozenComparatorsRawSha256": "7678ae3f6a9a0199f3ab31556cdbd1ade579dae23e9a21915ae08a8cc59cfcfb",
    "exactSourceWavelengthGridRawSha256": "2f2fb3c9bf0002bdbe7d97f36e100f4334a40ac8fcfd7e5d6a98306de2cead23",
    "exactSourceAuthorizationTemplateRawSha256": "6e15ff7723369d30bb0188bfb3ca1643fcc12c98182daf9dd25e01a52fac7ff9",
    "exactSourceExecutionWorkflowSha256": "c3493a855e9dfb97309b941dfec0988bbae71240f07a893856ff872a1400ef74",
}
SOURCE_FILES = {
    "exactSourceRunnerSha256": V1 / "runner.py",
    "exactSourceAuditSha256": V1 / "audit.py",
    "exactSourcePreregistrationRawSha256": V1 / "preregistration.json",
    "exactSourceAnalysisContractRawSha256": V1 / "contract.json",
    "exactSourceFrozenComparatorsRawSha256": V1 / "frozen-comparators.zlib.b64",
    "exactSourceWavelengthGridRawSha256": V1 / "wavelength-grid.dat",
    "exactSourceAuthorizationTemplateRawSha256": V1 / "authorization-template.json",
    "exactSourceExecutionWorkflowSha256": V1_EXECUTION,
}


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise RuntimeError(f"{path} is not a JSON object")
    return value


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def verify_static_package() -> None:
    for field, path in SOURCE_FILES.items():
        actual = raw_sha256(path)
        expected = EXPECTED_SOURCE_HASHES[field]
        if actual != expected:
            raise RuntimeError(f"frozen source mismatch: {field}: {actual} != {expected}")

    prereg = load_json(V2_PREREG)
    if prereg.get("stageId") != STAGE:
        raise RuntimeError("wrong v2 preregistration stage")
    if prereg.get("scientificDesignChanged") is not False:
        raise RuntimeError("scientific design changed")
    transport = prereg.get("transportContract", {})
    if transport.get("requiredExecutionKey") != EXECUTION_KEY:
        raise RuntimeError("wrong execution key in preregistration")
    if transport.get("maximumDispatchesThatMayReachSolver") != 1:
        raise RuntimeError("wrong dispatch ceiling")
    if transport.get("requiredRunAttempt") != 1:
        raise RuntimeError("wrong run-attempt contract")
    if transport.get("duplicateMustRefuseBeforeSyntaxOrSolver") is not True:
        raise RuntimeError("duplicate refusal boundary changed")

    authorization = load_json(V2_AUTH)
    if authorization.get("stageId") != STAGE:
        raise RuntimeError("wrong authorization stage")
    if authorization.get("executionKey") != EXECUTION_KEY:
        raise RuntimeError("wrong authorization execution key")


def package_hashes() -> dict[str, Any]:
    verify_static_package()
    return {
        **EXPECTED_SOURCE_HASHES,
        "exactV2RunnerAdapterSha256": raw_sha256(Path(__file__)),
        "exactV2DuplicateRunAuditSha256": raw_sha256(DUPLICATE_AUDIT),
        "exactV2PreregistrationRawSha256": raw_sha256(V2_PREREG),
        "exactV2ExecutionWorkflowSha256": raw_sha256(V2_EXECUTION),
        "maximumSolverExecutionCount": 6,
        "maximumSyntaxCheckCount": 6,
        "maximumConfiguredMcPhotonsSum": 960000000,
        "maximumAuthorizedRunnerMinutes": 90,
        "perCaseTimeoutSeconds": 1200,
        "purpose": STAGE,
        "executionKey": EXECUTION_KEY,
    }


def load_source_runner():
    spec = importlib.util.spec_from_file_location("reference_vroom_v1_source", V1_RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load frozen source runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def configure_source_runner(module):
    original_validate = module.validate_frozen

    def validate_frozen_v2():
        verify_static_package()
        saved_stage = module.STAGE
        saved_auth = module.AUTH
        saved_execution = module.EXECUTION
        try:
            module.STAGE = "reference-vroom-v1"
            module.AUTH = V1_AUTH
            module.EXECUTION = V1_EXECUTION
            return original_validate()
        finally:
            module.STAGE = saved_stage
            module.AUTH = saved_auth
            module.EXECUTION = saved_execution

    def verify_authorization_v2():
        authorization = load_json(V2_AUTH)
        required_true = (
            "authorized",
            "runMystic",
            "runUvspec",
            "scientificDiagnostic",
            "successDoesNotAuthorizeProduction",
        )
        if authorization.get("stageId") != STAGE:
            raise module.Refusal("authorization", "wrong v2 authorization stage")
        if authorization.get("executionKey") != EXECUTION_KEY:
            raise module.Refusal("authorization", "wrong v2 execution key")
        if not all(authorization.get(key) is True for key in required_true):
            raise module.Refusal("authorization", "v2 authorization is disabled or incomplete")
        if authorization.get("authorizationOrdinal") != 1:
            raise module.Refusal("authorization", "authorization ordinal is not one")
        if authorization.get("consumed") is not False:
            raise module.Refusal("authorization", "authorization is already marked consumed")
        if authorization.get("exactAuthorizationCommit") is not None:
            raise module.Refusal("authorization", "self-referential exactAuthorizationCommit must remain null")

        if os.getenv("GITHUB_ACTIONS") != "true":
            raise module.Refusal("github-context", "not running in GitHub Actions")
        if os.getenv("GITHUB_EVENT_NAME") != "workflow_dispatch":
            raise module.Refusal("github-context", "not a workflow_dispatch run")
        if os.getenv("GITHUB_RUN_ATTEMPT") != "1":
            raise module.Refusal("github-context", "run attempt is not one")
        if os.getenv("INPUT_EXECUTION_KEY") != EXECUTION_KEY:
            raise module.Refusal("github-context", "wrong workflow execution key")
        if os.getenv("INPUT_AUTHORIZATION_ORDINAL") != "1":
            raise module.Refusal("github-context", "wrong workflow authorization ordinal")

        head = git("rev-parse", "HEAD")
        parent = git("rev-parse", "HEAD^")
        if os.getenv("INPUT_AUTHORIZATION_REF") != head:
            raise module.Refusal("authorization-purpose", "authorization input is not checked-out HEAD")
        if authorization.get("exactAuthorizationParentCommit") != parent:
            raise module.Refusal("authorization-purpose", "authorization parent mismatch")
        changed = git("diff", "--name-only", parent, head).splitlines()
        if changed != [AUTHORIZATION_PATH]:
            raise module.Refusal("authorization-purpose", "authorization commit is not one-purpose", changed)

        fresh = package_hashes()
        stale = {key: (authorization.get(key), expected) for key, expected in fresh.items() if authorization.get(key) != expected}
        if stale:
            raise module.Refusal("authorization-hash", "stale v2 authorization", stale)
        return authorization

    module.STAGE = STAGE
    module.BRANCH = "workflow_dispatch/reference-vroom-v2"
    module.AUTH = V2_AUTH
    module.EXECUTION = V2_EXECUTION
    module.validate_frozen = validate_frozen_v2
    module.hashes = package_hashes
    module.verify_auth = verify_authorization_v2
    return module


def main() -> int:
    try:
        module = configure_source_runner(load_source_runner())
        return int(module.main())
    except Exception as exc:
        print(json.dumps({"status": "REFUSED", "stageId": STAGE, "reason": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
