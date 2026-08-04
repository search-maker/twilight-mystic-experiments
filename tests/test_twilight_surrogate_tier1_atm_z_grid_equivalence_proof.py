from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    ROOT
    / "experiments"
    / "mystic-batch-v1"
    / "twilight_surrogate_tier1_atm_z_grid_equivalence_proof.py"
)
spec = importlib.util.spec_from_file_location("tier1_atm_z_grid_equivalence", MODULE_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot load {MODULE_PATH}")
PROOF = importlib.util.module_from_spec(spec)
spec.loader.exec_module(PROOF)


class EquivalenceInstrumentationTests(unittest.TestCase):
    def test_tolerances_are_unmodified(self) -> None:
        self.assertIs(PROOF.PREREGISTERED_TOLERANCES, PROOF.BASE.PREREGISTERED_TOLERANCES)
        self.assertEqual(
            PROOF.PREREGISTERED_TOLERANCES["layerBoundaryKm"],
            {"rtol": 0.0, "atol": 1.0e-6},
        )

    def test_optical_verbose_table_is_parsed_without_netcdf(self) -> None:
        stderr = """*** optical_properties()
   lc | z[km] | Rayleigh | Aerosol | Water cloud | Ice cloud | Molecular
    0 | 1.0000 | 1.0e-3 | 2.0e-3 3.0e-4 0.650 | 0 0 0 | 0 0 0 0 0 0 0 | 4.0e-4
    1 | 0.3571 | 2.0e-3 | 3.0e-3 4.0e-4 0.660 | 0 0 0 | 0 0 0 0 0 0 0 | 5.0e-4
  sum | -nan | 3.0e-3 | 5.0e-3 7.0e-4 -nan | 0 0 -nan | 0 0 -nan -nan -nan -nan -nan | 9.0e-4
"""
        table = PROOF.parse_resolved_optical_table(stderr)
        self.assertEqual(table["lowerBoundaryKm"], [1.0, 0.3571])
        self.assertEqual(len(table["totalLayerOpticalDepth"]), 2)
        decision = PROOF.validate_optical_pair(
            table,
            table,
            [0.357143, 1.0, 2.0],
        )
        self.assertTrue(decision["passed"])
        self.assertFalse(decision["cloudsConfigured"])

    def test_profile_equivalence_uses_a_b_difference_and_exact_surface(self) -> None:
        rows = []
        for local, sea, pressure in (
            (0.0, 0.357143, 970.0),
            (64.642860, 65.0, 0.109),
        ):
            rows.append(
                {
                    "lambda": 550.0,
                    "zout_sur": local,
                    "zout_sea": sea,
                    "z_sur": 0.357143,
                    "p": pressure,
                    "T": 280.0,
                    "n_AIR": 2.0e19,
                    "n_O3": 2.0e12,
                    "n_O2": 4.0e18,
                    "n_H2O": 2.0e16,
                    "n_CO2": 8.0e15,
                    "n_NO2": 2.0e10,
                    "edir": 1.0,
                    "edn": 2.0,
                    "eup": 0.5,
                    "uu": 0.1,
                }
            )
        decision = PROOF.validate_profile_pair(
            rows,
            rows,
            [0.357143, 65.0],
            0.357143,
        )
        self.assertTrue(decision["atmosphericProfileAndColumnPassed"])
        self.assertTrue(decision["deterministicControlPassed"])

    def test_boundary_always_forbids_authorization_and_dispatch(self) -> None:
        boundary = PROOF.boundary_fields()
        self.assertFalse(boundary["authorizationPermitted"])
        self.assertFalse(boundary["ordinal2ScientificDispatchPermitted"])
        self.assertFalse(boundary["scientificDatasetProduced"])
        self.assertFalse(boundary["sourceProvenance"]["sourceEvidenceAccepted"])
        self.assertFalse(
            boundary["sourceProvenance"]["expectedHashChangedToMakeCiGreen"]
        )


if __name__ == "__main__":
    unittest.main()
