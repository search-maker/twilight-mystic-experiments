from __future__ import annotations
import json
import unittest
from pathlib import Path

LEDGER = Path(__file__).resolve().parents[1] / 'review' / 'lunar-scattered-light-source-contract-v1' / 'xshooter-case-ledger-and-ancillary-plan-v1.json'

class LunarXshooterCaseLedgerAndAncillaryPlanV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = json.loads(LEDGER.read_text(encoding='utf-8'))

    def test_exact_case_universe_and_frozen_strata(self):
        cases = self.c['skyCases']
        self.assertEqual(len(cases), 18)
        self.assertEqual(len({x['id'] for x in cases}), 18)
        for run in ['A', 'B', 'C']:
            self.assertEqual({x['moonSeparationDeg'] for x in cases if x['run'] == run}, {7, 13, 20, 45, 90, 110})
        self.assertEqual(sum(x['stratum'] == 'PRIMARY_CLEAR' for x in cases), 13)
        self.assertEqual(sum(x['stratum'] == 'STRESS_7_DEG' for x in cases), 3)
        self.assertEqual(sum(x['stratum'] == 'STRESS_THIN_CIRRUS' for x in cases), 2)
        self.assertEqual({x['id'] for x in cases if x['stratum'] == 'STRESS_THIN_CIRRUS'}, {'A90', 'A110'})

    def test_timestamp_and_geometry_cannot_be_residual_tuned(self):
        t = self.c['timestampBoundary']
        self.assertTrue(t['publishedDateTimeStringsFrozenHere'])
        self.assertTrue(t['archiveMetadataMustConfirmTimestampSemanticsBeforeEphemerisEvaluation'])
        self.assertTrue(t['noTimestampAdjustmentMayBeChosenFromMysticResiduals'])
        for x in self.c['skyCases']:
            self.assertIn('ra', x)
            self.assertIn('dec', x)
            self.assertIn('airmass', x)

    def test_standard_star_langley_is_not_promoted_to_independent_aerosol_truth(self):
        s = self.c['standardStarContext']
        self.assertEqual(s['independentAerosolAdmissionStatus'], 'NOT_ADMITTED')
        self.assertFalse(s['mayBeUsedAsExactIndependentAodOrPhaseFunction'])
        reasons = ' '.join(s['publishedFailureReasons'])
        self.assertIn('ADR', reasons)
        self.assertIn('hours', reasons)
        self.assertIn('1 percent', reasons)
        self.assertEqual(len(s['observations']), 8)

    def test_same_sky_aerosol_fit_remains_forbidden(self):
        a = self.c['aerosolIndependenceGate']
        self.assertFalse(a['jonesBestFitAerosolFromSameSkySpectraAllowed'])
        self.assertFalse(a['standardStarLangleyAllowedAsExactIndependentAerosolState'])
        self.assertTrue(a['absoluteMysticValidationRequiresIndependentSameNightAerosolState'])
        self.assertTrue(a['aeronetOrEquivalentArchiveSearchStillRequired'])
        self.assertTrue(a['noResidualDrivenAerosolChoice'])
        self.assertIn('DIAGNOSTIC_ONLY', a['ifNoIndependentAerosolState'])

    def test_ancillary_products_have_narrow_roles(self):
        p = self.c['independentAncillaryPlan']
        self.assertFalse(p['esoDustCounts']['mayBeConvertedToColumnAodWithoutSeparateModelAndValidation'])
        self.assertFalse(p['esoDustCounts']['maySupplyAerosolPhaseFunction'])
        self.assertEqual(p['esoDustCounts']['publishedContext']['runAStartEndPerM3'], [20000, 69000])
        self.assertEqual(p['esoDustCounts']['publishedContext']['runBStartEndPerM3'], [14000, 30000])
        self.assertEqual(p['esoDustCounts']['publishedContext']['runCStartEndPerM3'], [220000, 24000])
        self.assertEqual(p['radiometerIwv']['publishedStartEndKgM2']['A'], [3.7, 4.1])
        self.assertEqual(p['radiometerIwv']['publishedStartEndKgM2']['B'], [1.6, 1.7])
        self.assertEqual(p['radiometerIwv']['publishedStartEndKgM2']['C'], [2.4, 2.6])
        self.assertFalse(p['radiometerIwv']['maySupplyAerosolState'])
        self.assertTrue(p['radiometerIwv']['rawOrAuthoritativeProductIdentityStillRequiredForMysticInput'])

    def test_no_validation_result_is_opened_or_authorized(self):
        g = self.c['openingGate']
        self.assertFalse(g['archiveProductsAcquiredAndHashed'])
        self.assertFalse(g['timestampSemanticsConfirmed'])
        self.assertFalse(g['independentAerosolLedgerComplete'])
        self.assertFalse(g['mysticResidualsOpened'])
        self.assertFalse(g['absoluteValidationAuthorized'])
        self.assertFalse(g['productionAuthorized'])

if __name__ == '__main__':
    unittest.main()
