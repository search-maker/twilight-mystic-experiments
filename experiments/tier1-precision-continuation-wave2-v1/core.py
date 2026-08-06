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
V5_PACKAGE_PATH = "experiments/tier1-precision-continuation-wave1-v5/package.py"
V5_CORE_PATH = "experiments/tier1-precision-continuation-wave1-v5/core.py"
SOURCE_DESCRIPTOR_PATH = "evidence/tier1-precision-continuation-wave2-v1/source-salvage.json"
SEED_PLAN_PATH = "evidence/tier1-precision-continuation-wave2-v1/seed-plan.json"
DUPLICATE_SNAPSHOT_PATH = "evidence/tier1-precision-continuation-wave2-v1/ordinal12-duplicate-search-snapshot.json"
SOURCE_MAIN_SHA = "4ebc7c0eef2e12562e5a1a9bed857c0fbf2c10f1"
SOURCE_SALVAGE_RUN_ID = 31_063_167_217
SOURCE_SALVAGE_ARTIFACT_ID = 8_952_843_354
SOURCE_SALVAGE_DESCRIPTOR_SHA256 = "55c6e11f7b7e7aabbc6f7f0c137f7920b49b3f10248dd565a12c70908c6ab978"
SOURCE_SALVAGE_ARTIFACT_DIGEST = "sha256:0fd662b3420e0162d9580cb30b4859775b3f43feba5b9264d26aed61c163f56b"
SOURCE_AGGREGATE_RAW_SHA256 = "b57477cf68555ec9752d43e817cadaf5e1f2bf33490b09767cad73b341a2ca8e"
SOURCE_AUDIT_RAW_SHA256 = "4e37595c348f4f9d8593db20cff5c69ed41068f4f2810934e5e8f93d1df62be5"
SOURCE_ANALYSIS_RAW_SHA256 = "8c472324573f182f4760e5101fb087d7d10f140e531261e3eeaa1e232a9bdfd4"
SOURCE_SALVAGE_REPORT_RAW_SHA256 = "5cd623009a1ea1b5e20aa00789ee26fdc66ccdbdc228627ad258ec760a85bb9e"
CANDIDATE_ORDINAL = 12
CANDIDATE_KEY = "twilight-surrogate-tier-1-v1:numerical:12"
CANDIDATE_TITLE = "Tier-1 precision continuation wave 2 ordinal 12"
CANDIDATE_BRANCH = "authorization/tier1-precision-continuation-wave2-ordinal12-v1"
CANDIDATE_AUTHORIZATION_PATH = "experiments/tier1-precision-continuation-wave2-v1/authorization.ordinal12.json"
STAGE_ID = "tier1-precision-continuation-wave2-preregistration-v1"
WAVE = 2
BLOCKS = (5, 6)
ACTIVE_GEOMETRY_IDS = (
    "train-0003",
    "train-0007",
    "train-0009",
    "train-0011",
    "train-0013",
    "train-0015",
    "train-0019",
    "train-0023",
    "train-0027",
    "train-0029",
    "train-0031",
    "train-0035",
    "train-0039",
    "train-0041",
    "train-0043",
    "train-0047",
)
CASE_COUNT = 32
GEOMETRY_COUNT = 16
TRAINING_GEOMETRY_COUNT = 14
HOLDOUT_GEOMETRY_COUNT = 2
TRAINING_CASE_COUNT = 28
HOLDOUT_CASE_COUNT = 4
MAX_CONFIGURED_PHOTON_HISTORIES = 4_600_000_000


class Refusal(RuntimeError):
    pass


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode()).hexdigest()


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


def _verify_self_hash(value: dict[str, Any], field: str, label: str) -> None:
    supplied = value.get(field)
    payload = {key: item for key, item in value.items() if key != field}
    if supplied != canonical_sha256(payload):
        raise Refusal(f"{label} self-hash changed")


