#!/usr/bin/env python3
from __future__ import annotations
import copy, importlib.util, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; E=ROOT/'experiments/tier2-stage1-execution-v1'; R=Path(__file__).resolve().parent
def mod(n,p):
    s=importlib.util.spec_from_file_location(n,p); assert s and s.loader; m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
P=mod('p',E/'preauthorization_guard_v1.py'); X=mod('xg',E/'execution_guard_v1.py')
C=json.loads((R/'tier2-stage1-execution-transport-v1.json').read_text()); M=json.loads((E/'stage1-execution-manifest-v1.json').read_text())
ORD=C['sourceBindings']['latestConsumedScientificOrdinal']+1; AUTH=f'authorization/tier2-stage1-ordinal{ORD}-v1'; DISP=f'dispatch/tier2-stage1-ordinal{ORD}-v1'; KEY=f'tier2-core-stage1-v1:numerical:{ORD}'; HEAD='a'*40; BASE='b'*40
A={'schemaVersion':1,'status':'AUTHORIZED_PENDING_SEPARATE_DISPATCH','enabled':True,'scientificOrdinal':ORD,'authorizationBranch':AUTH,'dispatchBranch':DISP,'executionKey':KEY,'manifestSha256':M['manifestSha256'],'transportContractSha256':C['contractSha256'],'exactAuthorizationParentCommit':BASE,'scientificExecutionAuthorized':True,'dispatchAuthorized':True,'automaticDispatch':False,'githubRerunAllowed':False,'retryAllowed':False,'resumeAllowed':False,'solverExecutionPerformed':False,'protectedHoldoutOpeningAuthorized':False,'modelFittingAuthorized':False,'modelSelectionAuthorized':False,'productionPromotionAuthorized':False,'stage2Authorized':False}
seed={'status':'PASSED_EXACT_HEAD_TRACKED_TREE_100_SEED_NEGATIVE_COLLISION_CHECK','repoHead':HEAD,'externalCollisionCount':0}
ctx={'eventName':'pull_request','runAttempt':1,'currentRunId':100,'headBranch':AUTH,'headSha':HEAD,'parentSha':BASE,'liveMain':BASE,'changedFiles':[C['authorization']['path']],'authorization':A,'mainAuthorizationPathPresent':False,'trackedSeedAudit':seed,'branches':[{'name':'dispatch/legacy-ordinal18-v1','commit':{'sha':'1'*40}},{'name':AUTH,'commit':{'sha':HEAD}}],'runs':[{'id':1,'event':'push','head_branch':'dispatch/legacy-ordinal18-v1','head_sha':'1'*40},{'id':100,'event':'pull_request','head_branch':AUTH,'head_sha':HEAD},{'id':101,'event':'pull_request','head_branch':AUTH,'head_sha':HEAD,'path':'.github/workflows/contract.yml'}],'artifacts':[],'issue60Comments':[{'id':5279964834,'body':f"candidate ledger {C['sourceBindings']['campaignContractSha256']} {C['seedAudit']['candidateFirstSeed']}..{C['seedAudit']['candidateLastSeed']}"}],'pr':{'number':1,'draft':True,'state':'open','headSha':HEAD,'baseSha':BASE}}
o=P.evaluate(C,M,ctx); assert o['candidateScientificOrdinal']==ORD and o['status'].startswith('AUTHORIZATION_IDENTITY_REVIEW_PASSED')
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
review=o
xc={'eventName':'push','runAttempt':1,'refName':DISP,'headSha':HEAD,'authorizationCommitSha':HEAD,'parentSha':BASE,'liveMain':BASE,'changedFiles':[C['authorization']['path']],'mainAuthorizationPathPresent':False,'trackedSeedAudit':seed,'currentRunId':200,'runs':[{'id':1,'event':'push','head_branch':'dispatch/legacy-ordinal18-v1'},{'id':200,'event':'push','head_branch':DISP}],'artifacts':[],'issue60Comments':[],'authorizationReview':{'headSha':HEAD,'headBranch':AUTH,'runAttempt':1,'status':'completed','conclusion':'success','runId':100},'authorizationPr':{'number':1,'state':'open','draft':True,'headSha':HEAD,'headBranch':AUTH,'merged':False}}
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

# Harden duplicate/provenance refusal coverage across every scientific artifact prefix.
for prefix in ('tier2-stage1-case-','tier2-stage1-preflight','tier2-stage1-aggregate','tier2-stage1-audit','tier2-stage1-handoff'):
    c=copy.deepcopy(ctx); c['artifacts'].append({'id':700+len(prefix),'name':prefix+'historical-evidence'})
    try:P.evaluate(C,M,c)
    except P.Refusal: pass
    else: raise AssertionError(f'preauthorization accepted prior artifact prefix {prefix}')
    d=copy.deepcopy(xc); d['artifacts'].append({'id':800+len(prefix),'name':prefix+'historical-evidence'})
    try:X.evaluate(C,M,A,review,d)
    except X.Refusal: pass
    else: raise AssertionError(f'execution guard accepted prior artifact prefix {prefix}')

# Candidate seeds in repository-global branch/run/artifact metadata are collisions,
# including underscore-formatted numeric literals.
meta_seed=copy.deepcopy(ctx); n=C['seedAudit']['candidateFirstSeed']+9; meta_seed['artifacts'].append({'id':901,'name':f'external-seed-{n:_}'})
try:P.evaluate(C,M,meta_seed)
except P.Refusal: pass
else: raise AssertionError('preauthorization accepted candidate seed in artifact metadata')

allocation_marker=copy.deepcopy(ctx); allocation_marker['issue60Comments'].append({'id':902,'body':f'ORDINAL{ORD}_TIER2_STAGE1_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED unexpected reuse'})
try:P.evaluate(C,M,allocation_marker)
except P.Refusal: pass
else: raise AssertionError('preauthorization accepted prior ordinal allocation marker')

dispatch_marker=copy.deepcopy(xc); dispatch_marker['issue60Comments'].append({'id':903,'body':f'ORDINAL{ORD}_TIER2_STAGE1_DISPATCH_CONSUMED historical'})
try:X.evaluate(C,M,A,review,dispatch_marker)
except X.Refusal: pass
else: raise AssertionError('execution guard accepted prior dispatch-consumed marker')

print('PASS: all five scientific artifact prefixes, metadata seeds, and ordinal markers refuse reuse')
