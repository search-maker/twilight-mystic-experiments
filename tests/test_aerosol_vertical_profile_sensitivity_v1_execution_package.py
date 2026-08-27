from __future__ import annotations

import importlib.util
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "experiments" / "aerosol-vertical-profile-sensitivity-v1" / "execution_package.py"


def load_module():
    spec = importlib.util.spec_from_file_location("avps_execution_package_test", MODULE)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot import execution package")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class AerosolVerticalProfileExecutionPackageTests(unittest.TestCase):
    def test_disabled_package_freezes_exact_360_case_surface_without_seed_or_ordinal(self) -> None:
        mod = load_module()
        package = mod.build_disabled_execution_package()
        self.assertEqual(package["status"], "DISABLED_EXECUTION_PACKAGE_REVIEW_ONLY_SEEDS_UNALLOCATED")
        self.assertEqual(package["caseCount"], 360)
        self.assertEqual(package["groupCount"], 72)
        self.assertEqual(package["distinctPreSeedScienceSurfaceCount"], 120)
        self.assertEqual(package["candidateSeedCount"], 72)
        self.assertEqual(
            package["candidateSeedCanonicalSha256"],
            "a2e22b526dfad84d4f23c0ca8b143d028fddc7e55f78deb93a43e194ebd6c35e",
        )
        self.assertEqual(
            package["candidateRowsCanonicalSha256"],
            "f22de8a9e30ba106759effb1170a5ca1d1e747cb2ac68293fa232dc7ed6ca683",
        )
        self.assertIsNone(package["scientificOrdinal"])
        self.assertFalse(package["candidateSeedsAppliedToCases"])
        self.assertFalse(package["scientificExecutionAuthorized"])
        self.assertFalse(package["solverExecutionAuthorized"])
        self.assertFalse(package["resultOpeningAuthorized"])
        self.assertFalse(package["productionAuthorized"])
        self.assertEqual(len(package["cases"]), 360)
        self.assertEqual(len({row["caseId"] for row in package["cases"]}), 360)
        self.assertEqual(len({row["caseSurfaceSha256"] for row in package["cases"]}), 120)
        for row in package["cases"]:
            self.assertIsNone(row["seed"])
            self.assertEqual(row["seedStatus"], "UNALLOCATED_REVIEW_ONLY")
            self.assertFalse(row["renderable"])
            self.assertFalse(row["executionAuthorized"])
            self.assertFalse(row["resultOpeningAuthorized"])
            surface = row["caseSurface"]
            self.assertIn("rte_solver mystic", surface)
            self.assertIn("mc_spherical 1D", surface)
            self.assertIn("mc_photons 20000000", surface)
            self.assertIn("mc_randomseed <UNALLOCATED_FRESH_GROUP_SEED>", surface)
            self.assertNotIn("mc_randomseed 0", surface)
            aerosol = [line for line in surface if line.startswith("aerosol_")]
            self.assertEqual(aerosol[0], "aerosol_default")
            self.assertEqual(aerosol[1], "aerosol_species_library OPAC")
            self.assertEqual(aerosol[2], "aerosol_species_file continental_average")
            self.assertEqual(sum(line.startswith("aerosol_file tau profiles/") for line in aerosol), 1)
            self.assertEqual(sum(line.startswith("aerosol_set_tau_at_wvl 550 ") for line in aerosol), 1)
            self.assertFalse(any(line.startswith("aerosol_modify ") for line in aerosol))

    def test_replicates_share_preseed_surface_but_cases_remain_distinct(self) -> None:
        mod = load_module()
        package = mod.build_disabled_execution_package()
        by_surface: dict[str, list[dict]] = {}
        for row in package["cases"]:
            by_surface.setdefault(row["caseSurfaceSha256"], []).append(row)
        self.assertEqual(len(by_surface), 120)
        self.assertTrue(all(len(rows) == 3 for rows in by_surface.values()))
        self.assertTrue(all(len({row["caseId"] for row in rows}) == 3 for rows in by_surface.values()))

    def test_profile_bundle_uses_exact_input_grid_and_unit_tau(self) -> None:
        mod = load_module()
        levels_desc = [120, 100, 80, 60, 50, 40, 35, 30, 25, 20, 15, 12, 10, 8, 6, 5, 4, 3, 2, 1, 0]
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "afglus.dat"
            path.write_text("# synthetic exact-grid fixture only\n" + "\n".join(f"{z} 1" for z in levels_desc) + "\n")
            bundle = mod.build_exact_profile_bundle(path)
        self.assertEqual(bundle["status"], "EXACT_AFGL_PROFILE_BUNDLE_REVIEW_ONLY")
        self.assertEqual(bundle["afglAltitudeEdgesKm"], list(reversed(levels_desc)))
        self.assertEqual(bundle["afglLevelCount"], len(levels_desc))
        self.assertEqual(len(bundle["profiles"]), 5)
        self.assertEqual(len({row["sha256"] for row in bundle["profiles"].values()}), 5)
        for row in bundle["profiles"].values():
            self.assertEqual(row["levelCount"], len(levels_desc))
            self.assertTrue(math.isclose(row["tauSum"], 1.0, rel_tol=0.0, abs_tol=1e-12))
            data = [line for line in row["text"].splitlines() if line and not line.startswith("#")]
            self.assertEqual(float(data[0].split()[1]), 0.0)

    def test_invalid_review_case_is_refused(self) -> None:
        mod = load_module()
        skeleton = mod._execution_candidate().build_review_execution_skeleton()
        case = json.loads(json.dumps(skeleton["cases"][0]))
        case["seed"] = 123456789
        case["seedStatus"] = "CANDIDATE"
        with self.assertRaises(mod.ExecutionPackageError):
            mod.render_case_science_surface(case)


if __name__ == "__main__":
    unittest.main()
