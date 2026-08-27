from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "review/avps-v1-ordinal40-post-consumption-recovery-v1"
CONTRACT = json.loads((REVIEW / "RECOVERY_CONTROL_CONTRACT.review.json").read_text())
HISTORY = json.loads((REVIEW / "HISTORICAL_CONTROL_EVIDENCE.review.json").read_text())
BLOCKER = json.loads((REVIEW / "SCIENCE_PREFLIGHT_BLOCKER.review.json").read_text())
EXECUTION_CONTRACT = ROOT / "experiments/aerosol-vertical-profile-sensitivity-v1/execution-contract.review.json"


def git_blob(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


class AvpsOrdinal40TwoStageRecoveryContract(unittest.TestCase):
    def test_review_authorizes_no_execution_or_mutation(self):
        self.assertEqual(CONTRACT["status"], "REVIEW_ONLY_NO_PUBLISHER_ACTIVATION_NO_SCIENCE_NO_SOLVER")
        for key in (
            "publisherRecoveryAuthorizedByThisReview",
            "scienceRecoveryAuthorizedByThisReview",
            "scientificExecutionAuthorizedByThisReview",
            "solverExecutionAuthorizedByThisReview",
            "resultOpeningAuthorizedByThisReview",
            "authorizationMutationAuthorizedByThisReview",
            "dispatchMutationAuthorizedByThisReview",
            "issue60MutationAuthorizedByThisReview",
            "mainMutationAuthorizedByThisReview",
            "productionAuthorized",
        ):
            self.assertIs(CONTRACT[key], False, key)

    def test_exact_ordinal40_identity_is_frozen(self):
        self.assertEqual(CONTRACT["baseMainSha"], "99ade7798627e67921139697ba1a004fa8a304bb")
        self.assertEqual(CONTRACT["scientificOrdinal"], 40)
        self.assertEqual(CONTRACT["authorizationPr"], 565)
        self.assertEqual(CONTRACT["authorizationHead"], "338ee82c8e088e929f45782b1f7ac1c3aaaaa533")
        self.assertEqual(CONTRACT["authorizationParent"], CONTRACT["baseMainSha"])
        self.assertEqual(CONTRACT["dispatchBranchHeadSha"], CONTRACT["authorizationHead"])

    def test_historical_evidence_freezes_all_three_prior_failures(self):
        self.assertEqual(HISTORY["status"], "THREE_PRIOR_PUBLISHER_RUNS_CONFIRMED_NO_SCIENCE_NO_SOLVER")
        rows = HISTORY["priorPublisherRuns"]
        self.assertEqual([r["runId"] for r in rows], [33114653044, 33117461748, 33119177406])
        self.assertTrue(all(r["runAttempt"] == 1 and r["conclusion"] == "failure" for r in rows))
        self.assertTrue(all(r["publisherEvidenceUploaded"] is False for r in rows))
        self.assertTrue(all(r["scienceDispatchReached"] is False for r in rows))
        self.assertTrue(all(r["solverExecutionObserved"] is False for r in rows))
        self.assertEqual(HISTORY["currentScienceWorkflowRunCount"], 0)
        self.assertEqual(HISTORY["allocationMarkerCount"], 1)
        self.assertEqual(HISTORY["consumedMarkerCount"], 1)

    def test_original_live_step_names_are_frozen(self):
        steps = {r["name"]: r["conclusion"] for r in HISTORY["originalPublisherExactRelevantSteps"]}
        self.assertEqual(steps["Actual git push consumes dispatch identity"], "success")
        self.assertNotIn("Perform actual git push that consumes dispatch identity", steps)
        self.assertEqual(steps["Mark consumed once and prove post-dispatch state"], "failure")
        self.assertEqual(steps["Explicitly dispatch attempt-1 science on pushed ref"], "skipped")
        self.assertIn("already has consumed marker", HISTORY["originalPublisherFailureLogNeedle"])

    def test_science_blocker_is_pre_solver_control_only(self):
        self.assertEqual(BLOCKER["failureBoundary"], "PRE_SOLVER")
        self.assertEqual(BLOCKER["requiredRepairScope"], "CONTROL_PLANE_ADMISSION_ONLY")
        self.assertEqual(BLOCKER["scienceWorkflowGitBlobSha1"], "55f48bbdf99aac58a96bd96f6735a4e56b8b466a")
        self.assertIn("build_dispatch_surface", BLOCKER["blockingCall"])
        self.assertIs(BLOCKER["publisherRecoveryMayAutoDispatchScience"], False)
        for key in (
            "scientificSourceMutationAllowed",
            "seedMutationAllowed",
            "caseUniverseMutationAllowed",
            "fieldFactorMutationAllowed",
            "runtimeIdentityMutationAllowed",
            "analysisMutationAllowed",
            "resultOpeningMutationAllowed",
        ):
            self.assertIs(BLOCKER[key], False, key)

    def test_stage_a_is_strictly_evidence_only_and_read_only(self):
        a = CONTRACT["stageA"]
        self.assertEqual(a["requiredPermissions"], {
            "actions": "read", "contents": "read", "issues": "read", "pull-requests": "read"
        })
        for key in (
            "actionsWritePermitted", "contentsWritePermitted", "issuesWritePermitted",
            "gitPushPermitted", "issue60PostPermitted", "scienceWorkflowDispatchPermitted",
        ):
            self.assertIs(a[key], False, key)
        self.assertEqual(a["requiredPublisherEvidenceStatus"], "DISPATCH_PUBLISHED_ZERO_RUNTIME")
        self.assertIs(a["mustProveZeroPriorScienceRuns"], True)

    def test_stage_b_may_repair_only_consumed_state_admission(self):
        b = CONTRACT["stageB"]
        self.assertIs(b["mustRequireStageASuccessfulPublisherEvidence"], True)
        self.assertIs(b["mustBindFrozenExecutionContractBlob"], True)
        self.assertIs(b["mustBindAllFrozenScientificSourceBlobs"], True)
        self.assertIs(b["mustRunLiveRepositoryGlobalSeedRecheck"], True)
        self.assertIs(b["newScientificOrdinalPermitted"], False)
        self.assertIs(b["newSeedAllocationPermitted"], False)
        self.assertIs(b["secondDispatchPushPermitted"], False)
        self.assertIs(b["secondConsumedMarkerPermitted"], False)
        self.assertIn("only the broken generic post-dispatch consumed-marker admission proof", b["allowedControlRepair"])

    def test_frozen_execution_contract_blob_and_science_parameters_match(self):
        frozen = CONTRACT["frozenExecutionContract"]
        self.assertEqual(git_blob(EXECUTION_CONTRACT), frozen["gitBlobSha1"])
        actual = json.loads(EXECUTION_CONTRACT.read_text())
        self.assertEqual(actual["expectedCaseCount"], frozen["expectedCaseCount"])
        self.assertEqual(actual["expectedGroupCount"], frozen["expectedGroupCount"])
        self.assertEqual(actual["fieldFactor"], frozen["fieldFactor"])
        self.assertEqual(actual["photonHistoriesPerCase"], frozen["photonHistoriesPerCase"])
        self.assertEqual(actual["orchestrationBindings"]["caseShards"], frozen["caseShards"])
        self.assertEqual(actual["orchestrationBindings"]["casesPerShard"], frozen["casesPerShard"])
        self.assertEqual(actual["runtimeIdentity"]["officialOptpropArchiveSha256"], frozen["officialOptpropArchiveSha256"])
        self.assertEqual(actual["runtimeIdentity"]["uvspecSha256"], frozen["uvspecSha256"])

    def test_asiv_recovery_precedent_is_explicitly_bound(self):
        p = CONTRACT["precedent"]
        self.assertEqual(p["stageId"], "asiv-matched-stellar-transport-recovery-v5-control-review")
        self.assertEqual(p["contractGitBlobSha1"], "bed640935666add4e78d394d4b10d0894ad68f03")


if __name__ == "__main__":
    unittest.main()
