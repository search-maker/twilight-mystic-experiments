from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

from tests.test_surrogate_training_v2_continuation_final_handoff import (
    ContinuationFinalHandoffTests,
)


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class Wave3AnalysisStageHandoffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.directory = cls.root / "modeling/surrogate-training-v2"
        cls.wrapper = load(
            cls.directory / "continuation_wave3_handoff.py",
            "surrogate_training_v2_wave3_analysis_handoff_test",
        )
        cls.adapter = load(
            cls.directory / "adapter.py",
            "surrogate_training_v2_wave3_analysis_adapter_test",
        )
        ContinuationFinalHandoffTests.setUpClass()
        cls.final_fixture = ContinuationFinalHandoffTests()

    @staticmethod
    def dump(path: Path, value):
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")

    def fixture(self, root: Path):
        paths, combined = self.final_fixture.combined_fixture(root, with_wave3=True)
        analysis = json.loads(paths["final_analysis"].read_text())
        analysis["stageId"] = self.wrapper.WAVE3_ANALYSIS_STAGE
        if "analysisSha256" in analysis:
            base = self.wrapper._final(self.root).load_base(self.root)
            analysis["analysisSha256"] = base.canonical_sha256(
                {key: value for key, value in analysis.items() if key != "analysisSha256"}
            )
        self.dump(paths["final_analysis"], analysis)
        return paths, combined

    def build(self, root: Path):
        paths, combined = self.fixture(root)
        outputs = self.wrapper.build(
            repository_root=self.root,
            source_dataset_path=paths["source_dataset"],
            source_audit_path=paths["source_audit"],
            continuation_results_root=combined,
            final_analysis_path=paths["final_analysis"],
            reference_anchors_path=paths["reference"],
            final_manifest_path=paths["manifest"],
            final_aggregate_path=paths["aggregate"],
            final_audit_path=paths["audit"],
            exact_main_sha="0" * 40,
            output_dir=root / "output",
        )
        return paths, outputs

    def test_accepts_wave3_analysis_stage_and_preserves_39_9(self):
        with tempfile.TemporaryDirectory() as raw:
            paths, outputs = self.build(Path(raw))
            dataset = json.loads(outputs["dataset"].read_text())
            record = next(
                row for row in dataset["records"] if row["geometryId"] == "train-0003"
            )
            self.assertEqual(record["statistics"]["blockCount"], 8)
            self.assertEqual(len(record["caseIds"]), 8)
            self.assertEqual(len(dataset["trainingGeometryIds"]), 39)
            self.assertEqual(len(dataset["internalHoldoutGeometryIds"]), 9)
            partitioned = self.adapter.read_tier1_dataset(
                outputs["dataset"],
                outputs["envelope"],
                outputs["design"],
                expected_main_sha="0" * 40,
            )
            self.assertEqual(len(partitioned.training), 39)
            self.assertEqual(len(partitioned.internal_holdout), 9)
            self.assertEqual(
                json.loads(paths["final_analysis"].read_text())["stageId"],
                self.wrapper.WAVE3_ANALYSIS_STAGE,
            )

    def test_refuses_wave2_analysis_stage_on_wave3_wrapper(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            paths, combined = self.final_fixture.combined_fixture(root, with_wave3=True)
            with self.assertRaisesRegex(Exception, "final continuation analysis stage changed"):
                self.wrapper.build(
                    repository_root=self.root,
                    source_dataset_path=paths["source_dataset"],
                    source_audit_path=paths["source_audit"],
                    continuation_results_root=combined,
                    final_analysis_path=paths["final_analysis"],
                    reference_anchors_path=paths["reference"],
                    final_manifest_path=paths["manifest"],
                    final_aggregate_path=paths["aggregate"],
                    final_audit_path=paths["audit"],
                    exact_main_sha="0" * 40,
                    output_dir=root / "output",
                )

    def test_refuses_exhausted_wave3_analysis(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            paths, combined = self.fixture(root)
            analysis = json.loads(paths["final_analysis"].read_text())
            analysis["analysis"]["exhaustedGeometryIds"] = ["train-0003"]
            analysis["analysis"]["scientificallyEligible"] = False
            self.dump(paths["final_analysis"], analysis)
            with self.assertRaisesRegex(Exception, "is exhausted"):
                self.wrapper.build(
                    repository_root=self.root,
                    source_dataset_path=paths["source_dataset"],
                    source_audit_path=paths["source_audit"],
                    continuation_results_root=combined,
                    final_analysis_path=paths["final_analysis"],
                    reference_anchors_path=paths["reference"],
                    final_manifest_path=paths["manifest"],
                    final_aggregate_path=paths["aggregate"],
                    final_audit_path=paths["audit"],
                    exact_main_sha="0" * 40,
                    output_dir=root / "output",
                )


if __name__ == "__main__":
    unittest.main()
