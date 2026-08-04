from __future__ import annotations
import importlib.util, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'experiments/model-readiness-v1/tier1_proposal.py';spec=importlib.util.spec_from_file_location('tier1_profiles',path);m=importlib.util.module_from_spec(spec);assert spec and spec.loader;spec.loader.exec_module(m)
class Tier1SourceProfiles(unittest.TestCase):
 def source(self,stage,name,path,artifact):
  analysis={'schemaVersion':1,'stageId':stage,'status':m.SOURCE_PROFILES[stage]['status'],'computationalReferenceScreeningComplete':True,'noAutomaticAdditionalBlocks':True,'screeningOnly':True,'successDoesNotAuthorizeProduction':True}
  run={'id':123,'status':'completed','conclusion':'success','event':'workflow_dispatch','run_attempt':1,'head_branch':'main','head_sha':'a'*40,'name':name,'path':path}
  artifacts={'artifacts':[{'id':9,'name':artifact,'digest':'sha256:'+'b'*64,'expired':False,'workflow_run':{'id':123}}]}
  return analysis,run,artifacts
 def test_both_completed_source_profiles_are_supported(self):
  for stage,p in m.SOURCE_PROFILES.items():
   result=m.validate_source(*self.source(stage,p['workflowName'],p['workflowPath'],p['artifact']))
   self.assertEqual(result['stageId'],stage);self.assertEqual(result['artifactName'],p['artifact'])
 def test_profile_mismatch_is_refused(self):
  stage='g01-fixed-precision-diagnosis-execution-v1';p=m.SOURCE_PROFILES[stage];analysis,run,artifacts=self.source(stage,p['workflowName'],p['workflowPath'],p['artifact']);run['name']='wrong'
  with self.assertRaises(m.ProposalError):m.validate_source(analysis,run,artifacts)
if __name__=='__main__':unittest.main()
