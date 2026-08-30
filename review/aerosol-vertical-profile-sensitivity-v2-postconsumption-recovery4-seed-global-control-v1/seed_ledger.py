from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

STAGE_ID = "aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery4"
NAMESPACE = "aerosol-vertical-profile-sensitivity-v2|postconsumption-recovery4-fresh-seed-control-v1|group-seed|sha256-v1"
MIN_SEED = 10_000_000
MAX_EXCLUSIVE = 2_147_483_647
SPAN = MAX_EXCLUSIVE - MIN_SEED
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SKELETON_PATH = ROOT / "review/aerosol-vertical-profile-sensitivity-v2-prereg/build_skeleton.py"
RECOVERY3_LEDGER_PATH = ROOT / "review/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3-seed-freshness-v1/seed_ledger.py"
EXPECTED_SKELETON_BLOB = "b4a4ab6917ad28f08d4980194f7b68f3961d5d59"
EXPECTED_SKELETON_CANONICAL = "a8d2d8f59aec01d82d8d98672152d00c11261660b0a69a59e2716c2edabd2b02"
EXPECTED_RECOVERY3_LEDGER_BLOB = "a4fc0b95c3627a310c0c17a1ae8b89701511b3b8"
EXPECTED_ORDINAL44_SEED_CANONICAL = "d2817b1ea4f2bdc8cb1842e565b099b015e4e28c5874482629fadc450069d9bf"
EXPECTED_SEED_CANONICAL = "ddded6b2d170ca2fac8d498bdba2887446c16995df0880d948fb2be00870b3de"
EXPECTED_ROWS_CANONICAL = "c439de417520b330c037e2628df02b6955f652563300aa5ef30477abf7661a98"


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


def consumed_seed_sets() -> tuple[set[int], set[int], set[int], set[int], dict[str, Any]]:
    if git_blob_sha1(RECOVERY3_LEDGER_PATH) != EXPECTED_RECOVERY3_LEDGER_BLOB:
        raise Refusal("consumed ordinal-44 recovery3 seed-ledger byte drift")
    # Recovery3 recursively validates consumed ordinals 41/42/43, including
    # ordinal-42 at its native historical worktree path via AVPS_ORDINAL42_LEDGER_PATH.
    mod = load_module(RECOVERY3_LEDGER_PATH, "avps_v2_consumed_ordinal44_recovery3_seed_ledger")
    set41, set42, set43 = mod.consumed_seed_sets()
    ledger = mod.validate_ledger()
    if ledger.get("candidateSeedCanonicalSha256") != EXPECTED_ORDINAL44_SEED_CANONICAL:
        raise Refusal("consumed ordinal-44 seed canonical drift")
    seeds = {int(x) for x in ledger.get("candidateSeeds", [])}
    if any(len(x) != 72 for x in (set41, set42, set43, seeds)):
        raise Refusal("consumed AVPS seed cardinality drift")
    all_sets = (set41, set42, set43, seeds)
    for i, left in enumerate(all_sets):
        for right in all_sets[i + 1:]:
            if left & right:
                raise Refusal("consumed AVPS seed sets unexpectedly overlap")
    for key in (
        "overlapWithConsumedOrdinal41SeedCount",
        "overlapWithConsumedOrdinal42SeedCount",
        "overlapWithConsumedOrdinal43SeedCount",
    ):
        if ledger.get(key) != 0:
            raise Refusal(f"recovery3 consumed-ledger invariant drift: {key}")
    return set41, set42, set43, seeds, ledger


