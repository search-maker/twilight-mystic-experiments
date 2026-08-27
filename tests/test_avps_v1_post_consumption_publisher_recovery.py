from __future__ import annotations

import hashlib
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACTIVE = ROOT / ".github/workflows/avps-v1-dispatch-publisher.yml"
TEMPLATE = ROOT / ".github/recovery-templates/avps-v1-dispatch-publisher-post-consumption-recovery.yml"
TEXT = TEMPLATE.read_text()
EXPECTED_ACTIVE_BLOB = "cd8aa5151533133a33c046ad2bed2bd7e2c11089"


def git_blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


class AvpsPostConsumptionPublisherRecovery(unittest.TestCase):
    def test_active_frozen_publisher_is_untouched_in_review(self):
        self.assertEqual(git_blob(ACTIVE), EXPECTED_ACTIVE_BLOB)
        self.assertNotEqual(git_blob(TEMPLATE), EXPECTED_ACTIVE_BLOB)

    def test_template_is_not_an_active_workflow_path(self):
        self.assertTrue(str(TEMPLATE.relative_to(ROOT)).startswith(".github/recovery-templates/"))
        self.assertFalse(str(TEMPLATE.relative_to(ROOT)).startswith(".github/workflows/"))

    def test_recovery_is_read_only_for_repo_and_issue_state(self):
        self.assertIn("actions: write", TEXT)
        self.assertIn("contents: read", TEXT)
        self.assertIn("issues: read", TEXT)
        self.assertNotIn("contents: write", TEXT)
        self.assertNotIn("issues: write", TEXT)
        self.assertIsNone(re.search(r"(?m)^\s*git\s+push(?:\s|$)", TEXT))
        self.assertNotIn('issues/60/comments" -f body=', TEXT)

    def test_recovery_requires_fresh_attempt_one_request(self):
        self.assertIn('test "$GITHUB_RUN_ATTEMPT" = 1', TEXT)
        self.assertIn("schemaVersion') != 2", TEXT)
        self.assertIn("RECOVER_ALREADY_CONSUMED_DISPATCH_AND_TRIGGER_SCIENCE", TEXT)
        self.assertIn("failedPublisherRunId", TEXT)
        self.assertIn("failedPublisherRequestHead", TEXT)
        self.assertIn("recoveryReviewPr", TEXT)
        self.assertIn("recoveryReviewHead", TEXT)

    def test_recovery_control_commit_is_direct_child_of_live_main_and_reviewed_blob(self):
        self.assertIn('test "${CONTROL_PARENTS[0]}" = "$LIVE_MAIN"', TEXT)
        self.assertIn('test "${#CONTROL_CHANGED[@]}" = 1', TEXT)
        self.assertIn('test "${CONTROL_CHANGED[0]}" = .github/workflows/avps-v1-dispatch-publisher.yml', TEXT)
        self.assertIn(".github/recovery-templates/avps-v1-dispatch-publisher-post-consumption-recovery.yml", TEXT)
        self.assertIn('test "$CONTROL_WORKFLOW_BLOB" = "$REVIEW_WORKFLOW_BLOB"', TEXT)
        self.assertIn("recovery review PR must remain Draft/open/unmerged", TEXT)

    def test_original_publisher_must_have_consumed_then_failed_before_science(self):
        for name in (
            "Bind request, authorization, preauthorization and zero-runtime review",
            "Prove dispatch eligible before creating ref",
            "Perform actual git push that consumes dispatch identity",
        ):
            self.assertIn(name, TEXT)
        self.assertIn("Mark consumed once and prove post-dispatch state", TEXT)
        self.assertIn("Stage immutable successful publisher evidence", TEXT)
        self.assertIn("Persist immutable publisher evidence before science trigger", TEXT)
        self.assertIn("Explicitly dispatch attempt-1 science on pushed ref", TEXT)
        self.assertIn("GlobalOrdinalRefusal: ordinal ${ORDINAL} already has consumed marker", TEXT)
        self.assertIn("original publisher crossed recovery boundary", TEXT)

    def test_current_state_requires_exact_single_allocation_and_consumption(self):
        self.assertIn("expected exactly one correct allocation marker", TEXT)
        self.assertIn("expected exactly one consumed marker", TEXT)
        self.assertIn("competing AVPS allocation marker exists", TEXT)
        self.assertIn('grep -q "^${AUTH_HEAD}[[:space:]]" dispatch-ls-remote.txt', TEXT)
        self.assertIn("AVPS science already exists on consumed dispatch ref", TEXT)
        self.assertIn("a successful publisher already exists; refuse duplicate recovery", TEXT)
        self.assertIn("publisher rerun history detected", TEXT)

    def test_recovered_artifact_matches_frozen_science_contract(self):
        required = (
            "'status':'DISPATCH_PUBLISHED_ZERO_RUNTIME'",
            "'authorizationHead':os.environ['AUTH_HEAD']",
            "'authorizationParent':os.environ['AUTH_PARENT']",
            "'authorizationPr':int(os.environ['PR_NUMBER'])",
            "'dispatchBranchHeadSha':os.environ['AUTH_HEAD']",
            "'actualGitPush':True",
            "'currentConsumedMarkerPosted':True",
            "'scientificRuntimeSetupPerformed':False",
            "'scientificExecutionPerformed':False",
            "'solverExecutionPerformed':False",
        )
        for token in required:
            self.assertIn(token, TEXT)
        self.assertIn("postConsumptionRecovery", TEXT)
        self.assertIn("actualGitPushPerformedByThisRun", TEXT)
        self.assertIn("currentConsumedMarkerPostedByThisRun", TEXT)
        self.assertIn("POST_CONSUMPTION_PUBLISHER_RECOVERY_PASS_NO_SECOND_CONSUMPTION", TEXT)

    def test_recovery_only_dispatches_existing_frozen_science_workflow(self):
        self.assertIn("actions/workflows/avps-v1-science.yml/dispatches", TEXT)
        self.assertIn("EXPLICIT_WORKFLOW_DISPATCH_AFTER_VERIFIED_POST_CONSUMPTION_RECOVERY", TEXT)
        lowered = TEXT.lower()
        self.assertNotIn("uvspec ", lowered)
        self.assertNotIn("libradtran", lowered)
        self.assertNotIn("mystic", lowered)

    def test_artifact_is_persisted_before_science_trigger(self):
        upload = TEXT.index("Persist immutable recovered publisher evidence before science trigger")
        trigger = TEXT.index("Explicitly dispatch attempt-1 science on existing consumed ref")
        self.assertLess(upload, trigger)
        self.assertIn("name: avps-v1-dispatch-publisher-ordinal-${{ steps.identity.outputs.ordinal }}", TEXT)


if __name__ == "__main__":
    unittest.main()
