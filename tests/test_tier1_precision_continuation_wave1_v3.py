from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_PATH = ROOT / "experiments/tier1-precision-continuation-wave1-v3/package.py"
PAGES_PATH = ROOT / "experiments/tier1-precision-continuation-wave1-v3/duplicate_pages.py"
SEED_PLAN_PATH = ROOT / "evidence/tier1-precision-continuation-wave1-v3/seed-plan.json"
SNAPSHOT_PATH = ROOT / "evidence/tier1-precision-continuation-wave1-v3/ordinal9-duplicate-search-snapshot.json"
TEMPLATE_PATH = ROOT / "experiments/tier1-precision-continuation-wave1-v3/execution-workflow.template.yml"
WORKFLOW_PATH = ROOT / ".github/workflows/tier1-precision-continuation-wave1-v3-contract.yml"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


package = load(PACKAGE_PATH, "tier1_wave1_v3_package_test")
pages = load(PAGES_PATH, "tier1_wave1_v3_pages_test")


def run_row(run_id: int, title: str, *, attempt: int = 1) -> dict:
    return {
        "id": run_id,
        "display_title": title,
        "status": "completed",
        "conclusion": "success",
        "event": "workflow_dispatch",
        "run_attempt": attempt,
        "head_sha": "1" * 40,
        "head_branch": "main",
    }


