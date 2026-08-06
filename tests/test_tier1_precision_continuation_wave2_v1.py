from __future__ import annotations

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


class Wave2V1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.package = load(
            cls.root / "experiments/tier1-precision-continuation-wave2-v1/package.py",
            "wave2_v1_test_package",
        )

    def test_preregistration_exact_scope_and_roles(self):
        p = self.package
        value = p.build_preregistration(self.root)
        p.validate_preregistration(value, self.root)
        self.assertEqual(value, p.build_preregistration(self.root))
        self.assertEqual(value["status"], "PREPARATION_ONLY_NOT_AUTHORIZED")
        self.assertEqual(value["wave"], 2)
        self.assertEqual(value["blocks"], [5, 6])
        self.assertEqual(value["geometryCount"], 16)
        self.assertEqual(value["caseCount"], 32)
        self.assertEqual(value["maximumConfiguredPhotonHistories"], 4_600_000_000)
        self.assertEqual(
            value["roleCounts"],
            {
                "surrogateTrainingGeometries": 14,
                "internalHoldoutGeometries": 2,
                "surrogateTrainingCases": 28,
                "internalHoldoutCases": 4,
            },
        )
        self.assertEqual(
            value["internalHoldoutGeometryIds"], ["train-0015", "train-0035"]
        )
        self.assertEqual(
            value["geometryIds"], value["sourceWave1NextGeometryIds"]
        )
        self.assertIn("train-0047", value["geometryIds"])
        self.assertEqual({row["block"] for row in value["cases"]}, {5, 6})
        self.assertEqual(len({row["caseId"] for row in value["cases"]}), 32)
        self.assertTrue(
            all("precision-continuation-wave2-v1" in row["caseId"] for row in value["cases"])
        )

    def test_seed_proof_covers_every_consumed_and_preserved_universe(self):
        proof = self.package.build_preregistration(self.root)["seedProof"]
        self.assertEqual(proof["preOrdinal8HistoricalSeedCount"], 196)
        self.assertEqual(proof["ordinal8WaveSeedCount"], 40)
        self.assertEqual(proof["ordinal9WaveSeedCount"], 40)
        self.assertEqual(proof["ordinal10WaveSeedCount"], 40)
        self.assertEqual(proof["ordinal11WaveSeedCount"], 40)
        self.assertEqual(proof["preservedFutureSeedCount"], 80)
        self.assertEqual(proof["wave2SeedCount"], 32)
        self.assertTrue(proof["allWave2SeedsUnique"])
        for key in (
            "historicalOverlap",
            "ordinal8Overlap",
            "ordinal9Overlap",
            "ordinal10Overlap",
            "ordinal11Overlap",
            "preservedFutureOverlap",
        ):
            self.assertEqual(proof[key], [], key)
        self.assertEqual(
            proof["wave2SeedsSha256"],
            "a2f25e18689d3acbb8f27c112385d608037d8821ffa287b43c2a1830f5aa38b5",
        )

    def test_source_salvage_and_candidate_identity_are_exact_and_closed(self):
        p = self.package
        c = p._core()
        source = c.source_descriptor(self.root)
        self.assertEqual(source["sourceWorkflowRunId"], 31063167217)
        self.assertEqual(source["sourceArtifactId"], 8952843354)
        self.assertEqual(
            source["sourceArtifactDigest"],
            "sha256:0fd662b3420e0162d9580cb30b4859775b3f43feba5b9264d26aed61c163f56b",
        )
        self.assertEqual(source["scientificSource"]["authorizationOrdinal"], 11)
        self.assertTrue(source["scientificSource"]["identityConsumed"])
        snapshot = c.duplicate_snapshot(self.root)
        self.assertEqual(snapshot["candidateOrdinal"], 12)
        self.assertFalse(snapshot["candidateAllocated"])
        self.assertFalse(snapshot["dispatchExists"])
        prereg = p.build_preregistration(self.root)
        candidate = prereg["candidateIdentity"]
        self.assertEqual(candidate["authorizationOrdinal"], 12)
        self.assertEqual(
            candidate["executionKey"], "twilight-surrogate-tier-1-v1:numerical:12"
        )
        self.assertFalse(candidate["allocated"])
        self.assertFalse(candidate["reserved"])
        self.assertIsNone(candidate["authorizationRef"])

    def test_templates_and_review_packet_authorize_nothing(self):
        p = self.package
        prereg = p.build_preregistration(self.root)
        template = p.authorization_template(prereg, self.root)
        packet = p.candidate_review(prereg, self.root)
        self.assertFalse(template["enabled"])
        self.assertIsNone(template["authorizationOrdinal"])
        self.assertIsNone(template["executionKey"])
        self.assertFalse(template["dispatch"])
        self.assertFalse(template["solverExecutionAuthorized"])
        self.assertFalse(packet["authorizationAllocated"])
        self.assertFalse(packet["dispatchEnabled"])
        self.assertFalse(packet["scientificExecution"])
        for key in (
            "surrogateTrainingAuthorized",
            "internalHoldoutOpeningAuthorized",
            "tier2Authorized",
            "productionPromotionAuthorized",
        ):
            self.assertFalse(packet[key])

    def test_generation_is_byte_deterministic(self):
        p = self.package
        with tempfile.TemporaryDirectory() as first_raw, tempfile.TemporaryDirectory() as second_raw:
            first = Path(first_raw)
            second = Path(second_raw)
            p.write_generated(self.root, first)
            p.write_generated(self.root, second)
            first_files = {path.name: path.read_bytes() for path in first.iterdir()}
            second_files = {path.name: path.read_bytes() for path in second.iterdir()}
            self.assertEqual(first_files, second_files)
            report = json.loads(first_files["generation-report.json"])
            self.assertEqual(report["status"], "DETERMINISTIC_REVIEW_ARTIFACTS_GENERATED")
            self.assertFalse(report["authorizationAllocated"])
            self.assertFalse(report["dispatchEnabled"])
            self.assertFalse(report["scientificExecution"])

    def test_preservation_and_stopping_rule_remain_closed(self):
        value = self.package.build_preregistration(self.root)
        preservation = value["preservation"]
        for key in (
            "ordinal11EvidenceImmutable",
            "ordinal11WorkflowNotRerun",
            "ordinal11IdentityNeverReused",
            "ordinal11SeedsNeverReused",
            "b1ThroughB4EvidenceImmutable",
            "physicalInputsUnchanged",
            "geometryRolesUnchanged",
            "photonHistoriesPerBlockUnchanged",
            "thresholdsUnchanged",
            "stoppingRuleUnchanged",
            "zeroHitTreatmentUnchanged",
        ):
            self.assertTrue(preservation[key])
        stopping = value["stoppingRule"]
        self.assertTrue(stopping["zeroHitOrdinaryRsemForbidden"])
        self.assertTrue(stopping["zeroHitRemainsAdaptiveUntilEightBlockCap"])
        self.assertFalse(stopping["automaticNextWave"])
        self.assertFalse(value["surrogateTrainingAuthorized"])
        self.assertFalse(value["internalHoldoutOpeningAuthorized"])
        self.assertFalse(value["tier2Authorized"])
        self.assertFalse(value["productionPromotionAuthorized"])


if __name__ == "__main__":
    unittest.main()
