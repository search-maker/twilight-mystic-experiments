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

spec = importlib.util.spec_from_file_location(
    "tier1_atm_z_grid_probe",
    MODULE_PATH,
)
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot load {MODULE_PATH}")
PROBE = importlib.util.module_from_spec(spec)
spec.loader.exec_module(PROBE)


ATMOSPHERE = """# z(km) pressure(hPa) temperature(K)
3.000000 700.0 270.0
2.000000 800.0 275.0
1.000000 900.0 280.0
0.000000 1013.0 288.0
"""


class AtmZGridProbeTests(unittest.TestCase):
    def test_forced_grid_preserves_levels_above_and_exact_site_bottom(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "atmosphere.dat"
            path.write_text(ATMOSPHERE, encoding="utf-8")
            grid = PROBE.forced_grid(path)
            self.assertEqual(grid, [3.0, 2.0, 1.0, 0.357143])
            self.assertEqual(grid[-1], PROBE.SITE_ALTITUDE_KM)

    def test_render_omits_altitude_and_mc_elevation(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            atmosphere = root / "atmosphere.dat"
            atmosphere.write_text(ATMOSPHERE, encoding="utf-8")
            text, grid = PROBE.render(
                root,
                atmosphere,
                root / "solar.dat",
                root / "out",
            )
            lines = text.splitlines()
            self.assertFalse(any(line.startswith("altitude ") for line in lines))
            self.assertFalse(any(line.startswith("mc_elevation_file ") for line in lines))
            self.assertEqual(lines.count("zout 0.000000"), 1)
            self.assertEqual(sum(line.startswith("atm_z_grid ") for line in lines), 1)
            self.assertEqual(grid[-1], 0.357143)

    def test_classification_requires_success_outputs_and_surface_marker(self) -> None:
        marker = "forced new altitude = 0.357143"
        status, accepted = PROBE.classify(0, marker + "\n", 1)
        self.assertEqual(
            status,
            "FROZEN_RUNTIME_ACCEPTS_ATM_Z_GRID_SITE_ALTITUDE_CANDIDATE",
        )
        self.assertTrue(accepted)

        for returncode, stderr, generated in (
            (1, marker + "\n", 1),
            (0, "", 1),
            (0, marker + "\n", 0),
        ):
            with self.subTest(
                returncode=returncode,
                stderr=stderr,
                generated=generated,
            ):
                status, accepted = PROBE.classify(
                    returncode,
                    stderr,
                    generated,
                )
                self.assertEqual(
                    status,
                    "UNEXPECTED_ATM_Z_GRID_SITE_ALTITUDE_PROBE_RESULT",
                )
                self.assertFalse(accepted)

    def test_malformed_or_out_of_range_atmosphere_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            malformed = root / "malformed.dat"
            malformed.write_text("0.0 1\n1.0 2\n", encoding="utf-8")
            with self.assertRaises(PROBE.ProbeError):
                PROBE.forced_grid(malformed)

            high_bottom = root / "high.dat"
            high_bottom.write_text(
                "3.0 1\n2.0 1\n1.0 1\n",
                encoding="utf-8",
            )
            with self.assertRaises(PROBE.ProbeError):
                PROBE.forced_grid(high_bottom)


if __name__ == "__main__":
    unittest.main()
