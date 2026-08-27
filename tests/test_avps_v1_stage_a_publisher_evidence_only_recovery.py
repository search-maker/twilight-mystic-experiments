from __future__ import annotations

import hashlib
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACTIVE = ROOT / ".github/workflows/avps-v1-dispatch-publisher.yml"
TEMPLATE = ROOT / ".github/recovery-templates/avps-v1-stage-a-publisher-evidence-only-recovery.yml"
TEXT = TEMPLATE.read_text()
EXPECTED_ACTIVE_BLOB = "cd8aa5151533133a33c046ad2bed2bd7e2c11089"


def git_blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


class AvpsStageAPublisherEvidenceOnlyRecovery(unittest.TestCase):
    def test_active_frozen_publisher_remains_untouched_in_review(self):
        self.assertEqual(git_blob(ACTIVE), EXPECTED_ACTIVE_BLOB)
        self.assertNotEqual(git_blob(TEMPLATE), EXPECTED_ACTIVE_BLOB)

    def test_template_remains_inactive_and_two_file_review_only(self):
        rel = str(TEMPLATE.relative_to(ROOT))
        self.assertTrue(rel.startswith(".github/recovery-templates/"))
        self.assertFalse(rel.startswith(".github/workflows/"))
        self.assertIn("Stage-A review file surface drift", TEXT)
        self.assertIn("tests/test_avps_v1_stage_a_publisher_evidence_only_recovery.py", TEXT)

    def test_permissions_are_strictly_read_only(self):
        for token in ("actions: read", "contents: read", "issues: read", "pull-requests: read"):
            self.assertIn(token, TEXT)
        for token in ("actions: write", "contents: write", "issues: write", "pull-requests: write"):
            self.assertNotIn(token, TEXT)

    def test_no_control_mutation_or_science_dispatch_exists(self):
        self.assertIsNone(re.search(r"(?m)^\s*git\s+push(?:\s|$)", TEXT))
        self.assertIsNone(re.search(r"(?m)^\s*gh\s+api\s+(?:--method\s+POST|-X\s+POST)(?:\s|$)", TEXT))
        self.assertNotIn("actions/workflows/avps-v1-science.yml/dispatches", TEXT)
        self.assertNotIn("science-dispatch.json", TEXT)
        self.assertNotIn("uvspec ", TEXT.lower())
        self.assertNotIn("mystic ", TEXT.lower())
        self.assertNotIn("libradtran", TEXT.lower())
        self.assertNotIn("setup-micromamba", TEXT.lower())
        self.assertNotIn("execute_case", TEXT.lower())

    def test_request_is_v3_fresh_attempt_one_and_evidence_only(self):
        self.assertIn('test "$GITHUB_RUN_ATTEMPT" = 1', TEXT)
        self.assertIn("r.get('schemaVersion') != 4", TEXT)
        self.assertIn("aerosol-vertical-profile-sensitivity-v1-stage-a-publisher-evidence-only-recovery", TEXT)
        self.assertIn("RECOVER_ALREADY_CONSUMED_PUBLISHER_EVIDENCE_ONLY_NO_SCIENCE", TEXT)
        for field in (
            "recoveryContractPr", "recoveryContractRunId", "recoveryContractHead",
            "stageAReviewPr", "stageAReviewRunId", "stageAReviewHead",
            "priorStageAFailureRunId", "priorStageAFailureJobId",
            "priorStageAFailureHead", "priorStageAFailureHistoryBranch",
        ):
            self.assertIn(field, TEXT)

    def test_request_environment_is_exported_before_python_reads(self):
        source = TEXT.index("source request.env")
        export = TEXT.index("export ORDINAL AUTH_HEAD AUTH_PARENT PR_NUMBER")
        first_env_read = TEXT.index("os.environ", source)
        self.assertLess(source, export)
        self.assertLess(export, first_env_read)
        for token in (
            "PRIOR_STAGE_A_FAILURE_RUN_ID", "PRIOR_STAGE_A_FAILURE_JOB_ID",
            "PRIOR_STAGE_A_FAILURE_HEAD", "PRIOR_STAGE_A_FAILURE_HISTORY_BRANCH",
        ):
            self.assertIn(token, TEXT[export:first_env_read])

    def test_binds_exact_contract_blocker_and_own_v3_review(self):
        self.assertIn("REVIEW_ONLY_NO_PUBLISHER_ACTIVATION_NO_SCIENCE_NO_SOLVER", TEXT)
        self.assertIn("THREE_PRIOR_PUBLISHER_RUNS_CONFIRMED_NO_SCIENCE_NO_SOLVER", TEXT)
        self.assertIn("FROZEN_SCIENCE_WORKFLOW_EXPECTED_TO_REFUSE_PRE_SOLVER_ON_LEGITIMATE_CONSUMED_MARKER", TEXT)
        self.assertIn("review/avps-v1-ordinal40-stage-a-publisher-evidence-only-3", TEXT)
        self.assertNotIn("review/avps-v1-ordinal40-stage-a-publisher-evidence-only-2", TEXT)
        self.assertNotIn("review/avps-v1-ordinal40-stage-a-publisher-evidence-only-1", TEXT)
        self.assertIn('test "$CONTROL_WORKFLOW_BLOB" = "$REVIEW_WORKFLOW_BLOB"', TEXT)

    def test_exact_authorization_and_preauthorization_evidence_are_bound(self):
        self.assertIn("AUTHORIZATION_REVIEW_PASS_ZERO_RUNTIME", TEXT)
        self.assertIn("PREAUTHORIZATION_SURFACE_CLEAN_NOT_ALLOCATED", TEXT)
        self.assertIn("PASS_CANDIDATE_SEEDS_AUTHORIZATION_RECHECK_NOT_ALLOCATED", TEXT)
        self.assertIn("sha256sum auth-review.zip", TEXT)
        self.assertIn("sha256sum preauth.zip", TEXT)
        self.assertIn("authorization review crossed zero-runtime boundary", TEXT)

    def test_four_prior_failures_are_required_exactly(self):
        self.assertIn("prior-publisher-history.json", TEXT)
        self.assertIn("len(prior)!=4", TEXT)
        self.assertIn("exact four unique prior publisher failures required", TEXT)
        self.assertIn("prior publisher run set drift", TEXT)
        self.assertIn("terminal attempt-1 failure", TEXT)
        self.assertIn("historical failed step", TEXT)
        self.assertIn("historical publisher evidence unexpectedly exists", TEXT)
        self.assertIn("history/avps-v1-stage-a-publisher-evidence-recovery-failed-1", TEXT)
        self.assertIn("Bind reviewed Stage-A request and recovery contracts", TEXT)
        self.assertIn("prior Stage-A v1 boundary drift", TEXT)
        self.assertIn("prior Stage-A v1 failure unexpectedly produced Actions artifacts", TEXT)

    def test_original_consuming_boundary_is_still_frozen(self):
        self.assertIn("originalPublisherExactRelevantSteps", TEXT)
        self.assertIn("original publisher boundary drift", TEXT)

    def test_exact_single_consumption_dispatch_head_and_zero_science_are_required(self):
        self.assertIn("expected exactly one reviewed allocation marker", TEXT)
        self.assertIn("expected exactly one consumed marker", TEXT)
        self.assertIn("competing AVPS allocation marker exists", TEXT)
        self.assertIn("AVPS dispatch branch already has workflow runs", TEXT)
        self.assertIn('grep -q "^${AUTH_HEAD}[[:space:]]" dispatch-ls-remote.txt', TEXT)

    def test_receipt_records_no_new_consumption_and_all_four_failures(self):
        self.assertIn("'status':'DISPATCH_PUBLISHED_ZERO_RUNTIME'", TEXT)
        self.assertIn("'actualGitPushPerformedByThisRun':False", TEXT)
        self.assertIn("'currentConsumedMarkerPostedByThisRun':False", TEXT)
        self.assertIn("'scienceTriggerMode':'NONE_STAGE_A_EVIDENCE_ONLY'", TEXT)
        self.assertIn("'scienceWorkflowDispatchPerformed':False", TEXT)
        self.assertIn("POST_CONSUMPTION_PUBLISHER_RECOVERY_PASS_NO_SECOND_CONSUMPTION_NO_SCIENCE_TRIGGER", TEXT)
        self.assertIn("'dispatchPushRepeated':False", TEXT)
        self.assertIn("'consumedMarkerRepeated':False", TEXT)
        self.assertIn("'scienceRunCountBeforeAndDuringStageA':0", TEXT)
        self.assertIn("'priorStageAFailedActivationRunId'", TEXT)
        self.assertIn("'stageARecoveryVersion':3", TEXT)
        self.assertIn("'scientificRuntimeSetupPerformed':False", TEXT)
        self.assertIn("'scientificExecutionPerformed':False", TEXT)
        self.assertIn("'solverExecutionPerformed':False", TEXT)

    def test_artifact_upload_is_terminal_step(self):
        step_names = re.findall(r"(?m)^      - name: (.+)$", TEXT)
        self.assertTrue(step_names)
        self.assertEqual(step_names[-1], "Persist immutable Stage-A v3 publisher evidence and stop")
        upload = TEXT.index("Persist immutable Stage-A v3 publisher evidence and stop")
        self.assertNotIn("- name:", TEXT[upload + len("Persist immutable Stage-A v3 publisher evidence and stop"):])
        self.assertIn("name: avps-v1-dispatch-publisher-ordinal-${{ steps.identity.outputs.ordinal }}", TEXT)


if __name__ == "__main__":
    unittest.main()
