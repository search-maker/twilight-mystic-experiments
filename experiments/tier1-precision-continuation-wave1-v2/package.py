from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
from typing import Any, Iterable


BASE_COMMIT_SHA = "2cb23408e73fc8e8313d483a02d8e05c58de9cff"
BASE_PACKAGE_RELATIVE_PATH = "experiments/tier1-precision-continuation-v2/package.py"
BASE_PACKAGE_RAW_SHA256 = "0ce3f817b535a15a27e4cb989a414185cab249224ea47a8de5f99a486992a037"
EVIDENCE_RAW_SHA256 = {
    "evidence/ordinal2-corrected-v2/audit-report.json": "a3b427bbd345e310f851d8839da4ff92931f9b747e6981700eb5a3878a38882b",
    "evidence/ordinal2-corrected-v2/batch-summary.json": "5041bf89000d067e644d234f2c42344dd8a2a15796a75785d9254af4af627d04",
    "evidence/ordinal2-corrected-v2/plan.json": "f19ea2eb742ca6e5ca638714128b52f3ba5167dfa23b9ff08ee19ae01416d448",
    "evidence/ordinal2-corrected-v2/tier1-numerical-dataset.json": "81db9f2c418d4b078c23586513c5ba4591f3f3a496367bd818c8701d26136c00",
}

ORDINAL1_RUN_ID = 30_906_913_329
ORDINAL1_RUN_ATTEMPT = 1
ORDINAL1_HEAD_SHA = "9ab74efabfd34799aeeb5c9220a84639861f739d"
ORDINAL1_ARTIFACT_ID = 8_891_411_443
ORDINAL1_ARTIFACT_NAME = "twilight-surrogate-tier-1-execution-preflight"
ORDINAL1_ARTIFACT_DIGEST = "sha256:154c4ab9b28d117c9213a31a88f52bc02b6d40c6b99e9222ff4c8e27868b5de3"
ORDINAL1_PLAN_RAW_SHA256 = "0c71e6f891020cf853610fb116049dc668d141eec21a90537721dba8c473386b"
ORDINAL1_SEEDS = tuple(range(910_001, 910_097))
CONSUMED_PROBE_SEEDS = (990_002, 990_003, 990_004, 990_005)

WAVE = 1
WAVE_BLOCKS = (3, 4)
EXPECTED_GEOMETRY_COUNT = 20
EXPECTED_CASE_COUNT = 40
EXPECTED_TRAINING_GEOMETRY_COUNT = 17
EXPECTED_HOLDOUT_GEOMETRY_COUNT = 3
EXPECTED_TRAINING_CASE_COUNT = 34
EXPECTED_HOLDOUT_CASE_COUNT = 6
MAX_CONFIGURED_PHOTON_HISTORIES = 5_100_000_000

PREREGISTRATION_RELATIVE_PATH = "evidence/tier1-precision-continuation-wave1-v2/preregistration.json"
AUTHORIZATION_TEMPLATE_RELATIVE_PATH = (
    "experiments/tier1-precision-continuation-wave1-v2/authorization.template.json"
)
HEX = set("0123456789abcdef")


class Refusal(RuntimeError):
    pass


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_source_sha256(path: Path) -> str:
    payload = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(payload).hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def dump_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n"


