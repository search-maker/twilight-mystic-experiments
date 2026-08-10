from __future__ import annotations
import importlib.util,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('g',ROOT/'full_spectrum_estimator_pilot_preauthorization_guard_v2.py'); assert s and s.loader; g=importlib.util.module_from_spec(s); s.loader.exec_module(g)
C=json.loads((ROOT/'full-spectrum-estimator-pilot-preauthorization-contract-v2.json').read_text()); E=json.loads((ROOT/'full-spectrum-estimator-pilot-execution-manifest-v4.json').read_text()); R=json.loads((ROOT/'rendered-review-v5/renderer-review-report.json').read_text())
def ctx(): return {'schemaVersion':1,'mode':'PRE_AUTHORIZATION','issue60':{'latestDirectiveToken':'MYSTIC-STATE-0066','supersedingDirectivePresent':False},'publication':{'packagePublished':True,'reviewPrNumber':123,'reviewHeadSha':'a'*40,'reviewBaseMainSha':'b'*40,'liveMainSha':'b'*40,'reviewChecksPassed':True,'publishedFileRawSha256':C['staticFileRawSha256']},'collisionRecheck':{'executionKeyCodeCollisionCount':0,'executionKeyIssueCollisionCount':0,'executionKeyPrCollisionCount':0,'authorizationBranchHistoricalRunCount':0,'dispatchBranchHistoricalRunCount':0,'exactCaseArtifactCount':0,'terminalArtifactCount':0,'authorizationBranchCurrentExists':False,'dispatchBranchCurrentExists':False},'seedRecheck':{'historicalSourceCount':166,'historicalUniqueSeedCount':166,'candidateSeedCount':44,'candidateUniqueSeedCount':44,'sourceCandidateSeedIntersectionCount':0,'sourceCandidateSeedIntersection':[],'executionManifestSha256':E['manifestSha256']},'runtimeIdentity':E['runtimeIdentityRequired'],'rendererRecheck':{'reportSha256':R['reportSha256'],'casesCanonicalSha256':R['casesCanonicalSha256'],'caseCount':44,'allPhysicalFingerprintsMatchHistorical':True,'allRenderedInputHashesMatchReport':True,'executionManifestSha256':E['manifestSha256']},'candidateIdentity':C['candidateIdentity'],'authorizationCommit':None}
class T(unittest.TestCase):
 def test_ready_is_structural_only(self):
  o=g.evaluate(ctx()); self.assertIn('READY_TO_CREATE',o['status']); self.assertFalse(o['scientificExecutionAuthorized']); self.assertFalse(o['dispatchPermitted'])
 def test_common_refusals(self):
  for mutate in (lambda x:x['publication'].__setitem__('packagePublished',False),lambda x:x['collisionRecheck'].__setitem__('dispatchBranchHistoricalRunCount',1),lambda x:x['publication'].__setitem__('liveMainSha','c'*40),lambda x:x['rendererRecheck'].__setitem__('casesCanonicalSha256','0'*64)):
   x=ctx(); mutate(x)
   with self.assertRaises(g.Refusal): g.evaluate(x)
 def test_seed_and_runtime_refused(self):
  x=ctx(); x['seedRecheck']['sourceCandidateSeedIntersectionCount']=1; x['seedRecheck']['sourceCandidateSeedIntersection']=[970001]
  with self.assertRaises(g.Refusal): g.evaluate(x)
  x=ctx(); x['runtimeIdentity']=dict(x['runtimeIdentity']); x['runtimeIdentity']['uvspecSha256']='0'*64
  with self.assertRaises(g.Refusal): g.evaluate(x)
 def test_post_authorization_exactly_one_file_only(self):
  x=ctx(); x['mode']='POST_AUTHORIZATION_COMMIT'; base={'sha':'c'*40,'parentSha':'a'*40,'branch':C['candidateIdentity']['authorizationBranch'],'merged':False,'authorizationOrdinal':14,'executionKey':C['candidateIdentity']['executionKey'],'scientificPayloadChanged':False}; x['authorizationCommit']={**base,'changedFiles':['experiments/full-spectrum-estimator-pilot-v2/authorization.json','README.md']}
  with self.assertRaises(g.Refusal): g.evaluate(x)
  x['authorizationCommit']={**base,'changedFiles':['experiments/full-spectrum-estimator-pilot-v2/authorization.json']}; o=g.evaluate(x); self.assertIn('STRUCTURALLY_VALID',o['status']); self.assertFalse(o['dispatchPermitted'])
if __name__=='__main__': unittest.main()
