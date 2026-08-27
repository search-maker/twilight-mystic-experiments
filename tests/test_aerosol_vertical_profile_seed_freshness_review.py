from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "experiments" / "aerosol-vertical-profile-sensitivity-v1"
SEED_LEDGER = STAGE / "seed_ledger.py"
PROOF = STAGE / "build_seed_freshness_proof.py"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class VerticalProfileSeedFreshnessReviewTests(unittest.TestCase):
    def test_candidate_seed_derivation_is_exact_and_unapplied(self):
        seed_mod = load("vertical_profile_seed_ledger_test", SEED_LEDGER)
        ledger = seed_mod.validate_ledger()
        self.assertEqual(ledger["candidateSeedCount"], 72)
        self.assertEqual(len(set(ledger["candidateSeeds"])), 72)
        self.assertTrue(ledger["allCollisionCountersZero"])
        self.assertEqual(
            ledger["candidateSeedCanonicalSha256"],
            "a2e22b526dfad84d4f23c0ca8b143d028fddc7e55f78deb93a43e194ebd6c35e",
        )
        self.assertEqual(
            ledger["candidateRowsCanonicalSha256"],
            "f22de8a9e30ba106759effb1170a5ca1d1e747cb2ac68293fa232dc7ed6ca683",
        )
        self.assertFalse(ledger["trackedCandidateSeedLedger"])
        self.assertFalse(ledger["candidateSeedFreshnessProven"])
        self.assertFalse(ledger["scientificOrdinalAllocated"])
        self.assertFalse(ledger["authorizationPermitted"])
        self.assertFalse(ledger["solverExecutionAuthorized"])
        self.assertFalse(ledger["resultOpeningAuthorized"])

    def test_seed_rows_bind_exact_72_frozen_group_ids(self):
        seed_mod = load("vertical_profile_seed_rows_test", SEED_LEDGER)
        rows = seed_mod.derive_rows()
        design = seed_mod.execution_candidate_module().build_review_execution_skeleton()
        self.assertEqual([row["groupId"] for row in rows], [row["groupId"] for row in design["groups"]])
        self.assertTrue(all(row["collisionCounter"] == 0 for row in rows))
        self.assertTrue(all(seed_mod.MIN_SEED <= row["seed"] < seed_mod.MAX_EXCLUSIVE for row in rows))

    def test_freshness_proof_refuses_collisions_or_identity_reuse(self):
        proof_mod = load("vertical_profile_seed_proof_test", PROOF)
        stage = STAGE
        tracked = {
            "candidateSeedCount": 72,
            "trackedTreeExternalCollisionCount": 0,
            "exactHeadTrackedTreeByteScanPassed": True,
            "requiredSelfLedgerPathsPresent": True,
            "selfLedgerHitCount": 0,
            "trackedFileCount": 100,
        }
        global_report = {
            "auditMode": "review-freeze",
            "candidateSeedCount": 72,
            "repositoryGlobalCollisionCount": 0,
            "repositoryGlobalCollisionSurfaceScanPassed": True,
            "repositoryGlobalDoubleEnumerationStable": True,
            "auditedBranchHeadMatchesRepositoryHead": True,
            "repositoryHeadExpected": "a" * 40,
            "auditedBranchHeadShaObserved": "a" * 40,
            "priorReviewProofArtifactCount": 0,
            "reviewProofIdentityFresh": True,
            "repositoryGlobalPostFenceCandidateSeedCollisionCount": 0,
        }
        out = proof_mod.build(stage, tracked, global_report, "a" * 40)
        self.assertEqual(out["status"], "PASS_CANDIDATE_SEEDS_FRESH_REVIEW_ONLY_NOT_ALLOCATED")
        self.assertFalse(out["scientificOrdinalAllocated"])
        self.assertFalse(out["authorizationCreated"])
        self.assertFalse(out["candidateSeedsAppliedToCases"])
        self.assertTrue(out["authorizationTimeRecheckRequired"])

        bad = dict(global_report)
        bad["repositoryGlobalCollisionCount"] = 1
        with self.assertRaises(proof_mod.Refusal):
            proof_mod.build(stage, tracked, bad, "a" * 40)
        bad = dict(global_report)
        bad["priorReviewProofArtifactCount"] = 1
        with self.assertRaises(proof_mod.Refusal):
            proof_mod.build(stage, tracked, bad, "a" * 40)


if __name__ == "__main__":
    unittest.main()
