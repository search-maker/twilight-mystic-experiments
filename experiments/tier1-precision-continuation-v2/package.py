from __future__ import annotations

import hashlib
import json
import math
import statistics
from typing import Any, Iterable

TARGET_RSEM = 0.05
ACCEPTED_MAX_RSEM = 0.08
INITIAL_BLOCKS = 2
MAX_TOTAL_BLOCKS = 8
BLOCK_WAVES = {1: (3, 4), 2: (5, 6), 3: (7, 8)}
MAX_WAVE_CASES = 40
MAX_WAVE_PHOTONS = 5_100_000_000
MAX_CONTINUATION_CASES = 120
MAX_CONTINUATION_PHOTONS = 15_300_000_000

SOURCE_RUN_ID = 30_952_457_327
SOURCE_RUN_ATTEMPT = 1
SOURCE_HEAD_SHA = "c9679a515c5f4538345d0d83252bcd8e37eb7b7e"
SOURCE_AUTHORIZATION_REF = "9f3ef4b2afd93d5ae15a45ac70c9f27e32636f88"
SOURCE_EXECUTION_KEY = "twilight-surrogate-tier-1-v1:numerical:2"
SOURCE_AUTHORIZATION_ORDINAL = 2
SOURCE_PLAN_RAW_SHA256 = "f19ea2eb742ca6e5ca638714128b52f3ba5167dfa23b9ff08ee19ae01416d448"
SOURCE_ARTIFACT_MANIFEST_RAW_SHA256 = "33ff075963f1f57828c6369d58eec7adb60dcc8df820b25e2d11cf33e79aa070"
SOURCE_HISTORICAL_REPRODUCTION_RAW_SHA256 = "1c992bf9e22ee1c293508f4dcbcdf00ea84c4ecf03ee4f0120de8dc5089dee57"
SOURCE_ARTIFACT_DIGESTS = {
    "twilight-surrogate-tier-1-ordinal2-execution-preflight": "sha256:e042bac7c3e50f03d0f2501e950d16393ce94da0c8bc45dd77efaa03e865eb8f",
    "twilight-surrogate-tier-1-ordinal2-aggregate": "sha256:b85620fa0af8ec4609ad4934c7f0bfbcdd346f8a5f6f4f2b3d55e5fadf6088c2",
    "twilight-surrogate-tier-1-ordinal2-audit": "sha256:9dbcd59c42c7696a5b43a2a5331434ed3047c8764229ae5f906a4596fb94eef0",
}

GEOMETRIES_BY_PHOTONS = {
    50_000_000: (
        "train-0009",
        "train-0017",
        "train-0033",
        "train-0041",
        "train-0046",
    ),
    100_000_000: (
        "train-0003",
        "train-0011",
        "train-0013",
        "train-0019",
        "train-0029",
        "train-0035",
        "train-0045",
    ),
    200_000_000: (
        "train-0007",
        "train-0015",
        "train-0023",
        "train-0027",
        "train-0031",
        "train-0039",
        "train-0043",
        "train-0047",
    ),
}
CONTINUATION_GEOMETRY_IDS = tuple(sorted(gid for ids in GEOMETRIES_BY_PHOTONS.values() for gid in ids))
INTERNAL_HOLDOUT_IDS = frozenset({"train-0015", "train-0035", "train-0045"})
ZERO_HIT_SOURCE_ID = "train-0047"

