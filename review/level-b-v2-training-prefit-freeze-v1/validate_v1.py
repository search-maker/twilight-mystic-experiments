#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, math
from pathlib import Path

TRAIN_IDS = [
    'train-0001','train-0002','train-0004','train-0006','train-0008','train-0009','train-0012','train-0014','train-0016','train-0017','train-0018','train-0021','train-0022','train-0024','train-0026','train-0028','train-0032','train-0033','train-0034','train-0036','train-0038','train-0042','train-0044','train-0046','train-0048','train-0052','train-0054','train-0056','train-0058','train-0062','train-0064','train-0066','train-0068','train-0072','train-0074','train-0076','train-0078','train-0082','train-0084','train-0086','train-0088','train-0092','train-0094','train-0096'
]
OPENED = ['train-0050','train-0060','train-0065','train-0070','train-0080','train-0090']
RIDGES = [0.00001,0.0001,0.001,0.01,0.1]
FAMILIES = [
    ('split-ridge-cos-compact','COS_COMPACT_13_TERMS',13,1),
    ('split-ridge-physical-compact','PHYSICAL_COMPACT_16_TERMS',16,2),
    ('split-ridge-physical-compact-cubic','PHYSICAL_COMPACT_16_PLUS_S_A_O_CUBICS_19_TERMS',19,3),
    ('split-ridge-physical-poly2','FULL_DEGREE2_ON_FIVE_PHYSICAL_COORDINATES_21_TERMS',21,4),
]

class Refusal(RuntimeError):
    pass

def req(cond: bool, msg: str) -> None:
    if not cond:
        raise Refusal(msg)

def load(path: Path) -> dict:
    obj=json.loads(path.read_text(encoding='utf-8'))
    req(isinstance(obj,dict),'protocol must be object')
    return obj

def validate(p: dict) -> None:
    req((p.get('schemaVersion'),p.get('protocolId'),p.get('status'),p.get('governance')) == (1,'level-b-v2-training-only-prefit-freeze-v1','REVIEW_ONLY_PREFIT_FREEZE_NO_CHANGED_REAL_FIT','MYSTIC-STATE-0068'),'identity drift')
    req(p.get('sourceMainAtFreeze')=='7e52511e8b30ae4522130ca2aa0a54aba2738274','source main drift')
    rb=p.get('rationaleSourceBoundary') or {}
    req(rb.get('ordinal22PostmortemMayInfluenceCandidateSelection') is False and rb.get('ordinal22ValuesMayBeReadByFutureTrainingExecution') is False,'ordinal22 rationale boundary opened')
    s=p.get('sourceTrainingRepresentation') or {}
    req((s.get('resultBindingGitBlobSha'),s.get('artifactId'),s.get('artifactDigest')) == ('a18acace210eaef621930bd5682113a686ad10a3',9208203541,'sha256:2fe50ed674155f440322c92d28877f5c022f0cc5fa13e1e601596a9902482815'),'representation source drift')
    req((s.get('trainingDatasetCanonicalSha256'),s.get('representationPackageSha256')) == ('bb7908426d9d545f43c082aebbaab1829a486e2962d0b9ee34a5e8bef5390133','2491ac91ed924f2ba69b37ea20f48d63f51d41146cd9fe50e0bd63bfb315a763'),'representation hash drift')
    req((s.get('trainingGeometryCount'),s.get('representationFeatureCount'),s.get('positiveIntegratedChannelCount'),s.get('nullspacePcaComponentCount')) == (44,13,3,10),'representation dimensions drift')
    req(s.get('holdoutValuesRead') is False,'source says holdout opened')
    r=p.get('roleIsolation') or {}
    req(r.get('exactTrainingGeometryIds')==TRAIN_IDS,'training geometry identity/order drift')
    req(r.get('openedV1ProtectedDiagnosticOnlyGeometryIds')==OPENED,'opened geometry identity drift')
    req(not set(TRAIN_IDS)&set(OPENED),'training/opened overlap')
    req(r.get('openedV1ProtectedValuesAllowedForTrainingOrSelection') is False and r.get('openedV1ProtectedValuesAllowedForThresholdOrSupportSelection') is False,'opened values admitted')
    req((r.get('trainingRecordCountRequired'),r.get('protectedRecordCountRequired'))==(44,0),'role count drift')
    t=p.get('targets') or {}
    req(t.get('positiveIntegratedChannels')==['photopicLuminanceCdM2','scotopicLuminanceScotCdM2','johnsonVEffectiveRadiance_mW_m2_nm_sr'],'channel drift')
    req(t.get('shapeTargetCount')==10 and t.get('epsilonSubstitutionAllowed') is False,'target semantics drift')
    m=p.get('modelSelection') or {}
    req(m.get('selectionData')=='EXACT_44_GEOMETRY_TRAINING_REPRESENTATION_ONLY','selection source drift')
    req(m.get('ridgeGrid')==RIDGES,'ridge grid drift')
    fam=m.get('candidateFamilies') or []
    req(len(fam)==4,'family count drift')
    total=0
    for got,exp in zip(fam,FAMILIES):
        fid,basis,nterms,rank=exp
        req((got.get('familyId'),got.get('kind'),got.get('basis'),got.get('basisTermCount'),got.get('complexityRank'))==(fid,'SPLIT_RIDGE',basis,nterms,rank),f'family drift: {fid}')
        req(got.get('primaryRidgeValues')==RIDGES and got.get('shapeRidgeValues')==RIDGES,'ridge family grid drift')
        req(got.get('penalizeIntercept') is False,'intercept penalty drift')
        total += len(RIDGES)*len(RIDGES)
    req(total==100 and m.get('candidateCountRequired')==100,'candidate count drift')
    cv=m.get('crossValidationFolds') or {}
    req(cv.get('balanced')=='FIVE_FOLDS_BY_SORTED_GEOMETRY_ID_POSITION_MOD_5','balanced CV drift')
    req(cv.get('leaveOneGeometryOut')=='EXACTLY_44_SINGLE_GEOMETRY_VALIDATION_FOLDS','LOO CV drift')
    req(len(cv.get('boundary') or [])==10 and cv.get('totalFoldCountRequired')==59,'CV count drift')
    g=m.get('trainingOnlyReadinessGates') or {}
    req(g=={
      'looMeanPrimaryMaleMax':0.25,
      'looWorstSinglePrimaryLogErrorMax':0.9,
      'looMeanShapeNrmseMax':1.0,
      'looWorstShapeNrmseMax':1.45,
      'boundaryWorstPrimaryMaleMax':0.3,
      'boundaryWorstShapeNrmseMax':1.45,
      'looPrimaryMustBeatFoldMatchedTrainingMeanBaselineByFraction':0.15,
    },'readiness gate drift')
    req(m.get('eligibilityRule')=='CANDIDATE_MUST_PASS_ALL_TRAINING_ONLY_READINESS_GATES','eligibility drift')
    req(m.get('noEligibleCandidateOutcome')=='NO_V2_CANDIDATE_PASSES_TRAINING_ONLY_READINESS_NO_ALL44_FINAL_FIT','no-candidate outcome drift')
    f=p.get('futureTrainingExecution') or {}
    req(f.get('authorizedOnThisReviewPullRequest') is False and f.get('separatePostMergeImplementationReviewRequired') is True and f.get('separatePostImplementationActivationRequired') is True,'fit review boundary drift')
    req(f.get('activationMayReadOrdinal22Artifact') is False and f.get('activationMayPerformChangedModelFits') is True and f.get('activationMustStopWithoutFinalFitIfNoCandidateEligible') is True,'activation boundary drift')
    v=p.get('futureValidationBoundary') or {}
    req(v.get('supportOodFrozenByThisProtocol') is False and v.get('numericalDefinitionOfDoneFrozenByThisProtocol') is False and v.get('separatePostTrainingFreezeRequiredBeforeAnyValidation') is True and v.get('protectedValidationAuthorized') is False and v.get('untouchedValidationValuesMayBeOpened') is False,'validation boundary drift')
    a=p.get('absoluteBoundaries') or {}
    for k in ('newMysticSolverExecutionAuthorized','ordinal22ProtectedValuesUsableForSelection','protectedValidationAuthorized','productionPromotionAuthorized','workerBLaneReactivated','workerCLaneReactivated'):
        req(a.get(k) is False,f'absolute boundary opened: {k}')

