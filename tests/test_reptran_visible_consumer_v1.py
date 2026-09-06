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


consumer = load_module(
    "reptran_visible_consumer_v1",
    PACKAGE / "reptran_cross_geometry_execution_adapter_v1.py",
)


class ReptranVisibleConsumerV1Tests(unittest.TestCase):
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
        hashes = {
            "uvspecSha256": "1" * 64,
            "uvspecHelpSha256": "2" * 64,
            "libRadtranDataTreeSha256": "3" * 64,
            "atmosphereSha256": "4" * 64,
            "runtimeLockRawSha256": "5" * 64,
        }
        self.proposal = {
            "schemaVersion": 1,
            "stageId": "cross-geometry-pilot-v1",
            "mode": "scientific-proposal",
            "proposalOnly": True,
            "scientificExecution": False,
            "successDoesNotAuthorizeProduction": True,
            "adapterId": "mystic-cross-geometry-v1",
            "batchId": "reptran-consumer-contract-v1",
            "runtime": hashes,
            "frozenInputs": {
                "albedo": 0.15,
                "wavelengthDomainNm": [380, 780],
                "diagnosticNodesNm": [500, 550, 600],
                "molecularAbsorption": "reptran",
                "mcSpherical": "1D",
                "alisSpectralImportanceSamplingNm": 550.0,
                "dataPaths": {
                    "solarFlux": {
                        "root": "libRadtranData",
                        "path": "solar_flux/atlas_plus_modtran",
                    },
                    "wavelengthGrid": {"root": "repository", "path": "grid.dat"},
                    "atmosphere": {"root": "libRadtranData", "path": "atmmod/afglus.dat"},
                },
            },
            "geometries": [
                {
                    "geometryId": "g-train-0054",
                    "sunDepressionDeg": 6.125,
                    "targetAltitudeDeg": 17.962963,
                    "relativeAzimuthDeg": 60.48,
                    "observerElevationM": 1180.758017,
                    "aod550": 0.067355,
                }
            ],
            "cases": [
                {
                    "caseId": "train-0054",
                    "groupId": "g-train-0054",
                    "method": "alis",
                    "block": 1,
                    "seed": 123456789,
                    "photonHistories": 1000,
                },
                {
                    "caseId": "diagnostic-reference",
                    "groupId": "g-train-0054",
                    "method": "reference-vroom",
                    "block": 1,
                    "seed": 123456790,
                    "photonHistories": 1000,
                },
            ],
        }
        self.runtime = {
            "schemaVersion": 1,
            "stageId": "mystic-batch-v1",
            "scientificSolverExecuted": False,
            "syntaxCheckExecuted": False,
            **hashes,
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _write_contract(self, proposal: dict | None = None, suffix: str = "") -> tuple[Path, Path]:
        proposal_path = self.root / f"proposal{suffix}.json"
        runtime_path = self.root / f"runtime{suffix}.json"
        proposal_path.write_text(json.dumps(proposal or self.proposal))
        runtime_path.write_text(json.dumps(self.runtime))
        return proposal_path, runtime_path

    def test_authoritative_consumer_wires_alis_to_reptran_ground_site_path(self) -> None:
        proposal_path, runtime_path = self._write_contract()
        prepared = consumer.prepare_case(
            proposal_path,
            runtime_path,
            "train-0054",
            self.data,
            self.root,
            self.root / "out",
        )
        text = Path(prepared["inputPath"]).read_text()
        lines = text.splitlines()
        self.assertEqual(lines.count("mol_abs_param reptran"), 1)
        self.assertNotIn("mol_abs_param crs", lines)
        self.assertEqual(lines.count("wavelength 380 780"), 1)
        self.assertEqual(lines.count("mc_spherical 1D"), 1)
        self.assertEqual(lines.count("mc_vroom off"), 1)
        self.assertEqual(lines.count("mc_spectral_is 550.0"), 1)
        self.assertEqual(lines.count("zout 0.000000"), 1)
        self.assertEqual(sum(line.startswith("atm_z_grid ") for line in lines), 1)
        self.assertFalse(any(line.startswith("altitude ") for line in lines))
        self.assertFalse(any(line.startswith("mc_elevation_file ") for line in lines))
        self.assertEqual(prepared["inputs"]["molecularAbsorption"], "reptran")
        self.assertEqual(
            prepared["renderingProof"]["route"],
            "authoritative-v1-visible-alis-reptran",
        )
        self.assertFalse(prepared["renderingProof"]["historicalCrsFallbackAllowed"])
        self.assertFalse(prepared["scientificSolverExecuted"])
        self.assertFalse(prepared["syntaxCheckExecuted"])

    def test_current_v1_consumer_refuses_crs_manifest_instead_of_falling_back(self) -> None:
        proposal = json.loads(json.dumps(self.proposal))
        proposal["frozenInputs"]["molecularAbsorption"] = "crs"
        proposal_path, runtime_path = self._write_contract(proposal, "-crs")
        with self.assertRaises(consumer.AdapterRefusal):
            consumer.prepare_case(
                proposal_path,
                runtime_path,
                "train-0054",
                self.data,
                self.root,
                self.root / "out-crs",
            )

    def test_reference_vroom_is_explicit_historical_crs_diagnostic_only(self) -> None:
        proposal_path, runtime_path = self._write_contract()
        prepared = consumer.prepare_case(
            proposal_path,
            runtime_path,
            "diagnostic-reference",
            self.data,
            self.root,
            self.root / "out-ref",
        )
        text = Path(prepared["inputPath"]).read_text()
        self.assertEqual(text.splitlines().count("mol_abs_param crs"), 1)
        self.assertNotIn("mol_abs_param reptran", text.splitlines())
        self.assertEqual(
            prepared["renderingProof"]["route"],
            "historical-reference-vroom-crs-diagnostic-only",
        )

    def test_route_is_isolated_from_historical_and_protected_consumers(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "mystic-batch-v1-cross-geometry-execution.yml").read_text()
        self.assertEqual(
            workflow.count(
                "EXECUTION_ADAPTER: experiments/mystic-batch-v1/reptran_cross_geometry_execution_adapter_v1.py"
            ),
            1,
        )
        historical = (PACKAGE / "cross_geometry_execution_adapter.py").read_text()
        self.assertNotIn("reptran_visible_renderer_v1.py", historical)
        self.assertNotIn("V1_VISIBLE_MOLECULAR_ABSORPTION", historical)
        self.assertNotIn("render_current_v1_case", historical)
        self.assertIn(
            "text = adapter.render_input(inputs, data_dir.resolve(), repository_root.resolve(), case_dir.resolve())",
            historical,
        )
        protected = (ROOT / ".github" / "workflows" / "jerusalem-tishrei-direct-mystic-v2-package-validation.yml").read_text()
        self.assertNotIn("reptran_cross_geometry_execution_adapter_v1.py", protected)
        self.assertIn("experiments/mystic-batch-v1/cross_geometry_execution_adapter.py", protected)


if __name__ == "__main__":
    unittest.main()
