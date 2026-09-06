#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODULE_PATH = HERE / "lunar_mystic_input_reptran.py"
CONTRACT_PATH = HERE / "prestage-contract.json"

spec = importlib.util.spec_from_file_location("lunar_reptran_prestage", MODULE_PATH)
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class LunarReptranPrestageTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.data = self.root / "data"
        self.data.mkdir()
        self.atm = self.root / "afglus.dat"
        self.atm.write_text(
            "120.000 1\n10.000 1\n5.000 1\n0.000 1\n",
            encoding="utf-8",
        )
        self.source = self.root / "lunar-source.dat"
        self.source_meta = mod.write_lunar_source_file(
            self.source,
            [380.0, 550.0, 780.0],
            [1e-6, 2e-6, 1e-6],
        )
        self.case_dir = self.root / "case"
        self.case_dir.mkdir()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def render(self, elevation: float = 2000.0):
        return mod.render_lunar_mystic_reptran_prestage(
            data_dir=self.data,
            atmosphere_file=self.atm,
            lunar_source_file=self.source,
            moon_zenith_deg=30.0,
            target_altitude_deg=45.0,
            target_relative_azimuth_to_moon_deg=90.0,
            observer_elevation_m=elevation,
            aod550=0.1,
            albedo=0.15,
            photon_histories=5_000_000,
            synthetic_review_seed=1,
            case_dir=self.case_dir,
            alis_importance_nm=550.0,
        )

    def test_contract_is_explicitly_non_authorizing(self) -> None:
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(contract["bindingIssue60Decision"], 5560785094)
        self.assertEqual(contract["dependencyChange"]["requiredMolAbsParam"], "reptran")
        self.assertFalse(contract["dependencyChange"]["historicalCrsFallbackAllowed"])
        self.assertEqual(contract["frozenPhysicalDesign"]["totalDirectionalCases"], 198)
        self.assertEqual(contract["futureExecutionPrestage"]["shardCount"], 18)
        self.assertEqual(contract["futureExecutionPrestage"]["casesPerShard"], 11)
        self.assertFalse(contract["futureExecutionPrestage"]["candidateExecutionIdAllocated"])
        self.assertFalse(contract["futureExecutionPrestage"]["candidateSeedUniverseCreated"])
        self.assertFalse(contract["authority"]["scientificSolverExecutionAuthorized"])
        self.assertFalse(contract["authority"]["protectedResultOpeningAuthorized"])

    def test_source_bytes_preserve_units_and_no_distance_rescaling(self) -> None:
        self.assertEqual(self.source_meta["inputUnit"], "W m-2 nm-1")
        self.assertEqual(self.source_meta["unit"], "mW m-2 nm-1")
        self.assertFalse(self.source_meta["dayOfYearDistanceScalingApplied"])
        rows = self.source.read_text(encoding="utf-8").splitlines()
        self.assertEqual(rows[0], "380.000000 1.000000000000e-03")
        self.assertEqual(rows[-1], "780.000000 1.000000000000e-03")

    def test_frozen_33_direction_plan_is_unchanged(self) -> None:
        samples = mod.finite_disk_direction_samples(
            moon_zenith_deg=30.0,
            target_altitude_deg=45.0,
            target_relative_azimuth_to_moon_deg=90.0,
            lunar_angular_radius_deg=0.25896468848728504,
        )
        self.assertEqual(len(samples), 33)
        self.assertEqual(samples[0]["sampleId"], "center")
        self.assertEqual(sum(x["radiusFraction"] == 0.5 for x in samples), 16)
        self.assertEqual(sum(x["radiusFraction"] == 1.0 for x in samples), 16)
        self.assertTrue(all(x["sameFullDiskIntegratedRoloIrradianceRequired"] for x in samples))
        self.assertTrue(all(x["physicalResolvedDiskWeight"] is None for x in samples))

    def test_renderer_emits_only_reptran_with_frozen_controls(self) -> None:
        text, meta = self.render()
        lines = text.splitlines()
        self.assertEqual(lines.count(f"source solar {self.source.resolve()}"), 1)
        self.assertEqual(lines.count("mol_abs_param reptran"), 1)
        self.assertFalse(any(line.startswith("mol_abs_param crs") for line in lines))
        self.assertEqual(lines.count("mc_spherical 1D"), 1)
        self.assertEqual(lines.count("mc_vroom off"), 1)
        self.assertEqual(lines.count("mc_spectral_is 550.0"), 1)
        self.assertEqual(lines.count("zout 0.000000"), 1)
        self.assertEqual(sum(line.startswith("atm_z_grid ") for line in lines), 1)
        self.assertEqual(meta["molecularAbsorption"], "reptran")
        self.assertFalse(meta["crsFallbackAllowed"])
        self.assertFalse(meta["runtimeCapabilityVerified"])
        self.assertFalse(meta["scientificSeedAllocated"])
        self.assertFalse(meta["solverExecutionAuthorized"])

    def test_reviewed_elevation_semantics_hold_at_zero_and_2km(self) -> None:
        for elevation in (0.0, 2000.0):
            text, meta = self.render(elevation)
            self.assertEqual(text.splitlines().count("zout 0.000000"), 1)
            self.assertEqual(meta["siteAltitudeKm"], elevation / 1000.0)
            self.assertEqual(meta["atmosphereGridKm"][0], elevation / 1000.0)

    def test_fail_closed_on_crs_or_duplicate_source(self) -> None:
        text, _ = self.render()
        with self.assertRaises(mod.LunarReptranPrestageError):
            mod.validate_rendered_reptran_input(
                text.replace("mol_abs_param reptran", "mol_abs_param crs"),
                self.source,
            )
        with self.assertRaises(mod.LunarReptranPrestageError):
            mod.validate_rendered_reptran_input(
                text + f"source solar {self.source.resolve()}\n",
                self.source,
            )

    def test_fail_closed_on_budget_or_alis_drift(self) -> None:
        kwargs = dict(
            data_dir=self.data,
            atmosphere_file=self.atm,
            lunar_source_file=self.source,
            moon_zenith_deg=30.0,
            target_altitude_deg=45.0,
            target_relative_azimuth_to_moon_deg=90.0,
            observer_elevation_m=0.0,
            aod550=0.1,
            albedo=0.15,
            synthetic_review_seed=1,
            case_dir=self.case_dir,
        )
        with self.assertRaises(mod.LunarReptranPrestageError):
            mod.render_lunar_mystic_reptran_prestage(
                photon_histories=4_999_999,
                alis_importance_nm=550.0,
                **kwargs,
            )
        with self.assertRaises(mod.LunarReptranPrestageError):
            mod.render_lunar_mystic_reptran_prestage(
                photon_histories=5_000_000,
                alis_importance_nm=650.0,
                **kwargs,
            )


if __name__ == "__main__":
    unittest.main()