class Wave1V3Tests(unittest.TestCase):
    def test_preregistration_is_deterministic_and_preserves_scope(self):
        first = package.build_preregistration(ROOT)
        second = package.build_preregistration(ROOT)
        self.assertEqual(first, second)
        package.validate_preregistration(first, ROOT)
        self.assertEqual(first["stageId"], "tier1-precision-continuation-wave1-preregistration-v3")
        self.assertEqual(first["caseCount"], 40)
        self.assertEqual(first["geometryCount"], 20)
        self.assertEqual(first["maximumConfiguredPhotonHistories"], 5_100_000_000)
        self.assertEqual(first["roleCounts"], {
            "surrogateTrainingGeometries": 17,
            "internalHoldoutGeometries": 3,
            "surrogateTrainingCases": 34,
            "internalHoldoutCases": 6,
        })
        self.assertEqual({row["block"] for row in first["cases"]}, {3, 4})
        self.assertTrue(all("precision-continuation-v3" in row["caseId"] for row in first["cases"]))
        self.assertTrue(all("precision-continuation-v2" in row["baseCaseId"] for row in first["cases"]))
        self.assertEqual(first["thresholds"], {"acceptedMaximum": 0.08, "targetMaximum": 0.05})
        self.assertTrue(first["stoppingRule"]["noEpsilonSubstitution"])
        self.assertFalse(first["authorizationEnabled"])
        self.assertFalse(first["dispatchEnabled"])
        self.assertFalse(first["scientificExecution"])

    def test_new_seed_universe_is_unique_and_disjoint(self):
        value = package.build_preregistration(ROOT)
        seeds = [row["seed"] for row in value["cases"]]
        self.assertEqual(len(seeds), 40)
        self.assertEqual(len(set(seeds)), 40)
        proof = value["seedProof"]
        self.assertEqual(proof["preOrdinal8HistoricalSeedCount"], 196)
        self.assertEqual(proof["ordinal8WaveSeedCount"], 40)
        self.assertEqual(proof["replacementWaveSeedCount"], 40)
        self.assertEqual(proof["historicalOverlap"], [])
        self.assertEqual(proof["ordinal8Overlap"], [])
        plan = json.loads(SEED_PLAN_PATH.read_text(encoding="utf-8"))
        ordered = [
            plan["seedsByGeometry"][gid][block]
            for gid in value["geometryIds"]
            for block in ("b3", "b4")
        ]
        self.assertEqual(seeds, ordered)
        self.assertEqual(package.canonical_sha256(ordered), plan["orderedSeedsSha256"])

    def test_candidate_identity_and_authorization_remain_closed(self):
        prereg = package.build_preregistration(ROOT)
        identity = prereg["candidateIdentity"]
        self.assertEqual(identity["authorizationOrdinal"], 9)
        self.assertEqual(identity["executionKey"], "twilight-surrogate-tier-1-v1:numerical:9")
        self.assertFalse(identity["allocated"])
        self.assertFalse(identity["reserved"])
        self.assertIsNone(identity["authorizationRef"])
        template = package.authorization_template(prereg, ROOT)
        self.assertEqual(template["status"], "DISABLED_TEMPLATE_NOT_AUTHORIZATION")
        self.assertFalse(template["enabled"])
        self.assertIsNone(template["authorizationOrdinal"])
        self.assertIsNone(template["executionKey"])
        self.assertFalse(template["solverExecutionAuthorized"])
        packet = package.review_packet(prereg, ROOT)
        self.assertEqual(packet["status"], "CANDIDATE_ORDINAL9_REVIEW_ONLY_NOT_ALLOCATED")
        self.assertFalse(packet["authorizationAllocated"])
        self.assertFalse(packet["dispatchEnabled"])
        self.assertFalse(packet["scientificExecution"])

    def test_consumed_ordinal8_is_preserved_as_historical_evidence(self):
        value = package.build_preregistration(ROOT)["consumedOrdinal8"]
        self.assertEqual(value["runId"], 31044664420)
        self.assertEqual(value["preflightJobId"], 92437178971)
        self.assertEqual(value["authorizationOrdinal"], 8)
        self.assertTrue(value["failureBeforeRuntimeManifestOrSolver"])
        self.assertTrue(value["seedsConsumedOnDispatch"])

    def test_flatten_pages_supports_one_and_multiple_pages(self):
        title = "Tier-1 precision continuation wave 1 ordinal 9"
        one = pages.flatten_pages([{"workflow_runs": [run_row(7, title)]}])
        self.assertEqual([row["id"] for row in one], [7])
        many = pages.flatten_pages([
            {"workflow_runs": [run_row(7, title)]},
            {"workflow_runs": [run_row(6, "other")]},
        ])
        self.assertEqual([row["id"] for row in many], [7, 6])
        report = pages.duplicate_audit(many, current_run_id=7, candidate_title=title)
        self.assertEqual(report["status"], "NO_PRIOR_MATCHING_RUN")
        self.assertEqual(report["inspectedRunCount"], 2)

    def test_duplicate_pages_fail_closed(self):
        title = "Tier-1 precision continuation wave 1 ordinal 9"
        with self.assertRaises(pages.Refusal):
            pages.flatten_pages([])
        with self.assertRaises(pages.Refusal):
            pages.flatten_pages([{}])
        broken = run_row(7, title)
        del broken["head_sha"]
        with self.assertRaises(pages.Refusal):
            pages.flatten_pages([{"workflow_runs": [broken]}])
        with self.assertRaises(pages.Refusal):
            pages.flatten_pages([{"workflow_runs": [run_row(7, title, attempt=2)]}])
        rows = pages.flatten_pages([{"workflow_runs": [run_row(7, title), run_row(6, title)]}])
        with self.assertRaises(pages.Refusal):
            pages.duplicate_audit(rows, current_run_id=7, candidate_title=title)

    def test_old_cli_incompatibility_is_not_reintroduced(self):
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertNotIn("--slurp --jq", workflow)
        self.assertNotIn("workflow_dispatch", workflow)
        template = TEMPLATE_PATH.read_text(encoding="utf-8")
        self.assertNotIn("workflow_dispatch:", template)
        self.assertNotIn("uvspec", template)
        self.assertNotIn("allow-execution", template)

    def test_generated_review_artifacts_are_byte_deterministic(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "a"
            second = root / "b"
            package.write_generated(ROOT, first)
            package.write_generated(ROOT, second)
            first_files = sorted(path.relative_to(first) for path in first.rglob("*") if path.is_file())
            second_files = sorted(path.relative_to(second) for path in second.rglob("*") if path.is_file())
            self.assertEqual(first_files, second_files)
            for relative in first_files:
                self.assertEqual((first / relative).read_bytes(), (second / relative).read_bytes())

    def test_cli_generation(self):
        with tempfile.TemporaryDirectory() as temporary:
            completed = subprocess.run(
                [sys.executable, str(PACKAGE_PATH), "--output-dir", temporary],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue((Path(temporary) / "candidate-review.json").is_file())

    def test_snapshot_is_review_only_and_has_no_collision(self):
        snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(snapshot["workflowDispatchRunCount"], 12)
        self.assertEqual(snapshot["realOrdinalCollisionMatches"], [])
        self.assertFalse(snapshot["candidateAllocated"])
        self.assertFalse(snapshot["candidateReserved"])
        self.assertFalse(snapshot["authorizationEnabled"])
        self.assertFalse(snapshot["dispatchEnabled"])


if __name__ == "__main__":
    unittest.main()
