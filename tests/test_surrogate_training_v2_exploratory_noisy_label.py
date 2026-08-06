from __future__ import annotations

import copy
import importlib.util
import math
import unittest
from pathlib import Path


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ExploratoryNoisyLabelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.module = load(
            cls.root / 'modeling/surrogate-training-v2/exploratory_noisy_label_training.py',
            'exploratory_noisy_label_test_module',
        )

    def binding(self):
        value = {
            'schemaVersion': 1,
            'stageId': 'surrogate-training-v2-wave3-terminal-source-binding-v1',
            'status': 'AUDITED_THREE_WAVE_SOURCE_BOUND',
            'runId': 31070968611,
            'runAttempt': 1,
            'authorizationRef': '6c22de3578b1b0dcbc640779baa66be8d1051fe1',
            'executionSourceMainSha': 'ae81798f538899b09b6c03c3d6e90ab93458427c',
            'executionManifestSha256': '822fc64fd25244a831d6ed3a266c0d942cd1ae9827ac6d94f51a58d585c3d9ed',
            'sourceOrdinal12AnalysisRawSha256': 'c18f9ca23c910924400360ca18c4186d30594bc1aa2d3dd07a43a6031b274237',
            'sourceOrdinal12AnalysisSha256': '8e87fd440d15233dc66543a9ca011535a857b12b5602fd506f6466a900bfafc2',
            'artifactCount': 35,
            'caseArtifactCount': 30,
            'geometryCount': 15,
            'nextWaveGeometryIds': [],
            'scientificallyEligible': False,
            'exhaustedGeometryIds': ['train-0002', 'train-0008', 'train-0021'],
            'aggregateRawSha256': '1' * 64,
            'auditRawSha256': '2' * 64,
            'analysisRawSha256': '3' * 64,
            'terminalReportRawSha256': '4' * 64,
            'terminalReportSha256': '5' * 64,
            'additionalExecutionAutomaticallyAuthorized': False,
            'internalHoldoutOpened': False,
            'tier2Authorized': False,
            'productionPromotionAuthorized': False,
        }
        value['bindingSha256'] = self.module.canonical_sha256(value)
        return value

    def dataset(self):
        rows = []
        for index in range(39):
            geometry_id = f'train-{index + 1:04d}'
            exhausted = index in {1, 7, 20}
            rows.append({
                'geometryId': geometry_id,
                'role': 'surrogate-training',
                'geometry': {
                    'sunDepressionDeg': 1.0 + index * 0.1,
                    'targetAltitudeDeg': 2.0 + (index % 8),
                    'relativeAzimuthDeg': 5.0 + index * 3.0,
                    'observerElevationM': 10.0 + index * 20.0,
                    'aod550': 0.05 + (index % 5) * 0.02,
                },
                'statistics': {
                    'meanCdM2': math.exp(-9.0 + index * 0.04),
                    'relativeStandardErrorOfMean': 0.32 if exhausted else 0.04,
                    'zeroHitBlockCount': 0,
                },
                'classification': 'PRECISION_CONTINUATION_EXHAUSTED' if exhausted else 'PRECISION_TARGET_MET',
                'scientificallyEligible': not exhausted,
            })
        value = {
            'schemaVersion': 1,
            'stageId': self.module.TRAINING_DATASET_STAGE,
            'status': self.module.TRAINING_DATASET_STATUS,
            'sourceBindingSha256': self.binding()['bindingSha256'],
            'trainingGeometryIds': list(self.module.TRAINING_GEOMETRY_IDS),
            'internalHoldoutGeometryIdsExcludedAndUnopened': list(self.module.HOLDOUT_GEOMETRY_IDS),
            'holdoutRecordCount': 0,
            'holdoutValuesIncluded': False,
            'records': rows,
        }
        value['datasetSha256'] = self.module.canonical_sha256(value)
        return value

    def test_freezes_training_only_model_with_ineligible_training_weights(self):
        artifact = self.module.run(self.dataset(), self.binding())
        self.assertEqual(len(artifact['trainingGeometryIds']), 39)
        self.assertEqual(len(artifact['internalHoldoutGeometryIdsExcludedAndUnopened']), 9)
        self.assertFalse(artifact['internalHoldoutOpened'])
        self.assertFalse(artifact['holdoutValuesRead'])
        self.assertFalse(artifact['scientificallyEligibleModelClaimed'])
        self.assertTrue(artifact['ineligibleTrainingGeometryIds'])
        self.assertTrue(all(0 < value <= 1 for value in artifact['trainingObservationWeights'].values()))

    def test_dataset_contains_no_holdout_records_or_values(self):
        dataset = self.dataset()
        self.assertEqual(len(dataset['records']), 39)
        self.assertTrue(all(record['role'] == 'surrogate-training' for record in dataset['records']))
        artifact = self.module.run(dataset, self.binding())
        self.assertEqual(artifact['holdoutRecordCount'], 0)
        self.assertFalse(artifact['holdoutValuesRead'])

    def test_refuses_injected_holdout_record(self):
        dataset = self.dataset()
        dataset['records'].append({
            'geometryId': 'train-0040',
            'role': 'internal-holdout',
        })
        dataset['datasetSha256'] = self.module.canonical_sha256(
            {key: value for key, value in dataset.items() if key != 'datasetSha256'}
        )
        with self.assertRaisesRegex(Exception, 'exactly 39 records'):
            self.module.run(dataset, self.binding())

    def test_refuses_nonterminal_training_record(self):
        dataset = self.dataset()
        dataset['records'][0]['classification'] = 'ADAPTIVE_CONTINUATION_REQUIRED'
        dataset['datasetSha256'] = self.module.canonical_sha256(
            {key: value for key, value in dataset.items() if key != 'datasetSha256'}
        )
        with self.assertRaisesRegex(Exception, 'not terminal'):
            self.module.run(dataset, self.binding())

    def test_refuses_partial_or_tampered_terminal_binding(self):
        binding = self.binding()
        binding['artifactCount'] = 34
        with self.assertRaisesRegex(Exception, 'self-hash changed'):
            self.module.run(self.dataset(), binding)


    def test_refuses_scientifically_eligible_source(self):
        binding = self.binding()
        binding['scientificallyEligible'] = True
        binding['exhaustedGeometryIds'] = []
        binding['bindingSha256'] = self.module.canonical_sha256(
            {key: value for key, value in binding.items() if key != 'bindingSha256'}
        )
        with self.assertRaisesRegex(Exception, 'terminal source binding changed'):
            self.module.run(self.dataset(), binding)

    def test_refuses_empty_exhausted_source(self):
        binding = self.binding()
        binding['exhaustedGeometryIds'] = []
        binding['bindingSha256'] = self.module.canonical_sha256(
            {key: value for key, value in binding.items() if key != 'bindingSha256'}
        )
        with self.assertRaisesRegex(Exception, 'nonempty unique exhausted geometry set'):
            self.module.run(self.dataset(), binding)

    def test_refuses_dataset_exhausted_set_drift(self):
        dataset = self.dataset()
        dataset['records'][20]['classification'] = 'PRECISION_TARGET_MET'
        dataset['records'][20]['scientificallyEligible'] = True
        dataset['datasetSha256'] = self.module.canonical_sha256(
            {key: value for key, value in dataset.items() if key != 'datasetSha256'}
        )
        with self.assertRaisesRegex(Exception, 'does not match terminal source binding'):
            self.module.run(dataset, self.binding())

    def test_zero_hit_training_point_gets_floor_weight(self):
        dataset = self.dataset()
        row = dataset['records'][3]
        row['classification'] = 'PRECISION_CONTINUATION_EXHAUSTED_ZERO_HIT'
        row['scientificallyEligible'] = False
        row['statistics']['zeroHitBlockCount'] = 1
        dataset['datasetSha256'] = self.module.canonical_sha256(
            {key: value for key, value in dataset.items() if key != 'datasetSha256'}
        )
        binding = self.binding()
        binding['exhaustedGeometryIds'] = sorted(binding['exhaustedGeometryIds'] + ['train-0004'])
        binding['bindingSha256'] = self.module.canonical_sha256(
            {key: value for key, value in binding.items() if key != 'bindingSha256'}
        )
        dataset['sourceBindingSha256'] = binding['bindingSha256']
        dataset['datasetSha256'] = self.module.canonical_sha256(
            {key: value for key, value in dataset.items() if key != 'datasetSha256'}
        )
        artifact = self.module.run(dataset, binding)
        self.assertEqual(artifact['trainingObservationWeights']['train-0004'], 0.025)


if __name__ == '__main__':
    unittest.main()
