#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any

STAGE_ID = "cross-geometry-final-convergence-v1"
GENERIC_STAGE_ID = "mystic-batch-v1"
DIAGNOSTIC_GROUPS = ("g01-reference-bridge", "g06-late-opposite-high-aerosol")
CARRIED_GROUPS = ("g02-early-near-low", "g03-early-perpendicular-high", "g04-mid-perpendicular")
METHODS = ("reference-vroom", "alis")


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mean_vector(vectors: list[list[float]]) -> list[float]:
    if not vectors or any(len(vector) != 15 for vector in vectors):
        raise ValueError("expected nonempty 15-node vectors")
    return [sum(float(vector[index]) for vector in vectors) / len(vectors) for index in range(15)]


def combine_source(source: dict[str, Any], new_records: list[dict[str, Any]]) -> tuple[list[float], list[float]]:
    source_values = [float(value) for value in source["valuesCdM2"]]
    values = source_values + [float(record["selectedPhotopicContributionCdM2"]) for record in new_records]
    source_count = len(source_values)
    total_count = len(values)
    node = [
        (
            float(source["nodeMeanRadiance"][index]) * source_count
            + sum(float(record["selectedNodeRadiance"][index]) for record in new_records)
        )
        / total_count
        for index in range(15)
    ]
    return values, node


def exact_records(root: Path, proposal: dict[str, Any], manifest_hash: str, adapter_hash: str) -> dict[str, dict[str, Any]]:
    planned = {case["caseId"]: case for case in proposal["cases"]}
    paths = sorted(root.rglob("case-result.json"))
    if len(paths) != len(planned):
        raise ValueError(f"expected {len(planned)} case results, found {len(paths)}")
    found: dict[str, dict[str, Any]] = {}
    for path in paths:
        record = load(path)
        case_id = record.get("caseId")
        case = planned.get(case_id)
        if case is None or case_id in found:
            raise ValueError(f"unplanned or duplicate case: {case_id}")
        required = {
            "stageId": GENERIC_STAGE_ID,
            "status": "COMPLETED",
            "batchId": proposal["batchId"],
            "ordinal": case["ordinal"],
            "seed": case["seed"],
            "photonHistories": case["photonHistories"],
            "manifestRawSha256": manifest_hash,
            "adapterRawSha256": adapter_hash,
            "syntaxCheckCount": 1,
            "solverExecutionCount": 1,
            "scientificDiagnostic": True,
            "successDoesNotAuthorizeProduction": True,
        }
        stale = {key: (record.get(key), expected) for key, expected in required.items() if record.get(key) != expected}
        if stale:
            raise ValueError(f"case invariant failed for {case_id}: {stale}")
        syntax = record.get("syntax")
        solver = record.get("solver")
        if not isinstance(syntax, dict) or syntax.get("exitCode") != 0 or syntax.get("timedOut") is not False:
            raise ValueError(f"syntax failed for {case_id}")
        if not isinstance(solver, dict) or solver.get("exitCode") != 0 or solver.get("timedOut") is not False:
            raise ValueError(f"solver failed for {case_id}")
        if len(record.get("selectedNodeRadiance", [])) != 15:
            raise ValueError(f"invalid spectrum for {case_id}")
        found[case_id] = {
            **record,
            **{key: case[key] for key in ("groupId", "method", "block", "purpose")},
            "alisSpectralImportanceSamplingNm": case.get("alisSpectralImportanceSamplingNm"),
        }
    return found


def exact_source_artifact(root: Path, frozen: Path) -> dict[str, Any]:
    matches = list(root.rglob("stage-two-screening-analysis.json"))
    if len(matches) != 1:
        raise ValueError("stage-two screening artifact is missing or duplicated")
    actual = load(matches[0])
    expected = load(frozen)
    if actual != expected:
        raise ValueError("downloaded stage-two screening differs from frozen copy")
    return expected


