#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,subprocess
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
TRANSPORT=HERE/'transport-v1.json'
def req(c:bool,m:str)->None:
    if not c: raise SystemExit('REFUSED: '+m)
def load(p:Path)->dict[str,Any]:
    x=json.loads(p.read_text(encoding='utf-8')); req(isinstance(x,dict),f'object required: {p}'); return x
def blob(p:str)->str:return subprocess.check_output(['git','rev-parse','HEAD:'+p],cwd=ROOT,text=True).strip()
def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('--require-review-inert',action='store_true');args=ap.parse_args();t=load(TRANSPORT)
    req((t['schemaVersion'],t['transportId'],t['status'],t['governance'])==(1,'level-b-v2-densified58-fresh-validation-ordinal25-transport-v1','REVIEW_ONLY_ORDINAL25_AUTHORIZATION_AND_ONE_SHOT_DISPATCH_TRANSPORT_NO_ALLOCATION','MYSTIC-STATE-0070'),'transport identity drift')
    req(t['sourceMainAtTransportFreeze']=='3ca85e69442eaa0454feb5e4fae54a58e0773a23','source main drift')
    b=t['recoveryBindings'];expected={
      b['recoveryPath']:'25d6783197d3b5334a277828ce133adaae9d98a3',b['contractPath']:'1370e53bd33cff442be9c4525e7a7dcb7710084f',b['evaluatorPath']:'a1f81d88fb9099a1b269de598067f7a9e7109537',b['manifestBuilderPath']:'6a27b9f3a54c079d6ce864c8cd1938f2f9ee83a5',b['executorPath']:'661f3c3bf4fef94c46eca096fd059f1a124a8e3c',b['adapterPath']:'5cd736d78c5b82d124b5b95548063677dbfe0ce9',b['baseExecutorPath']:'5bf0477f0d5100dcb73da8027233e8415ce9021c'}
    for p,w in expected.items():req(blob(p)==w,f'blob drift: {p}')
    req((b['recoveryGitBlobSha'],b['contractGitBlobSha'],b['evaluatorGitBlobSha'],b['manifestBuilderGitBlobSha'],b['executorGitBlobSha'],b['adapterGitBlobSha'],b['baseExecutorGitBlobSha'])==tuple(expected[p] for p in [b['recoveryPath'],b['contractPath'],b['evaluatorPath'],b['manifestBuilderPath'],b['executorPath'],b['adapterPath'],b['baseExecutorPath']]),'binding field drift')
    req((b['modelSha256'],b['modelArtifactId'],b['representationPackageSha256'],b['representationArtifactId'])==('91ae5811e55b3d4ef872ab672f006c4b383c6581a53de67cd018b6eb2666f9a7',9229229366,'2491ac91ed924f2ba69b37ea20f48d63f51d41146cd9fe50e0bd63bfb315a763',9208203541),'model/representation drift')
    p=t['ordinal24ImmutableRefusal'];req((p['authorizationHeadSha'],p['authorizationPullRequest'],p['authorizationReviewRunId'],p['allocationMarkerCommentId'],p['dispatchRunId'],p['dispatchRunAttempt'],p['dispatchRunConclusion'])==('520ff3cc5f8fee2defc1a0a950bfa7a40974479c',194,31840635840,5298149901,31840757436,1,'failure'),'ordinal24 refusal drift');req(p['preflightConclusion']=='success' and p['caseJobCount']==24 and p['terminalCaseFailureCount']==24 and p['evaluationConclusion']=='skipped' and p['syntaxCheckCount']==0 and p['solverExecutionCount']==0 and p['protectedValuesRead'] is False and p['scientificIdentityConsumed'] is True and p['retiredSeeds']==list(range(2101000001,2101000025)),'ordinal24 refusal accounting drift')
    s=t['scientificIdentity'];req((s['scientificOrdinal'],s['authorizationBranch'],s['dispatchBranch'],s['executionKey'])==(25,'authorization/level-b-v2-densified58-fresh-validation-ordinal25-v1','dispatch/level-b-v2-densified58-fresh-validation-ordinal25-v1','level-b-v2-densified58:fresh-protected-validation:25'),'ordinal25 identity drift');req(s['reservedSeeds']==list(range(2101000025,2101000049)) and s['allocatedAtTransportReview'] is False and s['consumedAtTransportReview'] is False,'ordinal25 seeds/allocation drift')
    e=t['executionContract'];req((e['geometryCount'],e['blocksPerGeometry'],e['caseCount'],e['photonHistoriesPerBlock'],e['configuredPhotonHistories'],e['maxParallel'])==(6,4,24,40000000,960000000,24),'execution accounting drift');req(e['exactAllowedDispatchBranch']==s['dispatchBranch'],'executor/dispatch mismatch');req(e['oneSyntaxCheckPerCase'] and e['oneSolverInvocationPerCase'] and e['workflowRunAttemptExactly']==1 and e['githubRerunAllowed'] is False and e['retryAllowed'] is False and e['resumeAllowed'] is False and e['evaluationOnlyAfterAllCasesSucceed'] and e['scientificFailureDoesNotFailOperationalEvaluationJob'],'execution semantics drift')
    a=t['authorizationContract'];req(a['authorizationPath']=='review/level-b-v2-densified58-fresh-validation-ordinal25-transport-v1/authorization.json' and a['authorizationMustBeExactlyOneNewFile'] and a['authorizationCommitMustBeDirectChildOfLiveMain'] and a['authorizationPullRequestMustRemainDraftAndUnmergedThroughDispatch'] and a['authorizationReviewRunAttemptExactly']==1 and a['prContextHeadIdentitySource']=='git rev-parse HEAD' and a['frozenNumericalDependency']=='numpy==2.3.2' and a['automaticDispatch'] is False and a['allocationMarkerMayBeWrittenOnlyAfterSuccessfulAuthorizationReview'] and a['dispatchBranchMayBeCreatedOnlyAfterAllocationMarker'],'authorization semantics drift')
    req(all(v is False for v in t['reviewSurface'].values()),'review surface opened')
    if args.require_review_inert:req(not (ROOT/a['authorizationPath']).exists(),'authorization present during transport review')
    print(json.dumps({'status':'PASS','scientificOrdinal':25,'authorizationBranch':s['authorizationBranch'],'dispatchBranch':s['dispatchBranch'],'reservedSeedCount':24,'protectedValuesRead':False,'scientificSolverExecutionAuthorizedByTransportReview':False},sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
