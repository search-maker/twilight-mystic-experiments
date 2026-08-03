#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

STAGE_ID = "cross-geometry-stage-two-v1"
AUTHORIZATION_ORDINAL = 3
EXECUTION_KEY = f"cross-geometry-stage-two-v1:screening:{AUTHORIZATION_ORDINAL}"
PACKAGE = Path("experiments/mystic-batch-v1")
PATHS = {
    "authorization": PACKAGE / "authorization.cross-geometry-stage-two.json",
    "authorizationTemplate": PACKAGE / "authorization.cross-geometry-stage-two-execution-template.json",
    "proposal": PACKAGE / "manifest.cross-geometry-stage-two.proposal.json",
    "sourceManifest": PACKAGE / "manifest.cross-geometry-pilot.proposal.json",
    "sourceAnalysis": PACKAGE / "results/screening-analysis.cross-geometry-pilot-screening-2.json",
    "sourceProvenance": PACKAGE / "results/stage-two-source-provenance.json",
    "contract": PACKAGE / "cross-geometry-contract.json",
    "baseAdapter": PACKAGE / "cross_geometry_adapter.py",
    "executionAdapter": PACKAGE / "cross_geometry_stage_two_execution_adapter.py",
    "analysisModule": PACKAGE / "cross_geometry_analysis.py",
    "duplicateRunAudit": PACKAGE / "duplicate_run_audit.py",
    "runtimeProbe": PACKAGE / "runtime_probe.py",
    "executionWorkflow": Path(".github/workflows/mystic-batch-v1-cross-geometry-stage-two-execution.yml"),
    "runtimeLock": PACKAGE / "runtime-lock.micromamba.json",
    "plan": PACKAGE / "cross_geometry_stage_two_execution_plan.py",
    "analysisDriver": PACKAGE / "cross_geometry_stage_two_execution_analysis_driver.py",
    "executor": PACKAGE / "scientific_case_executor.py",
    "aggregate": PACKAGE / "scientific_aggregate.py",
    "audit": PACKAGE / "scientific_audit.py",
}
EXPECTED_GROUPS = {
    "g01-reference-bridge",
    "g04-mid-perpendicular",
    "g05-mid-opposite-low",
    "g06-late-opposite-high-aerosol",
}


