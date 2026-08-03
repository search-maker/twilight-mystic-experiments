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

STAGE_ID = "cross-geometry-stage-two-v1"
GENERIC_STAGE_ID = "mystic-batch-v1"
EXPECTED_GROUPS = {
    "g01-reference-bridge",
    "g04-mid-perpendicular",
    "g05-mid-opposite-low",
    "g06-late-opposite-high-aerosol",
}
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


def normalized_relative(path: Path, name: str) -> str:
    text = path.as_posix()
    if path.is_absolute() or ".." in path.parts or text.startswith("./"):
        raise GuardRefusal("invalid-path", f"{name} must be normalized repository-relative", text)
    return text


def require_hash(value: Any, name: str) -> str:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise GuardRefusal("invalid-hash", f"{name} must be lowercase SHA-256", value)
    return value


def validate_guard(
    repository_root: Path,
    authorization_path: Path,
    authorization_template_path: Path,
    proposal_path: Path,
    source_manifest_path: Path,
    source_analysis_path: Path,
    source_provenance_path: Path,
    contract_path: Path,
    base_adapter_path: Path,
    execution_adapter_path: Path,
    analysis_module_path: Path,
    duplicate_run_audit_path: Path,
    runtime_probe_path: Path,
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
    require_one_purpose_commit: bool = True,
) -> dict[str, Any]:
    root = repository_root.resolve()
    path_map = {
        "authorization": authorization_path,
        "authorizationTemplate": authorization_template_path,
        "proposal": proposal_path,
        "sourceManifest": source_manifest_path,
        "sourceAnalysis": source_analysis_path,
        "sourceProvenance": source_provenance_path,
        "contract": contract_path,
        "baseAdapter": base_adapter_path,
        "executionAdapter": execution_adapter_path,
        "analysisModule": analysis_module_path,
        "duplicateRunAudit": duplicate_run_audit_path,
        "runtimeProbe": runtime_probe_path,
        "executionWorkflow": execution_workflow_path,
        "runtimeLock": runtime_lock_path,
        "plan": plan_path,
        "analysisDriver": analysis_driver_path,
        "executor": executor_path,
        "aggregate": aggregate_path,
        "audit": audit_path,
    }
    rel = {key: normalized_relative(value, key) for key, value in path_map.items()}
    absolute = {key: root / value for key, value in rel.items()}
    for key, path in absolute.items():
        if not path.is_file():
            raise GuardRefusal("missing-file", f"{key} file does not exist", str(path))

    if not ID_RE.fullmatch(execution_key):
        raise GuardRefusal("execution-key", "invalid execution key", execution_key)
    if not isinstance(authorization_ordinal, int) or isinstance(authorization_ordinal, bool) or authorization_ordinal < 1:
        raise GuardRefusal("authorization-ordinal", "authorization ordinal must be positive")
    if require_github_context:
        expected_context = {"GITHUB_ACTIONS": "true", "GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_RUN_ATTEMPT": "1"}
        stale = {key: (os.getenv(key), expected) for key, expected in expected_context.items() if os.getenv(key) != expected}
        if stale:
            raise GuardRefusal("github-context", "not exact first-attempt workflow_dispatch context", stale)

    proposal = load_json(absolute["proposal"])
    source_manifest = load_json(absolute["sourceManifest"])
    source_analysis = load_json(absolute["sourceAnalysis"])
    provenance = load_json(absolute["sourceProvenance"])
    contract = load_json(absolute["contract"])
    authorization = load_json(absolute["authorization"])
    authorization_template = load_json(absolute["authorizationTemplate"])
    disabled_template = {
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
    stale_template = {
        key: (authorization_template.get(key), expected)
        for key, expected in disabled_template.items()
        if authorization_template.get(key) != expected
    }
    if stale_template:
        raise GuardRefusal("authorization-template", "stage-two authorization template is not disabled", stale_template)
    if set(authorization) != set(authorization_template):
        raise GuardRefusal("authorization-schema", "active authorization fields differ from the frozen template schema")

    proposal_header = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "batchId": "cross-geometry-stage-two-screening-v1",
        "mode": "scientific-proposal",
        "proposalOnly": True,
        "scientificExecution": False,
        "successDoesNotAuthorizeProduction": True,
    }
    stale_header = {key: (proposal.get(key), expected) for key, expected in proposal_header.items() if proposal.get(key) != expected}
    if stale_header:
        raise GuardRefusal("proposal-header", "stage-two proposal header changed", stale_header)
    if source_manifest.get("stageId") != "cross-geometry-pilot-v1" or source_manifest.get("proposalOnly") is not True:
        raise GuardRefusal("source-manifest", "source pilot manifest header changed")
    if source_analysis.get("stageId") != "cross-geometry-pilot-v1" or source_analysis.get("status") != "SCREENING_ANALYZED":
        raise GuardRefusal("source-analysis", "source screening analysis header changed")
    if provenance.get("stageId") != STAGE_ID or provenance.get("status") != "SOURCE_SCREENING_FROZEN":
        raise GuardRefusal("source-provenance", "source provenance header changed")
    if contract.get("stageId") != "cross-geometry-pilot-v1" or contract.get("screeningOnly") is not True:
        raise GuardRefusal("contract", "screening contract header changed")

    source_manifest_hash = raw_sha256(absolute["sourceManifest"])
    source_analysis_hash = raw_sha256(absolute["sourceAnalysis"])
    source_provenance_hash = raw_sha256(absolute["sourceProvenance"])
    if proposal.get("sourceManifestRawSha256") != source_manifest_hash or provenance.get("sourceManifestRawSha256") != source_manifest_hash:
        raise GuardRefusal("source-manifest-hash", "source pilot manifest binding changed")
    if proposal.get("sourceAnalysisRawSha256") != source_analysis_hash or provenance.get("sourceAnalysisRawSha256") != source_analysis_hash:
        raise GuardRefusal("source-analysis-hash", "source screening analysis binding changed")
    if source_analysis.get("proposalRawSha256") != source_manifest_hash:
        raise GuardRefusal("source-analysis-manifest", "source analysis does not bind the pilot manifest")

    selected = proposal.get("selectedGeometryIds")
    cases = proposal.get("cases")
    if not isinstance(selected, list) or set(selected) != EXPECTED_GROUPS or len(selected) != 4:
        raise GuardRefusal("selected-geometries", "stage-two selected geometry set changed", selected)
    expandable = sorted(
        result.get("groupId")
        for result in source_analysis.get("geometryResults", [])
        if isinstance(result, dict) and result.get("classification") in {"NEEDS_MORE_BLOCKS", "SCREENING_DISCREPANCY"}
    )
    if expandable != sorted(EXPECTED_GROUPS) or sorted(selected) != expandable:
        raise GuardRefusal("selection-source", "stage-two selection is not the exact expandable source set", expandable)
    if source_analysis.get("classificationCounts") != {
        "NEEDS_MORE_BLOCKS": 4,
        "SCREENING_AGREEMENT": 2,
        "SCREENING_DISCREPANCY": 0,
        "STRUCTURAL_OR_EXECUTION_FAILURE": 0,
    }:
        raise GuardRefusal("source-classifications", "source screening classification counts changed")

    if not isinstance(cases, list) or len(cases) != 16:
        raise GuardRefusal("case-count", "stage-two proposal must contain exactly 16 cases")
    if [case.get("ordinal") for case in cases if isinstance(case, dict)] != list(range(1, 17)):
        raise GuardRefusal("ordinals", "stage-two case ordinals changed")
    if {case.get("groupId") for case in cases if isinstance(case, dict)} != EXPECTED_GROUPS:
        raise GuardRefusal("case-groups", "stage-two case group set changed")
    if {case.get("block") for case in cases if isinstance(case, dict)} != {3, 4}:
        raise GuardRefusal("case-blocks", "stage-two blocks must be 3 and 4")
    if {case.get("method") for case in cases if isinstance(case, dict)} != {"reference-vroom", "alis"}:
        raise GuardRefusal("case-methods", "stage-two methods changed")
    seeds = [case.get("seed") for case in cases if isinstance(case, dict)]
    pilot_seeds = {case.get("seed") for case in source_manifest.get("cases", []) if isinstance(case, dict)}
    if len(seeds) != 16 or len(set(seeds)) != 16 or pilot_seeds.intersection(seeds):
        raise GuardRefusal("case-seeds", "stage-two seeds are duplicated or reuse pilot seeds")
    photon_sum = sum(case.get("photonHistories", 0) for case in cases if isinstance(case, dict))
    if photon_sum != 320_000_000 or any(case.get("photonHistories") != 20_000_000 for case in cases if isinstance(case, dict)):
        raise GuardRefusal("photon-accounting", "stage-two photon accounting changed", photon_sum)

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
        raise GuardRefusal("source-provenance", "source artifact provenance changed", stale_provenance)

    required_auth = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "authorized": True,
        "scientificExecution": True,
        "scientificDiagnostic": True,
        "successDoesNotAuthorizeProduction": True,
        "executionKey": execution_key,
        "batchId": proposal["batchId"],
        "proposalPath": rel["proposal"],
        "proposalRawSha256": raw_sha256(absolute["proposal"]),
        "sourceManifestRawSha256": source_manifest_hash,
        "sourceAnalysisRawSha256": source_analysis_hash,
        "sourceProvenanceRawSha256": source_provenance_hash,
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
        "authorizationOrdinal": authorization_ordinal,
        "consumed": False,
        "exactAuthorizationCommit": None,
    }
    stale_auth = {key: (authorization.get(key), expected) for key, expected in required_auth.items() if authorization.get(key) != expected}
    if stale_auth:
        raise GuardRefusal("authorization-stale", "authorization is missing, disabled, or stale", stale_auth)

    head = git(root, "rev-parse", "HEAD")
    parent = git(root, "rev-parse", "HEAD^")
    if head != authorization_ref:
        raise GuardRefusal("authorization-ref", "checked-out HEAD is not supplied authorization ref", {"head": head, "input": authorization_ref})
    if authorization.get("exactAuthorizationParentCommit") != parent:
        raise GuardRefusal("authorization-parent", "authorization parent mismatch", {"actual": parent, "authorized": authorization.get("exactAuthorizationParentCommit")})
    if require_one_purpose_commit:
        changed = git(root, "diff", "--name-only", parent, head).splitlines()
        if changed != [rel["authorization"]]:
            raise GuardRefusal("one-purpose-commit", "authorization commit must change exactly the active stage-two authorization file", changed)

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
        "proposalRawSha256": raw_sha256(absolute["proposal"]),
        "sourceManifestRawSha256": source_manifest_hash,
        "sourceAnalysisRawSha256": source_analysis_hash,
        "sourceProvenanceRawSha256": source_provenance_hash,
        "contractRawSha256": raw_sha256(absolute["contract"]),
        "authorizationTemplateRawSha256": raw_sha256(absolute["authorizationTemplate"]),
        "baseAdapterRawSha256": raw_sha256(absolute["baseAdapter"]),
        "executionAdapterRawSha256": raw_sha256(absolute["executionAdapter"]),
        "analysisModuleRawSha256": raw_sha256(absolute["analysisModule"]),
        "duplicateRunAuditRawSha256": raw_sha256(absolute["duplicateRunAudit"]),
        "runtimeProbeRawSha256": raw_sha256(absolute["runtimeProbe"]),
        "executionWorkflowRawSha256": raw_sha256(absolute["executionWorkflow"]),
        "runtimeLockRawSha256": raw_sha256(absolute["runtimeLock"]),
        "caseCount": 16,
        "maximumParallel": proposal["limits"]["maximumParallel"],
        "perCaseTimeoutSeconds": proposal["limits"]["perCaseTimeoutSeconds"],
        "configuredMcPhotonsSum": photon_sum,
        "sourceScientificRunId": provenance["sourceScientificRunId"],
        "sourcePostprocessRunId": provenance["sourcePostprocessRunId"],
        "boundary": "one-purpose stage-two authorization verified before syntax check or solver execution",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, default=Path("."))
    for name in (
        "authorization", "authorization-template", "proposal", "source-manifest", "source-analysis", "source-provenance",
        "contract", "base-adapter", "execution-adapter", "analysis-module", "duplicate-run-audit", "runtime-probe",
        "execution-workflow", "runtime-lock", "plan", "analysis-driver", "executor", "aggregate", "audit",
    ):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--authorization-ref", required=True)
    parser.add_argument("--execution-key", required=True)
    parser.add_argument("--authorization-ordinal", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = validate_guard(
            args.repository_root, args.authorization, args.authorization_template, args.proposal,
            args.source_manifest, args.source_analysis, args.source_provenance, args.contract,
            args.base_adapter, args.execution_adapter, args.analysis_module, args.duplicate_run_audit, args.runtime_probe,
            args.execution_workflow, args.runtime_lock, args.plan,
            args.analysis_driver, args.executor, args.aggregate, args.audit,
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
