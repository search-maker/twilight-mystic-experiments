#!/usr/bin/env python3
from __future__ import annotations
import argparse, copy, hashlib, json
from pathlib import Path
from typing import Any

IMPL_ID='public-tier2-v1-core-stage1-authorization-implementation-v1'
GOV='MYSTIC-STATE-0067'
STATUS='REVIEW_ONLY_STAGE1_AUTHORIZATION_IMPLEMENTATION_NO_AUTHORIZATION_NO_SCIENCE'
MAIN='3b5cf241b72be90d8908f7b1fc72b7fcd799ec8d'
CONTRACT_SHA='5043929fdf13aaf90c9face0c380b514999a52a7226079807969a74469764f93'
CONTRACT_BLOB='dc69f67829cf7412e8e9374f005d92842bd500ca'
REPLAY_SHA='ea682afb1c5f1e1f18cdca1c2bc61be2701f9364dabbc6a9723d9ffc6e48349d'
REPLAY_BLOB='4dd550f6a9b31c3a67a213feb51a4209a0b25f40'
TRAIN_CASE_SHA='8651ec7e9b430c418cc5717afa221513e2a4ebff55f2caefddf8730c20a1ee89'
TRAIN_SEED_SHA='a5905c464fee13dc388ca57310f29fcd97379f7974a71cd50d745abe096b61ad'
TRAIN_IDS=['train-0052','train-0054','train-0056','train-0058','train-0062','train-0064','train-0066','train-0068','train-0072','train-0074','train-0076','train-0078','train-0082','train-0084','train-0086','train-0088','train-0092','train-0094','train-0096']
HOLD_IDS=['train-0050','train-0060','train-0065','train-0070','train-0080','train-0090']
SELF_PATHS=[
 'review/tier2-core-campaign-contract-v1/tier2-core-campaign-contract-v1.json',
 'review/tier2-core-campaign-contract-v1/validate_tier2_core_campaign_contract_v1.py',
 'review/tier2-stage1-authorization-implementation-v1/tier2-stage1-authorization-implementation-v1.json',
 'review/tier2-stage1-authorization-implementation-v1/validate_tier2_stage1_authorization_implementation_v1.py']

class Refusal(RuntimeError): pass
def req(c:bool,m:str)->None:
    if not c: raise Refusal(m)
def canon(v:Any)->bytes: return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def selfhash(d:dict[str,Any])->str:
    x=copy.deepcopy(d); x['implementationSha256']=None; return hashlib.sha256(canon(x)).hexdigest()
def ri(i:int,b:int)->float:
    r=0.0; f=1.0/b
    while i:
        i,d=divmod(i,b); r+=d*f; f/=b
    return r
def expected_geometry(i:int)->dict[str,Any]:
    g={'geometryId':f'train-{i:04d}','sourceIndex':i}
    specs=[('sunDepressionDeg',2,2.0,18.0),('targetAltitudeDeg',3,5.0,80.0),('relativeAzimuthDeg',5,0.0,180.0),('observerElevationM',7,0.0,2500.0),('aod550',11,0.05,0.4)]
    for k,b,lo,hi in specs:g[k]=round(lo+(hi-lo)*ri(i,b),6)
    role='protected-holdout' if i%5==0 else 'surrogate-training'; g['role']=role
    g['executionStage']='PROTECTED_HOLDOUT_AFTER_MODEL_FREEZE' if role=='protected-holdout' else 'TRAINING_ACQUISITION'
    sun=g['sunDepressionDeg']; alt=g['targetAltitudeDeg']; aod=g['aod550']
    g['photonHistoriesPerBlock']=20_000_000 if sun<=8 else 50_000_000
    g['alisSpectralImportanceSamplingNm']=600.0 if sun>=10 and alt<=20 else 500.0 if sun>=10 and alt>=35 and aod>=0.25 else 550.0
    return g
def expected_geometries()->list[dict[str,Any]]:
    return [g for i in range(49,97) if (g:=expected_geometry(i))['sunDepressionDeg']<=10.5]
