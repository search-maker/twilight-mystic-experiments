#!/usr/bin/env python3
import copy,json,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
C=json.loads((ROOT/'activation-contract.v1.json').read_text())

def canon(v):
 import hashlib; return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
main='a'*40; head='b'*40
base={'schemaVersion':1,'status':'AUTHORIZED_PENDING_SEPARATE_DISPATCH','enabled':True,'variant':'train0014','authorizationOrdinal':18,'executionKey':C['executionKey'],'runTitle':C['runTitle'],'authorizationBranch':C['authorizationBranch'],'dispatchBranch':C['dispatchBranch'],'exactAuthorizationParentCommit':main,'exactAuthorizationCommit':None,'preregistrationSha256':C['bindings']['preregistrationSha256'],'executionManifestSha256':C['bindings']['executionManifestSha256'],'analysisContractSha256':C['bindings']['analysisContractSha256'],'transportContractSha256':C['bindings']['transportContractSha256'],'activationContractSha256':C['activationContractSha256'],'runtimeIdentitySha256':C['bindings']['runtimeIdentitySha256'],'scientificExecutionAuthorized':True,'dispatchAuthorized':True,'automaticDispatch':False,'githubRerunAllowed':False,'retryAllowed':False,'resumeAllowed':False,'trainingAdmissionAuthorized':False,'modelFittingAuthorized':False,'modelSelectionAuthorized':False,'holdoutValidationOpeningAuthorized':False,'tier2Authorized':False,'productionPromotionAuthorized':False}; auth=dict(base); auth['authorizationSha256']=canon(auth)
pre={'status':'PREAUTHORIZATION_SURFACE_CLEAN_NOT_ALLOCATED','variant':'train0014','latestConsumedScientificOrdinal':17,'nextAvailableScientificOrdinalIfAllocatedLater':18,'seedCollisions':{'source166':[],'pilot':[],'ordinal17Confirmation':[],'otherFrozenContinuationVariant':[]}}
oldbranch={'name':'dispatch/full-spectrum-estimator-confirmation-v1-ordinal17','commit':{'sha':'c'*40}}
authbranch={'name':C['authorizationBranch'],'commit':{'sha':head}}; dispatchbranch={'name':C['dispatchBranch'],'commit':{'sha':head}}
pr={'number':999,'state':'open','draft':True,'merged':False,'headSha':head,'headBranch':C['authorizationBranch'],'baseSha':main}
with tempfile.TemporaryDirectory() as td:
 td=Path(td); (td/'auth.json').write_text(json.dumps(auth));
 def run(script,ctx):
  (td/'ctx.json').write_text(json.dumps(ctx)); return subprocess.run(['python3',str(ROOT/script),'--authorization',str(td/'auth.json'),'--contract',str(ROOT/'activation-contract.v1.json'),'--context',str(td/'ctx.json'),'--output',str(td/'o.json')],capture_output=True,text=True)
 actx={'eventName':'pull_request','runAttempt':1,'headBranch':C['authorizationBranch'],'headSha':head,'liveMain':main,'authorizationParent':main,'changedFiles':[C['authorizationPath']],'freshPreauthorization':pre,'pr':pr,'branches':[oldbranch,authbranch],'runs':[{'id':1,'event':'push','head_branch':oldbranch['name']}],'artifacts':[],'issue60Comments':[],'currentRunId':2,'mainAuthorizationPathPresent':False}
 r=run('authorization_guard_v1.py',actx); assert r.returncode==0,r.stdout+r.stderr
 bad=copy.deepcopy(actx); bad['freshPreauthorization']['nextAvailableScientificOrdinalIfAllocatedLater']=19; assert run('authorization_guard_v1.py',bad).returncode==2
 marker=f"ORDINAL18_TRAIN0014_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED commit={head} parent={main} pr=999"
 ectx={'eventName':'push','runAttempt':1,'refName':C['dispatchBranch'],'headSha':head,'dispatchBranchHeadSha':head,'liveMain':main,'authorizationParent':main,'changedFiles':[C['authorizationPath']],'pr':pr,'authorizationReview':{'workflow':C['authorizationReviewWorkflow'],'headSha':head,'prNumber':999,'runAttempt':1,'status':'completed','conclusion':'success','scientificRuntimeSetupPerformed':False,'scientificExecutionPerformed':False},'branches':[oldbranch,authbranch,dispatchbranch],'runs':[{'id':1,'event':'push','head_branch':oldbranch['name']}],'artifacts':[],'issue60Comments':[{'body':marker}],'currentRunId':3,'mainAuthorizationPathPresent':False}
 r=run('execution_guard_v1.py',ectx); assert r.returncode==0,r.stdout+r.stderr
 bad=copy.deepcopy(ectx); bad['runAttempt']=2; assert run('execution_guard_v1.py',bad).returncode==2
 bad=copy.deepcopy(ectx); bad['artifacts']=[{'id':7,'name':'training-continuation-train0014-case-x'}]; assert run('execution_guard_v1.py',bad).returncode==2
print('authorization/execution guard tests: PASS')
