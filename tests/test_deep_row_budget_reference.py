from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFERENCE_DIR = ROOT / "experiments" / "deep-solar-twilight-v1"
SCRIPTS = (
    "row_budget_transport_reference.py",
    "row_budget_dual_reference.py",
    "row_budget_bellman_dual_certificate.py",
)


class DeepRowBudgetReferenceContractTests(unittest.TestCase):
    def test_all_exact_reference_self_tests(self) -> None:
        for name in SCRIPTS:
            script = REFERENCE_DIR / name
            self.assertTrue(script.is_file(), name)
            with self.subTest(script=name):
                completed = subprocess.run(
                    [sys.executable, str(script), "--self-test"],
                    cwd=ROOT,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                self.assertEqual(
                    completed.returncode,
                    0,
                    msg=(
                        f"{name} self-test failed\n"
                        f"stdout:\n{completed.stdout}\n"
                        f"stderr:\n{completed.stderr}"
                    ),
                )

    def test_reference_sources_preserve_non_authorizing_boundaries(self) -> None:
        combined = "\n".join((REFERENCE_DIR / name).read_text() for name in SCRIPTS)
        self.assertIn("floats are forbidden", combined)
        self.assertIn("No protected MYSTIC result", combined)
        self.assertNotIn("epsilon =", combined)
        self.assertNotIn("workflow_dispatch", combined)


if __name__ == "__main__":
    unittest.main()
