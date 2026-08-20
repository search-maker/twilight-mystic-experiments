import importlib.util
import sys
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'experiments/aerosol-family-challenge-v2-r8'
CAND=BASE/'execution-candidate'
WORKFLOW=ROOT/'.github/workflows/aerosol-family-v2-r8-preauthorization-audit.yml'


def load(name,path):
    sys.path.insert(0,str(path.parent))
    try:
        spec=importlib.util.spec_from_file_location(name,path)
        if spec is None or spec.loader is None:
            raise RuntimeError(path)
        mod=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        sys.path.pop(0)


class R8PreauthorizationAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fresh=load('afc2_r8_preauth_fresh',CAND/'freshness.py')
        sys.modules['freshness']=cls.fresh
        cls.surface=load('afc2_r8_preauth_surface',CAND/'authorization_surface.py')
        cls.auth=load('afc2_r8_preauth_auth',CAND/'authorization_guard.py')
        cls.ordinal=load('afc2_r8_preauth_ordinal',CAND/'preauthorization_ordinal.py')

    def clean_payload(self):
        return {
            'branches':[
                {'name':'main','commit':{'sha':'1'*40}},
                {'name':'dispatch/other-project-ordinal-31','commit':{'sha':'2'*40}},
            ],
            'runs':[], 'artifacts':[], 'pulls':[], 'issues':[],
            'issueComments':[], 'pullReviewComments':[], 'commitComments':[], 'issue60Comments':[],
        }

    def test_existing_guard_derives_and_accepts_only_fresh_next_identity(self):
        payload=self.clean_payload()
        latest=self.surface._latest_consumed_ordinal(payload,'__none__',-1)
        self.assertEqual(31,latest)
        candidate,observations=self.ordinal.derive_next_global_ordinal(payload,latest)
        self.assertEqual(31,max(row['ordinal'] for row in observations))
        surface=self.surface.build_surface(payload,candidate,candidate_code_paths_on_main_inspected=True)
        out=self.auth.preauthorize({
            'freshness':surface,
            'authorizationCreated':False,
            'scientificRuntimeSetupPerformed':False,
            'scientificExecutionPerformed':False,
        },candidate)
        self.assertEqual('PREAUTHORIZATION_FRESHNESS_PASS_AUTHORIZATION_CREATION_PERMITTED',out['status'])
        self.assertFalse(out['ordinalAllocatedReservedOrConsumedByReview'])
        with self.assertRaises(Exception):
            self.auth.preauthorize({
                'freshness':surface,
                'authorizationCreated':False,
                'scientificRuntimeSetupPerformed':False,
                'scientificExecutionPerformed':False,
            },candidate+1)


    def test_global_reserved_identity_ahead_of_consumed_refuses_candidate(self):
        payload=self.clean_payload()
        payload['branches'].append({'name':'authorization/other-project-ordinal-32','commit':{'sha':'4'*40}})
        latest=self.surface._latest_consumed_ordinal(payload,'__none__',-1)
        self.assertEqual(31,latest)
        with self.assertRaises(self.ordinal.GlobalOrdinalRefusal):
            self.ordinal.derive_next_global_ordinal(payload,latest)

    def test_positive_global_allocation_claim_ahead_of_consumed_refuses_candidate(self):
        payload=self.clean_payload()
        payload['issues']=[{'id':8,'title':'control','body':'We authorized ordinal 32 for another scientific execution.'}]
        latest=self.surface._latest_consumed_ordinal(payload,'__none__',-1)
        with self.assertRaises(self.ordinal.GlobalOrdinalRefusal):
            self.ordinal.derive_next_global_ordinal(payload,latest)

    def test_consumed_candidate_marker_refuses_preauthorization(self):
        payload=self.clean_payload()
        payload['issue60Comments']=[{'id':1,'body':self.fresh.consumed_marker(32)}]
        payload['issueComments']=list(payload['issue60Comments'])
        surface=self.surface.build_surface(payload,32,candidate_code_paths_on_main_inspected=True)
        self.assertEqual(1,surface['currentConsumedMarkerCount'])
        with self.assertRaises(Exception):
            self.auth.preauthorize({
                'freshness':surface,
                'authorizationCreated':False,
                'scientificRuntimeSetupPerformed':False,
                'scientificExecutionPerformed':False,
            },32)

    def test_workflow_is_attempt1_exact_main_zero_runtime_and_no_transition(self):
        text=WORKFLOW.read_text()
        self.assertIn('test "$GITHUB_RUN_ATTEMPT" = 1',text)
        self.assertIn('test "$GITHUB_REF_NAME" = main',text)
        self.assertIn('experiments/aerosol-family-challenge-v2-r8/execution-candidate/preauthorization_ordinal.py',text)
        self.assertIn('tests/test_aerosol_family_r8_preauthorization_audit.py',text)
        self.assertIn('test "$(git rev-parse origin/main)" = "$GITHUB_SHA"',text)
        self.assertIn('tracked_tree_seed_scan.py',text)
        self.assertIn('repository_global_seed_scan.py',text)
        self.assertIn('--audit-mode authorization-recheck',text)
        self.assertIn('--expected-branch-name main',text)
        self.assertIn('from authorization_guard import preauthorize',text)
        self.assertIn('from preauthorization_ordinal import derive_next_global_ordinal',text)
        self.assertIn('global-ordinal-surface.json',text)
        self.assertIn("'status':'PREAUTHORIZATION_SURFACE_CLEAN_NOT_ALLOCATED'",text)
        self.assertIn("'scientificOrdinalAllocated':False",text)
        self.assertIn("'authorizationCreated':False",text)
        self.assertIn("'dispatchCreated':False",text)
        self.assertNotIn('setup-micromamba',text)
        self.assertNotIn('--allow-execution',text)
        self.assertNotIn('git push origin',text)
        self.assertNotIn('/dispatches',text)
        self.assertNotIn('AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED',text)
        self.assertNotIn('AUTHORIZED_PENDING_SEPARATE_DISPATCH',text)
        self.assertNotIn("'scientificExecutionAuthorized':True",text)
        self.assertNotIn("'solverExecutionAuthorized':True",text)
        self.assertNotIn('gh api',text)
        self.assertIn('issues: write',text)
        self.assertIn('id: upload',text)
        self.assertIn('steps.upload.outputs.artifact-id',text)
        self.assertIn('steps.upload.outputs.artifact-digest',text)
        self.assertIn("method='POST'",text)
        self.assertIn('/issues/60/comments',text)
        self.assertIn('AFC2-R8-PREAUTHORIZATION-RUN',text)
        self.assertIn('next_if_separately_allocated=',text)
        self.assertNotIn('ordinal=',text)
        self.assertIn('Print terminal non-allocation readback',text)
        self.assertIn('Publish terminal observable checkpoint to Issue 60',text)
        self.assertLess(text.index('Persist zero-runtime preauthorization evidence'),text.index('Publish terminal observable checkpoint to Issue 60'))

    def test_artifact_name_does_not_claim_a_candidate_identity(self):
        text=WORKFLOW.read_text()
        self.assertIn('name: aerosol-family-v2-r8-preauthorization-proof',text)
        self.assertNotIn('preauthorization-proof-ordinal-',text)
        self.assertIn('next_if_separately_allocated=',text)


if __name__=='__main__':
    unittest.main()
