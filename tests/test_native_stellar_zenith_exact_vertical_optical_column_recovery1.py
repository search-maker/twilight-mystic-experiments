import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "review/native-stellar-zenith-v3/diagnose_exact_vertical_optical_column_recovery1.py"
spec = importlib.util.spec_from_file_location("exact_vertical_optical_column_recovery1", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


class ExactVerticalOpticalColumnRecovery1Tests(unittest.TestCase):
    def _atmosphere(self, root: Path) -> Path:
        path = root / "afglus-test.dat"
        path.write_text("120 1\n10 1\n2 1\n1 1\n0 1\n", encoding="utf-8")
        return path

    def _grid(self, root: Path) -> Path:
        path = root / "repo" / "experiments" / "aerosol-family-challenge-v2-r8" / "wavelength-grid-1nm.dat"
        path.parent.mkdir(parents=True)
        path.write_text("".join(f"{value}\n" for value in range(380, 781)), encoding="utf-8")
        return path

    def test_frozen_prior_failure_identity(self):
        self.assertEqual(module.PRIOR_RUN_ID, 33040457601)
        self.assertEqual(module.PRIOR_ARTIFACT_ID, 9633642762)
        self.assertEqual(
            module.PRIOR_ARTIFACT_DIGEST,
            "sha256:f2f6f5b0d33518a48d36312b7f4bf18bea4ae22e1ce5fba2e80775c6b063332f",
        )
        self.assertEqual(
            module.PRIOR_DISPATCH_SHA,
            "2663fbc3241b31e095f3fb814cecc5a60e078c0a",
        )
        self.assertEqual(
            module.FAILURE_CLASS,
            "PRE_SOLVER_WAVELENGTH_GRID_RELATIVE_PATH_NOT_FOUND",
        )

    def test_exact_grid_validation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            grid = self._grid(root)
            self.assertEqual(module.read_exact_grid(grid), list(range(380, 781)))
            grid.write_text("380\n381\n383\n", encoding="utf-8")
            with self.assertRaises(module.RecoveryRefusal):
                module.read_exact_grid(grid)

    def test_resolved_grid_is_same_bytes_and_absolute(self):
        with tempfile.TemporaryDirectory() as td:
            grid = self._grid(Path(td))
            resolved = module.resolve_same_grid(grid)
            self.assertTrue(resolved.is_absolute())
            self.assertEqual(grid.read_bytes(), resolved.read_bytes())
            self.assertEqual(resolved, grid.resolve())

    def test_renderer_diff_is_exactly_wavelength_grid_path(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = root / "repo"
            grid_abs = self._grid(root)
            atmosphere = self._atmosphere(root)
            old_cwd = Path.cwd()
            try:
                os.chdir(repo)
                relative_grid = Path("experiments/aerosol-family-challenge-v2-r8/wavelength-grid-1nm.dat")
                proof = module.render_pair(
                    observer_elevation_m=500.0,
                    aod550=0.30,
                    data_dir=root / "data",
                    atmosphere_file=atmosphere,
                    wavelength_grid_file=relative_grid,
                )
            finally:
                os.chdir(old_cwd)
            self.assertEqual(proof["originalGridPath"], "experiments/aerosol-family-challenge-v2-r8/wavelength-grid-1nm.dat")
            self.assertEqual(Path(proof["resolvedGridPath"]), grid_abs.resolve())
            self.assertGreaterEqual(proof["differenceLineIndexZeroBased"], 0)
            original = proof["originalInput"].splitlines()
            recovery = proof["recoveryInput"].splitlines()
            diffs = [(a, b) for a, b in zip(original, recovery, strict=True) if a != b]
            self.assertEqual(len(diffs), 1)
            self.assertTrue(diffs[0][0].startswith("wavelength_grid_file "))
            self.assertTrue(diffs[0][1].startswith("wavelength_grid_file /"))

    def test_relative_path_breaks_from_case_cwd_absolute_path_does_not(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = root / "repo"
            grid = self._grid(root)
            case_dir = repo / "diagnostic-output" / "raw" / "case"
            case_dir.mkdir(parents=True)
            relative = Path("experiments/aerosol-family-challenge-v2-r8/wavelength-grid-1nm.dat")
            old_cwd = Path.cwd()
            try:
                os.chdir(case_dir)
                self.assertFalse(relative.is_file())
                self.assertTrue(grid.resolve().is_file())
            finally:
                os.chdir(old_cwd)

    def test_recovery_surface_preserves_all_four_cases_and_thresholds(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = root / "repo"
            self._grid(root)
            atmosphere = self._atmosphere(root)
            old_cwd = Path.cwd()
            try:
                os.chdir(repo)
                proof = module.validate_recovery_surface(
                    data_dir=root / "data",
                    atmosphere_file=atmosphere,
                    wavelength_grid_file=Path("experiments/aerosol-family-challenge-v2-r8/wavelength-grid-1nm.dat"),
                )
            finally:
                os.chdir(old_cwd)
            self.assertEqual(len(proof["caseProofs"]), 4)
            self.assertFalse(proof["scientificInputsChanged"])
            self.assertFalse(proof["acceptanceThresholdsChanged"])
            self.assertFalse(proof["protectedHoldoutOpened"])
            self.assertEqual(module.v1.MAX_ABS_DELTA_TAU, 1e-5)
            self.assertEqual(module.v1.MAX_ABS_DELTA_AV_MAG, 1e-4)

    def test_execute_recovery_passes_only_resolved_grid_to_immutable_v1(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = root / "repo"
            grid = self._grid(root)
            atmosphere = self._atmosphere(root)
            output = repo / "out"
            old_cwd = Path.cwd()
            try:
                os.chdir(repo)
                relative = Path("experiments/aerosol-family-challenge-v2-r8/wavelength-grid-1nm.dat")
                fake_result = {
                    "schemaVersion": 1,
                    "stageId": module.v1.STAGE_ID,
                    "status": "EXACT_VERTICAL_OPTICAL_COLUMN_DIAGNOSTIC_PASS",
                    "solverInvocationCount": 4,
                    "metrics": {"maxAbsDeltaOpticalDepth": 0.0, "maxAbsDeltaAvMag": 0.0},
                    "claimBoundary": {
                        "protectedHoldoutOpened": False,
                        "modelFitPerformed": False,
                        "productionAuthorized": False,
                    },
                }
                with mock.patch.object(module.v1, "execute_campaign", return_value=fake_result) as call:
                    result = module.execute_recovery(
                        root=repo,
                        uvspec=Path("/tmp/uvspec"),
                        data_dir=root / "data",
                        atmosphere_file=atmosphere,
                        wavelength_grid_file=relative,
                        sed_bundle_path=Path("/tmp/sed"),
                        johnson_v_path=Path("/tmp/v"),
                        output_dir=output,
                        allow_execution=True,
                    )
            finally:
                os.chdir(old_cwd)
            kwargs = call.call_args.kwargs
            self.assertTrue(kwargs["wavelength_grid_file"].is_absolute())
            self.assertEqual(kwargs["wavelength_grid_file"], grid.resolve())
            self.assertTrue(kwargs["allow_execution"])
            self.assertEqual(result["stageId"], module.STAGE_ID)
            self.assertEqual(result["recoveryOf"]["runId"], module.PRIOR_RUN_ID)
            self.assertTrue((output / "exact-vertical-optical-column-recovery1-summary.json").is_file())

    def test_execution_fails_closed_without_explicit_authorization(self):
        with self.assertRaises(module.RecoveryRefusal):
            module.execute_recovery(
                root=Path("."),
                uvspec=Path("missing"),
                data_dir=Path("missing"),
                atmosphere_file=Path("missing"),
                wavelength_grid_file=Path("missing"),
                sed_bundle_path=Path("missing"),
                johnson_v_path=Path("missing"),
                output_dir=Path("missing"),
                allow_execution=False,
            )


if __name__ == "__main__":
    unittest.main()
