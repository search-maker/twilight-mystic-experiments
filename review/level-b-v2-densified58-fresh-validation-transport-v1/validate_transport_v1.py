#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
TRANSPORT=HERE/'transport-v1.json'
AUTH_PATH=HERE/'authorization.json'
CONTRACT=ROOT/'review/level-b-v2-densified58-fresh-validation-v1/contract-v1.json'
IMPL=ROOT/'review/level-b-v2-densified58-fresh-validation-implementation-v1/implementation-v1.json'
EVAL=ROOT/'review/level-b-v2-densified58-fresh-validation-implementation-v1/fresh_validation_v1.py'
MANIFEST=ROOT/'experiments/level-b-v2-densified58-fresh-validation-v1/build_manifest_v1.py'
ADAPTER=ROOT/'experiments/level-b-v2-densified58-fresh-validation-v1/adapter_v1.py'
EXECUTOR=ROOT/'experiments/level-b-v2-densified58-fresh-validation-v1/executor_v1.py'
MODEL_RESULT=ROOT/'review/level-b-v2-training-fit-result-v3-densified58/result-v3.json'
REVIEW_WF=ROOT/'.github/workflows/level-b-v2-densified58-fresh-validation-transport-v1.yml'
AUTH_WF=ROOT/'.github/workflows/level-b-v2-densified58-fresh-validation-authorization-review-v1.yml'
EXEC_WF=ROOT/'.github/workflows/level-b-v2-densified58-fresh-validation-execution-v1.yml'
EXPECTED={
 CONTRACT:'aad11350311ce3768488e64ed72edc3e48646ff9',
 IMPL:'34e797346e937c4d1164b61cd2cc7197213aa97a',
 EVAL:'085f040caa6aec53aace00381035115358b21239',
 MANIFEST:'5972fed72f38a7375251b80d841fb872c2008035',
 ADAPTER:'5cd736d78c5b82d124b5b95548063677dbfe0ce9',
 EXECUTOR:'5bf0477f0d5100dcb73da8027233e8415ce9021c',
 MODEL_RESULT:'28ff90afa0de1734aa0b6718bc93ebdce1ded54a',
}
AUTH_BRANCH='authorization/level-b-v2-densified58-fresh-validation-ordinal24-v1'
DISPATCH_BRANCH='dispatch/level-b-v2-densified58-fresh-validation-ordinal24-v1'
AUTH_REL='review/level-b-v2-densified58-fresh-validation-transport-v1/authorization.json'

def req(c,m):
    if not c: raise SystemExit('REFUSED: '+m)
