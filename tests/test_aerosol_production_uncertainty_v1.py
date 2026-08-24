import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "review/aerosol-production-uncertainty-v1/policy.review.json"


class AerosolProductionUncertaintyV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = json.loads(POLICY.read_text())

    def test_review_is_fail_closed_and_allocates_no_ordinal(self):
        p = self.policy
        self.assertEqual(p["status"], "REVIEW_ONLY_POLICY_NOT_PRODUCTION_AUTHORIZED")
        gate = p["nextScientificExperimentGate"]
        self.assertFalse(gate["scientificOrdinalRequested"])
        self.assertFalse(gate["ordinal39Allocated"])
        self.assertFalse(gate["solverExecutionAuthorized"])
        auth = p["authorization"]
        self.assertTrue(all(value is False for value in auth.values()))

    def test_exact_verified_reports_are_bound(self):
        src = self.policy["sourceBindings"]
        self.assertEqual(src["exactReviewParentMain"], "0ee03dd09ca732a6fefe635291880d33cd4a0a97")
        self.assertEqual(src["aopsOrdinal37Report"]["gitBlobSha1"], "c7a58d8d7ac0ee2a6f1acbf9368df09b881bbd66")
        self.assertEqual(src["afpfOrdinal38Report"]["gitBlobSha1"], "2aac443d60893832c1867657ecd50d9703782ac3")

    def test_policy_forbids_unjustified_probability_or_single_family_selection(self):
        q = self.policy["productionUncertaintyPolicy"]
        self.assertEqual(q["defaultRepresentationWhenAerosolFamilyIsNotIndependentlyValidated"], "SET_VALUED_SCENARIO_ENVELOPE")
        self.assertFalse(q["probabilityWeightedEnsembleAllowedWithoutExternallyValidatedPrior"])
        self.assertFalse(q["equalWeightingOfScenarioStatesAllowed"])
        self.assertFalse(q["singleBestAerosolFamilySelectionFromAodAloneAllowed"])
        self.assertFalse(q["silentCollapseToCurrentBaselineAllowed"])
        self.assertFalse(q["controlledAopsConstantSsaGStatesMayDefineProductionClimatology"])

    def test_candidate_review_support_is_exact_afpf_five_state_universe(self):
        self.assertEqual(
            self.policy["productionUncertaintyPolicy"]["candidateScenarioStatesForReview"],
            [
                "native-rural-ss",
                "opac-continental-average",
                "opac-maritime-clean",
                "opac-desert",
                "opac-desert-spheroids",
            ],
        )

    def test_no_universal_aerosol_or_clock_time_correction(self):
        e = self.policy["frozenEvidenceImplications"]
        self.assertFalse(e["aod550AloneSufficientForAerosolOpticalState"])
        self.assertFalse(e["universalPhaseFunctionCorrectionSupported"])
        self.assertFalse(e["universalParticleShapeCorrectionSupported"])
        self.assertFalse(e["universalAerosolToClockMinutesCorrectionSupported"])
        c = self.policy["productionUncertaintyPolicy"]["clockMinuteConversion"]
        self.assertFalse(c["universalConversionAllowed"])
        self.assertTrue(c["requiresActualDateLocationSolarDepressionRate"])

    def test_activation_requirements_remain_explicitly_unresolved(self):
        r = self.policy["activationRequirements"]
        self.assertTrue(r)
        self.assertTrue(all(value is False for value in r.values()))


if __name__ == "__main__":
    unittest.main()
