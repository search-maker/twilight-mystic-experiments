#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
from typing import Any


BASE_PACKAGE_PATH = "experiments/tier1-precision-continuation-v2/package.py"
V2_WAVE_PACKAGE_PATH = "experiments/tier1-precision-continuation-wave1-v2/package.py"
V2_PREREGISTRATION_PATH = "evidence/tier1-precision-continuation-wave1-v2/preregistration.json"
SEED_PLAN_PATH = "evidence/tier1-precision-continuation-wave1-v3/seed-plan.json"
DUPLICATE_SNAPSHOT_PATH = "evidence/tier1-precision-continuation-wave1-v3/ordinal9-duplicate-search-snapshot.json"

SOURCE_MAIN_SHA = "1c1a699def045c59d3cbf7162b94216cb2a53366"
V2_PREREGISTRATION_SHA256 = "03ac61690981232edd30cbd5a674f8b246d9abc31ac2f1c8cf9bb4e57eeb3c96"
CONSUMED_ORDINAL8_RUN = 31_044_664_420
CONSUMED_ORDINAL8_JOB = 92_437_178_971
CONSUMED_ORDINAL8_REF = "5168be57c28bca5f316d70a785a782ea9b3b1036"
CONSUMED_ORDINAL8_KEY = "twilight-surrogate-tier-1-v1:numerical:8"
CONSUMED_ORDINAL8_TITLE = "Tier-1 precision continuation wave 1 ordinal 8"

CANDIDATE_ORDINAL = 9
CANDIDATE_KEY = "twilight-surrogate-tier-1-v1:numerical:9"
CANDIDATE_TITLE = "Tier-1 precision continuation wave 1 ordinal 9"
CANDIDATE_BRANCH = "authorization/tier1-precision-continuation-wave1-ordinal9-v3"
CANDIDATE_AUTHORIZATION_PATH = "experiments/tier1-precision-continuation-wave1-v3/authorization.ordinal9.json"

STAGE_ID = "tier1-precision-continuation-wave1-preregistration-v3"
WAVE = 1
BLOCKS = (3, 4)
CASE_COUNT = 40
GEOMETRY_COUNT = 20
TRAINING_GEOMETRY_COUNT = 17
HOLDOUT_GEOMETRY_COUNT = 3
TRAINING_CASE_COUNT = 34
HOLDOUT_CASE_COUNT = 6
MAX_CONFIGURED_PHOTON_HISTORIES = 5_100_000_000
HEX = set("0123456789abcdef")


class Refusal(RuntimeError):
    pass


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= HEX


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


