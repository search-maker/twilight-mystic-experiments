from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "experiments" / "mystic-batch-v1"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


renderer = load_module(
    "reptran_visible_renderer_v1", PACKAGE / "reptran_visible_renderer_v1.py"
)
legacy = load_module("legacy_cross_geometry_adapter", PACKAGE / "cross_geometry_adapter.py")


class ReptranVisibleRendererV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.data = self.root / "data"
        (self.data / "solar_flux").mkdir(parents=True)
        (self.data / "atmmod").mkdir(parents=True)
        (self.data / "solar_flux" / "atlas_plus_modtran").write_text("solar\n")
        (self.data / "atmmod" / "afglus.dat").write_text(
            "100 1\n50 1\n10 1\n0 1\n"
        )
        (self.root / "grid.dat").write_text("380\n500\n550\n600\n780\n")
        self.case_dir = self.root / "case"
        self.case_dir.mkdir()
        self.inputs = {
            "caseId": "train-test",
            "groupId": "train-test",
            "method": "alis",
            "block": 1,
            "seed": 123456789,
            "photonHistories": 1_000_000,
            "sunDepressionDeg": 6.125,
            "targetAltitudeDeg": 17.962963,
            "relativeAzimuthDeg": 60.48,
            "observerElevationM": 1180.758017,
            "aod550": 0.067355,
            "albedo": 0.15,
            "wavelengthDomainNm": [380, 780],
            "diagnosticNodesNm": [500, 550, 600],
            "molecularAbsorption": "reptran",
            "mcSpherical": "1D",
            "alisSpectralImportanceSamplingNm": 550.0,
            "solarFlux": {
                "root": "libRadtranData",
                "path": "solar_flux/atlas_plus_modtran",
            },
            "wavelengthGrid": {"root": "repository", "path": "grid.dat"},
            "atmosphere": {"root": "libRadtranData", "path": "atmmod/afglus.dat"},
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_ground_site_renderer_differs_from_legacy_only_by_absorption(self) -> None:
        text, proof = renderer.render_ground_site_input(
            self.inputs, self.data, self.root, self.case_dir
        )
        lines = text.splitlines()
        self.assertEqual(lines.count("mol_abs_param reptran"), 1)
        self.assertNotIn("mol_abs_param crs", lines)
        self.assertEqual(lines.count("zout 0.000000"), 1)
        self.assertEqual(sum(line.startswith("atm_z_grid ") for line in lines), 1)
        self.assertFalse(any(line.startswith("altitude ") for line in lines))
        self.assertFalse(any(line.startswith("mc_elevation_file ") for line in lines))
        self.assertFalse(any(line.startswith("wavelength_grid_file ") for line in lines))
        self.assertEqual(lines.count("mc_vroom off"), 1)
        self.assertEqual(lines.count("mc_spectral_is 550.0"), 1)
        self.assertEqual(
            proof["onlyDifferenceAgainstLegacyCrs"],
            [["mol_abs_param crs", "mol_abs_param reptran"]],
        )
        self.assertEqual(proof["observerElevationMechanism"], "atm_z_grid")
        self.assertAlmostEqual(proof["siteAltitudeKm"], 1.180758017, places=12)
        self.assertAlmostEqual(proof["atmosphereGridKm"][0], 1.180758017, places=12)
        self.assertEqual(proof["zoutKmAboveLocalSurface"], 0.0)
        self.assertFalse(proof["scientificSolverExecuted"])
        self.assertFalse(proof["protectedResultOpened"])

    def test_legacy_renderer_remains_crs_and_unmodified(self) -> None:
        old_inputs = dict(self.inputs)
        old_inputs["molecularAbsorption"] = "crs"
        text = legacy.render_input(old_inputs, self.data, self.root, self.case_dir)
        lines = text.splitlines()
        self.assertEqual(lines.count("mol_abs_param crs"), 1)
        self.assertNotIn("mol_abs_param reptran", lines)

    def test_renderer_refuses_crs_as_successor_input(self) -> None:
        bad = dict(self.inputs)
        bad["molecularAbsorption"] = "crs"
        with self.assertRaises(renderer.ReptranVisibleRendererError):
            renderer.render_input(bad, self.data, self.root, self.case_dir)

    def test_renderer_refuses_unvalidated_reference_vroom_path(self) -> None:
        bad = dict(self.inputs)
        bad["method"] = "reference-vroom"
        with self.assertRaises(renderer.ReptranVisibleRendererError):
            renderer.render_input(bad, self.data, self.root, self.case_dir)


if __name__ == "__main__":
    unittest.main()
