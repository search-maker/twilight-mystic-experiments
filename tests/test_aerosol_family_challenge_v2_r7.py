import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
R6=ROOT/'experiments/aerosol-family-challenge-v2'
R7=ROOT/'experiments/aerosol-family-challenge-v2-r7'

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise RuntimeError(path)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

class AerosolFamilyR7Continuation(unittest.TestCase):
    def test_seed_ledger_is_fresh_relative_to_r6_ledger(self):
        old=json.loads((R6/'candidate-seed-ledger.v1.json').read_text())['candidateSeeds']
        new=json.loads((R7/'candidate-seed-ledger.v2.json').read_text())['candidateSeeds']
        self.assertEqual(72,len(new)); self.assertEqual(72,len(set(new))); self.assertFalse(set(old)&set(new))

    def test_manifest_changes_only_seed_and_continuation_governance(self):
        r6=load('afc2_r6_test_core',R6/'core.py')
        r7=load('afc2_r7_test_core',R7/'core.py')
        old_design=json.loads((R6/'design.review.json').read_text())
        new_design=json.loads((R7/'design.review.json').read_text())
        old=r6.build_manifest(old_design); new=r7.build_manifest(new_design)
        self.assertEqual(576,len(old['cases'])); self.assertEqual(576,len(new['cases']))
        self.assertEqual(old['configuredPhotonHistoriesTotal'],new['configuredPhotonHistoriesTotal'])
        for a,b in zip(old['cases'],new['cases'],strict=True):
            aa=dict(a); bb=dict(b); aa.pop('seed'); bb.pop('seed')
            self.assertEqual(aa,bb)
            self.assertNotEqual(a['seed'],b['seed'])
        self.assertEqual('NONE_SEEDS_AND_GOVERNANCE_IDENTITY_ONLY',new['scientificScopeChange'])

    def test_r7_review_is_fail_closed_and_non_authorizing(self):
        design=json.loads((R7/'design.review.json').read_text())
        self.assertFalse(design['scientificExecutionAuthorized']); self.assertFalse(design['solverExecutionAuthorized']); self.assertFalse(design['resultsOpened'])
        review=design['seedFreshnessReview']
        self.assertFalse(review['authorizationPermitted'])
        self.assertFalse(review['exactHeadTrackedTreeByteScanPassed'])
        self.assertFalse(review['repositoryGlobalCollisionSurfaceScanPassed'])
        self.assertEqual('aerosol-family-v2-r7-freeze-proof',review['proofBundleArtifactName'])

if __name__=='__main__': unittest.main()
