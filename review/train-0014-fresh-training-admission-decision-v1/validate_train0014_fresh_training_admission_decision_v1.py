#!/usr/bin/env python3
from __future__ import annotations
import argparse, copy, hashlib, json, math, statistics
from pathlib import Path
from typing import Any

DID='public-tier1-train-0014-fresh-training-admission-decision-v1'
STATUS='REVIEW_ONLY_POST_RESULT_TRAINING_ADMISSION_DECISION_NO_FITTING'
GOV='MYSTIC-STATE-0067'
DECISION_SHA='a5c73eeac21c7db40ded50842653d03f0ec0ee63287fcf5694083ee3692c8135'
PREREG_SHA='6cebee523f775d0814c563aecef0475b5d512b611b06e79a1f9adef089f7eaf0'
ANALYSIS_CONTRACT_SHA='1f7dc8cc71beeb2b56a15a137f377317ae0de90de088ea429fc2eafedcc89c0c'
ANALYSIS_SHA='32dbaa5c006ffb60aa4114e104f518c46bdde210951004319f045f4b8f9824f7'
ANALYSIS_RAW_SHA='5f551a7b3358a121cbe7005d445616a524208718b42e4d0aea085a703d9fca92'
EVIDENCE_SHA='cbe03cd80d6e820849dfd27dbca8260fcdd4def5f4ee1c5fda0ece10fd2f5d96'
MANIFEST_SHA='493329bcaf941910fc6a33bf9364ff424875e88594028e5d6908b0d20e77699c'
REPORT_SHA='9090e4daf54964034694e1137b791faafbe96fdefd421081c34be6c3e0eb6e85'
READINESS_SHA='d43d876862c89aac078069d7f52d7f9be2cf41c36e8ba0e37c31c1fde5bfdc81'
EXHAUSTED_SHA='5eacb2f5f25cb478bacef5261d51fcb1db9e1cf31be22ef2545a103763edfa54'
SALVAGE_RUN=31662184272
SALVAGE_ARTIFACT=9166569024
SALVAGE_DIGEST='sha256:98d78438add36b7aaebefe53a26af8ee1b5f2ead5ba6507eb49faa95420d4838'
SALVAGE_HEAD='b2bd49b855e2ef2718d21c328a5a627792b11390'
SOURCE_RUN=31659053288
SOURCE_HEAD='52da7e06ef1d68a01cdcb76dcdac906bf45b9acf'
CASE_IDS=[f'train-0014-fs-acquire-alis-600-t{i}' for i in range(1,5)]
SEEDS=[1700000001,1700000002,1700000003,1700000004]
PRIMARY=('photopicLuminanceCdM2','scotopicLuminanceScotCdM2','johnsonVEffectiveRadiance_mW_m2_nm_sr')
EXPECTED_STATS={
 'photopicLuminanceCdM2': {'mean':0.025021849097808392,'sampleStd':0.0026476279315157253,'rsem':0.052906320415536855},
 'scotopicLuminanceScotCdM2': {'mean':0.11317369012595753,'sampleStd':0.015231467893271311,'rsem':0.06729244171644193},
 'johnsonVEffectiveRadiance_mW_m2_nm_sr': {'mean':0.00035995952128805393,'sampleStd':3.791466884549908e-05,'rsem':0.05266518400434011},
}

class Refusal(RuntimeError): pass
def req(c:bool,m:str)->None:
    if not c: raise Refusal(m)
def load(p:Path)->dict[str,Any]:
    v=json.loads(p.read_text()); req(isinstance(v,dict),f'object required: {p}'); return v
def canon(v:Any)->str: return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def self_hash_null(v:dict[str,Any],field:str)->str:
    c=copy.deepcopy(v); c[field]=None; return canon(c)
def self_hash_remove(v:dict[str,Any],field:str)->str:
    return canon({k:x for k,x in v.items() if k!=field})
def close(a:float,b:float,tol:float=1e-15)->bool: return math.isclose(float(a),float(b),rel_tol=0.0,abs_tol=tol)

