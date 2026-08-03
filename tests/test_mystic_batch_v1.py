from __future__ import annotations

import importlib.util
import json
import shutil
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


plan_module = load_module("mystic_batch_plan", PACKAGE / "plan.py")
case_module = load_module("mystic_batch_case", PACKAGE / "synthetic_case_runner.py")
aggregate_module = load_module("mystic_batch_aggregate", PACKAGE / "aggregate.py")
audit_module = load_module("mystic_batch_audit", PACKAGE / "audit.py")


class MysticBatchV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.manifest = self.root / "manifest.json"
        self.authorization = self.root / "authorization.json"
        shutil.copy2(PACKAGE / "manifest.synthetic.json", self.manifest)
        shutil.copy2(PACKAGE / "authorization.json", self.authorization)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def build_plan(self):
        return plan_module.build_plan(self.manifest, self.authorization, allow_synthetic=True)

    def write_plan(self):
        plan = self.build_plan()
        path = self.root / "plan.json"
        path.write_text(plan_module.dump_json(plan))
        return plan, path

    def run_pipeline(self):
        plan, plan_path = self.write_plan()
        cases_root = self.root / "case-output"
        for case in plan["cases"]:
            case_module.run_case(plan_path, case["caseId"], cases_root)
        aggregate_dir = self.root / "aggregate"
        aggregate = aggregate_module.aggregate_batch(plan_path, cases_root, aggregate_dir)
        audit_path = self.root / "audit" / "audit-report.json"
        audit = audit_module.audit_batch(plan_path, cases_root, aggregate_dir, audit_path)
        return plan, cases_root, aggregate_dir, aggregate, audit

    def test_end_to_end_synthetic_matrix_contract(self) -> None:
        plan, _, _, aggregate, audit = self.run_pipeline()
        self.assertEqual(plan["caseCount"], 6)
        self.assertEqual(plan["maximumParallel"], 6)
        self.assertEqual(aggregate["syntheticExecutionCount"], 6)
        self.assertEqual(aggregate["syntaxCheckCount"], 0)
        self.assertEqual(aggregate["solverExecutionCount"], 0)
        self.assertEqual(audit["status"], "PASSED")
        self.assertFalse(audit["scientificResult"])

    def test_duplicate_seed_is_refused(self) -> None:
        manifest = json.loads(self.manifest.read_text())
        manifest["cases"][1]["seed"] = manifest["cases"][0]["seed"]
        self.manifest.write_text(json.dumps(manifest))
        with self.assertRaises(plan_module.BatchRefusal) as caught:
            self.build_plan()
        self.assertEqual(caught.exception.code, "duplicate-case-identity")

    def test_photon_ceiling_is_refused(self) -> None:
        manifest = json.loads(self.manifest.read_text())
        manifest["limits"]["maximumConfiguredMcPhotonsSum"] = 100
        self.manifest.write_text(json.dumps(manifest))
        with self.assertRaises(plan_module.BatchRefusal) as caught:
            self.build_plan()
        self.assertEqual(caught.exception.code, "photon-ceiling")

    def test_synthetic_run_requires_disabled_authorization(self) -> None:
        authorization = json.loads(self.authorization.read_text())
        authorization["authorized"] = True
        self.authorization.write_text(json.dumps(authorization))
        with self.assertRaises(plan_module.BatchRefusal) as caught:
            self.build_plan()
        self.assertEqual(caught.exception.code, "synthetic-authorization")

    def test_scientific_mode_requires_pinned_runtime_and_remains_disabled(self) -> None:
        manifest = json.loads(self.manifest.read_text())
        manifest["mode"] = "scientific"
        manifest["scientificExecution"] = True
        manifest["runtime"].update(
            {
                "containerImageDigest": "sha256:" + "a" * 64,
                "uvspecSha256": "b" * 64,
                "libRadtranDataSha256": "c" * 64,
                "atmosphereSha256": "d" * 64,
            }
        )
        self.manifest.write_text(json.dumps(manifest, sort_keys=True))
        authorization = json.loads(self.authorization.read_text())
        authorization.update(
            {
                "authorized": True,
                "scientificExecution": True,
                "batchId": manifest["batchId"],
                "manifestRawSha256": plan_module.raw_sha256(self.manifest),
                "authorizationOrdinal": 1,
            }
        )
        self.authorization.write_text(json.dumps(authorization))
        with self.assertRaises(plan_module.BatchRefusal) as caught:
            self.build_plan()
        self.assertEqual(caught.exception.code, "scientific-adapter-not-installed")

    def test_audit_detects_tampered_seed(self) -> None:
        plan, cases_root, aggregate_dir, _, _ = self.run_pipeline()
        case_id = plan["cases"][0]["caseId"]
        result_path = cases_root / case_id / "case-result.json"
        result = json.loads(result_path.read_text())
        result["seed"] += 1
        result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        with self.assertRaises(audit_module.AuditFailure):
            audit_module.audit_batch(
                self.root / "plan.json",
                cases_root,
                aggregate_dir,
                self.root / "audit-tampered.json",
            )


if __name__ == "__main__":
    unittest.main()
