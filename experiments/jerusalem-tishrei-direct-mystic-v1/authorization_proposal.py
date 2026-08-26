#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

STAGE_ID = "cross-geometry-pilot-v1"
PURPOSE = "jerusalem-tishrei-direct-mystic-v1"
BATCH_ID = "jerusalem-tishrei-three-star-direct-mystic-v1"
EXECUTION_KEY = "jerusalem-tishrei-direct-mystic-v1:diagnostic:1"
AUTHORIZATION_ORDINAL = 1
APPLICATION_SHA = "e2d5b761206b6223526f6f79fcb0af5f6de3ba06"
HUMAN_THRESHOLD_GIT_BLOB_SHA1 = "bb4cd0ff02159ecffe276022cec9d292c7a434a3"
DERIVED_CHANNELS_GIT_BLOB_SHA1 = "ccfd04d4c21188966351f4257e92893d7ce340c7"
EVIDENCE_ARTIFACT_ID = 9612259358
EVIDENCE_DIGEST = "sha256:d43120ad60d2e4a502023cd187bbeffecd6364d4edc975c14c84432c3c8097c5"
PACKAGE = Path("experiments/jerusalem-tishrei-direct-mystic-v1")
PATHS = {
    "authorization": PACKAGE / "authorization.cross-geometry.json",
    "proposal": PACKAGE / "manifest.proposal.json",
    "evidence": PACKAGE / "level-b-event-evidence.json",
    "analysisContract": PACKAGE / "analysis-contract.json",
    "proposalAdapter": Path("experiments/mystic-batch-v1/cross_geometry_adapter.py"),
    "executionAdapter": Path("experiments/mystic-batch-v1/cross_geometry_execution_adapter.py"),
    "executionWorkflow": Path(".github/workflows/jerusalem-tishrei-direct-mystic-v1-execution.yml"),
    "runtimeLock": Path("experiments/mystic-batch-v1/runtime-lock.micromamba.json"),
    "plan": Path("experiments/mystic-batch-v1/cross_geometry_execution_plan.py"),
    "analysisDriver": PACKAGE / "analyze_direct_sky.py",
    "visibilityHelper": PACKAGE / "compute_sky_only_visibility.mjs",
    "derivedChannels": Path("experiments/aerosol-family-challenge-v2/derived_channels.py"),
    "executor": Path("experiments/mystic-batch-v1/scientific_case_executor.py"),
    "aggregate": Path("experiments/mystic-batch-v1/scientific_aggregate.py"),
    "audit": Path("experiments/mystic-batch-v1/scientific_audit.py"),
    "authorizationProposalBuilder": PACKAGE / "authorization_proposal.py",
}
HUMAN_THRESHOLD = Path("scientific-tools/visibility-v3/human-threshold.mjs")


