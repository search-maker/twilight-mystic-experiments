#!/usr/bin/env python3
from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent
MODULE_PATH = ROOT / 'analyze_full_spectrum_estimator_pilot_v7_compat.py'
V7_CONTRACT_PATH = ROOT.parents[1] / 'experiments' / 'full-spectrum-estimator-pilot-v2' / 'postprocess-contract.ordinal16.v7.json'
V8_CONTRACT_PATH = ROOT.parents[1] / 'experiments' / 'full-spectrum-estimator-pilot-v2' / 'postprocess-analyzer-contract.ordinal16.v8.json'
WORKFLOW_PATH = ROOT.parents[1] / '.github' / 'workflows' / 'full-spectrum-estimator-pilot-v2-ordinal16-postprocess-v8.yml'

spec = importlib.util.spec_from_file_location('postprocess_analyzer_v7_compat', MODULE_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError('cannot import compatibility analyzer')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def load_json(path: Path):
    return json.loads(path.read_text())


def case_rows():
    rows = []
    for i in range(44):
        rows.append({
            'caseId': f'case-{i:02d}',
            'geometryId': f'g-{i // 4:02d}',
            'method': 'reference-vroom-1nm' if i % 4 < 2 else 'alis-alt-importance',
            'replicate': (i % 2) + 1,
            'seed': 970001 + i,
            'photonHistories': 1000,
            'importanceCenterNm': None if i % 4 < 2 else 550.0,
            'channels': {
                'photopicLuminanceCdM2': 1.0,
                'scotopicLuminanceScotCdM2': 1.0,
                'johnsonVEffectiveRadiance_mW_m2_nm_sr': 1.0,
            },
        })
    return rows


def acquisition():
    return {'cases': [
        {k: row[k] for k in ('caseId', 'geometryId', 'method', 'replicate', 'seed', 'photonHistories', 'importanceCenterNm')}
        for row in case_rows()
    ]}


def base_evidence(v7_contract):
    value = {
        'schemaVersion': 1,
        'evidenceId': mod.V7_EVIDENCE_ID,
        'status': 'COMPLETE_NORMALIZED_PILOT_EVIDENCE',
        'protocolSha256': mod.v6.ACQUISITION_PROTOCOL_SHA,
        'executionManifestSha256': mod.v6.EXEC_SHA,
        'caseCount': 44,
        'holdoutValuesRead': False,
        'cases': case_rows(),
        'postprocessAdapter': mod.expected_postprocess_adapter(v7_contract),
    }
    value['evidenceSha256'] = mod.v6.canon(value)
    return value


class CompatibilityAnalyzerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v7_contract = load_json(V7_CONTRACT_PATH)
        cls.v8_contract = load_json(V8_CONTRACT_PATH)

    def _evidence_bound_to_contract(self):
        evidence = base_evidence(self.v7_contract)
        # Unit fixtures are synthetic; bind the contract to the fixture self-hash
        # while testing logic. Exact production SHA binding is separately asserted.
        contract = copy.deepcopy(self.v8_contract)
        contract['normalizedEvidenceV7Sha256'] = evidence['evidenceSha256']
        contract['contractSha256'] = None
        contract['contractSha256'] = mod._self_hash(contract, 'contractSha256')
        return evidence, contract

    def test_exact_adapter_reaches_frozen_v6_without_mutating_v7(self):
        evidence, contract = self._evidence_bound_to_contract()
        before = copy.deepcopy(evidence)
        captured = {}

        def fake_analyze(acq, ap, admission, compat):
            captured['compat'] = copy.deepcopy(compat)
            return {
                'analysisId': 'public-tier1-full-spectrum-estimator-pilot-analysis-v6',
                'status': 'PILOT_SCREENING_ANALYZED_NO_AUTOMATIC_ESTIMATOR_SELECTION',
                'normalizedEvidenceSha256': compat['evidenceSha256'],
                'classificationCounts': {'SYNTHETIC': 1},
                'analysisSha256': 'a' * 64,
            }

        with mock.patch.object(mod, 'EXPECTED_V7_EVIDENCE_SHA256', evidence['evidenceSha256']), \
             mock.patch.object(mod.v6, 'analyze', side_effect=fake_analyze):
            result = mod.analyze_v7_compat(acquisition(), {}, {}, evidence, self.v7_contract, contract)

        self.assertEqual(evidence, before)
        self.assertEqual(captured['compat']['evidenceId'], mod.V6_EVIDENCE_ID)
        self.assertNotIn('postprocessAdapter', captured['compat'])
        compat_sha = captured['compat']['evidenceSha256']
        self.assertEqual(compat_sha, mod.v6.canon({k: v for k, v in captured['compat'].items() if k != 'evidenceSha256'}))
        self.assertEqual(result['normalizedEvidenceV7Sha256'], evidence['evidenceSha256'])
        self.assertEqual(result['compatibilityEvidenceV6Sha256'], compat_sha)
        self.assertFalse(result['scientificSolverReexecuted'])
        self.assertFalse(result['holdoutOpeningAuthorized'])

    def test_production_contract_binds_exact_observed_v7_evidence_sha(self):
        self.assertEqual(self.v8_contract['normalizedEvidenceV7Sha256'], mod.EXPECTED_V7_EVIDENCE_SHA256)
        self.assertEqual(mod.EXPECTED_V7_EVIDENCE_SHA256, 'd0979b6827f80e2f2b76f62340a72dcec14a3cb016b9645680c38da0d5fcf0f5')

    def test_wrong_evidence_id_refused(self):
        evidence, contract = self._evidence_bound_to_contract()
        evidence['evidenceId'] = 'wrong'
        evidence['evidenceSha256'] = mod.v6.canon({k: v for k, v in evidence.items() if k != 'evidenceSha256'})
        contract['normalizedEvidenceV7Sha256'] = evidence['evidenceSha256']
        contract['contractSha256'] = None
        contract['contractSha256'] = mod._self_hash(contract, 'contractSha256')
        with mock.patch.object(mod, 'EXPECTED_V7_EVIDENCE_SHA256', evidence['evidenceSha256']):
            with self.assertRaisesRegex(ValueError, 'evidence identity drift'):
                mod.build_v6_compatibility_view(evidence, self.v7_contract, contract)

    def test_wrong_v7_contract_hash_refused(self):
        evidence, contract = self._evidence_bound_to_contract()
        bad = copy.deepcopy(self.v7_contract)
        bad['contractSha256'] = '0' * 64
        with mock.patch.object(mod, 'EXPECTED_V7_EVIDENCE_SHA256', evidence['evidenceSha256']):
            with self.assertRaises(ValueError):
                mod.build_v6_compatibility_view(evidence, bad, contract)

    def test_source_run_head_attempt_adapter_drift_refused(self):
        for key, value in (
            ('sourceScientificRunId', 1),
            ('sourceScientificRunAttempt', 2),
            ('sourceScientificHeadSha', '0' * 40),
        ):
            evidence, contract = self._evidence_bound_to_contract()
            evidence['postprocessAdapter'][key] = value
            evidence['evidenceSha256'] = mod.v6.canon({k: v for k, v in evidence.items() if k != 'evidenceSha256'})
            contract['normalizedEvidenceV7Sha256'] = evidence['evidenceSha256']
            contract['contractSha256'] = None
            contract['contractSha256'] = mod._self_hash(contract, 'contractSha256')
            with mock.patch.object(mod, 'EXPECTED_V7_EVIDENCE_SHA256', evidence['evidenceSha256']):
                with self.assertRaisesRegex(ValueError, 'adapter provenance drift'):
                    mod.build_v6_compatibility_view(evidence, self.v7_contract, contract)

    def test_missing_or_extra_adapter_provenance_refused(self):
        for mutate in ('missing', 'extra'):
            evidence, contract = self._evidence_bound_to_contract()
            if mutate == 'missing':
                evidence['postprocessAdapter'].pop('normalizerVersion')
            else:
                evidence['postprocessAdapter']['unexpected'] = True
            evidence['evidenceSha256'] = mod.v6.canon({k: v for k, v in evidence.items() if k != 'evidenceSha256'})
            contract['normalizedEvidenceV7Sha256'] = evidence['evidenceSha256']
            contract['contractSha256'] = None
            contract['contractSha256'] = mod._self_hash(contract, 'contractSha256')
            with mock.patch.object(mod, 'EXPECTED_V7_EVIDENCE_SHA256', evidence['evidenceSha256']):
                with self.assertRaisesRegex(ValueError, 'adapter provenance drift'):
                    mod.build_v6_compatibility_view(evidence, self.v7_contract, contract)

    def test_protocol_execution_and_holdout_boundary_drift_refused(self):
        mutations = (
            ('protocolSha256', '0' * 64, 'acquisition protocol drift'),
            ('executionManifestSha256', '0' * 64, 'execution manifest drift'),
            ('holdoutValuesRead', True, 'protected-boundary drift'),
        )
        for key, value, reason in mutations:
            evidence, contract = self._evidence_bound_to_contract()
            evidence[key] = value
            evidence['evidenceSha256'] = mod.v6.canon({k: v for k, v in evidence.items() if k != 'evidenceSha256'})
            contract['normalizedEvidenceV7Sha256'] = evidence['evidenceSha256']
            contract['contractSha256'] = None
            contract['contractSha256'] = mod._self_hash(contract, 'contractSha256')
            with mock.patch.object(mod, 'EXPECTED_V7_EVIDENCE_SHA256', evidence['evidenceSha256']):
                with self.assertRaisesRegex(ValueError, reason):
                    mod.build_v6_compatibility_view(evidence, self.v7_contract, contract)

    def test_case_universe_drift_refused_before_frozen_analyzer(self):
        evidence, contract = self._evidence_bound_to_contract()
        evidence['cases'][0]['seed'] += 1
        evidence['evidenceSha256'] = mod.v6.canon({k: v for k, v in evidence.items() if k != 'evidenceSha256'})
        contract['normalizedEvidenceV7Sha256'] = evidence['evidenceSha256']
        contract['contractSha256'] = None
        contract['contractSha256'] = mod._self_hash(contract, 'contractSha256')
        with mock.patch.object(mod, 'EXPECTED_V7_EVIDENCE_SHA256', evidence['evidenceSha256']):
            with self.assertRaisesRegex(ValueError, 'case mismatch'):
                mod.analyze_v7_compat(acquisition(), {}, {}, evidence, self.v7_contract, contract)

    def test_workflow_is_zero_solver_surface(self):
        text = WORKFLOW_PATH.read_text()
        forbidden = ('micromamba', 'uvspec', 'rte_solver', 'mc_photons', 'libRadtran')
        for token in forbidden:
            self.assertNotIn(token, text)
        self.assertIn('GITHUB_RUN_ATTEMPT', text)
        self.assertIn('postprocess/full-spectrum-estimator-pilot-v2-ordinal16-v8', text)


if __name__ == '__main__':
    unittest.main()
