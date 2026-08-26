import hashlib
import importlib.machinery
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
V2 = ROOT / "review/asiv-matched-stellar-transport-v2"
ACTIVE_SCIENCE = ROOT / ".github/workflows/asiv-matched-stellar-v2-fresh-validation.yml"
ACTIVE_AUTH = ROOT / ".github/workflows/asiv-matched-stellar-v2-authorization-review.yml"
SCIENCE_CANDIDATE = V2 / "science-workflow-v2.yml.review"
AUTH_CANDIDATE = V2 / "authorization-review-workflow-v2.yml.review"
ACTIVATION = V2 / "WORKFLOW_ACTIVATION_CONTRACT.review.json"
AUTH_PATH = V2 / "authorization-fresh-validation-v2.json"
BUILDER = V2 / "authorization_builder_v2.py.review"


def git_blob(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def load_review(path: Path, name: str):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class MatchedStellarV2WorkflowActivationTest(unittest.TestCase):
    def test_active_workflows_are_exact_candidate_git_blobs(self):
        self.assertTrue(ACTIVE_SCIENCE.is_file())
        self.assertTrue(ACTIVE_AUTH.is_file())
        self.assertEqual(git_blob(ACTIVE_SCIENCE), git_blob(SCIENCE_CANDIDATE))
        self.assertEqual(git_blob(ACTIVE_AUTH), git_blob(AUTH_CANDIDATE))
        self.assertEqual(git_blob(ACTIVE_SCIENCE), "d65d51168b3a8f7d93388e79ab4382194a83b074")
        self.assertEqual(git_blob(ACTIVE_AUTH), "dd9fcfac50eddd17d82d26095605ed872984817c")

    def test_activation_contract_matches_active_paths(self):
        contract = json.loads(ACTIVATION.read_text(encoding="utf-8"))
        self.assertEqual(contract["status"], "ACTIVATION_REVIEW_ONLY_NO_AUTHORIZATION_NO_DISPATCH")
        rows = contract["activeWorkflows"]
        self.assertEqual(rows[str(ACTIVE_SCIENCE.relative_to(ROOT))]["candidateGitBlobSha1"], git_blob(ACTIVE_SCIENCE))
        self.assertEqual(rows[str(ACTIVE_AUTH.relative_to(ROOT))]["candidateGitBlobSha1"], git_blob(ACTIVE_AUTH))
        boundary = contract["scienceBoundary"]
        self.assertEqual(boundary["freshValidationCaseCount"], 768)
        self.assertEqual(boundary["freshValidationShardCount"], 24)
        self.assertEqual(boundary["reusedTrainingSpectrumCount"], 2700)
        self.assertEqual(boundary["newTrainingSolverSpectrumCount"], 0)
        self.assertEqual(boundary["perFamilyMaxAbsDeltaAvMagGate"], 0.025)
        self.assertEqual(boundary["perFamilyRmsDeltaAvMagGate"], 0.010)

    def test_activation_creates_no_authorization(self):
        self.assertFalse(AUTH_PATH.exists())
        contract = json.loads(ACTIVATION.read_text(encoding="utf-8"))
        for value in contract["activationDoesNotCreate"].values():
            self.assertTrue(value)

    def test_active_science_is_one_shot_validation_only(self):
        text = ACTIVE_SCIENCE.read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch", text)
        self.assertIn('test "$GITHUB_RUN_ATTEMPT" = 1', text)
        self.assertIn('test "$GITHUB_RUN_NUMBER" = 1', text)
        self.assertIn("dispatch/asiv-matched-stellar-transport-v2-fresh-validation", text)
        self.assertIn("batch['shardCount']!=24", text)
        self.assertIn("batch['caseCount']!=768", text)
        self.assertIn("batch['trainingCaseCount']!=0", text)
        self.assertIn("newTrainingSolverSpectrumCount", text)
        self.assertIn("9580080568", text)
        self.assertNotIn("training-000", text)

    def test_active_authorization_review_has_no_solver_execution(self):
        text = ACTIVE_AUTH.read_text(encoding="utf-8")
        self.assertIn("V2_AUTHORIZATION_REVIEW_PASS_NO_DISPATCH", text)
        self.assertIn("authorization-fresh-validation-v2.json", text)
        self.assertIn("m.validate_v2_authorization(auth)", text)
        self.assertNotIn("execute_validation_shard(", text)
        self.assertNotIn("workflow_dispatch", text)

    def test_builder_now_derives_a_strict_compatible_v2_document_without_writes(self):
        builder = load_review(BUILDER, "v2_builder_activation_test")
        document = builder.build_authorization(exact_parent_commit="0" * 40)
        self.assertEqual(document["stageId"], "asiv-matched-stellar-transport-v1-execution-authorization")
        self.assertEqual(document["controlStageId"], "asiv-matched-stellar-transport-v2-fresh-validation-authorization")
        self.assertTrue(document["scientificExecutionAuthorized"])
        self.assertTrue(document["solverExecutionAuthorized"])
        self.assertTrue(document["validationOnlyExecutionAuthorized"])
        self.assertFalse(document["trainingExecutionAuthorized"])
        self.assertEqual(document["validationCaseCount"], 768)
        self.assertEqual(document["validationShardCount"], 24)
        self.assertEqual(document["reusedTraining"]["spectrumCount"], 2700)
        self.assertEqual(document["reusedTraining"]["newTrainingSolverSpectrumCount"], 0)
        self.assertEqual(document["freshValidationGates"]["perFamilyMaxAbsDeltaAvMag"], 0.025)
        self.assertEqual(document["freshValidationGates"]["perFamilyRmsDeltaAvMag"], 0.010)
        self.assertEqual(document["v2ControlBindings"]["scienceWorkflowActiveGitBlobSha1"], git_blob(ACTIVE_SCIENCE))
        self.assertEqual(document["v2ControlBindings"]["authorizationReviewWorkflowActiveGitBlobSha1"], git_blob(ACTIVE_AUTH))
        self.assertFalse(document["dispatchAuthorized"])
        self.assertFalse(document["automaticDispatch"])
        self.assertFalse(document["pandoraHoldoutAccessAllowed"])
        self.assertFalse(document["starsvisibilityMutationAuthorized"])
        self.assertFalse(document["productionActivationAuthorized"])


if __name__ == "__main__":
    unittest.main()
