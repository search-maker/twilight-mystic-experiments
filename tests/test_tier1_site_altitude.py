from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
MODULE_ROOT = ROOT / "experiments/mystic-batch-v1"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


adapter = load_module(
    "tier1_altitude_adapter",
    MODULE_ROOT / "twilight_surrogate_tier1_execution_adapter.py",
)


def atmosphere_text() -> str:
    return (
        "# z p T air o3 o2 h2o co2 no2\n"
        "120.0 1 1 1 1 1 1 1 1\n"
        "2.0 1 1 1 1 1 1 1 1\n"
        "1.0 1 1 1 1 1 1 1 1\n"
        "0.0 1 1 1 1 1 1 1 1\n"
    )


class Tier1SiteAltitudeTests(unittest.TestCase):
    def test_replaces_output_altitude_with_validated_grid_and_ground_zout(self):
        with tempfile.TemporaryDirectory() as temp:
            atmosphere = Path(temp) / "afglus.dat"
            atmosphere.write_text(atmosphere_text())
            rendered = (
                f"atmosphere_file {atmosphere.resolve()}\n"
                "rte_solver mystic\n"
                "zout 0.357143\n"
                "quiet\n"
            )
            corrected, altitude_km, grid = adapter.apply_ground_site_atm_z_grid(
                rendered, 357.142857
            )
            self.assertEqual(altitude_km, 0.357142857)
            self.assertEqual(grid, [0.357142857, 1.0, 2.0, 120.0])
            self.assertIn(
                "atm_z_grid 0.357143 1.000000 2.000000 120.000000\n",
                corrected,
            )
            self.assertIn("zout 0.000000\n", corrected)
            self.assertNotIn("zout 0.357143", corrected)
            self.assertNotIn("\naltitude ", corrected)
            self.assertNotIn("mc_elevation_file", corrected)

    def test_zero_elevation_preserves_all_original_levels(self):
        with tempfile.TemporaryDirectory() as temp:
            atmosphere = Path(temp) / "afglus.dat"
            atmosphere.write_text(atmosphere_text())
            rendered = f"atmosphere_file {atmosphere.resolve()}\nzout 0.000000\n"
            corrected, altitude_km, grid = adapter.apply_ground_site_atm_z_grid(
                rendered, 0
            )
            self.assertEqual(altitude_km, 0.0)
            self.assertEqual(grid, [0.0, 1.0, 2.0, 120.0])
            self.assertIn(
                "atm_z_grid 0.000000 1.000000 2.000000 120.000000\n",
                corrected,
            )
            self.assertEqual(corrected.count("zout 0.000000"), 1)

    def test_refuses_missing_duplicate_or_forbidden_elevation_mechanism(self):
        with tempfile.TemporaryDirectory() as temp:
            atmosphere = Path(temp) / "afglus.dat"
            atmosphere.write_text(atmosphere_text())
            atmosphere_line = f"atmosphere_file {atmosphere.resolve()}\n"
            with self.assertRaises(adapter.AdapterError):
                adapter.apply_ground_site_atm_z_grid(atmosphere_line + "quiet\n", 100)
            with self.assertRaises(adapter.AdapterError):
                adapter.apply_ground_site_atm_z_grid(
                    atmosphere_line + "zout 0\nzout 1\n", 100
                )
            with self.assertRaises(adapter.AdapterError):
                adapter.apply_ground_site_atm_z_grid("zout 0\n", 100)
            with self.assertRaises(adapter.AdapterError):
                adapter.apply_ground_site_atm_z_grid(
                    atmosphere_line + "altitude 0.1\nzout 0\n", 100
                )
            with self.assertRaises(adapter.AdapterError):
                adapter.apply_ground_site_atm_z_grid(
                    atmosphere_line + "mc_elevation_file x\nzout 0\n", 100
                )

    def test_prepare_case_records_physical_semantics(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            atmosphere = root / "atmmod" / "afglus.dat"
            atmosphere.parent.mkdir(parents=True)
            atmosphere.write_text(atmosphere_text())
            stub = root / "cross_geometry_adapter.py"
            stub.write_text(
                """
def resolve_case(manifest, case_id):
    return manifest['cases'][0], manifest['geometries'][0]

def normalized_inputs(manifest, case, geometry):
    return {
        'observerElevationM': geometry['observerElevationM'],
        'alisSpectralImportanceSamplingNm': 550.0,
    }

def render_input(inputs, data_dir, repository_root, case_dir):
    atmosphere = (data_dir / 'atmmod' / 'afglus.dat').resolve()
    return (
        f"atmosphere_file {atmosphere}\\n"
        f"rte_solver mystic\\n"
        f"zout {inputs['observerElevationM'] / 1000.0:.6f}\\n"
        "quiet\\n"
    )
"""
            )
            hashes = {
                name: "a" * 64
                for name in (
                    "uvspecSha256",
                    "uvspecHelpSha256",
                    "libRadtranDataTreeSha256",
                    "atmosphereSha256",
                    "runtimeLockRawSha256",
                )
            }
            cases = []
            geometries = []
            for ordinal in range(1, 97):
                cases.append(
                    {
                        "ordinal": ordinal,
                        "caseId": f"case-{ordinal:03d}",
                        "groupId": f"geometry-{(ordinal + 1) // 2:03d}",
                        "method": "alis",
                        "block": 1 if ordinal % 2 else 2,
                        "seed": 900000 + ordinal,
                        "photonHistories": 72_500_000,
                        "alisSpectralImportanceSamplingNm": 550.0,
                        "role": "surrogate-training",
                    }
                )
            for index in range(1, 49):
                geometries.append(
                    {
                        "geometryId": f"geometry-{index:03d}",
                        "observerElevationM": (
                            357.142857 if index == 1 else float(index)
                        ),
                    }
                )
            manifest = {
                "schemaVersion": 1,
                "stageId": adapter.STAGE_ID,
                "batchId": "twilight-surrogate-space-filling-v1-tier-1",
                "mode": "scientific-proposal",
                "proposalOnly": True,
                "scientificExecution": False,
                "successDoesNotAuthorizeProduction": True,
                "adapterId": adapter.ADAPTER_ID,
                "caseSpecificAlisSpectralImportanceSampling": True,
                "runtime": hashes,
                "cases": cases,
                "geometries": geometries,
            }
            runtime = {
                "schemaVersion": 1,
                "stageId": "mystic-batch-v1",
                "scientificSolverExecuted": False,
                "syntaxCheckExecuted": False,
                **hashes,
            }
            manifest_path = root / "manifest.json"
            runtime_path = root / "runtime.json"
            manifest_path.write_text(json.dumps(manifest))
            runtime_path.write_text(json.dumps(runtime))
            old_base = adapter.BASE
            adapter.BASE = stub
            try:
                result = adapter.prepare_case(
                    manifest_path,
                    runtime_path,
                    "case-001",
                    root,
                    root,
                    root / "output",
                )
            finally:
                adapter.BASE = old_base
            text = Path(result["inputPath"]).read_text()
            self.assertIn("atm_z_grid 0.357143", text)
            self.assertIn("zout 0.000000", text)
            self.assertNotIn("\naltitude ", text)
            self.assertNotIn("mc_elevation_file", text)
            self.assertEqual(result["siteAltitudeKm"], 0.357142857)
            self.assertEqual(result["zoutKmAboveLocalSurface"], 0.0)
            self.assertEqual(result["observerElevationMechanism"], "atm_z_grid")
            self.assertEqual(result["atmosphereGridBottomKm"], 0.357142857)
            self.assertEqual(
                result["observerElevationSemantics"],
                "site-altitude-above-sea-level-via-atm-z-grid; "
                "sensor-at-local-surface",
            )


if __name__ == "__main__":
    unittest.main()