def _seed_plan(root: Path) -> dict[str, Any]:
    plan = load_json(root / SEED_PLAN_PATH)
    required = {
        "schemaVersion": 1,
        "stageId": "tier1-precision-continuation-wave1-v3-seed-plan",
        "status": "REVIEW_ONLY_NOT_AUTHORIZATION",
        "sourceMainSha": SOURCE_MAIN_SHA,
        "replacesConsumedOrdinal": 8,
        "replacesConsumedRunId": CONSUMED_ORDINAL8_RUN,
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
    identity = plan.get("candidateIdentity")
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
    if identity != expected_identity:
        raise Refusal("candidate identity is not review-only")
    return plan


def _patched_base(root: Path, plan: dict[str, Any]):
    base = load_module(root / BASE_PACKAGE_PATH, "tier1_continuation_v3_patched_base")
    seed_rows = plan.get("seedsByGeometry")
    if not isinstance(seed_rows, dict) or set(seed_rows) != set(base.CONTINUATION_GEOMETRY_IDS):
        raise Refusal("seed geometry universe changed")
    patched = {gid: tuple(values) for gid, values in base.PRECOMPUTED_SEEDS.items()}
    ordered: list[int] = []
    for gid in base.CONTINUATION_GEOMETRY_IDS:
        row = seed_rows.get(gid)
        if not isinstance(row, dict) or set(row) != {"b3", "b4"}:
            raise Refusal(f"seed pair missing for {gid}")
        pair = (row["b3"], row["b4"])
        if any(not isinstance(seed, int) or isinstance(seed, bool) or not (0 < seed < 2_147_483_647) for seed in pair):
            raise Refusal("seed outside positive signed-32-bit range")
        ordered.extend(pair)
        patched[gid] = pair + tuple(patched[gid][2:])
    if len(set(ordered)) != CASE_COUNT:
        raise Refusal("new wave-1 seeds are not unique")
    if canonical_sha256(ordered) != plan.get("orderedSeedsSha256"):
        raise Refusal("ordered seed hash changed")
    all_patched = [patched[gid][block - 3] for gid in base.CONTINUATION_GEOMETRY_IDS for block in range(3, 9)]
    if len(set(all_patched)) != len(all_patched):
        raise Refusal("new wave-1 seeds collide with preserved future-wave seeds")
    base.PRECOMPUTED_SEEDS = patched
    return base, ordered


def _proposal(root: Path):
    plan = _seed_plan(root)
    base, ordered = _patched_base(root, plan)
    wave_v2 = load_module(root / V2_WAVE_PACKAGE_PATH, "tier1_wave1_v2_source")
    dataset, aggregate, audit, provenance, source_seeds = wave_v2._base_inputs(root, base)
    proposal = base.build(dataset, aggregate, audit, provenance)
    base.validate_proposal(proposal)
    return plan, base, wave_v2, proposal, source_seeds, ordered


def build_preregistration(root: Path | None = None) -> dict[str, Any]:
    root = (root or repository_root()).resolve()
    plan, base, wave_v2, proposal, source_seeds, ordered = _proposal(root)
    v2_prereg = wave_v2.build_preregistration(root)
    wave_v2.validate_preregistration(v2_prereg, root)
    if v2_prereg.get("preregistrationSha256") != V2_PREREGISTRATION_SHA256:
        raise Refusal("consumed ordinal-8 preregistration binding changed")

    source_records = {row["geometryId"]: row for row in proposal["sourceRecords"]}
    base_cases = base.wave_cases(proposal, WAVE, base.CONTINUATION_GEOMETRY_IDS)
    cases: list[dict[str, Any]] = []
    for case_ordinal, row in enumerate(base_cases, start=1):
        source = source_records[row["groupId"]]
        base_case_id = row["caseId"]
        case_id = base_case_id.replace("precision-continuation-v2", "precision-continuation-v3")
        cases.append(
            {
                **copy.deepcopy(row),
                "caseId": case_id,
                "baseCaseId": base_case_id,
                "caseOrdinal": case_ordinal,
                "replacementGeneration": 3,
                "geometry": copy.deepcopy(source["geometry"]),
                "preservedSourceCaseIds": list(source["caseIds"]),
                "preservedSourceValuesCdM2": list(source["valuesCdM2"]),
                "preservedZeroHitCaseIds": list(source["zeroHitCaseIds"]),
            }
        )

    v2_wave_seeds = [row["seed"] for row in v2_prereg["cases"]]
    historical = set(wave_v2.ORDINAL1_SEEDS) | set(source_seeds) | set(wave_v2.CONSUMED_PROBE_SEEDS)
    new_seeds = [row["seed"] for row in cases]
    if len(historical) != 196:
        raise Refusal("historical seed universe changed")
    if set(new_seeds) & historical:
        raise Refusal("new seeds overlap pre-ordinal-8 historical seeds")
    if set(new_seeds) & set(v2_wave_seeds):
        raise Refusal("new seeds overlap consumed ordinal-8 wave seeds")
    if new_seeds != ordered:
        raise Refusal("case ordering and seed-plan ordering diverged")

    training_ids = sorted(row["geometryId"] for row in proposal["sourceRecords"] if row["role"] == "surrogate-training")
    holdout_ids = sorted(row["geometryId"] for row in proposal["sourceRecords"] if row["role"] == "internal-holdout")
    if (
        len(cases) != CASE_COUNT
        or len({row["caseId"] for row in cases}) != CASE_COUNT
        or len({row["groupId"] for row in cases}) != GEOMETRY_COUNT
        or {row["block"] for row in cases} != set(BLOCKS)
        or len(training_ids) != TRAINING_GEOMETRY_COUNT
        or len(holdout_ids) != HOLDOUT_GEOMETRY_COUNT
        or sum(row["role"] == "surrogate-training" for row in cases) != TRAINING_CASE_COUNT
        or sum(row["role"] == "internal-holdout" for row in cases) != HOLDOUT_CASE_COUNT
        or sum(row["photonHistories"] for row in cases) != MAX_CONFIGURED_PHOTON_HISTORIES
    ):
        raise Refusal("frozen scientific scope changed")

    preregistration: dict[str, Any] = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "PREPARATION_ONLY_NOT_AUTHORIZED",
        "sourceMainSha": SOURCE_MAIN_SHA,
        "proposalOnly": True,
        "scientificExecution": False,
        "authorizationEnabled": False,
        "authorizationOrdinal": None,
        "authorizationRef": None,
        "executionKey": None,
        "dispatchEnabled": False,
        "workflowDispatchEnabled": False,
        "solverExecutionAuthorized": False,
        "githubRerunAllowed": False,
        "candidateIdentity": copy.deepcopy(plan["candidateIdentity"]),
        "consumedOrdinal8": {
            "runId": CONSUMED_ORDINAL8_RUN,
            "preflightJobId": CONSUMED_ORDINAL8_JOB,
            "authorizationOrdinal": 8,
            "authorizationRef": CONSUMED_ORDINAL8_REF,
            "executionKey": CONSUMED_ORDINAL8_KEY,
            "runTitle": CONSUMED_ORDINAL8_TITLE,
            "failureBeforeRuntimeManifestOrSolver": True,
            "seedsConsumedOnDispatch": True,
        },
        "sourceBindings": {
            "v2PreregistrationPath": V2_PREREGISTRATION_PATH,
            "v2PreregistrationSha256": V2_PREREGISTRATION_SHA256,
            "v2PreregistrationRawSha256": source_sha256(root / V2_PREREGISTRATION_PATH),
            "v2BaseProposalSha256": proposal["proposalSha256"],
            "seedPlanPath": SEED_PLAN_PATH,
            "seedPlanRawSha256": raw_sha256(root / SEED_PLAN_PATH),
            "duplicateSearchSnapshotPath": DUPLICATE_SNAPSHOT_PATH,
            "duplicateSearchSnapshotRawSha256": raw_sha256(root / DUPLICATE_SNAPSHOT_PATH),
            "ordinal2Source": copy.deepcopy(proposal["source"]),
        },
        "wave": WAVE,
        "blocks": list(BLOCKS),
        "geometryIds": list(base.CONTINUATION_GEOMETRY_IDS),
        "geometryCount": GEOMETRY_COUNT,
        "trainingGeometryIds": training_ids,
        "internalHoldoutGeometryIds": holdout_ids,
        "roleCounts": {
            "surrogateTrainingGeometries": TRAINING_GEOMETRY_COUNT,
            "internalHoldoutGeometries": HOLDOUT_GEOMETRY_COUNT,
            "surrogateTrainingCases": TRAINING_CASE_COUNT,
            "internalHoldoutCases": HOLDOUT_CASE_COUNT,
        },
        "caseCount": CASE_COUNT,
        "maximumConfiguredPhotonHistories": MAX_CONFIGURED_PHOTON_HISTORIES,
        "cases": cases,
        "seedProof": {
            "preOrdinal8HistoricalSeedCount": len(historical),
            "preOrdinal8HistoricalSeedsSha256": canonical_sha256(sorted(historical)),
            "ordinal8WaveSeedCount": len(v2_wave_seeds),
            "ordinal8WaveSeedsSha256": canonical_sha256(v2_wave_seeds),
            "replacementWaveSeedCount": len(new_seeds),
            "replacementWaveSeedsSha256": canonical_sha256(new_seeds),
            "allReplacementSeedsUnique": len(set(new_seeds)) == CASE_COUNT,
            "historicalOverlap": [],
            "ordinal8Overlap": [],
            "seedsConsumedOnDispatchEvenOnPreflightFailure": True,
        },
        "thresholds": copy.deepcopy(v2_prereg["thresholds"]),
        "stoppingRule": copy.deepcopy(v2_prereg["stoppingRule"]),
        "classifications": copy.deepcopy(v2_prereg["classifications"]),
        "executionContract": {
            **copy.deepcopy(v2_prereg["executionContract"]),
            "paginatedDuplicateSearchUsesSlurpWithoutJq": True,
            "paginatedPagesValidatedAndFlattenedByPython": True,
            "malformedOrPartialRunEvidenceRefused": True,
        },
        "preservation": {
            **copy.deepcopy(v2_prereg["preservation"]),
            "ordinal8EvidenceImmutable": True,
            "ordinal8WorkflowNotReenabled": True,
            "onlyWave1SeedsAndVersionedIdentityChange": True,
        },
        "surrogateTrainingAuthorized": False,
        "internalHoldoutOpeningAuthorized": False,
        "tier2Authorized": False,
        "productionPromotionAuthorized": False,
        "boundary": "review-only v3 replacement preparation; no identity allocation, authorization, dispatch, solver execution, fitting, holdout opening, Tier-2, or production action",
    }
    preregistration["preregistrationSha256"] = canonical_sha256(preregistration)
    return preregistration


