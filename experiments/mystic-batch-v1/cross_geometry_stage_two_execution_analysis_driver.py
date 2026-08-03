#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

STAGE_ID = "cross-geometry-stage-two-v1"
SOURCE_STAGE_ID = "cross-geometry-pilot-v1"
GENERIC_STAGE_ID = "mystic-batch-v1"
ANALYSIS_MODULE = Path(__file__).with_name("cross_geometry_analysis.py")
SELECTED_GROUPS = {
    "g01-reference-bridge",
    "g04-mid-perpendicular",
    "g05-mid-opposite-low",
    "g06-late-opposite-high-aerosol",
}
CARRIED_GROUPS = {
    "g02-early-near-low",
    "g03-early-perpendicular-high",
}
METHODS = {"reference-vroom", "alis"}


class AnalysisFailure(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise AnalysisFailure(f"cannot read JSON object: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise AnalysisFailure(f"expected JSON object: {path}")
    return value


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_analysis_module(path: Path):
    spec = importlib.util.spec_from_file_location("cross_geometry_stage_two_analysis", path)
    if spec is None or spec.loader is None:
        raise AnalysisFailure(f"cannot load analysis module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def exact_records(
    manifest: dict[str, Any],
    records_payload: dict[str, Any],
    manifest_hash: str,
    adapter_hash: str | None,
    expected_blocks: set[int],
) -> list[dict[str, Any]]:
    cases = manifest.get("cases")
    records = records_payload.get("records")
    if not isinstance(cases, list) or not isinstance(records, list):
        raise AnalysisFailure("manifest cases or records missing")
    cases_by_id = {
        case["caseId"]: case
        for case in cases
        if isinstance(case, dict) and isinstance(case.get("caseId"), str)
    }
    if len(cases_by_id) != len(cases):
        raise AnalysisFailure("manifest case IDs are missing or duplicated")
    found: dict[str, dict[str, Any]] = {}
    failures: list[dict[str, Any]] = []
    for record in records:
        if not isinstance(record, dict):
            failures.append({"code": "non-object-record"})
            continue
        case_id = record.get("caseId")
        if not isinstance(case_id, str) or case_id in found:
            failures.append({"code": "duplicate-or-missing-case-id", "caseId": case_id})
            continue
        case = cases_by_id.get(case_id)
        if case is None:
            failures.append({"code": "unplanned-case", "caseId": case_id})
            continue
        required = {
            "stageId": GENERIC_STAGE_ID,
            "status": "COMPLETED",
            "batchId": manifest.get("batchId"),
            "ordinal": case.get("ordinal"),
            "seed": case.get("seed"),
            "photonHistories": case.get("photonHistories"),
            "manifestRawSha256": manifest_hash,
            "syntaxCheckCount": 1,
            "solverExecutionCount": 1,
            "scientificDiagnostic": True,
            "successDoesNotAuthorizeProduction": True,
        }
        if adapter_hash is not None:
            required["adapterRawSha256"] = adapter_hash
        stale = {key: (record.get(key), expected) for key, expected in required.items() if record.get(key) != expected}
        if stale:
            failures.append({"code": "case-invariant", "caseId": case_id, "detail": stale})
        syntax = record.get("syntax")
        solver = record.get("solver")
        if not isinstance(syntax, dict) or syntax.get("exitCode") != 0 or syntax.get("timedOut") is not False:
            failures.append({"code": "syntax-status", "caseId": case_id, "detail": syntax})
        if not isinstance(solver, dict) or solver.get("exitCode") != 0 or solver.get("timedOut") is not False:
            failures.append({"code": "solver-status", "caseId": case_id, "detail": solver})
        if case.get("block") not in expected_blocks or case.get("method") not in METHODS:
            failures.append({"code": "case-design", "caseId": case_id})
        value = record.get("selectedPhotopicContributionCdM2")
        radiance = record.get("selectedNodeRadiance")
        std = record.get("selectedNodeStdRadiance")
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
            failures.append({"code": "photopic-value", "caseId": case_id, "detail": value})
        if not isinstance(radiance, list) or len(radiance) != 15 or not isinstance(std, list) or len(std) != 15:
            failures.append({"code": "spectral-vector", "caseId": case_id})
        found[case_id] = {
            **record,
            "groupId": case.get("groupId"),
            "method": case.get("method"),
            "block": case.get("block"),
        }
    missing = sorted(set(cases_by_id) - set(found))
    if missing:
        failures.append({"code": "missing-cases", "caseIds": missing})
    if len(records) != len(cases_by_id):
        failures.append({"code": "record-count", "actual": len(records), "expected": len(cases_by_id)})
    if failures:
        raise AnalysisFailure(f"case artifact invariants failed: {failures}")
    return [found[case["caseId"]] for case in cases]


def verify_source_postprocess(
    source_postprocess_root: Path,
    source_analysis_path: Path,
    provenance: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    report_path = source_postprocess_root / "postprocess-report.json"
    aggregate_path = source_postprocess_root / "aggregate" / "batch-summary.json"
    audit_path = source_postprocess_root / "audit" / "audit-report.json"
    records_path = source_postprocess_root / "screening" / "records.json"
    screening_path = source_postprocess_root / "screening" / "screening-analysis.json"
    for path in (report_path, aggregate_path, audit_path, records_path, screening_path):
        if not path.is_file():
            raise AnalysisFailure(f"source postprocess artifact missing: {path}")

    report = load_json(report_path)
    aggregate = load_json(aggregate_path)
    audit = load_json(audit_path)
    records = load_json(records_path)
    screening = load_json(screening_path)
    frozen_screening = load_json(source_analysis_path)

    expected_report = {
        "schemaVersion": 1,
        "stageId": SOURCE_STAGE_ID,
        "status": "POSTPROCESS_COMPLETED",
        "sourceRunId": provenance.get("sourceScientificRunId"),
        "sourceAuthorizationRef": provenance.get("sourceAuthorizationRef"),
        "authorizationOrdinal": provenance.get("sourceAuthorizationOrdinal"),
        "executionKey": provenance.get("sourceExecutionKey"),
        "caseCount": 24,
        "configuredMcPhotonsSum": 480_000_000,
        "aggregateClassification": "BATCH_NUMERICALLY_COMPLETE",
        "auditStatus": "PASSED",
        "screeningStatus": "SCREENING_ANALYZED",
    }
    stale = {key: (report.get(key), expected) for key, expected in expected_report.items() if report.get(key) != expected}
    if stale:
        raise AnalysisFailure(f"source postprocess report changed: {stale}")
    if aggregate.get("stageId") != GENERIC_STAGE_ID or aggregate.get("status") != "COMPLETED" or aggregate.get("classification") != "BATCH_NUMERICALLY_COMPLETE":
        raise AnalysisFailure("source generic aggregate is not complete")
    if aggregate.get("caseCountPlanned") != 24 or aggregate.get("caseCountCompleted") != 24 or aggregate.get("caseCountFailed") != 0:
        raise AnalysisFailure("source aggregate case accounting changed")
    if aggregate.get("syntaxCheckCount") != 24 or aggregate.get("solverExecutionCount") != 24:
        raise AnalysisFailure("source aggregate execution counts changed")
    if aggregate.get("configuredMcPhotonsSum") != 480_000_000 or aggregate.get("completedConfiguredMcPhotonsSum") != 480_000_000:
        raise AnalysisFailure("source aggregate photon accounting changed")
    if audit.get("stageId") != GENERIC_STAGE_ID or audit.get("status") != "PASSED" or audit.get("caseResultCount") != 24:
        raise AnalysisFailure("source independent audit did not pass")
    if screening != frozen_screening:
        raise AnalysisFailure("source screening artifact differs from the committed frozen analysis")

    hash_bindings = {
        "sourcePostprocessReportRawSha256": raw_sha256(report_path),
        "sourceAggregateRawSha256": raw_sha256(aggregate_path),
        "sourceAuditRawSha256": raw_sha256(audit_path),
        "sourceAnalysisRawSha256": raw_sha256(screening_path),
    }
    stale_hashes = {
        key: (provenance.get(key), actual)
        for key, actual in hash_bindings.items()
        if provenance.get(key) != actual
    }
    if stale_hashes:
        raise AnalysisFailure(f"source postprocess hashes changed: {stale_hashes}")
    if report.get("aggregateRawSha256") != hash_bindings["sourceAggregateRawSha256"]:
        raise AnalysisFailure("source report aggregate hash mismatch")
    if report.get("auditRawSha256") != hash_bindings["sourceAuditRawSha256"]:
        raise AnalysisFailure("source report audit hash mismatch")
    if report.get("screeningRawSha256") != hash_bindings["sourceAnalysisRawSha256"]:
        raise AnalysisFailure("source report screening hash mismatch")
    return records, frozen_screening


def analyze_combined(
    source_manifest: dict[str, Any],
    stage_two_proposal: dict[str, Any],
    contract: dict[str, Any],
    source_screening: dict[str, Any],
    source_records: list[dict[str, Any]],
    stage_two_records: list[dict[str, Any]],
    analysis_module: Any,
) -> dict[str, Any]:
    selected = set(stage_two_proposal.get("selectedGeometryIds", []))
    if selected != SELECTED_GROUPS:
        raise AnalysisFailure(f"stage-two selected geometry set changed: {selected}")
    source_groups = {geometry.get("geometryId") for geometry in source_manifest.get("geometries", []) if isinstance(geometry, dict)}
    if source_groups != SELECTED_GROUPS | CARRIED_GROUPS:
        raise AnalysisFailure("source geometry universe changed")
    source_by_group: dict[str, list[dict[str, Any]]] = {}
    stage_two_by_group: dict[str, list[dict[str, Any]]] = {}
    for record in source_records:
        source_by_group.setdefault(record["roupId"], []).append(record)
    for record in stage_two_records:
        stage_two_by_group.setdefault(record["groupId"], []).append(record)
    if set(stage_two_by_group) != SELECTED_GROUPS:
        raise AnalysisFailure("stage-two result group set changed")

    four_block_contract = json.loads(json.dumps(contract))
    four_block_contract["requiredBlocksPerMethodPerGeometry"] = 4
    results: list[dict[str, Any]] = []
    source_results = {
        result.get("groupId"): result
        for result in source_screening.get("geometryResults", [])
        if isinstance(result, dict) and isinstance(result.get("groupId"), str)
    }
    if set(source_results) != source_groups:
        raise AnalysisFailure("source screening result set changed")

    for group_id in sorted(source_groups):
        if group_id in SELECTED_GROUPS:
            combined = source_by_group.get(group_id, []) + stage_two_by_group.get(group_id, [])
            result = analysis_module.analyze_geometry(group_id, combined, four_block_contract)
            classification = result.get("classification")
            if classification == "STRUCTURAL_OR_EXECUTION_FAILURE":
                next_action = "TECHNICAL_DIAGNOSIS_REQUIRED"
            elif classification == "SCREENING_AGREEMENT":
                next_action = "NO_ADDITIONAL_MONTE_CARLO_RECOMMENDED_BY_THIS_SCREENING"
            else:
                next_action = "FINAL_FRESH_BLOCKS_5_6_RECOMMENDED_BEFORE_DIAGNOSIS"
            results.append({
                **result,
                "carriedForwardFromPilot": False,
                "blocksPerMethodAnalyzed": 4,
                "nextAction": next_action,
            })
        else:
            carried = source_results[group_id]
            results.append({
                **carried,
                "carriedForwardFromPilot": True,
                "blocksPerMethodAnalyzed": 2,
                "nextAction": "NO_ADDITIONAL_MONTE_CARLO_RECOMMENDED_BY_PILOT_SCREENING",
            })

    classifications = contract.get("classifications")
    if not isinstance(classifications, list):
        raise AnalysisFailure("contract classifications missing")
    counts = {
        classification: sum(result.get("classification") == classification for result in results)
        for classification in classifications
    }
    selected_counts = {
        classification: sum(
            result.get("classification") == classification and not result.get("carriedForwardFromPilot")
            for result in results
        )
        for classification in classifications
    }
    structural = counts.get("STRUCTURAL_OR_EXECUTION_FAILURE", 0)
    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "STAGE_TWO_SCREENING_ANALYZED" if structural == 0 else "STAGE_TWO_SCREENING_STRUCTURAL_FAILURE",
        "screeningOnly": True,
        "successDoesNotAuthorizeProduction": True,
        "sourcePilotBlocksPerMethod": 2,
        "newStageTwoBlocksPerMethod": 2,
        "selectedGeometryIds": sorted(SELECTED_GROUPS),
        "carriedForwardGeometryIds": sorted(CARRIED_GROUPS),
        "geometryResults": results,
        "classificationCounts": counts,
        "selectedGeometryClassificationCounts": selected_counts,
        "boundary": "combined four-block screening for selected geometries plus carried pilot results; no physical, observational, surrogate, LUT, or production validity claim",
    }


def analyze_artifacts(
    source_manifest_path: Path,
    stage_two_proposal_path: Path,
    contract_path: Path,
    source_analysis_path: Path,
    source_provenance_path: Path,
    source_postprocess_root: Path,
    stage_two_cases_root: Path,
    stage_two_summary_path: Path,
    stage_two_audit_path: Path,
    output_dir: Path,
) -> tuple[dict[str, Any], bool]:
    source_manifest = load_json(source_manifest_path)
    stage_two_proposal = load_json(stage_two_proposal_path)
    contract = load_json(contract_path)
    provenance = load_json(source_provenance_path)
    stage_two_summary = load_json(stage_two_summary_path)
    stage_two_audit = load_json(stage_two_audit_path)

    if source_manifest.get("stageId") != SOURCE_STAGE_ID or source_manifest.get("proposalOnly") is not True:
        raise AnalysisFailure("wrong source pilot manifest header")
    if stage_two_proposal.get("stageId") != STAGE_ID or stage_two_proposal.get("proposalOnly") is not True:
        raise AnalysisFailure("wrong stage-two proposal header")
    if contract.get("stageId") != SOURCE_STAGE_ID or contract.get("screeningOnly") is not True:
        raise AnalysisFailure("wrong screening contract header")
    if provenance.get("stageId") != STAGE_ID or provenance.get("status") != "SOURCE_SCREENING_FROZEN":
        raise AnalysisFailure("wrong source provenance header")
    if raw_sha256(source_manifest_path) != stage_two_proposal.get("sourceManifestRawSha256"):
        raise AnalysisFailure("stage-two proposal source manifest hash mismatch")
    if raw_sha256(source_analysis_path) != stage_two_proposal.get("sourceAnalysisRawSha256"):
        raise AnalysisFailure("stage-two proposal source analysis hash mismatch")

    if stage_two_summary.get("stageId") != GENERIC_STAGE_ID or stage_two_summary.get("status") != "COMPLETED" or stage_two_summary.get("classification") != "BATCH_NUMERICALLY_COMPLETE":
        raise AnalysisFailure("stage-two generic aggregate is not numerically complete")
    if stage_two_summary.get("caseCountPlanned") != 16 or stage_two_summary.get("caseCountCompleted") != 16 or stage_two_summary.get("caseCountFailed") != 0:
        raise AnalysisFailure("stage-two aggregate case accounting changed")
    if stage_two_summary.get("syntaxCheckCount") != 16 or stage_two_summary.get("solverExecutionCount") != 16:
        raise AnalysisFailure("stage-two aggregate execution counts changed")
    if stage_two_summary.get("configuredMcPhotonsSum") != 320_000_000 or stage_two_summary.get("completedConfiguredMcPhotonsSum") != 320_000_000:
        raise AnalysisFailure("stage-two aggregate photon accounting changed")
    if stage_two_audit.get("stageId") != GENERIC_STAGE_ID or stage_two_audit.get("status") != "PASSED" or stage_two_audit.get("caseResultCount") != 16:
        raise AnalysisFailure("stage-two independent audit did not pass")

    source_payload, source_screening = verify_source_postprocess(source_postprocess_root, source_analysis_path, provenance)
    source_adapter_hash = None
    source_records = exact_records(
        source_manifest,
        source_payload,
        raw_sha256(source_manifest_path),
        source_adapter_hash,
        {1, 2},
     )
    stage_two_payload = {"records": [load_json(path) for path in sorted(stage_two_cases_root.rglob("case-result.json"))]}
    adapter_hash = stage_two_summary.get("scientificAdapterRawSha256")
    if not isinstance(adapter_hash, str) or len(adapter_hash) != 64:
        raise AnalysisFailure("stage-two aggregate adapter hash missing")
    stage_two_records = exact_records(
        stage_two_proposal,
        stage_two_payload,
        raw_sha256(stage_two_proposal_path),
        adapter_hash,
        {3, 4},
    )

    analysis_module = load_analysis_module(ANALYSIS_MODULE)
    result = analyze_combined(
        source_manifest,
        stage_two_proposal,
        contract,
        source_screening,
        source_records,
        stage_two_records,
        analysis_module,
    )
    result.update({
        "sourceManifestRawSha256": raw_sha256(source_manifest_path),
        "stageTwoProposalRawSha256": raw_sha256(stage_two_proposal_path),
        "contractRawSha256": raw_sha256(contract_path),
        "sourceAnalysisRawSha256": raw_sha256(source_analysis_path),
        "sourceProvenanceRawSha256": raw_sha256(source_provenance_path),
        "sourcePostprocessReportRawSha256": provenance["sourcePostprocessReportRawSha256"],
        "stageTwoSummaryRawSha256": raw_sha256(stage_two_summary_path),
        "stageTwoAuditRawSha256": raw_sha256(stage_two_audit_path),
        "sourceCaseResultCount": 24,
        "stageTwoCaseResultCount": 16,
        "combinedCaseResultCount": 40,
        "combinedConfiguredMcPhotonsSum": 800_000_000,
        "executionArtifactAuditsPassed": True,
    })
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "stage-two-screening-analysis.json").write_text(dump(result))
    passed = result["status"] == "STAGE_TWO_SCREENING_ANALYZED"
    return result, passed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--stage-two-proposal", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--source-analysis", type=Path, required=True)
    parser.add_argument("--source-provenance", type=Path, required=True)
    parser.add_argument("--source-postprocess-root", type=Path, required=True)
    parser.add_argument("--stage-two-cases-root", type=Path, required=True)
    parser.add_argument("--stage-two-summary", type=Path, required=True)
    parser.add_argument("--stage-two-audit", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result, passed = analyze_artifacts(
            args.source_manifest,
            args.stage_two_proposal,
            args.contract,
            args.source_analysis,
            args.source_provenance,
            args.source_postprocess_root,
            args.stage_two_cases_root,
            args.stage_two_summary,
            args.stage_two_audit,
            args.output_dir,
        )
        print(dump(result), end="")
        return 0 if passed else 2
    except Exception as exc:
        print(dump({"status": "REFUSED", "stageId": STAGE_ID, "reason": str(exc)}), end="", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
