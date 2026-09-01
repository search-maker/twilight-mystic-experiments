from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = (
    ROOT
    / "integration"
    / "measurement-operator-provenance-v1"
    / "measurement_operator_contract.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("measurement_operator_contract", MODULE)
    if spec is None or spec.loader is None:
        raise RuntimeError(MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


contract = load_module()


class MeasurementOperatorContractTests(unittest.TestCase):
    def operator(self, operator_id: str = "operator-a"):
        components = contract.MATERIAL_COMPONENTS
        return {
            "schemaVersion": 1,
            "operatorId": operator_id,
            "status": {component: "complete" for component in components},
            "operatorSpec": {
                "observableClass": "point-direction",
                "angularResponse": {
                    "kind": "delta-direction",
                    "fieldOfViewDiameterDeg": 0.0,
                    "weighting": "delta",
                },
                "pointing": {
                    "centerAltitudeDeg": 90.0,
                    "centerAzimuthConvention": "undefined-at-zenith",
                },
                "spectralResponse": {
                    "kind": "photopic-luminance",
                    "responseId": "cie-v-lambda-explicit-fixture",
                },
                "calibration": {
                    "kind": "physical-luminance",
                    "scale": 1.0,
                    "zeroPoint": "not-applicable-physical-unit",
                },
                "temporalResponse": {
                    "kind": "instantaneous-sample",
                    "integrationSeconds": 0.0,
                    "averaging": "none",
                },
                "units": {"quantity": "luminance", "unit": "cd/m^2"},
                "geometryConvention": {
                    "solarAltitude": "geometric-topocentric",
                    "refractionApplied": False,
                },
            },
            "provenance": {component: "unit-test fixture" for component in components},
        }

    def compare(self, measured, synthetic, claim="quantitative-validation", applied=True):
        return contract.compare_operators(
            measured_operator=measured,
            synthetic_operator=synthetic,
            claim_class=claim,
            synthetic_operator_applied=applied,
        )

    def test_complete_exact_operator_match_passes(self):
        measured = self.operator("measured")
        synthetic = self.operator("synthetic")
        result = self.compare(measured, synthetic)
        self.assertEqual(result["status"], "VALID_OPERATOR_MATCH")
        self.assertTrue(result["sameOperatorSpec"])
        self.assertEqual(result["mismatchedSections"], [])

    def test_missing_operator_material_is_refused(self):
        measured = self.operator("measured")
        del measured["operatorSpec"]["spectralResponse"]
        with self.assertRaises(contract.MeasurementOperatorRefusal):
            self.compare(measured, self.operator("synthetic"))

    def test_point_vs_wide_field_is_refused_quantitatively(self):
        measured = self.operator("measured")
        synthetic = self.operator("synthetic")
        synthetic["operatorSpec"]["observableClass"] = "wide-field"
        synthetic["operatorSpec"]["angularResponse"] = {
            "kind": "measured-wide-field-response",
            "fieldOfViewDiameterDeg": 120.0,
            "weighting": "explicit-fixture",
        }
        with self.assertRaises(contract.MeasurementOperatorRefusal):
            self.compare(measured, synthetic)

    def test_finite_aperture_diameter_mismatch_is_refused(self):
        measured = self.operator("measured")
        synthetic = self.operator("synthetic")
        for value in (measured, synthetic):
            value["operatorSpec"]["observableClass"] = "finite-aperture"
            value["operatorSpec"]["angularResponse"] = {
                "kind": "circular-finite-aperture",
                "fieldOfViewDiameterDeg": 1.5,
                "weighting": "explicit-fixture-top-hat",
            }
        synthetic["operatorSpec"]["angularResponse"]["fieldOfViewDiameterDeg"] = 2.0
        with self.assertRaises(contract.MeasurementOperatorRefusal):
            self.compare(measured, synthetic)

    def test_spectral_mismatch_is_refused(self):
        measured = self.operator("measured")
        synthetic = self.operator("synthetic")
        synthetic["operatorSpec"]["spectralResponse"]["responseId"] = "other-bandpass"
        with self.assertRaises(contract.MeasurementOperatorRefusal):
            self.compare(measured, synthetic)

    def test_synthetic_operator_must_actually_be_applied(self):
        with self.assertRaises(contract.MeasurementOperatorRefusal):
            self.compare(self.operator("measured"), self.operator("synthetic"), applied=False)

    def test_partial_historical_operator_cannot_be_quantitative(self):
        measured = self.operator("historical")
        measured["status"]["angularResponse"] = "partial"
        measured["operatorSpec"]["angularResponse"]["weighting"] = "unknown-explicit"
        with self.assertRaises(contract.MeasurementOperatorRefusal):
            self.compare(measured, self.operator("synthetic"))

    def test_partial_historical_operator_remains_diagnostic(self):
        measured = self.operator("historical")
        synthetic = copy.deepcopy(measured)
        synthetic["operatorId"] = "synthetic-research"
        measured["status"]["angularResponse"] = "partial"
        measured["status"]["spectralResponse"] = "partial"
        measured["status"]["calibration"] = "partial"
        measured["status"]["temporalResponse"] = "partial"
        synthetic["status"] = {
            component: "complete" for component in contract.MATERIAL_COMPONENTS
        }
        result = self.compare(measured, synthetic, claim="diagnostic")
        self.assertEqual(result["status"], "DIAGNOSTIC_ONLY")
        self.assertTrue(result["sameOperatorSpec"])
        self.assertEqual(
            set(result["incompleteMeasuredComponents"]),
            {"angularResponse", "spectralResponse", "calibration", "temporalResponse"},
        )

    def test_diagnostic_reports_operator_mismatch_without_passing_it(self):
        measured = self.operator("measured")
        synthetic = self.operator("synthetic")
        synthetic["operatorSpec"]["geometryConvention"]["solarAltitude"] = "apparent"
        result = self.compare(measured, synthetic, claim="diagnostic")
        self.assertEqual(result["status"], "DIAGNOSTIC_ONLY")
        self.assertFalse(result["sameOperatorSpec"])
        self.assertIn("geometryConvention", result["mismatchedSections"])


if __name__ == "__main__":
    unittest.main()