def is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= HEX


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise Refusal(f"cannot load reviewed base module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def base_module(root: Path | None = None):
    root = root or repository_root()
    path = root / BASE_PACKAGE_RELATIVE_PATH
    if canonical_source_sha256(path) != BASE_PACKAGE_RAW_SHA256:
        raise Refusal("reviewed continuation-v2 package hash changed")
    return _load_module("tier1_precision_continuation_v2_base", path)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise Refusal(f"cannot load bound JSON: {path}") from exc
    if not isinstance(value, dict):
        raise Refusal(f"bound JSON root must be an object: {path}")
    return value


def _verify_evidence_hashes(root: Path) -> None:
    for relative_path, expected_hash in EVIDENCE_RAW_SHA256.items():
        if canonical_source_sha256(root / relative_path) != expected_hash:
            raise Refusal(f"bound evidence hash changed: {relative_path}")


def _base_inputs(root: Path, base) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], list[int]]:
    _verify_evidence_hashes(root)
    evidence = root / "evidence" / "ordinal2-corrected-v2"
    dataset = _load_json(evidence / "tier1-numerical-dataset.json")
    aggregate = _load_json(evidence / "batch-summary.json")
    audit = _load_json(evidence / "audit-report.json")
    plan = _load_json(evidence / "plan.json")
    rows = plan.get("cases")
    if not isinstance(rows, list) or len(rows) != 96:
        raise Refusal("bound ordinal-2 plan case universe changed")
    source_seeds = [row.get("seed") for row in rows if isinstance(row, dict)]
    if (
        len(source_seeds) != 96
        or any(not isinstance(seed, int) or isinstance(seed, bool) or seed <= 0 for seed in source_seeds)
        or len(set(source_seeds)) != 96
        or base.canonical_sha256(sorted(source_seeds)) != base.SOURCE_SEEDS_SHA256
    ):
        raise Refusal("bound ordinal-2 seed universe changed")
    provenance = {
        "runId": base.SOURCE_RUN_ID,
        "runAttempt": base.SOURCE_RUN_ATTEMPT,
        "headSha": base.SOURCE_HEAD_SHA,
        "authorizationRef": base.SOURCE_AUTHORIZATION_REF,
        "executionKey": base.SOURCE_EXECUTION_KEY,
        "authorizationOrdinal": base.SOURCE_AUTHORIZATION_ORDINAL,
        "event": "workflow_dispatch",
        "planRawSha256": base.SOURCE_PLAN_RAW_SHA256,
        "artifactManifestRawSha256": base.SOURCE_ARTIFACT_MANIFEST_RAW_SHA256,
        "historicalReproductionRawSha256": base.SOURCE_HISTORICAL_REPRODUCTION_RAW_SHA256,
        "artifactDigests": base.SOURCE_ARTIFACT_DIGESTS,
        "historicalTerminalConclusion": "failure",
        "historicalEvidenceImmutable": True,
        "correctedInterpretationOnly": True,
        "sourceSeeds": source_seeds,
        "sourceSeedsSha256": base.SOURCE_SEEDS_SHA256,
        "bindings": {
            "datasetSha256": base.SOURCE_DATASET_CANONICAL_SHA256,
            "aggregateSha256": base.SOURCE_AGGREGATE_CANONICAL_SHA256,
            "auditSha256": base.SOURCE_AUDIT_CANONICAL_SHA256,
        },
    }
    return dataset, aggregate, audit, provenance, source_seeds


def _build_base_proposal(root: Path, base) -> tuple[dict[str, Any], list[int]]:
    dataset, aggregate, audit, provenance, source_seeds = _base_inputs(root, base)
    proposal = base.build(dataset, aggregate, audit, provenance)
    base.validate_proposal(proposal)
    return proposal, source_seeds


