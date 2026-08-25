import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "review/asiv-matched-stellar-transport-v1/recovery-v5"
AUTH_CANDIDATE = BASE / "authorization-review-workflow-v5.yml.review"
SCIENCE_CANDIDATE = BASE / "science-workflow-v5.yml.review"
AUTH_ACTIVE = ROOT / ".github/workflows/asiv-matched-stellar-authorization-review-recovery-v5.yml"
SCIENCE_ACTIVE = ROOT / ".github/workflows/asiv-matched-stellar-science-recovery-v5.yml"
CONTRACT = BASE / "WORKFLOW_ACTIVATION_CONTRACT.review.json"

AUTH_BLOB = "1a9a5258f9980467ff1f5504a79ec9d5f78495b9"
SCIENCE_BLOB = "d6cced250cc3fdbdb914f3c643e419c6b931c8c6"
CONTRACT_BLOB = "068629daa71068d7a3cf1028cd23b089cf0cdcd6"
FROZEN_HELP_SHA = "868aea5af762d968f6f62c4e1472916d25232ed9cab5be112d753b0823d20548"


def blob(path: Path) -> str:
    return subprocess.check_output(["git", "hash-object", str(path)], text=True).strip()


class RecoveryV5WorkflowActivationTests(unittest.TestCase):
    def test_active_workflows_are_exact_candidate_git_blobs(self):
        self.assertEqual(blob(AUTH_CANDIDATE), AUTH_BLOB)
        self.assertEqual(blob(AUTH_ACTIVE), AUTH_BLOB)
        self.assertEqual(AUTH_ACTIVE.read_bytes(), AUTH_CANDIDATE.read_bytes())
        self.assertEqual(blob(SCIENCE_CANDIDATE), SCIENCE_BLOB)
        self.assertEqual(blob(SCIENCE_ACTIVE), SCIENCE_BLOB)
        self.assertEqual(SCIENCE_ACTIVE.read_bytes(), SCIENCE_CANDIDATE.read_bytes())
        self.assertEqual(blob(CONTRACT), CONTRACT_BLOB)

    def test_science_trigger_and_one_shot_identity_are_frozen(self):
        text = SCIENCE_ACTIVE.read_text(encoding="utf-8")
        self.assertIn("on:\n  workflow_dispatch:\n", text)
        self.assertNotIn("\n  push:", text)
        self.assertNotIn("\n  schedule:", text)
        self.assertIn('test "$GITHUB_RUN_NUMBER" = 1', text)
        self.assertIn('test "$GITHUB_RUN_ATTEMPT" = 1', text)
        self.assertIn('test "$GITHUB_REF_NAME" = dispatch/asiv-matched-stellar-transport-recovery-v5', text)
        self.assertIn("subprocess.run([str(uvspec),'-h'],capture_output=True,check=True)", text)
        self.assertNotIn("subprocess.run([str(uvspec),'--help']", text)
        self.assertIn(FROZEN_HELP_SHA, text)
        self.assertIn("max-parallel: 8", text)
        self.assertIn("scientificCaseCount']=3468", text)
        self.assertIn("recoveryVersion']=5", text)
        self.assertNotIn("rerun-failed-jobs", text)

    def test_authorization_review_trigger_is_narrow_and_non_scientific(self):
        text = AUTH_ACTIVE.read_text(encoding="utf-8")
        self.assertIn("on:\n  pull_request:\n", text)
        self.assertIn("authorization-recovery-v5.json", text)
        self.assertNotIn("workflow_dispatch:", text)
        self.assertNotIn("execute_shard_strict", text)
        self.assertIn("gate.validate_strict_authorization(auth)", text)
        self.assertIn("batch.validate_batch_authorization(auth)", text)

    def test_activation_contract_grants_no_execution_authority(self):
        row = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(row["recoveryVersion"], 5)
        self.assertEqual(row["freezeMergeMainSha"], "6d9d07b13f5c9eb9145c2ac8be8271ac87918d91")
        self.assertEqual(row["authorizationReview"]["expectedGitBlobSha1"], AUTH_BLOB)
        self.assertEqual(row["science"]["expectedGitBlobSha1"], SCIENCE_BLOB)
        self.assertEqual(row["runtimeHelpCorrection"]["invocation"], "uvspec -h")
        self.assertEqual(row["runtimeHelpCorrection"]["frozenHelpSha256"], FROZEN_HELP_SHA)
        self.assertFalse(row["runtimeHelpCorrection"]["expectedHashChanged"])
        self.assertEqual(row["scienceCardinality"]["totalShardCount"], 99)
        self.assertEqual(row["scienceCardinality"]["totalCaseCount"], 3468)
        self.assertEqual(row["scienceCardinality"]["validationJohnsonVComparisonsTotal"], 2304)
        self.assertEqual(row["acceptanceGates"]["perFamilyMaxAbsDeltaAvMag"], 0.025)
        self.assertEqual(row["acceptanceGates"]["perFamilyRmsDeltaAvMag"], 0.01)
        for key in (
            "authorizationFileCreated",
            "authorizationBranchCreated",
            "dispatchBranchCreated",
            "scientificExecutionAuthorizedByActivation",
            "solverExecutionPerformedByActivation",
            "githubRerunPermitted",
            "solverRetryPermitted",
            "solverResumePermitted",
            "nativeRebuildAuthorized",
            "pandoraHoldoutAccessAllowed",
            "starsvisibilityMutationAuthorized",
            "productionAuthorized",
        ):
            self.assertFalse(row[key], key)


if __name__ == "__main__":
    unittest.main()
