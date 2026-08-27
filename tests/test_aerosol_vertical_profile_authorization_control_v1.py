from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "experiments/aerosol-vertical-profile-sensitivity-v1"
DESIGN_PATH = STAGE / "execution_design.py"
GUARD_PATH = STAGE / "authorization_guard.py"
BUILDER_PATH = STAGE / "build_authorization.py"
WORKFLOW = ROOT / ".github/workflows/aerosol-vertical-profile-authorization-review.yml"
PREAUTH_WORKFLOW = ROOT / ".github/workflows/aerosol-vertical-profile-preauthorization-main-gate.yml"
SEED_CANONICAL = "a2e22b526dfad84d4f23c0ca8b143d028fddc7e55f78deb93a43e194ebd6c35e"
ROWS_CANONICAL = "f22de8a9e30ba106759effb1170a5ca1d1e747cb2ac68293fa232dc7ed6ca683"


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
        "stageId": "aerosol-vertical-profile-sensitivity-v1-seed-authorization-recheck",
        "status": "PASS_CANDIDATE_SEEDS_AUTHORIZATION_RECHECK_NOT_ALLOCATED",
        "auditedMainHead": main,
        "auditedBranchHeadMatchesRepositoryHead": True,
        "candidateSeedCount": 72,
        "candidateSeedCanonicalSha256": SEED_CANONICAL,
        "candidateRowsCanonicalSha256": ROWS_CANONICAL,
        "allCollisionCountersZero": True,
        "candidateSeedLiteralsTrackedInGit": False,
        "exactHeadTrackedTreeByteScanPassed": True,
        "trackedTreeExternalCollisionCount": 0,
        "repositoryGlobalCollisionSurfaceScanPassed": True,
        "repositoryGlobalCollisionCount": 0,
        "repositoryGlobalDoubleEnumerationStable": True,
        "priorReviewProofArtifactCount": 1,
        "scientificOrdinalAllocated": False,
        "authorizationCreated": False,
        "dispatchCreated": False,
        "candidateSeedsAppliedToCases": False,
        "scientificExecutionAuthorized": False,
        "solverExecutionAuthorized": False,
        "resultOpeningAuthorized": False,
        "productionAuthorized": False,
    }


def preauth_report(main: str, ordinal: int) -> dict:
    return {
        "schemaVersion": 1,
        "stageId": "aerosol-vertical-profile-sensitivity-v1-preauthorization",
        "status": "PREAUTHORIZATION_SURFACE_CLEAN_NOT_ALLOCATED",
        "exactMainSha": main,
        "runId": 123456,
        "runAttempt": 1,
        "latestPriorConsumedScientificOrdinal": ordinal - 1,
        "nextAvailableScientificOrdinal": ordinal,
        "candidateSeedCount": 72,
        "candidateSeedCanonicalSha256": SEED_CANONICAL,
        "candidateRowsCanonicalSha256": ROWS_CANONICAL,
        "trackedTreeExternalCollisionCount": 0,
        "repositoryGlobalCollisionCount": 0,
        "repositoryGlobalDoubleEnumerationStable": True,
        "scientificOrdinalAllocated": False,
        "authorizationCreated": False,
        "dispatchCreated": False,
        "candidateSeedsAppliedToCases": False,
        "scientificRuntimeSetupPerformed": False,
        "scientificExecutionPerformed": False,
        "solverExecutionPerformed": False,
        "resultOpeningPerformed": False,
        "reportSha256": "c" * 64,
    }


def common_surface(ordinal: int, *, auth_exists: bool, head: str | None = None) -> dict:
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
        "matchingAuthorizationMarkers": 0,
        "candidateSeedAuthorizationRecheckPassed": True,
    }


