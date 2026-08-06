from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.test_tier1_precision_continuation_wave3_v1 import Wave3V1Tests


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Wave3ExecutionV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.directory = cls.root / "experiments/tier1-precision-continuation-wave3-v1"
        cls.package = load(cls.directory / "package.py", "wave3_execution_test_package")
        cls.execution = load(cls.directory / "execution.py", "wave3_execution_test_driver")
        cls.postprocess = load(cls.directory / "postprocess.py", "wave3_execution_test_postprocess")
        cls.executor = load(cls.directory / "case_executor.py", "wave3_execution_test_case_executor")
        cls.matrix = load(cls.directory / "matrix_output.py", "wave3_execution_test_matrix")
        Wave3V1Tests.setUpClass()
        cls.source_fixture = Wave3V1Tests()

    def source_path(self, root: Path) -> Path:
        return self.source_fixture.write_source(root)

    def manifest(self, root: Path):
        source_path = self.source_path(root)
        prereg = self.package.build_preregistration(
            self.package.load_json(source_path), source_path, self.root
        )
        head = "1" * 40
        authorization_ref = "2" * 40
        context = {
            "eventName": "workflow_dispatch",
            "runAttempt": 1,
            "displayTitle": self.execution.RUN_TITLE,
            "authorizationOrdinal": 13,
            "executionKey": self.execution.EXECUTION_KEY,
            "headBranch": "main",
            "headSha": head,
            "authorizationRef": authorization_ref,
            "runId": 616161,
        }
        authorization = {
            "schemaVersion": 1,
            "stageId": "tier1-precision-continuation-wave3-authorization-v1",
            "status": "AUTHORIZED_PENDING_SEPARATE_DISPATCH",
            "authorizationOrdinal": 13,
            "executionKey": self.execution.EXECUTION_KEY,
            "runTitle": self.execution.RUN_TITLE,
            "runAttempt": 1,
            "wave": 3,
            "blocks": [7, 8],
            "geometryCount": prereg["geometryCount"],
            "caseCount": prereg["caseCount"],
            "enabled": True,
            "solverExecutionAuthorized": True,
            "automaticDispatch": False,
            "dispatch": False,
            "workflowDispatchEnabled": False,
            "githubRerunAllowed": False,
            "surrogateTrainingAuthorized": False,
            "internalHoldoutOpeningAuthorized": False,
            "tier2Authorized": False,
            "productionPromotionAuthorized": False,
            "sourceRunId": 31065046524,
            "sourceRunAttempt": 1,
            "sourceMainSha": "0ef7e011e00a4c4badcafb2f6ca06256026b1746",
            "sourceAuthorizationRef": "18a5746778441d57b722c740a17c94af9b56e9c9",
            "sourceExecutionKey": "twilight-surrogate-tier-1-v1:numerical:12",
            "preregistrationSha256": prereg["preregistrationSha256"],
            "sourceAnalysisRawSha256": prereg["sourceAnalysisRawSha256"],
            "sourceAnalysisSha256": prereg["sourceAnalysisSha256"],
            "executionSourceHeadSha": head,
        }
        metadata = {
            "authorizationCommit": authorization_ref,
            "authorizationParent": head,
            "changedFiles": [self.execution.AUTHORIZATION_PATH],
            "parentCount": 1,
        }
        runtime = {
            "uvspecSha256": "3" * 64,
            "uvspecHelpSha256": "4" * 64,
            "libRadtranDataTreeSha256": "5" * 64,
            "atmosphereSha256": "6" * 64,
            "runtimeLockRawSha256": "7" * 64,
        }
        runs = [
            {
                "id": context["runId"],
                "display_title": self.execution.RUN_TITLE,
                "status": "in_progress",
                "conclusion": None,
                "event": "workflow_dispatch",
                "run_attempt": 1,
                "head_sha": head,
                "head_branch": "main",
            }
        ]
        manifest = self.execution.build_manifest(
            self.root,
            authorization,
            context,
            runs,
            runtime,
            metadata,
            source_path,
        )
        return source_path, prereg, manifest

    def fake_results(self, manifest):
        base_executor = self.executor._base(self.root)
        nodes = [1e-6] * len(base_executor.CIE)
        value = 683.002 * 10.0 * sum(
            (node / 1000.0) * weight
            for node, weight in zip(nodes, base_executor.CIE)
        )
        rows = []
        for case in manifest["cases"]:
            row = {
                "schemaVersion": 1,
                "stageId": self.execution.STAGE_ID,
                "status": "COMPLETED",
                "caseId": case["caseId"],
                "groupId": case["groupId"],
                "block": case["block"],
                "role": case["role"],
                "seed": case["seed"],
                "photonHistories": case["photonHistories"],
                "manifestSha256": manifest["manifestSha256"],
                "runtimeReportSha256": "8" * 64,
                "inputSha256": "9" * 64,
                "radianceOutputSha256": "a" * 64,
                "stdOutputSha256": "b" * 64,
                "syntaxCheckCount": 1,
                "solverExecutionCount": 1,
                "selectedNodeRadiance": nodes,
                "selectedNodeStdRadiance": [0.0] * len(nodes),
                "selectedPhotopicContributionCdM2": value,
                "zeroHit": False,
                "fittingSurfaceExposed": False,
                "retryAllowed": False,
                "resumeAllowed": False,
            }
            row["contentSha256"] = self.execution.canonical_sha256(row)
            rows.append(row)
        return rows

    def test_manifest_and_matrix_are_dynamic_exact_and_closed(self):
        with tempfile.TemporaryDirectory() as raw:
            _, prereg, manifest = self.manifest(Path(raw))
            self.execution.validate_manifest(manifest)
            self.assertEqual(manifest["geometryIds"], prereg["geometryIds"])
            self.assertEqual(manifest["geometryCount"], 2)
            self.assertEqual(manifest["caseCount"], 4)
            self.assertEqual(manifest["blocks"], [7, 8])
            self.assertEqual(manifest["authorizationOrdinal"], 13)
            self.assertFalse(manifest["githubRerunAllowed"])
            self.assertFalse(manifest["retryAllowed"])
            self.assertFalse(manifest["resumeAllowed"])
            matrix = json.loads(self.matrix.matrix_value(manifest))["include"]
            self.assertEqual(len(matrix), 4)
            self.assertEqual(len({row["caseId"] for row in matrix}), 4)
            self.assertTrue(all(row["timeoutSeconds"] == 2400 for row in matrix))

    def test_manifest_refuses_prior_matching_title(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source_path = self.source_path(root)
            prereg = self.package.build_preregistration(
                self.package.load_json(source_path), source_path, self.root
            )
            head, auth_ref = "1" * 40, "2" * 40
            context = {
                "eventName": "workflow_dispatch",
                "runAttempt": 1,
                "displayTitle": self.execution.RUN_TITLE,
                "authorizationOrdinal": 13,
                "executionKey": self.execution.EXECUTION_KEY,
                "headBranch": "main",
                "headSha": head,
                "authorizationRef": auth_ref,
                "runId": 616161,
            }
            authorization = {
                "schemaVersion": 1,
                "stageId": "tier1-precision-continuation-wave3-authorization-v1",
                "status": "AUTHORIZED_PENDING_SEPARATE_DISPATCH",
                "authorizationOrdinal": 13,
                "executionKey": self.execution.EXECUTION_KEY,
                "runTitle": self.execution.RUN_TITLE,
                "runAttempt": 1,
                "wave": 3,
                "blocks": [7, 8],
                "geometryCount": prereg["geometryCount"],
                "caseCount": prereg["caseCount"],
                "enabled": True,
                "solverExecutionAuthorized": True,
                "automaticDispatch": False,
                "dispatch": False,
                "workflowDispatchEnabled": False,
                "githubRerunAllowed": False,
                "surrogateTrainingAuthorized": False,
                "internalHoldoutOpeningAuthorized": False,
                "tier2Authorized": False,
                "productionPromotionAuthorized": False,
                "sourceRunId": 31065046524,
                "sourceRunAttempt": 1,
                "sourceMainSha": "0ef7e011e00a4c4badcafb2f6ca06256026b1746",
                "sourceAuthorizationRef": "18a5746778441d57b722c740a17c94af9b56e9c9",
                "sourceExecutionKey": "twilight-surrogate-tier-1-v1:numerical:12",
                "preregistrationSha256": prereg["preregistrationSha256"],
                "sourceAnalysisRawSha256": prereg["sourceAnalysisRawSha256"],
                "sourceAnalysisSha256": prereg["sourceAnalysisSha256"],
                "executionSourceHeadSha": head,
            }
            metadata = {
                "authorizationCommit": auth_ref,
                "authorizationParent": head,
                "changedFiles": [self.execution.AUTHORIZATION_PATH],
                "parentCount": 1,
            }
            runtime = {key: str(index) * 64 for index, key in enumerate((
                "uvspecSha256", "uvspecHelpSha256", "libRadtranDataTreeSha256",
                "atmosphereSha256", "runtimeLockRawSha256"), start=3)}
            run = {
                "display_title": self.execution.RUN_TITLE,
                "status": "completed",
                "conclusion": "failure",
                "event": "workflow_dispatch",
                "run_attempt": 1,
                "head_sha": head,
                "head_branch": "main",
            }
            with self.assertRaisesRegex(Exception, "prior matching execution title exists"):
                self.execution.build_manifest(
                    self.root, authorization, context,
                    [{"id": 616161, **run}, {"id": 616160, **run}],
                    runtime, metadata, source_path,
                )

    def test_translation_aggregate_and_independent_audit(self):
        with tempfile.TemporaryDirectory() as raw:
            _, prereg, manifest = self.manifest(Path(raw))
            results = self.fake_results(manifest)
            self.execution.validate_results(manifest, results)
            translated = self.postprocess.translate_results(prereg, results)
            self.assertEqual(len(translated), 4)
            self.assertEqual({row["block"] for row in translated}, {7, 8})
            aggregate = self.postprocess.aggregate_wave3(prereg, results, self.root)
            self.assertEqual(aggregate["aggregate"]["status"], "COMPLETED")
            audit = self.postprocess.audit_wave3(prereg, results, aggregate, self.root)
            self.assertEqual(audit["audit"]["status"], "PASSED")
            self.assertEqual(audit["audit"]["failures"], [])

    def test_result_hash_tamper_is_refused(self):
        with tempfile.TemporaryDirectory() as raw:
            _, prereg, manifest = self.manifest(Path(raw))
            results = self.fake_results(manifest)
            results[0]["contentSha256"] = "0" * 64
            with self.assertRaisesRegex(Exception, "case result hash drift"):
                self.execution.validate_results(manifest, results)
            with self.assertRaisesRegex(Exception, "content hash changed"):
                self.postprocess.translate_results(prereg, results)

    def test_executor_fake_runner_performs_exactly_two_process_calls(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _, _, manifest_value = self.manifest(root)
            case_id = manifest_value["cases"][0]["caseId"]
            manifest = root / "manifest.json"
            runtime = root / "runtime.json"
            adapter = root / "adapter.py"
            output = root / "output"
            manifest.write_text(json.dumps(manifest_value), encoding="utf-8")
            runtime.write_text("{}\n", encoding="utf-8")
            adapter.write_text(
                "import hashlib\n"
                "def prepare_case(manifest_path,runtime_report_path,case_id,data_dir,repository_root,output_root):\n"
                " d=output_root/case_id; d.mkdir(parents=True); text='source solar'+chr(10); (d/'input-resolved.txt').write_text(text); return {'inputResolvedSha256':hashlib.sha256(text.encode()).hexdigest()}\n",
                encoding="utf-8",
            )
            calls = []

            def runner(command, text, cwd, timeout):
                calls.append(list(command))
                if len(calls) == 2:
                    spectrum = "\n".join(
                        f"{node} 1.0" for node in self.executor._base(self.root).NODES
                    ) + "\n"
                    (cwd / "mc.rad.spc").write_text(spectrum, encoding="utf-8")
                    (cwd / "mc.rad.std.spc").write_text(spectrum, encoding="utf-8")
                return {"exitCode": 0, "timedOut": False, "stdout": "", "stderr": ""}

            env = {
                "GITHUB_ACTIONS": "true",
                "GITHUB_EVENT_NAME": "workflow_dispatch",
                "GITHUB_RUN_ATTEMPT": "1",
            }
            with mock.patch.dict(os.environ, env, clear=False):
                result = self.executor.execute_case(
                    manifest, runtime, adapter, case_id, root, self.root,
                    Path("/fake/uvspec"), output, 2400, True, runner=runner,
                )
            self.assertEqual(len(calls), 2)
            self.assertEqual(result["stageId"], self.execution.STAGE_ID)
            self.assertEqual(result["syntaxCheckCount"], 1)
            self.assertEqual(result["solverExecutionCount"], 1)
            self.assertTrue((output / case_id / "case-result.json").is_file())


if __name__ == "__main__":
    unittest.main()
