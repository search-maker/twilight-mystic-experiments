#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path
RID='public-tier1-train-0037-targeted-estimator-comparison-v1'
STATUS='REVIEW_ONLY_FROZEN_BEFORE_ANY_TRAIN_0037_COMPARISON_RESULT'
DECISION_SHA='fa6178e9042226c5326306ee42f9fa7f3cdaca292552b36b3b8e151b2412cc0f'
READY_SHA='d43d876862c89aac078069d7f52d7f9be2cf41c36e8ba0e37c31c1fde5bfdc81'
SCREEN_SHA='69d877c5c90e80dfd0956d73f1790d30129423ab58b6414ac24d776bc2c7120f'
SOURCE_500_SHA='fb0e35d999f1a3aacab14eadabeb1259a2b479a56370e7029791a52acf44c1fa'
SOURCE_600_SHA='9813f1ea69627d0f7ccf717c224edbcbe14b452e1010291188350aee119486ea'
PHYS_SHA='d6a7d988a8962598971840b136284bfc07937038590d5ecc72f224834d742feb'
SEEDS=list(range(1800000001,1800000013)); CENTERS=[500.0,550.0,600.0]
class Refusal(RuntimeError): pass
def req(c,m):
 if not c: raise Refusal(m)
def load(p):
 v=json.loads(Path(p).read_text()); req(isinstance(v,dict),f'object required: {p}'); return v
