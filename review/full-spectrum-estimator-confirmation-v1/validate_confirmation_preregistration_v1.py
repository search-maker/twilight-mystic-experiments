#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

ALLOWED={
 'LOW_TWO_BLOCK_RSEM_SCREENING_CANDIDATE',
 'SCREENING_VARIANCE_GAIN_ON_HISTORICAL_PROBLEM_CHANNELS',
 'RARE_EVENT_TWO_METHOD_FINITE_SCREENING_REQUIRES_CONFIRMATION',
}
EXPECTED_ANALYSIS_SHA='69d877c5c90e80dfd0956d73f1790d30129423ab58b6414ac24d776bc2c7120f'
EXPECTED_EVIDENCE_SHA='d0979b6827f80e2f2b76f62340a72dcec14a3cb016b9645680c38da0d5fcf0f5'
EXPECTED_PILOT_PROTOCOL_SHA='7ca0923204452ab203249dfd060dd5fef5465c48a20ba529c0a20748e0152434'
EXPECTED_SCREEN_PROTOCOL_SHA='ad847ecb7f46629787148c572fe0e6d6d26c7eda12837d74de00b28abb64de6f'
EXPECTED_SEEDS=set(range(1600000001,1600000025))

def canon(v):
 return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def load(p):
 v=json.loads(Path(p).read_text())
 if not isinstance(v,dict): raise ValueError(f'expected object: {p}')
 return v

