from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

STAGE_ID = "aerosol-vertical-profile-sensitivity-v2-postconsumption-successor-preauth-v1"
NAMESPACE = "aerosol-vertical-profile-sensitivity-v2|postconsumption-successor-fresh-seed-control-v1|group-seed|sha256-v1"
MIN_SEED = 10_000_000
MAX_EXCLUSIVE = 2_147_483_647
SPAN = MAX_EXCLUSIVE - MIN_SEED
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SKELETON_PATH = ROOT / "review/aerosol-vertical-profile-sensitivity-v2-prereg/build_skeleton.py"
RECOVERY4_LEDGER_PATH = ROOT / "review/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery4-seed-global-control-v1/seed_ledger.py"
EXPECTED_SKELETON_BLOB = "b4a4ab6917ad28f08d4980194f7b68f3961d5d59"
EXPECTED_SKELETON_CANONICAL = "a8d2d8f59aec01d82d8d98672152d00c11261660b0a69a59e2716c2edabd2b02"
EXPECTED_RECOVERY4_LEDGER_BLOB = "16af5c68ae7e3cfc0cfbef4c8e2022517bf2ae91"
EXPECTED_ORDINAL45_SEED_CANONICAL = "ddded6b2d170ca2fac8d498bdba2887446c16995df0880d948fb2be00870b3de"
EXPECTED_SEED_CANONICAL = "6ace6be3b0298f3fa35cdc522a3375c0480a4154371c15bbbf4a3f930a5d17cd"
EXPECTED_ROWS_CANONICAL = "30c0c1e38755f2c04b59448569c15c38a8b3b850c73d235ea38ce8f880d30f8b"


class Refusal(RuntimeError):
    pass