class ProposalFailure(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ProposalFailure(f"cannot read JSON object {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ProposalFailure(f"expected JSON object: {path}")
    return value


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def ensure_disabled(active: dict[str, Any], template: dict[str, Any]) -> None:
    if active != template:
        raise ProposalFailure("active stage-two authorization differs from disabled template")
    required = {
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
    stale = {key: (active.get(key), expected) for key, expected in required.items() if active.get(key) != expected}
    if stale:
        raise ProposalFailure(f"active stage-two authorization is not disabled: {stale}")


def validate_frozen_science(proposal: dict[str, Any], source: dict[str, Any], analysis: dict[str, Any], provenance: dict[str, Any]) -> None:
    required = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "batchId": "cross-geometry-stage-two-screening-v1",
        "mode": "scientific-proposal",
        "proposalOnly": True,
        "scientificExecution": False,
        "successDoesNotAuthorizeProduction": True,
    }
    stale = {key: (proposal.get(key), expected) for key, expected in required.items() if proposal.get(key) != expected}
    if stale:
        raise ProposalFailure(f"stage-two proposal header changed: {stale}")
    if source.get("stageId") != "cross-geometry-pilot-v1" or source.get("proposalOnly") is not True:
        raise ProposalFailure("source pilot manifest header changed")
    if analysis.get("stageId") != "cross-geometry-pilot-v1" or analysis.get("status") != "SCREENING_ANALYZED":
        raise ProposalFailure("source screening analysis header changed")
    if provenance.get("stageId") != STAGE_ID or provenance.get("status") != "SOURCE_SCREENING_FROZEN":
        raise ProposalFailure("source provenance header changed")

    selected = proposal.get("selectedGeometryIds")
    cases = proposal.get("cases")
    if not isinstance(selected, list) or set(selected) != EXPECTED_GROUPS or len(selected) != 4:
        raise ProposalFailure("stage-two selected geometry set changed")
    if not isinstance(cases, list) or len(cases) != 16:
        raise ProposalFailure("stage-two proposal must contain exactly 16 cases")
    if {case.get("groupId") for case in cases if isinstance(case, dict)} != EXPECTED_GROUPS:
        raise ProposalFailure("stage-two case group set changed")
    if {case.get("block") for case in cases if isinstance(case, dict)} != {3, 4}:
        raise ProposalFailure("stage-two blocks must be 3 and 4")
    if {case.get("method") for case in cases if isinstance(case, dict)} != {"reference-vroom", "alis"}:
        raise ProposalFailure("stage-two method set changed")
    seeds = [case.get("seed") for case in cases if isinstance(case, dict)]
    pilot_seeds = {case.get("seed") for case in source.get("cases", []) if isinstance(case, dict)}
    if len(seeds) != 16 or len(set(seeds)) != 16 or pilot_seeds.intersection(seeds):
        raise ProposalFailure("stage-two seeds are duplicated or reuse pilot seeds")
    photon_sum = sum(case.get("photonHistories", 0) for case in cases if isinstance(case, dict))
    if photon_sum != 320_000_000 or any(case.get("photonHistories") != 20_000_000 for case in cases if isinstance(case, dict)):
        raise ProposalFailure(f"stage-two photon accounting changed: {photon_sum}")
    if analysis.get("classificationCounts") != {
        "NEEDS_MORE_BLOCKS": 4,
        "SCREENING_AGREEMENT": 2,
        "SCREENING_DISCREPANCY": 0,
        "STRUCTURAL_OR_EXECUTION_FAILURE": 0,
    }:
        raise ProposalFailure("source screening classification counts changed")
    provenance_required = {
        "sourceScientificRunId": 30856116586,
        "sourcePostprocessRunId": 30858046820,
        "sourceAuthorizationRef": "018f61ef8f83c00e69d7d72b301fd37ba0de3c0a",
        "sourceAuthorizationOrdinal": 2,
        "sourcePostprocessArtifactId": 8873226100,
        "sourcePostprocessArtifactDigest": "sha256:32ade5a6f72562b77f25d4e5232c0d51f4cc82171497f5a02965760c026cf736",
        "authorizationCreated": False,
        "scientificExecution": False,
    }
    stale_provenance = {key: (provenance.get(key), expected) for key, expected in provenance_required.items() if provenance.get(key) != expected}
    if stale_provenance:
        raise ProposalFailure(f"source provenance changed: {stale_provenance}")


def build_proposal(repository_root: Path) -> dict[str, Any]:
    root = repository_root.resolve()
    absolute = {key: root / path for key, path in PATHS.items()}
    for key, path in absolute.items():
        if not path.is_file():
            raise ProposalFailure(f"missing {key}: {path}")

    active = load_json(absolute["authorization"])
    template = load_json(absolute["authorizationTemplate"])
    ensure_disabled(active, template)

    proposal = load_json(absolute["proposal"])
    source = load_json(absolute["sourceManifest"])
    analysis = load_json(absolute["sourceAnalysis"])
    provenance = load_json(absolute["sourceProvenance"])
    validate_frozen_science(proposal, source, analysis, provenance)

    source_manifest_hash = raw_sha256(absolute["sourceManifest"])
    source_analysis_hash = raw_sha256(absolute["sourceAnalysis"])
    if proposal.get("sourceManifestRawSha256") != source_manifest_hash or provenance.get("sourceManifestRawSha256") != source_manifest_hash:
        raise ProposalFailure("source pilot manifest hash binding changed")
    if proposal.get("sourceAnalysisRawSha256") != source_analysis_hash or provenance.get("sourceAnalysisRawSha256") != source_analysis_hash:
        raise ProposalFailure("source screening analysis hash binding changed")

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
        "sourceManifestRawSha256": source_manifest_hash,
        "sourceAnalysisRawSha256": source_analysis_hash,
        "sourceProvenanceRawSha256": raw_sha256(absolute["sourceProvenance"]),
        "contractRawSha256": raw_sha256(absolute["contract"]),
        "authorizationTemplateRawSha256": raw_sha256(absolute["authorizationTemplate"]),
        "baseAdapterRawSha256": raw_sha256(absolute["baseAdapter"]),
        "executionAdapterRawSha256": raw_sha256(absolute["executionAdapter"]),
        "analysisModuleRawSha256": raw_sha256(absolute["analysisModule"]),
        "duplicateRunAuditRawSha256": raw_sha256(absolute["duplicateRunAudit"]),
        "runtimeProbeRawSha256": raw_sha256(absolute["runtimeProbe"]),
        "executionWorkflowRawSha256": raw_sha256(absolute["executionWorkflow"]),
        "runtimeLockRawSha256": raw_sha256(absolute["runtimeLock"]),
        "planRawSha256": raw_sha256(absolute["plan"]),
        "analysisDriverRawSha256": raw_sha256(absolute["analysisDriver"]),
        "executorRawSha256": raw_sha256(absolute["executor"]),
        "aggregateRawSha256": raw_sha256(absolute["aggregate"]),
        "auditRawSha256": raw_sha256(absolute["audit"]),
        "exactAuthorizationParentCommit": source_commit,
        "exactAuthorizationCommit": None,
        "authorizationOrdinal": AUTHORIZATION_ORDINAL,
        "consumed": False,
        "note": "Proposal only. A future one-purpose commit may replace only authorization.cross-geometry-stage-two.json with this object; a separate reviewed workflow_dispatch is still required.",
    }
    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "PROPOSAL_ONLY_NOT_AUTHORIZATION",
        "executionAuthorizedByProposal": False,
        "sourceCommit": source_commit,
        "proposedAuthorization": proposed_authorization,
        "caseCount": 16,
        "configuredMcPhotonsSum": 320_000_000,
        "sourceScientificRunId": provenance["sourceScientificRunId"],
        "sourcePostprocessRunId": provenance["sourcePostprocessRunId"],
        "boundary": "This artifact computes exact stage-two authorization inputs only. It performs no syntax check, uvspec process, MYSTIC solver, retry, or workflow dispatch.",
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
