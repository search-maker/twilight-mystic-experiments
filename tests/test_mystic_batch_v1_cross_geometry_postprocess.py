from __future__ import annotations

import importlib.util
import json
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


plan_module = load_module("cross_geometry_execution_plan", PACKAGE / "cross_geometry_execution_plan.py")
postprocess_module = load_module("cross_geometry_postprocess", PACKAGE / "cross_geometry_postprocess.py")
aggregate_module = load_module("scientific_aggregate", PACKAGE / "scientific_aggregate.py") if (PACKAGE / "scientific_aggregate.py").is_file() else None
audit_module = load_module("scientific_audit", PACKAGE / "scientific_audit.py") if (PACKAGE / "scientific_audit.py").is_file() else None


def cases() -> list[dict]:
    values = []
    for index in range(24):
        values.append(
            {
                "ordinal": index + 1,
                "caseId": f"case-{index + 1:02d}",
                "groupId": f"g{index // 4 + 1:02d}",
                "method": "reference-vroom" if index % 2 == 0 else "alis",
                "block": index % 2 + 1,
                "seed": 78001 + index,
                "photonHistories": 20_000_000,
            }
        )
    return values


def proposal() -> dict:
    return {
        "schemaVersion": 1,
        "stageId": "cross-geometry-pilot-v1",
        "batchId": "cross-geometry-pilot-screening-v1",
        "proposalOnly": True,
        "scientificExecution": False,
        "limits": {
            "maximumCases": 24,
            "maximumParallel": 6,
            "maximumConfiguredMcPhotonsSum": 480_000_000,
            "perCaseTimeoutSeconds": 900,
        },
        "cases": cases(),
    }


def authorization(ordinal: int = 2) -> dict:
    return {
        "schemaVersion": 1,
        "stageId": "cross-geometry-pilot-v1",
        "authorized": True,
        "scientificExecution": True,
        "scientificDiagnostic": True,
        "successDoesNotAuthorizeProduction": True,
        "executionKey": f"cross-geometry-pilot-v1:screening:{ordinal}",
        "batchId": "cross-geometry-pilot-screening-v1",
        "authorizationOrdinal": ordinal,
        "proposalRawSha256": "1" * 64,
        "executionAdapterRawSha256": "2" * 64,
        "runtimeLockRawSha256": "3" * 64,
        "executionWorkflowRawSha256": "4" * 64,
    }


def guard(ordinal: int = 2) -> dict:
    return {
        "schemaVersion": 1,
        "stageId": "cross-geometry-pilot-v1",
        "status": "AUTHORIZED",
        "authorizationRef": "a" * 40,
        "executionKey": f"cross-geometry-pilot-v1:screening:{ordinal}",
        "authorizationOrdinal": ordinal,
        "batchId": "cross-geometry-pilot-screening-v1",
        "proposalRawSha256": "1" * 64,
        "caseCount": 24,
        "configuredMcPhotonsSum": 480_000_000,
    }