def derive_rows() -> list[dict[str, Any]]:
    if git_blob_sha1(SKELETON_PATH) != EXPECTED_SKELETON_BLOB:
        raise Refusal("AVPS v2 recovery4 seed control refuses: prereg skeleton byte drift")
    skeleton = load_module(SKELETON_PATH, "avps_v2_recovery4_seed_skeleton").build_review_skeleton()
    if skeleton.get("canonicalSkeletonSha256") != EXPECTED_SKELETON_CANONICAL:
        raise Refusal("skeleton canonical identity drift")
    groups = skeleton.get("groups")
    if not isinstance(groups, list) or len(groups) != 72 or len({str(r.get('groupId')) for r in groups}) != 72:
        raise Refusal("72-group universe drift")
    if skeleton.get("seedCount") != 0 or skeleton.get("scientificOrdinal") is not None:
        raise Refusal("prereg skeleton already carries seed/ordinal")

    consumed41, consumed42, consumed43, consumed44, _ = consumed_seed_sets()
    consumed = consumed41 | consumed42 | consumed43 | consumed44
    rows: list[dict[str, Any]] = []
    used: set[int] = set()
    for group in groups:
        group_id = str(group["groupId"])
        if not group_id.startswith("avps-v2-"):
            raise Refusal(f"AVPS v2 recovery4 group namespace drift: {group_id}")
        counter = 0
        while True:
            material = f"{NAMESPACE}|groupId={group_id}|counter={counter}"
            digest = hashlib.sha256(material.encode()).hexdigest()
            seed = (int(digest[:16], 16) % SPAN) + MIN_SEED
            if seed not in used and seed not in consumed:
                break
            counter += 1
        if not MIN_SEED <= seed < MAX_EXCLUSIVE:
            raise Refusal("candidate seed escaped scanner-visible signed-32-bit domain")
        used.add(seed)
        rows.append({"groupId": group_id, "collisionCounter": counter, "derivationMaterialSha256": digest, "seed": seed})

    seeds = [int(row["seed"]) for row in rows]
    if len(rows) != 72 or len(used) != 72:
        raise Refusal("candidate seed cardinality/uniqueness drift")
    if any(int(row["collisionCounter"]) != 0 for row in rows):
        raise Refusal("unexpected recovery4 within-ledger/consumed collision counter")
    candidate_set = set(seeds)
    for label, consumed_set in ((41, consumed41), (42, consumed42), (43, consumed43), (44, consumed44)):
        if consumed_set & candidate_set:
            raise Refusal(f"fresh recovery4 candidate set overlaps consumed ordinal-{label} seeds")
    if canonical_sha256(seeds) != EXPECTED_SEED_CANONICAL:
        raise Refusal("recovery4 candidate seed canonical hash drift")
    if canonical_sha256(rows) != EXPECTED_ROWS_CANONICAL:
        raise Refusal("recovery4 candidate row canonical hash drift")
    return rows


def validate_ledger() -> dict[str, Any]:
    rows = derive_rows()
    seeds = [int(row["seed"]) for row in rows]
    _, _, _, _, r3 = consumed_seed_sets()
    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "POSTCONSUMPTION_RECOVERY4_CANDIDATE_ONLY_NOT_APPLIED_NOT_AUTHORIZED",
        "namespace": NAMESPACE,
        "candidateSeedCount": 72,
        "candidateSeeds": seeds,
        "candidateRows": rows,
        "candidateMinSeed": min(seeds),
        "candidateMaxSeed": max(seeds),
        "candidateSeedCanonicalSha256": EXPECTED_SEED_CANONICAL,
        "candidateRowsCanonicalSha256": EXPECTED_ROWS_CANONICAL,
        "consumedOrdinal41SeedCanonicalSha256": r3["consumedOrdinal41SeedCanonicalSha256"],
        "consumedOrdinal42SeedCanonicalSha256": r3["consumedOrdinal42SeedCanonicalSha256"],
        "consumedOrdinal43SeedCanonicalSha256": r3["consumedOrdinal43SeedCanonicalSha256"],
        "consumedOrdinal44SeedCanonicalSha256": EXPECTED_ORDINAL44_SEED_CANONICAL,
        "overlapWithConsumedOrdinal41SeedCount": 0,
        "overlapWithConsumedOrdinal42SeedCount": 0,
        "overlapWithConsumedOrdinal43SeedCount": 0,
        "overlapWithConsumedOrdinal44SeedCount": 0,
        "allCollisionCountersZero": True,
        "historicalOrdinal42LedgerValidatedAtNativePath": True,
        "trackedCandidateSeedLedger": False,
        "candidateSeedFreshnessProven": False,
        "candidateSeedsAppliedToCases": False,
        "scientificOrdinalAllocated": False,
        "authorizationCreated": False,
        "dispatchCreated": False,
        "scientificRuntimeSetupPerformed": False,
        "scientificExecutionPerformed": False,
        "solverExecutionAuthorized": False,
        "resultOpeningAuthorized": False,
        "levelBOpeningAuthorized": False,
        "protectedHoldoutOpeningAuthorized": False,
        "productionAuthorized": False,
        "taylorOrJerusalemFitAuthorized": False,
        "newMappingAuthorized": False,
    }


if __name__ == "__main__":
    x = validate_ledger()
    print(json.dumps({
        "status": "PASS_AVPS_V2_RECOVERY4_CANDIDATE_LEDGER_DETERMINISTIC_NOT_AUTHORIZED",
        "candidateSeedCount": x["candidateSeedCount"],
        "candidateSeedCanonicalSha256": x["candidateSeedCanonicalSha256"],
        "candidateRowsCanonicalSha256": x["candidateRowsCanonicalSha256"],
        "overlapWithConsumedOrdinal44SeedCount": x["overlapWithConsumedOrdinal44SeedCount"],
        "scientificOrdinalAllocated": x["scientificOrdinalAllocated"],
    }, sort_keys=True))
