from __future__ import annotations
import hashlib, json, sys, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
EXECD=ROOT/'experiments/aerosol-optical-property-sensitivity-v1/execution-candidate'
sys.path.insert(0,str(EXECD))
import control_surface, global_ordinal

H='aec35f62bf4971d871b5ae2a50bff6cdfb107ac4'
AUTH='authorization/aerosol-optical-property-sensitivity-v1-ordinal-36'
HIST='history/aerosol-optical-property-sensitivity-v1-ordinal-36-auth-review-failed-1'

def payload():
    return {
        'branches':[{'name':AUTH,'commit':{'sha':H}},{'name':HIST,'commit':{'sha':H}}],
        'runs':[{'id':32612380809,'head_branch':AUTH,'head_sha':H,'path':'.github/workflows/aops-v1-authorization-review.yml','event':'pull_request','run_attempt':1,'status':'completed','conclusion':'failure'}],
        'artifacts':[],
        'pulls':[{'number':299,'state':'closed','merged_at':None,'head':{'ref':AUTH,'sha':H},'title':'failed review','body':''}],
        'issues':[], 'issueComments':[], 'pullReviewComments':[], 'commitComments':[],
        'issue60Comments':[{'id':1,'body':'ORDINAL35_AEROSOL_FAMILY_V2_R8_TIMEOUT_RECOVERY_V1_DISPATCH_CONSUMED'}],
    }

class Recovery(unittest.TestCase):
    def test_failed_review_reuses_unconsumed_ordinal(self):
        p=payload()
        n,obs=global_ordinal.derive_next_global_ordinal(p,35)
        self.assertEqual(n,36)
        self.assertEqual(max(int(x['ordinal']) for x in obs),36)
        h=global_ordinal.failed_authorization_history(p,36)
        self.assertEqual(h['heads'],[H])
        self.assertEqual(h['prNumbers'],[299])
        self.assertEqual(h['reviewRunIds'],[32612380809])

    def test_control_surface_marks_exact_failed_head_reusable(self):
        s=control_surface.build_surface(payload(),36,active_authorization_path_on_main_exists=False,candidate_code_paths_on_main_inspected=True,candidate_seed_authorization_recheck_passed=True,allow_authorization_branch=False,allow_dispatch_branch=False)
        self.assertTrue(s['authorizationBranchExists'])
        self.assertTrue(s['authorizationBranchReusableAfterFailedReview'])
        self.assertEqual(s['positiveCandidateClaimsExcludingCurrent'],0)
        self.assertEqual(s['candidateExecutionKeyPriorUseCount'],0)
        self.assertEqual(s['currentConsumedMarkerCount'],0)

    def test_both_transport_guards_supply_execution_design(self):
        for rel in ('.github/workflows/aops-v1-authorization-review.yml','.github/workflows/aops-v1-dispatch-publisher.yml'):
            text=(ROOT/rel).read_text()
            self.assertIn("'executionDesign':stage/'execution_design.py'",text)

    def test_transport_bindings_match_changed_bytes(self):
        c=json.loads((ROOT/'experiments/aerosol-optical-property-sensitivity-v1/transport-contract.v1.json').read_text())
        for rel in (
            '.github/workflows/aops-v1-authorization-review.yml',
            '.github/workflows/aops-v1-dispatch-publisher.yml',
            'experiments/aerosol-optical-property-sensitivity-v1/execution-candidate/control_surface.py',
            'experiments/aerosol-optical-property-sensitivity-v1/execution-candidate/global_ordinal.py',
        ):
            data=(ROOT/rel).read_bytes()
            blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
            self.assertEqual(c['gitBlobBindings'][rel],blob)
