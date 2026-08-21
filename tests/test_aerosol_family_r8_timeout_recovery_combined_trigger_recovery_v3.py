from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
STAGE = "aerosol-family-challenge-v2-r8-timeout-recovery-v1"
REVIEW = ROOT / "experiments" / STAGE / "combined-trigger-recovery-v3.review.json"
FREEZE = ROOT / "evidence" / STAGE / "combined-trigger-recovery-v3.freeze.json"
OPENING = ROOT / ".github/workflows/aerosol-family-v2-r8-timeout-recovery-v1-combined-opening-recovery-v3.yml"
PUBLISHER = ROOT / ".github/workflows/aerosol-family-v2-r8-timeout-recovery-v1-combined-opening-publisher-v3.yml"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CombinedTriggerRecoveryV3Tests(unittest.TestCase):
    def test_v3_review_preserves_v1_v2_terminal_histories(self):
        d=json.loads(REVIEW.read_text())
        self.assertEqual("REVIEW_ONLY_FRESH_V3_CONTROL_PLANE_IDENTITY_AFTER_V2_AUDIT_LOG_RENDER_FAILURE_RESULTS_UNOPENED",d["status"])
        self.assertEqual(32508493509,d["failedOpeningIdentityV1"]["publisherRunId"])
        self.assertTrue(d["failedOpeningIdentityV1"]["openingIdentityConsumed"])
        self.assertEqual(32510096551,d["failedOpeningIdentityV2"]["publisherRunId"])
        self.assertFalse(d["failedOpeningIdentityV2"]["openingIdentityConsumed"])
        self.assertEqual(0,d["failedOpeningIdentityV2"]["openingRunCount"])
        c=d["v3Correction"]
        self.assertFalse(c["runtimeHistoricalRawLogFetchPermitted"])
        self.assertEqual("EXACT_RUN_JOB_STEP_METADATA_PLUS_IMMUTABLE_ISSUE60_CHECKPOINTS",c["historicalFailureProof"])
        self.assertEqual("EXPLICIT_JSON_OBJECT",c["workflowDispatchPayloadEncoding"])
        self.assertEqual("string",c["scienceRunIdInputJsonType"])
        self.assertFalse(d["scientificResultOpeningAuthorizedAtReview"])

    def test_v3_publisher_never_fetches_historical_raw_logs_and_uses_json_string(self):
        text=PUBLISHER.read_text()
        self.assertNotIn("/actions/jobs/${V1_PUBLISHER_JOB_ID}/logs",text)
        self.assertNotIn("/actions/jobs/${V2_PUBLISHER_JOB_ID}/logs",text)
        self.assertNotIn("--allow-escape-sequences",text)
        self.assertIn("5373207353",text)
        self.assertIn("5373348599",text)
        self.assertIn("'inputs':{'science_run_id':'32503223236'}",text)
        self.assertIn("--input workflow-dispatch-v3.json",text)
        self.assertNotIn("-F \"inputs[science_run_id]",text)
        self.assertIn("COMBINED_OPENING_RECOVERY_V3_ALLOCATED",text)
        self.assertIn("COMBINED_OPENING_RECOVERY_V3_CONSUMED",text)
        self.assertNotIn("setup-micromamba@",text)
        self.assertNotIn("uvspec",text)

    def test_v3_opening_attempt1_solver_free_frozen_analysis(self):
        text=OPENING.read_text()
        self.assertIn("workflow_dispatch:",text)
        self.assertNotIn("workflow_run:",text)
        self.assertIn('test "$GITHUB_RUN_ATTEMPT" = 1',text)
        self.assertIn("combined-opening-v3-run-32503223236",text)
        self.assertIn("32508493509",text)
        self.assertIn("32510096551",text)
        self.assertIn("19bd924ab86ed0744b3fd77ce5d6756039674d5f",text)
        self.assertIn("path: frozen-analysis",text)
        self.assertIn("--repository-root frozen-analysis",text)
        self.assertNotIn("setup-micromamba@",text)
        self.assertNotIn("command -v uvspec",text)
        self.assertNotIn("/rerun",text)

    def test_v3_freeze_binds_exact_bytes(self):
        f=json.loads(FREEZE.read_text())
        self.assertEqual("FROZEN_FRESH_V3_CONTROL_PLANE_IDENTITY_NOT_DISPATCHED",f["status"])
        self.assertEqual(sha(REVIEW),f["reviewRawSha256"])
        self.assertEqual(sha(OPENING),f["openingWorkflowRawSha256"])
        self.assertEqual(sha(PUBLISHER),f["publisherWorkflowRawSha256"])
        self.assertEqual(sha(Path(__file__)),f["testRawSha256"])
        self.assertEqual(32510096551,f["failedV2PublisherRunId"])
        self.assertEqual(0,f["failedV2OpeningRunCount"])
        self.assertFalse(f["scientificResultOpeningAuthorizedByFreezeAlone"])
        self.assertFalse(f["scientificSolverExecutionAuthorized"])


if __name__ == "__main__":
    unittest.main()
