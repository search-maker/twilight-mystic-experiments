from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "experiments/aerosol-full-phase-function-sensitivity-v1"
EXECD = STAGE / "execution-candidate"
DESIGN_PATH = STAGE / "execution_design.py"
FRESHNESS_PATH = EXECD / "freshness.py"
SURFACE_PATH = EXECD / "preauthorization_surface.py"
GUARD_PATH = EXECD / "authorization_guard.py"
BUILDER_PATH = EXECD / "build_authorization.py"
WORKFLOW = ROOT / ".github/workflows/afpf-v1-authorization-review.yml"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def seed_proof(main: str) -> dict:
    return {
        "schemaVersion": 1,
        "stageId": "aerosol-full-phase-function-sensitivity-v1-seed-authorization-recheck",
        "status": "PASS_CANDIDATE_SEEDS_AUTHORIZATION_RECHECK_NOT_ALLOCATED",
        "auditedMainHead": main,
        "auditedBranchHeadMatchesRepositoryHead": True,
        "candidateSeedCount": 72,
        "candidateSeedCanonicalSha256": "d3a3b0f8ddd6f73160e021377c66a1dd6f16ea4f7c8687db7677caf84a033a2b",
        "candidateRowsCanonicalSha256": "72a53f2a86be3b0d380528d9ef39893864d1f2ac9e2306611ce0c4afc88ffee4",
        "allCollisionCountersZero": True,
        "exactHeadTrackedTreeByteScanPassed": True,
        "trackedTreeExternalCollisionCount": 0,
        "repositoryGlobalCollisionSurfaceScanPassed": True,
        "repositoryGlobalCollisionCount": 0,
        "repositoryGlobalDoubleEnumerationStable": True,
        "scientificOrdinalAllocated": False,
        "authorizationCreated": False,
        "dispatchCreated": False,
        "scientificExecutionAuthorized": False,
        "solverExecutionAuthorized": False,
        "resultOpeningAuthorized": False,
    }


def common_surface(ordinal: int, *, auth_exists: bool, head: str | None = None, marker_count: int = 0) -> dict:
    return {
        "nextAvailableScientificOrdinal": ordinal,
        "latestPriorConsumedScientificOrdinal": ordinal - 1,
        "candidatePriorScientificRunCount": 0,
        "candidateExecutionKeyPriorUseCount": 0,
        "positiveCandidateClaimsExcludingCurrent": 0,
        "allBranchesInspected": True,
        "allActionsRunsInspected": True,
        "allActionsArtifactsInspected": True,
        "allStatePullRequestsInspected": True,
        "allStateIssuesInspected": True,
        "allRepositoryIssueCommentsInspected": True,
        "allRepositoryPullReviewCommentsInspected": True,
        "issue60AndCommentsInspected": True,
        "candidateCodePathsOnMainInspected": True,
        "dispatchBranchExists": False,
        "currentConsumedMarkerCount": 0,
        "authorizationBranchExists": auth_exists,
        "authorizationBranchHeadSha": head,
        "activeAuthorizationPathOnMainExists": False,
        "matchingAuthorizationMarkers": marker_count,
        "candidateSeedAuthorizationRecheckPassed": True,
    }


