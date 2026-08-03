from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "experiments" / "mystic-batch-v1"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


guard_module = load_module("batch_execution_guard", PACKAGE / "execution_guard.py")
duplicate_module = load_module("batch_duplicate_audit", PACKAGE / "duplicate_run_audit.py")
plan_module = load_module("batch_scientific_plan", PACKAGE / "scientific_plan.py")
executor_module = load_module("batch_case_executor", PACKAGE / "scientific_case_executor.py")
aggregate_module = load_module("batch_scientific_aggregate", PACKAGE / "scientific_aggregate.py")
audit_module = load_module("batch_scientific_audit", PACKAGE / "scientific_audit.py")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ScientificExecutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_exact_one_purpose_authorization_guard(self) -> None:
        repo = self.root / "repo"
        (repo / "experiments/mystic-batch-v1").mkdir(parents=True)
        (repo / ".github/workflows").mkdir(parents=True)
        manifest_rel = Path("experiments/mystic-batch-v1/manifest.batch.json")
        auth_rel = Path("experiments/mystic-batch-v1/authorization.scientific.json")
        adapter_rel = Path("experiments/mystic-batch-v1/scientific_adapter.py")
        lock_rel = Path("experiments/mystic-batch-v1/runtime-lock.micromamba.json")
        workflow_rel = Path(".github/workflows/mystic-batch-v1-scientific-execution.yml")
        manifest = {
            "schemaVersion": 1,
            "stageId": "mystic-batch-v1",
            "batchId": "guard-test-v1",
            "mode": "scientific",
            "scientificExecution": True,
            "limits": {
                "maximumCases": 2,
                "maximumParallel": 2,
                "maximumConfiguredMcPhotonsSum": 200,
                "perCaseTimeoutSeconds": 60,
            },
            "cases": [
                {"ordinal": 1, "caseId": "case-1", "seed": 101, "photonHistories": 100},
                {"ordinal": 2, "caseId": "case-2", "seed": 102, "photonHistories": 100},
            ],
        }
        (repo / manifest_rel).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        (repo / adapter_rel).write_text("# adapter\n")
        (repo / lock_rel).write_text("{}\n")
        (repo / workflow_rel).write_text("name: execution\n")
        disabled = {
            "schemaVersion": 1,
            "stageId": "mystic-batch-v1",
            "authorized": False,
            "scientificExecution": False,
            "successDoesNotAuthorizeProduction": True,
            "executionKey": None,
            "batchId": None,
            "manifestPath": None,
            "manifestRawSha256": None,
            "runtimeLockRawSha256": None,
            "scientificAdapterRawSha256": None,
            "executionWorkflowRawSha256": None,
            "exactAuthorizationParentCommit": None,
            "exactAuthorizationCommit": None,
            "authorizationOrdinal": 0,
            "consumed": False,
        }
        (repo / auth_rel).write_text(json.dumps(disabled, indent=2, sort_keys=True) + "\n")
        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
        subprocess.run(["git", "add", "."], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-m", "parent"], cwd=repo, check=True, capture_output=True)
        parent = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
        execution_key = "mystic-batch-v1:guard-test-v1:1"
        enabled = {
            **disabled,
            "authorized": True,
            "scientificExecution": True,
            "executionKey": execution_key,
            "batchId": manifest["batchId"],
            "manifestPath": manifest_rel.as_posix(),
            "manifestRawSha256": sha(repo / manifest_rel),
            "runtimeLockRawSha256": sha(repo / lock_rel),
            "scientificAdapterRawSha256": sha(repo / adapter_rel),
            "executionWorkflowRawSha256": sha(repo / workflow_rel),
            "exactAuthorizationParentCommit": parent,
            "authorizationOrdinal": 1,
        }
        (repo / auth_rel).write_text(json.dumps(enabled, indent=2, sort_keys=True) + "\n")
        subprocess.run(["git", "add", auth_rel.as_posix()], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-m", "authorize"], cwd=repo, check=True, capture_output=True)
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
        report = guard_module.validate_guard(
            repo,
            auth_rel,
            manifest_rel,
            adapter_rel,
            workflow_rel,
            lock_rel,
            head,
            execution_key,
            1,
            require_github_context=False,
        )
        self.assertEqual(report["status"], "AUTHORIZED")
        self.assertEqual(report["caseCount"], 2)
        self.assertEqual(report["configuredMcPhotonsSum"], 200)

    def test_duplicate_marker_is_refused(self) -> None:
        title = duplicate_module.expected_title("key-1", "a" * 40, 1)
        current = {
            "id": 20,
            "display_title": title,
            "event": "workflow_dispatch",
            "run_attempt": 1,
            "status": "in_progress",
            "conclusion": None,
        }
        duplicate = {**current, "id": 10, "status": "completed", "conclusion": "failure"}
        with self.assertRaises(duplicate_module.DuplicateRefusal):
            duplicate_module.evaluate({"total_count": 2, "workflow_runs": [current, duplicate]}, 20, title)

    def test_scientific_plan_builds_exact_matrix(self) -> None:
        manifest_path = self.root / "manifest.json"
        guard_path = self.root / "guard.json"
        manifest = {
            "batchId": "plan-test-v1",
            "limits": {"maximumParallel": 2, "perCaseTimeoutSeconds": 120},
            "cases": [
                {"ordinal": 2, "caseId": "case-b", "seed": 2, "photonHistories": 20},
                {"ordinal": 1, "caseId": "case-a", "seed": 1, "photonHistories": 10},
            ],
        }
        guard = {
            "status": "AUTHORIZED",
            "stageId": "mystic-batch-v1",
            "batchId": "plan-test-v1",
            "manifestRawSha256": "a" * 64,
            "authorizationRef": "b" * 40,
            "authorizationOrdinal": 1,
            "executionKey": "key-1",
            "runtimeLockRawSha256": "c" * 64,
            "scientificAdapterRawSha256": "d" * 64,
            "executionWorkflowRawSha256": "e" * 64,
        }
        manifest_path.write_text(json.dumps(manifest))
        guard_path.write_text(json.dumps(guard))
        plan = plan_module.build_plan(manifest_path, guard_path)
        self.assertEqual([item["case_id"] for item in plan["matrix"]["include"]], ["case-a", "case-b"])
        self.assertEqual(plan["configuredMcPhotonsSum"], 30)

    def _write_fake_adapter(self) -> Path:
        path = self.root / "fake_adapter.py"
        path.write_text(
            textwrap.dedent(
                """
                import hashlib
                from pathlib import Path

                def prepare_case(manifest_path, runtime_report_path, case_id, data_dir, repository_root, output_root):
                    case_dir = Path(output_root) / case_id
                    case_dir.mkdir(parents=True, exist_ok=True)
                    text = "quiet\\n"
                    input_path = case_dir / "input-resolved.txt"
                    input_path.write_text(text)
                    return {"inputResolvedSha256": hashlib.sha256(text.encode()).hexdigest()}
                """
            )
        )
        return path

    def _write_fake_uvspec(self) -> tuple[Path, Path]:
        script = self.root / "uvspec"
        log = self.root / "uvspec.log"
        nodes = executor_module.NODES
        script.write_text(
            "#!/usr/bin/env python3\n"
            "import os, sys\n"
            "from pathlib import Path\n"
            "log = Path(os.environ['FAKE_UVSPEC_LOG'])\n"
            "mode = 'syntax' if len(sys.argv) > 1 and sys.argv[1] == '-c' else 'solver'\n"
            "with log.open('a') as h: h.write(mode + '\\n')\n"
            "_ = sys.stdin.read()\n"
            "if mode == 'solver' and os.environ.get('FAKE_SOLVER_FAIL') == '1': sys.exit(7)\n"
            "if mode == 'solver':\n"
            f"    nodes = {nodes!r}\n"
            "    Path('mc.rad.spc').write_text(''.join(f'{n} 1.0\\n' for n in nodes))\n"
            "    Path('mc.rad.std.spc').write_text(''.join(f'{n} 0.1\\n' for n in nodes))\n"
        )
        script.chmod(script.stat().st_mode | stat.S_IXUSR)
        return script, log

    def _execution_fixture(self) -> tuple[Path, Path, Path, Path, Path]:
        manifest_path = self.root / "manifest.json"
        runtime_path = self.root / "runtime.json"
        adapter_path = self._write_fake_adapter()
        uvspec, log = self._write_fake_uvspec()
        manifest = {
            "batchId": "executor-test-v1",
            "cases": [{"ordinal": 1, "caseId": "case-one", "seed": 101, "photonHistories": 100}],
        }
        manifest_path.write_text(json.dumps(manifest))
        runtime_path.write_text(json.dumps({"runtime": "test"}))
        return manifest_path, runtime_path, adapter_path, uvspec, log

    def test_executor_runs_one_syntax_and_one_solver(self) -> None:
        manifest, runtime, adapter, uvspec, log = self._execution_fixture()
        output = self.root / "output"
        env = {
            "GITHUB_ACTIONS": "true",
            "GITHUB_EVENT_NAME": "workflow_dispatch",
            "GITHUB_RUN_ATTEMPT": "1",
            "FAKE_UVSPEC_LOG": str(log),
        }
        with mock.patch.dict(os.environ, env, clear=False):
            result, ok = executor_module.execute_case(
                manifest,
                runtime,
                adapter,
                "case-one",
                self.root,
                self.root,
                uvspec,
                output,
                30,
                True,
            )
        self.assertTrue(ok)
        self.assertEqual(log.read_text().splitlines(), ["syntax", "solver"])
        self.assertEqual(result["syntaxCheckCount"], 1)
        self.assertEqual(result["solverExecutionCount"], 1)
        self.assertGreater(result["selectedPhotopicContributionCdM2"], 0)

    def test_executor_does_not_retry_failed_solver(self) -> None:
        manifest, runtime, adapter, uvspec, log = self._execution_fixture()
        env = {
            "GITHUB_ACTIONS": "true",
            "GITHUB_EVENT_NAME": "workflow_dispatch",
            "GITHUB_RUN_ATTEMPT": "1",
            "FAKE_UVSPEC_LOG": str(log),
            "FAKE_SOLVER_FAIL": "1",
        }
        with mock.patch.dict(os.environ, env, clear=False):
            result, ok = executor_module.execute_case(
                manifest,
                runtime,
                adapter,
                "case-one",
                self.root,
                self.root,
                uvspec,
                self.root / "output-fail",
                30,
                True,
            )
        self.assertFalse(ok)
        self.assertEqual(log.read_text().splitlines(), ["syntax", "solver"])
        self.assertEqual(result["solverExecutionCount"], 1)

    def test_aggregate_and_independent_audit(self) -> None:
        plan_path = self.root / "plan.json"
        cases_root = self.root / "cases"
        aggregate_dir = self.root / "aggregate"
        plan = {
            "stageId": "mystic-batch-v1",
            "scientificExecution": True,
            "batchId": "aggregate-test-v1",
            "manifestRawSha256": "a" * 64,
            "authorizationRef": "b" * 40,
            "configuredMcPhotonsSum": 200,
            "runtimeLockRawSha256": "c" * 64,
            "scientificAdapterRawSha256": "d" * 64,
            "executionWorkflowRawSha256": "e" * 64,
            "cases": [
                {"ordinal": 1, "caseId": "case-1", "seed": 1, "photonHistories": 100},
                {"ordinal": 2, "caseId": "case-2", "seed": 2, "photonHistories": 100},
            ],
        }
        plan_path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n")
        for case, value in zip(plan["cases"], [10.0, 12.0]):
            case_dir = cases_root / case["caseId"]
            case_dir.mkdir(parents=True)
            result = {
                "stageId": "mystic-batch-v1",
                "status": "COMPLETED",
                "scientificDiagnostic": True,
                "successDoesNotAuthorizeProduction": True,
                "batchId": plan["batchId"],
                "caseId": case["caseId"],
                "ordinal": case["ordinal"],
                "seed": case["seed"],
                "photonHistories": case["photonHistories"],
                "manifestRawSha256": plan["manifestRawSha256"],
                "adapterRawSha256": plan["scientificAdapterRawSha256"],
                "runtimeReportRawSha256": "f" * 64,
                "inputResolvedSha256": "1" * 64,
                "radianceOutputSha256": "2" * 64,
                "stdOutputSha256": "3" * 64,
                "syntaxCheckCount": 1,
                "solverExecutionCount": 1,
                "syntax": {"exitCode": 0, "timedOut": False, "elapsedSeconds": 1.0},
                "solver": {"exitCode": 0, "timedOut": False, "elapsedSeconds": 2.0},
                "selectedPhotopicContributionCdM2": value,
                "failure": None,
            }
            (case_dir / "case-result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        summary, complete = aggregate_module.aggregate(plan_path, cases_root, aggregate_dir)
        self.assertTrue(complete)
        self.assertEqual(summary["classification"], "BATCH_NUMERICALLY_COMPLETE")
        report, passed = audit_module.audit(plan_path, cases_root, aggregate_dir, self.root / "audit.json")
        self.assertTrue(passed)
        self.assertEqual(report["status"], "PASSED")

    def test_aggregate_refuses_completed_case_with_wrong_counts(self) -> None:
        plan_path = self.root / "plan-bad.json"
        cases_root = self.root / "cases-bad"
        aggregate_dir = self.root / "aggregate-bad"
        plan = {
            "stageId": "mystic-batch-v1",
            "scientificExecution": True,
            "batchId": "bad-counts-v1",
            "manifestRawSha256": "a" * 64,
            "authorizationRef": "b" * 40,
            "configuredMcPhotonsSum": 100,
            "runtimeLockRawSha256": "c" * 64,
            "scientificAdapterRawSha256": "d" * 64,
            "executionWorkflowRawSha256": "e" * 64,
            "cases": [{"ordinal": 1, "caseId": "case-1", "seed": 1, "photonHistories": 100}],
        }
        plan_path.write_text(json.dumps(plan))
        case_dir = cases_root / "case-1"
        case_dir.mkdir(parents=True)
        result = {
            "stageId": "mystic-batch-v1",
            "status": "COMPLETED",
            "scientificDiagnostic": True,
            "successDoesNotAuthorizeProduction": True,
            "batchId": plan["batchId"],
            "caseId": "case-1",
            "ordinal": 1,
            "seed": 1,
            "photonHistories": 100,
            "manifestRawSha256": plan["manifestRawSha256"],
            "adapterRawSha256": plan["scientificAdapterRawSha256"],
            "runtimeReportRawSha256": "f" * 64,
            "inputResolvedSha256": "1" * 64,
            "radianceOutputSha256": "2" * 64,
            "stdOutputSha256": "3" * 64,
            "syntaxCheckCount": 0,
            "solverExecutionCount": 1,
            "syntax": {"exitCode": 0, "timedOut": False, "elapsedSeconds": 1.0},
            "solver": {"exitCode": 0, "timedOut": False, "elapsedSeconds": 2.0},
            "selectedPhotopicContributionCdM2": 10.0,
            "failure": None,
        }
        (case_dir / "case-result.json").write_text(json.dumps(result))
        summary, complete = aggregate_module.aggregate(plan_path, cases_root, aggregate_dir)
        self.assertFalse(complete)
        self.assertEqual(summary["classification"], "STRUCTURAL_OR_EXECUTION_FAILURE")


if __name__ == "__main__":
    unittest.main()
