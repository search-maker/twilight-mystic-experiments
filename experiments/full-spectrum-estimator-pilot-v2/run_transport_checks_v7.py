#!/usr/bin/env python3
from __future__ import annotations
import argparse, compileall, json, re, sys
from pathlib import Path

HERE=Path(__file__).resolve().parent

def require(c:bool,m:str)->None:
    if not c: raise SystemExit(m)

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--repository-root',type=Path,required=True); a=ap.parse_args(); root=a.repository_root.resolve()
    sys.path.insert(0,str(root/'experiments/full-spectrum-estimator-pilot-v2'))
    import candidate_v7 as v7
    c,b=v7.validate_static(root)
    require(c['candidateIdentity']['globalScientificOrdinal']==15,'v7 candidate ordinal drift')
    require(c['freshnessRules']['latestPriorConsumedScientificOrdinalExactly']==14,'v7 prior ordinal drift')
    require(c['priorAttempt14']['runId']==31542689486 and c['priorAttempt14']['solverExecutions']==0 and c['priorAttempt14']['scientificCaseJobsStarted']==0,'ordinal-14 pre-solver failure binding drift')
    require(c['scientificPayload']['seedDisposition']=='FROZEN_UNEXECUTED_SEEDS_RETAINED_AFTER_PRE_SOLVER_TRANSPORT_FAILURE','seed disposition drift')
    require(v7.positive_candidate_claims('Ordinal 14 was consumed by a failed pre-solver attempt.')==[],'historical ordinal 14 contaminated ordinal 15 candidate parser')
    require(len(v7.positive_candidate_claims('We allocated ordinal 15 for this run.'))==1,'positive ordinal-15 claim not detected')
    for text in ('No ordinal 15 authorization occurred.','Authorization for ordinal 15 was refused.','`Ordinal 15 is authorized.`','> Ordinal 15 is authorized.','```text\nOrdinal 15 is authorized.\n```'):
        require(v7.positive_candidate_claims(text)==[],f'negative/quoted ordinal-15 text misclassified: {text!r}')
    prior={'branches':[{'name':'dispatch/full-spectrum-estimator-pilot-v2-ordinal14','commit':{'sha':'1'*40}}],'runs':[{'id':14,'event':'push','head_branch':'dispatch/full-spectrum-estimator-pilot-v2-ordinal14','head_sha':'1'*40,'path':'.github/workflows/full-spectrum-estimator-pilot-v2-ordinal14-execution-v6.yml','status':'completed','conclusion':'failure'}],'pulls':[],'issues':[],'issue60Comments':[],'activeAuthorizationPathOnMainExists':False}
    s=v7.build_surface(prior)
    require(s['latestPriorConsumedScientificOrdinal']==14 and s['nextAvailableScientificOrdinal']==15,'prior ordinal-14 surface did not advance to 15')
    require(s['candidatePriorScientificRunCount']==0,'ordinal-14 run was misclassified as ordinal-15 scientific history')
    auth_head='b'*40; parent='a'*40
    auth={
      'schemaVersion':1,'status':'AUTHORIZED_PENDING_SEPARATE_DISPATCH','enabled':True,'authorizationOrdinal':15,
      'executionKey':v7.EXECUTION_KEY,'runTitle':v7.TITLE,'authorizationBranch':v7.AUTH_BRANCH,'dispatchBranch':v7.DISPATCH_BRANCH,
      'exactAuthorizationParentCommit':parent,'exactAuthorizationCommit':None,'reviewBindingSha256':b['bindingSha256'],'transportContractSha256':c['contractSha256'],
      'solverExecutionAuthorized':True,'dispatchAuthorized':False,'automaticDispatch':False,'githubRerunAllowed':False,'resumeAllowed':False,'retryAllowed':False,
      'modelFittingAuthorized':False,'modelSelectionAuthorized':False,'holdoutValidationOpeningAuthorized':False,'tier2Authorized':False,'productionPromotionAuthorized':False}
    fresh={'latestPriorConsumedScientificOrdinal':14,'nextAvailableScientificOrdinal':15,'candidatePriorScientificRunCount':0,'authorizationBranchExists':True,'authorizationBranchHeadSha':auth_head,'authorizationBranchReusableAfterFailedReview':False,'dispatchBranchExists':False,'dispatchBranchHeadSha':None,'positiveCandidateClaimsExcludingCurrent':0,'matchingAuthorizationMarkers':0,'activeAuthorizationPathOnMainExists':False,'allStatePullRequestsInspected':True,'allStateIssuesInspected':True,'allActionsRunsInspected':True,'allBranchesInspected':True,'issue60AndCommentsInspected':True,'candidateCodePathsOnMainInspected':True}
    review_ctx={'liveMain':parent,'headSha':auth_head,'parentSha':parent,'parentCount':1,'changedPaths':['experiments/full-spectrum-estimator-pilot-v2/authorization.ordinal15.json'],'eventName':'pull_request','eventAction':'opened','runAttempt':1,'scientificRuntimeSetupPerformed':False,'scientificExecutionPerformed':False,'freshness':fresh,'pr':{'number':120,'state':'open','draft':True,'merged':False,'headBranch':v7.AUTH_BRANCH,'baseBranch':'main','headRepo':c['repository'],'baseRepo':c['repository'],'headSha':auth_head}}
    require(v7.review(auth,review_ctx)['status']=='AUTHORIZATION_REVIEW_PASS_ZERO_RUNTIME','v7 synthetic authorization review failed')
    fresh_dispatch=dict(fresh); fresh_dispatch['matchingAuthorizationMarkers']=1
    marker=f'ORDINAL15_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED commit={auth_head} parent={parent} pr=120'
    d={'liveMain':parent,'authorizationHead':auth_head,'authorizationParent':parent,'pr':{'number':120,'state':'open','draft':True,'merged':False,'headBranch':v7.AUTH_BRANCH,'headSha':auth_head},'authorizationReview':{'headSha':auth_head,'prNumber':120,'workflow':c['authorizationReviewRules']['workflow'],'runAttempt':1,'conclusion':'success','scientificRuntimeSetupPerformed':False,'scientificExecutionPerformed':False},'freshness':fresh_dispatch,'issue60Markers':[marker]}
    require(v7.dispatch_evaluate(auth,d)['status']=='DISPATCH_ELIGIBLE_NOT_CREATED','v7 synthetic dispatch guard failed')
    post=dict(fresh_dispatch); post['dispatchBranchExists']=True; post['dispatchBranchHeadSha']=auth_head; d2=dict(d); d2['freshness']=post
    e={'githubActions':True,'eventName':'push','refName':v7.DISPATCH_BRANCH,'headSha':auth_head,'dispatchBranchHeadSha':auth_head,'runAttempt':1,'priorMatchingScientificRuns':0,'resumeRequested':False,'retryRequested':False,'automaticDownstreamTransition':False,'dispatchEligibility':d2}
    require(v7.execution_evaluate(auth,e)['status']=='SCIENTIFIC_EXECUTION_GUARD_PASS','v7 synthetic execution guard failed')
    compact=v7.compact_matrix_output(root)
    require('\n' not in compact and '\r' not in compact,'matrix GitHub output payload is not single-line JSON')
    decoded=json.loads(compact); require(len(decoded.get('include',[]))==44,'compact matrix does not contain exactly 44 cases')
    require([x['seed'] for x in decoded['include']]==list(range(970001,970045)),'v7 compact matrix seed sequence drift')
    workflows=[
      root/'.github/workflows/full-spectrum-estimator-pilot-v2-transport-review-v7.yml',
      root/'.github/workflows/full-spectrum-estimator-pilot-v2-authorization-review-v7.yml',
      root/'.github/workflows/full-spectrum-estimator-pilot-v2-ordinal15-execution-v7.yml']
    try: import yaml
    except Exception as exc: raise SystemExit(f'PyYAML unavailable: {exc}')
    for p in workflows:
        require(isinstance(yaml.safe_load(p.read_text()),dict),f'workflow YAML did not parse to mapping: {p.name}')
    for p in workflows[:2]:
        text=p.read_text(); forbidden=('setup-micromamba','rubin-libradtran','command -v uvspec','--allow-execution','workflow_dispatch:','schedule:','repository_dispatch:')
        require(not [x for x in forbidden if x in text],f'review workflow exposes scientific runtime surface: {p.name}')
    sci=workflows[2].read_text()
    require('dispatch/full-spectrum-estimator-pilot-v2-ordinal15' in sci,'ordinal-15 scientific trigger branch missing')
    require("printf 'matrix=%s" not in sci,'legacy multiline-unsafe matrix output command retained')
    require("separators=(',',':')" in sci,'compact single-line matrix serialization missing')
    for alt in ('workflow_dispatch:','schedule:','repository_dispatch:'): require(alt not in sci,f'scientific workflow exposes alternate trigger: {alt}')
    for name in ('candidate_v7.py','run_transport_checks_v7.py'):
        require(compileall.compile_file(str(root/'experiments/full-spectrum-estimator-pilot-v2'/name),quiet=1,force=True),f'compile failed: {name}')
    print(json.dumps({'status':'TRANSPORT_V7_CHECKS_PASS','candidateOrdinal':15,'priorOrdinal':14,'caseCount':44,'seedStart':970001,'seedStop':970044,'priorAttempt14SolverExecutions':0,'matrixOutputSingleLine':True,'scientificExecutionPerformed':False,'automaticDownstreamTransition':False},indent=2,sort_keys=True))
    return 0
if __name__=='__main__': raise SystemExit(main())
