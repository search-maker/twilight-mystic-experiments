from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "experiments" / "mystic-batch-v1"


def load(path: Path):
    return json.loads(path.read_text())


def module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FinalConvergenceContract(unittest.TestCase):
    def setUp(self) -> None:
        self.screening_path = PKG / "results/screening-analysis.cross-geometry-stage-two-3.json"
        self.convergence_path = PKG / "results/convergence-v2.cross-geometry-stage-two-3.json"
        self.provenance_path = PKG / "results/final-convergence-source-provenance.json"
        self.stage2_path = PKG / "manifest.cross-geometry-stage-two.proposal.json"
        self.proposal_path = PKG / "manifest.cross-geometry-final-convergence.proposal.json"

    def test_convergence_v2_reproduces_frozen_result(self) -> None:
        convergence = module("convergence_v2", PKG / "cross_geometry_convergence_v2.py")
        self.assertEqual(convergence.reanalyze_stage_two(load(self.screening_path)), load(self.convergence_path))
        results = {item["groupId"]: item for item in load(self.convergence_path)["geometryResults"]}
        self.assertEqual(results["g04-mid-perpendicular"]["classificationV2"], "SCREENING_AGREEMENT")
        self.assertEqual(results["g01-reference-bridge"]["classificationV2"], "NEEDS_MORE_PRECISION")
        self.assertFalse(results["g01-reference-bridge"]["methodStatisticsV2"]["alis"]["reportedNodeStdAvailable"])

    def test_final_manifest_reproduces_from_frozen_sources(self) -> None:
        generator = module("final_generator", PKG / "cross_geometry_final_convergence.py")
        generated = generator.build(
            load(self.stage2_path),
            load(self.screening_path),
            load(self.convergence_path),
            load(self.provenance_path),
            self.stage2_path,
            self.screening_path,
            self.convergence_path,
        )
        self.assertEqual(generated, load(self.proposal_path))
        self.assertEqual(len(generated["cases"]), 26)
        self.assertEqual(sum(case["photonHistories"] for case in generated["cases"]), 520_000_000)
        self.assertEqual(generated["limits"]["maximumParallel"], 16)
        diagnostic = [case for case in generated["cases"] if case["purpose"] == "alis-reference-diagnostic"]
        self.assertEqual(len(diagnostic), 18)
        self.assertEqual({case["alisSpectralImportanceSamplingNm"] for case in diagnostic}, {500.0, 550.0, 600.0})

    def test_authorization_is_exactly_disabled(self) -> None:
        active = load(PKG / "authorization.cross-geometry-final.json")
        template = load(PKG / "authorization.cross-geometry-final-execution-template.json")
        self.assertEqual(active, template)
        self.assertFalse(active["authorized"])
        self.assertEqual(active["authorizationOrdinal"], 0)

    def test_adapter_and_plan_boundaries(self) -> None:
        adapter = module("final_adapter", PKG / "cross_geometry_final_execution_adapter.py")
        proposal = load(self.proposal_path)
        adapter.validate_manifest(proposal)
        broken = json.loads(json.dumps(proposal))
        next(case for case in broken["cases"] if case["purpose"] == "alis-reference-diagnostic")["alisSpectralImportanceSamplingNm"] = 575.0
        with self.assertRaises(adapter.AdapterRefusal):
            adapter.validate_manifest(broken)

        plan_module = module("final_plan", PKG / "cross_geometry_final_execution_plan.py")
        guard = {
            "status": "AUTHORIZED",
            "stageId": "cross-geometry-final-convergence-v1",
            "batchId": proposal["batchId"],
            "proposalRawSha256": "a" * 64,
            "executionAdapterRawSha256": "b" * 64,
            "runtimeLockRawSha256": "c" * 64,
            "executionWorkflowRawSha256": "d" * 64,
            "authorizationRef": "e" * 40,
            "authorizationOrdinal": 4,
            "executionKey": "cross-geometry-final-convergence-v1:screening:4",
            "sourceScreeningRawSha256": "f" * 64,
            "sourceConvergenceV2RawSha256": "1" * 64,
            "sourceProvenanceRawSha256": "2" * 64,
        }
        with tempfile.TemporaryDirectory() as temporary:
            guard_path = Path(temporary) / "guard.json"
            guard_path.write_text(json.dumps(guard))
            plan = plan_module.build_plan(self.proposal_path, guard_path)
        self.assertEqual(plan["caseCount"], 26)
        self.assertEqual(plan["maximumParallel"], 16)
        self.assertEqual(plan["configuredMcPhotonsSum"], 520_000_000)

    def test_workflows_are_manual_one_shot_or_proposal_only(self) -> None:
        execution = (ROOT / ".github/workflows/mystic-batch-v1-cross-geometry-final-execution.yml").read_text()
        header = execution.split("jobs:", 1)[0]
        self.assertIn("workflow_dispatch:", header)
        self.assertNotIn("pull_request:", header)
        self.assertNotIn("push:", header)
        self.assertIn("fail-fast: false", execution)
        self.assertIn("max-parallel: ${{ fromJSON(needs.preflight.outputs.max_parallel) }}", execution)
        self.assertEqual(execution.count("Execute exactly one isolated final-convergence case"), 1)
        self.assertNotIn("retry", execution.lower())

        proposal_workflow = (ROOT / ".github/workflows/mystic-batch-v1-cross-geometry-final-authorization-proposal.yml").read_text()
        proposal_header = proposal_workflow.split("jobs:", 1)[0]
        self.assertNotIn("workflow_dispatch:", proposal_header)
        self.assertNotIn("uvspec", proposal_workflow.lower())
        self.assertNotIn("micromamba", proposal_workflow.lower())


if __name__ == "__main__":
    unittest.main()
