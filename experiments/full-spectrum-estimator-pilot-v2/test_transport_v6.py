from __future__ import annotations
import hashlib, importlib.util, json, os, ssl, subprocess, sys, tempfile, unittest, urllib.error, zipfile
from pathlib import Path
from unittest import mock

HERE=Path(__file__).resolve().parent
REPO=Path(os.environ.get('TRANSPORT_TEST_REPOSITORY_ROOT', str(HERE.parents[1]))).resolve()
sys.path.insert(0,str(HERE))
import freshness, github_surface, package_evidence, authorization_guard, dispatch_guard, execution_guard, executor

def load(p): return json.loads(Path(p).read_text())
CONTRACT=load(HERE/'transport-contract.v6.json'); BINDING=load(HERE/'review-binding.v6.json'); TEMPLATE=load(HERE/'authorization-template.ordinal14.json')
REVIEW=REPO/'review/full-spectrum-estimator-pilot-v2'
MANIFEST=load(REVIEW/'full-spectrum-estimator-pilot-execution-manifest-v4.json') if REVIEW.exists() else None

def fresh_base(auth_exists=False, auth_head=None, marker_count=0):
    return {'latestPriorConsumedScientificOrdinal':13,'nextAvailableScientificOrdinal':14,'candidatePriorScientificRunCount':0,'authorizationBranchExists':auth_exists,'authorizationBranchHeadSha':auth_head,'dispatchBranchExists':False,'dispatchBranchHeadSha':None,'positiveCandidateClaimsExcludingCurrent':0,'matchingAuthorizationMarkers':marker_count,'activeAuthorizationPathOnMainExists':False,'allStatePullRequestsInspected':True,'allStateIssuesInspected':True,'allActionsRunsInspected':True,'allBranchesInspected':True,'issue60AndCommentsInspected':True,'candidateCodePathsOnMainInspected':True}

def enabled_auth(parent='a'*40):
    return {'schemaVersion':1,'status':'AUTHORIZED_PENDING_SEPARATE_DISPATCH','enabled':True,'authorizationOrdinal':14,'executionKey':freshness.EXECUTION_KEY,'runTitle':freshness.TITLE,'authorizationBranch':freshness.AUTH_BRANCH,'dispatchBranch':freshness.DISPATCH_BRANCH,'exactAuthorizationParentCommit':parent,'exactAuthorizationCommit':None,'reviewBindingSha256':BINDING['bindingSha256'],'transportContractSha256':CONTRACT['contractSha256'],'solverExecutionAuthorized':True,'dispatchAuthorized':False,'automaticDispatch':False,'githubRerunAllowed':False,'resumeAllowed':False,'retryAllowed':False,'modelFittingAuthorized':False,'modelSelectionAuthorized':False,'holdoutValidationOpeningAuthorized':False,'tier2Authorized':False,'productionPromotionAuthorized':False}

def auth_ctx(head='b'*40,parent='a'*40):
    return {'liveMain':parent,'headSha':head,'parentSha':parent,'parentCount':1,'changedPaths':['experiments/full-spectrum-estimator-pilot-v2/authorization.ordinal14.json'],'eventName':'pull_request','eventAction':'opened','runAttempt':1,'scientificRuntimeSetupPerformed':False,'scientificExecutionPerformed':False,'freshness':fresh_base(True,head,0),'pr':{'number':110,'state':'open','draft':True,'merged':False,'headBranch':freshness.AUTH_BRANCH,'baseBranch':'main','headRepo':CONTRACT['repository'],'baseRepo':CONTRACT['repository'],'headSha':head}}

def dispatch_ctx(head='b'*40,parent='a'*40):
    return {'liveMain':parent,'authorizationHead':head,'authorizationParent':parent,'pr':{'number':110,'state':'open','draft':True,'merged':False,'headBranch':freshness.AUTH_BRANCH,'headSha':head},'authorizationReview':{'headSha':head,'prNumber':110,'workflow':CONTRACT['authorizationReviewRules']['workflow'],'runAttempt':1,'conclusion':'success','scientificRuntimeSetupPerformed':False,'scientificExecutionPerformed':False},'freshness':fresh_base(True,head,1),'issue60Markers':[f'ORDINAL14_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED commit={head} parent={parent} pr=110']}