def _historical_seed_proof(base, source_seeds: list[int], wave_seeds: list[int]) -> dict[str, Any]:
    ordinal1 = set(ORDINAL1_SEEDS)
    ordinal2 = set(source_seeds)
    probes = set(CONSUMED_PROBE_SEEDS)
    historical = ordinal1 | ordinal2 | probes
    if len(ordinal1) != 96 or len(ordinal2) != 96 or len(probes) != 4:
        raise Refusal("historical seed source count changed")
    if len(historical) != 196:
        raise Refusal("historical seed sources unexpectedly overlap")
    if len(wave_seeds) != EXPECTED_CASE_COUNT or len(set(wave_seeds)) != EXPECTED_CASE_COUNT:
        raise Refusal("wave-1 seeds are not exactly 40 unique values")
    overlap = sorted(set(wave_seeds) & historical)
    if overlap:
        raise Refusal(f"wave-1 seed overlaps consumed historical seed: {overlap}")
    return {
        "ordinal1": {
            "runId": ORDINAL1_RUN_ID,
            "runAttempt": ORDINAL1_RUN_ATTEMPT,
            "headSha": ORDINAL1_HEAD_SHA,
            "artifactId": ORDINAL1_ARTIFACT_ID,
            "artifactName": ORDINAL1_ARTIFACT_NAME,
            "artifactDigest": ORDINAL1_ARTIFACT_DIGEST,
            "planRawSha256": ORDINAL1_PLAN_RAW_SHA256,
            "seedCount": len(ordinal1),
            "seedsSha256": canonical_sha256(sorted(ordinal1)),
        },
        "ordinal2": {
            "runId": base.SOURCE_RUN_ID,
            "runAttempt": base.SOURCE_RUN_ATTEMPT,
            "headSha": base.SOURCE_HEAD_SHA,
            "authorizationRef": base.SOURCE_AUTHORIZATION_REF,
            "executionKey": base.SOURCE_EXECUTION_KEY,
            "authorizationOrdinal": base.SOURCE_AUTHORIZATION_ORDINAL,
            "seedCount": len(ordinal2),
            "seedsSha256": canonical_sha256(sorted(ordinal2)),
        },
        "consumedProbeSeeds": {
            "seedCount": len(probes),
            "seeds": sorted(probes),
            "seedsSha256": canonical_sha256(sorted(probes)),
        },
        "historicalSeedCount": len(historical),
        "historicalSeedsSha256": canonical_sha256(sorted(historical)),
        "wave1SeedCount": len(wave_seeds),
        "wave1SeedsSha256": canonical_sha256(wave_seeds),
        "allWave1SeedsUnique": True,
        "historicalOverlap": [],
        "seedsConsumedOnDispatchEvenOnFailure": True,
    }