def source_descriptor(root: Path) -> dict[str, Any]:
    value = load_json(root / SOURCE_DESCRIPTOR_PATH)
    _verify_self_hash(value, "descriptorSha256", "source salvage descriptor")
    required = {
        "schemaVersion": 1,
        "stageId": "tier1-precision-continuation-wave2-v1-source-salvage",
        "status": "REVIEWED_MAIN_BOUND_POSTPROCESS_SOURCE",
        "sourceMainSha": SOURCE_MAIN_SHA,
        "sourceWorkflowRunId": SOURCE_SALVAGE_RUN_ID,
        "sourceWorkflowRunAttempt": 1,
        "sourceWorkflowEvent": "push",
        "sourceArtifactId": SOURCE_SALVAGE_ARTIFACT_ID,
        "sourceArtifactName": "tier1-wave1-ordinal11-postprocess-salvage",
        "sourceArtifactSizeBytes": 43_224,
        "sourceArtifactDigest": SOURCE_SALVAGE_ARTIFACT_DIGEST,
        "sourceDownloadedZipSha256": SOURCE_SALVAGE_ARTIFACT_DIGEST.removeprefix("sha256:"),
        "classificationCounts": {
            "ADAPTIVE_CONTINUATION_REQUIRED": 16,
            "PRECISION_ACCEPTED": 1,
            "PRECISION_TARGET_MET": 3,
        },
        "nextWaveGeometryIds": list(ACTIVE_GEOMETRY_IDS),
        "nextWave": WAVE,
        "nextBlocks": list(BLOCKS),
        "nextCaseCount": CASE_COUNT,
        "solverExecutionsPerformedBySalvage": 0,
        "sourceArtifactsModified": False,
        "additionalExecutionAutomaticallyAuthorized": False,
        "surrogateTrainingAuthorized": False,
        "internalHoldoutOpeningAuthorized": False,
        "tier2Authorized": False,
        "productionPromotionAuthorized": False,
    }
    stale = {key: (value.get(key), expected) for key, expected in required.items() if value.get(key) != expected}
    if stale:
        raise Refusal(f"source salvage descriptor changed: {stale}")
    payloads = value.get("sourcePayloads")
    expected_payloads = {
        "aggregateRawSha256": SOURCE_AGGREGATE_RAW_SHA256,
        "auditRawSha256": SOURCE_AUDIT_RAW_SHA256,
        "analysisRawSha256": SOURCE_ANALYSIS_RAW_SHA256,
        "salvageReportRawSha256": SOURCE_SALVAGE_REPORT_RAW_SHA256,
        "salvageReportSelfSha256": "c394244feb7fafd4916b440d5e2f5e87d6a049b009520ceb721b755df08476b6",
        "sourceInventoryRawSha256": "866ce7a402c785eaa936b85d0f2039fbe464dc52b52b9921efd4c9b253f89495",
    }
    if payloads != expected_payloads:
        raise Refusal("source salvage payload bindings changed")
    source = value.get("scientificSource")
    expected_source = {
        "runId": 31_052_639_692,
        "runAttempt": 1,
        "headSha": "5b28ea31649f2c37e8b56ddae893a57608c2e148",
        "authorizationOrdinal": 11,
        "authorizationRef": "23b2f823d826a1655f716006c9b87d07e44e0e99",
        "executionKey": "twilight-surrogate-tier-1-v1:numerical:11",
        "runTitle": "Tier-1 precision continuation wave 1 ordinal 11",
        "caseCount": 40,
        "blocks": [3, 4],
        "identityConsumed": True,
        "seedsConsumed": True,
        "rerunAllowed": False,
        "reuseAllowed": False,
    }
    if source != expected_source:
        raise Refusal("consumed ordinal-11 source identity changed")
    return value


