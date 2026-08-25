from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "review/asiv-matched-stellar-transport-v1"
RECOVERY = STAGE / "recovery-v2"
PARSER_PATH = RECOVERY / "micromamba_list_parser_v2.py"
BUILDER_PATH = RECOVERY / "authorization_builder_recovery_v2.py"
CONTRACT_PATH = RECOVERY / "RECOVERY_CONTROL_CONTRACT.review.json"
EVIDENCE_PATH = RECOVERY / "RUN_32848973816_PRE_SOLVER_FAILURE.review.json"
AUTH_CANDIDATE = RECOVERY / "authorization-review-workflow-v2.yml.review"
SCIENCE_CANDIDATE = RECOVERY / "science-workflow-v2.yml.review"
AUTHORIZATION_PATH = STAGE / "authorization-recovery-v2.json"
ACTIVE_AUTH = ROOT / ".github/workflows/asiv-matched-stellar-authorization-review-recovery-v2.yml"
ACTIVE_SCIENCE = ROOT / ".github/workflows/asiv-matched-stellar-science-recovery-v2.yml"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AsivMatchedStellarRecoveryV2Tests(unittest.TestCase):
    def test_parser_accepts_bare_and_enveloped_package_arrays(self):
        p = load(PARSER_PATH, "recovery_parser")
        record = {"name": "rubin-libradtran", "version": "2.0.6", "build_string": "py312pl5321he9373c2_1"}
        for payload in (
            [record, {"name": "python", "version": "3.12.4", "build": "x"}],
            {"packages": [record]},
            {"result": {"packages": [record]}},
        ):
            got = p.extract_unique_package_record(payload, "rubin-libradtran")
            self.assertEqual(got, record)
            self.assertEqual(p.exact_package_spec(got), "rubin-libradtran=2.0.6=py312pl5321he9373c2_1")

    def test_parser_fails_closed_on_missing_duplicate_or_ambiguous_arrays(self):
        p = load(PARSER_PATH, "recovery_parser_refusals")
        record = {"name": "rubin-libradtran", "version": "2.0.6", "build": "exact"}
        bad = (
            {"packages": [{"name": "python", "version": "3", "build": "x"}]},
            {"packages": [record, copy.deepcopy(record)]},
            {"left": [record], "right": [copy.deepcopy(record)]},
        )
        for payload in bad:
            with self.assertRaises(p.MicromambaListParserRefusal):
                p.extract_unique_package_record(payload, "rubin-libradtran")

    def test_frozen_prior_failure_evidence_is_strictly_pre_solver(self):
        e = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(e["status"], "V1_PRE_SOLVER_INFRASTRUCTURE_FAILURE_CONFIRMED")
        self.assertEqual(e["priorRunId"], 32848973816)
        self.assertEqual(e["priorRunAttempt"], 1)
        self.assertEqual(e["failedJobId"], 97805508810)
        self.assertFalse(e["runtimeIdentityVerificationCompleted"])
        self.assertFalse(e["solverStepSucceededOrFailedInAnyShard"])
        self.assertFalse(e["priorSolverExecutionObserved"])
        self.assertEqual(e["priorScientificShardArtifactCount"], 0)
        self.assertEqual(e["priorFinalValidationArtifactCount"], 0)
        self.assertFalse(e["githubRerunPermitted"])
        self.assertEqual(e["permittedCorrectionScope"], "metadata parsing of micromamba list --json only")
        self.assertFalse(e["scientificSourceBytesMayChange"])
        self.assertFalse(e["acceptanceGatesMayChange"])

    def test_recovery_contract_is_non_authorizing_and_science_invariant(self):
        c = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(c["status"], "FROZEN_REVIEW_ONLY_PRESOLVER_RECOVERY_V2_NO_AUTHORIZATION_NO_DISPATCH")
        for key in (
            "scientificExecutionAuthorized", "solverExecutionAuthorized", "authorizationFileCreated",
            "authorizationCommitCreated", "authorizationBranchCreated", "dispatchBranchCreated",
            "workflowActivationAuthorized", "workflowDispatchAuthorized", "resultOpeningAuthorized",
            "productionActivationAuthorized", "pandoraHoldoutAccessAllowed", "starsvisibilityMutationAuthorized",
            "nativeRebuildAuthorized", "retryPermitted", "resumePermitted", "githubRerunPermitted",
        ):
            self.assertFalse(c[key], key)
        inv = c["scientificInvariance"]
        self.assertFalse(inv["scientificSourcesChangedByRecovery"])
        self.assertFalse(inv["caseUniverseChangedByRecovery"])
        self.assertFalse(inv["runtimeIdentityHashesChangedByRecovery"])
        self.assertFalse(inv["photometricAssetsChangedByRecovery"])
        self.assertFalse(inv["acceptanceGatesChangedByRecovery"])
        self.assertEqual(inv["batchManifestCanonicalSha256"], "1756c756e1e865c729a3d93a1084c6081a5eefa6a05f4e874bdaed84e8359663")
        self.assertEqual(inv["totalCaseCount"], 3468)
        self.assertEqual(inv["totalShardCount"], 99)
        self.assertEqual(inv["maxAbsoluteJohnsonVExtinctionErrorMagPerFamily"], 0.025)
        self.assertEqual(inv["rmsJohnsonVExtinctionErrorMagPerFamily"], 0.01)

    def test_builder_pre_activation_template_passes_original_strict_and_batch_gates(self):
        b = load(BUILDER_PATH, "recovery_builder")
        parent = "a" * 40
        self.assertFalse(AUTHORIZATION_PATH.exists())
        auth = b.build_authorization(ROOT, parent, require_active_workflows=False)
        self.assertEqual(auth["status"], "AUTHORIZED_ONE_SHOT_SCIENTIFIC_EXECUTION")
        self.assertEqual(auth["stageId"], "asiv-matched-stellar-transport-v1-execution-authorization")
        self.assertEqual(auth["authorizationBranch"], "authorization/asiv-matched-stellar-transport-recovery-v2")
        self.assertEqual(auth["dispatchBranch"], "dispatch/asiv-matched-stellar-transport-recovery-v2")
        self.assertEqual(auth["executionKey"], "asiv-matched-stellar-transport-recovery-v2-one-shot")
        self.assertEqual(auth["recoveryPriorRunId"], 32848973816)
        self.assertTrue(auth["recoveryPriorRunWasPreSolverFailure"])
        self.assertFalse(auth["retryPermitted"])
        self.assertFalse(auth["resumePermitted"])
        self.assertFalse(auth["githubRerunPermitted"])
        self.assertEqual(auth["caseUniverse"]["validationJohnsonVComparisonsTotal"], 2304)
        self.assertEqual(auth["validationAcceptance"]["maxAbsoluteJohnsonVExtinctionErrorMagPerFamily"], 0.025)
        self.assertEqual(auth["validationAcceptance"]["rmsJohnsonVExtinctionErrorMagPerFamily"], 0.01)
        b.validate_authorization(ROOT, auth, parent, require_active_workflows=False)
        self.assertFalse(AUTHORIZATION_PATH.exists())

    def test_active_recovery_workflow_state_is_atomic_and_exact_if_present(self):
        b = load(BUILDER_PATH, "recovery_builder_activation")
        active_count = int(ACTIVE_AUTH.exists()) + int(ACTIVE_SCIENCE.exists())
        self.assertIn(active_count, (0, 2))
        if active_count == 2:
            observed = b.validate_active_workflows(ROOT)
            self.assertEqual(observed["authorizationReviewWorkflowActiveGitBlobSha1"], "a334c8d4537f4503a502978f106daf83c87a1c9e")
            self.assertEqual(observed["scienceWorkflowActiveGitBlobSha1"], "91fc9bc11102cc30db9c3ed46a2ee9290747c986")

    def test_recovery_workflow_is_new_one_shot_and_rechecks_v1_before_solver(self):
        text = SCIENCE_CANDIDATE.read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", text)
        self.assertIn('test "$GITHUB_RUN_ATTEMPT" = 1', text)
        self.assertIn("dispatch/asiv-matched-stellar-transport-recovery-v2", text)
        self.assertIn("authorization/asiv-matched-stellar-transport-recovery-v2", text)
        self.assertIn("32848973816", text)
        self.assertIn("V1_PRE_SOLVER_INFRASTRUCTURE_FAILURE_CONFIRMED", text)
        self.assertIn("priorScientificShardArtifactCount", text)
        self.assertIn("micromamba_list_parser_v2.py", text)
        self.assertIn("extract_unique_package_record", text)
        self.assertIn("execute_shard_strict", text)
        self.assertIn("allow_execution=True", text)
        self.assertIn("max-parallel: 8", text)
        self.assertIn("fail-fast: true", text)
        self.assertIn("exactly 99 unique complete recovery shard artifacts required", text)
        self.assertIn("validate_complete_universe", text)
        self.assertNotIn("git push", text)
        self.assertNotIn("repository: search-maker/starsvisibility", text)
        self.assertNotIn("secrets.", text)

    def test_recovery_auth_review_candidate_has_no_execution_surface(self):
        text = AUTH_CANDIDATE.read_text(encoding="utf-8")
        self.assertIn("pull_request:", text)
        self.assertNotIn("workflow_dispatch:", text)
        self.assertIn("authorization-recovery-v2.json", text)
        self.assertIn("draft == true", text)
        self.assertNotIn("uvspec", text)
        self.assertNotIn("micromamba", text)
        self.assertNotIn("allow_execution=True", text)


if __name__ == "__main__":
    unittest.main()
