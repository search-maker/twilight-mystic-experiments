#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import json
import unittest
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
TRAIN = HERE / 'train_v3.py'
PREFIT = HERE.parent / 'level-b-v2-training-prefit-freeze-v3-densified58/protocol-v3.json'
spec = importlib.util.spec_from_file_location('densified58_v3', TRAIN)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p3 = json.loads(PREFIT.read_text())
        cls.effective = mod.effective_protocol(cls.p3)

    def test_candidate_semantics_inherited_exactly(self):
        inherited = mod.v2.load_json(mod.G2_PROTOCOL)
        self.assertEqual(mod.v2.candidate_specs(self.effective), mod.v2.candidate_specs(inherited))
        self.assertEqual(len(mod.v2.candidate_specs(self.effective)), 230)
        self.assertEqual(self.effective['modelSelection']['trainingOnlyReadinessGates'], inherited['modelSelection']['trainingOnlyReadinessGates'])
        self.assertEqual(self.effective['modelSelection']['selectionScore'], inherited['modelSelection']['selectionScore'])
        self.assertEqual(self.effective['modelSelection']['tieBreak'], inherited['modelSelection']['tieBreak'])

    def test_58_geometry_fold_arithmetic(self):
        recs = mod.synthetic_records(self.effective)
        folds = mod.folds58(recs, self.effective, enforce_counts=False)
        self.assertEqual(len(recs), 58)
        self.assertEqual(len(folds), 73)
        self.assertEqual([len(x['val']) for x in folds[:5]], [12, 12, 12, 11, 11])
        self.assertEqual(sum(1 for x in folds if x['kind'] == 'loo'), 58)

    def test_frozen_projection_math(self):
        n = 13
        W = np.zeros((3, n), dtype=np.float64)
        W[0, 0] = 1.0
        W[1, 1] = 1.0
        W[2, 2] = 1.0
        grand = np.zeros(n, dtype=np.float64)
        components = np.zeros((10, n), dtype=np.float64)
        for j in range(10):
            components[j, 3 + j] = 1.0
        y = np.arange(1, n + 1, dtype=np.float64) * 2.0
        channels, coeff = mod.project_block(y, W, grand, components)
        np.testing.assert_allclose(channels, y[:3])
        np.testing.assert_allclose(coeff, y[3:] / y[0])

    def test_two_block_statistics_use_sample_std(self):
        stats = mod.stats2([1.0, 3.0])
        self.assertAlmostEqual(stats['mean'], 2.0)
        self.assertAlmostEqual(stats['sampleStd'], np.sqrt(2.0))
        self.assertAlmostEqual(stats['standardError'], 1.0)
        self.assertAlmostEqual(stats['relativeStandardError'], 0.5)

    def test_role_isolation_excludes_opened_ordinal22(self):
        expanded = self.p3['roleIsolation']['exactExpandedTrainingGeometryIds']
        opened = self.p3['roleIsolation']['openedOrdinal22DiagnosticOnlyGeometryIds']
        self.assertEqual(len(expanded), 58)
        self.assertFalse(set(expanded) & set(opened))
        self.assertEqual(expanded[-14:], [f'train-{i:04d}' for i in range(101, 115)])


if __name__ == '__main__':
    unittest.main()
