#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path
from typing import Any

RID='public-tier1-full-spectrum-training-admission-readiness-v2'
RSTATUS='REVIEW_ONLY_TRAINING_ADMISSION_READINESS_NO_EXECUTION'
GATE_ID='public-tier1-full-spectrum-training-admission-gate-v1'
GATE_PROTOCOL='255cde972ba00ac321260b89b644a2d3f30bd3f7d685427d3a350c06424ba5b3'
DECISION_ID='public-tier1-full-spectrum-estimator-confirmation-decision-v1'
DECISION_SHA='fa6178e9042226c5326306ee42f9fa7f3cdaca292552b36b3b8e151b2412cc0f'
SCREEN_SHA='69d877c5c90e80dfd0956d73f1790d30129423ab58b6414ac24d776bc2c7120f'
ELIGIBLE=['train-0001','train-0002','train-0004','train-0006','train-0008','train-0009','train-0012','train-0016','train-0017','train-0018','train-0021','train-0022','train-0024','train-0026','train-0028','train-0032','train-0033','train-0034','train-0036','train-0038','train-0042','train-0044','train-0046','train-0048']
CONT=['train-0014','train-0037']
EXHAUSTED=['train-0003','train-0007','train-0011','train-0013','train-0019','train-0023','train-0027','train-0029','train-0031','train-0039','train-0041','train-0043','train-0047']
ALL=set(ELIGIBLE+CONT+EXHAUSTED)
class Refusal(RuntimeError): pass
def req(c,m):
    if not c: raise Refusal(m)
def load(p:Path)->dict[str,Any]:
    v=json.loads(p.read_text()); req(isinstance(v,dict),f'expected JSON object: {p}'); return v
