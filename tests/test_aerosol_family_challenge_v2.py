from __future__ import annotations

import copy
import importlib.util
import io
import json
import sys
import subprocess
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "experiments" / "aerosol-family-challenge-v2"


def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, PKG / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


core = load("core", "core.py")
adapter = load("afc2_adapter", "adapter.py")
render = load("afc2_render", "render.py")
derived = load("afc2_derived", "derived_channels.py")
freeze_mod = load("afc2_freeze", "freeze.py")
seed_ledger = load("afc2_seed_ledger", "seed_ledger.py")
tree_scan = load("afc2_tree_scan", "tracked_tree_seed_scan.py")
artifact_scan = load("afc2_artifact_scan", "actions_artifact_seed_scan.py")
repo_global_scan = load("afc2_repo_global_scan", "repository_global_seed_scan.py")
analysis_mod = load("afc2_analysis", "analysis.py")
freshness = load("freshness", "execution-candidate/freshness.py")
auth_guard = load("authorization_guard", "execution-candidate/authorization_guard.py")
dispatch_guard = load("dispatch_guard", "execution-candidate/dispatch_guard.py")
exec_guard = load("afc2_exec_guard", "execution-candidate/guard.py")
exec_mod = load("afc2_exec_executor", "execution-candidate/executor.py")


