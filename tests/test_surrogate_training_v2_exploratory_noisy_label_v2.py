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
MODULE_PATH = ROOT / 'modeling/surrogate-training-v2/exploratory_noisy_label_training_v2.py'
DATASET_PATH = Path(os.environ.get('V2_SOURCE_DATASET', '/mnt/data/pr99-real/terminal-training-only-dataset.json'))
MODEL_V1_PATH = Path(os.environ.get('V2_SOURCE_MODEL_V1', '/mnt/data/pr99-real/exploratory-training-only-model.json'))

spec = importlib.util.spec_from_file_location('exploratory_noisy_label_training_v2', MODULE_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(MODULE_PATH)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class ExploratoryNoisyLabelV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.dataset = m.load(DATASET_PATH)
        cls.source_model = m.load(MODEL_V1_PATH)
        cls.expected = m.freeze(
            copy.deepcopy(cls.dataset),
            copy.deepcopy(cls.source_model),
            dataset_path=DATASET_PATH,
            source_model_path=MODEL_V1_PATH,
        )

    def test_rebuilds_frozen_v2_byte_for_byte(self) -> None:
        rebuilt = m.freeze(
            copy.deepcopy(self.dataset),
            copy.deepcopy(self.source_model),
            dataset_path=DATASET_PATH,
            source_model_path=MODEL_V1_PATH,
        )
        self.assertEqual(rebuilt, self.expected)
        self.assertEqual(rebuilt['modelHash'], 'c75971120e778e9ca85ffec81cdd8aa362fd46be364b436c54ef6cdf2a82bcac')
        self.assertEqual(rebuilt['basis'], 'poly2-cos')
        self.assertEqual(rebuilt['selectedRidge'], 0.001)
        self.assertEqual(rebuilt['modelState']['columnCount'], 21)
        self.assertEqual(len(rebuilt['modelState']['coefficients']), 21)

    def test_training_only_selection_is_frozen(self) -> None:
        selected = self.expected['selectedTrainingOnlyEvaluation']
        self.assertAlmostEqual(selected['selectionScore'], 1.2786593067617205, places=12)
        self.assertAlmostEqual(selected['meanFoldMeanAbsoluteLogError'], 0.33404214855115416, places=12)
        low = selected['azimuthLowFold']
        self.assertEqual(low['count'], 8)
        self.assertEqual(low['withinFactorTwoCount'], 7)
        self.assertAlmostEqual(low['meanAbsoluteLogError'], 0.336804420626049, places=12)
        self.assertAlmostEqual(low['maximumAbsoluteLogError'], 0.7609283047705393, places=12)
        ranking = self.expected['trainingOnlyCandidateRanking']
        self.assertEqual((ranking[0]['basis'], ranking[0]['ridge']), ('poly2-cos', 0.001))
        self.assertEqual((ranking[1]['basis'], ranking[1]['ridge']), ('poly2-physical', 0.001))

    def test_uses_frozen_physical_design_not_training_extrema(self) -> None:
        design = self.expected['basisDefinition']
        self.assertEqual(design['proposalRanges'], {key: list(value) for key, value in m.PROPOSAL_RANGES.items()})
        self.assertEqual(design['baseFeatures'][2], 'cos(relativeAzimuthDeg*pi/180)')
        at_zero = m.proposal_cos([2.0, 5.0, 0.0, 0.0, 0.05])
        at_opposite = m.proposal_cos([18.0, 80.0, 180.0, 2500.0, 0.4])
        self.assertEqual(at_zero, [0.0, 0.0, 1.0, 0.0, 0.0])
        for actual, expected in zip(at_opposite, [1.0, 1.0, -1.0, 1.0, 1.0], strict=True):
            self.assertAlmostEqual(actual, expected, places=15)

    def test_opened_holdout_is_not_reused(self) -> None:
        for field in (
            'openedInternalHoldoutUsedForSelection',
            'openedInternalHoldoutUsedForFitting',
            'openedInternalHoldoutUsedForPreprocessing',
            'openedInternalHoldoutUsedForThresholds',
            'internalHoldoutV1Reused',
            'independentValidationOpened',
            'hardAnchorsOpened',
            'softDiagnosticsOpened',
            'generalizationValidated',
            'observationallyValidated',
            'scientificEligibilityClaimed',
            'tier2Authorized',
            'productionModelReady',
            'productionPromotionAuthorized',
        ):
            self.assertIs(self.expected[field], False, field)
        raw = m.dump(self.expected)
        self.assertNotIn('INTERNAL_HOLDOUT_GENERALIZATION_FAILED', raw)
        self.assertNotIn('train-0045"', raw)
        self.assertNotIn('0.44373205161175233', raw)

    def test_refuses_training_target_tampering(self) -> None:
        changed = copy.deepcopy(self.dataset)
        changed['records'][0]['statistics']['meanCdM2'] *= 1.01
        changed['datasetSha256'] = m.canonical_sha256(
            {key: value for key, value in changed.items() if key != 'datasetSha256'}
        )
        with self.assertRaisesRegex(m.Refusal, 'self-hash changed'):
            m.freeze(changed, copy.deepcopy(self.source_model))

    def test_refuses_source_model_tampering(self) -> None:
        changed = copy.deepcopy(self.source_model)
        changed['modelState']['coefficients'][0] += 1e-8
        changed['modelHash'] = m.canonical_sha256(
            {key: value for key, value in changed.items() if key != 'modelHash'}
        )
        with self.assertRaisesRegex(m.Refusal, 'self-hash changed'):
            m.freeze(copy.deepcopy(self.dataset), changed)

    def test_model_restoration_is_exact(self) -> None:
        records = m.validate_training_dataset(copy.deepcopy(self.dataset), DATASET_PATH)
        state = {
            'basis': self.expected['basis'],
            'ridge': self.expected['selectedRidge'],
            'coefficients': self.expected['modelState']['coefficients'],
            'columnCount': self.expected['modelState']['columnCount'],
        }
        predictions = [m.predict_log(state, record) for record in records]
        self.assertEqual(len(predictions), 39)
        self.assertTrue(all(math.isfinite(value) for value in predictions))
        self.assertAlmostEqual(
            self.expected['weightedResidualRmseLog'],
            0.1161378259687029,
            places=12,
        )


if __name__ == '__main__':
    unittest.main()