# Frozen before any continuation result exists. The values are the first 64 bits of
# SHA-256(domain|geometry|block|0), reduced to the positive signed-32-bit solver
# range. The table, rather than runtime derivation, is the execution input.
PRECOMPUTED_SEEDS = {
    "train-0003": (2030605205, 819816404, 1102146994, 2067663015, 395581942, 993246868),
    "train-0007": (1396939381, 1450118913, 1823975308, 1040412589, 1217508928, 404585035),
    "train-0009": (951515230, 126609209, 768920775, 1312096696, 7555926, 1302328510),
    "train-0011": (1941243723, 1084704385, 812905955, 2055805979, 1979049835, 2243404),
    "train-0013": (258811206, 798048238, 1726781302, 1542299504, 1885603703, 2027304805),
    "train-0015": (549051806, 1292094427, 1997252098, 1289539055, 774924126, 1436232820),
    "train-0017": (318712048, 1913526394, 2016615805, 2140268804, 1320520932, 1448386049),
    "train-0019": (1490872196, 283132490, 837050074, 87553339, 1711200898, 1469255731),
    "train-0023": (2038127017, 1402283858, 679775142, 1355727498, 2073925867, 194440251),
    "train-0027": (1465623902, 1701543173, 107458770, 1043582738, 1768292115, 1223926188),
    "train-0029": (503304190, 159394619, 1089712093, 1555270081, 647051626, 353277491),
    "train-0031": (1640860361, 1303777985, 123341971, 2102375349, 1478983102, 111072113),
    "train-0033": (473668965, 1761260683, 1641568217, 1392764571, 1934596228, 307718753),
    "train-0035": (1085136387, 1778412062, 1314109880, 1139009761, 935545584, 767582620),
    "train-0039": (130116680, 46685338, 402294420, 940717330, 1082031181, 577717495),
    "train-0041": (1606769031, 1281038820, 835773094, 1077775044, 315992270, 2055411087),
    "train-0043": (208763858, 946259494, 509684938, 1814726469, 1857968567, 1636760941),
    "train-0045": (421826168, 1299253357, 1844460124, 1007959511, 1371906123, 319759536),
    "train-0046": (1192821328, 675405632, 1013446151, 492481933, 380539867, 2042141358),
    "train-0047": (1530296586, 1938692625, 2028175294, 559174787, 202450280, 1316925969),
}

ALLOWED_ROLES = {"surrogate-training", "internal-holdout"}
HEX = set("0123456789abcdef")


class Refusal(RuntimeError):
    pass


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= HEX


def _finite(value: Any, name: str, *, nonnegative: bool = False) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise Refusal(f"{name} must be numeric")
    number = float(value)
    if not math.isfinite(number) or (number < 0 if nonnegative else number <= 0):
        raise Refusal(f"{name} must be finite and {'nonnegative' if nonnegative else 'positive'}")
    return number


def _photon_schedule() -> dict[str, int]:
    return {gid: photons for photons, ids in GEOMETRIES_BY_PHOTONS.items() for gid in ids}


def _seed_for(gid: str, block: int) -> int:
    return PRECOMPUTED_SEEDS[gid][block - 3]


def _stable_rsem(values: Iterable[float]) -> float:
    rows = [_finite(value, "block value") for value in values]
    if len(rows) < 2:
        raise Refusal("at least two positive blocks are required")
    scale = max(rows)
    scaled = [value / scale for value in rows]
    mean = statistics.fmean(scaled)
    return statistics.stdev(scaled) / math.sqrt(len(scaled)) / mean


def _at_most(value: float, threshold: float) -> bool:
    return value < threshold or math.isclose(value, threshold, rel_tol=0.0, abs_tol=1e-15)


def classify_values(values: Iterable[float]) -> dict[str, Any]:
    rows = [_finite(value, "block value", nonnegative=True) for value in values]
    if len(rows) not in {2, 4, 6, 8}:
        raise Refusal("block count must be an audited wave boundary")
    zero_count = sum(value == 0.0 for value in rows)
    cap_reached = len(rows) == MAX_TOTAL_BLOCKS
    if zero_count:
        classification = "PRECISION_CONTINUATION_EXHAUSTED_ZERO_HIT" if cap_reached else "ADAPTIVE_CONTINUATION_REQUIRED"
        rsem = None
        rsem_status = "NOT_COMPUTED_ZERO_HIT_PRESENT"
        numerical_status = "NUMERICAL_ZERO_HIT_UNDERCONVERGED" if not cap_reached else "NUMERICAL_ZERO_HIT_EXHAUSTED"
    else:
        rsem = _stable_rsem(rows)
        rsem_status = "COMPUTED"
        if _at_most(rsem, TARGET_RSEM):
            classification = "PRECISION_TARGET_MET"
            numerical_status = "NUMERICALLY_CONVERGED_TARGET"
        elif _at_most(rsem, ACCEPTED_MAX_RSEM):
            classification = "PRECISION_ACCEPTED"
            numerical_status = "NUMERICALLY_CONVERGED_ACCEPTED"
        elif cap_reached:
            classification = "PRECISION_CONTINUATION_EXHAUSTED"
            numerical_status = "NUMERICAL_PRECISION_EXHAUSTED"
        else:
            classification = "ADAPTIVE_CONTINUATION_REQUIRED"
            numerical_status = "NUMERICAL_PRECISION_INSUFFICIENT"
    return {
        "blockCount": len(rows),
        "valuesCdM2": rows,
        "nonzeroBlockValuesCdM2": [value for value in rows if value != 0.0],
        "zeroHitBlockCount": zero_count,
        "zeroHitBlockFraction": zero_count / len(rows),
        "relativeStandardErrorOfMean": rsem,
        "relativeStandardErrorStatus": rsem_status,
        "classification": classification,
        "numericalStatus": numerical_status,
        "capReached": cap_reached,
        "scientificallyEligible": classification in {"PRECISION_TARGET_MET", "PRECISION_ACCEPTED"},
    }


