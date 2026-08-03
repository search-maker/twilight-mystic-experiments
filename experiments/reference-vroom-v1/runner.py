#!/usr/bin/env python3
from __future__ import annotations
import argparse, base64, hashlib, importlib.util, json, math, os, random, statistics, subprocess, sys, time, zlib
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]; HERE=Path(__file__).resolve().parent
PREREG=HERE/'preregistration.json'; CONTRACT=HERE/'contract.json'; COMPARATORS=HERE/'frozen-comparators.zlib.b64'; GRID=HERE/'wavelength-grid.dat'
AUTH=HERE/'authorization.json'; AUTH_TEMPLATE=HERE/'authorization-template.json'; AUDIT=HERE/'audit.py'; EXECUTION=ROOT/'.github/workflows/reference-vroom-execution.yml'
STAGE='reference-vroom-v1'; BRANCH='authorization/reference-vroom-v1'; NODES=[470,480,490,500,510,520,530,540,560,580,590,600,610,640,660]
CIE=[.09098,.13902,.20802,.323,.503,.71,.862,.954,.995,.87,.757,.631,.503,.175,.061]; SEEDS=list(range(77301,77307)); PHOTONS=160_000_000
MAX_SOLVER=6; MAX_SYNTAX=6; MAX_PHOTONS=960_000_000; MAX_MINUTES=90; CASE_TIMEOUT=1200; MAX_BYTES=512*1024*1024

class Refusal(RuntimeError):
 def __init__(self,code,reason,detail=None): super().__init__(reason); self.code=code; self.reason=reason; self.detail=detail
 def as_dict(self): return {'status':'REFUSED','classification':'STRUCTURAL_OR_EXECUTION_FAILURE','code':self.code,'reason':self.reason,'detail':self.detail}
def load(path):
 v=json.loads(path.read_text());
 if not isinstance(v,dict): raise Refusal('json-object',f'{path} is not an object')
 return v