def method_summary(convergence_module: Any, values: list[float], node: list[float]) -> dict[str, Any]:
    return convergence_module.method_summary(values, node, None)


def recommended_photons_per_block(coefficient_of_variation_at_20m: float, target_rsem: float = 0.08, blocks: int = 4) -> tuple[int, bool]:
    raw = 20_000_000 * (coefficient_of_variation_at_20m / (target_rsem * math.sqrt(blocks))) ** 2
    rounded = max(20_000_000, math.ceil(raw / 10_000_000) * 10_000_000)
    capped = rounded > 400_000_000
    return min(rounded, 400_000_000), capped


def build_confirmation_proposal(base: dict[str, Any], requests: list[dict[str, Any]]) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    ordinal = 1
    geometries = {geometry["geometryId"]: geometry for geometry in base["geometries"]}
    seed_bases = {
        ("g01-reference-bridge", "alis"): 80000,
        ("g01-reference-bridge", "reference-vroom"): 80200,
        ("g05-mid-opposite-low", "alis"): 81000,
        ("g05-mid-opposite-low", "reference-vroom"): 81200,
        ("g06-late-opposite-high-aerosol", "alis"): 82000,
        ("g06-late-opposite-high-aerosol", "reference-vroom"): 82200,
    }
    for request in requests:
        group = request["groupId"]
        method = request["method"]
        reference_nm = request.get("alisSpectralImportanceSamplingNm")
        photons = request["photonHistoriesPerBlock"]
        seed_base = seed_bases[(group, method)] + (int(reference_nm) if reference_nm is not None else 0)
        for replicate in range(1, 5):
            case: dict[str, Any] = {
                "caseId": f"cgc-{group.split('-')[0]}-{method.replace('reference-', '')}-r{replicate}",
                "groupId": group,
                "method": method,
                "ordinal": ordinal,
                "seed": seed_base + replicate,
                "block": replicate,
                "photonHistories": photons,
                "purpose": request["purpose"],
            }
            if reference_nm is not None:
                case["alisSpectralImportanceSamplingNm"] = reference_nm
            cases.append(case)
            ordinal += 1
    selected_groups = sorted({request["groupId"] for request in requests})
    return {
        "schemaVersion": 1,
        "stageId": "cross-geometry-selected-reference-confirmation-v1",
        "mode": "scientific-proposal",
        "proposalOnly": True,
        "scientificExecution": False,
        "successDoesNotAuthorizeProduction": True,
        "adapterId": "mystic-cross-geometry-v1",
        "sourceFinalConvergenceStageId": STAGE_ID,
        "selectedGeometryIds": selected_groups,
        "geometries": [geometries[group] for group in selected_groups],
        "frozenInputs": base["frozenInputs"],
        "runtime": base["runtime"],
        "cases": cases,
        "limits": {
            "maximumCases": len(cases),
            "maximumConfiguredMcPhotonsSum": sum(case["photonHistories"] for case in cases),
            "maximumParallel": 16,
            "perCaseTimeoutSeconds": 1800,
        },
        "analysisPlan": {
            "selectionDataExcludedFromConfirmationDecision": True,
            "confirmationBlocksPerRequestedMethod": 4,
            "targetRelativeStandardErrorOfMean": 0.08,
            "maximumPhotonHistoriesPerBlock": 400_000_000,
            "noOpenEndedAdditionalBlocks": True,
        },
        "boundary": "fixed held-out confirmation after bounded reference selection; no authorization or automatic execution",
    }