def exec_ctx(head='b'*40,parent='a'*40):
    d=dispatch_ctx(head,parent); d['freshness']['dispatchBranchExists']=True; d['freshness']['dispatchBranchHeadSha']=head
    return {'githubActions':True,'eventName':'push','refName':freshness.DISPATCH_BRANCH,'headSha':head,'dispatchBranchHeadSha':head,'runAttempt':1,'priorMatchingScientificRuns':0,'resumeRequested':False,'retryRequested':False,'automaticDownstreamTransition':False,'dispatchEligibility':d}

class StaticBindingTests(unittest.TestCase):
    def test_01_contract_self_hash(self): self.assertEqual(CONTRACT['contractSha256'],package_evidence.selfhash(CONTRACT,'contractSha256'))
    def test_02_binding_self_hash(self): self.assertEqual(BINDING['bindingSha256'],package_evidence.selfhash(BINDING,'bindingSha256'))
    def test_03_template_raw_hash(self): self.assertEqual(CONTRACT['authorizationRules']['templateRawSha256'],package_evidence.rawsha(HERE/'authorization-template.ordinal14.json'))
    def test_04_template_disabled(self): self.assertFalse(TEMPLATE['enabled']); self.assertIsNone(TEMPLATE['exactAuthorizationCommit']); self.assertIsNone(TEMPLATE['exactAuthorizationParentCommit'])
    def test_05_review_path_count(self): self.assertEqual(BINDING['reviewPathCount'],146); self.assertEqual(len(BINDING['reviewPaths']),146)
    def test_06_scientific_identity(self): self.assertEqual(BINDING['scientificIdentity']['caseCount'],44); self.assertEqual(BINDING['scientificIdentity']['candidateSeedRange'],[970001,970044])
    def test_07_static_verify(self): self.assertEqual(package_evidence.verify_static(REPO)['status'],'STATIC_BINDING_PASS')
    def test_08_matrix_exact(self):
        rows=package_evidence.matrix(REPO); self.assertEqual(len(rows),44); self.assertEqual([r['seed'] for r in rows],list(range(970001,970045)))
    def test_09_review_tree_identity(self): self.assertEqual(BINDING['mergedTreeSha'],'c222260aeb341d9a1aa0f189cfcbd9252a4f46b3')
    def test_10_new_identity_not_v5(self): self.assertTrue(CONTRACT['contractId'].endswith('-v6')); self.assertNotEqual(CONTRACT['contractSha256'],'fb4c003aad2f0655c7d4faadc65e6c6664b7306cd87b134a5eee772f31839fdd')

