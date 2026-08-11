#!/usr/bin/env python3
from __future__ import annotations
import argparse, compileall, json, os, sys
from pathlib import Path
from unittest import mock

HERE=Path(__file__).resolve().parent

def require(c:bool,m:str)->None:
    if not c: raise SystemExit(m)

def expect_refusal(fn,msg:str)->None:
    try: fn()
    except Exception: return
    raise SystemExit(msg)

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--repository-root',type=Path,required=True); a=ap.parse_args(); root=a.repository_root.resolve()
    sys.path.insert(0,str(root/'experiments/full-spectrum-estimator-pilot-v2'))
    import candidate_v8 as v8, executor
    c,b=v8.validate_static(root)
    require(c['candidateIdentity']['globalScientificOrdinal']==16,'v8 candidate ordinal drift')
    require(c['freshnessRules']['latestPriorConsumedScientificOrdinalExactly']==15,'v8 prior ordinal drift')
    p=c['priorAttempt15']
    require(p['runId']==31544203626 and p['caseJobsCreated']==44 and p['caseJobsReachedExecutor']==44,'ordinal-15 attempt binding drift')
    require(p['syntaxChecks']==0 and p['solverExecutions']==0 and p['frozenSeedsRemainUnexecuted'] is True,'ordinal-15 pre-solver evidence drift')
    require(executor.DEFAULT_EXPECTED_DISPATCH_BRANCH=='dispatch/full-spectrum-estimator-pilot-v2-ordinal14','executor legacy default drift')
    base_env={'GITHUB_ACTIONS':'true','GITHUB_EVENT_NAME':'push','GITHUB_RUN_ATTEMPT':'1'}
    with mock.patch.dict(os.environ,{**base_env,'GITHUB_REF_NAME':'dispatch/full-spectrum-estimator-pilot-v2-ordinal14'},clear=False):
        executor.validate_execution_context()
    with mock.patch.dict(os.environ,{**base_env,'GITHUB_REF_NAME':'dispatch/full-spectrum-estimator-pilot-v2-ordinal16'},clear=False):
        expect_refusal(lambda: executor.validate_execution_context(),'executor default accepted ordinal16 without explicit binding')
        executor.validate_execution_context('dispatch/full-spectrum-estimator-pilot-v2-ordinal16')
        expect_refusal(lambda: executor.validate_execution_context('dispatch/full-spectrum-estimator-pilot-v2-ordinal15'),'executor accepted wrong explicit branch')
    with mock.patch.dict(os.environ,{**base_env,'GITHUB_REF_NAME':'evil'},clear=False):
        expect_refusal(lambda: executor.validate_execution_context('evil'),'executor accepted non-canonical expected branch')
    require(v8.positive_candidate_claims('Ordinal 15 was consumed by a failed pre-solver attempt.')==[],'historical ordinal15 contaminated ordinal16 parser')
    prior_marker='ORDINAL15_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED commit='+'1'*40+' parent='+'2'*40+' pr=121'
    candidate_marker='ORDINAL16_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED commit='+'3'*40+' parent='+'4'*40+' pr=124'
    require(v8.positive_candidate_claims(prior_marker)==[],'historical structured ordinal15 marker contaminated ordinal16 parser')
    require(v8.positive_candidate_claims('authorization.ordinal15.json was historical evidence.')==[],'historical ordinal15 identifier contaminated ordinal16 parser')
    require(v8.positive_candidate_claims(candidate_marker)==[candidate_marker],'exact candidate ordinal16 marker was not detected')
    require(len(v8.positive_candidate_claims('We allocated ordinal 16 for this run.'))==1,'positive ordinal16 claim not detected')
    for text in ('No ordinal 16 authorization occurred.','Authorization for ordinal 16 was refused.','`Ordinal 16 is authorized.`','> Ordinal 16 is authorized.','```text\nOrdinal 16 is authorized.\n```'):
        require(v8.positive_candidate_claims(text)==[],f'negative/quoted ordinal16 text misclassified: {text!r}')
    prior={'branches':[{'name':'dispatch/full-spectrum-estimator-pilot-v2-ordinal15','commit':{'sha':'1'*40}}],'runs':[{'id':15,'event':'push','head_branch':'dispatch/full-spectrum-estimator-pilot-v2-ordinal15','head_sha':'1'*40,'path':'.github/workflows/full-spectrum-estimator-pilot-v2-ordinal15-execution-v7.yml','status':'completed','conclusion':'failure'}],'pulls':[],'issues':[],'issue60Comments':[{'body':prior_marker}],'activeAuthorizationPathOnMainExists':False}
    s=v8.build_surface(prior)
    require(s['latestPriorConsumedScientificOrdinal']==15 and s['nextAvailableScientificOrdinal']==16,'prior ordinal15 surface did not advance to 16')
    require(s['candidatePriorScientificRunCount']==0,'ordinal15 run misclassified as ordinal16 history')
    require(s['positiveCandidateClaimsExcludingCurrent']==0,'historical structured ordinal15 marker counted as candidate16 claim in full surface')
    auth_head='b'*40; parent='a'*40
    auth={'schemaVersion':1,'status':'AUTHORIZED_PENDING_SEPARATE_DISPATCH','enabled':True,'authorizationOrdinal':16,'executionKey':v8.EXECUTION_KEY,'runTitle':v8.TITLE,'authorizationBranch':v8.AUTH_BRANCH,'dispatchBranch':v8.DISPATCH_BRANCH,'exactAuthorizationParentCommit':parent,'exactAuthorizationCommit':None,'reviewBindingSha256':b['bindingSha256'],'transportContractSha256':c['contractSha256'],'solverExecutionAuthorized':True,'dispatchAuthorized':False,'automaticDispatch':False,'githubRerunAllowed':False,'resumeAllowed':False,'retryAllowed':False,'modelFittingAuthorized':False,'modelSelectionAuthorized':False,'holdoutValidationOpeningAuthorized':False,'tier2Authorized':False,'productionPromotionAuthorized':False}
    fresh={'latestPriorConsumedScientificOrdinal':15,'nextAvailableScientificOrdinal':16,'candidatePriorScientificRunCount':0,'authorizationBranchExists':True,'authorizationBranchHeadSha':auth_head,'authorizationBranchReusableAfterFailedReview':False,'dispatchBranchExists':False,'dispatchBranchHeadSha':None,'positiveCandidateClaimsExcludingCurrent':0,'matchingAuthorizationMarkers':0,'activeAuthorizationPathOnMainExists':False,'allStatePullRequestsInspected':True,'allStateIssuesInspected':True,'allActionsRunsInspected':True,'allBranchesInspected':True,'issue60AndCommentsInspected':True,'candidateCodePathsOnMainInspected':True}
    review_ctx={'liveMain':parent,'headSha':auth_head,'parentSha':parent,'parentCount':1,'changedPaths':['experiments/full-spectrum-estimator-pilot-v2/authorization.ordinal16.json'],'eventName':'pull_request','eventAction':'opened','runAttempt':1,'scientificRuntimeSetupPerformed':False,'scientificExecutionPerformed':False,'freshness':fresh,'pr':{'number':122,'state':'open','draft':True,'merged':False,'headBranch':v8.AUTH_BRANCH,'baseBranch':'main','headRepo':c['repository'],'baseRepo':c['repository'],'headSha':auth_head}}
    require(v8.review(auth,review_ctx)['status']=='AUTHORIZATION_REVIEW_PASS_ZERO_RUNTIME','v8 synthetic authorization review failed')
    fresh_dispatch=dict(fresh); fresh_dispatch['matchingAuthorizationMarkers']=1
    marker=f'ORDINAL16_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED commit={auth_head} parent={parent} pr=122'
    d={'liveMain':parent,'authorizationHead':auth_head,'authorizationParent':parent,'pr':{'number':122,'state':'open','draft':True,'merged':False,'headBranch':v8.AUTH_BRANCH,'headSha':auth_head},'authorizationReview':{'headSha':auth_head,'prNumber':122,'workflow':c['authorizationReviewRules']['workflow'],'runAttempt':1,'conclusion':'success','scientificRuntimeSetupPerformed':False,'scientificExecutionPerformed':False},'freshness':fresh_dispatch,'issue60Markers':[marker]}
    require(v8.dispatch_evaluate(auth,d)['status']=='DISPATCH_ELIGIBLE_NOT_CREATED','v8 synthetic dispatch guard failed')
    post=dict(fresh_dispatch); post['dispatchBranchExists']=True; post['dispatchBranchHeadSha']=auth_head; d2=dict(d); d2['freshness']=post
    e={'githubActions':True,'eventName':'push','refName':v8.DISPATCH_BRANCH,'headSha':auth_head,'dispatchBranchHeadSha':auth_head,'runAttempt':1,'priorMatchingScientificRuns':0,'resumeRequested':False,'retryRequested':False,'automaticDownstreamTransition':False,'dispatchEligibility':d2}
    require(v8.execution_evaluate(auth,e)['status']=='SCIENTIFIC_EXECUTION_GUARD_PASS','v8 synthetic execution guard failed')
    compact=v8.compact_matrix_output(root); require('\n' not in compact and '\r' not in compact,'v8 matrix output not single-line'); decoded=json.loads(compact); require(len(decoded['include'])==44,'v8 matrix count drift'); require([x['seed'] for x in decoded['include']]==list(range(970001,970045)),'v8 seed drift')
    workflows=[root/'.github/workflows/full-spectrum-estimator-pilot-v2-transport-review-v8.yml',root/'.github/workflows/full-spectrum-estimator-pilot-v2-authorization-review-v8.yml',root/'.github/workflows/full-spectrum-estimator-pilot-v2-ordinal16-execution-v8.yml']
    try: import yaml
    except Exception as exc: raise SystemExit(f'PyYAML unavailable: {exc}')
    for pth in workflows: require(isinstance(yaml.safe_load(pth.read_text()),dict),f'workflow YAML invalid: {pth.name}')
    for pth in workflows[:2]:
        text=pth.read_text(); forbidden=('setup-micromamba','rubin-libradtran','command -v uvspec','--allow-execution','workflow_dispatch:','schedule:','repository_dispatch:'); require(not [x for x in forbidden if x in text],f'review workflow exposes runtime: {pth.name}')
    sci=workflows[2].read_text(); require(v8.DISPATCH_BRANCH in sci,'v8 trigger missing'); require('--expected-dispatch-branch dispatch/full-spectrum-estimator-pilot-v2-ordinal16' in sci,'v8 executor branch binding missing'); require("separators=(',',':')" in sci,'v8 compact matrix missing')
    for alt in ('workflow_dispatch:','schedule:','repository_dispatch:'): require(alt not in sci,f'v8 alternate trigger exposed: {alt}')
    for name in ('executor.py','candidate_v8.py','run_transport_checks_v8.py'): require(compileall.compile_file(str(root/'experiments/full-spectrum-estimator-pilot-v2'/name),quiet=1,force=True),f'compile failed: {name}')
    print(json.dumps({'status':'TRANSPORT_V8_CHECKS_PASS','candidateOrdinal':16,'priorOrdinal':15,'caseCount':44,'priorAttempt15CaseJobs':44,'priorAttempt15SyntaxChecks':0,'priorAttempt15SolverExecutions':0,'executorLegacyDefaultOrdinal14':True,'executorExplicitOrdinal16Binding':True,'priorStructuredMarkerIsolationRegression':True,'scientificExecutionPerformed':False},indent=2,sort_keys=True)); return 0
if __name__=='__main__': raise SystemExit(main())
