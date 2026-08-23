from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECOVERY = ROOT / "experiments/aerosol-optical-property-sensitivity-v1-analysis-recovery-v1"
PROTOCOL = RECOVERY / "protocol.review.json"
HUMAN = RECOVERY / "bound-human-threshold.mjs"
WORKFLOW = ROOT / ".github/workflows/aops-v1-analysis-recovery-v1.yml"


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


class AopsV1AnalysisRecoveryV1Tests(unittest.TestCase):
    def test_protocol_binds_exact_consumed_source_and_forbids_new_science(self) -> None:
        p = json.loads(PROTOCOL.read_text())
        self.assertEqual(p["stageId"], "aerosol-optical-property-sensitivity-v1-analysis-recovery-v1")
        self.assertEqual(p["status"], "REVIEW_ONLY_ANALYSIS_RECOVERY_NOT_EXECUTED")
        src = p["sourceScience"]
        self.assertEqual(src["workflowRunId"], 32624595188)
        self.assertEqual(src["workflowRunAttempt"], 1)
        self.assertEqual(src["scientificOrdinal"], 37)
        self.assertEqual(src["dispatchHead"], "a1895adebf39a5c2c12d80276a119e032fdf090b")
        self.assertEqual(src["sourceConclusion"], "failure")
        self.assertEqual(src["caseJobCount"], 360)
        self.assertEqual(src["caseJobSuccessCount"], 360)
        self.assertEqual(src["caseArtifactCount"], 360)
        self.assertEqual(src["aggregateJobId"], 97168843965)
        self.assertEqual(src["exact360AcquisitionScalarSpectralStepConclusion"], "success")
        self.assertFalse(src["levelBExecuted"])
        self.assertFalse(src["finalAnalysisArtifactPersisted"])
        boundary = p["executionBoundary"]
        for key in (
            "analysisRecoveryExecutionAuthorizedByThisReview",
            "solverExecutionPermitted",
            "uvspecPermitted",
            "libRadtranRuntimeSetupPermitted",
            "scientificDispatchPermitted",
            "scientificOrdinalAllocationPermitted",
            "scientificSeedAllocationPermitted",
            "githubRerunPermitted",
            "retryPermitted",
            "resumePermitted",
        ):
            self.assertIs(boundary[key], False, key)
        self.assertIs(boundary["separateSingleUseRecoveryRequestRequiredAfterMerge"], True)

    def test_bound_human_threshold_is_exact_upstream_git_blob(self) -> None:
        p = json.loads(PROTOCOL.read_text())
        self.assertEqual(p["humanThresholdBinding"]["gitBlobSha1"], "bb4cd0ff02159ecffe276022cec9d292c7a434a3")
        self.assertEqual(git_blob_sha1(HUMAN), "bb4cd0ff02159ecffe276022cec9d292c7a434a3")

    def test_frozen_analysis_bindings_are_exact(self) -> None:
        p = json.loads(PROTOCOL.read_text())["frozenCodeBindings"]
        pairs = {
            "aggregateResultsGitBlobSha1": ROOT / p["aggregateResultsPath"],
            "analysisGitBlobSha1": ROOT / p["analysisPath"],
            "levelBDriverGitBlobSha1": ROOT / p["levelBDriverPath"],
            "levelBAnalysisGitBlobSha1": ROOT / p["levelBAnalysisPath"],
            "executionContractGitBlobSha1": ROOT / p["executionContractPath"],
            "sourceExecutionWorkflowGitBlobSha1": ROOT / p["sourceExecutionWorkflowPath"],
        }
        for key, path in pairs.items():
            self.assertEqual(git_blob_sha1(path), p[key], f"byte drift: {path}")

    def test_workflow_is_request_gated_and_analysis_only(self) -> None:
        text = WORKFLOW.read_text()
        self.assertIn("status/aops-v1-analysis-recovery-ordinal-37", text)
        self.assertIn("execution-request.json", text)
        self.assertIn("SOURCE_RUN_ID: \"32624595188\"", text)
        self.assertIn("--workflow-run-id 32624595188 --scientific-ordinal 37", text)
        self.assertIn("aops-v1-analysis-recovery-ordinal-37", text)
        self.assertIn("AOPS-V1-ANALYSIS-RECOVERY-COMPLETED", text)
        self.assertNotIn("AOPS-V1-SCIENCE-COMPLETED", text)
        for forbidden in (
            "workflow_dispatch:",
            "uvspec",
            "setup-micromamba",
            "rubin-libradtran",
            "execute_case(",
            "executor.py",
            "mc_photons",
            "rte_solver mystic",
            "rerun_workflow",
            "re-run",
        ):
            self.assertNotIn(forbidden, text, forbidden)

    def test_workflow_requires_exact_source_terminal_shape_before_download(self) -> None:
        text = WORKFLOW.read_text()
        self.assertIn("len(jobs)!=362", text)
        self.assertIn("len(cases)!=360", text)
        self.assertIn("source case jobs not exact 360/360 success", text)
        self.assertIn("Run frozen exact-360 acquisition and scalar/spectral analysis':'success'", text)
        self.assertIn("Fetch exact bound starsvisibility human-threshold implementation':'failure'", text)
        self.assertIn("Run frozen Level-B propagation only after exact-360 aggregate':'skipped'", text)
        self.assertIn("source unexpectedly already has final analysis artifact", text)
        self.assertIn("artifact digest mismatch", text)

    def test_no_inference_or_epsilon_rules_are_relaxed(self) -> None:
        p = json.loads(PROTOCOL.read_text())["analysisRules"]
        self.assertFalse(p["pValuesPermitted"])
        self.assertFalse(p["confidenceIntervalsPermitted"])
        self.assertFalse(p["epsilonSubstitutionPermitted"])
        self.assertFalse(p["postResultRuleChangePermitted"])
        self.assertFalse(p["newCrossCellPoolingPermitted"])
        self.assertFalse(p["universalSunDepressionToMinutesConversionPermitted"])


if __name__ == "__main__":
    unittest.main()
