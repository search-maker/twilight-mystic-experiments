from __future__ import annotations

import importlib.util
import json
import math
import pathlib
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "review" / "low-altitude-stellar-transport-v1" / "run_phase_b_training_v1.py"
SPEC = importlib.util.spec_from_file_location("run_phase_b_training_v1", MODULE_PATH)
assert SPEC and SPEC.loader
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


class PhaseBTrainingV1ReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = pathlib.Path(self.tmp.name)
        self.atmosphere = base / "afglus.dat"
        self.atmosphere.write_text("120 1\n80 1\n50 1\n20 1\n10 1\n5 1\n2.5 1\n0 1\n", encoding="utf-8")
        self.wavelength = base / "wavelength-grid.dat"
        self.wavelength.write_text("380\n780\n", encoding="utf-8")
        self.data_dir = base / "data"

    def _stdout(self, altitude: float, transmission: float) -> str:
        mu0 = math.sin(math.radians(altitude))
        return "\n".join(f"{w} {mu0 * transmission:.17g}" for w in range(380, 781)) + "\n"

    def test_training_universe_is_exactly_275_and_excludes_seam(self):
        cases = m.phase_b.build_training_cases()
        self.assertEqual(len(cases), 275)
        self.assertEqual(sorted({r["targetGeometricAltitudeDeg"] for r in cases}), list(m.phase_b.TRAINING_ALTITUDE_DEG))
        self.assertTrue(all(r["targetGeometricAltitudeDeg"] < 5.0 for r in cases))
        self.assertEqual(m.EXPECTED_INVOCATIONS, 275)

    def test_review_ledger_freezes_geometry_and_keeps_protected_closed(self):
        ledger = m.review_ledger()
        self.assertEqual(ledger["scientificState"], "LOWALT-STELLAR-STATE-0001")
        self.assertEqual(ledger["trainingSpectrumCount"], 275)
        self.assertEqual(ledger["protectedSpectrumCountExecuted"], 0)
        self.assertFalse(ledger["protectedResultsOpened"])
        self.assertEqual(ledger["solver"], "sdisort")
        self.assertEqual(ledger["solverGeometry"], "pseudo-spherical")
        self.assertEqual(ledger["targetAltitudeBasis"], "topocentric-vacuum-geometric")
        self.assertEqual(ledger["sourceZenithAngleRule"], "90deg-targetGeometricAltitudeDeg")
        self.assertFalse(ledger["refractionAppliedInRadiativeTransfer"])
        self.assertFalse(ledger["positiveEpsilonSubstitutionAllowed"])
        self.assertFalse(ledger["exactHorizonIncluded"])
        self.assertFalse(ledger["productionAuthorized"])

    def test_renderer_matches_phase_a_semantics_on_shared_endpoint_coordinates(self):
        phase_a_path = MODULE_PATH.parent / "low_altitude_phase_a.py"
        spec = importlib.util.spec_from_file_location("phase_a_compare", phase_a_path)
        assert spec and spec.loader
        phase_a = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(phase_a)
        for altitude in (0.25, 0.5, 1.0, 2.0, 3.0, 4.0):
            for elevation in (0.0, 2500.0):
                for aod in (0.05, 0.40):
                    expected = phase_a.render_uvspec_input(
                        data_dir=self.data_dir,
                        atmosphere_file=self.atmosphere,
                        wavelength_grid_file=self.wavelength,
                        target_altitude_deg=altitude,
                        observer_elevation_m=elevation,
                        aod550=aod,
                    )
                    actual = m.render_training_input(
                        data_dir=self.data_dir,
                        atmosphere_file=self.atmosphere,
                        wavelength_grid_file=self.wavelength,
                        target_altitude_deg=altitude,
                        observer_elevation_m=elevation,
                        aod550=aod,
                    )
                    self.assertEqual(actual, expected)

    def test_renderer_accepts_every_frozen_middle_elevation_without_phase_a_endpoint_leak(self):
        for elevation in m.phase_b.ELEVATION_KNOTS_M:
            text = m.render_training_input(
                data_dir=self.data_dir,
                atmosphere_file=self.atmosphere,
                wavelength_grid_file=self.wavelength,
                target_altitude_deg=0.75,
                observer_elevation_m=elevation,
                aod550=0.10,
            )
            self.assertIn("sza 89.25000000", text)
            self.assertIn("rte_solver sdisort", text)
            self.assertIn("sdisort nscat 1", text)
            self.assertNotIn("refraction", text.lower())
        with self.assertRaises(m.TrainingExecutionRefusal):
            m.render_training_input(
                data_dir=self.data_dir,
                atmosphere_file=self.atmosphere,
                wavelength_grid_file=self.wavelength,
                target_altitude_deg=5.0,
                observer_elevation_m=500.0,
                aod550=0.10,
            )

    def test_parser_accepts_positive_401_point_spectrum_and_refuses_zero(self):
        altitude = 0.75
        parsed = m.parse_training_transmission(self._stdout(altitude, 0.2), target_altitude_deg=altitude)
        self.assertEqual(len(parsed["directOpticalDepth"]), 401)
        self.assertFalse(parsed["positiveEpsilonSubstitutionUsed"])
        self.assertAlmostEqual(parsed["sourceZenithAngleDeg"], 89.25)
        mu0 = math.sin(math.radians(altitude))
        zero = "\n".join(f"{w} {0.0 if w == 550 else mu0 * 0.2:.17g}" for w in range(380, 781)) + "\n"
        with self.assertRaisesRegex(m.TrainingExecutionRefusal, "NUMERICALLY_UNRESOLVED"):
            m.parse_training_transmission(zero, target_altitude_deg=altitude)

    def test_execution_is_explicit_and_nonresumable(self):
        with self.assertRaisesRegex(m.TrainingExecutionRefusal, "allow_execution"):
            m.execute_campaign(
                uvspec=pathlib.Path('/does/not/matter'),
                data_dir=self.data_dir,
                atmosphere_file=self.atmosphere,
                wavelength_grid_file=self.wavelength,
                output_dir=pathlib.Path(self.tmp.name) / 'out',
                allow_execution=False,
            )
        existing = pathlib.Path(self.tmp.name) / "already"
        existing.mkdir()
        fake_uvspec = pathlib.Path(self.tmp.name) / "uvspec"
        fake_uvspec.write_text("", encoding="utf-8")
        with self.assertRaisesRegex(m.TrainingExecutionRefusal, "retry/resume"):
            m.execute_campaign(
                uvspec=fake_uvspec,
                data_dir=self.data_dir,
                atmosphere_file=self.atmosphere,
                wavelength_grid_file=self.wavelength,
                output_dir=existing,
                allow_execution=True,
            )

    def test_one_unresolved_case_does_not_hide_later_training_evidence(self):
        cases = [
            {"targetGeometricAltitudeDeg": 0.25, "sourceZenithAngleDeg": 89.75, "observerElevationM": 0.0, "aod550": 0.05},
            {"targetGeometricAltitudeDeg": 0.5, "sourceZenithAngleDeg": 89.5, "observerElevationM": 0.0, "aod550": 0.05},
        ]
        fake_uvspec = pathlib.Path(self.tmp.name) / "uvspec"
        fake_uvspec.write_text("", encoding="utf-8")
        out = pathlib.Path(self.tmp.name) / "tiny-exec"
        responses = [
            SimpleNamespace(returncode=0, stdout="\n".join(f"{w} 0" for w in range(380, 781)) + "\n", stderr=""),
            SimpleNamespace(returncode=0, stdout=self._stdout(0.5, 0.25), stderr=""),
        ]
        with mock.patch.object(m.phase_b, "validate_frozen_universe", return_value=None), \
             mock.patch.object(m.phase_b, "build_training_cases", return_value=cases), \
             mock.patch.object(m, "EXPECTED_INVOCATIONS", 2), \
             mock.patch.object(m.subprocess, "run", side_effect=responses):
            payload = m.execute_campaign(
                uvspec=fake_uvspec,
                data_dir=self.data_dir,
                atmosphere_file=self.atmosphere,
                wavelength_grid_file=self.wavelength,
                output_dir=out,
                allow_execution=True,
            )
        self.assertTrue(payload["executionComplete"])
        self.assertFalse(payload["trainingScientificallyEligible"])
        self.assertEqual(payload["solverInvocationCount"], 2)
        self.assertEqual(payload["passingTrainingSpectrumCount"], 1)
        self.assertEqual(payload["numericallyUnresolvedTrainingSpectrumCount"], 1)
        self.assertEqual([row["status"] for row in payload["cases"]], ["NUMERICALLY_UNRESOLVED", "PASS"])
        receipt = json.loads((out / "execution-receipt.json").read_text(encoding="utf-8"))
        self.assertFalse(receipt["trainingScientificallyEligible"])
        self.assertEqual(receipt["solverInvocationCount"], 2)

    def test_control_contains_no_protected_execution_surface(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn('protectedValidationOpened', source)
        self.assertIn('protectedSolverInvocationCount', source)
        self.assertNotIn('build_protected_cases()', source)
        self.assertNotIn('evaluate_protected_deltas(', source)
        self.assertNotIn('Taylor', source)
        self.assertNotIn('Jerusalem', source)
        self.assertNotIn('MYSTIC Monte Carlo', source)


if __name__ == "__main__":
    unittest.main()
