from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

STAGE_ID = "aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery2"
NAMESPACE = "aerosol-vertical-profile-sensitivity-v2|postconsumption-recovery2|group-seed|sha256-v1"
MIN_SEED = 10_000_000
MAX_EXCLUSIVE = 2_147_483_647
SPAN = MAX_EXCLUSIVE - MIN_SEED
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SKELETON_PATH = ROOT / "review/aerosol-vertical-profile-sensitivity-v2-prereg/build_skeleton.py"
ORDINAL41_LEDGER_PATH = ROOT / "review/aerosol-vertical-profile-sensitivity-v2-seed-freshness/seed_ledger.py"
EXPECTED_SKELETON_BLOB = "b4a4ab6917ad28f08d4980194f7b68f3961d5d59"
EXPECTED_SKELETON_CANONICAL = "a8d2d8f59aec01d82d8d98672152d00c11261660b0a69a59e2716c2edabd2b02"
EXPECTED_ORDINAL41_LEDGER_BLOB = "c757507b05074340507df1ca6e76d35b44cf6090"
EXPECTED_ORDINAL42_LEDGER_BLOB = "491d1b6653bea0fcc5275269723a76aa1af52300"
EXPECTED_ORDINAL41_SEED_CANONICAL = "02f624d582e9b2caba6b920d65a5e8a8bc8fc1a2693623bc2f73abf5d3f706d2"
EXPECTED_ORDINAL42_SEED_CANONICAL = "a514212990a94a39d577bd038b631a600e18e4c0f750f781bbd7c99b897228a7"
EXPECTED_SEED_CANONICAL = "38c074fe01bd6d09fa7dc78af1ad323e2f42b606ca992c2950b8fc1f5b343a9f"
EXPECTED_ROWS_CANONICAL = "a88b28dcfaaeb354f294d1705a0f8ddbcd061083f277a038ab8c9dace44d9954"


class Refusal(RuntimeError):
    pass


