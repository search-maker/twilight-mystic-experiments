#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
CORE=ROOT/'review/level-b-v2-densified58-fresh-validation-implementation-v1/fresh_validation_v1.py'
MANIFEST=ROOT/'experiments/level-b-v2-densified58-fresh-validation-v1/build_manifest_v1.py'
CONTRACT=ROOT/'review/level-b-v2-densified58-fresh-validation-v1/contract-v1.json'

def mod(name,path):
    s=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
core=mod('fresh_validation_core_test',CORE)
manifest_mod=mod('fresh_validation_manifest_test',MANIFEST)

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract=json.loads(CONTRACT.read_text())

    def test_exact_case_universe_and_seed_order(self):
        rows=core.expected_cases(self.contract)
        self.assertEqual(len(rows),24)
        self.assertEqual([r['seed'] for r in rows],list(range(2101000001,2101000025)))
        self.assertEqual([r['block'] for r in rows[:4]],[1,2,3,4])
        self.assertTrue(all(r['photonHistories']==40_000_000 and r['alisSpectralImportanceSamplingNm']==550.0 for r in rows))

    def test_manifest_is_review_only_and_exact_budget(self):
        m=manifest_mod.build(ROOT,self.contract)
        self.assertEqual(m['manifestId'],'level-b-v2-densified58-fresh-validation-execution-manifest-v1')
        self.assertEqual((m['geometryCount'],m['caseCount'],m['configuredPhotonHistories']),(6,24,960_000_000))
        self.assertFalse(m['closedUntilAuthorization']['scientificOrdinalAllocated'])
        self.assertFalse(m['closedUntilAuthorization']['protectedHoldoutOpeningAuthorized'])
        self.assertFalse(m['closedUntilAuthorization']['holdoutValuesMayBeRead'])
        self.assertFalse(m['closedUntilAuthorization']['scientificSolverExecutionAuthorized'])
        self.assertEqual(len({c['caseId'] for c in m['cases']}),24)

    def good_records(self):
        records=[]
        for i in range(6):
            channel_errors={}
            for channel in core.CHANNELS:
                channel_errors[channel]={'signedLogError':0.01,'absoluteLogError':0.01,'uncertaintyNormalizedError':0.20,'baselineAbsoluteLogError':0.20}
            records.append({'geometryId':f'synthetic-{i}','insideValidatedSupport':True,'channelErrors':channel_errors,'shapePerCaseNrmse':0.20,'shapeWorstSingleCoefficientNormalizedError':0.40})
        return records

    def test_synthetic_pass_uses_baseline_ratio(self):
        s=core.summarize_records(self.good_records(),self.contract)
        self.assertTrue(s['supportPass'])
        self.assertTrue(s['shapePass'])
        self.assertTrue(s['baselinePass'])
        self.assertAlmostEqual(s['aggregatePrimaryMeanAbsoluteLogError'],0.01)
        self.assertAlmostEqual(s['frozenTrainingMeanBaselinePrimaryMeanAbsoluteLogErrorOnHoldout'],0.20)
        self.assertAlmostEqual(s['aggregateToBaselineFraction'],0.05)
        self.assertTrue(s['definitionOfDonePassed'])

    def test_primary_worst_gate_failure_cannot_be_hidden_by_good_mean(self):
        records=self.good_records()
        records[5]['channelErrors']['photopicLuminanceCdM2']['signedLogError']=0.36
        records[5]['channelErrors']['photopicLuminanceCdM2']['absoluteLogError']=0.36
        records[5]['channelErrors']['photopicLuminanceCdM2']['uncertaintyNormalizedError']=2.0
        s=core.summarize_records(records,self.contract)
        self.assertFalse(s['channelSummary']['photopicLuminanceCdM2']['passes'])
        self.assertFalse(s['definitionOfDonePassed'])

    def test_uncertainty_gate_failure_is_terminal(self):
        records=self.good_records()
        records[0]['channelErrors']['scotopicLuminanceScotCdM2']['uncertaintyNormalizedError']=3.0000001
        s=core.summarize_records(records,self.contract)
        self.assertFalse(s['channelSummary']['scotopicLuminanceScotCdM2']['passes'])
        self.assertFalse(s['definitionOfDonePassed'])

    def test_shape_gate_failure_is_terminal(self):
        records=self.good_records()
        records[-1]['shapePerCaseNrmse']=1.2500001
        s=core.summarize_records(records,self.contract)
        self.assertFalse(s['shapePass'])
        self.assertFalse(s['definitionOfDonePassed'])

    def test_zero_or_missing_primary_error_cannot_pass(self):
        records=self.good_records()
        records[2]['insideValidatedSupport']=False
        records[2]['channelErrors']['johnsonVEffectiveRadiance_mW_m2_nm_sr']={'signedLogError':None,'absoluteLogError':None,'uncertaintyNormalizedError':None,'baselineAbsoluteLogError':None}
        s=core.summarize_records(records,self.contract)
        self.assertFalse(s['supportPass'])
        self.assertFalse(s['channelSummary']['johnsonVEffectiveRadiance_mW_m2_nm_sr']['passes'])
        self.assertFalse(s['baselinePass'])
        self.assertFalse(s['definitionOfDonePassed'])

if __name__=='__main__': unittest.main()