class FreshnessParserTests(unittest.TestCase):
    def test_11_negative_allocation_not_positive(self):
        self.assertEqual(freshness.positive_candidate_claims('No ordinal 14 allocation, reservation, authorization, or consumption occurred.'),[])
        self.assertEqual(freshness.positive_candidate_claims('No authorization commit/branch, dispatch branch, pilot result, fitting/model selection, holdout/validation opening, or ordinal-14 allocation/reservation/consumption occurred.'),[])
        self.assertEqual(freshness.positive_candidate_claims('control-ledger parsing ignores negative mentions and additionally refuses explicit positive ordinal-14 allocation/authorization claims.'),[])
        self.assertEqual(freshness.positive_candidate_claims('Do not allocate and reserve ordinal 14.'),[])
        self.assertEqual(freshness.positive_candidate_claims('Authorization for ordinal 14 was refused.'),[])
        self.assertEqual(freshness.positive_candidate_claims('ordinal 14 authorization is blocked.'),[])
        self.assertEqual(freshness.positive_candidate_claims('ordinal 14 allocation did not occur.'),[])
        self.assertEqual(freshness.positive_candidate_claims('authorization for ordinal 14 was denied.'),[])
        self.assertEqual(freshness.positive_candidate_claims('ordinal 14 authorization was not granted.'),[])
        self.assertEqual(freshness.positive_candidate_claims('ordinal 14 allocation never occurred.'),[])
        self.assertEqual(freshness.positive_candidate_claims('authorization for ordinal 14 does not exist.'),[])
        self.assertEqual(freshness.positive_candidate_claims('Authorization for ordinal 14 is pending review.'),[])
        self.assertEqual(freshness.positive_candidate_claims('Authorization request for ordinal 14 is pending.'),[])
        self.assertEqual(freshness.positive_candidate_claims('We discussed authorization for ordinal 14 but did not grant it.'),[])
        self.assertEqual(freshness.positive_candidate_claims('It is false that ordinal 14 is authorized.'),[])
        self.assertEqual(freshness.positive_candidate_claims('We cannot authorize ordinal 14.'),[])
        self.assertEqual(freshness.positive_candidate_claims('We have yet to authorize ordinal 14.'),[])
        self.assertEqual(freshness.positive_candidate_claims('Ordinal 14 may be authorized later.'),[])
        self.assertEqual(freshness.positive_candidate_claims('Ordinal 14 will not be authorized.'),[])
        self.assertEqual(freshness.positive_candidate_claims('Ordinal 14 authorization was rescinded.'),[])
        self.assertEqual(freshness.positive_candidate_claims('If ordinal 14 is authorized, do not proceed.'),[])
        self.assertEqual(freshness.positive_candidate_claims('Whether ordinal 14 is authorized remains unknown.'),[])
        self.assertEqual(freshness.positive_candidate_claims('Before ordinal 14 is authorized, refresh the ledger.'),[])
        self.assertEqual(freshness.positive_candidate_claims('No authorization for ordinal 14 was granted.'),[])
        self.assertEqual(freshness.positive_candidate_claims('No ordinal 14 allocation occurred.'),[])
        ops={'allocate':('allocated','allocation'),'reserve':('reserved','reservation'),'authorize':('authorized','authorization'),'consume':('consumed','consumption'),'dispatch':('dispatched','dispatch')}
        for base,(pp,noun) in ops.items():
            for text in (
                f'We did not {base} ordinal 14.', f'We cannot {base} ordinal 14.', f'We may {base} ordinal 14 later.',
                f'We will {base} ordinal 14 later.', f'We plan to {base} ordinal 14.', f'We have yet to {base} ordinal 14.',
                f'If ordinal 14 is {pp}, continue.', f'Whether ordinal 14 is {pp} remains unknown.', f'Before ordinal 14 is {pp}, refresh.',
                f'Ordinal 14 may be {pp} later.', f'Ordinal 14 will not be {pp}.', f'{noun.title()} for ordinal 14 is pending review.',
                f'{noun.title()} request for ordinal 14 is pending.',
                f'Did we {base} ordinal 14?', f'Do we {base} ordinal 14?',
                f'Was ordinal 14 {pp}?', f'Has ordinal 14 been {pp}?',
                f"We haven't {pp} ordinal 14.", f"Ordinal 14 isn't {pp}.",
                f"Ordinal 14 wasn't {pp}.", f"Ordinal 14 hasn't been {pp}.",
                f'We expect ordinal 14 to be {pp}.', f'Ordinal 14 is expected to be {pp}.',
                f'We hope ordinal 14 is {pp}.',
            ):
                self.assertEqual(freshness.positive_candidate_claims(text),[],text)
    def test_12_candidate_only_not_positive(self): self.assertEqual(freshness.positive_candidate_claims('ordinal 14 remains candidate-only and not authorized.'),[])
    def test_13_positive_allocated(self):
        self.assertEqual(len(freshness.positive_candidate_claims('We allocated ordinal 14 for this run.')),1)
        self.assertEqual(len(freshness.positive_candidate_claims('No authorization existed previously, but we allocated ordinal 14 now.')),1)
        self.assertEqual(len(freshness.positive_candidate_claims('We did not reserve ordinal 14 before, but ordinal 14 is now authorized.')),1)
        self.assertEqual(len(freshness.positive_candidate_claims('Ordinal 14 was not reserved, and authorization was granted for ordinal 14.')),1)
        self.assertEqual(len(freshness.positive_candidate_claims('Ordinal 14 was not reserved initially, then ordinal 14 was authorized.')),1)
        self.assertEqual(len(freshness.positive_candidate_claims('Ordinal 14 was not reserved and is now authorized.')),1)
        self.assertEqual(len(freshness.positive_candidate_claims('Ordinal 14 is authorized, and no dispatch has occurred yet.')),1)
        self.assertEqual(len(freshness.positive_candidate_claims('Although no dispatch exists, ordinal 14 is authorized.')),1)
        self.assertEqual(len(freshness.positive_candidate_claims('No prior authorization existed and we allocated ordinal 14 now.')),1)
        self.assertEqual(len(freshness.positive_candidate_claims('We allocated ordinal 14 without dispatching it.')),1)
        self.assertEqual(len(freshness.positive_candidate_claims('Ordinal 14 was allocated while dispatch is not authorized.')),1)
        self.assertEqual(len(freshness.positive_candidate_claims('Not only did we authorize ordinal 14; the branch remains absent.')),1)
        self.assertEqual(len(freshness.positive_candidate_claims('Ordinal 14 was authorized, but later revoked.')),1)
        self.assertEqual(len(freshness.positive_candidate_claims('We allocated ordinal 14 provisionally, subject to approval.')),1)
        self.assertEqual(len(freshness.positive_candidate_claims('Ordinal 14 is not authorized but is allocated.')),1)
        self.assertEqual(len(freshness.positive_candidate_claims('Ordinal 14 is allocated but not authorized.')),1)
        self.assertEqual(len(freshness.positive_candidate_claims('Authorization for ordinal 14 was granted.')),1)
        self.assertEqual(len(freshness.positive_candidate_claims('Ordinal 14 allocation occurred.')),1)
        ops={'allocate':'allocated','reserve':'reserved','authorize':'authorized','consume':'consumed','dispatch':'dispatched'}
        for base,pp in ops.items():
            for text in (
                f'We {pp} ordinal 14.', f'Ordinal 14 is {pp}.', f'Ordinal 14 was {pp}.',
                f'Ordinal 14 has been {pp}.', f'Not only did we {base} ordinal 14.',
                f'We did {base} ordinal 14.', f'We do {base} ordinal 14.',
                f'We have {pp} ordinal 14.',
                f'We {pp} ordinal 14, but dispatch is not authorized.',
            ):
                self.assertEqual(len(freshness.positive_candidate_claims(text)),1,text)
    def test_14_positive_authorized(self): self.assertEqual(len(freshness.positive_candidate_claims('ordinal 14 is authorized for execution.')),1)
    def test_15_marker_positive(self): self.assertEqual(len(freshness.positive_candidate_claims('ORDINAL14_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED commit='+'b'*40+' parent='+'a'*40+' pr=110')),1)
    def test_16_mixed_ordinals_finds_14(self): self.assertEqual(len(freshness.positive_candidate_claims('ordinal 13 was consumed; we now reserve ordinal 14.')),1)
    def test_17_identity_mention_only(self): self.assertEqual(freshness.positive_candidate_claims('Review branch authorization/full-spectrum-estimator-pilot-v2-ordinal14 is absent.'),[])
    def test_18_matching_marker(self): self.assertTrue(freshness.matching_marker('ORDINAL14_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED commit='+'b'*40+' parent='+'a'*40+' pr=110','b'*40,'a'*40,110))

