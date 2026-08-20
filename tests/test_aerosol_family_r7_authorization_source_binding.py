from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUTH_WORKFLOW = ROOT / ".github/workflows/aerosol-family-v2-r7-authorization-review.yml"
EXEC_WORKFLOW = ROOT / ".github/workflows/aerosol-family-v2-r7-execution.yml"
R7_DESIGN = ROOT / "experiments/aerosol-family-challenge-v2-r7/design.review.json"


class R7AuthorizationSourceBindingRegression(unittest.TestCase):
    def test_bound_base_design_path_is_repo_root_relative_and_resolves(self):
        design = json.loads(R7_DESIGN.read_text())
        base_design_path = Path(design["baseDesignPath"])
        self.assertFalse(base_design_path.is_absolute())
        resolved = ROOT / base_design_path
        self.assertTrue(resolved.is_file(), resolved)
        base_design = json.loads(resolved.read_text())
        source_base = base_design["sourceBindings"]["publicRepoMainSha"]
        self.assertRegex(source_base, re.compile(r"^[0-9a-f]{40}$"))

    def test_authorization_review_uses_repo_root_relative_base_design_path(self):
        text = AUTH_WORKFLOW.read_text()
        self.assertIn('Path(d["baseDesignPath"])', text)
        self.assertIn('["sourceBindings"]["publicRepoMainSha"]', text)
        self.assertNotIn(
            'Path("experiments/aerosol-family-challenge-v2-r7") / d["baseDesignPath"]',
            text,
        )
        self.assertNotIn(
            'json.load(open("experiments/aerosol-family-challenge-v2-r7/design.review.json"))["sourceBindings"]',
            text,
        )

    def test_execution_preflight_uses_repo_root_relative_base_design_path(self):
        text = EXEC_WORKFLOW.read_text()
        self.assertIn('Path(d["baseDesignPath"])', text)
        self.assertIn('["sourceBindings"]["publicRepoMainSha"]', text)
        self.assertNotIn(
            'json.load(open("experiments/aerosol-family-challenge-v2-r7/design.review.json"))["sourceBindings"]',
            text,
        )



if __name__ == "__main__":
    unittest.main()
