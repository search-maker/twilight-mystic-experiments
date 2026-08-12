#!/usr/bin/env python3
from __future__ import annotations
import argparse,copy,hashlib,json
from pathlib import Path
PID='public-tier1-full-spectrum-precision-exhausted-treatment-v1'; STATUS='REVIEW_ONLY_EXPLICIT_TREATMENTS_FROZEN_NO_FITTING'; PROTOCOL_SHA='5eacb2f5f25cb478bacef5261d51fcb1db9e1cf31be22ef2545a103763edfa54'
ORDER=['train-0003','train-0007','train-0011','train-0013','train-0019','train-0023','train-0027','train-0029','train-0031','train-0039','train-0041','train-0043','train-0047']
EXPECTED={'train-0003':'FINITE_UNDERPRECISION_CONTINUED_REFUSAL','train-0007':'FINITE_UNDERPRECISION_CONTINUED_REFUSAL','train-0011':'FINITE_UNDERPRECISION_CONTINUED_REFUSAL','train-0013':'FAILED_CONFIRMATION_CONTINUED_REFUSAL','train-0019':'FINITE_UNDERPRECISION_CONTINUED_REFUSAL','train-0023':'GROSS_METHOD_DISAGREEMENT_CONTINUED_REFUSAL','train-0027':'FINITE_UNDERPRECISION_CONTINUED_REFUSAL','train-0029':'FINITE_UNDERPRECISION_CONTINUED_REFUSAL','train-0031':'GROSS_METHOD_DISAGREEMENT_CONTINUED_REFUSAL','train-0039':'RARE_EVENT_EXACT_ZERO_CONTINUED_REFUSAL','train-0041':'FAILED_CONFIRMATION_CONTINUED_REFUSAL','train-0043':'FINITE_UNDERPRECISION_CONTINUED_REFUSAL','train-0047':'RARE_EVENT_EXACT_ZERO_CONTINUED_REFUSAL'}
class Refusal(RuntimeError): pass
def req(c,m):
 if not c: raise Refusal(m)
