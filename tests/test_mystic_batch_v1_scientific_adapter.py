from __future__ import annotations

import importlib.util
import json
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


adapter = load_module("mystic_batch_scientific_adapter", PACKAGE / "scientific_adapter.py")
probe = load_module("mystic_batch_runtime_probe", PACKAGE / "runtime_probe.py")


class ScientificAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.data = self.root / "data"
        (self.data / "solar_flux").mkdir(parents=True)
        (self.data / "atmmod").mkdir(parents=True)
        (self.data / "solar_flux" / "atlas_plus_modtran").write_text("solar\n")
        (self.data / "atmmod" / "afglus.dat").write_text("atmosphere\n")
        self.grid = self.root / "twilight-grid.dat"
        self.grid.write_text("380\n470\n550\n660\n780\n")
        self.atmosphere = self.data / "atmmod" / "afglus.dat"
        self.runtime_lock = self.root / "runtime-lock.json"
        self.runtime_lock.write_text((PACKAGE / "runtime-lock.micromamba.json").read_text())
        self.uvspec = self.root / "uvspec"
        self.uvspec.write_text("#!/bin/sh\nprintf 'fake uvspec help\\n'\n")
        self.uvspec.chmod(0o755)
        self.runtime_report_path = self.root / "runtime-report.json"
        report = probe.build_report(self.uvspec, self.data, self.atmosphere, self.runtime_lock, skip_help=False)
        self.runtime_report_path.write_text(probe.dump_json(report))
        self.manifest_path = self.root / "manifest.json"
        self.manifest_path.write_text(adapter.dump_json(self.make_manifest(report)))

    def tearDown(self) -> None:
        self.temp.cleanup()

    def make_manifest(self, report: dict) -> dict:
        return {
            "schemaVersion": 1,
            "stageId": "mystic-batch-v1",
            "batchId": "reference-anchor-template-v1",
            "mode": "scientific",
            "scientificExecution": True,
            "adapterId": "mystic-spectral-radiance-v1",
            "runtime": {
                "kind": "micromamba-lock",
                "containerImageDigest": None,
                "exactPackageSpec": "rubin-libradtran=2.0.6=py312pl5321he9373c2_1",
                "uvspecSha256": report["uvspecSha256"],
                "uvspecHelpSha256": report["uvspecHelpSha256"],
                "libRadtranDataTreeSha256": report["libRadtranDataTreeSha256"],
                "atmosphereSha256": report["atmosphereSha256"],
                "runtimeLockRawSha256": report["runtimeLockRawSha256"],
            },
            "limits": {
                "maximumCases": 6,
                "maximumParallel": 6,
                "maximumConfiguredMcPhotonsSum": 960000000,
                "perCaseTimeoutSeconds": 1200,
            },
            "frozenInputs": {
                "wavelengthDomainNm": [380, 780],
                "diagnosticNodesNm": [470, 480, 490, 500, 510, 520, 530, 540, 560, 580, 590, 600, 610, 640, 660],
                "molecularAbsorption": "crs",
                "mcSpherical": "1D",
                "mcVroom": "on",
                "aod550": 0.15,
                "albedo": 0.15,
                "dataPaths": {
                    "solarFlux": {"root": "libRadtranData", "path": "solar_flux/atlas_plus_modtran"},
                    "wavelengthGrid": {"root": "repository", "path": "twilight-grid.dat"},
                    "atmosphere": {"root": "libRadtranData", "path": "atmmod/afglus.dat"},
                },
            },
            "cases": [{
                "ordinal": 1,
                "caseId": "reference-seed-77301",
                "seed": 77301,
                "photonHistories": 160000000,
                "parameters": {
                    "sunDepressionDeg": 12.0,
                    "targetAltitudeDeg": 10.0,
                    "relativeAzimuthDeg": 120.0,
                    "observerElevationM": 0.0,
                },
            }],
        }

    def test_runtime_probe_captures_reproducible_identity_without_solver(self) -> None:
        first = probe.build_report(self.uvspec, self.data, self.atmosphere, self.runtime_lock)
        second = probe.build_report(self.uvspec, self.data, self.atmosphere, self.runtime_lock)
        self.assertEqual(first["uvspecSha256"], second["uvspecSha256"])
        self.assertEqual(first["libRadtranDataTreeSha256"], second["libRadtranDataTreeSha256"])
        self.assertFalse(first["scientificSolverExecuted"])
        self.assertFalse(first["syntaxCheckExecuted"])

    def test_adapter_prepares_exact_reference_input_without_execution(self) -> None:
        output = self.root / "prepared"
        proposal = adapter.prepare_case(self.manifest_path, self.runtime_report_path, "reference-seed-77301", self.data, self.root, output)
        resolved = (output / "reference-seed-77301" / "input-resolved.txt").read_text()
        self.assertEqual(proposal["status"], "PREPARED_NO_SOLVER")
        self.assertFalse(proposal["scientificSolverExecuted"])
        self.assertIn("sza 102.000000", resolved)
        self.assertIn("umu -0.17364818", resolved)
        self.assertIn("phi 120.000000", resolved)
        self.assertIn("mc_photons 160000000", resolved)
        self.assertIn("mc_randomseed 77301", resolved)
        self.assertIn("mc_vroom on", resolved)
        self.assertIn("wavelength 380 780", resolved)

    def test_adapter_refuses_runtime_identity_mismatch(self) -> None:
        manifest = json.loads(self.manifest_path.read_text())
        manifest["runtime"]["uvspecSha256"] = "f" * 64
        self.manifest_path.write_text(adapter.dump_json(manifest))
        with self.assertRaises(adapter.AdapterRefusal) as caught:
            adapter.prepare_case(self.manifest_path, self.runtime_report_path, "reference-seed-77301", self.data, self.root, self.root / "rejected")
        self.assertEqual(caught.exception.code, "runtime-identity")

    def test_adapter_refuses_path_traversal(self) -> None:
        manifest = json.loads(self.manifest_path.read_text())
        manifest["frozenInputs"]["dataPaths"]["wavelengthGrid"]["path"] = "../outside.dat"
        self.manifest_path.write_text(adapter.dump_json(manifest))
        with self.assertRaises(adapter.AdapterRefusal) as caught:
            adapter.prepare_case(self.manifest_path, self.runtime_report_path, "reference-seed-77301", self.data, self.root, self.root / "rejected-path")
        self.assertEqual(caught.exception.code, "invalid-path")

    def test_adapter_refuses_unsupported_mystic_configuration(self) -> None:
        manifest = json.loads(self.manifest_path.read_text())
        manifest["frozenInputs"]["mcSpherical"] = "3D"
        self.manifest_path.write_text(adapter.dump_json(manifest))
        with self.assertRaises(adapter.AdapterRefusal) as caught:
            adapter.prepare_case(self.manifest_path, self.runtime_report_path, "reference-seed-77301", self.data, self.root, self.root / "rejected-config")
        self.assertEqual(caught.exception.code, "mc-spherical")


if __name__ == "__main__":
    unittest.main()
