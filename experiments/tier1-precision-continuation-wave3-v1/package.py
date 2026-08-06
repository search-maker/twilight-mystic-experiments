#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

WAVE2_CORE_PATH = "experiments/tier1-precision-continuation-wave2-v1/core.py"
SOURCE_STAGE_ID = "tier1-precision-continuation-wave2-analysis-v1"
STAGE_ID = "tier1-precision-continuation-wave3-preregistration-v1"
CANDIDATE_ORDINAL = 13
CANDIDATE_KEY = "twilight-surrogate-tier-1-v1:numerical:13"
CANDIDATE_TITLE = "Tier-1 precision continuation wave 3 ordinal 13"
CANDIDATE_BRANCH = "authorization/tier1-precision-continuation-wave3-ordinal13-v1"
CANDIDATE_AUTHORIZATION_PATH = "experiments/tier1-precision-continuation-wave3-v1/authorization.ordinal13.json"
SOURCE_RUN_ID = 31_065_046_524
SOURCE_RUN_ATTEMPT = 1
SOURCE_MAIN_SHA = "0ef7e011e00a4c4badcafb2f6ca06256026b1746"
SOURCE_AUTHORIZATION_REF = "18a5746778441d57b722c740a17c94af9b56e9c9"
SOURCE_EXECUTION_KEY = "twilight-surrogate-tier-1-v1:numerical:12"
WAVE = 3
BLOCKS = (7, 8)


class Refusal(RuntimeError):
    pass


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


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


def validate_source_analysis(value: dict[str, Any], root: Path | None = None) -> tuple[list[str], dict[str, dict[str, Any]]]:
    root = (root or repository_root()).resolve()
    wave2 = load_module(root / WAVE2_CORE_PATH, "wave3_v1_wave2_source")
    state = wave2.proposal(root)
    expected_universe = set(wave2.ACTIVE_GEOMETRY_IDS)
    if value.get("stageId") != SOURCE_STAGE_ID:
        raise Refusal("wave-two analysis stage changed")
    payload = {key: item for key, item in value.items() if key != "analysisSha256"}
    if value.get("analysisSha256") != canonical_sha256(payload):
        raise Refusal("wave-two analysis self-hash changed")
    for key in (
        "additionalExecutionAutomaticallyAuthorized",
        "surrogateFitAuthorized",
        "internalHoldoutOpened",
        "tier2Authorized",
        "productionPromotionAuthorized",
    ):
        if value.get(key) is not False:
            raise Refusal(f"closed wave-two boundary changed: {key}")
    body = value.get("analysis")
    if not isinstance(body, dict) or body.get("status") != "CONTINUATION_ANALYZED":
        raise Refusal("wave-two continuation analysis incomplete")
    points = body.get("points")
    if not isinstance(points, list) or len(points) != 20:
        raise Refusal("wave-two continuation geometry universe changed")
    by_id: dict[str, dict[str, Any]] = {}
    for point in points:
        if not isinstance(point, dict):
            raise Refusal("wave-two continuation point malformed")
        geometry_id = point.get("geometryId")
        if not isinstance(geometry_id, str) or not geometry_id or geometry_id in by_id:
            raise Refusal("wave-two continuation point identity duplicated or missing")
        by_id[geometry_id] = point
    active = body.get("nextWaveGeometryIds")
    if not isinstance(active, list) or not active:
        raise Refusal("no wave three required")
    if len(active) != len(set(active)) or not set(active) <= expected_universe:
        raise Refusal("wave-three active set is outside the reviewed wave-two universe")
    if body.get("exhaustedGeometryIds") != []:
        raise Refusal("wave-two analysis unexpectedly exhausted a geometry")
    if body.get("scientificallyEligible") is not False:
        raise Refusal("wave-three source unexpectedly claims universal eligibility")
    for geometry_id in active:
        point = by_id.get(geometry_id)
        if (
            not isinstance(point, dict)
            or point.get("classification") != "ADAPTIVE_CONTINUATION_REQUIRED"
            or point.get("blockCount") != 6
            or point.get("capReached") is not False
            or point.get("scientificallyEligible") is not False
        ):
            raise Refusal(f"wave-three source point is not an active b1-b6 continuation: {geometry_id}")
    for geometry_id in expected_universe - set(active):
        point = by_id.get(geometry_id)
        if not isinstance(point, dict) or point.get("classification") not in {
            "PRECISION_TARGET_MET",
            "PRECISION_ACCEPTED",
        } or point.get("scientificallyEligible") is not True:
            raise Refusal(f"resolved wave-two point changed: {geometry_id}")
    return list(active), by_id


