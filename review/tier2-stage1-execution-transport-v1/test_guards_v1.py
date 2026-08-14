#!/usr/bin/env python3
from __future__ import annotations
import copy, importlib.util, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; E=ROOT/'experiments/tier2-stage1-execution-v1'; R=Path(__file__).resolve().parent
def mod(n,p):
    s=importlib.util.spec_from_file_location(n,p); assert s and s.loader; m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
P=mod('p',E/'preauthorization_guard_v1.py'); X=mod('xg',E/'execution_guard_v1.py')
C=json.loads((R/'tier2-stage1-execution-transport-v1.json').read_text()); M=json.loads((E/'stage1-execution-manifest-v1.json').read_text())
ORD=C['sourceBindings']['latestConsumedScientificOrdinal']+1; AUTH=C['authorization']['authorizationBranchTemplate'].format(scientificOrdinal=ORD); DISP=C['authorization']['dispatchBranchTemplate'].format(scientificOrdinal=ORD); KEY=C['authorization']['executionKeyTemplate'].format(scientificOrdinal=ORD); HEAD='a'*40; BASE='b'*40
A={'schemaVersion':1,'status':'AUTHORIZED_PENDING_SEPARATE_DISPATCH','enabled':True,'scientificOrdinal':ORD,'authorizationBranch':AUTH,'dispatchBranch':DISP,'executionKey':KEY,'manifestSha256':M['manifestSha256'],'transportContractSha256':C['contractSha256'],'exactAuthorizationParentCommit':BASE,'scientificExecutionAuthorized':True,'dispatchAuthorized':True,'automaticDispatch':False,'githubRerunAllowed':False,'retryAllowed':False,'resumeAllowed':False,'solverExecutionPerformed':False,'protectedHoldoutOpeningAuthorized':False,'modelFittingAuthorized':False,'modelSelectionAuthorized':False,'productionPromotionAuthorized':False,'stage2Authorized':False}
seed={'status':'PASSED_EXACT_HEAD_TRACKED_TREE_100_SEED_NEGATIVE_COLLISION_CHECK','repoHead':HEAD,'externalCollisionCount':0}
REC=C['recovery']['priorFailedPresolverDispatch']
recovery_run={'id':REC['runId'],'event':'push','head_branch':REC['branch'],'head_sha':REC['headSha'],'run_attempt':REC['runAttempt'],'status':'completed','conclusion':REC['conclusion']}
recovery_artifacts=[{'id':x['artifactId'],'name':x['name'],'digest':x['digest'],'workflow_run':{'id':REC['runId'],'head_branch':REC['branch'],'head_sha':REC['headSha']}} for x in REC['allowedArtifacts']]
ctx={'eventName':'pull_request','runAttempt':1,'currentRunId':100,'headBranch':AUTH,'headSha':HEAD,'parentSha':BASE,'liveMain':BASE,'changedFiles':[C['authorization']['path']],'authorization':A,'mainAuthorizationPathPresent':False,'trackedSeedAudit':seed,'branches':[{'name':REC['branch'],'commit':{'sha':REC['headSha']}},{'name':AUTH,'commit':{'sha':HEAD}}],'runs':[recovery_run,{'id':100,'event':'pull_request','head_branch':AUTH,'head_sha':HEAD},{'id':101,'event':'pull_request','head_branch':AUTH,'head_sha':HEAD,'path':'.github/workflows/contract.yml'}],'artifacts':recovery_artifacts,'issue60Comments':[{'id':5279964834,'body':f"candidate ledger {C['sourceBindings']['campaignContractSha256']} {C['seedAudit']['candidateFirstSeed']}..{C['seedAudit']['candidateLastSeed']}"}],'pr':{'number':1,'draft':True,'state':'open','headSha':HEAD,'baseSha':BASE}}
o=P.evaluate(C,M,ctx); assert o['candidateScientificOrdinal']==ORD and o['status'].startswith('AUTHORIZATION_IDENTITY_REVIEW_PASSED')
# Regression for the preserved failed v1 authorization review: the old negative-check
# comment consumed the old dispatch string, but must not contaminate a newer versioned
# identity. The failed v2 authorization review is immutable history and likewise must not
# contaminate v3. Conversely, publishing the current dispatch identity early must still fail.
legacy_identity_comment=copy.deepcopy(ctx)
legacy_identity_comment['issue60Comments'].append({'id':5285605573,'body':'early warning: no authorization/tier2-stage1-ordinal19-v1 or dispatch/tier2-stage1-ordinal19-v1 branch identity'})
legacy_o=P.evaluate(C,M,legacy_identity_comment); assert legacy_o['dispatchBranch']==DISP
current_identity_comment=copy.deepcopy(ctx)
current_identity_comment['issue60Comments'].append({'id':5285605573,'body':f'early warning: no {DISP} branch identity'})
try:P.evaluate(C,M,current_identity_comment)
except P.Refusal: pass
else: raise AssertionError('preauthorization accepted current dispatch identity already recorded in Issue #60')
extra_auth=copy.deepcopy(ctx); extra_auth['authorization']['unexpectedField']='refuse'
try:P.evaluate(C,M,extra_auth)
except P.Refusal: pass
else: raise AssertionError('preauthorization accepted extra authorization field')

