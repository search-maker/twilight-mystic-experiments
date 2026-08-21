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
FREEZE = ROOT / "evidence" / STAGE / "review-freeze.json"


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
        self.assertFalse(self.f["candidateSeedsAllocated"])
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
        self.assertFalse(self.f["scientificExecutionAuthorized"])
        self.assertFalse(self.f["solverExecutionAuthorized"])
        self.assertFalse(self.f["resultOpeningAuthorized"])


if __name__ == "__main__":
    unittest.main()
