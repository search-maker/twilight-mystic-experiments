#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,subprocess
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[2]
T=Path(__file__).resolve().parent/'transport-v3.json'
def req(c:bool,m:str)->None:
    if not c: raise SystemExit('REFUSED: '+m)
def load(p:Path)->dict[str,Any]:
    x=json.loads(p.read_text());req(isinstance(x,dict),f'object required: {p}');return x
def blob(path:str)->str:return subprocess.check_output(['git','rev-parse','HEAD:'+path],cwd=ROOT,text=True).strip()
def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('--require-review-inert',action='store_true');a=ap.parse_args();t=load(T)
    req((t['schemaVersion'],t['transportId'],t['governance'])==(3,'level-b-v2-densified58-fresh-validation-transport-v3','MYSTIC-STATE-0070'),'identity drift')
    req(t['status']=='REVIEW_ONLY_AUTHORIZATION_V3_AND_DISPATCH_V3_TRANSPORT_NO_AUTHORIZATION_FILE_NO_ALLOCATION','status drift')
    req(t['sourceMainAtTransportFreeze']=='1bd08afa723bb8756e1087b1481b2d0df1908084','source main drift')
    b=t['sourceBindings']; expected={b['priorTransportV2Path']:'200c79c646570442c25266a09a72725f768e7892',b['freshValidationContractPath']:'aad11350311ce3768488e64ed72edc3e48646ff9',b['implementationContractPath']:'34e797346e937c4d1164b61cd2cc7197213aa97a',b['evaluatorPath']:'085f040caa6aec53aace00381035115358b21239',b['manifestBuilderPath']:'5972fed72f38a7375251b80d841fb872c2008035',b['adapterPath']:'5cd736d78c5b82d124b5b95548063677dbfe0ce9',b['executorPath']:'5bf0477f0d5100dcb73da8027233e8415ce9021c'}
    for p,w in expected.items():req(blob(p)==w,f'blob drift: {p}')
    req((b['priorTransportV2GitBlobSha'],b['freshValidationContractGitBlobSha'],b['implementationContractGitBlobSha'],b['evaluatorGitBlobSha'],b['manifestBuilderGitBlobSha'],b['adapterGitBlobSha'],b['executorGitBlobSha'])==(expected[b['priorTransportV2Path']],expected[b['freshValidationContractPath']],expected[b['implementationContractPath']],expected[b['evaluatorPath']],expected[b['manifestBuilderPath']],expected[b['adapterPath']],expected[b['executorPath']]),'source binding drift')
    req((b['modelArtifactId'],b['modelCanonicalSha256'],b['representationArtifactId'],b['representationPackageSha256'])==(9229229366,'91ae5811e55b3d4ef872ab672f006c4b383c6581a53de67cd018b6eb2666f9a7',9208203541,'2491ac91ed924f2ba69b37ea20f48d63f51d41146cd9fe50e0bd63bfb315a763'),'model/representation drift')
    rs=t['priorAuthorizationRefusals'];req(len(rs)==2 and [x['authorizationVersion'] for x in rs]==[1,2],'refusal version drift')
    req((rs[0]['authorizationCommitSha'],rs[0]['pullRequest'],rs[0]['authorizationReviewRunId'],rs[0]['reason'])==('1cefb761f0ec57059da0dbdfe2229d0fd0ab8e9b',190,31838796101,'MISSING_NUMPY_DEPENDENCY_BEFORE_MANIFEST_BUILD'),'v1 refusal drift')
    req((rs[1]['authorizationCommitSha'],rs[1]['pullRequest'],rs[1]['authorizationReviewRunId'],rs[1]['reason'])==('3d35ea42d89fdf6f1b013ed7cc5c3a1b10b99a7f',192,31839703495,'PULL_REQUEST_GITHUB_SHA_MERGE_REF_USED_INSTEAD_OF_CHECKED_OUT_AUTHORIZATION_HEAD'),'v2 refusal drift')
    req(all(x['allocationMarkerWritten'] is False and x['dispatchBranchCreated'] is False and x['protectedValuesRead'] is False and x['scientificSolverExecutionPerformed'] is False and x['authorizationIdentityMayBeReused'] is False for x in rs),'refusal boundary drift')
    s=t['scientificIdentity'];req((s['scientificOrdinal'],s['authorizationBranch'],s['dispatchBranch'],s['executionKey'])==(24,'authorization/level-b-v2-densified58-fresh-validation-ordinal24-v3','dispatch/level-b-v2-densified58-fresh-validation-ordinal24-v3','level-b-v2-densified58:fresh-protected-validation:24'),'current identity drift');req(s['reservedSeeds']==list(range(2101000001,2101000025)),'seed drift');req(s['allocatedAtTransportReview'] is False and s['consumedAtTransportReview'] is False,'allocation drift')
    ac=t['authorizationContract'];req(ac['authorizationPath']=='review/level-b-v2-densified58-fresh-validation-transport-v3/authorization.json','auth path drift');req(ac['frozenNumericalDependency']=='numpy==2.3.2','numpy drift');req(ac['prContextHeadIdentitySource']=='git rev-parse HEAD' and ac['pullRequestGithubShaMayBeUsedAsAuthorizationHead'] is False,'PR head identity rule drift')
    req(ac['authorizationMustBeExactlyOneNewFile'] and ac['authorizationCommitMustBeDirectChildOfLiveMain'] and ac['authorizationPullRequestMustRemainDraftAndUnmergedThroughDispatch'] and ac['authorizationReviewRunAttemptExactly']==1 and ac['automaticDispatch'] is False,'auth sequencing drift')
    d=t['dispatchContract'];req((d['geometryCount'],d['caseCount'],d['configuredPhotonHistories'],d['maxParallel'])==(6,24,960000000,24),'dispatch accounting drift');req(d['dispatchHeadMustExactlyEqualAuthorizationHead'] and d['oneMatchingAllocationMarkerRequired'] and d['oneSyntaxCheckPerCase'] and d['oneSolverInvocationPerCase'] and d['evaluationRunsOnlyAfterAllCaseJobsSucceed'] and d['scientificFailureDoesNotFailOperationalWorkflow'],'dispatch rules weakened');req(d['githubRerunAllowed'] is False and d['retryAllowed'] is False and d['resumeAllowed'] is False and d['dispatchRunAttemptExactly']==1,'dispatch continuation opened')
    req(all(v is False for v in t['reviewSurface'].values()),'review surface opened');req(all(v is False for v in t['closedBoundaries'].values()),'closed boundary opened')
    auth=ROOT/ac['authorizationPath']
    if a.require_review_inert:req(not auth.exists(),'authorization present during transport-v3 review')
    print(json.dumps({'status':'PASS','scientificOrdinal':24,'authorizationBranch':s['authorizationBranch'],'dispatchBranch':s['dispatchBranch'],'priorRefusalCount':2,'authorizationV3FilePresent':auth.exists(),'protectedValuesRead':False,'scientificSolverExecutionAuthorizedByTransportReview':False},sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
