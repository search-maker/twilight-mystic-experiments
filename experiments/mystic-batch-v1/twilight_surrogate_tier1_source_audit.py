#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

STAGE_ID = "twilight-surrogate-tier-1-source-audit-v1"
PROPOSAL_STAGE_ID = "twilight-surrogate-tier-1-proposal-v1"
WORKFLOW_NAME = "Twilight surrogate tier-1 proposal"
WORKFLOW_PATH = ".github/workflows/twilight-surrogate-tier-1-proposal.yml"
ARTIFACT_NAME = "twilight-surrogate-tier-1-proposal-v1"
SHA256_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class SourceAuditError(RuntimeError):
    pass


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise SourceAuditError(f"expected JSON object: {path}")
    return value


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def anchor_partition(anchors: dict[str, Any]) -> tuple[list[str], list[str]]:
    rows = anchors.get("anchors")
    if not isinstance(rows, list) or len(rows) != 6 or any(not isinstance(row, dict) for row in rows):
        raise SourceAuditError("reference anchor rows missing")
    if any(row.get("eligibleForTraining") is not False for row in rows):
        raise SourceAuditError("reference anchor became eligible for training")
    hard = [row for row in rows if row.get("anchorStrength", "hard") == "hard"]
    soft = [row for row in rows if row.get("anchorStrength") == "soft-diagnostic"]
    if len(hard) + len(soft) != 6 or (len(hard), len(soft)) not in {(6, 0), (5, 1)}:
        raise SourceAuditError(f"unsupported hard/soft anchor partition: {len(hard)}/{len(soft)}")
    if any(row.get("eligibleForModelAcceptance", True) is not True for row in hard):
        raise SourceAuditError("hard anchor cannot gate model acceptance")
    if any(row.get("eligibleForModelAcceptance") is not False for row in soft):
        raise SourceAuditError("soft diagnostic became eligible for model acceptance")
    hard_ids = sorted(str(row.get("groupId")) for row in hard)
    soft_ids = sorted(str(row.get("groupId")) for row in soft)
    if len(set(hard_ids + soft_ids)) != 6:
        raise SourceAuditError("reference anchor IDs are missing or duplicated")
    return hard_ids, soft_ids