def validate_prereg(p:dict[str,Any])->None:
    req(p.get('preregistrationId')=='public-tier1-train-0014-fresh-training-acquisition-v1','prereg id drift')
    req(p.get('preregistrationSha256')==PREREG_SHA and p.get('preregistrationSha256')==self_hash_null(p,'preregistrationSha256'),'prereg hash drift')
    req(p.get('status')=='REVIEW_ONLY_FROZEN_BEFORE_ANY_FRESH_TRAINING_RESULT','prereg status drift')
    cfg=p.get('configuration') or {}
    req(cfg.get('geometryId')=='train-0014' and cfg.get('method')=='alis-alt-importance' and cfg.get('importanceCenterNm')==600.0,'prereg configuration drift')
    design=p.get('caseDesign') or {}
    req(design.get('caseCount')==4 and design.get('freshIndependentBlocksExactly')==4,'prereg block universe drift')
    req(design.get('seeds')==SEEDS and design.get('perBlockPhotonHistories')==50000000 and design.get('totalConfiguredPhotonHistories')==200000000,'prereg seed/budget drift')
    req(design.get('automaticAdditionalBlocks') is False and design.get('seedReuseAllowed') is False,'prereg extension/reuse drift')
    ev=p.get('trainingEvaluation') or {}
    req(ev.get('historicalFinalTargetRsem')==0.05 and ev.get('historicalMaximumAcceptedRsem')==0.08,'prereg thresholds drift')
    req(ev.get('automaticTrainingAdmissionAfterAnalysis') is False and ev.get('automaticExtensionBeyondFourBlocks') is False,'prereg automatic boundary drift')
    req(ev.get('confirmationValuesIncludedInTrainingStatistics') is False and ev.get('historicalTrainingValuesIncludedInNewFourBlockStatistics') is False,'prereg evidence-role drift')
    req(ev.get('exactZeroPolicy')=='PRESERVE_EXACT_ZERO_NO_EPSILON','prereg zero policy drift')

def validate_evidence(e:dict[str,Any])->None:
    req(e.get('evidenceId')=='public-tier1-training-continuation-train0014-normalized-evidence-v1','evidence id drift')
    req(e.get('evidenceSha256')==EVIDENCE_SHA and e.get('evidenceSha256')==self_hash_remove(e,'evidenceSha256'),'evidence hash drift')
    req(e.get('status')=='NORMALIZED_ATTEMPT1_FRESH_EVIDENCE' and e.get('variant')=='train0014','evidence status/variant drift')
    req(e.get('analysisContractSha256')==ANALYSIS_CONTRACT_SHA and e.get('executionManifestSha256')==MANIFEST_SHA,'evidence contract binding drift')
    req(e.get('caseCount')==4 and e.get('holdoutValuesRead') is False and e.get('epsilonSubstitutionUsed') is False and e.get('exactZeroPreserved') is True,'evidence boundary drift')
    rows=e.get('cases'); req(isinstance(rows,list) and len(rows)==4,'evidence case count drift')
    rows=sorted(rows,key=lambda r:r.get('block'))
    req([r.get('caseId') for r in rows]==CASE_IDS and [r.get('seed') for r in rows]==SEEDS,'evidence case/seed identity drift')
    for i,r in enumerate(rows,1):
        req(r.get('block')==i and r.get('geometryId')=='train-0014' and r.get('method')=='alis-alt-importance' and r.get('importanceCenterNm')==600.0,'evidence case configuration drift')
        req(r.get('photonHistories')==50000000,'evidence photon drift')
        z=r.get('zeroHitByChannel') or {}; req(set(z)==set(PRIMARY) and not any(z.values()),'evidence zero drift')
        ch=r.get('channels') or {}; req(set(ch)==set(PRIMARY) and all(math.isfinite(float(ch[k])) and float(ch[k])>0 for k in PRIMARY),'evidence channel drift')
    for ch in PRIMARY:
        vals=[float(r['channels'][ch]) for r in rows]
        mean=statistics.fmean(vals); sd=statistics.stdev(vals); rsem=sd/math.sqrt(4)/mean
        ex=EXPECTED_STATS[ch]
        req(close(mean,ex['mean']) and close(sd,ex['sampleStd']) and close(rsem,ex['rsem']),'recomputed evidence statistics drift: '+ch)

