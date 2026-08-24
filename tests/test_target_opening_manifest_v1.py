import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "review" / "empirical-twilight-radiance-source-admission-v1" / "validate_target_opening_manifest_v1.py"
spec = importlib.util.spec_from_file_location("opening_v1", SCRIPT)
opening = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(opening)

H = "a" * 64


def bindings():
    return {key: H for key in opening.REQUIRED_BINDINGS}


def object_row(source_id="obj-001", spectrometer=2):
    return {
        "sourceObjectId": source_id,
        "sourcePathOrProviderObjectId": f"provider:{source_id}",
        "siteId": "Izana",
        "instrumentId": "209",
        "spectrometerId": spectrometer,
        "exposureIdentity": f"exposure:{source_id}",
        "metadataIdentitySha256": H,
        "calibrationBindingId": "cal-1",
        "operationBindingId": "op-1",
        "protectedArrays": ["LEVEL1.DATA", "LEVEL1.UNCERTAINTY", "LEVEL1.UNCERTAINTY.INSTRUMENT"],
    }


def manifest(lane="PANDORA209_S2_JOHNSON_V_ONLY_V1", objects=None):
    return {
        "schemaVersion": 1,
        "datasetFreezeId": "freeze-test",
        "laneId": lane,
        "createdAtUtc": "2026-08-24T00:00:00Z",
        "preValueBindings": bindings(),
        "objects": objects or [object_row()],
        "authorization": {
            "targetOpeningAuthorized": False,
            "separateAuthorizationArtifactRequired": True,
        },
    }


class TargetOpeningManifestV1Tests(unittest.TestCase):
    def test_valid_s2_manifest_is_still_unauthorized(self):
        result = opening.validate_prevalue_manifest(manifest())
        self.assertTrue(result["valid"])
        self.assertEqual(result["laneId"], "PANDORA209_S2_JOHNSON_V_ONLY_V1")
        self.assertEqual(result["objectCount"], 1)
        self.assertFalse(result["targetOpeningAuthorized"])
        self.assertEqual(len(result["manifestCanonicalSha256"]), 64)

    def test_prevalue_manifest_cannot_self_authorize(self):
        doc = manifest()
        doc["authorization"]["targetOpeningAuthorized"] = True
        with self.assertRaisesRegex(ValueError, "targetOpeningAuthorized=false"):
            opening.validate_prevalue_manifest(doc)

    def test_target_outcome_fields_are_rejected_before_opening(self):
        doc = manifest()
        doc["objects"][0]["observedRadiance"] = 123.0
        with self.assertRaisesRegex(ValueError, "target-outcome field"):
            opening.validate_prevalue_manifest(doc)

    def test_johnson_lane_rejects_s1(self):
        with self.assertRaisesRegex(ValueError, "spectrometerId not allowed"):
            opening.validate_prevalue_manifest(manifest(objects=[object_row(spectrometer=1)]))

    def test_three_channel_lane_requires_both_spectrometers(self):
        doc = manifest(
            lane="PANDORA209_S1S2_THREE_CHANNEL_V1",
            objects=[object_row("obj-001", 1)],
        )
        with self.assertRaisesRegex(ValueError, "both spectrometer"):
            opening.validate_prevalue_manifest(doc)

    def test_three_channel_lane_accepts_sorted_s1_s2_objects(self):
        doc = manifest(
            lane="PANDORA209_S1S2_THREE_CHANNEL_V1",
            objects=[object_row("obj-001", 1), object_row("obj-002", 2)],
        )
        result = opening.validate_prevalue_manifest(doc)
        self.assertEqual(result["objectCount"], 2)

    def test_objects_must_be_unique_and_canonically_ordered(self):
        duplicate = manifest(objects=[object_row("obj-001"), object_row("obj-001")])
        with self.assertRaisesRegex(ValueError, "duplicate sourceObjectId"):
            opening.validate_prevalue_manifest(duplicate)
        unordered = manifest(objects=[object_row("obj-002"), object_row("obj-001")])
        with self.assertRaisesRegex(ValueError, "lexicographically ordered"):
            opening.validate_prevalue_manifest(unordered)

    def test_binding_hashes_fail_closed(self):
        doc = manifest()
        doc["preValueBindings"][opening.REQUIRED_BINDINGS[0]] = "not-a-hash"
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            opening.validate_prevalue_manifest(doc)


if __name__ == "__main__":
    unittest.main()
