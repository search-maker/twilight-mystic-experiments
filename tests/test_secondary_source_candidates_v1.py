import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "review" / "empirical-twilight-radiance-source-admission-v1" / "SECONDARY_SOURCE_CANDIDATES.review.json"


class SecondarySourceCandidatesV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(PATH.read_text(encoding="utf-8"))

    def test_no_target_values_or_fallback_opening(self):
        self.assertFalse(self.doc["targetRadianceOpened"])
        self.assertTrue(self.doc["interpretation"]["noFallbackSourceAdmittedYet"])
        self.assertFalse(self.doc["interpretation"]["mayOpenFallbackTargetValuesNow"])
        self.assertFalse(self.doc["interpretation"]["maySwitchSourceAfterSeeingIzanaResiduals"])
        self.assertTrue(all(value is False for value in self.doc["authorization"].values()))

    def test_jeonju_is_dual_archive_but_not_strictly_admitted(self):
        row = next(c for c in self.doc["candidates"] if c["candidateId"].startswith("jeonju"))
        self.assertTrue(row["publicArchive"]["dualSpectrometerArchivePresence"])
        self.assertFalse(row["calibrationMetadataFinding"]["spectrometer2FinishedAbsoluteRadianceCalibrationProven"])
        self.assertFalse(row["externalAtmosphereFinding"]["sufficientForCurrentStrictAodContract"])
        self.assertFalse(row["siteElevation"]["exactPandoraSiteElevationFrozen"])

    def test_aod_favorable_candidates_do_not_invent_public_s2(self):
        for candidate_id in (
            "seoul-ku-pandora235-aeronet-favorable",
            "yongin-pandora232-aeronet-favorable",
        ):
            row = next(c for c in self.doc["candidates"] if c["candidateId"] == candidate_id)
            self.assertFalse(row["publicArchive"]["dualSpectrometerArchivePresence"])
            self.assertIsNone(row["publicArchive"]["spectrometer2DirectorySurfaced"])


if __name__ == "__main__":
    unittest.main()
