from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "experiments/aerosol-family-challenge-v2"
CANDIDATE = BASE / "execution-candidate"
AUTH_WORKFLOW = ROOT / ".github/workflows/aerosol-family-v2-authorization-review.yml"
EXEC_WORKFLOW = ROOT / ".github/workflows/aerosol-family-v2-execution.yml"


def load_module(name: str, path: Path):
    sys.path.insert(0, str(path.parent))
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise RuntimeError(path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


class AuthorizationSurfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.freshness = load_module("afc2_activation_freshness", CANDIDATE / "freshness.py")
        sys.modules["freshness"] = cls.freshness
        cls.surface = load_module("afc2_activation_surface", CANDIDATE / "authorization_surface.py")

    def payload(self, ordinal: int = 29):
        auth = self.freshness.authorization_branch(ordinal)
        dispatch = self.freshness.dispatch_branch(ordinal)
        return {
            "branches": [
                {"name": "main", "commit": {"sha": "1" * 40}},
                {"name": "dispatch/other-project-ordinal-28", "commit": {"sha": "2" * 40}},
                {"name": auth, "commit": {"sha": "3" * 40}},
            ],
            "runs": [{"id": 777, "head_branch": dispatch, "display_title": self.freshness.execution_key(ordinal)}],
            "artifacts": [], "pulls": [], "issues": [], "issueComments": [],
            "pullReviewComments": [], "commitComments": [], "issue60Comments": [],
        }

    def test_current_run_is_excluded_and_prior_global_ordinal_is_preserved(self):
        out = self.surface.build_surface(self.payload(), 29, current_run_id=777)
        self.assertEqual(out["latestPriorConsumedScientificOrdinal"], 28)
        self.assertEqual(out["nextAvailableScientificOrdinal"], 29)
        self.assertEqual(out["candidatePriorScientificRunCount"], 0)
        self.assertEqual(out["candidateExecutionKeyPriorUseCount"], 0)
        self.assertTrue(out["authorizationBranchExists"])
        self.assertFalse(out["dispatchBranchExists"])

    def test_exact_current_marker_is_counted_but_not_self_deadlocked(self):
        p = self.payload()
        head, parent = "3" * 40, "4" * 40
        marker = self.freshness.authorization_marker(29, head, parent, 250)
        row = {"id": 9, "body": marker}
        p["issueComments"].append(dict(row))
        p["issue60Comments"].append(dict(row))
        out = self.surface.build_surface(p, 29, current_pr=250, current_run_id=777, marker_head=head, marker_parent=parent)
        self.assertEqual(out["matchingAuthorizationMarkers"], 1)
        self.assertEqual(out["matchingAuthorizationMarkerBodies"], [marker])
        self.assertEqual(out["positiveCandidateClaimsExcludingCurrent"], 0)

    def test_matching_marker_outside_issue60_remains_a_positive_claim(self):
        p = self.payload()
        head, parent = "3" * 40, "4" * 40
        marker = self.freshness.authorization_marker(29, head, parent, 250)
        p["issueComments"].append({"id": 10, "body": marker})
        out = self.surface.build_surface(p, 29, current_pr=250, current_run_id=777, marker_head=head, marker_parent=parent)
        self.assertEqual(out["matchingAuthorizationMarkers"], 0)
        self.assertGreater(out["positiveCandidateClaimsExcludingCurrent"], 0)

    def test_prior_execution_key_use_fails_freshness_surface(self):
        p = self.payload()
        p["artifacts"].append({"id": 91, "name": self.freshness.execution_key(29)})
        out = self.surface.build_surface(p, 29, current_run_id=777)
        self.assertEqual(out["candidateExecutionKeyPriorUseCount"], 1)

    def test_assertive_positive_candidate_claim_is_visible(self):
        p = self.payload()
        p["issues"].append({"id": 92, "title": "Allocated ordinal 29", "body": "The system allocated ordinal 29."})
        out = self.surface.build_surface(p, 29, current_run_id=777)
        self.assertGreater(out["positiveCandidateClaimsExcludingCurrent"], 0)


class WorkflowBoundaryTests(unittest.TestCase):
    def test_authorization_review_is_zero_runtime_opened_pr_only(self):
        text = AUTH_WORKFLOW.read_text()
        self.assertIn("pull_request:", text)
        self.assertIn("types: [opened]", text)
        self.assertIn("experiments/aerosol-family-challenge-v2/authorization.json", text)
        self.assertNotIn("workflow_dispatch:", text)
        self.assertNotIn("repository_dispatch:", text)
        self.assertNotIn("schedule:", text)
        self.assertNotIn("mamba-org/setup-micromamba", text)
        self.assertNotIn("command -v uvspec", text)
        self.assertNotIn("--allow-execution", text)
        self.assertIn("--audit-mode authorization-recheck", text)
        self.assertIn("AUTHORIZATION_REVIEW_PASS_ZERO_RUNTIME", (CANDIDATE / "authorization_guard.py").read_text())

    def test_execution_is_push_only_and_solver_is_below_preflight(self):
        text = EXEC_WORKFLOW.read_text()
        self.assertIn('"dispatch/aerosol-family-challenge-v2-ordinal-*"', text)
        self.assertNotIn("workflow_dispatch:", text)
        self.assertNotIn("repository_dispatch:", text)
        self.assertNotIn("schedule:", text)
        preflight = text.split("\n  cases-dep2:\n", 1)[0]
        self.assertNotIn("setup-micromamba", preflight)
        self.assertNotIn("command -v uvspec", preflight)
        self.assertNotIn("--allow-execution", preflight)
        self.assertIn("EXACT_ONE_USE_AEROSOL_FAMILY_V2_DISPATCH_AUTHORIZED", preflight)
        self.assertIn("_AEROSOL_FAMILY_V2_DISPATCH_CONSUMED", preflight)
        self.assertLess(preflight.index("Persist pre-solver guard evidence"), preflight.index("Consume dispatch identity exactly once"))

    def test_four_shards_preserve_global_maximum_parallelism_eight(self):
        text = EXEC_WORKFLOW.read_text()
        for dep in (2, 4, 6, 8):
            self.assertIn(f"cases-dep{dep}:", text)
            self.assertIn(f"matrix: ${{{{ fromJSON(needs.preflight.outputs.matrix{dep}) }}}}", text)
        self.assertEqual(text.count("max-parallel: 2"), 4)
        self.assertIn("expected exactly 576 current-run case artifacts", text)

    def test_analysis_wrapper_is_frozen_binding_aware_and_cross_solar_spotlight_is_tag_based(self):
        text = (CANDIDATE / "aggregate_results.py").read_text()
        self.assertIn('"analysisContractRawSha256"', text)
        self.assertIn('"analysisImplementationRawSha256"', text)
        self.assertIn('"derivedChannelsRawSha256"', text)
        self.assertIn('"geometryTag": "cross-solar"', text)
        self.assertNotIn('"geometryId": "g04"', text)
        self.assertIn("NUMERICALLY_UNRESOLVED_NO_EPSILON", text)
        self.assertIn("inferentialPValueOrConfidenceIntervalPermitted", text)


if __name__ == "__main__":
    unittest.main()
