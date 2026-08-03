#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, importlib.util, json, math, sys, zipfile
from pathlib import Path, PurePosixPath
HERE=Path(__file__).resolve().parent; RUNNER=HERE/'runner.py'; STAGE='reference-vroom-v1'
class AuditFailure(RuntimeError): pass
def module():
 s=importlib.util.spec_from_file_location('reference_vroom_runner',RUNNER); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
def unique(z,name):
 x=[p for p in z.namelist() if not p.endswith('/') and PurePosixPath(p).name==name]
 if len(x)!=1: raise AuditFailure(f'expected one {name}, found {len(x)}')
 return x[0]
def close(a,e,path='analysis'):
 if isinstance(e,dict):
  if not isinstance(a,dict) or set(a)!=set(e): raise AuditFailure(f'{path} keys differ')
  for k in e: close(a[k],e[k],f'{path}.{k}')
 elif isinstance(e,list):
  if not isinstance(a,list) or len(a)!=len(e): raise AuditFailure(f'{path} list differs')
  for i,(x,y) in enumerate(zip(a,e)): close(x,y,f'{path}[{i}]')
 elif isinstance(e,(int,float)) and not isinstance(e,bool):
  if not isinstance(a,(int,float)) or not math.isclose(float(a),float(e),rel_tol=1e-12,abs_tol=1e-15): raise AuditFailure(f'{path} differs')
 elif a!=e: raise AuditFailure(f'{path} differs')
def validate_cases(cases,r,all_required):
 expected=set(r.SEEDS); seen=set()
 if not isinstance(cases,list): raise AuditFailure('cases not list')
 for c in cases:
  seed=c.get('seed')
  if seed not in expected or seed in seen or c.get('method')!='reference-vroom' or c.get('photonHistories')!=r.PHOTONS: raise AuditFailure(f'invalid case {seed}')
  for key in ('selectedNodeRadiance','selectedNodeStdRadiance'):
   v=c.get(key)
   if not isinstance(v,list) or len(v)!=len(r.NODES) or any(not isinstance(x,(int,float)) or not math.isfinite(x) or x<0 for x in v): raise AuditFailure(f'invalid {key} {seed}')
  seen.add(seed)
 if all_required and seen!=expected: raise AuditFailure('not exact six cases')
def audit(zip_path,metadata_path,run_id,sha):
 meta=json.loads(Path(metadata_path).read_text()); run=meta['run']; art=meta['artifact']
 if run.get('id')!=run_id or run.get('head_sha')!=sha or run.get('status')!='completed' or run.get('run_attempt')!=1 or run.get('event')!='push' or run.get('head_branch')!='authorization/reference-vroom-v1': raise AuditFailure('run identity mismatch')
 digest=art.get('digest',''); actual=hashlib.sha256(Path(zip_path).read_bytes()).hexdigest()
 if digest!='sha256:'+actual: raise AuditFailure('artifact digest mismatch')
 with zipfile.ZipFile(zip_path) as z: ab=z.read(unique(z,'analysis-result.json')); mb=z.read(unique(z,'run-manifest.json'))
 result=json.loads(ab); manifest=json.loads(mb); r=module(); _,contract,frozen=r.validate_frozen()
 if result.get('stageId')!=STAGE or manifest.get('stageId')!=STAGE or manifest.get('authorizationCommit')!=sha or manifest.get('resultSha256')!=hashlib.sha256(ab).hexdigest(): raise AuditFailure('manifest mismatch')
 for k in ('solverExecutionCount','syntaxCheckCount','attemptedConfiguredMcPhotonsSum','completedConfiguredMcPhotonsSum','classification'):
  if result.get(k)!=manifest.get(k): raise AuditFailure(f'manifest differs {k}')
 classification=result.get('classification')
 if classification=='STRUCTURAL_OR_EXECUTION_FAILURE':
  if result.get('status')!='FAILED' or result.get('analysis') is not None or len(result.get('cases',[]))>=6: raise AuditFailure('bad structural result')
  validate_cases(result.get('cases'),r,False); scientific=False
 else:
  if result.get('status')!='COMPLETED' or result.get('solverExecutionCount')!=6 or result.get('syntaxCheckCount')!=6 or result.get('completedConfiguredMcPhotonsSum')!=960000000 or run.get('conclusion')!='success': raise AuditFailure('bad complete result')
  validate_cases(result.get('cases'),r,True); recomputed=r.analyze(result['cases'],frozen,contract); close(result.get('analysis'),recomputed)
  if recomputed['classification']!=classification: raise AuditFailure('classification differs')
  scientific=True
 return {'schemaVersion':1,'stageId':STAGE,'verified':True,'scientificClassificationAvailable':scientific,'classification':classification,'completeCaseCount':len(result.get('cases',[])),'solverExecutionCount':result.get('solverExecutionCount'),'syntaxCheckCount':result.get('syntaxCheckCount'),'workflowRun':run,'artifact':{'id':art.get('id'),'name':art.get('name'),'sizeInBytes':art.get('size_in_bytes'),'sha256':actual},'boundary':'read-only post-run audit; no dispatch, rerun, resume, or solver authorization'}
def selftest():
 r=module(); p=r.proposal(); assert p['resolvedInputAssertions']=={'containsMcVroomOn':True,'containsMcVroomOff':False,'containsSpectralImportanceSampling':False}; return {'status':'PASS','stageId':STAGE}
def main():
 p=argparse.ArgumentParser(); p.add_argument('--zip'); p.add_argument('--metadata'); p.add_argument('--expected-run-id',type=int); p.add_argument('--expected-head-sha'); p.add_argument('--output'); p.add_argument('--self-test',action='store_true'); a=p.parse_args()
 try:
  if a.self_test: print(json.dumps(selftest(),indent=2,sort_keys=True)); return 0
  s=audit(a.zip,a.metadata,a.expected_run_id,a.expected_head_sha); Path(a.output).write_text(json.dumps(s,indent=2,sort_keys=True)+'\n'); print(json.dumps(s,indent=2,sort_keys=True)); return 0
 except Exception as e: print(json.dumps({'verified':False,'error':str(e)},sort_keys=True),file=sys.stderr); return 2
if __name__=='__main__': raise SystemExit(main())
