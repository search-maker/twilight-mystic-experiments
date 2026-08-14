#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, math, subprocess
from pathlib import Path

TRAIN_IDS=['train-0001','train-0002','train-0004','train-0006','train-0008','train-0009','train-0012','train-0014','train-0016','train-0017','train-0018','train-0021','train-0022','train-0024','train-0026','train-0028','train-0032','train-0033','train-0034','train-0036','train-0038','train-0042','train-0044','train-0046','train-0048','train-0052','train-0054','train-0056','train-0058','train-0062','train-0064','train-0066','train-0068','train-0072','train-0074','train-0076','train-0078','train-0082','train-0084','train-0086','train-0088','train-0092','train-0094','train-0096']
OPENED=['train-0050','train-0060','train-0065','train-0070','train-0080','train-0090']
PR=[1e-5,1e-4,1e-3,1e-2,1e-1]
SR=[1e-3,1e-2,1e-1,1.0,10.0]
IDWK=[4,6,8,12]; IDWP=[1.0,2.0]
EXPECTED_RESULT_BLOB='c7ca202d55113b59369a4e74a94cc80cc47eca71'
class Refusal(RuntimeError): pass
def req(c,m):
    if not c: raise Refusal(m)
def load(p):
    x=json.loads(Path(p).read_text()); req(isinstance(x,dict),'protocol object required'); return x

