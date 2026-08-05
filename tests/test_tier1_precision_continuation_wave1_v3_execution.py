from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXECUTION_PATH = ROOT / "experiments/tier1-precision-continuation-wave1-v3/execution.py"
PACKAGE_PATH = ROOT / "experiments/tier1-precision-continuation-wave1-v3/package.py"
PAGES_PATH = ROOT / "experiments/tier1-precision-continuation-wave1-v3/duplicate_pages.py"
ADAPTER_PATH = ROOT / "experiments/tier1-precision-continuation-wave1-v3/execution_adapter.py"
EXECUTOR_PATH = ROOT / "experiments/tier1-precision-continuation-wave1-v3/case_executor.py"
WORKFLOW_PATH = ROOT / ".github/workflows/tier1-precision-continuation-wave1-ordinal9-execution.yml"
CONTRACT_PATH = ROOT / ".github/workflows/tier1-precision-continuation-wave1-v3-execution-contract.yml"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


e = load(EXECUTION_PATH, "wave1_v3_execution_test")
p = load(PACKAGE_PATH, "wave1_v3_package_execution_test")
pages = load(PAGES_PATH, "wave1_v3_pages_execution_test")


def current_row(run_id: int = 101):
    return {
        "id": run_id,
        "display_title": e.RUN_TITLE,
        "status": "in_progress",
        "conclusion": None,
        "event": "workflow_dispatch",
        "run_attempt": 1,
        "head_sha": "b" * 40,
        "head_branch": "main",
    }


def inputs():
    context = {
        "eventName": "workflow_dispatch",
        "runAttempt": 1,
        "displayTitle": e.RUN_TITLE,
        "authorizationRef": "a" * 40,
        "authorizationOrdinal": 9,
        "executionKey": e.EXECUTION_KEY,
        "headBranch": "main",
        "headSha": "b" * 40,
        "runId": 101,
    }
    auth = {
        "schemaVersion": 1,
        "stageId": "tier1-precision-continuation-wave1-authorization-v3",
        "status": "AUTHORIZED_PENDING_SEPARATE_DISPATCH",
        "authorizationOrdinal": 9,
        "executionKey": e.EXECUTION_KEY,
        "runTitle": e.RUN_TITLE,
        "runAttempt": 1,
        "caseCount": 40,
        "blocks": [3, 4],
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
        "preregistrationSha256": e.EXPECTED_PREREGISTRATION_SHA256,
        "executionSourceHeadSha": context["headSha"],
    }
    metadata = {
        "authorizationCommit": context["authorizationRef"],
        "authorizationParent": context["headSha"],
        "changedFiles": [e.AUTHORIZATION_PATH],
        "parentCount": 1,
    }
    runtime = {
        "uvspecSha256": "1" * 64,
        "uvspecHelpSha256": "2" * 64,
        "libRadtranDataTreeSha256": "3" * 64,
        "atmosphereSha256": "4" * 64,
        "runtimeLockRawSha256": "5" * 64,
    }
    return auth, context, [current_row()], runtime, metadata


def fake_results(manifest):
    base = p.load_module(ROOT / p.BASE_PACKAGE_PATH, "wave1_v3_test_base")
    node_value = 1.0 / (6.83002 * sum(base.CIE))
    nodes = [node_value] * len(base.CIE)
    value = base._photopic_value(nodes)
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
            "alisSpectralImportanceSamplingNm": case["alisSpectralImportanceSamplingNm"],
            "geometrySha256": case["geometrySha256"],
            "manifestSha256": manifest["manifestSha256"],
            "runtimeReportSha256": "6" * 64,
            "inputSha256": "7" * 64,
            "radianceOutputSha256": "8" * 64,
            "stdOutputSha256": "9" * 64,
            "artifactSha256": "a" * 64,
            "runtimeSha256": "b" * 64,
            "syntaxCheckCount": 1,
            "solverExecutionCount": 1,
            "syntax": {"exitCode": 0, "timedOut": False},
            "solver": {"exitCode": 0, "timedOut": False},
            "selectedNodeRadiance": nodes,
            "selectedNodeStdRadiance": [0.0] * len(nodes),
            "selectedPhotopicContributionCdM2": value,
            "valueCdM2": value,
            "zeroHit": False,
            "fittingSurfaceExposed": False,
            "retryAllowed": False,
            "resumeAllowed": False,
        }
        row["contentSha256"] = e.canonical_sha256(row)
        rows.append(row)
    return rows


