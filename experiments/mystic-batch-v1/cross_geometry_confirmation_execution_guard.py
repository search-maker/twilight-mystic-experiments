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

STAGE_ID = "cross-geometry-selected-reference-confirmation-v1"
SOURCE_AUTHORIZATION_REF = "7e630b8f46259ddf6a0cfdf5e381872c0182d0ba"
SOURCE_EXECUTION_KEY = "cross-geometry-final-convergence-v1:screening:4"
SOURCE_AUTHORIZATION_ORDINAL = 4
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._:-]{2,159}$")


class GuardRefusal(RuntimeError):
    def __init__(self, code: str, reason: str, detail: Any | None = None) -> None:
        super().__init__(reason)
        self.code = code
        self.reason = reason
        self.detail = detail


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise GuardRefusal("invalid-json", f"cannot read JSON object: {path}", str(exc)) from exc
    if not isinstance(value, dict):
        raise GuardRefusal("invalid-json-object", f"expected JSON object: {path}")
    return value


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def load_package(path: Path):
    spec = importlib.util.spec_from_file_location("cross_geometry_confirmation_package", path)
    if spec is None or spec.loader is None:
        raise GuardRefusal("package-load", f"cannot load confirmation package: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def require_hash(value: Any, name: str) -> str:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise GuardRefusal("invalid-hash", f"{name} must be lowercase SHA-256", value)
    return value


def validate_guard(
    repository_root: Path,
    authorization_path: Path,
    authorization_template_path: Path,
    source_analysis_path: Path,
    source_proposal_path: Path,
    source_readiness_path: Path,
    source_run_metadata_path: Path,
    promoted_manifest_output: Path,
    package_path: Path,
    base_adapter_path: Path,
    execution_adapter_path: Path,
    duplicate_run_audit_path: Path,
    runtime_probe_path: Path,
    execution_workflow_path: Path,
    runtime_lock_path: Path,
    plan_path: Path,
    analysis_driver_path: Path,
    convergence_module_path: Path,
    executor_path: Path,
    aggregate_path: Path,
    audit_path: Path,
    source_run_id: int,
    authorization_ref: str,
    execution_key: str,
    authorization_ordinal: int,
    require_github_context: bool = True,
    require_one_purpose_commit: bool = True,
) -> dict[str, Any]:
    root = repository_root.resolve()
    repo_paths = {
        "authorization": authorization_path,
        "authorizationTemplate": authorization_template_path,
        "package": package_path,
        "baseAdapter": base_adapter_path,
        "executionAdapter": execution_adapter_path,
        "duplicateRunAudit": duplicate_run_audit_path,
        "runtimeProbe": runtime_probe_path,
        "executionWorkflow": execution_workflow_path,
        "runtimeLock": runtime_lock_path,
        "plan": plan_path,
        "analysisDriver": analysis_driver_path,
        "convergenceModule": convergence_module_path,
        "executor": executor_path,
        "aggregate": aggregate_path,
        "audit": audit_path,
    }
    absolute: dict[str, Path] = {}
    relative: dict[str, str] = {}
    for key, path in repo_paths.items():
        if path.is_absolute() or ".." in path.parts:
            raise GuardRefusal("invalid-path", f"{key} must be repository-relative", str(path))
        relative[key] = path.as_posix()
        absolute[key] = root / path
        if not absolute[key].is_file():
            raise GuardRefusal("missing-file", f"{key} file missing", str(absolute[key]))
    for key, path in {
        "sourceAnalysis": source_analysis_path,
        "sourceProposal": source_proposal_path,
        "sourceReadiness": source_readiness_path,
        "sourceRunMetadata": source_run_metadata_path,
    }.items():
        if not path.is_file():
            raise GuardRefusal("missing-source-file", f"{key} file missing", str(path))
    if require_github_context:
        expected = {"GITHUB_ACTIONS": "true", "GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_RUN_ATTEMPT": "1"}
        stale = {key: (os.getenv(key), value) for key, value in expected.items() if os.getenv(key) != value}
        if stale:
            raise GuardRefusal("github-context", "not exact first-attempt workflow_dispatch context", stale)
    if not ID_RE.fullmatch(execution_key):
        raise GuardRefusal("execution-key", "invalid execution key", execution_key)
    if not isinstance(source_run_id, int) or source_run_id < 1:
        raise GuardRefusal("source-run-id", "source run ID must be positive")
    if not isinstance(authorization_ordinal, int) or authorization_ordinal < 1:
        raise GuardRefusal("authorization-ordinal", "authorization ordinal must be positive")

    authorization = load(absolute["authorization"])
    template = load(absolute["authorizationTemplate"])
    if set(authorization) != set(template):
        raise GuardRefusal("authorization-schema", "active authorization fields differ from template")
    disabled = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "authorized": False,
        "scientificExecution": False,
        "scientificDiagnostic": False,
        "successDoesNotAuthorizeProduction": True,
        "authorizationOrdinal": 0,
        "consumed": False,
        "exactAuthorizationParentCommit": None,
        "exactAuthorizationCommit": None,
    }
    stale_template = {key: (template.get(key), value) for key, value in disabled.items() if template.get(key) != value}
    if stale_template:
        raise GuardRefusal("authorization-template", "confirmation authorization template is not disabled", stale_template)

    package = load_package(absolute["package"])
    manifest = package.promote(source_analysis_path, source_proposal_path, source_readiness_path, source_run_metadata_path, source_run_id)
    promoted_manifest_output.parent.mkdir(parents=True, exist_ok=True)
    promoted_manifest_output.write_text(package.dump(manifest))
    promoted_hash = raw_sha256(promoted_manifest_output)

    expected_auth = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "authorized": True,
        "scientificExecution": True,
        "scientificDiagnostic": True,
        "successDoesNotAuthorizeProduction": True,
        "executionKey": execution_key,
        "batchId": manifest["batchId"],
        "sourceRunId": source_run_id,
        "sourceAuthorizationRef": SOURCE_AUTHORIZATION_REF,
        "sourceExecutionKey": SOURCE_EXECUTION_KEY,
        "sourceAuthorizationOrdinal": SOURCE_AUTHORIZATION_ORDINAL,
        "sourceFinalAnalysisRawSha256": raw_sha256(source_analysis_path),
        "sourceProposalRawSha256": raw_sha256(source_proposal_path),
        "sourceReadinessRawSha256": raw_sha256(source_readiness_path),
        "sourceRunMetadataRawSha256": raw_sha256(source_run_metadata_path),
        "promotedManifestRawSha256": promoted_hash,
        "authorizationTemplateRawSha256": raw_sha256(absolute["authorizationTemplate"]),
        "packageRawSha256": raw_sha256(absolute["package"]),
        "baseAdapterRawSha256": raw_sha256(absolute["baseAdapter"]),
        "executionAdapterRawSha256": raw_sha256(absolute["executionAdapter"]),
        "duplicateRunAuditRawSha256": raw_sha256(absolute["duplicateRunAudit"]),
        "runtimeProbeRawSha256": raw_sha256(absolute["runtimeProbe"]),
        "executionWorkflowRawSha256": raw_sha256(absolute["executionWorkflow"]),
        "runtimeLockRawSha256": raw_sha256(absolute["runtimeLock"]),
        "planRawSha256": raw_sha256(absolute["plan"]),
        "analysisDriverRawSha256": raw_sha256(absolute["analysisDriver"]),
        "convergenceModuleRawSha256": raw_sha256(absolute["convergenceModule"]),
        "executorRawSha256": raw_sha256(absolute["executor"]),
        "aggregateRawSha256": raw_sha256(absolute["aggregate"]),
        "auditRawSha256": raw_sha256(absolute["audit"]),
        "authorizationOrdinal": authorization_ordinal,
        "consumed": False,
        "exactAuthorizationCommit": None,
    }
    for key, value in expected_auth.items():
        if authorization.get(key) != value:
            raise GuardRefusal("authorization-stale", "authorization is missing, disabled, or stale", {key: (authorization.get(key), value)})
    for key in expected_auth:
        if key.endswith("RawSha256"):
            require_hash(authorization[key], key)

    head = git(root, "rev-parse", "HEAD")
    parent = git(root, "rev-parse", "HEAD^")
    if head != authorization_ref:
        raise GuardRefusal("authorization-ref", "checked-out HEAD is not supplied authorization ref", {"head": head, "input": authorization_ref})
    if authorization.get("exactAuthorizationParentCommit") != parent:
        raise GuardRefusal("authorization-parent", "authorization parent mismatch", {"actual": parent, "authorized": authorization.get("exactAuthorizationParentCommit")})
    if require_one_purpose_commit:
        changed = git(root, "diff", "--name-only", parent, head).splitlines()
        if changed != [relative["authorization"]]:
            raise GuardRefusal("one-purpose-commit", "authorization commit must change exactly the active confirmation authorization file", changed)

    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "AUTHORIZED",
        "batchId": manifest["batchId"],
        "executionKey": execution_key,
        "authorizationRef": head,
        "authorizationParentCommit": parent,
        "authorizationOrdinal": authorization_ordinal,
        "sourceRunId": source_run_id,
        "sourceFinalAnalysisRawSha256": expected_auth["sourceFinalAnalysisRawSha256"],
        "sourceProposalRawSha256": expected_auth["sourceProposalRawSha256"],
        "sourceReadinessRawSha256": expected_auth["sourceReadinessRawSha256"],
        "sourceRunMetadataRawSha256": expected_auth["sourceRunMetadataRawSha256"],
        "promotedManifestRawSha256": promoted_hash,
        "executionAdapterRawSha256": expected_auth["executionAdapterRawSha256"],
        "runtimeLockRawSha256": expected_auth["runtimeLockRawSha256"],
        "executionWorkflowRawSha256": expected_auth["executionWorkflowRawSha256"],
        "caseCount": len(manifest["cases"]),
        "configuredMcPhotonsSum": sum(case["photonHistories"] for case in manifest["cases"]),
        "boundary": "one-purpose held-out confirmation authorization verified before syntax or solver execution",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--authorization-template", type=Path, required=True)
    parser.add_argument("--source-analysis", type=Path, required=True)
    parser.add_argument("--source-proposal", type=Path, required=True)
    parser.add_argument("--source-readiness", type=Path, required=True)
    parser.add_argument("--source-run-metadata", type=Path, required=True)
    parser.add_argument("--promoted-manifest-output", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--base-adapter", type=Path, required=True)
    parser.add_argument("--execution-adapter", type=Path, required=True)
    parser.add_argument("--duplicate-run-audit", type=Path, required=True)
    parser.add_argument("--runtime-probe", type=Path, required=True)
    parser.add_argument("--execution-workflow", type=Path, required=True)
    parser.add_argument("--runtime-lock", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--analysis-driver", type=Path, required=True)
    parser.add_argument("--convergence-module", type=Path, required=True)
    parser.add_argument("--executor", type=Path, required=True)
    parser.add_argument("--aggregate", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--source-run-id", type=int, required=True)
    parser.add_argument("--authorization-ref", required=True)
    parser.add_argument("--execution-key", required=True)
    parser.add_argument("--authorization-ordinal", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = validate_guard(
            args.repository_root, args.authorization, args.authorization_template,
            args.source_analysis, args.source_proposal, args.source_readiness, args.source_run_metadata,
            args.promoted_manifest_output, args.package, args.base_adapter, args.execution_adapter,
            args.duplicate_run_audit, args.runtime_probe, args.execution_workflow, args.runtime_lock,
            args.plan, args.analysis_driver, args.convergence_module, args.executor, args.aggregate, args.audit,
            args.source_run_id, args.authorization_ref, args.execution_key, args.authorization_ordinal,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump(report))
        print(dump(report), end="")
        return 0
    except GuardRefusal as exc:
        payload = {"schemaVersion": 1, "stageId": STAGE_ID, "status": "REFUSED_BEFORE_SYNTAX_OR_SOLVER", "code": exc.code, "reason": exc.reason, "detail": exc.detail}
        print(dump(payload), end="", file=sys.stderr)
        return 2
    except Exception as exc:
        print(dump({"schemaVersion": 1, "stageId": STAGE_ID, "status": "REFUSED_BEFORE_SYNTAX_OR_SOLVER", "code": "unexpected", "reason": str(exc)}), end="", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
