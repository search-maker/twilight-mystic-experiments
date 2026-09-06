from __future__ import annotations

import hashlib
import importlib.util
import json
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


guard_module = load_module("cg_execution_guard", PACKAGE / "cross_geometry_execution_guard.py")
plan_module = load_module("cg_execution_plan", PACKAGE / "cross_geometry_execution_plan.py")
adapter_module = load_module("cg_execution_adapter", PACKAGE / "cross_geometry_execution_adapter.py")
driver_module = load_module("cg_analysis_driver", PACKAGE / "cross_geometry_execution_analysis_driver.py")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def proposal_payload(case_count: int = 24) -> dict:
    cases = []
    for index in range(case_count):
        method = "reference-vroom" if index % 2 == 0 else "alis"
        cases.append(
            {
                "ordinal": index + 1,
                "caseId": f"case-{index + 1:02d}",
                "groupId": f"group-{index // 4 + 1}",
                "method": method,
                "block": index % 2 + 1,
                "seed": 80000 + index,
                "photonHistories": 20_000_000,
            }
        )
    return {
        "schemaVersion": 1,
        "stageId": "cross-geometry-pilot-v1",
        "batchId": "cross-geometry-pilot-screening-v1",
        "mode": "scientific-proposal",
        "proposalOnly": True,
        "scientificExecution": False,
        "successDoesNotAuthorizeProduction": True,
        "limits": {
            "maximumCases": case_count,
            "maximumParallel": 6,
            "maximumConfiguredMcPhotonsSum": case_count * 20_000_000,
            "perCaseTimeoutSeconds": 900,
        },
        "cases": cases,
    }


class CrossGeometryExecutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _guard_repo(self, extra_change: bool = False) -> tuple[Path, dict[str, Path], str, str]:
        repo = self.root / "repo"
        package = repo / "experiments/mystic-batch-v1"
        workflows = repo / ".github/workflows"
        package.mkdir(parents=True)
        workflows.mkdir(parents=True)
        paths = {
            "authorization": package / "authorization.cross-geometry.json",
            "proposal": package / "proposal.json",
            "contract": package / "contract.json",
            "proposal_template": package / "proposal-template.json",
            "proposal_adapter": package / "proposal-adapter.py",
            "proposal_validator": package / "proposal-validator.py",
            "execution_adapter": package / "execution-adapter.py",
            "execution_workflow": workflows / "execution.yml",
            "runtime_lock": package / "runtime-lock.json",
            "plan": package / "plan.py",
            "analysis_driver": package / "analysis.py",
            "executor": package / "executor.py",
            "aggregate": package / "aggregate.py",
            "audit": package / "audit.py",
        }
        proposal = proposal_payload()
        paths["proposal"].write_text(json.dumps(proposal, indent=2, sort_keys=True) + "\n")
        paths["contract"].write_text(json.dumps({"stageId": "cross-geometry-pilot-v1", "screeningOnly": True}) + "\n")
        paths["proposal_template"].write_text("{}\n")
        paths["proposal_adapter"].write_text("# proposal adapter\n")
        paths["proposal_validator"].write_text(
            "def validate(*args):\n    return {'status': 'PROPOSAL_VALIDATED_NO_EXECUTION'}\n"
        )
        for key in ("execution_adapter", "execution_workflow", "runtime_lock", "plan", "analysis_driver", "executor", "aggregate", "audit"):
            paths[key].write_text(f"# {key}\n")
        disabled = json.loads((PACKAGE / "authorization.cross-geometry-execution-template.json").read_text())
        paths["authorization"].write_text(json.dumps(disabled, indent=2, sort_keys=True) + "\n")
        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
        subprocess.run(["git", "add", "."], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-m", "parent"], cwd=repo, check=True, capture_output=True)
        parent = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
        execution_key = "cross-geometry-pilot-v1:screening:1"
        enabled = {
            **disabled,
            "authorized": True,
            "scientificExecution": True,
            "scientificDiagnostic": True,
            "executionKey": execution_key,
            "batchId": proposal["batchId"],
            "proposalPath": paths["proposal"].relative_to(repo).as_posix(),
            "proposalRawSha256": sha(paths["proposal"]),
            "contractRawSha256": sha(paths["contract"]),
            "proposalAdapterRawSha256": sha(paths["proposal_adapter"]),
            "proposalValidatorRawSha256": sha(paths["proposal_validator"]),
            "executionAdapterRawSha256": sha(paths["execution_adapter"]),
            "executionWorkflowRawSha256": sha(paths["execution_workflow"]),
            "runtimeLockRawSha256": sha(paths["runtime_lock"]),
            "planRawSha256": sha(paths["plan"]),
            "analysisDriverRawSha256": sha(paths["analysis_driver"]),
            "executorRawSha256": sha(paths["executor"]),
            "aggregateRawSha256": sha(paths["aggregate"]),
            "auditRawSha256": sha(paths["audit"]),
            "exactAuthorizationParentCommit": parent,
            "authorizationOrdinal": 1,
        }
        paths["authorization"].write_text(json.dumps(enabled, indent=2, sort_keys=True) + "\n")
        if extra_change:
            paths["runtime_lock"].write_text("# changed in authorization commit\n")
        subprocess.run(["git", "add", "."], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-m", "authorize"], cwd=repo, check=True, capture_output=True)
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
        return repo, paths, head, execution_key

    def _call_guard(self, repo: Path, paths: dict[str, Path], head: str, key: str):
        rel = {name: path.relative_to(repo) for name, path in paths.items()}
        return guard_module.validate_guard(
            repo,
            rel["authorization"], rel["proposal"], rel["contract"], rel["proposal_template"],
            rel["proposal_adapter"], rel["proposal_validator"], rel["execution_adapter"],
            rel["execution_workflow"], rel["runtime_lock"], rel["plan"], rel["analysis_driver"],
            rel["executor"], rel["aggregate"], rel["audit"], head, key, 1,
            require_github_context=False,
        )

    def test_exact_one_purpose_authorization_guard(self) -> None:
        repo, paths, head, key = self._guard_repo()
        report = self._call_guard(repo, paths, head, key)
        self.assertEqual(report["status"], "AUTHORIZED")
        self.assertEqual(report["caseCount"], 24)
        self.assertEqual(report["configuredMcPhotonsSum"], 480_000_000)

    def test_guard_refuses_multi_file_authorization_commit(self) -> None:
        repo, paths, head, key = self._guard_repo(extra_change=True)
        with self.assertRaises(guard_module.GuardRefusal):
            self._call_guard(repo, paths, head, key)

    def test_plan_builds_exact_method_matrix(self) -> None:
        proposal_path = self.root / "proposal.json"
        guard_path = self.root / "guard.json"
        proposal = proposal_payload(4)
        proposal["limits"]["maximumParallel"] = 2
        proposal_path.write_text(json.dumps(proposal))
        guard_path.write_text(json.dumps({
            "status": "AUTHORIZED",
            "stageId": "cross-geometry-pilot-v1",
            "batchId": proposal["batchId"],
            "proposalRawSha256": "a" * 64,
            "authorizationRef": "b" * 40,
            "authorizationOrdinal": 1,
            "executionKey": "key-1",
        }))
        plan = plan_module.build_plan(proposal_path, guard_path)
        self.assertEqual(plan["scientificPurpose"], "cross-geometry-pilot-v1")
        self.assertEqual([item["method"] for item in plan["matrix"]["include"]], ["reference-vroom", "alis", "reference-vroom", "alis"])
        self.assertEqual(plan["configuredMcPhotonsSum"], 80_000_000)

    def _fake_proposal_adapter(self) -> Path:
        path = self.root / "fake_proposal_adapter.py"
        path.write_text(textwrap.dedent("""
            def validate_manifest(proposal):
                if proposal.get('proposalOnly') is not True:
                    raise RuntimeError('not proposal')
            def resolve_case(proposal, case_id):
                case = next(case for case in proposal['cases'] if case['caseId'] == case_id)
                return case, proposal['geometries'][0]
            def normalized_inputs(proposal, case, geometry):
                return {'method': case['method'], 'seed': case['seed'], 'photonHistories': case['photonHistories']}
            def render_input(inputs, data_dir, repository_root, case_dir):
                return f"method {inputs['method']}\\nseed {inputs['seed']}\\n"
        """))
        return path

    def _adapter_fixture(self) -> tuple[Path, Path]:
        proposal_path = self.root / "adapter-proposal.json"
        runtime_path = self.root / "runtime.json"
        runtime = {
            "uvspecSha256": "1" * 64,
            "uvspecHelpSha256": "2" * 64,
            "libRadtranDataTreeSha256": "3" * 64,
            "atmosphereSha256": "4" * 64,
            "runtimeLockRawSha256": "5" * 64,
        }
        proposal = {
            "proposalOnly": True,
            "batchId": "adapter-test",
            "runtime": runtime,
            "geometries": [{"geometryId": "g1"}],
            "cases": [
                {"caseId": "ref-case", "groupId": "g1", "method": "reference-vroom", "block": 1, "seed": 1, "photonHistories": 10},
                {"caseId": "alis-case", "groupId": "g1", "method": "alis", "block": 1, "seed": 2, "photonHistories": 10},
            ],
        }
        report = {
            "schemaVersion": 1,
            "stageId": "mystic-batch-v1",
            "scientificSolverExecuted": False,
            "syntaxCheckExecuted": False,
            **runtime,
        }
        proposal_path.write_text(json.dumps(proposal))
        runtime_path.write_text(json.dumps(report))
        return proposal_path, runtime_path

    def test_execution_adapter_prepares_both_methods_after_runtime_check(self) -> None:
        proposal, runtime = self._adapter_fixture()
        fake = self._fake_proposal_adapter()
        with mock.patch.object(adapter_module, "PROPOSAL_ADAPTER", fake):
            ref = adapter_module.prepare_case(proposal, runtime, "ref-case", self.root, self.root, self.root / "ref-out")
            alis = adapter_module.prepare_case(proposal, runtime, "alis-case", self.root, self.root, self.root / "alis-out")
        self.assertEqual(ref["method"], "reference-vroom")
        self.assertEqual(alis["method"], "alis")
        self.assertNotEqual(ref["inputResolvedSha256"], alis["inputResolvedSha256"])

    def test_execution_adapter_refuses_runtime_mismatch(self) -> None:
        proposal, runtime = self._adapter_fixture()
        report = json.loads(runtime.read_text())
        report["uvspecSha256"] = "0" * 64
        runtime.write_text(json.dumps(report))
        with mock.patch.object(adapter_module, "PROPOSAL_ADAPTER", self._fake_proposal_adapter()):
            with self.assertRaises(adapter_module.AdapterRefusal):
                adapter_module.prepare_case(proposal, runtime, "ref-case", self.root, self.root, self.root / "out")

    def _analysis_fixture(self, omit_last: bool = False):
        proposal = proposal_payload(4)
        proposal_path = self.root / "analysis-proposal.json"
        contract_path = self.root / "contract.json"
        summary_path = self.root / "summary.json"
        audit_path = self.root / "audit.json"
        cases_root = self.root / "cases"
        proposal_path.write_text(json.dumps(proposal, indent=2, sort_keys=True) + "\n")
        contract_path.write_text(json.dumps({"stageId": "cross-geometry-pilot-v1"}))
        summary_path.write_text(json.dumps({"status": "COMPLETED", "classification": "BATCH_NUMERICALLY_COMPLETE"}))
        audit_path.write_text(json.dumps({"status": "PASSED"}))
        selected = proposal["cases"][:-1] if omit_last else proposal["cases"]
        manifest_hash = sha(proposal_path)
        for case in selected:
            case_dir = cases_root / case["caseId"]
            case_dir.mkdir(parents=True)
            record = {
                "status": "COMPLETED",
                "batchId": proposal["batchId"],
                "caseId": case["caseId"],
                "ordinal": case["ordinal"],
                "seed": case["seed"],
                "photonHistories": case["photonHistories"],
                "manifestRawSha256": manifest_hash,
                "syntaxCheckCount": 1,
                "solverExecutionCount": 1,
                "syntax": {"timedOut": False, "exitCode": 0},
                "solver": {"timedOut": False, "exitCode": 0},
                "selectedPhotopicContributionCdM2": 1.0,
                "selectedNodeRadiance": [1.0] * 15,
                "selectedNodeStdRadiance": [0.01] * 15,
            }
            (case_dir / "case-result.json").write_text(json.dumps(record))
        fake_analysis = self.root / "fake_analysis.py"
        fake_analysis.write_text(textwrap.dedent("""
            def analyze(proposal_path, contract_path, records_path):
                return {
                    'schemaVersion': 1,
                    'stageId': 'cross-geometry-pilot-v1',
                    'status': 'SCREENING_ANALYZED',
                    'classificationCounts': {'STRUCTURAL_OR_EXECUTION_FAILURE': 0, 'SCREENING_AGREEMENT': 1},
                    'geometryResults': [],
                    'boundary': 'screening only'
                }
        """))
        return proposal_path, contract_path, cases_root, summary_path, audit_path, fake_analysis

    def test_analysis_driver_binds_generic_audit_and_screening(self) -> None:
        fixture = self._analysis_fixture()
        with mock.patch.object(driver_module, "ANALYSIS_MODULE", fixture[-1]):
            result, passed = driver_module.analyze_artifacts(*fixture[:-1], self.root / "analysis-output")
        self.assertTrue(passed)
        self.assertTrue(result["executionArtifactAuditPassed"])
        self.assertEqual(result["caseResultCount"], 4)

    def test_analysis_driver_refuses_missing_case(self) -> None:
        fixture = self._analysis_fixture(omit_last=True)
        with mock.patch.object(driver_module, "ANALYSIS_MODULE", fixture[-1]):
            with self.assertRaises(driver_module.DriverFailure):
                driver_module.analyze_artifacts(*fixture[:-1], self.root / "analysis-output-missing")


if __name__ == "__main__":
    unittest.main()
