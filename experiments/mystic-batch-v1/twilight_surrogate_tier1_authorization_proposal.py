#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

STAGE_ID = "twilight-surrogate-tier-1-authorization-proposal-v1"
EXECUTION_STAGE_ID = "twilight-surrogate-tier-1-execution-v1"
EXECUTION_KEY = "twilight-surrogate-tier-1-v1:numerical:1"
AUTHORIZATION_ORDINAL = 1
AUTHORIZATION_PATH = Path(
    "experiments/mystic-batch-v1/authorization.twilight-surrogate-tier-1.json"
)
TEMPLATE_PATH = Path(
    "experiments/mystic-batch-v1/authorization.twilight-surrogate-tier-1-template.json"
)


class ProposalError(RuntimeError):
    pass


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ProposalError(f"expected JSON object: {path}")
    return value


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def paths() -> dict[str, Path]:
    base = Path("experiments/mystic-batch-v1")
    return {
        "executionPackageRawSha256": base / "twilight_surrogate_tier1_execution_package.py",
        "executionAdapterRawSha256": base / "twilight_surrogate_tier1_execution_adapter.py",
        "executionPlanRawSha256": base / "twilight_surrogate_tier1_execution_plan.py",
        "analysisDriverRawSha256": base / "twilight_surrogate_tier1_analysis.py",
        "sourceAuditCodeRawSha256": base / "twilight_surrogate_tier1_source_audit.py",
        "duplicateRunAuditRawSha256": base / "duplicate_run_audit.py",
        "runtimeProbeRawSha256": base / "runtime_probe.py",
        "executionWorkflowRawSha256": Path(
            ".github/workflows/twilight-surrogate-tier-1-execution.yml"
        ),
        "runtimeLockRawSha256": base / "runtime-lock.micromamba.json",
        "executorRawSha256": base / "scientific_case_executor.py",
        "aggregateRawSha256": base / "scientific_aggregate.py",
        "auditRawSha256": base / "scientific_audit.py",
        "baseAdapterRawSha256": base / "cross_geometry_adapter.py",
        "sourcePilotManifestRawSha256": base / "manifest.cross-geometry-pilot.proposal.json",
        "authorizationProposalCodeRawSha256": base / "twilight_surrogate_tier1_authorization_proposal.py",
    }


def build(root: Path, source_audit_path: Path) -> dict[str, Any]:
    source_audit = load(source_audit_path)
    required_source = {
        "schemaVersion": 1,
        "stageId": "twilight-surrogate-tier-1-source-audit-v1",
        "status": "TIER_1_SOURCE_PROPOSAL_AUDITED",
        "geometryCount": 48,
        "caseCount": 96,
        "configuredMcPhotonsSum": 6_960_000_000,
        "referenceAnchorCount": 6,
        "scientificExecution": False,
        "executionAuthorized": False,
        "surrogateTrainingAuthorized": False,
        "productionModelReady": False,
        "observationValidationRequired": True,
    }
    stale = {
        key: (source_audit.get(key), expected)
        for key, expected in required_source.items()
        if source_audit.get(key) != expected
    }
    if stale:
        raise ProposalError(f"source audit mismatch: {stale}")

    template = load(root / TEMPLATE_PATH)
    active = load(root / AUTHORIZATION_PATH)
    if active != template:
        raise ProposalError("active authorization differs from disabled template")
    required_template = {
        "schemaVersion": 1,
        "stageId": EXECUTION_STAGE_ID,
        "authorized": False,
        "scientificExecution": False,
        "scientificDiagnostic": False,
        "authorizationOrdinal": 0,
        "consumed": False,
        "exactAuthorizationParentCommit": None,
        "exactAuthorizationCommit": None,
    }
    stale = {
        key: (template.get(key), expected)
        for key, expected in required_template.items()
        if template.get(key) != expected
    }
    if stale:
        raise ProposalError(f"disabled template mismatch: {stale}")

    parent = git(root, "rev-parse", "HEAD")
    if not parent or len(parent) != 40:
        raise ProposalError("exact authorization parent commit unavailable")

    authorization = dict(template)
    authorization.update(
        {
            "authorized": True,
            "scientificExecution": True,
            "scientificDiagnostic": True,
            "executionKey": EXECUTION_KEY,
            "sourceProposalRunId": source_audit["sourceProposalRunId"],
            "sourceProposalArtifactId": source_audit["sourceProposalArtifactId"],
            "sourceProposalArtifactDigest": source_audit["sourceProposalArtifactDigest"],
            "tier1ProposalRawSha256": source_audit["tier1ProposalRawSha256"],
            "sourceProposalAuditRawSha256": raw_sha256(source_audit_path),
            "exactAuthorizationParentCommit": parent,
            "exactAuthorizationCommit": None,
            "authorizationOrdinal": AUTHORIZATION_ORDINAL,
            "consumed": False,
            "note": "One-purpose tier-1 numerical execution authorization proposal. This proposal does not authorize execution until copied unchanged into a single-file child commit and manually dispatched.",
        }
    )
    for field, relative_path in paths().items():
        path = root / relative_path
        if not path.is_file():
            raise ProposalError(f"bound file missing: {relative_path}")
        authorization[field] = raw_sha256(path)

    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "PROPOSAL_ONLY_NOT_AUTHORIZATION",
        "executionAuthorizedByProposal": False,
        "scientificExecution": False,
        "sourceProposalRunId": source_audit["sourceProposalRunId"],
        "sourceProposalArtifactId": source_audit["sourceProposalArtifactId"],
        "sourceProposalArtifactDigest": source_audit["sourceProposalArtifactDigest"],
        "sourceProposalAuditRawSha256": raw_sha256(source_audit_path),
        "authorizationPath": AUTHORIZATION_PATH.as_posix(),
        "exactAuthorizationParentCommit": parent,
        "executionKey": EXECUTION_KEY,
        "authorizationOrdinal": AUTHORIZATION_ORDINAL,
        "caseCount": 96,
        "configuredMcPhotonsSum": 6_960_000_000,
        "maximumParallel": 8,
        "authorization": authorization,
        "boundary": "proposal only; no syntax check, solver, model fitting, or authorization commit is created",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--source-audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = build(args.repository_root.resolve(), args.source_audit)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump(result))
        print(dump(result), end="")
        return 0
    except Exception as exc:
        print(
            dump({"schemaVersion": 1, "stageId": STAGE_ID, "status": "REFUSED", "reason": str(exc)}),
            file=sys.stderr,
            end="",
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
