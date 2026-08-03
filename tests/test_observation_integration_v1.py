from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "experiments" / "observation-integration-v1"
sys.path.insert(0, str(PACKAGE))

import contracts  # noqa: E402
import demo  # noqa: E402
import radiance_api  # noqa: E402
import visibility_api  # noqa: E402


class ObservationIntegrationV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.example_path = PACKAGE / "observation.synthetic.json"
        self.example = json.loads(self.example_path.read_text())

    def test_observation_contract_accepts_calibration_example(self) -> None:
        normalized = contracts.validate_observation(self.example)
        self.assertEqual(normalized["role"], "calibration")
        self.assertTrue(normalized["usedForParameterTuning"])

    def test_validation_record_cannot_be_used_for_tuning(self) -> None:
        invalid = copy.deepcopy(self.example)
        invalid["role"] = "validation"
        invalid["usedForParameterTuning"] = True
        with self.assertRaises(contracts.ContractError):
            contracts.validate_observation(invalid)

    def test_canonical_observation_hash_is_order_independent(self) -> None:
        normalized = contracts.validate_observation(self.example)
        reordered = {key: normalized[key] for key in reversed(list(normalized))}
        self.assertEqual(contracts.canonical_sha256(normalized), contracts.canonical_sha256(reordered))

    def test_synthetic_radiance_response_is_bound_and_complete(self) -> None:
        request = {
            "schemaVersion": 1,
            "apiId": "twilight-radiance-spectrum-v1",
            "sunDepressionDeg": 10.0,
            "targetAltitudeDeg": 30.0,
            "relativeAzimuthDeg": 90.0,
            "aod550": 0.15,
            "observerElevationM": 20.0,
        }
        response = radiance_api.SyntheticRadianceProvider().predict(request)
        self.assertEqual(len(response["radianceWm2SrNm"]), len(radiance_api.WAVELENGTHS_NM))
        self.assertTrue(response["syntheticOnly"])
        self.assertFalse(response["outOfDomain"])

    def test_radiance_request_rejects_invalid_geometry(self) -> None:
        request = {
            "schemaVersion": 1,
            "apiId": "twilight-radiance-spectrum-v1",
            "sunDepressionDeg": 10.0,
            "targetAltitudeDeg": 100.0,
            "relativeAzimuthDeg": 90.0,
            "aod550": 0.15,
            "observerElevationM": 20.0,
        }
        with self.assertRaises(contracts.ContractError):
            radiance_api.SyntheticRadianceProvider().predict(request)

    def test_end_to_end_demo_and_darker_sky_monotonicity(self) -> None:
        provider = radiance_api.SyntheticRadianceProvider()
        base = {
            "schemaVersion": 1,
            "apiId": "star-visibility-integration-v1",
            "catalogMagnitude": 4.0,
            "colorIndexBv": 0.7,
            "extinctionMagnitude": 0.2,
            "observerAdaptationOffsetMagnitude": 0.0,
            "radianceRequest": {
                "schemaVersion": 1,
                "apiId": "twilight-radiance-spectrum-v1",
                "sunDepressionDeg": 6.0,
                "targetAltitudeDeg": 30.0,
                "relativeAzimuthDeg": 90.0,
                "aod550": 0.15,
                "observerElevationM": 20.0,
            },
        }
        early = visibility_api.predict_visibility(base, provider)
        late_request = copy.deepcopy(base)
        late_request["radianceRequest"]["sunDepressionDeg"] = 15.0
        late = visibility_api.predict_visibility(late_request, provider)
        self.assertGreater(late["syntheticVisibilityProbability"], early["syntheticVisibilityProbability"])
        self.assertTrue(late["syntheticOnly"])
        with tempfile.TemporaryDirectory() as temp:
            result = demo.run(self.example_path, Path(temp) / "demo.json")
            self.assertEqual(result["status"], "SYNTHETIC_DEMO_COMPLETE")
            self.assertFalse(result["visibility"]["scientificVisibilityModelInstalled"])


if __name__ == "__main__":
    unittest.main()
