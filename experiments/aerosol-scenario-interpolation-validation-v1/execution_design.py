from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path
from typing import Any

STAGE_DIR = Path(__file__).resolve().parent
STAGE = "aerosol-scenario-interpolation-validation-v1"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
EXPECTED_SEED_CANONICAL = "cd04e0f7a206ca7fd49f3b00eae8de6d49ba8dc1427c21e5c7530adf03837040"
EXPECTED_ROWS_CANONICAL = "d88da58b6fe896b8324df224c5e849399b770783d4d63bb2bc4a7b01aa844e8b"


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
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def validate_freshness_proof(proof: dict[str, Any], expected_head: str) -> None:
    if SHA40.fullmatch(expected_head or "") is None:
        raise DesignRefusal("expected audited head invalid")
    if proof.get("stageId") != f"{STAGE}-preauthorization-freshness-proof":
        raise DesignRefusal("ASIV freshness proof stage drift")
    if proof.get("status") != "PASS_ASIV_SEED_AND_GEOMETRY_AUTHORIZATION_RECHECK_NOT_ALLOCATED":
        raise DesignRefusal("ASIV seed+geometry freshness proof missing")
    if proof.get("auditedMainHead") != expected_head:
        raise DesignRefusal("ASIV freshness proof exact-head drift")
    if proof.get("candidateSeedCount") != 24 or proof.get("holdoutGeometryCount") != 8:
        raise DesignRefusal("ASIV freshness proof cardinality drift")
    if proof.get("candidateSeedCanonicalSha256") != EXPECTED_SEED_CANONICAL:
        raise DesignRefusal("candidate seed canonical hash drift")
    if proof.get("candidateRowsCanonicalSha256") != EXPECTED_ROWS_CANONICAL:
        raise DesignRefusal("candidate row canonical hash drift")
    if proof.get("allCollisionCountersZero") is not True:
        raise DesignRefusal("candidate collision counter drift")
    for key in ("trackedTreeExternalCollisionCount", "repositoryGlobalCollisionCount", "trackedGeometryCollisionCount", "metadataGeometryCollisionCount"):
        if proof.get(key) != 0:
            raise DesignRefusal(f"freshness collision exists: {key}")
    if proof.get("repositoryGlobalDoubleEnumerationStable") is not True:
        raise DesignRefusal("repository-global seed enumeration unstable")
    for key in (
        "scientificOrdinalAllocated", "authorizationCreated", "dispatchCreated",
        "scientificExecutionAuthorized", "solverExecutionAuthorized", "resultOpeningAuthorized",
    ):
        if proof.get(key) is not False:
            raise DesignRefusal(f"freshness proof crossed control boundary: {key}")


def build_review_execution_design(freshness_proof: dict[str, Any], expected_head: str) -> dict[str, Any]:
    validate_freshness_proof(freshness_proof, expected_head)
    seed_mod = _load("asiv_seed_ledger_for_execution_design", STAGE_DIR / "seed_ledger.py")
    transport = _load("asiv_execution_transport_for_execution_design", STAGE_DIR / "execution_transport.py")
    ledger = seed_mod.validate()
    rows = seed_mod.derive_rows()
    if ledger.get("candidateSeedCanonicalSha256") != EXPECTED_SEED_CANONICAL or ledger.get("candidateRowsCanonicalSha256") != EXPECTED_ROWS_CANONICAL:
        raise DesignRefusal("frozen ASIV candidate ledger hash drift")
    seed_by_group = {str(row["groupId"]): int(row["seed"]) for row in rows}
    if len(seed_by_group) != 24 or len(set(seed_by_group.values())) != 24:
        raise DesignRefusal("ASIV candidate group-seed mapping drift")
    design = transport.build_seedless_design(STAGE_DIR.parents[1])
    design["status"] = "CANDIDATE_SEEDED_DESIGN_FRESHNESS_PROVEN_REVIEW_ONLY"
    design["candidateSeedsAllocated"] = True
    design["candidateSeedFreshnessProven"] = True
    design["authorizationTimeSeedRecheckRequired"] = True
    design["authorizationTimeGeometryRecheckRequired"] = True
    design["freshnessProofAuditedHead"] = expected_head
    design["candidateSeedCanonicalSha256"] = EXPECTED_SEED_CANONICAL
    design["candidateRowsCanonicalSha256"] = EXPECTED_ROWS_CANONICAL
    for group in design["groups"]:
        gid = str(group["groupId"])
        group["seed"] = seed_by_group[gid]
        group["seedStatus"] = "CANDIDATE_FRESHNESS_PROVEN_REVIEW_ONLY"
    for case in design["cases"]:
        case["seed"] = seed_by_group[str(case["groupId"])]
        case["seedStatus"] = "CANDIDATE_FRESHNESS_PROVEN_REVIEW_ONLY"
    design.pop("canonicalDesignSha256", None)
    design["canonicalDesignSha256"] = canonical_sha256(design)
    transport.validate_authorized_design(STAGE_DIR.parents[1], design)
    return design
