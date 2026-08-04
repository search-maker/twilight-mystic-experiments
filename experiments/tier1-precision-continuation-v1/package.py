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
CONTINUATION_SEED_BASE = 930_000
ALLOWED_ROLES = {"surrogate-training", "internal-holdout"}
ALLOWED_IMPORTANCE_NM = {500.0, 550.0, 600.0}
HEX = set("0123456789abcdef")


class Refusal(RuntimeError):
    pass


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= HEX


def finite_positive(value: Any, name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise Refusal(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise Refusal(f"{name} must be finite and positive")
    return result


def classify_rsem(rsem: Any) -> str:
    if not isinstance(rsem, (int, float)) or isinstance(rsem, bool):
        raise Refusal("invalid RSEM")
    value = float(rsem)
    if not math.isfinite(value) or value < 0:
        raise Refusal("invalid RSEM")
    if value <= TARGET_RSEM:
        return "PRECISION_TARGET_MET"
    if value <= ACCEPTED_MAX_RSEM:
        return "PRECISION_ACCEPTED"
    return "ADAPTIVE_CONTINUATION_REQUIRED"


def rsem(values: Iterable[float]) -> float:
    rows = [finite_positive(value, "block value") for value in values]
    if len(rows) < 2:
        raise Refusal("at least two blocks are required")
    mean = statistics.fmean(rows)
    return statistics.stdev(rows) / math.sqrt(len(rows)) / mean


def required_total_blocks(source_rsem: float) -> int:
    if classify_rsem(source_rsem) != "ADAPTIVE_CONTINUATION_REQUIRED":
        return INITIAL_BLOCKS
    projected = math.ceil(INITIAL_BLOCKS * (float(source_rsem) / TARGET_RSEM) ** 2)
    return min(MAX_TOTAL_BLOCKS, max(INITIAL_BLOCKS + 1, projected))


def _validate_artifacts(provenance: dict[str, Any]) -> None:
    artifacts = provenance.get("artifacts")
    required_names = {
        "twilight-surrogate-tier-1-execution-preflight",
        "twilight-surrogate-tier-1-aggregate",
        "twilight-surrogate-tier-1-audit",
        "twilight-surrogate-tier-1-analysis",
    }
    if not isinstance(artifacts, list):
        raise Refusal("artifact provenance missing")
    by_name: dict[str, dict[str, Any]] = {}
    for artifact in artifacts:
        if not isinstance(artifact, dict) or not isinstance(artifact.get("name"), str):
            raise Refusal("invalid artifact provenance row")
        name = artifact["name"]
        if name in by_name:
            raise Refusal("duplicate artifact provenance")
        by_name[name] = artifact
    if set(by_name) != required_names:
        raise Refusal("required artifacts missing or unexpected")
    run_id = provenance.get("runId")
    for artifact in by_name.values():
        if artifact.get("expired") is not False:
            raise Refusal("expired artifact")
        if artifact.get("runId") != run_id:
            raise Refusal("artifact belongs to another run")
        digest = artifact.get("digest")
        if not isinstance(digest, str) or not digest.startswith("sha256:") or not is_sha256(digest[7:]):
            raise Refusal("invalid artifact digest")


def _validate_provenance(
    dataset: dict[str, Any], aggregate: dict[str, Any], audit: dict[str, Any], provenance: dict[str, Any]
) -> None:
    if provenance.get("runAttempt") != 1:
        raise Refusal("source is not first attempt")
    if provenance.get("event") != "workflow_dispatch":
        raise Refusal("source event changed")
    if not isinstance(provenance.get("runId"), int) or provenance["runId"] < 1:
        raise Refusal("source run ID invalid")
    head_sha = provenance.get("headSha")
    if not isinstance(head_sha, str) or len(head_sha) != 40 or set(head_sha) > HEX:
        raise Refusal("source head SHA invalid")
    required_flags = (
        "artifactsComplete",
        "sourceProvenanceValid",
        "hashesValid",
        "seedsValid",
        "photonAccountingValid",
        "firstAttemptAuditPassed",
    )
    if any(provenance.get(name) is not True for name in required_flags):
        raise Refusal("source provenance validation failed")
    bindings = provenance.get("bindings")
    expected = {
        "datasetSha256": canonical_sha256(dataset),
        "aggregateSha256": canonical_sha256(aggregate),
        "auditSha256": canonical_sha256(audit),
    }
    if not isinstance(bindings, dict) or any(bindings.get(key) != value for key, value in expected.items()):
        raise Refusal("source hash binding failed")
    _validate_artifacts(provenance)


def _validate_source_cases(dataset: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    cases = dataset.get("cases")
    if not isinstance(cases, list) or len(cases) != 96:
        raise Refusal("source case contract changed")
    by_id: dict[str, dict[str, Any]] = {}
    by_group: dict[str, list[dict[str, Any]]] = {}
    seeds: set[int] = set()
    photon_sum = 0
    for case in cases:
        if not isinstance(case, dict):
            raise Refusal("invalid source case")
        case_id = case.get("caseId")
        group_id = case.get("groupId")
        if not isinstance(case_id, str) or case_id in by_id or not isinstance(group_id, str):
            raise Refusal("duplicate or invalid source case ID")
        if case.get("block") not in {1, 2} or case.get("role") not in ALLOWED_ROLES:
            raise Refusal("source block or role changed")
        importance = float(case.get("alisSpectralImportanceSamplingNm", -1))
        if importance not in ALLOWED_IMPORTANCE_NM:
            raise Refusal("source importance wavelength changed")
        seed = case.get("seed")
        if not isinstance(seed, int) or seed in seeds:
            raise Refusal("source seed missing or reused")
        photons = case.get("photonHistories")
        if not isinstance(photons, int) or photons <= 0:
            raise Refusal("source photon allocation invalid")
        geometry_sha = case.get("geometrySha256")
        if not is_sha256(geometry_sha):
            raise Refusal("source geometry binding missing")
        seeds.add(seed)
        photon_sum += photons
        by_id[case_id] = case
        by_group.setdefault(group_id, []).append(case)
    if photon_sum != 6_960_000_000:
        raise Refusal("source photon accounting changed")
    if len(by_group) != 48 or any(sorted(row["block"] for row in group) != [1, 2] for group in by_group.values()):
        raise Refusal("source block set changed")
    return by_id, by_group


def validate_source(
    dataset: dict[str, Any], aggregate: dict[str, Any], audit: dict[str, Any], provenance: dict[str, Any]
) -> list[dict[str, Any]]:
    required_dataset = {
        "schemaVersion": 1,
        "stageId": "twilight-surrogate-tier-1-analysis-v1",
        "status": "TIER_1_NUMERICAL_DATASET_COMPLETE",
        "geometryCount": 48,
        "caseCount": 96,
        "configuredMcPhotonsSum": 6_960_000_000,
        "blocksPerGeometry": 2,
        "allCasesFirstAttempt": True,
        "aggregatePassed": True,
        "independentAuditPassed": True,
        "sourceProvenanceValidated": True,
        "hashValidationPassed": True,
        "seedValidationPassed": True,
        "photonAccountingPassed": True,
    }
    stale = {key: (dataset.get(key), value) for key, value in required_dataset.items() if dataset.get(key) != value}
    if stale:
        raise Refusal(f"dataset contract changed: {stale}")
    thresholds = dataset.get("precisionThresholds")
    if thresholds != {"targetMaximum": TARGET_RSEM, "acceptedMaximum": ACCEPTED_MAX_RSEM}:
        raise Refusal("precision thresholds changed")

    required_aggregate = {
        "classification": "BATCH_NUMERICALLY_COMPLETE",
        "caseCountPlanned": 96,
        "caseCountCompleted": 96,
        "caseCountFailed": 0,
        "syntaxCheckCount": 96,
        "solverExecutionCount": 96,
        "configuredMcPhotonsSum": 6_960_000_000,
        "completedConfiguredMcPhotonsSum": 6_960_000_000,
    }
    if any(aggregate.get(key) != value for key, value in required_aggregate.items()):
        raise Refusal("aggregate failed or changed")
    required_audit = {
        "status": "PASSED",
        "caseResultCount": 96,
        "planValidationPassed": True,
        "seedValidationPassed": True,
        "hashValidationPassed": True,
        "photonAccountingPassed": True,
        "firstAttemptValidationPassed": True,
    }
    if any(audit.get(key) != value for key, value in required_audit.items()):
        raise Refusal("independent audit failed or changed")
    _validate_provenance(dataset, aggregate, audit, provenance)
    source_cases, cases_by_group = _validate_source_cases(dataset)

    geometries = dataset.get("geometries")
    if not isinstance(geometries, list) or len(geometries) != 48:
        raise Refusal("source geometry count changed")
    geometry_map: dict[str, dict[str, Any]] = {}
    for geometry in geometries:
        if not isinstance(geometry, dict) or not isinstance(geometry.get("geometryId"), str):
            raise Refusal("invalid source geometry")
        geometry_id = geometry["geometryId"]
        if geometry_id in geometry_map:
            raise Refusal("duplicate source geometry")
        geometry_map[geometry_id] = geometry
    if set(geometry_map) != set(cases_by_group):
        raise Refusal("geometry/case universe mismatch")

    records = dataset.get("records")
    if not isinstance(records, list) or len(records) != 48:
        raise Refusal("record count changed")
    seen: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            raise Refusal("invalid record")
        geometry_id = record.get("geometryId")
        if not isinstance(geometry_id, str) or geometry_id in seen or geometry_id not in geometry_map:
            raise Refusal("record geometry invalid or duplicated")
        seen.add(geometry_id)
        group = cases_by_group[geometry_id]
        roles = {case["role"] for case in group}
        photons = {case["photonHistories"] for case in group}
        importance = {float(case["alisSpectralImportanceSamplingNm"]) for case in group}
        geometry_sha = canonical_sha256(geometry_map[geometry_id])
        if len(roles) != 1 or record.get("role") != next(iter(roles)):
            raise Refusal("record role changed")
        if len(photons) != 1 or record.get("photonHistoriesPerBlock") != next(iter(photons)):
            raise Refusal("record photon allocation changed")
        if len(importance) != 1 or float(record.get("alisSpectralImportanceSamplingNm", -1)) != next(iter(importance)):
            raise Refusal("record importance wavelength changed")
        if any(case["geometrySha256"] != geometry_sha for case in group):
            raise Refusal("source geometry changed")
        expected_case_ids = sorted(case["caseId"] for case in group)
        if sorted(record.get("caseIds", [])) != expected_case_ids:
            raise Refusal("source block deleted or replaced")
        stats = record.get("statistics")
        if not isinstance(stats, dict) or stats.get("blockCount") != INITIAL_BLOCKS:
            raise Refusal("source block count changed")
        values = stats.get("blockValuesCdM2")
        if not isinstance(values, list) or len(values) != INITIAL_BLOCKS:
            raise Refusal("source block values missing")
        computed = rsem(values)
        stored = stats.get("relativeStandardErrorOfMean")
        if not isinstance(stored, (int, float)) or not math.isclose(float(stored), computed, rel_tol=1e-12, abs_tol=1e-15):
            raise Refusal("RSEM calculation does not match contract")
        classification = classify_rsem(computed)
        if record.get("classification") != classification:
            raise Refusal("source classification changed")
        if any(case_id not in source_cases for case_id in expected_case_ids):
            raise Refusal("record references unknown source case")
    return records


def build(
    dataset: dict[str, Any], aggregate: dict[str, Any], audit: dict[str, Any], provenance: dict[str, Any]
) -> dict[str, Any]:
    records = validate_source(dataset, aggregate, audit, provenance)
    used_seeds = {case["seed"] for case in dataset["cases"]}
    continuation_cases: list[dict[str, Any]] = []
    points: list[dict[str, Any]] = []
    ordinal = 0
    for record in sorted(records, key=lambda row: row["geometryId"]):
        geometry_id = record["geometryId"]
        source_rsem = float(record["statistics"]["relativeStandardErrorOfMean"])
        source_classification = classify_rsem(source_rsem)
        total_blocks = required_total_blocks(source_rsem)
        additional = total_blocks - INITIAL_BLOCKS
        fresh_seeds: list[int] = []
        for block in range(INITIAL_BLOCKS + 1, total_blocks + 1):
            ordinal += 1
            seed = CONTINUATION_SEED_BASE + ordinal
            if seed in used_seeds:
                raise Refusal("continuation seed reuse")
            used_seeds.add(seed)
            fresh_seeds.append(seed)
            continuation_cases.append(
                {
                    "ordinal": ordinal,
                    "caseId": f"{geometry_id}-precision-continuation-b{block}",
                    "groupId": geometry_id,
                    "block": block,
                    "seed": seed,
                    "role": record["role"],
                    "photonHistories": record["photonHistoriesPerBlock"],
                    "alisSpectralImportanceSamplingNm": record["alisSpectralImportanceSamplingNm"],
                    "geometrySha256": canonical_sha256(
                        next(item for item in dataset["geometries"] if item["geometryId"] == geometry_id)
                    ),
                    "sourceCaseIds": sorted(record["caseIds"]),
                    "proposalOnly": True,
                }
            )
        points.append(
            {
                "geometryId": geometry_id,
                "role": record["role"],
                "sourceClassification": source_classification,
                "sourceRsem": source_rsem,
                "sourceBlockCount": INITIAL_BLOCKS,
                "requiredTotalBlockCount": total_blocks,
                "additionalBlockCount": additional,
                "hardCapTotalBlocks": MAX_TOTAL_BLOCKS,
                "freshSeeds": fresh_seeds,
                "sourceBlockValuesCdM2": list(record["statistics"]["blockValuesCdM2"]),
            }
        )
    source_bindings = {
        "datasetSha256": canonical_sha256(dataset),
        "aggregateSha256": canonical_sha256(aggregate),
        "auditSha256": canonical_sha256(audit),
        "provenanceSha256": canonical_sha256(provenance),
    }
    proposal = {
        "schemaVersion": 1,
        "stageId": "tier1-precision-continuation-proposal-v1",
        "status": "PROPOSAL_ONLY_NOT_AUTHORIZATION",
        "proposalOnly": True,
        "scientificExecution": False,
        "automaticDispatch": False,
        "automaticContinuation": False,
        "githubRerunAllowed": False,
        "thresholds": {
            "targetMaximum": TARGET_RSEM,
            "acceptedMaximum": ACCEPTED_MAX_RSEM,
            "classifications": [
                "PRECISION_TARGET_MET",
                "PRECISION_ACCEPTED",
                "ADAPTIVE_CONTINUATION_REQUIRED",
            ],
        },
        "initialBlocksPerGeometry": INITIAL_BLOCKS,
        "hardCapTotalBlocksPerGeometry": MAX_TOTAL_BLOCKS,
        "sourceRunId": provenance["runId"],
        "sourceRunAttempt": provenance["runAttempt"],
        "sourceBindings": source_bindings,
        "pointCount": len(points),
        "continuationGeometryCount": sum(point["additionalBlockCount"] > 0 for point in points),
        "caseCount": len(continuation_cases),
        "configuredContinuationPhotonHistories": sum(case["photonHistories"] for case in continuation_cases),
        "points": points,
        "cases": continuation_cases,
        "authorizationEnabled": False,
        "authorizationOrdinalAllocated": False,
        "surrogateFitAuthorized": False,
        "tier2AutomaticallyAuthorized": False,
        "productionPromotionAuthorized": False,
        "boundary": "bounded proposal only; a separate one-purpose authorization commit and first-attempt dispatch are required",
    }
    proposal["proposalSha256"] = canonical_sha256(proposal)
    return proposal


def authorization_template(proposal: dict[str, Any]) -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "stageId": "tier1-precision-continuation-authorization-template-v1",
        "enabled": False,
        "authorizationOrdinal": None,
        "executionKey": None,
        "authorizationCommit": None,
        "proposalSha256": proposal.get("proposalSha256", canonical_sha256(proposal)),
        "automaticDispatch": False,
        "githubRerunAllowed": False,
        "onePurposeCommitRequired": True,
        "firstAttemptOnly": True,
    }


def refuse_duplicate_execution(proposal: dict[str, Any], prior_runs: list[dict[str, Any]]) -> None:
    proposal_sha = proposal.get("proposalSha256")
    for run in prior_runs:
        if not isinstance(run, dict):
            raise Refusal("invalid prior-run row")
        if run.get("proposalSha256") == proposal_sha:
            raise Refusal("duplicate continuation proposal execution")
        if run.get("authorizationOrdinal") is not None and run.get("authorizationOrdinal") == run.get("requestedOrdinal"):
            raise Refusal("authorization ordinal already consumed")


def aggregate_results(proposal: dict[str, Any], results: list[dict[str, Any]]) -> dict[str, Any]:
    expected = {case["caseId"]: case for case in proposal.get("cases", [])}
    if len(expected) != proposal.get("caseCount"):
        raise Refusal("proposal case universe invalid")
    seen: set[str] = set()
    index: list[dict[str, Any]] = []
    values_by_group: dict[str, list[float]] = {}
    for result in results:
        if not isinstance(result, dict):
            raise Refusal("invalid result row")
        case_id = result.get("caseId")
        expected_case = expected.get(case_id)
        if expected_case is None or case_id in seen:
            raise Refusal("unplanned or duplicate result")
        seen.add(case_id)
        required = {
            "seed": expected_case["seed"],
            "role": expected_case["role"],
            "photonHistories": expected_case["photonHistories"],
            "alisSpectralImportanceSamplingNm": expected_case["alisSpectralImportanceSamplingNm"],
            "geometrySha256": expected_case["geometrySha256"],
            "status": "COMPLETED",
            "syntaxCheckCount": 1,
            "solverExecutionCount": 1,
        }
        if any(result.get(key) != value for key, value in required.items()):
            raise Refusal("case contract failed")
        solver = result.get("solver")
        syntax = result.get("syntax")
        if not isinstance(solver, dict) or solver.get("exitCode") != 0 or solver.get("timedOut") is not False:
            raise Refusal("solver result failed")
        if not isinstance(syntax, dict) or syntax.get("exitCode") != 0 or syntax.get("timedOut") is not False:
            raise Refusal("syntax result failed")
        for name in ("artifactSha256", "inputSha256", "outputSha256", "runtimeSha256"):
            if not is_sha256(result.get(name)):
                raise Refusal("case hash contract failed")
        value = finite_positive(result.get("valueCdM2"), "continuation value")
        values_by_group.setdefault(expected_case["groupId"], []).append(value)
        index.append({"caseId": case_id, "artifactSha256": result["artifactSha256"]})
    if seen != set(expected):
        raise Refusal("missing continuation result")
    return {
        "schemaVersion": 1,
        "stageId": "tier1-precision-continuation-aggregate-v1",
        "status": "COMPLETED",
        "classification": "CONTINUATION_NUMERICALLY_COMPLETE",
        "proposalSha256": proposal["proposalSha256"],
        "caseCountPlanned": len(expected),
        "caseCountCompleted": len(results),
        "configuredPhotonHistories": proposal["configuredContinuationPhotonHistories"],
        "completedPhotonHistories": sum(case["photonHistories"] for case in expected.values()),
        "valuesByGeometry": {key: values_by_group[key] for key in sorted(values_by_group)},
        "caseIndex": sorted(index, key=lambda row: row["caseId"]),
        "automaticAuthorization": False,
        "productionPromotion": False,
    }


def independent_audit(proposal: dict[str, Any], aggregate: dict[str, Any], results: list[dict[str, Any]]) -> dict[str, Any]:
    rebuilt = aggregate_results(proposal, results)
    if rebuilt != aggregate:
        raise Refusal("aggregate does not reproduce independently")
    return {
        "schemaVersion": 1,
        "stageId": "tier1-precision-continuation-audit-v1",
        "status": "PASSED",
        "proposalSha256": proposal["proposalSha256"],
        "aggregateSha256": canonical_sha256(aggregate),
        "caseResultCount": len(results),
        "duplicateRunRefused": True,
        "seedValidationPassed": True,
        "hashValidationPassed": True,
        "photonAccountingPassed": True,
        "blockDeletionDetected": True,
        "automaticAuthorization": False,
        "productionPromotion": False,
    }


def final_analysis(proposal: dict[str, Any], aggregate: dict[str, Any], audit: dict[str, Any]) -> dict[str, Any]:
    if aggregate.get("status") != "COMPLETED" or audit.get("status") != "PASSED":
        raise Refusal("continuation aggregate or audit failed")
    if aggregate.get("proposalSha256") != proposal.get("proposalSha256") or audit.get("proposalSha256") != proposal.get("proposalSha256"):
        raise Refusal("continuation provenance mismatch")
    point_map = {point["geometryId"]: point for point in proposal["points"]}
    rows: list[dict[str, Any]] = []
    for geometry_id in sorted(point_map):
        point = point_map[geometry_id]
        continuation = aggregate["valuesByGeometry"].get(geometry_id, [])
        expected_count = point["additionalBlockCount"]
        if len(continuation) != expected_count:
            raise Refusal("continuation block count mismatch")
        values = list(point["sourceBlockValuesCdM2"]) + list(continuation)
        final_rsem = rsem(values)
        classification = classify_rsem(final_rsem)
        rows.append(
            {
                "geometryId": geometry_id,
                "role": point["role"],
                "blockCount": len(values),
                "relativeStandardErrorOfMean": final_rsem,
                "classification": classification,
                "capReached": len(values) == MAX_TOTAL_BLOCKS,
            }
        )
    return {
        "schemaVersion": 1,
        "stageId": "tier1-precision-continuation-final-analysis-v1",
        "status": "CONTINUATION_ANALYZED",
        "thresholds": proposal["thresholds"],
        "points": rows,
        "adaptiveContinuationRequiredGeometryIds": [
            row["geometryId"] for row in rows if row["classification"] == "ADAPTIVE_CONTINUATION_REQUIRED"
        ],
        "noFourthClassification": True,
        "additionalExecutionAutomaticallyAuthorized": False,
        "tier2AutomaticallyAuthorized": False,
        "surrogateFitAuthorized": False,
        "productionPromotionAuthorized": False,
    }
