from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "experiments" / "mystic-batch-v1" / "cross_geometry_authorization_proposal.py"


def load_module():
    spec = importlib.util.spec_from_file_location("cross_geometry_authorization_attempt", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


proposal = load_module()


class CrossGeometryAuthorizationAttemptTests(unittest.TestCase):
    def test_failed_first_preflight_is_not_reused(self) -> None:
        self.assertEqual(proposal.AUTHORIZATION_ORDINAL, 2)
        self.assertEqual(
            proposal.EXECUTION_KEY,
            "cross-geometry-pilot-v1:screening:2",
        )
        self.assertNotEqual(
            proposal.EXECUTION_KEY,
            "cross-geometry-pilot-v1:screening:1",
        )


if __name__ == "__main__":
    unittest.main()
