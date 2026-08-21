from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
STAGE = "aerosol-optical-property-sensitivity-v1"
PROTOCOL = ROOT / "experiments" / STAGE / "protocol.review.json"
REVIEW = ROOT / "experiments" / STAGE / "SCIENTIFIC_REVIEW.md"
FREEZE = ROOT / "evidence" / STAGE / "review-freeze.json"


def git_blob_sha1(path: Path) -> str:
    import hashlib
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


class AerosolOpticalPropertySensitivityV1ReviewTests(unittest.TestCase):
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
        self.assertFalse(self.f["afc2R8Modified"])
        self.assertFalse((ROOT / "experiments" / STAGE / "authorization.json").exists())

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
        self.assertFalse(self.f["scientificExecutionAuthorized"])
        self.assertFalse(self.f["solverExecutionAuthorized"])
        self.assertFalse(self.f["resultOpeningAuthorized"])


if __name__ == "__main__":
    unittest.main()
