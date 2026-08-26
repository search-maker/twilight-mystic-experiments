import hashlib
import importlib.machinery
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
V2 = ROOT / "review/asiv-matched-stellar-transport-v2"
EXECUTION = V2 / "validation_execution_v2.py.review"
VALIDATOR = V2 / "validate_fresh_v2.py.review"
CONTROL = V2 / "VALIDATION_EXECUTION_CONTRACT.review.json"
SCIENCE = V2 / "science-workflow-v2.yml.review"
AUTH_REVIEW = V2 / "authorization-review-workflow-v2.yml.review"
BUILDER = V2 / "authorization_builder_v2.py.review"
AUTH_PATH = V2 / "authorization-fresh-validation-v2.json"
ACTIVE_SCIENCE = ROOT / ".github/workflows/asiv-matched-stellar-v2-fresh-validation.yml"
ACTIVE_AUTH = ROOT / ".github/workflows/asiv-matched-stellar-v2-authorization-review.yml"


def load_review(path: Path, name: str):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def git_blob(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


class MatchedStellarV2ValidationExecutionReviewTest(unittest.TestCase):
    def test_exact_validation_only_shard_universe(self):
        m = load_review(EXECUTION, "v2exec_test")
        batch = m.build_validation_shards()
        self.assertEqual(batch["status"], "FROZEN_UNEXECUTED_VALIDATION_ONLY_SHARDS")
        self.assertEqual(batch["caseCount"], 768)
        self.assertEqual(batch["shardCount"], 24)
        self.assertEqual(batch["shardSize"], 32)
        self.assertEqual(batch["trainingCaseCount"], 0)
        self.assertEqual(len(batch["shards"]), 24)
        self.assertTrue(all(row["caseCount"] == 32 for row in batch["shards"]))
        ids = [case["caseId"] for shard in batch["shards"] for case in shard["cases"]]
        self.assertEqual(len(ids), 768)
        self.assertEqual(len(set(ids)), 768)
        self.assertEqual(ids[0], "fresh-v2-0000")
        self.assertEqual(ids[-1], "fresh-v2-0767")
        self.assertTrue(all(case["solverExecutionAuthorized"] is False for shard in batch["shards"] for case in shard["cases"]))

    def test_executor_uses_existing_strict_gate_and_no_self_authorization(self):
        text = EXECUTION.read_text(encoding="utf-8")
        self.assertIn("execution_authorization_gate_review.py", text)
        self.assertIn("gate.validate_strict_authorization(document)", text)
        self.assertIn("gate.execute_one_case_strict(", text)
        self.assertNotIn("execution_transport_review.py", text)
        self.assertIn("allow_execution is not True", text)
        self.assertIn('"trainingExecutionAuthorized": False', text)
        self.assertNotIn("import subprocess", text)
        self.assertNotIn("import requests", text)
        self.assertNotIn("import urllib", text)

    def test_validator_is_complete_set_only_and_reuses_old_training(self):
        text = VALIDATOR.read_text(encoding="utf-8")
        self.assertIn("exactly 24 complete shard roots required", text)
        self.assertIn("set(actual) != set(expected)", text)
        self.assertIn("runtimeLuts", text)
        self.assertIn("EXPECTED_V5_FINAL_ARTIFACT_ID = 9580080568", text)
        self.assertIn("newTrainingSolverSpectrumCount", text)
        self.assertNotIn("import subprocess", text)
        self.assertNotIn("import requests", text)
        self.assertNotIn("import urllib", text)

    def test_execution_contract_binds_exact_review_bytes(self):
        contract = json.loads(CONTROL.read_text(encoding="utf-8"))
        self.assertEqual(contract["status"], "FROZEN_REVIEW_ONLY_NO_AUTHORIZATION_NO_DISPATCH")
        universe = contract["freshValidationUniverse"]
        self.assertTrue(universe["validationOnly"])
        self.assertEqual(universe["validationAtmosphericCaseCount"], 768)
        self.assertEqual(universe["validationShardCount"], 24)
        self.assertEqual(universe["validationCasesPerShard"], 32)
        self.assertEqual(universe["trainingSolverCaseCount"], 0)
        self.assertEqual(universe["reusedTrainingSpectrumCount"], 2700)
        blobs = contract["frozenGitBlobs"]
        self.assertEqual(blobs["methodContractGitBlobSha1"], git_blob(V2 / "METHOD_AND_FRESH_VALIDATION_CONTRACT.review.json"))
        self.assertEqual(blobs["interpolationCandidateGitBlobSha1"], git_blob(V2 / "interpolation_candidate_v2.py.review"))
        self.assertEqual(blobs["validationExecutionGitBlobSha1"], git_blob(EXECUTION))
        self.assertEqual(blobs["freshValidatorGitBlobSha1"], git_blob(VALIDATOR))
        self.assertEqual(blobs["scienceWorkflowCandidateGitBlobSha1"], git_blob(SCIENCE))
        self.assertEqual(blobs["authorizationReviewWorkflowCandidateGitBlobSha1"], git_blob(AUTH_REVIEW))
        self.assertEqual(blobs["v1StrictAuthorizationGateGitBlobSha1"], "9bbe4f8fe64f7f32dd3e3e69469a15b30f658dde")

    def test_gates_and_old_training_source_are_immutable(self):
        contract = json.loads(CONTROL.read_text(encoding="utf-8"))
        self.assertEqual(contract["gates"]["perFamilyMaxAbsDeltaAvMag"], 0.025)
        self.assertEqual(contract["gates"]["perFamilyRmsDeltaAvMag"], 0.010)
        self.assertTrue(contract["gates"]["everyFamilyMustPassSeparately"])
        self.assertFalse(contract["gates"]["postResultThresholdRelaxationAuthorized"])
        self.assertFalse(contract["gates"]["postResultMethodChangeAuthorized"])
        source = contract["trainingSource"]
        self.assertEqual(source["sourceRunId"], 32889328517)
        self.assertEqual(source["artifactId"], 9580080568)
        self.assertEqual(source["artifactDigest"], "sha256:bccc9f58a649202c395842df298ace1c4f609badc0d0530e40ba10d8ddc5300f")
        self.assertEqual(source["allowedField"], "runtimeLuts")
        self.assertFalse(source["openedV1ValidationCasesReusableAsFreshHoldout"])

    def test_science_candidate_is_24_shard_validation_only_one_shot(self):
        text = SCIENCE.read_text(encoding="utf-8")
        self.assertIn("test \"$GITHUB_RUN_ATTEMPT\" = 1", text)
        self.assertIn("test \"$GITHUB_RUN_NUMBER\" = 1", text)
        self.assertIn("dispatch/asiv-matched-stellar-transport-v2-fresh-validation", text)
        self.assertIn("batch['shardCount']!=24", text)
        self.assertIn("batch['caseCount']!=768", text)
        self.assertIn("batch['trainingCaseCount']!=0", text)
        self.assertIn("uvspec),'-h'", text)
        self.assertIn("9580080568", text)
        self.assertIn("asiv-matched-stellar-final-validation-recovery-v5", text)
        self.assertIn("execute_validation_shard(", text)
        self.assertIn("Validate exact fresh 768-case universe", text)
        self.assertIn("newTrainingSolverSpectrumCount", text)
        self.assertNotIn("execute_shard_strict(", text)
        self.assertNotIn("training-000", text)
        self.assertNotIn("continue-on-error", text)

    def test_authorization_review_candidate_is_no_solver_and_exact_one_file(self):
        text = AUTH_REVIEW.read_text(encoding="utf-8")
        self.assertIn("authorization-fresh-validation-v2.json", text)
        self.assertIn('test "${#CHANGED[@]}" = 1', text)
        self.assertIn('test "$PR_DRAFT" = true', text)
        self.assertIn("m.validate_v2_authorization(auth)", text)
        self.assertIn("9580080568", text)
        self.assertIn("V2_AUTHORIZATION_REVIEW_PASS_NO_DISPATCH", text)
        self.assertIn("solverExecutionPerformed':False", text)
        self.assertNotIn("execute_validation_shard(", text)
        self.assertNotIn("uvspec", text.lower())

    def test_builder_has_no_write_network_solver_or_dispatch_surface(self):
        text = BUILDER.read_text(encoding="utf-8")
        self.assertIn("build_authorization", text)
        self.assertIn("gate.current_authorization_binding()", text)
        self.assertIn("execution.validate_v2_authorization(document)", text)
        self.assertNotIn("import requests", text)
        self.assertNotIn("import urllib", text)
        self.assertNotIn("subprocess.run", text)
        self.assertNotIn("Popen(", text)
        self.assertNotIn("execute_validation_shard(", text)
        self.assertNotIn("workflow_dispatch", text)

    def test_freeze_stage_has_no_active_workflow_or_authorization(self):
        self.assertFalse(ACTIVE_SCIENCE.exists())
        self.assertFalse(ACTIVE_AUTH.exists())
        self.assertFalse(AUTH_PATH.exists())


if __name__ == "__main__":
    unittest.main()