class AerosolVerticalProfileAuthorizationControlV1Tests(unittest.TestCase):
    def test_seeded_design_is_exact_360_case_72_group_nonrenderable_universe(self) -> None:
        design_mod = load("avps_design_test", DESIGN_PATH)
        main = "a" * 40
        design = design_mod.build_review_execution_design(seed_proof(main), main)
        self.assertEqual(design["status"], "CANDIDATE_SEEDED_DESIGN_FRESHNESS_PROVEN_REVIEW_ONLY")
        self.assertEqual(design["caseCount"], 360)
        self.assertEqual(design["groupCount"], 72)
        self.assertEqual(design["statesPerGroup"], 5)
        self.assertEqual(design["seedCount"], 72)
        self.assertTrue(all(row["renderable"] is False for row in design["cases"]))
        self.assertTrue(all(row["executionAuthorized"] is False for row in design["cases"]))
        self.assertTrue(all(row["resultOpeningAuthorized"] is False for row in design["cases"]))
        self.assertEqual(len({row["seed"] for row in design["cases"]}), 72)
        for group in design["groups"]:
            seeds = {row["seed"] for row in design["cases"] if row["groupId"] == group["groupId"]}
            self.assertEqual(seeds, {group["candidateSeed"]})

    def test_seeded_design_refuses_wrong_main_or_collision(self) -> None:
        design_mod = load("avps_design_refusal_test", DESIGN_PATH)
        main = "a" * 40
        with self.assertRaises(design_mod.DesignRefusal):
            design_mod.build_review_execution_design(seed_proof(main), "b" * 40)
        bad = seed_proof(main); bad["repositoryGlobalCollisionCount"] = 1
        with self.assertRaises(design_mod.DesignRefusal):
            design_mod.build_review_execution_design(bad, main)

    def test_builder_produces_exact_pending_dispatch_document(self) -> None:
        builder = load("avps_builder_test", BUILDER_PATH)
        main = "a" * 40
        auth = builder.build(
            ROOT, main, 40, preauth_report(main, 40), seed_proof(main),
            preauthorization_artifact_id=999,
            preauthorization_artifact_digest="sha256:" + "d" * 64,
        )
        self.assertEqual(auth["scientificOrdinal"], 40)
        self.assertEqual(auth["authorizationBranch"], "authorization/aerosol-vertical-profile-sensitivity-v1-ordinal-40")
        self.assertEqual(auth["dispatchBranch"], "dispatch/aerosol-vertical-profile-sensitivity-v1-ordinal-40")
        self.assertEqual(auth["caseCount"], 360)
        self.assertEqual(auth["commonRandomNumberGroupCount"], 72)
        self.assertIs(auth["scientificExecutionAuthorized"], True)
        self.assertIs(auth["solverExecutionAuthorized"], True)
        self.assertIs(auth["dispatchAuthorized"], False)
        self.assertIs(auth["resultOpeningAuthorized"], False)
        self.assertIs(auth["automaticDispatch"], False)
        self.assertIs(auth["consumed"], False)
        self.assertIs(auth["productionAuthorized"], False)
        self.assertIs(auth["taylorOrJerusalemFitAuthorized"], False)

    def test_authorization_document_is_exact_and_fail_closed(self) -> None:
        builder = load("avps_builder_drift_test", BUILDER_PATH)
        guard = load("avps_guard_drift_test", GUARD_PATH)
        main = "a" * 40
        report = preauth_report(main, 40); proof = seed_proof(main)
        kwargs = dict(preauthorization_artifact_id=999, preauthorization_artifact_digest="sha256:" + "d" * 64)
        auth = builder.build(ROOT, main, 40, report, proof, **kwargs)
        for key, value in (
            ("dispatchAuthorized", True),
            ("resultOpeningAuthorized", True),
            ("candidateSeedCanonicalSha256", "0" * 64),
            ("exactAuthorizationParentCommit", "b" * 40),
            ("taylorOrJerusalemFitAuthorized", True),
        ):
            bad = copy.deepcopy(auth); bad[key] = value
            with self.assertRaises(guard.AuthorizationRefusal):
                guard.validate_enabled_document(ROOT, bad, main, report, proof, **kwargs)

    def test_review_requires_one_file_draft_direct_child_attempt1_and_fresh_surface(self) -> None:
        builder = load("avps_builder_review_test", BUILDER_PATH)
        guard = load("avps_guard_review_test", GUARD_PATH)
        main = "a" * 40; head = "b" * 40
        report = preauth_report(main, 40); proof = seed_proof(main)
        kwargs = dict(preauthorization_artifact_id=999, preauthorization_artifact_digest="sha256:" + "d" * 64)
        auth = builder.build(ROOT, main, 40, report, proof, **kwargs)
        ctx = {
            "liveMain": main, "headSha": head, "parentSha": main, "parentCount": 1,
            "changedPaths": ["experiments/aerosol-vertical-profile-sensitivity-v1/authorization.json"],
            "authorizationPath": "experiments/aerosol-vertical-profile-sensitivity-v1/authorization.json",
            "pr": {"number": 999, "state": "open", "draft": True, "merged": False,
                   "headBranch": "authorization/aerosol-vertical-profile-sensitivity-v1-ordinal-40",
                   "baseBranch": "main", "headRepo": "search-maker/twilight-mystic-experiments",
                   "baseRepo": "search-maker/twilight-mystic-experiments", "headSha": head},
            "runAttempt": 1, "eventName": "pull_request", "eventAction": "opened",
            "scientificRuntimeSetupPerformed": False, "scientificExecutionPerformed": False,
            "freshness": common_surface(40, auth_exists=True, head=head),
        }
        out = guard.review(auth, ctx, ROOT, report, proof, **kwargs)
        self.assertEqual(out["status"], "EXACT_ONE_FILE_AVPS_V1_AUTHORIZATION_REVIEW_PASS_ZERO_RUNTIME")
        bad = copy.deepcopy(ctx); bad["changedPaths"].append("README.md")
        with self.assertRaises(guard.AuthorizationRefusal):
            guard.review(auth, bad, ROOT, report, proof, **kwargs)

    def test_authorization_workflow_is_opened_attempt1_zero_runtime_and_parent_preauth_bound(self) -> None:
        text = WORKFLOW.read_text()
        self.assertIn("types: [opened]", text)
        self.assertIn("test \"$GITHUB_RUN_ATTEMPT\" = 1", text)
        self.assertIn("aerosol-vertical-profile-preauthorization-main-gate.yml", text)
        self.assertIn("vertical-profile-v1-preauthorization-proof", text)
        self.assertIn("authorization/aerosol-vertical-profile-sensitivity-v1-ordinal-", text)
        self.assertIn("authorization-review-evidence", text)
        self.assertIn("candidateSeedAuthorizationRecheckPassed", text)
        for forbidden in ("setup-micromamba", "rubin-libradtran", "--allow-execution", "git push ", "workflow_dispatch:", "repository_dispatch:"):
            self.assertNotIn(forbidden, text)

    def test_preauthorization_workflow_retriggers_when_authorization_control_merges(self) -> None:
        text = PREAUTH_WORKFLOW.read_text()
        for path in (
            "experiments/aerosol-vertical-profile-sensitivity-v1/execution_design.py",
            "experiments/aerosol-vertical-profile-sensitivity-v1/authorization_guard.py",
            "experiments/aerosol-vertical-profile-sensitivity-v1/build_authorization.py",
            ".github/workflows/aerosol-vertical-profile-authorization-review.yml",
        ):
            self.assertIn(path, text)


if __name__ == "__main__":
    unittest.main()