def blob(path): return subprocess.check_output(['git','rev-parse','HEAD:'+str(path.relative_to(ROOT))],cwd=ROOT,text=True).strip()
def load(path):
    x=json.loads(path.read_text()); req(isinstance(x,dict),f'object required: {path}'); return x

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--require-review-inert',action='store_true'); a=ap.parse_args()
    t=load(TRANSPORT); c=load(CONTRACT); i=load(IMPL); r=load(MODEL_RESULT)
    req((t.get('schemaVersion'),t.get('transportId'),t.get('status'),t.get('governance'))==(1,'level-b-v2-densified58-fresh-validation-transport-v1','REVIEW_ONLY_AUTHORIZATION_AND_DISPATCH_TRANSPORT_NO_AUTHORIZATION_FILE_NO_ALLOCATION','MYSTIC-STATE-0070'),'transport identity drift')
    req(t.get('sourceMainAtTransportFreeze')=='e2beca0293114179fc06be7e9f564738b7d5087a','transport source-main drift')
    for path,want in EXPECTED.items(): req(blob(path)==want,f'git blob drift: {path}')
    sb=t['sourceBindings']
    req(sb['freshValidationContractGitBlobSha']==EXPECTED[CONTRACT] and sb['implementationContractGitBlobSha']==EXPECTED[IMPL] and sb['evaluatorGitBlobSha']==EXPECTED[EVAL],'core binding drift')
    req(sb['manifestBuilderGitBlobSha']==EXPECTED[MANIFEST] and sb['adapterGitBlobSha']==EXPECTED[ADAPTER] and sb['executorGitBlobSha']==EXPECTED[EXECUTOR],'transport-code binding drift')
    req(sb['trainingModelResultGitBlobSha']==EXPECTED[MODEL_RESULT] and sb['modelCanonicalSha256']=='91ae5811e55b3d4ef872ab672f006c4b383c6581a53de67cd018b6eb2666f9a7','model binding drift')
    req((sb['modelArtifactId'],sb['representationArtifactId'])==(9229229366,9208203541),'artifact identity drift')
    req(sb['representationPackageSha256']=='2491ac91ed924f2ba69b37ea20f48d63f51d41146cd9fe50e0bd63bfb315a763','representation binding drift')
    sid=t['scientificIdentity']; req((sid['scientificOrdinal'],sid['authorizationBranch'],sid['dispatchBranch'])==(24,AUTH_BRANCH,DISPATCH_BRANCH),'scientific identity drift')
    req(sid['reservedSeeds']==list(range(2101000001,2101000025)),'reserved seeds drift')
    req(sid['allocationMarkerPrefix']=='ALLOCATED-SCIENCE-IDENTITY | MYSTIC-STATE-0070 | ordinal=24 | authHead=' and sid['allocationMarkerSeedSuffix']==' | seeds=2101000001-2101000024','allocation marker format drift')
    req(sid['allocatedAtTransportReview'] is False and sid['consumedAtTransportReview'] is False,'transport review allocated/consumed identity')
    ac=t['authorizationContract']; req(ac['authorizationPath']==AUTH_REL and ac['authorizationMustBeExactlyOneNewFile'] is True and ac['authorizationCommitMustBeDirectChildOfLiveMain'] is True,'authorization shape drift')
    req(ac['authorizationPullRequestMustRemainDraftAndUnmergedThroughDispatch'] is True and ac['authorizationReviewRunAttemptExactly']==1 and ac['automaticDispatch'] is False,'authorization review semantics drift')
    expected=ac['authorizationJsonExpected']; req(expected['scientificOrdinal']==24 and expected['runAttemptRequired']==1 and expected['scientificExecutionAuthorized'] is True and expected['protectedValidationAuthorized'] is True and expected['protectedValuesMayBeRead'] is True,'authorization expected semantics drift')
    for k in ('githubRerunAllowed','retryAllowed','resumeAllowed','modelRetuningAuthorized','productionPromotionAuthorized','workerBLaneReactivated','workerCLaneReactivated'): req(expected[k] is False,f'authorization expected boundary opened: {k}')
    dc=t['dispatchContract']; req((dc['caseCount'],dc['geometryCount'],dc['configuredPhotonHistories'],dc['maxParallel'])==(24,6,960000000,24),'dispatch accounting drift')
    req(dc['dispatchHeadMustExactlyEqualAuthorizationHead'] is True and dc['dispatchRunAttemptExactly']==1 and dc['oneMatchingAllocationMarkerRequired'] is True,'dispatch identity guard drift')
    for k in ('githubRerunAllowed','retryAllowed','resumeAllowed'): req(dc[k] is False,f'dispatch continuation opened: {k}')
    fs=t['freshnessSemantics']; req(fs['preregistrationAndTransportMentionsDoNotAllocateOrConsumeOrdinalOrSeeds'] is True and fs['allocationRequiresExactIssue60AllocationMarker'] is True and fs['consumptionRequiresExactDispatchIdentityRun'] is True,'freshness semantics drift')
    for k,v in t['closedBoundaries'].items(): req(v is False,f'closed transport boundary opened: {k}')
    req(c['executionEnvelope']['candidateScientificOrdinal']==24 and c['executionEnvelope']['scientificOrdinalAllocated'] is False and c['executionEnvelope']['reservedSeeds']==sid['reservedSeeds'],'prereg scientific identity drift')
    req(c['boundaries']['protectedValidationAuthorized'] is False and c['boundaries']['scientificSolverExecutionAuthorized'] is False,'prereg boundary drift')
    req(i['futureAuthorization']['protectedValidationAuthorizedNow'] is False and i['futureAuthorization']['scientificSolverExecutionAuthorizedNow'] is False,'implementation boundary drift')
    req(r['scientificBoundaries']['protectedValidationAuthorized'] is False and r['scientificBoundaries']['newMysticSolverExecutionAuthorized'] is False,'training result boundary drift')
    for wf in (REVIEW_WF,AUTH_WF,EXEC_WF): req(wf.is_file(),f'missing workflow: {wf}')
    rt=REVIEW_WF.read_text(); at=AUTH_WF.read_text(); et=EXEC_WF.read_text()
    trigger_headers=[text.split('jobs:',1)[0] for text in (rt,at,et)]
    req(all('workflow_dispatch:' not in header and '\nschedule:' not in header for header in trigger_headers),'manual/scheduled trigger introduced')
    req(AUTH_BRANCH in at and 'pull_request:' in at and 'push:' not in at.split('jobs:',1)[0],'authorization workflow trigger drift')
    req(DISPATCH_BRANCH in et and 'push:' in et.split('jobs:',1)[0] and 'pull_request:' not in et.split('jobs:',1)[0],'execution workflow trigger drift')
    req(AUTH_REL in at and AUTH_REL in et,'authorization path missing from future workflows')
    req('GITHUB_RUN_ATTEMPT' in at and 'GITHUB_RUN_ATTEMPT' in et,'attempt-one guard missing')
    req('allocationMarkerPrefix' in et or 'ALLOCATED-SCIENCE-IDENTITY' in et,'allocation marker guard missing from execution')
    if a.require_review_inert:
        req(not AUTH_PATH.exists(),'authorization file present during transport review')
        req(t['reviewSurface']['authorizationFilePresent'] is False and t['reviewSurface']['authorizationBranchCreatedByThisReview'] is False and t['reviewSurface']['dispatchBranchCreatedByThisReview'] is False,'review surface drift')
        req(t['reviewSurface']['scientificOrdinalAllocated'] is False and t['reviewSurface']['reservedSeedsAllocated'] is False and t['reviewSurface']['protectedValuesMayBeRead'] is False and t['reviewSurface']['scientificSolverExecutionAuthorized'] is False,'review scientific boundary opened')
    print(json.dumps({'status':'PASS','scientificOrdinal':24,'reservedSeedCount':24,'authorizationBranch':AUTH_BRANCH,'dispatchBranch':DISPATCH_BRANCH,'authorizationFilePresent':AUTH_PATH.exists(),'protectedValuesRead':False,'scientificSolverExecutionAuthorizedByTransportReview':False},sort_keys=True))
    return 0
if __name__=='__main__': raise SystemExit(main())
