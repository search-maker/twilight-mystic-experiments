import json
import math
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "review/native-stellar-zenith-v3/ZENITH_EPSILON_SELECTION_RESULT_V1.json"


class NativeStellarZenithEpsilonSelectionResultV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = json.loads(RESULT.read_text(encoding="utf-8"))

    def test_source_and_protocol_identity(self):
        d = self.d
        self.assertEqual(d["status"], "NO_SELECTION_UNDER_PREREGISTERED_PROTOCOL")
        self.assertEqual(d["sourceDiagnostic"]["runId"], 33036341965)
        self.assertEqual(d["sourceDiagnostic"]["artifactId"], 9632148364)
        self.assertEqual(d["sourceDiagnostic"]["solverInvocationCount"], 76)
        self.assertEqual(d["sourceDiagnostic"]["largestSourceZenithAngleRejectedByAnyCornerDeg"], 0.05)
        self.assertEqual(d["selector"]["safetyFactorAboveLargestRejectedSza"], 1.25)
        self.assertEqual(d["selector"]["maxRelativePlaneParallelAirmassExcess"], 1e-7)
        self.assertEqual(d["selector"]["maxAbsDeltaAvMag"], 1e-4)
        self.assertEqual(d["selector"]["requiredSafetyMarginSzaDeg"], 0.0625)

    def test_candidate_airmass_values_are_recomputed_not_asserted_only(self):
        d = self.d
        self.assertEqual(d["allCornerUsableSourceZenithAngleDeg"], [0.1, 0.5, 1.0])
        for row in d["candidateEvaluations"]:
            sza = float(row["sourceZenithAngleDeg"])
            recomputed = 1.0 / math.cos(math.radians(sza)) - 1.0
            self.assertAlmostEqual(
                row["relativePlaneParallelAirmassExcessVsExactVertical"],
                recomputed,
                places=15,
            )
            self.assertEqual(row["passesAirmassBound"], recomputed <= 1e-7)
            self.assertFalse(row["eligible"])
        self.assertTrue(all(row["passesSafetyMargin"] for row in d["candidateEvaluations"]))
        self.assertTrue(all(not row["passesAirmassBound"] for row in d["candidateEvaluations"]))
        self.assertIsNone(d["selected"])

    def test_claim_boundary_remains_closed(self):
        decision = self.d["decision"]
        for key in (
            "epsilonSubstitutionForPhysicalZenithAuthorized",
            "postResultThresholdRelaxationAuthorized",
            "protectedHoldoutOpeningAuthorized",
            "modelFitAuthorized",
            "acceptanceGateEvaluationAuthorized",
            "productionAuthorized",
            "empiricalRealSkyValidationClaimAuthorized",
            "humanFirstSeeingValidationClaimAuthorized",
        ):
            self.assertIs(decision[key], False)


if __name__ == "__main__":
    unittest.main()
