from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/published-twilight-radiance-benchmark-v1.yml"
RESULT = ROOT / "review/published-twilight-radiance-benchmark-v1/KOOMEN_1952_SHAPE_CONTINUOUS_AOD_RUN_32805147882_RESULT.review.json"
CERTIFIER = ROOT / "review/published-twilight-radiance-benchmark-v1/certify_koomen_shape_continuous_aod_v1.py"


class PublishedTwilightRadianceWorkflowClassificationV1Tests(unittest.TestCase):
    def test_exit_two_is_diagnostic_noncertification_not_hidden_execution_failure(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('if [ "$rc" -ne 0 ] && [ "$rc" -ne 2 ]; then', text)
        self.assertIn("unexpected certifier execution exit code", text)
        self.assertIn("if rc == 2 and not failed:", text)
        self.assertIn("if rc == 0 and failed:", text)
        self.assertIn("failed certification record lacks explicit numerical failure evidence", text)
        self.assertIn("formalPassFailAuthorized", text)
        self.assertIn("modelRetuningAuthorized", text)
        self.assertIn("pandoraHoldoutOpened", text)

    def test_scientific_certifier_settings_remain_frozen(self):
        text = CERTIFIER.read_text(encoding="utf-8")
        self.assertIn("DEFAULT_LOG_TOLERANCE = 1e-4", text)
        self.assertIn('parser.add_argument("--max-depth", type=int, default=50)', text)
        self.assertIn('parser.add_argument("--max-nodes", type=int, default=500000)', text)
        self.assertIn('"algorithmId": "CERTIFIED_SAME_AOD_SAME_SCENARIO_SHAPE_INTERVAL_BNB_V1"', text)

    def test_committed_result_records_resource_cap_without_retuning(self):
        result = json.loads(RESULT.read_text(encoding="utf-8"))
        self.assertEqual(result["summary"]["gridSupportedPairCount"], 11)
        self.assertEqual(result["summary"]["certifiedEvaluatedPairCount"], 10)
        self.assertEqual(result["summary"]["certifiedObservedMoreNegativeCount"], 10)
        pair = result["inconclusivePair"]
        self.assertEqual((pair["relativeAzimuthDeg"], pair["targetAltitudeDeg"]), (90.0, 30.0))
        self.assertEqual(pair["reason"], "MAX_NODES")
        self.assertEqual(pair["maxNodes"], 500000)
        self.assertGreater(pair["branchNodes"], pair["maxNodes"])
        self.assertLess(pair["maximumRecordedCertificationGap"], pair["logTolerance"])
        self.assertFalse(result["frozenSettings"]["settingsRelaxedAfterResult"])
        self.assertFalse(result["claimBoundary"]["modelRetuningAuthorized"])
        self.assertFalse(result["claimBoundary"]["pandoraHoldoutOpened"])


if __name__ == "__main__":
    unittest.main()