def seed_plan(root: Path) -> dict[str, Any]:
    value = load_json(root / SEED_PLAN_PATH)
    _verify_self_hash(value, "seedPlanSha256", "wave-two seed plan")
    required = {
        "schemaVersion": 1,
        "stageId": "tier1-precision-continuation-wave2-v1-seed-plan",
        "status": "REVIEW_ONLY_NOT_AUTHORIZATION",
        "sourceMainSha": SOURCE_MAIN_SHA,
        "sourceSalvageDescriptorSha256": SOURCE_SALVAGE_DESCRIPTOR_SHA256,
        "wave": WAVE,
        "blocks": list(BLOCKS),
        "activeGeometryIds": list(ACTIVE_GEOMETRY_IDS),
        "geometryCount": GEOMETRY_COUNT,
        "caseCount": CASE_COUNT,
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
    stale = {key: (value.get(key), expected) for key, expected in required.items() if value.get(key) != expected}
    if stale:
        raise Refusal(f"wave-two seed plan changed: {stale}")
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
    if value.get("candidateIdentity") != expected_identity:
        raise Refusal("candidate identity is not review-only")
    return value


def duplicate_snapshot(root: Path) -> dict[str, Any]:
    value = load_json(root / DUPLICATE_SNAPSHOT_PATH)
    _verify_self_hash(value, "snapshotSha256", "ordinal-12 duplicate snapshot")
    required = {
        "schemaVersion": 1,
        "stageId": "tier1-precision-continuation-wave2-v1-ordinal12-duplicate-search",
        "status": "NO_COLLISION_REVIEW_ONLY",
        "sourceMainSha": SOURCE_MAIN_SHA,
        "candidateOrdinal": CANDIDATE_ORDINAL,
        "candidateExecutionKey": CANDIDATE_KEY,
        "candidateRunTitle": CANDIDATE_TITLE,
        "repositoryCodeExactKeyMatches": 0,
        "repositoryBranchOrdinal12Matches": 0,
        "recentWorkflowRunOrdinal12Matches": 0,
        "openIssueSearchOrdinal12MatchesExcludingControlLedger": 0,
        "candidateAllocated": False,
        "authorizationRef": None,
        "dispatchExists": False,
        "scientificExecutionExists": False,
        "githubRerunAllowed": False,
    }
    stale = {key: (value.get(key), expected) for key, expected in required.items() if value.get(key) != expected}
    if stale:
        raise Refusal(f"ordinal-12 duplicate snapshot changed: {stale}")
    return value


def proposal(root: Path):
    descriptor = source_descriptor(root)
    plan = seed_plan(root)
    snapshot = duplicate_snapshot(root)
    v5_core = load_module(root / V5_CORE_PATH, "tier1_wave1_v5_core_for_wave2")
    _, base, wave_v2, proposal_value, source_seeds, ordinal11_ordered = v5_core.proposal(root)
    base.validate_proposal(proposal_value)
    rows = plan.get("seedsByGeometry")
    if not isinstance(rows, dict) or set(rows) != set(ACTIVE_GEOMETRY_IDS):
        raise Refusal("wave-two seed geometry universe changed")
    ordered: list[int] = []
    for gid in ACTIVE_GEOMETRY_IDS:
        row = rows.get(gid)
        if not isinstance(row, dict) or set(row) != {"b5", "b6"}:
            raise Refusal(f"wave-two seed pair missing for {gid}")
        pair = (row["b5"], row["b6"])
        if any(
            not isinstance(seed, int)
            or isinstance(seed, bool)
            or not 0 < seed < 2_147_483_647
            for seed in pair
        ):
            raise Refusal("wave-two seed outside positive signed-32-bit range")
        frozen_pair = tuple(base.PRECOMPUTED_SEEDS[gid][2:4])
        if pair != frozen_pair:
            raise Refusal(f"wave-two seed pair no longer matches original preregistration for {gid}")
        ordered.extend(pair)
    if len(set(ordered)) != CASE_COUNT or canonical_sha256(ordered) != plan.get("orderedSeedsSha256"):
        raise Refusal("ordered wave-two seed proof changed")
    historical = set(wave_v2.ORDINAL1_SEEDS) | set(source_seeds) | set(wave_v2.CONSUMED_PROBE_SEEDS)
    v2_package = load_module(root / V2_WAVE_PACKAGE_PATH, "tier1_wave1_v2_for_wave2")
    v3_package = load_module(root / V3_PACKAGE_PATH, "tier1_wave1_v3_for_wave2")
    v4_package = load_module(root / V4_PACKAGE_PATH, "tier1_wave1_v4_for_wave2")
    v5_package = load_module(root / V5_PACKAGE_PATH, "tier1_wave1_v5_for_wave2")
    v2_prereg = v2_package.build_preregistration(root)
    v3_prereg = v3_package.build_preregistration(root)
    v4_prereg = v4_package.build_preregistration(root)
    v5_prereg = v5_package.build_preregistration(root)
    for module, prereg in (
        (v2_package, v2_prereg),
        (v3_package, v3_prereg),
        (v4_package, v4_prereg),
        (v5_package, v5_prereg),
    ):
        module.validate_preregistration(prereg, root)
    ordinal8 = [row["seed"] for row in v2_prereg["cases"]]
    ordinal9 = [row["seed"] for row in v3_prereg["cases"]]
    ordinal10 = [row["seed"] for row in v4_prereg["cases"]]
    ordinal11 = [row["seed"] for row in v5_prereg["cases"]]
    if ordinal11 != ordinal11_ordered:
        raise Refusal("consumed ordinal-11 seed ordering changed")
    original_future = [
        base.PRECOMPUTED_SEEDS[gid][block - 3]
        for gid in base.CONTINUATION_GEOMETRY_IDS
        for block in (5, 6, 7, 8)
    ]
    remaining_future = [seed for seed in original_future if seed not in set(ordered)]
    if len(original_future) != 80 or len(set(original_future)) != 80:
        raise Refusal("original future-wave seed universe changed")
    if len(remaining_future) != 48 or set(remaining_future) & set(ordered):
        raise Refusal("remaining future-wave seed universe changed")
    consumed = historical | set(ordinal8) | set(ordinal9) | set(ordinal10) | set(ordinal11)
    if set(ordered) & consumed:
        raise Refusal("wave-two seeds overlap consumed evidence")
    if not set(ordered) < set(original_future):
        raise Refusal("wave-two seeds are not the frozen original b5-b6 subset")
    return {
        "descriptor": descriptor,
        "plan": plan,
        "snapshot": snapshot,
        "base": base,
        "waveV2": wave_v2,
        "proposal": proposal_value,
        "sourceSeeds": source_seeds,
        "historicalSeeds": historical,
        "ordinal8": ordinal8,
        "ordinal9": ordinal9,
        "ordinal10": ordinal10,
        "ordinal11": ordinal11,
        "originalFuture": original_future,
        "remainingFuture": remaining_future,
        "ordered": ordered,
    }