def validate_analysis(a:dict[str,Any])->None:
    req(a.get('analysisId')=='public-tier1-training-continuation-train0014-analysis-v1','analysis id drift')
    req(a.get('analysisSha256')==ANALYSIS_SHA and a.get('analysisSha256')==self_hash_remove(a,'analysisSha256'),'analysis hash drift')
    req(a.get('analysisContractSha256')==ANALYSIS_CONTRACT_SHA and a.get('normalizedEvidenceSha256')==EVIDENCE_SHA,'analysis source binding drift')
    req(a.get('status')=='ANALYZED_WITHOUT_DOWNSTREAM_ADMISSION' and a.get('variant')=='train0014','analysis status drift')
    r=a.get('result') or {}
    req(r.get('classification')=='FRESH_TRAINING_PRECISION_WITHIN_HISTORICAL_MAXIMUM','analysis classification drift')
    req(r.get('anyExactZeroPrimaryBlock') is False and r.get('automaticExtension') is False and r.get('automaticTrainingAdmission') is False and r.get('valuesAdmittedAsTrainingLabels') is False,'analysis boundary drift')
    stats=r.get('statistics') or {}; req(set(stats)==set(PRIMARY),'analysis statistics universe drift')
    for ch in PRIMARY:
        ex=EXPECTED_STATS[ch]; got=stats[ch]
        req(close(got.get('mean'),ex['mean']) and close(got.get('sampleStd'),ex['sampleStd']) and close(got.get('rsem'),ex['rsem']),'analysis statistic drift: '+ch)
        req(float(got['rsem'])<=0.08,'historical maximum exceeded: '+ch)
    req(max(float(stats[ch]['rsem']) for ch in PRIMARY)>0.05,'expected within-maximum/non-final-target class no longer true')
    b=a.get('downstreamBoundary') or {}
    for k in ('trainingAdmissionAuthorized','scientificExecutionAuthorized','modelFittingAuthorized','modelSelectionAuthorized','holdoutValidationOpeningAuthorized','tier2Authorized','productionPromotionAuthorized'):
        req(b.get(k) is False,'analysis downstream boundary drift: '+k)

def validate_report(r:dict[str,Any])->None:
    req(r.get('reportSha256')==REPORT_SHA and r.get('reportSha256')==self_hash_remove(r,'reportSha256'),'salvage report hash drift')
    req(r.get('status')=='AUDITED_POSTPROCESS_SALVAGE_COMPLETE' and r.get('stageId')=='training-continuation-train0014-ordinal18-postprocess-salvage-v2','salvage report status drift')
    req(r.get('analysisSha256')==ANALYSIS_SHA and r.get('normalizedEvidenceSha256')==EVIDENCE_SHA and r.get('analysisContractSha256')==ANALYSIS_CONTRACT_SHA,'salvage report analysis binding drift')
    req(r.get('authoritativeExecutionManifestSha256')==MANIFEST_SHA,'salvage report manifest drift')
    req(r.get('sourceRunId')==SOURCE_RUN and r.get('sourceRunAttempt')==1 and r.get('sourceHeadSha')==SOURCE_HEAD,'source science identity drift')
    req(r.get('solverExecutionsPerformedBySalvage')==0 and r.get('sourceArtifactsModified') is False,'salvage scientific mutation drift')
    req(r.get('classification')=='FRESH_TRAINING_PRECISION_WITHIN_HISTORICAL_MAXIMUM' and r.get('anyExactZeroPrimaryBlock') is False,'salvage classification drift')
    req(r.get('automaticTrainingAdmission') is False and r.get('valuesAdmittedAsTrainingLabels') is False,'salvage automatic boundary drift')
    req(r.get('holdoutOpened') is False and r.get('modelFittingAuthorized') is False and r.get('modelSelectionAuthorized') is False and r.get('tier2Authorized') is False and r.get('productionPromotionAuthorized') is False,'salvage downstream boundary drift')

def validate_readiness(r:dict[str,Any])->None:
    req(r.get('readinessId')=='public-tier1-full-spectrum-training-admission-readiness-v2','readiness id drift')
    req(r.get('readinessSha256')==READINESS_SHA and r.get('readinessSha256')==self_hash_null(r,'readinessSha256'),'readiness hash drift')
    u=r.get('currentUniverse') or {}; req(u.get('existingTrainingEligibleCount')==24 and u.get('continuationRequiredGeometryIds')==['train-0014','train-0037'] and u.get('precisionExhaustedCount')==13,'prior readiness universe drift')
    by={x.get('geometryId'):x for x in r.get('geometryTreatments',[])}
    x=by.get('train-0014') or {}; req(x.get('currentTrainingLabelAdmitted') is False and x.get('fittingUsePermittedNow') is False,'prior train0014 readiness drift')
    x=by.get('train-0037') or {}; req(x.get('currentTrainingLabelAdmitted') is False,'prior train0037 readiness drift')

