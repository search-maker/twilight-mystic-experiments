from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'modeling/surrogate-training-v2/exploratory_anchor_real_evaluation.py'
spec = importlib.util.spec_from_file_location('anchor_real_v2', PATH)
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class ExternalAnchorRealEvaluationTests(unittest.TestCase):
    def test_claim_identity_is_unique_and_v2_specific(self):
        self.assertEqual(
            m.CLAIM_NAME,
            'surrogate-training-v2-exploratory-external-anchor-opening-claim-v2',
        )
        self.assertEqual(m.MODEL_HASH, 'c75971120e778e9ca85ffec81cdd8aa362fd46be364b436c54ef6cdf2a82bcac')
        self.assertEqual(m.PROTOCOL_SHA256, '7ddeb3d0c4e29a8e419513339e50925d09a340d8fe86c651ea7f0e7b277b8a77')

    def test_model_artifact_identity_is_frozen(self):
        self.assertEqual(m.MODEL_SPEC, {
            'artifactId': 8969169714,
            'name': 'surrogate-training-v2-exploratory-noisy-label-v2-contract',
            'runId': 31105103370,
            'headSha': 'ca6da420cd7acfbcfad77c4f55eecc78b4e1bdfe',
            'zipSha256': 'b5d64aab87066eea029ef57dcfcfb1e50753a54a848c73641adc2a308ad18a3e',
            'member': 'exploratory-training-only-model-v2.json',
            'memberRawSha256': '2497c0b78f552a03564565e44d2b633828428eda0bc967954f646cfdf1dd0cb5',
        })

    def test_anchor_artifact_identity_is_frozen(self):
        self.assertEqual(m.ANCHOR_SPEC, {
            'artifactId': 8890906227,
            'name': 'twilight-surrogate-tier-1-proposal-v1',
            'runId': 30905632743,
            'headSha': '9ab74efabfd34799aeeb5c9220a84639861f739d',
            'zipSha256': '899507d315ae25db88babb3f610587fca24238e7a7000038eed009c7a14af9a0',
            'member': 'validated-reference-anchors.json',
        })

    def test_exact_member_refuses_ambiguous_archive(self):
        import io, zipfile
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            archive.writestr('a/value.json', b'{}')
            archive.writestr('b/value.json', b'{}')
        with self.assertRaisesRegex(m.Refusal, 'member universe changed'):
            m.exact_member(buffer.getvalue(), 'value.json', 'test')

    def test_report_hash_is_canonical(self):
        value = {'schemaVersion': 1, 'status': 'TEST'}
        first = m.canonical_sha256(value)
        second = m.canonical_sha256({'status': 'TEST', 'schemaVersion': 1})
        self.assertEqual(first, second)


if __name__ == '__main__':
    unittest.main()
