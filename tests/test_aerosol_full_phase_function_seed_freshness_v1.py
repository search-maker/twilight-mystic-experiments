from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "experiments/aerosol-full-phase-function-sensitivity-v1"
SEED_LEDGER = STAGE / "seed_ledger.py"
TRACKED_SCAN = STAGE / "tracked_tree_seed_scan.py"
GLOBAL_SCAN = STAGE / "repository_global_seed_scan.py"
PROOF_BUILDER = STAGE / "build_seed_freshness_proof.py"
SELF_POLICY = STAGE / "seed-self-ledger-policy.v1.json"
CANDIDATE_LEDGER = STAGE / "candidate-seed-ledger.v1.json"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AerosolFullPhaseFunctionSeedFreshnessV1Tests(unittest.TestCase):
    def test_candidate_ledger_is_exact_deterministic_72_group_derivation(self) -> None:
        seed_mod = load_module("afpf_seed_ledger_test", SEED_LEDGER)
        ledger = seed_mod.validate_ledger()
        rows = seed_mod.derive_rows()
        self.assertEqual(ledger["status"], "CANDIDATE_ONLY_NOT_APPLIED_NOT_AUTHORIZED")
        self.assertEqual(ledger["candidateSeedCount"], 72)
        self.assertEqual(len(rows), 72)
        self.assertEqual(len({row["groupId"] for row in rows}), 72)
        self.assertEqual(len({row["seed"] for row in rows}), 72)
        self.assertEqual(ledger["candidateSeeds"], [row["seed"] for row in rows])
        self.assertTrue(all(row["collisionCounter"] == 0 for row in rows))
        self.assertTrue(all(seed_mod.MIN_SEED <= row["seed"] < seed_mod.MAX_EXCLUSIVE for row in rows))
        self.assertGreaterEqual(seed_mod.MIN_SEED, 10_000_000)
        self.assertLess(seed_mod.MAX_EXCLUSIVE, 10_000_000_000)
        self.assertIs(ledger["candidateSeedFreshnessProven"], False)
        self.assertIs(ledger["authorizationPermitted"], False)
        self.assertIs(ledger["solverExecutionAuthorized"], False)
        self.assertIs(ledger["resultOpeningAuthorized"], False)

    def test_self_ledger_policy_allows_only_exact_candidate_and_future_proof_paths(self) -> None:
        policy = json.loads(SELF_POLICY.read_text())
        self.assertEqual(policy["schemaVersion"], 2)
        self.assertEqual(policy["requiredTrackedSelfLedgerPaths"], [
            "experiments/aerosol-full-phase-function-sensitivity-v1/candidate-seed-ledger.v1.json"
        ])
        self.assertEqual(policy["futureEvidenceSelfLedgerPaths"], [
            "evidence/aerosol-full-phase-function-sensitivity-v1/seed-freshness-proof.json"
        ])
        self.assertIs(policy["candidateSeedsMayAppearElsewhereInTrackedTree"], False)
        self.assertIs(policy["authorizationPermitted"], False)

    def test_scanner_wrappers_bind_frozen_family_scanners_and_unique_proof_name(self) -> None:
        tracked = load_module("afpf_tracked_wrapper_test", TRACKED_SCAN)
        global_scan = load_module("afpf_global_wrapper_test", GLOBAL_SCAN)
        self.assertEqual(tracked.git_blob_sha1(tracked.BASE), tracked.EXPECTED_BLOB)
        self.assertEqual(global_scan.git_blob_sha1(global_scan.BASE), global_scan.EXPECTED_BLOB)
        self.assertEqual(global_scan.mod.REVIEW_PROOF_ARTIFACT_NAME, "afpf-v1-seed-freshness-review-proof")

    def test_tracked_tree_scan_allows_self_ledger_but_refuses_external_candidate_literal(self) -> None:
        wrapper = load_module("afpf_tracked_scan_behavior", TRACKED_SCAN)
        base = wrapper.mod
        candidates = base.load_candidates(CANDIDATE_LEDGER)
        required, future = base.load_self_ledger_policy(SELF_POLICY)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger_rel = Path("experiments/aerosol-full-phase-function-sensitivity-v1/candidate-seed-ledger.v1.json")
            (root / ledger_rel).parent.mkdir(parents=True)
            (root / ledger_rel).write_bytes(CANDIDATE_LEDGER.read_bytes())
            file_list = root / "files.nul"
            file_list.write_bytes(str(ledger_rel).encode() + b"\0")
            passed = base.scan_with_policy(root, file_list, candidates, required, future)
            self.assertTrue(passed["exactHeadTrackedTreeByteScanPassed"])
            self.assertEqual(passed["trackedTreeExternalCollisionCount"], 0)
            self.assertTrue(passed["requiredSelfLedgerPathsPresent"])

            external = Path("notes.txt")
            first_seed = json.loads(CANDIDATE_LEDGER.read_text())["candidateSeeds"][0]
            (root / external).write_text(f"external {first_seed}\n")
            file_list.write_bytes(str(ledger_rel).encode() + b"\0" + str(external).encode() + b"\0")
            refused = base.scan_with_policy(root, file_list, candidates, required, future)
            self.assertFalse(refused["exactHeadTrackedTreeByteScanPassed"])
            self.assertEqual(refused["trackedTreeExternalCollisionCount"], 1)

    def _good_reports(self):
        tracked = {
            "candidateSeedCount": 72,
            "trackedFileCount": 1000,
            "trackedTreeExternalCollisionCount": 0,
            "exactHeadTrackedTreeByteScanPassed": True,
            "requiredSelfLedgerPathsPresent": True,
            "futureEvidenceSelfLedgerPathCountPresent": 0,
        }
        global_report = {
            "auditMode": "review-freeze",
            "candidateSeedCount": 72,
            "repositoryGlobalCollisionCount": 0,
            "repositoryGlobalCollisionSurfaceScanPassed": True,
            "repositoryGlobalDoubleEnumerationStable": True,
            "repositoryGlobalPostFenceCandidateSeedCollisionCount": 0,
            "auditedBranchName": "review/aerosol-full-phase-function-seed-freshness-v1",
            "auditedBranchHeadMatchesRepositoryHead": True,
            "repositoryHeadExpected": "a" * 40,
            "auditedBranchHeadShaObserved": "a" * 40,
            "priorReviewProofArtifactCount": 0,
            "reviewProofIdentityFresh": True,
            "repositoryGlobalStableContextSha256": "b" * 64,
            "repositoryGlobalSnapshotFenceSha256": "c" * 64,
            "repositoryGlobalPostFenceArrivalCounts": {},
        }
        return tracked, global_report

    def test_proof_builder_promotes_only_to_fresh_nonrenderable_review_design(self) -> None:
        builder = load_module("afpf_seed_proof_builder_test", PROOF_BUILDER)
        tracked, global_report = self._good_reports()
        proof, design = builder.build(
            STAGE,
            tracked,
            global_report,
            "review/aerosol-full-phase-function-seed-freshness-v1",
            "a" * 40,
            "review-freeze",
        )
        self.assertEqual(proof["status"], "PASS_CANDIDATE_SEEDS_REVIEW_FREEZE_NOT_AUTHORIZED")
        self.assertEqual(proof["candidateSeedCount"], 72)
        self.assertEqual(proof["seededDesignCaseCount"], 360)
        self.assertEqual(proof["seededDesignGroupCount"], 72)
        self.assertIs(proof["scientificOrdinalAllocated"], False)
        self.assertIs(proof["authorizationCreated"], False)
        self.assertIs(proof["solverExecutionAuthorized"], False)
        self.assertIs(proof["resultOpeningAuthorized"], False)
        self.assertEqual(design["status"], "CANDIDATE_SEEDED_DESIGN_FRESHNESS_PROVEN_REVIEW_ONLY")
        self.assertIs(design["candidateSeedFreshnessProven"], True)
        self.assertIs(design["scientificExecutionAuthorized"], False)
        self.assertTrue(all(row["renderable"] is False for row in design["cases"]))
        self.assertTrue(all(row["executionAuthorized"] is False for row in design["cases"]))
        by_group = {}
        for row in design["cases"]:
            by_group.setdefault(row["groupId"], []).append(row)
        self.assertEqual(len(by_group), 72)
        for members in by_group.values():
            self.assertEqual(len(members), 5)
            self.assertEqual(len({row["seed"] for row in members}), 1)

    def test_proof_builder_refuses_collision_or_consumed_review_identity(self) -> None:
        builder = load_module("afpf_seed_proof_builder_refusal_test", PROOF_BUILDER)
        tracked, global_report = self._good_reports()
        bad = dict(global_report)
        bad["repositoryGlobalCollisionCount"] = 1
        bad["repositoryGlobalCollisionSurfaceScanPassed"] = False
        with self.assertRaises(builder.Refusal):
            builder.build(STAGE, tracked, bad, bad["auditedBranchName"], "a" * 40, "review-freeze")
        consumed = dict(global_report)
        consumed["priorReviewProofArtifactCount"] = 1
        consumed["reviewProofIdentityFresh"] = False
        with self.assertRaises(builder.Refusal):
            builder.build(STAGE, tracked, consumed, consumed["auditedBranchName"], "a" * 40, "review-freeze")


if __name__ == "__main__":
    unittest.main()
