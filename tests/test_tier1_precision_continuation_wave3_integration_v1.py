from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from tests.test_tier1_precision_continuation_wave2_execution_v1 import Wave2ExecutionV1Tests
from tests.test_tier1_precision_continuation_wave3_execution_v1 import Wave3ExecutionV1Tests


class Wave3IntegrationV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        Wave2ExecutionV1Tests.setUpClass()
        Wave3ExecutionV1Tests.setUpClass()
        cls.wave2 = Wave2ExecutionV1Tests()
        cls.wave3 = Wave3ExecutionV1Tests()

    def test_actual_wave1_plus_synthetic_wave2_and_wave3_reaches_cap_analysis(self):
        source_root = os.getenv("WAVE3_SOURCE_SALVAGE_ROOT")
        if not source_root:
            self.skipTest("merged-main wave-one salvage not mounted")
        source = Path(source_root)
        wave1_aggregate = self.wave2.execution.load_bound_source(
            source / "salvage/aggregate.json",
            self.wave2.execution.SOURCE_AGGREGATE_RAW_SHA256,
        )
        wave1_audit = self.wave2.execution.load_bound_source(
            source / "salvage/audit.json",
            self.wave2.execution.SOURCE_AUDIT_RAW_SHA256,
        )

        wave2_manifest = self.wave2.manifest()
        wave2_results = self.wave2.fake_results(wave2_manifest)
        wave2_aggregate = self.wave2.execution.aggregate(
            self.root, wave2_manifest, wave2_results
        )
        wave2_audit = self.wave2.execution.audit(
            self.root, wave2_manifest, wave2_results, wave2_aggregate
        )
        wave2_analysis = self.wave2.execution.analyze(
            self.root,
            wave2_manifest,
            wave1_aggregate,
            wave1_audit,
            wave2_aggregate,
            wave2_audit,
        )
        self.assertEqual(
            len(wave2_analysis["analysis"]["nextWaveGeometryIds"]), 16
        )
        self.assertFalse(wave2_analysis["analysis"]["scientificallyEligible"])

        with tempfile.TemporaryDirectory() as raw:
            work = Path(raw)
            original = self.wave3.source_path
            self.wave3.source_path = lambda root: self.wave3.source_fixture.write_source(
                root, wave2_analysis
            )
            try:
                _, preregistration, wave3_manifest = self.wave3.manifest(work)
            finally:
                self.wave3.source_path = original
            self.assertEqual(preregistration["geometryCount"], 16)
            self.assertEqual(preregistration["caseCount"], 32)
            wave3_results = self.wave3.fake_results(wave3_manifest)
            wave3_aggregate = self.wave3.postprocess.aggregate_wave3(
                preregistration, wave3_results, self.root
            )
            wave3_audit = self.wave3.postprocess.audit_wave3(
                preregistration, wave3_results, wave3_aggregate, self.root
            )
            analysis = self.wave3.postprocess.analyze_waves(
                preregistration,
                wave1_aggregate,
                wave1_audit,
                wave2_aggregate,
                wave2_audit,
                wave3_aggregate,
                wave3_audit,
                self.root,
            )
        body = analysis["analysis"]
        self.assertEqual(body["status"], "CONTINUATION_ANALYZED")
        self.assertEqual(len(body["points"]), 20)
        self.assertEqual(body["nextWaveGeometryIds"], [])
        self.assertTrue(body["exhaustedGeometryIds"])
        self.assertFalse(analysis["additionalExecutionAutomaticallyAuthorized"])
        self.assertFalse(analysis["surrogateFitAuthorized"])
        self.assertFalse(analysis["internalHoldoutOpened"])
        self.assertFalse(analysis["tier2Authorized"])
        self.assertFalse(analysis["productionPromotionAuthorized"])


if __name__ == "__main__":
    unittest.main()
