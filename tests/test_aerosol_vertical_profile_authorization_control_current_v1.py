from __future__ import annotations

import copy
import importlib.util
import sys
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
PACKAGE_CANONICAL = "ecf7052454e47a9e047cb944f22b031473c0986e9d8b9cec1aa010d425b39cc1"
PACKAGE_BLOB = "4b588e5eb289e9074935bf4ca22a4e2c6185bdb9"
AFGL_DIGEST = "sha256:2061136f069e9a16fa5c5b3d0991121bb04d7a268d1b7c7f93c60d734d537b48"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
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


class AerosolVerticalProfileAuthorizationControlCurrentV1Tests(unittest.TestCase):
    def test_seeded_design_is_bound_to_merged_disabled_package_and_exact_afgl_evidence(self) -> None:
        design_mod = load("avps_design_current_test", DESIGN_PATH)
        main = "a" * 40
        design = design_mod.build_review_execution_design(seed_proof(main), main)
        self.assertEqual((design["caseCount"], design["groupCount"]), (360, 72))
        self.assertEqual(design["seedCount"], 72)
        self.assertEqual(design["sourceDisabledExecutionPackageBlobSha1"], PACKAGE_BLOB)
        self.assertEqual(design["sourceDisabledExecutionPackageCanonicalSha256"], PACKAGE_CANONICAL)
        self.assertEqual(design["exactAfglProfileBundleArtifactDigest"], AFGL_DIGEST)
        self.assertEqual(len(design["exactAfglProfileTauSha256"]), 5)
        self.assertEqual(len({row["candidateSeed"] for row in design["groups"]}), 72)
        self.assertTrue(all(row["seed"] is not None for row in design["cases"]))
        self.assertTrue(all(row["renderable"] is False for row in design["cases"]))
        self.assertTrue(all(row["executionAuthorized"] is False for row in design["cases"]))
        self.assertTrue(all(row["resultOpeningAuthorized"] is False for row in design["cases"]))

    def test_design_refuses_package_byte_drift_and_seed_collision(self) -> None:
        design_mod = load("avps_design_current_refusal_test", DESIGN_PATH)
        main = "a" * 40
        original = design_mod.EXPECTED_EXECUTION_PACKAGE_BLOB
        design_mod.EXPECTED_EXECUTION_PACKAGE_BLOB = "0" * 40
        try:
            with self.assertRaises(design_mod.DesignRefusal):
                design_mod.build_review_execution_design(seed_proof(main), main)
        finally:
            design_mod.EXPECTED_EXECUTION_PACKAGE_BLOB = original
        bad = seed_proof(main)
        bad["repositoryGlobalCollisionCount"] = 1
        with self.assertRaises(design_mod.DesignRefusal):
            design_mod.build_review_execution_design(bad, main)

    def test_builder_freezes_current_package_runtime_and_profile_identity(self) -> None:
        builder = load("avps_builder_current_test", BUILDER_PATH)
        guard = load("avps_guard_current_test", GUARD_PATH)
        main = "a" * 40
        report = preauth_report(main, 40)
        proof = seed_proof(main)
        kwargs = dict(preauthorization_artifact_id=999, preauthorization_artifact_digest="sha256:" + "d" * 64)
        auth = builder.build(ROOT, main, 40, report, proof, **kwargs)
        self.assertEqual(auth["authorizationBranch"], "authorization/aerosol-vertical-profile-sensitivity-v1-ordinal-40")
        self.assertEqual(auth["dispatchBranch"], "dispatch/aerosol-vertical-profile-sensitivity-v1-ordinal-40")
        self.assertEqual(auth["disabledExecutionPackageBlobSha1"], PACKAGE_BLOB)
        self.assertEqual(auth["disabledExecutionPackageCanonicalSha256"], PACKAGE_CANONICAL)
        self.assertEqual(auth["exactAfglProfileBundleArtifactDigest"], AFGL_DIGEST)
        self.assertEqual(len(auth["exactAfglProfileTauSha256"]), 5)
        self.assertEqual((auth["caseCount"], auth["commonRandomNumberGroupCount"]), (360, 72))
        self.assertTrue(auth["scientificExecutionAuthorized"] and auth["solverExecutionAuthorized"])
        for key in ("dispatchAuthorized", "resultOpeningAuthorized", "automaticDispatch", "consumed", "productionAuthorized", "taylorOrJerusalemFitAuthorized"):
            self.assertIs(auth[key], False)
        bad = copy.deepcopy(auth)
        bad["disabledExecutionPackageCanonicalSha256"] = "0" * 64
        with self.assertRaises(guard.AuthorizationRefusal):
            guard.validate_enabled_document(ROOT, bad, main, report, proof, **kwargs)

    def test_review_requires_exact_one_file_draft_direct_child_attempt1(self) -> None:
        builder = load("avps_builder_current_review_test", BUILDER_PATH)
        guard = load("avps_guard_current_review_test", GUARD_PATH)
        main = "a" * 40
        head = "b" * 40
        report = preauth_report(main, 40)
        proof = seed_proof(main)
        kwargs = dict(preauthorization_artifact_id=999, preauthorization_artifact_digest="sha256:" + "d" * 64)
        auth = builder.build(ROOT, main, 40, report, proof, **kwargs)
        ctx = {
            "liveMain": main, "headSha": head, "parentSha": main, "parentCount": 1,
            "changedPaths": ["experiments/aerosol-vertical-profile-sensitivity-v1/authorization.json"],
            "authorizationPath": "experiments/aerosol-vertical-profile-sensitivity-v1/authorization.json",
            "pr": {"number": 999, "state": "open", "draft": True, "merged": False,
                   "headBranch": "authorization/aerosol-vertical-profile-sensitivity-v1-ordinal-40", "baseBranch": "main",
                   "headRepo": "search-maker/twilight-mystic-experiments", "baseRepo": "search-maker/twilight-mystic-experiments", "headSha": head},
            "runAttempt": 1, "eventName": "pull_request", "eventAction": "opened",
            "scientificRuntimeSetupPerformed": False, "scientificExecutionPerformed": False,
            "freshness": common_surface(40, auth_exists=True, head=head),
        }
        out = guard.review(auth, ctx, ROOT, report, proof, **kwargs)
        self.assertEqual(out["status"], "EXACT_ONE_FILE_AVPS_V1_AUTHORIZATION_REVIEW_PASS_ZERO_RUNTIME")
        self.assertEqual(out["disabledExecutionPackageCanonicalSha256"], PACKAGE_CANONICAL)
        bad = copy.deepcopy(ctx)
        bad["changedPaths"].append("README.md")
        with self.assertRaises(guard.AuthorizationRefusal):
            guard.review(auth, bad, ROOT, report, proof, **kwargs)

    def test_workflows_keep_zero_runtime_and_invalidate_preauthorization_on_control_drift(self) -> None:
        text = WORKFLOW.read_text()
        for required in (
            "types: [opened]", "test \"$GITHUB_RUN_ATTEMPT\" = 1",
            "vertical-profile-v1-preauthorization-proof", "authorization-review-evidence",
            "candidateSeedAuthorizationRecheckPassed",
        ):
            self.assertIn(required, text)
        for forbidden in ("setup-micromamba", "rubin-libradtran", "--allow-execution", "git push ", "workflow_dispatch:", "repository_dispatch:"):
            self.assertNotIn(forbidden, text)
        pre = PREAUTH_WORKFLOW.read_text()
        for path in (
            "experiments/aerosol-vertical-profile-sensitivity-v1/execution_design.py",
            "experiments/aerosol-vertical-profile-sensitivity-v1/authorization_guard.py",
            "experiments/aerosol-vertical-profile-sensitivity-v1/build_authorization.py",
            "tests/test_aerosol_vertical_profile_authorization_control_current_v1.py",
            ".github/workflows/aerosol-vertical-profile-authorization-review.yml",
        ):
            self.assertIn(path, pre)


if __name__ == "__main__":
    unittest.main()