def _validate_source_provenance(
    dataset: dict[str, Any], aggregate: dict[str, Any], audit: dict[str, Any], provenance: dict[str, Any]
) -> set[int]:
    required = {
        "runId": SOURCE_RUN_ID,
        "runAttempt": SOURCE_RUN_ATTEMPT,
        "headSha": SOURCE_HEAD_SHA,
        "authorizationRef": SOURCE_AUTHORIZATION_REF,
        "executionKey": SOURCE_EXECUTION_KEY,
        "authorizationOrdinal": SOURCE_AUTHORIZATION_ORDINAL,
        "event": "workflow_dispatch",
        "planRawSha256": SOURCE_PLAN_RAW_SHA256,
        "artifactManifestRawSha256": SOURCE_ARTIFACT_MANIFEST_RAW_SHA256,
        "historicalReproductionRawSha256": SOURCE_HISTORICAL_REPRODUCTION_RAW_SHA256,
        "artifactDigests": SOURCE_ARTIFACT_DIGESTS,
        "historicalTerminalConclusion": "failure",
        "historicalEvidenceImmutable": True,
        "correctedInterpretationOnly": True,
    }
    if any(provenance.get(key) != value for key, value in required.items()):
        raise Refusal("ordinal-2 source identity or immutable-history boundary changed")
    bindings = provenance.get("bindings")
    expected = {
        "datasetSha256": canonical_sha256(dataset),
        "aggregateSha256": canonical_sha256(aggregate),
        "auditSha256": canonical_sha256(audit),
    }
    if not isinstance(bindings, dict) or any(bindings.get(key) != value for key, value in expected.items()):
        raise Refusal("corrected source binding failed")
    source_seeds = provenance.get("sourceSeeds")
    if not isinstance(source_seeds, list) or len(source_seeds) != 96:
        raise Refusal("source seed universe missing")
    if any(not isinstance(seed, int) or isinstance(seed, bool) or seed <= 0 for seed in source_seeds):
        raise Refusal("source seed invalid")
    if len(set(source_seeds)) != 96:
        raise Refusal("source seed reuse")
    if provenance.get("sourceSeedsSha256") != canonical_sha256(sorted(source_seeds)):
        raise Refusal("source seed binding failed")
    return set(source_seeds)