def validate_preregistration(value: dict[str, Any], root: Path | None = None) -> None:
    if not isinstance(value, dict):
        raise Refusal("v3 preregistration missing")
    payload = dict(value)
    supplied = payload.pop("preregistrationSha256", None)
    if not is_sha256(supplied) or canonical_sha256(payload) != supplied:
        raise Refusal("v3 preregistration hash changed")
    if value != build_preregistration(root):
        raise Refusal("v3 preregistration differs from frozen generation")


def authorization_template(preregistration: dict[str, Any], root: Path | None = None) -> dict[str, Any]:
    validate_preregistration(preregistration, root)
    value = {
        "schemaVersion": 1,
        "stageId": "tier1-precision-continuation-wave1-authorization-template-v3",
        "status": "DISABLED_TEMPLATE_NOT_AUTHORIZATION",
        "preregistrationSha256": preregistration["preregistrationSha256"],
        "wave": WAVE,
        "blocks": list(BLOCKS),
        "caseCount": CASE_COUNT,
        "enabled": False,
        "authorizationOrdinal": None,
        "authorizationRef": None,
        "authorizationCommit": None,
        "executionKey": None,
        "dispatch": False,
        "workflowDispatchEnabled": False,
        "runAttempt": None,
        "automaticDispatch": False,
        "githubRerunAllowed": False,
        "solverExecutionAuthorized": False,
        "surrogateTrainingAuthorized": False,
        "internalHoldoutOpeningAuthorized": False,
        "tier2Authorized": False,
        "productionPromotionAuthorized": False,
    }
    value["templateSha256"] = canonical_sha256(value)
    return value


