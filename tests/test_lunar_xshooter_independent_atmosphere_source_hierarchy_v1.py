from __future__ import annotations
import json
import unittest
from pathlib import Path

PLAN = Path(__file__).resolve().parents[1] / 'review' / 'lunar-scattered-light-source-contract-v1' / 'xshooter-independent-atmosphere-source-hierarchy-v1.json'


class XshooterIndependentAtmosphereSourceHierarchyV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = json.loads(PLAN.read_text(encoding='utf-8'))

    def test_source_hierarchy_is_fixed_and_residual_blind(self):
        sources = self.p['sourceHierarchy']
        self.assertEqual([s['priority'] for s in sources], [1, 2, 3])
        self.assertEqual(sources[0]['doi'], '10.5067/MODIS/MOD04_L2.061')
        self.assertEqual(sources[1]['class'], 'REANALYSIS')
        self.assertEqual(sources[2]['doi'], '10.24381/d58bbf47')
        rules = self.p['fixedSpatialTemporalRules']
        self.assertTrue(rules['noResidualDrivenSourceChoice'])
        self.assertTrue(rules['noResidualDrivenInterpolation'])

    def test_merra2_exact_collections_and_reanalysis_boundary_are_frozen(self):
        m = self.p['sourceHierarchy'][1]
        self.assertEqual(m['horizontalGrid'], '0.625 degree longitude x 0.5 degree latitude')
        self.assertEqual(m['nativeModelLevels'], 72)
        collections = {c['shortName']: c for c in m['collections']}
        self.assertEqual(collections['M2T1NXAER']['doi'], '10.5067/KLICLTZ8EM9D')
        self.assertEqual(collections['M2I3NVAER']['doi'], '10.5067/LTVB4GPCOTK2')
        self.assertFalse(m['directMeasurementClaimAllowed'])

    def test_eac4_grid_cadence_and_aerosol_fields_are_bound(self):
        e = self.p['sourceHierarchy'][2]
        self.assertEqual(e['datasetId'], 'cams-global-reanalysis-eac4')
        self.assertEqual(e['horizontalGrid'], '0.75 degree x 0.75 degree')
        self.assertEqual(e['modelLevels'], 60)
        self.assertEqual(e['cadence'], '3-hourly')
        self.assertIn('total aerosol optical depth at 550 nm', e['requestedAerosolFields'])
        self.assertFalse(e['directMeasurementClaimAllowed'])

    def test_shared_assimilation_information_is_not_counted_as_independent_replication(self):
        d = self.p['dependenceBoundary']
        self.assertTrue(d['merra2AssimilatesSpaceBasedAerosolObservations'])
        self.assertTrue(d['directSatelliteAndReanalysisProductsMayShareObservationalInformation'])
        self.assertFalse(d['sourceAgreementMayBeCountedAsStatisticallyIndependentReplicates'])
        self.assertTrue(d['sourceDisagreementMustBePreservedAsAtmosphericUncertaintyNotResolvedFromXshooterResiduals'])

    def test_timestamp_and_claim_gates_remain_closed(self):
        t = self.p['timestampBoundary']
        self.assertFalse(t['publishedStringsMayBeAssumedUtcBeforeEsoArchiveConfirmation'])
        self.assertTrue(t['archiveTimestampSemanticsMustBeConfirmedBeforeTimeInterpolation'])
        self.assertTrue(t['noTimeShiftMayBeChosenFromMysticOrXshooterResiduals'])
        g = self.p['claimGate']
        self.assertFalse(g['sameSpectrumJonesAerosolFitsAllowed'])
        self.assertTrue(g['absoluteValidationRequiresPreResidualAtmosphereEnvelope'])
        self.assertFalse(g['mysticResidualsOpened'])
        self.assertFalse(g['absoluteValidationAuthorized'])
        self.assertFalse(g['productionAuthorized'])


if __name__ == '__main__':
    unittest.main()