class V3ExecutionTests(unittest.TestCase):
    def test_manifest_is_deterministic_and_exact(self):
        auth, context, runs, runtime, metadata = inputs()
        first = e.build_manifest(ROOT, auth, context, runs, runtime, metadata)
        second = e.build_manifest(ROOT, auth, context, runs, runtime, metadata)
        self.assertEqual(first, second)
        e.validate_manifest(first)
        self.assertEqual(first["caseCount"], 40)
        self.assertEqual(first["geometryCount"], 20)
        self.assertEqual(first["maximumConfiguredPhotonHistories"], 5_100_000_000)
        self.assertEqual(first["seedProof"]["historicalOverlap"], [])
        self.assertEqual(first["seedProof"]["ordinal8Overlap"], [])
        self.assertTrue(first["solverExecutionAuthorized"])
        self.assertFalse(first["githubRerunAllowed"])

    def test_wrong_authorization_or_commit_shape_is_refused(self):
        auth, context, runs, runtime, metadata = inputs()
        auth["authorizationOrdinal"] = 8
        with self.assertRaises(e.Refusal):
            e.build_manifest(ROOT, auth, context, runs, runtime, metadata)
        auth, context, runs, runtime, metadata = inputs()
        metadata["changedFiles"] = [e.AUTHORIZATION_PATH, "other"]
        with self.assertRaises(e.Refusal):
            e.build_manifest(ROOT, auth, context, runs, runtime, metadata)
        auth, context, runs, runtime, metadata = inputs()
        context["runAttempt"] = 2
        with self.assertRaises(e.Refusal):
            e.build_manifest(ROOT, auth, context, runs, runtime, metadata)

    def test_duplicate_parser_refuses_prior_title(self):
        rows = pages.flatten_pages([{"workflow_runs": [current_row(101), current_row(100)]}])
        with self.assertRaises(pages.Refusal):
            pages.duplicate_audit(rows, current_run_id=101, candidate_title=e.RUN_TITLE)

    def test_complete_synthetic_result_path(self):
        auth, context, runs, runtime, metadata = inputs()
        manifest = e.build_manifest(ROOT, auth, context, runs, runtime, metadata)
        results = fake_results(manifest)
        e.validate_results(manifest, results)
        aggregate = e.aggregate(ROOT, manifest, results)
        self.assertEqual(aggregate["aggregate"]["status"], "COMPLETED")
        self.assertEqual(aggregate["aggregate"]["caseCountObserved"], 40)
        audit = e.audit(ROOT, manifest, results, aggregate)
        self.assertEqual(audit["audit"]["status"], "PASSED")
        analysis = e.analyze(ROOT, manifest, aggregate, audit)
        self.assertEqual(analysis["analysis"]["status"], "CONTINUATION_ANALYZED")
        self.assertFalse(analysis["surrogateFitAuthorized"])
        self.assertFalse(analysis["internalHoldoutOpened"])

    def test_verified_execution_seal_is_removed_only_for_scientific_translation(self):
        auth, context, runs, runtime, metadata = inputs()
        manifest = e.build_manifest(ROOT, auth, context, runs, runtime, metadata)
        results = fake_results(manifest)
        e.validate_results(manifest, results)
        translated_input = e.package_results(results)
        self.assertEqual(len(translated_input), 40)
        self.assertTrue(all("contentSha256" not in row for row in translated_input))
        self.assertEqual([row["caseId"] for row in translated_input], [row["caseId"] for row in results])

    def test_wrappers_rebind_reviewed_v2_components(self):
        adapter = load(ADAPTER_PATH, "wave1_v3_adapter_test")
        executor = load(EXECUTOR_PATH, "wave1_v3_executor_test")
        self.assertEqual(adapter._base(ROOT).STAGE_ID, e.STAGE_ID)
        self.assertEqual(executor._base().STAGE_ID, e.STAGE_ID)

    def test_workflow_uses_compatible_pagination_and_closed_post_actions(self):
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("--slurp > run-pages.json", workflow)
        self.assertNotIn("--slurp --jq", workflow)
        self.assertIn("duplicate_pages.py --pages run-pages.json --output runs.json", workflow)
        self.assertIn("GITHUB_RUN_ATTEMPT", workflow)
        self.assertNotIn("rerun", workflow.lower().replace("githubrerunallowed", ""))
        contract = CONTRACT_PATH.read_text(encoding="utf-8")
        self.assertNotIn("workflow_dispatch:", contract)
        self.assertIn("authorization.ordinal9.json", contract)
        self.assertIn("github.event.pull_request.head.sha", contract)


if __name__ == "__main__":
    unittest.main()