def canon(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def self_hash(v,f): c=dict(v); c[f]=None; return canon(c)
def shat(t): return hashlib.sha256(t.encode()).hexdigest()
def norm_all(t):
 out=[]
 for line in t.splitlines():
  if line.startswith('mc_randomseed '): line='mc_randomseed <SEED>'
  elif line.startswith('mc_basename '): line='mc_basename <BASENAME>'
  elif line.startswith('mc_spectral_is '): line='mc_spectral_is <CENTER>'
  out.append(line)
 return '\n'.join(out)+'\n'
def collect_seeds(v):
 out=[]
 if isinstance(v,dict):
  for k,x in v.items():
   if k=='seed' and isinstance(x,int): out.append(x)
   else: out.extend(collect_seeds(x))
 elif isinstance(v,list):
  for x in v: out.extend(collect_seeds(x))
 return out
def validate(p,decision,ready,gate,screen,seed_audit,s500,s600,template_root):
 req(p.get('preregistrationId')==RID and p.get('status')==STATUS,'prereg identity/status drift')
 req(p.get('preregistrationSha256')==self_hash(p,'preregistrationSha256'),'prereg self-hash mismatch')
 req(decision.get('decisionSha256')==DECISION_SHA and decision.get('decisionSha256')==self_hash(decision,'decisionSha256'),'decision binding drift')
 req(ready.get('readinessSha256')==READY_SHA and ready.get('readinessSha256')==self_hash(ready,'readinessSha256'),'readiness binding drift')
 req(gate.get('gateId')=='public-tier1-full-spectrum-training-admission-gate-v1' and gate.get('fittingAuthorized') is False,'gate identity/boundary drift')
 req(gate.get('continuationRequiredGeometryIds')==['train-0014','train-0037'],'continuation universe drift')
 gr=[x for x in gate.get('geometryReports',[]) if x.get('geometryId')=='train-0037']; req(len(gr)==1,'train-0037 gate report missing/duplicate')
 req(gr[0].get('classification')=='FULL_CHANNEL_CONTINUATION_REQUIRED' and gr[0].get('scientificallyEligibleForTraining') is False,'train-0037 gate classification drift')
 sc=gr[0].get('channels',{}).get('scotopicLuminanceScotCdM2',{}); req(sc.get('relativeStandardErrorOfMean')==0.15128486473118663,'historical train-0037 RSEM drift')
 req(screen.get('analysisSha256')==SCREEN_SHA and screen.get('sourceScientificRunId')==31546667072 and screen.get('sourceScientificRunAttempt')==1,'screening identity drift')
 r=screen.get('geometryReport',{}); req(r.get('geometryId')=='train-0037' and r.get('historicalImportanceCenterNm')==550.0 and r.get('phenotype')=='scotopic-only-underprecision','screening geometry drift')
 mr=r.get('methodReports',[]); req([x.get('importanceCenterNm') for x in mr]==[500.0,600.0] and all(x.get('classification')=='NO_CLEAR_SCREENING_GAIN' for x in mr),'alternate screening classification drift')
 req(screen.get('modelFittingAuthorized') is False and screen.get('modelSelectionAuthorized') is False and screen.get('holdoutOpeningAuthorized') is False,'screening downstream boundary drift')
 req(shat(s500)==SOURCE_500_SHA and shat(s600)==SOURCE_600_SHA,'source template hash drift')
 req(norm_all(s500)==norm_all(s600) and shat(norm_all(s500))==PHYS_SHA,'source physical identity drift')
 sb=p.get('sourceBindings',{}); req(sb.get('ordinal16ScreeningAnalysisSha256')==SCREEN_SHA and sb.get('normalizedPhysicalTemplateFingerprintSha256')==PHYS_SHA,'source binding drift')
 d=p.get('comparisonDesign',{}); req(d.get('caseCount')==12 and d.get('importanceCentersNm')==CENTERS and d.get('freshIndependentBlocksPerCenterExactly')==4,'comparison design drift')
 req(d.get('perBlockPhotonHistories')==100000000 and d.get('totalConfiguredPhotonHistories')==1200000000,'photon budget drift')
 req(d.get('seeds')==SEEDS and d.get('seedRange')==[SEEDS[0],SEEDS[-1]] and d.get('seedReuseAllowed') is False and d.get('automaticAdditionalBlocks') is False,'seed/block boundary drift')
 cases=d.get('cases',[]); req(len(cases)==12 and len({x.get('caseId') for x in cases})==12 and len({x.get('seed') for x in cases})==12,'case universe drift')
 expected=[]
 for c in CENTERS:
  expected.extend([(c,b) for b in (1,2,3,4)])
 req([(x.get('importanceCenterNm'),x.get('comparisonBlock')) for x in cases]==expected,'center/block ordering drift')
 for row in cases:
  cid=row['caseId']; t=(Path(template_root)/cid/'input-template.txt').read_text()
  req(shat(t)==row.get('templateSha256'),'template hash drift: '+cid)
  req(shat(norm_all(t))==PHYS_SHA and row.get('templatePhysicalFingerprintSha256')==PHYS_SHA,'template physical drift: '+cid)
  req(f"mc_randomseed {row['seed']}" in t and f"mc_spectral_is {row['importanceCenterNm']:.1f}" in t and f"${{OUTPUT_DIR}}/{cid}/mc" in t,'template identity drift: '+cid)
  req('mc_photons 100000000' in t and 'mc_vroom off' in t,'template numerical contract drift: '+cid)
 audit_seeds=set(collect_seeds(seed_audit)); req(not (set(SEEDS)&audit_seeds),'candidate seed collision in supplied audit')
 ev=p.get('comparisonEvaluation',{}); req(ev.get('historicalFinalTargetRsem')==0.05 and ev.get('historicalMaximumAcceptedRsem')==0.08,'RSEM threshold drift')
 req(ev.get('historicalMeanRatioClosedInterval')==[0.5,2.0] and ev.get('pairwiseCenterMeanRatioClosedInterval')==[0.5,2.0],'mean-ratio screen drift')
 for k in ('automaticCenterSelection','automaticTrainingAdmission','comparisonValuesAdmittedAsTrainingLabels','historicalValuesIncludedInFreshStatistics','ordinal16ScreeningValuesIncludedInFreshStatistics','independentVroomReferenceIncluded','biasOrEquivalenceClaimAuthorized'):
  req(ev.get(k) is False,'comparison boundary drift: '+k)
 req(ev.get('separatePostComparisonDecisionRequired') is True and ev.get('separateFreshTrainingAcquisitionRequiredAfterAnyLaterNomination') is True,'post-comparison lifecycle drift')
 b=p.get('executionBoundary',{})
 for k in ('scientificExecutionAuthorized','authorizationOrdinalAllocated','dispatchAuthorized','githubRerunAllowed','retryAllowed','resumeAllowed','comparisonValuesOpened','comparisonValuesAdmittedAsTrainingLabels','modelFittingAuthorized','modelSelectionAuthorized','holdoutValidationOpeningAuthorized','tier2Authorized','productionPromotionAuthorized'):
  req(b.get(k) is False,'execution boundary drift: '+k)
def main():
 ap=argparse.ArgumentParser()
 for x in ('preregistration','decision','readiness','gate','screening','seed-audit','source-500','source-600','template-root'): ap.add_argument('--'+x,type=Path,required=True)
 ap.add_argument('--output',type=Path); a=ap.parse_args()
 try:
  p=load(a.preregistration); validate(p,load(a.decision),load(a.readiness),load(a.gate),load(a.screening),load(a.seed_audit),a.source_500.read_text(),a.source_600.read_text(),a.template_root)
  out={'status':'PASS','preregistrationSha256':p['preregistrationSha256'],'caseCount':12,'scientificExecutionAuthorized':False,'ordinalAllocated':False,'automaticCenterSelection':False}; rc=0
 except Exception as e:
  out={'status':'REFUSED','reason':str(e),'scientificExecutionAuthorized':False,'ordinalAllocated':False,'automaticCenterSelection':False}; rc=2
 if a.output: a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
 print(json.dumps(out,sort_keys=True)); return rc
if __name__=='__main__': raise SystemExit(main())
