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


class Tier1SiteAltitudeTests(unittest.TestCase):
    def test_replaces_output_altitude_with_site_altitude_and_ground_zout(self):
        rendered = "rte_solver mystic\nzout 0.357143\nquiet\n"
        corrected, altitude_km = adapter.apply_ground_site_altitude(rendered, 357.142857)
        self.assertEqual(altitude_km, 0.357142857)
        self.assertIn("altitude 0.357143\n", corrected)
        self.assertIn("zout 0.000000\n", corrected)
        self.assertNotIn("zout 0.357143", corrected)

    def test_zero_elevation_remains_ground_level(self):
        corrected, altitude_km = adapter.apply_ground_site_altitude("zout 0.000000\n", 0)
        self.assertEqual(altitude_km, 0.0)
        self.assertEqual(corrected, "altitude 0.000000\nzout 0.000000\n")

    def test_refuses_missing_or_duplicate_zout(self):
        with self.assertRaises(adapter.AdapterError):
            adapter.apply_ground_site_altitude("quiet\n", 100)
        with self.assertRaises(adapter.AdapterError):
            adapter.apply_ground_site_altitude("zout 0\nzout 1\n", 100)

    def test_prepare_case_records_physical_semantics(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
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
    return f"rte_solver mystic\\nzout {inputs['observerElevationM'] / 1000.0:.6f}\\nquiet\\n"
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
                        "observerElevationM": 357.142857 if index == 1 else float(index),
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
            self.assertIn("altitude 0.357143", text)
            self.assertIn("zout 0.000000", text)
            self.assertEqual(result["siteAltitudeKm"], 0.357142857)
            self.assertEqual(result["zoutKmAboveLocalSurface"], 0.0)
            self.assertEqual(
                result["observerElevationSemantics"],
                "site-altitude-above-sea-level; sensor-at-local-surface",
            )


if __name__ == "__main__":
    unittest.main()
