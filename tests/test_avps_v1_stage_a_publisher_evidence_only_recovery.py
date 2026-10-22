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

    def test_template_is_inactive_and_review_surface_is_explicit(self):
        rel = str(TEMPLATE.relative_to(ROOT))
        self.assertTrue(rel.startswith(".github/recovery-templates/"))
        self.assertFalse(rel.startswith(".github/workflows/"))
        self.assertIn("stage-a-publisher-evidence-only", rel)
        self.assertIn("Stage-A review file surface drift", TEXT)
        self.assertIn("tests/test_avps_v1_stage_a_publisher_evidence_only_recovery.py", TEXT)

    def test_permissions_are_strictly_read_only(self):
        required = (
            "actions: read",
            "contents: read",
            "issues: read",
            "pull-requests: read",
        )
        for token in required:
            self.assertIn(token, TEXT)
        forbidden = (
            "actions: write",
            "contents: write",
            "issues: write",
            "pull-requests: write",
        )
        for token in forbidden:
            self.assertNotIn(token, TEXT)

    def test_no_ref_issue_or_science_mutation_command_exists(self):
        self.assertIsNone(re.search(r"(?m)^\s*git\s+push(?:\s|$)", TEXT))
        self.assertIsNone(re.search(r"(?m)^\s*gh\s+api\s+(?:--method\s+POST|-X\s+POST)(?:\s|$)", TEXT))
        self.assertNotIn("/issues/60/comments\" -f body=", TEXT)
        self.assertNotIn("actions/workflows/avps-v1-science.yml/dispatches", TEXT)
        self.assertNotIn("workflow-dispatch", TEXT.lower())
        self.assertNotIn("science-dispatch.json", TEXT)

    def test_stage_a_contains_no_scientific_execution(self):
        lowered = TEXT.lower()
        self.assertNotIn("uvspec ", lowered)
        self.assertNotIn("mystic ", lowered)
        self.assertNotIn("libradtran", lowered)
        self.assertNotIn("setup-micromamba", lowered)
        self.assertNotIn("execute_case", lowered)
        self.assertIn("scientificRuntimeSetupPerformed':False", TEXT)
        self.assertIn("scientificExecutionPerformed':False", TEXT)
        self.assertIn("solverExecutionPerformed':False", TEXT)

    def test_request_is_fresh_attempt_one_and_evidence_only(self):
        self.assertIn('test "$GITHUB_RUN_ATTEMPT" = 1', TEXT)
        self.assertIn("r.get('schemaVersion') != 3", TEXT)
        self.assertIn("aerosol-vertical-profile-sensitivity-v1-stage-a-publisher-evidence-only-recovery", TEXT)
        self.assertIn("RECOVER_ALREADY_CONSUMED_PUBLISHER_EVIDENCE_ONLY_NO_SCIENCE", TEXT)
        for field in (
            "recoveryContractPr",
            "recoveryContractRunId",
            "recoveryContractHead",
            "stageAReviewPr",
            "stageAReviewRunId",
            "stageAReviewHead",
        ):
            self.assertIn(field, TEXT)

    def test_request_variables_are_exported_before_embedded_python_environment_reads(self):
        source = TEXT.index("source request.env")
        export = TEXT.index(
            "export ORDINAL AUTH_HEAD AUTH_PARENT PR_NUMBER RECOVERY_CONTRACT_PR "
            "RECOVERY_CONTRACT_RUN_ID RECOVERY_CONTRACT_HEAD STAGE_A_REVIEW_PR "
            "STAGE_A_REVIEW_RUN_ID STAGE_A_REVIEW_HEAD"
        )
        first_env_read_after_source = TEXT.index("os.environ", source)
        self.assertLess(source, export)
        self.assertLess(export, first_env_read_after_source)

    def test_stage_a_binds_green_two_stage_contract_and_own_green_review(self):
        self.assertIn("recoveryContractRunId", TEXT)
        self.assertIn("stageAReviewRunId", TEXT)
        self.assertIn("review run is not exact successful attempt 1", TEXT)
        self.assertIn("recovery-control-contract.json", TEXT)
        self.assertIn("historical-control-evidence.json", TEXT)
        self.assertIn("science-preflight-blocker.json", TEXT)
        self.assertIn("REVIEW_ONLY_NO_PUBLISHER_ACTIVATION_NO_SCIENCE_NO_SOLVER", TEXT)
        self.assertIn("FROZEN_SCIENCE_PREFLIGHT_EXPECTED_TO_REJECT_LEGITIMATE_CONSUMED_MARKER", TEXT)
        self.assertIn("publisher-evidence-only-recovery", TEXT)
        self.assertIn("actionsWritePermitted", TEXT)
        self.assertIn("scienceWorkflowDispatchPermitted", TEXT)

    def test_activation_control_must_be_direct_child_of_live_main_and_exact_reviewed_blob(self):
        self.assertIn('test "${CONTROL_PARENTS[0]}" = "$LIVE_MAIN"', TEXT)
        self.assertIn('test "${#CONTROL_CHANGED[@]}" = 1', TEXT)
        self.assertIn('test "${CONTROL_CHANGED[0]}" = .github/workflows/avps-v1-dispatch-publisher.yml', TEXT)
        self.assertIn("avps-v1-stage-a-publisher-evidence-only-recovery.yml", TEXT)
        self.assertIn('test "$CONTROL_WORKFLOW_BLOB" = "$REVIEW_WORKFLOW_BLOB"', TEXT)

    def test_exact_authorization_and_preauthorization_evidence_are_bound(self):
        self.assertIn("AUTHORIZATION_REVIEW_PASS_ZERO_RUNTIME", TEXT)
        self.assertIn("PREAUTHORIZATION_SURFACE_CLEAN_NOT_ALLOCATED", TEXT)
        self.assertIn("PASS_CANDIDATE_SEEDS_AUTHORIZATION_RECHECK_NOT_ALLOCATED", TEXT)
        self.assertIn("authorization review artifact drift", TEXT)
        self.assertIn("preauthorization artifact drift", TEXT)
        self.assertIn("sha256sum auth-review.zip", TEXT)
        self.assertIn("sha256sum preauth.zip", TEXT)

    def test_three_prior_failures_and_original_boundary_are_required(self):
        self.assertIn("THREE_PRIOR_PUBLISHER_RUNS_CONFIRMED_NO_SCIENCE_NO_SOLVER", TEXT)
        self.assertIn("len(h.get('priorPublisherRuns',[]))!=3", TEXT)
        self.assertIn("prior publisher run set drift", TEXT)
        self.assertIn("prior publisher", TEXT)
        self.assertIn("terminal attempt-1 failure", TEXT)
        self.assertIn("originalPublisherExactRelevantSteps", TEXT)
        self.assertIn("original publisher boundary drift", TEXT)
        self.assertIn("historical failed step", TEXT)
        self.assertIn("historical publisher evidence unexpectedly exists", TEXT)

    def test_exact_single_consumption_and_zero_science_are_required(self):
        self.assertIn("expected exactly one reviewed allocation marker", TEXT)
        self.assertIn("expected exactly one consumed marker", TEXT)
        self.assertIn("competing AVPS allocation marker exists", TEXT)
        self.assertIn("AVPS dispatch branch already has workflow runs", TEXT)
        self.assertIn('grep -q "^${AUTH_HEAD}[[:space:]]" dispatch-ls-remote.txt', TEXT)

    def test_receipt_matches_two_stage_contract_and_records_no_new_consumption(self):
        self.assertIn("'status':'DISPATCH_PUBLISHED_ZERO_RUNTIME'", TEXT)
        self.assertIn("'actualGitPush':True", TEXT)
        self.assertIn("'actualGitPushPerformedByThisRun':False", TEXT)
        self.assertIn("'currentConsumedMarkerPosted':True", TEXT)
        self.assertIn("'currentConsumedMarkerPostedByThisRun':False", TEXT)
        self.assertIn("'scienceTriggerMode':'NONE_STAGE_A_EVIDENCE_ONLY'", TEXT)
        self.assertIn("'scienceWorkflowDispatchPerformed':False", TEXT)
        self.assertIn("POST_CONSUMPTION_PUBLISHER_RECOVERY_PASS_NO_SECOND_CONSUMPTION_NO_SCIENCE_TRIGGER", TEXT)
        self.assertIn("'dispatchPushRepeated':False", TEXT)
        self.assertIn("'consumedMarkerRepeated':False", TEXT)
        self.assertIn("'scienceRunCountBeforeAndDuringStageA':0", TEXT)

    def test_artifact_upload_is_terminal_workflow_step(self):
        step_names = re.findall(r"(?m)^      - name: (.+)$", TEXT)
        self.assertTrue(step_names)
        self.assertEqual(step_names[-1], "Persist immutable Stage-A publisher evidence and stop")
        upload = TEXT.index("Persist immutable Stage-A publisher evidence and stop")
        self.assertNotIn("- name:", TEXT[upload + len("Persist immutable Stage-A publisher evidence and stop"):])
        self.assertIn("name: avps-v1-dispatch-publisher-ordinal-${{ steps.identity.outputs.ordinal }}", TEXT)


if __name__ == "__main__":
    unittest.main()
