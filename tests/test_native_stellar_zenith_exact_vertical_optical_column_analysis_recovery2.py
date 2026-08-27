import importlib.util
import math
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "review/native-stellar-zenith-v3/analyze_exact_vertical_optical_column_recovery2.py"
spec = importlib.util.spec_from_file_location("exact_vertical_optical_column_analysis_recovery2", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


class ExactVerticalOpticalColumnAnalysisRecovery2Tests(unittest.TestCase):
    @staticmethod
    def _dense_stdout(offset=0.0):
        rows = []
        for i in range(module.DENSE_ROW_COUNT):
            wavelength = module.DENSE_START_NM + module.DENSE_STEP_NM * i
            transmission = 0.4 + 0.00005 * i + offset
            rows.append(f"{wavelength:.3f} {transmission:.9e}\n")
        return "".join(rows)

    @staticmethod
    def _stderr_flux(delta=0.0):
        rows = []
        for iv in range(module.INTEGER_NODE_COUNT):
            dense_index = iv * 20
            wavelength = 380 + iv
            transmission = 0.4 + 0.00005 * dense_index + delta
            rows.append(
                f"  iv = {iv}, {float(wavelength):.6f} nm, iq = 0, "
                f"flux_dir[lu=0] = {transmission:.9e}, flux_dn[lu=0] = 0.0, "
                "flux_up[lu=0] = 0.0, weight_r = 1.0000000e+00\n"
            )
        return "".join(rows)

    def test_source_identity_and_original_gates_are_frozen(self):
        self.assertEqual(module.SOURCE_RUN_ID, 33041069040)
        self.assertEqual(module.SOURCE_DISPATCH_SHA, "ac4a1230fd3ceb500019f5188173fb8f7165f5ec")
        self.assertEqual(module.SOURCE_ARTIFACT_ID, 9633879569)
        self.assertEqual(
            module.SOURCE_ARTIFACT_DIGEST,
            "sha256:eba59cc5d22e1600b0c38809cac29d615dddd0af02b491febae65164c3a1004e",
        )
        self.assertEqual(module.SOURCE_SOLVER_INVOCATION_COUNT, 4)
        self.assertEqual(module.MAX_ABS_DELTA_TAU, 1e-5)
        self.assertEqual(module.MAX_ABS_DELTA_AV_MAG, 1e-4)
        self.assertEqual(module.STDOUT_STDERR_FLUX_TOLERANCE, 1e-7)

    def test_dense_stdout_parser_validates_8001_rows_and_selects_401_integer_nodes(self):
        parsed = module.parse_dense_direct_transmission(self._dense_stdout())
        self.assertEqual(parsed["denseRowCount"], 8001)
        self.assertEqual(parsed["wavelengthNm"], list(range(380, 781)))
        self.assertEqual(len(parsed["directTransmission"]), 401)
        self.assertAlmostEqual(parsed["directTransmission"][0], 0.4, places=12)
        self.assertAlmostEqual(parsed["directTransmission"][1], 0.401, places=12)
        self.assertAlmostEqual(parsed["directOpticalDepth"][0], -math.log(0.4), places=12)

    def test_dense_stdout_parser_fails_closed_on_count_step_or_transmission_drift(self):
        text = self._dense_stdout()
        with self.assertRaises(module.Recovery2Refusal):
            module.parse_dense_direct_transmission("\n".join(text.splitlines()[:-1]))
        lines = text.splitlines()
        lines[123] = "386.151 5.000000000e-01"
        with self.assertRaises(module.Recovery2Refusal):
            module.parse_dense_direct_transmission("\n".join(lines) + "\n")
        lines = text.splitlines()
        lines[50] = "382.500 0.0"
        with self.assertRaises(module.Recovery2Refusal):
            module.parse_dense_direct_transmission("\n".join(lines) + "\n")

    def test_stderr_direct_flux_parser_requires_all_401_final_iq0_nodes(self):
        parsed = module.parse_stderr_direct_flux(self._stderr_flux())
        self.assertEqual(parsed["wavelengthNm"], list(range(380, 781)))
        self.assertEqual(len(parsed["directTransmission"]), 401)
        with self.assertRaises(module.Recovery2Refusal):
            module.parse_stderr_direct_flux("\n".join(self._stderr_flux().splitlines()[:-1]))

    def test_stdout_stderr_crosscheck_passes_below_frozen_tolerance_and_rejects_above(self):
        dense = module.parse_dense_direct_transmission(self._dense_stdout())
        near = module.parse_stderr_direct_flux(self._stderr_flux(delta=5e-8))
        decision = module.crosscheck_selected_stdout_against_stderr(dense, near)
        self.assertTrue(decision["passed"])
        self.assertLessEqual(decision["maxAbsDeltaTransmission"], 1e-7)
        far = module.parse_stderr_direct_flux(self._stderr_flux(delta=2e-7))
        decision = module.crosscheck_selected_stdout_against_stderr(dense, far)
        self.assertFalse(decision["passed"])
        self.assertGreater(decision["maxAbsDeltaTransmission"], 1e-7)

    def test_case_input_identity_and_layer_count_are_derived_from_preserved_input(self):
        text = """data_files_path /data
atmosphere_file /data/afglus.dat
source solar /data/solar_flux/atlas_plus_modtran
mol_abs_param crs
wavelength_grid_file /repo/grid.dat
wavelength 380 780
sza 0.00000000
atm_z_grid 1.250000 2.000000 3.000000 4.000000
zout 0.000000
albedo 0.15000000
aerosol_default
aerosol_set_tau_at_wvl 550 0.10000000
rte_solver disort
number_of_streams 16
output_quantity transmittance
output_user lambda edir
verbose
"""
        parsed = module.parse_case_input(text)
        self.assertEqual(parsed["observerElevationM"], 1250.0)
        self.assertEqual(parsed["aod550"], 0.1)
        self.assertEqual(parsed["expectedLayerCount"], 3)
        self.assertEqual(parsed["atmZGridLevelCount"], 4)

    def test_case_input_refuses_nonexact_zenith_or_solver_drift(self):
        good = """sza 0.00000000
atm_z_grid 0.500000 1.000000
zout 0.000000
aerosol_set_tau_at_wvl 550 0.30000000
rte_solver disort
number_of_streams 16
output_quantity transmittance
output_user lambda edir
"""
        with self.assertRaises(module.Recovery2Refusal):
            module.parse_case_input(good.replace("sza 0.00000000", "sza 0.10000000"))
        with self.assertRaises(module.Recovery2Refusal):
            module.parse_case_input(good.replace("rte_solver disort", "rte_solver sdisort"))

    def test_source_recovery_summary_requires_exact_dense_parser_failure_boundary(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            data = {
                "stageId": "native-stellar-zenith-exact-vertical-optical-column-recovery1",
                "status": "EXACT_VERTICAL_OPTICAL_COLUMN_DIAGNOSTIC_FAIL",
                "solverInvocationCount": 4,
                "successfulParsedCaseCount": 0,
                "failures": [
                    {"failure": "non-integral wavelength in 1-nm output"}
                    for _ in range(4)
                ],
            }
            path = root / "exact-vertical-optical-column-recovery1-summary.json"
            import json
            path.write_text(json.dumps(data), encoding="utf-8")
            result = module.validate_source_recovery_summary(root)
            self.assertEqual(result["solverInvocationCount"], 4)
            data["failures"][0]["failure"] = "different failure"
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(module.Recovery2Refusal):
                module.validate_source_recovery_summary(root)

    def test_equal_401_node_columns_have_zero_original_scientific_metrics(self):
        tau = [0.1 + 0.0001 * i for i in range(401)]
        result = module.v1.evaluate_case(
            root=ROOT,
            parsed_direct={"wavelengthNm": list(range(380, 781)), "directOpticalDepth": tau},
            parsed_verbose={"wavelengthNm": list(range(380, 781)), "verboseColumnOpticalDepth": list(tau)},
            sed_bundle_path=ROOT / "review/asiv-matched-stellar-transport-v1/frozen-assets/pickles-sed-1nm.json",
            johnson_v_path=ROOT / "review/asiv-matched-stellar-transport-v1/frozen-assets/johnson-v-1nm.json",
        )
        self.assertEqual(result["maxAbsDeltaOpticalDepth"], 0.0)
        self.assertEqual(result["maxAbsDeltaAvMag"], 0.0)
        self.assertTrue(result["spectralOpticalColumnPassed"])
        self.assertTrue(result["johnsonVConsequencePassed"])

    def test_recovery2_source_contains_no_solver_execution_api(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn("subprocess", source)
        self.assertNotIn("run_uvspec", source)
        self.assertNotIn("execute_campaign(", source)
        self.assertNotIn("rte_solver ", source)


if __name__ == "__main__":
    unittest.main()
