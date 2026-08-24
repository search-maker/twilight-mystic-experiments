from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECOVERY = ROOT / "experiments/aerosol-full-phase-function-sensitivity-v1-analysis-recovery-v1"
PROTOCOL = RECOVERY / "protocol.review.json"
HUMAN = RECOVERY / "bound-human-threshold.mjs"
WORKFLOW = ROOT / ".github/workflows/afpf-v1-analysis-recovery-v1.yml"


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


class AfpfV1AnalysisRecoveryV1Tests(unittest.TestCase):
    def test_protocol_binds_exact_consumed_source_and_forbids_new_science(self) -> None:
        p = json.loads(PROTOCOL.read_text())
        self.assertEqual(p["stageId"], "aerosol-full-phase-function-sensitivity-v1-analysis-recovery-v1")
        self.assertEqual(p["status"], "REVIEW_ONLY_ANALYSIS_RECOVERY_NOT_EXECUTED")
        src = p["sourceScience"]
        self.assertEqual(src["workflowRunId"], 32672764808)
        self.assertEqual(src["workflowRunAttempt"], 1)
        self.assertEqual(src["scientificOrdinal"], 38)
        self.assertEqual(src["dispatchHead"], "7c160d1b1d1fbaa534076b7d30c14fcceda0e877")
        self.assertEqual(src["authorizationParentMain"], "c6096fa860802793128c386bb685e6698af108f9")
        self.assertEqual(src["sourceConclusion"], "failure")
        self.assertEqual(src["caseJobCount"], 360)
        self.assertEqual(src["caseJobSuccessCount"], 360)
        self.assertEqual(src["caseArtifactCount"], 360)
        self.assertEqual(src["aggregateJobId"], 97294103672)
        self.assertEqual(src["preflightArtifact"]["id"], 9501900123)
        self.assertEqual(src["preflightArtifact"]["digest"], "sha256:33807259982a4bceae06e079338af1bbbecb60a6024ca4bf94c4267e65d4c1b2")
        self.assertEqual(src["exact360AcquisitionScalarSpectralStepConclusion"], "success")
        self.assertEqual(src["levelBInputBuildStepConclusion"], "success")
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
            "buildLevelBInputGitBlobSha1": ROOT / p["buildLevelBInputPath"],
            "levelBRunnerGitBlobSha1": ROOT / p["levelBRunnerPath"],
            "levelBAnalysisGitBlobSha1": ROOT / p["levelBAnalysisPath"],
            "executionContractGitBlobSha1": ROOT / p["executionContractPath"],
            "sourceExecutionWorkflowGitBlobSha1": ROOT / p["sourceExecutionWorkflowPath"],
        }
        for key, path in pairs.items():
            self.assertEqual(git_blob_sha1(path), p[key], f"byte drift: {path}")

    def test_workflow_is_request_gated_and_analysis_only(self) -> None:
        text = WORKFLOW.read_text()
        self.assertIn("status/afpf-v1-analysis-recovery-ordinal-38", text)
        self.assertIn("execution-request.json", text)
        self.assertIn('SOURCE_RUN_ID: "32672764808"', text)
        self.assertIn("--workflow-run-id 32672764808", text)
        self.assertIn("--scientific-ordinal 38", text)
        self.assertIn("afpf-v1-analysis-recovery-ordinal-38", text)
        self.assertIn("AFPF-V1-ANALYSIS-RECOVERY-COMPLETED", text)
        self.assertNotIn("AFPF-V1-SCIENCE-COMPLETED", text)
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
        self.assertIn("int(agg[0].get('id') or 0)!=97294103672", text)
        self.assertIn("Run frozen exact-360 acquisition and scalar spectral analysis':'success'", text)
        self.assertIn("Build Level-B input only after exact-360 aggregate success':'success'", text)
        self.assertIn("Fetch exact bound starsvisibility human-threshold implementation':'failure'", text)
        self.assertIn("Run frozen Level-B propagation only after exact-360 aggregate':'skipped'", text)
        self.assertIn("source unexpectedly already has final analysis artifact", text)
        self.assertIn("9501900123", text)
        self.assertIn("33807259982a4bceae06e079338af1bbbecb60a6024ca4bf94c4267e65d4c1b2", text)
        self.assertIn("artifact digest mismatch", text)
        self.assertIn("preflight artifact digest mismatch", text)

    def test_recovery_replays_exact_design_and_frozen_level_b(self) -> None:
        text = WORKFLOW.read_text()
        self.assertIn("d2ad0e3ebcea48b2c683ab8a1c255af074cdaaa084c7082ac9345d021c8c9f62", text)
        self.assertIn("build_level_b_input.py", text)
        self.assertIn("level_b_runner.mjs", text)
        self.assertIn("bb4cd0ff02159ecffe276022cec9d292c7a434a3", text)
        self.assertIn("desert_spheroids_vs_desert", text)
        self.assertIn("contrastCountPerCell!==7", text)

    def test_no_inference_or_epsilon_rules_are_relaxed(self) -> None:
        p = json.loads(PROTOCOL.read_text())["analysisRules"]
        self.assertEqual(p["priorityShapeContrast"], "desert_spheroids_vs_desert")
        self.assertFalse(p["pValuesPermitted"])
        self.assertFalse(p["confidenceIntervalsPermitted"])
        self.assertFalse(p["epsilonSubstitutionPermitted"])
        self.assertFalse(p["postResultRuleChangePermitted"])
        self.assertFalse(p["newCrossCellPoolingPermitted"])
        self.assertFalse(p["universalSunDepressionToMinutesConversionPermitted"])


if __name__ == "__main__":
    unittest.main()
