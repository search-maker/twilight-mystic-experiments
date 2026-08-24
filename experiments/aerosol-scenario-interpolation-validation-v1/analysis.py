from __future__ import annotations

import hashlib
import importlib.util
import json
import math
from pathlib import Path
from typing import Any

STAGE = "aerosol-scenario-interpolation-validation-v1"
PROTOCOL_REL = Path("review/aerosol-scenario-interpolation-validation-v1/protocol.review.json")
PROTOCOL_BLOB = "27923f9d40d35b001c15b20b7909e3fcd12fd833"
EVALUATOR_REL = Path("review/aerosol-scenario-interpolation-validation-v1/evaluate_selected_model_v1.py")
EVALUATOR_BLOB = "063c49dbdd6626a3e67440c53508260ac7d23f70"
SELECTOR_REL = Path("review/asiv-v1-training-selector-implementation/select_training_model_v1.py")
SELECTOR_BLOB = "c65183f959244abc851de45e609bfc5a9b38cd67"
CHANNELS = ("photopicLuminanceCdM2", "scotopicLuminanceScotCdM2", "johnsonVEffectiveRadiance_mW_m2_nm_sr")
CONTRASTS = (
    ("continental_vs_native", "opac-continental-average"),
    ("maritime_vs_native", "opac-maritime-clean"),
    ("desert_vs_native", "opac-desert"),
    ("desert_spheroids_vs_native", "opac-desert-spheroids"),
)
NATIVE = "native-rural-ss"


