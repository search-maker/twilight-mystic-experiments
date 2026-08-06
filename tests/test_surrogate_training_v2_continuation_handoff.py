from __future__ import annotations

import importlib.util
import json
import math
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "modeling/surrogate-training-v2/continuation_handoff.py"
spec = importlib.util.spec_from_file_location("continuation_handoff_tested", MODULE_PATH)
assert spec and spec.loader
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)

ADAPTIVE = [
    "train-0003","train-0007","train-0009","train-0011","train-0013","train-0015","train-0017","train-0019","train-0023","train-0027",
    "train-0029","train-0031","train-0033","train-0035","train-0039","train-0041","train-0043","train-0045","train-0046","train-0047",
]
WAVE2 = [gid for gid in ADAPTIVE if gid not in {"train-0017","train-0033","train-0045","train-0046"}]


def write(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    return path


def node_row(value: float):
    scalar = value / (6.83002 * sum(h.CIE))
    return [scalar] * 15


def result(case, value, stage, manifest_sha="f"*64):
    nodes = node_row(value)
    row = {
        "schemaVersion": 1,
        "stageId": stage,
        "status": "COMPLETED",
        "caseId": case["caseId"],
        "groupId": case["groupId"],
        "block": case["block"],
        "role": case["role"],
        "seed": case["seed"],
        "photonHistories": case["photonHistories"],
        "manifestSha256": manifest_sha,
        "runtimeReportSha256": "1"*64,
        "inputSha256": "2"*64,
        "radianceOutputSha256": "3"*64,
        "stdOutputSha256": "4"*64,
        "syntaxCheckCount": 1,
        "solverExecutionCount": 1,
        "selectedNodeRadiance": nodes,
        "selectedNodeStdRadiance": [0.0]*15,
        "selectedPhotopicContributionCdM2": h.photopic(nodes),
        "zeroHit": False,
        "fittingSurfaceExposed": False,
        "retryAllowed": False,
        "resumeAllowed": False,
    }
    row["contentSha256"] = h.canonical_sha256(row)
    return row


def reference():
    hard = [f"g0{i}-hard" for i in range(2,7)]
    soft = ["g01-soft"]
    anchors=[]
    for index,gid in enumerate(hard+soft,1):
        geometry={"sunDepressionDeg":2.0+index,"targetAltitudeDeg":10.0+index,"relativeAzimuthDeg":20.0+index,"observerElevationM":100.0*index,"aod550":0.05+0.01*index}
        anchors.append({"groupId":gid,"geometry":geometry,"methods":{"alis":{"meanCdM2":1.0+index,"nodeMeanRadiance":[0.1+index*0.01]*15}},"anchorStrength":"hard" if gid in hard else "soft-diagnostic","eligibleForTraining":False})
    return {"schemaVersion":1,"stageId":"twilight-model-readiness-v1","status":"REFERENCE_ANCHORS_VALIDATED","anchorCount":6,"trainingAutomaticallyAuthorized":False,"hardValidationAnchorIds":hard,"softDiagnosticAnchorIds":soft,"anchors":anchors}


def make_fixture(root: Path):
    source_records=[]
    for i in range(1,49):
        gid=f"train-{i:04d}"
        role="internal-holdout" if i%8==5 else "surrogate-training"
        is_adaptive=gid in ADAPTIVE
        values=[0.9,1.1] if is_adaptive else [0.99,1.01]
        mean=sum(values)/2
        source_records.append({
            "geometryId":gid,
            "geometry":{"geometryId":gid,"sunDepressionDeg":2.0+i%17,"targetAltitudeDeg":5.0+i%70,"relativeAzimuthDeg":float((i*17)%181),"observerElevationM":float(i*50),"aod550":0.05+(i%10)*0.02,"alisSpectralImportanceSamplingNm":550.0,"executionTierId":"tier-1-provisional","photonHistoriesPerBlock":20000000},
            "role":role,
            "classification":"ADAPTIVE_CONTINUATION_REQUIRED" if is_adaptive else "PRECISION_TARGET_MET",
            "numericalStatus":"NUMERICAL_PRECISION_INSUFFICIENT" if is_adaptive else "NUMERICALLY_CONVERGED",
            "scientificallyEligible":not is_adaptive,
            "eligibleForProvisionalFit":role=="surrogate-training" and not is_adaptive,
            "eligibleForInternalHoldout":role=="internal-holdout" and not is_adaptive,
            "executionComplete":True,
            "caseIds":[f"{gid}-alis-b1",f"{gid}-alis-b2"],
            "zeroHitCaseIds":[],
            "statistics":{
                "blockCount":2,"valuesCdM2":values,"nonzeroBlockValuesCdM2":values,"meanCdM2":mean,
                "sampleStdCdM2":math.sqrt(0.02) if is_adaptive else math.sqrt(0.0002),
                "relativeStandardErrorOfMean":0.1 if is_adaptive else 0.01,"relativeStandardErrorStatus":"COMPUTED",
                "zeroHitBlockCount":0,"zeroHitBlockFraction":0.0,"nodeMeanRadiance":node_row(mean),
            }
        })
    source={"records":source_records,"adaptiveContinuationRequiredGeometryIds":ADAPTIVE,"executionComplete":True,"internalHoldoutRecordCount":6}
    source_path=write(root/"source.json",source)
    w1_cases=[]; w2_cases=[]
    for gi,gid in enumerate(ADAPTIVE):
        role=next(x["role"] for x in source_records if x["geometryId"]==gid)
        for block in (3,4):
            w1_cases.append({"caseId":f"{gid}-precision-continuation-v5-b{block}","groupId":gid,"block":block,"role":role,"seed":10000+gi*2+block,"photonHistories":100000000})
        if gid in WAVE2:
            for block in (5,6):
                w2_cases.append({"caseId":f"{gid}-precision-continuation-wave2-v1-b{block}","groupId":gid,"block":block,"role":role,"seed":20000+gi*2+block,"photonHistories":100000000})
    w1_manifest=write(root/"w1-manifest.json",{"cases":w1_cases})
    w2_manifest=write(root/"w2-manifest.json",{"cases":w2_cases})
    w1_root=root/"w1-results"; w2_root=root/"w2-results"
    for case in w1_cases:
        write(w1_root/case["caseId"]/"case-result.json",result(case,1.0,"tier1-precision-continuation-wave1-ordinal11-execution-v5"))
    for case in w2_cases:
        write(w2_root/case["caseId"]/"case-result.json",result(case,1.0,"tier1-precision-continuation-wave2-ordinal12-execution-v1"))
    points=[]
    for gid in ADAPTIVE:
        values=[0.9,1.1,1.0,1.0] + ([1.0,1.0] if gid in WAVE2 else [])
        sample_std=__import__("statistics").stdev(values)
        rsem=sample_std/math.sqrt(len(values))/(sum(values)/len(values))
        points.append({"geometryId":gid,"role":next(x["role"] for x in source_records if x["geometryId"]==gid),"classification":"PRECISION_TARGET_MET","scientificallyEligible":True,"valuesCdM2":values,"blockCount":len(values),"relativeStandardErrorOfMean":rsem,"zeroHitBlockCount":0,"zeroHitBlockFraction":0.0})
    final_analysis=write(root/"analysis.json",{"analysis":{"status":"CONTINUATION_ANALYZED","nextWaveGeometryIds":[],"exhaustedGeometryIds":[],"scientificallyEligible":True,"points":points}})
    terminal=write(root/"terminal.json",{"status":"AUDITED_TWO_WAVE_ANALYSIS_COMPLETE","scientificallyEligible":True,"nextWaveGeometryIds":[],"exhaustedGeometryIds":[],"runAttempt":1,"caseCount":32})
    reference_path=write(root/"reference.json",reference())
    source_run=write(root/"run.json",{"id":123,"head_sha":"a"*40,"status":"completed","conclusion":"success","run_attempt":1})
    source_artifacts=write(root/"artifacts.json",{"artifacts":[{"id":i+1,"name":f"a{i}","digest":"sha256:"+"a"*64,"expired":False} for i in range(40)]})
    dummies=[write(root/f"dummy{i}.json",{}) for i in range(4)]
    return dict(source_dataset_path=source_path,wave1_manifest_path=w1_manifest,wave1_results_root=w1_root,wave2_manifest_path=w2_manifest,wave2_results_root=w2_root,wave1_aggregate_path=dummies[0],wave1_audit_path=dummies[1],wave2_aggregate_path=dummies[2],wave2_audit_path=dummies[3],final_analysis_path=final_analysis,terminal_report_path=terminal,reference_path=reference_path,source_run_path=source_run,source_artifacts_path=source_artifacts)


class ContinuationHandoffTests(unittest.TestCase):
    def test_builds_adapter_compatible_48_record_dataset(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw); args=make_fixture(root); paths=h.build(**args,output_dir=root/"out",exact_main_sha="b"*40)
            dataset=json.loads(paths["dataset"].read_text()); envelope=json.loads(paths["envelope"].read_text()); audit=json.loads(paths["audit"].read_text())
            self.assertEqual(len(dataset["records"]),48); self.assertEqual(len(dataset["trainingGeometryIds"]),42); self.assertEqual(len(dataset["internalHoldoutGeometryIds"]),6)
            continued=next(x for x in dataset["records"] if x["geometryId"]=="train-0003"); self.assertEqual(continued["statistics"]["blockCount"],6); self.assertEqual(len(continued["continuationCaseIds"]),4)
            short=next(x for x in dataset["records"] if x["geometryId"]=="train-0017"); self.assertEqual(short["statistics"]["blockCount"],4); self.assertEqual(len(short["continuationCaseIds"]),2)
            untouched=next(x for x in dataset["records"] if x["geometryId"]=="train-0001"); self.assertEqual(untouched["statistics"]["blockCount"],2); self.assertEqual(untouched["continuationCaseIds"],[])
            self.assertEqual(envelope["exactMainSha"],"b"*40); self.assertTrue(envelope["scientificExecution"]); self.assertFalse(envelope["productionModelReady"])
            self.assertEqual(audit["status"],"PASSED"); self.assertEqual(len(audit["caseResultHashes"]),72)

    def test_refuses_remaining_continuation(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw); args=make_fixture(root); analysis=json.loads(args["final_analysis_path"].read_text()); analysis["analysis"]["nextWaveGeometryIds"]=["train-0003"]; write(args["final_analysis_path"],analysis)
            with self.assertRaisesRegex(Exception,"not fully eligible"): h.build(**args,output_dir=root/"out",exact_main_sha="b"*40)

    def test_refuses_result_tamper_and_zero_hit(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw); args=make_fixture(root); path=next(args["wave2_results_root"].rglob("case-result.json")); row=json.loads(path.read_text()); row["selectedPhotopicContributionCdM2"]=0.0; write(path,row)
            with self.assertRaises(Exception): h.build(**args,output_dir=root/"out",exact_main_sha="b"*40)


if __name__=="__main__": unittest.main()
