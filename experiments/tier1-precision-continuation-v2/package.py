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
SOURCE_DATASET_CANONICAL_SHA256 = "0fef4b51922abcf3026cd3c1be2251972cf7cab5c4925644a82a921150f0774e"
SOURCE_AGGREGATE_CANONICAL_SHA256 = "4321a6255da3eb8a06316a2b25beb370575431f83816eeef8f0de7cad9584940"
SOURCE_AUDIT_CANONICAL_SHA256 = "52448c99047d90fc8c88aa253f0ba74aa78562c9e6f55397e15005d39aad4a94"
SOURCE_SEEDS_SHA256 = "609270965a1296608c20a9e832d027686a932b52e0b671b3c5bc4fa865ac6122"
SOURCE_CONTINUATION_RECORDS_SHA256 = "1576b45cefb38ddc4c1f4dec93b38121f5e6439654ab45e259b8ef6df650490b"
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
CIE = [0.09098, 0.13902, 0.20802, 0.323, 0.503, 0.71, 0.862, 0.954, 0.995, 0.87, 0.757, 0.631, 0.503, 0.175, 0.061]


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
    report = {
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
    return report


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
        "datasetSha256": SOURCE_DATASET_CANONICAL_SHA256,
        "aggregateSha256": SOURCE_AGGREGATE_CANONICAL_SHA256,
        "auditSha256": SOURCE_AUDIT_CANONICAL_SHA256,
    }
    if (
        canonical_sha256(dataset) != SOURCE_DATASET_CANONICAL_SHA256
        or canonical_sha256(aggregate) != SOURCE_AGGREGATE_CANONICAL_SHA256
        or canonical_sha256(audit) != SOURCE_AUDIT_CANONICAL_SHA256
    ):
        raise Refusal("corrected source payload differs from reviewed ordinal-2 evidence")
    if not isinstance(bindings, dict) or any(bindings.get(key) != value for key, value in expected.items()):
        raise Refusal("corrected source binding failed")
    source_seeds = provenance.get("sourceSeeds")
    if not isinstance(source_seeds, list) or len(source_seeds) != 96:
        raise Refusal("source seed universe missing")
    if any(not isinstance(seed, int) or isinstance(seed, bool) or seed <= 0 for seed in source_seeds):
        raise Refusal("source seed invalid")
    if len(set(source_seeds)) != 96:
        raise Refusal("source seed reuse")
    if (
        canonical_sha256(sorted(source_seeds)) != SOURCE_SEEDS_SHA256
        or provenance.get("sourceSeedsSha256") != SOURCE_SEEDS_SHA256
    ):
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
    zero_rows = audit.get("zeroHitDiagnostics")
    zero = zero_rows[0] if isinstance(zero_rows, list) and len(zero_rows) == 1 else None
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
    records = _validate_source_records(dataset)
    projected = [
        {
            "geometryId": gid,
            "role": records[gid]["role"],
            "caseIds": list(records[gid]["caseIds"]),
            "valuesCdM2": list(records[gid]["statistics"]["valuesCdM2"]),
            "zeroHitCaseIds": list(records[gid].get("zeroHitCaseIds", [])),
            "geometry": records[gid]["geometry"],
        }
        for gid in CONTINUATION_GEOMETRY_IDS
    ]
    if canonical_sha256(projected) != SOURCE_CONTINUATION_RECORDS_SHA256:
        raise Refusal("continuation source geometry or numerical evidence changed")
    return records, source_seeds


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
            "datasetSha256": SOURCE_DATASET_CANONICAL_SHA256,
            "aggregateSha256": SOURCE_AGGREGATE_CANONICAL_SHA256,
            "auditSha256": SOURCE_AUDIT_CANONICAL_SHA256,
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
        "thresholds": {"targetMaximum": TARGET_RSEM, "acceptedMaximum": ACCEPTED_MAX_RSEM},
        "waveBlocks": {str(wave): list(blocks) for wave, blocks in BLOCK_WAVES.items()},
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
            "sourceSeedsSha256": SOURCE_SEEDS_SHA256,
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
        "boundary": "proposal and contract preparation only; no authorization, dispatch, scientific execution, surrogate fit, or production claim",
    }
    proposal["proposalSha256"] = canonical_sha256(proposal)
    return proposal


