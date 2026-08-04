#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

STAGE_ID = "cross-geometry-selected-reference-confirmation-v1"
SOURCE_STAGE_ID = "cross-geometry-final-convergence-v1"
BATCH_ID = "cross-geometry-selected-reference-confirmation-v1"
METHODS = {"reference-vroom", "alis"}
PURPOSES = {"precision-confirmation", "selected-reference-confirmation", "vroom-precision-confirmation"}
ALIS_REFERENCES = {405.0, 500.0, 550.0, 600.0}
MAX_CASES = 24
MAX_PHOTONS_PER_CASE = 400_000_000
MAX_TOTAL_PHOTONS = MAX_CASES * MAX_PHOTONS_PER_CASE


class ConfirmationPackageError(RuntimeError):
    pass


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfirmationPackageError(f"cannot read JSON object {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ConfirmationPackageError(f"expected JSON object: {path}")
    return value


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _finite_positive_int(value: Any, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ConfirmationPackageError(f"{name} must be a positive integer")
    return value


def _validate_source(analysis: dict[str, Any], proposal: dict[str, Any], readiness: dict[str, Any]) -> None:
    expected_analysis = {
        "schemaVersion": 1,
        "stageId": SOURCE_STAGE_ID,
        "status": "FINAL_CONVERGENCE_ANALYZED",
        "screeningOnly": True,
        "successDoesNotAuthorizeProduction": True,
    }
    stale = {key: (analysis.get(key), expected) for key, expected in expected_analysis.items() if analysis.get(key) != expected}
    if stale:
        raise ConfirmationPackageError(f"final analysis header mismatch: {stale}")
    if analysis.get("heldOutConfirmationRequired") is not True:
        raise ConfirmationPackageError("source analysis does not require held-out confirmation")
    expected_proposal = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "sourceFinalConvergenceStageId": SOURCE_STAGE_ID,
        "mode": "scientific-proposal",
        "proposalOnly": True,
        "scientificExecution": False,
        "successDoesNotAuthorizeProduction": True,
        "adapterId": "mystic-cross-geometry-v1",
    }
    stale = {key: (proposal.get(key), expected) for key, expected in expected_proposal.items() if proposal.get(key) != expected}
    if stale:
        raise ConfirmationPackageError(f"confirmation proposal header mismatch: {stale}")
    if readiness.get("schemaVersion") != 1 or readiness.get("status") != "COMPUTATIONAL_REFERENCE_SCREENING_IN_PROGRESS":
        raise ConfirmationPackageError("source readiness does not permit confirmation")
    if readiness.get("productionModelReady") is not False or readiness.get("observationValidationRequired") is not True:
        raise ConfirmationPackageError("source readiness safety boundary changed")


def _validate_cases(proposal: dict[str, Any], analysis: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    cases = proposal.get("cases")
    limits = proposal.get("limits")
    plan = proposal.get("analysisPlan")
    if not isinstance(cases, list) or not cases or len(cases) > MAX_CASES:
        raise ConfirmationPackageError(f"confirmation must contain 1..{MAX_CASES} cases")
    if not isinstance(limits, dict) or not isinstance(plan, dict):
        raise ConfirmationPackageError("confirmation limits or analysis plan missing")
    if plan.get("selectionDataExcludedFromConfirmationDecision") is not True:
        raise ConfirmationPackageError("selection data exclusion changed")
    if plan.get("confirmationBlocksPerRequestedMethod") != 4:
        raise ConfirmationPackageError("confirmation must use four held-out blocks per requested method")
    if float(plan.get("targetRelativeStandardErrorOfMean", -1)) != 0.08:
        raise ConfirmationPackageError("confirmation RSEM target changed")
    if plan.get("maximumPhotonHistoriesPerBlock") != MAX_PHOTONS_PER_CASE:
        raise ConfirmationPackageError("maximum photons per held-out block changed")
    if plan.get("noOpenEndedAdditionalBlocks") is not True:
        raise ConfirmationPackageError("open-ended additional blocks are forbidden")

    ids: set[str] = set()
    seeds: set[int] = set()
    groups: set[str] = set()
    requests: dict[tuple[str, str, float | None, str], list[dict[str, Any]]] = {}
    ordered = sorted(cases, key=lambda case: case.get("ordinal", -1))
    if [case.get("ordinal") for case in ordered] != list(range(1, len(ordered) + 1)):
        raise ConfirmationPackageError("confirmation ordinals must be contiguous from one")
    for case in ordered:
        if not isinstance(case, dict):
            raise ConfirmationPackageError("confirmation case must be an object")
        case_id = case.get("caseId")
        group = case.get("groupId")
        method = case.get("method")
        purpose = case.get("purpose")
        seed = _finite_positive_int(case.get("seed"), "seed")
        block = _finite_positive_int(case.get("block"), "block")
        photons = _finite_positive_int(case.get("photonHistories"), "photonHistories")
        if not isinstance(case_id, str) or not case_id or case_id in ids:
            raise ConfirmationPackageError(f"invalid or duplicate caseId: {case_id}")
        if not isinstance(group, str) or not group:
            raise ConfirmationPackageError("invalid groupId")
        if method not in METHODS or purpose not in PURPOSES:
            raise ConfirmationPackageError(f"invalid method or purpose for {case_id}")
        if seed in seeds:
            raise ConfirmationPackageError(f"duplicate seed: {seed}")
        if block not in {1, 2, 3, 4}:
            raise ConfirmationPackageError(f"confirmation block outside 1..4: {case_id}")
        if photons < 20_000_000 or photons > MAX_PHOTONS_PER_CASE or photons % 10_000_000:
            raise ConfirmationPackageError(f"invalid photons for {case_id}: {photons}")
        reference = case.get("alisSpectralImportanceSamplingNm")
        if method == "alis":
            if not isinstance(reference, (int, float)) or not math.isfinite(float(reference)) or float(reference) not in ALIS_REFERENCES:
                raise ConfirmationPackageError(f"invalid ALIS reference for {case_id}: {reference}")
            reference = float(reference)
        elif reference is not None:
            raise ConfirmationPackageError(f"VROOM case must not contain ALIS reference: {case_id}")
        ids.add(case_id)
        seeds.add(seed)
        groups.add(group)
        key = (group, method, reference, purpose)
        requests.setdefault(key, []).append(case)

    for key, request_cases in requests.items():
        blocks = sorted(case["block"] for case in request_cases)
        photons = {case["photonHistories"] for case in request_cases}
        if blocks != [1, 2, 3, 4] or len(photons) != 1:
            raise ConfirmationPackageError(f"held-out request must contain four equal-photon blocks: {key}")

    selected = proposal.get("selectedGeometryIds")
    geometries = proposal.get("geometries")
    if not isinstance(selected, list) or set(selected) != groups or len(selected) != len(groups):
        raise ConfirmationPackageError("selected geometry set does not match cases")
    if not isinstance(geometries, list) or {item.get("geometryId") for item in geometries if isinstance(item, dict)} != groups:
        raise ConfirmationPackageError("geometry definitions do not match cases")
    total = sum(case["photonHistories"] for case in ordered)
    if total > MAX_TOTAL_PHOTONS:
        raise ConfirmationPackageError("confirmation photon total exceeds hard cap")
    if limits.get("maximumCases") != len(ordered) or limits.get("maximumConfiguredMcPhotonsSum") != total:
        raise ConfirmationPackageError("proposal limits disagree with cases")
    if limits.get("maximumParallel") != 16 or limits.get("perCaseTimeoutSeconds") != 1800:
        raise ConfirmationPackageError("confirmation execution limits changed")
    if analysis.get("heldOutConfirmationCaseCount") != len(ordered):
        raise ConfirmationPackageError("source analysis case count does not match proposal")
    if analysis.get("heldOutConfirmationConfiguredMcPhotonsSum") != total:
        raise ConfirmationPackageError("source analysis photon total does not match proposal")
    return ordered, total


def promote(
    analysis_path: Path,
    proposal_path: Path,
    readiness_path: Path,
    source_run_metadata_path: Path,
    expected_source_run_id: int,
) -> dict[str, Any]:
    analysis = load(analysis_path)
    proposal = load(proposal_path)
    readiness = load(readiness_path)
    run = load(source_run_metadata_path)
    _validate_source(analysis, proposal, readiness)
    cases, total = _validate_cases(proposal, analysis)
    if run.get("id") != expected_source_run_id:
        raise ConfirmationPackageError("source run ID mismatch")
    if run.get("event") != "workflow_dispatch" or run.get("run_attempt") != 1 or run.get("status") != "completed" or run.get("conclusion") != "success":
        raise ConfirmationPackageError("source run is not a successful first-attempt workflow_dispatch")
    expected_title = "Cross geometry final convergence v1 | key=cross-geometry-final-convergence-v1:screening:4 | auth=7e630b8f46259ddf6a0cfdf5e381872c0182d0ba | ordinal=4"
    if run.get("display_title") != expected_title:
        raise ConfirmationPackageError("source run one-shot marker changed")
    promoted = json.loads(json.dumps(proposal))
    promoted.update({
        "batchId": BATCH_ID,
        "scientificDiagnostic": True,
        "sourceRunId": expected_source_run_id,
        "sourceFinalAnalysisRawSha256": raw_sha256(analysis_path),
        "sourceProposalRawSha256": raw_sha256(proposal_path),
        "sourceReadinessRawSha256": raw_sha256(readiness_path),
        "sourceRunMetadataRawSha256": raw_sha256(source_run_metadata_path),
        "cases": cases,
    })
    promoted["limits"] = {**promoted["limits"], "maximumConfiguredMcPhotonsSum": total}
    promoted["boundary"] = "promoted immutable held-out confirmation package from one successful first-attempt final-convergence run; no production or observational validity claim"
    return promoted


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--analysis", type=Path, required=True)
    parser.add_argument("--proposal", type=Path, required=True)
    parser.add_argument("--readiness", type=Path, required=True)
    parser.add_argument("--source-run-metadata", type=Path, required=True)
    parser.add_argument("--source-run-id", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = promote(args.analysis, args.proposal, args.readiness, args.source_run_metadata, args.source_run_id)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump(result))
        print(dump({"status": "PROMOTED", "stageId": STAGE_ID, "caseCount": len(result["cases"]), "configuredMcPhotonsSum": result["limits"]["maximumConfiguredMcPhotonsSum"]}), end="")
        return 0
    except Exception as exc:
        print(dump({"status": "REFUSED", "stageId": STAGE_ID, "reason": str(exc)}), end="", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