class AerosolFullPhaseFunctionAuthorizationControlV1Tests(unittest.TestCase):
    def test_execution_design_reconstructs_exact_nonrenderable_360_case_universe(self) -> None:
        design_mod = load("afpf_design_test", DESIGN_PATH)
        main = "a" * 40
        design = design_mod.build_review_execution_design(seed_proof(main), main)
        self.assertEqual(design["status"], "CANDIDATE_SEEDED_DESIGN_FRESHNESS_PROVEN_REVIEW_ONLY")
        self.assertEqual(design["caseCount"], 360)
        self.assertEqual(design["groupCount"], 72)
        self.assertEqual(design["statesPerGroup"], 5)
        self.assertTrue(all(row["renderable"] is False for row in design["cases"]))
        self.assertTrue(all(row["executionAuthorized"] is False for row in design["cases"]))
        self.assertEqual(design["candidateSeedCanonicalSha256"], design_mod.EXPECTED_SEED_CANONICAL)
        self.assertEqual(design["candidateRowsCanonicalSha256"], design_mod.EXPECTED_ROWS_CANONICAL)

    def test_execution_design_refuses_collision_or_wrong_main(self) -> None:
        design_mod = load("afpf_design_refusal_test", DESIGN_PATH)
        main = "a" * 40
        bad = seed_proof(main)
        bad["repositoryGlobalCollisionCount"] = 1
        with self.assertRaises(design_mod.DesignRefusal):
            design_mod.build_review_execution_design(bad, main)
        with self.assertRaises(design_mod.DesignRefusal):
            design_mod.build_review_execution_design(seed_proof(main), "b" * 40)

    def test_builder_produces_pending_dispatch_document_bound_to_exact_parent(self) -> None:
        builder = load("afpf_build_auth_test", BUILDER_PATH)
        main = "a" * 40
        auth = builder.build(ROOT, main, 38, common_surface(38, auth_exists=False), seed_proof(main))
        self.assertEqual(auth["scientificOrdinal"], 38)
        self.assertEqual(auth["exactAuthorizationParentCommit"], main)
        self.assertEqual(auth["status"], "AUTHORIZED_PENDING_SEPARATE_DISPATCH")
        self.assertIs(auth["exactAuthorizationCommit"], None)
        self.assertIs(auth["scientificExecutionAuthorized"], True)
        self.assertIs(auth["solverExecutionAuthorized"], True)
        self.assertIs(auth["dispatchAuthorized"], False)
        self.assertIs(auth["resultOpeningAuthorized"], False)
        self.assertIs(auth["automaticDispatch"], False)
        self.assertIs(auth["consumed"], False)
        self.assertEqual(auth["augmentedDataTreeSha256"], "5d8bbf8e6b91ec3d405dee36f21a94afbb6e5ec6cd67da2dd5dd541738199d80")
        self.assertEqual(len(auth["byteBindings"]), 23)

    def test_authorization_document_rejects_dispatch_or_parent_drift(self) -> None:
        builder = load("afpf_build_auth_drift_test", BUILDER_PATH)
        guard = load("afpf_guard_drift_test", GUARD_PATH)
        main = "a" * 40
        proof = seed_proof(main)
        auth = builder.build(ROOT, main, 38, common_surface(38, auth_exists=False), proof)
        bad = copy.deepcopy(auth); bad["dispatchAuthorized"] = True
        with self.assertRaises(guard.AuthorizationRefusal):
            guard.validate_enabled_document(ROOT, bad, main, proof)
        bad = copy.deepcopy(auth); bad["exactAuthorizationParentCommit"] = "b" * 40
        with self.assertRaises(guard.AuthorizationRefusal):
            guard.validate_enabled_document(ROOT, bad, main, proof)

    def test_review_requires_exact_one_file_draft_direct_child_and_fresh_auth_surface(self) -> None:
        builder = load("afpf_build_auth_review_test", BUILDER_PATH)
        guard = load("afpf_guard_review_test", GUARD_PATH)
        main = "a" * 40; head = "b" * 40
        proof = seed_proof(main)
        auth = builder.build(ROOT, main, 38, common_surface(38, auth_exists=False), proof)
        ctx = {
            "liveMain": main, "headSha": head, "parentSha": main, "parentCount": 1,
            "changedPaths": ["experiments/aerosol-full-phase-function-sensitivity-v1/authorization.json"],
            "authorizationPath": "experiments/aerosol-full-phase-function-sensitivity-v1/authorization.json",
            "pr": {"number": 999, "state": "open", "draft": True, "merged": False,
                   "headBranch": "authorization/aerosol-full-phase-function-sensitivity-v1-ordinal-38",
                   "baseBranch": "main", "headRepo": "search-maker/twilight-mystic-experiments",
                   "baseRepo": "search-maker/twilight-mystic-experiments", "headSha": head},
            "runAttempt": 1, "eventName": "pull_request", "eventAction": "opened",
            "scientificRuntimeSetupPerformed": False, "scientificExecutionPerformed": False,
            "freshness": common_surface(38, auth_exists=True, head=head),
        }
        out = guard.review(auth, ctx, ROOT, proof)
        self.assertEqual(out["status"], "EXACT_ONE_FILE_AFPF_AUTHORIZATION_REVIEW_PASS_ZERO_RUNTIME")
        bad = copy.deepcopy(ctx); bad["changedPaths"].append("README.md")
        with self.assertRaises(guard.AuthorizationRefusal):
            guard.review(auth, bad, ROOT, proof)

    def test_workflow_is_opened_attempt1_zero_runtime_and_artifact_only(self) -> None:
        text = WORKFLOW.read_text()
        self.assertIn("types: [opened]", text)
        self.assertIn("test \"$GITHUB_RUN_ATTEMPT\" = 1", text)
        self.assertIn("afpf-v1-preauthorization-audit.yml/runs", text)
        self.assertIn("afpf-v1-authorization-review-ordinal-", text)
        self.assertIn("authorization-review-evidence", text)
        for forbidden in ("setup-micromamba", "rubin-libradtran", "command -v uvspec", "--allow-execution", "git push ", "workflow_dispatch:"):
            self.assertNotIn(forbidden, text)

    def test_surface_wrapper_still_binds_current_freshness_bytes(self) -> None:
        surface = load("afpf_surface_binding_test", SURFACE_PATH)
        data = FRESHNESS_PATH.read_bytes()
        import hashlib
        blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        self.assertEqual(blob, surface.LOCAL_FRESHNESS_BLOB)


if __name__ == "__main__":
    unittest.main()