def verify(pr, screening, evidence, pilot, seed_audit):
 supplied=pr.get('preregistrationSha256')
 tmp=dict(pr); tmp['preregistrationSha256']=None
 if supplied!=canon(tmp): raise ValueError('confirmation preregistration self-hash mismatch')
 if pr.get('status')!='REVIEW_ONLY_FROZEN_BEFORE_ANY_CONFIRMATION_RESULT': raise ValueError('confirmation preregistration status drift')
 src=pr.get('sourcePilot') or {}
 if src.get('postprocessRunId')!=31556854044 or src.get('postprocessRunAttempt')!=1 or src.get('postprocessArtifactId')!=9126300230: raise ValueError('source postprocess identity drift')
 if src.get('postprocessArtifactDigest')!='sha256:263505300e994364874b06b2137ad5fd6b1fa57f0a45629a1410f684a81c880b': raise ValueError('source artifact digest drift')
 if src.get('scientificRunId')!=31546667072 or src.get('scientificRunAttempt')!=1 or src.get('scientificOrdinal')!=16 or src.get('scientificHeadSha')!='183188bdbe5a899f5dcd1bc4e423fa385d26e3af': raise ValueError('source scientific identity drift')
 if src.get('normalizedEvidenceV7Sha256')!=EXPECTED_EVIDENCE_SHA or src.get('screeningAnalysisV8Sha256')!=EXPECTED_ANALYSIS_SHA or src.get('pilotAcquisitionProtocolSha256')!=EXPECTED_PILOT_PROTOCOL_SHA or src.get('pilotScreeningAnalysisProtocolSha256')!=EXPECTED_SCREEN_PROTOCOL_SHA: raise ValueError('source immutable hash binding drift')
 if screening.get('analysisSha256')!=EXPECTED_ANALYSIS_SHA or screening.get('analysisSha256')!=canon({k:v for k,v in screening.items() if k!='analysisSha256'}): raise ValueError('screening analysis identity/self-hash drift')
 if (screening.get('screeningAnalysisV6') or {}).get('screeningAnalysisProtocolSha256')!=EXPECTED_SCREEN_PROTOCOL_SHA: raise ValueError('screening analysis protocol binding drift')
 if evidence.get('evidenceSha256')!=EXPECTED_EVIDENCE_SHA or evidence.get('evidenceSha256')!=canon({k:v for k,v in evidence.items() if k!='evidenceSha256'}): raise ValueError('normalized evidence identity/self-hash drift')
 if evidence.get('caseCount')!=44 or evidence.get('holdoutValuesRead') is not False: raise ValueError('normalized evidence boundary drift')
 if pilot.get('protocolSha256')!=EXPECTED_PILOT_PROTOCOL_SHA: raise ValueError('pilot protocol identity drift')
 ap=pilot.get('analysisPlan') or {}; cb=ap.get('confirmationBoundary') or {}
 if cb.get('confirmationRequiresSeparatePreregistrationBeforeThoseValuesAreOpened') is not True or cb.get('firstConfirmationFreshIndependentBlocksPerChosenMethod')!=4 or cb.get('screeningBlocksMayEnterFinalConfirmationPrecisionGate') is not False or cb.get('automaticExtensionBeyondFirstConfirmation') is not False: raise ValueError('frozen confirmation boundary drift')
 if ap.get('historicalFinalTargetRsem')!=0.05 or ap.get('historicalMaximumAcceptedRsem')!=0.08: raise ValueError('frozen confirmation precision thresholds drift')
 derived=[]
 for g in screening['screeningAnalysisV6']['geometryReports']:
  for m in g['methodReports']:
   if m.get('method')=='alis-alt-importance' and m.get('classification') in ALLOWED:
    derived.append((g['geometryId'],float(m['importanceCenterNm']),m['classification']))
 derived=sorted(derived)
 actual=sorted((x['geometryId'],float(x['importanceCenterNm']),x['screeningClassification']) for x in pr.get('candidates',[]))
 if actual!=derived or len(actual)!=6: raise ValueError(f'candidate nomination drift: {actual!r} != {derived!r}')
 erows=evidence.get('cases') or []
 for c in pr['candidates']:
  matches=sorted((r for r in erows if r.get('geometryId')==c['geometryId'] and r.get('method')=='alis-alt-importance' and float(r.get('importanceCenterNm'))==float(c['importanceCenterNm'])), key=lambda r:r['replicate'])
  if len(matches)!=2 or [r['replicate'] for r in matches]!=[1,2]: raise ValueError(f'pilot candidate case binding drift: {c["candidateId"]}')
  if [r['caseId'] for r in matches]!=c['pilotCaseIds']: raise ValueError(f'pilot case-id binding drift: {c["candidateId"]}')
  if any(r['photonHistories']!=c['perBlockPhotonHistories'] for r in matches): raise ValueError(f'pilot photon-count binding drift: {c["candidateId"]}')
 design=pr.get('caseDesign') or {}; cases=design.get('cases') or []
 if design.get('caseCount')!=24 or len(cases)!=24 or design.get('freshIndependentBlocksPerCandidate')!=4: raise ValueError('confirmation case-count/block-count drift')
 if design.get('automaticAdditionalBlocks') is not False or design.get('screeningBlocksReusedAsConfirmation') is not False: raise ValueError('confirmation extension/selection-block boundary drift')
 seeds=[r.get('seed') for r in cases]
 if set(seeds)!=EXPECTED_SEEDS or len(seeds)!=len(set(seeds)) or max(seeds)>2147483647: raise ValueError('confirmation seed range/uniqueness drift')
 if sum(int(r.get('photonHistories',0)) for r in cases)!=2_000_000_000: raise ValueError('confirmation photon-budget drift')
 pilot_seeds={r.get('seed') for r in erows}
 if set(seeds)&pilot_seeds: raise ValueError('confirmation seed collision with ordinal-16 pilot')
 source_cases=seed_audit.get('sourceCases') or []
 if seed_audit.get('status')!='PASSED_LOCAL_EXACT_166_SOURCE_SEED_AUDIT' or len(source_cases)!=166: raise ValueError('exact 166-source seed audit identity/count drift')
 source_seeds={r.get('seed') for r in source_cases}
 if None in source_seeds or len(source_seeds)!=166: raise ValueError('source seed audit missing/duplicate seed values')
 if set(seeds)&source_seeds: raise ValueError('confirmation seed collision with exact 166-source audit')
 by={c['candidateId']:c for c in pr['candidates']}
 if len(by)!=6: raise ValueError('duplicate candidateId in confirmation preregistration')
 blocks={}
 for r in cases:
  c=by.get(r.get('candidateId'))
  if c is None: raise ValueError('confirmation case references unknown candidate')
  if r.get('geometryId')!=c['geometryId'] or r.get('method')!='alis-alt-importance' or float(r.get('importanceCenterNm'))!=float(c['importanceCenterNm']) or r.get('photonHistories')!=c['perBlockPhotonHistories']: raise ValueError(f'confirmation case physics/budget drift: {r.get("caseId")}')
  blocks.setdefault(r['candidateId'],[]).append(r.get('confirmationBlock'))
 if any(sorted(v)!=[1,2,3,4] for v in blocks.values()) or set(blocks)!=set(by): raise ValueError('confirmation block identity drift')
 ev=pr.get('confirmationEvaluation') or {}
 if ev.get('confirmationBlocksOnly') is not True or ev.get('screeningBlocksExcludedFromFinalPrecisionGate') is not True or ev.get('historicalFinalTargetRsem')!=0.05 or ev.get('historicalMaximumAcceptedRsem')!=0.08 or ev.get('automaticExtensionBeyondFirstConfirmation') is not False or ev.get('automaticGlobalEstimatorSelection') is not False: raise ValueError('confirmation evaluation boundary drift')
 xb=pr.get('executionBoundary') or {}
 if any(xb.get(k) is not False for k in ('scientificExecutionAuthorized','workflowDispatchAuthorized','githubRerunAllowed','retryAllowed','resumeAllowed','modelFittingAuthorized','modelSelectionAuthorized','holdoutValidationOpeningAuthorized','tier2Authorized','productionPromotionAuthorized')): raise ValueError('review-only execution boundary drift')
 if xb.get('authorizationOrdinalAllocated') is not False: raise ValueError('confirmation ordinal must remain unallocated in review package')
 return {'status':'PASSED','candidateCount':6,'confirmationCaseCount':24,'seedMin':min(seeds),'seedMax':max(seeds),'scientificExecutionAuthorized':False}

def main():
 p=argparse.ArgumentParser(); p.add_argument('--preregistration',required=True); p.add_argument('--screening-analysis',required=True); p.add_argument('--normalized-evidence',required=True); p.add_argument('--pilot-preregistration',required=True); p.add_argument('--source-seed-audit',required=True); a=p.parse_args()
 try:
  print(json.dumps(verify(load(a.preregistration),load(a.screening_analysis),load(a.normalized_evidence),load(a.pilot_preregistration),load(a.source_seed_audit)),indent=2,sort_keys=True)); return 0
 except Exception as e:
  print(json.dumps({'status':'REFUSED','reason':str(e),'scientificExecutionAuthorized':False},indent=2,sort_keys=True)); return 2
if __name__=='__main__': raise SystemExit(main())