def build_preregistration(root: Path | None = None) -> dict[str, Any]:
    root = (root or repository_root()).resolve()
    base = base_module(root)
    proposal, source_seeds = _build_base_proposal(root, base)
    source_records = {row["geometryId"]: row for row in proposal["sourceRecords"]}
    base_cases = base.wave_cases(proposal, WAVE, base.CONTINUATION_GEOMETRY_IDS)
    cases: list[dict[str, Any]] = []
    for case_ordinal, row in enumerate(base_cases, start=1):
        source = source_records[row["groupId"]]
        cases.append(
            {
                **copy.deepcopy(row),
                "caseOrdinal": case_ordinal,
                "geometry": copy.deepcopy(source["geometry"]),
                "preservedSourceCaseIds": list(source["caseIds"]),
                "preservedSourceValuesCdM2": list(source["valuesCdM2"]),
                "preservedZeroHitCaseIds": list(source["zeroHitCaseIds"]),
            }
        )
    case_ids = [row["caseId"] for row in cases]
    wave_seeds = [row["seed"] for row in cases]
    roles = {gid: source_records[gid]["role"] for gid in base.CONTINUATION_GEOMETRY_IDS}
    training_ids = sorted(gid for gid, role in roles.items() if role == "surrogate-training")
    holdout_ids = sorted(gid for gid, role in roles.items() if role == "internal-holdout")
    photon_total = sum(row["photonHistories"] for row in cases)
    if (
        len(cases) != EXPECTED_CASE_COUNT
        or len(set(case_ids)) != EXPECTED_CASE_COUNT
        or {row["block"] for row in cases} != set(WAVE_BLOCKS)
        or len(training_ids) != EXPECTED_TRAINING_GEOMETRY_COUNT
        or len(holdout_ids) != EXPECTED_HOLDOUT_GEOMETRY_COUNT
        or sum(row["role"] == "surrogate-training" for row in cases) != EXPECTED_TRAINING_CASE_COUNT
        or sum(row["role"] == "internal-holdout" for row in cases) != EXPECTED_HOLDOUT_CASE_COUNT
        or photon_total != MAX_CONFIGURED_PHOTON_HISTORIES
    ):
        raise Refusal("frozen wave-1 scope or budget changed")
    preregistration = {
        "schemaVersion": 1,
        "stageId": "tier1-precision-continuation-wave1-preregistration-v2",
        "status": "PREPARATION_ONLY_NOT_AUTHORIZED",
        "baseCommitSha": BASE_COMMIT_SHA,
        "proposalOnly": True,
        "scientificExecution": False,
        "authorizationEnabled": False,
        "authorizationOrdinal": None,
        "authorizationRef": None,
        "executionKey": None,
        "dispatchEnabled": False,
        "workflowDispatchEnabled": False,
        "githubRerunAllowed": False,
        "sourceBindings": {
            "basePackageRelativePath": BASE_PACKAGE_RELATIVE_PATH,
            "basePackageRawSha256": BASE_PACKAGE_RAW_SHA256,
            "evidenceRawSha256": EVIDENCE_RAW_SHA256,
            "baseProposalSha256": proposal["proposalSha256"],
            "ordinal2Source": copy.deepcopy(proposal["source"]),
        },
        "wave": WAVE,
        "blocks": list(WAVE_BLOCKS),
        "geometryIds": list(base.CONTINUATION_GEOMETRY_IDS),
        "geometryCount": EXPECTED_GEOMETRY_COUNT,
        "trainingGeometryIds": training_ids,
        "internalHoldoutGeometryIds": holdout_ids,
        "roleCounts": {
            "surrogateTrainingGeometries": EXPECTED_TRAINING_GEOMETRY_COUNT,
            "internalHoldoutGeometries": EXPECTED_HOLDOUT_GEOMETRY_COUNT,
            "surrogateTrainingCases": EXPECTED_TRAINING_CASE_COUNT,
            "internalHoldoutCases": EXPECTED_HOLDOUT_CASE_COUNT,
        },
        "caseCount": EXPECTED_CASE_COUNT,
        "maximumConfiguredPhotonHistories": MAX_CONFIGURED_PHOTON_HISTORIES,
        "cases": cases,
        "seedProof": _historical_seed_proof(base, source_seeds, wave_seeds),
        "thresholds": copy.deepcopy(proposal["thresholds"]),
        "stoppingRule": copy.deepcopy(proposal["stoppingRule"]),
        "classifications": {
            "structuralOrExecutionFailure": "STRUCTURAL_OR_EXECUTION_FAILURE",
            "executionComplete": "CONTINUATION_WAVE_EXECUTION_COMPLETE",
            "zeroHitUnderconverged": "NUMERICAL_ZERO_HIT_UNDERCONVERGED",
            "continue": "ADAPTIVE_CONTINUATION_REQUIRED",
            "target": "PRECISION_TARGET_MET",
            "accepted": "PRECISION_ACCEPTED",
            "zeroHitCannotBecomeEligibleFromContinuationAlone": True,
        },
        "executionContract": {
            "runAttemptMustEqual": 1,
            "eventMustEqual": "workflow_dispatch",
            "duplicateSearchRequiredBeforeSolver": True,
            "syntaxCheckCountPerCase": 1,
            "solverExecutionCountPerCase": 1,
            "retryForbidden": True,
            "resumeForbidden": True,
            "exactCaseUniverseRequired": True,
            "requiredResultHashes": [
                "artifactSha256",
                "inputSha256",
                "radianceOutputSha256",
                "stdOutputSha256",
                "runtimeSha256",
            ],
            "rawSelectedNodeRadianceCount": len(base.CIE),
            "independentRawRecomputationRequired": True,
        },
        "preservation": {
            "originalBlocksB1B2Preserved": True,
            "historicalArtifactsImmutable": True,
            "geometryInputsUnchanged": True,
            "photonScheduleUnchanged": True,
            "rolesUnchanged": True,
            "thresholdsUnchanged": True,
            "zeroHitHandlingUnchanged": True,
            "evidenceBindingsUnchanged": True,
        },
        "boundary": "reversible wave-1 preparation only; no authorization identity, enabled dispatch, solver execution, fitting, holdout opening, Tier-2, or production action",
    }
    preregistration["preregistrationSha256"] = canonical_sha256(preregistration)
    return preregistration


def validate_preregistration(preregistration: dict[str, Any], root: Path | None = None) -> None:
    if not isinstance(preregistration, dict):
        raise Refusal("wave-1 preregistration missing")
    payload = dict(preregistration)
    supplied_hash = payload.pop("preregistrationSha256", None)
    if not is_sha256(supplied_hash) or canonical_sha256(payload) != supplied_hash:
        raise Refusal("wave-1 preregistration hash changed")
    expected = build_preregistration(root)
    if preregistration != expected:
        raise Refusal("wave-1 preregistration differs from frozen generation")


