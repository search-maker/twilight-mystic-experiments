from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_ROOT = ROOT / "experiments/mystic-batch-v1"


def load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, MODULE_ROOT / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


core = load_module("g01_fixed_core", "g01_fixed_diagnostic_execution.py")
adapter = load_module("g01_fixed_adapter", "g01_fixed_diagnostic_adapter.py")


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n")


def held_values():
    return [0.004506067717766593, 0.003010531920610223, 0.0032999632406862296, 0.0038986015089986065]


def summary(values, node=0.0035):
    import math, statistics
    mean=statistics.fmean(values); std=statistics.stdev(values)
    return {"blockCount":len(values),"valuesCdM2":values,"meanCdM2":mean,"sampleStandardDeviationCdM2":std,"coefficientOfVariation":std/mean,"relativeStandardErrorOfMean":(std/mean)/math.sqrt(len(values)),"nodeMeanRadiance":[node]*15,"reportedNodeStdAvailable":False,"photopicWeightedReportedRelativeStd":None}


def proposal_fixture():
    cases=[]
    for ordinal,(block,seed) in enumerate(zip(range(5,9),core.NEW_SEEDS),start=1):
        cases.append({"ordinal":ordinal,"caseId":f"g01pd-alis-b{block}","groupId":core.GROUP_ID,"method":"alis","block":block,"seed":seed,"photonHistories":50_000_000,"alisSpectralImportanceSamplingNm":600.0,"purpose":"fixed-final-precision-diagnosis"})
    return {"schemaVersion":1,"stageId":core.STAGE_ID,"batchId":"g01-fixed-precision-diagnosis-v1","status":"PROPOSAL_ONLY_NOT_AUTHORIZATION","mode":"scientific-proposal","proposalOnly":True,"scientificExecution":False,"scientificDiagnostic":True,"successDoesNotAuthorizeProduction":True,"sourceRunId":30875148389,"diagnosisRawSha256":None,"selectedGeometryIds":[core.GROUP_ID],"selectedAlisReferenceNm":600.0,"existingHeldOutBlocks":[1,2,3,4],"newDiagnosticBlocks":[5,6,7,8],"cases":cases,"limits":{"maximumCases":4,"maximumParallel":4,"perCaseTimeoutSeconds":900,"maximumPhotonHistoriesPerBlock":50_000_000,"maximumConfiguredMcPhotonsSum":200_000_000},"analysisPlan":{"combineOnlyPreservedHeldOutBlocksAndNewDiagnosticBlocks":True,"combinedAlisBlockCount":8,"selectionDataExcludedFromAcceptanceDecision":True,"targetRelativeStandardErrorOfMean":0.08,"frozenReferenceMaximumRelativeStandardErrorOfMean":0.10,"integratedMeanRatioAlisToVroomClosedInterval":[0.5,2.0],"minimumVroomPhotopicWeightFractionNodeRatioInsideInterval":0.80,"passClassification":"G01_FIXED_PRECISION_DIAGNOSIS_PASSED","persistentVarianceClassification":"G01_PERSISTENT_HIGH_VARIANCE","methodDiscrepancyClassification":"G01_METHOD_DISCREPANCY","noAutomaticAdditionalBlocks":True},"executionAuthorizedByProposal":False,"surrogateTrainingAutomaticallyAuthorized":False,"productionModelReady":False,"observationValidationRequired":True}


def pilot_fixture():
    runtime={key:"a"*64 for key in ("uvspecSha256","uvspecHelpSha256","libRadtranDataTreeSha256","atmosphereSha256","runtimeLockRawSha256")}
    return {"stageId":"cross-geometry-pilot-v1","adapterId":"mystic-cross-geometry-v1","runtime":runtime,"frozenInputs":{"alisSpectralImportanceSamplingNm":405.0,"wavelengthDomainNm":[380,780],"diagnosticNodesNm":[470,480,490,500,510,520,530,540,560,580,590,600,610,640,660],"molecularAbsorption":"crs","mcSpherical":"1D","albedo":0.15,"dataPaths":{"solarFlux":{"root":"libRadtranData","path":"solar"},"wavelengthGrid":{"root":"repository","path":"grid"},"atmosphere":{"root":"libRadtranData","path":"atm"}}},"geometries":[{"geometryId":core.GROUP_ID,"sunDepressionDeg":6.0,"targetAltitudeDeg":30.0,"relativeAzimuthDeg":90.0,"observerElevationM":0.0,"aod550":0.15}]}


class FixedDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
        self.diagnosis=self.root/"diagnosis.json"; self.proposal=self.root/"proposal.json"; self.readiness=self.root/"readiness.json"
        self.run=self.root/"run.json"; self.artifacts=self.root/"artifacts.json"; self.pilot=self.root/"pilot.json"
        self.source_analysis=self.root/"source-analysis.json"; self.source_readiness=self.root/"source-readiness.json"; self.source_dataset=self.root/"source-dataset.json"
        write(self.source_analysis,{"schemaVersion":1,"stageId":"cross-geometry-held-out-confirmation-timeout-continuation-v1","status":"TIMEOUT_CONTINUATION_ANALYZED","computationalReferenceScreeningComplete":False,"noAutomaticAdditionalBlocks":True,"screeningOnly":True,"successDoesNotAuthorizeProduction":True})
        write(self.source_readiness,{"schemaVersion":1,"status":"COMPUTATIONAL_REFERENCE_SCREENING_REQUIRES_DIAGNOSIS","computationalReferenceScreeningComplete":False,"acceptedReferenceGeometryCount":5,"heldOutConfirmationFailureCount":1,"technicalDiagnosisRequiredGeometryIds":[core.GROUP_ID],"noAutomaticAdditionalBlocks":True,"productionModelReady":False,"observationValidationRequired":True,"surrogateTrainingAutomaticallyAuthorized":False})
        write(self.source_dataset,{"schemaVersion":1,"status":"INCOMPLETE_COMPUTATIONAL_REFERENCE_DATASET","records":[{"groupId":group} for group in ("g02-early-near-low","g03-early-perpendicular-high","g04-mid-perpendicular","g05-mid-opposite-low","g06-late-opposite-high-aerosol")]})
        vroom=summary([0.0031,0.0038,0.0034,0.0036,0.0035,0.0038],node=0.0035); held=summary(held_values(),node=0.00365)
        write(self.diagnosis,{"schemaVersion":1,"stageId":core.SOURCE_STAGE_ID,"status":"G01_MONTE_CARLO_PRECISION_DIAGNOSED","sourceRunId":30875148389,"groupId":core.GROUP_ID,"failureMode":"MONTE_CARLO_PRECISION_ONLY","structuralExecutionFailure":False,"methodCompatibilityPassed":True,"selectedAlisReferenceNm":600.0,"heldOutStatistics":held,"frozenVroomStatistics":vroom,"selectionDataExcludedFromAcceptanceDecision":True,"singleBlockDeletionAuthorized":False,"targetRelativeStandardErrorOfMean":0.08,"recommendedFixedTotalBlocks":8,"recommendedAdditionalBlocks":4,"planningHeuristicIsNotAcceptanceEvidence":True,"sourceAnalysisRawSha256":core.raw_sha256(self.source_analysis),"sourceReadinessRawSha256":core.raw_sha256(self.source_readiness),"sourceDatasetRawSha256":core.raw_sha256(self.source_dataset)})
        proposal=proposal_fixture(); proposal["diagnosisRawSha256"]=core.raw_sha256(self.diagnosis); write(self.proposal,proposal)
        write(self.readiness,{"schemaVersion":1,"stageId":core.SOURCE_STAGE_ID,"status":"G01_FIXED_PRECISION_DIAGNOSIS_PROPOSED_PENDING_SEPARATE_AUTHORIZATION","sourceRunId":30875148389,"diagnosisComplete":True,"failureMode":"MONTE_CARLO_PRECISION_ONLY","newCaseCount":4,"newConfiguredMcPhotonsSum":200_000_000,"scientificExecution":False,"executionAuthorized":False,"noAutomaticAdditionalBlocks":True,"surrogateTrainingAuthorized":False,"productionModelReady":False,"observationValidationRequired":True})
        write(self.run,{"id":321,"status":"completed","conclusion":"success","run_attempt":1,"head_branch":"main","head_sha":"b"*40,"name":core.SOURCE_WORKFLOW_NAME,"path":core.SOURCE_WORKFLOW_PATH,"event":"push"})
        write(self.artifacts,{"artifacts":[{"id":654,"name":core.SOURCE_ARTIFACT_NAME,"expired":False,"digest":"sha256:"+"c"*64,"workflow_run":{"id":321}}]}); write(self.pilot,pilot_fixture())

    def tearDown(self): self.tmp.cleanup()

    def audited_manifest(self):
        audit=core.source_audit(self.diagnosis,self.proposal,self.readiness,self.run,self.artifacts); audit_path=self.root/"source-audit.json"; write(audit_path,audit)
        manifest=core.build_manifest(self.proposal,self.pilot,audit_path); manifest_path=self.root/"manifest.json"; write(manifest_path,manifest)
        return audit,audit_path,manifest,manifest_path

    def test_source_audit_and_manifest_are_exact(self):
        audit,_,manifest,_=self.audited_manifest(); self.assertEqual(audit["status"],"G01_DIAGNOSIS_SOURCE_AUDITED"); self.assertEqual(len(manifest["cases"]),4); self.assertEqual(manifest["frozenInputs"]["alisSpectralImportanceSamplingNm"],600.0); self.assertTrue(manifest["noAutomaticAdditionalBlocks"])

    def test_source_audit_refuses_retry(self):
        value=json.loads(self.run.read_text()); value["run_attempt"]=2; write(self.run,value)
        with self.assertRaises(core.StageError): core.source_audit(self.diagnosis,self.proposal,self.readiness,self.run,self.artifacts)

    def test_adapter_forces_600_nm(self):
        _,_,manifest,manifest_path=self.audited_manifest(); runtime_path=self.root/"runtime.json"; write(runtime_path,{"schemaVersion":1,"stageId":"mystic-batch-v1","scientificSolverExecuted":False,"syntaxCheckExecuted":False,**manifest["runtime"]})
        stub=self.root/"base.py"; stub.write_text("""
def resolve_case(m,cid):
 c=[x for x in m['cases'] if x['caseId']==cid][0]; return c,m['geometries'][0]
def normalized_inputs(m,c,g): return {'alisSpectralImportanceSamplingNm':405.0}
def render_input(i,d,r,o): return f\"mc_spectral_is {i['alisSpectralImportanceSamplingNm']}\\n\"
""")
        old=adapter.BASE; adapter.BASE=stub
        try: result=adapter.prepare_case(manifest_path,runtime_path,core.NEW_CASE_IDS[0],self.root,self.root,self.root/"out")
        finally: adapter.BASE=old
        self.assertEqual(result["alisSpectralImportanceSamplingNm"],600.0); self.assertIn("600.0",Path(result["inputPath"]).read_text())

    def test_plan_is_four_cases_and_200m(self):
        _,_,_,manifest_path=self.audited_manifest(); guard_path=self.root/"guard.json"; write(guard_path,{"status":"AUTHORIZED","authorizationRef":"d"*40,"authorizationOrdinal":1,"executionKey":core.EXECUTION_KEY})
        for name in ("adapter.py","lock.json","workflow.yml"): (self.root/name).write_text("fixture\n")
        result=core.plan(manifest_path,guard_path,self.root/"adapter.py",self.root/"lock.json",self.root/"workflow.yml"); self.assertEqual(result["caseCount"],4); self.assertEqual(result["configuredMcPhotonsSum"],200_000_000); self.assertEqual(result["perCaseTimeoutSeconds"],900)

    def _case(self,cid,seed,value):
        return {"caseId":cid,"status":"COMPLETED","seed":seed,"photonHistories":50_000_000,"syntaxCheckCount":1,"solverExecutionCount":1,"syntax":{"exitCode":0,"timedOut":False},"solver":{"exitCode":0,"timedOut":False},"selectedPhotopicContributionCdM2":value,"selectedNodeRadiance":[value]*15}

    def _analysis(self,new_values):
        _,_,_,manifest_path=self.audited_manifest(); old_root=self.root/"old"; new_root=self.root/"new"
        for i,value in enumerate(held_values(),1): write(old_root/f"r{i}/case-result.json",self._case(f"cgc-g01-alis-r{i}",80600+i,value))
        for i,value in enumerate(new_values): write(new_root/f"n{i}/case-result.json",self._case(core.NEW_CASE_IDS[i],core.NEW_SEEDS[i],value))
        batch=self.root/"batch.json"; audit=self.root/"audit.json"; conv=self.root/"conv.py"; write(batch,{"classification":"BATCH_NUMERICALLY_COMPLETE","caseCountCompleted":4,"configuredMcPhotonsSum":200_000_000}); write(audit,{"status":"PASSED","caseResultCount":4})
        conv.write_text("""
def classify(methods,rules):
 v=methods['reference-vroom']; a=methods['alis']; ratios=[x/y for x,y in zip(a['nodeMeanRadiance'],v['nodeMeanRadiance'])]
 return {'meanRatioAlisToVroom':a['meanCdM2']/v['meanCdM2'],'vroomPhotopicWeightFractionNodeRatioInsideInterval':sum(1 for r in ratios if .5<=r<=2)/len(ratios),'nodeMeanRatiosAlisToVroom':ratios}
""")
        return core.analyze(self.diagnosis,self.proposal,manifest_path,self.source_analysis,self.source_readiness,self.source_dataset,old_root,new_root,batch,audit,conv)

    def test_analysis_can_pass_fixed_endpoint(self):
        result,dataset,readiness=self._analysis([0.00355,0.00365,0.00360,0.00370]); self.assertEqual(result["classification"],"G01_FIXED_PRECISION_DIAGNOSIS_PASSED"); self.assertEqual(len(dataset["records"]),6); self.assertTrue(readiness["computationalReferenceScreeningComplete"])

    def test_analysis_stops_on_persistent_variance(self):
        result,dataset,readiness=self._analysis([0.0010,0.0065,0.0012,0.0068]); self.assertEqual(result["classification"],"G01_PERSISTENT_HIGH_VARIANCE"); self.assertEqual(len(dataset["records"]),5); self.assertFalse(readiness["computationalReferenceScreeningComplete"])

    def test_authorization_proposal_binds_disabled_parent(self):
        audit,audit_path,_,manifest_path=self.audited_manifest(); repo=self.root/"repo"; subprocess.run(["git","init","-q",repo],check=True); subprocess.run(["git","-C",repo,"config","user.email","test@example.com"],check=True); subprocess.run(["git","-C",repo,"config","user.name","Test"],check=True)
        template=json.loads((MODULE_ROOT/"authorization.g01-fixed-precision-diagnosis-template.json").read_text()); write(repo/core.AUTH_TEMPLATE_PATH,template); write(repo/core.AUTH_PATH,template)
        for path in core.bound_paths().values():
            target=repo/path; target.parent.mkdir(parents=True,exist_ok=True); target.write_text(f"fixture {path}\n")
        subprocess.run(["git","-C",repo,"add","."],check=True); subprocess.run(["git","-C",repo,"commit","-qm","base"],check=True)
        result=core.authorization_proposal(repo,audit_path,manifest_path); self.assertEqual(result["status"],"PROPOSAL_ONLY_NOT_AUTHORIZATION"); self.assertFalse(result["executionAuthorizedByProposal"]); self.assertEqual(result["authorization"]["authorizationOrdinal"],1)


if __name__ == "__main__": unittest.main()
