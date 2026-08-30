import importlib.util
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PATH = ROOT / "review/low-altitude-stellar-transport-v1/protected_v2_fresh_matrix.py"
SPEC = importlib.util.spec_from_file_location("low_altitude_protected_v2_test", PATH)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class FreshProtectedV2MatrixTests(unittest.TestCase):
    def test_protocol_validates(self):
        mod.validate_protocol()

    def test_axes_are_exact_centers_of_every_frozen_interpolation_interval(self):
        self.assertEqual(mod.PROTECTED_ALTITUDE_DEG, mod._midpoints(tuple(float(x) for x in mod.phase_b.LOWER_ASSET_ALTITUDE_DEG)))
        self.assertEqual(mod.PROTECTED_ELEVATION_M, mod._midpoints(tuple(float(x) for x in mod.phase_b.ELEVATION_KNOTS_M)))
        self.assertEqual(mod.PROTECTED_AOD550, mod._midpoints(tuple(float(x) for x in mod.phase_b.AOD_KNOTS)))

    def test_exact_176_cell_center_universe_and_528_photometric_comparisons(self):
        rows = mod.build_protected_cases()
        self.assertEqual(len(rows), 11 * 4 * 4)
        self.assertEqual(len(mod.fresh_keys()), 176)
        self.assertEqual(176 * len(mod.REPRESENTATIVE_LIBRARY_NUMBERS), 528)
        self.assertEqual(mod.REPRESENTATIVE_LIBRARY_NUMBERS, (1, 26, 45))

    def test_fresh_matrix_is_disjoint_from_opened_v1_training_and_seam(self):
        training = {
            mod._coord(r["targetGeometricAltitudeDeg"], r["observerElevationM"], r["aod550"])
            for r in mod.phase_b.build_training_cases()
        }
        seam = {
            mod._coord(r["targetGeometricAltitudeDeg"], r["observerElevationM"], r["aod550"])
            for r in mod.phase_b.build_seam_cases()
        }
        self.assertFalse(mod.fresh_keys() & mod.inadmissible_v1_keys())
        self.assertFalse(mod.fresh_keys() & training)
        self.assertFalse(mod.fresh_keys() & seam)
        self.assertFalse(set(mod.PROTECTED_ALTITUDE_DEG) & set(mod.INADMISSIBLE_V1_ALTITUDE_DEG))
        self.assertFalse(set(mod.PROTECTED_ELEVATION_M) & set(mod.INADMISSIBLE_V1_ELEVATION_M))
        self.assertFalse(set(mod.PROTECTED_AOD550) & set(mod.INADMISSIBLE_V1_AOD550))

    def test_acceptance_and_claim_boundary_are_inherited_not_tuned(self):
        ledger = mod.review_ledger()
        self.assertEqual(ledger["acceptance"]["maxAbsDeltaAvMag"], 0.025)
        self.assertEqual(ledger["acceptance"]["rmsDeltaAvMag"], 0.010)
        self.assertTrue(ledger["acceptance"]["globalAndEveryAltitudeCellCenterMustPass"])
        self.assertFalse(ledger["acceptance"]["postResultFloorBackSelectionAuthorized"])
        self.assertEqual(ledger["claimBoundary"]["minimumSupportedGeometricAltitudeIfPassDeg"], 0.25)
        self.assertFalse(ledger["claimBoundary"]["exactHorizonSupported"])
        self.assertFalse(ledger["claimBoundary"]["productionAuthorized"])
        self.assertFalse(ledger["claimBoundary"]["applicationSupportChanged"])

    def test_result_blind_and_refraction_separation_are_explicit(self):
        ledger = mod.review_ledger()
        self.assertEqual(ledger["matrixSelectionBasis"], "exact-geometric-center-of-every-frozen-trilinear-interpolation-cell")
        self.assertFalse(ledger["protectedResidualsUsedForMatrixSelection"])
        self.assertFalse(ledger["inadmissibleV1NumericalResultsUsed"])
        self.assertFalse(ledger["mysticState0077ResidualsUsed"])
        self.assertFalse(ledger["taylorOrJerusalemUsed"])
        self.assertEqual(ledger["targetAltitudeBasis"], "topocentric-vacuum-geometric")
        self.assertFalse(ledger["refractionAppliedInRadiativeTransfer"])
        self.assertTrue(ledger["seamRequirement"]["exactFiveDegreeContentIdentityRequired"])
        self.assertEqual(ledger["seamRequirement"]["exactFiveDegreeProvider"], "authoritative-v3.2")

    def test_review_surface_cannot_open_protected_results(self):
        ledger = mod.review_ledger()
        self.assertFalse(ledger["protectedSolverExecutionAuthorized"])
        self.assertFalse(ledger["protectedResultsOpened"])
        self.assertFalse(ledger["trainingOrRepresentationChanged"])
        source = PATH.read_text(encoding="utf-8")
        self.assertNotIn("subprocess", source)
        self.assertNotIn("uvspec", source)
        self.assertNotIn("--execute", source)

    def test_ledger_is_deterministic(self):
        first = mod.review_ledger()
        second = mod.review_ledger()
        self.assertEqual(first, second)
        self.assertEqual(len(first["ledgerSha256"]), 64)
        int(first["ledgerSha256"], 16)
        json.dumps(first, sort_keys=True)


if __name__ == "__main__":
    unittest.main()
