from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "experiments/aerosol-optical-property-sensitivity-v1"
EXEC = STAGE / "execution-candidate"
FREEZE = ROOT / "evidence/aerosol-optical-property-sensitivity-v1/review-freeze.json"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


class AopsAuthorizationReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.freshness = load("aops_freshness_review_test", EXEC / "freshness.py")
        self.auth = load("aops_auth_guard_review_test", EXEC / "authorization_guard.py")
        self.proof_builder = load("aops_seed_auth_proof_builder_review_test", STAGE / "build_seed_authorization_proof.py")
        self.freeze = json.loads(FREEZE.read_text())

    @staticmethod
    def freshness_context(ordinal: int, recheck: bool) -> dict:
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
            "authorizationBranchExists": False,
            "authorizationBranchReusableAfterFailedReview": False,
            "activeAuthorizationPathOnMainExists": False,
            "matchingAuthorizationMarkers": 0,
            "candidateSeedAuthorizationRecheckPassed": recheck,
        }

    def test_global_ordinal_names_are_stage_specific_and_monotonic_inputs(self) -> None:
        ordinal = 987654
        self.assertEqual(
            self.freshness.authorization_branch(ordinal),
            f"authorization/aerosol-optical-property-sensitivity-v1-ordinal-{ordinal}",
        )
        self.assertEqual(
            self.freshness.dispatch_branch(ordinal),
            f"dispatch/aerosol-optical-property-sensitivity-v1-ordinal-{ordinal}",
        )
        self.assertEqual(
            self.freshness.execution_key(ordinal),
            f"aerosol-optical-property-sensitivity-v1:numerical:{ordinal}",
        )
        marker = self.freshness.authorization_marker(ordinal, "a" * 40, "b" * 40, 123)
        self.assertTrue(self.freshness.matching_marker(marker, ordinal, "a" * 40, "b" * 40, 123))

    def test_preauthorization_refuses_without_authorization_time_seed_recheck(self) -> None:
        with self.assertRaisesRegex(self.freshness.FreshnessRefusal, "seed recheck"):
            self.freshness.validate_preauthorization(self.freshness_context(1000, False), 1000)
        self.freshness.validate_preauthorization(self.freshness_context(1000, True), 1000)

    def test_authorization_template_is_disabled(self) -> None:
        t = json.loads((EXEC / "authorization.template.json").read_text())
        self.assertEqual(t["status"], "TEMPLATE_DISABLED_NOT_AUTHORIZATION")
        for key in (
            "enabled",
            "scientificExecutionAuthorized",
            "solverExecutionAuthorized",
            "dispatchAuthorized",
            "resultOpeningAuthorized",
            "automaticDispatch",
            "consumed",
        ):
            self.assertFalse(t[key], key)
        self.assertIsNone(t["scientificOrdinal"])
        self.assertIsNone(t["executionKey"])
        self.assertEqual(t["candidateSeedCanonicalSha256"], self.freeze["candidateSeedCanonicalSha256"])

    def test_seed_authorization_proof_builder_requires_both_freshness_surfaces(self) -> None:
        head = "a" * 40
        tracked = {
            "candidateSeedCount": 72,
            "trackedTreeExternalCollisionCount": 0,
            "exactHeadTrackedTreeByteScanPassed": True,
            "requiredSelfLedgerPathsPresent": True,
            "trackedFileCount": 999,
        }
        global_report = {
            "auditMode": "authorization-recheck",
            "candidateSeedCount": 72,
            "repositoryGlobalCollisionCount": 0,
            "repositoryGlobalCollisionSurfaceScanPassed": True,
            "repositoryGlobalDoubleEnumerationStable": True,
            "auditedBranchHeadMatchesRepositoryHead": True,
            "repositoryHeadExpected": head,
            "auditedBranchHeadShaObserved": head,
            "repositoryGlobalPostFenceCandidateSeedCollisionCount": 0,
            "repositoryGlobalStableContextSha256": "b" * 64,
            "repositoryGlobalSnapshotFenceSha256": "c" * 64,
            "repositoryGlobalPostFenceArrivalCounts": {},
        }
        proof = self.proof_builder.build(STAGE, tracked, global_report, head)
        self.assertEqual(proof["status"], "PASS_CANDIDATE_SEEDS_AUTHORIZATION_RECHECK_NOT_ALLOCATED")
        self.assertEqual(proof["candidateSeedCount"], 72)
        self.assertTrue(proof["allCollisionCountersZero"])
        self.assertFalse(proof["scientificOrdinalAllocated"])
        self.assertFalse(proof["authorizationCreated"])
        self.assertFalse(proof["solverExecutionAuthorized"])
        self.auth.validate_seed_authorization_proof(proof)
        broken = dict(global_report)
        broken["repositoryGlobalCollisionCount"] = 1
        with self.assertRaisesRegex(self.proof_builder.Refusal, "collision"):
            self.proof_builder.build(STAGE, tracked, broken, head)

    def test_freeze_binds_authorization_surface(self) -> None:
        f = self.freeze
        expected = {
            f["authorizationTemplatePath"]: f["authorizationTemplateGitBlobSha1"],
            f["authorizationGuardPath"]: f["authorizationGuardGitBlobSha1"],
            f["freshnessGuardPath"]: f["freshnessGuardGitBlobSha1"],
            f["seedAuthorizationProofBuilderPath"]: f["seedAuthorizationProofBuilderGitBlobSha1"],
        }
        for rel, blob in expected.items():
            self.assertEqual(git_blob_sha1(ROOT / rel), blob, rel)
        self.assertTrue(f["authorizationGuardImplementedReviewOnly"])
        self.assertTrue(f["authorizationTimeSeedProofBuilderImplementedReviewOnly"])
        self.assertFalse(f["candidateSeedAuthorizationRecheckPassed"])
        self.assertFalse(f["scientificOrdinalAllocated"])
        self.assertFalse(f["authorizationCreated"])
        self.assertFalse(f["dispatchCreated"])


if __name__ == "__main__":
    unittest.main()