def git_blob_sha1(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise Refusal(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def historical_ordinal42_ledger_path() -> Path:
    raw = os.environ.get("AVPS_ORDINAL42_LEDGER_PATH", "").strip()
    if not raw:
        raise Refusal("AVPS_ORDINAL42_LEDGER_PATH is required; consumed ordinal-42 ledger must be validated at its native historical worktree path")
    path = Path(raw).resolve()
    if not path.is_file():
        raise Refusal(f"historical ordinal-42 seed ledger not found at native path: {path}")
    return path


def consumed_seed_sets() -> tuple[set[int], set[int]]:
    if git_blob_sha1(ORDINAL41_LEDGER_PATH) != EXPECTED_ORDINAL41_LEDGER_BLOB:
        raise Refusal("ordinal-41 seed-ledger byte drift")
    ordinal42_path = historical_ordinal42_ledger_path()
    if git_blob_sha1(ordinal42_path) != EXPECTED_ORDINAL42_LEDGER_BLOB:
        raise Refusal("ordinal-42 historical seed-ledger byte drift")

    ordinal41 = load_module(ORDINAL41_LEDGER_PATH, "avps_v2_consumed_ordinal41_seed_ledger").validate_ledger()
    ordinal42 = load_module(ordinal42_path, "avps_v2_consumed_ordinal42_seed_ledger_native_history").validate_ledger()
    if ordinal41.get("candidateSeedCanonicalSha256") != EXPECTED_ORDINAL41_SEED_CANONICAL:
        raise Refusal("ordinal-41 consumed seed canonical drift")
    if ordinal42.get("candidateSeedCanonicalSha256") != EXPECTED_ORDINAL42_SEED_CANONICAL:
        raise Refusal("ordinal-42 consumed seed canonical drift")
    set41 = {int(x) for x in ordinal41.get("candidateSeeds", [])}
    set42 = {int(x) for x in ordinal42.get("candidateSeeds", [])}
    if len(set41) != 72 or len(set42) != 72:
        raise Refusal("consumed seed cardinality drift")
    if set41.intersection(set42):
        raise Refusal("historical ordinal-41/42 seed sets unexpectedly overlap")
    return set41, set42


def derive_rows() -> list[dict[str, Any]]:
    if git_blob_sha1(SKELETON_PATH) != EXPECTED_SKELETON_BLOB:
        raise Refusal("AVPS v2 recovery2 seed review refuses: prereg skeleton byte drift")
    skeleton = load_module(SKELETON_PATH, "avps_v2_recovery2_seed_skeleton").build_review_skeleton()
    if skeleton.get("canonicalSkeletonSha256") != EXPECTED_SKELETON_CANONICAL:
        raise Refusal("skeleton canonical identity drift")
    groups = skeleton.get("groups")
    if not isinstance(groups, list) or len(groups) != 72 or len({str(r.get('groupId')) for r in groups}) != 72:
        raise Refusal("72-group universe drift")
    if skeleton.get("seedCount") != 0 or skeleton.get("scientificOrdinal") is not None:
        raise Refusal("prereg skeleton already carries seed/ordinal")

    consumed41, consumed42 = consumed_seed_sets()
    rows: list[dict[str, Any]] = []
    used: set[int] = set()
    for group in groups:
        group_id = str(group["groupId"])
        if not group_id.startswith("avps-v2-"):
            raise Refusal(f"AVPS v2 recovery2 group namespace drift: {group_id}")
        counter = 0
        while True:
            material = f"{NAMESPACE}|groupId={group_id}|counter={counter}"
            digest = hashlib.sha256(material.encode()).hexdigest()
            seed = (int(digest[:16], 16) % SPAN) + MIN_SEED
            if seed not in used:
                break
            counter += 1
        if not MIN_SEED <= seed < MAX_EXCLUSIVE:
            raise Refusal("candidate seed escaped scanner-visible signed-32-bit domain")
        used.add(seed)
        rows.append({
            "groupId": group_id,
            "collisionCounter": counter,
            "derivationMaterialSha256": digest,
            "seed": seed,
        })

    seeds = [int(row["seed"]) for row in rows]
    if len(rows) != 72 or len(used) != 72:
        raise Refusal("candidate seed cardinality/uniqueness drift")
    if any(int(row["collisionCounter"]) != 0 for row in rows):
        raise Refusal("unexpected within-ledger collision counter")
    if consumed41.intersection(seeds):
        raise Refusal("fresh recovery2 candidate set overlaps consumed ordinal-41 seeds")
    if consumed42.intersection(seeds):
        raise Refusal("fresh recovery2 candidate set overlaps consumed ordinal-42 seeds")
    if canonical_sha256(seeds) != EXPECTED_SEED_CANONICAL:
        raise Refusal("recovery2 candidate seed canonical hash drift")
    if canonical_sha256(rows) != EXPECTED_ROWS_CANONICAL:
        raise Refusal("recovery2 candidate row canonical hash drift")
    return rows


def validate_ledger() -> dict[str, Any]:
    rows = derive_rows()
    seeds = [int(row["seed"]) for row in rows]
    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "POSTCONSUMPTION_RECOVERY2_CANDIDATE_ONLY_ARTIFACT_ONLY_NOT_APPLIED_NOT_AUTHORIZED",
        "namespace": NAMESPACE,
        "candidateSeedCount": 72,
        "candidateSeeds": seeds,
        "candidateRows": rows,
        "candidateMinSeed": min(seeds),
        "candidateMaxSeed": max(seeds),
        "candidateSeedCanonicalSha256": EXPECTED_SEED_CANONICAL,
        "candidateRowsCanonicalSha256": EXPECTED_ROWS_CANONICAL,
        "consumedOrdinal41SeedCanonicalSha256": EXPECTED_ORDINAL41_SEED_CANONICAL,
        "consumedOrdinal42SeedCanonicalSha256": EXPECTED_ORDINAL42_SEED_CANONICAL,
        "overlapWithConsumedOrdinal41SeedCount": 0,
        "overlapWithConsumedOrdinal42SeedCount": 0,
        "allCollisionCountersZero": True,
        "historicalOrdinal42LedgerValidatedAtNativePath": True,
        "trackedCandidateSeedLedger": False,
        "candidateSeedFreshnessProven": False,
        "candidateSeedsAppliedToCases": False,
        "scientificOrdinalAllocated": False,
        "authorizationCreated": False,
        "dispatchCreated": False,
        "solverExecutionAuthorized": False,
        "resultOpeningAuthorized": False,
        "productionAuthorized": False,
    }


if __name__ == "__main__":
    x = validate_ledger()
    print(json.dumps({
        "status": "PASS_AVPS_V2_POSTCONSUMPTION_RECOVERY2_CANDIDATE_LEDGER_DETERMINISTIC_NOT_AUTHORIZED",
        "candidateSeedCount": x["candidateSeedCount"],
        "candidateSeedCanonicalSha256": x["candidateSeedCanonicalSha256"],
        "candidateRowsCanonicalSha256": x["candidateRowsCanonicalSha256"],
        "overlapWithConsumedOrdinal41SeedCount": x["overlapWithConsumedOrdinal41SeedCount"],
        "overlapWithConsumedOrdinal42SeedCount": x["overlapWithConsumedOrdinal42SeedCount"],
        "historicalOrdinal42LedgerValidatedAtNativePath": x["historicalOrdinal42LedgerValidatedAtNativePath"],
    }, sort_keys=True))