def comparators(): return json.loads(zlib.decompress(base64.b64decode(COMPARATORS.read_bytes())))
def dump(v): return json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+'\n'
def raw(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def payload(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def git(*args): return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()
def cases(): return [{'ordinal':i+1,'caseId':f'reference-vroom-{s}','method':'reference-vroom','seed':s,'photonHistories':PHOTONS} for i,s in enumerate(SEEDS)]

def validate_frozen():
 p=load(PREREG); c=load(CONTRACT); f=comparators(); a=load(AUTH); t=load(AUTH_TEMPLATE)
 d=p.get('design',{}); source=p.get('frozenSourceEvidence')
 if p.get('stageId')!=STAGE or d.get('seeds')!=SEEDS or d.get('caseCount')!=6 or d.get('mcPhotonsPerCase')!=PHOTONS or d.get('maximumConfiguredMcPhotonsSum')!=MAX_PHOTONS or d.get('vroom')!='on' or d.get('method')!='conventional-reference-only': raise Refusal('prereg','preregistration changed')
 if d.get('diagnosticNodesNm')!=NODES or d.get('wavelengthDomainNm')!=[380,780]: raise Refusal('prereg-domain','domain or nodes changed')
 if source!={'workflowRunId':30777018904,'artifactId':8843259287,'artifactSha256':'462b000f3e7fedebf400c016e9484ff04b64224cd35dcba31f2079a3cd7527d3','classification':'INCONCLUSIVE'}: raise Refusal('source','source evidence changed')
 if c.get('stageId')!=STAGE or c.get('classificationOrder')!=p['analysisPlan']['decisionOrder']: raise Refusal('contract','contract changed')
 if f.get('stageId')!=STAGE or f.get('source',{}).get('artifactSha256')!=source['artifactSha256'] or len(f.get('alisCases',[]))!=6 or len(f.get('referenceVroomOffCases',[]))!=6: raise Refusal('comparators','frozen comparators changed')
 grid=[int(x) for x in GRID.read_text().split()]
 if grid[0]!=380 or grid[-1]!=780 or not set(NODES)<=set(grid): raise Refusal('grid','grid changed')
 if a!=t and not a.get('authorized'): raise Refusal('authorization-template','disabled authorization differs from template')
 return p,c,f

def hashes():
 return {'exactRunnerSha256':raw(Path(__file__)),'exactAuditSha256':raw(AUDIT),'exactPreregistrationRawSha256':raw(PREREG),'exactCaseSetPayloadSha256':payload(cases()),'exactAnalysisContractRawSha256':raw(CONTRACT),'exactFrozenComparatorsRawSha256':raw(COMPARATORS),'exactWavelengthGridRawSha256':raw(GRID),'exactAuthorizationTemplateRawSha256':raw(AUTH_TEMPLATE),'exactExecutionWorkflowSha256':raw(EXECUTION),'maximumSolverExecutionCount':MAX_SOLVER,'maximumSyntaxCheckCount':MAX_SYNTAX,'maximumConfiguredMcPhotonsSum':MAX_PHOTONS,'maximumAuthorizedRunnerMinutes':MAX_MINUTES,'perCaseTimeoutSeconds':CASE_TIMEOUT,'purpose':STAGE}
AUTH_FIELDS=('exactAuthorizationParentCommit',*hashes().keys())
def verify_auth():
 a=load(AUTH)
 if a.get('stageId')!=STAGE or not all(a.get(k) is True for k in ('authorized','runMystic','runUvspec','scientificDiagnostic','successDoesNotAuthorizeProduction')): raise Refusal('authorization','not authorized')
 if os.getenv('GITHUB_ACTIONS')!='true' or os.getenv('GITHUB_EVENT_NAME')!='push' or os.getenv('GITHUB_RUN_ATTEMPT')!='1' or os.getenv('GITHUB_REF_NAME')!=BRANCH: raise Refusal('github-context','not exact first push context')
 parent=git('rev-parse','HEAD^')
 if a.get('exactAuthorizationParentCommit')!=parent or git('diff','--name-only',parent,'HEAD').splitlines()!=['experiments/reference-vroom-v1/authorization.json']: raise Refusal('authorization-purpose','authorization commit is not one-purpose')
 fresh=hashes(); bad={k:(a.get(k),v) for k,v in fresh.items() if a.get(k)!=v}
 if bad: raise Refusal('authorization-hash','stale authorization',bad)
 return a

def parse_spectrum(path):
 found={}
 for line in path.read_text(errors='replace').splitlines():
  parts=line.split()
  if len(parts)<2: continue
  try: w=float(parts[0]); v=float(parts[-1])
  except ValueError: continue
  for n in NODES:
   if abs(w-n)<=1e-7: found[n]=v
 if sorted(found)!=NODES or any(not math.isfinite(found[n]) or found[n]<0 for n in NODES): raise Refusal('spectrum',f'invalid selected spectrum {path}')
 return [found[n] for n in NODES]
def luminance(vals): return 683.002*10*sum((v/1000)*w for v,w in zip(vals,CIE))
def node_means(records,key='selectedNodeRadiance'): return [statistics.fmean(r[key][i] for r in records) for i in range(len(NODES))]
def boot(num,den,seed,resamples,confidence):
 rng=random.Random(seed); x=[]
 for _ in range(resamples): x.append(statistics.fmean(rng.choice(num) for _ in num)/statistics.fmean(rng.choice(den) for _ in den))
 x.sort(); a=(1-confidence)/2; return [x[math.floor(a*len(x))],x[math.ceil((1-a)*len(x))-1]]
def weighted(values,weights,threshold):
 total=sum(weights); return sum(v*w for v,w in zip(values,weights))/total,sum(w for v,w in zip(values,weights) if v<=threshold)/total
def compare(num_records,den_records,contract,seed):
 num=[r['selectedPhotopicContributionCdM2'] for r in num_records]; den=[r['selectedPhotopicContributionCdM2'] for r in den_records]
 nm=node_means(num_records); dm=node_means(den_records); ratios=[a/b if b else math.inf for a,b in zip(nm,dm)]; weights=[b*w for b,w in zip(dm,CIE)]; interval=contract['crossMethodAgreement']['integratedMeanRatioAlisToVroomReferenceClosedInterval']
 return {'meanRatio':statistics.fmean(num)/statistics.fmean(den),'bootstrapRatioCi90':boot(num,den,seed,contract['bootstrap']['resamples'],contract['bootstrap']['confidenceLevel']),'denominatorPhotopicWeightFractionNodeRatioWithinFactorTwo':sum(w for r,w in zip(ratios,weights) if interval[0]<=r<=interval[1])/sum(weights),'nodeMeanRatios':ratios}
def analyze(records,f,c):
 lum=[r['selectedPhotopicContributionCdM2'] for r in records]; mean=statistics.fmean(lum); cv=statistics.stdev(lum)/mean; means=node_means(records); weights=[m*w for m,w in zip(means,CIE)]
 empirical=[]; reported=[]
 for i in range(len(NODES)):
  vals=[r['selectedNodeRadiance'][i] for r in records]; empirical.append(statistics.stdev(vals)/statistics.fmean(vals)); reported.append(statistics.fmean(r['selectedNodeStdRadiance'][i]/r['selectedNodeRadiance'][i] for r in records))
 g=c['internalStability']; we,fe=weighted(empirical,weights,g['empiricalNodeCvThreshold']); wr,fr=weighted(reported,weights,g['reportedRelativeStdThreshold'])
 gates={'integratedCv':cv<=g['maximumIntegratedCoefficientOfVariation'],'photopicWeightedEmpiricalNodeCv':we<=g['maximumPhotopicWeightedEmpiricalNodeCv'],'empiricalNodeCvWeightFraction':fe>=g['minimumPhotopicWeightFractionEmpiricalNodeCvAtMostThreshold'],'photopicWeightedReportedRelativeStd':wr<=g['maximumPhotopicWeightedReportedRelativeStd'],'reportedRelativeStdWeightFraction':fr>=g['minimumPhotopicWeightFractionReportedRelativeStdAtMostThreshold']}; stable=all(gates.values())
 alis=compare(f['alisCases'],records,c,c['bootstrap']['seed']); interval=c['crossMethodAgreement']['integratedMeanRatioAlisToVroomReferenceClosedInterval']; cg=c['crossMethodAgreement']; agree_g={'integratedRatio':interval[0]<=alis['meanRatio']<=interval[1],'bootstrapIntervalContained':interval[0]<=alis['bootstrapRatioCi90'][0] and alis['bootstrapRatioCi90'][1]<=interval[1],'photopicWeightFraction':alis['denominatorPhotopicWeightFractionNodeRatioWithinFactorTwo']>=cg['minimumVroomReferencePhotopicWeightFractionWithNodeRatioInsideInterval']}; agrees=all(agree_g.values())
 classification='VROOM_REFERENCE_STABLE_AND_AGREES_WITH_ALIS' if stable and agrees else ('PERSISTENT_METHOD_DISCREPANCY' if stable else 'VROOM_REFERENCE_STILL_UNDERCONVERGED')
 return {'classification':classification,'vroomInternalStability':{'integratedPhotopic':{'values':lum,'mean':mean,'sampleStd':statistics.stdev(lum),'coefficientOfVariation':cv},'nodeMeanRadiance':means,'empiricalNodeCv':empirical,'photopicWeightedEmpiricalNodeCv':we,'photopicWeightFractionEmpiricalNodeCvAtMostThreshold':fe,'reportedRelativeStdByNode':reported,'photopicWeightedReportedRelativeStd':wr,'photopicWeightFractionReportedRelativeStdAtMostThreshold':fr,'gateResults':gates,'passed':stable},'alisVsVroomReference':{**alis,'gateResults':agree_g,'agreementPassed':agrees},'vroomReferenceVsFrozenVroomOffReference':compare(records,f['referenceVroomOffCases'],c,c['bootstrap']['seed']+1)}
def render(case,data,atmosphere,case_dir):
 return '\n'.join([f'data_files_path {data}',f'atmosphere_file {atmosphere}',f"source solar {data/'solar_flux/atlas_plus_modtran'}",'mol_abs_param crs',f'wavelength_grid_file {GRID}','wavelength 380 780','sza 102.000000','phi0 0.00','rte_solver mystic','mc_spherical 1D',f"mc_photons {case['photonHistories']}",'mc_vroom on','mc_std',f"mc_randomseed {case['seed']}",f"mc_basename {case_dir/'mc'}",'albedo 0.15','aerosol_default','aerosol_set_tau_at_wvl 550 0.150000','zout 0','umu -0.17364818','phi 120.00','quiet'])+'\n'
def process(cmd,text,cwd,timeout):
 start=time.monotonic()
 try:
  p=subprocess.run(cmd,input=text,text=True,capture_output=True,cwd=cwd,timeout=timeout); return {'exitCode':p.returncode,'timedOut':False,'elapsedSeconds':time.monotonic()-start,'stdout':p.stdout,'stderr':p.stderr}
 except subprocess.TimeoutExpired as e: return {'exitCode':None,'timedOut':True,'elapsedSeconds':time.monotonic()-start,'stdout':e.stdout or '','stderr':e.stderr or ''}
def execute(args):
 _,c,f=validate_frozen(); a=verify_auth()
 if not args.allow_execution: raise Refusal('execution-flag','--allow-execution required')
 out=Path(args.output_dir).resolve(); out.mkdir(); u=Path(args.uvspec).resolve(); data=Path(args.data_dir).resolve(); atm=Path(args.atmosphere).resolve(); records=[]; syntax=solver=attempted=0; failure=None; start=time.monotonic()
 for case in cases():
  try:
   if time.monotonic()-start>MAX_MINUTES*60: raise Refusal('runner-time','runner time ceiling exceeded')
   d=out/case['caseId']; d.mkdir(); text=render(case,data,atm,d); (d/'input-resolved.txt').write_text(text)
   syntax+=1; s=process([str(u),'-c'],text,d,60)
   for k in ('stdout','stderr'): (d/f'syntax-{k}.txt').write_text(str(s[k]))
   if s['timedOut'] or s['exitCode']!=0: raise Refusal('syntax-failure','syntax failed',s)
   solver+=1; attempted+=case['photonHistories']; r=process([str(u)],text,d,CASE_TIMEOUT)
   for k in ('stdout','stderr'): (d/f'solver-{k}.txt').write_text(str(r[k]))
   if r['timedOut'] or r['exitCode']!=0: raise Refusal('solver-failure','solver failed',r)
   sp=d/'mc.rad.spc'; sd=d/'mc.rad.std.spc'; vals=parse_spectrum(sp); std=parse_spectrum(sd); records.append({**case,'selectedNodeRadiance':vals,'selectedNodeStdRadiance':std,'selectedPhotopicContributionCdM2':luminance(vals),'elapsedSeconds':r['elapsedSeconds'],'outputSha256':raw(sp),'stdOutputSha256':raw(sd)})
  except Refusal as e: failure={**e.as_dict(),'caseId':case['caseId']}; break
 complete=sum(x['photonHistories'] for x in records)
 if failure is None and len(records)==6: analysis=analyze(records,f,c); status='COMPLETED'; classification=analysis['classification']; ok=True
 else: analysis=None; status='FAILED'; classification='STRUCTURAL_OR_EXECUTION_FAILURE'; ok=False; failure=failure or Refusal('incomplete','six cases not complete').as_dict()
 result={'schemaVersion':1,'stageId':STAGE,'status':status,'classification':classification,'successDoesNotAuthorizeProduction':True,'solverExecutionCount':solver,'syntaxCheckCount':syntax,'attemptedConfiguredMcPhotonsSum':attempted,'completedConfiguredMcPhotonsSum':complete,'structuralFailure':failure,'preregistrationRawSha256':raw(PREREG),'contractRawSha256':raw(CONTRACT),'frozenComparatorsRawSha256':raw(COMPARATORS),'authorizationConsumed':True,'cases':records,'analysis':analysis}; ap=out/'analysis-result.json'; ap.write_text(dump(result)); manifest={'schemaVersion':1,'stageId':STAGE,'authorizationCommit':git('rev-parse','HEAD'),'authorizationParentCommit':a['exactAuthorizationParentCommit'],'solverExecutionCount':solver,'syntaxCheckCount':syntax,'attemptedConfiguredMcPhotonsSum':attempted,'completedConfiguredMcPhotonsSum':complete,'classification':classification,'resultSha256':raw(ap)}; (out/'run-manifest.json').write_text(dump(manifest))
 if sum(p.stat().st_size for p in out.rglob('*') if p.is_file())>MAX_BYTES: raise Refusal('artifact-size','artifact too large')
 return result,ok
def proposal():
 p,c,f=validate_frozen(); sample=render(cases()[0],Path('/data'),Path('/atmosphere'),Path('/case')); return {'stageId':STAGE,'authorizationRequired':True,'executionAuthorizedByProposal':False,'requiredAuthorizationBranch':BRANCH,'cases':cases(),'expectedHashes':hashes(),'classificationOrder':c['classificationOrder'],'frozenComparatorSource':f['source'],'resolvedInputAssertions':{'containsMcVroomOn':'mc_vroom on' in sample,'containsMcVroomOff':'mc_vroom off' in sample,'containsSpectralImportanceSampling':'mc_spectral_is' in sample}}
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--print-proposal',action='store_true'); ap.add_argument('--verify-only',action='store_true'); ap.add_argument('--allow-execution',action='store_true'); ap.add_argument('--output-dir'); ap.add_argument('--uvspec'); ap.add_argument('--data-dir'); ap.add_argument('--atmosphere'); a=ap.parse_args()
 try:
  if a.print_proposal: print(dump(proposal()),end=''); return 0
  if a.verify_only: validate_frozen(); verify_auth(); print(dump({'status':'AUTHORIZED','purpose':STAGE}),end=''); return 0
  if not all((a.output_dir,a.uvspec,a.data_dir,a.atmosphere)): raise Refusal('arguments','runtime arguments missing')
  r,ok=execute(a); print(dump({'status':r['status'],'classification':r['classification']}),end=''); return 0 if ok else 2
 except Exception as e:
  r=e if isinstance(e,Refusal) else Refusal('unhandled',str(e)); print(dump(r.as_dict()),end='',file=sys.stderr); return 2
if __name__=='__main__': raise SystemExit(main())
