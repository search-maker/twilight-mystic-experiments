from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUTH_WORKFLOW = ROOT / ".github/workflows/aerosol-family-v2-r7-authorization-review.yml"


class R7AuthorizationSourceBindingRegression(unittest.TestCase):
    def test_authorization_review_resolves_source_base_through_bound_base_design(self):
        text = AUTH_WORKFLOW.read_text()
        self.assertIn('d["baseDesignPath"]', text)
        self.assertIn('["sourceBindings"]["publicRepoMainSha"]', text)
        self.assertNotIn(
            'json.load(open("experiments/aerosol-family-challenge-v2-r7/design.review.json"))["sourceBindings"]',
            text,
        )


if __name__ == "__main__":
    unittest.main()
