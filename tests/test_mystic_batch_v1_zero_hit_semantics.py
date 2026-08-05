from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "experiments" / "mystic-batch-v1"
FIXTURE = ROOT / "tests" / "fixtures" / "mystic-batch-v1-zero-hit-v2" / "fixture.json"
NODES = [470, 480, 490, 500, 510, 520, 530, 540, 560, 580, 590, 600, 610, 640, 660]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


aggregate_module = load_module("zero_hit_aggregate", PACKAGE / "scientific_aggregate_v2.py")
audit_module = load_module("zero_hit_audit", PACKAGE / "scientific_audit_v2.py")
analysis_module = load_module("zero_hit_analysis", PACKAGE / "twilight_surrogate_tier1_analysis_v2.py")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


class ZeroHitSemanticsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.cases_root = self.root / "case-artifacts"
        self.aggregate_dir = self.root / "aggregate"
        self.audit_path = self.root / "audit" / "audit-report.json"
        self.fixture = json.loads(FIXTURE.read_text())
        self.plan_path = self._build_fixture()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _build_fixture(self) -> Path:
        plan_path = self.root / "plan.json"
        cases = [
            {
                key: source[key]
                for key in ("caseId", "groupId", "block", "role", "ordinal", "seed", "photonHistories")
            }
            for source in self.fixture["cases"]
        ]
        plan = {
            "stageId": "mystic-batch-v1",
            "scientificExecution": True,
            "batchId": "ordinal2-zero-hit-regression-v2",
            "manifestRawSha256": "a" * 64,
            "authorizationRef": "b" * 40,
            "configuredMcPhotonsSum": sum(case["photonHistories"] for case in cases),
            "runtimeLockRawSha256": "c" * 64,
            "scientificAdapterRawSha256": "d" * 64,
            "executionWorkflowRawSha256": "e" * 64,
            "cases": cases,
        }
        write_json(plan_path, plan)
        for source in self.fixture["cases"]:
            case_id = source["caseId"]
            case_dir = self.cases_root / "case-output" / case_id
            runtime_dir = self.cases_root / "runtime-reports" / case_id
            case_dir.mkdir(parents=True)
            runtime_dir.mkdir(parents=True)
            input_path = case_dir / "input-resolved.txt"
            radiance_path = case_dir / "mc.rad.spc"
            std_path = case_dir / "mc.rad.std.spc"
            runtime_path = runtime_dir / "runtime-report.json"
            input_path.write_text(f"case {case_id}\n")
            radiance_path.write_text(
                "".join(f"{node:.5f} {value:.17g}\n" for node, value in zip(NODES, source["nodes"]))
            )
            std_path.write_text("".join(f"{node:.5f} 0\n" for node in NODES))
            write_json(runtime_path, {"stageId": "mystic-batch-v1", "status": "RUNTIME_IDENTITY_CAPTURED"})
            result = {
                "schemaVersion": 1,
                "stageId": "mystic-batch-v1",
                "status": "COMPLETED",
                "scientificDiagnostic": True,
                "successDoesNotAuthorizeProduction": True,
                "batchId": plan["batchId"],
                "caseId": case_id,
                "ordinal": source["ordinal"],
                "seed": source["seed"],
                "photonHistories": source["photonHistories"],
                "manifestRawSha256": plan["manifestRawSha256"],
                "adapterRawSha256": plan["scientificAdapterRawSha256"],
                "runtimeReportRawSha256": sha256(runtime_path),
                "inputResolvedSha256": sha256(input_path),
                "radianceOutputSha256": sha256(radiance_path),
                "stdOutputSha256": sha256(std_path),
                "syntaxCheckCount": 1,
                "solverExecutionCount": 1,
                "syntax": {"exitCode": 0, "timedOut": False, "elapsedSeconds": 0.01},
                "solver": {"exitCode": 0, "timedOut": False, "elapsedSeconds": 1000.0},
                "selectedPhotopicContributionCdM2": source["photopic"],
                "selectedNodeRadiance": source["nodes"],
                "selectedNodeStdRadiance": [0.0] * 15,
                "failure": None,
            }
            write_json(case_dir / "case-result.json", result)
        return plan_path

    def _case_result_path(self, case_id: str) -> Path:
        return self.cases_root / "case-output" / case_id / "case-result.json"

    def _aggregate(self):
        return aggregate_module.aggregate(self.plan_path, self.cases_root, self.aggregate_dir)

    def _audit(self):
        return audit_module.audit(self.plan_path, self.cases_root, self.aggregate_dir, self.audit_path)

    def test_zero_hit_is_execution_complete_but_scientifically_ineligible(self) -> None:
        summary, execution_complete = self._aggregate()
        self.assertTrue(execution_complete)
        self.assertEqual(summary["status"], "COMPLETED")
        self.assertEqual(summary["classification"], "SCIENTIFICALLY_INELIGIBLE")
        self.assertTrue(summary["executionComplete"])
        self.assertFalse(summary["scientificallyEligible"])
        self.assertEqual(summary["caseCountCompleted"], 6)
        self.assertEqual(summary["caseCountFailed"], 0)
        self.assertEqual(summary["structuralFailures"], [])
        self.assertEqual(summary["continuationRequiredGeometryIds"], ["train-0047"])
        self.assertEqual(summary["zeroHitDiagnostics"][0]["caseId"], "train-0047-alis-b1")
        self.assertEqual(summary["zeroHitDiagnostics"][0]["classification"], "NUMERICAL_ZERO_HIT_UNDERCONVERGED")

        geometries = {item["geometryId"]: item for item in summary["geometryResults"]}
        self.assertEqual(set(geometries), {"train-0046", "train-0047", "train-0048"})
        self.assertEqual(geometries["train-0047"]["classification"], "ADAPTIVE_CONTINUATION_REQUIRED")
        self.assertIsNone(geometries["train-0047"]["statistics"]["coefficientOfVariation"])
        self.assertEqual(
            geometries["train-0047"]["statistics"]["coefficientOfVariationStatus"],
            "NOT_COMPUTED_ZERO_HIT_PRESENT",
        )
        self.assertIsNotNone(geometries["train-0046"]["statistics"])
        self.assertIsNotNone(geometries["train-0048"]["statistics"])

        report, passed = self._audit()
        self.assertTrue(passed)
        self.assertEqual(report["status"], "PASSED")
        self.assertEqual(report["batchClassification"], "SCIENTIFICALLY_INELIGIBLE")
        self.assertTrue(report["zeroHitDiagnostics"][0]["derivedFromRawOutputs"])
        self.assertTrue(report["unaffectedGeometryStatisticsVerified"])
        self.assertFalse(report["incompleteGeometryEnteredTrainingEligibility"])

    def test_solver_crash_and_timeout_remain_execution_failures(self) -> None:
        for mutation in ("crash", "timeout"):
            with self.subTest(mutation=mutation):
                self.tearDown()
                self.setUp()
                path = self._case_result_path("train-0046-alis-b1")
                result = json.loads(path.read_text())
                if mutation == "crash":
                    result["status"] = "FAILED"
                    result["solver"]["exitCode"] = 7
                    result["failure"] = {"code": "solver-failure"}
                else:
                    result["solver"]["timedOut"] = True
                write_json(path, result)
                summary, execution_complete = self._aggregate()
                self.assertFalse(execution_complete)
                self.assertEqual(summary["classification"], "STRUCTURAL_OR_EXECUTION_FAILURE")
                geometry = next(item for item in summary["geometryResults"] if item["geometryId"] == "train-0046")
                self.assertFalse(geometry["executionComplete"])
                self.assertEqual(geometry["classification"], "STRUCTURAL_OR_EXECUTION_FAILURE")
                report, passed = self._audit()
                self.assertFalse(passed)
                self.assertEqual(report["status"], "FAILED")
                self.assertEqual(report["batchClassification"], "STRUCTURAL_OR_EXECUTION_FAILURE")

    def test_positive_science_values_are_recomputed_from_raw_spectra(self) -> None:
        result_path = self._case_result_path("train-0046-alis-b1")
        result = json.loads(result_path.read_text())
        result["selectedPhotopicContributionCdM2"] = 999.0
        result["selectedNodeRadiance"] = [999.0] * 15
        write_json(result_path, result)
        self._aggregate()
        report, passed = self._audit()
        self.assertFalse(passed)
        codes = {item["code"] for item in report["failures"]}
        self.assertIn("selected-radiance-raw-mismatch", codes)
        self.assertIn("photopic-raw-mismatch", codes)

    def test_malformed_completed_case_is_failed_at_batch_and_geometry_levels(self) -> None:
        result_path = self._case_result_path("train-0046-alis-b1")
        result = json.loads(result_path.read_text())
        result["selectedNodeRadiance"] = [1.0]
        write_json(result_path, result)
        summary, execution_complete = self._aggregate()
        self.assertFalse(execution_complete)
        self.assertEqual(summary["classification"], "STRUCTURAL_OR_EXECUTION_FAILURE")
        geometry = next(item for item in summary["geometryResults"] if item["geometryId"] == "train-0046")
        self.assertFalse(geometry["executionComplete"])
        self.assertEqual(geometry["classification"], "STRUCTURAL_OR_EXECUTION_FAILURE")
        self.assertIsNone(geometry["statistics"])

    def test_missing_malformed_and_hash_mismatched_outputs_fail_independent_audit(self) -> None:
        mutations = ("missing", "malformed", "hash-mismatch")
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                self.tearDown()
                self.setUp()
                summary, execution_complete = self._aggregate()
                self.assertTrue(execution_complete)
                case_id = "train-0046-alis-b1"
                spectrum = self.cases_root / "case-output" / case_id / "mc.rad.spc"
                result_path = self._case_result_path(case_id)
                result = json.loads(result_path.read_text())
                if mutation == "missing":
                    spectrum.unlink()
                elif mutation == "malformed":
                    spectrum.write_text("470 nan\n")
                    result["radianceOutputSha256"] = sha256(spectrum)
                    write_json(result_path, result)
                else:
                    spectrum.write_text(spectrum.read_text() + "700 1\n")
                report, passed = self._audit()
                self.assertFalse(passed)
                self.assertEqual(report["status"], "FAILED")
                self.assertEqual(report["batchClassification"], "STRUCTURAL_OR_EXECUTION_FAILURE")

    def test_identity_drift_and_duplicate_seed_are_refused(self) -> None:
        summary, _ = self._aggregate()
        self.assertEqual(summary["classification"], "SCIENTIFICALLY_INELIGIBLE")
        path = self._case_result_path("train-0048-alis-b2")
        result = json.loads(path.read_text())
        result["seed"] += 1
        write_json(path, result)
        drift_summary, drift_complete = self._aggregate()
        self.assertFalse(drift_complete)
        self.assertEqual(drift_summary["classification"], "STRUCTURAL_OR_EXECUTION_FAILURE")

        self.tearDown()
        self.setUp()
        plan = json.loads(self.plan_path.read_text())
        plan["cases"][1]["seed"] = plan["cases"][0]["seed"]
        write_json(self.plan_path, plan)
        duplicate_summary, _ = self._aggregate()
        self.assertEqual(duplicate_summary["classification"], "STRUCTURAL_OR_EXECUTION_FAILURE")
        duplicate_geometry = next(
            item for item in duplicate_summary["geometryResults"] if item["geometryId"] == "train-0046"
        )
        self.assertFalse(duplicate_geometry["executionComplete"])
        self.assertEqual(duplicate_geometry["classification"], "STRUCTURAL_OR_EXECUTION_FAILURE")
        duplicate_report, passed = self._audit()
        self.assertFalse(passed)
        self.assertTrue(any(item["code"] == "duplicate-planned-seeds" for item in duplicate_report["failures"]))

    def test_aggregate_case_paths_are_relative_posix_and_location_independent(self) -> None:
        first, first_complete = self._aggregate()
        self.assertTrue(first_complete)
        self.assertTrue(all(not Path(item["path"]).is_absolute() for item in first["caseIndex"]))
        self.assertTrue(all("\\" not in item["path"] for item in first["caseIndex"]))
        copied_cases = self.root / "copied-case-artifacts"
        shutil.copytree(self.cases_root, copied_cases)
        second, second_complete = aggregate_module.aggregate(
            self.plan_path, copied_cases, self.root / "copied-aggregate"
        )
        self.assertTrue(second_complete)
        self.assertEqual(first, second)

    def test_tier1_analysis_emits_all_48_points_while_zero_hit_remains_ineligible(self) -> None:
        analysis_root = self.root / "analysis-fixture"
        case_root = analysis_root / "cases"
        case_root.mkdir(parents=True)
        geometries = []
        cases = []
        for geometry_number in range(1, 49):
            geometry_id = f"train-{geometry_number:04d}"
            geometries.append({"geometryId": geometry_id, "testCoordinate": geometry_number})
            role = "surrogate-training" if geometry_number <= 39 else "internal-holdout"
            for block in (1, 2):
                case_id = f"{geometry_id}-alis-b{block}"
                value = 0.0 if geometry_number == 47 and block == 1 else 7.721895898159138e-13 if geometry_number == 47 else float(geometry_number)
                nodes = [0.0] * 15 if value == 0.0 else [value / 100.0] * 15
                cases.append(
                    {
                        "caseId": case_id,
                        "groupId": geometry_id,
                        "block": block,
                        "role": role,
                        "seed": geometry_number * 10 + block,
                        "photonHistories": 1,
                    }
                )
                case_dir = case_root / case_id
                case_dir.mkdir()
                write_json(
                    case_dir / "case-result.json",
                    {
                        "caseId": case_id,
                        "status": "COMPLETED",
                        "seed": geometry_number * 10 + block,
                        "photonHistories": 1,
                        "solver": {"exitCode": 0, "timedOut": False},
                        "selectedPhotopicContributionCdM2": value,
                        "selectedNodeRadiance": nodes,
                    },
                )
        manifest_path = analysis_root / "manifest.json"
        summary_path = analysis_root / "summary.json"
        audit_path = analysis_root / "audit.json"
        write_json(
            manifest_path,
            {
                "stageId": "twilight-surrogate-tier-1-execution-v1",
                "geometries": geometries,
                "cases": cases,
            },
        )
        write_json(
            summary_path,
            {
                "schemaVersion": 2,
                "status": "COMPLETED",
                "executionComplete": True,
                "classification": "SCIENTIFICALLY_INELIGIBLE",
                "caseCountCompleted": 96,
                "configuredMcPhotonsSum": 6_960_000_000,
                "manifestRawSha256": sha256(manifest_path),
            },
        )
        case_hashes = {
            json.loads(path.read_text())["caseId"]: sha256(path)
            for path in sorted(case_root.rglob("case-result.json"))
        }
        write_json(
            audit_path,
            {
                "schemaVersion": 2,
                "stageId": "mystic-batch-v1",
                "status": "PASSED",
                "batchClassification": "SCIENTIFICALLY_INELIGIBLE",
                "executionComplete": True,
                "scientificallyEligible": False,
                "caseResultCount": 96,
                "failures": [],
                "successDoesNotAuthorizeProduction": True,
                "incompleteGeometryEnteredTrainingEligibility": False,
                "manifestRawSha256": sha256(manifest_path),
                "aggregateRawSha256": sha256(summary_path),
                "caseResultHashes": case_hashes,
            },
        )
        analysis, dataset = analysis_module.analyze(manifest_path, case_root, summary_path, audit_path)
        self.assertEqual(len(analysis["points"]), 48)
        self.assertEqual(analysis["zeroHitGeometryIds"], ["train-0047"])
        self.assertEqual(analysis["adaptiveContinuationRequiredGeometryIds"], ["train-0047"])
        self.assertEqual(analysis["status"], "TIER_1_ANALYZED_WITH_CONTINUATION_REQUIRED")
        self.assertFalse(analysis["scientificallyEligible"])
        self.assertEqual(dataset["status"], "TIER_1_NUMERICAL_DATASET_PARTIAL_PRECISION")
        zero_point = next(point for point in analysis["points"] if point["geometryId"] == "train-0047")
        self.assertEqual(zero_point["numericalStatus"], "NUMERICAL_ZERO_HIT_UNDERCONVERGED")
        self.assertFalse(zero_point["eligibleForProvisionalFit"])
        self.assertEqual(zero_point["statistics"]["relativeStandardErrorStatus"], "NOT_COMPUTED_ZERO_HIT_PRESENT")
        self.assertEqual(len([point for point in analysis["points"] if point["scientificallyEligible"]]), 47)
        complete_audit = json.loads(audit_path.read_text())
        incomplete_audit = dict(complete_audit)
        incomplete_audit.pop("failures")
        write_json(audit_path, incomplete_audit)
        with self.assertRaisesRegex(analysis_module.AnalysisError, "independent audit failed"):
            analysis_module.analyze(manifest_path, case_root, summary_path, audit_path)
        write_json(audit_path, complete_audit)
        tampered_path = case_root / "train-0001-alis-b1" / "case-result.json"
        tampered = json.loads(tampered_path.read_text())
        tampered["selectedPhotopicContributionCdM2"] = 999.0
        write_json(tampered_path, tampered)
        with self.assertRaisesRegex(analysis_module.AnalysisError, "hashes differ"):
            analysis_module.analyze(manifest_path, case_root, summary_path, audit_path)


if __name__ == "__main__":
    unittest.main()
