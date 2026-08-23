from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "experiments/aerosol-full-phase-function-sensitivity-v1"
FRESHNESS = STAGE / "execution-candidate/freshness.py"
SURFACE = STAGE / "execution-candidate/preauthorization_surface.py"
PROOF = STAGE / "build_seed_authorization_proof.py"
WORKFLOW = ROOT / ".github/workflows/afpf-v1-preauthorization-audit.yml"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


class AerosolFullPhaseFunctionPreauthorizationV1Tests(unittest.TestCase):
    def test_identity_namespace_is_afpf_and_review_only(self) -> None:
        freshness = load_module("afpf_freshness_test", FRESHNESS)
        ordinal = 38
        self.assertEqual(
            freshness.authorization_branch(ordinal),
            "authorization/aerosol-full-phase-function-sensitivity-v1-ordinal-38",
        )
        self.assertEqual(
            freshness.dispatch_branch(ordinal),
            "dispatch/aerosol-full-phase-function-sensitivity-v1-ordinal-38",
        )
        self.assertEqual(
            freshness.execution_key(ordinal),
            "aerosol-full-phase-function-sensitivity-v1:numerical:38",
        )
        marker = freshness.authorization_marker(ordinal, "a" * 40, "b" * 40, 123)
        self.assertTrue(freshness.matching_marker(marker, ordinal, "a" * 40, "b" * 40, 123))
        self.assertEqual(freshness.consumed_marker(ordinal), "ORDINAL38_AFPF_V1_DISPATCH_CONSUMED")

    def test_preauthorization_validator_requires_seed_recheck_and_no_identity(self) -> None:
        freshness = load_module("afpf_freshness_ctx_test", FRESHNESS)
        ctx = {
            "nextAvailableScientificOrdinal": 38,
            "latestPriorConsumedScientificOrdinal": 37,
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
            "activeAuthorizationPathOnMainExists": False,
            "matchingAuthorizationMarkers": 0,
            "candidateSeedAuthorizationRecheckPassed": True,
        }
        freshness.validate_preauthorization(ctx, 38)
        bad = dict(ctx)
        bad["candidateSeedAuthorizationRecheckPassed"] = False
        with self.assertRaises(freshness.FreshnessRefusal):
            freshness.validate_preauthorization(bad, 38)
        bad = dict(ctx)
        bad["authorizationBranchExists"] = True
        with self.assertRaises(freshness.FreshnessRefusal):
            freshness.validate_preauthorization(bad, 38)

    def test_surface_wrapper_binds_proven_aops_control_bytes_and_refuses_unreviewed_recovery(self) -> None:
        surface = load_module("afpf_preauth_surface_test", SURFACE)
        self.assertEqual(
            git_blob_sha1(ROOT / "experiments/aerosol-optical-property-sensitivity-v1/execution-candidate/control_surface.py"),
            surface.AOPS_CONTROL_BLOB,
        )
        self.assertEqual(
            git_blob_sha1(ROOT / "experiments/aerosol-optical-property-sensitivity-v1/execution-candidate/global_ordinal.py"),
            surface.AOPS_GLOBAL_ORDINAL_BLOB,
        )
        self.assertEqual(git_blob_sha1(FRESHNESS), surface.LOCAL_FRESHNESS_BLOB)
        identity = surface.identity_for(38)
        self.assertEqual(identity["authorizationBranch"], "authorization/aerosol-full-phase-function-sensitivity-v1-ordinal-38")
        payload = {"branches": [{"name": "history/aerosol-full-phase-function-sensitivity-v1-ordinal-38-auth-review-failed-1"}]}
        with self.assertRaises(surface.SurfaceRefusal):
            surface._failed_history_must_be_absent(payload, 38)

    def test_seed_authorization_proof_is_exact_main_and_unallocated(self) -> None:
        proof = load_module("afpf_seed_authorization_proof_test", PROOF)
        tracked = {
            "candidateSeedCount": 72,
            "trackedTreeExternalCollisionCount": 0,
            "exactHeadTrackedTreeByteScanPassed": True,
            "requiredSelfLedgerPathsPresent": True,
            "trackedFileCount": 999,
        }
        head = "a" * 40
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
        output = proof.build(STAGE, tracked, global_report, head)
        self.assertEqual(output["status"], "PASS_CANDIDATE_SEEDS_AUTHORIZATION_RECHECK_NOT_ALLOCATED")
        self.assertEqual(output["auditedMainHead"], head)
        self.assertEqual(output["candidateSeedCount"], 72)
        for key in (
            "scientificOrdinalAllocated",
            "authorizationCreated",
            "dispatchCreated",
            "scientificExecutionAuthorized",
            "solverExecutionAuthorized",
            "resultOpeningAuthorized",
        ):
            self.assertIs(output[key], False)

    def test_workflow_is_push_main_zero_runtime_and_no_identity_allocation(self) -> None:
        text = WORKFLOW.read_text()
        self.assertIn("name: AFPF v1 fresh preauthorization audit", text)
        self.assertIn("branches: [main]", text)
        self.assertIn("PREAUTHORIZATION_SURFACE_CLEAN_NOT_ALLOCATED", text)
        self.assertIn("next_if_separately_allocated", text)
        self.assertIn("scientificOrdinalAllocated':False", text)
        self.assertIn("authorizationCreated':False", text)
        self.assertIn("dispatchCreated':False", text)
        for forbidden in (
            "setup-micromamba",
            "rubin-libradtran",
            "command -v uvspec",
            "--allow-execution",
            "git push ",
            "workflow_dispatch:",
            "repository_dispatch:",
        ):
            self.assertNotIn(forbidden, text)
        self.assertFalse((STAGE / "authorization.json").exists())


if __name__ == "__main__":
    unittest.main()
