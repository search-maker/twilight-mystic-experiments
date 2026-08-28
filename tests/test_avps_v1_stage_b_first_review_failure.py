from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "review/avps-v1-ordinal40-stage-b-science-recovery-v1/FIRST_REVIEW_FAILURE_AND_429_RETRY.review.json"


class AvpsStageBFirstReviewFailure(unittest.TestCase):
    def setUp(self):
        self.r = json.loads(RECORD.read_text())

    def test_failed_review_identity_and_no_rerun_are_frozen(self):
        r = self.r
        self.assertEqual(r["status"], "FROZEN_FAILED_REVIEW_NO_SCIENCE_FRESH_ATTEMPT1_REQUIRED")
        self.assertEqual(r["failedReviewPr"], 574)
        self.assertEqual(r["failedReviewHead"], "9a3390d27963359c7c39b1762a1b8eec90e24185")
        self.assertIs(r["failedReviewMustNotBeRerun"], True)
        self.assertIs(r["failedReviewMustNotBeActivated"], True)

    def test_generic_failure_is_static_review_only(self):
        f = self.r["genericContractFailure"]
        self.assertEqual(f["runId"], 33130500968)
        self.assertEqual(f["runAttempt"], 1)
        self.assertEqual(f["jobId"], 98718644364)
        self.assertEqual(f["testsPassed"], 1013)
        self.assertEqual(f["testsTotal"], 1014)
        self.assertEqual(f["failureClass"], "STATIC_REVIEW_OVERCONSTRAINT")
        self.assertIs(f["scientificIdentityFailureObserved"], False)
        self.assertIs(f["scientificExecutionObserved"], False)
        self.assertIs(f["solverExecutionObserved"], False)
        self.assertIs(f["resultOpeningObserved"], False)

    def test_live_failure_is_exact_429_after_tracked_tree_pass(self):
        f = self.r["liveSurfaceReviewFailure"]
        self.assertEqual(f["runId"], 33130501045)
        self.assertEqual(f["runAttempt"], 1)
        self.assertEqual(f["jobId"], 98718644744)
        self.assertEqual(f["failureClass"], "READ_ONLY_GITHUB_METADATA_ACQUISITION_RATE_LIMIT")
        self.assertEqual(f["exactFailureNeedle"], "HTTP Error 429: Too Many Requests")
        self.assertEqual(f["trackedTreeStatus"], "PASS_NO_TRACKED_TREE_CANDIDATE_SEED_COLLISIONS_OUTSIDE_SELF_LEDGER")
        self.assertEqual(f["trackedTreeFilesScanned"], 417)
        self.assertEqual(f["trackedTreeOccurrenceCount"], 76)
        self.assertIs(f["recoveredFreshnessConstructionStarted"], False)
        self.assertIs(f["unchangedPostDispatchFreshnessValidatorRan"], False)
        self.assertIs(f["unchangedScienceGuardRan"], False)
        self.assertIs(f["scientificExecutionObserved"], False)
        self.assertIs(f["solverExecutionObserved"], False)

    def test_retry_policy_is_bounded_exact_429_only(self):
        p = self.r["v2RetryPolicy"]
        self.assertEqual(p["frozenScannerGitBlobSha1"], "1cfb54e3ed96ff57f84739b4e4393544c49e2d32")
        self.assertEqual(p["maximumAttempts"], 3)
        self.assertEqual(p["retryOnlyExactNeedle"], "HTTP Error 429: Too Many Requests")
        self.assertEqual(p["retryDelaysSeconds"], [60, 120])
        self.assertIs(p["partialOutputDeletedBeforeRetry"], True)
        self.assertIs(p["non429FailureRetryPermitted"], False)
        self.assertIs(p["http503RetryPermitted"], False)
        self.assertIs(p["third429Terminal"], True)
        self.assertIs(p["scannerBytesMayChange"], False)
        self.assertIs(p["seedCollisionMayBeRetried"], False)

    def test_v2_can_validate_live_surface_but_is_not_activation_ready(self):
        v2 = self.r["freshReviewV2"]
        self.assertEqual(v2["branch"], "review/avps-v1-ordinal40-stage-b-science-recovery-control-2")
        self.assertIs(v2["mustUseFreshPullRequest"], True)
        self.assertIs(v2["mustUseFreshAttempt1Runs"], True)
        self.assertIs(v2["genericContractSuccessRequired"], True)
        self.assertIs(v2["dedicatedLiveSurfaceReviewSuccessRequired"], True)
        self.assertIs(v2["dedicatedLiveReviewUses429RetryWrapper"], True)
        self.assertIs(v2["inactiveScienceTransportUses429RetryWrapper"], False)
        self.assertIs(v2["activationReadyIfBothReviewChecksPass"], False)
        self.assertIs(v2["activationBeforeBothSuccessesPermitted"], False)
        self.assertIn("separate Stage-B transport review", v2["nextRequiredReviewAfterGreenV2"])

    def test_science_state_remains_unopened(self):
        s = self.r["scienceStateAfterFailedReview"]
        self.assertIs(s["stageAComplete"], True)
        self.assertIs(s["stageBActivated"], False)
        self.assertIs(s["avpsScienceRunStarted"], False)
        self.assertIs(s["scientificSolverRunStarted"], False)
        self.assertIs(s["scientificResultOpened"], False)
        self.assertIs(s["secondAllocationMarkerCreated"], False)
        self.assertIs(s["secondConsumedMarkerCreated"], False)
        self.assertIs(s["secondDispatchPushPerformed"], False)


if __name__ == "__main__":
    unittest.main()
