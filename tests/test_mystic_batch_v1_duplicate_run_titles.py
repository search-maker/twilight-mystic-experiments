from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "experiments" / "mystic-batch-v1" / "duplicate_run_audit.py"


def load_module():
    spec = importlib.util.spec_from_file_location("duplicate_run_audit_title_contract", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


duplicate = load_module()


class DuplicateRunTitleContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.execution_key = "cross-geometry-pilot-v1:screening:2"
        self.authorization_ref = "a" * 40
        self.ordinal = 2
        self.expected = duplicate.expected_title(
            self.execution_key,
            self.authorization_ref,
            self.ordinal,
        )
        self.marker = duplicate.one_shot_marker(self.expected)

    def test_cross_geometry_prefix_is_accepted(self) -> None:
        current_title = f"Cross geometry pilot v1 {self.marker}"
        payload = {
            "total_count": 1,
            "workflow_runs": [
                {
                    "id": 20,
                    "display_title": current_title,
                    "event": "workflow_dispatch",
                    "run_attempt": 1,
                    "status": "in_progress",
                    "conclusion": None,
                }
            ],
        }
        report = duplicate.evaluate(payload, 20, self.expected)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["displayTitle"], current_title)
        self.assertEqual(report["oneShotMarker"], self.marker)

    def test_duplicate_is_refused_even_with_another_prefix(self) -> None:
        current = {
            "id": 20,
            "display_title": f"Cross geometry pilot v1 {self.marker}",
            "event": "workflow_dispatch",
            "run_attempt": 1,
            "status": "in_progress",
            "conclusion": None,
        }
        previous = {
            **current,
            "id": 10,
            "display_title": f"MYSTIC batch v1 {self.marker}",
            "status": "completed",
            "conclusion": "failure",
        }
        with self.assertRaises(duplicate.DuplicateRefusal):
            duplicate.evaluate(
                {"total_count": 2, "workflow_runs": [current, previous]},
                20,
                self.expected,
            )

    def test_wrong_authorization_marker_is_refused(self) -> None:
        wrong_title = f"Cross geometry pilot v1 {self.marker.replace(self.authorization_ref, 'b' * 40)}"
        payload = {
            "total_count": 1,
            "workflow_runs": [
                {
                    "id": 20,
                    "display_title": wrong_title,
                    "event": "workflow_dispatch",
                    "run_attempt": 1,
                }
            ],
        }
        with self.assertRaises(duplicate.DuplicateRefusal):
            duplicate.evaluate(payload, 20, self.expected)


if __name__ == "__main__":
    unittest.main()
