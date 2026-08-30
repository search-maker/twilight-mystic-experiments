from __future__ import annotations

import importlib.util
import math
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXEC_PATH = ROOT / "review/low-altitude-stellar-transport-v2/lowalt_state_0002_capability_exec001.py"

spec = importlib.util.spec_from_file_location("lowalt_exec001", EXEC_PATH)
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class LowAltState0002Exec001Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.controller, cls.manifest = mod.load_controller(ROOT)

    def atmosphere_file(self, directory: Path) -> Path:
        path = directory / "afglus-mini.dat"
        path.write_text("50 1\n10 1\n5 1\n2 1\n0 1\n", encoding="utf-8")
        return path

    def test_controller_binding_and_fresh_universe(self) -> None:
        m = self.manifest
        self.assertEqual(m["scientificState"], "LOWALT-STELLAR-STATE-0002")
        self.assertEqual(m["protocolId"], "lowalt-state-0002-capability-runtime-v1")
        self.assertEqual(m["freshCaseCount"], 20)
        self.assertEqual(m["timedInvocationCount"], 60)
        self.assertEqual(m["capabilitySpectrumCount"], 20)
        self.assertEqual(m["timingOnlyInvocationCount"], 40)
        self.assertFalse(m["protectedResultsAuthorized"])
        self.assertFalse(m["applicationSupportChangeAuthorized"])
        self.assertFalse(m["exactHorizonSupported"])
        self.assertEqual(set(m["freshAxes"]["targetGeometricAltitudeDeg"]), {"0.30", "0.70", "1.40", "2.90", "4.60"})
        self.assertEqual(m["collisionAudit"]["openedState0001ProtectedAltitudeCollisionCount"], 0)
        self.assertEqual(m["collisionAudit"]["openedState0001TrainingAltitudeCollisionCount"], 0)

    def test_renderer_is_geometric_sdisort_and_site_truncated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            atmosphere = self.atmosphere_file(d)
            grid = d / "grid.dat"
            grid.write_text("380\n780\n", encoding="utf-8")
            text = mod.render_uvspec_input(
                manifest=self.manifest, data_dir=d, atmosphere_file=atmosphere,
                wavelength_grid_file=grid, target_altitude_deg=0.30,
                observer_elevation_m=2500.0, aod550=0.40,
            )
        self.assertIn("sza 89.70000000", text)
        self.assertIn("atm_z_grid 2.500000 5.000000 10.000000 50.000000", text)
        self.assertIn("rte_solver sdisort", text)
        self.assertIn("sdisort nscat 1", text)
        self.assertIn("aerosol_set_tau_at_wvl 550 0.40000000", text)
        self.assertNotIn("refraction", text.lower())
        self.assertNotIn("nrefrac", text.lower())

    def test_renderer_refuses_non_fresh_or_horizon_coordinate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            atmosphere = self.atmosphere_file(d)
            grid = d / "grid.dat"
            grid.write_text("380\n780\n", encoding="utf-8")
            for altitude in (0.0, 0.25, 5.0):
                with self.assertRaises(mod.ExecutionRefusal):
                    mod.render_uvspec_input(
                        manifest=self.manifest, data_dir=d, atmosphere_file=atmosphere,
                        wavelength_grid_file=grid, target_altitude_deg=altitude,
                        observer_elevation_m=0.0, aod550=0.05,
                    )

    def test_parser_recovers_los_transmission_without_epsilon(self) -> None:
        h = 0.70
        mu0 = math.sin(math.radians(h))
        expected_t = math.exp(-0.123)
        stdout = "\n".join(f"{w} {mu0 * expected_t:.17g}" for w in range(380, 781)) + "\n"
        parsed = mod.parse_direct_transmission(stdout, manifest=self.manifest, target_altitude_deg=h)
        self.assertEqual(parsed["wavelengthNm"], list(range(380, 781)))
        self.assertTrue(all(abs(x - expected_t) < 1e-12 for x in parsed["lineOfSightDirectTransmission"]))
        self.assertTrue(all(abs(x - 0.123) < 1e-12 for x in parsed["directOpticalDepth"]))
        self.assertFalse(parsed["positiveEpsilonSubstitutionUsed"])

    def test_parser_fails_closed_on_zero_or_missing_output(self) -> None:
        h = 1.40
        mu0 = math.sin(math.radians(h))
        lines = [f"{w} {mu0 * 0.5:.17g}" for w in range(380, 781)]
        lines[10] = "390 0"
        with self.assertRaises(mod.ExecutionRefusal):
            mod.parse_direct_transmission("\n".join(lines) + "\n", manifest=self.manifest, target_altitude_deg=h)
        with self.assertRaises(mod.ExecutionRefusal):
            mod.parse_direct_transmission("\n".join(lines[:-1]) + "\n", manifest=self.manifest, target_altitude_deg=h)

    def test_timing_summary_uses_frozen_budgets_and_nearest_rank_p95(self) -> None:
        rows = []
        ordinal = 0
        for altitude in self.manifest["freshAxes"]["targetGeometricAltitudeDeg"]:
            for _ in range(12):
                ordinal += 1
                rows.append({"elapsedSeconds": ordinal / 100.0, "targetGeometricAltitudeDeg": altitude})
        summary = mod.timing_summary(rows, self.manifest)
        self.assertEqual(summary["count"], 60)
        self.assertAlmostEqual(summary["medianSeconds"], 0.305)
        self.assertAlmostEqual(summary["p95NearestRankSeconds"], 0.57)
        self.assertAlmostEqual(summary["maxSeconds"], 0.60)
        self.assertAlmostEqual(summary["totalSeconds"], sum(i / 100.0 for i in range(1, 61)))
        self.assertAlmostEqual(summary["projectedSerialSecondsAtMedian"]["ordinaryTimelineBase2049"], 0.305 * 2049)
        self.assertAlmostEqual(summary["projectedSerialSecondsAtP95"]["sevenDayAnnualSingleTarget108597"], 0.57 * 108597)
        self.assertEqual(summary["routingBoundary"], "PER_SAMPLE_REMOTE_SDISORT_REMAINS_ARCHITECTURALLY_INELIGIBLE_INDEPENDENT_OF_TIMING")

    def test_executor_source_contains_no_opened_failure_metrics_or_target_fit_inputs(self) -> None:
        source = EXEC_PATH.read_text(encoding="utf-8")
        for forbidden in (
            "0.20750414925067062", "0.044561710921862445", "33316048419",
            "9733633988", "Taylor residual", "Jerusalem residual",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
