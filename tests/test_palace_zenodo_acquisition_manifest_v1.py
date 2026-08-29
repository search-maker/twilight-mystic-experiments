from __future__ import annotations
import json
import unittest
from pathlib import Path

MANIFEST = Path(__file__).resolve().parents[1] / 'review' / 'night-background-source-admission-v1' / 'palace-v1.0-zenodo-acquisition-manifest-v1.json'


class PalaceZenodoAcquisitionManifestV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = json.loads(MANIFEST.read_text(encoding='utf-8'))

    def test_exact_version_identity_is_frozen_separately_from_concept_doi(self):
        z = self.m['zenodo']
        self.assertEqual(z['conceptDoi'], '10.5281/zenodo.14064022')
        self.assertEqual(z['versionDoi'], '10.5281/zenodo.14064023')
        self.assertEqual(z['recordId'], 14064023)
        self.assertEqual(z['recordUrl'], 'https://zenodo.org/records/14064023')

    def test_all_three_published_assets_and_md5_identities_are_bound(self):
        assets = {a['name']: a for a in self.m['releaseAssets']}
        self.assertEqual(set(assets), {'PALACE.zip', 'PMD.zip', 'test.zip'})
        self.assertEqual(assets['PALACE.zip']['publishedMd5'], '840f26b56dd508c7b751b3927f0ea102')
        self.assertEqual(assets['PMD.zip']['publishedMd5'], '434ef6bf1498920832298cd31b4ddc69')
        self.assertEqual(assets['test.zip']['publishedMd5'], '861d5671f661f9a3c1378b63b18ada21')
        self.assertIn('436 ASCII', assets['PMD.zip']['publishedRole'])

    def test_metadata_is_not_misrepresented_as_downloaded_byte_verification(self):
        for asset in self.m['releaseAssets']:
            self.assertIsNone(asset['downloadedBytesSha256'])
            self.assertFalse(asset['byteSizeVerified'])
            self.assertFalse(asset['publishedMd5VerifiedAgainstDownloadedBytes'])
        b = self.m['acquisitionBoundary']
        self.assertFalse(b['publishedMd5MaySubstituteForDownloadedByteVerification'])
        self.assertFalse(b['implementationMayBeginBeforeRequiredRuntimeAssetsAreDownloadedAndSha256Bound'])
        self.assertTrue(b['archiveMemberInventoryRequiredBeforeImplementation'])

    def test_validation_and_production_remain_closed(self):
        b = self.m['acquisitionBoundary']
        self.assertFalse(b['sourceOrTestValuesMayBeChangedToFitTaylorOrJerusalem'])
        self.assertFalse(b['sameSessionMeasuredAirglowClaimAllowed'])
        self.assertFalse(b['globalSiteTransferClaimAllowed'])
        g = self.m['implementationGate']
        self.assertFalse(g['providerImplementationAuthorized'])
        self.assertFalse(g['empiricallyValidatedByThisProject'])
        self.assertFalse(g['productionAuthorized'])


if __name__ == '__main__':
    unittest.main()