def build_preregistration(source_analysis: dict[str, Any], source_analysis_path: Path, root: Path | None = None) -> dict[str, Any]:
    root = (root or repository_root()).resolve()
    active, points = validate_source_analysis(source_analysis, root)
    wave2 = load_module(root / WAVE2_CORE_PATH, "wave3_v1_wave2_state")
    state = wave2.proposal(root)
    base = state["base"]
    proposal = state["proposal"]
    source_records = {row["geometryId"]: row for row in proposal["sourceRecords"]}
    cases: list[dict[str, Any]] = []
    for case_ordinal, row in enumerate(base.wave_cases(proposal, WAVE, active), start=1):
        source = source_records[row["groupId"]]
        base_case_id = row["caseId"]
        cases.append(
            {
                **copy.deepcopy(row),
                "caseId": base_case_id.replace(
                    "precision-continuation-v2",
                    "precision-continuation-wave3-v1",
                ),
                "baseCaseId": base_case_id,
                "caseOrdinal": case_ordinal,
                "waveGeneration": 1,
                "geometry": copy.deepcopy(source["geometry"]),
                "sourceWave2Classification": points[row["groupId"]]["classification"],
                "sourceWave2BlockCount": points[row["groupId"]]["blockCount"],
            }
        )
    if (
        len(cases) != 2 * len(active)
        or len({row["caseId"] for row in cases}) != len(cases)
        or {row["block"] for row in cases} != set(BLOCKS)
        or {row["groupId"] for row in cases} != set(active)
    ):
        raise Refusal("wave-three case universe changed")
    ordered_seeds = [row["seed"] for row in cases]
    for geometry_id in active:
        expected = tuple(base.PRECOMPUTED_SEEDS[geometry_id][4:6])
        observed = tuple(
            row["seed"]
            for row in sorted(
                (item for item in cases if item["groupId"] == geometry_id),
                key=lambda item: item["block"],
            )
        )
        if observed != expected:
            raise Refusal(f"original preregistered b7-b8 seeds changed: {geometry_id}")
    consumed = (
        set(state["historicalSeeds"])
        | set(state["ordinal8"])
        | set(state["ordinal9"])
        | set(state["ordinal10"])
        | set(state["ordinal11"])
        | set(state["ordered"])
    )
    if len(set(ordered_seeds)) != len(ordered_seeds) or set(ordered_seeds) & consumed:
        raise Refusal("wave-three seeds overlap consumed evidence")
    all_b7_b8 = {
        base.PRECOMPUTED_SEEDS[geometry_id][block - 3]
        for geometry_id in base.CONTINUATION_GEOMETRY_IDS
        for block in BLOCKS
    }
    if not set(ordered_seeds) <= all_b7_b8:
        raise Refusal("wave-three seeds are not the original preregistered b7-b8 subset")
    untouched_b7_b8 = sorted(all_b7_b8 - set(ordered_seeds))
    training_ids = sorted(
        geometry_id
        for geometry_id in active
        if source_records[geometry_id]["role"] == "surrogate-training"
    )
    holdout_ids = sorted(
        geometry_id
        for geometry_id in active
        if source_records[geometry_id]["role"] == "internal-holdout"
    )
    value = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "PREPARATION_ONLY_NOT_AUTHORIZED",
        "proposalOnly": True,
        "scientificExecution": False,
        "authorizationEnabled": False,
        "dispatchEnabled": False,
        "solverExecutionAuthorized": False,
        "githubRerunAllowed": False,
        "candidateIdentity": {
            "authorizationOrdinal": CANDIDATE_ORDINAL,
            "executionKey": CANDIDATE_KEY,
            "runTitle": CANDIDATE_TITLE,
            "authorizationBranch": CANDIDATE_BRANCH,
            "authorizationPath": CANDIDATE_AUTHORIZATION_PATH,
            "allocated": False,
            "reserved": False,
            "authorizationRef": None,
            "status": "UNALLOCATED_REVIEW_ONLY",
        },
        "sourceOrdinal12": {
            "runId": SOURCE_RUN_ID,
            "runAttempt": SOURCE_RUN_ATTEMPT,
            "mainSha": SOURCE_MAIN_SHA,
            "authorizationRef": SOURCE_AUTHORIZATION_REF,
            "executionKey": SOURCE_EXECUTION_KEY,
            "identityAndSeedsConsumed": True,
            "rerunAllowed": False,
        },
        "sourceAnalysisRawSha256": raw_sha256(source_analysis_path),
        "sourceAnalysisSha256": source_analysis["analysisSha256"],
        "proposalSha256": proposal["proposalSha256"],
        "wave": WAVE,
        "blocks": list(BLOCKS),
        "geometryIds": list(active),
        "geometryCount": len(active),
        "trainingGeometryIds": training_ids,
        "internalHoldoutGeometryIds": holdout_ids,
        "caseCount": len(cases),
        "maximumConfiguredPhotonHistories": sum(row["photonHistories"] for row in cases),
        "cases": cases,
        "seedProof": {
            "wave3SeedCount": len(ordered_seeds),
            "wave3SeedsSha256": canonical_sha256(ordered_seeds),
            "allWave3SeedsUnique": len(set(ordered_seeds)) == len(ordered_seeds),
            "consumedOverlap": [],
            "wave3SubsetOfOriginalPreregisteredB7B8": True,
            "untouchedB7B8SeedCount": len(untouched_b7_b8),
            "untouchedB7B8SeedsSha256": canonical_sha256(untouched_b7_b8),
            "seedsConsumedOnDispatchEvenOnPreflightFailure": True,
        },
        "stoppingRule": {
            "waveBoundaryBlocks": list(BLOCKS),
            "maximumTotalBlocks": 8,
            "zeroHitOrdinaryRsemForbidden": True,
            "unresolvedAtMaximumClassification": [
                "PRECISION_CONTINUATION_EXHAUSTED",
                "PRECISION_CONTINUATION_EXHAUSTED_ZERO_HIT",
            ],
            "automaticNextWave": False,
            "noWaveAfterB8": True,
        },
        "surrogateTrainingAuthorized": False,
        "internalHoldoutOpeningAuthorized": False,
        "tier2Authorized": False,
        "productionPromotionAuthorized": False,
        "boundary": "dynamic b7-b8 preparation only from terminal ordinal-12 analysis; no identity allocation, authorization, dispatch, solver execution, fitting, holdout opening, Tier-2, or production action",
    }
    value["preregistrationSha256"] = canonical_sha256(value)
    return value


