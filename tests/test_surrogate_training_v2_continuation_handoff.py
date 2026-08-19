from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ContinuationHandoffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.directory = cls.root / "modeling/surrogate-training-v2"
        cls.handoff = load(
            cls.directory / "continuation_handoff.py",
            "surrogate_training_v2_continuation_handoff_test",
        )
        cls.adapter = load(
            cls.directory / "adapter.py", "surrogate_training_v2_continuation_adapter_test"
        )
        cls.continuation_ids = [
            "train-0003", "train-0007", "train-0009", "train-0011",
            "train-0013", "train-0015", "train-0017", "train-0019",
            "train-0023", "train-0027", "train-0029", "train-0031",
            "train-0033", "train-0035", "train-0039", "train-0041",
            "train-0043", "train-0045", "train-0046", "train-0047",
        ]
        cls.wave2_ids = [
            "train-0003", "train-0007", "train-0009", "train-0011",
            "train-0013", "train-0015", "train-0019", "train-0023",
            "train-0027", "train-0029", "train-0031", "train-0035",
            "train-0039", "train-0041", "train-0043", "train-0047",
        ]

    def _dump(self, path: Path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def fixture(self, root: Path):
        source_records = []
        raw = {}
        points = []
        training_ids = [f"train-{index:04d}" for index in range(1, 40)]
        holdout_ids = [f"train-{index:04d}" for index in range(40, 49)]
        for index, geometry_id in enumerate(training_ids + holdout_ids, start=1):
            role = "surrogate-training" if geometry_id in training_ids else "internal-holdout"
            base = 1e-5 * (1.0 + index / 100.0)
            nodes1 = [base * (1.0 + node / 100.0) for node in range(15)]
            nodes2 = [base * 1.001 * (1.0 + node / 100.0) for node in range(15)]
            case_ids = [f"{geometry_id}-alis-b1", f"{geometry_id}-alis-b2"]
            for case_id, nodes in zip(case_ids, (nodes1, nodes2)):
                raw[case_id] = {"radiance": {"selectedNodeValues": nodes}}
            stats = self.handoff._statistics([nodes1, nodes2])
            continuation = geometry_id in self.continuation_ids
            source_records.append({
                "caseIds": case_ids,
                "classification": "ADAPTIVE_CONTINUATION_REQUIRED" if continuation else "PRECISION_TARGET_MET",
                "eligibleForInternalHoldout": role == "internal-holdout" and not continuation,
                "eligibleForProvisionalFit": role == "surrogate-training" and not continuation,
                "executionComplete": True,
                "geometry": {
                    "alisSpectralImportanceSamplingNm": 550.0,
                    "aod550": 0.05 + index / 1000.0,
                    "executionTierId": "tier-1-provisional",
                    "geometryId": geometry_id,
                    "observerElevationM": float(index * 25),
                    "photonHistoriesPerBlock": 50_000_000,
                    "relativeAzimuthDeg": float(index % 180),
                    "sunDepressionDeg": 2.0 + (index % 16),
                    "targetAltitudeDeg": 5.0 + (index % 70),
                },
                "geometryId": geometry_id,
                "numericalStatus": "NUMERICAL_PRECISION_INSUFFICIENT" if continuation else "NUMERICALLY_CONVERGED",
                "role": role,
                "scientificallyEligible": not continuation,
                "statistics": stats,
                "zeroHitCaseIds": [],
            })
        source_dataset = {
            "schemaVersion": 2,
            "stageId": self.handoff.SOURCE_DATASET_STAGE,
            "status": self.handoff.SOURCE_DATASET_STATUS,
            "executionComplete": True,
            "records": source_records,
        }
        source_audit = {"rawCaseEvidence": raw}
        wave1_root = root / "wave1"
        wave2_root = root / "wave2"
        result_rows = {}
        for geometry_id in self.continuation_ids:
            source = next(row for row in source_records if row["geometryId"] == geometry_id)
            node_rows = [raw[case_id]["radiance"]["selectedNodeValues"] for case_id in source["caseIds"]]
            final_block = 6 if geometry_id in self.wave2_ids else 4
            for block in range(3, final_block + 1):
                factor = 1.0005 + block / 10000.0
                nodes = [value * factor for value in node_rows[0]]
                stage = (
                    "tier1-precision-continuation-wave1-ordinal11-execution-v5"
                    if block in {3, 4}
                    else "tier1-precision-continuation-wave2-ordinal12-execution-v1"
                )
                case_id = f"{geometry_id}-precision-continuation-test-b{block}"
                row = {
                    "schemaVersion": 1,
                    "stageId": stage,
                    "status": "COMPLETED",
                    "caseId": case_id,
                    "groupId": geometry_id,
                    "block": block,
                    "role": source["role"],
                    "seed": 100000 + len(result_rows),
                    "photonHistories": 50_000_000,
                    "manifestSha256": "1" * 64,
                    "runtimeReportSha256": "2" * 64,
                    "inputSha256": "3" * 64,
                    "radianceOutputSha256": "4" * 64,
                    "stdOutputSha256": "5" * 64,
                    "syntaxCheckCount": 1,
                    "solverExecutionCount": 1,
                    "selectedNodeRadiance": nodes,
                    "selectedNodeStdRadiance": [0.0] * 15,
                    "selectedPhotopicContributionCdM2": self.handoff._photopic(nodes),
                    "zeroHit": False,
                    "fittingSurfaceExposed": False,
                    "retryAllowed": False,
                    "resumeAllowed": False,
                }
                row["contentSha256"] = self.handoff.canonical_sha256(row)
                target = wave1_root if block in {3, 4} else wave2_root
                self._dump(target / case_id / "case-result.json", row)
                result_rows[case_id] = row
                node_rows.append(nodes)
            statistics_value = self.handoff._statistics(node_rows)
            points.append({
                "geometryId": geometry_id,
                "role": source["role"],
                "blockCount": final_block,
                "valuesCdM2": statistics_value["valuesCdM2"],
                "nonzeroBlockValuesCdM2": statistics_value["valuesCdM2"],
                "zeroHitBlockCount": 0,
                "zeroHitBlockFraction": 0.0,
                "relativeStandardErrorOfMean": statistics_value["relativeStandardErrorOfMean"],
                "relativeStandardErrorStatus": "COMPUTED",
                "classification": "PRECISION_TARGET_MET",
                "numericalStatus": "NUMERICALLY_CONVERGED_TARGET",
                "capReached": False,
                "scientificallyEligible": True,
            })
        final_analysis = {
            "schemaVersion": 1,
            "stageId": self.handoff.FINAL_ANALYSIS_STAGE,
            "analysis": {
                "schemaVersion": 2,
                "stageId": "tier1-precision-continuation-analysis-v2",
                "status": "CONTINUATION_ANALYZED",
                "points": points,
                "nextWaveGeometryIds": [],
                "exhaustedGeometryIds": [],
                "scientificallyEligible": True,
                "additionalExecutionAutomaticallyAuthorized": False,
                "surrogateFitAuthorized": False,
                "productionPromotionAuthorized": False,
            },
            "surrogateFitAuthorized": False,
            "internalHoldoutOpened": False,
            "tier2Authorized": False,
            "productionPromotionAuthorized": False,
        }
        reference = {
            "schemaVersion": 1,
            "stageId": "twilight-model-readiness-v1",
            "status": "REFERENCE_ANCHORS_VALIDATED",
            "anchorCount": 6,
            "trainingAutomaticallyAuthorized": False,
            "hardValidationAnchorIds": [f"g0{index}" for index in range(2, 7)],
            "softDiagnosticAnchorIds": ["g01"],
            "anchors": [],
        }
        for index, group_id in enumerate(reference["hardValidationAnchorIds"] + ["g01"], start=1):
            reference["anchors"].append({
                "groupId": group_id,
                "geometry": {
                    "sunDepressionDeg": float(index + 2),
                    "targetAltitudeDeg": float(index + 10),
                    "relativeAzimuthDeg": float(index * 10),
                    "observerElevationM": float(index * 100),
                    "aod550": 0.1,
                },
                "methods": {"alis": {"meanCdM2": 1.0 + index, "nodeMeanRadiance": [1e-4] * 15}},
                "anchorStrength": "soft-diagnostic" if group_id == "g01" else "hard",
                "eligibleForTraining": False,
            })
        paths = {
            "source_dataset": root / "source-dataset.json",
            "source_audit": root / "source-audit.json",
            "final_analysis": root / "final-analysis.json",
            "reference": root / "reference.json",
            "manifest": root / "manifest.json",
            "aggregate": root / "aggregate.json",
            "audit": root / "audit.json",
            "wave1": wave1_root,
            "wave2": wave2_root,
        }
        self._dump(paths["source_dataset"], source_dataset)
        self._dump(paths["source_audit"], source_audit)
        self._dump(paths["final_analysis"], final_analysis)
        self._dump(paths["reference"], reference)
        self._dump(paths["manifest"], {"status": "AUTHORIZED_FOR_ONE_ATTEMPT1_EXECUTION"})
        self._dump(paths["aggregate"], {"status": "COMPLETED"})
        self._dump(paths["audit"], {"status": "PASSED", "failures": []})
        return paths, result_rows

    def build(self, root: Path):
        paths, rows = self.fixture(root)
        output = root / "output"
        result = self.handoff.build(
            source_dataset_path=paths["source_dataset"],
            source_audit_path=paths["source_audit"],
            wave1_results_root=paths["wave1"],
            wave2_results_root=paths["wave2"],
            final_analysis_path=paths["final_analysis"],
            reference_anchors_path=paths["reference"],
            final_manifest_path=paths["manifest"],
            final_aggregate_path=paths["aggregate"],
            final_audit_path=paths["audit"],
            exact_main_sha="0" * 40,
            output_dir=output,
        )
        return paths, rows, result

    def test_builds_adapter_compatible_48_geometry_dataset(self):
        with tempfile.TemporaryDirectory() as raw:
            paths, _, result = self.build(Path(raw))
            dataset = json.loads(result["dataset"].read_text())
            report = json.loads(result["report"].read_text())
            self.assertEqual(len(dataset["records"]), 48)
            self.assertEqual(len(dataset["trainingGeometryIds"]), 39)
            self.assertEqual(len(dataset["internalHoldoutGeometryIds"]), 9)
            counts = {record["geometryId"]: len(record["caseIds"]) for record in dataset["records"]}
            self.assertEqual(counts["train-0017"], 4)
            self.assertEqual(counts["train-0003"], 6)
            self.assertEqual(counts["train-0001"], 2)
            partitioned = self.adapter.read_tier1_dataset(
                result["dataset"], result["envelope"], result["design"], expected_main_sha="0" * 40
            )
            self.assertEqual(len(partitioned.training), 39)
            self.assertEqual(len(partitioned.internal_holdout), 9)
            self.assertEqual(report["status"], "FINAL_NUMERICAL_DATASET_READY_FOR_SEPARATE_TRAINING_REVIEW")
            self.assertFalse(report["modelFittingAuthorized"])
            self.assertFalse(report["internalHoldoutOpeningAuthorized"])

    def test_refuses_remaining_adaptive_geometry(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            paths, _ = self.fixture(root)
            analysis = json.loads(paths["final_analysis"].read_text())
            analysis["analysis"]["nextWaveGeometryIds"] = [self.continuation_ids[0]]
            analysis["analysis"]["scientificallyEligible"] = False
            self._dump(paths["final_analysis"], analysis)
            with self.assertRaisesRegex(Exception, "still requires execution"):
                self.handoff.build(
                    source_dataset_path=paths["source_dataset"], source_audit_path=paths["source_audit"],
                    wave1_results_root=paths["wave1"], wave2_results_root=paths["wave2"],
                    final_analysis_path=paths["final_analysis"], reference_anchors_path=paths["reference"],
                    final_manifest_path=paths["manifest"], final_aggregate_path=paths["aggregate"],
                    final_audit_path=paths["audit"], exact_main_sha="0" * 40, output_dir=root / "output",
                )

    def test_refuses_zero_hit_even_with_updated_hash(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            paths, _ = self.fixture(root)
            target = next(paths["wave2"].rglob("train-0003*/*case-result.json"))
            row = json.loads(target.read_text())
            row["selectedNodeRadiance"] = [0.0] * 15
            row["selectedPhotopicContributionCdM2"] = 0.0
            row["zeroHit"] = True
            row["contentSha256"] = self.handoff.canonical_sha256({key: value for key, value in row.items() if key != "contentSha256"})
            self._dump(target, row)
            with self.assertRaisesRegex(Exception, "zero or negative block evidence"):
                self.handoff.build(
                    source_dataset_path=paths["source_dataset"], source_audit_path=paths["source_audit"],
                    wave1_results_root=paths["wave1"], wave2_results_root=paths["wave2"],
                    final_analysis_path=paths["final_analysis"], reference_anchors_path=paths["reference"],
                    final_manifest_path=paths["manifest"], final_aggregate_path=paths["aggregate"],
                    final_audit_path=paths["audit"], exact_main_sha="0" * 40, output_dir=root / "output",
                )

    def test_refuses_case_result_hash_tamper(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            paths, _ = self.fixture(root)
            target = next(paths["wave1"].rglob("case-result.json"))
            row = json.loads(target.read_text())
            row["contentSha256"] = "f" * 64
            self._dump(target, row)
            with self.assertRaisesRegex(Exception, "content hash changed"):
                self.handoff.build(
                    source_dataset_path=paths["source_dataset"], source_audit_path=paths["source_audit"],
                    wave1_results_root=paths["wave1"], wave2_results_root=paths["wave2"],
                    final_analysis_path=paths["final_analysis"], reference_anchors_path=paths["reference"],
                    final_manifest_path=paths["manifest"], final_aggregate_path=paths["aggregate"],
                    final_audit_path=paths["audit"], exact_main_sha="0" * 40, output_dir=root / "output",
                )

    def test_adapter_refuses_case_count_block_count_mismatch(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _, _, result = self.build(root)
            dataset = json.loads(result["dataset"].read_text())
            record = next(item for item in dataset["records"] if len(item["caseIds"]) == 6)
            record["caseIds"] = record["caseIds"][:-1]
            self._dump(result["dataset"], dataset)
            envelope = json.loads(result["envelope"].read_text())
            envelope["datasetRawSha256"] = hashlib.sha256(result["dataset"].read_bytes()).hexdigest()
            self._dump(result["envelope"], envelope)
            with self.assertRaisesRegex(Exception, "case IDs do not match audited block count"):
                self.adapter.read_tier1_dataset(
                    result["dataset"], result["envelope"], result["design"], expected_main_sha="0" * 40
                )


if __name__ == "__main__":
    unittest.main()
