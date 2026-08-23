from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

STAGE_ID = "aerosol-full-phase-function-sensitivity-v1"
NAMESPACE = "aerosol-full-phase-function-sensitivity-v1|group-seed|sha256-v1"
MIN_SEED = 10_000_000
MAX_EXCLUSIVE = 2_147_483_647
SPAN = MAX_EXCLUSIVE - MIN_SEED
REVIEW_CORE_PATH = Path(__file__).resolve().parent / "review_core.py"
REVIEW_CORE_BLOB = "e89bc6ec5deb89e9084e1cafe02b15e42de72ad3"
LEDGER_PATH = Path(__file__).resolve().parent / "candidate-seed-ledger.v1.json"


class Refusal(RuntimeError):
    pass


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def review_core():
    if git_blob_sha1(REVIEW_CORE_PATH) != REVIEW_CORE_BLOB:
        raise Refusal("frozen AFPF review_core bytes changed")
    spec = importlib.util.spec_from_file_location("afpf_seed_bound_review_core", REVIEW_CORE_PATH)
    if spec is None or spec.loader is None:
        raise Refusal("cannot load frozen AFPF review_core")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def derive_rows() -> list[dict[str, Any]]:
    core = review_core()
    groups = core.group_skeletons()
    if len(groups) != 72 or len({str(row["groupId"]) for row in groups}) != 72:
        raise Refusal("frozen 72-group universe drift")
    rows: list[dict[str, Any]] = []
    used: set[int] = set()
    for group in groups:
        group_id = str(group["groupId"])
        if group.get("seed") is not None or group.get("seedStatus") != "UNALLOCATED_REVIEW_ONLY":
            raise Refusal(f"review group already contains seed: {group_id}")
        counter = 0
        while True:
            material = f"{NAMESPACE}|groupId={group_id}|counter={counter}"
            digest = hashlib.sha256(material.encode()).hexdigest()
            seed = (int(digest[:16], 16) % SPAN) + MIN_SEED
            if seed not in used:
                break
            counter += 1
        if not MIN_SEED <= seed < MAX_EXCLUSIVE:
            raise Refusal("derived seed escaped scanner-visible signed-32-bit domain")
        used.add(seed)
        rows.append({
            "groupId": group_id,
            "collisionCounter": counter,
            "derivationMaterialSha256": digest,
            "seed": seed,
        })
    if len(rows) != 72 or len(used) != 72:
        raise Refusal("candidate seed cardinality/uniqueness drift")
    return rows


def build_ledger() -> dict[str, Any]:
    rows = derive_rows()
    seeds = [int(row["seed"]) for row in rows]
    return {
        "schemaVersion": 1,
        "stageId": f"{STAGE_ID}-candidate-seeds",
        "status": "CANDIDATE_ONLY_NOT_APPLIED_NOT_AUTHORIZED",
        "namespace": NAMESPACE,
        "derivation": "seed=(uint64_be(SHA256(namespace|groupId|counter)[0:8]) % (MAX_EXCLUSIVE-MIN_SEED)) + MIN_SEED; increment counter only for within-ledger collision",
        "scannerCompatibility": {
            "minimumSeedInclusive": MIN_SEED,
            "maximumSeedExclusive": MAX_EXCLUSIVE,
            "allCandidateSeedsHaveAtLeastSevenDecimalDigits": True,
            "reason": "repository-global seed scanners recognize candidate literals only in the 7-20 decimal-digit token domain; AFPF v1 derivation is intentionally a strict subset of that detectable domain",
        },
        "candidateSeedCount": 72,
        "candidateSeeds": seeds,
        "candidateRows": rows,
        "candidateFirstSeed": seeds[0],
        "candidateLastSeed": seeds[-1],
        "candidateMinSeed": min(seeds),
        "candidateMaxSeed": max(seeds),
        "allCollisionCountersZero": all(row["collisionCounter"] == 0 for row in rows),
        "candidateSeedCanonicalSha256": canonical_sha256(seeds),
        "candidateRowsCanonicalSha256": canonical_sha256(rows),
        "appliedToCaseSkeletons": False,
        "candidateSeedFreshnessProven": False,
        "scientificOrdinalAllocated": False,
        "authorizationPermitted": False,
        "solverExecutionAuthorized": False,
        "resultOpeningAuthorized": False,
    }


def validate_ledger() -> dict[str, Any]:
    ledger = json.loads(LEDGER_PATH.read_text())
    expected = build_ledger()
    if ledger != expected:
        raise Refusal("candidate seed ledger differs from deterministic frozen derivation")
    return ledger


if __name__ == "__main__":
    value = validate_ledger()
    print(json.dumps({
        "status": "PASS_AFPF_CANDIDATE_LEDGER_DETERMINISTIC_NOT_AUTHORIZED",
        "candidateSeedCount": value["candidateSeedCount"],
        "candidateSeedCanonicalSha256": value["candidateSeedCanonicalSha256"],
        "candidateRowsCanonicalSha256": value["candidateRowsCanonicalSha256"],
        "allCollisionCountersZero": value["allCollisionCountersZero"],
        "candidateSeedFreshnessProven": value["candidateSeedFreshnessProven"],
    }, sort_keys=True))
