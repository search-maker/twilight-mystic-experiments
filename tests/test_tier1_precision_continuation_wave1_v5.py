from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
V5 = ROOT / "experiments/tier1-precision-continuation-wave1-v5"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


p = load(V5 / "package.py", "wave1_v5_test_package")
e = load(V5 / "execution.py", "wave1_v5_test_execution")
x = load(V5 / "case_executor.py", "wave1_v5_test_case_executor")


def fake_results(prereg):
    _, base, _, _, _, _ = p._core().proposal(ROOT)
    node = 1.0 / (6.83002 * sum(base.CIE))
    nodes = [node] * len(base.CIE)
    value = base._photopic_value(nodes)
    return [{
        "caseId": case["caseId"], "seed": case["seed"], "role": case["role"], "block": case["block"],
        "photonHistories": case["photonHistories"], "alisSpectralImportanceSamplingNm": case["alisSpectralImportanceSamplingNm"],
        "geometrySha256": case["geometrySha256"], "status": "COMPLETED", "syntaxCheckCount": 1,
        "solverExecutionCount": 1, "syntax": {"exitCode": 0, "timedOut": False},
        "solver": {"exitCode": 0, "timedOut": False}, "valueCdM2": value,
        "selectedNodeRadiance": nodes, "artifactSha256": "1" * 64, "inputSha256": "2" * 64,
        "radianceOutputSha256": "3" * 64, "stdOutputSha256": "4" * 64, "runtimeSha256": "5" * 64,
    } for case in prereg["cases"]]


class Wave1V5Tests(unittest.TestCase):
    def test_preregistration_is_exact_closed_and_fresh(self):
        first = p.build_preregistration(ROOT)
        self.assertEqual(first, p.build_preregistration(ROOT))
        p.validate_preregistration(first, ROOT)
        self.assertEqual((first["caseCount"], first["geometryCount"], first["maximumConfiguredPhotonHistories"]), (40, 20, 5_100_000_000))
        self.assertEqual(first["roleCounts"], {"surrogateTrainingGeometries": 17, "internalHoldoutGeometries": 3, "surrogateTrainingCases": 34, "internalHoldoutCases": 6})
        proof = first["seedProof"]
        self.assertEqual((proof["preOrdinal8HistoricalSeedCount"], proof["ordinal8WaveSeedCount"], proof["ordinal9WaveSeedCount"], proof["ordinal10WaveSeedCount"], proof["replacementWaveSeedCount"]), (196, 40, 40, 40, 40))
        for key in ("historicalOverlap", "ordinal8Overlap", "ordinal9Overlap", "ordinal10Overlap", "futureWaveOverlap"):
            self.assertEqual(proof[key], [])
        self.assertFalse(first["authorizationEnabled"])
        self.assertFalse(first["dispatchEnabled"])

    def test_candidate_and_template_allocate_nothing(self):
        prereg = p.build_preregistration(ROOT)
        packet = p.candidate_review(prereg, ROOT)
        template = p.authorization_template(prereg, ROOT)
        self.assertFalse(packet["authorizationAllocated"])
        self.assertFalse(packet["scientificExecution"])
        self.assertFalse(template["enabled"])
        self.assertIsNone(template["authorizationOrdinal"])
        self.assertIsNone(template["authorizationRef"])

    def test_complete_synthetic_postprocess_path(self):
        prereg = p.build_preregistration(ROOT)
        post = load(V5 / "postprocess.py", "wave1_v5_test_postprocess")
        results = fake_results(prereg)
        aggregate = post.aggregate_wave1(prereg, results, ROOT)
        self.assertEqual(aggregate["aggregate"]["caseCountObserved"], 40)
        audit = post.audit_wave1(prereg, results, aggregate, ROOT)
        self.assertEqual(audit["audit"]["status"], "PASSED")
        analysis = post.analyze_wave1(prereg, aggregate, audit, ROOT)
        self.assertEqual(analysis["analysis"]["status"], "CONTINUATION_ANALYZED")
        self.assertFalse(analysis["surrogateFitAuthorized"])

    def test_executor_binds_directly_to_callable_v2_api(self):
        base = x._base(ROOT)
        for name in ("execute_case", "dump", "parse_spectrum", "verify_context"):
            self.assertTrue(callable(getattr(base, name, None)), name)
        source = (V5 / "case_executor.py").read_text(encoding="utf-8")
        self.assertIn("tier1-precision-continuation-wave1-v2/case_executor.py", source)
        self.assertNotIn("tier1-precision-continuation-wave1-v3/case_executor.py", source)
        self.assertNotIn("tier1-precision-continuation-wave1-v4/case_executor.py", source)

    def test_executor_fake_runner_performs_one_syntax_one_solver_and_writes_result(self):
        case_id = "train-0003-precision-continuation-v5-b3"
        with tempfile.TemporaryDirectory() as raw:
            temp = Path(raw)
            manifest = temp / "manifest.json"
            runtime = temp / "runtime.json"
            adapter = temp / "adapter.py"
            output = temp / "output"
            manifest.write_text(json.dumps({"manifestSha256": "f" * 64, "cases": [{"caseId": case_id, "groupId": "train-0003", "block": 3, "role": "surrogate-training", "seed": 644726611, "photonHistories": 100000000}]}), encoding="utf-8")
            runtime.write_text("{}\n", encoding="utf-8")
            adapter.write_text(
                "import hashlib\nfrom pathlib import Path\n"
                "def prepare_case(manifest_path,runtime_report_path,case_id,data_dir,repository_root,output_root):\n"
                " d=output_root/case_id; d.mkdir(parents=True); text='source solar\\n'; (d/'input-resolved.txt').write_text(text); return {'inputResolvedSha256':hashlib.sha256(text.encode()).hexdigest()}\n",
                encoding="utf-8",
            )
            calls = []
            def runner(command, text, cwd, timeout):
                calls.append(list(command))
                if len(calls) == 2:
                    spectrum = "".join(f"{node} 1.0\\n" for node in x._base(ROOT).NODES)
                    (cwd / "mc.rad.spc").write_text(spectrum, encoding="utf-8")
                    (cwd / "mc.rad.std.spc").write_text(spectrum, encoding="utf-8")
                return {"exitCode": 0, "timedOut": False, "stdout": "", "stderr": ""}
            env = {"GITHUB_ACTIONS": "true", "GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_RUN_ATTEMPT": "1"}
            with mock.patch.dict(os.environ, env, clear=False):
                result = x.execute_case(manifest, runtime, adapter, case_id, temp, ROOT, Path("/fake/uvspec"), output, 2400, True, runner=runner)
            self.assertEqual(len(calls), 2)
            self.assertEqual(result["stageId"], x.STAGE_ID)
            self.assertEqual(result["syntaxCheckCount"], 1)
            self.assertEqual(result["solverExecutionCount"], 1)
            self.assertEqual(result["contentSha256"], x._base(ROOT).canonical_sha256({k: v for k, v in result.items() if k != "contentSha256"}))
            self.assertTrue((output / case_id / "case-result.json").is_file())

    def test_error_serializer_is_independent_and_identity_is_ordinal11(self):
        self.assertEqual(e.AUTHORIZATION_ORDINAL, 11)
        self.assertEqual(e.EXECUTION_KEY, "twilight-surrogate-tier-1-v1:numerical:11")
        payload = json.loads(x.dump({"status": "REFUSED", "reason": "test"}))
        self.assertEqual(payload["status"], "REFUSED")


if __name__ == "__main__":
    unittest.main()
