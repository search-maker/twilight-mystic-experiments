from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "integration" / "twilight-observation-v1"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validator = load("validator", PACKAGE / "observation_validator.py")
calibration = load("calibration", PACKAGE / "calibration.py")
visibility = load("visibility", PACKAGE / "visibility_api.py")


class ObservationIntegrationTests(unittest.TestCase):
    def record(self):
        return {
            "schemaVersion": 1,
            "stageId": "twilight-observation-v1",
            "observationId": "obs-001",
            "sessionId": "session-001",
            "observerPseudonym": "observer-001",
            "timestampUtc": "2026-08-03T20:00:00Z",
            "location": {
                "latitudeDeg": 40.7,
                "longitudeDeg": -73.9,
                "observerElevationM": 10,
                "horizontalAccuracyM": 5,
            },
            "pointing": {
                "altitudeDeg": 30,
                "azimuthDeg": 90,
                "angularRadiusDeg": 1,
                "sunDepressionDeg": 6,
                "relativeSolarAzimuthDeg": 180,
            },
            "atmosphere": {
                "cloudFraction": 0,
                "aod550": 0.15,
                "aodSource": "instrument",
                "waterVaporCm": 2.0,
            },
            "quality": {"usable": True, "exclusionReasons": []},
            "source": {
                "instrumentType": "sqm",
                "calibrationId": "cal-001",
                "rawFileSha256": ["a" * 64],
            },
        }

    def test_observation_validates_and_gets_session_split(self):
        result = validator.validate(self.record(), "frozen-salt", 0.2)
        self.assertEqual(result["status"], "VALIDATED")
        self.assertIn(result["datasetRole"], {"calibration", "validation"})

    def test_same_session_never_leaks_roles(self):
        first = validator.validate(self.record(), "frozen-salt", 0.2)
        second_record = self.record()
        second_record["observationId"] = "obs-002"
        second = validator.validate(second_record, "frozen-salt", 0.2)
        self.assertEqual(first["datasetRole"], second["datasetRole"])

    def test_instrument_requires_raw_hash(self):
        record = self.record()
        record["source"]["rawFileSha256"] = []
        with self.assertRaises(validator.ObservationRefusal):
            validator.validate(record, "salt", 0.2)

    def test_camera_calibration_dark_subtracts(self):
        result = calibration.calibrated_camera_radiance(
            {
                "modelType": "dark-subtracted-linear-radiance-v1",
                "calibrationId": "cal-1",
                "spectralBandId": "green",
                "darkCountsPerSecond": 10,
                "radiancePerCountPerSecond": 0.01,
            },
            {
                "exposureSeconds": 2,
                "meanCounts": 220,
                "relativeStandardError": 0.05,
            },
        )
        self.assertAlmostEqual(result["radiance"], 1.0)

    def test_sqm_uses_explicit_zero_point(self):
        result = calibration.calibrated_sqm_luminance(
            {
                "modelType": "sqm-log-luminance-v1",
                "calibrationId": "cal-2",
                "zeroPointCdM2": 100000,
                "magnitudeOffset": 0,
            },
            {"sqmMagPerArcsec2": 20, "magnitudeStandardError": 0.1},
        )
        self.assertGreater(result["photopicLuminanceCdM2"], 0)
        self.assertGreater(result["logStandardError"], 0)

    def request(self, star, background):
        return {
            "schemaVersion": 1,
            "stageId": "twilight-observation-v1",
            "apiVersion": "visibility-signal-margin-v1",
            "modelDomain": "synthetic",
            "starSignal": star,
            "backgroundSignalInDetectionAperture": background,
            "thresholdContrast": 0.1,
            "observerLogMarginSigma": 0.2,
        }

    def test_visibility_probability_increases_with_signal(self):
        low = visibility.probability_from_signals(self.request(1, 20))
        high = visibility.probability_from_signals(self.request(4, 20))
        self.assertLess(low["visibilityProbability"], high["visibilityProbability"])

    def test_first_crossing_interpolates(self):
        samples = [
            {"minutesAfterSunset": 10, "request": self.request(1, 20)},
            {"minutesAfterSunset": 12, "request": self.request(2, 20)},
            {"minutesAfterSunset": 14, "request": self.request(4, 20)},
        ]
        result = visibility.first_crossing(samples, 0.5)
        self.assertEqual(result["status"], "CROSSING_FOUND")
        self.assertGreaterEqual(result["estimatedMinutesAfterSunset"], 10)
        self.assertLessEqual(result["estimatedMinutesAfterSunset"], 14)


if __name__ == "__main__":
    unittest.main()
