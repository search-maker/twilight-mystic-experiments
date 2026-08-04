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

STAGE_ID = "cross-geometry-final-convergence-v1"
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._:-]{2,159}$")
EXTERNAL_SCREENING_SHA = "61d8c42b11995a5787f74b2bb9e2efd503cff949564973c8c05b7b7c6f3ca01b"


class Refusal(RuntimeError):
    def __init__(self, code: str, reason: str, detail: Any = None) -> None:
        super().__init__(reason)
        self.code = code
        self.reason = reason
        self.detail = detail


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except Exception as exc:
        raise Refusal("json", f"cannot read {path}", str(exc)) from exc
    if not isinstance(value, dict):
        raise Refusal("json", f"expected object {path}")
    return value


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def relative(path: Path, name: str) -> str:
    if path.is_absolute() or ".." in path.parts:
        raise Refusal("path", f"invalid {name} path", str(path))
    return path.as_posix()


def validate(root: Path, paths: dict[str, Path], authorization_ref: str, execution_key: str, ordinal: int, github_context: bool = True, one_purpose: bool = True) -> dict[str, Any]:
    root = root.resolve()
    rel = {name: relative(path, name) for name, path in paths.items()}
    absolute = {name: root / path for name, path in rel.items()}
    for name, path in absolute.items():
        if not path.is_file():
            raise Refusal("missing", f"missing {name}", str(path))
    if not ID_RE.fullmatch(execution_key):
        raise Refusal("key", "invalid execution key")
    if ordinal < 1:
        raise Refusal("ordinal", "ordinal must be positive")
    if github_context:
        expected = {"GITHUB_ACTIONS": "true", "GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_RUN_ATTEMPT": "1"}
        stale = {key: (os.getenv(key), value) for key, value in expected.items() if os.getenv(key) != value}
        if stale:
            raise Refusal("context", "not first-attempt manual dispatch", stale)

    proposal = load(absolute["proposal"])
    frozen_screening = load(absolute["sourceScreening"])
    convergence = load(absolute["sourceConvergence"])
    provenance = load(absolute["sourceProvenance"])
    authorization = load(absolute["authorization"])
    template = load(absolute["authorizationTemplate"])

    required_header = {"schemaVersion": 1, "stageId": STAGE_ID, "batchId": "cross-geometry-final-convergence-screening-v1", "proposalOnly": True, "scientificExecution": False, "successDoesNotAuthorizeProduction": True}
    stale = {key: (proposal.get(key), value) for key, value in required_header.items() if proposal.get(key) != value}
    if stale:
        raise Refusal("proposal", "proposal header changed", stale)
    if frozen_screening.get("stageId") != "cross-geometry-stage-two-v1" or frozen_screening.get("status") != "STAGE_TWO_SCREENING_ANALYZED":
        raise Refusal("source", "wrong frozen stage-two screening")
    if convergence.get("stageId") != "cross-geometry-convergence-v2" or convergence.get("status") != "REANALYZED_WITH_MEAN_UNCERTAINTY":
        raise Refusal("convergence", "wrong convergence analysis")
    if provenance.get("stageId") != STAGE_ID or provenance.get("status") != "SOURCE_STAGE_TWO_FROZEN":
        raise Refusal("provenance", "wrong provenance")

    if proposal.get("sourceStageTwoScreeningRawSha256") != EXTERNAL_SCREENING_SHA or provenance.get("sourceStageTwoScreeningRawSha256") != EXTERNAL_SCREENING_SHA:
        raise Refusal("source-artifact-hash", "source screening artifact binding changed")
    if provenance.get("frozenScreeningCopyRawSha256") != digest(absolute["sourceScreening"]):
        raise Refusal("frozen-copy-hash", "frozen screening copy changed")
    if proposal.get("sourceConvergenceV2RawSha256") != digest(absolute["sourceConvergence"]) or provenance.get("sourceConvergenceV2RawSha256") != digest(absolute["sourceConvergence"]):
        raise Refusal("convergence-hash", "convergence binding changed")

    expected_provenance = {"sourceScientificRunId": 30863907633, "sourceAuthorizationRef": "5f7a5a7f2f9270328315edda12580cd72fda4c51", "sourceAuthorizationOrdinal": 3, "sourceExecutionKey": "cross-geometry-stage-two-v1:screening:3", "sourceScreeningArtifactId": 8875564303, "sourceScreeningArtifactName": "cross-geometry-stage-two-v1-screening", "sourceScreeningArtifactDigest": "sha256:3cbc3bfd2c0121de258b9c11d245e4e3d8f160e786a871a59515d405e64ee5de", "sourceAggregateArtifactId": 8875550285, "sourceAuditArtifactId": 8875557534, "sourceCaseArtifactCount": 16, "sourceCombinedCaseResultCount": 40, "sourceCombinedConfiguredMcPhotonsSum": 800_000_000, "authorizationCreated": False, "scientificExecution": False}
    stale_provenance = {key: (provenance.get(key), value) for key, value in expected_provenance.items() if provenance.get(key) != value}
    if stale_provenance:
        raise Refusal("provenance", "source run/artifact changed", stale_provenance)

    cases = proposal.get("cases")
    if not isinstance(cases, list) or len(cases) != 26 or [case.get("ordinal") for case in cases] != list(range(1, 27)):
        raise Refusal("cases", "case set changed")
    if sum(case.get("photonHistories", 0) for case in cases) != 520_000_000 or any(case.get("photonHistories") != 20_000_000 for case in cases):
        raise Refusal("photons", "photon accounting changed")
    if len({case.get("seed") for case in cases}) != 26:
        raise Refusal("seeds", "seeds duplicated")
    if {case.get("purpose") for case in cases} != {"continuation", "alis-reference-diagnostic"}:
        raise Refusal("purpose", "purpose set changed")
    expected_limits = {"maximumCases": 26, "maximumConfiguredMcPhotonsSum": 520_000_000, "maximumParallel": 16, "perCaseTimeoutSeconds": 900}
    if proposal.get("limits") != expected_limits:
        raise Refusal("limits", "execution limits changed", proposal.get("limits"))

    diagnostic = [case for case in cases if case.get("purpose") == "alis-reference-diagnostic"]
    continuation = [case for case in cases if case.get("purpose") == "continuation"]
    if len(diagnostic) != 18 or len(continuation) != 8:
        raise Refusal("design", "purpose accounting changed")
    if {case.get("groupId") for case in diagnostic} != {"g01-reference-bridge", "g06-late-opposite-high-aerosol"} or {case.get("alisSpectralImportanceSamplingNm") for case in diagnostic} != {500.0, 550.0, 600.0}:
        raise Refusal("design", "diagnostic design changed")
    for group in ("g01-reference-bridge", "g06-late-opposite-high-aerosol"):
        for reference_nm in (500.0, 550.0, 600.0):
            subset = [case for case in diagnostic if case.get("groupId") == group and case.get("alisSpectralImportanceSamplingNm") == reference_nm]
            if len(subset) != 3:
                raise Refusal("design", "diagnostic replicate count changed", {"group": group, "referenceNm": reference_nm, "count": len(subset)})

    disabled = {"schemaVersion": 1, "stageId": STAGE_ID, "authorized": False, "scientificExecution": False, "scientificDiagnostic": False, "authorizationOrdinal": 0, "consumed": False, "exactAuthorizationParentCommit": None, "exactAuthorizationCommit": None}
    if any(template.get(key) != value for key, value in disabled.items()):
        raise Refusal("template", "authorization template not disabled")
    if set(authorization) != set(template):
        raise Refusal("schema", "authorization schema changed")

    expected_authorization = {"schemaVersion": 1, "stageId": STAGE_ID, "authorized": True, "scientificExecution": True, "scientificDiagnostic": True, "successDoesNotAuthorizeProduction": True, "executionKey": execution_key, "batchId": proposal["batchId"], "proposalPath": rel["proposal"], "proposalRawSha256": digest(absolute["proposal"]), "sourceScreeningRawSha256": digest(absolute["sourceScreening"]), "sourceConvergenceV2RawSha256": digest(absolute["sourceConvergence"]), "sourceProvenanceRawSha256": digest(absolute["sourceProvenance"]), "authorizationTemplateRawSha256": digest(absolute["authorizationTemplate"]), "baseAdapterRawSha256": digest(absolute["baseAdapter"]), "executionAdapterRawSha256": digest(absolute["executionAdapter"]), "duplicateRunAuditRawSha256": digest(absolute["duplicateRunAudit"]), "runtimeProbeRawSha256": digest(absolute["runtimeProbe"]), "executionWorkflowRawSha256": digest(absolute["executionWorkflow"]), "runtimeLockRawSha256": digest(absolute["runtimeLock"]), "planRawSha256": digest(absolute["plan"]), "analysisDriverRawSha256": digest(absolute["analysisDriver"]), "convergenceModuleRawSha256": digest(absolute["convergenceModule"]), "executorRawSha256": digest(absolute["executor"]), "aggregateRawSha256": digest(absolute["aggregate"]), "auditRawSha256": digest(absolute["audit"]), "authorizationOrdinal": ordinal, "consumed": False, "exactAuthorizationCommit": None}
    stale_authorization = {key: (authorization.get(key), value) for key, value in expected_authorization.items() if authorization.get(key) != value}
    if stale_authorization:
        raise Refusal("auth", "authorization stale", stale_authorization)

    head = git(root, "rev-parse", "HEAD")
    parent = git(root, "rev-parse", "HEAD^")
    if head != authorization_ref:
        raise Refusal("ref", "HEAD differs from authorization ref", {"head": head, "input": authorization_ref})
    if authorization.get("exactAuthorizationParentCommit") != parent:
        raise Refusal("parent", "authorization parent mismatch")
    if one_purpose:
        changed = git(root, "diff", "--name-only", parent, head).splitlines()
        if changed != [rel["authorization"]]:
            raise Refusal("one-purpose", "authorization commit changed unexpected files", changed)

    return {"schemaVersion": 1, "stageId": STAGE_ID, "status": "AUTHORIZED", "batchId": proposal["batchId"], "executionKey": execution_key, "authorizationRef": head, "authorizationParentCommit": parent, "authorizationOrdinal": ordinal, "proposalRawSha256": digest(absolute["proposal"]), "executionAdapterRawSha256": digest(absolute["executionAdapter"]), "runtimeLockRawSha256": digest(absolute["runtimeLock"]), "executionWorkflowRawSha256": digest(absolute["executionWorkflow"]), "sourceScreeningRawSha256": digest(absolute["sourceScreening"]), "sourceScreeningArtifactRawSha256": EXTERNAL_SCREENING_SHA, "sourceConvergenceV2RawSha256": digest(absolute["sourceConvergence"]), "sourceProvenanceRawSha256": digest(absolute["sourceProvenance"]), "boundary": "authorized exact bounded final-convergence matrix; no production validity"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, default=Path("."))
    names = ["authorization", "authorization-template", "proposal", "source-screening", "source-convergence", "source-provenance", "base-adapter", "execution-adapter", "duplicate-run-audit", "runtime-probe", "execution-workflow", "runtime-lock", "plan", "analysis-driver", "convergence-module", "executor", "aggregate", "audit"]
    for name in names:
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--authorization-ref", required=True)
    parser.add_argument("--execution-key", required=True)
    parser.add_argument("--authorization-ordinal", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    mapping = {"authorization": "authorization", "authorization-template": "authorizationTemplate", "proposal": "proposal", "source-screening": "sourceScreening", "source-convergence": "sourceConvergence", "source-provenance": "sourceProvenance", "base-adapter": "baseAdapter", "execution-adapter": "executionAdapter", "duplicate-run-audit": "duplicateRunAudit", "runtime-probe": "runtimeProbe", "execution-workflow": "executionWorkflow", "runtime-lock": "runtimeLock", "plan": "plan", "analysis-driver": "analysisDriver", "convergence-module": "convergenceModule", "executor": "executor", "aggregate": "aggregate", "audit": "audit"}
    paths = {mapping[name]: getattr(args, name.replace("-", "_")) for name in names}
    try:
        result = validate(args.repository_root, paths, args.authorization_ref, args.execution_key, args.authorization_ordinal)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump(result))
        print(dump(result), end="")
        return 0
    except Refusal as exc:
        refusal = {"schemaVersion": 1, "stageId": STAGE_ID, "status": "REFUSED_BEFORE_SYNTAX_OR_SOLVER", "code": exc.code, "reason": exc.reason, "detail": exc.detail}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump(refusal))
        print(dump(refusal), end="", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
