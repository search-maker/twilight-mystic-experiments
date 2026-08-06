from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Wave2ExecutionV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.directory = cls.root / "experiments/tier1-precision-continuation-wave2-v1"
        cls.package = load(cls.directory / "package.py", "wave2_execution_test_package")
        cls.execution = load(cls.directory / "execution.py", "wave2_execution_test_driver")
        cls.postprocess = load(cls.directory / "postprocess.py", "wave2_execution_test_postprocess")
        cls.executor = load(cls.directory / "case_executor.py", "wave2_execution_test_case_executor")

    def manifest(self):
        p, e = self.package, self.execution
        prereg = p.build_preregistration(self.root)
        head = "1" * 40
        authorization_ref = "2" * 40
        context = {
            "eventName": "workflow_dispatch",
            "runAttempt": 1,
            "displayTitle": e.RUN_TITLE,
            "authorizationOrdinal": 12,
            "executionKey": e.EXECUTION_KEY,
            "headBranch": "main",
            "headSha": head,
            "authorizationRef": authorization_ref,
            "runId": 424242,
        }
        authorization = {
            "schemaVersion": 1,
            "stageId": "tier1-precision-continuation-wave2-authorization-v1",
            "status": "AUTHORIZED_PENDING_SEPARATE_DISPATCH",
            "authorizationOrdinal": 12,
            "executionKey": e.EXECUTION_KEY,
            "runTitle": e.RUN_TITLE,
            "runAttempt": 1,
            "wave": 2,
            "caseCount": 32,
            "blocks": [5, 6],
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
            "preregistrationSha256": prereg["preregistrationSha256"],
            "executionSourceHeadSha": head,
            "sourceSalvageDescriptorSha256": prereg["sourceBindings"]["sourceSalvageDescriptorSha256"],
        }
        metadata = {
            "authorizationCommit": authorization_ref,
            "authorizationParent": head,
            "changedFiles": [e.AUTHORIZATION_PATH],
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
                "display_title": e.RUN_TITLE,
                "status": "in_progress",
                "conclusion": None,
                "event": "workflow_dispatch",
                "run_attempt": 1,
                "head_sha": head,
                "head_branch": "main",
            }
        ]
        return e.build_manifest(
            self.root, authorization, context, runs, runtime, metadata
        )

    def fake_results(self, manifest):
        e = self.execution
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
                "stageId": e.STAGE_ID,
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
            row["contentSha256"] = e.canonical_sha256(row)
            rows.append(row)
        return rows

    def test_manifest_binds_exact_32_case_identity(self):
        manifest = self.manifest()
        self.execution.validate_manifest(manifest)
        self.assertEqual(manifest["caseCount"], 32)
        self.assertEqual(manifest["geometryCount"], 16)
        self.assertEqual(manifest["blocks"], [5, 6])
        self.assertEqual(manifest["authorizationOrdinal"], 12)
        self.assertEqual(
            manifest["executionKey"], "twilight-surrogate-tier-1-v1:numerical:12"
        )
        self.assertFalse(manifest["githubRerunAllowed"])
        self.assertFalse(manifest["retryAllowed"])
        self.assertFalse(manifest["resumeAllowed"])
        self.assertEqual(manifest["duplicateRunAudit"]["matchingRuns"], [])

    def test_manifest_refuses_prior_matching_title(self):
        p, e = self.package, self.execution
        prereg = p.build_preregistration(self.root)
        head, authorization_ref = "1" * 40, "2" * 40
        context = {
            "eventName": "workflow_dispatch",
            "runAttempt": 1,
            "displayTitle": e.RUN_TITLE,
            "authorizationOrdinal": 12,
            "executionKey": e.EXECUTION_KEY,
            "headBranch": "main",
            "headSha": head,
            "authorizationRef": authorization_ref,
            "runId": 424242,
        }
        authorization = {
            "schemaVersion": 1,
            "stageId": "tier1-precision-continuation-wave2-authorization-v1",
            "status": "AUTHORIZED_PENDING_SEPARATE_DISPATCH",
            "authorizationOrdinal": 12,
            "executionKey": e.EXECUTION_KEY,
            "runTitle": e.RUN_TITLE,
            "runAttempt": 1,
            "wave": 2,
            "caseCount": 32,
            "blocks": [5, 6],
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
            "preregistrationSha256": prereg["preregistrationSha256"],
            "executionSourceHeadSha": head,
            "sourceSalvageDescriptorSha256": prereg["sourceBindings"]["sourceSalvageDescriptorSha256"],
        }
        metadata = {
            "authorizationCommit": authorization_ref,
            "authorizationParent": head,
            "changedFiles": [e.AUTHORIZATION_PATH],
            "parentCount": 1,
        }
        runtime = {
            key: str(index) * 64
            for index, key in enumerate(
                (
                    "uvspecSha256",
                    "uvspecHelpSha256",
                    "libRadtranDataTreeSha256",
                    "atmosphereSha256",
                    "runtimeLockRawSha256",
                ),
                start=3,
            )
        }
        base_run = {
            "display_title": e.RUN_TITLE,
            "status": "completed",
            "conclusion": "failure",
            "event": "workflow_dispatch",
            "run_attempt": 1,
            "head_sha": head,
            "head_branch": "main",
        }
        runs = [
            {"id": context["runId"], **base_run},
            {"id": context["runId"] - 1, **base_run},
        ]
        with self.assertRaisesRegex(Exception, "prior matching execution title exists"):
            e.build_manifest(self.root, authorization, context, runs, runtime, metadata)

    def test_translation_aggregate_and_independent_audit(self):
        manifest = self.manifest()
        results = self.fake_results(manifest)
        self.execution.validate_results(manifest, results)
        translated = self.postprocess.translate_results(
            self.package.build_preregistration(self.root), results
        )
        self.assertEqual(len(translated), 32)
        self.assertEqual({row["block"] for row in translated}, {5, 6})
        aggregate = self.execution.aggregate(self.root, manifest, results)
        self.assertEqual(aggregate["aggregate"]["status"], "COMPLETED")
        audit = self.execution.audit(self.root, manifest, results, aggregate)
        self.assertEqual(audit["audit"]["status"], "PASSED")
        self.assertEqual(audit["audit"]["failures"], [])

    def test_result_hash_tamper_is_refused(self):
        manifest = self.manifest()
        results = self.fake_results(manifest)
        results[0]["contentSha256"] = "0" * 64
        with self.assertRaisesRegex(Exception, "case result hash drift"):
            self.execution.validate_results(manifest, results)
        with self.assertRaisesRegex(Exception, "content hash changed"):
            self.postprocess.translate_results(
                self.package.build_preregistration(self.root), results
            )

    def test_executor_fake_runner_performs_exactly_two_process_calls(self):
        manifest_value = self.manifest()
        case_id = manifest_value["cases"][0]["caseId"]
        with tempfile.TemporaryDirectory() as raw:
            temp = Path(raw)
            manifest = temp / "manifest.json"
            runtime = temp / "runtime.json"
            adapter = temp / "adapter.py"
            output = temp / "output"
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
                return {
                    "exitCode": 0,
                    "timedOut": False,
                    "stdout": "",
                    "stderr": "",
                }

            env = {
                "GITHUB_ACTIONS": "true",
                "GITHUB_EVENT_NAME": "workflow_dispatch",
                "GITHUB_RUN_ATTEMPT": "1",
            }
            with mock.patch.dict(os.environ, env, clear=False):
                result = self.executor.execute_case(
                    manifest,
                    runtime,
                    adapter,
                    case_id,
                    temp,
                    self.root,
                    Path("/fake/uvspec"),
                    output,
                    2400,
                    True,
                    runner=runner,
                )
            self.assertEqual(len(calls), 2)
            self.assertEqual(result["stageId"], self.execution.STAGE_ID)
            self.assertEqual(result["syntaxCheckCount"], 1)
            self.assertEqual(result["solverExecutionCount"], 1)
            self.assertTrue((output / case_id / "case-result.json").is_file())

    def test_actual_source_two_wave_analysis_when_available(self):
        source_root = os.getenv("WAVE2_SOURCE_SALVAGE_ROOT")
        if not source_root:
            self.skipTest("merged-main source salvage not mounted")
        source = Path(source_root)
        source_aggregate_path = source / "salvage/aggregate.json"
        source_audit_path = source / "salvage/audit.json"
        source_aggregate = self.execution.load_bound_source(
            source_aggregate_path, self.execution.SOURCE_AGGREGATE_RAW_SHA256
        )
        source_audit = self.execution.load_bound_source(
            source_audit_path, self.execution.SOURCE_AUDIT_RAW_SHA256
        )
        manifest = self.manifest()
        results = self.fake_results(manifest)
        aggregate = self.execution.aggregate(self.root, manifest, results)
        audit = self.execution.audit(self.root, manifest, results, aggregate)
        analysis = self.execution.analyze(
            self.root,
            manifest,
            source_aggregate,
            source_audit,
            aggregate,
            audit,
        )
        self.assertEqual(analysis["analysis"]["status"], "CONTINUATION_ANALYZED")
        self.assertEqual(len(analysis["analysis"]["points"]), 20)
        self.assertFalse(analysis["additionalExecutionAutomaticallyAuthorized"])
        self.assertFalse(analysis["surrogateFitAuthorized"])
        self.assertFalse(analysis["internalHoldoutOpened"])
        self.assertFalse(analysis["tier2Authorized"])
        self.assertFalse(analysis["productionPromotionAuthorized"])


if __name__ == "__main__":
    unittest.main()