class SurfaceTests(unittest.TestCase):
    def payload(self):
        return {'branches':[{'name':'dispatch/tier1-precision-continuation-wave3-ordinal13-v1','commit':{'sha':'1'*40}}], 'runs':[], 'pulls':[], 'issues':[], 'issue60Comments':[], 'activeAuthorizationPathOnMainExists':False}
    def test_19_surface_prior13(self):
        self.assertEqual(github_surface.build_surface(self.payload())['latestPriorConsumedScientificOrdinal'],13)
        p=self.payload(); p['branches']=[]; p['runs']=[{'id':99,'head_branch':'dispatch/tier1-precision-continuation-wave3-ordinal13-v1','display_title':'old','name':'old'}]; self.assertEqual(github_surface.build_surface(p)['latestPriorConsumedScientificOrdinal'],13)
    def test_20_surface_auth_branch(self):
        p=self.payload();p['branches'].append({'name':freshness.AUTH_BRANCH,'commit':{'sha':'b'*40}}); s=github_surface.build_surface(p); self.assertTrue(s['authorizationBranchExists']); self.assertEqual(s['authorizationBranchHeadSha'],'b'*40)
    def test_21_surface_dispatch_branch(self):
        p=self.payload();p['branches'].append({'name':freshness.DISPATCH_BRANCH,'commit':{'sha':'b'*40}}); self.assertTrue(github_surface.build_surface(p)['dispatchBranchExists'])
    def test_22_current_pr_excluded(self):
        p=self.payload();p['pulls']=[{'number':110,'title':'ordinal 14 authorized','body':''}]; self.assertEqual(github_surface.build_surface(p,current_pr=110)['positiveCandidateClaimsExcludingCurrent'],0)
    def test_23_marker_count_excluded_from_positive(self):
        p=self.payload();p['issue60Comments']=[{'body':'ORDINAL14_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED commit='+'b'*40+' parent='+'a'*40+' pr=110'}]; s=github_surface.build_surface(p,110,'b'*40,'a'*40); self.assertEqual(s['matchingAuthorizationMarkers'],1); self.assertEqual(s['positiveCandidateClaimsExcludingCurrent'],0)
    def test_24_candidate_run_detected(self):
        p=self.payload();p['runs']=[{'id':123,'head_branch':freshness.DISPATCH_BRANCH,'display_title':'x','name':'x'}]; self.assertEqual(github_surface.build_surface(p)['candidatePriorScientificRunCount'],1); self.assertEqual(github_surface.build_surface(p,current_run_id=123)['candidatePriorScientificRunCount'],0)

