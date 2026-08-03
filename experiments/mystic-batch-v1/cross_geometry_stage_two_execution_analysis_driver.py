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
PILOT_ID = "cross-geometry-pilot-v1"
GENERIC_ID = "mystic-batch-v1"
ANALYSIS_MODULE = Path(__file__).with_name("cross_geometry_analysis.py")
SELECTED = {"g01-reference-bridge", "g04-mid-perpendicular", "g05-mid-opposite-low", "g06-late-opposite-high-aerosol"}
CARRIED = {"g02-early-near-low", "g03-early-perpendicular-high"}
METHODS = {"reference-vroom", "alis"}


class AnalysisFailure(RuntimeError):
    pass


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise AnalysisFailure(f"cannot read JSON object {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise AnalysisFailure(f"expected JSON object: {path}")
    return value


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def analysis_module():
    spec = importlib.util.spec_from_file_location("cross_geometry_stage_two_analysis", ANALYSIS_MODULE)
    if spec is None or spec.loader is None:
        raise AnalysisFailure(f"cannot load analysis module: {ANALYSIS_MODULE}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def exact_records(manifest: dict[str, Any], payload: dict[str, Any], manifest_hash: str, adapter_hash: str | None, blocks: set[int]) -> list[dict[str, Any]]:
    cases = manifest.get("cases")
    records = payload.get("records")
    if not isinstance(cases, list) or not isinstance(records, list):
        raise AnalysisFailure("manifest cases or records missing")
    planned = {case.get("caseId"): case for case in cases if isinstance(case, dict) and isinstance(case.get("caseId"), str)}
    if len(planned) != len(cases) or len(records) != len(cases):
        raise AnalysisFailure("case or record count mismatch")
    found: dict[str, dict[str, Any]] = {}
    failures: list[dict[str, Any]] = []
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("caseId"), str) or record["caseId"] in found:
            failures.append({"code": "invalid-or-duplicate-record"})
            continue
        case = planned.get(record["caseId"])
        if case is None:
            failures.append({"code": "unplanned-case", "caseId": record["caseId"]})
            continue
        required = {
            "stageId": GENERIC_ID, "status": "COMPLETED", "batchId": manifest.get("batchId"),
            "ordinal": case.get("ordinal"), "seed": case.get("seed"), "photonHistories": case.get("photonHistories"),
            "manifestRawSha256": manifest_hash, "syntaxCheckCount": 1, "solverExecutionCount": 1,
            "scientificDiagnostic": True, "successDoesNotAuthorizeProduction": True,
        }
        if adapter_hash is not None:
            required["adapterRawSha256"] = adapter_hash
        stale = {key: (record.get(key), expected) for key, expected in required.items() if record.get(key) != expected}
        if stale:
            failures.append({"code": "case-invariant", "caseId": record["caseId"], "detail": stale})
        syntax, solver = record.get("syntax"), record.get("solver")
        if not isinstance(syntax, dict) or syntax.get("exitCode") != 0 or syntax.get("timedOut") is not False:
            failures.append({"code": "syntax-status", "caseId": record["caseId"]})
        if not isinstance(solver, dict) or solver.get("exitCode") != 0 or solver.get("timedOut") is not False:
            failures.append({"code": "solver-status", "caseId": record["caseId"]})
        value, radiance, std = record.get("selectedPhotopicContributionCdM2"), record.get("selectedNodeRadiance"), record.get("selectedNodeStdRadiance")
        if case.get("block") not in blocks or case.get("method") not in METHODS:
            failures.append({"code": "case-design", "caseId": record["caseId"]})
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
            failures.append({"code": "photopic-value", "caseId": record["caseId"]})
        if not isinstance(radiance, list) or len(radiance) != 15 or not isinstance(std, list) or len(std) != 15:
            failures.append({"code": "spectral-vector", "caseId": record["caseId"]})
        found[record["caseId"]] = {**record, "groupId": case.get("groupId"), "method": case.get("method"), "block": case.get("block")}
    missing = sorted(set(planned) - set(found))
    if missing:
        failures.append({"code": "missing-cases", "caseIds": missing})
    if failures:
        raise AnalysisFailure(f"case artifact invariants failed: {failures}")
    return [found[case["caseId"]] for case in cases]


def verify_source(root: Path, frozen_analysis_path: Path, provenance: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    paths = {
        "report": root / "postprocess-report.json",
        "aggregate": root / "aggregate/batch-summary.json",
        "audit": root / "audit/audit-report.json",
        "records": root / "screening/records.json",
        "analysis": root / "screening/screening-analysis.json",
    }
    if any(not path.is_file() for path in paths.values()):
        raise AnalysisFailure("preserved pilot postprocess artifact is incomplete")
    values = {key: load(path) for key, path in paths.items()}
    report, aggregate, audit = values["report"], values["aggregate"], values["audit"]
    expected_report = {
        "schemaVersion": 1, "stageId": PILOT_ID, "status": "POSTPROCESS_COMPLETED",
        "sourceRunId": provenance.get("sourceScientificRunId"), "sourceAuthorizationRef": provenance.get("sourceAuthorizationRef"),
        "authorizationOrdinal": provenance.get("sourceAuthorizationOrdinal"), "executionKey": provenance.get("sourceExecutionKey"),
        "caseCount": 24, "configuredMcPhotonsSum": 480_000_000,
        "aggregateClassification": "BATCH_NUMERICALLY_COMPLETE", "auditStatus": "PASSED", "screeningStatus": "SCREENING_ANALYZED",
    }
    stale = {key: (report.get(key), expected) for key, expected in expected_report.items() if report.get(key) != expected}
    if stale:
        raise AnalysisFailure(f"pilot postprocess report changed: {stale}")
    if aggregate.get("stageId") != GENERIC_ID or aggregate.get("status") != "COMPLETED" or aggregate.get("classification") != "BATCH_NUMERICALLY_COMPLETE":
        raise AnalysisFailure("pilot aggregate is not complete")
    if (aggregate.get("caseCountPlanned"), aggregate.get("caseCountCompleted"), aggregate.get("caseCountFailed")) != (24, 24, 0):
        raise AnalysisFailure("pilot aggregate case accounting changed")
    if (aggregate.get("syntaxCheckCount"), aggregate.get("solverExecutionCount")) != (24, 24):
        raise AnalysisFailure("pilot execution accounting changed")
    if (aggregate.get("configuredMcPhotonsSum"), aggregate.get("completedConfiguredMcPhotonsSum")) != (480_000_000, 480_000_000):
        raise AnalysisFailure("pilot photon accounting changed")
    if audit.get("stageId") != GENERIC_ID or audit.get("status") != "PASSED" or audit.get("caseResultCount") != 24:
        raise AnalysisFailure("pilot independent audit did not pass")
    frozen = load(frozen_analysis_path)
    if values["analysis"] != frozen:
        raise AnalysisFailure("pilot screening differs from frozen analysis")
    bindings = {
        "sourcePostprocessReportRawSha256": sha(paths["report"]), "sourceAggregateRawSha256": sha(paths["aggregate"]),
        "sourceAuditRawSha256": sha(paths["audit"]), "sourceAnalysisRawSha256": sha(paths["analysis"]),
    }
    stale_hashes = {key: (provenance.get(key), actual) for key, actual in bindings.items() if provenance.get(key) != actual}
    if stale_hashes:
        raise AnalysisFailure(f"pilot postprocess hashes changed: {stale_hashes}")
    if report.get("aggregateRawSha256") != bindings["sourceAggregateRawSha256"] or report.get("auditRawSha256") != bindings["sourceAuditRawSha256"] or report.get("screeningRawSha256") != bindings["sourceAnalysisRawSha256"]:
        raise AnalysisFailure("pilot postprocess report hash binding changed")
    return values["records"], frozen


def analyze_combined(source: dict[str, Any], stage2: dict[str, Any], contract: dict[str, Any], pilot_screening: dict[str, Any], source_records: list[dict[str, Any]], stage2_records: list[dict[str, Any]], analyzer: Any) -> dict[str, Any]:
    if set(stage2.get("selectedGeometryIds", [])) != SELECTED:
        raise AnalysisFailure("selected geometry set changed")
    universe = {item.get("geometryId") for item in source.get("geometries", []) if isinstance(item, dict)}
    if universe != SELECTED | CARRIED:
        raise AnalysisFailure("pilot geometry universe changed")
    by_source: dict[str, list[dict[str, Any]]] = {}
    by_stage2: dict[str, list[dict[str, Any]]] = {}
    for record in source_records:
        by_source.setdefault(record["groupId"], []).append(record)
    for record in stage2_records:
        by_stage2.setdefault(record["groupId"], []).append(record)
    if set(by_stage2) != SELECTED:
        raise AnalysisFailure("stage-two result geometry set changed")
    pilot_results = {item.get("groupId"): item for item in pilot_screening.get("geometryResults", []) if isinstance(item, dict)}
    if set(pilot_results) != universe:
        raise AnalysisFailure("pilot screening result set changed")
    four = json.loads(json.dumps(contract))
    four["requiredBlocksPerMethodPerGeometry"] = 4
    results: list[dict[str, Any]] = []
    for group in sorted(universe):
        if group in SELECTED:
            result = analyzer.analyze_geometry(group, by_source.get(group, []) + by_stage2.get(group, []), four)
            classification = result.get("classification")
            next_action = (
                "TECHNICAL_DIAGNOSIS_REQUIRED" if classification == "STRUCTURAL_OR_EXECUTION_FAILURE" else
                "NO_ADDITIONAL_MONTE_CARLO_RECOMMENDED_BY_THIS_SCREENING" if classification == "SCREENING_AGREEMENT" else
                "FINAL_FRESH_BLOCKS_5_6_RECOMMENDED_BEFORE_DIAGNOSIS"
            )
            results.append({**result, "carriedForwardFromPilot": False, "blocksPerMethodAnalyzed": 4, "nextAction": next_action})
        else:
            results.append({**pilot_results[group], "carriedForwardFromPilot": True, "blocksPerMethodAnalyzed": 2, "nextAction": "NO_ADDITIONAL_MONTE_CARLO_RECOMMENDED_BY_PILOT_SCREENING"})
    classes = contract.get("classifications")
    if not isinstance(classes, list):
        raise AnalysisFailure("contract classifications missing")
    counts = {name: sum(item.get("classification") == name for item in results) for name in classes}
    selected_counts = {name: sum(item.get("classification") == name and not item.get("carriedForwardFromPilot") for item in results) for name in classes}
    return {
        "schemaVersion": 1, "stageId": STAGE_ID,
        "status": "STAGE_TWO_SCREENING_ANALYZED" if counts.get("STRUCTURAL_OR_EXECUTION_FAILURE", 0) == 0 else "STAGE_TWO_SCREENING_STRUCTURAL_FAILURE",
        "screeningOnly": True, "successDoesNotAuthorizeProduction": True,
        "sourcePilotBlocksPerMethod": 2, "newStageTwoBlocksPerMethod": 2,
        "selectedGeometryIds": sorted(SELECTED), "carriedForwardGeometryIds": sorted(CARRIED),
        "geometryResults": results, "classificationCounts": counts, "selectedGeometryClassificationCounts": selected_counts,
        "boundary": "combined four-block screening for selected geometries plus carried pilot results; no physical, observational, surrogate, LUT, or production validity claim",
    }


def analyze_artifacts(source_manifest_path: Path, stage2_path: Path, contract_path: Path, source_analysis_path: Path, provenance_path: Path, source_root: Path, stage2_cases_root: Path, stage2_summary_path: Path, stage2_audit_path: Path, output_dir: Path) -> tuple[dict[str, Any], bool]:
    source, stage2, contract, provenance = load(source_manifest_path), load(stage2_path), load(contract_path), load(provenance_path)
    summary, audit = load(stage2_summary_path), load(stage2_audit_path)
    if source.get("stageId") != PILOT_ID or source.get("proposalOnly") is not True:
        raise AnalysisFailure("wrong pilot manifest header")
    if stage2.get("stageId") != STAGE_ID or stage2.get("proposalOnly") is not True:
        raise AnalysisFailure("wrong stage-two proposal header")
    if contract.get("stageId") != PILOT_ID or contract.get("screeningOnly") is not True:
        raise AnalysisFailure("wrong screening contract header")
    if provenance.get("stageId") != STAGE_ID or provenance.get("status") != "SOURCE_SCREENING_FROZEN":
        raise AnalysisFailure("wrong provenance header")
    if sha(source_manifest_path) != stage2.get("sourceManifestRawSha256") or sha(source_analysis_path) != stage2.get("sourceAnalysisRawSha256"):
        raise AnalysisFailure("stage-two source hash binding changed")
    if summary.get("stageId") != GENERIC_ID or summary.get("status") != "COMPLETED" or summary.get("classification") != "BATCH_NUMERICALLY_COMPLETE":
        raise AnalysisFailure("stage-two aggregate is not complete")
    if (summary.get("caseCountPlanned"), summary.get("caseCountCompleted"), summary.get("caseCountFailed")) != (16, 16, 0):
        raise AnalysisFailure("stage-two case accounting changed")
    if (summary.get("syntaxCheckCount"), summary.get("solverExecutionCount")) != (16, 16):
        raise AnalysisFailure("stage-two execution accounting changed")
    if (summary.get("configuredMcPhotonsSum"), summary.get("completedConfiguredMcPhotonsSum")) != (320_000_000, 320_000_000):
        raise AnalysisFailure("stage-two photon accounting changed")
    if audit.get("stageId") != GENERIC_ID or audit.get("status") != "PASSED" or audit.get("caseResultCount") != 16:
        raise AnalysisFailure("stage-two independent audit did not pass")
    source_payload, pilot_screening = verify_source(source_root, source_analysis_path, provenance)
    source_records = exact_records(source, source_payload, sha(source_manifest_path), None, {1, 2})
    stage2_payload = {"records": [load(path) for path in sorted(stage2_cases_root.rglob("case-result.json"))]}
    adapter_hash = summary.get("scientificAdapterRawSha256")
    if not isinstance(adapter_hash, str) or len(adapter_hash) != 64:
        raise AnalysisFailure("stage-two adapter hash missing")
    stage2_records = exact_records(stage2, stage2_payload, sha(stage2_path), adapter_hash, {3, 4})
    result = analyze_combined(source, stage2, contract, pilot_screening, source_records, stage2_records, analysis_module())
    result.update({
        "sourceManifestRawSha256": sha(source_manifest_path), "stageTwoProposalRawSha256": sha(stage2_path),
        "contractRawSha256": sha(contract_path), "sourceAnalysisRawSha256": sha(source_analysis_path),
        "sourceProvenanceRawSha256": sha(provenance_path), "sourcePostprocessReportRawSha256": provenance["sourcePostprocessReportRawSha256"],
        "stageTwoSummaryRawSha256": sha(stage2_summary_path), "stageTwoAuditRawSha256": sha(stage2_audit_path),
        "sourceCaseResultCount": 24, "stageTwoCaseResultCount": 16, "combinedCaseResultCount": 40,
        "combinedConfiguredMcPhotonsSum": 800_000_000, "executionArtifactAuditsPassed": True,
    })
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "stage-two-screening-analysis.json").write_text(dump(result))
    return result, result["status"] == "STAGE_TWO_SCREENING_ANALYZED"


def main() -> int:
    parser = argparse.ArgumentParser()
    for name in ("source-manifest", "stage-two-proposal", "contract", "source-analysis", "source-provenance", "source-postprocess-root", "stage-two-cases-root", "stage-two-summary", "stage-two-audit", "output-dir"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    try:
        result, passed = analyze_artifacts(args.source_manifest, args.stage_two_proposal, args.contract, args.source_analysis, args.source_provenance, args.source_postprocess_root, args.stage_two_cases_root, args.stage_two_summary, args.stage_two_audit, args.output_dir)
        print(dump(result), end="")
        return 0 if passed else 2
    except Exception as exc:
        print(dump({"status": "REFUSED", "stageId": STAGE_ID, "reason": str(exc)}), end="", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
