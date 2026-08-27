import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "review/native-stellar-zenith-v3/probe_vertical_optical_grid_format_recovery1.py"


def load_module():
    spec = importlib.util.spec_from_file_location("stellar_optical_grid_format_probe_recovery1", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load optical-grid format probe recovery1")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class StellarOpticalGridFormatProbeRecovery1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load_module()

    def test_recovery_identity_and_scope_are_frozen(self):
        m = self.m
        self.assertEqual(m.FAILED_RUN_ID, 33037957904)
        self.assertEqual(m.FAILURE_REASON, "WRITE_OPTICAL_PROPERTIES_REQUIRES_EXPLICIT_SOLAR_SOURCE_FILENAME")
        self.assertEqual(m.RECOVERY_CHANGE_SCOPE, "solar-source-filename-only")
        self.assertEqual(m.OBSERVER_ELEVATION_M, 500.0)
        self.assertEqual(m.AOD550, 0.10)
        self.assertEqual(m.SZA_DEG, 0.0)
        self.assertEqual(len(m.WAVELENGTH_NM), 401)
        self.assertIn(m.OBSERVER_ELEVATION_M, m.base.ELEVATION_KNOTS_M)
        self.assertIn(m.AOD550, m.base.AOD_KNOTS)
        self.assertNotIn(m.OBSERVER_ELEVATION_M, m.base.VALIDATION_ELEVATION_M)
        self.assertNotIn(m.AOD550, m.base.VALIDATION_AOD550)

    def test_renderer_changes_only_solar_source_binding_surface(self):
        m = self.m
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            atmosphere = root / "afglus.dat"
            atmosphere.write_text("10 1\n5 1\n0 1\n", encoding="utf-8")
            grid = root / "grid.dat"
            grid.write_text("\n".join(str(x) for x in range(380, 781)) + "\n", encoding="utf-8")
            recovered = m.render_input(data_dir=root, atmosphere_file=atmosphere, wavelength_grid_file=grid)
            original = m.probe.render_input(data_dir=root, atmosphere_file=atmosphere, wavelength_grid_file=grid)
        recovered_lines = recovered.splitlines()
        original_lines = original.splitlines()
        self.assertEqual(len(recovered_lines), len(original_lines))
        differences = [(a, b) for a, b in zip(original_lines, recovered_lines) if a != b]
        self.assertEqual(len(differences), 1)
        self.assertEqual(differences[0][0], "source solar")
        self.assertTrue(differences[0][1].startswith("source solar "))
        self.assertTrue(differences[0][1].endswith(str(m.SOLAR_FLUX_RELATIVE_PATH)))
        self.assertIn("write_optical_properties", recovered)
        self.assertIn("rte_solver disort", recovered)
        self.assertNotIn("rte_solver mystic", recovered.lower())
        self.assertNotIn("mc_", recovered.lower())

    def test_execution_is_inert_without_authorization(self):
        m = self.m
        with self.assertRaisesRegex(m.ProbeRefusal, "allow_execution=True"):
            m.execute(
                uvspec=Path("missing"), data_dir=Path("missing"), atmosphere_file=Path("missing"),
                wavelength_grid_file=Path("missing"), output_dir=Path("missing"), allow_execution=False,
            )


if __name__ == "__main__":
    unittest.main()
