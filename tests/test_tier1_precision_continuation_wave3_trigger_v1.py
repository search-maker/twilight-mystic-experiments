from __future__ import annotations

import importlib.util
import os
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


class Wave3TriggerV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.directory = cls.root / "experiments/tier1-precision-continuation-wave3-v1"
        cls.guard = load(
            cls.directory / "terminal_trigger_execution.py",
            "wave3_terminal_trigger_test_guard",
        )
        cls.trigger = load(
            cls.directory / "trigger_execution.py",
            "wave3_terminal_trigger_test_base",
        )
        cls.case_trigger = load(
            cls.directory / "trigger_case_executor.py",
            "wave3_terminal_trigger_test_case",
        )
        _, _, cls.binding = cls.guard._modules(cls.root)

    def context(self):
        return {
            "eventName": "push",
            "triggerBranch": self.trigger.TRIGGER_BRANCH,
            "runAttempt": 1,
            "displayTitle": "Tier-1 precision continuation wave 3 ordinal 13",
            "authorizationOrdinal": 13,
            "executionKey": "twilight-surrogate-tier-1-v1:numerical:13",
            "headBranch": "main",
            "headSha": "1" * 40,
            "authorizationRef": "2" * 40,
            "runId": 717171,
        }

    def manifest(self):
        cases = []
        seed = 1000
        for geometry_id in self.binding.ACTIVE_GEOMETRY_IDS:
            for block in (7, 8):
                seed += 1
                cases.append(
                    {
                        "caseId": f"{geometry_id}-wave3-b{block}",
                        "groupId": geometry_id,
                        "block": block,
                        "seed": seed,
                    }
                )
        report = {
            "status": "ORDINAL12_TERMINAL_SOURCE_EXACTLY_BOUND",
            "reportSha256": "a" * 64,
        }
        value = {
            "schemaVersion": 1,
            "stageId": "tier1-precision-continuation-wave3-ordinal13-execution-v1",
            "status": "AUTHORIZED_FOR_ONE_ATTEMPT1_EXECUTION",
            "displayTitle": "Tier-1 precision continuation wave 3 ordinal 13",
            "authorizationRef": "2" * 40,
            "authorizationOrdinal": 13,
            "executionKey": "twilight-surrogate-tier-1-v1:numerical:13",
            "runId": 717171,
            "runAttempt": 1,
            "eventName": "push",
            "triggerBranch": self.trigger.TRIGGER_BRANCH,
            "headBranch": "main",
            "headSha": "1" * 40,
            "blocks": [7, 8],
            "wave": 3,
            "geometryIds": list(self.binding.ACTIVE_GEOMETRY_IDS),
            "geometryCount": 15,
            "caseCount": 30,
            "cases": cases,
            "sourceBindings": {
                "sourceAnalysisRawSha256": self.binding.SOURCE_ANALYSIS_RAW_SHA256,
                "sourceAnalysisSha256": self.binding.SOURCE_ANALYSIS_SHA256,
            },
            "terminalSourceBinding": self.guard.terminal_binding_value(report, self.binding),
            "githubRerunAllowed": False,
            "retryAllowed": False,
            "resumeAllowed": False,
        }
        base = self.trigger._base(self.root)
        value["manifestSha256"] = base.canonical_sha256(value)
        return value, report

    def reseal(self, value):
        base = self.trigger._base(self.root)
        value["manifestSha256"] = base.canonical_sha256(
            {key: item for key, item in value.items() if key != "manifestSha256"}
        )

    def test_exact_push_context_is_accepted(self):
        self.trigger._base(self.root).validate_context(self.context())

    def test_non_push_or_wrong_branch_context_is_refused(self):
        value = self.context()
        value["eventName"] = "workflow_dispatch"
        with self.assertRaisesRegex(Exception, "push-trigger run context mismatch"):
            self.trigger._base(self.root).validate_context(value)
        value = self.context()
        value["triggerBranch"] = "dispatch/wrong"
        with self.assertRaisesRegex(Exception, "push-trigger run context mismatch"):
            self.trigger._base(self.root).validate_context(value)

    def test_terminal_bound_30_case_manifest_is_accepted(self):
        manifest, report = self.manifest()
        self.guard.validate_terminal_manifest(manifest, report, self.root)

    def test_terminal_manifest_refuses_active_set_or_hash_drift(self):
        manifest, report = self.manifest()
        manifest["geometryIds"] = manifest["geometryIds"][:-1]
        self.reseal(manifest)
        with self.assertRaisesRegex(Exception, "manifest scope changed"):
            self.guard.validate_terminal_manifest(manifest, report, self.root)
        manifest, report = self.manifest()
        manifest["sourceBindings"]["sourceAnalysisRawSha256"] = "0" * 64
        self.reseal(manifest)
        with self.assertRaisesRegex(Exception, "source hash changed"):
            self.guard.validate_terminal_manifest(manifest, report, self.root)

    def test_terminal_manifest_refuses_duplicate_seed(self):
        manifest, report = self.manifest()
        manifest["cases"][1]["seed"] = manifest["cases"][0]["seed"]
        self.reseal(manifest)
        with self.assertRaisesRegex(Exception, "case universe changed"):
            self.guard.validate_terminal_manifest(manifest, report, self.root)

    def test_case_executor_requires_exact_attempt1_push_environment(self):
        exact = {
            "GITHUB_ACTIONS": "true",
            "GITHUB_EVENT_NAME": "push",
            "GITHUB_RUN_ATTEMPT": "1",
            "GITHUB_REF_NAME": self.trigger.TRIGGER_BRANCH,
        }
        with mock.patch.dict(os.environ, exact, clear=False):
            self.case_trigger._base(self.root).verify_context(True)
        wrong = {**exact, "GITHUB_RUN_ATTEMPT": "2"}
        with mock.patch.dict(os.environ, wrong, clear=False):
            with self.assertRaisesRegex(Exception, "not exact first-attempt one-use push trigger"):
                self.case_trigger._base(self.root).verify_context(True)

    def test_case_executor_requires_explicit_allow_execution(self):
        exact = {
            "GITHUB_ACTIONS": "true",
            "GITHUB_EVENT_NAME": "push",
            "GITHUB_RUN_ATTEMPT": "1",
            "GITHUB_REF_NAME": self.trigger.TRIGGER_BRANCH,
        }
        with mock.patch.dict(os.environ, exact, clear=False):
            with self.assertRaisesRegex(Exception, "--allow-execution required"):
                self.case_trigger._base(self.root).verify_context(False)


if __name__ == "__main__":
    unittest.main()
