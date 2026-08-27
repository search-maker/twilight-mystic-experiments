from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
from pathlib import Path
from typing import Any

STAGE = "aerosol-vertical-profile-sensitivity-v1"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
EXPECTED_SEED_CANONICAL = "a2e22b526dfad84d4f23c0ca8b143d028fddc7e55f78deb93a43e194ebd6c35e"
EXPECTED_ROWS_CANONICAL = "f22de8a9e30ba106759effb1170a5ca1d1e747cb2ac68293fa232dc7ed6ca683"


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
    expected_head: str,
) -> dict[str, Any]:
    if SHA40.fullmatch(expected_head) is None:
        raise Refusal("expected head must be a 40-character SHA")
    seed_mod = load_module("vertical_profile_seed_ledger_for_freshness_proof", stage_dir / "seed_ledger.py")
    ledger = seed_mod.validate_ledger()
    rows = seed_mod.derive_rows()

    if ledger.get("status") != "CANDIDATE_ONLY_ARTIFACT_ONLY_NOT_APPLIED_NOT_AUTHORIZED":
        raise Refusal("candidate ledger status drift")
    if ledger.get("trackedCandidateSeedLedger") is not False:
        raise Refusal("candidate seed literals unexpectedly tracked")
    if ledger.get("candidateSeedCount") != 72 or len(rows) != 72:
        raise Refusal("candidate seed cardinality drift")
    if ledger.get("candidateSeedCanonicalSha256") != EXPECTED_SEED_CANONICAL:
        raise Refusal("candidate seed canonical hash drift")
    if ledger.get("candidateRowsCanonicalSha256") != EXPECTED_ROWS_CANONICAL:
        raise Refusal("candidate row canonical hash drift")
    if EXPECTED_SEED_CANONICAL != canonical_sha256(ledger["candidateSeeds"]):
        raise Refusal("candidate seed canonical recomputation drift")
    if EXPECTED_ROWS_CANONICAL != canonical_sha256(rows):
        raise Refusal("candidate row canonical recomputation drift")
    if any(int(row.get("collisionCounter", -1)) != 0 for row in rows):
        raise Refusal("candidate within-ledger collision counter drift")

    if tracked_tree_report.get("candidateSeedCount") != 72:
        raise Refusal("tracked-tree candidate count drift")
    if tracked_tree_report.get("trackedTreeExternalCollisionCount") != 0:
        raise Refusal("tracked-tree candidate seed collision exists")
    if tracked_tree_report.get("exactHeadTrackedTreeByteScanPassed") is not True:
        raise Refusal("tracked-tree byte scan did not pass")
    if tracked_tree_report.get("requiredSelfLedgerPathsPresent") is not True:
        raise Refusal("tracked-tree empty self-ledger policy did not pass")
    if tracked_tree_report.get("selfLedgerHitCount") != 0:
        raise Refusal("candidate seed literal unexpectedly exists in tracked tree")

    global_report = repository_global_report
    if global_report.get("auditMode") != "review-freeze":
        raise Refusal("repository-global initial scan must use review-freeze mode")
    if global_report.get("candidateSeedCount") != 72:
        raise Refusal("repository-global candidate count drift")
    if global_report.get("repositoryGlobalCollisionCount") != 0:
        raise Refusal("repository-global candidate seed collision exists")
    if global_report.get("repositoryGlobalCollisionSurfaceScanPassed") is not True:
        raise Refusal("repository-global collision surface scan did not pass")
    if global_report.get("repositoryGlobalDoubleEnumerationStable") is not True:
        raise Refusal("repository-global double enumeration was not stable")
    if global_report.get("auditedBranchHeadMatchesRepositoryHead") is not True:
        raise Refusal("repository-global audited branch head mismatch")
    if global_report.get("repositoryHeadExpected") != expected_head:
        raise Refusal("repository-global expected head drift")
    if global_report.get("auditedBranchHeadShaObserved") != expected_head:
        raise Refusal("repository-global observed head drift")
    if global_report.get("priorReviewProofArtifactCount") != 0:
        raise Refusal("candidate seed review-proof identity already existed")
    if global_report.get("reviewProofIdentityFresh") is not True:
        raise Refusal("candidate seed review-proof identity is not fresh")
    if global_report.get("repositoryGlobalPostFenceCandidateSeedCollisionCount") not in (0, None):
        raise Refusal("post-fence candidate seed collision exists")

    return {
        "schemaVersion": 1,
        "stageId": f"{STAGE}-candidate-seed-freshness-review",
        "status": "PASS_CANDIDATE_SEEDS_FRESH_REVIEW_ONLY_NOT_ALLOCATED",
        "auditedHead": expected_head,
        "candidateSeedCount": 72,
        "candidateSeedCanonicalSha256": EXPECTED_SEED_CANONICAL,
        "candidateRowsCanonicalSha256": EXPECTED_ROWS_CANONICAL,
        "allCollisionCountersZero": True,
        "candidateSeedLiteralsTrackedInGit": False,
        "trackedFileCount": tracked_tree_report.get("trackedFileCount"),
        "trackedTreeExternalCollisionCount": 0,
        "exactHeadTrackedTreeByteScanPassed": True,
        "repositoryGlobalCollisionCount": 0,
        "repositoryGlobalCollisionSurfaceScanPassed": True,
        "repositoryGlobalDoubleEnumerationStable": True,
        "repositoryGlobalStableContextSha256": global_report.get("repositoryGlobalStableContextSha256"),
        "repositoryGlobalSnapshotFenceSha256": global_report.get("repositoryGlobalSnapshotFenceSha256"),
        "repositoryGlobalPostFenceArrivalCounts": global_report.get("repositoryGlobalPostFenceArrivalCounts") or {},
        "scientificOrdinalAllocated": False,
        "authorizationCreated": False,
        "dispatchCreated": False,
        "candidateSeedsAppliedToCases": False,
        "scientificExecutionAuthorized": False,
        "solverExecutionAuthorized": False,
        "resultOpeningAuthorized": False,
        "productionAuthorized": False,
        "authorizationTimeRecheckRequired": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-dir", type=Path, required=True)
    parser.add_argument("--tracked-tree-report", type=Path, required=True)
    parser.add_argument("--repository-global-report", type=Path, required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = build(
        args.stage_dir,
        json.loads(args.tracked_tree_report.read_text()),
        json.loads(args.repository_global_report.read_text()),
        args.expected_head,
    )
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
