from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
STAGE = "aerosol-family-challenge-v2-r8-timeout-recovery-v1"
REVIEW = ROOT / "experiments" / STAGE / "combined-trigger-recovery.review.json"
FREEZE = ROOT / "evidence" / STAGE / "combined-trigger-recovery.freeze.json"
OPENING = ROOT / ".github/workflows/aerosol-family-v2-r8-timeout-recovery-v1-combined-opening-recovery.yml"
PUBLISHER = ROOT / ".github/workflows/aerosol-family-v2-r8-timeout-recovery-v1-combined-opening-publisher.yml"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CombinedTriggerRecoveryV1Tests(unittest.TestCase):
    def test_review_freezes_only_control_plane_recovery(self):
        d = json.loads(REVIEW.read_text())
        self.assertEqual("REVIEW_ONLY_CONTROL_PLANE_TRIGGER_RECOVERY_RESULTS_UNOPENED", d["status"])
        self.assertEqual(32503223236, d["sourceScience"]["runId"])
        self.assertEqual(1, d["sourceScience"]["runAttempt"])
        self.assertEqual("success", d["sourceScience"]["conclusion"])
        self.assertFalse(d["sourceScience"]["scientificChannelsOpenedBeforeRecoveryReview"])
        self.assertFalse(d["scientificResultOpeningAuthorizedAtReview"])
        self.assertFalse(d["scientificChannelsOpenedWhileDefiningRecovery"])
        rules = d["unchangedScientificRules"]
        self.assertEqual((568, 8, 576, 72, 24), (rules["sourceRetainedCases"], rules["freshReplacementCases"], rules["effectiveCaseCount"], rules["comparisonGroupCount"], rules["analysisCellCount"]))
        self.assertFalse(rules["epsilonSubstitutionPermitted"])
        self.assertFalse(rules["pValuesPermitted"])
        self.assertFalse(rules["confidenceIntervalsPermitted"])
        self.assertFalse(rules["newMonteCarloExecutionPermitted"])
        self.assertFalse(rules["scientificSolverExecutionPermitted"])

    def test_execution_is_dispatch_only_one_use_and_pins_frozen_analysis(self):
        text = OPENING.read_text()
        self.assertIn("workflow_dispatch:", text)
        self.assertNotIn("workflow_run:", text)
        self.assertNotIn("repository_dispatch:", text)
        self.assertIn("test \"$GITHUB_RUN_ATTEMPT\" = 1", text)
        self.assertIn("32503223236", text)
        self.assertIn("b37aab8fd2c2f0a6b58eef79a00811c9adea02a0", text)
        self.assertIn("19bd924ab86ed0744b3fd77ce5d6756039674d5f", text)
        self.assertIn("path: frozen-analysis", text)
        self.assertIn("combined_aggregate.py", text)
        self.assertIn("--repository-root frozen-analysis", text)
        self.assertNotIn("uses: mamba-org/setup-micromamba", text)
        self.assertNotIn("command -v uvspec", text)
        self.assertNotIn("rerun_url", text)
        self.assertNotIn("/rerun", text)

    def test_publisher_requires_one_file_request_and_direct_dispatch(self):
        text = PUBLISHER.read_text()
        self.assertIn("status/aerosol-family-v2-r8-timeout-recovery-v1-combined-opening-publisher-run-32503223236", text)
        self.assertIn("test \"${#CHANGED[@]}\" = 1", text)
        self.assertIn("REQUEST_ONE_USE_FROZEN_COMBINED_RESULT_OPENING", text)
        self.assertIn("original combined workflow unexpectedly", text)
        self.assertIn("AFC2_R8_TIMEOUT_RECOVERY_V1_COMBINED_OPENING_RECOVERY_ALLOCATED", text)
        self.assertIn("AFC2_R8_TIMEOUT_RECOVERY_V1_COMBINED_OPENING_RECOVERY_CONSUMED", text)
        self.assertIn("/dispatches", text)
        self.assertIn("inputs[science_run_id]=32503223236", text)
        self.assertNotIn("setup-micromamba@", text)
        self.assertNotIn("uvspec", text)

    def test_freeze_binds_review_and_transport_bytes(self):
        f = json.loads(FREEZE.read_text())
        self.assertEqual("FROZEN_CONTROL_PLANE_TRIGGER_RECOVERY_NOT_DISPATCHED", f["status"])
        self.assertEqual(sha(REVIEW), f["reviewRawSha256"])
        self.assertEqual(sha(OPENING), f["openingWorkflowRawSha256"])
        self.assertEqual(sha(PUBLISHER), f["publisherWorkflowRawSha256"])
        self.assertEqual(sha(Path(__file__)), f["testRawSha256"])
        self.assertFalse(f["scientificResultOpeningAuthorizedByFreezeAlone"])
        self.assertFalse(f["scientificSolverExecutionAuthorized"])


if __name__ == "__main__":
    unittest.main()