def _validate_source_records(dataset: dict[str, Any]) -> dict[str, dict[str, Any]]:
    records = dataset.get("records")
    if not isinstance(records, list) or len(records) != 48:
        raise Refusal("expected all 48 source records")
    by_id: dict[str, dict[str, Any]] = {}
    counts: dict[str, int] = {}
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("geometryId"), str):
            raise Refusal("invalid source record")
        gid = record["geometryId"]
        if gid in by_id:
            raise Refusal("duplicate source geometry")
        by_id[gid] = record
        classification = record.get("classification")
        counts[classification] = counts.get(classification, 0) + 1
        if record.get("executionComplete") is not True or not isinstance(record.get("scientificallyEligible"), bool):
            raise Refusal("source execution/scientific state changed")
        role = record.get("role")
        if role not in ALLOWED_ROLES:
            raise Refusal("source role invalid")
        expected_role = "internal-holdout" if gid in INTERNAL_HOLDOUT_IDS else None
        if gid in CONTINUATION_GEOMETRY_IDS and expected_role and role != expected_role:
            raise Refusal("internal holdout role changed")
        if gid in CONTINUATION_GEOMETRY_IDS and not expected_role and role != "surrogate-training":
            raise Refusal("training role changed")
    if counts != {"PRECISION_TARGET_MET": 25, "PRECISION_ACCEPTED": 3, "ADAPTIVE_CONTINUATION_REQUIRED": 20}:
        raise Refusal("source precision classification counts changed")
    if tuple(dataset.get("adaptiveContinuationRequiredGeometryIds", [])) != CONTINUATION_GEOMETRY_IDS:
        raise Refusal("continuation geometry selection changed")
    if dataset.get("zeroHitGeometryIds") != [ZERO_HIT_SOURCE_ID]:
        raise Refusal("source zero-hit geometry changed")

    schedule = _photon_schedule()
    for gid in CONTINUATION_GEOMETRY_IDS:
        record = by_id.get(gid)
        if record is None:
            raise Refusal("continuation source record missing")
        if record.get("scientificallyEligible") is not False:
            raise Refusal("continuation geometry became scientifically eligible")
        geometry = record.get("geometry")
        if not isinstance(geometry, dict) or geometry.get("geometryId") != gid:
            raise Refusal("source geometry binding missing")
        if geometry.get("photonHistoriesPerBlock") != schedule[gid]:
            raise Refusal("source photon schedule changed")
        if sorted(record.get("caseIds", [])) != [f"{gid}-alis-b1", f"{gid}-alis-b2"]:
            raise Refusal("source block deleted or replaced")
        stats = record.get("statistics")
        if not isinstance(stats, dict) or stats.get("blockCount") != 2:
            raise Refusal("source statistics missing")
        values = stats.get("valuesCdM2")
        if not isinstance(values, list) or len(values) != 2:
            raise Refusal("source values missing")
        measured = classify_values(values)
        if measured["classification"] != "ADAPTIVE_CONTINUATION_REQUIRED":
            raise Refusal("selected source no longer requires continuation")
        if gid == ZERO_HIT_SOURCE_ID:
            if measured["zeroHitBlockCount"] != 1 or record.get("zeroHitCaseIds") != [f"{gid}-alis-b1"]:
                raise Refusal("ordinal-2 zero-hit evidence changed")
            if stats.get("relativeStandardErrorOfMean") is not None or stats.get("relativeStandardErrorStatus") != "NOT_COMPUTED_ZERO_HIT_PRESENT":
                raise Refusal("zero-hit RSEM must remain null")
        else:
            if measured["zeroHitBlockCount"] or stats.get("zeroHitBlockCount") != 0:
                raise Refusal("unexpected source zero hit")
            stored = stats.get("relativeStandardErrorOfMean")
            if not isinstance(stored, (int, float)) or not math.isclose(float(stored), measured["relativeStandardErrorOfMean"], rel_tol=1e-12, abs_tol=1e-15):
                raise Refusal("source RSEM changed")
    return by_id


def validate_source(
    dataset: dict[str, Any], aggregate: dict[str, Any], audit: dict[str, Any], provenance: dict[str, Any]
) -> tuple[dict[str, dict[str, Any]], set[int]]:
    dataset_required = {
        "schemaVersion": 2,
        "stageId": "twilight-surrogate-tier-1-analysis-v2",
        "status": "TIER_1_NUMERICAL_DATASET_PARTIAL_PRECISION",
        "executionComplete": True,
        "scientificallyEligible": False,
    }
    if any(dataset.get(key) != value for key, value in dataset_required.items()):
        raise Refusal("schema-v2 dataset state changed")
    aggregate_required = {
        "schemaVersion": 2,
        "stageId": "mystic-batch-v1",
        "status": "COMPLETED",
        "classification": "SCIENTIFICALLY_INELIGIBLE",
        "executionComplete": True,
        "scientificallyEligible": False,
        "caseCountPlanned": 96,
        "caseCountCompleted": 96,
        "caseCountFailed": 0,
        "syntaxCheckCount": 96,
        "solverExecutionCount": 96,
        "configuredMcPhotonsSum": 6_960_000_000,
        "completedConfiguredMcPhotonsSum": 6_960_000_000,
        "zeroHitCaseCount": 1,
    }
    if any(aggregate.get(key) != value for key, value in aggregate_required.items()):
        raise Refusal("schema-v2 aggregate state changed")
    if aggregate.get("continuationRequiredGeometryIds") != [ZERO_HIT_SOURCE_ID]:
        raise Refusal("aggregate zero-hit continuation state changed")
    audit_required = {
        "schemaVersion": 2,
        "stageId": "mystic-batch-v1",
        "status": "PASSED",
        "batchClassification": "SCIENTIFICALLY_INELIGIBLE",
        "executionComplete": True,
        "scientificallyEligible": False,
        "caseResultCount": 96,
        "incompleteGeometryEnteredTrainingEligibility": False,
        "unaffectedGeometryStatisticsVerified": True,
    }
    if any(audit.get(key) != value for key, value in audit_required.items()):
        raise Refusal("schema-v2 independent audit state changed")
    zero = audit.get("zeroHitDiagnostics")
    if not isinstance(zero, dict) or any(
        zero.get(key) != value
        for key, value in {
            "caseId": "train-0047-alis-b1",
            "geometryId": ZERO_HIT_SOURCE_ID,
            "block": 1,
            "classification": "NUMERICAL_ZERO_HIT_UNDERCONVERGED",
            "derivedFromRawOutputs": True,
        }.items()
    ):
        raise Refusal("independent zero-hit audit changed")
    source_seeds = _validate_source_provenance(dataset, aggregate, audit, provenance)
    return _validate_source_records(dataset), source_seeds


