import json
import tempfile
import unittest
from pathlib import Path
from tests.exploratory_terminal_training_fixture import ExploratoryTerminalTrainingFixture


class TerminalDatasetTests(ExploratoryTerminalTrainingFixture, unittest.TestCase):
    def build(self, source, binding, analysis, results):
        value = json.loads(source.read_text())
        return self.builder.build(
            self.root, source, binding, analysis, results,
            expected_source_dataset_sha256=value['datasetSha256'],
            expected_source_dataset_raw_sha256=self.builder.raw_sha256(source),
        )

    def test_exact_source_default_and_training_boundary(self):
        with tempfile.TemporaryDirectory() as raw:
            source, binding, analysis, results = self.fixture(Path(raw))
            with self.assertRaisesRegex(Exception, 'exact b1-b6 source'):
                self.builder.build(self.root, source, binding, analysis, results)
            value = self.build(source, binding, analysis, results)
            self.assertEqual(value['trainingGeometryIds'], list(self.builder.TRAINING_IDS))
            self.assertEqual(value['internalHoldoutGeometryIdsExcludedAndUnopened'], list(self.builder.HOLDOUT_IDS))
            self.assertEqual(len(value['records']), 39)
            self.assertEqual(value['holdoutRecordCount'], 0)
            self.assertFalse(value['holdoutValuesIncluded'])
            self.assertNotIn('secretHoldoutTargetMustNotReachOutput', json.dumps(value))
            self.model.validate_training_dataset(value, self.builder.load(binding))

    def test_zero_hit_null_rsem_and_full_case_provenance(self):
        with tempfile.TemporaryDirectory() as raw:
            source_path, binding_path, analysis_path, results = self.fixture(Path(raw))
            source = json.loads(source_path.read_text())
            row = next(x for x in source['records'] if x['geometryId'] == 'train-0003')
            row['zeroHitCaseIds'] = ['train-0003-b5']
            row['statistics'].update(zeroHitBlockCount=1, zeroHitBlockFraction=1/6)
            source['datasetSha256'] = self.builder.canonical_sha256({k:v for k,v in source.items() if k != 'datasetSha256'})
            source_path.write_text(json.dumps(source, sort_keys=True) + '\n')

            terminal = json.loads(analysis_path.read_text())
            point = next(x for x in terminal['analysis']['points'] if x['geometryId'] == 'train-0003')
            point.update(classification='PRECISION_CONTINUATION_EXHAUSTED_ZERO_HIT',
                         numericalStatus='NUMERICAL_ZERO_HIT_EXHAUSTED',
                         relativeStandardErrorOfMean=None,
                         relativeStandardErrorStatus='NOT_COMPUTED_ZERO_HIT_PRESENT',
                         zeroHitBlockCount=2, zeroHitBlockFraction=.25)
            point['valuesCdM2'][7] = 0.0
            point['nonzeroBlockValuesCdM2'] = [x for x in point['valuesCdM2'] if x > 0]
            analysis_path.write_text(json.dumps(terminal, sort_keys=True) + '\n')

            path = results/'train-0003'/'b8'/'case-result.json'
            result = json.loads(path.read_text())
            result.update(selectedNodeRadiance=[0.0]*15,
                          selectedPhotopicContributionCdM2=0.0, zeroHit=True)
            result['contentSha256'] = self.builder.canonical_sha256({k:v for k,v in result.items() if k != 'contentSha256'})
            path.write_text(json.dumps(result, sort_keys=True) + '\n')

            binding = json.loads(binding_path.read_text())
            binding['analysisRawSha256'] = self.builder.raw_sha256(analysis_path)
            binding['bindingSha256'] = self.model.canonical_sha256({k:v for k,v in binding.items() if k != 'bindingSha256'})
            binding_path.write_text(json.dumps(binding, sort_keys=True) + '\n')
            value = self.build(source_path, binding_path, analysis_path, results)

        row = next(x for x in value['records'] if x['geometryId'] == 'train-0003')
        self.assertIsNone(row['statistics']['relativeStandardErrorOfMean'])
        self.assertEqual(row['statistics']['relativeStandardErrorStatus'], 'NOT_COMPUTED_ZERO_HIT_PRESENT')
        self.assertEqual(row['zeroHitCaseIds'], ['train-0003-b5', 'train-0003-precision-continuation-wave3-v1-b8'])

    def test_refuses_incomplete_cases_and_exhausted_drift(self):
        with tempfile.TemporaryDirectory() as raw:
            source, binding, analysis, results = self.fixture(Path(raw))
            next(results.rglob('case-result.json')).unlink()
            with self.assertRaisesRegex(Exception, 'expected 26'):
                self.build(source, binding, analysis, results)
        with tempfile.TemporaryDirectory() as raw:
            source, binding_path, analysis, results = self.fixture(Path(raw))
            binding = json.loads(binding_path.read_text())
            binding['exhaustedGeometryIds'].remove('train-0047')
            binding['bindingSha256'] = self.model.canonical_sha256({k:v for k,v in binding.items() if k != 'bindingSha256'})
            binding_path.write_text(json.dumps(binding, sort_keys=True) + '\n')
            with self.assertRaisesRegex(Exception, 'binding/classification mismatch'):
                self.build(source, binding_path, analysis, results)


if __name__ == '__main__':
    unittest.main()