def validate_exhausted(p:dict[str,Any])->None:
    req(p.get('protocolId')=='public-tier1-full-spectrum-precision-exhausted-treatment-v1','exhausted protocol id drift')
    req(p.get('protocolSha256')==EXHAUSTED_SHA and p.get('protocolSha256')==self_hash_null(p,'protocolSha256'),'exhausted protocol hash drift')
    u=p.get('treatmentUniverse') or {}; req(u.get('precisionExhaustedGeometryCount')==13 and u.get('allPrecisionExhaustedGeometriesHaveExplicitTreatment') is True,'exhausted treatment universe drift')
    req(all(x.get('admittedForFitting') is False for x in u.get('treatments',[])),'exhausted geometry admission drift')
    rem=p.get('remainingTrainingBoundary') or {}; req(rem.get('precisionExhaustedGeometryTreatmentComplete') is True and rem.get('continuationRequiredGeometryIds')==['train-0014','train-0037'],'exhausted remaining boundary drift')

def validate_decision(d:dict[str,Any])->None:
    req(d.get('decisionId')==DID and d.get('status')==STATUS and d.get('governance')==GOV,'decision identity/status drift')
    req(d.get('decisionSha256')==DECISION_SHA and d.get('decisionSha256')==self_hash_null(d,'decisionSha256'),'decision self-hash drift')
    s=d.get('sourceBindings') or {}
    req(s.get('train0014PreregistrationSha256')==PREREG_SHA and s.get('analysisContractSha256')==ANALYSIS_CONTRACT_SHA and s.get('analysisSha256')==ANALYSIS_SHA and s.get('analysisRawSha256')==ANALYSIS_RAW_SHA and s.get('normalizedEvidenceSha256')==EVIDENCE_SHA and s.get('authoritativeExecutionManifestSha256')==MANIFEST_SHA,'decision source binding drift')
    req(s.get('salvageV2ReportSha256')==REPORT_SHA and s.get('priorTrainingReadinessSha256')==READINESS_SHA and s.get('precisionExhaustedTreatmentSha256')==EXHAUSTED_SHA,'decision governance binding drift')
    req(s.get('scientificOrdinal')==18 and s.get('sourceScientificRunId')==SOURCE_RUN and s.get('sourceScientificRunAttempt')==1 and s.get('sourceScientificHeadSha')==SOURCE_HEAD,'decision source science drift')
    art=s.get('salvageV2Artifact') or {}; req(art.get('artifactId')==SALVAGE_ARTIFACT and art.get('digest')==SALVAGE_DIGEST and art.get('runId')==SALVAGE_RUN and art.get('runAttempt')==1 and art.get('headSha')==SALVAGE_HEAD and art.get('headBranch')=='postprocess/training-continuation-train0014-ordinal18-salvage-v2','decision salvage artifact drift')
    sem=d.get('decisionSemantics') or {}
    req(sem.get('decisionType')=='EXACT_GEOMETRY_FRESH_TRAINING_LABEL_ADMISSION_ONLY' and sem.get('freshOrdinal18ValuesAdmittedAsTrainingLabels') is True,'decision admission semantic drift')
    for k in ('confirmationValuesAdmittedAsTrainingLabels','historicalTrain0014ValuesCombinedWithFreshEvidence','globalEstimatorSelected','modelFittingAuthorized','modelSelectionAuthorized','newScientificExecutionAuthorized','productionPromotionAuthorized','protectedHoldoutOpeningAuthorized','tier2Authorized','train0037Resolved'):
        req(sem.get(k) is False,'decision safety semantic drift: '+k)
    f=d.get('frozenInterpretation') or {}
    req(f.get('admissionDecision')=='ADMIT_FRESH_FOUR_BLOCK_TRAINING_EVIDENCE_WITHIN_HISTORICAL_MAXIMUM','decision class drift')
    req(f.get('sourceClassification')=='FRESH_TRAINING_PRECISION_WITHIN_HISTORICAL_MAXIMUM' and f.get('exactZeroObserved') is False,'decision evidence interpretation drift')
    req(f.get('historicalFinalTargetRsem')==0.05 and f.get('historicalMaximumAcceptedRsem')==0.08 and close(f.get('maximumPrimaryChannelRsem'),EXPECTED_STATS['scotopicLuminanceScotCdM2']['rsem']),'decision threshold drift')
    lab=f.get('admittedTrainingLabel') or {}; req(lab.get('aggregation')=='ARITHMETIC_MEAN_OVER_EXACTLY_FOUR_FRESH_ORDINAL18_BLOCKS' and lab.get('sourceBlockCount')==4 and lab.get('sourceCaseIds')==CASE_IDS and lab.get('sourceSeeds')==SEEDS,'decision label construction drift')
    req(lab.get('confirmationValuesIncluded') is False and lab.get('historicalTrainingValuesIncluded') is False,'decision label source contamination')
    stats=lab.get('statistics') or {}; req(set(stats)==set(PRIMARY),'decision label statistics universe drift')
    for ch in PRIMARY:
        ex=EXPECTED_STATS[ch]; got=stats[ch]
        req(close(got.get('mean'),ex['mean']) and close(got.get('sampleStd'),ex['sampleStd']) and close(got.get('rsem'),ex['rsem']),'decision label statistics drift: '+ch)
    u=f.get('currentUniverseAfterDecision') or {}
    req(u.get('priorAdmittedHistoricalGeometryCount')==24 and u.get('admittedTrainingGeometryCount')==25 and u.get('newlyAdmittedGeometryIds')==['train-0014'],'decision universe count drift')
    req(u.get('remainingContinuationRequiredGeometryIds')==['train-0037'] and u.get('precisionExhaustedExplicitTreatmentCount')==13 and u.get('precisionExhaustedTreatmentComplete') is True,'decision remaining universe drift')
    req(u.get('allTrainingGeometriesHaveFinalTreatment') is False and u.get('globalModelFittingAuthorized') is False,'decision global fitting boundary drift')
    n=d.get('nextBoundary') or {}
    req(n.get('freshScientificOrdinal19Allocated') is False and n.get('noAutomaticTransition') is True and n.get('modelFittingRequiresSeparateVersionedProtocolAfterTrain0037FinalTreatment') is True,'decision next boundary drift')