def build(
    dataset: dict[str, Any], aggregate: dict[str, Any], audit: dict[str, Any], provenance: dict[str, Any]
) -> dict[str, Any]:
    records, source_seeds = validate_source(dataset, aggregate, audit, provenance)
    all_seeds = [_seed_for(gid, block) for gid in CONTINUATION_GEOMETRY_IDS for block in range(3, 9)]
    if len(set(all_seeds)) != MAX_CONTINUATION_CASES or set(all_seeds) & source_seeds:
        raise Refusal("precomputed continuation seed freshness proof failed")
    schedule = _photon_schedule()
    cases: list[dict[str, Any]] = []
    for gid in CONTINUATION_GEOMETRY_IDS:
        record = records[gid]
        geometry_sha = canonical_sha256(record["geometry"])
        for block in range(3, 9):
            cases.append(
                {
                    "caseId": f"{gid}-precision-continuation-v2-b{block}",
                    "groupId": gid,
                    "block": block,
                    "wave": (block - 1) // 2,
                    "seed": _seed_for(gid, block),
                    "role": record["role"],
                    "photonHistories": schedule[gid],
                    "alisSpectralImportanceSamplingNm": record["geometry"]["alisSpectralImportanceSamplingNm"],
                    "geometrySha256": geometry_sha,
                    "sourceCaseIds": list(record["caseIds"]),
                    "proposalOnly": True,
                }
            )
    wave_photons = {
        str(wave): sum(case["photonHistories"] for case in cases if case["wave"] == wave) for wave in BLOCK_WAVES
    }
    if len(cases) != MAX_CONTINUATION_CASES or any(value != MAX_WAVE_PHOTONS for value in wave_photons.values()):
        raise Refusal("continuation budget calculation changed")
    proposal = {
        "schemaVersion": 2,
        "stageId": "tier1-precision-continuation-preparation-v2",
        "status": "PROPOSAL_ONLY_NOT_AUTHORIZATION",
        "proposalOnly": True,
        "scientificExecution": False,
        "automaticDispatch": False,
        "automaticContinuation": False,
        "authorizationEnabled": False,
        "authorizationOrdinalAllocated": False,
        "githubRerunAllowed": False,
        "firstAttemptOnly": True,
        "source": {
            "runId": SOURCE_RUN_ID,
            "runAttempt": SOURCE_RUN_ATTEMPT,
            "headSha": SOURCE_HEAD_SHA,
            "authorizationRef": SOURCE_AUTHORIZATION_REF,
            "executionKey": SOURCE_EXECUTION_KEY,
            "authorizationOrdinal": SOURCE_AUTHORIZATION_ORDINAL,
            "planRawSha256": SOURCE_PLAN_RAW_SHA256,
            "artifactManifestRawSha256": SOURCE_ARTIFACT_MANIFEST_RAW_SHA256,
            "historicalReproductionRawSha256": SOURCE_HISTORICAL_REPRODUCTION_RAW_SHA256,
            "artifactDigests": SOURCE_ARTIFACT_DIGESTS,
            "datasetSha256": canonical_sha256(dataset),
            "aggregateSha256": canonical_sha256(aggregate),
            "auditSha256": canonical_sha256(audit),
            "historicalTerminalConclusion": "failure",
            "correctedInterpretationOnly": True,
            "historicalEvidenceImmutable": True,
        },
        "thresholds": {"targetMaximum": TARGET_RSEM, "acceptedMaximum": ACCEPTED_MAX_RSEM},
        "waveBlocks": {str(wave): list(blocks) for wave, blocks in BLOCK_WAVES.items()},
        "initialBlocksPerGeometry": INITIAL_BLOCKS,
        "hardCapTotalBlocksPerGeometry": MAX_TOTAL_BLOCKS,
        "continuationGeometryIds": list(CONTINUATION_GEOMETRY_IDS),
        "continuationGeometryCount": len(CONTINUATION_GEOMETRY_IDS),
        "sourceRecords": [
            {
                "geometryId": gid,
                "role": records[gid]["role"],
                "caseIds": list(records[gid]["caseIds"]),
                "valuesCdM2": list(records[gid]["statistics"]["valuesCdM2"]),
                "zeroHitCaseIds": list(records[gid].get("zeroHitCaseIds", [])),
                "geometry": records[gid]["geometry"],
            }
            for gid in CONTINUATION_GEOMETRY_IDS
        ],
        "photonScheduleGeometryIds": {str(key): list(value) for key, value in GEOMETRIES_BY_PHOTONS.items()},
        "maximumCasesPerWave": MAX_WAVE_CASES,
        "maximumConfiguredPhotonHistoriesPerWave": MAX_WAVE_PHOTONS,
        "maximumContinuationCases": MAX_CONTINUATION_CASES,
        "maximumConfiguredContinuationPhotonHistories": MAX_CONTINUATION_PHOTONS,
        "potentialCases": cases,
        "seedProof": {
            "sourceSeedCount": len(source_seeds),
            "sourceSeedsSha256": canonical_sha256(sorted(source_seeds)),
            "continuationSeedCount": len(all_seeds),
            "continuationSeedsSha256": canonical_sha256(all_seeds),
            "allContinuationSeedsUnique": True,
            "sourceContinuationOverlap": [],
            "seedsConsumedOnDispatchEvenOnFailure": True,
        },
        "stoppingRule": {
            "evaluateOnlyAfterCompleteAuditedTwoBlockWave": True,
            "allOriginalAndContinuationBlocksPreserved": True,
            "targetIfRsemAtMost": TARGET_RSEM,
            "acceptedIfRsemAboveTargetAndAtMost": ACCEPTED_MAX_RSEM,
            "continueIfRsemAboveAcceptedAndBelowCap": True,
            "zeroHitKeepsRsemNull": True,
            "zeroHitContinuesUntilCap": True,
            "noEpsilonSubstitution": True,
            "noSelectiveBlockDeletion": True,
        },
        "freshIdentityRule": {
            "separateAuthorizationRequiredForEachWave": True,
            "nextVerifiedUnusedMonotonicOrdinalRequired": True,
            "freshExecutionKeyRequired": True,
            "onePurposeAuthorizationCommitRequired": True,
            "exactHeadWorkflowDispatchRequired": True,
            "runAttemptMustEqual": 1,
            "githubRerunForbidden": True,
            "identityAndSeedsConsumedOnDispatch": True,
        },
        "surrogateFitAuthorized": False,
        "tier2AutomaticallyAuthorized": False,
        "productionPromotionAuthorized": False,
        "boundary": "proposal and contract preparation only; no authorization, dispatch, scientific execution, surrogate fit, or production claim",
    }
    proposal["proposalSha256"] = canonical_sha256(proposal)
    return proposal