class AnalysisRefusal(RuntimeError):
    pass


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _module(name: str, path: Path, blob: str):
    if git_blob_sha1(path) != blob:
        raise AnalysisRefusal(f"bound source byte drift: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AnalysisRefusal(f"cannot import {path}")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod


def qlinear(values: list[float], q: float) -> float:
    xs = sorted(float(x) for x in values)
    if not xs or not 0 <= q <= 1:
        raise AnalysisRefusal("quantile input invalid")
    pos = q * (len(xs) - 1); lo = int(math.floor(pos)); hi = int(math.ceil(pos))
    if lo == hi: return xs[lo]
    f = pos - lo; return xs[lo] * (1 - f) + xs[hi] * f


def summarize_three(values: list[float]) -> dict[str, Any]:
    if len(values) != 3 or any(not math.isfinite(float(x)) for x in values):
        return {"status": "NUMERICALLY_UNRESOLVED", "replicateValues": values, "mean": None, "sampleStd": None, "standardError": None}
    vals = [float(x) for x in values]; mean = sum(vals) / 3.0
    sample_std = math.sqrt(sum((x - mean) ** 2 for x in vals) / 2.0)
    return {"status": "FINITE_THREE_REPLICATES", "replicateValues": vals, "mean": mean, "sampleStd": sample_std, "standardError": sample_std / math.sqrt(3.0)}


def build_scalar_truth(case_results: list[dict[str, Any]]) -> dict[str, Any]:
    if len(case_results) != 120:
        raise AnalysisRefusal(f"exact 120 case results required, got {len(case_results)}")
    by_key: dict[tuple[str, int, str], dict[str, Any]] = {}
    for row in case_results:
        if row.get("status") != "COMPLETED" or row.get("workflowRunAttempt") != 1 or row.get("solverExecutionCount") != 1 or row.get("syntaxCheckCount") != 1:
            raise AnalysisRefusal("case execution identity/status drift")
        if row.get("retryPerformed") is not False or row.get("resumePerformed") is not False or row.get("githubRerun") is not False:
            raise AnalysisRefusal("rerun/retry/resume evidence detected")
        key = (str(row.get("holdoutId")), int(row.get("replicate")), str(row.get("stateId")))
        if key in by_key:
            raise AnalysisRefusal(f"duplicate case identity: {key}")
        channels = row.get("channels") or {}
        if any(not math.isfinite(float(channels.get(ch, float('nan')))) or float(channels[ch]) <= 0 for ch in CHANNELS):
            raise AnalysisRefusal(f"nonpositive/nonfinite integrated channel: {key}")
        by_key[key] = row
    expected = {(f"asiv-holdout-{h:02d}", r, state) for h in range(1, 9) for r in (1, 2, 3) for state in (NATIVE, *(x[1] for x in CONTRASTS))}
    if set(by_key) != expected:
        raise AnalysisRefusal("exact holdout/replicate/five-state case universe required")
    holdouts = []
    finite_rows = 0
    for h in range(1, 9):
        hid = f"asiv-holdout-{h:02d}"
        first = by_key[(hid, 1, NATIVE)]
        summaries: dict[str, dict[str, Any]] = {}
        replicate_records = []
        for r in (1, 2, 3):
            native = by_key[(hid, r, NATIVE)]
            group_seed = native.get("seed")
            records = {NATIVE: native}
            for _, state in CONTRASTS:
                alt = by_key[(hid, r, state)]
                if alt.get("seed") != group_seed or alt.get("groupId") != native.get("groupId"):
                    raise AnalysisRefusal(f"CRN pairing drift: {hid} replicate {r}")
                records[state] = alt
            replicate_records.append({"replicate": r, "groupId": native.get("groupId"), "seed": group_seed, "recordsByState": {state: {ch: float(records[state]["channels"][ch]) for ch in CHANNELS} for state in records}})
        for contrast, state in CONTRASTS:
            summaries[contrast] = {}
            for ch in CHANNELS:
                vals = []
                for rec in replicate_records:
                    a = rec["recordsByState"][state][ch]; n = rec["recordsByState"][NATIVE][ch]
                    vals.append(math.log(a / n))
                summary = summarize_three(vals); summaries[contrast][ch] = summary
                if summary["status"] == "FINITE_THREE_REPLICATES": finite_rows += 1
        holdouts.append({
            "holdoutId": hid,
            "sunDepressionDeg": first["sunDepressionDeg"],
            "targetAltitudeDeg": first["targetAltitudeDeg"],
            "relativeAzimuthDeg": first["relativeAzimuthDeg"],
            "observerElevationM": first["observerElevationM"],
            "aod550": first["aod550"],
            "replicates": replicate_records,
            "stateVsNative": summaries,
        })
    if finite_rows != 96:
        raise AnalysisRefusal(f"required 96 finite three-replicate scalar rows, got {finite_rows}")
    return {"schemaVersion": 1, "stageId": "asiv-v1-direct-scalar-truth", "status": "COMPLETE_EXACT_120_CASE_SCALAR_TRUTH", "caseCount": 120, "groupCount": 24, "holdoutCount": 8, "finiteThreeReplicateStateVsNativeChannelRows": 96, "holdouts": holdouts}


def evaluate(repository_root: Path, scalar_truth: dict[str, Any], predictions: dict[str, Any], analysis_index_path: Path) -> dict[str, Any]:
    protocol_path = repository_root / PROTOCOL_REL
    if git_blob_sha1(protocol_path) != PROTOCOL_BLOB:
        raise AnalysisRefusal("ASIV protocol byte drift")
    protocol = json.loads(protocol_path.read_text())
    dod = protocol["holdoutEvaluationDefinitionOfDone"]
    if scalar_truth.get("status") != "COMPLETE_EXACT_120_CASE_SCALAR_TRUTH" or scalar_truth.get("finiteThreeReplicateStateVsNativeChannelRows") != 96:
        raise AnalysisRefusal("scalar truth not complete")
    if predictions.get("status") != "PREDICTIONS_FROM_FROZEN_SELECTED_TRAINING_MODEL" or predictions.get("selectedModelCanonicalSha256") != "0b11a1691bfd2d9e3f073c786044bacedd3e9210bcb0660c76f21c34128a61af" or predictions.get("geometryCount") != 8:
        raise AnalysisRefusal("prediction identity/cardinality drift")
    evaluator = _module("asiv_bound_evaluator", repository_root / EVALUATOR_REL, EVALUATOR_BLOB)
    selector, _, _, _ = evaluator.reconstruct(analysis_index_path)
    if git_blob_sha1(repository_root / SELECTOR_REL) != SELECTOR_BLOB:
        raise AnalysisRefusal("selector byte drift")
    analysis_index = json.loads(analysis_index_path.read_text())
    cell_by_id = {str(c["analysisCellId"]): c for c in analysis_index.get("cells") or []}
    pred_by_id = {str(p["geometryId"]): p for p in predictions.get("predictions") or []}
    truth_by_id = {str(h["holdoutId"]): h for h in scalar_truth["holdouts"]}
    expected_ids = {f"asiv-holdout-{i:02d}" for i in range(1, 9)}
    if set(pred_by_id) != expected_ids or set(truth_by_id) != expected_ids:
        raise AnalysisRefusal("holdout identity universe drift")
    field_names = [f"{contrast}::{ch}" for contrast, _ in CONTRASTS for ch in CHANNELS]
    pred_rows=[]; truth_rows=[]; nearest_rows=[]; zero_rows=[]; per_holdout=[]; endpoint_errors=[]; signed_by_field=[[] for _ in range(12)]
    for hid in sorted(expected_ids):
        pr = pred_by_id[hid]; truth = truth_by_id[hid]
        pred_vec = [float(pr["predictedLogContrasts"][name]) for name in field_names]
        truth_vec = [float(truth["stateVsNative"][contrast][ch]["mean"]) for contrast, _ in CONTRASTS for ch in CHANNELS]
        near_id = str(pr["nearestOrdinal38TrainingCellId"])
        if near_id not in cell_by_id:
            raise AnalysisRefusal(f"nearest ordinal-38 cell missing: {near_id}")
        near_vec = [float(x) for x in selector.fields(cell_by_id[near_id])]
        if len(pred_vec)!=12 or len(truth_vec)!=12 or len(near_vec)!=12 or any(not math.isfinite(x) for x in pred_vec+truth_vec+near_vec):
            raise AnalysisRefusal("nonfinite/invalid 12-field evaluation vector")
        pred_rows.append(pred_vec); truth_rows.append(truth_vec); nearest_rows.append(near_vec); zero_rows.append([0.0]*12)
        abs_errors=[abs(a-b) for a,b in zip(pred_vec,truth_vec)]
        for j,(a,b) in enumerate(zip(pred_vec,truth_vec)): signed_by_field[j].append(a-b)
        per_holdout.append({"holdoutId":hid,"observerElevationM":truth["observerElevationM"],"meanAbsoluteLogContrastError":sum(abs_errors)/12.0,"worstAbsoluteLogContrastError":max(abs_errors),"nearestOrdinal38TrainingCellId":near_id})
        for ch_index,ch in enumerate(CHANNELS):
            pvals=[pred_vec[ci*3+ch_index] for ci in range(4)]; tvals=[truth_vec[ci*3+ch_index] for ci in range(4)]
            for endpoint,pv,tv in (("minimum_log_contrast",min(pvals),min(tvals)),("maximum_log_contrast",max(pvals),max(tvals))):
                err=abs(pv-tv); endpoint_errors.append(err)
    metrics = selector.metrics(pred_rows,truth_rows,nearest_rows,zero_rows)
    if len(endpoint_errors)!=48: raise AnalysisRefusal("scenario-envelope endpoint count drift")
    endpoint = {"definition":"per-holdout-per-channel min/max across four OPAC-vs-native log contrasts","endpointCount":48,"meanAbsoluteLogError":sum(endpoint_errors)/48.0,"worstAbsoluteLogError":max(endpoint_errors)}
    by_elevation: dict[str,list[float]]={}
    for row in per_holdout: by_elevation.setdefault(str(float(row["observerElevationM"])),[]).append(float(row["meanAbsoluteLogContrastError"]))
    if sorted(len(v) for v in by_elevation.values()) != [2,2,2,2]: raise AnalysisRefusal("four balanced elevation levels required")
    elevation = {key:{"holdoutCount":len(vals),"aggregateMeanAbsoluteLogContrastError":sum(vals)/len(vals)} for key,vals in sorted(by_elevation.items(),key=lambda kv:float(kv[0]))}
    checks = {
        "aggregateMeanAbsoluteLogContrastError": metrics["aggregateMeanAbsoluteLogContrastError"] <= float(dod["aggregateMeanAbsoluteLogContrastErrorMax"]),
        "medianAbsoluteLogContrastError": metrics["medianAbsoluteLogContrastError"] <= float(dod["medianAbsoluteLogContrastErrorMax"]),
        "p90AbsoluteLogContrastError": metrics["p90AbsoluteLogContrastError"] <= float(dod["p90AbsoluteLogContrastErrorMax"]),
        "worstAbsoluteLogContrastError": metrics["worstAbsoluteLogContrastError"] <= float(dod["worstAbsoluteLogContrastErrorMax"]),
        "maxOver12FieldsAbsoluteMeanSignedBias": metrics["maxOver12FieldsAbsoluteMeanSignedBias"] <= float(dod["maxOver12FieldsAbsoluteMeanSignedBiasMax"]),
        "improvementVsNearest": metrics["meanErrorImprovementVsNearestCellBaselineFraction"] is not None and metrics["meanErrorImprovementVsNearestCellBaselineFraction"] >= float(dod["aggregateMeanErrorImprovementVsNearestOrdinal38CellBaselineMinFraction"]),
        "improvementVsZero": metrics["meanErrorImprovementVsZeroContrastBaselineFraction"] is not None and metrics["meanErrorImprovementVsZeroContrastBaselineFraction"] >= float(dod["aggregateMeanErrorImprovementVsZeroContrastBaselineMinFraction"]),
        "eachElevation": all(row["aggregateMeanAbsoluteLogContrastError"] <= float(dod["eachElevationLevelAggregateMeanAbsoluteLogContrastErrorMax"]) for row in elevation.values()),
        "scenarioEnvelopeEndpointMean": endpoint["meanAbsoluteLogError"] <= float(dod["scenarioEnvelopeEndpointMeanAbsoluteLogErrorMax"]),
        "scenarioEnvelopeEndpointWorst": endpoint["worstAbsoluteLogError"] <= float(dod["scenarioEnvelopeEndpointWorstAbsoluteLogErrorMax"]),
        "allPredictionsFinite": metrics["allPredictionsFinite"] is True,
    }
    return {"schemaVersion":1,"stageId":"asiv-v1-frozen-scalar-holdout-evaluation","status":"PASS_FROZEN_SCALAR_GATES" if all(checks.values()) else "FAIL_FROZEN_SCALAR_GATES","selectedModelCanonicalSha256":predictions["selectedModelCanonicalSha256"],"requiredFiniteThreeReplicateStateVsNativeChannelRows":96,"metrics":metrics,"scenarioEnvelopeEndpoints":endpoint,"elevationLevels":elevation,"perHoldout":per_holdout,"gateChecks":checks,"allScalarGatesPass":all(checks.values()),"retuningPerformed":False,"epsilonSubstitutionPerformed":False,"fullSpectrumInterpolationPassClaim":False,"productionAuthorized":False}
