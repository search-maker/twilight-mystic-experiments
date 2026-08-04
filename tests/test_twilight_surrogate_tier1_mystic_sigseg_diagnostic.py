from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "experiments"
    / "mystic-batch-v1"
    / "twilight_surrogate_tier1_mystic_sigseg_diagnostic.py"
)
SPEC = importlib.util.spec_from_file_location("sigseg_diagnostic", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
DIAG = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DIAG)


class FakeProbe:
    PRIMARY_SITE_ALTITUDE_KM = 0.357143
    MYSTIC_PHOTONS = 1
    MYSTIC_SEED = 990004
    EXPECTED_ZOUT = "zout 0.000000"

    @staticmethod
    def forced_grid_ascending(atmosphere: Path, site_altitude_km: float) -> list[float]:
        del atmosphere
        return [site_altitude_km, 1.0, 2.0, 120.0]

    @staticmethod
    def render_mystic_input(
        data_dir: Path,
        atmosphere: Path,
        solar_flux: Path,
        output_dir: Path,
        grid_ascending: list[float],
        resolved: bool,
    ) -> str:
        del data_dir, atmosphere, solar_flux, grid_ascending, resolved
        return "\n".join(
            [
                "atm_z_grid 0.357143 1.000000 2.000000 120.000000",
                "rte_solver mystic",
                "mc_spherical 1D",
                "mc_photons 1",
                "mc_vroom off",
                "mc_std",
                "mc_randomseed 990004",
                f"mc_basename {output_dir}/mc",
                "mc_spectral_is 550.0",
                "zout 0.000000",
                "umu -0.50000000",
                "phi 36.000000",
                "verbose",
                "",
            ]
        )


class SigsegDiagnosticTests(unittest.TestCase):
    def test_probe_contract_is_frozen(self) -> None:
        DIAG.validate_probe_contract(FakeProbe)
        FakeProbe.MYSTIC_PHOTONS = 2
        with self.assertRaises(DIAG.DiagnosticError):
            DIAG.validate_probe_contract(FakeProbe)
        FakeProbe.MYSTIC_PHOTONS = 1

    def test_exact_input_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            atmosphere = root / "atmosphere.dat"
            atmosphere.write_text("120 1\n0 1\n", encoding="utf-8")
            raw, resolved, grid = DIAG.build_exact_input(
                FakeProbe,
                root,
                atmosphere,
                root / "solar",
                root / "output" / "h-0.357143" / "mystic-B-one-photon",
            )
            self.assertEqual(raw, resolved)
            self.assertEqual(grid[0], 0.357143)
            self.assertIn("mc_photons 1", resolved.splitlines())
            self.assertIn("mc_randomseed 990004", resolved.splitlines())
            self.assertIn("zout 0.000000", resolved.splitlines())
            self.assertFalse(any(line.startswith("altitude ") for line in resolved.splitlines()))
            self.assertFalse(
                any(line.startswith("mc_elevation_file ") for line in resolved.splitlines())
            )

    def test_gdb_command_has_one_run_and_complete_context(self) -> None:
        text = DIAG.gdb_command_text(Path("/tmp/input-resolved.txt"))
        self.assertEqual(sum(line.startswith("run < ") for line in text.splitlines()), 1)
        self.assertIn("handle SIGSEGV stop print nopass", text)
        self.assertIn("thread apply all bt full", text)
        self.assertIn("info registers", text)
        self.assertIn("info proc mappings", text)

    def test_parse_gdb_evidence(self) -> None:
        text = "\n".join(
            [
                "Program received signal SIGSEGV, Segmentation fault.",
                "=== TIER1_SIGNAL_CONTEXT ===",
                "#0  0x0000000000401234 in sample_frame ()",
                "#1  0x0000000000401000 in ?? ()",
                "rip            0x401234  0x401234 <sample_frame+4>",
                "=== END_TIER1_SIGNAL_CONTEXT ===",
            ]
        )
        parsed = DIAG.parse_gdb_evidence(text)
        self.assertTrue(parsed["sigsegvReproduced"])
        self.assertTrue(parsed["backtraceObserved"])
        self.assertEqual(parsed["backtraceFrameCount"], 2)
        self.assertEqual(parsed["symbolicFrameCount"], 1)
        self.assertTrue(parsed["instructionPointerObserved"])
        self.assertTrue(parsed["signalContextBoundaryObserved"])

    def test_failure_report_never_authorizes(self) -> None:
        report = DIAG.failure_report("test")
        self.assertFalse(report["proofPassed"])
        self.assertFalse(report["authorizationPermitted"])
        self.assertFalse(report["ordinal2ScientificDispatchPermitted"])
        self.assertFalse(report["scientificDatasetProduced"])
        self.assertEqual(report["mysticSolverExecutionCount"], 0)
        self.assertEqual(report["maximumPermittedMysticSolverExecutionCount"], 1)


if __name__ == "__main__":
    unittest.main()