class AerosolFamilyChallengeV2Tests(unittest.TestCase):
    def design(self):
        return json.loads((PKG / "design.review.json").read_text(encoding="utf-8"))

    def full_seed_audit(self, design_path: Path, mode: str = 'review-freeze'):
        design = json.loads(design_path.read_text(encoding="utf-8"))
        seeds = design["groupSeeds"]
        return {
            "schemaVersion": 2,
            "stageId": "aerosol-family-challenge-v2-seed-audit",
            "status": "PASSED_EXACT_HEAD_TRACKED_TREE_AND_REPOSITORY_GLOBAL_COLLISION_SURFACES_NEGATIVE_CHECK",
            "repositoryFullName": core.REPOSITORY_FULL_NAME,
            "auditMode": mode,
            "auditedBranchName": "main" if mode == "review-freeze" else freshness.authorization_branch(999),
            "auditedBranchHeadShaObserved": "a" * 40,
            "auditedBranchHeadMatchesRepositoryHead": True,
            "priorReviewProofArtifactCount": 0 if mode == "review-freeze" else 1,
            "reviewProofIdentityFresh": True if mode == "review-freeze" else None,
            "reviewProofArtifactName": "aerosol-family-v2-r6-freeze-proof",
            "repositoryHead": "a" * 40,
            "sourceBaseMainSha": core.PUBLIC_REPO_MAIN_SHA,
            "candidateFirstSeed": seeds[0],
            "candidateLastSeed": seeds[-1],
            "candidateSeedCount": len(seeds),
            "candidateSeedCanonicalSha256": core.canonical_sha256(seeds),
            "candidateSeedLedgerRawSha256": core.raw_sha256(PKG / "candidate-seed-ledger.v1.json"),
            "candidateSeedDerivationNamespace": core.SEED_DERIVATION_NAMESPACE,
            "auditedDesignRawSha256": core.raw_sha256(design_path),
            "exactHeadTrackedTreeByteScanPassed": True,
            "futureEvidenceSelfLedgerPathsPresent": [],
            "futureEvidenceSelfLedgerPathCountPresent": 0,
            "repositoryGlobalCollisionSurfaceScanPassed": True,
            "repositoryGlobalDoubleEnumerationStable": True,
            "repositoryGlobalEnumerationPassCount": 2,
            "repositoryGlobalStableContextSha256": "b" * 64,
            "allStatePullRequestsInspected": True,
            "allStateIssuesInspected": True,
            "allRepositoryIssueCommentsInspected": True,
            "allRepositoryPullReviewCommentsInspected": True,
            "allRepositoryCommitCommentsInspected": True,
            "externalCollisionCount": 0,
            "excludedCurrentAuditRunId": 123456,
            "authorizationPermitted": False,
        }

    def transport_paths(self, manifest_path: Path, freeze_path: Path, base_dir: Path | None = None):
        src = PKG / "execution-candidate"
        if base_dir is None:
            return {
                "manifest": manifest_path,
                "freeze": freeze_path,
                "transport": src / "transport-contract.v3.json",
                "adapter": PKG / "adapter.py",
                "executor": src / "executor.py",
                "workflow": src / "workflow.yml.template",
                "authorizationGuard": src / "authorization_guard.py",
                "dispatchGuard": src / "dispatch_guard.py",
                "freshness": src / "freshness.py",
                "authorizationReviewWorkflow": src / "authorization-review-workflow.yml.template",
            }
        repo_pkg = base_dir / "experiments" / "aerosol-family-challenge-v2"
        repo_exec = repo_pkg / "execution-candidate"
        repo_exec.mkdir(parents=True, exist_ok=True)
        mapping = {
            "manifest": (manifest_path, repo_pkg / "manifest.frozen.json"),
            "freeze": (freeze_path, repo_pkg / "freeze-record.json"),
            "transport": (src / "transport-contract.v3.json", repo_exec / "transport-contract.v3.json"),
            "adapter": (PKG / "adapter.py", repo_pkg / "adapter.py"),
            "executor": (src / "executor.py", repo_exec / "executor.py"),
            "workflow": (src / "workflow.yml.template", repo_exec / "workflow.yml.template"),
            "authorizationGuard": (src / "authorization_guard.py", repo_exec / "authorization_guard.py"),
            "dispatchGuard": (src / "dispatch_guard.py", repo_exec / "dispatch_guard.py"),
            "freshness": (src / "freshness.py", repo_exec / "freshness.py"),
            "authorizationReviewWorkflow": (
                src / "authorization-review-workflow.yml.template",
                repo_exec / "authorization-review-workflow.yml.template",
            ),
        }
        out = {}
        for key, (source, destination) in mapping.items():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            out[key] = destination
        return out

    def enabled_authorization(self, paths: dict[str, Path], parent: str, ordinal: int = 999):
        return {
            "schemaVersion": 1,
            "stageId": "aerosol-family-challenge-v2-authorization",
            "status": "AUTHORIZED_PENDING_SEPARATE_DISPATCH",
            "repositoryFullName": core.REPOSITORY_FULL_NAME,
            "enabled": True,
            "scientificExecutionAuthorized": True,
            "solverExecutionAuthorized": True,
            "dispatchAuthorized": False,
            "automaticDispatch": False,
            "consumed": False,
            "executionKey": freshness.execution_key(ordinal),
            "scientificOrdinal": ordinal,
            "authorizationBranch": freshness.authorization_branch(ordinal),
            "dispatchBranch": freshness.dispatch_branch(ordinal),
            "exactAuthorizationParentCommit": parent,
            "exactAuthorizationCommit": None,
            "manifestRawSha256": core.raw_sha256(paths["manifest"]),
            "freezeRecordRawSha256": core.raw_sha256(paths["freeze"]),
            "transportContractRawSha256": core.raw_sha256(paths["transport"]),
            "adapterRawSha256": core.raw_sha256(paths["adapter"]),
            "executorRawSha256": core.raw_sha256(paths["executor"]),
            "workflowRawSha256": core.raw_sha256(paths["workflow"]),
            "authorizationGuardRawSha256": core.raw_sha256(paths["authorizationGuard"]),
            "dispatchGuardRawSha256": core.raw_sha256(paths["dispatchGuard"]),
            "freshnessGuardRawSha256": core.raw_sha256(paths["freshness"]),
            "authorizationReviewWorkflowRawSha256": core.raw_sha256(paths["authorizationReviewWorkflow"]),
            "runtimeLockRawSha256": "3b5fbec964642b04c73a6423b3355dbcc4ba5e84f9614f6d74420491bacc20c5",
            "githubRerunAllowed": False,
            "retryAllowed": False,
            "resumeAllowed": False,
            "protectedHoldoutOpeningAuthorized": False,
            "modelFittingAuthorized": False,
            "modelSelectionAuthorized": False,
            "tier2Authorized": False,
            "productionPromotionAuthorized": False,
        }

    def identity_freshness(self, ordinal: int, head: str | None = None, *, dispatch_exists: bool = False, marker_count: int = 0):
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
            "authorizationBranchExists": head is not None,
            "authorizationBranchHeadSha": head,
            "authorizationBranchReusableAfterFailedReview": False,
            "activeAuthorizationPathOnMainExists": False,
            "matchingAuthorizationMarkers": marker_count,
            "dispatchBranchExists": dispatch_exists,
            "dispatchBranchHeadSha": head if dispatch_exists else None,
        }

    def authorization_review_context(self, authorization: dict, head: str, parent: str, *, pr_number: int = 77):
        ordinal = authorization["scientificOrdinal"]
        return {
            "liveMain": parent,
            "headSha": head,
            "parentSha": parent,
            "parentCount": 1,
            "authorizationPath": "experiments/aerosol-family-challenge-v2/authorization.json",
            "changedPaths": ["experiments/aerosol-family-challenge-v2/authorization.json"],
            "pr": {
                "number": pr_number,
                "state": "open",
                "draft": True,
                "merged": False,
                "headBranch": authorization["authorizationBranch"],
                "baseBranch": "main",
                "headRepo": core.REPOSITORY_FULL_NAME,
                "baseRepo": core.REPOSITORY_FULL_NAME,
                "headSha": head,
            },
            "runAttempt": 1,
            "eventName": "pull_request",
            "eventAction": "opened",
            "scientificRuntimeSetupPerformed": False,
            "scientificExecutionPerformed": False,
            "freshness": self.identity_freshness(ordinal, head, dispatch_exists=False, marker_count=0),
        }

    def test_official_family_and_season_codes_are_frozen(self):
        self.assertEqual(core.FAMILIES, {"rural": 1, "maritime": 4, "urban": 5, "tropospheric": 6})
        self.assertEqual(core.SEASONS, {"spring-summer": 1, "fall-winter": 2})

    def test_review_geometry_is_exactly_source_bound_g02_g04_g06_at_zero_meters(self):
        design = self.design()
        self.assertEqual(design["geometryTemplates"], [dict(row) for row in core.V2_GEOMETRY_TEMPLATES])
        self.assertEqual([row["observerElevationM"] for row in design["geometryTemplates"]], [0.0, 0.0, 0.0])
        core.validate_design(design)

    def test_geometry_drift_refuses(self):
        design = self.design()
        design["geometryTemplates"][1]["observerElevationM"] = 1000.0
        with self.assertRaises(core.Refusal):
            core.build_manifest(design)

    def test_uniform_20m_photon_budget_and_total_11_52b(self):
        manifest = core.build_manifest(self.design())
        self.assertEqual(set(self.design()["photonHistoriesBySunDepression"].values()), {20_000_000})
        self.assertEqual(manifest["configuredPhotonHistoriesTotal"], 11_520_000_000)

    def test_photon_budget_drift_refuses(self):
        design = self.design()
        design["photonHistoriesBySunDepression"]["8"] = 19_000_000
        with self.assertRaises(core.Refusal):
            core.build_manifest(design)

    def test_exact_72_groups_and_576_cases(self):
        manifest = core.build_manifest(self.design())
        self.assertEqual(manifest["comparisonGroupCount"], 72)
        self.assertEqual(manifest["caseCount"], 576)

    def test_manifest_has_24_analysis_cells_with_three_replicates_each(self):
        manifest = core.build_manifest(self.design())
        self.assertEqual(manifest["analysisCellCount"], 24)
        cells = {}
        for group in manifest["groups"]:
            cells.setdefault(group["analysisCellId"], []).append(group["replicate"])
        self.assertEqual(len(cells), 24)
        self.assertTrue(all(sorted(reps) == [1, 2, 3] for reps in cells.values()))

    def test_each_group_has_eight_states_and_pairing_invariants(self):
        manifest = core.build_manifest(self.design())
        by_group = {}
        for case in manifest["cases"]:
            by_group.setdefault(case["groupId"], []).append(case)
        self.assertEqual(len(by_group), 72)
        for rows in by_group.values():
            self.assertEqual(len(rows), 8)
            anchor = rows[0]
            for field in core.PAIRING_FIELDS:
                self.assertEqual({row[field] for row in rows}, {anchor[field]})
            self.assertEqual(
                {(row["aerosolFamily"], row["aerosolSeason"]) for row in rows},
                {(f, s) for f in core.FAMILIES for s in core.SEASONS},
            )


    def test_candidate_seed_ledger_is_sha256_derived_and_exactly_matches_core(self):
        ledger = seed_ledger.build_ledger()
        self.assertEqual(ledger["namespace"], core.SEED_DERIVATION_NAMESPACE)
        self.assertEqual(ledger["candidateSeeds"], list(core.CANDIDATE_GROUP_SEEDS))
        self.assertEqual(len(set(ledger["candidateSeeds"])), 72)
        self.assertTrue(ledger["allCollisionCountersZero"])
        self.assertEqual(ledger["candidateSeedCanonicalSha256"], core.canonical_sha256(list(core.CANDIDATE_GROUP_SEEDS)))

    def test_design_candidate_seed_derivation_binds_exact_local_ledger_bytes(self):
        design = self.design()
        design["seedFreshnessReview"]["candidateSeedDerivation"]["ledgerRawSha256"] = "0" * 64
        with self.assertRaisesRegex(core.Refusal, "exact local ledger bytes"):
            core.validate_design(design)

    def test_candidate_seed_derivation_is_bound_to_analysis_cell_and_replicate(self):
        manifest = core.build_manifest(self.design())
        expected = {(row["analysisCellId"], row["replicate"]): row["seed"] for row in core.CANDIDATE_SEED_ROWS}
        got = {(row["analysisCellId"], row["replicate"]): row["seed"] for row in manifest["groups"]}
        self.assertEqual(got, expected)

    def test_common_random_number_seed_is_shared_within_group_only(self):
        manifest = core.build_manifest(self.design())
        group_seeds = {}
        for case in manifest["cases"]:
            group_seeds.setdefault(case["groupId"], set()).add(case["seed"])
        self.assertTrue(all(len(seeds) == 1 for seeds in group_seeds.values()))
        flattened = [next(iter(seeds)) for seeds in group_seeds.values()]
        self.assertEqual(len(set(flattened)), 72)
        self.assertEqual(flattened[0], core.CANDIDATE_SEED_FIRST)
        self.assertEqual(flattened[-1], core.CANDIDATE_SEED_LAST)

    def test_duplicate_group_seed_refuses(self):
        design = self.design()
        design["groupSeeds"][1] = design["groupSeeds"][0]
        with self.assertRaises(core.Refusal):
            core.build_manifest(design)

    def test_versioned_candidate_seed_ledger_drift_refuses(self):
        design = self.design()
        design["groupSeeds"] = list(range(1_912_000_001, 1_912_000_073))
        design["seedFreshnessReview"]["candidateFirstSeed"] = design["groupSeeds"][0]
        design["seedFreshnessReview"]["candidateLastSeed"] = design["groupSeeds"][-1]
        design["seedFreshnessReview"]["candidateSeedCanonicalSha256"] = core.canonical_sha256(design["groupSeeds"])
        with self.assertRaises(core.Refusal):
            core.build_manifest(design)

    def test_full_spectrum_contract_distinguishes_calculation_and_raw_output_grids(self):
        manifest = core.build_manifest(self.design())
        self.assertEqual(manifest["calculationGrid"], {"startNm": 380, "stopNm": 780, "stepNm": 1, "nodeCount": 401})
        self.assertEqual(manifest["expectedRawOutputGrid"], {"startNm": 380.0, "stopNm": 780.0, "stepNm": 0.05, "nodeCount": 8001, "pointToleranceNm": 0.00005})
        for case in manifest["cases"][:16]:
            self.assertEqual(case["calculationGrid"]["nodeCount"], 401)
            self.assertEqual(case["expectedRawOutputGrid"]["nodeCount"], 8001)

    def test_reviewed_calculation_grid_is_exact_401_node_git_blob(self):
        grid = PKG / "wavelength-grid-1nm.dat"
        self.assertEqual(grid.read_text().splitlines(), [str(x) for x in range(380, 781)])
        self.assertEqual(core.git_blob_sha1(grid), "3bb3db96580d555ef758f57cabd6cac55b61cebb")

    def test_rendered_case_inp_contains_exact_family_season_and_full_spectrum_surface(self):
        manifest = core.build_manifest(self.design())
        group_id = manifest["cases"][0]["groupId"]
        rows = [c for c in manifest["cases"] if c["groupId"] == group_id]
        with tempfile.TemporaryDirectory() as td_s:
            td = Path(td_s)
            data = td / "data"
            out = td / "out"
            rendered = []
            for case in rows:
                text = adapter.render_case_input(case, data, ROOT, out)
                case_dir = td / case["caseId"]
                case_dir.mkdir()
                inp = case_dir / "case.inp"
                inp.write_text(text)
                reread = inp.read_text()
                adapter.assert_exact_aerosol_state(reread, case)
                adapter.assert_exact_spectrum_surface(reread)
                self.assertIn(f"aerosol_haze {case['aerosolHazeCode']}\n", reread)
                self.assertIn(f"aerosol_season {case['aerosolSeasonCode']}\n", reread)
                self.assertIn("mc_vroom on\n", reread)
                self.assertIn("mc_std\n", reread)
                self.assertNotIn("mc_spectral_is ", reread)
                rendered.append(reread)
            self.assertEqual(len(set(rendered)), 8)

    def test_all_576_rendered_inputs_bind_case_seed_budget_geometry_aod_and_aerosol_state(self):
        manifest = core.build_manifest(self.design())
        with tempfile.TemporaryDirectory() as td_s:
            td = Path(td_s)
            for case in manifest["cases"]:
                text = adapter.render_case_input(case, td / "data", ROOT, td / "out")
                lines = text.splitlines()
                self.assertIn(f"mc_randomseed {case['seed']}", lines)
                self.assertIn(f"mc_photons {case['photonHistories']}", lines)
                self.assertIn(f"sza {90.0 + case['sunDepressionDeg']:.6f}", lines)
                self.assertIn(f"phi {case['relativeAzimuthDeg']:.6f}", lines)
                self.assertIn(f"aerosol_set_tau_at_wvl 550 {case['aod550']:.6f}", lines)
                self.assertIn(f"aerosol_haze {case['aerosolHazeCode']}", lines)
                self.assertIn(f"aerosol_season {case['aerosolSeasonCode']}", lines)
                adapter.assert_exact_aerosol_state(text, case)
                adapter.assert_exact_spectrum_surface(text)

    def test_pinned_base_transform_rejects_unexpected_aerosol_directive(self):
        case = core.build_manifest(self.design())["cases"][0]
        base = (
            f"rte_solver mystic\nmc_photons {case['photonHistories']}\nmc_randomseed {case['seed']}\n"
            f"aerosol_default\naerosol_visibility 50\naerosol_set_tau_at_wvl 550 {case['aod550']:.6f}\n"
            "zout 0.000000\nquiet\n"
        )
        with self.assertRaisesRegex(core.Refusal, "base aerosol directive surface drifted"):
            adapter.transform_pinned_base_render(base, case)

    def test_pinned_base_transform_preserves_non_aerosol_lines(self):
        case = core.build_manifest(self.design())["cases"][0]
        base = (
            f"data_files_path /x\nrte_solver mystic\nmc_photons {case['photonHistories']}\nmc_randomseed {case['seed']}\n"
            f"aerosol_default\naerosol_set_tau_at_wvl 550 {case['aod550']:.6f}\nzout 0.000000\nquiet\n"
        )
        out = adapter.transform_pinned_base_render(base, case)
        for line in ("data_files_path /x", "rte_solver mystic", f"mc_photons {case['photonHistories']}", f"mc_randomseed {case['seed']}", "zout 0.000000", "quiet"):
            self.assertEqual(out.splitlines().count(line), 1)

    def test_manifest_generation_is_deterministic(self):
        a = core.build_manifest(self.design())
        b = core.build_manifest(self.design())
        self.assertEqual(core.canonical_sha256(a), core.canonical_sha256(b))

    def test_derived_channel_implementation_is_scale_consistent_and_sp_invariant(self):
        wl = [380.0 + 0.05 * i for i in range(8001)]
        one = [1.0] * 8001
        two = [2.0] * 8001
        a = derived.derive_channels(wl, one)
        b = derived.derive_channels(wl, two)
        for key in ("photopicLuminanceCdM2", "scotopicLuminanceScotCdM2", "johnsonVEffectiveRadiance_mW_m2_nm_sr"):
            self.assertAlmostEqual(b[key], 2.0 * a[key], places=10)
        self.assertAlmostEqual(a["scotopicPhotopicRatio"], b["scotopicPhotopicRatio"], places=12)

    def test_frozen_analysis_order_is_pair_first_then_three_replicates(self):
        base = {
            "photopicLuminanceCdM2": 10.0,
            "scotopicLuminanceScotCdM2": 20.0,
            "scotopicPhotopicRatio": 2.0,
            "johnsonVEffectiveRadiance_mW_m2_nm_sr": 5.0,
            "radianceSpectrum": [1.0] * 8001,
        }
        state = {
            "photopicLuminanceCdM2": 20.0,
            "scotopicLuminanceScotCdM2": 40.0,
            "scotopicPhotopicRatio": 2.0,
            "johnsonVEffectiveRadiance_mW_m2_nm_sr": 10.0,
            "radianceSpectrum": [2.0] * 8001,
        }
        reps = [analysis_mod.paired_replicate_contrast(state, base) for _ in range(3)]
        summary = analysis_mod.aggregate_state_replicates(reps)
        want = __import__("math").log(2.0)
        for channel in analysis_mod.PRIMARY_CHANNELS:
            row = summary["primary"][channel]
            self.assertAlmostEqual(row["mean"], want, places=12)
            self.assertAlmostEqual(row["sampleStd"], 0.0, places=12)
            self.assertAlmostEqual(row["standardError"], 0.0, places=12)
            self.assertEqual(row["signConsistency"], "CONSISTENT_NONNEGATIVE")
            self.assertEqual(row["meanInterpretationLabel"], "STRONG_AT_LEAST_50_PERCENT")
            self.assertEqual(row["meanStrongRatioFlag"], "VERY_LARGE_RATIO_AT_LEAST_2X_OR_AT_MOST_HALF")
            self.assertFalse(row["magnitudeInterpretationUncertain"])
        self.assertAlmostEqual(summary["spectralLogRatioByWavelength"][4000]["mean"], want, places=12)
        self.assertFalse(summary["inferentialPValueOrConfidenceIntervalPermitted"])

    def test_strong_ratio_flag_is_directionally_symmetric_at_preregistered_boundaries(self):
        import math
        self.assertEqual(analysis_mod.strong_ratio_flag(math.log(1.5)), "STRONG_RATIO_AT_LEAST_1P5X_OR_AT_MOST_TWO_THIRDS")
        self.assertEqual(analysis_mod.strong_ratio_flag(math.log(2.0 / 3.0)), "STRONG_RATIO_AT_LEAST_1P5X_OR_AT_MOST_TWO_THIRDS")
        self.assertEqual(analysis_mod.strong_ratio_flag(math.log(2.0)), "VERY_LARGE_RATIO_AT_LEAST_2X_OR_AT_MOST_HALF")
        self.assertEqual(analysis_mod.strong_ratio_flag(math.log(0.5)), "VERY_LARGE_RATIO_AT_LEAST_2X_OR_AT_MOST_HALF")
        self.assertEqual(analysis_mod.strong_ratio_flag(math.log(1.2)), "NOT_STRONG_RATIO_FLAG")

    def test_analysis_contract_binds_current_analysis_implementation_bytes(self):
        contract = json.loads((PKG / "analysis-contract.v3.json").read_text())
        self.assertEqual(contract["analysisImplementation"]["localImplementationRawSha256"], core.raw_sha256(PKG / "analysis.py"))
        self.assertIn("separate directional ratio flag", contract["strongRatioFlag"])

    def test_frozen_analysis_preserves_zero_as_unresolved_no_epsilon(self):
        self.assertIsNone(analysis_mod.paired_log(0.0, 1.0))
        self.assertIsNone(analysis_mod.paired_log(1.0, 0.0))
        row = analysis_mod.summarize_three([0.1, None, 0.2])
        self.assertEqual(row["status"], "NUMERICALLY_UNRESOLVED")
        self.assertIsNone(row["mean"])

    def test_marginal_mc_std_diagnostic_is_never_used_as_paired_contrast_uncertainty(self):
        wl = [380.0 + 0.05 * i for i in range(8001)]
        rad = [2.0] * 8001
        std = [0.2] * 8001
        diag = derived.marginal_mc_std_diagnostics(wl, rad, std)
        self.assertEqual(diag["status"], "MARGINAL_MC_STD_DIAGNOSTIC_ONLY")
        self.assertAlmostEqual(diag["medianRelativeStd"], 0.1, places=12)
        self.assertAlmostEqual(diag["maximumRelativeStd"], 0.1, places=12)
        self.assertFalse(diag["pairedContrastUncertaintyUsePermitted"])

    def test_derived_channel_grid_mismatch_refuses(self):
        wl = [380.0 + 0.05 * i for i in range(8001)]
        rad = [1.0] * 8001
        wl[100] += 0.01
        with self.assertRaises(ValueError):
            derived.derive_channels(wl, rad)

    def test_derived_channel_source_and_local_hash_are_frozen(self):
        design = self.design()
        source = design["sourceBindings"]["derivedChannelImplementationBasis"]
        self.assertEqual(source["gitBlobSha"], "9bc53956fc4a49935ba2957087d8bf4203b7e8be")
        contract = json.loads((PKG / "analysis-contract.v3.json").read_text())
        self.assertEqual(contract["channelDefinitions"]["sourceGitBlobSha"], source["gitBlobSha"])
        self.assertEqual(contract["channelDefinitions"]["localImplementationRawSha256"], core.raw_sha256(PKG / "derived_channels.py"))

    def test_analysis_contract_is_crn_aware_and_forbids_independent_quadrature(self):
        contract = json.loads((PKG / "analysis-contract.v3.json").read_text())
        self.assertEqual(contract["schemaVersion"], 3)
        self.assertEqual(contract["status"], "FROZEN_BEFORE_RESULTS")
        self.assertFalse(contract["resultsOpened"])
        self.assertIn("independent quadrature", contract["commonRandomNumberUncertainty"]["forbidden"])
        self.assertIn("three independent paired-seed replicate contrasts", contract["commonRandomNumberUncertainty"]["rule"])
        self.assertIn("coefficient retuning", set(contract["forbidden"]))
        self.assertIn("human-threshold retuning", set(contract["forbidden"]))
        self.assertIn("field-factor retuning", set(contract["forbidden"]))

    def test_no_posthoc_scalar_color_metric_is_left_open(self):
        contract = json.loads((PKG / "analysis-contract.v3.json").read_text())
        self.assertEqual(
            contract["channelDefinitions"]["additionalScalarColorIndex"],
            "NONE_PREDECLARED; spectral/color response is represented by S/P and the full per-wavelength paired log-ratio vector",
        )

    def test_review_seed_evidence_is_explicitly_incomplete(self):
        design = self.design()
        review = json.loads((PKG / "seed-collision-review.v2.json").read_text(encoding="utf-8"))
        self.assertTrue(design["seedFreshnessReview"]["candidateOnly"])
        self.assertFalse(review["exactHeadTrackedTreeByteScanPassed"])
        self.assertFalse(review["repositoryGlobalCollisionSurfaceScanPassed"])
        self.assertIsNone(review["externalCollisionCount"])
        self.assertFalse(review["authorizationPermitted"])
        self.assertEqual(review["auditedDesignRawSha256"], core.raw_sha256(PKG / "design.review.json"))

    def test_seed_proof_template_is_schema_v2_and_explicitly_not_proof(self):
        template = json.loads((PKG / "seed-freshness-proof.template.json").read_text())
        self.assertEqual(template["schemaVersion"], 2)
        self.assertEqual(template["status"], "INCOMPLETE_REVIEW_TEMPLATE_NOT_PROOF")
        self.assertFalse(template["exactHeadTrackedTreeByteScanPassed"])
        self.assertFalse(template["repositoryGlobalCollisionSurfaceScanPassed"])
        self.assertIsNone(template["repositoryHead"])
        self.assertFalse(template["authorizationPermitted"])

    def test_only_v3_analysis_contract_is_active_at_package_root(self):
        self.assertFalse((PKG / "analysis-contract.v2.json").exists())
        self.assertTrue((PKG / "analysis-contract.v3.json").is_file())
        self.assertTrue((PKG / "reference/superseded-pre-result/analysis-contract.v2.json").is_file())

    def test_review_seed_audit_refuses_freeze_before_writing_outputs(self):
        with tempfile.TemporaryDirectory() as td_s:
            td = Path(td_s)
            manifest_path = td / "manifest.json"
            freeze_path = td / "freeze.json"
            with self.assertRaisesRegex(core.Refusal, "seed freshness proof is incomplete"):
                freeze_mod.freeze(
                    PKG / "design.review.json",
                    PKG / "analysis-contract.v3.json",
                    PKG / "seed-collision-review.v2.json",
                    manifest_path,
                    freeze_path,
                )
            self.assertFalse(manifest_path.exists())
            self.assertFalse(freeze_path.exists())

    def test_freeze_success_path_requires_explicit_exact_design_bound_seed_proof(self):
        with tempfile.TemporaryDirectory() as td_s:
            td = Path(td_s)
            audit_path = td / "seed-audit.json"
            manifest_path = td / "manifest.json"
            freeze_path = td / "freeze.json"
            audit_path.write_text(core.dump(self.full_seed_audit(PKG / "design.review.json")), encoding="utf-8")
            record = freeze_mod.freeze(
                PKG / "design.review.json",
                PKG / "analysis-contract.v3.json",
                audit_path,
                manifest_path,
                freeze_path,
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(record["status"], "FROZEN_REVIEW_PACKAGE_NOT_AUTHORIZATION")
            self.assertEqual(record["seedAuditExactHead"], "a" * 40)
            self.assertTrue(record["authorizationTimeSeedRecheckStillRequired"])
            self.assertEqual(manifest["status"], "FROZEN_MANIFEST_SEED_FRESHNESS_PROVEN_REVIEW_ONLY")
            self.assertFalse(record["scientificExecutionAuthorized"])
            self.assertFalse(record["solverExecutionAuthorized"])
            self.assertFalse(record["resultsOpened"])

    def test_seed_audit_exact_head_can_differ_from_source_base_main(self):
        audit = self.full_seed_audit(PKG / "design.review.json")
        self.assertNotEqual(audit["repositoryHead"], core.PUBLIC_REPO_MAIN_SHA)
        core.validate_seed_audit_for_freeze(audit, PKG / "design.review.json", self.design())


    def test_seed_audit_schema_v1_is_not_freeze_eligible(self):
        audit = self.full_seed_audit(PKG / "design.review.json")
        audit["schemaVersion"] = 1
        with self.assertRaisesRegex(core.Refusal, "seed freshness proof is incomplete"):
            core.validate_seed_audit_for_freeze(audit, PKG / "design.review.json", self.design())

    def test_preauthorization_refuses_incomplete_all_state_identity_surface(self):
        ctx = {
            "authorizationCreated": False,
            "scientificRuntimeSetupPerformed": False,
            "scientificExecutionPerformed": False,
            "freshness": self.identity_freshness(999, None, dispatch_exists=False, marker_count=0),
        }
        ctx["freshness"]["allStateIssuesInspected"] = False
        with self.assertRaisesRegex(freshness.FreshnessRefusal, "all-state issues not inspected"):
            auth_guard.preauthorize(ctx, 999)

    def test_seed_audit_candidate_ledger_hash_mismatch_refuses(self):
        audit = self.full_seed_audit(PKG / "design.review.json")
        audit["candidateSeedLedgerRawSha256"] = "0" * 64
        with self.assertRaisesRegex(core.Refusal, "does not bind exact candidate seed ledger"):
            core.validate_seed_audit_for_freeze(audit, PKG / "design.review.json", self.design())

    def test_seed_audit_design_hash_mismatch_refuses(self):
        audit = self.full_seed_audit(PKG / "design.review.json")
        audit["auditedDesignRawSha256"] = "0" * 64
        with self.assertRaisesRegex(core.Refusal, "does not bind exact design bytes"):
            core.validate_seed_audit_for_freeze(audit, PKG / "design.review.json", self.design())

    def test_tracked_tree_scanner_allows_only_declared_self_ledger(self):
        with tempfile.TemporaryDirectory() as td_s:
            td = Path(td_s)
            allowed = td / "design.json"
            external = td / "other.txt"
            seed = core.CANDIDATE_SEED_FIRST
            allowed.write_text(str(seed))
            external.write_text("nothing")
            fl = td / "files.nul"
            fl.write_bytes(b"design.json\0other.txt\0")
            ok = tree_scan.scan(td, fl, {seed, *list(core.CANDIDATE_GROUP_SEEDS)[1:]}, {"design.json"})
            self.assertTrue(ok["exactHeadTrackedTreeByteScanPassed"])
            external.write_text(str(seed))
            bad = tree_scan.scan(td, fl, {seed, *list(core.CANDIDATE_GROUP_SEEDS)[1:]}, {"design.json"})
            self.assertFalse(bad["exactHeadTrackedTreeByteScanPassed"])
            self.assertEqual(bad["trackedTreeExternalCollisionCount"], 1)


    def empty_repository_global_context(self):
        return {
            "branches": [], "runs": [], "artifacts": [], "pulls": [], "issues": [],
            "issueComments": [], "pullReviewComments": [], "commitComments": [], "issue60Comments": [],
        }

    def test_repository_global_scanner_detects_candidate_on_control_or_run_metadata(self):
        seed = core.CANDIDATE_SEED_FIRST
        base = self.empty_repository_global_context()
        ok = repo_global_scan.evaluate_context(base, set(core.CANDIDATE_GROUP_SEEDS))
        self.assertTrue(ok["repositoryGlobalCollisionSurfaceScanPassed"])
        bad = copy.deepcopy(base)
        bad["issue60Comments"] = [{"id": 1, "body": f"seed {seed}"}]
        out = repo_global_scan.evaluate_context(bad, set(core.CANDIDATE_GROUP_SEEDS))
        self.assertFalse(out["repositoryGlobalCollisionSurfaceScanPassed"])
        self.assertEqual(out["repositoryGlobalCollisionCount"], 1)

    def test_repository_global_scanner_covers_all_state_pr_issue_and_repository_comments(self):
        seed = core.CANDIDATE_SEED_FIRST
        for surface in ("pulls", "issues", "issueComments", "pullReviewComments", "commitComments"):
            ctx = self.empty_repository_global_context()
            ctx[surface] = [{"id": 77, "body": f"historical seed {seed}"}]
            out = repo_global_scan.evaluate_context(ctx, set(core.CANDIDATE_GROUP_SEEDS))
            self.assertFalse(out["repositoryGlobalCollisionSurfaceScanPassed"], surface)
            self.assertEqual(out["repositoryGlobalCollisionCount"], 1, surface)

    def test_repository_global_scanner_excludes_only_current_run_metadata(self):
        seed = core.CANDIDATE_SEED_FIRST
        ctx = self.empty_repository_global_context()
        ctx["runs"] = [{"id": 99, "display_title": str(seed)}]
        ok = repo_global_scan.evaluate_context(ctx, set(core.CANDIDATE_GROUP_SEEDS), current_run_id=99)
        self.assertTrue(ok["repositoryGlobalCollisionSurfaceScanPassed"])
        bad = repo_global_scan.evaluate_context(ctx, set(core.CANDIDATE_GROUP_SEEDS), current_run_id=100)
        self.assertFalse(bad["repositoryGlobalCollisionSurfaceScanPassed"])

    def test_repository_global_stability_fingerprint_ignores_only_current_run_and_same_run_artifact_metadata(self):
        seed = core.CANDIDATE_SEED_FIRST
        first = self.empty_repository_global_context()
        second = copy.deepcopy(first)
        first["runs"] = [{"id": 99, "status": "queued", "display_title": str(seed)}]
        second["runs"] = [{"id": 99, "status": "in_progress", "display_title": str(seed)}]
        first["artifacts"] = [{"id": 1, "name": "proof", "workflow_run": {"id": 99}}]
        second["artifacts"] = [{"id": 2, "name": "proof", "workflow_run": {"id": 99}}]
        stable = repo_global_scan.require_two_pass_stability(first, second, current_run_id=99)
        self.assertEqual(len(stable), 64)
        second["issueComments"] = [{"id": 7, "body": "new external metadata"}]
        with self.assertRaisesRegex(RuntimeError, "metadata changed between two complete enumerations"):
            repo_global_scan.require_two_pass_stability(first, second, current_run_id=99)

    def test_repository_global_stability_ignores_status_timestamp_and_order_drift(self):
        first = self.empty_repository_global_context()
        second = copy.deepcopy(first)
        seed = core.CANDIDATE_SEED_FIRST
        first["runs"] = [
            {"id": 2, "status": "queued", "updated_at": "2026-01-01T00:00:00Z", "display_title": "safe"},
            {"id": 1, "status": "in_progress", "updated_at": "2026-01-01T00:00:01Z", "display_title": "safe"},
        ]
        second["runs"] = [
            {"id": 1, "status": "completed", "updated_at": "2026-01-01T00:01:00Z", "display_title": "safe"},
            {"id": 2, "status": "completed", "updated_at": "2026-01-01T00:01:01Z", "display_title": "safe"},
        ]
        first["artifacts"] = [{"id": 9, "name": "proof", "created_at": "2026-01-01T00:00:00Z", "workflow_run": {"id": 99}}]
        second["artifacts"] = [{"id": 9, "name": "proof", "created_at": "2026-01-01T00:02:00Z", "workflow_run": {"id": 99}}]
        self.assertEqual(
            repo_global_scan.require_two_pass_stability(first, second, current_run_id=99),
            repo_global_scan.require_two_pass_stability(second, first, current_run_id=99),
        )
        self.assertNotIn(str(seed), json.dumps(repo_global_scan.canonical_collision_context(first, 99), sort_keys=True))

    def test_repository_global_stability_detects_collision_relevant_identity_and_content_changes(self):
        seed = core.CANDIDATE_SEED_FIRST
        cases = []
        for surface, row_a, row_b in (
            ("branches", {"name": "main", "commit": {"sha": "a" * 40}}, {"name": "main", "commit": {"sha": "b" * 40}}),
            ("artifacts", {"id": 1, "name": "proof"}, {"id": 1, "name": str(seed)}),
            ("pulls", {"number": 1, "body": "safe"}, {"number": 1, "body": str(seed)}),
            ("issues", {"number": 2, "body": "safe"}, {"number": 2, "body": str(seed)}),
            ("issueComments", {"id": 3, "body": "safe"}, {"id": 3, "body": str(seed)}),
            ("pullReviewComments", {"id": 4, "body": "safe"}, {"id": 4, "body": str(seed)}),
            ("commitComments", {"id": 5, "body": "safe"}, {"id": 5, "body": str(seed)}),
        ):
            first = self.empty_repository_global_context()
            second = self.empty_repository_global_context()
            first[surface] = [row_a]
            second[surface] = [row_b]
            cases.append((surface, first, second))
        for surface, first, second in cases:
            with self.subTest(surface=surface):
                with self.assertRaisesRegex(RuntimeError, "metadata changed between two complete enumerations"):
                    repo_global_scan.require_two_pass_stability(first, second)

    def test_repository_global_audit_binds_expected_branch_head_not_only_stable_metadata(self):
        ctx = self.empty_repository_global_context()
        ctx["branches"] = [{"name": "main", "commit": {"sha": "a" * 40}}]
        ok = repo_global_scan.evaluate_context(
            ctx, set(core.CANDIDATE_GROUP_SEEDS), audit_mode="review-freeze",
            expected_branch_name="main", expected_repo_head="a" * 40,
        )
        self.assertTrue(ok["auditedBranchHeadMatchesRepositoryHead"])
        stale = repo_global_scan.evaluate_context(
            ctx, set(core.CANDIDATE_GROUP_SEEDS), audit_mode="review-freeze",
            expected_branch_name="main", expected_repo_head="b" * 40,
        )
        self.assertFalse(stale["auditedBranchHeadMatchesRepositoryHead"])
        self.assertEqual(stale["auditedBranchHeadShaObserved"], "a" * 40)

    def test_repository_global_scanner_excludes_current_run_artifact_self_metadata_but_not_other_artifacts(self):
        seed = core.CANDIDATE_SEED_FIRST
        ctx = self.empty_repository_global_context()
        ctx["artifacts"] = [{"id": 1, "name": str(seed), "workflow_run": {"id": 99}}]
        ok = repo_global_scan.evaluate_context(ctx, set(core.CANDIDATE_GROUP_SEEDS), current_run_id=99)
        self.assertTrue(ok["repositoryGlobalCollisionSurfaceScanPassed"])
        bad = repo_global_scan.evaluate_context(ctx, set(core.CANDIDATE_GROUP_SEEDS), current_run_id=100)
        self.assertFalse(bad["repositoryGlobalCollisionSurfaceScanPassed"])

    def test_freeze_refuses_repository_global_seed_proof_without_stable_double_enumeration(self):
        audit = self.full_seed_audit(PKG / "design.review.json")
        audit["repositoryGlobalDoubleEnumerationStable"] = False
        with self.assertRaisesRegex(core.Refusal, "stable double enumeration"):
            core.validate_seed_audit_for_freeze(audit, PKG / "design.review.json", self.design())

    def test_future_evidence_self_ledger_paths_are_predeclared_but_not_required_on_review_head(self):
        ledger = json.loads((PKG / "seed-self-ledger-paths.json").read_text())
        self.assertEqual(ledger["schemaVersion"], 2)
        self.assertIn("evidence/aerosol-family-challenge-v2/manifest.frozen.json", ledger["futureEvidenceSelfLedgerPaths"])
        self.assertIn("experiments/aerosol-family-challenge-v2/design.review.json", ledger["requiredTrackedSelfLedgerPaths"])

    def test_prior_review_proof_artifact_refuses_review_freeze_but_is_allowed_for_authorization_recheck(self):
        ctx = self.empty_repository_global_context()
        ctx["artifacts"] = [{
            "id": 7001,
            "name": "aerosol-family-v2-r6-freeze-proof",
            "workflow_run": {"id": 55},
        }]
        review = repo_global_scan.evaluate_context(
            ctx, set(core.CANDIDATE_GROUP_SEEDS), current_run_id=99,
            stable_double_enumeration_passed=True, stable_context_sha256_value="c" * 64,
            audit_mode="review-freeze",
        )
        self.assertEqual(review["auditMode"], "review-freeze")
        self.assertEqual(review["priorReviewProofArtifactCount"], 1)
        self.assertFalse(review["reviewProofIdentityFresh"])
        auth = repo_global_scan.evaluate_context(
            ctx, set(core.CANDIDATE_GROUP_SEEDS), current_run_id=99,
            stable_double_enumeration_passed=True, stable_context_sha256_value="c" * 64,
            audit_mode="authorization-recheck",
        )
        self.assertEqual(auth["auditMode"], "authorization-recheck")
        self.assertEqual(auth["priorReviewProofArtifactCount"], 1)
        self.assertIsNone(auth["reviewProofIdentityFresh"])
        self.assertTrue(auth["repositoryGlobalCollisionSurfaceScanPassed"])

    def test_freeze_refuses_authorization_recheck_audit_mode(self):
        audit = self.full_seed_audit(PKG / "design.review.json", mode="authorization-recheck")
        with self.assertRaisesRegex(core.Refusal, "fresh review-freeze seed audit"):
            core.validate_seed_audit_for_freeze(audit, PKG / "design.review.json", self.design())

    def test_freeze_refuses_if_permanent_future_evidence_path_already_exists(self):
        audit = self.full_seed_audit(PKG / "design.review.json")
        audit["futureEvidenceSelfLedgerPathsPresent"] = ["evidence/aerosol-family-challenge-v2/freeze-record.json"]
        audit["futureEvidenceSelfLedgerPathCountPresent"] = 1
        with self.assertRaisesRegex(core.Refusal, "preserved freeze evidence"):
            core.validate_seed_audit_for_freeze(audit, PKG / "design.review.json", self.design())

    def test_tracked_self_ledger_policy_allows_absent_future_paths_but_requires_current_paths(self):
        required, future = tree_scan.load_self_ledger_policy(PKG / "seed-self-ledger-paths.json")
        candidate = core.CANDIDATE_SEED_FIRST
        with tempfile.TemporaryDirectory() as td_s:
            td = Path(td_s)
            required_path = next(iter(required))
            rp = td / required_path
            rp.parent.mkdir(parents=True, exist_ok=True)
            rp.write_text(f"seed {candidate}\n", encoding="utf-8")
            file_list = td / "files.nul"
            file_list.write_bytes(required_path.encode() + b"\0")
            partial = tree_scan.scan_with_policy(td, file_list, set(core.CANDIDATE_GROUP_SEEDS), {required_path}, future)
            self.assertTrue(partial["exactHeadTrackedTreeByteScanPassed"])
            self.assertTrue(partial["requiredSelfLedgerPathsPresent"])
            self.assertTrue(partial["futureEvidenceSelfLedgerPathsAbsent"])
            self.assertEqual(partial["futureEvidenceSelfLedgerPathCountPresent"], 0)
            missing = tree_scan.scan_with_policy(td, file_list, set(core.CANDIDATE_GROUP_SEEDS), {required_path, "required/missing.json"}, future)
            self.assertFalse(missing["exactHeadTrackedTreeByteScanPassed"])
            self.assertEqual(missing["missingAllowedSelfLedgerPaths"], ["required/missing.json"])
            future_path = next(iter(future))
            fp = td / future_path
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(f"proof seed {candidate}\n", encoding="utf-8")
            file_list.write_bytes(required_path.encode() + b"\0" + future_path.encode() + b"\0")
            present = tree_scan.scan_with_policy(td, file_list, set(core.CANDIDATE_GROUP_SEEDS), {required_path}, future)
            self.assertTrue(present["exactHeadTrackedTreeByteScanPassed"])
            self.assertEqual(present["trackedTreeExternalCollisionCount"], 0)
            self.assertEqual(present["futureEvidenceSelfLedgerPathCountPresent"], 1)
            self.assertIn(future_path, present["futureEvidenceSelfLedgerPathsPresent"])

    def test_merge_seed_proof_cli_enforces_review_freeze_one_use_and_exact_branch_head(self):
        with tempfile.TemporaryDirectory() as td_s:
            td = Path(td_s)
            tracked = {
                "exactHeadTrackedTreeByteScanPassed": True,
                "trackedFileCount": 50,
                "trackedTreeExternalCollisionCount": 0,
                "futureEvidenceSelfLedgerPathsPresent": [],
                "futureEvidenceSelfLedgerPathCountPresent": 0,
            }
            global_proof = {
                "auditMode": "review-freeze",
                "auditedBranchName": "main",
                "repositoryHeadExpected": "a" * 40,
                "auditedBranchHeadShaObserved": "a" * 40,
                "auditedBranchHeadMatchesRepositoryHead": True,
                "priorReviewProofArtifactCount": 0,
                "reviewProofIdentityFresh": True,
                "reviewProofArtifactName": "aerosol-family-v2-r6-freeze-proof",
                "repositoryGlobalCollisionSurfaceScanPassed": True,
                "repositoryGlobalCollisionCount": 0,
                "repositoryGlobalDoubleEnumerationStable": True,
                "repositoryGlobalEnumerationPassCount": 2,
                "repositoryGlobalStableContextSha256": "d" * 64,
                "currentAuditRunSelfMetadataExclusion": {"runId": 123},
                "allStatePullRequestsInspected": True,
                "allStateIssuesInspected": True,
                "allRepositoryIssueCommentsInspected": True,
                "allRepositoryPullReviewCommentsInspected": True,
                "allRepositoryCommitCommentsInspected": True,
            }
            for key in (
                "branchCountEnumerated", "workflowRunCountEnumerated", "artifactMetadataCountEnumerated",
                "allStatePullRequestCountEnumerated", "allStateIssueCountEnumerated",
                "repositoryIssueCommentCountEnumerated", "repositoryPullReviewCommentCountEnumerated",
                "repositoryCommitCommentCountEnumerated", "issue60CommentCountEnumerated",
            ):
                global_proof[key] = 0
            tp = td / "tracked.json"; gp = td / "global.json"; out = td / "proof.json"
            tp.write_text(json.dumps(tracked)); gp.write_text(json.dumps(global_proof))
            cmd = [
                sys.executable, str(PKG / "merge_seed_proof.py"),
                "--design", str(PKG / "design.review.json"),
                "--candidate-seed-ledger", str(PKG / "candidate-seed-ledger.v1.json"),
                "--tracked", str(tp), "--repository-global", str(gp),
                "--repo-head", "a" * 40, "--source-base-main-sha", core.PUBLIC_REPO_MAIN_SHA,
                "--current-run-id", "123", "--audit-mode", "review-freeze", "--output", str(out),
            ]
            good = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(good.returncode, 0, good.stderr)
            proof = json.loads(out.read_text())
            self.assertEqual(proof["auditMode"], "review-freeze")
            self.assertTrue(proof["auditedBranchHeadMatchesRepositoryHead"])
            self.assertEqual(proof["futureEvidenceSelfLedgerPathCountPresent"], 0)
            global_proof["priorReviewProofArtifactCount"] = 1
            global_proof["reviewProofIdentityFresh"] = False
            gp.write_text(json.dumps(global_proof))
            duplicate = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(duplicate.returncode, 2)
            global_proof["priorReviewProofArtifactCount"] = 0
            global_proof["reviewProofIdentityFresh"] = True
            global_proof["auditedBranchHeadShaObserved"] = "b" * 40
            global_proof["auditedBranchHeadMatchesRepositoryHead"] = False
            gp.write_text(json.dumps(global_proof))
            moved = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(moved.returncode, 2)

    def test_actions_zip_scanner_detects_candidate_seed_bytes(self):
        seed = core.CANDIDATE_SEED_FIRST
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("case-result.json", json.dumps({"seed": seed}))
        hits = artifact_scan.scan_zip(buf.getvalue(), {seed}, {"surface": "test"})
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["seed"], seed)

    def test_review_package_python_has_no_solver_process_execution_primitive(self):
        forbidden = ("subprocess", "os.system", "os.popen", "Popen(", "check_call(", "check_output(")
        for path in PKG.glob("*.py"):
            text = path.read_text(encoding="utf-8")
            for token in forbidden:
                self.assertNotIn(token, text, f"{path.name} contains {token}")

    def _positive_frozen_files(self, td: Path):
        seed_audit = td / "seed-audit.json"
        seed_audit.write_text(core.dump(self.full_seed_audit(PKG / "design.review.json")))
        manifest = td / "manifest.json"
        freeze = td / "freeze.json"
        freeze_mod.freeze(PKG / "design.review.json", PKG / "analysis-contract.v3.json", seed_audit, manifest, freeze)
        return manifest, freeze

    def test_execution_guard_accepts_crn_seed_reuse_only_within_eight_state_groups(self):
        with tempfile.TemporaryDirectory() as td_s:
            td = Path(td_s)
            manifest_path, freeze_path = self._positive_frozen_files(td)
            manifest = json.loads(manifest_path.read_text())
            freeze_record = json.loads(freeze_path.read_text())
            paths = self.transport_paths(manifest_path, freeze_path)
            head = "b" * 40
            parent = "c" * 40
            authorization = self.enabled_authorization(paths, parent, ordinal=999)
            live_seed_audit = self.full_seed_audit(PKG / "design.review.json", mode="authorization-recheck")
            live_seed_audit.update({"repositoryHead": head, "auditedBranchHeadShaObserved": head, "excludedCurrentAuditRunId": 123456})
            pr_number = 77
            identity = self.identity_freshness(999, head, dispatch_exists=True, marker_count=1)
            marker = freshness.authorization_marker(999, head, parent, pr_number)
            context = {
                "githubActions": True,
                "eventName": "push",
                "runAttempt": 1,
                "headSha": head,
                "parentSha": parent,
                "refName": authorization["dispatchBranch"],
                "dispatchBranchHeadSha": head,
                "authorizationHead": head,
                "authorizationCommitParentCount": 1,
                "authorizationCommitChangedPaths": ["experiments/aerosol-family-challenge-v2/authorization.json"],
                "pr": {
                    "number": pr_number,
                    "state": "open",
                    "draft": True,
                    "merged": False,
                    "headSha": head,
                    "headBranch": authorization["authorizationBranch"],
                },
                "authorizationReview": {
                    "status": "AUTHORIZATION_REVIEW_PASS_ZERO_RUNTIME",
                    "headSha": head,
                    "prNumber": pr_number,
                    "runAttempt": 1,
                    "conclusion": "success",
                    "scientificRuntimeSetupPerformed": False,
                    "scientificExecutionPerformed": False,
                },
                "freshness": identity,
                "issue60Markers": [marker],
                "priorRunsOnDispatch": [],
                "priorCaseArtifactNames": [],
                "issue60Comments": [],
                "currentRunId": 123456,
            }
            report = exec_guard.evaluate(
                core, freeze_record, manifest, authorization, live_seed_audit, context, paths,
            )
            self.assertEqual(report["status"], "EXACT_ONE_USE_AEROSOL_FAMILY_V2_DISPATCH_AUTHORIZED")
            self.assertEqual(report["caseCount"], 576)
            self.assertEqual(report["comparisonGroupCount"], 72)
            self.assertFalse(report["authorizationDocumentOwnCommitShaEmbedded"])
            bad_audit = copy.deepcopy(live_seed_audit)
            bad_audit["candidateSeedCanonicalSha256"] = "0" * 64
            with self.assertRaisesRegex(exec_guard.GuardRefusal, "candidate ledger drift"):
                exec_guard.evaluate(core, freeze_record, manifest, authorization, bad_audit, context, paths)

    def test_real_git_one_file_authorization_commit_is_constructible_and_externally_bound(self):
        with tempfile.TemporaryDirectory() as td_s:
            td = Path(td_s)
            manifest_path, freeze_path = self._positive_frozen_files(td)
            repo = td / "repo"
            repo.mkdir()
            paths = self.transport_paths(manifest_path, freeze_path, repo)
            subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True, text=True)
            subprocess.run(["git", "config", "user.name", "Aerosol Review Test"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.email", "aerosol-review@example.invalid"], cwd=repo, check=True)
            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-m", "frozen review transport"], cwd=repo, check=True, capture_output=True, text=True)
            parent = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
            ordinal = 999
            authorization = self.enabled_authorization(paths, parent, ordinal)
            branch = authorization["authorizationBranch"]
            subprocess.run(["git", "switch", "-c", branch], cwd=repo, check=True, capture_output=True, text=True)
            auth_path = repo / "experiments" / "aerosol-family-challenge-v2" / "authorization.json"
            auth_path.write_text(core.dump(authorization), encoding="utf-8")
            subprocess.run(["git", "add", str(auth_path.relative_to(repo))], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-m", "authorize aerosol family v2"], cwd=repo, check=True, capture_output=True, text=True)
            head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
            parent_line = subprocess.check_output(["git", "rev-list", "--parents", "-n", "1", "HEAD"], cwd=repo, text=True).strip().split()
            changed = subprocess.check_output(["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"], cwd=repo, text=True).splitlines()
            self.assertEqual(len(parent_line) - 1, 1)
            self.assertEqual(parent_line[1], parent)
            self.assertEqual(changed, ["experiments/aerosol-family-challenge-v2/authorization.json"])
            self.assertIsNone(authorization["exactAuthorizationCommit"])
            ctx = self.authorization_review_context(authorization, head, parent)
            ctx["parentCount"] = len(parent_line) - 1
            ctx["changedPaths"] = changed
            review = auth_guard.review(authorization, ctx, paths)
            self.assertEqual(review["status"], "AUTHORIZATION_REVIEW_PASS_ZERO_RUNTIME")
            self.assertEqual(review["authorizationHead"], head)
            self.assertEqual(review["authorizationParent"], parent)
            embedded = copy.deepcopy(authorization)
            embedded["exactAuthorizationCommit"] = head
            with self.assertRaisesRegex(auth_guard.AuthorizationRefusal, "must not embed own commit SHA"):
                auth_guard.review(embedded, ctx, paths)

    def test_dispatch_guard_requires_zero_runtime_review_and_exact_control_marker(self):
        with tempfile.TemporaryDirectory() as td_s:
            td = Path(td_s)
            manifest_path, freeze_path = self._positive_frozen_files(td)
            paths = self.transport_paths(manifest_path, freeze_path)
            head = "d" * 40
            parent = "e" * 40
            ordinal = 999
            pr_number = 77
            authorization = self.enabled_authorization(paths, parent, ordinal)
            base_ctx = {
                "authorizationHead": head,
                "authorizationParent": parent,
                "liveMain": parent,
                "pr": {"number": pr_number, "state": "open", "draft": True, "merged": False, "headBranch": authorization["authorizationBranch"], "headSha": head},
                "authorizationReview": {"status": "AUTHORIZATION_REVIEW_PASS_ZERO_RUNTIME", "headSha": head, "prNumber": pr_number, "runAttempt": 1, "conclusion": "success", "scientificRuntimeSetupPerformed": False, "scientificExecutionPerformed": False},
                "freshness": self.identity_freshness(ordinal, head, dispatch_exists=False, marker_count=1),
                "issue60Markers": [],
            }
            with self.assertRaisesRegex(auth_guard.AuthorizationRefusal, "exactly one exact Issue #60 authorization marker required"):
                dispatch_guard.evaluate(authorization, base_ctx, paths)
            marker = freshness.authorization_marker(ordinal, head, parent, pr_number)
            base_ctx["issue60Markers"] = [marker]
            eligible = dispatch_guard.evaluate(authorization, base_ctx, paths)
            self.assertEqual(eligible["status"], "DISPATCH_ELIGIBLE_NOT_CREATED")
            post = copy.deepcopy(base_ctx)
            post["freshness"] = self.identity_freshness(ordinal, head, dispatch_exists=True, marker_count=1)
            post["dispatchBranchHeadSha"] = head
            transitioned = dispatch_guard.evaluate(authorization, post, paths, post_dispatch=True)
            self.assertEqual(transitioned["status"], "DISPATCH_TRANSITION_VALID")

    def test_positive_candidate_claim_parser_ignores_review_prose_but_detects_real_allocation(self):
        ordinal = 999
        self.assertEqual(freshness.positive_candidate_claims("No ordinal 999 allocation exists; review only.", ordinal), [])
        self.assertEqual(freshness.positive_candidate_claims("Would we allocate ordinal 999 after review?", ordinal), [])
        self.assertEqual(freshness.positive_candidate_claims("> We allocated ordinal 999\n```\nwe allocated ordinal 999\n```", ordinal), [])
        claims = freshness.positive_candidate_claims("Ordinal 998 was consumed; we now allocated ordinal 999.", ordinal)
        self.assertEqual(len(claims), 1)
        marker = freshness.authorization_marker(ordinal, "a" * 40, "b" * 40, 7)
        self.assertEqual(freshness.positive_candidate_claims(marker, ordinal), [marker])

    def test_authorization_review_workflow_is_zero_runtime_and_hard_disabled(self):
        text = (PKG / "execution-candidate/authorization-review-workflow.yml.template").read_text()
        self.assertIn("pull_request:", text)
        self.assertIn("types: [opened]", text)
        self.assertIn("if: ${{ false }}", text)
        self.assertIn("exit 2", text)
        self.assertNotIn("uvspec", text.lower())
        self.assertNotIn("libRadtran", text)

    def test_r6_transport_contract_forbids_self_embedded_authorization_head_and_requires_stable_proof(self):
        contract = json.loads((PKG / "execution-candidate/transport-contract.v3.json").read_text())
        self.assertTrue(contract["authorizationDocumentMustNotEmbedOwnCommitSha"])
        self.assertTrue(contract["authorizationParentBoundInsideDocument"])
        self.assertIn("EXTERNAL_GIT_COMMIT_METADATA", contract["authorizationHeadBindingMode"])
        self.assertTrue(contract["authorizationBoundary"]["authorizationReviewScientificExecutionForbidden"])
        self.assertTrue(contract["authorizationBoundary"]["seedFreshnessAllStatePullRequestsRequired"])
        self.assertTrue(contract["authorizationBoundary"]["seedFreshnessAllStateIssuesRequired"])
        self.assertEqual(contract["schemaVersion"], 3)
        self.assertTrue(contract["authorizationBoundary"]["seedFreshnessRepositoryGlobalDoubleEnumerationRequired"])
        self.assertTrue(contract["reviewSeedProofLifecycle"]["workflowDispatchRequiresWorkflowOnDefaultBranch"])
        self.assertEqual(contract["reviewSeedProofLifecycle"]["repositoryGlobalCompleteEnumerationPassesRequired"], 2)
        self.assertTrue(contract["reviewSeedProofLifecycle"]["followupEvidenceOnlyPreservationCommitRequiredBeforeAuthorization"])
        self.assertTrue(contract["reviewSeedProofLifecycle"]["workflowRunAttemptExactly1Required"])
        self.assertEqual(contract["reviewSeedProofLifecycle"]["reviewFreezeAuditModeRequired"], "review-freeze")
        self.assertTrue(contract["reviewSeedProofLifecycle"]["priorReviewProofArtifactCountMustBeZero"])
        self.assertTrue(contract["reviewSeedProofLifecycle"]["exactDefaultBranchHeadMustEqualWorkflowDispatchSha"])
        self.assertEqual(contract["authorizationBoundary"]["authorizationTimeSeedAuditModeRequired"], "authorization-recheck")
        self.assertTrue(contract["authorizationBoundary"]["authorizationTimeAuditMustObserveExactAuthorizationBranchHead"])

    def test_r6_review_seed_workflow_is_attempt1_review_freeze_and_persists_frozen_proof(self):
        text = (PKG / "review-seed-proof-workflow.yml.template").read_text()
        self.assertIn('test "$GITHUB_RUN_ATTEMPT" = "1"', text)
        self.assertEqual(text.count("--audit-mode review-freeze"), 2)
        self.assertIn('--expected-branch-name "$GITHUB_REF_NAME"', text)
        self.assertIn('--expected-repo-head "$GITHUB_SHA"', text)
        self.assertIn("aerosol-family-v2-r6-freeze-proof", text)
        self.assertIn("freeze.py", text)
        self.assertIn("manifest.frozen.json", text)
        self.assertIn("freeze-record.json", text)
        self.assertIn("actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1", text)
        self.assertIn("actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a", text)

    def test_only_transport_v3_is_active_and_v2_is_superseded_reference(self):
        root = PKG / "execution-candidate"
        self.assertTrue((root / "transport-contract.v3.json").is_file())
        self.assertFalse((root / "transport-contract.v2.json").exists())
        self.assertTrue((root / "reference/superseded-pre-result/transport-contract.v2.json").is_file())

    def test_execution_guard_refuses_review_freeze_audit_as_authorization_recheck(self):
        with tempfile.TemporaryDirectory() as td_s:
            td = Path(td_s)
            manifest_path, freeze_path = self._positive_frozen_files(td)
            manifest = json.loads(manifest_path.read_text())
            freeze_record = json.loads(freeze_path.read_text())
            paths = self.transport_paths(manifest_path, freeze_path)
            head = "b" * 40
            parent = "c" * 40
            ordinal = 999
            authorization = self.enabled_authorization(paths, parent, ordinal=ordinal)
            live_seed_audit = self.full_seed_audit(PKG / "design.review.json", mode="review-freeze")
            live_seed_audit.update({"repositoryHead": head, "auditedBranchHeadShaObserved": head, "excludedCurrentAuditRunId": 123456})
            pr_number = 77
            marker = freshness.authorization_marker(ordinal, head, parent, pr_number)
            context = {
                "githubActions": True, "eventName": "push", "runAttempt": 1,
                "headSha": head, "parentSha": parent, "refName": authorization["dispatchBranch"],
                "dispatchBranchHeadSha": head, "authorizationHead": head,
                "authorizationCommitParentCount": 1,
                "authorizationCommitChangedPaths": ["experiments/aerosol-family-challenge-v2/authorization.json"],
                "pr": {"number": pr_number, "state": "open", "draft": True, "merged": False, "headSha": head, "headBranch": authorization["authorizationBranch"]},
                "authorizationReview": {"status": "AUTHORIZATION_REVIEW_PASS_ZERO_RUNTIME", "headSha": head, "prNumber": pr_number, "runAttempt": 1, "conclusion": "success", "scientificRuntimeSetupPerformed": False, "scientificExecutionPerformed": False},
                "freshness": self.identity_freshness(ordinal, head, dispatch_exists=True, marker_count=1),
                "issue60Markers": [marker], "priorRunsOnDispatch": [], "priorCaseArtifactNames": [],
                "issue60Comments": [], "currentRunId": 123456,
            }
            with self.assertRaisesRegex(exec_guard.GuardRefusal, "authorization-recheck mode"):
                exec_guard.evaluate(core, freeze_record, manifest, authorization, live_seed_audit, context, paths)

    def test_disabled_authorization_template_refuses_execution_guard(self):
        with tempfile.TemporaryDirectory() as td_s:
            td = Path(td_s)
            manifest_path, freeze_path = self._positive_frozen_files(td)
            manifest = json.loads(manifest_path.read_text())
            freeze_record = json.loads(freeze_path.read_text())
            auth = json.loads((PKG / "execution-candidate/authorization.template.json").read_text())
            dummy = td / "dummy"; dummy.write_text("x")
            with self.assertRaises(exec_guard.GuardRefusal):
                exec_guard.evaluate(
                    core, freeze_record, manifest, auth, {}, {},
                    {"manifest": manifest_path, "freeze": freeze_path, "transport": dummy, "adapter": dummy, "executor": dummy, "workflow": dummy},
                )

    def test_review_only_governance_modules_have_no_process_execution_primitive(self):
        forbidden = ("subprocess", "os.system", "os.popen", "Popen(", "check_call(", "check_output(")
        for rel in (
            "execution-candidate/freshness.py",
            "execution-candidate/authorization_guard.py",
            "execution-candidate/dispatch_guard.py",
            "execution-candidate/guard.py",
        ):
            text = (PKG / rel).read_text(encoding="utf-8")
            for token in forbidden:
                self.assertNotIn(token, text, f"{rel} contains {token}")

    def test_execution_candidate_fake_runner_calls_exactly_one_syntax_and_one_solver_and_saves_full_raw_evidence(self):
        with tempfile.TemporaryDirectory() as td_s:
            td = Path(td_s)
            # A real freeze is not needed here; executor consumes the already-authorized guard report.
            manifest = core.build_manifest(self.design())
            manifest_path = td / "manifest.json"
            manifest_path.write_text(core.dump(manifest))
            guard_path = td / "guard.json"
            guard_path.write_text(json.dumps({
                "status": "EXACT_ONE_USE_AEROSOL_FAMILY_V2_DISPATCH_AUTHORIZED",
                "solverExecutionPermittedNow": True,
                "manifestRawSha256": core.raw_sha256(manifest_path),
            }))
            runtime = manifest["sourceBindings"]["runtimeLock"]
            runtime_path = td / "runtime.json"
            runtime_path.write_text(json.dumps({
                "uvspecSha256": runtime["uvspecSha256"],
                "uvspecHelpSha256": runtime["uvspecHelpSha256"],
                "libRadtranDataTreeSha256": runtime["libRadtranDataTreeSha256"],
                "atmosphereSha256": runtime["atmosphereSha256"],
                "runtimeLockRawSha256": runtime["rawSha256"],
                "scientificSolverExecuted": False,
            }))
            uvspec = td / "uvspec"; uvspec.write_text("dummy executable bytes")
            calls = []
            def fake_runner(command, text, cwd, timeout):
                calls.append(list(command))
                if len(command) == 1:
                    spectrum = "".join(f"{380.0 + i*0.05:.2f} 1.0\n" for i in range(8001))
                    std = "".join(f"{380.0 + i*0.05:.2f} 0.1\n" for i in range(8001))
                    (cwd / "mc.rad.spc").write_text(spectrum)
                    (cwd / "mc.rad.std.spc").write_text(std)
                    (cwd / "mc.flx.spc").write_text("raw flux\n")
                    (cwd / "mc.flx.std.spc").write_text("raw flux std\n")
                return {"exitCode": 0, "timedOut": False, "stdout": "ok", "stderr": ""}
            original_sha = exec_mod._sha
            def test_sha(path):
                if Path(path) == uvspec:
                    return runtime["uvspecSha256"]
                return original_sha(Path(path))
            exec_mod._sha = test_sha
            try:
                result = exec_mod.execute_case(
                    ROOT, manifest_path, guard_path, runtime_path, manifest["cases"][0]["caseId"],
                    td / "data", td / "outputs", uvspec, allow_execution=True, runner=fake_runner,
                )
            finally:
                exec_mod._sha = original_sha
            self.assertEqual(len(calls), 2)
            self.assertEqual(calls[0], [str(uvspec), "-c"])
            self.assertEqual(calls[1], [str(uvspec)])
            self.assertEqual(result["syntaxCheckCount"], 1)
            self.assertEqual(result["solverExecutionCount"], 1)
            self.assertEqual(result["rawOutputNodeCount"], 8001)
            self.assertEqual(result["workflowRunAttempt"], 1)
            self.assertEqual(result["caseInpSha256"], core.raw_sha256(td / "outputs" / manifest["cases"][0]["caseId"] / "case.inp"))
            self.assertFalse(result["marginalMcStdDiagnostics"]["pairedContrastUncertaintyUsePermitted"])
            case_dir = td / "outputs" / manifest["cases"][0]["caseId"]
            contract = json.loads((PKG / "execution-candidate/transport-contract.v3.json").read_text())
            for name in contract["perCase"]["requiredMembers"]:
                self.assertTrue((case_dir / name).is_file(), name)
            self.assertEqual(result["runtimeReportRawSha256"], core.raw_sha256(case_dir / "runtime-report.json"))
            self.assertEqual(result["radianceOutputSha256"], core.raw_sha256(case_dir / "mc.rad.spc"))
            self.assertEqual(result["stdRadianceOutputSha256"], core.raw_sha256(case_dir / "mc.rad.std.spc"))

    def test_executor_refuses_runtime_report_that_is_not_explicitly_pre_solver(self):
        with tempfile.TemporaryDirectory() as td_s:
            td = Path(td_s)
            manifest = core.build_manifest(self.design())
            manifest_path = td / "manifest.json"
            manifest_path.write_text(core.dump(manifest))
            guard_path = td / "guard.json"
            guard_path.write_text(json.dumps({"status": "EXACT_ONE_USE_AEROSOL_FAMILY_V2_DISPATCH_AUTHORIZED", "solverExecutionPermittedNow": True, "manifestRawSha256": core.raw_sha256(manifest_path)}))
            runtime = manifest["sourceBindings"]["runtimeLock"]
            runtime_path = td / "runtime.json"
            runtime_path.write_text(json.dumps({
                "uvspecSha256": runtime["uvspecSha256"],
                "uvspecHelpSha256": runtime["uvspecHelpSha256"],
                "libRadtranDataTreeSha256": runtime["libRadtranDataTreeSha256"],
                "atmosphereSha256": runtime["atmosphereSha256"],
                "runtimeLockRawSha256": runtime["rawSha256"],
                "scientificSolverExecuted": True,
            }))
            uvspec = td / "uvspec"
            uvspec.write_text("dummy")
            with self.assertRaisesRegex(exec_mod.ExecutionRefusal, "must be pre-solver"):
                exec_mod.execute_case(
                    ROOT, manifest_path, guard_path, runtime_path, manifest["cases"][0]["caseId"],
                    td / "data", td / "outputs", uvspec, allow_execution=True,
                    runner=lambda *args, **kwargs: self.fail("runner must not be reached"),
                )

    def test_execution_workflow_candidate_is_hard_disabled(self):
        text = (PKG / "execution-candidate/workflow.yml.template").read_text()
        self.assertIn("if: ${{ false }}", text)
        self.assertIn("exit 2", text)
        self.assertNotIn("--allow-execution", text)

    def test_workflow_template_is_review_only_and_does_not_invoke_uvspec(self):
        text = (PKG / "review-seed-proof-workflow.yml.template").read_text()
        self.assertIn("REVIEW-ONLY TEMPLATE", text)
        self.assertNotIn("uvspec", text.lower().replace("cannot invoke uvspec", ""))
        self.assertIn("actions: read", text)
        self.assertIn("--candidate-seed-ledger", text)
        self.assertIn("--current-run-id", text)
        self.assertNotIn("--first", text)
        self.assertNotIn("--last", text)
        self.assertIn("Freeze preregistration bytes before any solver", text)
        self.assertIn("aerosol-family-v2-r6-freeze-proof", text)
        self.assertIn("actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a", text)
        self.assertIn("actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1", text)
        self.assertIn("manifest.frozen.json", text)
        self.assertIn("freeze-record.json", text)


if __name__ == "__main__":
    unittest.main()
