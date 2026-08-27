import importlib.util
import math
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "review/native-stellar-zenith-v3/diagnose_exact_vertical_disort_bridge_v1.py"


def load_module():
    spec = importlib.util.spec_from_file_location("exact_vertical_disort_bridge_v1", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load exact vertical DISORT bridge module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ExactVerticalDisortBridgeV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load_module()

    def test_frozen_case_universe_and_gates(self):
        m = self.m
        m.validate_case_universe()
        rows = m.build_case_universe()
        self.assertEqual(len(rows), 20)
        self.assertEqual(m.DISORT_SZA_DEG, (0.0, 0.5, 1.0))
        self.assertEqual(m.SDISORT_SZA_DEG, (0.5, 1.0))
        self.assertFalse(any(r["solver"] == "sdisort" and r["szaDeg"] == 0.0 for r in rows))
        self.assertEqual(m.MAX_ABS_DELTA_VERTICAL_TAU, 5e-6)
        self.assertEqual(m.MAX_ABS_DELTA_SOLVER_BRIDGE_TAU, 5e-6)
        self.assertEqual(m.MAX_ABS_DELTA_AV_MAG, 1e-4)

    def _render(self, solver, sza):
        m = self.m
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            atmosphere = root / "afglus.dat"
            atmosphere.write_text("10 1\n5 1\n0 1\n", encoding="utf-8")
            grid = root / "wavelength.dat"
            grid.write_text("\n".join(str(x) for x in range(380, 781)) + "\n", encoding="utf-8")
            return m.render_uvspec_input(
                solver=solver,
                sza_deg=sza,
                observer_elevation_m=0.0,
                aod550=0.05,
                data_dir=root,
                atmosphere_file=atmosphere,
                wavelength_grid_file=grid,
            )

    def test_exact_vertical_disort_renderer_is_not_sdisort(self):
        text = self._render("disort", 0.0)
        self.assertIn("sza 0.00000000", text)
        self.assertIn("rte_solver disort", text)
        self.assertNotIn("sdisort nscat", text)
        self.assertIn("output_quantity transmittance", text)
        self.assertIn("output_user lambda edir", text)

    def test_near_zenith_sdisort_renderer_preserves_nscat1(self):
        text = self._render("sdisort", 0.5)
        self.assertIn("sza 0.50000000", text)
        self.assertIn("rte_solver sdisort", text)
        self.assertIn("sdisort nscat 1", text)

    def test_plane_parallel_vertical_reconstruction_identity(self):
        m = self.m
        tau_vertical = 0.237
        for sza in (0.0, 0.5, 1.0):
            mu = math.cos(math.radians(sza))
            edir = mu * math.exp(-tau_vertical / mu)
            stdout = "\n".join(f"{w} {edir:.16g}" for w in range(380, 781)) + "\n"
            parsed = m.parse_direct_transmission(stdout, sza_deg=sza)
            reconstructed = m.reconstructed_vertical_optical_depth(parsed)
            self.assertTrue(all(abs(value - tau_vertical) < 2e-15 for value in reconstructed))

    def test_parser_rejects_incomplete_grid(self):
        m = self.m
        with self.assertRaisesRegex(m.BridgeRefusal, "exact 380..780"):
            m.parse_direct_transmission("380 0.5\n", sza_deg=0.0)

    def test_execution_is_inert_without_explicit_authorization(self):
        m = self.m
        with self.assertRaisesRegex(m.BridgeRefusal, "allow_execution=True"):
            m.execute_campaign(
                root=Path("."), uvspec=Path("missing"), data_dir=Path("missing"),
                atmosphere_file=Path("missing"), wavelength_grid_file=Path("missing"),
                sed_bundle_path=Path("missing"), johnson_v_path=Path("missing"),
                output_dir=Path("missing"), allow_execution=False,
            )


if __name__ == "__main__":
    unittest.main()
