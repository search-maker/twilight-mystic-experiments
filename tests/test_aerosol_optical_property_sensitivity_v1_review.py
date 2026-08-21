from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
STAGE = "aerosol-optical-property-sensitivity-v1"
STAGE_DIR = ROOT / "experiments" / STAGE
PROTOCOL = STAGE_DIR / "protocol.review.json"
REVIEW = STAGE_DIR / "SCIENTIFIC_REVIEW.md"
ADAPTER = STAGE_DIR / "adapter.py"
REVIEW_CORE = STAGE_DIR / "review_core.py"
CANDIDATE_LEDGER = STAGE_DIR / "candidate-seed-ledger.v1.json"
SEED_VALIDATOR = STAGE_DIR / "seed_ledger.py"
TRACKED_SCANNER = STAGE_DIR / "tracked_tree_seed_scan.py"
GLOBAL_SCANNER = STAGE_DIR / "repository_global_seed_scan.py"
SEED_POLICY = STAGE_DIR / "seed-self-ledger-policy.v1.json"
FREEZE = ROOT / "evidence" / STAGE / "review-freeze.json"
SEED_PROOF = ROOT / "evidence" / STAGE / "seed-freshness-proof.json"


def git_blob_sha1(path: Path) -> str:
    import hashlib
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class AerosolOpticalPropertySensitivityV1ReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.adapter = load_module("aops_v1_adapter", ADAPTER)
        cls.review_core = load_module("aops_v1_review_core", REVIEW_CORE)
        cls.seed_validator = load_module("aops_v1_seed_validator", SEED_VALIDATOR)

    def setUp(self):
        self.p = json.loads(PROTOCOL.read_text())
        self.f = json.loads(FREEZE.read_text())

    def test_review_is_non_executable_and_does_not_mutate_r8(self):
        self.assertEqual("REVIEW_ONLY_PREREGISTRATION_EXECUTION_DISABLED_RESULTS_NOT_OPENED", self.p["status"])
        self.assertFalse(self.p["scientificExecutionAuthorized"])
        self.assertFalse(self.p["solverExecutionAuthorized"])
        self.assertFalse(self.p["resultOpeningAuthorized"])
        self.assertTrue(self.p["parentEvidence"]["r8IsImmutablePriorEvidence"])
        self.assertFalse(self.p["parentEvidence"]["reuseR8ScientificIdentityOrSeeds"])
        self.assertTrue(self.f["candidateSeedLedgerMaterialized"])
        self.assertFalse(self.f["candidateSeedsAppliedToCaseSkeletons"])
        self.assertTrue(self.f["candidateSeedFreshnessProofPassed"])
        self.assertFalse(self.f["candidateSeedAuthorizationRecheckPassed"])
        self.assertFalse(self.f["scientificOrdinalAllocated"])
        self.assertFalse(self.f["authorizationCreated"])
        self.assertFalse(self.f["dispatchCreated"])
        self.assertFalse(self.f["reviewCasesRenderable"])
        self.assertFalse(self.f["afc2R8Modified"])
        self.assertFalse((STAGE_DIR / "authorization.json").exists())
        workflows = ROOT / ".github" / "workflows"
        self.assertFalse(any(STAGE in p.name for p in workflows.glob("*.yml")))
        self.assertFalse(any(STAGE in p.name for p in workflows.glob("*.yaml")))

    def test_exact_design_cardinality_and_states(self):
        d = self.p["fixedNumericalAndPhysicalDesign"]
        self.assertEqual([2.0, 4.0, 6.0, 8.0], d["sunDepressionDeg"])
        self.assertEqual([0.10, 0.30], d["aod550"])
        self.assertEqual([1, 2, 3], d["replicates"])
        self.assertEqual(3, len(d["geometries"]))
        self.assertEqual(20_000_000, d["photonHistoriesPerCase"])
        states = self.p["aerosolStates"]
        self.assertEqual(5, len(states))
        self.assertEqual(5, len({s["stateId"] for s in states}))
        self.assertEqual((None, None), (states[0]["ssaSet"], states[0]["ggSet"]))
        factorial = {(s["ssaSet"], s["ggSet"]) for s in states[1:]}
        self.assertEqual({(0.85, 0.60), (0.85, 0.80), (0.98, 0.60), (0.98, 0.80)}, factorial)
        cells = len(d["sunDepressionDeg"]) * len(d["aod550"]) * len(d["geometries"])
        cases = cells * len(d["replicates"]) * len(states)
        self.assertEqual(24, cells)
        self.assertEqual(360, cases)
        self.assertEqual(360, self.p["caseCardinality"]["expectedCases"])
        self.assertEqual(72, self.p["caseCardinality"]["commonRandomNumberGroups"])

    def test_review_core_builds_exact_non_renderable_unseeded_universe(self):
        cells = self.review_core.analysis_cells()
        groups = self.review_core.group_skeletons()
        cases = self.review_core.case_skeletons()
        manifest = self.review_core.review_manifest()
        self.assertEqual(24, len(cells))
        self.assertEqual(72, len(groups))
        self.assertEqual(360, len(cases))
        self.assertEqual(360, len({c["caseId"] for c in cases}))
        self.assertTrue(all(g["seed"] is None and g["seedStatus"] == "UNALLOCATED_REVIEW_ONLY" for g in groups))
        self.assertTrue(all(c["seed"] is None and c["renderable"] is False and c["executionAuthorized"] is False for c in cases))
        self.assertEqual("REVIEW_ONLY_CASE_SKELETONS_NON_RENDERABLE_NO_SEEDS", manifest["status"])
        self.assertFalse(manifest["candidateSeedsAllocated"])
        self.assertFalse(manifest["scientificExecutionAuthorized"])
        self.assertFalse(manifest["resultOpeningAuthorized"])
        grouped = {}
        for c in cases:
            grouped.setdefault(c["groupId"], []).append(c)
        self.assertEqual(72, len(grouped))
        self.assertTrue(all(len(v) == 5 and {x["stateId"] for x in v} == {s["stateId"] for s in self.p["aerosolStates"]} for v in grouped.values()))

    def test_candidate_seed_ledger_is_deterministic_unique_and_not_applied(self):
        ledger = self.seed_validator.validate_ledger()
        rows = self.seed_validator.derive_rows()
        seeds = [row["seed"] for row in rows]
        self.assertEqual(72, len(seeds))
        self.assertEqual(72, len(set(seeds)))
        self.assertEqual(ledger["candidateFirstSeed"], seeds[0])
        self.assertEqual(ledger["candidateLastSeed"], seeds[-1])
        self.assertTrue(all(row["collisionCounter"] == 0 for row in rows))
        self.assertEqual("09d011f216187ad48d23e1744a0bb8b9f7c6aa65f0e1ceba1495f8440aa59366", ledger["candidateSeedCanonicalSha256"])
        self.assertEqual("0fad36398515581a9cc723a2fc2c10a1b88f26882501a57a46c7868cc832da9a", ledger["candidateRowsCanonicalSha256"])
        self.assertFalse(ledger["appliedToCaseSkeletons"])
        self.assertFalse(ledger["scientificOrdinalAllocated"])
        self.assertFalse(ledger["authorizationPermitted"])
        self.assertFalse(ledger["solverExecutionAuthorized"])
        self.assertTrue(all(g["seed"] is None for g in self.review_core.group_skeletons()))

    def test_seed_freshness_proof_is_exact_and_still_requires_authorization_recheck(self):
        proof = json.loads(SEED_PROOF.read_text())
        self.assertEqual("PASS_CANDIDATE_SEEDS_REVIEW_FRESHNESS_NOT_AUTHORIZED", proof["status"])
        self.assertEqual("695ed9a666e3dec4fa1bcc22e62b1f79991e9918", proof["auditedHead"])
        self.assertEqual(72, proof["candidateSeedCount"])
        self.assertEqual(0, proof["trackedTreeExternalCollisionCount"])
        self.assertTrue(proof["exactHeadTrackedTreeByteScanPassed"])
        self.assertEqual(0, proof["repositoryGlobalCollisionCount"])
        self.assertTrue(proof["repositoryGlobalCollisionSurfaceScanPassed"])
        self.assertTrue(proof["repositoryGlobalDoubleEnumerationStable"])
        self.assertTrue(proof["auditedBranchHeadMatchesRepositoryHead"])
        self.assertTrue(proof["authorizationTimeRecheckStillRequired"])
        self.assertFalse(proof["candidateSeedsAppliedToCaseSkeletons"])
        self.assertFalse(proof["scientificOrdinalAllocated"])
        self.assertFalse(proof["authorizationCreated"])
        self.assertFalse(proof["dispatchCreated"])
        self.assertFalse(proof["solverExecutionAuthorized"])
        self.assertFalse(proof["resultOpeningAuthorized"])

    def test_seed_scanners_are_bound_and_self_ledger_policy_is_narrow(self):
        self.assertEqual("1c110d75b516cb7b9d50dc2674080f4a67e55d2a", git_blob_sha1(ROOT / "experiments/aerosol-family-challenge-v2/tracked_tree_seed_scan.py"))
        self.assertEqual("4c6d704fa24228284780bcb1dd7c52537b4c5b0d", git_blob_sha1(ROOT / "experiments/aerosol-family-challenge-v2/repository_global_seed_scan.py"))
        self.assertIn("EXPECTED_BLOB = \"1c110d75b516cb7b9d50dc2674080f4a67e55d2a\"", TRACKED_SCANNER.read_text())
        self.assertIn("EXPECTED_BLOB = \"4c6d704fa24228284780bcb1dd7c52537b4c5b0d\"", GLOBAL_SCANNER.read_text())
        self.assertIn('aops-v1-seed-freshness-review-proof', GLOBAL_SCANNER.read_text())
        policy = json.loads(SEED_POLICY.read_text())
        self.assertEqual(2, policy["schemaVersion"])
        self.assertEqual(["experiments/aerosol-optical-property-sensitivity-v1/candidate-seed-ledger.v1.json"], policy["requiredTrackedSelfLedgerPaths"])
        self.assertEqual(["evidence/aerosol-optical-property-sensitivity-v1/seed-freshness-proof.json"], policy["futureEvidenceSelfLedgerPaths"])
        self.assertFalse(policy["candidateSeedsMayAppearElsewhereInTrackedTree"])
        self.assertFalse(policy["authorizationPermitted"])
        self.assertFalse(policy["solverExecutionAuthorized"])

    def test_adapter_exact_aerosol_directive_order_and_fail_closed_seed_gate(self):
        native = self.adapter.aerosol_block("native-rural-ss", 0.10)
        self.assertEqual([
            "aerosol_default",
            "aerosol_haze 1",
            "aerosol_vulcan 1",
            "aerosol_season 1",
            "aerosol_set_tau_at_wvl 550 0.100000",
        ], native)
        factorial = self.adapter.aerosol_block("ssa085-g080", 0.30)
        self.assertEqual(native[:4] + [
            "aerosol_set_tau_at_wvl 550 0.300000",
            "aerosol_modify ssa set 0.85",
            "aerosol_modify gg set 0.80",
        ], factorial)
        skeleton = dict(self.review_core.case_skeletons()[0])
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(self.adapter.Refusal):
                self.adapter.render_case_input(skeleton, Path(td) / "data", ROOT, Path(td) / "out")
            seeded_but_unauthorized = dict(skeleton, seed=json.loads(CANDIDATE_LEDGER.read_text())["candidateSeeds"][0])
            with self.assertRaises(self.adapter.Refusal):
                self.adapter.render_case_input(seeded_but_unauthorized, Path(td) / "data", ROOT, Path(td) / "out")
            executable_mock = dict(skeleton, seed=123456789, renderable=True, executionAuthorized=True)
            text = self.adapter.render_case_input(executable_mock, Path(td) / "data", ROOT, Path(td) / "out")
        self.adapter.assert_exact_aerosol_surface(text, executable_mock["stateId"], executable_mock["aod550"])
        self.assertEqual(1, text.count("mc_randomseed 123456789"))
        self.assertEqual(1, text.count("aerosol_set_tau_at_wvl 550 0.100000"))
        self.assertNotIn("aerosol_modify ", text)

    def test_factorial_render_contains_exact_one_ssa_and_g_override(self):
        row = next(c for c in self.review_core.case_skeletons() if c["stateId"] == "ssa098-g080")
        row = dict(row, seed=987654321, renderable=True, executionAuthorized=True)
        with tempfile.TemporaryDirectory() as td:
            text = self.adapter.render_case_input(row, Path(td) / "data", ROOT, Path(td) / "out")
        self.assertEqual(1, text.count("aerosol_modify ssa set 0.98"))
        self.assertEqual(1, text.count("aerosol_modify gg set 0.80"))
        self.assertEqual(1, text.count("aerosol_set_tau_at_wvl 550 0.100000"))
        self.assertNotIn("mc_spectral_is ", text)

    def test_crn_and_analysis_rules_are_frozen(self):
        crn = self.p["commonRandomNumbers"]
        self.assertTrue(crn["required"])
        self.assertTrue(crn["sameFreshSeedAcrossAllFiveStatesWithinGroup"])
        self.assertFalse(crn["candidateSeedsAllocatedInThisReview"])
        self.assertTrue(crn["repositoryGlobalFreshnessAuditRequiredBeforeAuthorization"])
        self.assertFalse(crn["githubRerunRetryResumePermitted"])
        self.assertEqual("aerosol-optical-property-sensitivity-v1|group-seed|sha256-v1", crn["freshNamespaceRequired"])
        n = self.p["numericRules"]
        self.assertEqual("NUMERICALLY_UNRESOLVED", n["requiredNonpositiveOrNonfiniteResponse"])
        self.assertFalse(n["epsilonSubstitutionPermitted"])
        self.assertFalse(n["pValuesPermitted"])
        self.assertFalse(n["confidenceIntervalsPermitted"])
        self.assertFalse(n["postResultRuleChangePermitted"])
        self.assertFalse(n["adaptiveCaseAdditionPermitted"])

    def test_level_b_endpoint_and_control_surface_are_exact(self):
        lb = self.p["secondaryLevelBEndpoint"]
        self.assertTrue(lb["preregistered"])
        self.assertEqual("a422afe5fc4197ab15323bafb15512001e061454", lb["starsvisibilityMainSha"])
        self.assertEqual("bb4cd0ff02159ecffe276022cec9d292c7a434a3", lb["humanThresholdGitBlobSha1"])
        self.assertEqual(2.4, lb["fieldFactor"])
        c = self.p["libRadtranControlSurface"]
        self.assertEqual("aerosol_modify ssa set <SSA>", c["ssaDirective"])
        self.assertEqual("aerosol_modify gg set <G>", c["asymmetryDirective"])
        text = REVIEW.read_text()
        self.assertIn("not the full scattering phase function", text)
        self.assertIn("aerosol_file moments", text)

    def test_review_freeze_binds_exact_bytes(self):
        self.assertEqual("FROZEN_REVIEW_ONLY_EXECUTION_DISABLED_RESULTS_NOT_OPENED", self.f["status"])
        self.assertEqual("2a9feb864fe7bf328074854d22f0e3c6a5cb7616", self.f["baseMainSha"])
        self.assertEqual(git_blob_sha1(PROTOCOL), self.f["protocolGitBlobSha1"])
        self.assertEqual(git_blob_sha1(REVIEW), self.f["scientificReviewGitBlobSha1"])
        self.assertEqual(git_blob_sha1(ADAPTER), self.f["adapterGitBlobSha1"])
        self.assertEqual(git_blob_sha1(REVIEW_CORE), self.f["reviewCoreGitBlobSha1"])
        self.assertEqual(git_blob_sha1(CANDIDATE_LEDGER), self.f["candidateSeedLedgerGitBlobSha1"])
        self.assertEqual(git_blob_sha1(SEED_VALIDATOR), self.f["candidateSeedValidatorGitBlobSha1"])
        self.assertEqual(git_blob_sha1(TRACKED_SCANNER), self.f["trackedTreeSeedScannerGitBlobSha1"])
        self.assertEqual(git_blob_sha1(GLOBAL_SCANNER), self.f["repositoryGlobalSeedScannerGitBlobSha1"])
        self.assertEqual(git_blob_sha1(SEED_POLICY), self.f["seedSelfLedgerPolicyGitBlobSha1"])
        self.assertEqual(git_blob_sha1(SEED_PROOF), self.f["seedFreshnessProofGitBlobSha1"])
        self.assertEqual("09d011f216187ad48d23e1744a0bb8b9f7c6aa65f0e1ceba1495f8440aa59366", self.f["candidateSeedCanonicalSha256"])
        self.assertTrue(self.f["candidateSeedFreshnessProofPassed"])
        self.assertFalse(self.f["candidateSeedAuthorizationRecheckPassed"])
        self.assertFalse(self.f["scientificExecutionAuthorized"])
        self.assertFalse(self.f["solverExecutionAuthorized"])
        self.assertFalse(self.f["resultOpeningAuthorized"])


if __name__ == "__main__":
    unittest.main()
