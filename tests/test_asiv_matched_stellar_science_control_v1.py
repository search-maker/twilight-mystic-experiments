from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "review/asiv-matched-stellar-transport-v1"
CONTROL = STAGE / "science-control"
BUILDER_PATH = CONTROL / "authorization_builder_review.py"
CONTRACT_PATH = CONTROL / "SCIENCE_CONTROL_CONTRACT.review.json"
AUTH_REVIEW_CANDIDATE = CONTROL / "authorization-review-workflow.yml.review"
SCIENCE_CANDIDATE = CONTROL / "science-workflow.yml.review"
AUTHORIZATION_PATH = STAGE / "authorization.json"
ACTIVE_AUTH_REVIEW = ROOT / ".github/workflows/asiv-matched-stellar-authorization-review-v1.yml"
ACTIVE_SCIENCE = ROOT / ".github/workflows/asiv-matched-stellar-science-v1.yml"


def load_builder():
    spec = importlib.util.spec_from_file_location("matched_stellar_science_control_builder", BUILDER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AsivMatchedStellarScienceControlV1Tests(unittest.TestCase):
    def test_control_contract_is_non_authorizing_and_binds_exact_review_bytes(self):
        mod = load_builder()
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(contract["status"], "FROZEN_REVIEW_ONLY_SCIENCE_CONTROL_NO_AUTHORIZATION_NO_DISPATCH")
        for key in (
            "scientificExecutionAuthorized", "solverExecutionAuthorized", "authorizationFileCreated",
            "authorizationCommitCreated", "authorizationBranchCreated", "dispatchBranchCreated",
            "workflowActivationAuthorized", "workflowDispatchAuthorized", "resultOpeningAuthorized",
            "productionActivationAuthorized", "pandoraHoldoutAccessAllowed", "starsvisibilityMutationAuthorized",
            "nativeRebuildAuthorized", "retryPermitted", "resumePermitted", "githubRerunPermitted",
        ):
            self.assertFalse(contract[key], key)
        bindings = contract["sourceBindings"]
        self.assertEqual(bindings["authorizationBuilderGitBlobSha1"], mod.git_blob_sha1(BUILDER_PATH))
        self.assertEqual(bindings["authorizationReviewWorkflowCandidateGitBlobSha1"], mod.git_blob_sha1(AUTH_REVIEW_CANDIDATE))
        self.assertEqual(bindings["scienceWorkflowCandidateGitBlobSha1"], mod.git_blob_sha1(SCIENCE_CANDIDATE))
        self.assertEqual(bindings["batchOrchestrationGitBlobSha1"], "d1c4f156967e592ee41f4c1a829e7d551a4f7ea7")
        self.assertEqual(bindings["batchOrchestrationContractGitBlobSha1"], "7214a7e6ff969242cab20d9019ccc522ab96ddde")
        auth_control = contract["authorizationControl"]
        self.assertTrue(auth_control["activeAuthorizationReviewWorkflowMustExistBeforeAuthorization"])
        self.assertTrue(auth_control["activeScienceWorkflowMustExistBeforeAuthorization"])
        self.assertTrue(auth_control["activeAuthorizationReviewWorkflowMustBeGitBlobIdenticalToCandidate"])
        self.assertTrue(auth_control["activeScienceWorkflowMustBeGitBlobIdenticalToCandidate"])

    def test_no_authorization_or_active_science_workflow_exists_in_review_package(self):
        self.assertFalse(AUTHORIZATION_PATH.exists())
        self.assertFalse(ACTIVE_AUTH_REVIEW.exists())
        self.assertFalse(ACTIVE_SCIENCE.exists())
        self.assertTrue(AUTH_REVIEW_CANDIDATE.is_file())
        self.assertTrue(SCIENCE_CANDIDATE.is_file())
        self.assertFalse(str(AUTH_REVIEW_CANDIDATE.relative_to(ROOT)).startswith(".github/workflows/"))
        self.assertFalse(str(SCIENCE_CANDIDATE.relative_to(ROOT)).startswith(".github/workflows/"))

    def test_real_authorization_default_refuses_before_workflow_activation(self):
        mod = load_builder()
        parent = "d" * 40
        with self.assertRaises(mod.AuthorizationBuilderRefusal) as ctx:
            mod.build_authorization(ROOT, parent)
        self.assertIn("active authorization-review workflow is absent", str(ctx.exception))

    def test_builder_constructs_and_validates_only_an_in_memory_pre_activation_template(self):
        mod = load_builder()
        parent = "a" * 40
        self.assertFalse(AUTHORIZATION_PATH.exists())
        auth = mod.build_authorization(ROOT, parent, require_active_workflows=False)
        self.assertFalse(AUTHORIZATION_PATH.exists())
        self.assertEqual(auth["status"], "AUTHORIZED_ONE_SHOT_SCIENTIFIC_EXECUTION")
        self.assertTrue(auth["scientificExecutionAuthorized"])
        self.assertTrue(auth["solverExecutionAuthorized"])
        self.assertTrue(auth["batchExecutionAuthorized"])
        self.assertFalse(auth["dispatchAuthorized"])
        self.assertFalse(auth["automaticDispatch"])
        self.assertFalse(auth["consumed"])
        self.assertEqual(auth["exactAuthorizationParentCommit"], parent)
        self.assertEqual(auth["authorizationBranch"], "authorization/asiv-matched-stellar-transport-v1")
        self.assertEqual(auth["dispatchBranch"], "dispatch/asiv-matched-stellar-transport-v1")
        self.assertEqual(auth["workflowRunAttemptRequired"], 1)
        self.assertEqual(auth["controlBindings"]["authorizationReviewWorkflowActiveGitBlobSha1Expected"], "6ed68a90f2614dd762b5484e740a146e2cb636cc")
        self.assertEqual(auth["controlBindings"]["scienceWorkflowActiveGitBlobSha1Expected"], "d59151ae4746db7deed7f20656c0574f5c46b883")
        mod.validate_authorization(ROOT, auth, parent, require_active_workflows=False)

    def test_control_binding_drift_is_refused(self):
        mod = load_builder()
        parent = "b" * 40
        auth = mod.build_authorization(ROOT, parent, require_active_workflows=False)
        drifted = copy.deepcopy(auth)
        drifted["controlBindings"]["scienceWorkflowCandidateGitBlobSha1"] = "0" * 40
        with self.assertRaises(mod.AuthorizationBuilderRefusal):
            mod.validate_authorization(ROOT, drifted, parent, require_active_workflows=False)

    def test_batch_binding_drift_is_refused_through_control_builder(self):
        mod = load_builder()
        parent = "c" * 40
        auth = mod.build_authorization(ROOT, parent, require_active_workflows=False)
        drifted = copy.deepcopy(auth)
        drifted["batchBindings"]["batchManifestCanonicalSha256"] = "0" * 64
        with self.assertRaises(Exception):
            mod.validate_authorization(ROOT, drifted, parent, require_active_workflows=False)

    def test_authorization_review_candidate_is_review_only(self):
        text = AUTH_REVIEW_CANDIDATE.read_text(encoding="utf-8")
        self.assertIn("pull_request:", text)
        self.assertNotIn("workflow_dispatch:", text)
        self.assertIn("authorization.json", text)
        self.assertIn("draft == true", text)
        self.assertIn("GITHUB_RUN_ATTEMPT", text)
        self.assertIn("AUTHORIZATION_REVIEW_PASS_NO_DISPATCH", text)
        self.assertNotIn("uvspec", text)
        self.assertNotIn("micromamba", text)
        self.assertNotIn("git push", text)
        self.assertNotIn("allow_execution=True", text)

    def test_science_candidate_has_exact_one_shot_complete_batch_gates(self):
        text = SCIENCE_CANDIDATE.read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", text)
        self.assertNotIn("pull_request:", text)
        self.assertIn("test \"$GITHUB_RUN_ATTEMPT\" = 1", text)
        self.assertIn("dispatch/asiv-matched-stellar-transport-v1", text)
        self.assertIn("authorization/asiv-matched-stellar-transport-v1", text)
        self.assertIn("authorization PR must remain Draft/open/unmerged", text)
        self.assertIn("one-shot science history violated", text)
        self.assertIn("max-parallel: 8", text)
        self.assertIn("fail-fast: true", text)
        self.assertIn("execute_shard_strict", text)
        self.assertIn("allow_execution=True", text)
        self.assertIn("exactly 99 unique complete shard artifacts required", text)
        self.assertIn("validate_complete_universe", text)
        self.assertIn("743391266", text)
        self.assertIn("11daa1f1f4be0fd4ddf7e881ec2005498049674a1540d37b4b1e8f5e16052c7e", text)
        self.assertNotIn("git push", text)
        self.assertNotIn("repository: search-maker/starsvisibility", text)
        self.assertNotIn("secrets.", text)

    def test_activation_is_explicitly_separate_and_still_non_authorizing(self):
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        activation = contract["activationRequirements"]
        self.assertTrue(activation["activationMustBeSeparateReviewAfterThisContractIsMerged"])
        self.assertTrue(activation["activationMustCopyCandidateBytesExactlyToFutureActivePaths"])
        self.assertTrue(activation["activationMustProveGitBlobIdentityOfCopiedWorkflowContents"])
        self.assertTrue(activation["activationMustNotCreateAuthorizationJson"])
        self.assertTrue(activation["activationMustNotCreateAuthorizationOrDispatchBranches"])
        self.assertTrue(activation["activationMustNotDispatchScience"])
        self.assertTrue(activation["authorizationBuilderDefaultMustRefuseBeforeExactActiveWorkflowsExist"])
        self.assertTrue(activation["authorizationMayBeCreatedOnlyAfterActivationReviewIsGreenAndMerged"])


if __name__ == "__main__":
    unittest.main()
