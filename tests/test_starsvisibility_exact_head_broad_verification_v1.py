import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github/workflows/starsvisibility-exact-head-broad-verification-v1.yml'


class StarsvisibilityExactHeadBroadVerificationV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding='utf-8')

    def test_dispatch_is_one_file_and_read_only(self):
        self.assertIn('review/starsvisibility-broad-exact-head-dispatch/dispatch.json', self.text)
        self.assertIn('test "$GITHUB_RUN_ATTEMPT" = "1"', self.text)
        self.assertIn("assert d.get('readOnly') is True", self.text)
        self.assertIn("assert d.get('scientificExecution') is False", self.text)
        self.assertIn('persist-credentials: false', self.text)

    def test_no_scientific_solver_is_available(self):
        self.assertIn('test -z "$(command -v uvspec || true)"', self.text)
        self.assertNotIn('micromamba', self.text)
        self.assertNotIn('mc_photons', self.text)
        self.assertNotIn('allow-execution', self.text)

    def test_exact_private_sha_is_checked_out_and_verified(self):
        self.assertIn('repository: search-maker/starsvisibility', self.text)
        self.assertIn('ref: ${{ steps.dispatch.outputs.application_sha }}', self.text)
        self.assertIn('test "$(git rev-parse HEAD)" = "$EXPECTED_SHA"', self.text)

    def test_broad_application_surface_is_exercised(self):
        for command in (
            'npm run build:pages',
            'npm run test:level-b-current-main',
            'npm run test:level-b-sitewide-preview',
            'node scripts/test-level-b-stellar-v2-dist.mjs',
        ):
            self.assertIn(command, self.text)


if __name__ == '__main__':
    unittest.main()