# Multiple attempt-1/non-scientific checks on the same exact authorization head are allowed;
# a historical reuse of the authorization branch name at a different head is refused.
reuse=copy.deepcopy(ctx); reuse['runs'].append({'id':88,'event':'pull_request','head_branch':AUTH,'head_sha':'c'*40})
try:P.evaluate(C,M,reuse)
except P.Refusal: pass
else: raise AssertionError('preauthorization accepted historical authorization-branch identity reuse')
drift=copy.deepcopy(ctx); drift['issue60Comments'][0]['body'] += f" used={C['seedAudit']['candidateFirstSeed']+7}"
try:P.evaluate(C,M,drift)
except P.Refusal: pass
else: raise AssertionError('preauthorization accepted drifted allowed Issue #60 seed ledger comment')

for mutate in ('prior_dispatch','external_seed','prior_artifact'):
    c=copy.deepcopy(ctx)
    if mutate=='prior_dispatch': c['runs'].append({'id':9,'event':'push','head_branch':DISP})
    elif mutate=='external_seed': c['issue60Comments'].append({'id':2,'body':str(C['seedAudit']['candidateFirstSeed']+7)})
    else: c['artifacts'].append({'id':7,'name':'tier2-stage1-case-old'})
    try:P.evaluate(C,M,c)
    except P.Refusal: pass
    else: raise AssertionError(f'preauthorization accepted {mutate}')
# Recovery exception is exact: any case artifact, missing allowed artifact, or run-attempt drift is refused.
case_art=copy.deepcopy(ctx); case_art['artifacts'].append({'id':999,'name':'tier2-stage1-case-historical','digest':'sha256:'+'0'*64,'workflow_run':{'id':REC['runId'],'head_branch':REC['branch'],'head_sha':REC['headSha']}})
try:P.evaluate(C,M,case_art)
except P.Refusal: pass
else: raise AssertionError('preauthorization accepted historical case artifact')
missing_art=copy.deepcopy(ctx); missing_art['artifacts']=missing_art['artifacts'][:-1]
try:P.evaluate(C,M,missing_art)
except P.Refusal: pass
else: raise AssertionError('preauthorization accepted missing recovery artifact')
rerun=copy.deepcopy(ctx); rerun['runs'][0]['run_attempt']=2
try:P.evaluate(C,M,rerun)
except P.Refusal: pass
else: raise AssertionError('preauthorization accepted rerun recovery evidence')
review=o
xc={'eventName':'push','runAttempt':1,'refName':DISP,'headSha':HEAD,'authorizationCommitSha':HEAD,'parentSha':BASE,'liveMain':BASE,'changedFiles':[C['authorization']['path']],'mainAuthorizationPathPresent':False,'trackedSeedAudit':seed,'currentRunId':200,'runs':[recovery_run,{'id':200,'event':'push','head_branch':DISP}],'artifacts':copy.deepcopy(recovery_artifacts),'issue60Comments':[],'authorizationReview':{'headSha':HEAD,'headBranch':AUTH,'runAttempt':1,'status':'completed','conclusion':'success','runId':100},'authorizationPr':{'number':1,'state':'open','draft':True,'headSha':HEAD,'headBranch':AUTH,'merged':False}}
xo=X.evaluate(C,M,A,review,xc); assert xo['status']=='EXACT_ONE_USE_STAGE1_DISPATCH_AUTHORIZED' and xo['solverExecutionPermittedNow'] is True and xo['stage2Authorized'] is False
bad_review=copy.deepcopy(review); bad_review['transportContractSha256']='0'*64
try:X.evaluate(C,M,A,bad_review,xc)
except X.Refusal: pass
else: raise AssertionError('execution guard accepted mismatched authorization-review transport binding')
closed_pr=copy.deepcopy(xc); closed_pr['authorizationPr']['state']='closed'
try:X.evaluate(C,M,A,review,closed_pr)
except X.Refusal: pass
else: raise AssertionError('execution guard accepted closed authorization PR')
bad=copy.deepcopy(xc); bad['runs'].append({'id':199,'event':'push','head_branch':DISP})
try:X.evaluate(C,M,A,review,bad)
except X.Refusal: pass
else: raise AssertionError('execution guard accepted prior dispatch run')
print('PASS: preauthorization and one-use execution guards fail closed')