class AuthorizationTests(unittest.TestCase):
    def test_25_preauthorization_pass(self): self.assertTrue(authorization_guard.preauthorize({'freshness':fresh_base(False,None,0),'authorizationCreated':False,'scientificExecutionPerformed':False})['authorizationCreationPermitted'])
    def test_26_preauthorization_rejects_existing_auth_branch(self):
        with self.assertRaises(Exception): authorization_guard.preauthorize({'freshness':fresh_base(True,'b'*40,0),'authorizationCreated':False,'scientificExecutionPerformed':False})
    def test_27_review_pass(self): self.assertEqual(authorization_guard.review(enabled_auth(),auth_ctx())['status'],'AUTHORIZATION_REVIEW_PASS_ZERO_RUNTIME')
    def test_28_embed_own_sha_rejected(self):
        a=enabled_auth();a['exactAuthorizationCommit']='b'*40
        with self.assertRaises(Exception): authorization_guard.review(a,auth_ctx())
    def test_29_wrong_parent_rejected(self):
        c=auth_ctx();c['parentSha']='c'*40
        with self.assertRaises(Exception): authorization_guard.review(enabled_auth(),c)
    def test_30_extra_file_rejected(self):
        c=auth_ctx();c['changedPaths'].append('x')
        with self.assertRaises(Exception): authorization_guard.review(enabled_auth(),c)
    def test_31_nondraft_rejected(self):
        c=auth_ctx();c['pr']['draft']=False
        with self.assertRaises(Exception): authorization_guard.review(enabled_auth(),c)
    def test_32_cross_repo_rejected(self):
        c=auth_ctx();c['pr']['headRepo']='fork/repo'
        with self.assertRaises(Exception): authorization_guard.review(enabled_auth(),c)
    def test_33_attempt2_rejected(self):
        c=auth_ctx();c['runAttempt']=2
        with self.assertRaises(Exception): authorization_guard.review(enabled_auth(),c)
    def test_34_runtime_setup_rejected(self):
        c=auth_ctx();c['scientificRuntimeSetupPerformed']=True
        with self.assertRaises(Exception): authorization_guard.review(enabled_auth(),c)
    def test_35_positive_claim_rejected(self):
        c=auth_ctx();c['freshness']['positiveCandidateClaimsExcludingCurrent']=1
        with self.assertRaises(Exception): authorization_guard.review(enabled_auth(),c)
    def test_36_real_git_constructibility(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); subprocess.run(['git','init','-q'],cwd=r,check=True); subprocess.run(['git','config','user.email','test@example.invalid'],cwd=r,check=True); subprocess.run(['git','config','user.name','test'],cwd=r,check=True)
            (r/'base').write_text('base\n'); subprocess.run(['git','add','base'],cwd=r,check=True); subprocess.run(['git','commit','-qm','base'],cwd=r,check=True); parent=subprocess.check_output(['git','rev-parse','HEAD'],cwd=r,text=True).strip()
            ap=r/'experiments/full-spectrum-estimator-pilot-v2/authorization.ordinal14.json';ap.parent.mkdir(parents=True);a=enabled_auth(parent);ap.write_text(json.dumps(a,sort_keys=True)+'\n');subprocess.run(['git','add',str(ap.relative_to(r))],cwd=r,check=True);subprocess.run(['git','commit','-qm','auth'],cwd=r,check=True);head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=r,text=True).strip()
            changed=subprocess.check_output(['git','diff-tree','--no-commit-id','--name-only','-r','HEAD'],cwd=r,text=True).splitlines(); c=auth_ctx(head,parent);c['changedPaths']=changed;c['pr']['headSha']=head;c['freshness']['authorizationBranchHeadSha']=head
            self.assertEqual(authorization_guard.review(a,c)['authorizationHead'],head)

