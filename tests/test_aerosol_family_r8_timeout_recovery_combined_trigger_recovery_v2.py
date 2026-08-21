from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
STAGE = "aerosol-family-challenge-v2-r8-timeout-recovery-v1"
REVIEW = ROOT / "experiments" / STAGE / "combined-trigger-recovery-v2.review.json"
FREEZE = ROOT / "evidence" / STAGE / "combined-trigger-recovery-v2.freeze.json"
OPENING = ROOT / ".github/workflows/aerosol-family-v2-r8-timeout-recovery-v1-combined-opening-recovery-v2.yml"
PUBLISHER = ROOT / ".github/workflows/aerosol-family-v2-r8-timeout-recovery-v1-combined-opening-publisher-v2.yml"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CombinedTriggerRecoveryV2Tests(unittest.TestCase):
    def test_v2_review_binds_v1_terminal_failure_and_fresh_identity(self):
        d = json.loads(REVIEW.read_text())
        self.assertEqual("REVIEW_ONLY_FRESH_CONTROL_PLANE_IDENTITY_AFTER_V1_DISPATCH_PAYLOAD_FAILURE_RESULTS_UNOPENED", d["status"])
        v1 = d["failedOpeningIdentityV1"]
        self.assertEqual(32508493509, v1["publisherRunId"])
        self.assertEqual(1, v1["publisherRunAttempt"])
        self.assertEqual("failure", v1["publisherConclusion"])
        self.assertTrue(v1["openingIdentityConsumed"])
        self.assertEqual(0, v1["openingRunCount"])
        self.assertEqual("Invalid value for input 'science_run_id'", v1["exactGitHubError"])
        self.assertFalse(v1["scientificChannelsOpened"])
        self.assertFalse(v1["rerunPermitted"])
        correction = d["v2Correction"]
        self.assertEqual("EXPLICIT_JSON_OBJECT", correction["workflowDispatchPayloadEncoding"])
        self.assertEqual("string", correction["scienceRunIdInputJsonType"])
        self.assertFalse(correction["ghTypedFormFieldDispatchPermitted"])
        self.assertFalse(d["scientificResultOpeningAuthorizedAtReview"])

    def test_v2_publisher_uses_explicit_json_string_and_never_typed_F(self):
        text = PUBLISHER.read_text()
        self.assertIn("workflow-dispatch-v2.json", text)
        self.assertIn("'inputs':{'science_run_id':'32503223236'}", text)
        self.assertIn("--input workflow-dispatch-v2.json", text)
        self.assertNotIn("-F \"inputs[science_run_id]", text)
        self.assertIn("Invalid value for input 'science_run_id'", text)
        self.assertIn("V1_PUBLISHER_RUN_ID: '32508493509'", text)
        self.assertIn("V1_PUBLISHER_JOB_ID: '96853960455'", text)
        self.assertIn("v1 opening workflow unexpectedly has", text)
        self.assertIn("COMBINED_OPENING_RECOVERY_V2_ALLOCATED", text)
        self.assertIn("COMBINED_OPENING_RECOVERY_V2_CONSUMED", text)
        self.assertNotIn("setup-micromamba@", text)
        self.assertNotIn("uvspec", text)

    def test_v2_opening_remains_attempt1_solver_free_and_frozen_analysis_pinned(self):
        text = OPENING.read_text()
        self.assertIn("workflow_dispatch:", text)
        self.assertNotIn("workflow_run:", text)
        self.assertIn("test \"$GITHUB_RUN_ATTEMPT\" = 1", text)
        self.assertIn("combined-opening-v2-run-32503223236", text)
        self.assertIn("32508493509", text)
        self.assertIn("19bd924ab86ed0744b3fd77ce5d6756039674d5f", text)
        self.assertIn("path: frozen-analysis", text)
        self.assertIn("--repository-root frozen-analysis", text)
        self.assertIn("afc2-r8-timeout-recovery-v1-combined-analysis-trigger-recovery-v2", text)
        self.assertNotIn("setup-micromamba@", text)
        self.assertNotIn("command -v uvspec", text)
        self.assertNotIn("/rerun", text)

    def test_v2_freeze_binds_exact_review_transport_bytes(self):
        f = json.loads(FREEZE.read_text())
        self.assertEqual("FROZEN_FRESH_V2_CONTROL_PLANE_IDENTITY_NOT_DISPATCHED", f["status"])
        self.assertEqual(sha(REVIEW), f["reviewRawSha256"])
        self.assertEqual(sha(OPENING), f["openingWorkflowRawSha256"])
        self.assertEqual(sha(PUBLISHER), f["publisherWorkflowRawSha256"])
        self.assertEqual(sha(Path(__file__)), f["testRawSha256"])
        self.assertEqual(32508493509, f["failedV1PublisherRunId"])
        self.assertEqual(0, f["failedV1OpeningRunCount"])
        self.assertFalse(f["scientificResultOpeningAuthorizedByFreezeAlone"])
        self.assertFalse(f["scientificSolverExecutionAuthorized"])


if __name__ == "__main__":
    unittest.main()
