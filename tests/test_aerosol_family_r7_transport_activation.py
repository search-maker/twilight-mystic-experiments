from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "experiments/aerosol-family-challenge-v2-r7"
CANDIDATE = BASE / "execution-candidate"
AUTH_WORKFLOW = ROOT / ".github/workflows/aerosol-family-v2-r7-authorization-review.yml"
EXEC_WORKFLOW = ROOT / ".github/workflows/aerosol-family-v2-r7-execution.yml"


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
        self.assertIn("experiments/aerosol-family-challenge-v2-r7/authorization.json", text)
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
        self.assertIn('"dispatch/aerosol-family-challenge-v2-r7-ordinal-*"', text)
        self.assertNotIn("workflow_dispatch:", text)
        self.assertNotIn("repository_dispatch:", text)
        self.assertNotIn("schedule:", text)
        preflight = text.split("\n  cases-dep2:\n", 1)[0]
        self.assertNotIn("setup-micromamba", preflight)
        self.assertNotIn("command -v uvspec", preflight)
        self.assertNotIn("--allow-execution", preflight)
        self.assertIn("EXACT_ONE_USE_AEROSOL_FAMILY_V2_R7_DISPATCH_AUTHORIZED", preflight)
        self.assertIn("_AEROSOL_FAMILY_V2_R7_DISPATCH_CONSUMED", preflight)
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

import json

class R7TransportIdentityOnlyEquivalence(unittest.TestCase):
    def test_r7_transport_is_mechanical_identity_path_adaptation_of_r6(self):
        root = Path(__file__).resolve().parents[1]
        r6 = root / 'experiments' / 'aerosol-family-challenge-v2' / 'execution-candidate'
        r7 = root / 'experiments' / 'aerosol-family-challenge-v2-r7' / 'execution-candidate'
        names = [
            'README.md', 'authorization-review-workflow.yml.template', 'authorization.template.json',
            'authorization_guard.py', 'dispatch_guard.py', 'executor.py', 'freshness.py', 'guard.py',
            'transport-contract.v3.json', 'workflow.yml.template', 'aggregate_results.py', 'authorization_surface.py',
        ]
        def normalize(text: str, name: str) -> str:
            proof='__AFC2_R6_PROOF_ARTIFACT__'
            text=text.replace('aerosol-family-v2-r7-freeze-proof',proof)
            text=text.replace('aerosol-family-challenge-v2-r7','aerosol-family-challenge-v2')
            text=text.replace('aerosol-family-v2-r7','aerosol-family-v2')
            text=text.replace(proof,'aerosol-family-v2-r6-freeze-proof')
            text=text.replace('AEROSOL_FAMILY_V2_R7','AEROSOL_FAMILY_V2')
            text=text.replace('candidate-seed-ledger.v2.json','candidate-seed-ledger.v1.json')
            text=text.replace('R7_REVIEW_ONLY_TRANSPORT_CANDIDATE_NOT_AUTHORIZED','R6_REVIEW_ONLY_TRANSPORT_CANDIDATE_NOT_AUTHORIZED')
            text=text.replace('Aerosol-family v2 R7 authorization review','Aerosol-family v2 authorization review')
            text=text.replace('Aerosol-family v2 R7 scientific execution','Aerosol-family v2 scientific execution')
            text=text.replace('Aerosol-family v2 R7 status/aerosol-family-v2-r7-review-freeze-diagnostic-1','Aerosol-family v2 status/aerosol-family-v2-r7-review-freeze-diagnostic-1')
            if name == 'authorization_surface.py':
                text=text.replace(
                    'AUTHORIZATION_REVIEW_WORKFLOW = ".github/workflows/aerosol-family-v2-authorization-review.yml"\n',
                    '',
                )
                start=text.index('\ndef _failed_authorization_ref_reusable(')
                end=text.index('\ndef build_surface(', start)
                text=text[:start] + text[end:]
                text=text.replace(
                    '"authorizationBranchReusableAfterFailedReview": _failed_authorization_ref_reusable(\n'
                    '            auth_branch, auth_head, pulls, runs\n'
                    '        ),',
                    '"authorizationBranchReusableAfterFailedReview": False,',
                )
            if name == 'README.md':
                text=text.replace('R7','R6')
            return text
        for name in names:
            self.assertEqual((r6/name).read_text(), normalize((r7/name).read_text(),name), name)

    def test_r7_transport_keeps_science_and_holdout_boundaries_closed(self):
        root = Path(__file__).resolve().parents[1]
        contract=json.loads((root/'experiments/aerosol-family-challenge-v2-r7/execution-candidate/transport-contract.v3.json').read_text())
        self.assertEqual(contract['stageId'],'aerosol-family-challenge-v2-r7-execution-transport')
        self.assertEqual(contract['status'],'R7_REVIEW_ONLY_TRANSPORT_CANDIDATE_NOT_AUTHORIZED')
        self.assertEqual(contract['caseUniverse']['caseCount'],576)
        self.assertEqual(contract['caseUniverse']['comparisonGroupCount'],72)
        self.assertEqual(contract['caseUniverse']['configuredPhotonHistories'],11520000000)
        self.assertFalse(contract['scientificExecutionAuthorized'])
        self.assertFalse(contract['solverExecutionAuthorized'])
        self.assertFalse(contract['githubRerunAllowed'])
        self.assertFalse(contract['retryAllowed'])
        self.assertFalse(contract['resumeAllowed'])
        self.assertFalse(contract['authorizationBoundary']['protectedHoldoutOpeningAuthorized'])
        self.assertEqual(contract['reviewSeedProofLifecycle']['proofBundleArtifactName'],'aerosol-family-v2-r7-freeze-proof')