def review_packet(preregistration: dict[str, Any], root: Path | None = None) -> dict[str, Any]:
    root = (root or repository_root()).resolve()
    validate_preregistration(preregistration, root)
    snapshot = load_json(root / DUPLICATE_SNAPSHOT_PATH)
    expected = {
        "status": "NO_REAL_COLLISION_FOUND_REVIEW_ONLY",
        "verifiedMainSha": SOURCE_MAIN_SHA,
        "candidateOrdinal": CANDIDATE_ORDINAL,
        "candidateExecutionKey": CANDIDATE_KEY,
        "candidateRunTitle": CANDIDATE_TITLE,
        "candidateAuthorizationBranch": CANDIDATE_BRANCH,
        "candidateAuthorizationPath": CANDIDATE_AUTHORIZATION_PATH,
        "candidateAllocated": False,
        "candidateReserved": False,
        "authorizationRef": None,
        "authorizationEnabled": False,
        "dispatchEnabled": False,
        "scientificExecution": False,
    }
    stale = {key: (snapshot.get(key), value) for key, value in expected.items() if snapshot.get(key) != value}
    if stale:
        raise Refusal(f"duplicate-search snapshot changed: {stale}")
    if any(snapshot.get(key) for key in (
        "exactExecutionKeyMatches",
        "exactRunTitleMatches",
        "exactAuthorizationBranchMatches",
        "exactAuthorizationPathMatches",
        "realOrdinalCollisionMatches",
    )):
        raise Refusal("candidate ordinal 9 has a real collision")
    packet = {
        "schemaVersion": 1,
        "stageId": "tier1-precision-continuation-wave1-v3-candidate-review",
        "status": "CANDIDATE_ORDINAL9_REVIEW_ONLY_NOT_ALLOCATED",
        "preregistrationSha256": preregistration["preregistrationSha256"],
        "candidateIdentity": copy.deepcopy(preregistration["candidateIdentity"]),
        "caseCount": CASE_COUNT,
        "geometryCount": GEOMETRY_COUNT,
        "maximumConfiguredPhotonHistories": MAX_CONFIGURED_PHOTON_HISTORIES,
        "roleCounts": copy.deepcopy(preregistration["roleCounts"]),
        "seedProof": copy.deepcopy(preregistration["seedProof"]),
        "duplicateSearchSnapshotRawSha256": raw_sha256(root / DUPLICATE_SNAPSHOT_PATH),
        "authorizationAllocated": False,
        "authorizationEnabled": False,
        "dispatchEnabled": False,
        "scientificExecution": False,
        "solverExecutionAuthorized": False,
        "surrogateTrainingAuthorized": False,
        "internalHoldoutOpeningAuthorized": False,
        "tier2Authorized": False,
        "productionPromotionAuthorized": False,
    }
    packet["packetSha256"] = canonical_sha256(packet)
    return packet


