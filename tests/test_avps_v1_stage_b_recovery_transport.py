from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ROOT / ".github/recovery-templates/avps-v1-stage-b-science-recovery-publisher.yml"
SCIENCE = ROOT / ".github/recovery-templates/avps-v1-stage-b-science-recovery.yml"
HELPER = ROOT / "review/avps-v1-ordinal40-stage-b-science-recovery-v1/post_consumption_surface.py"
PT = PUBLISHER.read_text()
ST = SCIENCE.read_text()
HT = HELPER.read_text()


class AvpsStageBRecoveryTransport(unittest.TestCase):
    def test_templates_are_inactive_review_files(self):
        for path in (PUBLISHER, SCIENCE):
            rel = str(path.relative_to(ROOT))
            self.assertTrue(rel.startswith(".github/recovery-templates/"), rel)
            self.assertFalse(rel.startswith(".github/workflows/"), rel)

    def test_publisher_has_only_actions_write_and_no_repository_mutation(self):
        self.assertIn("actions: write", PT)
        self.assertIn("contents: read", PT)
        self.assertIn("issues: read", PT)
        self.assertIn("pull-requests: read", PT)
        for forbidden in ("contents: write", "issues: write", "pull-requests: write"):
            self.assertNotIn(forbidden, PT)
        self.assertIsNone(re.search(r"(?m)^\s*git\s+push(?:\s|$)", PT))
        self.assertNotIn("issues/60/comments\" -f body=", PT)
        self.assertNotIn("uvspec ", PT.lower())
        self.assertNotIn("execute_case", PT)

    def test_publisher_persists_pre_dispatch_evidence_before_one_dispatch_call(self):
        persist = PT.index("Persist immutable pre-dispatch Stage-B publisher evidence")
        dispatch = PT.index("Dispatch exact reviewed Stage-B science recovery transport")
        self.assertLess(persist, dispatch)
        endpoint = 'actions/workflows/avps-v1-science.yml/dispatches'
        self.assertEqual(PT.count(endpoint), 1)
        self.assertIn('-f ref="$GITHUB_REF_NAME"', PT)
        self.assertIn("scienceWorkflowDispatchPerformedAtReceiptTime':False", PT)

    def test_transport_control_commit_is_exact_three_file_surface(self):
        for text in (PT, ST):
            self.assertIn('test "${#CONTROL_CHANGED[@]}" = 3', text)
            self.assertIn('.github/workflows/avps-v1-dispatch-publisher.yml', text)
            self.assertIn('.github/workflows/avps-v1-science.yml', text)
            self.assertIn('review/avps-v1-ordinal40-stage-b-science-recovery-v1/post_consumption_surface.py', text)

    def test_science_requires_actual_workflow_dispatch_but_preserves_logical_dispatch_identity(self):
        self.assertIn("on:\n  workflow_dispatch:", ST)
        self.assertIn('test "$GITHUB_EVENT_NAME" = workflow_dispatch', ST)
        self.assertIn("'eventName':os.environ['GITHUB_EVENT_NAME']", ST)
        self.assertIn("'refName':dispatch", ST)
        self.assertIn("'transportRef':os.environ['GITHUB_REF_NAME']", ST)
        self.assertIn("'logicalDispatchRef':dispatch", ST)
        self.assertIn("'logicalScienceHead':os.environ['AUTH_HEAD']", ST)

    def test_science_checkout_and_guard_use_exact_frozen_authorization_head(self):
        self.assertIn("ref: ${{ steps.identity.outputs.auth_head }}", ST)
        self.assertIn("ref: ${{ needs.preflight.outputs.auth_head }}", ST)
        self.assertIn("338ee82c8e088e929f45782b1f7ac1c3aaaaa533", ST)
        self.assertIn("55f48bbdf99aac58a96bd96f6735a4e56b8b466a", ST)
        self.assertIn("c774be7ea8655854bb85071a9fb260e21498beda", ST)
        self.assertIn("build_post_consumption_surface", ST)
        self.assertIn("sg.evaluate(Path('science')", ST)
        self.assertIn("EXACT_ONE_USE_AVPS_V1_DISPATCH_AUTHORIZED", ST)
        self.assertIn("FAILED_AUTHORIZATION_HISTORY_SUBPROOF_ONLY", HT)
        self.assertIn("freshness.validate_dispatch(surface, ordinal, head_sha, post_dispatch=True)", HT)

    def test_exact_science_identity_is_frozen(self):
        self.assertIn("candidateSeedCanonicalSha256", ST)
        self.assertIn("repository_global_seed_scan.py", ST)
        self.assertIn("--audit-mode authorization-recheck", ST)
        self.assertIn("--expected-branch-name \"dispatch/aerosol-vertical-profile-sensitivity-v1-ordinal-${ORDINAL}\"", ST)
        self.assertIn("rubin-libradtran=2.0.6=py312pl5321he9373c2_1", ST)
        self.assertIn("11daa1f1f4be0fd4ddf7e881ec2005498049674a1540d37b4b1e8f5e16052c7e", ST)
        self.assertIn("5d8bbf8e6b91ec3d405dee36f21a94afbb6e5ec6cd67da2dd5dd541738199d80", ST)
        self.assertIn("Execute exactly one preregistered AVPS case", ST)
        self.assertIn("execute_case(", ST)

    def test_four_frozen_90_case_shards_and_concurrency_are_preserved(self):
        for dep in (2, 4, 6, 8):
            self.assertIn(f"matrix{dep}", ST)
            self.assertIn(f"cases-dep{dep}:", ST)
        self.assertIn("if any(len(rows)!=90 for rows in by.values())", ST)
        self.assertEqual(ST.count("max-parallel: 2"), 4)
        self.assertIn("len({r['caseId'] for rows in by.values() for r in rows})!=360", ST)

    def test_no_result_opening_or_interpretation_exists_in_stage_b_transport(self):
        forbidden = (
            "aggregate_results",
            "open_results",
            "primary-analysis.json",
            "verified-analysis-input.json",
            "human-threshold.mjs",
            "COMPLETED_PREREGISTERED_AVPS_V1_PRIMARY_ANALYSIS_AFTER_EXACT_360_GATE",
        )
        for token in forbidden:
            self.assertNotIn(token, ST)
        self.assertIn("COMPLETE_EXACT_360_RAW_CASE_ARTIFACT_METADATA_RESULTS_UNOPENED", ST)
        self.assertIn("'caseContentsDownloadedOrOpened':False", ST)
        self.assertIn("'aggregateResultsExecuted':False", ST)
        self.assertIn("'primaryResultsOpened':False", ST)
        self.assertIn("'levelBResultsOpened':False", ST)
        self.assertIn("'scientificInterpretationPerformed':False", ST)

    def test_science_transport_cannot_mutate_refs_or_issue60(self):
        self.assertIn("actions: read", ST)
        self.assertIn("contents: read", ST)
        self.assertIn("issues: read", ST)
        for forbidden in ("actions: write", "contents: write", "issues: write"):
            self.assertNotIn(forbidden, ST)
        self.assertIsNone(re.search(r"(?m)^\s*git\s+push(?:\s|$)", ST))
        self.assertNotIn("issues/60/comments\" -f body=", ST)

    def test_one_shot_science_history_is_explicit(self):
        self.assertIn("Stage-B science one-shot history violated", ST)
        self.assertIn("ids != [int(os.environ['GITHUB_RUN_ID'])]", ST)
        self.assertIn("original dispatch branch has prior science", ST)


if __name__ == "__main__":
    unittest.main()
