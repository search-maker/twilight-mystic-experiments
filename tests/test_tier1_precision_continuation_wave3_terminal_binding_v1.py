from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TerminalBindingV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.binding = load(
            cls.root / "experiments/tier1-precision-continuation-wave3-v1/terminal_binding.py",
            "wave3_terminal_binding_test",
        )

    def payload(self):
        points = []
        for geometry_id in self.binding.ACTIVE_GEOMETRY_IDS:
            points.append(
                {
                    "geometryId": geometry_id,
                    "blockCount": 6,
                    "capReached": False,
                    "classification": "ADAPTIVE_CONTINUATION_REQUIRED",
                    "scientificallyEligible": False,
                    "zeroHitBlockCount": self.binding.EXPECTED_ZERO_HIT_COUNTS.get(geometry_id, 0),
                }
            )
        for geometry_id, (block_count, classification) in self.binding.RESOLVED_GEOMETRIES.items():
            points.append(
                {
                    "geometryId": geometry_id,
                    "blockCount": block_count,
                    "capReached": False,
                    "classification": classification,
                    "scientificallyEligible": True,
                    "zeroHitBlockCount": 0,
                }
            )
        return {
            "schemaVersion": 1,
            "stageId": "tier1-precision-continuation-wave2-analysis-v1",
            "analysisSha256": self.binding.SOURCE_ANALYSIS_SHA256,
            "preregistrationSha256": self.binding.SOURCE_PREREGISTRATION_SHA256,
            "sourceWave1AggregateSha256": self.binding.SOURCE_WAVE1_AGGREGATE_SHA256,
            "sourceWave1AuditSha256": self.binding.SOURCE_WAVE1_AUDIT_SHA256,
            "wave2AggregateSha256": self.binding.SOURCE_WAVE2_AGGREGATE_SHA256,
            "wave2AuditSha256": self.binding.SOURCE_WAVE2_AUDIT_SHA256,
            "additionalExecutionAutomaticallyAuthorized": False,
            "surrogateFitAuthorized": False,
            "internalHoldoutOpened": False,
            "tier2Authorized": False,
            "productionPromotionAuthorized": False,
            "analysis": {
                "schemaVersion": 2,
                "stageId": "tier1-precision-continuation-analysis-v2",
                "status": "CONTINUATION_ANALYZED",
                "nextWaveGeometryIds": list(self.binding.ACTIVE_GEOMETRY_IDS),
                "exhaustedGeometryIds": [],
                "scientificallyEligible": False,
                "additionalExecutionAutomaticallyAuthorized": False,
                "surrogateFitAuthorized": False,
                "productionPromotionAuthorized": False,
                "points": sorted(points, key=lambda row: row["geometryId"]),
            },
        }

    def test_exact_terminal_structure_is_accepted(self):
        report = self.binding.validate_structure(self.payload())
        self.assertEqual(report["status"], "ORDINAL12_TERMINAL_SOURCE_EXACTLY_BOUND")
        self.assertEqual(report["geometryCount"], 15)
        self.assertEqual(report["caseCount"], 30)
        self.assertEqual(report["geometryIds"], list(self.binding.ACTIVE_GEOMETRY_IDS))
        self.assertFalse(report["authorizationAllocated"])
        self.assertFalse(report["dispatchEnabled"])

    def test_refuses_active_set_reordering_or_reduction(self):
        value = self.payload()
        value["analysis"]["nextWaveGeometryIds"] = list(reversed(value["analysis"]["nextWaveGeometryIds"]))
        with self.assertRaisesRegex(Exception, "scope changed"):
            self.binding.validate_structure(value)

    def test_refuses_zero_hit_semantic_drift(self):
        value = self.payload()
        point = next(row for row in value["analysis"]["points"] if row["geometryId"] == "train-0039")
        point["zeroHitBlockCount"] = 0
        with self.assertRaisesRegex(Exception, "active terminal point changed"):
            self.binding.validate_structure(value)

    def test_refuses_resolved_geometry_reopening(self):
        value = self.payload()
        point = next(row for row in value["analysis"]["points"] if row["geometryId"] == "train-0009")
        point["scientificallyEligible"] = False
        with self.assertRaisesRegex(Exception, "resolved terminal point changed"):
            self.binding.validate_structure(value)

    def test_refuses_source_hash_drift(self):
        value = self.payload()
        value["wave2AuditSha256"] = "0" * 64
        with self.assertRaisesRegex(Exception, "terminal binding changed"):
            self.binding.validate_structure(value)


if __name__ == "__main__":
    unittest.main()
