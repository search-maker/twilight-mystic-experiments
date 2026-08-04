#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

STAGE_ID = "twilight-surrogate-tier-1-execution-v1"
SOURCE_AUDIT_STAGE_ID = "twilight-surrogate-tier-1-source-audit-v1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class GuardError(RuntimeError):
    pass


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise GuardError(f"expected JSON object: {path}")
    return value


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def validate(
    root: Path,
    authorization_path: Path,
    template_path: Path,
    manifest_path: Path,
    source_audit_path: Path,
    paths: dict[str, Path],
    authorization_ref: str,
    execution_key: str,
    authorization_ordinal: int,
    require_context: bool = True,
    require_one_purpose: bool = True,
) -> dict[str, Any]:
    if require_context:
        expected_context = {
            "GITHUB_ACTIONS": "true",
            "GITHUB_EVENT_NAME": "workflow_dispatch",
            "GITHUB_RUN_ATTEMPT": "1",
        }
        stale = {
            key: (os.getenv(key), expected)
            for key, expected in expected_context.items()
            if os.getenv(key) != expected
        }
        if stale:
            raise GuardError(f"wrong GitHub context: {stale}")

    authorization = load(root / authorization_path)
    template = load(root / template_path)
    manifest = load(manifest_path)
    source_audit = load(source_audit_path)

    if authorization.keys() != template.keys():
        raise GuardError("authorization schema differs from disabled template")
    if template.get("authorized") is not False or template.get("authorizationOrdinal") != 0:
        raise GuardError("authorization template is not disabled")
    if manifest.get("stageId") != STAGE_ID:
        raise GuardError("tier-1 execution manifest invalid")
    if len(manifest.get("cases", [])) != 96 or len(manifest.get("geometries", [])) != 48:
        raise GuardError("tier-1 execution manifest count changed")
    if source_audit.get("stageId") != SOURCE_AUDIT_STAGE_ID or source_audit.get("status") != "TIER_1_SOURCE_PROPOSAL_AUDITED":
        raise GuardError("source proposal audit invalid")
    if source_audit.get("caseCount") != 96 or source_audit.get("configuredMcPhotonsSum") != 6_960_000_000:
        raise GuardError("source proposal audit count changed")

    expected = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "authorized": True,
        "scientificExecution": True,
        "scientificDiagnostic": True,
        "successDoesNotAuthorizeProduction": True,
        "executionKey": execution_key,
        "sourceProposalRunId": source_audit["sourceProposalRunId"],
        "sourceProposalArtifactId": source_audit["sourceProposalArtifactId"],
        "sourceProposalArtifactDigest": source_audit["sourceProposalArtifactDigest"],
        "tier1ProposalRawSha256": source_audit["tier1ProposalRawSha256"],
        "sourceProposalAuditRawSha256": raw_sha256(source_audit_path),
        "executionPackageRawSha256": raw_sha256(root / paths["executionPackage"]),
        "executionAdapterRawSha256": raw_sha256(root / paths["executionAdapter"]),
        "executionPlanRawSha256": raw_sha256(root / paths["executionPlan"]),
        "analysisDriverRawSha256": raw_sha256(root / paths["analysisDriver"]),
        "sourceAuditCodeRawSha256": raw_sha256(root / paths["sourceAuditCode"]),
        "duplicateRunAuditRawSha256": raw_sha256(root / paths["duplicateRunAudit"]),
        "runtimeProbeRawSha256": raw_sha256(root / paths["runtimeProbe"]),
        "executionWorkflowRawSha256": raw_sha256(root / paths["executionWorkflow"]),
        "runtimeLockRawSha256": raw_sha256(root / paths["runtimeLock"]),
        "executorRawSha256": raw_sha256(root / paths["executor"]),
        "aggregateRawSha256": raw_sha256(root / paths["aggregate"]),
        "auditRawSha256": raw_sha256(root / paths["audit"]),
        "baseAdapterRawSha256": raw_sha256(root / paths["baseAdapter"]),
        "sourcePilotManifestRawSha256": raw_sha256(root / paths["sourcePilotManifest"]),
        "authorizationProposalCodeRawSha256": raw_sha256(root / paths["authorizationProposalCode"]),
        "authorizationOrdinal": authorization_ordinal,
        "consumed": False,
        "exactAuthorizationCommit": None,
    }
    for key, expected_value in expected.items():
        if authorization.get(key) != expected_value:
            raise GuardError(
                f"authorization stale: {key}: {authorization.get(key)!r} != {expected_value!r}"
            )
    for key, expected_value in expected.items():
        if key.endswith("RawSha256") and (
            not isinstance(expected_value, str) or not SHA256_RE.fullmatch(expected_value)
        ):
            raise GuardError(f"invalid authorization hash: {key}")

    head = git(root, "rev-parse", "HEAD")
    parent = git(root, "rev-parse", "HEAD^")
    if head != authorization_ref:
        raise GuardError("authorization ref does not equal checked-out HEAD")
    if authorization.get("exactAuthorizationParentCommit") != parent:
        raise GuardError("authorization parent does not equal checked-out parent")
    if require_one_purpose:
        changed = git(root, "diff", "--name-only", parent, head).splitlines()
        if changed != [authorization_path.as_posix()]:
            raise GuardError(f"authorization commit is not one-purpose: {changed}")

    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "AUTHORIZED",
        "executionKey": execution_key,
        "authorizationRef": head,
        "authorizationParentCommit": parent,
        "authorizationOrdinal": authorization_ordinal,
        "sourceProposalRunId": source_audit["sourceProposalRunId"],
        "sourceProposalArtifactId": source_audit["sourceProposalArtifactId"],
        "sourceProposalArtifactDigest": source_audit["sourceProposalArtifactDigest"],
        "manifestRawSha256": raw_sha256(manifest_path),
        "executionAdapterRawSha256": expected["executionAdapterRawSha256"],
        "runtimeLockRawSha256": expected["runtimeLockRawSha256"],
        "executionWorkflowRawSha256": expected["executionWorkflowRawSha256"],
        "caseCount": 96,
        "configuredMcPhotonsSum": 6_960_000_000,
        "maximumParallel": 8,
        "scientificExecution": True,
        "scientificDiagnostic": True,
        "successDoesNotAuthorizeProduction": True,
        "surrogateTrainingAuthorized": False,
        "productionModelReady": False,
        "observationValidationRequired": True,
        "boundary": "one-purpose tier-1 numerical execution authorization; no model fitting or production use",
    }


