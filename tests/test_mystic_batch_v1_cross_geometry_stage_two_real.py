from __future__ import annotations

import hashlib
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "experiments" / "mystic-batch-v1"
RESULTS = PACKAGE / "results"
SOURCE_MANIFEST = PACKAGE / "manifest.cross-geometry-pilot.proposal.json"
SOURCE_ANALYSIS = RESULTS / "screening-analysis.cross-geometry-pilot-screening-2.json"
PROPOSAL = PACKAGE / "manifest.cross-geometry-stage-two.proposal.json"
PROVENANCE = RESULTS / "stage-two-source-provenance.json"
STAGE_TWO = PACKAGE / "cross_geometry_stage_two.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path: Path):
    return json.loads(path.read_text())


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


stage_two = load_module("cross_geometry_stage_two_real", STAGE_TWO)


class CrossGeometryStageTwoRealProposalTests(unittest.TestCase):
    def test_committed_proposal_is_exact_generator_output(self) -> None:
        generated = stage_two.build(SOURCE_MANIFEST, SOURCE_ANALYSIS)
        self.assertEqual(load_json(PROPOSAL), generated)

    def test_frozen_source_selects_only_predeclared_expandable_geometries(self) -> None:
        analysis = load_json(SOURCE_ANALYSIS)
        selected = sorted(
            result["groupId"]
            for result in analysis["geometryResults"]
            if result["classification"] in stage_two.EXPANDABLE
        )
        self.assertEqual(
            selected,
            [
                "g01-reference-bridge",
                "g04-mid-perpendicular",
                "g05-mid-opposite-low",
                "g06-late-opposite-high-aerosol",
            ],
        )
        self.assertEqual(analysis["classificationCounts"]["NEEDS_MORE_BLOCKS"], 4)
        self.assertEqual(analysis["classificationCounts"]["SCREENING_AGREEMENT"], 2)
        self.assertEqual(analysis["classificationCounts"]["SCREENING_DISCREPANCY"], 0)
        self.assertEqual(analysis["classificationCounts"]["STRUCTURAL_OR_EXECUTION_FAILURE"], 0)

    def test_exact_fresh_case_and_photon_accounting(self) -> None:
        source = load_json(SOURCE_MANIFEST)
        proposal = load_json(PROPOSAL)
        self.assertIs(proposal["proposalOnly"], True)
        self.assertIs(proposal["scientificExecution"], False)
        self.assertEqual(len(proposal["cases"]), 16)
        self.assertEqual(sum(case["photonHistories"] for case in proposal["cases"]), 320_000_000)
        self.assertEqual({case["block"] for case in proposal["cases"]}, {3, 4})
        self.assertEqual({case["method"] for case in proposal["cases"]}, {"reference-vroom", "alis"})
        self.assertEqual(len({case["caseId"] for case in proposal["cases"]}), 16)
        self.assertEqual(len({case["seed"] for case in proposal["cases"]}), 16)
        source_seeds = {case["seed"] for case in source["cases"]}
        self.assertFalse(source_seeds.intersection(case["seed"] for case in proposal["cases"]))
        self.assertEqual(proposal["limits"]["maximumConfiguredMcPhotonsSum"], 320_000_000)
        self.assertEqual(proposal["limits"]["maximumParallel"], 6)

    def test_source_provenance_binds_the_completed_artifact_pipeline(self) -> None:
        analysis = load_json(SOURCE_ANALYSIS)
        proposal = load_json(PROPOSAL)
        provenance = load_json(PROVENANCE)
        self.assertEqual(provenance["sourceScientificRunId"], 30856116586)
        self.assertEqual(provenance["sourcePostprocessRunId"], 30858046820)
        self.assertEqual(
            provenance["sourceAuthorizationRef"],
            "018f61ef8f83c00e69d7d72b301fd37ba0de3c0a",
        )
        self.assertEqual(provenance["sourceAuthorizationOrdinal"], 2)
        self.assertEqual(provenance["sourcePostprocessArtifactId"], 8873226100)
        self.assertEqual(
            provenance["sourcePostprocessArtifactDigest"],
            "sha256:32ade5a6f72562b77f25d4e5232c0d51f4cc82171497f5a02965760c026cf736",
        )
        self.assertEqual(provenance["sourceAnalysisRawSha256"], raw_sha256(SOURCE_ANALYSIS))
        self.assertEqual(proposal["sourceAnalysisRawSha256"], raw_sha256(SOURCE_ANALYSIS))
        self.assertEqual(proposal["sourceManifestRawSha256"], analysis["proposalRawSha256"])
        self.assertIs(provenance["authorizationCreated"], False)
        self.assertIs(provenance["scientificExecution"], False)


if __name__ == "__main__":
    unittest.main()
