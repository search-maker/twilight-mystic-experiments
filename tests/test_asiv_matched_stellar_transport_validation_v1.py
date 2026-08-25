from __future__ import annotations

import importlib.util
import json
import math
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "review/asiv-matched-stellar-transport-v1/assemble_validate_matched_stellar_v1.py"
CONTRACT = ROOT / "review/asiv-matched-stellar-transport-v1/EXECUTION_TRANSPORT_CONTRACT.review.json"


def load_validator():
    spec = importlib.util.spec_from_file_location("asiv_matched_stellar_validation", VALIDATOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def synthetic_pickles_bundle():
    templates = []
    for number in range(1, 132):
        color = 1.0
        if number in (1, 2):
            color = -0.3
        elif number == 64:
            color = 0.64
        elif number == 65:
            color = 0.66
        elif number in (130, 131):
            color = 2.0
        templates.append({
            "templateId": f"synthetic:{number}",
            "libraryNumber": number,
            "spectralType": f"T{number}",
            "colorCalibrationSpectralType": f"T{number}",
            "spectralTypeLabelAgreement": True,
            "abundance": "normal",
            "bMinusVLandoltBmVc": color,
            "fluxRelative": [1.0] * 401,
        })
    return {
        "schemaVersion": 1,
        "quantity": "relative-stellar-f-lambda-shape",
        "wavelengthNm": list(range(380, 781)),
        "templates": templates,
    }


class AsivMatchedStellarTransportValidationV1Tests(unittest.TestCase):
    def test_contract_binds_corrected_validator_and_exact_upstream_photometry(self):
        mod = load_validator()
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        bindings = contract["sourceBindings"]
        self.assertEqual(mod.git_blob_sha1(VALIDATOR), bindings["validationAssemblerGitBlobSha1"])
        self.assertEqual(bindings["upstreamPicklesBuilderGitBlobSha1"], "c0c051582f4e4b7b2d7e6d41f19412e4de7b7964")
        self.assertEqual(bindings["upstreamStellarTransmissionGitBlobSha1"], "5a24286395bb7fb3c9aebe30e8291c63a4ba6e75")
        self.assertEqual(bindings["upstreamBrowserJohnsonVCanonicalizationGitBlobSha1"], "c44d34f33fb26dc070b14dde85fe3fdbf01cd4b3")
        self.assertEqual(contract["photometricValidationAssets"]["picklesSedBundleSha256"], mod.EXPECTED_SED_BUNDLE_SHA256)
        self.assertEqual(contract["photometricValidationAssets"]["johnsonVRawAssetSha256"], mod.EXPECTED_JOHNSON_V_RAW_SHA256)

    def test_deterministic_pickles_representative_ties_use_lower_library_number(self):
        mod = load_validator()
        selected = mod.select_three_pickles_representatives(synthetic_pickles_bundle())
        self.assertEqual([row["libraryNumber"] for row in selected], [1, 64, 130])

    def test_johnson_v_preserves_0081_411_to_401_compatibility_semantics(self):
        mod = load_validator()
        raw = {
            "wavelengthNm": list(range(380, 781)),
            "response": [1.0] * 401 + [0.0] * 10,
        }
        wavelength, response = mod.canonicalize_johnson_v_bandpass(raw)
        self.assertEqual(wavelength, [float(value) for value in range(380, 781)])
        self.assertEqual(response, [1.0] * 401)
        raw["response"][-1] = 1e-12
        with self.assertRaises(mod.ValidationRefusal):
            mod.canonicalize_johnson_v_bandpass(raw)

    def test_band_extinction_matches_constant_transmission_ratio(self):
        mod = load_validator()
        wavelength = [float(value) for value in range(380, 781)]
        got = mod.band_extinction_mag(
            wavelength_nm=wavelength,
            flux_relative=[1.0] * 401,
            band_response=[1.0] * 401,
            transmission=[0.5] * 401,
        )
        self.assertAlmostEqual(got, -2.5 * math.log10(0.5), places=14)

    def test_trilinear_tau_matches_0081_coordinate_and_storage_order(self):
        mod = load_validator()
        altitudes = [10.0, 20.0]
        elevations = [0.0, 1000.0]
        aods = [0.1, 0.2]
        spectra = []
        for altitude in altitudes:
            for elevation in elevations:
                for aod in aods:
                    tau = 2.0 / math.sin(math.radians(altitude)) + 0.001 * elevation + 3.0 * aod
                    spectra.append([tau] * 401)
        runtime = {
            "axes": {
                "targetAltitudeDeg": altitudes,
                "observerElevationM": elevations,
                "aod550": aods,
            },
            "directOpticalDepth": spectra,
        }
        altitude = 15.0
        elevation = 400.0
        aod = 0.15
        expected = 2.0 / math.sin(math.radians(altitude)) + 0.001 * elevation + 3.0 * aod
        result = mod.interpolate_optical_depth(
            runtime,
            target_altitude_deg=altitude,
            observer_elevation_m=elevation,
            aod550=aod,
        )
        self.assertEqual(len(result), 401)
        for value in result:
            self.assertAlmostEqual(value, expected, places=13)

    def test_partial_execution_universe_is_refused_before_metrics(self):
        mod = load_validator()
        with self.assertRaisesRegex(mod.ValidationRefusal, "partial results forbidden"):
            mod.classify_complete_case_universe([])

    def test_prefrozen_manifest_has_exact_complete_counts(self):
        mod = load_validator()
        manifest = mod.load_candidate().build_prefrozen_manifest()
        self.assertEqual(manifest["training"]["caseCount"], 2700)
        self.assertEqual(manifest["validation"]["atmosphericCaseCount"], 768)
        self.assertEqual(manifest["validation"]["johnsonVComparisonCount"], 2304)
        self.assertEqual(len(manifest["families"]), 4)

    def test_validator_has_no_solver_or_process_execution_surface(self):
        source = VALIDATOR.read_text(encoding="utf-8")
        self.assertNotIn("import subprocess", source)
        self.assertNotIn("subprocess.", source)
        self.assertNotIn("run_process_group", source)
        self.assertNotIn("Popen(", source)
        self.assertNotIn("os.system", source)
        self.assertIn("REVIEW_ONLY_COMPLETE_SET_VALIDATOR_NOT_EXECUTED", source)


if __name__ == "__main__":
    unittest.main()