def analyze(proposal_path: Path, frozen_screening_path: Path, source_convergence_path: Path, source_artifact_root: Path, cases_root: Path, summary_path: Path, audit_path: Path, convergence_module: Any, output_dir: Path) -> dict[str, Any]:
    proposal = load(proposal_path)
    source = exact_source_artifact(source_artifact_root, frozen_screening_path)
    convergence_v2 = load(source_convergence_path)
    summary = load(summary_path)
    audit = load(audit_path)
    if proposal.get("stageId") != STAGE_ID or len(proposal.get("cases", [])) != 26:
        raise ValueError("wrong final-convergence proposal")
    if proposal.get("sourceStageTwoScreeningRawSha256") != raw_sha256(frozen_screening_path):
        raise ValueError("proposal does not bind frozen stage-two screening")
    if proposal.get("sourceConvergenceV2RawSha256") != raw_sha256(source_convergence_path):
        raise ValueError("proposal does not bind convergence-v2 reanalysis")
    if summary.get("stageId") != GENERIC_STAGE_ID or summary.get("classification") != "BATCH_NUMERICALLY_COMPLETE":
        raise ValueError("aggregate is incomplete")
    if (summary.get("caseCountCompleted"), summary.get("caseCountFailed")) != (26, 0):
        raise ValueError("aggregate case accounting changed")
    if (summary.get("configuredMcPhotonsSum"), summary.get("completedConfiguredMcPhotonsSum")) != (520_000_000, 520_000_000):
        raise ValueError("aggregate photon accounting changed")
    if audit.get("stageId") != GENERIC_STAGE_ID or audit.get("status") != "PASSED" or audit.get("caseResultCount") != 26:
        raise ValueError("independent audit failed")
    adapter_hash = summary.get("scientificAdapterRawSha256")
    if not isinstance(adapter_hash, str) or len(adapter_hash) != 64:
        raise ValueError("aggregate adapter hash is missing")
    records = exact_records(cases_root, proposal, raw_sha256(proposal_path), adapter_hash)
    source_results = {item["groupId"]: item for item in source["geometryResults"]}
    convergence_results = {item["groupId"]: item for item in convergence_v2["geometryResults"]}
    rules = {
        "integratedMeanRatioAlisToVroomClosedInterval": [0.5, 2.0],
        "minimumVroomPhotopicWeightFractionNodeRatioInsideInterval": 0.80,
        "maximumRelativeStandardErrorOfMean": 0.10,
    }
    results: list[dict[str, Any]] = []
    confirmation_requests: list[dict[str, Any]] = []
    technical_diagnosis_groups: list[str] = []

    for group in CARRIED_GROUPS:
        if group == "g04-mid-perpendicular":
            corrected = convergence_results[group]
            if corrected.get("classificationV2") != "SCREENING_AGREEMENT":
                raise ValueError("g04 convergence-v2 carry-forward changed")
            results.append({
                "groupId": group,
                "classification": "SCREENING_AGREEMENT",
                "source": "convergence-v2-reanalysis",
                "carriedForward": True,
                "methodStatistics": corrected.get("methodStatisticsV2"),
                "meanRatioAlisToVroom": corrected.get("meanRatioAlisToVroom"),
                "vroomPhotopicWeightFractionNodeRatioInsideInterval": corrected.get("vroomPhotopicWeightFractionNodeRatioInsideInterval"),
            })
        else:
            pilot = source_results[group]
            results.append({**pilot, "source": "stage-two-screening", "carriedForward": True})

    g05_methods: dict[str, dict[str, Any]] = {}
    for method in METHODS:
        source_method = source_results["g05-mid-opposite-low"]["methodStatistics"][method]
        new_records = [record for record in records.values() if record["groupId"] == "g05-mid-opposite-low" and record["method"] == method]
        values, node = combine_source(source_method, new_records)
        g05_methods[method] = method_summary(convergence_module, values, node)
    g05_decision = convergence_module.classify(g05_methods, rules)
    g05_classification = g05_decision["classification"]
    g05_result = {"groupId": "g05-mid-opposite-low", "classification": g05_classification, "methodStatistics": g05_methods, **g05_decision, "carriedForward": False}
    if g05_classification == "NEEDS_MORE_PRECISION":
        g05_result["nextAction"] = "FIXED_HELD_OUT_PRECISION_CONFIRMATION"
        for method in METHODS:
            stats = g05_methods[method]
            if stats["relativeStandardErrorOfMean"] > rules["maximumRelativeStandardErrorOfMean"]:
                photons, capped = recommended_photons_per_block(stats["coefficientOfVariation"])
                confirmation_requests.append({"groupId": "g05-mid-opposite-low", "method": method, "purpose": "precision-confirmation", "alisSpectralImportanceSamplingNm": 405.0 if method == "alis" else None, "photonHistoriesPerBlock": photons, "recommendationCappedAt400MPerBlock": capped})
    elif g05_classification == "SCREENING_DISCREPANCY":
        g05_result["nextAction"] = "TECHNICAL_DIAGNOSIS_REQUIRED"
        technical_diagnosis_groups.append("g05-mid-opposite-low")
    else:
        g05_result["nextAction"] = "NO_ADDITIONAL_MONTE_CARLO_RECOMMENDED_BY_SCREENING"
    results.append(g05_result)

    for group in DIAGNOSTIC_GROUPS:
        source_vroom = source_results[group]["methodStatistics"]["reference-vroom"]
        new_vroom = [record for record in records.values() if record["groupId"] == group and record["method"] == "reference-vroom"]
        vroom_values, vroom_node = combine_source(source_vroom, new_vroom)
        vroom_summary = method_summary(convergence_module, vroom_values, vroom_node)
        candidates: list[dict[str, Any]] = []
        for reference_nm in (500.0, 550.0, 600.0):
            candidate_records = [record for record in records.values() if record["groupId"] == group and record["purpose"] == "alis-reference-diagnostic" and record["alisSpectralImportanceSamplingNm"] == reference_nm]
            values = [float(record["selectedPhotopicContributionCdM2"]) for record in candidate_records]
            node = mean_vector([record["selectedNodeRadiance"] for record in candidate_records])
            alis_summary = method_summary(convergence_module, values, node)
            decision = convergence_module.classify({"reference-vroom": vroom_summary, "alis": alis_summary}, rules)
            compatible = 0.5 <= decision["meanRatioAlisToVroom"] <= 2.0 and decision["vroomPhotopicWeightFractionNodeRatioInsideInterval"] >= 0.80
            candidates.append({"referenceNm": reference_nm, "compatible": compatible, "alisStatistics": alis_summary, **decision})
        compatible_candidates = [candidate for candidate in candidates if candidate["compatible"]]
        if not compatible_candidates:
            chosen = min(candidates, key=lambda candidate: candidate["alisStatistics"]["relativeStandardErrorOfMean"])
            classification = "SCREENING_DISCREPANCY"
            next_action = "TECHNICAL_DIAGNOSIS_REQUIRED"
            technical_diagnosis_groups.append(group)
        else:
            chosen = min(compatible_candidates, key=lambda candidate: candidate["alisStatistics"]["relativeStandardErrorOfMean"])
            classification = "REFERENCE_SELECTED_NEEDS_CONFIRMATION"
            next_action = "FIXED_HELD_OUT_SELECTED_REFERENCE_CONFIRMATION"
            alis_photons, alis_capped = recommended_photons_per_block(chosen["alisStatistics"]["coefficientOfVariation"])
            confirmation_requests.append({"groupId": group, "method": "alis", "purpose": "selected-reference-confirmation", "alisSpectralImportanceSamplingNm": chosen["referenceNm"], "photonHistoriesPerBlock": alis_photons, "recommendationCappedAt400MPerBlock": alis_capped})
            if vroom_summary["relativeStandardErrorOfMean"] > rules["maximumRelativeStandardErrorOfMean"]:
                vroom_photons, vroom_capped = recommended_photons_per_block(vroom_summary["coefficientOfVariation"])
                confirmation_requests.append({"groupId": group, "method": "reference-vroom", "purpose": "vroom-precision-confirmation", "alisSpectralImportanceSamplingNm": None, "photonHistoriesPerBlock": vroom_photons, "recommendationCappedAt400MPerBlock": vroom_capped})
        results.append({
            "groupId": group,
            "classification": classification,
            "vroomStatistics": vroom_summary,
            "candidateAlisReferences": candidates,
            "selectedAlisReferenceNm": chosen["referenceNm"],
            "selectedAlisCoefficientOfVariation": chosen["alisStatistics"]["coefficientOfVariation"],
            "selectedAlisRelativeStandardErrorOfMean": chosen["alisStatistics"]["relativeStandardErrorOfMean"],
            "selectedMeanRatioAlisToVroom": chosen["meanRatioAlisToVroom"],
            "selectedNodeAgreementFraction": chosen["vroomPhotopicWeightFractionNodeRatioInsideInterval"],
            "selectionDataMayNotServeAsConfirmation": True,
            "nextAction": next_action,
            "carriedForward": False,
        })

    classification_counts: dict[str, int] = {}
    for result in results:
        classification = result["classification"]
        classification_counts[classification] = classification_counts.get(classification, 0) + 1
    confirmation_proposal = build_confirmation_proposal(proposal, confirmation_requests)
    output = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "FINAL_CONVERGENCE_ANALYZED",
        "screeningOnly": True,
        "successDoesNotAuthorizeProduction": True,
        "sourceCombinedCaseResultCount": 40,
        "newCaseResultCount": 26,
        "combinedCaseResultCount": 66,
        "combinedConfiguredMcPhotonsSum": 1_320_000_000,
        "geometryResults": results,
        "classificationCounts": classification_counts,
        "heldOutConfirmationRequired": bool(confirmation_proposal["cases"]),
        "heldOutConfirmationCaseCount": len(confirmation_proposal["cases"]),
        "heldOutConfirmationConfiguredMcPhotonsSum": confirmation_proposal["limits"]["maximumConfiguredMcPhotonsSum"],
        "technicalDiagnosisRequiredGeometryIds": sorted(technical_diagnosis_groups),
        "boundary": "corrected mean-uncertainty screening and bounded ALIS importance-wavelength selection; selected references require independent held-out confirmation before acceptance",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "final-convergence-analysis.json").write_text(dump(output))
    (output_dir / "next-confirmation-proposal.json").write_text(dump(confirmation_proposal))
    readiness = {
        "schemaVersion": 1,
        "status": "COMPUTATIONAL_REFERENCE_SCREENING_IN_PROGRESS" if confirmation_proposal["cases"] or technical_diagnosis_groups else "COMPUTATIONAL_REFERENCE_SCREENING_COMPLETE",
        "productionModelReady": False,
        "physicalValidationReady": False,
        "observationValidationRequired": True,
        "screeningAgreementGeometryCount": classification_counts.get("SCREENING_AGREEMENT", 0),
        "heldOutConfirmationCaseCount": len(confirmation_proposal["cases"]),
        "technicalDiagnosisRequiredGeometryCount": len(technical_diagnosis_groups),
        "sourceCaseCount": 66,
        "sourceConfiguredMcPhotonsSum": 1_320_000_000,
    }
    (output_dir / "model-readiness.json").write_text(dump(readiness))
    return output


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("cross_geometry_convergence_v2", path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load convergence module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--proposal", type=Path, required=True)
    parser.add_argument("--frozen-source-screening", type=Path, required=True)
    parser.add_argument("--source-convergence", type=Path, required=True)
    parser.add_argument("--source-screening-artifact-root", type=Path, required=True)
    parser.add_argument("--cases-root", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--convergence-module", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = analyze(args.proposal, args.frozen_source_screening, args.source_convergence, args.source_screening_artifact_root, args.cases_root, args.summary, args.audit, load_module(args.convergence_module), args.output_dir)
        print(dump(result), end="")
        return 0
    except Exception as exc:
        print(dump({"status": "REFUSED", "stageId": STAGE_ID, "reason": str(exc)}), end="", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
