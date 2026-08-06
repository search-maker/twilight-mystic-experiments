from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests.exploratory_terminal_training_fixture import ExploratoryTerminalTrainingFixture


class ExploratoryTerminalTrainingDatasetTests(ExploratoryTerminalTrainingFixture, unittest.TestCase):
    def test_builds_39_record_training_only_dataset_and_skips_holdout_values(self):
        with tempfile.TemporaryDirectory() as raw:
            source, binding, analysis, results = self.fixture(Path(raw))
            source_binding = self.builder.load(binding)
            value = self.builder.build(self.root, source, binding, analysis, results)
        self.assertEqual(len(value['records']), 39)
        self.assertEqual(value['holdoutRecordCount'], 0)
        self.assertFalse(value['holdoutValuesIncluded'])
        self.assertNotIn('secretHoldoutTargetMustNotReachOutput', json.dumps(value))
        self.assertEqual(
            value['internalHoldoutGeometryIdsExcludedAndUnopened'],
            ['train-0005', 'train-0010', 'train-0015', 'train-0020', 'train-0025', 'train-0030', 'train-0035', 'train-0040', 'train-0045'],
        )
        self.model.validate_training_dataset(value, source_binding)

    def test_updates_all_13_training_wave3_geometries_to_block_eight(self):
        with tempfile.TemporaryDirectory() as raw:
            source, binding, analysis, results = self.fixture(Path(raw))
            value = self.builder.build(self.root, source, binding, analysis, results)
        by_id = {row['geometryId']: row for row in value['records']}
        self.assertEqual(len(self.builder.WAVE3_TRAINING_IDS), 13)
        for gid in self.builder.WAVE3_TRAINING_IDS:
            self.assertEqual(by_id[gid]['statistics']['blockCount'], 8)
            self.assertEqual(len(by_id[gid]['caseIds']), 8)
        self.assertIn('train-0047', by_id)
        self.assertNotIn('train-0035', by_id)
        self.assertEqual(by_id['train-0047']['classification'], 'PRECISION_CONTINUATION_EXHAUSTED')

    def test_refuses_missing_training_case(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source, binding, analysis, results = self.fixture(root)
            next(results.rglob('case-result.json')).unlink()
            with self.assertRaisesRegex(Exception, 'expected 26'):
                self.builder.build(self.root, source, binding, analysis, results)

    def test_refuses_terminal_analysis_hash_drift(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source, binding, analysis, results = self.fixture(root)
            analysis.write_text(analysis.read_text() + ' ')
            with self.assertRaisesRegex(Exception, 'raw hash changed'):
                self.builder.build(self.root, source, binding, analysis, results)

    def test_refuses_exhausted_set_mismatch(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source, binding_path, analysis, results = self.fixture(root)
            binding = json.loads(binding_path.read_text())
            binding['exhaustedGeometryIds'] = [gid for gid in binding['exhaustedGeometryIds'] if gid != 'train-0047']
            binding['bindingSha256'] = self.model.canonical_sha256(
                {key: item for key, item in binding.items() if key != 'bindingSha256'}
            )
            binding_path.write_text(json.dumps(binding, indent=2, sort_keys=True) + '\n')
            with self.assertRaisesRegex(Exception, 'binding/classification mismatch'):
                self.builder.build(self.root, source, binding_path, analysis, results)


if __name__ == "__main__":
    unittest.main()
