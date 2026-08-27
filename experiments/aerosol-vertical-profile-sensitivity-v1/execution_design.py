from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import re
from pathlib import Path
from typing import Any

STAGE = "aerosol-vertical-profile-sensitivity-v1"
HERE = Path(__file__).resolve().parent
SHA40 = re.compile(r"^[0-9a-f]{40}$")
EXPECTED_SEED_CANONICAL = "a2e22b526dfad84d4f23c0ca8b143d028fddc7e55f78deb93a43e194ebd6c35e"
EXPECTED_ROWS_CANONICAL = "f22de8a9e30ba106759effb1170a5ca1d1e747cb2ac68293fa232dc7ed6ca683"


class DesignRefusal(RuntimeError):
    pass


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise DesignRefusal(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def validate_seed_authorization_proof(proof: dict[str, Any], expected_main: str) -> None:
    if SHA40.fullmatch(expected_main or "") is None:
        raise DesignRefusal("expected main SHA invalid")
    if proof.get("stageId") != f"{STAGE}-seed-authorization-recheck":
        raise DesignRefusal("seed proof stage drift")
    if proof.get("status") != "PASS_CANDIDATE_SEEDS_AUTHORIZATION_RECHECK_NOT_ALLOCATED":
        raise DesignRefusal("authorization-time seed proof missing")
    if proof.get("auditedMainHead") != expected_main or proof.get("auditedBranchHeadMatchesRepositoryHead") is not True:
        raise DesignRefusal("seed proof exact-main binding drift")
    if proof.get("candidateSeedCount") != 72:
        raise DesignRefusal("candidate seed count drift")
    if proof.get("candidateSeedCanonicalSha256") != EXPECTED_SEED_CANONICAL:
        raise DesignRefusal("candidate seed canonical hash drift")
    if proof.get("candidateRowsCanonicalSha256") != EXPECTED_ROWS_CANONICAL:
        raise DesignRefusal("candidate row canonical hash drift")
    if proof.get("allCollisionCountersZero") is not True:
        raise DesignRefusal("candidate seed collision counter drift")
    if proof.get("candidateSeedLiteralsTrackedInGit") is not False:
        raise DesignRefusal("candidate seed literals unexpectedly tracked")
    if proof.get("exactHeadTrackedTreeByteScanPassed") is not True or proof.get("trackedTreeExternalCollisionCount") != 0:
        raise DesignRefusal("tracked-tree seed scan did not pass")
    if proof.get("repositoryGlobalCollisionSurfaceScanPassed") is not True or proof.get("repositoryGlobalCollisionCount") != 0:
        raise DesignRefusal("repository-global seed scan did not pass")
    if proof.get("repositoryGlobalDoubleEnumerationStable") is not True:
        raise DesignRefusal("repository-global enumeration unstable")
    if int(proof.get("priorReviewProofArtifactCount") or 0) < 1:
        raise DesignRefusal("prior review proof artifact missing")
    for key in (
        "scientificOrdinalAllocated", "authorizationCreated", "dispatchCreated",
        "candidateSeedsAppliedToCases", "scientificExecutionAuthorized",
        "solverExecutionAuthorized", "resultOpeningAuthorized", "productionAuthorized",
    ):
        if proof.get(key) is not False:
            raise DesignRefusal(f"seed proof crossed control boundary: {key}")


def build_review_execution_design(seed_proof: dict[str, Any], expected_main: str) -> dict[str, Any]:
    validate_seed_authorization_proof(seed_proof, expected_main)
    skeleton_mod = _load("avps_execution_candidate_for_seeded_design", HERE / "execution_candidate.py")
    seed_mod = _load("avps_seed_ledger_for_seeded_design", HERE / "seed_ledger.py")
    skeleton = skeleton_mod.build_review_execution_skeleton()
    ledger = seed_mod.validate_ledger()
    rows = seed_mod.derive_rows()
    if ledger.get("candidateSeedCanonicalSha256") != EXPECTED_SEED_CANONICAL:
        raise DesignRefusal("ledger seed canonical hash drift")
    if ledger.get("candidateRowsCanonicalSha256") != EXPECTED_ROWS_CANONICAL:
        raise DesignRefusal("ledger row canonical hash drift")
    seed_by_group = {str(row["groupId"]): int(row["seed"]) for row in rows}
    if len(seed_by_group) != 72:
        raise DesignRefusal("candidate group seed mapping drift")

    design = copy.deepcopy(skeleton)
    design["status"] = "CANDIDATE_SEEDED_DESIGN_FRESHNESS_PROVEN_REVIEW_ONLY"
    design["seedCount"] = 72
    design["candidateSeedFreshnessProven"] = True
    design["authorizationTimeSeedRecheckRequired"] = True
    design["seedAuthorizationProofAuditedMain"] = expected_main
    design["candidateSeedCanonicalSha256"] = EXPECTED_SEED_CANONICAL
    design["candidateRowsCanonicalSha256"] = EXPECTED_ROWS_CANONICAL
    design["scientificOrdinal"] = None
    for group in design["groups"]:
        gid = str(group["groupId"])
        if gid not in seed_by_group:
            raise DesignRefusal(f"missing candidate seed for group {gid}")
        group["candidateSeed"] = seed_by_group[gid]
        group["seedStatus"] = "CANDIDATE_FRESHNESS_PROVEN_REVIEW_ONLY"
        group["executionAuthorized"] = False
    for case in design["cases"]:
        gid = str(case["groupId"])
        case["seed"] = seed_by_group[gid]
        case["seedStatus"] = "CANDIDATE_FRESHNESS_PROVEN_REVIEW_ONLY"
        case["renderable"] = False
        case["executionAuthorized"] = False
        case["resultOpeningAuthorized"] = False
    if len(design["groups"]) != 72 or len(design["cases"]) != 360:
        raise DesignRefusal("seeded design cardinality drift")
    if any(group["candidateSeed"] is None for group in design["groups"]):
        raise DesignRefusal("seeded design contains unseeded group")
    if any(case["seed"] is None for case in design["cases"]):
        raise DesignRefusal("seeded design contains unseeded case")
    design.pop("canonicalDesignSha256", None)
    design["canonicalDesignSha256"] = canonical_sha256(design)
    return design