class DispatchTests(unittest.TestCase):
    def test_37_dispatch_pass(self): self.assertEqual(dispatch_guard.evaluate(enabled_auth(),dispatch_ctx())['status'],'DISPATCH_ELIGIBLE_NOT_CREATED')
    def test_38_missing_marker(self):
        c=dispatch_ctx();c['issue60Markers']=[];c['freshness']['matchingAuthorizationMarkers']=0
        with self.assertRaises(Exception): dispatch_guard.evaluate(enabled_auth(),c)
    def test_39_wrong_marker(self):
        c=dispatch_ctx();c['issue60Markers']=['ORDINAL14_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED commit='+'c'*40+' parent='+'a'*40+' pr=110']
        with self.assertRaises(Exception): dispatch_guard.evaluate(enabled_auth(),c)
    def test_40_review_attempt2(self):
        c=dispatch_ctx();c['authorizationReview']['runAttempt']=2
        with self.assertRaises(Exception): dispatch_guard.evaluate(enabled_auth(),c)
    def test_41_review_failure(self):
        c=dispatch_ctx();c['authorizationReview']['conclusion']='failure'
        with self.assertRaises(Exception): dispatch_guard.evaluate(enabled_auth(),c)
    def test_42_main_moved(self):
        c=dispatch_ctx();c['liveMain']='c'*40
        with self.assertRaises(Exception): dispatch_guard.evaluate(enabled_auth(),c)
    def test_43_auth_pr_merged(self):
        c=dispatch_ctx();c['pr']['merged']=True
        with self.assertRaises(Exception): dispatch_guard.evaluate(enabled_auth(),c)

class ExecutionGuardTests(unittest.TestCase):
    def test_44_execution_guard_pass(self): self.assertEqual(execution_guard.evaluate(enabled_auth(),exec_ctx())['status'],'SCIENTIFIC_EXECUTION_GUARD_PASS')
    def test_45_wrong_event(self):
        c=exec_ctx();c['eventName']='workflow_dispatch'
        with self.assertRaises(Exception): execution_guard.evaluate(enabled_auth(),c)
    def test_46_wrong_ref(self):
        c=exec_ctx();c['refName']='main'
        with self.assertRaises(Exception): execution_guard.evaluate(enabled_auth(),c)
    def test_47_attempt2(self):
        c=exec_ctx();c['runAttempt']=2
        with self.assertRaises(Exception): execution_guard.evaluate(enabled_auth(),c)
    def test_48_prior_run(self):
        c=exec_ctx();c['priorMatchingScientificRuns']=1
        with self.assertRaises(Exception): execution_guard.evaluate(enabled_auth(),c)
    def test_49_resume_rejected(self):
        c=exec_ctx();c['resumeRequested']=True
        with self.assertRaises(Exception): execution_guard.evaluate(enabled_auth(),c)
    def test_50_head_mismatch(self):
        c=exec_ctx();c['headSha']='c'*40
        with self.assertRaises(Exception): execution_guard.evaluate(enabled_auth(),c)

