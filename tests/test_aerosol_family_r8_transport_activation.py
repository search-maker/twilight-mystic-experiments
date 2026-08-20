import importlib.util
import json
import sys
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'experiments/aerosol-family-challenge-v2-r8'
CAND=BASE/'execution-candidate'
AUTH=ROOT/'.github/workflows/aerosol-family-v2-r8-authorization-review.yml'
EXEC=ROOT/'.github/workflows/aerosol-family-v2-r8-execution.yml'
PUB=ROOT/'.github/workflows/aerosol-family-v2-r8-dispatch-publisher.yml'

def load(name,path):
    sys.path.insert(0,str(path.parent))
    try:
        spec=importlib.util.spec_from_file_location(name,path)
        if spec is None or spec.loader is None: raise RuntimeError(path)
        mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
    finally: sys.path.pop(0)

class R8Transport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fresh=load('afc2_r8_transport_fresh',CAND/'freshness.py')
        sys.modules['freshness']=cls.fresh
        cls.surface=load('afc2_r8_transport_surface',CAND/'authorization_surface.py')

    def payload(self,n=32,consumed=False,dispatch=False):
        auth=self.fresh.authorization_branch(n); disp=self.fresh.dispatch_branch(n)
        branches=[{'name':'main','commit':{'sha':'1'*40}},{'name':'dispatch/other-project-ordinal-31','commit':{'sha':'2'*40}},{'name':auth,'commit':{'sha':'3'*40}}]
        if dispatch: branches.append({'name':disp,'commit':{'sha':'3'*40}})
        comments=[]
        if consumed: comments.append({'id':9,'body':self.fresh.consumed_marker(n)})
        return {'branches':branches,'runs':[],'artifacts':[],'pulls':[],'issues':[],'issueComments':list(comments),'pullReviewComments':[],'commitComments':[],'issue60Comments':comments}

    def test_current_consumed_marker_does_not_advance_latest_prior(self):
        out=self.surface.build_surface(self.payload(consumed=True,dispatch=True),32)
        self.assertEqual(31,out['latestPriorConsumedScientificOrdinal'])
        self.assertEqual(32,out['nextAvailableScientificOrdinal'])
        self.assertEqual(1,out['currentConsumedMarkerCount'])

    def test_dispatch_requires_zero_marker_before_and_one_after(self):
        pre=self.surface.build_surface(self.payload(),32)
        pre['matchingAuthorizationMarkers']=1
        self.fresh.validate_dispatch(pre,32,'3'*40,post_dispatch=False)
        post=self.surface.build_surface(self.payload(consumed=True,dispatch=True),32)
        post['matchingAuthorizationMarkers']=1
        self.fresh.validate_dispatch(post,32,'3'*40,post_dispatch=True)
        post['currentConsumedMarkerCount']=2
        with self.assertRaises(Exception): self.fresh.validate_dispatch(post,32,'3'*40,post_dispatch=True)

    def test_execution_is_workflow_dispatch_only_and_publisher_evidence_precedes_guard(self):
        text=EXEC.read_text()
        self.assertIn('workflow_dispatch:',text)
        self.assertNotIn('push:\n    branches:\n      - "dispatch/aerosol-family-challenge-v2-r8-ordinal-*"',text)
        self.assertIn('Resolve exact successful actual-git-push publisher evidence',text)
        self.assertNotIn('Consume dispatch identity exactly once before any scientific runtime setup',text)
        self.assertIn('  cases-dep2:',text)
        self.assertIn('steps: &case_steps',text)
        self.assertEqual(3,text.count('steps: *case_steps'))
        self.assertLess(text.index('Resolve exact successful actual-git-push publisher evidence'),text.index('Evaluate exact one-use dispatch guard before scientific runtime setup'))

    def test_publisher_performs_actual_git_push_then_marker_then_explicit_dispatch(self):
        text=PUB.read_text()
        self.assertIn('git push origin "$AUTH_HEAD:refs/heads/$DISPATCH_BRANCH"',text)
        self.assertIn('export ORDINAL AUTH_HEAD AUTH_BRANCH DISPATCH_BRANCH AUTH_PARENT',text)
        self.assertLess(text.index('export ORDINAL AUTH_HEAD AUTH_BRANCH DISPATCH_BRANCH AUTH_PARENT'),text.index("os.environ['AUTH_BRANCH']"))
        self.assertNotIn('/git/refs',text)
        self.assertIn('ORDINAL${ORDINAL}_AEROSOL_FAMILY_V2_R8_DISPATCH_CONSUMED',text)
        self.assertIn('aerosol-family-v2-r8-execution.yml/dispatches',text)
        self.assertLess(text.index('git push origin'),text.index('DISPATCH_CONSUMED'))
        self.assertLess(text.index('DISPATCH_CONSUMED'),text.index('aerosol-family-v2-r8-execution.yml/dispatches'))
        self.assertNotIn('setup-micromamba',text)
        self.assertNotIn('--allow-execution',text)

    def test_authorization_binds_publisher_and_science_scope_unchanged(self):
        template=json.loads((CAND/'authorization.template.json').read_text())
        self.assertIn('dispatchPublisherWorkflowRawSha256',template)
        contract=json.loads((CAND/'transport-contract.v3.json').read_text())
        self.assertEqual(576,contract['caseUniverse']['caseCount'])
        self.assertEqual(72,contract['caseUniverse']['comparisonGroupCount'])
        self.assertEqual(11520000000,contract['caseUniverse']['configuredPhotonHistories'])
        self.assertFalse(contract['scientificExecutionAuthorized'])
        self.assertFalse(contract['solverExecutionAuthorized'])
        self.assertTrue(contract['dispatchPublisher']['actualGitPushRequired'])
        self.assertTrue(contract['dispatchPublisher']['restRefCreationForbidden'])
        self.assertFalse(contract['dispatchPublisher']['githubTokenPushReliedUponToTriggerScience'])

    def test_authorization_review_is_zero_runtime_and_knows_publisher_binding(self):
        text=AUTH.read_text()
        self.assertIn('types: [opened]',text)
        self.assertIn('dispatchPublisherWorkflow',text)
        self.assertNotIn('setup-micromamba',text)
        self.assertNotIn('--allow-execution',text)

if __name__=='__main__': unittest.main()
