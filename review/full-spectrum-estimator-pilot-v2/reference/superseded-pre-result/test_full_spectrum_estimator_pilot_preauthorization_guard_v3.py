from __future__ import annotations
import importlib.util,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('guard3',ROOT/'full_spectrum_estimator_pilot_preauthorization_guard_v3.py'); assert s and s.loader; guard=importlib.util.module_from_spec(s); s.loader.exec_module(guard)
C=json.loads((ROOT/'full-spectrum-estimator-pilot-preauthorization-contract-v3.json').read_text()); E=json.loads((ROOT/'full-spectrum-estimator-pilot-execution-manifest-v4.json').read_text()); R=json.loads((ROOT/'rendered-review-v5/renderer-review-report.json').read_text())
def ctx(): return {'schemaVersion':1,'mode':'PRE_AUTHORIZATION','issue60':{'latestDirectiveToken':'MYSTIC-STATE-0066','supersedingDirectivePresent':False},'publication':{'packagePublished':True,'reviewPrNumber':109,'reviewHeadSha':'a'*40,'reviewBaseMainSha':'b'*40,'liveMainSha':'b'*40,'reviewChecksPassed':True,'publishedFileRawSha256':C['staticFileRawSha256']},'collisionRecheck':{'executionKeyCodeCollisionCount':0,'executionKeyIssueCollisionCount':0,'executionKeyPrCollisionCount':0,'authorizationBranchHistoricalRunCount':0,'dispatchBranchHistoricalRunCount':0,'exactCaseArtifactCount':0,'terminalArtifactCount':0,'authorizationBranchCurrentExists':False,'dispatchBranchCurrentExists':False},'seedRecheck':{'historicalSourceCount':166,'historicalUniqueSeedCount':166,'candidateSeedCount':44,'candidateUniqueSeedCount':44,'sourceCandidateSeedIntersectionCount':0,'sourceCandidateSeedIntersection':[],'executionManifestSha256':E['manifestSha256']},'runtimeIdentity':E['runtimeIdentityRequired'],'rendererRecheck':{'reportSha256':R['reportSha256'],'casesCanonicalSha256':R['casesCanonicalSha256'],'caseCount':44,'allPhysicalFingerprintsMatchHistorical':True,'allRenderedInputHashesMatchReport':True,'executionManifestSha256':E['manifestSha256']},'candidateIdentity':C['candidateIdentity'],'authorizationCommit':None}
class T(unittest.TestCase):
 def test_static_and_pre_auth(self):
  out=guard.evaluate(ctx()); self.assertEqual(out['status'],'READY_TO_CREATE_SEPARATE_ONE_FILE_AUTHORIZATION_NOT_EXECUTION_AUTHORIZED'); self.assertFalse(out['scientificExecutionAuthorized']); self.assertEqual(out['screeningAnalysisProtocolSha256'],C['screeningAnalysisProtocolSha256'])
 def test_main_move_refused(self):
  x=ctx(); x['publication']['liveMainSha']='c'*40
  with self.assertRaisesRegex(guard.Refusal,'live main moved'): guard.evaluate(x)
 def test_directive_refused(self):
  x=ctx(); x['issue60']['latestDirectiveToken']='MYSTIC-STATE-0067'; x['issue60']['supersedingDirectivePresent']=True
  with self.assertRaises(guard.Refusal): guard.evaluate(x)
 def test_static_analysis_tamper_refused(self):
  x=ctx(); x['publication']['publishedFileRawSha256']=dict(x['publication']['publishedFileRawSha256']); x['publication']['publishedFileRawSha256']['analysis']='0'*64
  with self.assertRaisesRegex(guard.Refusal,'published review-head file hashes'): guard.evaluate(x)
 def test_runtime_refused(self):
  x=ctx(); x['runtimeIdentity']=dict(x['runtimeIdentity']); x['runtimeIdentity']['uvspecSha256']='0'*64
  with self.assertRaisesRegex(guard.Refusal,'runtime identity'): guard.evaluate(x)
 def test_post_auth_requires_exact_parent_and_one_file(self):
  x=ctx(); x['mode']='POST_AUTHORIZATION_COMMIT'; x['authorizationCommit']={'sha':'c'*40,'parentSha':'a'*40,'branch':C['candidateIdentity']['authorizationBranch'],'merged':False,'authorizationOrdinal':14,'executionKey':C['candidateIdentity']['executionKey'],'changedFiles':['experiments/full-spectrum-estimator-pilot-v2/authorization.json'],'scientificPayloadChanged':False}
  out=guard.evaluate(x); self.assertTrue(out['authorizationStructureValid']); self.assertFalse(out['dispatchPermitted'])
  y=ctx(); y['mode']='POST_AUTHORIZATION_COMMIT'; y['authorizationCommit']=dict(x['authorizationCommit']); y['authorizationCommit']['changedFiles']=['a','b']
  with self.assertRaisesRegex(guard.Refusal,'exactly one file'): guard.evaluate(y)
if __name__=='__main__': unittest.main()