class ProposalFailure(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ProposalFailure(f"expected JSON object: {path}")
    return value


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def git_blob_sha1(root: Path, rel: Path) -> str:
    return git(root, "rev-parse", f"HEAD:{rel.as_posix()}")


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("tishrei_proposal_adapter", path)
    if spec is None or spec.loader is None:
        raise ProposalFailure(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def ensure_disabled(auth: dict[str, Any]) -> None:
    expected = {
        "stageId": STAGE_ID,
        "scientificPurpose": PURPOSE,
        "authorized": False,
        "scientificExecution": False,
        "scientificDiagnostic": False,
        "executionKey": None,
        "batchId": None,
        "authorizationOrdinal": 0,
        "consumed": False,
        "exactAuthorizationParentCommit": None,
        "exactAuthorizationCommit": None,
    }
    stale = {k: (auth.get(k), v) for k, v in expected.items() if auth.get(k) != v}
    if stale:
        raise ProposalFailure(f"active authorization is not disabled: {stale}")


def build(repo_root: Path, application_root: Path) -> dict[str, Any]:
    root = repo_root.resolve(); app = application_root.resolve()
    abs_paths = {k: root / v for k, v in PATHS.items()}
    for k, p in abs_paths.items():
        if not p.is_file():
            raise ProposalFailure(f"missing {k}: {p}")
    human = app / HUMAN_THRESHOLD
    if not human.is_file():
        raise ProposalFailure(f"missing frozen human threshold: {human}")
    if git(app, "rev-parse", "HEAD") != APPLICATION_SHA:
        raise ProposalFailure("application checkout is not exact frozen SHA")
    if git_blob_sha1(app, HUMAN_THRESHOLD) != HUMAN_THRESHOLD_GIT_BLOB_SHA1:
        raise ProposalFailure("frozen human-threshold Git blob drift")
    if git_blob_sha1(root, PATHS["derivedChannels"]) != DERIVED_CHANNELS_GIT_BLOB_SHA1:
        raise ProposalFailure("frozen derived-channels Git blob drift")

    auth = load_json(abs_paths["authorization"]); ensure_disabled(auth)
    manifest = load_json(abs_paths["proposal"])
    evidence = load_json(abs_paths["evidence"])
    contract = load_json(abs_paths["analysisContract"])
    adapter = load_module(abs_paths["proposalAdapter"]); adapter.validate_manifest(manifest)

    if manifest.get("batchId") != BATCH_ID or manifest.get("proposalOnly") is not True or manifest.get("scientificExecution") is not False:
        raise ProposalFailure("manifest boundary changed")
    geometries = manifest.get("geometries") or []
    cases = manifest.get("cases") or []
    if len(geometries) != 3 or len(cases) != 12:
        raise ProposalFailure("manifest geometry/case count changed")
    if len({c.get("caseId") for c in cases}) != 12:
        raise ProposalFailure("case IDs are not unique")
    if sum(int(c["photonHistories"]) for c in cases) != 240_000_000:
        raise ProposalFailure("manifest photon accounting changed")
    if Counter(c.get("method") for c in cases) != Counter({"alis": 6, "reference-vroom": 6}):
        raise ProposalFailure("manifest method counts changed")
    event = manifest.get("preregisteredEvent") or {}
    if event.get("threeStarSemantics", {}).get("fieldFactorBaseline") != 3.14:
        raise ProposalFailure("F=3.14 changed")
    if event.get("sunDepressionDeg") != 5.2416836635666755 or event.get("atmosphere", {}).get("aod550") != 0.22:
        raise ProposalFailure("frozen event geometry/AOD changed")

    source = evidence.get("source") or {}
    if source.get("artifactId") != EVIDENCE_ARTIFACT_ID or source.get("artifactDigest") != EVIDENCE_DIGEST:
        raise ProposalFailure("event evidence source changed")
    if evidence.get("applicationMainSha") != APPLICATION_SHA or evidence.get("event", {}).get("fieldFactor") != 3.14 or len(evidence.get("stars") or []) != 3:
        raise ProposalFailure("event evidence boundary changed")

    if contract.get("analysisId") != "jerusalem-tishrei-direct-mystic-level-b-comparison-v1" or contract.get("scientificExecution") is not False:
        raise ProposalFailure("analysis contract changed")
    inputs = contract.get("inputs") or {}
    if inputs.get("applicationMainSha") != APPLICATION_SHA:
        raise ProposalFailure("analysis application SHA changed")
    if inputs.get("humanThresholdGitBlobSha1") != HUMAN_THRESHOLD_GIT_BLOB_SHA1 or inputs.get("derivedChannelsGitBlobSha1") != DERIVED_CHANNELS_GIT_BLOB_SHA1:
        raise ProposalFailure("analysis Git-blob bindings changed")
    sky_only = contract.get("skyOnlyVisibilitySubstitution") or {}
    if sky_only.get("fieldFactor") != 3.14 or sky_only.get("branch") != "full" or sky_only.get("noParameterTuning") is not True:
        raise ProposalFailure("analysis human-threshold boundary changed")
    if contract.get("methodRoles", {}).get("alis", {}).get("expectedOutputGrid") != {"nodeCount": 8001, "startNm": 380.0, "stopNm": 780.0, "stepNm": 0.05}:
        raise ProposalFailure("ALIS full-spectrum grid contract changed")
    if not str(contract.get("methodRoles", {}).get("referenceVroom", {}).get("forbiddenUse", "")).startswith("do not derive"):
        raise ProposalFailure("reference-VROOM sparse-only boundary changed")
    boundary = contract.get("claimBoundary") or {}
    if boundary.get("noParameterTuning") is not True or boundary.get("fullSpectrumLevelBValidated") is not False or boundary.get("productionAuthorized") is not False:
        raise ProposalFailure("analysis claim boundary changed")

    source_commit = git(root, "rev-parse", "HEAD")
    proposed = {
        **auth,
        "authorized": True,
        "scientificExecution": True,
        "scientificDiagnostic": True,
        "executionKey": EXECUTION_KEY,
        "batchId": BATCH_ID,
        "proposalPath": PATHS["proposal"].as_posix(),
        "proposalRawSha256": raw_sha256(abs_paths["proposal"]),
        "levelBEvidenceRawSha256": raw_sha256(abs_paths["evidence"]),
        "analysisContractRawSha256": raw_sha256(abs_paths["analysisContract"]),
        "proposalAdapterRawSha256": raw_sha256(abs_paths["proposalAdapter"]),
        "executionAdapterRawSha256": raw_sha256(abs_paths["executionAdapter"]),
        "executionWorkflowRawSha256": raw_sha256(abs_paths["executionWorkflow"]),
        "runtimeLockRawSha256": raw_sha256(abs_paths["runtimeLock"]),
        "planRawSha256": raw_sha256(abs_paths["plan"]),
        "analysisDriverRawSha256": raw_sha256(abs_paths["analysisDriver"]),
        "visibilityHelperRawSha256": raw_sha256(abs_paths["visibilityHelper"]),
        "derivedChannelsRawSha256": raw_sha256(abs_paths["derivedChannels"]),
        "humanThresholdRawSha256": raw_sha256(human),
        "executorRawSha256": raw_sha256(abs_paths["executor"]),
        "aggregateRawSha256": raw_sha256(abs_paths["aggregate"]),
        "auditRawSha256": raw_sha256(abs_paths["audit"]),
        "authorizationProposalBuilderRawSha256": raw_sha256(abs_paths["authorizationProposalBuilder"]),
        "exactAuthorizationParentCommit": source_commit,
        "exactAuthorizationCommit": None,
        "authorizationOrdinal": AUTHORIZATION_ORDINAL,
        "consumed": False,
        "note": "Proposal only. A future reviewed one-purpose commit may replace only authorization.cross-geometry.json with this exact object. A separate workflow_dispatch with matching key/ref/ordinal is still required. No production authorization.",
    }
    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "scientificPurpose": PURPOSE,
        "status": "PROPOSAL_ONLY_NOT_AUTHORIZATION",
        "executionAuthorizedByProposal": False,
        "sourceCommit": source_commit,
        "applicationSha": APPLICATION_SHA,
        "humanThresholdGitBlobSha1": HUMAN_THRESHOLD_GIT_BLOB_SHA1,
        "derivedChannelsGitBlobSha1": DERIVED_CHANNELS_GIT_BLOB_SHA1,
        "proposedAuthorization": proposed,
        "boundary": "hash proposal only; no syntax check, uvspec process, MYSTIC solver, workflow dispatch, parameter tuning, or Pandora",
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repository-root", type=Path, default=Path("."))
    p.add_argument("--application-root", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    try:
        report = build(args.repository_root, args.application_root)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump(report)); print(dump(report), end=""); return 0
    except Exception as exc:
        print(dump({"schemaVersion":1,"stageId":STAGE_ID,"scientificPurpose":PURPOSE,"status":"REFUSED","reason":str(exc)}), end="", file=sys.stderr); return 2


if __name__ == "__main__":
    raise SystemExit(main())