def write_generated(source_analysis_path: Path, output_dir: Path, root: Path | None = None) -> dict[str, Any]:
    root = (root or repository_root()).resolve()
    source = load_json(source_analysis_path)
    preregistration = build_preregistration(source, source_analysis_path, root)
    output_dir.mkdir(parents=True, exist_ok=True)
    prereg_path = output_dir / "preregistration.json"
    prereg_path.write_text(dump(preregistration), encoding="utf-8", newline="\n")
    report = {
        "schemaVersion": 1,
        "stageId": "tier1-precision-continuation-wave3-v1-generation-report",
        "status": "DYNAMIC_REVIEW_ARTIFACTS_GENERATED_NOT_AUTHORIZED",
        "sourceAnalysisRawSha256": preregistration["sourceAnalysisRawSha256"],
        "preregistrationRawSha256": raw_sha256(prereg_path),
        "preregistrationSha256": preregistration["preregistrationSha256"],
        "geometryCount": preregistration["geometryCount"],
        "caseCount": preregistration["caseCount"],
        "authorizationAllocated": False,
        "dispatchEnabled": False,
        "scientificExecution": False,
    }
    report["reportSha256"] = canonical_sha256(report)
    (output_dir / "generation-report.json").write_text(
        dump(report), encoding="utf-8", newline="\n"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-analysis", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(dump(write_generated(args.source_analysis, args.output_dir)), end="")
        return 0
    except Exception as exc:
        print(dump({"status": "REFUSED", "reason": str(exc)}), end="")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
