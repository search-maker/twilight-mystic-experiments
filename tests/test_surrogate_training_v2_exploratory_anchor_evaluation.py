from __future__ import annotations

import copy
import importlib.util
import json
import math
import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / 'modeling/surrogate-training-v2/exploratory_anchor_evaluation.py'
MODEL_PATH = Path(os.environ.get('ANCHOR_V2_MODEL_PATH', '/mnt/data/pr106-model-v2-head-ca6da42/exploratory-training-only-model-v2.json'))
PROTOCOL_PATH = ROOT / 'modeling/surrogate-training-v2/exploratory_anchor_protocol.json'
spec = importlib.util.spec_from_file_location('anchor_eval', MODULE_PATH)
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class AnchorEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not MODEL_PATH.is_file():
            raise unittest.SkipTest('frozen v2 model artifact not mounted')
        cls.model = m.load(MODEL_PATH)
        cls.protocol = m.load(PROTOCOL_PATH)

    def anchor(self, group: str, strength: str, fraction: float, multiplier: float = 1.0):
        ranges = m.PROPOSAL_RANGES
        geometry = {'geometryId': group}
        for name in m.FEATURES:
            low, high = ranges[name]
            geometry[name] = low + fraction * (high - low)
        provisional = {
            'groupId': group,
            'geometry': geometry,
            'methods': {
                'alis': {'meanCdM2': 1.0, 'relativeStandardErrorOfMean': 0.05},
                'reference-vroom': {'meanCdM2': 1.0, 'relativeStandardErrorOfMean': 0.05},
            },
            'eligibleForTraining': False,
            'eligibleForModelAcceptance': strength == 'hard',
            'observationValidationRequired': True,
            'anchorStrength': strength,
        }
        prediction = m.predict(self.model, provisional)['predictionCdM2']
        provisional['methods']['alis']['meanCdM2'] = prediction * multiplier * 1.05
        provisional['methods']['reference-vroom']['meanCdM2'] = prediction * multiplier / 1.05
        return provisional

    def anchors(self, multipliers=None):
        if multipliers is None:
            multipliers = [1.0, 1.1, 0.9, 1.25, 0.8]
        hard = [
            self.anchor(group, 'hard', 0.1 + index * 0.15, multipliers[index])
            for index, group in enumerate(m.EXPECTED_HARD_IDS)
        ]
        soft = [self.anchor(m.EXPECTED_SOFT_IDS[0], 'soft-diagnostic', 0.45, 20.0)]
        return {
            'schemaVersion': 1,
            'stageId': 'twilight-model-readiness-v1',
            'status': 'REFERENCE_ANCHORS_VALIDATED',
            'sourceStageId': 'g01-fixed-precision-diagnosis-execution-v1',
            'anchorCount': 6,
            'hardValidationAnchorCount': 5,
            'softDiagnosticAnchorCount': 1,
            'hardValidationAnchorIds': list(m.EXPECTED_HARD_IDS),
            'softDiagnosticAnchorIds': list(m.EXPECTED_SOFT_IDS),
            'anchors': hard + soft,
            'trainingAutomaticallyAuthorized': False,
            'productionModelReady': False,
            'observationValidationRequired': True,
        }

    def write(self, directory: Path, value):
        path = directory / 'anchors.json'
        path.write_text(m.dump(value), encoding='utf-8', newline='\n')
        return path

    def test_protocol_and_model_are_frozen(self):
        m.validate_protocol(copy.deepcopy(self.protocol))
        m.validate_model(copy.deepcopy(self.model), MODEL_PATH)
        self.assertEqual(self.protocol['protocolSha256'], m.EXPECTED_PROTOCOL_SHA256)
        self.assertEqual(self.model['modelHash'], m.EXPECTED_MODEL_HASH)

    def test_passes_synthetic_hard_anchors_and_ignores_soft_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = self.write(Path(temporary), self.anchors())
            result = m.evaluate(MODEL_PATH, PROTOCOL_PATH, path)
        self.assertTrue(result['computationallyValidated'])
        self.assertTrue(result['generalizationValidated'])
        self.assertEqual(result['hardAnchorCount'], 5)
        self.assertEqual(result['softDiagnosticCount'], 1)
        self.assertTrue(all(result['acceptanceChecks'].values()))
        self.assertFalse(result['observationallyValidated'])
        self.assertFalse(result['productionModelReady'])
        self.assertGreater(result['softDiagnosticRows'][0]['absoluteLogErrorToConsensus'], math.log(10))

    def test_fails_without_tuning_when_hard_anchors_are_poor(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = self.write(Path(temporary), self.anchors([10.0] * 5))
            result = m.evaluate(MODEL_PATH, PROTOCOL_PATH, path)
        self.assertFalse(result['computationallyValidated'])
        self.assertFalse(result['acceptanceChecks']['meanAbsoluteLogError'])
        self.assertTrue(result['thresholdTuningFromAnchorsForbidden'])
        self.assertTrue(result['modelOrPreprocessingChangeAfterOpeningForbidden'])

    def test_refuses_protocol_threshold_tampering(self):
        changed = copy.deepcopy(self.protocol)
        changed['acceptanceCriteria']['meanAbsoluteLogErrorMaximum'] = 99.0
        changed['protocolSha256'] = m.canonical_sha256(
            {key: value for key, value in changed.items() if key != 'protocolSha256'}
        )
        with self.assertRaisesRegex(m.AnchorRefusal, 'self-hash changed'):
            m.validate_protocol(changed)

    def test_refuses_model_tampering(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'model.json'
            changed = copy.deepcopy(self.model)
            changed['modelState']['coefficients'][0] += 1e-8
            changed['modelHash'] = m.canonical_sha256(
                {key: value for key, value in changed.items() if key != 'modelHash'}
            )
            path.write_text(m.dump(changed), encoding='utf-8', newline='\n')
            with self.assertRaisesRegex(m.AnchorRefusal, 'raw hash changed'):
                m.validate_model(changed, path)

    def test_refuses_anchor_partition_drift(self):
        changed = self.anchors()
        changed['anchors'][0]['anchorStrength'] = 'soft-diagnostic'
        with self.assertRaisesRegex(m.AnchorRefusal, 'anchor policy changed'):
            m.validate_anchors(changed)

    def test_refuses_anchor_identity_drift(self):
        changed = self.anchors()
        changed['anchors'][0]['groupId'] = 'g99'
        with self.assertRaisesRegex(m.AnchorRefusal, 'anchor identity changed'):
            m.validate_anchors(changed)

    def test_out_of_proposal_range_fails_acceptance(self):
        changed = self.anchors()
        changed['anchors'][0]['geometry']['relativeAzimuthDeg'] = 181.0
        prediction = m.predict(self.model, changed['anchors'][0])['predictionCdM2']
        changed['anchors'][0]['methods']['alis']['meanCdM2'] = prediction
        changed['anchors'][0]['methods']['reference-vroom']['meanCdM2'] = prediction
        with tempfile.TemporaryDirectory() as temporary:
            path = self.write(Path(temporary), changed)
            result = m.evaluate(MODEL_PATH, PROTOCOL_PATH, path)
        self.assertFalse(result['computationallyValidated'])
        self.assertEqual(result['outOfProposalRangeCount'], 1)
        self.assertFalse(result['acceptanceChecks']['outOfProposalRangeCount'])


if __name__ == '__main__':
    unittest.main()