def authorization_template(preregistration: dict[str, Any], root: Path | None = None) -> dict[str, Any]:
    validate_preregistration(preregistration, root)
    template = {
        "schemaVersion": 1,
        "stageId": "tier1-precision-continuation-wave1-authorization-template-v2",
        "status": "DISABLED_TEMPLATE_NOT_AUTHORIZATION",
        "preregistrationSha256": preregistration["preregistrationSha256"],
        "wave": WAVE,
        "blocks": list(WAVE_BLOCKS),
        "caseCount": EXPECTED_CASE_COUNT,
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
    }
    template["templateSha256"] = canonical_sha256(template)
    return template


def case_contracts(preregistration: dict[str, Any], root: Path | None = None) -> list[dict[str, Any]]:
    validate_preregistration(preregistration, root)
    return [
        {
            "caseId": row["caseId"],
            "caseOrdinal": row["caseOrdinal"],
            "groupId": row["groupId"],
            "block": row["block"],
            "seed": row["seed"],
            "role": row["role"],
            "photonHistories": row["photonHistories"],
            "alisSpectralImportanceSamplingNm": row["alisSpectralImportanceSamplingNm"],
            "geometrySha256": row["geometrySha256"],
            "syntaxCheckCountExactly": 1,
            "solverExecutionCountExactly": 1,
            "retryAllowed": False,
            "attemptMustEqual": 1,
            "proposalOnly": True,
        }
        for row in preregistration["cases"]
    ]


def duplicate_run_audit(
    preregistration: dict[str, Any], candidate_title: str, existing_runs: Iterable[dict[str, Any]], root: Path | None = None
) -> dict[str, Any]:
    validate_preregistration(preregistration, root)
    if not isinstance(candidate_title, str) or not candidate_title.strip():
        raise Refusal("candidate run title missing")
    matches: list[dict[str, Any]] = []
    rows = list(existing_runs)
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("display_title"), str):
            raise Refusal("duplicate search run metadata malformed")
        if row["display_title"] == candidate_title:
            matches.append({"runId": row.get("id"), "displayTitle": row["display_title"]})
    report = {
        "schemaVersion": 1,
        "stageId": "tier1-precision-continuation-wave1-duplicate-run-audit-v2",
        "preregistrationSha256": preregistration["preregistrationSha256"],
        "candidateTitle": candidate_title,
        "searchedRunCount": len(rows),
        "matchingRuns": matches,
        "status": "REFUSED_DUPLICATE" if matches else "PASSED_NO_DUPLICATE",
        "searchCompletedBeforeSolver": True,
        "solverCallsBeforeSearch": 0,
    }
    report["auditSha256"] = canonical_sha256(report)
    return report


def validate_run_context(run: dict[str, Any], duplicate_audit: dict[str, Any]) -> None:
    if not isinstance(run, dict):
        raise Refusal("run context missing")
    if run.get("event") != "workflow_dispatch" or run.get("run_attempt") != 1:
        raise Refusal("continuation execution requires workflow_dispatch attempt 1")
    if duplicate_audit.get("status") != "PASSED_NO_DUPLICATE" or duplicate_audit.get("searchCompletedBeforeSolver") is not True:
        raise Refusal("duplicate-run refusal did not pass before solver")
    payload = dict(duplicate_audit)
    supplied_hash = payload.pop("auditSha256", None)
    if not is_sha256(supplied_hash) or canonical_sha256(payload) != supplied_hash:
        raise Refusal("duplicate-run audit hash changed")


def _base_for_preregistration(preregistration: dict[str, Any], root: Path | None = None):
    root = (root or repository_root()).resolve()
    validate_preregistration(preregistration, root)
    base = base_module(root)
    proposal, _ = _build_base_proposal(root, base)
    if proposal["proposalSha256"] != preregistration["sourceBindings"]["baseProposalSha256"]:
        raise Refusal("base proposal binding changed")
    return root, base, proposal