def audit(
    proposal_path: Path,
    anchors_path: Path,
    readiness_path: Path,
    source_run_path: Path,
    source_artifacts_path: Path,
) -> dict[str, Any]:
    proposal = load(proposal_path)
    anchors = load(anchors_path)
    readiness = load(readiness_path)
    source_run = load(source_run_path)
    source_artifacts = load(source_artifacts_path)

    required_run = {
        "status": "completed",
        "conclusion": "success",
        "run_attempt": 1,
        "head_branch": "main",
        "name": WORKFLOW_NAME,
        "path": WORKFLOW_PATH,
    }
    stale = {
        key: (source_run.get(key), expected)
        for key, expected in required_run.items()
        if source_run.get(key) != expected
    }
    if stale:
        raise SourceAuditError(f"source proposal workflow mismatch: {stale}")
    if source_run.get("event") not in {"workflow_run", "workflow_dispatch", "push"}:
        raise SourceAuditError(f"unsupported source proposal event: {source_run.get('event')}")
    run_id = source_run.get("id")
    head_sha = source_run.get("head_sha")
    if not isinstance(run_id, int) or run_id < 1:
        raise SourceAuditError("source proposal run ID invalid")
    if not isinstance(head_sha, str) or not re.fullmatch(r"[0-9a-f]{40}", head_sha):
        raise SourceAuditError("source proposal head SHA invalid")

    artifacts = source_artifacts.get("artifacts")
    if not isinstance(artifacts, list):
        raise SourceAuditError("source artifact listing missing")
    matches = [
        item for item in artifacts
        if isinstance(item, dict) and item.get("name") == ARTIFACT_NAME
    ]
    if len(matches) != 1:
        raise SourceAuditError(f"expected one {ARTIFACT_NAME} artifact, found {len(matches)}")
    artifact = matches[0]
    artifact_id = artifact.get("id")
    digest = artifact.get("digest")
    if not isinstance(artifact_id, int) or artifact_id < 1:
        raise SourceAuditError("source proposal artifact ID invalid")
    if artifact.get("expired") is not False:
        raise SourceAuditError("source proposal artifact expired")
    if not isinstance(digest, str) or not SHA256_DIGEST_RE.fullmatch(digest):
        raise SourceAuditError("source proposal artifact digest invalid")
    workflow_run = artifact.get("workflow_run")
    if isinstance(workflow_run, dict) and workflow_run.get("id") not in {None, run_id}:
        raise SourceAuditError("source proposal artifact belongs to another run")

    required_proposal = {
        "schemaVersion": 1,
        "stageId": PROPOSAL_STAGE_ID,
        "status": "PROPOSAL_ONLY_NOT_AUTHORIZATION",
        "mode": "scientific-proposal",
        "proposalOnly": True,
        "scientificExecution": False,
        "successDoesNotAuthorizeProduction": True,
        "observationValidationRequired": True,
        "authorizationRequired": True,
        "executionTierId": "tier-1-provisional",
        "geometryCount": 48,
        "caseCount": 96,
        "configuredMcPhotonsSum": 6_960_000_000,
        "method": "alis",
        "blocksPerGeometry": 2,
        "surrogateTrainingAutomaticallyAuthorized": False,
        "productionModelReady": False,
    }
    stale = {
        key: (proposal.get(key), expected)
        for key, expected in required_proposal.items()
        if proposal.get(key) != expected
    }
    if stale:
        raise SourceAuditError(f"tier-1 proposal mismatch: {stale}")
    cases = proposal.get("cases")
    geometries = proposal.get("geometries")
    if not isinstance(cases, list) or len(cases) != 96:
        raise SourceAuditError("tier-1 proposal case count changed")
    if not isinstance(geometries, list) or len(geometries) != 48:
        raise SourceAuditError("tier-1 proposal geometry count changed")
    if [case.get("ordinal") for case in cases] != list(range(1, 97)):
        raise SourceAuditError("tier-1 proposal case ordinals changed")
    if len({case.get("seed") for case in cases}) != 96:
        raise SourceAuditError("tier-1 proposal seeds are not unique")
    if sum(int(case.get("photonHistories", -1)) for case in cases) != 6_960_000_000:
        raise SourceAuditError("tier-1 proposal photon accounting changed")
    if any(
        case.get("method") != "alis"
        or case.get("executionTierId") != "tier-1-provisional"
        or case.get("role") not in {"surrogate-training", "internal-holdout"}
        or float(case.get("alisSpectralImportanceSamplingNm", -1)) not in {500.0, 550.0, 600.0}
        for case in cases
    ):
        raise SourceAuditError("tier-1 case contract changed")

    required_anchors = {
        "schemaVersion": 1,
        "stageId": "twilight-model-readiness-v1",
        "status": "REFERENCE_ANCHORS_VALIDATED",
        "anchorCount": 6,
        "trainingAutomaticallyAuthorized": False,
        "productionModelReady": False,
        "observationValidationRequired": True,
    }
    stale = {
        key: (anchors.get(key), expected)
        for key, expected in required_anchors.items()
        if anchors.get(key) != expected
    }
    if stale:
        raise SourceAuditError(f"reference anchors mismatch: {stale}")
    hard_ids, soft_ids = anchor_partition(anchors)
    if sorted(proposal.get("externalValidationAnchorIds", [])) != sorted(hard_ids + soft_ids):
        raise SourceAuditError("proposal external anchor IDs differ from validated anchors")
    if sorted(proposal.get("hardExternalValidationAnchorIds", hard_ids)) != hard_ids:
        raise SourceAuditError("proposal hard anchor IDs differ from validated anchors")
    if sorted(proposal.get("softDiagnosticAnchorIds", soft_ids)) != soft_ids:
        raise SourceAuditError("proposal soft diagnostic IDs differ from validated anchors")
    policy = proposal.get("referenceAnchorPolicy")
    if soft_ids:
        required_policy = {
            "allExcludedFromFitting": True,
            "hardAnchorsGateComputationalAcceptance": True,
            "softDiagnosticsAreReportOnly": True,
            "softDiagnosticsCannotCompensateForFailedPrecision": True,
        }
        if not isinstance(policy, dict) or any(policy.get(k) != v for k, v in required_policy.items()):
            raise SourceAuditError("soft diagnostic proposal policy changed")

    required_readiness = {
        "schemaVersion": 1,
        "stageId": PROPOSAL_STAGE_ID,
        "status": "TIER_1_PROPOSAL_READY_PENDING_SEPARATE_AUTHORIZATION",
        "referenceAnchorCount": 6,
        "geometryCount": 48,
        "caseCount": 96,
        "configuredMcPhotonsSum": 6_960_000_000,
        "scientificExecution": False,
        "executionAuthorized": False,
        "surrogateTrainingAuthorized": False,
        "productionModelReady": False,
        "observationValidationRequired": True,
    }
    stale = {
        key: (readiness.get(key), expected)
        for key, expected in required_readiness.items()
        if readiness.get(key) != expected
    }
    hard_count = readiness.get("hardValidationAnchorCount", len(hard_ids))
    soft_count = readiness.get("softDiagnosticAnchorCount", len(soft_ids))
    if hard_count != len(hard_ids) or soft_count != len(soft_ids):
        stale.update({
            "hardValidationAnchorCount": (hard_count, len(hard_ids)),
            "softDiagnosticAnchorCount": (soft_count, len(soft_ids)),
        })
    if stale:
        raise SourceAuditError(f"tier-1 readiness mismatch: {stale}")

    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "TIER_1_SOURCE_PROPOSAL_AUDITED",
        "sourceProposalRunId": run_id,
        "sourceProposalHeadSha": head_sha,
        "sourceProposalEvent": source_run["event"],
        "sourceProposalArtifactId": artifact_id,
        "sourceProposalArtifactName": ARTIFACT_NAME,
        "sourceProposalArtifactDigest": digest,
        "tier1ProposalRawSha256": raw_sha256(proposal_path),
        "validatedAnchorsRawSha256": raw_sha256(anchors_path),
        "tier1ReadinessRawSha256": raw_sha256(readiness_path),
        "geometryCount": 48,
        "caseCount": 96,
        "configuredMcPhotonsSum": 6_960_000_000,
        "referenceAnchorCount": 6,
        "hardValidationAnchorCount": len(hard_ids),
        "softDiagnosticAnchorCount": len(soft_ids),
        "scientificExecution": False,
        "executionAuthorized": False,
        "surrogateTrainingAuthorized": False,
        "productionModelReady": False,
        "observationValidationRequired": True,
        "boundary": (
            "audits the proposal artifact only; all anchors remain outside fitting; soft diagnostics "
            "are report-only; no syntax check, solver, model fitting, or authorization"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--proposal", type=Path, required=True)
    parser.add_argument("--anchors", type=Path, required=True)
    parser.add_argument("--readiness", type=Path, required=True)
    parser.add_argument("--source-run", type=Path, required=True)
    parser.add_argument("--source-artifacts", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = audit(
            args.proposal,
            args.anchors,
            args.readiness,
            args.source_run,
            args.source_artifacts,
        )
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