def git_blob_sha1(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise Refusal(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def consumed_seed_sets() -> tuple[set[int], set[int], set[int], set[int], set[int], dict[str, Any]]:
    if git_blob_sha1(RECOVERY4_LEDGER_PATH) != EXPECTED_RECOVERY4_LEDGER_BLOB:
        raise Refusal("consumed ordinal-45 Recovery4 seed-ledger byte drift")
    recovery4 = load_module(RECOVERY4_LEDGER_PATH, "avps_v2_consumed_ordinal45_recovery4_seed_ledger")
    set41, set42, set43, set44, _ = recovery4.consumed_seed_sets()
    ledger45 = recovery4.validate_ledger()
    if ledger45.get("candidateSeedCanonicalSha256") != EXPECTED_ORDINAL45_SEED_CANONICAL:
        raise Refusal("consumed ordinal-45 seed canonical drift")
    set45 = {int(x) for x in ledger45.get("candidateSeeds", [])}
    all_sets = (set41, set42, set43, set44, set45)
    if any(len(x) != 72 for x in all_sets):
        raise Refusal("consumed AVPS seed cardinality drift")
    for index, left in enumerate(all_sets):
        for right in all_sets[index + 1 :]:
            if left & right:
                raise Refusal("consumed AVPS seed sets unexpectedly overlap")
    for ordinal in (41, 42, 43, 44):
        key = f"overlapWithConsumedOrdinal{ordinal}SeedCount"
        if ledger45.get(key) != 0:
            raise Refusal(f"Recovery4 consumed-ledger invariant drift: {key}")
    return set41, set42, set43, set44, set45, ledger45


def derive_rows() -> list[dict[str, Any]]:
    if git_blob_sha1(SKELETON_PATH) != EXPECTED_SKELETON_BLOB:
        raise Refusal("successor seed control refuses: prereg skeleton byte drift")
    skeleton = load_module(SKELETON_PATH, "avps_v2_successor_seed_skeleton").build_review_skeleton()
    if skeleton.get("canonicalSkeletonSha256") != EXPECTED_SKELETON_CANONICAL:
        raise Refusal("skeleton canonical identity drift")
    groups = skeleton.get("groups")
    if not isinstance(groups, list) or len(groups) != 72 or len({str(row.get('groupId')) for row in groups}) != 72:
        raise Refusal("72-group universe drift")
    if skeleton.get("seedCount") != 0 or skeleton.get("scientificOrdinal") is not None:
        raise Refusal("prereg skeleton already carries seed/ordinal")

    consumed41, consumed42, consumed43, consumed44, consumed45, _ = consumed_seed_sets()
    consumed = consumed41 | consumed42 | consumed43 | consumed44 | consumed45
    rows: list[dict[str, Any]] = []
    used: set[int] = set()
    for group in groups:
        group_id = str(group["groupId"])
        if not group_id.startswith("avps-v2-"):
            raise Refusal(f"AVPS v2 successor group namespace drift: {group_id}")
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
        rows.append(
            {
                "groupId": group_id,
                "collisionCounter": counter,
                "derivationMaterialSha256": digest,
                "seed": seed,
            }
        )

    seeds = [int(row["seed"]) for row in rows]
    if len(rows) != 72 or len(used) != 72:
        raise Refusal("candidate seed cardinality/uniqueness drift")
    if any(int(row["collisionCounter"]) != 0 for row in rows):
        raise Refusal("unexpected successor within-ledger/consumed collision counter")
    candidate = set(seeds)
    for label, consumed_set in (
        (41, consumed41),
        (42, consumed42),
        (43, consumed43),
        (44, consumed44),
        (45, consumed45),
    ):
        if consumed_set & candidate:
            raise Refusal(f"fresh successor candidate set overlaps consumed ordinal-{label} seeds")
    if canonical_sha256(seeds) != EXPECTED_SEED_CANONICAL:
        raise Refusal("successor candidate seed canonical hash drift")
    if canonical_sha256(rows) != EXPECTED_ROWS_CANONICAL:
        raise Refusal("successor candidate row canonical hash drift")
    return rows


def validate_ledger() -> dict[str, Any]:
    rows = derive_rows()
    seeds = [int(row["seed"]) for row in rows]
    set41, set42, set43, set44, set45, ledger45 = consumed_seed_sets()
    consumed_sets = {41: set41, 42: set42, 43: set43, 44: set44, 45: set45}
    out: dict[str, Any] = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "POSTCONSUMPTION_SUCCESSOR_CANDIDATE_ONLY_NOT_APPLIED_NOT_AUTHORIZED",
        "namespace": NAMESPACE,
        "candidateSeedCount": 72,
        "candidateSeeds": seeds,
        "candidateRows": rows,
        "candidateMinSeed": min(seeds),
        "candidateMaxSeed": max(seeds),
        "candidateSeedCanonicalSha256": EXPECTED_SEED_CANONICAL,
        "candidateRowsCanonicalSha256": EXPECTED_ROWS_CANONICAL,
        "consumedOrdinal45SeedCanonicalSha256": EXPECTED_ORDINAL45_SEED_CANONICAL,
        "recovery4HistoricalLedgerBlobSha1": EXPECTED_RECOVERY4_LEDGER_BLOB,
        "ordinal45Recovery4Status": ledger45.get("status"),
        "allCollisionCountersZero": True,
        "historicalOrdinal42LedgerValidatedAtNativePath": True,
        "trackedCandidateSeedLedger": False,
        "candidateSeedFreshnessProven": False,
        "candidateSeedsAppliedToCases": False,
        "seedUniverseConsumed": False,
        "scientificOrdinalAllocated": False,
        "authorizationCreated": False,
        "dispatchCreated": False,
        "publisherInvoked": False,
        "scienceInvoked": False,
        "writeQuietEntered": False,
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
    for ordinal, consumed_set in consumed_sets.items():
        out[f"overlapWithConsumedOrdinal{ordinal}SeedCount"] = len(set(seeds) & consumed_set)
    for ordinal in (41, 42, 43, 44):
        key = f"consumedOrdinal{ordinal}SeedCanonicalSha256"
        if key in ledger45:
            out[key] = ledger45[key]
    return out


if __name__ == "__main__":
    ledger = validate_ledger()
    print(
        json.dumps(
            {
                "status": "PASS_AVPS_V2_SUCCESSOR_CANDIDATE_LEDGER_DETERMINISTIC_NOT_AUTHORIZED",
                "candidateSeedCount": ledger["candidateSeedCount"],
                "candidateSeedCanonicalSha256": ledger["candidateSeedCanonicalSha256"],
                "candidateRowsCanonicalSha256": ledger["candidateRowsCanonicalSha256"],
                "overlapWithConsumedOrdinal45SeedCount": ledger["overlapWithConsumedOrdinal45SeedCount"],
                "scientificOrdinalAllocated": ledger["scientificOrdinalAllocated"],
            },
            sort_keys=True,
        )
    )
