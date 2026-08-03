from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "experiment/audit.py"
RUNNER_PATH = ROOT / "experiment/runner.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


auditor = load_module("corrected_auditor", AUDIT_PATH)
runner = load_module("corrected_runner_for_audit", RUNNER_PATH)
RUN_ID = 123456789
HEAD_SHA = "a" * 40


def complete_records():
    baseline = runner.load_json(runner.BASELINE_PATH)
    alis_cases = [case for case in baseline["cases"] if case["method"] == "alis"]
    reference_cases = [case for case in baseline["cases"] if case["method"] == "reference"]
    alis_means = [sum(case["selectedNodeRadiance"][i] for case in alis_cases) / 6 for i in range(15)]
    reference_means = [sum(case["selectedNodeRadiance"][i] for case in reference_cases) / 6 for i in range(15)]
    common = [(a ** 0.35) * (r ** 0.65) for a, r in zip(alis_means, reference_means)]
    factors = [0.98, 1.01, 0.99, 1.02, 0.97, 1.03]
    records = []
    ordinal = 0
    for method, seeds, photons in (("alis", range(77101, 77107), 40_000_000), ("reference", range(77201, 77207), 160_000_000)):
        for seed, factor in zip(seeds, factors):
            ordinal += 1
            values = [value * factor for value in common]
            records.append({
                "ordinal": ordinal,
                "caseId": f"corrected-convergence-{method}-{seed}",
                "method": method,
                "seed": seed,
                "photonHistories": photons,
                "selectedNodeRadiance": values,
                "selectedPhotopicContributionCdM2": runner.selected_contribution(values),
                "elapsedSeconds": 1.0,
                "outputSha256": "1" * 64,
            })
    return records


def write_fixture(root: Path, structural: bool):
    if structural:
        cases = complete_records()[:6]
        classification = "STRUCTURAL_OR_EXECUTION_FAILURE"
        result = {
            "schemaVersion": 1,
            "stageId": runner.STAGE_ID,
            "status": "FAILED",
            "classification": classification,
            "successDoesNotAuthorizeProduction": True,
            "solverExecutionCount": 7,
            "syntaxCheckCount": 7,
            "attemptedConfiguredMcPhotonsSum": 400_000_000,
            "completedConfiguredMcPhotonsSum": 240_000_000,
            "structuralFailure": {"code": "solver-failure", "caseId": "corrected-convergence-reference-77201"},
            "authorizationConsumed": True,
            "cases": cases,
            "analysis": None,
        }
        conclusion = "failure"
    else:
        cases = complete_records()
        analysis = runner.analyze(cases, runner.load_json(runner.BASELINE_PATH), runner.load_json(runner.CONTRACT_PATH))
        classification = analysis["classification"]
        result = {
            "schemaVersion": 1,
            "stageId": runner.STAGE_ID,
            "status": "COMPLETED",
            "classification": classification,
            "successDoesNotAuthorizeProduction": True,
            "solverExecutionCount": 12,
            "syntaxCheckCount": 12,
            "attemptedConfiguredMcPhotonsSum": 1_200_000_000,
            "completedConfiguredMcPhotonsSum": 1_200_000_000,
            "structuralFailure": None,
            "authorizationConsumed": True,
            "cases": cases,
            "analysis": analysis,
        }
        conclusion = "success"
    result_bytes = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode()
    run_manifest = {
        "schemaVersion": 1,
        "stageId": runner.STAGE_ID,
        "authorizationCommit": HEAD_SHA,
        "authorizationParentCommit": "b" * 40,
        "authorization": {},
        "solverExecutionCount": result["solverExecutionCount"],
        "syntaxCheckCount": result["syntaxCheckCount"],
        "attemptedConfiguredMcPhotonsSum": result["attemptedConfiguredMcPhotonsSum"],
        "completedConfiguredMcPhotonsSum": result["completedConfiguredMcPhotonsSum"],
        "classification": classification,
        "resultSha256": hashlib.sha256(result_bytes).hexdigest(),
    }
    zip_path = root / "artifact.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("output/analysis-result.json", result_bytes)
        archive.writestr("output/run-manifest.json", json.dumps(run_manifest, indent=2, sort_keys=True) + "\n")
    metadata = {
        "run": {
            "id": RUN_ID,
            "head_sha": HEAD_SHA,
            "status": "completed",
            "conclusion": conclusion,
            "run_attempt": 1,
            "event": "push",
            "head_branch": runner.AUTH_BRANCH,
        },
        "artifact": {
            "id": 99,
            "name": "corrected-spectral-convergence-run",
            "size_in_bytes": zip_path.stat().st_size,
            "digest": "sha256:" + hashlib.sha256(zip_path.read_bytes()).hexdigest(),
        },
    }
    metadata_path = root / "metadata.json"
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    return zip_path, metadata_path


class AuditTests(unittest.TestCase):
    def test_complete_artifact_is_independently_recomputed(self):
        with tempfile.TemporaryDirectory() as directory:
            zip_path, metadata_path = write_fixture(Path(directory), structural=False)
            summary = auditor.audit(zip_path, metadata_path, RUN_ID, HEAD_SHA)
        self.assertTrue(summary["verified"])
        self.assertTrue(summary["scientificClassificationAvailable"])
        self.assertEqual(summary["classification"], "BOTH_CONVERGE_AND_AGREE")
        self.assertEqual(summary["completeCaseCount"], 12)

    def test_structural_artifact_is_verified_without_fake_scientific_metrics(self):
        with tempfile.TemporaryDirectory() as directory:
            zip_path, metadata_path = write_fixture(Path(directory), structural=True)
            summary = auditor.audit(zip_path, metadata_path, RUN_ID, HEAD_SHA)
        self.assertTrue(summary["verified"])
        self.assertFalse(summary["scientificClassificationAvailable"])
        self.assertEqual(summary["classification"], "STRUCTURAL_OR_EXECUTION_FAILURE")
        self.assertEqual(summary["completeCaseCount"], 6)

    def test_digest_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            zip_path, metadata_path = write_fixture(Path(directory), structural=False)
            metadata = json.loads(metadata_path.read_text())
            metadata["artifact"]["digest"] = "sha256:" + "f" * 64
            metadata_path.write_text(json.dumps(metadata))
            with self.assertRaises(auditor.AuditFailure):
                auditor.audit(zip_path, metadata_path, RUN_ID, HEAD_SHA)


if __name__ == "__main__":
    unittest.main()
