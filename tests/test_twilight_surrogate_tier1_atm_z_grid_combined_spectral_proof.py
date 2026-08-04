from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    ROOT
    / "experiments"
    / "mystic-batch-v1"
    / "twilight_surrogate_tier1_atm_z_grid_combined_spectral_proof.py"
)
spec = importlib.util.spec_from_file_location(
    "tier1_atm_z_grid_combined_spectral_proof", MODULE_PATH
)
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot load {MODULE_PATH}")
COMBINED = importlib.util.module_from_spec(spec)
spec.loader.exec_module(COMBINED)

ATMOSPHERE = """# z p T air O3 O2 H2O CO2 NO2
3.000000 700 270 1e19 1e12 2e18 1e16 4e15 1e10
2.000000 800 275 2e19 2e12 4e18 2e16 8e15 2e10
1.000000 900 280 3e19 3e12 6e18 3e16 1.2e16 3e10
0.000000 1013 288 4e19 4e12 8e18 4e16 1.6e16 4e10
"""


class CombinedSpectralProofTests(unittest.TestCase):
    def test_corrected_mystic_domain_is_tier1_and_reference_is_interior(self) -> None:
        COMBINED.validate_immutable_contract()
        self.assertEqual(COMBINED.MYSTIC_WAVELENGTH_START_NM, 380.0)
        self.assertEqual(COMBINED.MYSTIC_WAVELENGTH_END_NM, 780.0)
        self.assertEqual(COMBINED.MYSTIC_IMPORTANCE_WAVELENGTH_NM, 550.0)
        self.assertLess(
            COMBINED.MYSTIC_WAVELENGTH_START_NM,
            COMBINED.MYSTIC_IMPORTANCE_WAVELENGTH_NM,
        )
        self.assertLess(
            COMBINED.MYSTIC_IMPORTANCE_WAVELENGTH_NM,
            COMBINED.MYSTIC_WAVELENGTH_END_NM,
        )

    def test_mystic_input_changes_only_spectral_domain_from_deterministic_common(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            atmosphere = root / "atmosphere.dat"
            atmosphere.write_text(ATMOSPHERE, encoding="utf-8")
            grid = COMBINED.BASE.forced_grid_ascending(atmosphere, 0.357143)
            mystic = COMBINED.corrected_render_mystic_input(
                root,
                atmosphere,
                root / "solar.dat",
                root / "output",
                grid,
                False,
            )
            deterministic = COMBINED.PROOF.render_profile_input(
                root,
                atmosphere,
                root / "solar.dat",
                "B-atm-z-grid-candidate",
                0.357143,
                grid,
                False,
            )
            self.assertIn("wavelength 380.0 780.0", mystic)
            self.assertNotIn("wavelength 550.0 550.0", mystic)
            self.assertIn("mc_spectral_is 550.0", mystic)
            self.assertIn("wavelength 550.0 550.0", deterministic)
            self.assertNotIn("wavelength 380.0 780.0", deterministic)

    def test_combined_candidate_preserves_no_altitude_one_photon_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            atmosphere = root / "atmosphere.dat"
            atmosphere.write_text(ATMOSPHERE, encoding="utf-8")
            grid = COMBINED.BASE.forced_grid_ascending(atmosphere, 0.357143)
            text = COMBINED.corrected_render_mystic_input(
                root,
                atmosphere,
                root / "solar.dat",
                root / "output",
                grid,
                False,
            )
            self.assertNotIn("\naltitude ", "\n" + text)
            self.assertNotIn("mc_elevation_file ", text)
            self.assertEqual(text.splitlines().count("zout 0.000000"), 1)
            self.assertEqual(text.splitlines().count("mc_photons 1"), 1)
            self.assertEqual(text.splitlines().count("mc_randomseed 990004"), 1)
            self.assertIn(
                "atm_z_grid 0.357143 1.000000 2.000000 3.000000", text
            )

    def test_installation_changes_only_mystic_hooks_and_stage_id(self) -> None:
        original_tolerances = COMBINED.PROOF.PREREGISTERED_TOLERANCES.copy()
        COMBINED.install_corrected_mystic_boundary()
        self.assertIs(
            COMBINED.BASE.render_mystic_input,
            COMBINED.corrected_render_mystic_input,
        )
        self.assertIs(
            COMBINED.BASE.run_mystic_probe,
            COMBINED.corrected_run_mystic_probe,
        )
        self.assertEqual(COMBINED.PROOF.STAGE_ID, COMBINED.STAGE_ID)
        self.assertEqual(
            COMBINED.PROOF.PREREGISTERED_TOLERANCES,
            original_tolerances,
        )


if __name__ == "__main__":
    unittest.main()
