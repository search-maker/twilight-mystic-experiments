#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,math,re
from pathlib import Path
RID='public-tier1-train-0014-fresh-training-acquisition-v1'; RSTATUS='REVIEW_ONLY_FROZEN_BEFORE_ANY_FRESH_TRAINING_RESULT'
DECISION_SHA='fa6178e9042226c5326306ee42f9fa7f3cdaca292552b36b3b8e151b2412cc0f'; READY_SHA='d43d876862c89aac078069d7f52d7f9be2cf41c36e8ba0e37c31c1fde5bfdc81'
SOURCE_TEMPLATE_SHA='333f0f75661867a2f8854fcf2b04181d60d1c15aa983d1d6226ddc4273db0475'; PHYS_SHA='37be7d517bcd129f017048b4684b71bce03270da5ed48f90ff4ad95aa790aa25'
SEEDS=list(range(1700000001,1700000005))
class Refusal(RuntimeError): pass
def req(c,m):
 if not c: raise Refusal(m)
def load(p): v=json.loads(Path(p).read_text()); req(isinstance(v,dict),f'object required: {p}'); return v
def canon(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def self_hash(v,f): c=dict(v); c[f]=None; return canon(c)
def sha_text(t): return hashlib.sha256(t.encode()).hexdigest()
def norm(t):
 out=[]
 for line in t.splitlines():
  if line.startswith('mc_randomseed '): line='mc_randomseed <SEED>'
  elif line.startswith('mc_basename '): line='mc_basename <BASENAME>'
  out.append(line)
 return '\n'.join(out)+'\n'
def collect_seeds(v):
 out=[]
 if isinstance(v,dict):
  for k,x in v.items():
   if k.lower()=='seed' and isinstance(x,int): out.append(x)
   else: out.extend(collect_seeds(x))
 elif isinstance(v,list):
  for x in v: out.extend(collect_seeds(x))
 return out
def validate(p,decision,ready,gate,seed_audit,conf_manifest,render,source_template,template_root):
 req(p.get('preregistrationId')==RID and p.get('status')==RSTATUS,'prereg identity/status drift'); req(p.get('preregistrationSha256')==self_hash(p,'preregistrationSha256'),'prereg self-hash mismatch')
 req(decision.get('decisionSha256')==DECISION_SHA and decision.get('decisionSha256')==self_hash(decision,'decisionSha256'),'decision binding drift')
 req(ready.get('readinessSha256')==READY_SHA and ready.get('readinessSha256')==self_hash(ready,'readinessSha256'),'readiness binding drift')
 req(gate.get('gateId')=='public-tier1-full-spectrum-training-admission-gate-v1' and gate.get('fittingAuthorized') is False,'training gate drift')
 by={r['geometryId']:r for r in gate['geometryReports']}; req(by['train-0014']['classification']=='FULL_CHANNEL_CONTINUATION_REQUIRED','train-0014 gate drift')
 cfg=p.get('configuration') or {}; req(cfg.get('geometryId')=='train-0014' and cfg.get('method')=='alis-alt-importance' and cfg.get('importanceCenterNm')==600.0,'configuration drift'); req(cfg.get('globalEstimatorUseAuthorized') is False,'global config drift')
 src=p.get('sourceBindings') or {}; req(src.get('confirmationDecisionSha256')==DECISION_SHA and src.get('trainingReadinessSha256')==READY_SHA,'source decision/readiness drift')
 req(src.get('sourceConfirmationTemplateSha256')==SOURCE_TEMPLATE_SHA and src.get('normalizedTemplatePhysicalFingerprintSha256')==PHYS_SHA,'template source binding drift')
 req(sha_text(source_template)==SOURCE_TEMPLATE_SHA and sha_text(norm(source_template))==PHYS_SHA,'source template bytes drift')
 cm={c['caseId']:c for c in conf_manifest['cases']}; sc=cm.get('train-0014-fs-confirm-alis-600-c1'); req(sc is not None,'source confirmation case missing'); req(sc['seed']==1600000009 and sc['photonHistories']==50000000 and sc['numericalMethod']['mc_spectral_is_nm']==600.0,'source confirmation case drift')
 rr={c['caseId']:c for c in render['cases']}['train-0014-fs-confirm-alis-600-c1']; req(rr['physicalFingerprint']=='5eab27f6bad59ba4acfd9bcb98e357794b21fbc4de116e0f3747a663bedffd0f','source physical fingerprint drift')
 design=p.get('caseDesign') or {}; req(design.get('caseCount')==4 and design.get('freshIndependentBlocksExactly')==4 and design.get('perBlockPhotonHistories')==50000000 and design.get('totalConfiguredPhotonHistories')==200000000,'case design drift'); req(design.get('seeds')==SEEDS and design.get('seedRange')==[SEEDS[0],SEEDS[-1]] and design.get('automaticAdditionalBlocks') is False,'seed/block drift')
 rows=design.get('cases'); req(isinstance(rows,list) and len(rows)==4,'case rows drift')
 for i,row in enumerate(rows,1):
  cid=f'train-0014-fs-acquire-alis-600-t{i}'; req(row.get('caseId')==cid and row.get('seed')==SEEDS[i-1] and row.get('trainingAcquisitionBlock')==i,'case identity drift')
  t=(Path(template_root)/cid/'input-template.txt').read_text(); req(sha_text(t)==row.get('templateSha256'),'template hash drift'); req(sha_text(norm(t))==PHYS_SHA and norm(t)==norm(source_template),'template physical drift')
  req(re.search(rf'^mc_randomseed {SEEDS[i-1]}$',t,re.M) is not None,'template seed drift'); req(f'mc_basename ${{OUTPUT_DIR}}/{cid}/mc' in t,'template basename drift')
 used=set(collect_seeds(seed_audit))|{c['seed'] for c in conf_manifest['cases']}; req(not (set(SEEDS)&used),'candidate seed collision')
 ev=p.get('trainingEvaluation') or {}; req(ev.get('historicalFinalTargetRsem')==0.05 and ev.get('historicalMaximumAcceptedRsem')==0.08 and ev.get('exactZeroPolicy')=='PRESERVE_EXACT_ZERO_NO_EPSILON','evaluation drift'); req(ev.get('confirmationValuesIncludedInTrainingStatistics') is False and ev.get('historicalTrainingValuesIncludedInNewFourBlockStatistics') is False and ev.get('automaticTrainingAdmissionAfterAnalysis') is False and ev.get('automaticExtensionBeyondFourBlocks') is False,'evidence/automatic boundary drift')
 b=p.get('executionBoundary') or {}
 for k in ('scientificExecutionAuthorized','authorizationOrdinalAllocated','dispatchAuthorized','githubRerunAllowed','retryAllowed','resumeAllowed','confirmationValuesAdmittedAsTrainingLabels','freshTrainingValuesOpened','modelFittingAuthorized','modelSelectionAuthorized','holdoutValidationOpeningAuthorized','tier2Authorized','productionPromotionAuthorized'): req(b.get(k) is False,'execution boundary drift: '+k)
def main():
 ap=argparse.ArgumentParser();
 for x in ('preregistration','decision','readiness','gate','seed-audit','confirmation-manifest','render-report','source-template','template-root'): ap.add_argument('--'+x,type=Path,required=True)
 ap.add_argument('--output',type=Path); a=ap.parse_args()
 try:
  p=load(a.preregistration); validate(p,load(a.decision),load(a.readiness),load(a.gate),load(a.seed_audit),load(a.confirmation_manifest),load(a.render_report),a.source_template.read_text(),a.template_root)
  out={'status':'PASS','preregistrationSha256':p['preregistrationSha256'],'caseCount':4,'scientificExecutionAuthorized':False,'ordinalAllocated':False}; rc=0
 except Exception as e: out={'status':'REFUSED','reason':str(e),'scientificExecutionAuthorized':False,'ordinalAllocated':False}; rc=2
 if a.output: a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
 print(json.dumps(out,sort_keys=True)); return rc
if __name__=='__main__': raise SystemExit(main())