def validate(p:dict, root:Path):
    req((p.get('schemaVersion'),p.get('protocolId'),p.get('status'),p.get('governance'))==(2,'level-b-v2-training-only-prefit-freeze-v2','REVIEW_ONLY_SECOND_GENERATION_PREFIT_FREEZE_NO_CHANGED_REAL_FIT','MYSTIC-STATE-0068'),'identity drift')
    req(p.get('sourceMainAtFreeze')=='124005af6407c32867c11cb7907353a4f79d14bd','source main drift')
    g1=p.get('generation1ResultBinding') or {}
    req((g1.get('path'),g1.get('gitBlobSha'),g1.get('status'),g1.get('candidateCount'),g1.get('eligibleCandidateCount'),g1.get('universalFailedGate'),g1.get('universalWorstLooShapeGeometryId'))==('review/level-b-v2-training-fit-result-v1/result-v1.json',EXPECTED_RESULT_BLOB,'TRAINING_ONLY_NO_ELIGIBLE_CANDIDATE_NO_MODEL_FROZEN',100,0,'looWorstShape','train-0021'),'generation1 binding drift')
    result_path=root/g1['path']; req(result_path.exists(),'generation1 binding missing'); blob=subprocess.check_output(['git','hash-object',str(result_path)],text=True).strip(); req(blob==EXPECTED_RESULT_BLOB,f'generation1 result blob drift: {blob}')
    req(g1.get('mayRetroactivelyPass') is False,'generation1 retroactive pass opened')
    n=p.get('trainingOnlyNoiseDiagnosis') or {}; req(n.get('source')=='EXACT_SOURCE_TRAINING_REPRESENTATION_ONLY','diagnosis source drift'); req(n.get('train0021BlockCount')==2,'diagnosis block drift'); req(abs(float(n.get('train0021NormalizedPcaStandardErrorRms'))-1.4136803125907174)<1e-15,'diagnosis rms drift'); req(abs(float(n.get('train0021MaxNormalizedPcaStandardError'))-2.437475133373817)<1e-15,'diagnosis max drift'); req(n.get('generation1RawWorstShapeGateRemainsFailed') is True,'generation1 fail semantics drift')
    s=p.get('sourceTrainingRepresentation') or {}; req((s.get('artifactId'),s.get('artifactDigest'),s.get('trainingDatasetCanonicalSha256'),s.get('trainingDatasetFileSha256'),s.get('trainingGeometryCount'),s.get('protectedRecordCount'),s.get('holdoutValuesRead'))==(9208203541,'sha256:2fe50ed674155f440322c92d28877f5c022f0cc5fa13e1e601596a9902482815','bb7908426d9d545f43c082aebbaab1829a486e2962d0b9ee34a5e8bef5390133','066d6be846fa9b3bdd7236e327894f64d52ea56aa7e7b6e6af4d51d849eb1a61',44,0,False),'training source drift'); req(len(s.get('nullspaceCoefficientScales') or [])==10 and all(float(x)>0 for x in s['nullspaceCoefficientScales']),'scale drift')
    r=p.get('roleIsolation') or {}; req(r.get('exactTrainingGeometryIds')==TRAIN_IDS,'training ids drift'); req(r.get('openedV1ProtectedDiagnosticOnlyGeometryIds')==OPENED,'opened ids drift'); req(not set(TRAIN_IDS)&set(OPENED),'role overlap'); req(r.get('openedV1ProtectedValuesAllowed') is False,'opened values admitted')
    tu=p.get('targetsAndUncertainty') or {}; req(tu.get('shapeWeightedRidgeWeight')=='1/(1+shapeNormalizedStandardError^2)','shape weight drift'); req(tu.get('uncertaintyAdjustedPerRecordShapeNrmse')=='sqrt(mean((predictionNormalized-truthNormalized)^2/(1+shapeNormalizedStandardError^2)))','UA shape metric drift'); req(tu.get('epsilonSubstitutionAllowed') is False,'epsilon opened')
    ms=p.get('modelSelection') or {}; fam=ms.get('candidateFamilies') or []; req(len(fam)==8,'family count drift'); count=0
    for i,f in enumerate(fam):
        req(f.get('complexityRank')==i+1,'complexity order drift')
        if f.get('kind')=='UNCERTAINTY_WEIGHTED_SPLIT_RIDGE':
            req(f.get('primaryRidgeValues')==PR and f.get('shapeRidgeValues')==SR,'ridge grid drift'); req(f.get('penalizeIntercept') is False,'intercept drift'); count+=len(PR)*len(SR)
        elif f.get('kind')=='RIDGE_PRIMARY_IDW_SHAPE':
            req(f.get('primaryRidgeValues')==PR and f.get('neighbors')==IDWK and f.get('powers')==IDWP,'IDW grid drift'); req(f.get('exactMatchReturnsExactTrainingShapeTarget') is True,'IDW exact match drift'); count+=len(PR)*len(IDWK)*len(IDWP)
        else: raise Refusal('unknown family kind')
    req(count==230 and ms.get('candidateCountRequired')==230,'candidate count drift')
    prov=ms.get('candidateProvenance') or {}; req(prov.get('idwHyperparametersCopiedUnchangedFromMergedV1PrefitProtocol') is True and prov.get('idwNeighbors')==IDWK and prov.get('idwPowers')==IDWP and prov.get('ordinal22PostmortemInfluence') is False,'candidate provenance drift')
    cv=ms.get('crossValidationFolds') or {}; req(cv.get('totalFoldCountRequired')==59 and cv.get('expectedBalancedFoldCounts')==[9,9,9,9,8],'CV drift'); req(cv.get('expectedBoundaryFoldCounts')=={'sun-shallow':11,'sun-deep-core':11,'az-low':8,'az-high':9,'alt-low':10,'alt-high':7,'aod-low':9,'aod-high':6,'elev-low':9,'elev-high':6},'boundary fold counts drift')
    gates=ms.get('trainingOnlyReadinessGates') or {}; req(gates=={'looMeanPrimaryMaleMax':0.25,'looWorstSinglePrimaryLogErrorMax':0.9,'looMeanRawShapeNrmseMax':1.0,'looWorstUncertaintyAdjustedShapeNrmseMax':1.45,'looWorstUncertaintyAdjustedSingleCoefficientErrorMax':3.0,'boundaryWorstPrimaryMaleMax':0.3,'boundaryWorstRawShapeNrmseMax':1.45,'looPrimaryMustBeatFoldMatchedTrainingMeanBaselineByFraction':0.15},'gate drift'); req(ms.get('rawLooWorstShapeNrmse').startswith('REPORT_ONLY_'),'raw worst semantics drift'); req(ms.get('noEligibleCandidateOutcome')=='NO_GENERATION2_CANDIDATE_PASSES_TRAINING_ONLY_READINESS_NO_ALL44_FINAL_FIT','no candidate drift')
    ni=p.get('numericalImplementation') or {}; req((ni.get('pythonVersion'),ni.get('numpyVersion'),ni.get('dtype'),ni.get('randomnessAllowed'))==('3.12','2.3.2','float64',False),'numerical drift')
    fe=p.get('futureExecution') or {}; req(fe.get('realFitAuthorizedOnThisReviewPullRequest') is False and fe.get('separateImplementationReviewRequired') is True and fe.get('separateOneUseActivationAfterMergeRequired') is True and fe.get('activationMayReadOrdinal22Artifact') is False and fe.get('protectedValidationAuthorized') is False,'execution boundary drift')
    b=p.get('closedBoundaries') or {}; req(b.get('generation1ResultRemainsFailed') is True,'generation1 state drift')
    for k in ('newMysticSolverExecutionAuthorized','ordinal22ValuesUsableForSelection','protectedValidationAuthorized','productionPromotionAuthorized','workerBLaneReactivated','workerCLaneReactivated'): req(b.get(k) is False,f'opened boundary: {k}')

def selftest(p):
    count=0
    for f in p['modelSelection']['candidateFamilies']:
        if f['kind']=='UNCERTAINTY_WEIGHTED_SPLIT_RIDGE': count+=len(f['primaryRidgeValues'])*len(f['shapeRidgeValues'])
        else: count+=len(f['primaryRidgeValues'])*len(f['neighbors'])*len(f['powers'])
    req(count==230,'selftest candidate count')
    for se in [0.0,0.5,1.0,2.5]:
        w=1/(1+se*se); req(0<w<=1 and math.isfinite(w),'weight invalid')
    print('SELFTEST_OK')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('command',choices=['validate','selftest']); ap.add_argument('--protocol',required=True); a=ap.parse_args(); p=load(a.protocol); root=Path(a.protocol).resolve().parents[2]
    if a.command=='validate': validate(p,root); print('VALID_PREFIT_V2')
    else: selftest(p)
if __name__=='__main__': main()
