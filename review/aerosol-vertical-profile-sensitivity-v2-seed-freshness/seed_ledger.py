from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

STAGE_ID = "aerosol-vertical-profile-sensitivity-v2"
NAMESPACE = "aerosol-vertical-profile-sensitivity-v2|group-seed|sha256-v1"
MIN_SEED = 10_000_000
MAX_EXCLUSIVE = 2_147_483_647
SPAN = MAX_EXCLUSIVE - MIN_SEED
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SKELETON_PATH = ROOT / "review/aerosol-vertical-profile-sensitivity-v2-prereg/build_skeleton.py"
EXPECTED_SKELETON_BLOB = "b4a4ab6917ad28f08d4980194f7b68f3961d5d59"
EXPECTED_SKELETON_CANONICAL = "a8d2d8f59aec01d82d8d98672152d00c11261660b0a69a59e2716c2edabd2b02"
EXPECTED_SEED_CANONICAL = "02f624d582e9b2caba6b920d65a5e8a8bc8fc1a2693623bc2f73abf5d3f706d2"
EXPECTED_ROWS_CANONICAL = "41f70d6a0381db6b569d3f4e17d74bb38b05cf212c2f2e432455a502f73dc670"


class Refusal(RuntimeError):
    pass


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def skeleton_module():
    if git_blob_sha1(SKELETON_PATH) != EXPECTED_SKELETON_BLOB:
        raise Refusal("AVPS v2 seed review refuses: prereg skeleton builder byte drift")
    spec = importlib.util.spec_from_file_location("avps_v2_seed_bound_skeleton", SKELETON_PATH)
    if spec is None or spec.loader is None:
        raise Refusal("cannot load AVPS v2 prereg skeleton builder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def derive_rows() -> list[dict[str, Any]]:
    skeleton = skeleton_module().build_review_skeleton()
    if skeleton.get("canonicalSkeletonSha256") != EXPECTED_SKELETON_CANONICAL:
        raise Refusal("AVPS v2 skeleton canonical identity drift")
    groups = skeleton.get("groups")
    if not isinstance(groups, list) or len(groups) != 72 or len({str(r.get('groupId')) for r in groups}) != 72:
        raise Refusal("AVPS v2 72-group universe drift")
    if skeleton.get("seedCount") != 0 or skeleton.get("scientificOrdinal") is not None:
        raise Refusal("prereg skeleton already contains seed/ordinal")

    rows: list[dict[str, Any]] = []
    used: set[int] = set()
    for group in groups:
        group_id = str(group["groupId"])
        if not group_id.startswith("avps-v2-"):
            raise Refusal(f"fresh v2 group namespace drift: {group_id}")
        if group.get("candidateSeed") is not None or group.get("seedStatus") != "UNALLOCATED_REVIEW_ONLY":
            raise Refusal(f"prereg group already contains seed: {group_id}")
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
    if canonical_sha256(seeds) != EXPECTED_SEED_CANONICAL:
        raise Refusal("candidate seed canonical hash drift")
    if canonical_sha256(rows) != EXPECTED_ROWS_CANONICAL:
        raise Refusal("candidate row canonical hash drift")
    return rows


def build_ledger() -> dict[str, Any]:
    rows = derive_rows()
    seeds = [int(row["seed"]) for row in rows]
    return {
        "schemaVersion": 1,
        "stageId": f"{STAGE_ID}-candidate-seeds",
        "status": "CANDIDATE_ONLY_ARTIFACT_ONLY_NOT_APPLIED_NOT_AUTHORIZED",
        "namespace": NAMESPACE,
        "derivation": "seed=(uint64_be(SHA256(namespace|groupId|counter)[0:8]) % (MAX_EXCLUSIVE-MIN_SEED)) + MIN_SEED; increment counter only for within-ledger collision",
        "scannerCompatibility": {
            "minimumSeedInclusive": MIN_SEED,
            "maximumSeedExclusive": MAX_EXCLUSIVE,
            "allCandidateSeedsHaveAtLeastSevenDecimalDigits": True,
        },
        "candidateSeedCount": 72,
        "candidateSeeds": seeds,
        "candidateRows": rows,
        "candidateMinSeed": min(seeds),
        "candidateMaxSeed": max(seeds),
        "allCollisionCountersZero": True,
        "candidateSeedCanonicalSha256": EXPECTED_SEED_CANONICAL,
        "candidateRowsCanonicalSha256": EXPECTED_ROWS_CANONICAL,
        "trackedCandidateSeedLedger": False,
        "candidateSeedFreshnessProven": False,
        "candidateSeedsAppliedToCases": False,
        "scientificOrdinalAllocated": False,
        "authorizationCreated": False,
        "solverExecutionAuthorized": False,
        "resultOpeningAuthorized": False,
    }


def validate_ledger() -> dict[str, Any]:
    ledger = build_ledger()
    if ledger["candidateSeedCount"] != 72 or len(set(ledger["candidateSeeds"])) != 72:
        raise Refusal("candidate ledger cardinality/uniqueness drift")
    return ledger


if __name__ == "__main__":
    value = validate_ledger()
    print(json.dumps({
        "status": "PASS_AVPS_V2_CANDIDATE_LEDGER_DETERMINISTIC_ARTIFACT_ONLY_NOT_AUTHORIZED",
        "candidateSeedCount": value["candidateSeedCount"],
        "candidateSeedCanonicalSha256": value["candidateSeedCanonicalSha256"],
        "candidateRowsCanonicalSha256": value["candidateRowsCanonicalSha256"],
        "allCollisionCountersZero": value["allCollisionCountersZero"],
        "trackedCandidateSeedLedger": value["trackedCandidateSeedLedger"],
        "candidateSeedFreshnessProven": value["candidateSeedFreshnessProven"],
    }, sort_keys=True))