class ExecutorTests(unittest.TestCase):
    def test_51_alis_resolve(self):
        b=executor.resolve_input(REPO,'train-0009-fs-alis-500-r1',Path('/tmp/data'),Path('/tmp/out')); self.assertIn(b'mc_randomseed 970001',b); self.assertNotIn(b'${',b)
    def test_52_vroom_resolve(self):
        b=executor.resolve_input(REPO,'train-0009-fs-vroom-1nm-r1',Path('/tmp/data'),Path('/tmp/out')); self.assertIn(b'wavelength_grid_file ',b); self.assertNotIn(b'${WAVELENGTH_GRID_1NM}',b)
    def test_53_case_selection(self): self.assertEqual(executor.case_from_manifest(REPO,'train-0047-fs-vroom-1nm-r2')['seed'],970044)
    def test_54_execution_requires_allow(self):
        with self.assertRaises(Exception): executor.execute_case(REPO,'train-0009-fs-alis-500-r1',Path('/tmp/data'),Path('/tmp/out-x'),Path('/bin/false'),Path('/tmp/no'),1,False)
    def _fake_run(self,case_id,td):
        case=next(c for c in MANIFEST['cases'] if c['caseId']==case_id); runtime=MANIFEST['runtimeIdentityRequired']; runtime_path=Path(td)/'runtime.json'; runtime_path.write_text(json.dumps(runtime,sort_keys=True)+'\n'); data=Path('/unused/mock-data-root'); out=Path(td)/'out'
        def portable_resolve(repository_root, requested_case_id, data_dir, output_root):
            template=repository_root/executor.REVIEW_REL/'rendered-review-v5'/requested_case_id/'input-template.txt'
            text=template.read_text()
            replacements={
                '${LIBRADTRAN_DATA}':'/portable/share/libRadtran/data',
                '${ATMOSPHERE_FILE}':'/portable/share/libRadtran/data/atmmod/afglus.dat',
                '${SOLAR_FLUX_FILE}':'/portable/share/libRadtran/data/solar_flux/atlas_plus_modtran',
                '${WAVELENGTH_GRID_1NM}':'/portable/review/wavelength-grid-1nm.dat',
                '${OUTPUT_DIR}':'/portable/output',
            }
            for key,value in replacements.items(): text=text.replace(key,value)
            if '${' in text: raise AssertionError('portable mock left unresolved input placeholder')
            return text.encode()
        def runner(cmd,text,cwd,timeout):
            if len(cmd)==1:
                step=1.0 if case['method']=='reference-vroom-1nm' else .05; n=401 if step==1.0 else 8001; spec=''.join(f'{380+i*step:.2f} 1.0e-6\n' for i in range(n))
                for name in MANIFEST['artifactContract']['requiredMembersByMethod'][case['method']]:
                    if name in {'case-result.json','input-resolved.txt','runtime-report.json','prepared.json','randomseed','syntax-stdout.txt','syntax-stderr.txt','solver-stdout.txt','solver-stderr.txt','wavelength-grid-1nm.dat'}: continue
                    (cwd/name).write_text(spec if name in {'mc.rad.spc','mc.rad.std.spc'} else 'x\n')
            return {'exitCode':0,'timedOut':False,'stdout':'','stderr':''}
        env={'GITHUB_ACTIONS':'true','GITHUB_EVENT_NAME':'push','GITHUB_RUN_ATTEMPT':'1','GITHUB_REF_NAME':freshness.DISPATCH_BRANCH}
        with mock.patch.dict(os.environ,env,clear=False), mock.patch.object(executor,'resolve_input',side_effect=portable_resolve):
            result=executor.execute_case(REPO,case_id,data,out,Path('/fake/uvspec'),runtime_path,10,True,runner=runner)
        resolved=(out/case_id/'input-resolved.txt').read_text().splitlines()
        data_lines=[line for line in resolved if line.startswith('data_files_path ')]
        self.assertEqual(data_lines,['data_files_path /portable/share/libRadtran/data'])
        return case,out/case_id,result
    def _parse_zip(self,case,case_dir,td):
        z=Path(td)/'case.zip'
        with zipfile.ZipFile(z,'w',compression=zipfile.ZIP_DEFLATED) as zz:
            for f in case_dir.iterdir(): zz.write(f,arcname=f'case-output/{case["caseId"]}/{f.name}')
        spec=importlib.util.spec_from_file_location('norm_v6_test',REVIEW/'normalize_full_spectrum_estimator_pilot_results_v6.py'); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        return mod.parse_case_zip(z,case,MANIFEST['artifactContract']['requiredMembersByMethod'][case['method']])
    def test_55_mock_alis_artifact_contract(self):
        with tempfile.TemporaryDirectory(prefix='fspv2-artifact-', dir='/tmp') as td:
            case,d,r=self._fake_run('train-0009-fs-alis-500-r1',td); parsed=self._parse_zip(case,d,td); self.assertEqual(parsed['caseId'],case['caseId']); self.assertEqual(r['solverExecutionCount'],1)
    def test_56_mock_vroom_artifact_contract(self):
        with tempfile.TemporaryDirectory(prefix='fspv2-artifact-', dir='/tmp') as td:
            case,d,r=self._fake_run('train-0009-fs-vroom-1nm-r1',td); parsed=self._parse_zip(case,d,td); self.assertEqual(parsed['method'],'reference-vroom-1nm')