def default_paths() -> dict[str, Path]:
    base = Path("experiments/mystic-batch-v1")
    return {
        "executionPackage": base / "twilight_surrogate_tier1_execution_package.py",
        "executionAdapter": base / "twilight_surrogate_tier1_execution_adapter.py",
        "executionPlan": base / "twilight_surrogate_tier1_execution_plan.py",
        "analysisDriver": base / "twilight_surrogate_tier1_analysis.py",
        "sourceAuditCode": base / "twilight_surrogate_tier1_source_audit.py",
        "duplicateRunAudit": base / "duplicate_run_audit.py",
        "runtimeProbe": base / "runtime_probe.py",
        "executionWorkflow": Path(".github/workflows/twilight-surrogate-tier-1-execution.yml"),
        "runtimeLock": base / "runtime-lock.micromamba.json",
        "executor": base / "scientific_case_executor.py",
        "aggregate": base / "scientific_aggregate.py",
        "audit": base / "scientific_audit.py",
        "baseAdapter": base / "cross_geometry_adapter.py",
        "sourcePilotManifest": base / "manifest.cross-geometry-pilot.proposal.json",
        "authorizationProposalCode": base / "twilight_surrogate_tier1_authorization_proposal.py",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--authorization-template", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--source-audit", type=Path, required=True)
    parser.add_argument("--authorization-ref", required=True)
    parser.add_argument("--execution-key", required=True)
    parser.add_argument("--authorization-ordinal", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.repository_root.resolve()
    try:
        result = validate(
            root,
            args.authorization,
            args.authorization_template,
            args.manifest,
            args.source_audit,
            default_paths(),
            args.authorization_ref,
            args.execution_key,
            args.authorization_ordinal,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump(result))
        print(dump(result), end="")
        return 0
    except Exception as exc:
        print(
            dump(
                {
                    "schemaVersion": 1,
                    "stageId": STAGE_ID,
                    "status": "REFUSED_BEFORE_SYNTAX_OR_SOLVER",
                    "reason": str(exc),
                }
            ),
            file=sys.stderr,
            end="",
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