def physical(g: dict) -> tuple[float,...]:
    s=(float(g['sunDepressionDeg'])-2.0)/8.5
    a=math.sin(math.radians(float(g['targetAltitudeDeg'])))
    c=math.cos(math.radians(float(g['relativeAzimuthDeg'])))
    e=float(g['observerElevationM'])/2500.0
    o=math.log(float(g['aod550'])/0.05)/math.log(8.0)
    return s,a,c,e,o

def rawcos(g: dict) -> tuple[float,...]:
    s=(float(g['sunDepressionDeg'])-2.0)/8.5
    a=(float(g['targetAltitudeDeg'])-5.0)/75.0
    c=math.cos(math.radians(float(g['relativeAzimuthDeg'])))
    e=float(g['observerElevationM'])/2500.0
    o=(float(g['aod550'])-0.05)/0.35
    return s,a,c,e,o

def basis_terms(name: str,g:dict) -> list[float]:
    if name=='COS_COMPACT_13_TERMS':
        s,a,c,e,o=rawcos(g); return [1,s,a,c,e,o,s*s,a*a,c*c,s*a,s*c,s*o,a*c]
    s,a,c,e,o=physical(g)
    if name=='PHYSICAL_COMPACT_16_TERMS': return [1,s,a,c,e,o,s*s,a*a,c*c,o*o,s*a,s*c,s*o,a*c,a*o,c*o]
    if name=='PHYSICAL_COMPACT_16_PLUS_S_A_O_CUBICS_19_TERMS': return [1,s,a,c,e,o,s*s,a*a,c*c,o*o,s*a,s*c,s*o,a*c,a*o,c*o,s**3,a**3,o**3]
    if name=='FULL_DEGREE2_ON_FIVE_PHYSICAL_COORDINATES_21_TERMS':
        v=(s,a,c,e,o); out=[1,*v]
        for i in range(5):
            for j in range(i,5): out.append(v[i]*v[j])
        return out
    raise Refusal('unknown basis')

def selftest() -> None:
    g={'sunDepressionDeg':6.0,'targetAltitudeDeg':35.0,'relativeAzimuthDeg':73.0,'observerElevationM':900.0,'aod550':0.16}
    for _,name,n,_ in FAMILIES:
        x=basis_terms(name,g)
        req(len(x)==n and all(math.isfinite(v) for v in x),f'basis selftest failed: {name}')
    print('SELFTEST_OK')

def main() -> None:
    ap=argparse.ArgumentParser(); ap.add_argument('command',choices=['validate','selftest']); ap.add_argument('--protocol',type=Path)
    a=ap.parse_args()
    if a.command=='selftest': selftest(); return
    req(a.protocol is not None,'--protocol required'); validate(load(a.protocol)); print('VALID_PREFIT_FREEZE')

if __name__=='__main__': main()