class GitHubApiTransportTests(unittest.TestCase):
    URL='https://api.github.com/repos/search-maker/twilight-mystic-experiments/branches?page=1'
    def test_57_tls_failure_uses_verified_fallback(self):
        with mock.patch.object(github_surface,'_api_with_urllib',side_effect=ssl.SSLCertVerificationError()),mock.patch.object(github_surface,'_api_with_gh',return_value=[{'name':'main'}]) as fallback:
            self.assertEqual(github_surface._api(self.URL,'secret'),[{'name':'main'}]); fallback.assert_called_once_with(self.URL,'secret')
    def test_58_successful_paths_normalize_identically(self):
        payload=[{'name':'main'}]
        with mock.patch.object(github_surface,'_api_with_urllib',return_value=payload): self.assertEqual(github_surface._api(self.URL,'secret'),payload)
        with mock.patch.object(github_surface,'_api_with_urllib',side_effect=ssl.SSLCertVerificationError()),mock.patch.object(github_surface,'_api_with_gh',return_value=payload): self.assertEqual(github_surface._api(self.URL,'secret'),payload)
    def test_59_non_tls_error_is_not_swallowed(self):
        with mock.patch.object(github_surface,'_api_with_urllib',side_effect=urllib.error.URLError('network')),mock.patch.object(github_surface,'_api_with_gh') as fallback:
            with self.assertRaises(urllib.error.URLError): github_surface._api(self.URL,'secret')
            fallback.assert_not_called()
    def test_60_all_verified_transports_fail_closed(self):
        with mock.patch.object(github_surface,'_api_with_urllib',side_effect=ssl.SSLCertVerificationError()),mock.patch.object(github_surface,'_api_with_gh',side_effect=RuntimeError('fallback failed')):
            with self.assertRaisesRegex(RuntimeError,'fallback failed'): github_surface._api(self.URL,'secret')
    def test_61_fallback_refuses_noncanonical_url(self):
        with self.assertRaises(RuntimeError): github_surface._api_with_gh('https://example.invalid/x','secret')

class WorkflowTests(unittest.TestCase):
    def wf(self,name): return (REPO/'.github/workflows'/name).read_text()
    def test_57_transport_review_no_runtime(self):
        t=self.wf('full-spectrum-estimator-pilot-v2-transport-review-v6.yml'); self.assertNotIn('setup-micromamba',t); self.assertNotIn('--allow-execution',t)
    def test_58_auth_review_no_runtime(self):
        t=self.wf('full-spectrum-estimator-pilot-v2-authorization-review-v6.yml'); self.assertNotIn('setup-micromamba',t); self.assertNotIn('command -v uvspec',t)
    def test_59_auth_review_opened_only(self): self.assertIn('types: [opened]',self.wf('full-spectrum-estimator-pilot-v2-authorization-review-v6.yml'))
    def test_60_scientific_push_only(self):
        t=self.wf('full-spectrum-estimator-pilot-v2-ordinal14-execution-v6.yml'); self.assertIn('push:',t); self.assertNotIn('workflow_dispatch:',t); self.assertNotIn('schedule:',t); self.assertIn('GITHUB_RUN_ATTEMPT',t); self.assertEqual(t.count('gh api --paginate --slurp'),2); self.assertIn('for page in comment_pages for c in page',t)
    def test_61_scientific_exact_runtime(self): self.assertIn('rubin-libradtran=2.0.6=py312pl5321he9373c2_1',self.wf('full-spectrum-estimator-pilot-v2-ordinal14-execution-v6.yml'))
    def test_62_no_auto_downstream(self):
        t=self.wf('full-spectrum-estimator-pilot-v2-ordinal14-execution-v6.yml').lower(); self.assertNotIn('model fitting',t); self.assertNotIn('holdout validation',t); self.assertNotIn('tier2',t); self.assertNotIn('production promotion',t)

if __name__=='__main__': unittest.main(verbosity=2)
