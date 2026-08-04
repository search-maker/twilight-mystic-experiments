from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "experiments/mystic-batch-v1/cross_geometry_g01_precision_recovery_plan.py"
spec = importlib.util.spec_from_file_location("recovery", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n")


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.preflight = self.root / "preflight"
        self.cases = self.root / "cases"
        self.run = self.root / "run.json"
        self.jobs = self.root / "jobs.json"
        self.artifacts = self.root / "artifacts.json"
        self.auth = self.root / "authorization.json"
        include = [
            {"case_id": item["caseId"], "ordinal": item["ordinal"], "block": item["block"], "seed": item["seed"], "photon_histories": item["photonHistories"]}
            for item in module.EXPECTED_CASES
        ]
        write(self.preflight / "plan.json", {
            "schemaVersion": 1,
            "stageId": module.SOURCE_STAGE_ID,
            "status": "PLAN_FROZEN",
            "caseCount": 4,
            "configuredMcPhotonsSum": 200_000_000,
            "maxParallel": 4,
            "timeoutSeconds": 900,
            "matrix": {"include": include},
        })
        write(self.preflight / "authorization-guard.json", {
            "status": "AUTHORIZED",
            "stageId": module.SOURCE_STAGE_ID,
            "authorizationOrdinal": 7,
            "authorizationParentCommit": module.SOURCE_HEAD_SHA,
            "authorizationRef": module.AUTHORIZATION_REF,
            "executionKey": module.EXECUTION_KEY,
            "sourceDiagnosisRunId": 30876899126,
            "sourceRunId": 30875148389,
            "caseCount": 4,
            "configuredMcPhotonsSum": 200_000_000,
            "manifestRawSha256": module.MANIFEST_SHA,
        })
        write(self.preflight / "duplicate-run-audit.json", {
            "status": "PASS",
            "currentRunId": module.SOURCE_RUN_ID,
            "matchingPriorRunCount": 0,
        })
        write(self.run, {
            "id": module.SOURCE_RUN_ID,
            "status": "completed",
            "conclusion": "failure",
            "event": "workflow_dispatch",
            "run_attempt": 1,
            "head_branch": "main",
            "head_sha": module.SOURCE_HEAD_SHA,
            "name": f"G01 held-out precision continuation | key={module.EXECUTION_KEY} | auth={module.AUTHORIZATION_REF} | ordinal=7",
        })
        jobs = [{"name": "preflight", "conclusion": "success"}, {"name": "aggregate", "conclusion": "failure"}]
        jobs.extend({"name": f"cases ({item['caseId']}, fixture)", "conclusion": "success"} for item in module.EXPECTED_CASES)
        write(self.jobs, {"jobs": jobs})
        write(self.artifacts, {"artifacts": [
            {"name": name, "id": artifact_id, "digest": digest, "expired": False, "workflow_run": {"id": module.SOURCE_RUN_ID}}
            for name, (artifact_id, digest) in module.EXPECTED_ARTIFACTS.items()
        ]})
        write(self.auth, {
            "schemaVersion": 1,
            "stageId": module.SOURCE_STAGE_ID,
            "authorized": True,
            "scientificExecution": True,
            "scientificDiagnostic": True,
            "authorizationOrdinal": 7,
            "exactAuthorizationParentCommit": module.SOURCE_HEAD_SHA,
            "executionKey": module.EXECUTION_KEY,
            "sourceDiagnosisRunId": 30876899126,
            "sourceRunId": 30875148389,
            "proposalRawSha256": module.MANIFEST_SHA,
            "executionAdapterRawSha256": module.ADAPTER_SHA,
            "runtimeLockRawSha256": "1" * 64,
            "executionWorkflowRawSha256": "2" * 64,
            "aggregateRawSha256": "3" * 64,
            "auditRawSha256": "4" * 64,
            "analysisDriverRawSha256": "5" * 64,
        })
        for index, item in enumerate(module.EXPECTED_CASES):
            write(self.cases / item["caseId"] / "case-result.json", {
                "caseId": item["caseId"],
                "stageId": "mystic-batch-v1",
                "batchId": module.BATCH_ID,
                "ordinal": item["ordinal"],
                "seed": item["seed"],
                "photonHistories": item["photonHistories"],
                "manifestRawSha256": module.MANIFEST_SHA,
                "adapterRawSha256": module.ADAPTER_SHA,
                "scientificDiagnostic": True,
                "successDoesNotAuthorizeProduction": True,
                "status": "COMPLETED",
                "syntaxCheckCount": 1,
                "solverExecutionCount": 1,
                "syntax": {"exitCode": 0, "timedOut": False},
                "solver": {"exitCode": 0, "timedOut": False},
                "selectedPhotopicContributionCdM2": 0.003 + 0.0001 * index,
                "selectedNodeRadiance": [0.0001 + index * 0.000001] * 15,
                "inputResolvedSha256": "a" * 64,
                "radianceOutputSha256": "b" * 64,
                "stdOutputSha256": "c" * 64,
                "runtimeReportRawSha256": "d" * 64,
            })

    def tearDown(self):
        self.temp.cleanup()

    def call(self):
        return module.build(self.preflight, self.cases, self.run, self.jobs, self.artifacts, self.auth)

    def test_builds_generic_postprocess_plan(self):
        plan, audit = self.call()
        self.assertEqual(plan["stageId"], "mystic-batch-v1")
        self.assertTrue(plan["scientificExecution"])
        self.assertEqual(len(plan["cases"]), 4)
        self.assertEqual(plan["configuredMcPhotonsSum"], 200_000_000)
        self.assertEqual(audit["status"], "SOURCE_ARTIFACTS_VERIFIED_FOR_POSTPROCESS_ONLY")
        self.assertFalse(audit["scientificExecution"])
        self.assertTrue(audit["postprocessOnly"])

    def test_refuses_nonfailed_source_boundary(self):
        value = json.loads(self.run.read_text())
        value["conclusion"] = "success"
        write(self.run, value)
        with self.assertRaises(module.RecoveryError):
            self.call()

    def test_refuses_changed_case_seed(self):
        path = self.cases / module.EXPECTED_CASES[0]["caseId"] / "case-result.json"
        value = json.loads(path.read_text())
        value["seed"] += 1
        write(path, value)
        with self.assertRaises(module.RecoveryError):
            self.call()

    def test_refuses_nonfailed_aggregate(self):
        value = json.loads(self.jobs.read_text())
        next(job for job in value["jobs"] if job["name"] == "aggregate")["conclusion"] = "success"
        write(self.jobs, value)
        with self.assertRaises(module.RecoveryError):
            self.call()


if __name__ == "__main__":
    unittest.main()
