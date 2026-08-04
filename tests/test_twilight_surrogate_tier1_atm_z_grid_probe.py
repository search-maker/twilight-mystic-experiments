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
    / "twilight_surrogate_tier1_atm_z_grid_probe.py"
)
spec = importlib.util.spec_from_file_location("tier1_atm_z_grid_proof", MODULE_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot load {MODULE_PATH}")
PROOF = importlib.util.module_from_spec(spec)
spec.loader.exec_module(PROOF)

ATMOSPHERE = """# z p T air O3 O2 H2O CO2 NO2
3.000000 700 270 1e19 1e12 2e18 1e16 4e15 1e10
2.000000 800 275 2e19 2e12 4e18 2e16 8e15 2e10
1.000000 900 280 3e19 3e12 6e18 3e16 1.2e16 3e10
0.000000 1013 288 4e19 4e12 8e18 4e16 1.6e16 4e10
"""


def write_atmosphere(root: Path) -> Path:
    path = root / "atmosphere.dat"
    path.write_text(ATMOSPHERE, encoding="utf-8")
    return path


class AtmZGridEquivalenceProofTests(unittest.TestCase):
    def test_forced_grid_is_ascending_and_preserves_exact_original_levels(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            atmosphere = write_atmosphere(Path(raw))
            grid = PROOF.forced_grid_ascending(atmosphere, 0.357143)
            self.assertEqual(grid, [0.357143, 1.0, 2.0, 3.0])
            self.assertTrue(all(a < b for a, b in zip(grid, grid[1:])))

    def test_control_and_candidate_inputs_differ_only_in_height_representation(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            atmosphere = write_atmosphere(root)
            grid = PROOF.forced_grid_ascending(atmosphere, 0.357143)
            common = dict(
                data_dir=root,
                atmosphere=atmosphere,
                solar_flux=root / "solar.dat",
                site_altitude_km=0.357143,
                grid_ascending=grid,
                resolved=False,
            )
            a = PROOF.render_profile_input(
                representation="A-explicit-altitude-control", **common
            )
            b = PROOF.render_profile_input(
                representation="B-atm-z-grid-candidate", **common
            )
            self.assertIn("altitude 0.357143", a)
            self.assertNotIn("atm_z_grid ", a)
            self.assertNotIn("mc_elevation_file ", a)
            self.assertNotIn("\naltitude ", "\n" + b)
            self.assertNotIn("mc_elevation_file ", b)
            self.assertIn("atm_z_grid 0.357143 1.000000 2.000000 3.000000", b)
            self.assertIn("zout 0.000000 0.642857 1.642857 2.642857", b)

    def test_mystic_candidate_has_exact_prohibited_and_required_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            atmosphere = write_atmosphere(root)
            grid = PROOF.forced_grid_ascending(atmosphere, 0.357143)
            text = PROOF.render_mystic_input(
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
            self.assertIn("rte_solver mystic", text)
            self.assertIn("mc_spherical 1D", text)
            self.assertIn("mc_photons 1", text)
            self.assertIn("mc_randomseed 990004", text)

    def test_tolerances_are_preregistered_literals(self) -> None:
        self.assertEqual(
            PROOF.PREREGISTERED_TOLERANCES,
            {
                "layerBoundaryKm": {"rtol": 0.0, "atol": 1.0e-6},
                "surfaceAndOutputAltitudeKm": {"rtol": 0.0, "atol": 1.0e-6},
                "pressureTemperatureAndNumberDensity": {"rtol": 5.0e-6, "atol": 1.0e-8},
                "gasColumn": {"rtol": 1.0e-5, "atol": 1.0e-6},
                "layerOpticalProperty": {"rtol": 1.0e-5, "atol": 1.0e-10},
                "columnOpticalProperty": {"rtol": 1.0e-5, "atol": 1.0e-10},
                "deterministicRadianceOrIrradiance": {"rtol": 1.0e-5, "atol": 1.0e-10},
            },
        )

    def test_profile_parser_and_equivalence_decision(self) -> None:
        grid = [0.357143, 1.0]
        rows = []
        for local, sea, p, t, scale in (
            (0.0, 0.357143, 950.0, 285.0, 1.0),
            (0.642857, 1.0, 900.0, 280.0, 0.8),
        ):
            rows.append(
                {
                    "lambda": 550.0,
                    "zout_sur": local,
                    "zout_sea": sea,
                    "z_sur": 0.357143,
                    "p": p,
                    "T": t,
                    "n_AIR": 2.0e19 * scale,
                    "n_O3": 2.0e12 * scale,
                    "n_O2": 4.0e18 * scale,
                    "n_H2O": 2.0e16 * scale,
                    "n_CO2": 8.0e15 * scale,
                    "n_NO2": 2.0e10 * scale,
                    "edir": 1.0 * scale,
                    "edn": 2.0 * scale,
                    "eup": 0.5 * scale,
                    "uu": 0.1 * scale,
                }
            )
        decision = PROOF.validate_profile_pair(rows, rows, grid, 0.357143)
        self.assertTrue(decision["atmosphericProfileAndColumnPassed"])
        self.assertTrue(decision["deterministicControlPassed"])

    def test_mystic_gate_refuses_any_failed_stage(self) -> None:
        profile = {
            "decision": {
                "atmosphericProfileAndColumnPassed": True,
                "deterministicControlPassed": True,
            }
        }
        optical = {"decision": {"passed": True}}
        structural = [profile, profile]
        self.assertTrue(PROOF.should_run_mystic(profile, optical, structural))
        bad = {
            "decision": {
                "atmosphericProfileAndColumnPassed": False,
                "deterministicControlPassed": True,
            }
        }
        self.assertFalse(PROOF.should_run_mystic(bad, optical, structural))
        self.assertFalse(
            PROOF.should_run_mystic(profile, {"decision": {"passed": False}}, structural)
        )
        self.assertFalse(PROOF.should_run_mystic(profile, optical, [profile, bad]))


if __name__ == "__main__":
    unittest.main()
