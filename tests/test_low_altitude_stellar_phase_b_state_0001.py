#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import math
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'review'/'low-altitude-stellar-transport-v1'/'low_altitude_phase_b.py'
SPEC=importlib.util.spec_from_file_location('lowalt_phase_b',P); assert SPEC and SPEC.loader
m=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(m)

class PhaseBTests(unittest.TestCase):
    def test_frozen_counts_and_disjointness(self):
        self.assertEqual(len(m.build_training_cases()),275)
        self.assertEqual(len(m.build_protected_cases()),176)
        self.assertEqual(176*len(m.PICKLES_LIBRARY_NUMBERS),528)
        proof=m.prove_disjointness()
        self.assertEqual(proof['freshTrainingProtectedCollisionCount'],0)
        self.assertEqual(proof['historicalProtectedTupleCollisionCountByAltitudeProof'],0)
        self.assertLess(max(m.PROTECTED_ALTITUDE_DEG),5.0)
        self.assertEqual(m.HISTORICAL_PROTECTED_MIN_TARGET_ALTITUDE_DEG,5.0)

    def test_protected_altitudes_are_three_eighths_inside_every_cell(self):
        full=m.TRAINING_ALTITUDE_DEG+(m.SEAM_ALTITUDE_DEG,)
        expected=tuple(full[i]+0.375*(full[i+1]-full[i]) for i in range(len(full)-1))
        self.assertEqual(expected,m.PROTECTED_ALTITUDE_DEG)

    def test_routing_preserves_exact_five_degree_legacy_seam(self):
        self.assertEqual(m.route_provider(0.25),'lowalt_state_0001')
        self.assertEqual(m.route_provider(4.999999),'lowalt_state_0001')
        self.assertEqual(m.route_provider(5.0),'legacy_v32')
        self.assertEqual(m.route_provider(90.0),'legacy_v32')
        for h in (0.0,0.249999,90.000001):
            with self.assertRaisesRegex(m.PhaseBRefusal,'STELLAR_SPECTRAL_RUNTIME_OOD'):
                m.route_provider(h)

    def test_lower_interpolation_is_linear_in_tau_not_csc(self):
        haxis=m.TRAINING_ALTITUDE_DEG+(5.0,); eaxis=m.ELEVATION_M; aaxis=m.AOD550
        rows=[]
        for h in haxis:
            for e in eaxis:
                for a in aaxis:
                    rows.append([h+e/10000+a]*len(m.WAVELENGTH_NM))
        asset={'axes':{'targetAltitudeDeg':list(haxis),'observerElevationM':list(eaxis),'aod550':list(aaxis)},'directOpticalDepth':rows}
        tau=m.interpolate_lower_tau(asset,target_geometric_altitude_deg=0.375,observer_elevation_m=250,aod550=0.075)
        self.assertEqual(len(tau),401)
        self.assertAlmostEqual(tau[0],0.375+0.025+0.075,places=14)
        self.assertNotIn('csc',m.ledger()['representation']['altitudeInterpolation'])

    def test_underflow_is_refused_not_epsilon(self):
        haxis=m.TRAINING_ALTITUDE_DEG+(5.0,); rows=[]
        for h in haxis:
            for e in m.ELEVATION_M:
                for a in m.AOD550:
                    rows.append([1000.0]*len(m.WAVELENGTH_NM))
        asset={'axes':{'targetAltitudeDeg':list(haxis),'observerElevationM':list(m.ELEVATION_M),'aod550':list(m.AOD550)},'directOpticalDepth':rows}
        with self.assertRaisesRegex(m.PhaseBRefusal,'NUMERIC_UNRESOLVED'):
            m.interpolate_lower_tau(asset,target_geometric_altitude_deg=1.25,observer_elevation_m=1000,aod550=0.15)
        self.assertFalse(m.ledger()['failureSemantics']['epsilonSubstitutionAllowed'])

    def test_seam_extraction_is_25_rows_and_exact_first_altitude_block(self):
        alt=[5.0,6.0]; rows=[]
        for h in alt:
            for ie,e in enumerate(m.ELEVATION_M):
                for ja,a in enumerate(m.AOD550):
                    rows.append([h+ie+ja/10]*401)
        runtime={'axes':{'targetAltitudeDeg':alt,'observerElevationM':list(m.ELEVATION_M),'aod550':list(m.AOD550)},'wavelengthNm':list(m.WAVELENGTH_NM),'directOpticalDepth':rows}
        seam=m.extract_exact_5deg_seam(runtime)
        self.assertEqual(len(seam['rows']),25)
        self.assertTrue(all(r['targetGeometricAltitudeDeg']==5.0 for r in seam['rows']))
        self.assertEqual(seam['rows'][0]['directOpticalDepth'][0],5.0)
        self.assertEqual(seam['rows'][-1]['directOpticalDepth'][0],9.4)
        self.assertEqual(len(seam['seamCanonicalSha256']),64)

    def test_review_cli_has_no_solver_execution_surface(self):
        source=P.read_text(encoding='utf-8').lower()
        for forbidden in ('import subprocess','subprocess.','popen(','os.system','uvspec','--execute','allow_execution'):
            self.assertNotIn(forbidden,source)

if __name__=='__main__': unittest.main()
