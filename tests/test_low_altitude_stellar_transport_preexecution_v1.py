#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import math
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "review" / "low-altitude-stellar-transport-v1" / "low_altitude_phase_a.py"
SPEC = importlib.util.spec_from_file_location("low_altitude_phase_a", MODULE_PATH)
assert SPEC and SPEC.loader
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


class LowAltitudePreexecutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.atmosphere = base / "afglus.dat"
        self.wavelength = base / "wavelength_grid.dat"
        # Only altitude column is used by the review renderer; a second column
        # keeps the fixture structurally atmosphere-like.
        self.atmosphere.write_text("120 1\n80 1\n50 1\n20 1\n10 1\n5 1\n2.5 1\n0 1\n", encoding="utf-8")
        self.wavelength.write_text("380\n780\n", encoding="utf-8")
        self.data_dir = base / "data"

    def test_frozen_case_universe_is_28_and_above_horizon(self):
        cases = m.build_phase_a_cases()
        self.assertEqual(len(cases), 28)
        self.assertEqual(sorted({row["targetGeometricAltitudeDeg"] for row in cases}), [0.25, 0.5, 1.0, 2.0, 3.0, 4.0, 5.0])
        self.assertTrue(all(row["targetGeometricAltitudeDeg"] > 0 for row in cases))
        self.assertEqual(sum(row["seamControl"] for row in cases), 4)
        self.assertEqual(sorted({row["observerElevationM"] for row in cases}), [0.0, 2500.0])
        self.assertEqual(sorted({row["aod550"] for row in cases}), [0.05, 0.40])

    def test_ledger_is_review_only_and_epsilon_forbidden(self):
        ledger = m.case_ledger()
        self.assertFalse(ledger["scientificExecutionAuthorized"])
        self.assertFalse(ledger["solverExecutionAuthorized"])
        self.assertFalse(ledger["protectedResultsOpened"])
        self.assertFalse(ledger["refractionAppliedInRadiativeTransfer"])
        self.assertFalse(ledger["failureSemantics"]["epsilonSubstitutionAllowed"])
        self.assertFalse(ledger["failureSemantics"]["sameIdentityRetryAllowed"])
        self.assertEqual(len(ledger["caseLedgerSha256"]), 64)

    def test_renderer_uses_geometric_sza_pseudospherical_and_local_site_grid(self):
        text = m.render_uvspec_input(
            data_dir=self.data_dir,
            atmosphere_file=self.atmosphere,
            wavelength_grid_file=self.wavelength,
            target_altitude_deg=0.25,
            observer_elevation_m=2500.0,
            aod550=0.40,
        )
        self.assertIn("sza 89.75000000", text)
        self.assertIn("atm_z_grid 2.500000", text)
        self.assertIn("zout 0.000000", text)
        self.assertIn("rte_solver sdisort", text)
        self.assertIn("sdisort nscat 1", text)
        self.assertIn("wavelength 380 780", text)
        self.assertIn("aerosol_default", text)
        self.assertIn("aerosol_set_tau_at_wvl 550 0.40000000", text)
        lower = text.lower()
        self.assertNotIn("nrefrac", lower)
        self.assertNotIn("refraction", lower)
        self.assertNotIn("rte_solver mystic", lower)
        self.assertNotIn("mc_", lower)
        self.assertNotIn("angstrom", lower)
        self.assertNotIn("\naltitude ", lower)

    def test_renderer_refuses_exact_horizon_and_nonfrozen_coordinates(self):
        with self.assertRaises(m.LowAltitudeRefusal):
            m.render_uvspec_input(
                data_dir=self.data_dir, atmosphere_file=self.atmosphere,
                wavelength_grid_file=self.wavelength, target_altitude_deg=0.0,
                observer_elevation_m=0.0, aod550=0.05,
            )
        with self.assertRaises(m.LowAltitudeRefusal):
            m.render_uvspec_input(
                data_dir=self.data_dir, atmosphere_file=self.atmosphere,
                wavelength_grid_file=self.wavelength, target_altitude_deg=0.75,
                observer_elevation_m=0.0, aod550=0.05,
            )

    def test_parser_accepts_positive_complete_spectrum_without_epsilon(self):
        altitude = 0.25
        mu0 = math.sin(math.radians(altitude))
        stdout = "\n".join(f"{w} {mu0 * 0.25:.17g}" for w in range(380, 781)) + "\n"
        parsed = m.parse_direct_transmission(stdout, target_altitude_deg=altitude)
        self.assertEqual(parsed["wavelengthNm"], list(range(380, 781)))
        self.assertTrue(all(abs(value - 0.25) < 1e-12 for value in parsed["lineOfSightDirectTransmission"]))
        self.assertFalse(parsed["positiveEpsilonSubstitutionUsed"])
        self.assertAlmostEqual(parsed["sourceZenithAngleDeg"], 89.75)

    def test_parser_fails_closed_on_zero_underflow_or_incomplete_grid(self):
        altitude = 0.25
        mu0 = math.sin(math.radians(altitude))
        zero = "\n".join(f"{w} {0.0 if w == 550 else mu0 * 0.25:.17g}" for w in range(380, 781)) + "\n"
        with self.assertRaisesRegex(m.LowAltitudeRefusal, "NUMERICALLY_UNRESOLVED"):
            m.parse_direct_transmission(zero, target_altitude_deg=altitude)
        incomplete = "\n".join(f"{w} {mu0 * 0.25:.17g}" for w in range(380, 780)) + "\n"
        with self.assertRaises(m.LowAltitudeRefusal):
            m.parse_direct_transmission(incomplete, target_altitude_deg=altitude)

    def test_floor_classifier_requires_contiguous_suffix(self):
        cases = m.build_phase_a_cases()
        statuses = {row["caseId"]: ("PASS" if row["targetGeometricAltitudeDeg"] >= 1.0 else "NUMERICALLY_UNRESOLVED") for row in cases}
        result = m.classify_numerical_floor(statuses)
        self.assertEqual(result["status"], "CONTIGUOUS_SUFFIX_PASS")
        self.assertEqual(result["minimumNumericallyRepresentableAltitudeDeg"], 1.0)

        nonmonotone = {row["caseId"]: "PASS" for row in cases}
        for row in cases:
            if row["targetGeometricAltitudeDeg"] == 3.0:
                nonmonotone[row["caseId"]] = "NUMERICALLY_UNRESOLVED"
        blocked = m.classify_numerical_floor(nonmonotone)
        self.assertEqual(blocked["status"], "BLOCKED_NON_MONOTONE")
        self.assertIsNone(blocked["minimumNumericallyRepresentableAltitudeDeg"])

    def test_module_contains_no_solver_process_execution_surface(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn("import subprocess", source)
        self.assertNotIn("subprocess.", source)
        self.assertNotIn("Popen(", source)
        self.assertNotIn("os.system", source)
        self.assertNotIn("allow_execution", source)
        self.assertNotIn("--execute", source)


if __name__ == "__main__":
    unittest.main()
