import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "review" / "empirical-twilight-radiance-source-admission-v1" / "SET_VALUED_ACCEPTANCE_GATES.review.json"


class EmpiricalSetValuedAcceptanceGatesV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(PATH.read_text(encoding="utf-8"))

    def test_thresholds_inherit_preopening_0074_budget(self):
        prior = self.doc["priorBudgetEvidence"]
        self.assertFalse(prior["protectedRadianceWasOpenedWhenThresholdsChosen"])
        self.assertTrue(prior["thresholdsWereNotRetunedOnMeasuredResiduals"])
        gates = self.doc["numericPassFailGates"]
        self.assertEqual(gates["perChannelEqualSessionP95OfSessionMeanConservativeSetMissMagMaximum"], 0.20)
        self.assertEqual(gates["worstPreregisteredMarginalStratumChannelP90ConservativeSetMissMagMaximum"], 0.25)
        self.assertEqual(gates["maximumSingleObservationChannelConservativeSetMissMagMaximum"], 0.60)
        self.assertEqual(gates["biasGate"]["maximum"], 0.12)
        self.assertEqual(gates["externalSigmaLogMaximumPerObservationChannel"], 0.06)

    def test_uncertainty_is_not_subtracted_from_the_primary_error_gate(self):
        metric = self.doc["perObservationPrimaryMetric"]
        self.assertIn("certifiedUpperCentralSetMissLog", metric["conservativeSetMissMag"])
        self.assertIn("externalSigmaLog", metric["conservativeSetMissMag"])
        self.assertIn("would subtract uncertainty", metric["reasonMeasurementIntervalIsNotPrimaryGate"])
        excluded = "\n".join(metric["externalSigmaLog"]["excludeToAvoidDoubleCounting"])
        self.assertIn("AOD550", excluded)
        self.assertIn("aerosol-family", excluded)

    def test_scenario_set_remains_nonprobabilistic(self):
        model_set = self.doc["modelSetDefinition"]
        self.assertFalse(model_set["aerosolFamilyProbabilityWeightsAllowed"])
        self.assertFalse(model_set["aodProbabilityWeightsAllowed"])
        self.assertFalse(model_set["singleFamilySelectionFromAodAloneAllowed"])
        self.assertFalse(model_set["fitFamilyOrAodToMeasuredRadianceAllowed"])
        self.assertTrue(model_set["nearestModelSetMemberMayBeUsedForSetDistance"])
        self.assertFalse(model_set["numericPartitionMayAdaptToMeasuredRadiance"])

    def test_session_first_and_claim_scopes_are_explicit(self):
        agg = self.doc["sessionFirstAggregation"]
        self.assertEqual(agg["minimumIndependentSessionsForAnyTerminalEmpiricalPass"], 40)
        self.assertFalse(agg["rowWeightedPrimaryAggregateAllowed"])
        claims = self.doc["claimScopes"]
        self.assertEqual(claims["johnsonVOnlyS2PartialPass"]["allowedLabel"], "PARTIAL_EMPIRICAL_REAL_SKY_JOHNSON_V_ONLY_PASS")
        self.assertFalse(claims["johnsonVOnlyS2PartialPass"]["mayBeDescribedAsFullLevelBRealSkyValidation"])
        self.assertFalse(claims["fullFrozenDomainEmpiricalPass"]["izanaAloneCanSatisfy"])

    def test_target_opening_and_retuning_remain_forbidden(self):
        self.assertFalse(self.doc["targetRadianceOpened"])
        terminal = self.doc["terminalSemantics"]
        self.assertTrue(terminal["noPostOpeningSessionReplacement"])
        self.assertTrue(terminal["noPostOpeningThresholdChange"])
        self.assertTrue(terminal["noPostOpeningFamilyOrAodFit"])
        self.assertFalse(terminal["failedSessionsMayTrainOrRetuneCurrentModel"])
        self.assertTrue(all(value is False for value in self.doc["authorization"].values()))


if __name__ == "__main__":
    unittest.main()