def validate_proposal(proposal: dict[str, Any]) -> None:
    if not isinstance(proposal, dict):
        raise Refusal("continuation proposal missing")
    payload = dict(proposal)
    supplied_hash = payload.pop("proposalSha256", None)
    if not is_sha256(supplied_hash) or canonical_sha256(payload) != supplied_hash:
        raise Refusal("continuation proposal hash changed")
    required = {
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
        "initialBlocksPerGeometry": INITIAL_BLOCKS,
        "hardCapTotalBlocksPerGeometry": MAX_TOTAL_BLOCKS,
        "continuationGeometryIds": list(CONTINUATION_GEOMETRY_IDS),
        "continuationGeometryCount": len(CONTINUATION_GEOMETRY_IDS),
        "photonScheduleGeometryIds": {str(key): list(value) for key, value in GEOMETRIES_BY_PHOTONS.items()},
        "maximumCasesPerWave": MAX_WAVE_CASES,
        "maximumConfiguredPhotonHistoriesPerWave": MAX_WAVE_PHOTONS,
        "maximumContinuationCases": MAX_CONTINUATION_CASES,
        "maximumConfiguredContinuationPhotonHistories": MAX_CONTINUATION_PHOTONS,
        "surrogateFitAuthorized": False,
        "tier2AutomaticallyAuthorized": False,
        "productionPromotionAuthorized": False,
    }
    if any(proposal.get(key) != value for key, value in required.items()):
        raise Refusal("continuation proposal boundary changed")
    expected_source = {
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
        "datasetSha256": SOURCE_DATASET_CANONICAL_SHA256,
        "aggregateSha256": SOURCE_AGGREGATE_CANONICAL_SHA256,
        "auditSha256": SOURCE_AUDIT_CANONICAL_SHA256,
        "historicalTerminalConclusion": "failure",
        "correctedInterpretationOnly": True,
        "historicalEvidenceImmutable": True,
    }
    if proposal.get("source") != expected_source:
        raise Refusal("continuation proposal source changed")
    source_records = proposal.get("sourceRecords")
    if not isinstance(source_records, list) or canonical_sha256(source_records) != SOURCE_CONTINUATION_RECORDS_SHA256:
        raise Refusal("continuation proposal source records changed")
    records = {row.get("geometryId"): row for row in source_records if isinstance(row, dict)}
    if set(records) != set(CONTINUATION_GEOMETRY_IDS):
        raise Refusal("continuation proposal source universe changed")
    schedule = _photon_schedule()
    expected_cases: list[dict[str, Any]] = []
    for gid in CONTINUATION_GEOMETRY_IDS:
        record = records[gid]
        geometry = record.get("geometry")
        if not isinstance(geometry, dict):
            raise Refusal("continuation proposal geometry missing")
        geometry_sha = canonical_sha256(geometry)
        for block in range(3, 9):
            expected_cases.append(
                {
                    "caseId": f"{gid}-precision-continuation-v2-b{block}",
                    "groupId": gid,
                    "block": block,
                    "wave": (block - 1) // 2,
                    "seed": _seed_for(gid, block),
                    "role": record["role"],
                    "photonHistories": schedule[gid],
                    "alisSpectralImportanceSamplingNm": geometry["alisSpectralImportanceSamplingNm"],
                    "geometrySha256": geometry_sha,
                    "sourceCaseIds": list(record["caseIds"]),
                    "proposalOnly": True,
                }
            )
    if proposal.get("potentialCases") != expected_cases:
        raise Refusal("continuation proposal case universe changed")
    all_seeds = [row["seed"] for row in expected_cases]
    expected_seed_proof = {
        "sourceSeedCount": 96,
        "sourceSeedsSha256": SOURCE_SEEDS_SHA256,
        "continuationSeedCount": MAX_CONTINUATION_CASES,
        "continuationSeedsSha256": canonical_sha256(all_seeds),
        "allContinuationSeedsUnique": True,
        "sourceContinuationOverlap": [],
        "seedsConsumedOnDispatchEvenOnFailure": True,
    }
    if proposal.get("seedProof") != expected_seed_proof:
        raise Refusal("continuation proposal seed proof changed")
    expected_stopping_rule = {
        "evaluateOnlyAfterCompleteAuditedTwoBlockWave": True,
        "allOriginalAndContinuationBlocksPreserved": True,
        "targetIfRsemAtMost": TARGET_RSEM,
        "acceptedIfRsemAboveTargetAndAtMost": ACCEPTED_MAX_RSEM,
        "continueIfRsemAboveAcceptedAndBelowCap": True,
        "zeroHitKeepsRsemNull": True,
        "zeroHitContinuesUntilCap": True,
        "noEpsilonSubstitution": True,
        "noSelectiveBlockDeletion": True,
    }
    expected_fresh_identity_rule = {
        "separateAuthorizationRequiredForEachWave": True,
        "nextVerifiedUnusedMonotonicOrdinalRequired": True,
        "freshExecutionKeyRequired": True,
        "onePurposeAuthorizationCommitRequired": True,
        "exactHeadWorkflowDispatchRequired": True,
        "runAttemptMustEqual": 1,
        "githubRerunForbidden": True,
        "identityAndSeedsConsumedOnDispatch": True,
    }
    if proposal.get("stoppingRule") != expected_stopping_rule or proposal.get("freshIdentityRule") != expected_fresh_identity_rule:
        raise Refusal("continuation proposal stopping or identity rule changed")


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
    validate_proposal(proposal)
    if wave not in BLOCK_WAVES:
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