def aggregate_wave1(preregistration: dict[str, Any], results: list[dict[str, Any]], root: Path | None = None) -> dict[str, Any]:
    _, base, proposal = _base_for_preregistration(preregistration, root)
    aggregate = base.aggregate_wave(proposal, WAVE, base.CONTINUATION_GEOMETRY_IDS, results)
    wrapper = {
        "schemaVersion": 1,
        "stageId": "tier1-precision-continuation-wave1-aggregate-v2",
        "preregistrationSha256": preregistration["preregistrationSha256"],
        "baseProposalSha256": proposal["proposalSha256"],
        "aggregate": aggregate,
        "aggregateSha256": canonical_sha256(aggregate),
        "additionalExecutionAutomaticallyAuthorized": False,
    }
    wrapper["payloadSha256"] = canonical_sha256(wrapper)
    return wrapper


def audit_wave1(
    preregistration: dict[str, Any], results: list[dict[str, Any]], aggregate_wrapper: dict[str, Any], root: Path | None = None
) -> dict[str, Any]:
    _, base, proposal = _base_for_preregistration(preregistration, root)
    payload = dict(aggregate_wrapper)
    supplied_hash = payload.pop("payloadSha256", None)
    if not is_sha256(supplied_hash) or canonical_sha256(payload) != supplied_hash:
        raise Refusal("wave-1 aggregate wrapper hash changed")
    aggregate = aggregate_wrapper.get("aggregate")
    if not isinstance(aggregate, dict) or canonical_sha256(aggregate) != aggregate_wrapper.get("aggregateSha256"):
        raise Refusal("wave-1 aggregate payload hash changed")
    audit = base.audit_wave(proposal, WAVE, base.CONTINUATION_GEOMETRY_IDS, results, aggregate)
    wrapper = {
        "schemaVersion": 1,
        "stageId": "tier1-precision-continuation-wave1-independent-audit-v2",
        "preregistrationSha256": preregistration["preregistrationSha256"],
        "aggregateSha256": aggregate_wrapper["aggregateSha256"],
        "audit": audit,
        "auditSha256": canonical_sha256(audit),
        "independentlyRecomputedFromRawSelectedNodeRadiance": True,
        "additionalExecutionAutomaticallyAuthorized": False,
    }
    wrapper["payloadSha256"] = canonical_sha256(wrapper)
    return wrapper


def analyze_wave1(
    preregistration: dict[str, Any], aggregate_wrapper: dict[str, Any], audit_wrapper: dict[str, Any], root: Path | None = None
) -> dict[str, Any]:
    _, base, proposal = _base_for_preregistration(preregistration, root)
    for wrapper, label in ((aggregate_wrapper, "aggregate"), (audit_wrapper, "audit")):
        payload = dict(wrapper)
        supplied_hash = payload.pop("payloadSha256", None)
        if not is_sha256(supplied_hash) or canonical_sha256(payload) != supplied_hash:
            raise Refusal(f"wave-1 {label} wrapper hash changed")
    aggregate = aggregate_wrapper.get("aggregate")
    audit = audit_wrapper.get("audit")
    if not isinstance(aggregate, dict) or not isinstance(audit, dict):
        raise Refusal("wave-1 aggregate or audit missing")
    analysis = base.analyze_waves(proposal, [aggregate], [audit])
    result = {
        "schemaVersion": 1,
        "stageId": "tier1-precision-continuation-wave1-analysis-v2",
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
    result["analysisSha256"] = canonical_sha256(result)
    return result


def write_generated(root: Path, preregistration_path: Path, authorization_template_path: Path) -> None:
    preregistration = build_preregistration(root)
    template = authorization_template(preregistration, root)
    preregistration_path.parent.mkdir(parents=True, exist_ok=True)
    authorization_template_path.parent.mkdir(parents=True, exist_ok=True)
    preregistration_path.write_text(dump_json(preregistration), encoding="utf-8", newline="\n")
    authorization_template_path.write_text(dump_json(template), encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-preregistration", type=Path, required=True)
    parser.add_argument("--output-authorization-template", type=Path, required=True)
    args = parser.parse_args()
    write_generated(repository_root(), args.output_preregistration, args.output_authorization_template)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
