from __future__ import annotations

import copy
import importlib.util
import json
import math
import shutil
import statistics
import sys
import tempfile
import unittest
from pathlib import Path

from tests.test_surrogate_training_v2_continuation_handoff import ContinuationHandoffTests


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class ContinuationFinalHandoffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.directory = cls.root / "modeling/surrogate-training-v2"
        cls.final = load(
            cls.directory / "continuation_final_handoff.py",
            "surrogate_training_v2_continuation_final_handoff_test",
        )
        ContinuationHandoffTests.setUpClass()
        cls.fixture_test = ContinuationHandoffTests()

    def combined_fixture(self, root: Path, *, with_wave3: bool):
        paths, rows = self.fixture_test.fixture(root)
        combined = root / "combined"
        shutil.copytree(paths["wave1"], combined)
        shutil.copytree(paths["wave2"], combined, dirs_exist_ok=True)
        if with_wave3:
            source = next(
                row
                for row in rows.values()
                if row["groupId"] == "train-0003" and row["block"] == 6
            )
            wave3_values = []
            for block, factor in ((7, 1.0001), (8, 0.9999)):
                row = copy.deepcopy(source)
                row.update(
                    {
                        "stageId": self.final.WAVE3_RESULT_STAGE,
                        "caseId": f"train-0003-precision-continuation-wave3-v1-b{block}",
                        "block": block,
                        "seed": 900000 + block,
                        "selectedNodeRadiance": [
                            float(value) * factor
                            for value in source["selectedNodeRadiance"]
                        ],
                    }
                )
                row["selectedPhotopicContributionCdM2"] = self.fixture_test.handoff._photopic(
                    row["selectedNodeRadiance"]
                )
                row["zeroHit"] = False
                row["contentSha256"] = self.fixture_test.handoff.canonical_sha256(
                    {key: value for key, value in row.items() if key != "contentSha256"}
                )
                target = combined / row["caseId"] / "case-result.json"
                self.fixture_test._dump(target, row)
                wave3_values.append(row["selectedPhotopicContributionCdM2"])
            analysis = json.loads(paths["final_analysis"].read_text())
            point = next(
                item
                for item in analysis["analysis"]["points"]
                if item["geometryId"] == "train-0003"
            )
            values = [float(value) for value in point["valuesCdM2"]] + wave3_values
            mean = statistics.fmean(values)
            sample_std = statistics.stdev(values)
            rsem = sample_std / math.sqrt(len(values)) / mean
            point.update(
                {
                    "blockCount": 8,
                    "valuesCdM2": values,
                    "nonzeroBlockValuesCdM2": values,
                    "relativeStandardErrorOfMean": rsem,
                    "zeroHitBlockCount": 0,
                    "zeroHitBlockFraction": 0.0,
                    "classification": "PRECISION_TARGET_MET",
                    "numericalStatus": "NUMERICALLY_CONVERGED_TARGET",
                    "capReached": True,
                    "scientificallyEligible": True,
                }
            )
            analysis["analysisSha256"] = self.fixture_test.handoff.canonical_sha256(
                {key: value for key, value in analysis.items() if key != "analysisSha256"}
            )
            self.fixture_test._dump(paths["final_analysis"], analysis)
        return paths, combined

    def build_final(self, root: Path, *, with_wave3: bool):
        paths, combined = self.combined_fixture(root, with_wave3=with_wave3)
        return self.final.build(
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

    def test_accepts_full_b3_b8_evidence_in_one_combined_root(self):
        with tempfile.TemporaryDirectory() as raw:
            result = self.build_final(Path(raw), with_wave3=True)
            dataset = json.loads(result["dataset"].read_text())
            record = next(
                item for item in dataset["records"] if item["geometryId"] == "train-0003"
            )
            self.assertEqual(record["statistics"]["blockCount"], 8)
            self.assertEqual(len(record["caseIds"]), 8)
            self.assertTrue(
                record["caseIds"][-1].endswith("precision-continuation-wave3-v1-b8")
            )
            self.assertEqual(record["classification"], "PRECISION_TARGET_MET")
            self.assertTrue(record["scientificallyEligible"])

    def test_same_wrapper_accepts_terminal_b3_b6_without_wave3(self):
        with tempfile.TemporaryDirectory() as raw:
            result = self.build_final(Path(raw), with_wave3=False)
            dataset = json.loads(result["dataset"].read_text())
            record = next(
                item for item in dataset["records"] if item["geometryId"] == "train-0003"
            )
            self.assertEqual(record["statistics"]["blockCount"], 6)
            self.assertEqual(len(record["caseIds"]), 6)

    def test_refuses_unreviewed_wave3_stage(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            paths, combined = self.combined_fixture(root, with_wave3=True)
            target = next(
                path
                for path in combined.rglob("case-result.json")
                if "wave3-v1-b7" in str(path)
            )
            row = json.loads(target.read_text())
            row["stageId"] = "unreviewed-wave-three-stage"
            row["contentSha256"] = self.fixture_test.handoff.canonical_sha256(
                {key: value for key, value in row.items() if key != "contentSha256"}
            )
            self.fixture_test._dump(target, row)
            with self.assertRaisesRegex(Exception, "continuation result stage changed"):
                self.final.build(
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
