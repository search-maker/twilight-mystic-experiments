import importlib.util,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('m',ROOT/'experiments/tier2-disabled-readiness-v1/package.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def design():
 gs=[];cs=[];tiers=[]
 for i in range(1,97):
  tid='tier-1-provisional' if i<=48 else 'tier-2-completion';gid=f'train-{i:04d}';gs.append({'geometryId':gid,'executionTierId':tid});p=20000000 if i%8 in (0,1,2) else 50000000 if i%8 in (3,4) else 100000000 if i%8==5 else 200000000
  for b in (1,2):cs.append({'caseId':f'{gid}-alis-b{b}','groupId':gid,'executionTierId':tid,'role':'internal-holdout' if i%5==0 else 'surrogate-training','seed':910000+len(cs)+1,'photonHistories':p})
 t2=[c for c in cs if c['executionTierId']=='tier-2-completion'];t2[-1]['photonHistories']+=7320000000-sum(c['photonHistories'] for c in t2)
 for tid in ('tier-1-provisional','tier-2-completion'):tiers.append({'tierId':tid,'geometryIds':[g['geometryId'] for g in gs if g['executionTierId']==tid],'caseIds':[c['caseId'] for c in cs if c['executionTierId']==tid]})
 return {'stageId':'twilight-surrogate-training-design-v1','proposalOnly':True,'geometryCount':96,'caseCount':192,'executionTiers':tiers,'geometries':gs,'cases':cs}
class T(unittest.TestCase):
 def test_disabled(self):
  p=m.build(design(),{'uvspec':'a'*64});self.assertEqual(p['configuredMcPhotonsSum'],7320000000);self.assertFalse(p['automaticTrigger']);self.assertFalse(m.authorization_template(p)['enabled'])
 def test_fake_audit(self):
  p=m.build(design(),{});r=[{'caseId':c['caseId'],'seed':c['seed'],'syntaxCheckCount':1,'solverExecutionCount':1,'artifactSha256':'a'*64} for c in p['cases']];self.assertEqual(m.audit(p,r)['status'],'PASSED')
if __name__=='__main__':unittest.main()
