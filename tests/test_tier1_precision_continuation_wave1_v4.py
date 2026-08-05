from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V4 = ROOT / "experiments/tier1-precision-continuation-wave1-v4"
EVIDENCE = ROOT / "evidence/tier1-precision-continuation-wave1-v4"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


p = load(V4 / "package.py", "wave1_v4_test_package")
e = load(V4 / "execution.py", "wave1_v4_test_execution")


def fake_results(prereg):
    _, base, _, _, _, _ = p._proposal(ROOT)
    node = 1.0 / (6.83002 * sum(base.CIE))
    nodes = [node] * len(base.CIE)
    value = base._photopic_value(nodes)
    rows = []
    for case in prereg["cases"]:
        rows.append({
            "caseId": case["caseId"],
            "seed": case["seed"],
            "role": case["role"],
            "block": case["block"],
            "photonHistories": case["photonHistories"],
            "alisSpectralImportanceSamplingNm": case["alisSpectralImportanceSamplingNm"],
            "geometrySha256": case["geometrySha256"],
            "status": "COMPLETED",
            "syntaxCheckCount": 1,
            "solverExecutionCount": 1,
            "syntax": {"exitCode": 0, "timedOut": False},
            "solver": {"exitCode": 0, "timedOut": False},
            "valueCdM2": value,
            "selectedNodeRadiance": nodes,
            "artifactSha256": "1" * 64,
            "inputSha256": "2" * 64,
            "radianceOutputSha256": "3" * 64,
            "stdOutputSha256": "4" * 64,
            "runtimeSha256": "5" * 64,
        })
    return rows


class Wave1V4Tests(unittest.TestCase):
    def test_build_is_deterministic_closed_and_exact(self):
        first = p.build_preregistration(ROOT)
        second = p.build_preregistration(ROOT)
        self.assertEqual(first, second)
        p.validate_preregistration(first, ROOT)
        self.assertEqual(first["caseCount"], 40)
        self.assertEqual(first["geometryCount"], 20)
        self.assertEqual(first["maximumConfiguredPhotonHistories"], 5_100_000_000)
        self.assertEqual(first["roleCounts"], {
            "surrogateTrainingGeometries": 17,
            "internalHoldoutGeometries": 3,
            "surrogateTrainingCases": 34,
            "internalHoldoutCases": 6,
        })
        self.assertIsNone(first["authorizationOrdinal"])
        self.assertFalse(first["authorizationEnabled"])
        self.assertFalse(first["dispatchEnabled"])
        self.assertFalse(first["scientificExecution"])

    def test_seed_universe_is_fresh_against_all_consumed_and_future(self):
        value = p.build_preregistration(ROOT)
        proof = value["seedProof"]
        self.assertEqual(proof["preOrdinal8HistoricalSeedCount"], 196)
        self.assertEqual(proof["ordinal8WaveSeedCount"], 40)
        self.assertEqual(proof["ordinal9WaveSeedCount"], 40)
        self.assertEqual(proof["replacementWaveSeedCount"], 40)
        self.assertTrue(proof["allReplacementSeedsUnique"])
        self.assertEqual(proof["historicalOverlap"], [])
        self.assertEqual(proof["ordinal8Overlap"], [])
        self.assertEqual(proof["ordinal9Overlap"], [])
        self.assertEqual(proof["futureWaveOverlap"], [])

    def test_candidate_review_and_template_allocate_nothing(self):
        prereg = p.build_preregistration(ROOT)
        packet = p.candidate_review(prereg, ROOT)
        auth = p.authorization_template(prereg, ROOT)
        self.assertFalse(packet["authorizationAllocated"])
        self.assertFalse(packet["dispatchEnabled"])
        self.assertFalse(packet["scientificExecution"])
        self.assertFalse(auth["enabled"])
        self.assertIsNone(auth["authorizationOrdinal"])
        self.assertIsNone(auth["authorizationRef"])
        self.assertIsNone(auth["executionKey"])

    def test_matrix_cli_runs_through_real_bash_and_writes_one_valid_line(self):
        prereg = p.build_preregistration(ROOT)
        manifest = {"cases": prereg["cases"]}
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manifest_path = root / "execution-manifest.json"
            output_path = root / "github-output.txt"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            command = "set -euo pipefail; python \"$1\" --manifest \"$2\" --github-output \"$GITHUB_OUTPUT\""
            env = dict(os.environ)
            env["GITHUB_OUTPUT"] = str(output_path)
            subprocess.run(["bash", "-c", command, "bash", str(V4 / "matrix_output.py"), str(manifest_path)], check=True, env=env)
            lines = output_path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0].startswith("matrix="))
        matrix = json.loads(lines[0].split("=", 1)[1])
        self.assertEqual(len(matrix["include"]), 40)
        self.assertTrue(all(row["timeoutSeconds"] == 2400 for row in matrix["include"]))

    def test_complete_synthetic_aggregate_audit_analysis_path(self):
        prereg = p.build_preregistration(ROOT)
        results = fake_results(prereg)
        aggregate = p.aggregate_wave1(prereg, results, ROOT)
        self.assertEqual(aggregate["aggregate"]["status"], "COMPLETED")
        self.assertEqual(aggregate["aggregate"]["caseCountObserved"], 40)
        audit = p.audit_wave1(prereg, results, aggregate, ROOT)
        self.assertEqual(audit["audit"]["status"], "PASSED")
        analysis = p.analyze_wave1(prereg, aggregate, audit, ROOT)
        self.assertEqual(analysis["analysis"]["status"], "CONTINUATION_ANALYZED")
        self.assertFalse(analysis["surrogateFitAuthorized"])
        self.assertFalse(analysis["internalHoldoutOpened"])

    def test_execution_identity_is_ordinal10_and_dynamic_prereg_binding(self):
        self.assertEqual(e.AUTHORIZATION_ORDINAL, 10)
        self.assertEqual(e.EXECUTION_KEY, "twilight-surrogate-tier-1-v1:numerical:10")
        self.assertEqual(e.RUN_TITLE, "Tier-1 precision continuation wave 1 ordinal 10")
        self.assertNotIn("EXPECTED_PREREGISTRATION_SHA256", (V4 / "execution.py").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