def expected_cases()->list[dict[str,Any]]:
    seed=1_900_000_001; out=[]
    for g in sorted(expected_geometries(),key=lambda x:x['geometryId']):
        for block in range(1,5):
            out.append({'caseId':f"tier2-core-v1-{g['geometryId']}-b{block}",'geometryId':g['geometryId'],'role':g['role'],'executionStage':g['executionStage'],'block':block,'seed':seed,'photonHistories':g['photonHistoriesPerBlock'],'alisSpectralImportanceSamplingNm':g['alisSpectralImportanceSamplingNm'],'scientificValuesReadableBeforeRequiredFreeze':False if g['role']=='protected-holdout' else True}); seed+=1
    return out

def validate(d:dict[str,Any])->None:
    req(d.get('schemaVersion')==1 and d.get('implementationId')==IMPL_ID,'identity')
    req(d.get('governance')==GOV and d.get('status')==STATUS,'status')
    req(d.get('implementationSha256')==selfhash(d),'selfhash')
    s=d.get('sourceBindings') or {}
    req(s=={
      'liveMainAtFreeze':MAIN,
      'tier2CoreCampaignContractPath':'review/tier2-core-campaign-contract-v1/tier2-core-campaign-contract-v1.json',
      'tier2CoreCampaignContractSha256':CONTRACT_SHA,
      'tier2CoreCampaignContractGitBlobSha':CONTRACT_BLOB,
      'artifactReplayResultPath':'review/artifact-pipeline-replay-result-v1/artifact-pipeline-replay-result-v1.json',
      'artifactReplayResultSha256':REPLAY_SHA,
      'artifactReplayResultGitBlobSha':REPLAY_BLOB,
      'artifactReplayGateStatus':'SATISFIED_BY_REVIEWED_EXISTING_ARTIFACT_REPLAY',
      'latestConsumedScientificOrdinal':18},'source bindings')
    cases=expected_cases(); train=[c for c in cases if c['role']=='surrogate-training']; hold=[c for c in cases if c['role']=='protected-holdout']
    sc=d.get('stage1Scope') or {}
    req(sc.get('stageId')=='TRAINING_ACQUISITION','stage id')
    req(sc.get('trainingGeometryCount')==19 and sc.get('trainingCaseCount')==76 and sc.get('configuredPhotonHistories')==2_120_000_000,'stage counts')
    req(sc.get('trainingGeometryIds')==TRAIN_IDS,'training ids')
    req(sc.get('derivedTrainingCaseManifestSha256')==TRAIN_CASE_SHA==hashlib.sha256(canon(train)).hexdigest(),'training case hash')
    req(sc.get('derivedTrainingSeedLedgerSha256')==TRAIN_SEED_SHA==hashlib.sha256(canon([{'caseId':c['caseId'],'seed':c['seed']} for c in train])).hexdigest(),'training seed hash')
    req(sc.get('protectedHoldoutGeometryCountExcluded')==6 and sc.get('protectedHoldoutCaseCountExcluded')==24 and sc.get('protectedHoldoutGeometryIds')==HOLD_IDS,'holdout exclusion')
    req(sc.get('protectedHoldoutValuesReadable') is False and sc.get('protectedHoldoutExecutionAuthorized') is False,'holdout closed')
    req(len(train)==76 and len(hold)==24 and not ({c['seed'] for c in train}&{c['seed'] for c in hold}),'case split')
    a=d.get('seedCollisionReviewAudit') or {}
    req(a.get('status')=='REVIEW_TIME_NEGATIVE_COLLISION_CHECK_REQUIRES_EXACT_HEAD_RECHECK_BEFORE_AUTHORIZATION','audit status')
    req((a.get('candidateLedgerFirstSeed'),a.get('candidateLedgerLastSeed'),a.get('candidateLedgerSeedCount'))==(1_900_000_001,1_900_000_100,100),'candidate ledger range')
    req(a.get('assignmentRule')=='ASCENDING_GEOMETRY_ID_THEN_BLOCK_1_TO_4' and a.get('stage1SeedCount')==76 and a.get('reservedStage2SeedCount')==24,'seed assignment')
    req(a.get('selfLedgerMatchesIgnored') is True and a.get('allowedTrackedSelfLedgerPaths')==SELF_PATHS,'self-ledger paths')
    snap=a.get('prepublicationSearchSnapshot') or {}
    req(snap.get('repositoryMainSha')==MAIN and snap.get('repositoryCodePrefixQuery')=='1900000','search snapshot identity')
    req(snap.get('repositoryCodeMatchedPaths')==SELF_PATHS[:2] and snap.get('repositoryCodeExternalMatchCount')==0,'code collision snapshot')
    req(snap.get('pullRequestQuery')=='1900000' and snap.get('pullRequestSelfLedgerNumbers')==[144] and snap.get('pullRequestExternalMatchCount')==0,'PR collision snapshot')
    req(snap.get('issue60LogicalSelfLedgerMatchCount')==1 and snap.get('issue60ExternalMatchCount')==0 and snap.get('branchNamePrefixMatchCount')==0,'ledger/branch snapshot')
    req(a.get('trackedTreeExactHeadScanRequiredInReviewCI') is True and a.get('numericLiteralUnderscoreNormalizationRequired') is True,'tracked tree audit')
    req(a.get('rawArtifactBytesDirectlyScannedByThisReviewAudit') is False,'artifact-byte claim')
    req(a.get('knownArtifactSeedIdentityClosureMustBeRecheckedImmediatelyBeforeAuthorization') is True and a.get('repositoryGlobalDuplicateRunSeedProvenanceGuardRequiredImmediatelyBeforeAuthorization') is True,'preauth duplicate guard')
    req(a.get('authorizationPermittedByThisReviewAudit') is False,'audit authorization boundary')
    req(a.get('collisionOutcome')=='REFUSE_AUTHORIZATION_AND_VERSION_A_NEW_SEED_LEDGER_AND_CAMPAIGN_CONTRACT','collision outcome')
    lim=a.get('limitations'); req(isinstance(lim,list) and len(lim)==3,'audit limitations')
    auth=d.get('authorizationTemplate') or {}
    req(auth.get('templateOnly') is True and auth.get('enabled') is False,'template state')
    for k in ['campaignAuthorizationIssued','scientificExecutionAuthorized','workflowDispatchEnabled','campaignDispatchIssued','solverExecutionPerformed','modelFittingAuthorized','modelSelectionAuthorized','protectedHoldoutOpeningAuthorized','productionPromotionAuthorized','train0037ExecutionAuthorized']:
        req(auth.get(k) is False,f'closed authorization field {k}')
    for k in ['scientificOrdinal','authorizationRef','executionKey','dispatchBranch']:
        req(auth.get(k) is None,f'unallocated identity field {k}')
    nb=d.get('nextBoundary') or {}
    req(nb=={
      'nextAllowedWork':'REVIEW_AND_MERGE_IMPLEMENTATION_THEN_SEPARATE_STAGE1_AUTHORIZATION_IDENTITY_TRANSITION_IF_ALL_GATES_STILL_PASS',
      'separateAuthorizationTransitionRequired':True,
      'freshSeedAndIdentityCollisionAuditRequiredAtAuthorizationHead':True,
      'completeRunHistoryArtifactDuplicateGuardRequiredAtAuthorizationHead':True,
      'ordinal19AllocationAllowedByThisImplementation':False,
      'scientificExecutionAutomaticAfterMerge':False,
      'campaignDispatchAutomaticAfterMerge':False,
      'modelFittingAllowedByThisImplementation':False,
      'protectedHoldoutOpeningAllowedByThisImplementation':False,
      'stage2RemainsClosed':True},'next boundary')

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('--review',required=True);a=ap.parse_args()
    try:
        d=json.loads(Path(a.review).read_text(encoding='utf-8')); validate(d); print('TIER2_STAGE1_AUTHORIZATION_IMPLEMENTATION_VALID'); return 0
    except Exception as e:
        print(f'REFUSED: {e}'); return 2
if __name__=='__main__': raise SystemExit(main())
