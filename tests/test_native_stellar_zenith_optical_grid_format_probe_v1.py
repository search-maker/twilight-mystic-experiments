import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "review/native-stellar-zenith-v3/probe_vertical_optical_grid_format_v1.py"


def load_module():
    spec = importlib.util.spec_from_file_location("stellar_optical_grid_format_probe_v1", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load format probe")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class StellarOpticalGridFormatProbeV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load_module()

    def test_probe_uses_training_knot_not_protected_holdout(self):
        m = self.m
        self.assertEqual(m.OBSERVER_ELEVATION_M, 500.0)
        self.assertEqual(m.AOD550, 0.10)
        self.assertIn(m.OBSERVER_ELEVATION_M, m.base.ELEVATION_KNOTS_M)
        self.assertIn(m.AOD550, m.base.AOD_KNOTS)
        self.assertNotIn(m.OBSERVER_ELEVATION_M, m.base.VALIDATION_ELEVATION_M)
        self.assertNotIn(m.AOD550, m.base.VALIDATION_AOD550)
        self.assertEqual(len(m.WAVELENGTH_NM), 401)

    def test_render_contract_is_optical_materialization_only(self):
        m = self.m
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            atmosphere = root / "afglus.dat"
            atmosphere.write_text("10 1\n5 1\n0 1\n", encoding="utf-8")
            grid = root / "grid.dat"
            grid.write_text("\n".join(str(x) for x in range(380, 781)) + "\n", encoding="utf-8")
            text = m.render_input(data_dir=root, atmosphere_file=atmosphere, wavelength_grid_file=grid)
        self.assertIn("sza 0.00000000", text)
        self.assertIn("rte_solver disort", text)
        self.assertIn("write_optical_properties", text)
        self.assertIn("verbose", text)
        self.assertIn("wavelength 380 780", text)
        self.assertIn("aerosol_set_tau_at_wvl 550 0.10000000", text)
        self.assertNotIn("rte_solver mystic", text.lower())
        self.assertNotIn("mc_", text.lower())

    def test_execution_is_inert_without_authorization(self):
        m = self.m
        with self.assertRaisesRegex(m.ProbeRefusal, "allow_execution=True"):
            m.execute(
                uvspec=Path("missing"), data_dir=Path("missing"), atmosphere_file=Path("missing"),
                wavelength_grid_file=Path("missing"), output_dir=Path("missing"), allow_execution=False,
            )


if __name__ == "__main__":
    unittest.main()
