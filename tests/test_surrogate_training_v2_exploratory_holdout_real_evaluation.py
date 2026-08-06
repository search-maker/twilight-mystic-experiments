from __future__ import annotations

import importlib.util
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    'real_eval',
    ROOT / 'modeling/surrogate-training-v2/exploratory_holdout_real_evaluation_exact.py',
)
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class RealEvaluationContractTests(unittest.TestCase):
    def test_exact_artifact_universe_is_unique(self):
        ids = [row[0] for row in m.CASES]
        names = [row[1] for row in m.CASES]
        self.assertEqual(len(ids), 14)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(len(m.ANALYSES), 2)
        self.assertEqual(len({row['artifactId'] for row in m.ANALYSES}), 2)

    def test_holdout_case_distribution_is_frozen(self):
        identities = []
        for _, name, _, _, _, wave in m.CASES:
            match = re.search(r'(train-\d{4}).*-b([3-8])$', name)
            self.assertIsNotNone(match)
            identities.append((match.group(1), int(match.group(2)), wave))
        self.assertEqual(sum(wave == 'wave1' for _, _, wave in identities), 6)
        self.assertEqual(sum(wave == 'wave2' for _, _, wave in identities), 4)
        self.assertEqual(sum(wave == 'wave3' for _, _, wave in identities), 4)
        self.assertEqual(
            {geometry_id for geometry_id, _, wave in identities if wave == 'wave1'},
            {'train-0015', 'train-0035', 'train-0045'},
        )
        self.assertEqual(
            {geometry_id for geometry_id, _, wave in identities if wave in {'wave2', 'wave3'}},
            {'train-0015', 'train-0035'},
        )

    def test_exact_runner_redirects_to_exact_builder(self):
        target = ROOT / 'modeling/surrogate-training-v2/exploratory_holdout_dataset.py'
        loaded = m.module(target, 'redirect-test')
        self.assertTrue(loaded.__file__.endswith('exploratory_holdout_dataset_exact.py'))
        self.assertEqual(len(loaded.ORDINAL12_IDS), 20)
        self.assertEqual(len(loaded.ORDINAL13_IDS), 15)

    def test_claim_and_source_identities_are_frozen(self):
        self.assertEqual(
            m.CLAIM_NAME,
            'surrogate-training-v2-exploratory-holdout-opening-claim-v1',
        )
        self.assertEqual(
            m.MODEL_HASH,
            '381323604143498619cec494d221747d0d32f37a7e7cbb811b0154b6b4f68848',
        )
        self.assertEqual(
            m.PROTOCOL_SHA256,
            'f8fe9d486679ef1c9179ed08c790da987bc838cd952effcdebb33862f57d8f69',
        )


if __name__ == '__main__':
    unittest.main()
