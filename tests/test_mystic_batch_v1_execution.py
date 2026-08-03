from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "experiments" / "mystic-batch-v1"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


plan_module = load_module("mystic_scientific_plan", PACKAGE / "scientific_plan.py")
duplicate_module = load_module("mystic_duplicate_audit", PACKAGE / "duplicate_batch_audit.py")
case_module = load_module("mystic_scientific_case", PACKAGE / "scientific_case_runner.py")
aggregate_module = load_module("mystic_scientific_aggregate", PACKAGE / "scientific_aggregate.py")
audit_module = load_module("mystic_scientific_audit", PACKAGE / "scientific_audit.py")

NODES = [470, 480, 490, 500, 510, 520, 530, 540, 560, 580, 590, 600, 610, 640, 660]
WEIGHTS = [0.09098, 0.13902, 0.20802, 0.323, 0.503, 0.71, 0.862, 0.954, 0.995, 0.87, 0.757, 0.631, 0.503, 0.175, 0.061]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class MysticBatchExecutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.manifest_path = self.root / "manifests" / "batch.json"
        self.authorization_path = self.root / "experiments" / "mystic-batch-v1" / "authorization.scientific.json"
        self.adapter_path = self.root / "experiments" / "mystic-batch-v1" / "scientific_adapter.py"
        self.runtime_lock_path = self.root / "experiments" / "mystic-batch-v1" / "runtime-lock.micromamba.json"
        self.workflow_path = self.root / ".github" / "workflows" / "mystic-batch-v1-execution.yml"
        for path in (self.manifest_path, self.authorization_path, self.adapter_path, self.runtime_lock_path, self.workflow_path):
            path.parent.mkdir(parents=True, exist_ok=True)
        self.adapter_path.write_text("adapter-v1\n")
        self.runtime_lock_path.write_text("runtime-lock-v1\n")
        self.workflow_path.write_text("workflow-v1\n")
        self.manifest = self.make_manifest()
        self.manifest_path.write_text(json.dumps(self.manifest, indent=2, sort_keys=True) + "\n")
        self.authorization = self.make_authorization(enabled=False)
        self.authorization_path.write_text(json.dumps(self.authorization, indent=2, sort_keys=True) + "\n")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def make_manifest(self) -> dict:
        return {
            "schemaVersion": 1,
            "stageId": "mystic-batch-v1",
            "batchId": "test-reference-batch-v1",
            "mode": "scientific",
            "scientificExecution": True,
            "adapterId": "mystic-spectral-radiance-v1",
            "runtime": {
                "kind": "micromamba-lock",
                "containerImageDigest": None,
                "exactPackageSpec": "rubin-libradtran=2.0.6=py312pl5321he9373c2_1",
                "uvspecSha256": "1" * 64,
                "uvspecHelpSha256": "2" * 64,
                "libRadtranDataTreeSha256": "3" * 64,
                "atmosphereSha256": "4" * 64,
                "runtimeLockRawSha256": "5" * 64,
            },
            "limits": {
                "maximumCases": 2,
                "maximumParallel": 2,
                "maximumConfiguredMcPhotonsSum": 2000,
                "perCaseTimeoutSeconds": 60,
            },
            "frozenInputs": {
                "wavelengthDomainNm": [380, 780],
                "diagnosticNodesNm": NODES,
                "molecularAbsorption": "crs",
                "mcSpherical": "1D",
                "mcVroom": "on",
                "aod550": 0.15,
                "albedo": 0.15,
                "dataPaths": {
                    "solarFlux": {"root": "libRadtranData", "path": "solar_flux/atlas_plus_modtran"},
                    "wavelengthGrid": {"root": "repository", "path": "wavelength-grid.dat"},
                    "atmosphere": {"root": "libRadtranData", "path": "atmmod/afglus.dat"},
                },
            },
            "analysis": {
                "metricId": "selected-photopic-contribution-v1",
                "photopicWeights": WEIGHTS,
                "wavelengthBinWidthNm": 10.0,
                "luminousEfficacyLmPerW": 683.002,
                "radianceUnitScale": 0.001,
            },
            "cases": [
                {
                    "ordinal": 1,
                    "caseId": "case-seed-1001",
                    "seed": 1001,
                    "photonHistories": 1000,
                    "parameters": {
                        "sunDepressionDeg": 12.0,
                        "targetAltitudeDeg": 10.0,
                        "relativeAzimuthDeg": 120.0,
                        "observerElevationM": 0.0,
                    },
                },
                {
                    "ordinal": 2,
                    "caseId": "case-seed-1002",
                    "seed": 1002,
                    "photonHistories": 1000,
                    "parameters": {
                        "sunDepressionDeg": 12.0,
                        "targetAltitudeDeg": 10.0,
                        "relativeAzimuthDeg": 120.0,
                        "observerElevationM": 0.0,
                    },
                },
            ],
        }

    def make_authorization(self, enabled: bool) -> dict:
        return {
            "schemaVersion": 1,
            "stageId": "mystic-batch-v1",
            "authorized": enabled,
            "scientificExecution": enabled,
            "batchId": self.manifest["batchId"] if enabled else None,
            "manifestPath": self.manifest_path.relative_to(self.root).as_posix() if enabled else None,
            "manifestRawSha256": sha256(self.manifest_path) if enabled else None,
            "runtimeLockRawSha256": sha256(self.runtime_lock_path) if enabled else None,
            "scientificAdapterRawSha256": sha256(self.adapter_path) if enabled else None,
            "executionWorkflowRawSha256": sha256(self.workflow_path) if enabled else None,
            "exactAuthorizationParentCommit": "a" * 40 if enabled else None,
            "exactAuthorizationCommit": None,
            "authorizationOrdinal": 1 if enabled else 0,
            "consumed": False,
        }

    def build_plan(self) -> dict:
        return plan_module.build_plan(
            self.manifest_path,
            self.authorization_path,
            self.adapter_path,
            self.runtime_lock_path,
            self.workflow_path,
            self.root,
            allow_test_context=True,
        )

    def enable_authorization(self) -> None:
        self.authorization = self.make_authorization(enabled=True)
        self.authorization_path.write_text(json.dumps(self.authorization, indent=2, sort_keys=True) + "\n")

    def test_disabled_authorization_refuses_before_execution(self) -> None:
        with self.assertRaises(plan_module.PlanRefusal) as caught:
            self.build_plan()
        self.assertEqual(caught.exception.code, "authorization")

    def test_exact_authorization_builds_matrix_plan(self) -> None:
        self.enable_authorization()
        plan = self.build_plan()
        self.assertEqual(plan["status"], "AUTHORIZED_PLAN")
        self.assertEqual(plan["caseCount"], 2)
        self.assertEqual(plan["maximumParallel"], 2)
        self.assertEqual([item["case_id"] for item in plan["matrix"]["include"]], ["case-seed-1001", "case-seed-1002"])

    def test_duplicate_audit_self_test(self) -> None:
        result = duplicate_module.self_test()
        self.assertEqual(result["status"], "PASS")

    def create_fake_uvspec(self) -> Path:
        executable = self.root / "fake-uvspec"
        executable.write_text(
            "#!/usr/bin/env python3\n"
            "import pathlib, sys\n"
            "text = sys.stdin.read()\n"
            "if '-c' in sys.argv[1:]:\n"
            "    raise SystemExit(0)\n"
            "base = None\n"
            "for line in text.splitlines():\n"
            "    if line.startswith('mc_basename '):\n"
            "        base = pathlib.Path(line.split(' ', 1)[1])\n"
            "if base is None:\n"
            "    raise SystemExit(3)\n"
            f"nodes = {NODES!r}\n"
            "base.parent.mkdir(parents=True, exist_ok=True)\n"
            "rad = '\\n'.join(f'{node} {1.0 + index / 10.0}' for index, node in enumerate(nodes)) + '\\n'\n"
            "std = '\\n'.join(f'{node} 0.01' for node in nodes) + '\\n'\n"
            "pathlib.Path(str(base) + '.rad.spc').write_text(rad)\n"
            "pathlib.Path(str(base) + '.rad.std.spc').write_text(std)\n"
            "raise SystemExit(0)\n"
        )
        executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
        return executable

    def create_proposal(self, plan: dict, case: dict, cases_root: Path) -> Path:
        case_dir = cases_root / "prepared" / case["caseId"]
        case_dir.mkdir(parents=True, exist_ok=True)
        input_path = case_dir / "input-resolved.txt"
        input_path.write_text(f"mc_basename {case_dir / 'mc'}\n")
        runtime_report_path = cases_root / "runtime-report.json"
        if not runtime_report_path.exists():
            runtime_report_path.write_text(json.dumps({"runtime": "test"}, sort_keys=True) + "\n")
        proposal = {
            "schemaVersion": 1,
            "stageId": "mystic-batch-v1",
            "adapterId": "mystic-spectral-radiance-v1",
            "status": "PREPARED_NO_SOLVER",
            "scientificSolverExecuted": False,
            "batchId": plan["batchId"],
            "caseId": case["caseId"],
            "manifestRawSha256": plan["manifestRawSha256"],
            "runtimeReportRawSha256": sha256(runtime_report_path),
            "inputResolvedSha256": hashlib.sha256(input_path.read_text().encode()).hexdigest(),
            "inputs": {
                "ordinal": case["ordinal"],
                "seed": case["seed"],
                "photonHistories": case["photonHistories"],
            },
            "inputPath": str(input_path),
        }
        proposal_path = case_dir / "case-proposal.json"
        proposal_path.write_text(json.dumps(proposal, indent=2, sort_keys=True) + "\n")
        return proposal_path, runtime_report_path

    def run_complete_batch(self):
        self.enable_authorization()
        plan = self.build_plan()
        plan_path = self.root / "preflight" / "plan.json"
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        plan_path.write_text(plan_module.dump_json(plan))
        cases_root = self.root / "case-artifacts"
        fake_uvspec = self.create_fake_uvspec()
        for case in plan["cases"]:
            proposal_path, runtime_report_path = self.create_proposal(plan, case, cases_root)
            result, ok = case_module.execute_case(
                plan_path, proposal_path, runtime_report_path, case["caseId"], fake_uvspec
            )
            self.assertTrue(ok, result)
        aggregate_dir = self.root / "aggregate-output"
        aggregate = aggregate_module.aggregate_batch(plan_path, cases_root, aggregate_dir)
        audit_path = self.root / "audit-output" / "audit-report.json"
        audit = audit_module.audit_batch(plan_path, cases_root, aggregate_dir, audit_path)
        return plan, plan_path, cases_root, aggregate_dir, aggregate, audit

    def test_fake_solver_end_to_end_aggregate_and_audit(self) -> None:
        plan, _, _, _, aggregate, audit = self.run_complete_batch()
        self.assertEqual(aggregate["status"], "COMPLETED")
        self.assertEqual(aggregate["syntaxCheckCount"], 2)
        self.assertEqual(aggregate["solverExecutionCount"], 2)
        self.assertEqual(aggregate["completedConfiguredMcPhotonsSum"], 2000)
        self.assertEqual(audit["status"], "PASSED")
        self.assertEqual(audit["seeds"], [1001, 1002])
        self.assertFalse(aggregate["scientificInterpretationAssigned"])
        self.assertEqual(plan["configuredMcPhotonsSum"], 2000)

    def test_audit_detects_tampered_case_result(self) -> None:
        _, plan_path, cases_root, aggregate_dir, _, _ = self.run_complete_batch()
        result_path = next(cases_root.rglob("case-result.json"))
        result = json.loads(result_path.read_text())
        result["seed"] += 1
        result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        with self.assertRaises(audit_module.AuditFailure):
            audit_module.audit_batch(
                plan_path,
                cases_root,
                aggregate_dir,
                self.root / "audit-output" / "tampered.json",
            )


if __name__ == "__main__":
    unittest.main()
