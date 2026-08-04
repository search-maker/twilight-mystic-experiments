from __future__ import annotations
import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "experiments" / "observation-integration-v2"
sys.path.insert(0, str(PKG))

from contracts import ContractError, build_visibility_input, canonical_hash, synthetic_radiance_response, validate_observation, validate_radiance_request, validate_radiance_response
from example_data import observation, radiance_request


class ObservationIntegrationV2Tests(unittest.TestCase):
    def test_calibration_observation_valid(self):
        self.assertEqual(validate_observation(observation("calibration"))["role"], "calibration")

    def test_validation_observation_valid(self):
        self.assertEqual(validate_observation(observation("validation"))["role"], "validation")

    def test_validation_used_for_tuning_refused(self):
        value = observation("validation"); value["usedForTuning"] = True; value["canonicalHash"] = canonical_hash(value)
        with self.assertRaisesRegex(ContractError, "forbidden"): validate_observation(value)

    def test_hash_order_independent(self):
        value = radiance_request(); reordered = dict(reversed(list(value.items())))
        self.assertEqual(canonical_hash(value), canonical_hash(reordered))

    def test_hash_changes_with_field(self):
        value = radiance_request(); changed = copy.deepcopy(value); changed["aod550"] = 0.16
        self.assertNotEqual(canonical_hash(value), canonical_hash(changed))

    def test_invalid_geometry(self):
        value = radiance_request(); value["targetAltitudeDeg"] = 91; value["canonicalRequestHash"] = canonical_hash(value)
        with self.assertRaises(ContractError): validate_radiance_request(value)

    def test_missing_atmosphere(self):
        value = radiance_request(); del value["atmosphericProfileId"]; value["canonicalRequestHash"] = canonical_hash(value)
        with self.assertRaises(ContractError): validate_radiance_request(value)

    def test_contradictory_elevation_semantics(self):
        value = radiance_request(); value["sensorHeightAboveLocalSurfaceM"] = 5; value["canonicalRequestHash"] = canonical_hash(value)
        with self.assertRaisesRegex(ContractError, "contradicts"): validate_radiance_request(value)

    def test_missing_provenance(self):
        value = radiance_request(); del value["provenance"]; value["canonicalRequestHash"] = canonical_hash(value)
        with self.assertRaises(ContractError): validate_radiance_request(value)

    def test_duplicate_observation_id(self):
        value = observation()
        with self.assertRaisesRegex(ContractError, "duplicate"): validate_observation(value, {value["observationId"]})

    def test_malformed_timestamp(self):
        value = observation(); value["timestampUtc"] = "2026-08-04 00:30"; value["canonicalHash"] = canonical_hash(value)
        with self.assertRaises(ContractError): validate_observation(value)

    def test_incomplete_spectrum(self):
        response = synthetic_radiance_response(radiance_request()); response["spectrum"] = response["spectrum"][:-1]
        with self.assertRaisesRegex(ContractError, "15-node"): validate_radiance_response(response)

    def test_out_of_domain_propagation(self):
        request = radiance_request(); request["sunDepressionDeg"] = 20; request["canonicalRequestHash"] = canonical_hash(request)
        response = synthetic_radiance_response(request)
        visibility = build_visibility_input(response, catalog_magnitude=1, color_information=None, extinction_inputs={}, observer_adaptation_inputs={})
        self.assertTrue(visibility["outOfDomain"]); self.assertIn("OUT_OF_DOMAIN", visibility["warnings"])

    def test_uncertainty_propagation(self):
        response = synthetic_radiance_response(radiance_request())
        visibility = build_visibility_input(response, catalog_magnitude=1, color_information=None, extinction_inputs={}, observer_adaptation_inputs={})
        self.assertEqual(visibility["radianceUncertainty"], response["uncertainty"])

    def test_refusal_to_claim_scientific_model(self):
        visibility = build_visibility_input(synthetic_radiance_response(radiance_request()), catalog_magnitude=1, color_information=None, extinction_inputs={}, observer_adaptation_inputs={})
        self.assertFalse(visibility["scientificVisibilityModelInstalled"]); self.assertTrue(visibility["syntheticOnly"])

    def test_refusal_to_claim_production_readiness(self):
        response = synthetic_radiance_response(radiance_request()); response["productionEligibility"] = "eligible"
        with self.assertRaisesRegex(ContractError, "unvalidated"): validate_radiance_response(response)

    def test_reproducible_synthetic_example(self):
        self.assertEqual(synthetic_radiance_response(radiance_request()), synthetic_radiance_response(radiance_request()))

    def test_nan_rejected(self):
        value = radiance_request(); value["aod550"] = float("nan")
        with self.assertRaises(ContractError): validate_radiance_request(value)


if __name__ == "__main__": unittest.main()
