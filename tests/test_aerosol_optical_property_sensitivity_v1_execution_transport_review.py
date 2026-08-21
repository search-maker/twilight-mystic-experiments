from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "experiments/aerosol-optical-property-sensitivity-v1"
FREEZE = ROOT / "evidence/aerosol-optical-property-sensitivity-v1/review-freeze.json"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


class AopsExecutionTransportReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.executor = load("aops_executor_review_test", STAGE / "execution-candidate/executor.py")
        self.aggregate = load("aops_aggregate_review_test", STAGE / "execution-candidate/aggregate_results.py")
        self.design_mod = load("aops_execution_design_review_test", STAGE / "execution_design.py")
        self.contract = json.loads((STAGE / "execution-contract.review.json").read_text())
        self.freeze = json.loads(FREEZE.read_text())

    def test_execution_contract_is_review_only_and_exact(self) -> None:
        c = self.contract
        self.assertEqual(c["status"], "FROZEN_REVIEW_ONLY_EXECUTION_CONTRACT_NOT_AUTHORIZED")
        self.assertFalse(c["scientificExecutionAuthorized"])
        self.assertFalse(c["solverExecutionAuthorized"])
        self.assertFalse(c["resultOpeningAuthorized"])
        self.assertEqual(c["expectedCaseCount"], 360)
        self.assertEqual(c["expectedGroupCount"], 72)
        self.assertEqual(c["expectedAnalysisCellCount"], 24)
        self.assertEqual(c["expectedStatesPerGroup"], 5)
        self.assertEqual(c["expectedReplicatesPerCell"], 3)
        self.assertEqual(c["solverTimeoutSeconds"], 7200)
        self.assertEqual(c["githubJobCeilingMinutes"], 150)
        self.assertTrue(c["processGroupIsolationRequired"])
        self.assertEqual(c["rawSpectrumNodeCount"], 8001)
        self.assertEqual(len(c["rawMembersRequired"]), 13)

    def test_review_design_is_seeded_but_still_non_renderable(self) -> None:
        d = self.design_mod.build_review_execution_design()
        self.assertEqual(d["caseCount"], 360)
        self.assertEqual(d["groupCount"], 72)
        self.assertEqual(d["analysisCellCount"], 24)
        by_group: dict[str, list[dict]] = {}
        for row in d["cases"]:
            self.assertFalse(row["renderable"])
            self.assertFalse(row["executionAuthorized"])
            self.assertIsInstance(row["seed"], int)
            by_group.setdefault(row["groupId"], []).append(row)
        self.assertEqual(len(by_group), 72)
        for rows in by_group.values():
            self.assertEqual(len(rows), 5)
            self.assertEqual(len({row["seed"] for row in rows}), 1)
            self.assertEqual(len({row["stateId"] for row in rows}), 5)

    def test_bound_runner_runtime_grid_and_derived_bytes_match(self) -> None:
        c = self.contract
        runner = ROOT / c["sourceBindings"]["processGroupRunnerPath"]
        derived = ROOT / c["sourceBindings"]["r8DerivedChannelsPath"]
        grid = ROOT / c["sourceBindings"]["wavelengthGridPath"]
        runtime = ROOT / c["runtimeIdentity"]["runtimeLockPath"]
        self.assertEqual(git_blob_sha1(runner), c["sourceBindings"]["processGroupRunnerGitBlobSha1"])
        self.assertEqual(git_blob_sha1(derived), c["sourceBindings"]["r8DerivedChannelsGitBlobSha1"])
        self.assertEqual(git_blob_sha1(grid), c["sourceBindings"]["wavelengthGridGitBlobSha1"])
        self.assertEqual(git_blob_sha1(runtime), c["runtimeIdentity"]["runtimeLockGitBlobSha1"])
        self.assertEqual(hashlib.sha256(runtime.read_bytes()).hexdigest(), c["runtimeIdentity"]["runtimeLockRawSha256"])
        self.executor.validate_bound_sources(ROOT, c)

    def test_executor_refuses_without_explicit_execution_permission(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            with self.assertRaisesRegex(self.executor.ExecutionRefusal, "allow-execution"):
                self.executor.execute_case(
                    ROOT,
                    t / "guard.json",
                    t / "runtime.json",
                    "never-run-review-case",
                    t,
                    t / "out",
                    t / "uvspec",
                    allow_execution=False,
                )

    def test_aggregate_refuses_incomplete_artifact_universe_before_analysis(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            metadata = t / "artifacts.json"
            metadata.write_text(json.dumps({"artifacts": []}))
            with self.assertRaisesRegex(self.aggregate.AggregateRefusal, "exactly 360"):
                self.aggregate.aggregate(
                    ROOT,
                    t / "downloaded",
                    metadata,
                    expected_workflow_run_id=1,
                    expected_scientific_ordinal=1,
                )

    def test_freeze_binds_every_execution_and_result_opening_component(self) -> None:
        f = self.freeze
        expected = {
            f["executionContractPath"]: f["executionContractGitBlobSha1"],
            f["executionCandidateExecutorPath"]: f["executionCandidateExecutorGitBlobSha1"],
            f["executionCandidateAggregatorPath"]: f["executionCandidateAggregatorGitBlobSha1"],
            f["executionDesignPath"]: f["executionDesignGitBlobSha1"],
            f["analysisImplementationPath"]: f["analysisImplementationGitBlobSha1"],
            f["analysisContractPath"]: f["analysisContractGitBlobSha1"],
            f["levelBAnalysisPath"]: f["levelBAnalysisGitBlobSha1"],
        }
        for rel, blob in expected.items():
            self.assertEqual(git_blob_sha1(ROOT / rel), blob, rel)
        self.assertTrue(f["executionTransportImplementedReviewOnly"])
        self.assertTrue(f["exact360AcquisitionGateImplementedReviewOnly"])
        for key in (
            "candidateSeedAuthorizationRecheckPassed",
            "scientificOrdinalAllocated",
            "authorizationCreated",
            "dispatchCreated",
            "scientificExecutionAuthorized",
            "solverExecutionAuthorized",
            "resultOpeningAuthorized",
        ):
            self.assertFalse(f[key], key)


if __name__ == "__main__":
    unittest.main()