def _photopic_value(nodes: list[float]) -> float:
    return 683.002 * 10.0 * sum((value / 1000.0) * weight for value, weight in zip(nodes, CIE))


def audit_wave(
    proposal: dict[str, Any],
    wave: int,
    active_geometry_ids: Iterable[str],
    results: list[dict[str, Any]],
    aggregate: dict[str, Any],
) -> dict[str, Any]:
    active = tuple(sorted(active_geometry_ids))
    planned_rows = wave_cases(proposal, wave, active)
    planned = {case["caseId"]: case for case in planned_rows}
    observed: dict[str, dict[str, Any]] = {}
    failures: list[dict[str, Any]] = []
    values: dict[str, list[dict[str, Any]]] = {}
    zero_hits: list[dict[str, Any]] = []
    for result in results:
        if not isinstance(result, dict):
            failures.append({"code": "invalid-result-row"})
            continue
        case_id = result.get("caseId")
        if case_id not in planned or case_id in observed:
            failures.append({"code": "unplanned-or-duplicate-result", "caseId": case_id})
            continue
        observed[case_id] = result
        expected = planned[case_id]
        for key in ("seed", "role", "photonHistories", "alisSpectralImportanceSamplingNm", "geometrySha256"):
            if result.get(key) != expected[key]:
                failures.append({"code": "case-identity-drift", "caseId": case_id, "field": key})
        syntax, solver = result.get("syntax"), result.get("solver")
        if (
            result.get("status") != "COMPLETED"
            or not isinstance(syntax, dict)
            or syntax.get("exitCode") != 0
            or syntax.get("timedOut") is not False
            or not isinstance(solver, dict)
            or solver.get("exitCode") != 0
            or solver.get("timedOut") is not False
            or result.get("syntaxCheckCount") != 1
            or result.get("solverExecutionCount") != 1
        ):
            failures.append({"code": "execution-contract", "caseId": case_id})
            continue
        if any(
            not is_sha256(result.get(name))
            for name in ("artifactSha256", "inputSha256", "radianceOutputSha256", "stdOutputSha256", "runtimeSha256")
        ):
            failures.append({"code": "hash-contract", "caseId": case_id})
            continue
        try:
            nodes = [_finite(node, "raw radiance node", nonnegative=True) for node in result.get("selectedNodeRadiance", [])]
            reported_value = _finite(result.get("valueCdM2"), "reported continuation value", nonnegative=True)
        except Refusal as exc:
            failures.append({"code": "numeric-contract", "caseId": case_id, "detail": str(exc)})
            continue
        if len(nodes) != len(CIE):
            failures.append({"code": "spectral-node-count", "caseId": case_id})
            continue
        recomputed_value = _photopic_value(nodes)
        if not math.isclose(reported_value, recomputed_value, rel_tol=1e-12, abs_tol=1e-30):
            failures.append({"code": "reported-estimator-differs-from-raw-spectrum", "caseId": case_id})
            continue
        zero_hit = recomputed_value == 0.0
        row = {"caseId": case_id, "block": expected["block"], "valueCdM2": recomputed_value, "zeroHit": zero_hit}
        values.setdefault(expected["groupId"], []).append(row)
        if zero_hit:
            zero_hits.append(
                {
                    "caseId": case_id,
                    "geometryId": expected["groupId"],
                    "block": expected["block"],
                    "derivedFromRawOutputs": True,
                }
            )
    for case_id in sorted(set(planned) - set(observed)):
        failures.append({"code": "missing-result", "caseId": case_id})
    audited_values = {gid: sorted(rows, key=lambda row: row["block"]) for gid, rows in sorted(values.items())}
    expected_aggregate = {
        "schemaVersion": 2,
        "stageId": "tier1-precision-continuation-wave-aggregate-v2",
        "status": "COMPLETED",
        "classification": "CONTINUATION_WAVE_EXECUTION_COMPLETE",
        "executionComplete": True,
        "scientificallyEligible": False,
        "proposalSha256": proposal["proposalSha256"],
        "wave": wave,
        "activeGeometryIds": list(active),
        "caseCountPlanned": len(planned),
        "caseCountObserved": len(observed),
        "configuredPhotonHistories": sum(case["photonHistories"] for case in planned.values()),
        "valuesByGeometry": audited_values,
        "zeroHitDiagnostics": sorted(zero_hits, key=lambda row: row["caseId"]),
        "structuralFailures": [],
        "executionFailures": [],
        "additionalExecutionAutomaticallyAuthorized": False,
    }
    if aggregate != expected_aggregate:
        failures.append({"code": "aggregate-differs-from-independent-raw-audit"})
    report = {
        "schemaVersion": 2,
        "stageId": "tier1-precision-continuation-wave-audit-v2",
        "status": "PASSED" if not failures else "FAILED",
        "proposalSha256": proposal["proposalSha256"],
        "aggregateSha256": canonical_sha256(aggregate),
        "wave": wave,
        "activeGeometryIds": list(active),
        "caseResultCount": len(observed),
        "caseResultHashes": {case_id: canonical_sha256(result) for case_id, result in sorted(observed.items())},
        "rawValuesByGeometry": audited_values,
        "zeroHitDiagnostics": sorted(zero_hits, key=lambda row: row["caseId"]),
        "failures": failures,
        "independentlyRecomputedFromRawSelectedNodeRadiance": True,
        "additionalExecutionAutomaticallyAuthorized": False,
    }
    report["auditPayloadSha256"] = canonical_sha256(report)
    return report