def authorization_template(proposal: dict[str, Any], wave: int) -> dict[str, Any]:
    if wave not in BLOCK_WAVES:
        raise Refusal("invalid continuation wave")
    return {
        "schemaVersion": 2,
        "stageId": "tier1-precision-continuation-authorization-template-v2",
        "proposalSha256": proposal.get("proposalSha256"),
        "wave": wave,
        "enabled": False,
        "authorizationOrdinal": None,
        "executionKey": None,
        "authorizationCommit": None,
        "activeGeometryIds": None,
        "automaticDispatch": False,
        "githubRerunAllowed": False,
        "firstAttemptOnly": True,
        "onePurposeCommitRequired": True,
    }


def wave_cases(proposal: dict[str, Any], wave: int, active_geometry_ids: Iterable[str]) -> list[dict[str, Any]]:
    if proposal.get("status") != "PROPOSAL_ONLY_NOT_AUTHORIZATION" or wave not in BLOCK_WAVES:
        raise Refusal("invalid proposal or wave")
    active = tuple(sorted(active_geometry_ids))
    if not active or len(set(active)) != len(active) or not set(active) <= set(CONTINUATION_GEOMETRY_IDS):
        raise Refusal("invalid active continuation geometry set")
    cases = [case for case in proposal["potentialCases"] if case["wave"] == wave and case["groupId"] in active]
    if len(cases) != len(active) * 2:
        raise Refusal("wave case universe incomplete")
    if len(cases) > MAX_WAVE_CASES or sum(case["photonHistories"] for case in cases) > MAX_WAVE_PHOTONS:
        raise Refusal("wave exceeds preregistered budget")
    return cases


