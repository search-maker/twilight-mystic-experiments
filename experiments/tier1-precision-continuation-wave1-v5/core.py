from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

BASE_PACKAGE_PATH = "experiments/tier1-precision-continuation-v2/package.py"
V2_WAVE_PACKAGE_PATH = "experiments/tier1-precision-continuation-wave1-v2/package.py"
V3_PACKAGE_PATH = "experiments/tier1-precision-continuation-wave1-v3/package.py"
V4_PACKAGE_PATH = "experiments/tier1-precision-continuation-wave1-v4/package.py"
SEED_PLAN_PATH = "evidence/tier1-precision-continuation-wave1-v5/seed-plan.json"
DUPLICATE_SNAPSHOT_PATH = "evidence/tier1-precision-continuation-wave1-v5/ordinal11-duplicate-search-snapshot.json"
SOURCE_MAIN_SHA = "465c1734076af0e047bca422f281d9efba26a249"
V4_PREREGISTRATION_SHA256 = "72331ddcdfbd04ddc5b08b145181231642c608124fc02b9cf24d7778cdaed140"
CANDIDATE_ORDINAL = 11
CANDIDATE_KEY = "twilight-surrogate-tier-1-v1:numerical:11"
CANDIDATE_TITLE = "Tier-1 precision continuation wave 1 ordinal 11"
CANDIDATE_BRANCH = "authorization/tier1-precision-continuation-wave1-ordinal11-v5"
CANDIDATE_AUTHORIZATION_PATH = "experiments/tier1-precision-continuation-wave1-v5/authorization.ordinal11.json"
STAGE_ID = "tier1-precision-continuation-wave1-preregistration-v5"
WAVE = 1
BLOCKS = (3, 4)
CASE_COUNT = 40
GEOMETRY_COUNT = 20
TRAINING_GEOMETRY_COUNT = 17
HOLDOUT_GEOMETRY_COUNT = 3
TRAINING_CASE_COUNT = 34
HOLDOUT_CASE_COUNT = 6
MAX_CONFIGURED_PHOTON_HISTORIES = 5_100_000_000


class Refusal(RuntimeError):
    pass


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise Refusal(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise Refusal(f"expected object: {path}")
    return value


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise Refusal(f"module unavailable: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def seed_plan(root: Path) -> dict[str, Any]:
    plan = load_json(root / SEED_PLAN_PATH)
    required = {
        "schemaVersion": 1,
        "stageId": "tier1-precision-continuation-wave1-v5-seed-plan",
        "status": "REVIEW_ONLY_NOT_AUTHORIZATION",
        "sourceMainSha": SOURCE_MAIN_SHA,
        "replacesConsumedOrdinals": [8, 9, 10],
        "replacesConsumedRuns": [31_044_664_420, 31_048_812_892, 31_050_964_900],
        "seedCount": CASE_COUNT,
        "authorizationEnabled": False,
        "dispatchEnabled": False,
        "scientificExecution": False,
        "solverExecutionAuthorized": False,
        "githubRerunAllowed": False,
        "surrogateTrainingAuthorized": False,
        "internalHoldoutOpeningAuthorized": False,
        "tier2Authorized": False,
        "productionPromotionAuthorized": False,
    }
    stale = {key: (plan.get(key), value) for key, value in required.items() if plan.get(key) != value}
    if stale:
        raise Refusal(f"seed plan boundary changed: {stale}")
    expected_identity = {
        "authorizationOrdinal": CANDIDATE_ORDINAL,
        "executionKey": CANDIDATE_KEY,
        "runTitle": CANDIDATE_TITLE,
        "authorizationBranch": CANDIDATE_BRANCH,
        "authorizationPath": CANDIDATE_AUTHORIZATION_PATH,
        "allocated": False,
        "reserved": False,
        "authorizationRef": None,
        "status": "UNALLOCATED_REVIEW_ONLY",
    }
    if plan.get("candidateIdentity") != expected_identity:
        raise Refusal("candidate identity is not review-only")
    return plan


def proposal(root: Path):
    plan = seed_plan(root)
    base = load_module(root / BASE_PACKAGE_PATH, "tier1_continuation_v5_patched_base")
    rows = plan.get("seedsByGeometry")
    if not isinstance(rows, dict) or set(rows) != set(base.CONTINUATION_GEOMETRY_IDS):
        raise Refusal("seed geometry universe changed")
    patched = {gid: tuple(values) for gid, values in base.PRECOMPUTED_SEEDS.items()}
    ordered: list[int] = []
    for gid in base.CONTINUATION_GEOMETRY_IDS:
        row = rows.get(gid)
        if not isinstance(row, dict) or set(row) != {"b3", "b4"}:
            raise Refusal(f"seed pair missing for {gid}")
        pair = (row["b3"], row["b4"])
        if any(not isinstance(seed, int) or isinstance(seed, bool) or not 0 < seed < 2_147_483_647 for seed in pair):
            raise Refusal("seed outside positive signed-32-bit range")
        ordered.extend(pair)
        patched[gid] = pair + tuple(patched[gid][2:])
    if len(set(ordered)) != CASE_COUNT or canonical_sha256(ordered) != plan.get("orderedSeedsSha256"):
        raise Refusal("ordered replacement seed proof changed")
    all_patched = [patched[gid][block - 3] for gid in base.CONTINUATION_GEOMETRY_IDS for block in range(3, 9)]
    if len(set(all_patched)) != len(all_patched):
        raise Refusal("replacement seeds collide with preserved future-wave seeds")
    base.PRECOMPUTED_SEEDS = patched
    wave_v2 = load_module(root / V2_WAVE_PACKAGE_PATH, "tier1_wave1_v2_source_for_v5")
    dataset, aggregate, audit, provenance, source_seeds = wave_v2._base_inputs(root, base)
    proposal_value = base.build(dataset, aggregate, audit, provenance)
    base.validate_proposal(proposal_value)
    return plan, base, wave_v2, proposal_value, source_seeds, ordered
