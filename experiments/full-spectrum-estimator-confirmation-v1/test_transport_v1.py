#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util, json, tempfile, unittest
from pathlib import Path

HERE=Path(__file__).resolve().parent

def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path); assert spec and spec.loader
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module

authg=load_module('confirmation_auth_guard',HERE/'authorization_guard_v1.py')
execg=load_module('confirmation_execution_guard',HERE/'execution_guard_v1.py')
pkg=load_module('confirmation_package_evidence',HERE/'package_confirmation_evidence_v1.py')
CONTRACT=json.loads((HERE/'transport-contract.ordinal17.v1.json').read_text())
HEAD='a'*40
MAIN='b'*40
PR=140
AUTH_REVIEW_WORKFLOW='.github/workflows/full-spectrum-estimator-confirmation-v1-authorization-review-v1.yml'

def authorization():
    return {
      'schemaVersion':1,'status':'AUTHORIZED_PENDING_SEPARATE_DISPATCH','enabled':True,'authorizationOrdinal':17,
      'executionKey':'full-spectrum-estimator-confirmation-v1:numerical:17','runTitle':'Full-spectrum estimator confirmation v1 ordinal 17',
      'authorizationBranch':'authorization/full-spectrum-estimator-confirmation-v1-ordinal17','dispatchBranch':'dispatch/full-spectrum-estimator-confirmation-v1-ordinal17',
      'exactAuthorizationParentCommit':MAIN,'exactAuthorizationCommit':None,
      'confirmationPreregistrationSha256':'a801000ea0af81a109f9e0e1ec2b28befa0703e4ec47e9f85ee1b10b448a95b6',
      'confirmationExecutionManifestSha256':'9344ed18cfa93849d730cf080fe9f6c4c57f0cc5ea7b1be7ba9aa15d501c3fa8',
      'confirmationAnalysisContractSha256':'08f30045f6f595e5e11cca5401aa4e1ea88862651ed5d7439671a538bc532cc7',
      'transportContractSha256':'cab2d3d2d3bd92727f104b0fc906a51dbde293e0baa5678058ced7305b888c77',
      'solverExecutionAuthorized':True,'dispatchAuthorized':False,'automaticDispatch':False,'githubRerunAllowed':False,'resumeAllowed':False,'retryAllowed':False,
      'modelFittingAuthorized':False,'modelSelectionAuthorized':False,'holdoutValidationOpeningAuthorized':False,'tier2Authorized':False,'productionPromotionAuthorized':False,
    }

def branches(include_dispatch=False):
    rows=[{'name':'main','commit':{'sha':MAIN}}, {'name':'dispatch/full-spectrum-estimator-pilot-v2-ordinal16','commit':{'sha':'1'*40}}, {'name':'authorization/full-spectrum-estimator-confirmation-v1-ordinal17','commit':{'sha':HEAD}}]
    if include_dispatch: rows.append({'name':'dispatch/full-spectrum-estimator-confirmation-v1-ordinal17','commit':{'sha':HEAD}})
    return rows

def prior_runs():
    return [{'id':16,'event':'push','head_branch':'dispatch/full-spectrum-estimator-pilot-v2-ordinal16','head_sha':'1'*40,'path':'.github/workflows/full-spectrum-estimator-pilot-v2-ordinal16-execution-v8.yml','name':'pilot','display_title':'Full-spectrum estimator pilot v2 ordinal 16'}]

def auth_context():
    return {
      'eventName':'pull_request','runAttempt':1,'headBranch':'authorization/full-spectrum-estimator-confirmation-v1-ordinal17','headSha':HEAD,
      'liveMain':MAIN,'authorizationParent':MAIN,'changedFiles':['experiments/full-spectrum-estimator-confirmation-v1/authorization.ordinal17.json'],
      'pr':{'number':PR,'state':'open','draft':True,'merged':False,'headSha':HEAD,'headBranch':'authorization/full-spectrum-estimator-confirmation-v1-ordinal17','baseSha':MAIN},
      'branches':branches(False),'runs':prior_runs()+[{'id':99,'event':'pull_request','head_branch':'authorization/full-spectrum-estimator-confirmation-v1-ordinal17','head_sha':HEAD,'path':AUTH_REVIEW_WORKFLOW}],
      'artifacts':[],'issue60Comments':[],'currentRunId':99,'mainAuthorizationPathPresent':False,
    }