def aggregate_wave(
    proposal: dict[str, Any], wave: int, active_geometry_ids: Iterable[str], results: list[dict[str, Any]]
) -> dict[str, Any]:
    active = tuple(sorted(active_geometry_ids))
    planned_rows = wave_cases(proposal, wave, active)
    planned = {case["caseId"]: case for case in planned_rows}
    observed: dict[str, dict[str, Any]] = {}
    structural: list[dict[str, Any]] = []
    execution: list[dict[str, Any]] = []
    zero_hits: list[dict[str, Any]] = []
    values: dict[str, list[dict[str, Any]]] = {}
    for result in results:
        if not isinstance(result, dict):
            structural.append({"code": "invalid-result-row"})
            continue
        case_id = result.get("caseId")
        if case_id not in planned or case_id in observed:
            structural.append({"code": "unplanned-or-duplicate-result", "caseId": case_id})
            continue
        observed[case_id] = result
        expected = planned[case_id]
        for key in ("seed", "role", "photonHistories", "alisSpectralImportanceSamplingNm", "geometrySha256"):
            if result.get(key) != expected[key]:
                structural.append({"code": "case-identity-drift", "caseId": case_id, "field": key})
        if result.get("status") != "COMPLETED":
            execution.append({"code": "case-not-completed", "caseId": case_id})
            continue
        syntax, solver = result.get("syntax"), result.get("solver")
        if not isinstance(syntax, dict) or syntax.get("exitCode") != 0 or syntax.get("timedOut") is not False:
            execution.append({"code": "syntax-failure", "caseId": case_id})
            continue
        if not isinstance(solver, dict) or solver.get("exitCode") != 0 or solver.get("timedOut") is not False:
            execution.append({"code": "solver-failure", "caseId": case_id})
            continue
        if result.get("syntaxCheckCount") != 1 or result.get("solverExecutionCount") != 1:
            structural.append({"code": "execution-count", "caseId": case_id})
            continue
        if any(not is_sha256(result.get(name)) for name in ("artifactSha256", "inputSha256", "radianceOutputSha256", "stdOutputSha256", "runtimeSha256")):
            structural.append({"code": "hash-contract", "caseId": case_id})
            continue
        try:
            value = _finite(result.get("valueCdM2"), "continuation value", nonnegative=True)
            nodes = [_finite(node, "radiance node", nonnegative=True) for node in result.get("selectedNodeRadiance", [])]
        except Refusal as exc:
            structural.append({"code": "numeric-contract", "caseId": case_id, "detail": str(exc)})
            continue
        if len(nodes) != 15 or ((value == 0.0) != all(node == 0.0 for node in nodes)):
            structural.append({"code": "zero-estimator-inconsistent", "caseId": case_id})
            continue
        row = {"caseId": case_id, "block": expected["block"], "valueCdM2": value, "zeroHit": value == 0.0}
        values.setdefault(expected["groupId"], []).append(row)
        if value == 0.0:
            zero_hits.append({"caseId": case_id, "geometryId": expected["groupId"], "block": expected["block"], "derivedFromRawOutputs": True})
    for case_id in sorted(set(planned) - set(observed)):
        structural.append({"code": "missing-result", "caseId": case_id})
    failed = bool(structural or execution)
    return {
        "schemaVersion": 2,
        "stageId": "tier1-precision-continuation-wave-aggregate-v2",
        "status": "FAILED" if failed else "COMPLETED",
        "classification": "STRUCTURAL_OR_EXECUTION_FAILURE" if failed else "CONTINUATION_WAVE_EXECUTION_COMPLETE",
        "executionComplete": not failed,
        "scientificallyEligible": False,
        "proposalSha256": proposal["proposalSha256"],
        "wave": wave,
        "activeGeometryIds": list(active),
        "caseCountPlanned": len(planned),
        "caseCountObserved": len(observed),
        "configuredPhotonHistories": sum(case["photonHistories"] for case in planned.values()),
        "valuesByGeometry": {gid: sorted(rows, key=lambda row: row["block"]) for gid, rows in sorted(values.items())},
        "zeroHitDiagnostics": sorted(zero_hits, key=lambda row: row["caseId"]),
        "structuralFailures": structural,
        "executionFailures": execution,
        "additionalExecutionAutomaticallyAuthorized": False,
    }