def canon(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def self_hash(v,f):
    c=dict(v); c[f]=None; return canon(c)
def validate_gate(g):
    req(g.get('gateId')==GATE_ID and g.get('gateProtocolSha256')==GATE_PROTOCOL,'training gate identity drift')
    req(g.get('expectedGeometryCount')==39 and g.get('expectedCaseArtifactCount')==166 and g.get('eligibleGeometryCount')==24,'training gate counts drift')
    req(g.get('fullTrainingUniversePresent') is True and g.get('allTrainingGeometriesScientificallyEligible') is False,'training gate universe drift')
    req(g.get('fittingAuthorized') is False,'training gate fitting boundary drift')
    req(g.get('continuationRequiredGeometryIds')==CONT,'continuation geometry drift')
    rows=g.get('geometryReports'); req(isinstance(rows,list) and len(rows)==39,'training geometry report count drift')
    by={r.get('geometryId'):r for r in rows}; req(set(by)==ALL,'training geometry universe drift')
    for gid in ELIGIBLE: req(by[gid].get('classification')=='FULL_CHANNEL_TRAINING_ELIGIBLE' and by[gid].get('scientificallyEligibleForTraining') is True,f'eligible geometry drift: {gid}')
    for gid in EXHAUSTED: req(by[gid].get('classification')=='FULL_CHANNEL_PRECISION_EXHAUSTED' and by[gid].get('scientificallyEligibleForTraining') is False,f'exhausted geometry drift: {gid}')
    expected={'train-0014':0.11419096180087274,'train-0037':0.15128486473118663}
    for gid,rsem in expected.items():
        r=by[gid]; req(r.get('classification')=='FULL_CHANNEL_CONTINUATION_REQUIRED' and r.get('scientificallyEligibleForTraining') is False,f'continuation drift: {gid}')
        ch=(r.get('channels') or {}).get('scotopicLuminanceScotCdM2') or {}
        req(ch.get('classification')=='FULL_CHANNEL_CONTINUATION_REQUIRED','problem channel drift: '+gid)
        req(abs(float(ch.get('relativeStandardErrorOfMean'))-rsem)<1e-15,'problem RSEM drift: '+gid)
    return by
def validate_decision(d):
    req(d.get('decisionId')==DECISION_ID and d.get('decisionSha256')==DECISION_SHA,'confirmation decision identity drift')
    req(d.get('decisionSha256')==self_hash(d,'decisionSha256'),'confirmation decision self-hash mismatch')
    sem=d.get('decisionSemantics') or {}
    for k in ('globalEstimatorSelected','globalImportanceCenterSelected','confirmationValuesConvertedToTrainingEvidence','freshTrainingSeedsOrOrdinalAllocated','newScientificExecutionAuthorized','modelFittingAuthorized','modelSelectionAuthorized','protectedHoldoutOpeningAuthorized','tier2Authorized','productionPromotionAuthorized'): req(sem.get(k) is False,'confirmation decision boundary drift: '+k)
    rows={r['candidateId']:r for r in d['frozenInterpretation']['candidateDecisions']}
    req(rows['train-0014-alis-600']['sourceConfirmationClassification']=='CONFIRMED_WITHIN_HISTORICAL_MAXIMUM','train-0014 confirmation drift')
    req(rows['train-0014-alis-600']['confirmationValuesAdmittedAsTrainingLabels'] is False,'train-0014 evidence-role drift')
    req(rows['train-0009-alis-500']['sourceConfirmationClassification']=='CONFIRMED_AT_HISTORICAL_FINAL_TARGET','train-0009 confirmation drift')
def find_geometry_reports(v):
    if isinstance(v,dict):
        if isinstance(v.get('geometryReports'),list):
            for r in v['geometryReports']:
                if isinstance(r,dict) and r.get('geometryId'): yield r
        for x in v.values(): yield from find_geometry_reports(x)
    elif isinstance(v,list):
        for x in v: yield from find_geometry_reports(x)
def validate_screening(s):
    req(s.get('analysisSha256')==SCREEN_SHA and s.get('screeningStatus')=='PILOT_SCREENING_ANALYZED_NO_AUTOMATIC_ESTIMATOR_SELECTION','screening identity/status drift')
    req(s.get('modelFittingAuthorized') is False and s.get('modelSelectionAuthorized') is False and s.get('holdoutValuesRead') is False,'screening boundary drift')
    rows=[r for r in find_geometry_reports(s) if r.get('geometryId')=='train-0037']; req(len(rows)==1,'expected one train-0037 screening report')
    r=rows[0]; req(r.get('historicalImportanceCenterNm')==550.0 and r.get('historicalProblemChannels')==['scotopicLuminanceScotCdM2'],'train-0037 historical binding drift')
    methods={(m.get('method'),m.get('importanceCenterNm')):m for m in r.get('methodReports',[])}
    req(set(methods)=={('alis-alt-importance',500.0),('alis-alt-importance',600.0)},'train-0037 method universe drift')
    for key,m in methods.items(): req(m.get('classification')=='NO_CLEAR_SCREENING_GAIN',f'train-0037 screening classification drift: {key}')
def validate_readiness(r):
    req(r.get('readinessId')==RID and r.get('status')==RSTATUS,'readiness identity/status drift')
    req(r.get('readinessSha256')==self_hash(r,'readinessSha256'),'readiness self-hash mismatch')
    src=r.get('sourceTrainingAdmissionGate') or {}; req(src.get('gitBlobSha')=='c136f23f7df68b1481cb5ff939646198a3e336fe','gate blob binding drift')
    req((r.get('sourceConfirmationDecision') or {}).get('decisionSha256')==DECISION_SHA,'decision binding drift')
    req((r.get('sourcePilotScreening') or {}).get('analysisSha256')==SCREEN_SHA,'screening binding drift')
    u=r.get('currentUniverse') or {}
    req(u.get('geometryCount')==39 and u.get('existingTrainingEligibleCount')==24 and u.get('continuationRequiredCount')==2 and u.get('precisionExhaustedCount')==13,'readiness counts drift')
    req(u.get('existingTrainingEligibleGeometryIds')==ELIGIBLE and u.get('continuationRequiredGeometryIds')==CONT and u.get('precisionExhaustedGeometryIds')==EXHAUSTED,'readiness lists drift')
    req(u.get('allTrainingGeometriesScientificallyEligible') is False and u.get('allTrainingGeometriesHaveFinalTreatment') is False,'readiness closure drift')
    rows=r.get('geometryTreatments'); req(isinstance(rows,list) and len(rows)==39,'readiness treatment count drift')
    by={x.get('geometryId'):x for x in rows}; req(set(by)==ALL,'readiness treatment universe drift')
    for gid in ELIGIBLE:
        x=by[gid]; req(x.get('currentTrainingLabelAdmitted') is True and x.get('fittingUsePermittedNow') is True,'eligible treatment drift: '+gid)
    x=by['train-0009']; c=x.get('confirmedAlternateConfiguration') or {}; req(c.get('replacesExistingTrainingEvidence') is False and c.get('globalUseAuthorized') is False,'train-0009 alternate handling drift')
    x=by['train-0014']; req(x.get('currentTrainingLabelAdmitted') is False and x.get('postConfirmationTreatment')=='FRESH_TRAINING_ACQUISITION_PREREGISTRATION_REQUIRED_USING_CONFIRMED_600NM_CONFIGURATION','train-0014 readiness drift')
    c=x.get('confirmedConfiguration') or {}; req(c.get('importanceCenterNm')==600.0 and c.get('confirmationValuesAdmittedAsTrainingLabels') is False and c.get('globalUseAuthorized') is False,'train-0014 configuration drift')
    x=by['train-0037']; req(x.get('confirmedConfiguration') is None and x.get('postConfirmationTreatment')=='TARGETED_ESTIMATOR_COMPARISON_PREREGISTRATION_REQUIRED_NO_CONFIRMED_CONFIGURATION','train-0037 readiness drift')
    for gid in EXHAUSTED: req(by[gid].get('currentTrainingLabelAdmitted') is False and by[gid].get('fittingUsePermittedNow') is False,'exhausted treatment drift: '+gid)
    hb=r.get('hardBoundary') or {}
    for k in ('scientificExecutionAuthorized','freshSeedsAllocated','scientificOrdinalAllocated','dispatchAuthorized','confirmationValuesAdmittedAsTrainingLabels','globalEstimatorSelected','modelFittingAuthorized','modelSelectionAuthorized','protectedHoldoutOpeningAuthorized','tier2Authorized','productionPromotionAuthorized'): req(hb.get(k) is False,'hard boundary drift: '+k)
    req(len(r.get('nextReviewPackages') or [])==3,'next package surface drift')
def main():
    p=argparse.ArgumentParser(); p.add_argument('--gate',type=Path,required=True); p.add_argument('--decision',type=Path,required=True); p.add_argument('--screening',type=Path,required=True); p.add_argument('--readiness',type=Path,required=True); p.add_argument('--output',type=Path)
    a=p.parse_args()
    try:
        g=load(a.gate); d=load(a.decision); s=load(a.screening); r=load(a.readiness)
        validate_gate(g); validate_decision(d); validate_screening(s); validate_readiness(r)
        out={'status':'PASS','readinessSha256':r['readinessSha256'],'geometryCount':39,'fittingAuthorized':False,'scientificExecutionAuthorized':False}
        rc=0
    except Exception as e:
        out={'status':'REFUSED','reason':str(e),'fittingAuthorized':False,'scientificExecutionAuthorized':False}; rc=2
    if a.output: a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps(out,sort_keys=True)); return rc
if __name__=='__main__': raise SystemExit(main())
