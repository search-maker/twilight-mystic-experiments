from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
from pathlib import Path
from typing import Any

STAGE = "aerosol-full-phase-function-sensitivity-v1"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
AUDIT_MODES = {"review-freeze", "authorization-recheck"}


class Refusal(RuntimeError):
    pass


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise Refusal(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def build(
    stage_dir: Path,
    tracked_tree_report: dict[str, Any],
    repository_global_report: dict[str, Any],
    expected_branch_name: str,
    expected_head: str,
    audit_mode: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if audit_mode not in AUDIT_MODES:
        raise Refusal("unsupported seed freshness audit mode")
    if not expected_branch_name:
        raise Refusal("expected audited branch name required")
    if SHA40.fullmatch(expected_head) is None:
        raise Refusal("expected audited head must be a 40-character SHA")

    seed_mod = load_module("afpf_seed_ledger_for_freshness", stage_dir / "seed_ledger.py")
    transport = load_module("afpf_execution_transport_for_seed_freshness", stage_dir / "execution_transport.py")
    ledger = seed_mod.validate_ledger()
    rows = seed_mod.derive_rows()

    if ledger.get("status") != "CANDIDATE_ONLY_NOT_APPLIED_NOT_AUTHORIZED":
        raise Refusal("candidate seed ledger status drift")
    if ledger.get("candidateSeedCount") != 72 or len(ledger.get("candidateSeeds", [])) != 72:
        raise Refusal("candidate seed ledger cardinality drift")
    if len(set(ledger["candidateSeeds"])) != 72:
        raise Refusal("candidate seed ledger uniqueness drift")
    if any(isinstance(seed, bool) or not isinstance(seed, int) or not seed_mod.MIN_SEED <= seed < seed_mod.MAX_EXCLUSIVE for seed in ledger["candidateSeeds"]):
        raise Refusal("candidate seed outside frozen scanner-visible domain")
    if ledger.get("candidateSeedCanonicalSha256") != canonical_sha256(ledger["candidateSeeds"]):
        raise Refusal("candidate seed canonical hash drift")
    if ledger.get("candidateRowsCanonicalSha256") != canonical_sha256(rows):
        raise Refusal("candidate row canonical hash drift")
    if any(int(row.get("collisionCounter", -1)) != 0 for row in rows):
        raise Refusal("candidate seed within-ledger collision counter drift")

    if tracked_tree_report.get("candidateSeedCount") != 72:
        raise Refusal("tracked-tree candidate count drift")
    if tracked_tree_report.get("trackedTreeExternalCollisionCount") != 0:
        raise Refusal("tracked-tree candidate seed collision exists")
    if tracked_tree_report.get("exactHeadTrackedTreeByteScanPassed") is not True:
        raise Refusal("tracked-tree byte scan did not pass")
    if tracked_tree_report.get("requiredSelfLedgerPathsPresent") is not True:
        raise Refusal("required candidate self-ledger path missing")
    if tracked_tree_report.get("futureEvidenceSelfLedgerPathCountPresent") not in (0, None):
        raise Refusal("future seed-evidence self-ledger path unexpectedly already tracked")

    global_report = repository_global_report
    if global_report.get("auditMode") != audit_mode:
        raise Refusal("repository-global scan audit mode drift")
    if global_report.get("candidateSeedCount") != 72:
        raise Refusal("repository-global candidate count drift")
    if global_report.get("repositoryGlobalCollisionCount") != 0:
        raise Refusal("repository-global candidate seed collision exists")
    if global_report.get("repositoryGlobalCollisionSurfaceScanPassed") is not True:
        raise Refusal("repository-global collision surface scan did not pass")
    if global_report.get("repositoryGlobalDoubleEnumerationStable") is not True:
        raise Refusal("repository-global double enumeration was not stable")
    if global_report.get("repositoryGlobalPostFenceCandidateSeedCollisionCount") not in (0, None):
        raise Refusal("post-fence candidate seed collision exists")
    if global_report.get("auditedBranchName") != expected_branch_name:
        raise Refusal("repository-global audited branch name drift")
    if global_report.get("auditedBranchHeadMatchesRepositoryHead") is not True:
        raise Refusal("repository-global audited branch head mismatch")
    if global_report.get("repositoryHeadExpected") != expected_head:
        raise Refusal("repository-global expected head drift")
    if global_report.get("auditedBranchHeadShaObserved") != expected_head:
        raise Refusal("repository-global observed head drift")
    if audit_mode == "review-freeze":
        if global_report.get("priorReviewProofArtifactCount") != 0:
            raise Refusal("review-freeze proof artifact identity was already consumed")
        if global_report.get("reviewProofIdentityFresh") is not True:
            raise Refusal("review-freeze proof artifact identity is not fresh")

    seed_by_group = {str(row["groupId"]): int(row["seed"]) for row in rows}
    design = transport.bind_unproven_candidate_seed_map(seed_by_group)
    design["status"] = "CANDIDATE_SEEDED_DESIGN_FRESHNESS_PROVEN_REVIEW_ONLY"
    design["candidateSeedFreshnessProven"] = True
    design["authorizationTimeSeedRecheckRequired"] = True
    for row in design["groups"]:
        row["seedStatus"] = "CANDIDATE_FRESHNESS_PROVEN_REVIEW_ONLY"
    for row in design["cases"]:
        row["seedStatus"] = "CANDIDATE_FRESHNESS_PROVEN_REVIEW_ONLY"
    design.pop("canonicalDesignSha256", None)
    design["canonicalDesignSha256"] = transport.canonical_sha256(design)
    transport.validate_future_fresh_seeded_design(design)

    proof = {
        "schemaVersion": 1,
        "stageId": f"{STAGE}-seed-freshness",
        "status": "PASS_CANDIDATE_SEEDS_REVIEW_FREEZE_NOT_AUTHORIZED" if audit_mode == "review-freeze" else "PASS_CANDIDATE_SEEDS_AUTHORIZATION_RECHECK_NOT_ALLOCATED",
        "auditMode": audit_mode,
        "auditedBranchName": expected_branch_name,
        "auditedHead": expected_head,
        "auditedBranchHeadMatchesRepositoryHead": True,
        "candidateSeedCount": 72,
        "candidateSeedCanonicalSha256": ledger["candidateSeedCanonicalSha256"],
        "candidateRowsCanonicalSha256": ledger["candidateRowsCanonicalSha256"],
        "candidateSeedMinimumInclusive": seed_mod.MIN_SEED,
        "candidateSeedMaximumExclusive": seed_mod.MAX_EXCLUSIVE,
        "allCandidateSeedsScannerVisible": True,
        "allCollisionCountersZero": True,
        "trackedFileCount": tracked_tree_report.get("trackedFileCount"),
        "trackedTreeExternalCollisionCount": 0,
        "exactHeadTrackedTreeByteScanPassed": True,
        "repositoryGlobalCollisionCount": 0,
        "repositoryGlobalCollisionSurfaceScanPassed": True,
        "repositoryGlobalDoubleEnumerationStable": True,
        "repositoryGlobalStableContextSha256": global_report.get("repositoryGlobalStableContextSha256"),
        "repositoryGlobalSnapshotFenceSha256": global_report.get("repositoryGlobalSnapshotFenceSha256"),
        "repositoryGlobalPostFenceArrivalCounts": global_report.get("repositoryGlobalPostFenceArrivalCounts") or {},
        "seededDesignCanonicalSha256": design["canonicalDesignSha256"],
        "seededDesignCaseCount": design["caseCount"],
        "seededDesignGroupCount": design["groupCount"],
        "seededDesignStatesPerGroup": design["statesPerGroup"],
        "candidateSeedsAppliedOnlyToReviewDesignArtifact": True,
        "authorizationTimeRepositoryGlobalRecheckRequired": True,
        "scientificOrdinalAllocated": False,
        "authorizationCreated": False,
        "dispatchCreated": False,
        "scientificExecutionAuthorized": False,
        "solverExecutionAuthorized": False,
        "resultOpeningAuthorized": False,
        "renderable": False,
    }
    proof["proofCanonicalSha256"] = canonical_sha256(proof)
    return proof, design


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-dir", type=Path, required=True)
    parser.add_argument("--tracked-tree-report", type=Path, required=True)
    parser.add_argument("--repository-global-report", type=Path, required=True)
    parser.add_argument("--expected-branch-name", required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--audit-mode", choices=sorted(AUDIT_MODES), required=True)
    parser.add_argument("--output-proof", type=Path, required=True)
    parser.add_argument("--output-design", type=Path, required=True)
    args = parser.parse_args()
    proof, design = build(
        args.stage_dir,
        json.loads(args.tracked_tree_report.read_text()),
        json.loads(args.repository_global_report.read_text()),
        args.expected_branch_name,
        args.expected_head,
        args.audit_mode,
    )
    args.output_proof.write_text(json.dumps(proof, indent=2, sort_keys=True) + "\n")
    args.output_design.write_text(json.dumps(design, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
