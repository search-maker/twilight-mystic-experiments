import importlib.util,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('m',ROOT/'experiments/tier1-precision-continuation-v1/package.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def fixture(r=.09):
 rec=[]
 for i in range(48): rec.append({'geometryId':f'train-{i+1:04d}','role':'internal-holdout' if (i+1)%5==0 else 'surrogate-training','statistics':{'relativeStandardErrorOfMean':r if i==0 else .04,'photonHistoriesPerBlock':20000000}})
 return {'geometryCount':48,'caseCount':96,'configuredMcPhotonsSum':6960000000,'blocksPerGeometry':2,'records':rec,'cases':[{'seed':910001+i} for i in range(96)]}
class T(unittest.TestCase):
 def test_thresholds_and_cap(self):
  p=m.build(fixture(),{'classification':'BATCH_NUMERICALLY_COMPLETE','caseCountCompleted':96},{'status':'PASSED','caseResultCount':96},{'runAttempt':1,'artifactsComplete':True,'hashesValid':True,'seedsValid':True,'photonAccountingValid':True})
  self.assertEqual(p['points'][0]['sourceClassification'],'ADAPTIVE_CONTINUATION_REQUIRED');self.assertLessEqual(p['points'][0]['additionalBlockCount'],6);self.assertFalse(p['automaticDispatch']);self.assertFalse(m.authorization_template(p)['enabled'])
 def test_refuses_retry(self):
  with self.assertRaises(m.Refusal): m.build(fixture(),{'classification':'BATCH_NUMERICALLY_COMPLETE','caseCountCompleted':96},{'status':'PASSED','caseResultCount':96},{'runAttempt':2,'artifactsComplete':True,'hashesValid':True,'seedsValid':True,'photonAccountingValid':True})
 def test_fake_results(self):
  p=m.build(fixture(.2),{'classification':'BATCH_NUMERICALLY_COMPLETE','caseCountCompleted':96},{'status':'PASSED','caseResultCount':96},{'runAttempt':1,'artifactsComplete':True,'hashesValid':True,'seedsValid':True,'photonAccountingValid':True}); rs=[{'caseId':c['caseId'],'seed':c['seed'],'status':'COMPLETED','syntaxCheckCount':1,'solverExecutionCount':1,'value':1.0} for c in p['cases']];self.assertEqual(m.audit_results(p,rs)['status'],'PASSED')
if __name__=='__main__': unittest.main()
