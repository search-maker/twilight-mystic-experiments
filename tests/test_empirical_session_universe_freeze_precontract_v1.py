import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "review" / "empirical-twilight-radiance-source-admission-v1" / "SESSION_UNIVERSE_FREEZE_PRECONTRACT.review.json"


class EmpiricalSessionUniverseFreezePrecontractV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(PATH.read_text(encoding="utf-8"))

    def test_session_is_astronomical_transition_not_high_cadence_row(self):
        session = self.doc["sessionDefinition"]
        self.assertEqual(session["id"], "ASTRONOMICAL_TWILIGHT_TRANSITION_SESSION_V1")
        self.assertFalse(session["rowsFromSameDawnOrDuskAreIndependentSessions"])
        self.assertEqual(session["dawnAndDuskOnSameCivilDate"], "separate sessions")
        self.assertFalse(session["sessionGroupingMayUseRadianceValues"])

    def test_complete_metadata_eligible_universe_is_kept(self):
        rule = self.doc["completeUniverseRule"]
        self.assertTrue(rule["includeEveryMetadataEligibleSessionInAdmittedAcquisitionWindows"])
        self.assertFalse(rule["capAtFortySessions"])
        self.assertEqual(rule["minimumIndependentSessionsForTerminalPass"], 40)
        self.assertFalse(rule["replaceFailedOrMissingSessionAfterTargetOpening"])
        self.assertFalse(rule["dropOutlierSessionAfterTargetOpening"])
        self.assertFalse(rule["dropSessionBecauseOneChannelDisagrees"])

    def test_target_values_are_forbidden_in_preopening_manifest(self):
        manifest = self.doc["metadataManifestPerRow"]
        self.assertEqual(manifest["targetSpectralArray"], "FORBIDDEN_PREOPENING")
        self.assertEqual(manifest["derivedPhotopicScotopicJohnsonVFromTarget"], "FORBIDDEN_PREOPENING")
        self.assertEqual(manifest["modelResidual"], "FORBIDDEN_PREOPENING")
        integrity = self.doc["objectIntegrity"]
        self.assertFalse(integrity["mayInspectTargetArrayBeforeHashingDownloadedObject"])

    def test_s2_johnson_v_and_full_three_channel_lanes_are_separate(self):
        lanes = self.doc["sourceLanes"]
        self.assertFalse(lanes["pandora209s2JohnsonVPartial"]["s1PairingRequired"])
        self.assertFalse(lanes["pandora209s2JohnsonVPartial"]["fullThreeChannelClaimAllowed"])
        self.assertTrue(lanes["pandora209FullThreeChannel"]["s1s2PairingAndDirectionalCompatibilityRequired"])
        self.assertTrue(all(value is False for value in self.doc["authorization"].values()))


if __name__ == "__main__":
    unittest.main()
