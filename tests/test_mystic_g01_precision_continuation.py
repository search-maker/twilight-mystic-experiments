from __future__ import annotations
import importlib.util, json, math, statistics, tempfile, unittest, hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "experiments/mystic-batch-v1"

def module(name: str, path: Path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);assert spec and spec.loader;spec.loader.exec_module(m);return m
AUDIT=module("g01_source_audit",BASE/"cross_geometry_g01_precision_source_audit.py")
PLAN=module("g01_plan",BASE/"cross_geometry_g01_precision_execution_plan.py")
ANALYSIS=module("g01_analysis",BASE/"cross_geometry_g01_precision_analysis_driver.py")

def write(path: Path, value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2,sort_keys=True)+"\n")

def method(values, mean=None):
    mean=statistics.mean(values) if mean is None else mean
    sd=statistics.stdev(values);cv=sd/mean
    return {"blockCount":len(values),"valuesCdM2":values,"meanCdM2":mean,"sampleStandardDeviationCdM2":sd,"coefficientOfVariation":cv,"relativeStandardErrorOfMean":cv/math.sqrt(len(values)),"nodeMeanRadiance":[mean/40]*15,"reportedNodeStdAvailable":False,"photopicWeightedReportedRelativeStd":None}

class G01PrecisionTests(unittest.TestCase):
    def make_source(self, root: Path):
        proposal=json.loads((BASE/"g01-fixed-diagnostic-execution.proposal.json").read_text())
        old=[0.004506067717766593,0.003010531920610223,0.0032999632406862296,0.0038986015089986065]
        vroom_vals=[0.0030667663372535036,0.0043350386845514175,0.0025989544753383742,0.0033054814482914954,0.003914309208951925,0.003980629762365087]
        g01={"groupId":"g01-reference-bridge","classification":"HELD_OUT_CONFIRMATION_INCONCLUSIVE_PRECISION_CAP_REACHED","meanRatioAlisToVroom":1.0411093471572315,"vroomPhotopicWeightFractionNodeRatioInsideInterval":0.9650038923996925,"methodStatistics":{"alis":method(old),"reference-vroom":method(vroom_vals)}}
        g06={"groupId":"g06-late-opposite-high-aerosol","classification":"HELD_OUT_CONFIRMATION_PASSED"}
        analysis={"schemaVersion":1,"stageId":"cross-geometry-held-out-confirmation-timeout-continuation-v1","status":"TIMEOUT_CONTINUATION_ANALYZED","computationalReferenceScreeningComplete":False,"noAutomaticAdditionalBlocks":True,"screeningOnly":True,"successDoesNotAuthorizeProduction":True,"geometryResults":[g01,g06]}
        readiness={"schemaVersion":1,"status":"COMPUTATIONAL_REFERENCE_SCREENING_REQUIRES_DIAGNOSIS","computationalReferenceScreeningComplete":False,"acceptedReferenceGeometryCount":5,"heldOutConfirmationFailureCount":1,"technicalDiagnosisRequiredGeometryIds":["g01-reference-bridge"],"productionModelReady":False,"observationValidationRequired":True,"surrogateTrainingAutomaticallyAuthorized":False,"noAutomaticAdditionalBlocks":True}
        groups=["g02-early-near-low","g03-early-perpendicular-high","g04-mid-perpendicular","g05-mid-opposite-low","g06-late-opposite-high-aerosol"]
        records=[]
        for i,g in enumerate(groups,2):
            vals=[1.0+i/100,1.01+i/100]
            records.append({"groupId":g,"geometry":{"geometryId":g,"sunDepressionDeg":4.0,"targetAltitudeDeg":10.0,"relativeAzimuthDeg":30.0,"observerElevationM":0.0,"aod550":0.15},"methodStatistics":{"reference-vroom":{"valuesCdM2":vals,"meanCdM2":statistics.mean(vals),"coefficientOfVariation":0.01,"nodeMeanRadiance":[0.1]*15},"alis":{"valuesCdM2":vals,"meanCdM2":statistics.mean(vals),"coefficientOfVariation":0.01,"nodeMeanRadiance":[0.1]*15}},"methodOrigins":{"reference-vroom":"frozen","alis":"frozen"},"meanRatioAlisToVroom":1.0,"nodeAgreementFraction":1.0})
        dataset={"schemaVersion":1,"status":"INCOMPLETE_COMPUTATIONAL_REFERENCE_DATASET","sourceStageId":"cross-geometry-held-out-confirmation-timeout-continuation-v1","screeningOnly":True,"observationValidationRequired":True,"records":records}
        diagnosis_dir=root/"diagnosis"
        diagnosis={"schemaVersion":1,"stageId":"g01-fixed-precision-diagnosis-proposal-v1","status":"G01_MONTE_CARLO_PRECISION_DIAGNOSED","failureMode":"MONTE_CARLO_PRECISION_ONLY"}
        write(diagnosis_dir/"g01-precision-diagnosis.json",diagnosis)
        diagnosis_hash=hashlib.sha256((diagnosis_dir/"g01-precision-diagnosis.json").read_bytes()).hexdigest()
        proposal["diagnosisRawSha256"]=diagnosis_hash
        diag_proposal={k:proposal[k] for k in ("batchId","cases","limits","analysisPlan","selectedAlisReferenceNm","selectedGeometryIds","sourceRunId","sourceAnalysisArtifactId","sourceAnalysisArtifactDigest","diagnosisRawSha256","stageId")}
        write(diagnosis_dir/"g01-fixed-diagnostic-proposal.json",diag_proposal)
        write(diagnosis_dir/"g01-diagnosis-readiness.json",{"status":"G01_FIXED_PRECISION_DIAGNOSIS_PROPOSED_PENDING_SEPARATE_AUTHORIZATION","executionAuthorized":False,"noAutomaticAdditionalBlocks":True})
        ad=root/"analysis";write(ad/"timeout-continuation-analysis.json",analysis);write(ad/"reference-readiness.json",readiness);write(ad/"audited-reference-dataset.json",dataset)
        pf=root/"preflight";write(pf/"manifest.json",{"stageId":"cross-geometry-held-out-confirmation-timeout-continuation-v1"})
        for index,(case,seed,_) in enumerate([(x["caseId"],x["seed"],x["photonHistories"]) for x in proposal["preservedHeldOutCases"]]):
            row={"caseId":case,"status":"COMPLETED","seed":seed,"photonHistories":50_000_000,"solver":{"exitCode":0,"timedOut":False},"syntax":{"exitCode":0,"timedOut":False},"selectedPhotopicContributionCdM2":old[index],"selectedNodeRadiance":[old[index]/40]*15}
            write(pf/"source-g01"/case/"case-result.json",row)
        run={"id":30875148389,"status":"completed","conclusion":"success","event":"workflow_dispatch","run_attempt":1,"head_branch":"main","head_sha":"68617143a92ed8aef12e0cbdbaaf66a77c731bb1","name":"MYSTIC held-out timeout continuation v1 scientific execution","path":".github/workflows/mystic-batch-v1-cross-geometry-confirmation-timeout-continuation.yml","display_title":"key=cross-geometry-held-out-confirmation-timeout-continuation-v1:screening:6 auth=7a348428327f1dfbac3d0606e7661ecd766d5b92 ordinal=6"}
        artifacts={"artifacts":[{"name":proposal["sourceAnalysisArtifactName"],"digest":proposal["sourceAnalysisArtifactDigest"],"expired":False},{"name":proposal["sourcePreflightArtifactName"],"digest":proposal["sourcePreflightArtifactDigest"],"expired":False}]}
        write(root/"run.json",run);write(root/"artifacts.json",artifacts)
        diagnosis_run={"id":30876899126,"status":"completed","conclusion":"success","event":"pull_request","run_attempt":1,"head_branch":"agent/g01-precision-diagnosis-v1","head_sha":"9d6f155936578b8d409d25dfe57c7b741bda6915","name":"G01 fixed precision diagnosis proposal","path":".github/workflows/g01-fixed-precision-diagnosis-proposal.yml"}
        diagnosis_artifacts={"artifacts":[{"id":8879848416,"name":"g01-fixed-precision-diagnosis-proposal-v1","expired":False,"digest":"sha256:8b53ff4b0fd16a0523b186fe41bfcab3238f80e34e10b4be7dda257c716b4db4"}]}
        write(root/"diagnosis-run.json",diagnosis_run);write(root/"diagnosis-artifacts.json",diagnosis_artifacts)
        return proposal,diagnosis_dir,root/"diagnosis-run.json",root/"diagnosis-artifacts.json",ad,pf,root/"run.json",root/"artifacts.json",old

    def test_source_audit_reproduces_narrow_precision_gap(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);proposal,dd,dr,da,ad,pf,run,arts,_=self.make_source(root);pp=root/"proposal.json";write(pp,proposal)
            result=AUDIT.audit(pp,dd,dr,da,ad,pf,run,arts)
            self.assertEqual(result["status"],"SOURCE_G01_FIXED_PROPOSAL_AUDITED")
            self.assertEqual(result["recommendedFreshBlockCount"],4)
            self.assertLess(result["projectedRelativeStandardErrorAtEightBlocks"],0.08)

    def test_source_audit_refuses_non_precision_discrepancy(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);proposal,dd,dr,da,ad,pf,run,arts,_=self.make_source(root);data=json.loads((ad/"timeout-continuation-analysis.json").read_text());data["geometryResults"][0]["meanRatioAlisToVroom"]=2.5;write(ad/"timeout-continuation-analysis.json",data);pp=root/"proposal.json";write(pp,proposal)
            with self.assertRaises(ValueError): AUDIT.audit(pp,dd,dr,da,ad,pf,run,arts)

    def test_exact_plan_is_four_parallel_50m_cases(self):
        manifest=json.loads((BASE/"g01-fixed-diagnostic-execution.proposal.json").read_text())
        result=PLAN.build(manifest,{"stageId":manifest["stageId"],"status":"AUTHORIZED"})
        self.assertEqual(result["caseCount"],4);self.assertEqual(result["configuredMcPhotonsSum"],200_000_000);self.assertEqual(result["timeoutSeconds"],900)

    def test_analysis_assembles_six_normalized_records(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);proposal,_,_,_,ad,pf,_,_,old=self.make_source(root);pp=root/"proposal.json";write(pp,proposal)
            newroot=root/"new"
            new=[0.00355,0.00372,0.00361,0.00383]
            for i,value in enumerate(new,5):
                row={"caseId":f"g01pd-alis-b{i}","status":"COMPLETED","solver":{"exitCode":0,"timedOut":False},"syntax":{"exitCode":0,"timedOut":False},"selectedPhotopicContributionCdM2":value,"selectedNodeRadiance":[value/40]*15}
                write(newroot/f"c{i}"/"case-result.json",row)
            write(root/"summary.json",{"classification":"BATCH_NUMERICALLY_COMPLETE","caseCountCompleted":4,"caseCountFailed":0,"configuredMcPhotonsSum":200_000_000})
            write(root/"audit.json",{"status":"PASSED","caseResultCount":4})
            conv=root/"conv.py";conv.write_text("""
import math,statistics
def method_summary(values,nodes,reported):
 m=statistics.mean(values);s=statistics.stdev(values);cv=s/m
 return {'blockCount':len(values),'valuesCdM2':values,'meanCdM2':m,'sampleStandardDeviationCdM2':s,'coefficientOfVariation':cv,'relativeStandardErrorOfMean':cv/math.sqrt(len(values)),'nodeMeanRadiance':nodes,'reportedNodeStdAvailable':False,'photopicWeightedReportedRelativeStd':None}
def classify(stats,thresholds):
 a=stats['alis'];v=stats['reference-vroom'];return {'meanRatioAlisToVroom':a['meanCdM2']/v['meanCdM2'],'vroomPhotopicWeightFractionNodeRatioInsideInterval':1.0,'nodeMeanRatiosAlisToVroom':[1.0]*15}
""")
            pilot=root/"pilot.json";write(pilot,{"geometries":[{"geometryId":"g01-reference-bridge","sunDepressionDeg":12.0,"targetAltitudeDeg":10.0,"relativeAzimuthDeg":120.0,"observerElevationM":0.0,"aod550":0.15}]})
            out=root/"out";result=ANALYSIS.analyze(pp,ad,pf,newroot,root/"summary.json",root/"audit.json",conv,pilot,out)
            self.assertTrue(result["computationalReferenceScreeningComplete"])
            dataset=json.loads((out/"audited-reference-dataset.json").read_text());self.assertEqual(dataset["status"],"AUDITED_COMPUTATIONAL_REFERENCE_DATASET");self.assertEqual(len(dataset["records"]),6)
            for record in dataset["records"]:
                for stats in record["methodStatistics"].values():
                    self.assertIn("blockCount",stats);self.assertIn("relativeStandardErrorOfMean",stats)

if __name__ == "__main__": unittest.main()
