from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELPER_PATH = ROOT / "review/avps-v1-ordinal40-stage-b-science-recovery-v1/post_consumption_surface.py"
CONTRACT_PATH = ROOT / "review/avps-v1-ordinal40-stage-b-science-recovery-v1/RECOVERY_CONTROL_CONTRACT.review.json"

spec = importlib.util.spec_from_file_location("avps_stage_b_surface_tested", HELPER_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError("cannot import Stage-B recovery helper")
helper = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = helper
spec.loader.exec_module(helper)


class AvpsStageBPostConsumptionSurface(unittest.TestCase):
    def setUp(self):
        self.contract = json.loads(CONTRACT_PATH.read_text())

    def test_contract_is_review_only_and_binds_completed_stage_a(self):
        c = self.contract
        self.assertEqual(c["status"], "REVIEW_ONLY_STAGE_B_NO_ACTIVATION_NO_SCIENCE_NO_SOLVER")
        self.assertEqual(c["baseMainSha"], "99ade7798627e67921139697ba1a004fa8a304bb")
        self.assertEqual(c["scientificOrdinal"], 40)
        self.assertEqual(c["stageA"]["reviewPr"], 573)
        self.assertEqual(c["stageA"]["publisherRunId"], 33123226959)
        self.assertEqual(c["stageA"]["artifactId"], 9667291127)
        self.assertEqual(c["stageA"]["artifactDigest"], "sha256:0338d418d554c5ceaead8712a1ee860c2ee154d839cfe7c038098607786a0b3f")
        for key in (
            "activationAuthorizedByThisReview",
            "scienceDispatchAuthorizedByThisReview",
            "scientificExecutionAuthorizedByThisReview",
            "solverExecutionAuthorizedByThisReview",
            "resultOpeningAuthorizedByThisReview",
            "mainMutationAuthorizedByThisReview",
            "authorizationMutationAuthorizedByThisReview",
            "dispatchMutationAuthorizedByThisReview",
            "issue60MutationAuthorizedByThisReview",
            "productionAuthorized",
        ):
            self.assertIs(c[key], False, key)

    def test_exact_frozen_science_and_control_bytes_are_still_present(self):
        actual = helper.validate_frozen_science_bytes(ROOT)
        self.assertEqual(actual, helper.EXPECTED_SCIENCE_BLOBS)
        c = self.contract["frozenControlAndScienceBindings"]
        self.assertEqual(c["originalScienceWorkflowGitBlobSha1"], actual[".github/workflows/avps-v1-science.yml"])
        self.assertEqual(c["scienceGuardGitBlobSha1"], actual["experiments/aerosol-vertical-profile-sensitivity-v1/science_guard.py"])
        self.assertEqual(c["preauthorizationSurfaceGitBlobSha1"], actual["experiments/aerosol-vertical-profile-sensitivity-v1/preauthorization_surface.py"])
        self.assertEqual(c["globalOrdinalGitBlobSha1"], actual["experiments/aerosol-vertical-profile-sensitivity-v1/global_ordinal.py"])
        self.assertEqual(c["freshnessGitBlobSha1"], actual["experiments/aerosol-vertical-profile-sensitivity-v1/freshness.py"])
        self.assertEqual(c["executionContractGitBlobSha1"], actual["experiments/aerosol-vertical-profile-sensitivity-v1/execution-contract.review.json"])

    def _payload(self):
        return {
            "branches": [
                {"name": helper.FAILED_HISTORY_BRANCH, "commit": {"sha": helper.FAILED_HEAD}},
                {"name": helper.AUTH_BRANCH, "commit": {"sha": "338ee82c8e088e929f45782b1f7ac1c3aaaaa533"}},
                {"name": helper.DISPATCH_BRANCH, "commit": {"sha": "338ee82c8e088e929f45782b1f7ac1c3aaaaa533"}},
            ],
            "pulls": [
                {
                    "number": helper.FAILED_PR,
                    "state": "closed",
                    "merged_at": None,
                    "head": {"ref": helper.AUTH_BRANCH, "sha": helper.FAILED_HEAD},
                }
            ],
            "runs": [
                {
                    "id": helper.FAILED_REVIEW_RUN,
                    "head_branch": helper.AUTH_BRANCH,
                    "head_sha": helper.FAILED_HEAD,
                    "path": helper.AUTH_REVIEW_WORKFLOW,
                    "event": "pull_request",
                    "run_attempt": 1,
                    "status": "completed",
                    "conclusion": "failure",
                }
            ],
            "issue60Comments": [
                {
                    "id": 1,
                    "body": "ORDINAL40_AVPS_V1_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED commit=338ee82c8e088e929f45782b1f7ac1c3aaaaa533 parent=99ade7798627e67921139697ba1a004fa8a304bb pr=565",
                },
                {"id": 2, "body": "ORDINAL40_AVPS_V1_DISPATCH_CONSUMED"},
            ],
        }

    def test_failed_history_proof_deliberately_tolerates_current_legitimate_consumption(self):
        out = helper.recovery_failed_authorization_history(self._payload(), 40)
        self.assertEqual(out["heads"], [helper.FAILED_HEAD])
        self.assertEqual(out["prNumbers"], [helper.FAILED_PR])
        self.assertEqual(out["reviewRunIds"], [helper.FAILED_REVIEW_RUN])
        self.assertIn("CURRENT_SUCCESSFUL_HEAD_CONSUMPTION", out["recoverySemantics"])

    def test_failed_history_proof_still_refuses_allocation_of_failed_head(self):
        payload = self._payload()
        payload["issue60Comments"].append({
            "id": 3,
            "body": f"ORDINAL40_AVPS_V1_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED commit={helper.FAILED_HEAD} parent=99ade7798627e67921139697ba1a004fa8a304bb pr={helper.FAILED_PR}",
        })
        with self.assertRaisesRegex(helper.RecoverySurfaceRefusal, "acquired an allocation marker"):
            helper.recovery_failed_authorization_history(payload, 40)

    def test_failed_history_proof_still_refuses_science_on_failed_head(self):
        payload = self._payload()
        payload["runs"].append({
            "id": 999,
            "head_branch": helper.DISPATCH_BRANCH,
            "head_sha": helper.FAILED_HEAD,
            "path": helper.SCIENCE_WORKFLOW,
            "event": "workflow_dispatch",
            "run_attempt": 1,
            "status": "completed",
            "conclusion": "failure",
        })
        with self.assertRaisesRegex(helper.RecoverySurfaceRefusal, "has an AVPS science run"):
            helper.recovery_failed_authorization_history(payload, 40)

    def test_repair_scope_is_only_failed_history_subproof_then_original_validator(self):
        text = HELPER_PATH.read_text()
        self.assertIn("control.failed_authorization_history = recovery_failed_authorization_history", text)
        self.assertIn("control.failed_authorization_history = original_failed_history", text)
        self.assertIn("freshness.validate_dispatch(surface, ordinal, head_sha, post_dispatch=True)", text)
        self.assertIn("FAILED_AUTHORIZATION_HISTORY_SUBPROOF_ONLY", text)
        for forbidden in (
            "uvspec ",
            "execute_case(",
            "git push",
            "issues/60/comments",
            "actions/workflows/avps-v1-science.yml/dispatches",
        ):
            self.assertNotIn(forbidden, text)

    def test_scientific_identity_and_result_boundary_are_frozen(self):
        s = self.contract["frozenScientificExperiment"]
        self.assertEqual(s["caseCount"], 360)
        self.assertEqual(s["commonRandomNumberGroupCount"], 72)
        self.assertEqual(s["fieldFactor"], 3.14)
        self.assertEqual(s["photonHistoriesPerCase"], 20_000_000)
        self.assertFalse(s["taylorOrJerusalemFitAuthorized"])
        rb = self.contract["resultBoundary"]
        self.assertTrue(rb["stageBMayExecuteFrozenCasesOnlyAfterRecoveredGuardPasses"])
        self.assertFalse(rb["stageBPrimaryResultOpeningAuthorized"])
        self.assertFalse(rb["stageBAggregateInterpretationAuthorized"])
        self.assertTrue(rb["rawCaseArtifactsMustRemainUninterpretedUntilSeparateExact360AggregateReview"])


if __name__ == "__main__":
    unittest.main()
