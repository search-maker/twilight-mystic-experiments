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

STAGE_ID = "cross-geometry-pilot-v1"
PURPOSE = "jerusalem-tishrei-direct-mystic-v1"
BATCH_ID = "jerusalem-tishrei-three-star-direct-mystic-v1"
EXECUTION_KEY = "jerusalem-tishrei-direct-mystic-v1:diagnostic:1"
AUTHORIZATION_ORDINAL = 1
APPLICATION_SHA = "e2d5b761206b6223526f6f79fcb0af5f6de3ba06"
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

    auth = load_json(abs_paths["authorization"]); ensure_disabled(auth)
    manifest = load_json(abs_paths["proposal"])
    evidence = load_json(abs_paths["evidence"])
    contract = load_json(abs_paths["analysisContract"])
    adapter = load_module(abs_paths["proposalAdapter"]); adapter.validate_manifest(manifest)
    if manifest.get("batchId") != BATCH_ID or manifest.get("proposalOnly") is not True or manifest.get("scientificExecution") is not False:
        raise ProposalFailure("manifest boundary changed")
    if len(manifest.get("geometries") or []) != 3 or len(manifest.get("cases") or []) != 12:
        raise ProposalFailure("manifest geometry/case count changed")
    if sum(int(c["photonHistories"]) for c in manifest["cases"]) != 240_000_000:
        raise ProposalFailure("manifest photon accounting changed")
    if (manifest.get("preregisteredEvent") or {}).get("threeStarSemantics", {}).get("fieldFactorBaseline") != 3.14:
        raise ProposalFailure("F=3.14 changed")
    if evidence.get("source", {}).get("artifactId") != 9612259358:
        raise ProposalFailure("event evidence source changed")
    if contract.get("analysisId") != "jerusalem-tishrei-direct-mystic-level-b-comparison-v1" or contract.get("scientificExecution") is not False:
        raise ProposalFailure("analysis contract changed")

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
