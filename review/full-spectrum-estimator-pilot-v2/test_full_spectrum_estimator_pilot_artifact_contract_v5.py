from __future__ import annotations
import importlib.util,json,tempfile,unittest,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('norm',ROOT/'normalize_full_spectrum_estimator_pilot_results_v6.py'); assert s and s.loader; norm=importlib.util.module_from_spec(s); s.loader.exec_module(norm)
M=json.loads((ROOT/'full-spectrum-estimator-pilot-execution-manifest-v4.json').read_text()); CASES={c['caseId']:c for c in M['cases']}
def spectrum(step):
 n=int(round(400/step))+1; return ''.join(f'{380+i*step:.2f} 1.0e-6\n' for i in range(n)).encode()
def members(c):
 cid=c['caseId']; inp=(ROOT/'rendered-review-v5'/cid/'input-resolved-review.txt').read_bytes(); d={x:b'x\n' for x in M['artifactContract']['requiredMembersByMethod'][c['method']]}; d.update({'input-resolved.txt':inp,'runtime-report.json':(json.dumps(norm.RUNTIME,sort_keys=True,separators=(',',':'))+'\n').encode(),'randomseed':f"{c['seed']}\n".encode(),'syntax-stdout.txt':b'','syntax-stderr.txt':b'','solver-stdout.txt':b'','solver-stderr.txt':b''}); step=1.0 if c['method']=='reference-vroom-1nm' else .05; d['mc.rad.spc']=spectrum(step); d['mc.rad.std.spc']=spectrum(step)
 if c['method']=='reference-vroom-1nm': d['wavelength-grid-1nm.dat']=(ROOT/'wavelength-grid-1nm.dat').read_bytes()
 p={'schemaVersion':1,'stageId':'full-spectrum-estimator-pilot-v2-prepared','caseId':cid,'geometryId':c['geometryId'],'method':c['method'],'replicate':c['replicate'],'seed':c['seed'],'photonHistories':c['photonHistories'],'inputResolvedSha256':norm.raw_sha(inp),'executionManifestSha256':norm.EXEC_SHA}; d['prepared.json']=(json.dumps(p,sort_keys=True,separators=(',',':'))+'\n').encode(); rm={k:norm.raw_sha(v) for k,v in d.items() if k!='case-result.json'}; r={'schemaVersion':1,'stageId':'full-spectrum-estimator-pilot-v2','status':'COMPLETED','caseId':cid,'workflowRunAttempt':1,'syntaxCheckCount':1,'solverExecutionCount':1,'retryPerformed':False,'resumePerformed':False,'githubRerun':False,'syntaxExitCode':0,'solverExitCode':0,'syntaxTimedOut':False,'solverTimedOut':False,'seed':c['seed'],'photonHistories':c['photonHistories'],'inputResolvedSha256':norm.raw_sha(inp),'runtimeReportRawSha256':norm.raw_sha(d['runtime-report.json']),'radianceOutputSha256':norm.raw_sha(d['mc.rad.spc']),'stdRadianceOutputSha256':norm.raw_sha(d['mc.rad.std.spc']),'rawMemberSha256ByBasename':rm}; r['contentSha256']=norm.canon(r); d['case-result.json']=(json.dumps(r,sort_keys=True,separators=(',',':'))+'\n').encode(); return d
def write(p,cid,d):
 with zipfile.ZipFile(p,'w',compression=zipfile.ZIP_DEFLATED) as z:
  for k,v in d.items(): z.writestr(f'case-output/{cid}/{k}',v)
class T(unittest.TestCase):
 def parse(self,cid,mut=None):
  c=CASES[cid]; d=members(c); mut and mut(d,c)
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'c.zip'; write(p,cid,d); return norm.parse_case_zip(p,c,M['artifactContract']['requiredMembersByMethod'][c['method']])
 def test_valid_alis_and_vroom(self): self.assertEqual(self.parse('train-0009-fs-alis-500-r1')['caseId'],'train-0009-fs-alis-500-r1'); self.assertEqual(self.parse('train-0009-fs-vroom-1nm-r1')['method'],'reference-vroom-1nm')
 def test_extra_and_missing_members_refused(self):
  with self.assertRaisesRegex(ValueError,'exact artifact member set mismatch'): self.parse('train-0009-fs-alis-500-r1',lambda d,c:d.__setitem__('unexpected.txt',b'x'))
  with self.assertRaisesRegex(ValueError,'exact artifact member set mismatch'): self.parse('train-0009-fs-alis-500-r1',lambda d,c:d.__delitem__('mc0.rad.std'))
 def test_randomseed_mismatch_refused(self):
  def m(d,c):
   d['randomseed']=b'123\n'; r=json.loads(d['case-result.json']); r['rawMemberSha256ByBasename']['randomseed']=norm.raw_sha(d['randomseed']); r['contentSha256']=norm.canon({k:v for k,v in r.items() if k!='contentSha256'}); d['case-result.json']=(json.dumps(r,sort_keys=True,separators=(',',':'))+'\n').encode()
  with self.assertRaisesRegex(ValueError,'randomseed file does not equal manifest seed'): self.parse('train-0009-fs-alis-500-r1',m)
 def test_prepared_mismatch_refused(self):
  def m(d,c):
   p=json.loads(d['prepared.json']); p['caseId']='wrong'; d['prepared.json']=(json.dumps(p,sort_keys=True,separators=(',',':'))+'\n').encode(); r=json.loads(d['case-result.json']); r['rawMemberSha256ByBasename']['prepared.json']=norm.raw_sha(d['prepared.json']); r['contentSha256']=norm.canon({k:v for k,v in r.items() if k!='contentSha256'}); d['case-result.json']=(json.dumps(r,sort_keys=True,separators=(',',':'))+'\n').encode()
  with self.assertRaisesRegex(ValueError,'prepared-record binding mismatch'): self.parse('train-0009-fs-alis-500-r1',m)
 def test_grid_tamper_refused(self):
  def m(d,c):
   d['wavelength-grid-1nm.dat']+=b'#x\n'; r=json.loads(d['case-result.json']); r['rawMemberSha256ByBasename']['wavelength-grid-1nm.dat']=norm.raw_sha(d['wavelength-grid-1nm.dat']); r['contentSha256']=norm.canon({k:v for k,v in r.items() if k!='contentSha256'}); d['case-result.json']=(json.dumps(r,sort_keys=True,separators=(',',':'))+'\n').encode()
  with self.assertRaisesRegex(ValueError,'VROOM grid bytes drift'): self.parse('train-0009-fs-vroom-1nm-r1',m)
if __name__=='__main__': unittest.main()