def analyze_waves(proposal: dict[str, Any], wave_aggregates: list[dict[str, Any]]) -> dict[str, Any]:
    source_records = {case["groupId"]: case for case in proposal["potentialCases"] if case["block"] == 3}
    source_values = {
        gid: list(next(point for point in proposal["sourceRecords"] if point["geometryId"] == gid)["valuesCdM2"])
        for gid in CONTINUATION_GEOMETRY_IDS
    } if "sourceRecords" in proposal else None
    if source_values is None:
        raise Refusal("proposal source records missing")
    continuation: dict[str, list[dict[str, Any]]] = {gid: [] for gid in CONTINUATION_GEOMETRY_IDS}
    ordered = sorted(wave_aggregates, key=lambda row: row.get("wave", -1))
    if [row.get("wave") for row in ordered] != list(range(1, len(ordered) + 1)):
        raise Refusal("waves must be contiguous from wave one")
    expected_active = list(CONTINUATION_GEOMETRY_IDS)
    for aggregate in ordered:
        if aggregate.get("status") != "COMPLETED" or aggregate.get("executionComplete") is not True:
            raise Refusal("cannot analyze failed or incomplete wave")
        wave = aggregate.get("wave")
        if wave not in BLOCK_WAVES or aggregate.get("proposalSha256") != proposal.get("proposalSha256"):
            raise Refusal("wave provenance invalid")
        if aggregate.get("activeGeometryIds") != expected_active:
            raise Refusal("wave active set violates preregistered stopping rule")
        for gid, rows in aggregate.get("valuesByGeometry", {}).items():
            if gid not in continuation:
                raise Refusal("unplanned continuation geometry")
            continuation[gid].extend(rows)
        expected_active = []
        for gid in CONTINUATION_GEOMETRY_IDS:
            rows = sorted(continuation[gid], key=lambda row: row["block"])
            measured = classify_values(source_values[gid] + [row["valueCdM2"] for row in rows])
            if measured["classification"] == "ADAPTIVE_CONTINUATION_REQUIRED":
                expected_active.append(gid)
    points: list[dict[str, Any]] = []
    for gid in CONTINUATION_GEOMETRY_IDS:
        rows = sorted(continuation[gid], key=lambda row: row["block"])
        blocks = [row["block"] for row in rows]
        if blocks and blocks != list(range(3, max(blocks) + 1)):
            raise Refusal("continuation blocks are not additive and contiguous")
        values = source_values[gid] + [row["valueCdM2"] for row in rows]
        measured = classify_values(values)
        points.append({"geometryId": gid, "role": source_records[gid]["role"], **measured})
    next_ids = [point["geometryId"] for point in points if point["classification"] == "ADAPTIVE_CONTINUATION_REQUIRED"]
    return {
        "schemaVersion": 2,
        "stageId": "tier1-precision-continuation-analysis-v2",
        "status": "CONTINUATION_ANALYZED",
        "points": points,
        "nextWaveGeometryIds": next_ids,
        "exhaustedGeometryIds": [point["geometryId"] for point in points if point["classification"].startswith("PRECISION_CONTINUATION_EXHAUSTED")],
        "scientificallyEligible": all(point["scientificallyEligible"] for point in points),
        "additionalExecutionAutomaticallyAuthorized": False,
        "surrogateFitAuthorized": False,
        "productionPromotionAuthorized": False,
    }
