from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "experiments"
    / "mystic-batch-v1"
    / "twilight_surrogate_tier1_mystic_spectral_acceptance_probe.py"
)
SPEC = importlib.util.spec_from_file_location("spectral_acceptance", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
PROBE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROBE)


class FakeBase:
    @staticmethod
    def forced_grid_ascending(atmosphere: Path, site_altitude_km: float) -> list[float]:
        del atmosphere
        return [site_altitude_km, 1.0, 2.0, 120.0]


class SpectralAcceptanceTests(unittest.TestCase):
    def test_control_contract_uses_interior_alis_reference(self) -> None:
        PROBE.validate_control_contract()
        self.assertLess(PROBE.WAVELENGTH_START_NM, PROBE.IMPORTANCE_WAVELENGTH_NM)
        self.assertLess(PROBE.IMPORTANCE_WAVELENGTH_NM, PROBE.WAVELENGTH_END_NM)
        self.assertEqual(PROBE.MYSTIC_PHOTONS, 1)
        self.assertEqual(PROBE.MAXIMUM_MYSTIC_SOLVER_EXECUTIONS, 1)

    def test_render_input_preserves_candidate_and_tier1_spectral_domain(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            atmosphere = root / "atmosphere.dat"
            atmosphere.write_text("120 1\n0 1\n", encoding="utf-8")
            text, grid = PROBE.render_input(
                FakeBase,
                root / "data",
                atmosphere,
                root / "solar",
                root / "output",
                True,
            )
            lines = text.splitlines()
            self.assertEqual(grid[0], 0.357143)
            self.assertIn("wavelength 380.0 780.0", lines)
            self.assertIn("mc_spectral_is 550.0", lines)
            self.assertIn("mc_photons 1", lines)
            self.assertIn("mc_randomseed 990005", lines)
            self.assertIn("zout 0.000000", lines)
            self.assertFalse(any(line.startswith("altitude ") for line in lines))
            self.assertFalse(any(line.startswith("mc_elevation_file ") for line in lines))

    def test_inventory_includes_randomseed_and_numerical_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            randomseed = root / "randomseed"
            spectrum = root / "mc.is.spc"
            randomseed.write_text("990005\n", encoding="utf-8")
            spectrum.write_text("550 1.0\n", encoding="utf-8")
            rows = PROBE.inventory_files([randomseed, spectrum])
            by_name = {row["filename"]: row for row in rows}
            self.assertTrue(by_name["randomseed"]["randomSeedState"])
            self.assertFalse(by_name["randomseed"]["numericalOutput"])
            self.assertTrue(by_name["mc.is.spc"]["numericalOutput"])
            self.assertFalse(by_name["mc.is.spc"]["randomSeedState"])

    def test_prior_crash_interpretation_is_non_authorizing(self) -> None:
        value = PROBE.prior_crash_interpretation()
        self.assertEqual(
            value["classification"],
            "SINGLE_WAVELENGTH_ENDPOINT_ALIS_REFERENCE_NULL_DEREFERENCE",
        )
        self.assertEqual(value["observed"]["instruction"], "mov (%rax),%eax")
        self.assertEqual(value["observed"]["rax"], 0)
        self.assertTrue(
            value["correctedProbeConfiguration"]["referenceStrictlyInsideInterval"]
        )

    def test_failure_report_never_authorizes(self) -> None:
        report = PROBE.failure_report("test")
        self.assertFalse(report["acceptanceProbePassed"])
        self.assertFalse(report["combinedEquivalenceProofPassed"])
        self.assertFalse(report["authorizationPermitted"])
        self.assertFalse(report["ordinal2ScientificDispatchPermitted"])
        self.assertFalse(report["scientificDatasetProduced"])
        self.assertEqual(report["mysticSolverExecutionCount"], 0)
        self.assertEqual(report["maximumPermittedMysticSolverExecutionCount"], 1)


if __name__ == "__main__":
    unittest.main()