def _translate_results(preregistration: dict[str, Any], results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    expected = {row["caseId"]: row for row in preregistration["cases"]}
    if len(results) != CASE_COUNT or {row.get("caseId") for row in results} != set(expected):
        raise Refusal("partial, duplicate, or unplanned v3 result set")
    translated: list[dict[str, Any]] = []
    for result in results:
        case = expected[result["caseId"]]
        if result.get("seed") != case["seed"] or result.get("role") != case["role"] or result.get("block") != case["block"]:
            raise Refusal("v3 result provenance changed")
        values = result.get("selectedNodeRadiance")
        if not isinstance(values, list) or len(values) != 15 or any(
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(float(value))
            or value < 0
            for value in values
        ):
            raise Refusal("v3 result selected-node evidence malformed")
        row = copy.deepcopy(result)
        row["caseId"] = case["baseCaseId"]
        translated.append(row)
    return translated


def aggregate_wave1(preregistration: dict[str, Any], results: list[dict[str, Any]], root: Path | None = None) -> dict[str, Any]:
    root = (root or repository_root()).resolve()
    validate_preregistration(preregistration, root)
    _, base, _, proposal, _, _ = _proposal(root)
    aggregate = base.aggregate_wave(proposal, WAVE, base.CONTINUATION_GEOMETRY_IDS, _translate_results(preregistration, results))
    wrapper = {
        "schemaVersion": 1,
        "stageId": "tier1-precision-continuation-wave1-aggregate-v3",
        "preregistrationSha256": preregistration["preregistrationSha256"],
        "aggregate": aggregate,
        "aggregateSha256": canonical_sha256(aggregate),
        "additionalExecutionAutomaticallyAuthorized": False,
    }
    wrapper["payloadSha256"] = canonical_sha256(wrapper)
    return wrapper


def audit_wave1(preregistration: dict[str, Any], results: list[dict[str, Any]], aggregate_wrapper: dict[str, Any], root: Path | None = None) -> dict[str, Any]:
    root = (root or repository_root()).resolve()
    validate_preregistration(preregistration, root)
    _, base, _, proposal, _, _ = _proposal(root)
    payload = dict(aggregate_wrapper)
    supplied = payload.pop("payloadSha256", None)
    if not is_sha256(supplied) or canonical_sha256(payload) != supplied:
        raise Refusal("v3 aggregate wrapper hash changed")
    aggregate = aggregate_wrapper.get("aggregate")
    if not isinstance(aggregate, dict) or canonical_sha256(aggregate) != aggregate_wrapper.get("aggregateSha256"):
        raise Refusal("v3 aggregate payload changed")
    audit = base.audit_wave(proposal, WAVE, base.CONTINUATION_GEOMETRY_IDS, _translate_results(preregistration, results), aggregate)
    wrapper = {
        "schemaVersion": 1,
        "stageId": "tier1-precision-continuation-wave1-independent-audit-v3",
        "preregistrationSha256": preregistration["preregistrationSha256"],
        "aggregateSha256": aggregate_wrapper["aggregateSha256"],
        "audit": audit,
        "auditSha256": canonical_sha256(audit),
        "independentlyRecomputedFromRawSelectedNodeRadiance": True,
        "additionalExecutionAutomaticallyAuthorized": False,
    }
    wrapper["payloadSha256"] = canonical_sha256(wrapper)
    return wrapper


def analyze_wave1(preregistration: dict[str, Any], aggregate_wrapper: dict[str, Any], audit_wrapper: dict[str, Any], root: Path | None = None) -> dict[str, Any]:
    root = (root or repository_root()).resolve()
    validate_preregistration(preregistration, root)
    _, base, _, proposal, _, _ = _proposal(root)
    for wrapper, label in ((aggregate_wrapper, "aggregate"), (audit_wrapper, "audit")):
        payload = dict(wrapper)
        supplied = payload.pop("payloadSha256", None)
        if not is_sha256(supplied) or canonical_sha256(payload) != supplied:
            raise Refusal(f"v3 {label} wrapper hash changed")
    analysis = base.analyze_waves(proposal, [aggregate_wrapper["aggregate"]], [audit_wrapper["audit"]])
    value = {
        "schemaVersion": 1,
        "stageId": "tier1-precision-continuation-wave1-analysis-v3",
        "preregistrationSha256": preregistration["preregistrationSha256"],
        "aggregateSha256": aggregate_wrapper["aggregateSha256"],
        "auditSha256": audit_wrapper["auditSha256"],
        "analysis": analysis,
        "additionalExecutionAutomaticallyAuthorized": False,
        "surrogateFitAuthorized": False,
        "internalHoldoutOpened": False,
        "tier2Authorized": False,
        "productionPromotionAuthorized": False,
    }
    value["analysisSha256"] = canonical_sha256(value)
    return value


def write_generated(root: Path, output_dir: Path) -> dict[str, Any]:
    preregistration = build_preregistration(root)
    template = authorization_template(preregistration, root)
    packet = review_packet(preregistration, root)
    output_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "preregistration.json": preregistration,
        "authorization.template.json": template,
        "candidate-review.json": packet,
    }
    for name, value in files.items():
        (output_dir / name).write_text(dump(value), encoding="utf-8", newline="\n")
    report = {
        "schemaVersion": 1,
        "status": "DETERMINISTIC_REVIEW_ARTIFACTS_GENERATED",
        "sourceMainSha": SOURCE_MAIN_SHA,
        "fileHashes": {name: raw_sha256(output_dir / name) for name in sorted(files)},
        "authorizationAllocated": False,
        "dispatchEnabled": False,
        "scientificExecution": False,
    }
    report["reportSha256"] = canonical_sha256(report)
    (output_dir / "generation-report.json").write_text(dump(report), encoding="utf-8", newline="\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(dump(write_generated(repository_root(), args.output_dir)), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
