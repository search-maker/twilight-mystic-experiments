from __future__ import annotations

import importlib.util
import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest import mock


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Wave2TrainingDatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.module = load(
            cls.root / "modeling/surrogate-training-v2/exploratory_wave2_training_dataset.py",
            "wave2_training_dataset_test_module",
        )

    def fixture(self, root: Path):
        source_path = root / "source.json"
        audit_path = root / "audit.json"
        analysis_path = root / "analysis.json"
        wave1_root = root / "wave1"
        wave2_root = root / "wave2"
        wave1_root.mkdir()
        wave2_root.mkdir()
        records = []
        source_values: dict[str, list[float]] = {}
        for index, gid in enumerate(self.module.ALL_IDS, start=1):
            training = gid in self.module.TRAINING_IDS
            v1 = 0.001 + index * 0.00001
            v2 = v1 * 1.03
            source_values[gid] = [v1, v2]
            record = {
                "caseIds": [f"{gid}-alis-b1", f"{gid}-alis-b2"],
                "classification": "ADAPTIVE_CONTINUATION_REQUIRED" if gid in self.module.CONTINUATION_IDS else "PRECISION_TARGET_MET",
                "eligibleForInternalHoldout": not training,
                "eligibleForProvisionalFit": training and gid not in self.module.CONTINUATION_IDS,
                "executionComplete": True,
                "geometry": {
                    "geometryId": gid,
                    "sunDepressionDeg": 1.0 + index,
                    "targetAltitudeDeg": 2.0 + index,
                    "relativeAzimuthDeg": 3.0 + index,
                    "observerElevationM": 10.0 + index,
                    "aod550": 0.05 + index / 1000,
                },
                "geometryId": gid,
                "numericalStatus": "NUMERICAL_PRECISION_INSUFFICIENT" if gid in self.module.CONTINUATION_IDS else "NUMERICALLY_CONVERGED",
                "role": "surrogate-training" if training else "internal-holdout",
                "scientificallyEligible": gid not in self.module.CONTINUATION_IDS,
                "statistics": {
                    "blockCount": 2,
                    "meanCdM2": sum(source_values[gid]) / 2,
                    "nodeMeanRadiance": [((v1 + v2) / 2) / 10.0] * 15,
                    "nonzeroBlockValuesCdM2": list(source_values[gid]),
                    "relativeStandardErrorOfMean": 0.01,
                    "relativeStandardErrorStatus": "COMPUTED",
                    "sampleStdCdM2": abs(v2 - v1) / math.sqrt(2),
                    "valuesCdM2": list(source_values[gid]),
                    "zeroHitBlockCount": 0,
                    "zeroHitBlockFraction": 0.0,
                },
                "zeroHitCaseIds": [],
            }
            if not training:
                record["secretHoldoutTargetMustNotDeserialize"] = 100000 + index
            records.append(record)
        source = {
            "adaptiveContinuationRequiredGeometryIds": list(self.module.CONTINUATION_IDS),
            "executionComplete": True,
            "records": records,
            "schemaVersion": 2,
            "scientificallyEligible": False,
            "stageId": self.module.SOURCE_STAGE,
            "status": self.module.SOURCE_STATUS,
            "surrogateTrainingAutomaticallyAuthorized": False,
        }
        source_path.write_text(json.dumps(source, indent=2, sort_keys=True) + "\n")
        audit_path.write_text(json.dumps({"status": "PASSED", "evidence": "synthetic"}, sort_keys=True) + "\n")

        points = []
        for gid in self.module.CONTINUATION_IDS:
            base = source_values[gid]
            block_count = 6 if gid in self.module.WAVE2_TRAINING_IDS or gid in self.module.HOLDOUT_IDS and gid != "train-0045" else 4
            values = list(base)
            for block in range(3, block_count + 1):
                value = base[0] * (1.0 + block / 100.0)
                values.append(value)
                if gid in self.module.TRAINING_IDS:
                    result = {
                        "block": block,
                        "caseId": f"{gid}-synthetic-b{block}",
                        "fittingSurfaceExposed": False,
                        "groupId": gid,
                        "resumeAllowed": False,
                        "retryAllowed": False,
                        "role": "surrogate-training",
                        "schemaVersion": 1,
                        "selectedNodeRadiance": [value / self.module._photopic([1.0] * 15)] * 15,
                        "selectedPhotopicContributionCdM2": value,
                        "solverExecutionCount": 1,
                        "stageId": self.module.WAVE1_RESULT_STAGE if block in {3, 4} else self.module.WAVE2_RESULT_STAGE,
                        "status": "COMPLETED",
                        "syntaxCheckCount": 1,
                        "zeroHit": False,
                    }
                    result["contentSha256"] = self.module.canonical_sha256(result)
                    target = wave1_root if block in {3, 4} else wave2_root
                    case_dir = target / result["caseId"]
                    case_dir.mkdir()
                    (case_dir / "case-result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
            mean = sum(values) / len(values)
            std = math.sqrt(sum((value - mean) ** 2 for value in values) / (len(values) - 1))
            point = {
                "blockCount": block_count,
                "capReached": False,
                "classification": "PRECISION_ACCEPTED" if gid in self.module.WAVE1_ONLY_TRAINING_IDS else "ADAPTIVE_CONTINUATION_REQUIRED",
                "geometryId": gid,
                "nonzeroBlockValuesCdM2": values,
                "numericalStatus": "NUMERICALLY_CONVERGED_ACCEPTED" if gid in self.module.WAVE1_ONLY_TRAINING_IDS else "NUMERICAL_PRECISION_INSUFFICIENT",
                "relativeStandardErrorOfMean": std / math.sqrt(len(values)) / mean,
                "relativeStandardErrorStatus": "COMPUTED",
                "role": "surrogate-training" if gid in self.module.TRAINING_IDS else "internal-holdout",
                "scientificallyEligible": gid in self.module.WAVE1_ONLY_TRAINING_IDS,
                "valuesCdM2": values,
                "zeroHitBlockCount": 0,
                "zeroHitBlockFraction": 0.0,
            }
            if gid in self.module.HOLDOUT_IDS:
                point["secretHoldoutTargetMustNotDeserialize"] = 200000 + len(points)
            points.append(point)
        analysis = {
            "schemaVersion": 1,
            "stageId": self.module.ANALYSIS_STAGE,
            "additionalExecutionAutomaticallyAuthorized": False,
            "internalHoldoutOpened": False,
            "productionPromotionAuthorized": False,
            "surrogateFitAuthorized": False,
            "tier2Authorized": False,
            "analysis": {
                "schemaVersion": 2,
                "stageId": "tier1-precision-continuation-analysis-v2",
                "status": "CONTINUATION_ANALYZED",
                "scientificallyEligible": False,
                "surrogateFitAuthorized": False,
                "additionalExecutionAutomaticallyAuthorized": False,
                "productionPromotionAuthorized": False,
                "points": points,
            },
        }
        analysis_path.write_text(json.dumps(analysis, indent=2, sort_keys=True) + "\n")
        return source_path, audit_path, analysis_path, wave1_root, wave2_root

    def build(self, root: Path):
        source, audit, analysis, wave1, wave2 = self.fixture(root)
        return self.module.build(
            source, audit, analysis, wave1, wave2,
            expected_source_dataset_sha256=self.module.raw_sha256(source),
            expected_source_audit_sha256=self.module.raw_sha256(audit),
            expected_analysis_sha256=self.module.raw_sha256(analysis),
        )

    def test_builds_exact_training_only_b1_b6_dataset(self):
        with tempfile.TemporaryDirectory() as raw:
            value = self.build(Path(raw))
        self.assertEqual(len(value["records"]), 39)
        self.assertEqual(value["blockCountDistribution"], {"2": 22, "4": 3, "6": 14})
        self.assertEqual(value["holdoutRecordCount"], 0)
        self.assertFalse(value["holdoutValuesIncluded"])
        self.assertNotIn("secretHoldoutTargetMustNotDeserialize", json.dumps(value))
        self.assertEqual(value["datasetSha256"], self.module.canonical_sha256({k: v for k, v in value.items() if k != "datasetSha256"}))

    def test_never_deserializes_holdout_records_or_points(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source, audit, analysis, wave1, wave2 = self.fixture(root)
            original = json.loads
            def guarded(text, *args, **kwargs):
                if isinstance(text, str) and "secretHoldoutTargetMustNotDeserialize" in text:
                    raise AssertionError("holdout object was deserialized")
                return original(text, *args, **kwargs)
            with mock.patch.object(self.module.json, "loads", side_effect=guarded):
                value = self.module.build(
                    source, audit, analysis, wave1, wave2,
                    expected_source_dataset_sha256=self.module.raw_sha256(source),
                    expected_source_audit_sha256=self.module.raw_sha256(audit),
                    expected_analysis_sha256=self.module.raw_sha256(analysis),
                )
        self.assertEqual(len(value["records"]), 39)

    def test_refuses_source_hash_drift(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source, audit, analysis, wave1, wave2 = self.fixture(root)
            with self.assertRaisesRegex(Exception, "source corrected dataset raw hash changed"):
                self.module.build(source, audit, analysis, wave1, wave2, expected_source_dataset_sha256="0" * 64, expected_source_audit_sha256=self.module.raw_sha256(audit), expected_analysis_sha256=self.module.raw_sha256(analysis))

    def test_refuses_missing_or_extra_continuation_case(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source, audit, analysis, wave1, wave2 = self.fixture(root)
            next(wave1.rglob("case-result.json")).unlink()
            with self.assertRaisesRegex(Exception, "expected 34"):
                self.module.build(source, audit, analysis, wave1, wave2, expected_source_dataset_sha256=self.module.raw_sha256(source), expected_source_audit_sha256=self.module.raw_sha256(audit), expected_analysis_sha256=self.module.raw_sha256(analysis))

    def test_refuses_case_content_hash_drift(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source, audit, analysis, wave1, wave2 = self.fixture(root)
            path = next(wave2.rglob("case-result.json"))
            row = json.loads(path.read_text())
            row["selectedPhotopicContributionCdM2"] *= 2
            path.write_text(json.dumps(row, indent=2, sort_keys=True) + "\n")
            with self.assertRaisesRegex(Exception, "content hash changed"):
                self.module.build(source, audit, analysis, wave1, wave2, expected_source_dataset_sha256=self.module.raw_sha256(source), expected_source_audit_sha256=self.module.raw_sha256(audit), expected_analysis_sha256=self.module.raw_sha256(analysis))

    def test_refuses_analysis_point_order_drift(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source, audit, analysis, wave1, wave2 = self.fixture(root)
            document = json.loads(analysis.read_text())
            document["analysis"]["points"][0], document["analysis"]["points"][1] = document["analysis"]["points"][1], document["analysis"]["points"][0]
            analysis.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")
            with self.assertRaisesRegex(Exception, "point order or universe changed"):
                self.module.build(source, audit, analysis, wave1, wave2, expected_source_dataset_sha256=self.module.raw_sha256(source), expected_source_audit_sha256=self.module.raw_sha256(audit), expected_analysis_sha256=self.module.raw_sha256(analysis))


if __name__ == "__main__":
    unittest.main()
