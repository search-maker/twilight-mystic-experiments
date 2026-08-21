from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
from pathlib import Path
from typing import Any


STAGE = "aerosol-optical-property-sensitivity-v1"
SHA40 = re.compile(r"^[0-9a-f]{40}$")


class Refusal(RuntimeError):
    pass


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise Refusal(f"cannot import {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def build(
    stage_dir: Path,
    tracked_tree_report: dict[str, Any],
    repository_global_report: dict[str, Any],
    expected_main_head: str,
) -> dict[str, Any]:
    if SHA40.fullmatch(expected_main_head) is None:
        raise Refusal("expected main head must be a 40-character SHA")
    seed_mod = load_module("aops_seed_ledger_for_authorization_proof", stage_dir / "seed_ledger.py")
    ledger = seed_mod.validate_ledger()
    rows = seed_mod.derive_rows()

    if tracked_tree_report.get("candidateSeedCount") != 72:
        raise Refusal("tracked-tree candidate count drift")
    if tracked_tree_report.get("trackedTreeExternalCollisionCount") != 0:
        raise Refusal("tracked-tree candidate seed collision exists")
    if tracked_tree_report.get("exactHeadTrackedTreeByteScanPassed") is not True:
        raise Refusal("tracked-tree byte scan did not pass")
    if tracked_tree_report.get("requiredSelfLedgerPathsPresent") is not True:
        raise Refusal("required candidate self-ledger path missing")

    global_report = repository_global_report
    if global_report.get("auditMode") != "authorization-recheck":
        raise Refusal("repository-global scan must use authorization-recheck mode")
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
    if global_report.get("repositoryHeadExpected") != expected_main_head:
        raise Refusal("repository-global expected main head drift")
    if global_report.get("auditedBranchHeadShaObserved") != expected_main_head:
        raise Refusal("repository-global observed main head drift")
    if global_report.get("repositoryGlobalPostFenceCandidateSeedCollisionCount") not in (0, None):
        raise Refusal("post-fence candidate seed collision exists")

    seed_canonical = ledger.get("candidateSeedCanonicalSha256")
    rows_canonical = ledger.get("candidateRowsCanonicalSha256")
    if seed_canonical != canonical_sha256(ledger["candidateSeeds"]):
        raise Refusal("candidate seed canonical hash drift")
    if rows_canonical != canonical_sha256(rows):
        raise Refusal("candidate row canonical hash drift")
    if any(int(row.get("collisionCounter", -1)) != 0 for row in rows):
        raise Refusal("candidate seed collision counter drift")

    return {
        "schemaVersion": 1,
        "stageId": f"{STAGE}-seed-authorization-recheck",
        "status": "PASS_CANDIDATE_SEEDS_AUTHORIZATION_RECHECK_NOT_ALLOCATED",
        "auditedMainHead": expected_main_head,
        "auditedBranchHeadMatchesRepositoryHead": True,
        "candidateSeedCount": 72,
        "candidateSeedCanonicalSha256": seed_canonical,
        "candidateRowsCanonicalSha256": rows_canonical,
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
        "scientificOrdinalAllocated": False,
        "authorizationCreated": False,
        "dispatchCreated": False,
        "scientificExecutionAuthorized": False,
        "solverExecutionAuthorized": False,
        "resultOpeningAuthorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-dir", type=Path, required=True)
    parser.add_argument("--tracked-tree-report", type=Path, required=True)
    parser.add_argument("--repository-global-report", type=Path, required=True)
    parser.add_argument("--expected-main-head", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = build(
        args.stage_dir,
        json.loads(args.tracked_tree_report.read_text()),
        json.loads(args.repository_global_report.read_text()),
        args.expected_main_head,
    )
    args.output.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
