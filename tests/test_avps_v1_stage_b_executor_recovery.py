from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECOVERY = ROOT / "review/avps-v1-ordinal40-stage-b-executor-recovery-v1/recovery_executor.py"
CONTRACT = ROOT / "review/avps-v1-ordinal40-stage-b-executor-recovery-v1/RECOVERY_CONTRACT.review.json"

spec = importlib.util.spec_from_file_location("avps_executor_recovery_tested", RECOVERY)
if spec is None or spec.loader is None:
    raise RuntimeError("cannot import recovery executor")
recovery = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = recovery
spec.loader.exec_module(recovery)


class AvpsStageBExecutorRecovery(unittest.TestCase):
    def setUp(self):
        self.contract = json.loads(CONTRACT.read_text())

    def test_contract_is_review_only_and_science_is_frozen(self):
        c = self.contract
        self.assertEqual(c["status"], "REVIEW_ONLY_TRANSPORT_RECOVERY_NOT_AUTHORIZED")
        self.assertEqual(c["baseMainSha"], "99ade7798627e67921139697ba1a004fa8a304bb")
        self.assertEqual(c["scientificOrdinal"], 40)
        self.assertEqual(c["failedExecution"]["workflowRunId"], 33137514692)
        self.assertEqual(c["failedExecution"]["caseArtifactCount"], 0)
        self.assertEqual(c["failedExecution"]["terminalConclusion"], "cancelled")
        self.assertEqual(c["repair"]["scope"], "EMPTY_DIAGNOSTIC_STREAM_ARTIFACT_CONTRACT_ONLY")
        frozen = c["frozenScientificExperiment"]
        self.assertEqual(frozen["caseCount"], 360)
        self.assertEqual(frozen["commonRandomNumberGroupCount"], 72)
        self.assertEqual(frozen["photonHistoriesPerCase"], 20_000_000)
        self.assertEqual(frozen["fieldFactor"], 3.14)
        for key in (
            "seedAllocationChanged", "caseUniverseChanged", "verticalProfilesChanged",
            "aodChanged", "opacFamilyChanged", "wavelengthGridChanged",
            "geometryChanged", "runtimeIdentityChanged", "analysisChanged",
            "taylorOrJerusalemFitAuthorized",
        ):
            self.assertIs(frozen[key], False, key)
        for value in c["reviewBoundary"].values():
            self.assertIs(value, False)

    def test_recovery_is_not_github_rerun_retry_or_resume(self):
        s = self.contract["recoverySemantics"]
        self.assertFalse(s["githubRerun"])
        self.assertFalse(s["retryOfFailedWorkflowAttempt"])
        self.assertFalse(s["resumeOfPartialCaseSet"])
        self.assertTrue(s["newSeparatelyReviewedRecoveryExecutionRequired"])
        self.assertTrue(s["rerunAll360ExactFrozenCasesRequired"])
        self.assertFalse(s["partialReuseAuthorized"])
        self.assertFalse(s["newScientificOrdinalAuthorized"])
        self.assertFalse(s["newSeedAllocationAuthorized"])

    def test_original_executor_is_exact_and_transform_is_single_snippet_only(self):
        path = ROOT / recovery.ORIGINAL_EXECUTOR_REL
        self.assertEqual(recovery.git_blob_sha1(path), recovery.EXPECTED_ORIGINAL_EXECUTOR_GIT_BLOB_SHA1)
        original = path.read_text()
        self.assertEqual(original.count(recovery.OLD_SNIPPET), 1)
        transformed = recovery.transformed_original_source(ROOT)
        self.assertNotIn(recovery.OLD_SNIPPET, transformed)
        self.assertEqual(transformed.count(recovery.NEW_SNIPPET), 1)
        self.assertEqual(
            transformed.replace(recovery.NEW_SNIPPET, recovery.OLD_SNIPPET, 1),
            original,
        )

    def test_only_four_diagnostic_streams_may_be_empty(self):
        expected = {
            "syntax-stdout.txt", "syntax-stderr.txt",
            "solver-stdout.txt", "solver-stderr.txt",
        }
        self.assertEqual(set(recovery.EMPTY_ALLOWED_DIAGNOSTIC_MEMBERS), expected)
        self.assertEqual(
            set(self.contract["repair"]["diagnosticMembersAllowedEmpty"]),
            expected,
        )
        self.assertTrue(self.contract["repair"]["diagnosticMembersStillRequiredToExist"])
        self.assertTrue(self.contract["repair"]["diagnosticMembersStillHashed"])
        self.assertTrue(self.contract["repair"]["allOtherRawMembersRemainRequiredNonEmpty"])

    def test_result_provenance_preserves_non_retry_semantics(self):
        class FakeModule:
            @staticmethod
            def canonical_sha256(value):
                import hashlib, json
                return hashlib.sha256(
                    json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
                ).hexdigest()

        base = {
            "status": "COMPLETED",
            "retryPerformed": False,
            "resumePerformed": False,
            "githubRerun": False,
            "workflowRunAttempt": 1,
            "workflowRunId": 123,
            "contentSha256": "old",
        }
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "case-result.json"
            p.write_text("{}\n")
            out = recovery._rewrite_result_with_recovery_provenance(FakeModule, base, p)
            self.assertTrue(out["transportRecovery"])
            self.assertEqual(out["recoveryOfWorkflowRunId"], 33137514692)
            self.assertEqual(out["recoveryReason"], "EMPTY_DIAGNOSTIC_STREAM_ARTIFACT_CONTRACT_ONLY")
            self.assertFalse(out["scientificInputsChangedByRecovery"])
            self.assertFalse(out["seedAllocationChangedByRecovery"])
            self.assertFalse(out["caseUniverseChangedByRecovery"])
            self.assertFalse(out["runtimeIdentityChangedByRecovery"])
            self.assertFalse(out["resultOpeningAuthorizedByRecovery"])
            stored = json.loads(p.read_text())
            self.assertEqual(stored, out)
            self.assertNotEqual(out["contentSha256"], "old")

    def test_result_opening_stays_closed(self):
        b = self.contract["resultBoundary"]
        self.assertTrue(b["rawCaseArtifactsOnly"])
        self.assertFalse(b["aggregateResultsAuthorized"])
        self.assertFalse(b["openResultsAuthorized"])
        self.assertFalse(b["partialInterpretationAuthorized"])
        self.assertTrue(b["resultOpeningRequiresLaterSeparateExact360Gate"])


if __name__ == "__main__":
    unittest.main()
