from __future__ import annotations

import importlib.util
import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "review/native-stellar-zenith-v3/native_stellar_zenith_v32.py"


def load_module():
    spec = importlib.util.spec_from_file_location("native_stellar_zenith_v32_tested", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load v3.2 module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


m = load_module()


class NativeStellarZenithV32Tests(unittest.TestCase):
    def _atmosphere(self, root: Path) -> Path:
        path = root / "afglus.dat"
        path.write_text(
            "120.0 1\n80.0 1\n50.0 1\n25.0 1\n10.0 1\n5.0 1\n2.5 1\n1.25 1\n0.5 1\n0.0 1\n",
            encoding="utf-8",
        )
        return path

    def _source_runtime(self):
        return {
            "schemaVersion": 1,
            "quantity": "level-b-stellar-direct-optical-depth-lut",
            "axes": {
                "targetAltitudeDeg": list(m.OLD_ALTITUDE_KNOTS),
                "observerElevationM": list(m.ELEVATION_KNOTS_M),
                "aod550": list(m.AOD_KNOTS),
            },
            "wavelengthNm": list(m.WAVELENGTH_NM),
            "directOpticalDepth": [[0.1] * 401 for _ in range(675)],
            "representation": {"version": "stellar-transport-v2"},
            "provenance": {"productionAuthorized": False},
        }

    def _training_results(self):
        results = {}
        for row in m.build_training_cases():
            exact = m.is_exact_zenith(row["targetAltitudeDeg"])
            key = m._coord_key(row["targetAltitudeDeg"], row["observerElevationM"], row["aod550"])
            results[key] = {
                **row,
                "wavelengthNm": list(m.WAVELENGTH_NM),
                "directOpticalDepth": [0.2 if exact else 0.15] * 401,
                "lineOfSightDirectTransmission": [math.exp(-(0.2 if exact else 0.15))] * 401,
                "endpointMethod": (
                    "EXACT_VERTICAL_DISORT_RESOLVED_OPTICAL_COLUMN_V1"
                    if exact else "SDISORT_V3_UNCHANGED"
                ),
            }
        return results

    def test_frozen_universe_is_100_training_25_exact_75_sdisort_64_holdout(self):
        m.validate_frozen_case_universe()
        training = m.build_training_cases()
        holdout = m.build_validation_cases()
        self.assertEqual(len(training), 100)
        self.assertEqual(sum(m.is_exact_zenith(r["targetAltitudeDeg"]) for r in training), 25)
        self.assertEqual(sum(not m.is_exact_zenith(r["targetAltitudeDeg"]) for r in training), 75)
        self.assertEqual(len(holdout), 64)
        self.assertTrue(all(r["targetAltitudeDeg"] < 90.0 for r in holdout))
        self.assertEqual(m.VALIDATION_ALTITUDE_DEG, (80.9375, 83.4375, 85.9375, 88.4375))
        self.assertEqual(m.MAX_ABS_ERROR_MAG_LIMIT, 0.025)
        self.assertEqual(m.RMS_ERROR_MAG_LIMIT, 0.010)

    def test_proof_binding_is_exact_official_pass(self):
        m.validate_proof_binding()
        self.assertEqual(m.EXACT_VERTICAL_ANALYSIS_RUN_ID, 33041830554)
        self.assertEqual(m.EXACT_VERTICAL_ANALYSIS_DISPATCH_SHA, "bdac3f0f03f1d2c63d274076365f1f3331a8b68e")
        self.assertEqual(m.EXACT_VERTICAL_ANALYSIS_ARTIFACT_ID, 9634148868)
        self.assertEqual(
            m.EXACT_VERTICAL_ANALYSIS_ARTIFACT_DIGEST,
            "sha256:aa5b0b4a5b705bdcefd29c35113f331aa667b8dca9a2b228d44aa52ec864ca78",
        )
        self.assertLessEqual(m.EXACT_VERTICAL_PROOF_MAX_ABS_DELTA_TAU, 1e-5)
        self.assertLessEqual(m.EXACT_VERTICAL_PROOF_MAX_ABS_DELTA_AV_MAG, 1e-4)
        self.assertLessEqual(m.EXACT_VERTICAL_PROOF_MAX_DIRECT_FLUX_CROSSCHECK, 1e-7)

    def test_below_90_renderer_is_byte_for_byte_v3(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            atmosphere = self._atmosphere(root)
            data = root / "data"
            grid = root / "grid.dat"
            for altitude, elevation, aod in (
                (82.5, 0.0, 0.05),
                (85.0, 1250.0, 0.20),
                (87.5, 2500.0, 0.40),
                (88.4375, 781.25, 0.1375),
            ):
                expected = m.base.render_uvspec_input(
                    data_dir=data,
                    atmosphere_file=atmosphere,
                    wavelength_grid_file=grid,
                    target_altitude_deg=altitude,
                    observer_elevation_m=elevation,
                    aod550=aod,
                )
                actual = m.render_uvspec_input(
                    data_dir=data,
                    atmosphere_file=atmosphere,
                    wavelength_grid_file=grid,
                    target_altitude_deg=altitude,
                    observer_elevation_m=elevation,
                    aod550=aod,
                )
                self.assertEqual(actual, expected)

    def test_exact_90_renderer_is_disort_vertical_column_not_epsilon_or_sdisort(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            atmosphere = self._atmosphere(root)
            text = m.render_uvspec_input(
                data_dir=root / "data",
                atmosphere_file=atmosphere,
                wavelength_grid_file=root / "grid.dat",
                target_altitude_deg=90.0,
                observer_elevation_m=1250.0,
                aod550=0.30,
            )
        self.assertIn("sza 0.00000000\n", text)
        self.assertIn("rte_solver disort\n", text)
        self.assertIn("number_of_streams 16\n", text)
        self.assertIn("verbose\n", text)
        self.assertIn("source solar ", text)
        self.assertIn("atlas_plus_modtran", text)
        self.assertNotIn("rte_solver sdisort", text)
        self.assertNotIn("sdisort nscat", text)
        self.assertNotIn("rte_solver mystic", text)
        self.assertNotIn("mc_", text.lower())
        self.assertNotIn("sza 0.001", text)

    def test_exact_90_renderer_accepts_all_25_frozen_training_axis_states(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            atmosphere = self._atmosphere(root)
            for elevation in m.ELEVATION_KNOTS_M:
                for aod in m.AOD_KNOTS:
                    text = m.render_uvspec_input(
                        data_dir=root / "data",
                        atmosphere_file=atmosphere,
                        wavelength_grid_file=root / "grid.dat",
                        target_altitude_deg=90.0,
                        observer_elevation_m=elevation,
                        aod550=aod,
                    )
                    self.assertIn(f"aerosol_set_tau_at_wvl 550 {aod:.8f}", text)

    def test_exact_90_renderer_refuses_nontraining_elevation_or_aod(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            atmosphere = self._atmosphere(root)
            with self.assertRaises(m.ZenithV32Refusal):
                m.render_uvspec_input(
                    data_dir=root / "data", atmosphere_file=atmosphere,
                    wavelength_grid_file=root / "grid.dat", target_altitude_deg=90.0,
                    observer_elevation_m=600.0, aod550=0.20,
                )
            with self.assertRaises(m.ZenithV32Refusal):
                m.render_uvspec_input(
                    data_dir=root / "data", atmosphere_file=atmosphere,
                    wavelength_grid_file=root / "grid.dat", target_altitude_deg=90.0,
                    observer_elevation_m=500.0, aod550=0.15,
                )

    def test_below_90_parser_is_identical_to_v3(self):
        altitude = 87.5
        mu0 = math.sin(math.radians(altitude))
        stdout = "".join(f"{w} {0.8 * mu0:.12f}\n" for w in m.WAVELENGTH_NM)
        expected = m.base.parse_direct_transmission(stdout, target_altitude_deg=altitude)
        actual = m.parse_case_outputs(
            stdout_text=stdout, stderr_text="ignored", target_altitude_deg=altitude
        )
        self.assertEqual(actual["wavelengthNm"], expected["wavelengthNm"])
        self.assertEqual(actual["lineOfSightDirectTransmission"], expected["lineOfSightDirectTransmission"])
        self.assertEqual(actual["directOpticalDepth"], expected["directOpticalDepth"])
        self.assertEqual(actual["endpointMethod"], "SDISORT_V3_UNCHANGED")
        self.assertFalse(actual["exactVerticalOpticalColumnEndpointApplied"])

    def test_exact_90_parser_uses_verbose_layer_sum_and_ignores_stdout_as_estimator(self):
        tau = [0.2 + i * 1e-6 for i in range(401)]
        parsed_verbose = {
            "wavelengthNm": list(m.WAVELENGTH_NM),
            "verboseColumnOpticalDepth": tau,
            "layerCountByWavelength": [48] * 401,
        }
        with mock.patch.object(m.vertical, "parse_verbose_optical_columns", return_value=parsed_verbose) as parser:
            actual = m.parse_case_outputs(
                stdout_text="THIS DENSE STDOUT IS NOT THE ENDPOINT ESTIMATOR\n",
                stderr_text="frozen verbose evidence",
                target_altitude_deg=90.0,
                expected_layer_count_value=48,
            )
        parser.assert_called_once()
        self.assertEqual(actual["directOpticalDepth"], tau)
        self.assertEqual(actual["lineOfSightDirectTransmission"], [math.exp(-x) for x in tau])
        self.assertEqual(actual["endpointMethod"], "EXACT_VERTICAL_DISORT_RESOLVED_OPTICAL_COLUMN_V1")
        self.assertTrue(actual["exactVerticalOpticalColumnEndpointApplied"])
        self.assertFalse(actual["stdoutDirectSpectrumUsedAsEstimator"])
        self.assertEqual(actual["mu0"], 1.0)
        self.assertEqual(actual["sourceZenithAngleDeg"], 0.0)

    def test_exact_90_parser_requires_layer_count(self):
        with self.assertRaises(m.ZenithV32Refusal):
            m.parse_case_outputs(
                stdout_text="", stderr_text="", target_altitude_deg=90.0,
                expected_layer_count_value=None,
            )

    def test_build_extended_runtime_preserves_old_675_and_binds_endpoint_proof(self):
        source = self._source_runtime()
        old = json.loads(json.dumps(source["directOpticalDepth"]))
        runtime = m.build_extended_runtime(source, self._training_results())
        self.assertEqual(runtime["directOpticalDepth"][:675], old)
        self.assertEqual(len(runtime["directOpticalDepth"]), 775)
        self.assertEqual(runtime["axes"]["targetAltitudeDeg"][-4:], [82.5, 85.0, 87.5, 90.0])
        self.assertEqual(runtime["representation"]["version"], m.METHOD_VERSION)
        self.assertFalse(runtime["representation"]["positiveEpsilonSubstitutionUsed"])
        self.assertEqual(runtime["provenance"]["exactVerticalOpticalColumnTrainingSpectrumCount"], 25)
        self.assertEqual(runtime["provenance"]["belowZenithSdisortTrainingSpectrumCount"], 75)
        self.assertEqual(runtime["provenance"]["exactVerticalAnalysisRunId"], 33041830554)
        self.assertFalse(runtime["provenance"]["productionAuthorized"])

    def test_build_runtime_refuses_wrong_endpoint_provenance(self):
        source = self._source_runtime()
        results = self._training_results()
        exact_key = next(key for key, value in results.items() if value["targetAltitudeDeg"] == 90.0)
        results[exact_key]["endpointMethod"] = "SDISORT_V3_UNCHANGED"
        with self.assertRaises(m.ZenithV32Refusal):
            m.build_extended_runtime(source, results)

    def test_holdout_validation_requires_unchanged_sdisort_reference_method(self):
        validation_results = {}
        for row in m.build_validation_cases():
            validation_results[m._coord_key(row["targetAltitudeDeg"], row["observerElevationM"], row["aod550"])] = {
                **row,
                "endpointMethod": "SDISORT_V3_UNCHANGED",
            }
        fake = {
            "schemaVersion": 1,
            "stageId": "native-stellar-zenith-v3",
            "status": "COMPUTATIONAL_REFERENCE_VALIDATION_PASS",
            "interpolation": "old",
            "newTrainingSolverSpectrumCount": 100,
            "freshValidationAtmosphericSpectrumCount": 64,
            "johnsonVComparisonCount": 192,
            "overall": {"maxAbsDeltaAvMag": 0.001, "rmsDeltaAvMag": 0.0005, "passed": True},
            "byValidationAltitudeDeg": {str(h): {"passed": True} for h in m.VALIDATION_ALTITUDE_DEG},
            "claimBoundary": {"productionAuthorized": False},
        }
        with mock.patch.object(m.base, "validate_against_fresh_holdout", return_value=fake):
            result = m.validate_against_fresh_holdout(
                root=ROOT,
                extended_runtime={},
                validation_results=validation_results,
                sed_bundle_path=Path("sed"),
                johnson_v_path=Path("v"),
            )
        self.assertEqual(result["stageId"], m.STAGE_ID)
        self.assertEqual(result["protectedHoldoutSdisortSpectrumCount"], 64)
        self.assertTrue(result["exactVerticalEndpointProof"]["passed"])
        self.assertFalse(result["claimBoundary"]["positiveEpsilonSubstitutionUsed"])
        self.assertFalse(result["claimBoundary"]["productionAuthorized"])

    def test_holdout_validation_refuses_endpoint_method_drift(self):
        validation_results = {}
        for row in m.build_validation_cases():
            validation_results[m._coord_key(row["targetAltitudeDeg"], row["observerElevationM"], row["aod550"])] = {
                **row,
                "endpointMethod": "SDISORT_V3_UNCHANGED",
            }
        first_key = next(iter(validation_results))
        validation_results[first_key]["endpointMethod"] = "EXACT_VERTICAL_DISORT_RESOLVED_OPTICAL_COLUMN_V1"
        with self.assertRaises(m.ZenithV32Refusal):
            m.validate_against_fresh_holdout(
                root=ROOT,
                extended_runtime={},
                validation_results=validation_results,
                sed_bundle_path=Path("sed"),
                johnson_v_path=Path("v"),
            )

    def test_execute_campaign_fails_closed_without_explicit_authorization(self):
        with self.assertRaises(m.ZenithV32Refusal):
            m.execute_campaign(
                root=ROOT,
                source_runtime_path=Path("missing"),
                uvspec=Path("missing"),
                data_dir=Path("missing"),
                atmosphere_file=Path("missing"),
                wavelength_grid_file=Path("missing"),
                sed_bundle_path=Path("missing"),
                johnson_v_path=Path("missing"),
                output_dir=Path("missing"),
                allow_execution=False,
            )

    def test_review_summary_never_authorizes_holdout_or_production(self):
        summary = m.review_summary()
        self.assertEqual(summary["status"], "REVIEW_ONLY_NO_SOLVER_EXECUTION")
        self.assertEqual(summary["trainingSpectrumCount"], 100)
        self.assertEqual(summary["exactVerticalTrainingSpectrumCount"], 25)
        self.assertEqual(summary["protectedHoldoutSpectrumCount"], 64)
        self.assertFalse(summary["protectedHoldoutOpeningAuthorizedByReviewModule"])
        self.assertFalse(summary["productionAuthorized"])
        self.assertFalse(summary["positiveEpsilonSubstitutionUsed"])


if __name__ == "__main__":
    unittest.main()