def analyze_waves(
    proposal: dict[str, Any],
    wave_aggregates: list[dict[str, Any]],
    wave_audits: list[dict[str, Any]],
) -> dict[str, Any]:
    validate_proposal(proposal)
    if len(wave_aggregates) != len(wave_audits):
        raise Refusal("every continuation aggregate requires an independent audit")
    source_records = {case["groupId"]: case for case in proposal["potentialCases"] if case["block"] == 3}
    source_values = {
        gid: list(next(point for point in proposal["sourceRecords"] if point["geometryId"] == gid)["valuesCdM2"])
        for gid in CONTINUATION_GEOMETRY_IDS
    } if "sourceRecords" in proposal else None
    if source_values is None:
        raise Refusal("proposal source records missing")
    continuation: dict[str, list[dict[str, Any]]] = {gid: [] for gid in CONTINUATION_GEOMETRY_IDS}
    ordered_pairs = sorted(zip(wave_aggregates, wave_audits), key=lambda pair: pair[0].get("wave", -1))
    ordered = [pair[0] for pair in ordered_pairs]
    if [row.get("wave") for row in ordered] != list(range(1, len(ordered) + 1)):
        raise Refusal("waves must be contiguous from wave one")
    expected_active = list(CONTINUATION_GEOMETRY_IDS)
    for aggregate, audit in ordered_pairs:
        if aggregate.get("status") != "COMPLETED" or aggregate.get("executionComplete") is not True:
            raise Refusal("cannot analyze failed or incomplete wave")
        wave = aggregate.get("wave")
        if wave not in BLOCK_WAVES or aggregate.get("proposalSha256") != proposal.get("proposalSha256"):
            raise Refusal("wave provenance invalid")
        if aggregate.get("activeGeometryIds") != expected_active:
            raise Refusal("wave active set violates preregistered stopping rule")
        if (
            audit.get("schemaVersion") != 2
            or audit.get("stageId") != "tier1-precision-continuation-wave-audit-v2"
            or audit.get("status") != "PASSED"
            or audit.get("failures") != []
            or audit.get("proposalSha256") != proposal.get("proposalSha256")
            or audit.get("aggregateSha256") != canonical_sha256(aggregate)
            or audit.get("wave") != wave
            or audit.get("activeGeometryIds") != expected_active
            or audit.get("independentlyRecomputedFromRawSelectedNodeRadiance") is not True
        ):
            raise Refusal("continuation wave independent audit invalid")
        audit_payload = dict(audit)
        supplied_audit_hash = audit_payload.pop("auditPayloadSha256", None)
        if not is_sha256(supplied_audit_hash) or canonical_sha256(audit_payload) != supplied_audit_hash:
            raise Refusal("continuation wave independent audit payload changed")
        expected_cases = wave_cases(proposal, wave, expected_active)
        expected_case_ids = {case["caseId"] for case in expected_cases}
        hashes = audit.get("caseResultHashes")
        if (
            audit.get("caseResultCount") != len(expected_cases)
            or not isinstance(hashes, dict)
            or set(hashes) != expected_case_ids
            or any(not is_sha256(value) for value in hashes.values())
        ):
            raise Refusal("continuation wave audited case universe invalid")
        audited_values = audit.get("rawValuesByGeometry")
        if (
            not isinstance(audited_values, dict)
            or set(audited_values) != set(expected_active)
            or audited_values != aggregate.get("valuesByGeometry")
            or audit.get("zeroHitDiagnostics") != aggregate.get("zeroHitDiagnostics")
        ):
            raise Refusal("continuation wave audited geometry universe invalid")
        for gid, rows in audited_values.items():
            if gid not in continuation:
                raise Refusal("unplanned continuation geometry")
            if (
                not isinstance(rows, list)
                or [row.get("block") for row in rows if isinstance(row, dict)] != list(BLOCK_WAVES[wave])
                or len(rows) != 2
            ):
                raise Refusal("continuation wave audited block universe invalid")
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