def exec_context():
    marker=f'ORDINAL17_CONFIRMATION_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED commit={HEAD} parent={MAIN} pr={PR}'
    return {
      'eventName':'push','runAttempt':1,'refName':'dispatch/full-spectrum-estimator-confirmation-v1-ordinal17','headSha':HEAD,'dispatchBranchHeadSha':HEAD,
      'liveMain':MAIN,'authorizationParent':MAIN,'changedFiles':['experiments/full-spectrum-estimator-confirmation-v1/authorization.ordinal17.json'],
      'pr':{'number':PR,'state':'open','draft':True,'merged':False,'headSha':HEAD,'headBranch':'authorization/full-spectrum-estimator-confirmation-v1-ordinal17','baseSha':MAIN},
      'authorizationReview':{'workflow':AUTH_REVIEW_WORKFLOW,'headSha':HEAD,'prNumber':PR,'runAttempt':1,'status':'completed','conclusion':'success','scientificRuntimeSetupPerformed':False,'scientificExecutionPerformed':False},
      'branches':branches(True),'runs':prior_runs()+[{'id':101,'event':'push','head_branch':'dispatch/full-spectrum-estimator-confirmation-v1-ordinal17','head_sha':HEAD,'path':'.github/workflows/full-spectrum-estimator-confirmation-v1-ordinal17-execution-v1.yml'}],
      'artifacts':[],'issue60Comments':[{'body':marker}],'currentRunId':101,'mainAuthorizationPathPresent':False,
    }

class TransportTests(unittest.TestCase):
    def test_contract_self_hash_and_boundary(self):
        authg.verify_contract(CONTRACT); execg.verify_contract(CONTRACT)
        self.assertTrue(all(v is False for v in CONTRACT['transportBoundary'].values()))

    def test_authorization_review_clean(self):
        out=authg.review(authorization(),CONTRACT,auth_context())
        self.assertEqual(out['status'],'AUTHORIZED_REVIEW_PASSED_NOT_DISPATCHED'); self.assertFalse(out['scientificExecutionPerformed'])

    def test_authorization_review_refuses_existing_dispatch(self):
        ctx=auth_context(); ctx['branches']=branches(True)
        with self.assertRaisesRegex(authg.Refusal,'dispatch branch already exists'): authg.review(authorization(),CONTRACT,ctx)

    def test_authorization_review_refuses_prior_exact_head_review(self):
        ctx=auth_context(); ctx['runs'].append({'id':98,'event':'pull_request','head_sha':HEAD,'path':AUTH_REVIEW_WORKFLOW})
        with self.assertRaisesRegex(authg.Refusal,'prior authorization-review'): authg.review(authorization(),CONTRACT,ctx)

    def test_execution_guard_clean(self):
        out=execg.review(authorization(),CONTRACT,exec_context())
        self.assertEqual(out['status'],'EXECUTION_GUARD_PASSED_READY_FOR_24_CASES'); self.assertEqual(out['caseCount'],24)

    def test_execution_guard_refuses_missing_marker(self):
        ctx=exec_context(); ctx['issue60Comments']=[]
        with self.assertRaisesRegex(execg.Refusal,'exact ordinal17 confirmation marker'): execg.review(authorization(),CONTRACT,ctx)

    def test_execution_guard_refuses_prior_case_artifact(self):
        ctx=exec_context(); ctx['artifacts']=[{'id':5,'name':'full-spectrum-estimator-confirmation-v1-case-c1'}]
        with self.assertRaisesRegex(execg.Refusal,'prior confirmation case artifact'): execg.review(authorization(),CONTRACT,ctx)

    def test_execution_guard_refuses_second_scientific_run(self):
        ctx=exec_context(); ctx['runs'].append({'id':100,'event':'push','head_branch':'dispatch/full-spectrum-estimator-confirmation-v1-ordinal17','path':'.github/workflows/full-spectrum-estimator-confirmation-v1-ordinal17-execution-v1.yml'})
        with self.assertRaisesRegex(execg.Refusal,'prior confirmation scientific run'): execg.review(authorization(),CONTRACT,ctx)

    def test_package_evidence_accepts_24_exact_digests(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); cases=[]; arts=[]
            for i in range(24):
                cid=f'case-{i+1:02d}'; cases.append({'caseId':cid}); name=pkg.PREFIX+cid; p=root/(name+'.zip'); raw=f'zip-{i}'.encode(); p.write_bytes(raw)
                arts.append({'id':1000+i,'name':name,'digest':'sha256:'+hashlib.sha256(raw).hexdigest(),'expired':False})
            manifest={'manifestSha256':pkg.MANIFEST_SHA,'caseCount':24,'cases':cases}
            out=pkg.build(manifest,{'artifacts':arts},root,123,1,17,HEAD)
            self.assertEqual(out['caseCount'],24); self.assertEqual(out['sourceOrdinal'],17)

    def test_package_evidence_refuses_digest_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); cases=[]; arts=[]
            for i in range(24):
                cid=f'case-{i+1:02d}'; cases.append({'caseId':cid}); name=pkg.PREFIX+cid; p=root/(name+'.zip'); raw=f'zip-{i}'.encode(); p.write_bytes(raw)
                digest='0'*64 if i==7 else hashlib.sha256(raw).hexdigest(); arts.append({'id':1000+i,'name':name,'digest':'sha256:'+digest,'expired':False})
            manifest={'manifestSha256':pkg.MANIFEST_SHA,'caseCount':24,'cases':cases}
            with self.assertRaisesRegex(pkg.Refusal,'digest mismatch'): pkg.build(manifest,{'artifacts':arts},root,123,1,17,HEAD)

if __name__=='__main__': unittest.main()
