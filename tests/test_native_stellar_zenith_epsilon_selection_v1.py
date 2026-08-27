import copy
import importlib.util
import math
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "review/native-stellar-zenith-v3/select_zenith_epsilon_v1.py"


def load_module():
    spec = importlib.util.spec_from_file_location("select_zenith_epsilon_v1_test", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load epsilon selector")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def synthetic_summary(*, rejected=0.01975, delta_at_0025=8e-5):
    eps = [1.0,0.5,0.1,0.05,0.03,0.025,0.0225,0.021,0.0205,0.0200,0.0198,0.01975,0.0195,0.0190,0.018,0.015,0.010,0.001,0.0001]
    usable = [e for e in eps if e > rejected]
    groups = []
    for elevation, aod in ((0.0,0.05),(0.0,0.4),(2500.0,0.05),(2500.0,0.4)):
        comparisons=[]
        ref=min(usable)
        for e in usable:
            delta = 0.0 if e == ref else 2e-5
            if e == 0.025:
                delta = delta_at_0025
            comparisons.append({
                "sourceZenithAngleDeg":e,
                "maxAbsDeltaAvMagVsSmallestUsableSza":delta,
            })
        groups.append({
            "observerElevationM":elevation,
            "aod550":aod,
            "smallestSolverUsableSourceZenithAngleDeg":ref,
            "largestSolverRejectedSourceZenithAngleDeg":rejected,
            "solverUsabilityMonotonicTowardZenith":True,
            "allRejectedCasesMatchProvenEndpointSignature":True,
            "comparisons":comparisons,
        })
    return {
        "schemaVersion":2,
        "stageId":"native-stellar-zenith-v3-epsilon-convergence-v1",
        "status":"TRAINING_ONLY_NUMERICAL_CONVERGENCE_DIAGNOSTIC_COMPLETE",
        "sourceZenithAngleDeg":eps,
        "solverInvocationCount":76,
        "solverUsabilityMonotonicTowardZenithAcrossAllCorners":True,
        "allRejectedCasesMatchProvenEndpointSignature":True,
        "largestSourceZenithAngleRejectedByAnyCornerDeg":rejected,
        "groups":groups,
        "claimBoundary":{
            "protectedHoldoutOpened":False,
            "modelFitPerformed":False,
            "canonicalEpsilonSelected":False,
            "acceptanceGateEvaluated":False,
            "productionAuthorized":False,
            "empiricalRealSkyValidated":False,
            "humanFirstSeeingValidated":False,
        },
    }


class ZenithEpsilonSelectionV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m=load_module()

    def test_predeclared_protocol_constants(self):
        m=self.m
        self.assertEqual(m.SAFETY_FACTOR,1.25)
        self.assertEqual(m.MAX_RELATIVE_AIRMASS_EXCESS,1e-7)
        self.assertEqual(m.MAX_ABS_DELTA_AV_MAG,1e-4)
        self.assertEqual(m.EXPECTED_SOLVER_CALLS,76)
        self.assertEqual(len(m.EXPECTED_SZA),19)

    def test_boundary_0p01975_selects_0p025_when_photometry_passes(self):
        m=self.m
        out=m.evaluate(synthetic_summary())
        self.assertEqual(out["status"],"CANONICAL_EPSILON_SELECTED_BY_PREREGISTERED_PROTOCOL")
        self.assertAlmostEqual(out["requiredSafetyMarginSzaDeg"],0.0246875,places=12)
        self.assertEqual(out["selected"]["sourceZenithAngleDeg"],0.025)
        self.assertTrue(out["selected"]["passesSafetyMargin"])
        self.assertTrue(out["selected"]["passesAirmassBound"])
        self.assertTrue(out["selected"]["passesPhotometricConvergenceBound"])
        self.assertLess(m.relative_airmass_excess(0.025),1e-7)
        self.assertGreater(m.relative_airmass_excess(0.03),1e-7)

    def test_photometric_failure_can_force_no_selection(self):
        m=self.m
        out=m.evaluate(synthetic_summary(delta_at_0025=2e-4))
        self.assertEqual(out["status"],"NO_SELECTION_UNDER_PREREGISTERED_PROTOCOL")
        self.assertIsNone(out["selected"])

    def test_larger_rejected_boundary_can_force_no_selection(self):
        m=self.m
        out=m.evaluate(synthetic_summary(rejected=0.0205))
        self.assertEqual(out["status"],"NO_SELECTION_UNDER_PREREGISTERED_PROTOCOL")
        self.assertIsNone(out["selected"])

    def test_nonendpoint_rejection_invalidates_selection(self):
        m=self.m
        s=synthetic_summary()
        s["allRejectedCasesMatchProvenEndpointSignature"]=False
        with self.assertRaisesRegex(m.SelectionRefusal,"endpoint signature"):
            m.evaluate(s)

    def test_nonmonotonic_solver_boundary_invalidates_selection(self):
        m=self.m
        s=synthetic_summary()
        s["solverUsabilityMonotonicTowardZenithAcrossAllCorners"]=False
        with self.assertRaisesRegex(m.SelectionRefusal,"not monotonic"):
            m.evaluate(s)

    def test_claim_boundary_must_remain_closed(self):
        m=self.m
        s=synthetic_summary()
        s["claimBoundary"]["protectedHoldoutOpened"]=True
        with self.assertRaisesRegex(m.SelectionRefusal,"protectedHoldoutOpened"):
            m.evaluate(s)

    def test_selector_uses_only_all_corner_intersection(self):
        m=self.m
        s=synthetic_summary()
        s["groups"][0]["comparisons"]=[row for row in s["groups"][0]["comparisons"] if row["sourceZenithAngleDeg"]!=0.025]
        out=m.evaluate(s)
        self.assertNotIn(0.025,out["allCornerUsableSourceZenithAngleDeg"])
        self.assertEqual(out["status"],"NO_SELECTION_UNDER_PREREGISTERED_PROTOCOL")

    def test_output_does_not_authorize_holdout_or_production(self):
        out=self.m.evaluate(synthetic_summary())
        c=out["claimBoundary"]
        self.assertFalse(c["protectedHoldoutOpened"])
        self.assertFalse(c["solverExecuted"])
        self.assertFalse(c["modelFitPerformed"])
        self.assertFalse(c["acceptanceGateEvaluated"])
        self.assertFalse(c["productionAuthorized"])


if __name__ == "__main__":
    unittest.main()
