import importlib.util
import hashlib
import json
import math
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "review/native-stellar-zenith-v3/native_stellar_zenith_v32.py"
spec = importlib.util.spec_from_file_location("native_stellar_zenith_v32_endpoint_training", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


class NativeStellarZenithV32EndpointTrainingTests(unittest.TestCase):
    def _atmosphere(self, root: Path) -> Path:
        path = root / "afglus-test.dat"
        path.write_text("120 1\n10 1\n4 1\n3 1\n2 1\n1 1\n0 1\n", encoding="utf-8")
        return path

    def _grid(self, root: Path) -> Path:
        path = root / "grid.dat"
        path.write_text("".join(f"{w}\n" for w in range(380, 781)), encoding="utf-8")
        return path

    def test_frozen_training_composition_and_holdout_boundary(self):
        module.validate_frozen_training_universe()
        self.assertEqual(module.REUSED_ALTITUDE_DEG, (82.5, 85.0, 87.5))
        self.assertEqual(len(module.reused_training_coordinates()), 75)
        self.assertEqual(len(module.exact90_training_cases()), 25)
        self.assertEqual(module.base.VALIDATION_ALTITUDE_DEG, (80.9375, 83.4375, 85.9375, 88.4375))
        self.assertEqual(module.MAX_ABS_DELTA_TAU, 1e-5)
        self.assertEqual(module.MAX_ABS_DELTA_AV_MAG, 1e-4)
        self.assertEqual(module.STDOUT_STDERR_FLUX_TOLERANCE, 1e-7)

    def test_source_artifact_and_endpoint_validation_identities_are_frozen(self):
        self.assertEqual(module.SOURCE_V31_RUN_ID, 33035467761)
        self.assertEqual(module.SOURCE_V31_DISPATCH_SHA, "2a6f6eadb003ea70c99e0c306f232a6233650a0e")
        self.assertEqual(module.SOURCE_V31_ARTIFACT_ID, 9631872858)
        self.assertEqual(
            module.SOURCE_V31_ARTIFACT_DIGEST,
            "sha256:dd8cbf6c00fdcf34041fb61e43d0f97d43646a5d2bdaf5a2ef899ed1a40f078b",
        )
        self.assertEqual(module.EXACT_VERTICAL_VALIDATION_RUN_ID, 33041830554)
        self.assertEqual(module.EXACT_VERTICAL_VALIDATION_ARTIFACT_ID, 9634148868)
        self.assertEqual(
            module.EXACT_VERTICAL_VALIDATION_ARTIFACT_DIGEST,
            "sha256:aa5b0b4a5b705bdcefd29c35113f331aa667b8dca9a2b228d44aa52ec864ca78",
        )

    def test_exact90_renderer_is_exact_vertical_disort_only(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            atmosphere = self._atmosphere(root)
            grid = self._grid(root)
            text = module.render_exact90_input(
                data_dir=root / "data",
                atmosphere_file=atmosphere,
                wavelength_grid_file=grid,
                observer_elevation_m=1250.0,
                aod550=0.30,
            )
        self.assertIn("sza 0.00000000", text)
        self.assertIn("rte_solver disort", text)
        self.assertIn("number_of_streams 16", text)
        self.assertIn("source solar ", text)
        self.assertIn("solar_flux/atlas_plus_modtran", text)
        self.assertIn("output_quantity transmittance", text)
        self.assertIn("output_user lambda edir", text)
        self.assertIn("verbose", text)
        self.assertIn("atm_z_grid 1.250000", text)
        self.assertIn("zout 0.000000", text)
        for forbidden in (
            "rte_solver sdisort", "sdisort nscat", "rte_solver mystic", "mc_",
            "write_optical_properties", "mc_elevation_file",
        ):
            self.assertNotIn(forbidden, text.lower())

    def test_exact90_renderer_refuses_nontraining_atmosphere_coordinate(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            atmosphere = self._atmosphere(root)
            grid = self._grid(root)
            with self.assertRaises(module.ZenithV32Refusal):
                module.render_exact90_input(
                    data_dir=root,
                    atmosphere_file=atmosphere,
                    wavelength_grid_file=grid,
                    observer_elevation_m=750.0,
                    aod550=0.30,
                )

    def test_exact_vertical_validation_summary_must_be_pass_and_preserve_claim_boundary(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            good = {
                "stageId": module.ev_r2.STAGE_ID,
                "status": "EXACT_VERTICAL_OPTICAL_COLUMN_ANALYSIS_RECOVERY2_PASS",
                "parserEvidenceGate": {
                    "passed": True,
                    "maxStdoutStderrDirectFluxAbsDelta": 5e-8,
                },
                "scientificGates": {
                    "spectralOpticalColumnPassed": True,
                    "maxAbsDeltaOpticalDepth": 8e-6,
                    "johnsonVConsequencePassed": True,
                    "maxAbsDeltaAvMag": 2e-6,
                },
                "claimBoundary": {
                    "protectedHoldoutOpened": False,
                    "productionAuthorized": False,
                },
            }
            path = root / "exact-vertical-optical-column-analysis-recovery2-summary.json"
            path.write_text(json.dumps(good), encoding="utf-8")
            result = module.validate_exact_vertical_validation_artifact(root)
            self.assertEqual(result["status"], "EXACT_VERTICAL_OPTICAL_COLUMN_ANALYSIS_RECOVERY2_PASS")
            good["scientificGates"]["maxAbsDeltaOpticalDepth"] = 2e-5
            path.write_text(json.dumps(good), encoding="utf-8")
            with self.assertRaises(module.ZenithV32Refusal):
                module.validate_exact_vertical_validation_artifact(root)

    @staticmethod
    def _synthetic_source_runtime():
        spectra = []
        for h in module.base.OLD_ALTITUDE_KNOTS:
            for e in module.ELEVATION_KNOTS_M:
                for a in module.AOD_KNOTS:
                    tau = 0.05 + 0.4 * a + 0.00001 * e + 0.2 * module.base.csc_altitude(h)
                    spectra.append([tau + 1e-5 * i for i in range(401)])
        return {
            "schemaVersion": 1,
            "quantity": "level-b-stellar-direct-optical-depth-lut",
            "axes": {
                "targetAltitudeDeg": list(module.base.OLD_ALTITUDE_KNOTS),
                "observerElevationM": list(module.ELEVATION_KNOTS_M),
                "aod550": list(module.AOD_KNOTS),
            },
            "wavelengthNm": list(range(380, 781)),
            "directOpticalDepth": spectra,
            "representation": {},
            "provenance": {},
        }

    @staticmethod
    def _synthetic_training():
        reused = {}
        exact = {}
        for h in module.REUSED_ALTITUDE_DEG:
            for e in module.ELEVATION_KNOTS_M:
                for a in module.AOD_KNOTS:
                    # Exactly linear in csc altitude, so the 90 endpoint is a smooth limit.
                    tau = [0.03 + 0.3 * a + 0.000005 * e + 0.18 * module.base.csc_altitude(h) + 1e-5 * i for i in range(401)]
                    reused[module.coord_key(h, e, a)] = {"directOpticalDepth": tau}
        for e in module.ELEVATION_KNOTS_M:
            for a in module.AOD_KNOTS:
                tau = [0.03 + 0.3 * a + 0.000005 * e + 0.18 + 1e-5 * i for i in range(401)]
                exact[module.coord_key(90.0, e, a)] = {"directOpticalDepth": tau}
        return reused, exact

    def test_v32_runtime_assembles_exact_775_spectra_and_preserves_old_675(self):
        source = self._synthetic_source_runtime()
        reused, exact = self._synthetic_training()
        runtime = module.build_v32_training_runtime(source, reused, exact)
        self.assertEqual(len(runtime["directOpticalDepth"]), 775)
        self.assertEqual(runtime["directOpticalDepth"][:675], source["directOpticalDepth"])
        self.assertEqual(runtime["axes"]["targetAltitudeDeg"][-4:], [82.5, 85.0, 87.5, 90.0])
        p = runtime["provenance"]
        self.assertEqual(p["reusedNonZenithTrainingSpectrumCount"], 75)
        self.assertEqual(p["newExactZenithTrainingSpectrumCount"], 25)
        self.assertFalse(p["tiltedSdisortDisortInterchangeabilityClaimed"])
        self.assertFalse(p["epsilonApproximationUsedAtExactZenith"])
        self.assertFalse(p["protectedHoldoutOpened"])

    def test_structural_seam_passes_for_smooth_training_and_reproduces_both_knots(self):
        source = self._synthetic_source_runtime()
        reused, exact = self._synthetic_training()
        runtime = module.build_v32_training_runtime(source, reused, exact)
        training = dict(reused); training.update(exact)
        seam = module.structural_seam_validation(runtime, source, training)
        self.assertTrue(seam["passed"])
        self.assertEqual(seam["status"], "V32_TRAINING_STRUCTURAL_SEAM_PASS")
        self.assertLessEqual(seam["maxKnotReproductionAbsDeltaOpticalDepth"], 1e-12)
        self.assertEqual(seam["endpointOrderingViolationCount"], 0)
        self.assertEqual(seam["overshootViolationCount"], 0)
        self.assertEqual(seam["nonfiniteOrNegativeCount"], 0)
        self.assertFalse(
            seam["diagnosticOnlyExact90VsCscExtrapolationFrom85And87p5"]["acceptanceThresholdApplied"]
        )

    def test_structural_seam_rejects_physical_endpoint_order_reversal(self):
        source = self._synthetic_source_runtime()
        reused, exact = self._synthetic_training()
        # Add enough extinction at exact zenith to violate tau90 <= tau87.5.
        key = module.coord_key(90.0, 0.0, 0.05)
        exact[key] = {"directOpticalDepth": [x + 0.01 for x in exact[key]["directOpticalDepth"]]}
        runtime = module.build_v32_training_runtime(source, reused, exact)
        training = dict(reused); training.update(exact)
        seam = module.structural_seam_validation(runtime, source, training)
        self.assertFalse(seam["passed"])
        self.assertGreater(seam["endpointOrderingViolationCount"], 0)

    def test_execution_is_inert_without_explicit_authorization(self):
        with self.assertRaisesRegex(module.ZenithV32Refusal, "allow_execution=True"):
            module.execute_campaign(
                root=Path("."),
                source_runtime_path=Path("missing"),
                source_v31_root=Path("missing"),
                exact_vertical_validation_root=Path("missing"),
                uvspec=Path("missing"),
                data_dir=Path("missing"),
                atmosphere_file=Path("missing"),
                wavelength_grid_file=Path("missing"),
                sed_bundle_path=Path("missing"),
                johnson_v_path=Path("missing"),
                output_dir=Path("missing"),
                allow_execution=False,
            )

    def test_module_does_not_call_protected_holdout_builder(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn("build_validation_cases(", source)
        self.assertNotIn("validate_against_fresh_holdout(", source)
        self.assertNotIn("88.4375", source)


if __name__ == "__main__":
    unittest.main()
