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


class Wave2TriggerV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.directory = cls.root / "experiments/tier1-precision-continuation-wave2-v1"
        cls.package = load(cls.directory / "package.py", "wave2_trigger_test_package")
        cls.trigger = load(cls.directory / "trigger_execution.py", "wave2_trigger_test_execution")
        cls.trigger_executor = load(
            cls.directory / "trigger_case_executor.py", "wave2_trigger_test_case_executor"
        )
        cls.matrix = load(cls.directory / "matrix_output.py", "wave2_trigger_test_matrix")

    def manifest_inputs(self):
        prereg = self.package.build_preregistration(self.root)
        source = "1" * 40
        authorization_ref = "2" * 40
        context = {
            "eventName": "push",
            "triggerBranch": self.trigger.TRIGGER_BRANCH,
            "runAttempt": 1,
            "displayTitle": "Tier-1 precision continuation wave 2 ordinal 12",
            "authorizationOrdinal": 12,
            "executionKey": "twilight-surrogate-tier-1-v1:numerical:12",
            "headBranch": "main",
            "headSha": source,
            "authorizationRef": authorization_ref,
            "runId": 515151,
        }
        authorization = {
            "schemaVersion": 1,
            "stageId": "tier1-precision-continuation-wave2-authorization-v1",
            "status": "AUTHORIZED_PENDING_SEPARATE_DISPATCH",
            "authorizationOrdinal": 12,
            "executionKey": "twilight-surrogate-tier-1-v1:numerical:12",
            "runTitle": "Tier-1 precision continuation wave 2 ordinal 12",
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
            "executionSourceHeadSha": source,
            "sourceSalvageDescriptorSha256": prereg["sourceBindings"][
                "sourceSalvageDescriptorSha256"
            ],
            "triggerBranch": self.trigger.TRIGGER_BRANCH,
            "triggerEvent": "push",
        }
        metadata = {
            "authorizationCommit": authorization_ref,
            "authorizationParent": source,
            "changedFiles": [
                "experiments/tier1-precision-continuation-wave2-v1/authorization.ordinal12.json"
            ],
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
                "display_title": "Tier-1 precision continuation wave 2 ordinal 12",
                "status": "in_progress",
                "conclusion": None,
                "event": "push",
                "run_attempt": 1,
                "head_sha": authorization_ref,
                "head_branch": self.trigger.TRIGGER_BRANCH,
            }
        ]
        return authorization, context, runs, runtime, metadata

    def manifest(self):
        return self.trigger.build_manifest(
            self.root, *self.manifest_inputs()
        )

    def test_push_manifest_is_exact_and_closed(self):
        value = self.manifest()
        self.trigger.validate_manifest(value)
        self.assertEqual(value["eventName"], "push")
        self.assertEqual(value["triggerBranch"], self.trigger.TRIGGER_BRANCH)
        self.assertEqual(value["headBranch"], "main")
        self.assertEqual(value["authorizationOrdinal"], 12)
        self.assertEqual(value["caseCount"], 32)
        self.assertEqual(value["blocks"], [5, 6])
        self.assertFalse(value["githubRerunAllowed"])
        self.assertFalse(value["retryAllowed"])
        self.assertFalse(value["resumeAllowed"])
        self.assertFalse(value["automaticNextWave"])
        self.assertFalse(value["surrogateTrainingAuthorized"])
        self.assertFalse(value["internalHoldoutOpeningAuthorized"])
        self.assertFalse(value["tier2Authorized"])
        self.assertFalse(value["productionPromotionAuthorized"])

    def test_wrong_event_branch_attempt_and_authorization_trigger_refuse(self):
        authorization, context, runs, runtime, metadata = self.manifest_inputs()
        mutations = (
            (context, "eventName", "workflow_dispatch"),
            (context, "triggerBranch", "dispatch/wrong"),
            (context, "runAttempt", 2),
            (authorization, "triggerEvent", "workflow_dispatch"),
            (authorization, "triggerBranch", "dispatch/wrong"),
        )
        for target, key, bad in mutations:
            original = target[key]
            target[key] = bad
            with self.assertRaises(Exception, msg=key):
                self.trigger.build_manifest(
                    self.root, authorization, context, runs, runtime, metadata
                )
            target[key] = original

    def test_prior_matching_title_refuses_before_runtime_or_solver(self):
        authorization, context, runs, runtime, metadata = self.manifest_inputs()
        runs.append(
            {
                **runs[0],
                "id": context["runId"] - 1,
                "status": "completed",
                "conclusion": "failure",
            }
        )
        with self.assertRaisesRegex(Exception, "prior matching execution title exists"):
            self.trigger.build_manifest(
                self.root, authorization, context, runs, runtime, metadata
            )

    def test_matrix_is_exact_32_unique_b5_b6_cases(self):
        manifest = self.manifest()
        matrix = json.loads(self.matrix.matrix_value(manifest))
        include = matrix["include"]
        self.assertEqual(len(include), 32)
        self.assertEqual(len({row["caseId"] for row in include}), 32)
        self.assertTrue(all(row["timeoutSeconds"] == 2400 for row in include))
        bad = dict(manifest)
        bad["cases"] = manifest["cases"][:-1]
        with self.assertRaisesRegex(Exception, "exactly 32"):
            self.matrix.matrix_value(bad)

    def test_push_case_executor_uses_exact_event_ref_and_one_solver(self):
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
                    base = self.trigger_executor._base(self.root)
                    spectrum = "\n".join(f"{node} 1.0" for node in base.NODES) + "\n"
                    (cwd / "mc.rad.spc").write_text(spectrum, encoding="utf-8")
                    (cwd / "mc.rad.std.spc").write_text(spectrum, encoding="utf-8")
                return {
                    "exitCode": 0,
                    "timedOut": False,
                    "stdout": "",
                    "stderr": "",
                }

            good_env = {
                "GITHUB_ACTIONS": "true",
                "GITHUB_EVENT_NAME": "push",
                "GITHUB_RUN_ATTEMPT": "1",
                "GITHUB_REF_NAME": self.trigger.TRIGGER_BRANCH,
            }
            with mock.patch.dict(os.environ, good_env, clear=False):
                result = self.trigger_executor.execute_case(
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
            self.assertEqual(result["syntaxCheckCount"], 1)
            self.assertEqual(result["solverExecutionCount"], 1)
            self.assertTrue((output / case_id / "case-result.json").is_file())

            bad_env = dict(good_env)
            bad_env["GITHUB_REF_NAME"] = "dispatch/wrong"
            with mock.patch.dict(os.environ, bad_env, clear=False):
                with self.assertRaisesRegex(Exception, "one-use push trigger"):
                    self.trigger_executor._base(self.root).verify_context(True)

    def test_scientific_workflow_is_one_use_push_only(self):
        path = self.root / ".github/workflows/tier1-precision-continuation-wave2-ordinal12-execution.yml"
        text = path.read_text(encoding="utf-8")
        self.assertIn("run-name: Tier-1 precision continuation wave 2 ordinal 12", text)
        self.assertIn("dispatch/tier1-precision-continuation-wave2-ordinal12-v1", text)
        self.assertNotIn("workflow_dispatch:", text)
        self.assertIn("fail-fast: false", text)
        self.assertIn("max-parallel: 8", text)
        self.assertIn("GITHUB_RUN_ATTEMPT\" = 1", text)
        self.assertIn("source-salvage/salvage/aggregate.json", text)
        self.assertIn("source-salvage/salvage/audit.json", text)
        self.assertIn("trigger_case_executor.py", text)
        self.assertIn("--allow-execution", text)
        self.assertNotIn("surrogateFitAuthorized: true", text)
        self.assertNotIn("internalHoldoutOpened: true", text)
        self.assertNotIn("productionPromotionAuthorized: true", text)


if __name__ == "__main__":
    unittest.main()
