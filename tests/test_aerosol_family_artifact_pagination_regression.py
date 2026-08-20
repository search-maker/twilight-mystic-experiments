from pathlib import Path
import unittest


class AerosolFamilyArtifactPaginationRegression(unittest.TestCase):
    def test_case_preflight_lookup_paginates_all_same_run_artifacts(self):
        workflow = Path('.github/workflows/aerosol-family-v2-execution.yml').read_text()
        old = 'gh api "repos/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}/artifacts?per_page=100" > current-run-artifacts.json'
        paginated = 'gh api --paginate --slurp "repos/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}/artifacts?per_page=100" > current-run-artifact-pages.json'
        flatten = "rows=[a for page in pages for a in page.get('artifacts',[])]"
        self.assertNotIn(old, workflow)
        self.assertIn(paginated, workflow)
        self.assertIn("pages=json.load(open('current-run-artifact-pages.json'))", workflow)
        self.assertIn(flatten, workflow)

    def test_flattening_keeps_preflight_visible_after_more_than_100_case_artifacts(self):
        expected = 'aerosol-family-v2-preflight-ordinal-31'
        page1 = {'artifacts': [{'name': f'aerosol-family-v2-case-{i}', 'id': i, 'expired': False} for i in range(100)]}
        page2 = {'artifacts': [{'name': f'aerosol-family-v2-case-{i}', 'id': i, 'expired': False} for i in range(100, 106)] + [{'name': expected, 'id': 999, 'expired': False}]}
        pages = [page1, page2]
        rows = [a for page in pages for a in page.get('artifacts', [])]
        good = [a for a in rows if a.get('name') == expected and not a.get('expired', False)]
        self.assertEqual([999], [a['id'] for a in good])


if __name__ == '__main__':
    unittest.main()