class CrossGeometryPostprocessTests(unittest.TestCase):
    def test_execution_plan_freezes_generic_aggregate_bindings(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            proposal_path = root / "manifest.cross-geometry-pilot.proposal.json"
            guard_path = root / "authorization-guard.json"
            auth_path = root / "authorization.cross-geometry.json"
            proposal_path.write_text(json.dumps(proposal()))
            guard_path.write_text(json.dumps(guard()))
            auth_path.write_text(json.dumps(authorization()))
            plan = plan_module.build_plan(proposal_path, guard_path)
        self.assertEqual(plan["scientificAdapterRawSha256"], "2" * 64)
        self.assertEqual(plan["runtimeLockRawSha256"], "3" * 64)
        self.assertEqual(plan["executionWorkflowRawSha256"], "4" * 64)
        self.assertEqual(plan["configuredMcPhotonsSum"], 480_000_000)

    def test_recovery_supplements_preserved_ordinal_two_plan(self) -> None:
        source_proposal = proposal()
        source_guard = guard()
        source_auth = authorization()
        old_plan = {
            "schemaVersion": 1,
            "stageId": "mystic-batch-v1",
            "scientificPurpose": "cross-geometry-pilot-v1",
            "batchId": source_proposal["batchId"],
            "mode": "scientific",
            "scientificExecution": True,
            "successDoesNotAuthorizeProduction": True,
            "manifestRawSha256": "1" * 64,
            "authorizationRef": "a" * 40,
            "authorizationOrdinal": 2,
            "executionKey": "cross-geometry-pilot-v1:screening:2",
            "caseCount": 24,
            "configuredMcPhotonsSum": 480_000_000,
            "cases": cases(),
        }
        duplicate = {
            "status": "PASS",
            "currentRunId": 30856116586,
            "displayTitle": "Cross geometry pilot v1 | key=cross-geometry-pilot-v1:screening:2 | auth="
            + "a" * 40
            + " | ordinal=2",
        }
        recovered = postprocess_module.recover_plan(
            old_plan,
            source_proposal,
            source_auth,
            source_guard,
            duplicate,
            "a" * 40,
            "cross-geometry-pilot-v1:screening:2",
            2,
        )
        self.assertEqual(recovered["scientificAdapterRawSha256"], "2" * 64)
        self.assertEqual(recovered["runtimeLockRawSha256"], "3" * 64)
        self.assertEqual(recovered["executionWorkflowRawSha256"], "4" * 64)
        self.assertEqual(recovered["recoveredFromRunId"], 30856116586)
        self.assertIn("artifact-only recovery", recovered["boundary"])

    def test_recovery_refuses_reused_ordinal(self) -> None:
        source_proposal = proposal()
        old_plan = {
            "schemaVersion": 1,
            "stageId": "mystic-batch-v1",
            "scientificPurpose": "cross-geometry-pilot-v1",
            "batchId": source_proposal["batchId"],
            "mode": "scientific",
            "scientificExecution": True,
            "successDoesNotAuthorizeProduction": True,
            "manifestRawSha256": "1" * 64,
            "authorizationRef": "a" * 40,
            "authorizationOrdinal": 2,
            "executionKey": "cross-geometry-pilot-v1:screening:2",
            "caseCount": 24,
            "configuredMcPhotonsSum": 480_000_000,
            "cases": cases(),
        }
        duplicate = {
            "status": "PASS",
            "currentRunId": 30856116586,
            "displayTitle": "prefix | key=cross-geometry-pilot-v1:screening:2 | auth=" + "a" * 40 + " | ordinal=2",
        }
        with self.assertRaises(postprocess_module.PostprocessRefusal):
            postprocess_module.recover_plan(
                old_plan,
                source_proposal,
                authorization(1),
                guard(),
                duplicate,
                "a" * 40,
                "cross-geometry-pilot-v1:screening:2",
                2,
            )

    @unittest.skipIf(aggregate_module is None or audit_module is None, "generic aggregate modules not present in isolated fixture")
    def test_recovered_plan_satisfies_generic_aggregate_and_audit(self) -> None:
        source_proposal = proposal()
        source_guard = guard()
        source_auth = authorization()
        old_plan = {
            "schemaVersion": 1,
            "stageId": "mystic-batch-v1",
            "scientificPurpose": "cross-geometry-pilot-v1",
            "batchId": source_proposal["batchId"],
            "mode": "scientific",
            "scientificExecution": True,
            "successDoesNotAuthorizeProduction": True,
            "manifestRawSha256": "1" * 64,
            "authorizationRef": "a" * 40,
            "authorizationOrdinal": 2,
            "executionKey": "cross-geometry-pilot-v1:screening:2",
            "caseCount": 24,
            "configuredMcPhotonsSum": 480_000_000,
            "cases": cases(),
        }
        duplicate = {
            "status": "PASS",
            "currentRunId": 30856116586,
            "displayTitle": "prefix | key=cross-geometry-pilot-v1:screening:2 | auth=" + "a" * 40 + " | ordinal=2",
        }
        recovered = postprocess_module.recover_plan(
            old_plan, source_proposal, source_auth, source_guard, duplicate,
            "a" * 40, "cross-geometry-pilot-v1:screening:2", 2,
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan_path = root / "recovered-plan.json"
            cases_root = root / "cases"
            aggregate_dir = root / "aggregate"
            audit_path = root / "audit" / "audit-report.json"
            plan_path.write_text(json.dumps(recovered))
            for case in recovered["cases"]:
                case_dir = cases_root / case["caseId"]
                case_dir.mkdir(parents=True)
                record = {
                    "stageId": "mystic-batch-v1",
                    "status": "COMPLETED",
                    "scientificDiagnostic": True,
                    "successDoesNotAuthorizeProduction": True,
                    "batchId": recovered["batchId"],
                    "caseId": case["caseId"],
                    "ordinal": case["ordinal"],
                    "seed": case["seed"],
                    "photonHistories": case["photonHistories"],
                    "manifestRawSha256": recovered["manifestRawSha256"],
                    "adapterRawSha256": recovered["scientificAdapterRawSha256"],
                    "runtimeReportRawSha256": "5" * 64,
                    "inputResolvedSha256": "6" * 64,
                    "radianceOutputSha256": "7" * 64,
                    "stdOutputSha256": "8" * 64,
                    "syntaxCheckCount": 1,
                    "solverExecutionCount": 1,
                    "syntax": {"exitCode": 0, "timedOut": False},
                    "solver": {"exitCode": 0, "timedOut": False},
                    "selectedPhotopicContributionCdM2": float(case["ordinal"]),
                    "failure": None,
                }
                (case_dir / "case-result.json").write_text(json.dumps(record))
            summary, complete = aggregate_module.aggregate(plan_path, cases_root, aggregate_dir)
            self.assertTrue(complete)
            self.assertEqual(summary["caseCountCompleted"], 24)
            report, passed = audit_module.audit(plan_path, cases_root, aggregate_dir, audit_path)
            self.assertTrue(passed)
            self.assertEqual(report["status"], "PASSED")


if __name__ == "__main__":
    unittest.main()
