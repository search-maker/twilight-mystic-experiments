from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

STAGE = "aerosol-vertical-profile-sensitivity-v1"


class ResultOpeningRefusal(RuntimeError):
    pass


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ResultOpeningRefusal(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def validate_self_hash(payload: dict[str, Any]) -> None:
    stored = payload.get("contentSha256")
    check = dict(payload)
    check.pop("contentSha256", None)
    if stored != canonical_sha256(check):
        raise ResultOpeningRefusal("verified analysis-input self hash drift")


def open_results(repository_root: Path, analysis_input_path: Path) -> dict[str, Any]:
    stage_dir = repository_root / "experiments" / STAGE
    contract_path = stage_dir / "execution-contract.review.json"
    contract = json.loads(contract_path.read_text())
    if contract.get("stageId") != f"{STAGE}-execution-contract":
        raise ResultOpeningRefusal("execution contract stage drift")
    if contract.get("resultOpeningGate", {}).get("partialResultInterpretationPermitted") is not False:
        raise ResultOpeningRefusal("execution contract result-opening boundary drift")

    analysis_path = stage_dir / "analysis.py"
    if git_blob_sha1(analysis_path) != contract["sourceBindings"]["analysisGitBlobSha1"]:
        raise ResultOpeningRefusal("frozen analysis byte drift")
    analysis = load_module("avps_frozen_analysis_for_result_opening", analysis_path)

    payload = json.loads(analysis_input_path.read_text())
    validate_self_hash(payload)
    if payload.get("stageId") != f"{STAGE}-verified-analysis-input":
        raise ResultOpeningRefusal("analysis input stage drift")
    if payload.get("status") != "COMPLETE_EXACT_360_ANALYSIS_INPUT_AFTER_AGGREGATE_VERIFICATION":
        raise ResultOpeningRefusal("exact aggregate verification has not completed")
    if payload.get("sourceAcquisitionStatus") != "COMPLETE_EXACT_360_CASE_ARTIFACT_UNIVERSE_RESULTS_STILL_CLOSED":
        raise ResultOpeningRefusal("analysis input not bound to closed exact-360 acquisition")
    if payload.get("caseCount") != 360 or payload.get("groupCount") != 72 or payload.get("analysisCellCount") != 24:
        raise ResultOpeningRefusal("analysis input cardinality drift")
    if payload.get("statesPerGroup") != 5 or payload.get("primaryContrastCountPerCell") != 4:
        raise ResultOpeningRefusal("analysis input state/contrast cardinality drift")
    if payload.get("resultOpeningBeforeAggregatePermitted") is not False or payload.get("epsilonSubstitutionPermitted") is not False:
        raise ResultOpeningRefusal("analysis input numeric/result-opening boundary drift")
    if not isinstance(payload.get("cells"), list) or len(payload["cells"]) != 24:
        raise ResultOpeningRefusal("exact 24-cell universe required")

    expected_states = set(analysis.EXPECTED_STATES)
    cells: list[dict[str, Any]] = []
    seen = set()
    for cell in payload["cells"]:
        cell_id = str(cell.get("analysisCellId") or "")
        if not cell_id or cell_id in seen:
            raise ResultOpeningRefusal(f"duplicate/missing analysis cell: {cell_id}")
        seen.add(cell_id)
        reps = cell.get("replicates")
        if not isinstance(reps, list) or len(reps) != 3:
            raise ResultOpeningRefusal(f"{cell_id}: exactly three replicates required")
        replicate_contrasts = []
        for expected_rep, rep in enumerate(reps, start=1):
            if rep.get("replicate") != expected_rep:
                raise ResultOpeningRefusal(f"{cell_id}: replicate identity/order drift")
            records = rep.get("recordsByState")
            if not isinstance(records, dict) or set(records) != expected_states:
                raise ResultOpeningRefusal(f"{cell_id}: exact five-state universe required")
            per_channel = {
                channel: analysis.scalar_replicate_contrasts(records, channel)
                for channel in analysis.PRIMARY_CHANNELS
            }
            replicate_contrasts.append(per_channel)
        summary = analysis.aggregate_three_replicates(replicate_contrasts)
        analysis.validate_numeric_policy(summary)
        cells.append({
            "analysisCellId": cell_id,
            "sunDepressionDeg": cell["sunDepressionDeg"],
            "aod550": cell["aod550"],
            "geometryId": cell["geometryId"],
            "geometryTag": cell["geometryTag"],
            "targetAltitudeDeg": cell["targetAltitudeDeg"],
            "relativeAzimuthDeg": cell["relativeAzimuthDeg"],
            "primarySummary": summary,
        })

    output = {
        "schemaVersion": 1,
        "stageId": f"{STAGE}-primary-analysis",
        "status": "COMPLETED_PREREGISTERED_AVPS_V1_PRIMARY_ANALYSIS_AFTER_EXACT_360_GATE",
        "workflowRunId": payload["workflowRunId"],
        "scientificOrdinal": payload["scientificOrdinal"],
        "caseCount": 360,
        "groupCount": 72,
        "analysisCellCount": 24,
        "statesPerGroup": 5,
        "primaryContrastCountPerCell": 4,
        "referenceStateId": analysis.REFERENCE,
        "alternativeStateIds": list(analysis.ALTERNATIVES),
        "primaryChannels": list(analysis.PRIMARY_CHANNELS),
        "sourceAnalysisInputContentSha256": payload["contentSha256"],
        "analysisGitBlobSha1": git_blob_sha1(analysis_path),
        "pValuesPermitted": False,
        "confidenceIntervalsPermitted": False,
        "epsilonSubstitutionPermitted": False,
        "universalSunDepressionToMinutesConversionPermitted": False,
        "productionMaterialityThresholdCreated": False,
        "taylorOrJerusalemScoringPerformed": False,
        "cells": cells,
    }
    output["contentSha256"] = canonical_sha256(output)
    return output
