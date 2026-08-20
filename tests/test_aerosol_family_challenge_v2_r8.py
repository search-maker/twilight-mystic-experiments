import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
R6=ROOT/'experiments/aerosol-family-challenge-v2'
R7=ROOT/'experiments/aerosol-family-challenge-v2-r7'
R8=ROOT/'experiments/aerosol-family-challenge-v2-r8'

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise RuntimeError(path)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

class AerosolFamilyR8Continuation(unittest.TestCase):
    def test_seed_ledger_is_fresh_relative_to_r6_and_consumed_r7(self):
        s6=json.loads((R6/'candidate-seed-ledger.v1.json').read_text())['candidateSeeds']
        s7=json.loads((R7/'candidate-seed-ledger.v2.json').read_text())['candidateSeeds']
        row=json.loads((R8/'candidate-seed-ledger.v2.json').read_text())
        s8=row['candidateSeeds']
        self.assertEqual('aerosol-family-challenge-v2|group-seed|sha256-v3',row['namespace'])
        self.assertEqual('e90d18b4ecb3a4dd54f372dac4e585708e7478981c6c18ffaa351428625f3302',row['candidateSeedCanonicalSha256'])
        self.assertEqual(72,len(s8)); self.assertEqual(72,len(set(s8)))
        self.assertFalse(set(s6)&set(s8)); self.assertFalse(set(s7)&set(s8))

    def test_manifest_cases_change_only_seed(self):
        r7=load('afc2_r7_test_core_for_r8',R7/'core.py')
        r8=load('afc2_r8_test_core',R8/'core.py')
        d7=json.loads((R7/'design.review.json').read_text())
        d8=json.loads((R8/'design.review.json').read_text())
        m7=r7.build_manifest(d7); m8=r8.build_manifest(d8)
        self.assertEqual(576,len(m7['cases'])); self.assertEqual(576,len(m8['cases']))
        self.assertEqual(m7['configuredPhotonHistoriesTotal'],m8['configuredPhotonHistoriesTotal'])
        for a,b in zip(m7['cases'],m8['cases'],strict=True):
            aa=dict(a); bb=dict(b); aa.pop('seed'); bb.pop('seed')
            self.assertEqual(aa,bb); self.assertNotEqual(a['seed'],b['seed'])
        self.assertEqual('NONE_SEEDS_AND_GOVERNANCE_IDENTITY_ONLY',m8['scientificScopeChange'])

    def test_science_files_are_exact_r7_bytes(self):
        for name in ('analysis-contract.v3.json','analysis.py','derived_channels.py','adapter.py','wavelength-grid-1nm.dat'):
            self.assertEqual((R7/name).read_bytes(),(R8/name).read_bytes(),name)

    def test_prior_r7_consumption_binding_is_exact_and_review_is_fail_closed(self):
        d=json.loads((R8/'design.review.json').read_text())
        prior=d['priorContinuationBinding']
        self.assertEqual(31,prior['consumedScientificOrdinal'])
        self.assertEqual('DISPATCH_REF_CREATED_IDENTITY_CONSUMED_NO_ACTIONS_SCIENTIFIC_RUN',prior['disposition'])
        self.assertEqual('bf5254ff59450ae935705966c51d367a003e97afbcff98a7622b1c310c3ace3b',prior['candidateSeedCanonicalSha256'])
        self.assertFalse(d['scientificExecutionAuthorized']); self.assertFalse(d['solverExecutionAuthorized']); self.assertFalse(d['resultsOpened'])
        review=d['seedFreshnessReview']; self.assertFalse(review['authorizationPermitted'])
        self.assertFalse(review['exactHeadTrackedTreeByteScanPassed']); self.assertFalse(review['repositoryGlobalCollisionSurfaceScanPassed'])
        self.assertEqual('aerosol-family-v2-r8-freeze-proof',review['proofBundleArtifactName'])

if __name__=='__main__': unittest.main()