def load(p): v=json.loads(Path(p).read_text()); req(isinstance(v,dict),f'object required: {p}'); return v
def canon(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def self_hash(v,f): c=copy.deepcopy(v); c[f]=None; return canon(c)
def validate(p,decision,ready,gate,screen,confirm):
 req(p.get('protocolId')==PID and p.get('status')==STATUS,'protocol identity/status drift')
 req(p.get('protocolSha256')==PROTOCOL_SHA,'protocol SHA binding drift')
 req(p.get('protocolSha256')==self_hash(p,'protocolSha256'),'protocol self-hash mismatch')
 req(decision.get('decisionSha256')=='fa6178e9042226c5326306ee42f9fa7f3cdaca292552b36b3b8e151b2412cc0f' and decision.get('decisionSha256')==self_hash(decision,'decisionSha256'),'decision binding drift')
 req(ready.get('readinessSha256')=='d43d876862c89aac078069d7f52d7f9be2cf41c36e8ba0e37c31c1fde5bfdc81' and ready.get('readinessSha256')==self_hash(ready,'readinessSha256'),'readiness binding drift')
 req(gate.get('precisionExhaustedGeometryIds')==ORDER,'gate precision-exhausted universe drift')
 req(gate.get('fittingAuthorized') is False and gate.get('allTrainingGeometriesScientificallyEligible') is False,'gate boundary drift')
 reports={x.get('geometryId'):x for x in gate.get('geometryReports',[])}; req(set(ORDER)<=set(reports),'gate reports missing exhausted geometry')
 for gid in ORDER: req(reports[gid].get('classification')=='FULL_CHANNEL_PRECISION_EXHAUSTED' and reports[gid].get('scientificallyEligibleForTraining') is False,'gate classification drift: '+gid)
 for gid,z in (('train-0039',1),('train-0047',3)):
  ch=reports[gid].get('channels',{}); req(len(ch)==3 and all(x.get('zeroHitBlockCount')==z and x.get('classification')=='FULL_CHANNEL_PRECISION_EXHAUSTED_ZERO_HIT' for x in ch.values()),'rare-event zero evidence drift: '+gid)
 req(screen.get('analysisSha256')=='69d877c5c90e80dfd0956d73f1790d30129423ab58b6414ac24d776bc2c7120f','screen binding drift')
 sgr={x['geometryId']:x for x in screen.get('geometryReports',[])}
 for gid in ('train-0023','train-0031'):
  req(gid in sgr and any(m.get('classification')=='GROSS_METHOD_DISAGREEMENT' for m in sgr[gid].get('methodReports',[])),'gross-disagreement evidence missing: '+gid)
 req('train-0039' in sgr and all(m.get('classification')=='RARE_EVENT_UNRESOLVED' for m in sgr['train-0039'].get('methodReports',[])),'train-0039 rare-event screen drift')
 req(confirm.get('analysisSha256')=='69d58846e889fcd5051cdf66db9660f40d788271c0661b6742e236494f0f179d','confirmation binding drift')
 cgr={x['geometryId']:x for x in confirm.get('candidateReports',[])}
 req(cgr.get('train-0013',{}).get('classification')=='CONFIRMATION_PRECISION_NOT_ESTABLISHED','train-0013 confirmation drift')
 req(cgr.get('train-0041',{}).get('classification')=='CONFIRMATION_PRECISION_NOT_ESTABLISHED','train-0041 confirmation drift')
 req(cgr.get('train-0047',{}).get('classification')=='CONFIRMATION_PRECISION_NOT_ESTABLISHED' and len(cgr['train-0047'].get('statisticsByPrimaryChannel',{}))==3 and all(s.get('anyExactZero') is True for s in cgr['train-0047']['statisticsByPrimaryChannel'].values()),'train-0047 confirmation zero drift')
 u=p.get('treatmentUniverse',{}); req(u.get('precisionExhaustedGeometryIds')==ORDER and u.get('precisionExhaustedGeometryCount')==13 and u.get('allPrecisionExhaustedGeometriesHaveExplicitTreatment') is True,'treatment universe drift')
 rows=u.get('treatments',[]); req([x.get('geometryId') for x in rows]==ORDER and len({x.get('geometryId') for x in rows})==13,'treatment row universe drift')
 for row in rows:
  gid=row['geometryId']; req(row.get('treatmentClass')==EXPECTED[gid],'treatment class drift: '+gid)
  for k in ('admittedForFitting','valuesUsedAsNoisyLabels','targetedAcquisitionAuthorized','oodRegionDefined'): req(row.get(k) is False,'row boundary drift: '+gid+'.'+k)
  req(isinstance(row.get('reentryRequirements'),list) and row['reentryRequirements'],'reentry requirements missing: '+gid)
 g=p.get('globalSemantics',{})
 for k in ('existingHistoricalValuesAdmittedAsPrecisionEstablishedLabels','screeningValuesAdmittedAsTrainingLabels','confirmationValuesAdmittedAsTrainingLabels','epsilonSubstitutionAllowed','noisyLabelLikelihoodFrozen','targetedAcquisitionCampaignAuthorized','regionalOodBoundaryFrozen'): req(g.get(k) is False,'global boundary drift: '+k)
 for k in ('exactZeroPreserved','explicitTreatmentDoesNotEqualTrainingAdmission','futureModelSelectionProtocolMustFreezeSupportedDomainAndRefusalRuleBeforeFitting','futureReentryRequiresNewVersionedEvidenceAndSeparateAdmissionDecision'): req(g.get(k) is True,'global semantic drift: '+k)
 r=p.get('remainingTrainingBoundary',{}); req(r.get('alreadyEligibleHistoricalGeometryCount')==24 and r.get('continuationRequiredGeometryIds')==['train-0014','train-0037'] and r.get('precisionExhaustedGeometryTreatmentComplete') is True,'remaining boundary drift')
 req(r.get('allTrainingGeometriesScientificallyEligible') is False and r.get('modelSelectionProtocolFrozen') is False and r.get('modelFittingAuthorized') is False,'remaining fitting boundary drift')
 b=p.get('executionBoundary',{})
 for k in ('scientificExecutionAuthorized','authorizationOrdinalAllocated','dispatchAuthorized','githubRerunAllowed','retryAllowed','resumeAllowed','modelFittingAuthorized','modelSelectionAuthorized','holdoutValidationOpeningAuthorized','tier2Authorized','productionPromotionAuthorized'): req(b.get(k) is False,'execution boundary drift: '+k)
def main():
 ap=argparse.ArgumentParser()
 for x in ('protocol','decision','readiness','gate','screening','confirmation'): ap.add_argument('--'+x,type=Path,required=True)
 ap.add_argument('--output',type=Path); a=ap.parse_args()
 try:
  p=load(a.protocol); validate(p,load(a.decision),load(a.readiness),load(a.gate),load(a.screening),load(a.confirmation)); out={'status':'PASS','protocolSha256':p['protocolSha256'],'treatedGeometryCount':13,'modelFittingAuthorized':False}; rc=0
 except Exception as e: out={'status':'REFUSED','reason':str(e),'modelFittingAuthorized':False}; rc=2
 if a.output: a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
 print(json.dumps(out,sort_keys=True)); return rc
if __name__=='__main__': raise SystemExit(main())
