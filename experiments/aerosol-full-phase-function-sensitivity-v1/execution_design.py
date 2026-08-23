from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path
from typing import Any

STAGE_DIR = Path(__file__).resolve().parent
STAGE = "aerosol-full-phase-function-sensitivity-v1"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
EXPECTED_SEED_CANONICAL = "d3a3b0f8ddd6f73160e021377c66a1dd6f16ea4f7c8687db7677caf84a033a2b"
EXPECTED_ROWS_CANONICAL = "72a53f2a86be3b0d380528d9ef39893864d1f2ac9e2306611ce0c4afc88ffee4"


class DesignRefusal(RuntimeError):
    pass


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise DesignRefusal(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def validate_seed_authorization_proof(proof: dict[str, Any], expected_main: str) -> None:
    if SHA40.fullmatch(expected_main) is None:
        raise DesignRefusal("expected main SHA invalid")
    if proof.get("stageId") != f"{STAGE}-seed-authorization-recheck":
        raise DesignRefusal("seed authorization proof stage drift")
    if proof.get("status") != "PASS_CANDIDATE_SEEDS_AUTHORIZATION_RECHECK_NOT_ALLOCATED":
        raise DesignRefusal("authorization-time seed proof missing")
    if proof.get("auditedMainHead") != expected_main or proof.get("auditedBranchHeadMatchesRepositoryHead") is not True:
        raise DesignRefusal("seed authorization proof exact-main binding drift")
    if proof.get("candidateSeedCount") != 72:
        raise DesignRefusal("candidate seed count drift")
    if proof.get("candidateSeedCanonicalSha256") != EXPECTED_SEED_CANONICAL:
        raise DesignRefusal("candidate seed canonical hash drift")
    if proof.get("candidateRowsCanonicalSha256") != EXPECTED_ROWS_CANONICAL:
        raise DesignRefusal("candidate rows canonical hash drift")
    if proof.get("allCollisionCountersZero") is not True:
        raise DesignRefusal("candidate seed collision counter drift")
    if proof.get("exactHeadTrackedTreeByteScanPassed") is not True:
        raise DesignRefusal("tracked-tree seed scan did not pass")
    if proof.get("trackedTreeExternalCollisionCount") != 0:
        raise DesignRefusal("tracked-tree seed collision exists")
    if proof.get("repositoryGlobalCollisionSurfaceScanPassed") is not True:
        raise DesignRefusal("repository-global seed scan did not pass")
    if proof.get("repositoryGlobalCollisionCount") != 0:
        raise DesignRefusal("repository-global seed collision exists")
    if proof.get("repositoryGlobalDoubleEnumerationStable") is not True:
        raise DesignRefusal("repository-global seed enumeration unstable")
    for key in (
        "scientificOrdinalAllocated", "authorizationCreated", "dispatchCreated",
        "scientificExecutionAuthorized", "solverExecutionAuthorized", "resultOpeningAuthorized",
    ):
        if proof.get(key) is not False:
            raise DesignRefusal(f"seed proof crossed control boundary: {key}")


def build_review_execution_design(seed_proof: dict[str, Any], expected_main: str) -> dict[str, Any]:
    validate_seed_authorization_proof(seed_proof, expected_main)
    seed_mod = _load("afpf_seed_ledger_for_execution_design", STAGE_DIR / "seed_ledger.py")
    transport = _load("afpf_execution_transport_for_execution_design", STAGE_DIR / "execution_transport.py")
    ledger = seed_mod.validate_ledger()
    rows = seed_mod.derive_rows()
    if ledger.get("candidateSeedCanonicalSha256") != EXPECTED_SEED_CANONICAL:
        raise DesignRefusal("ledger seed canonical hash drift")
    if ledger.get("candidateRowsCanonicalSha256") != EXPECTED_ROWS_CANONICAL:
        raise DesignRefusal("ledger row canonical hash drift")
    seed_by_group = {str(row["groupId"]): int(row["seed"]) for row in rows}
    if len(seed_by_group) != 72:
        raise DesignRefusal("candidate group seed mapping drift")
    design = transport.bind_unproven_candidate_seed_map(seed_by_group)
    design["status"] = "CANDIDATE_SEEDED_DESIGN_FRESHNESS_PROVEN_REVIEW_ONLY"
    design["candidateSeedFreshnessProven"] = True
    design["authorizationTimeSeedRecheckRequired"] = True
    design["seedAuthorizationProofAuditedMain"] = expected_main
    design["candidateSeedCanonicalSha256"] = EXPECTED_SEED_CANONICAL
    design["candidateRowsCanonicalSha256"] = EXPECTED_ROWS_CANONICAL
    for row in design["groups"]:
        row["seedStatus"] = "CANDIDATE_FRESHNESS_PROVEN_REVIEW_ONLY"
    for row in design["cases"]:
        row["seedStatus"] = "CANDIDATE_FRESHNESS_PROVEN_REVIEW_ONLY"
    design.pop("canonicalDesignSha256", None)
    design["canonicalDesignSha256"] = canonical_sha256(design)
    transport.validate_future_fresh_seeded_design(design)
    return design
