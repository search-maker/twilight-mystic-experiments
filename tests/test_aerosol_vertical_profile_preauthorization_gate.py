from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "experiments" / "aerosol-vertical-profile-sensitivity-v1"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class VerticalProfilePreauthorizationGateTests(unittest.TestCase):
    def test_stage_specific_identity_names(self):
        fresh = load("avps_freshness_test", STAGE / "freshness.py")
        self.assertEqual(fresh.STAGE_ID, "aerosol-vertical-profile-sensitivity-v1")
        self.assertEqual(fresh.STAGE_TOKEN, "AVPS_V1")
        self.assertEqual(
            fresh.authorization_branch(40),
            "authorization/aerosol-vertical-profile-sensitivity-v1-ordinal-40",
        )
        self.assertEqual(
            fresh.dispatch_branch(40),
            "dispatch/aerosol-vertical-profile-sensitivity-v1-ordinal-40",
        )
        self.assertEqual(
            fresh.execution_key(40),
            "aerosol-vertical-profile-sensitivity-v1:numerical:40",
        )
        marker = fresh.authorization_marker(40, "a" * 40, "b" * 40, 555)
        self.assertEqual(
            marker,
            "ORDINAL40_AVPS_V1_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED "
            f"commit={'a'*40} parent={'b'*40} pr=555",
        )
        self.assertEqual(fresh.consumed_marker(40), "ORDINAL40_AVPS_V1_DISPATCH_CONSUMED")

    def test_preauthorization_surface_binds_audited_global_control(self):
        surface = load("avps_preauthorization_surface_test", STAGE / "preauthorization_surface.py")
        identity = surface.identity_for(40)
        self.assertEqual(identity["authorizationBranch"], "authorization/aerosol-vertical-profile-sensitivity-v1-ordinal-40")
        self.assertEqual(identity["dispatchBranch"], "dispatch/aerosol-vertical-profile-sensitivity-v1-ordinal-40")
        self.assertEqual(identity["executionKey"], "aerosol-vertical-profile-sensitivity-v1:numerical:40")
        self.assertEqual(surface.AUTHORIZATION_PATH, "experiments/aerosol-vertical-profile-sensitivity-v1/authorization.json")
        self.assertEqual(surface.CASE_ARTIFACT_PREFIX, "avps-v1-case-")

    def test_seed_authorization_proof_refuses_missing_review_artifact_or_collision(self):
        proof = load("avps_seed_authorization_proof_test", STAGE / "build_seed_authorization_proof.py")
        tracked = {
            "candidateSeedCount": 72,
            "trackedTreeExternalCollisionCount": 0,
            "exactHeadTrackedTreeByteScanPassed": True,
            "requiredSelfLedgerPathsPresent": True,
            "selfLedgerHitCount": 0,
            "trackedFileCount": 100,
        }
        global_report = {
            "auditMode": "authorization-recheck",
            "candidateSeedCount": 72,
            "repositoryGlobalCollisionCount": 0,
            "repositoryGlobalCollisionSurfaceScanPassed": True,
            "repositoryGlobalDoubleEnumerationStable": True,
            "auditedBranchHeadMatchesRepositoryHead": True,
            "repositoryHeadExpected": "a" * 40,
            "auditedBranchHeadShaObserved": "a" * 40,
            "repositoryGlobalPostFenceCandidateSeedCollisionCount": 0,
            "priorReviewProofArtifactCount": 1,
            "reviewProofArtifactName": "vertical-profile-v1-seed-freshness-review-proof",
        }
        out = proof.build(STAGE, tracked, global_report, "a" * 40)
        self.assertEqual(out["status"], "PASS_CANDIDATE_SEEDS_AUTHORIZATION_RECHECK_NOT_ALLOCATED")
        self.assertFalse(out["scientificOrdinalAllocated"])
        self.assertFalse(out["candidateSeedsAppliedToCases"])

        bad = dict(global_report)
        bad["priorReviewProofArtifactCount"] = 0
        with self.assertRaises(proof.Refusal):
            proof.build(STAGE, tracked, bad, "a" * 40)
        bad = dict(global_report)
        bad["repositoryGlobalCollisionCount"] = 1
        with self.assertRaises(proof.Refusal):
            proof.build(STAGE, tracked, bad, "a" * 40)


if __name__ == "__main__":
    unittest.main()