def validate_all(d,p,a,e,r,ready,exhausted)->None:
    validate_prereg(p); validate_evidence(e); validate_analysis(a); validate_report(r); validate_readiness(ready); validate_exhausted(exhausted); validate_decision(d)
    # Cross-object equality after every individual identity check.
    req(d['sourceBindings']['analysisSha256']==a['analysisSha256']==r['analysisSha256'],'cross analysis binding mismatch')
    req(d['sourceBindings']['normalizedEvidenceSha256']==e['evidenceSha256']==a['normalizedEvidenceSha256']==r['normalizedEvidenceSha256'],'cross evidence binding mismatch')
    req(d['sourceBindings']['train0014PreregistrationSha256']==p['preregistrationSha256'],'cross prereg binding mismatch')
    req(d['sourceBindings']['salvageV2ReportSha256']==r['reportSha256'],'cross report binding mismatch')
    req(d['sourceBindings']['priorTrainingReadinessSha256']==ready['readinessSha256'],'cross readiness binding mismatch')
    req(d['sourceBindings']['precisionExhaustedTreatmentSha256']==exhausted['protocolSha256'],'cross exhausted binding mismatch')

def main()->int:
    ap=argparse.ArgumentParser()
    for x in ('decision','preregistration','analysis','evidence','salvage-report','prior-readiness','exhausted-treatment'):
        ap.add_argument('--'+x,type=Path,required=True)
    ap.add_argument('--output',type=Path); args=ap.parse_args()
    try:
        d=load(args.decision); p=load(args.preregistration); a=load(args.analysis); e=load(args.evidence); r=load(args.salvage_report); ready=load(args.prior_readiness); exhausted=load(args.exhausted_treatment)
        validate_all(d,p,a,e,r,ready,exhausted)
        out={'status':'PASS','decisionSha256':d['decisionSha256'],'admittedGeometryId':'train-0014','admittedTrainingGeometryCount':25,'remainingContinuationRequiredGeometryIds':['train-0037'],'modelFittingAuthorized':False,'scientificExecutionAuthorized':False}; rc=0
    except Exception as exc:
        out={'status':'REFUSED','reason':str(exc),'modelFittingAuthorized':False,'scientificExecutionAuthorized':False}; rc=2
    if args.output: args.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps(out,sort_keys=True)); return rc
if __name__=='__main__': raise SystemExit(main())
