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

STAGE_ID = "cross-geometry-selected-reference-confirmation-v1"
AUTHORIZATION_ORDINAL = 5
EXECUTION_KEY = f"{STAGE_ID}:screening:{AUTHORIZATION_ORDINAL}"
SOURCE_AUTHORIZATION_REF = "7e630b8f46259ddf6a0cfdf5e381872c0182d0ba"
SOURCE_EXECUTION_KEY = "cross-geometry-final-convergence-v1:screening:4"
SOURCE_AUTHORIZATION_ORDINAL = 4
PACKAGE_ROOT = Path("experiments/mystic-batch-v1")
PATHS = {
    "authorization": PACKAGE_ROOT / "authorization.cross-geometry-confirmation.json",
    "authorizationTemplate": PACKAGE_ROOT / "authorization.cross-geometry-confirmation-execution-template.json",
    "package": PACKAGE_ROOT / "cross_geometry_confirmation_package.py",
    "baseAdapter": PACKAGE_ROOT / "cross_geometry_adapter.py",
    "executionAdapter": PACKAGE_ROOT / "cross_geometry_confirmation_execution_adapter.py",
    "duplicateRunAudit": PACKAGE_ROOT / "duplicate_run_audit.py",
    "runtimeProbe": PACKAGE_ROOT / "runtime_probe.py",
    "executionWorkflow": Path(".github/workflows/mystic-batch-v1-cross-geometry-confirmation-execution.yml"),
    "runtimeLock": PACKAGE_ROOT / "runtime-lock.micromamba.json",
    "plan": PACKAGE_ROOT / "cross_geometry_confirmation_execution_plan.py",
    "analysisDriver": PACKAGE_ROOT / "cross_geometry_confirmation_analysis_driver.py",
    "convergenceModule": PACKAGE_ROOT / "cross_geometry_convergence_v2.py",
    "executor": PACKAGE_ROOT / "scientific_case_executor.py",
    "aggregate": PACKAGE_ROOT / "scientific_aggregate.py",
    "audit": PACKAGE_ROOT / "scientific_audit.py",
}


class ProposalFailure(RuntimeError):
    pass


def load(path: Path) -> dict[str, Any]:
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


def load_package(path: Path):
    spec = importlib.util.spec_from_file_location("cross_geometry_confirmation_package", path)
    if spec is None or spec.loader is None:
        raise ProposalFailure(f"cannot load confirmation package: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_proposal(
    repository_root: Path,
    source_analysis_path: Path,
    source_proposal_path: Path,
    source_readiness_path: Path,
    source_run_metadata_path: Path,
    source_run_id: int,
) -> dict[str, Any]:
    root = repository_root.resolve()
    absolute = {key: root / path for key, path in PATHS.items()}
    for key, path in absolute.items():
        if not path.is_file():
            raise ProposalFailure(f"required repository file missing: {key}: {path}")
    active = load(absolute["authorization"])
    template = load(absolute["authorizationTemplate"])
    if active != template:
        raise ProposalFailure("active confirmation authorization differs from disabled template")
    required_disabled = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "authorized": False,
        "scientificExecution": False,
        "scientificDiagnostic": False,
        "authorizationOrdinal": 0,
        "consumed": False,
        "exactAuthorizationParentCommit": None,
        "exactAuthorizationCommit": None,
    }
    stale = {key: (active.get(key), value) for key, value in required_disabled.items() if active.get(key) != value}
    if stale:
        raise ProposalFailure(f"active confirmation authorization is not disabled: {stale}")
    source_analysis = load(source_analysis_path)
    if source_analysis.get("stageId") != "cross-geometry-final-convergence-v1" or source_analysis.get("status") != "FINAL_CONVERGENCE_ANALYZED":
        raise ProposalFailure("wrong source final-convergence analysis")
    if source_analysis.get("heldOutConfirmationRequired") is not True or source_analysis.get("heldOutConfirmationCaseCount") == 0:
        head = git(root, "rev-parse", "HEAD")
        return {
            "schemaVersion": 1,
            "stageId": STAGE_ID,
            "status": "NO_HELD_OUT_CONFIRMATION_REQUIRED",
            "sourceCommit": head,
            "sourceRunId": source_run_id,
            "authorizationOrdinal": None,
            "executionKey": None,
            "caseCount": 0,
            "configuredMcPhotonsSum": 0,
            "promotedManifest": None,
            "promotedManifestRawSha256": None,
            "authorization": None,
            "boundary": "source analysis requires no held-out execution; no authorization is proposed",
        }
    package = load_package(absolute["package"])
    manifest = package.promote(source_analysis_path, source_proposal_path, source_readiness_path, source_run_metadata_path, source_run_id)
    promoted_text = package.dump(manifest)
    promoted_hash = hashlib.sha256(promoted_text.encode("utf-8")).hexdigest()
    head = git(root, "rev-parse", "HEAD")
    authorization = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "authorized": True,
        "scientificExecution": True,
        "scientificDiagnostic": True,
        "successDoesNotAuthorizeProduction": True,
        "executionKey": EXECUTION_KEY,
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
        "exactAuthorizationParentCommit": head,
        "exactAuthorizationCommit": None,
        "authorizationOrdinal": AUTHORIZATION_ORDINAL,
        "consumed": False,
        "note": "One-purpose held-out confirmation authorization. It does not authorize model training, a production default, or observational-validity claims.",
    }
    if set(authorization) != set(template):
        raise ProposalFailure("proposed authorization fields differ from frozen template schema")
    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "PROPOSAL_ONLY_NOT_AUTHORIZATION",
        "sourceCommit": head,
        "sourceRunId": source_run_id,
        "authorizationOrdinal": AUTHORIZATION_ORDINAL,
        "executionKey": EXECUTION_KEY,
        "caseCount": len(manifest["cases"]),
        "configuredMcPhotonsSum": sum(case["photonHistories"] for case in manifest["cases"]),
        "promotedManifest": manifest,
        "promotedManifestRawSha256": promoted_hash,
        "authorization": authorization,
        "boundary": "proposal artifact only; a later one-purpose commit changing only the active authorization file and a separate manual dispatch are required",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--source-analysis", type=Path, required=True)
    parser.add_argument("--source-proposal", type=Path, required=True)
    parser.add_argument("--source-readiness", type=Path, required=True)
    parser.add_argument("--source-run-metadata", type=Path, required=True)
    parser.add_argument("--source-run-id", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        proposal = build_proposal(args.repository_root, args.source_analysis, args.source_proposal, args.source_readiness, args.source_run_metadata, args.source_run_id)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump(proposal))
        print(dump({key: proposal[key] for key in ("status", "stageId", "sourceRunId", "authorizationOrdinal", "executionKey", "caseCount", "configuredMcPhotonsSum")}), end="")
        return 0
    except Exception as exc:
        print(dump({"status": "REFUSED", "stageId": STAGE_ID, "reason": str(exc)}), end="", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
