#!/usr/bin/env python3
"""Contract coverage for POST_V1 deep-solar-twilight reference modules.

These tests execute only the modules' built-in deterministic self-tests.  They
do not execute uvspec/MYSTIC, open protected scientific results, or mutate any
AVPS/science identity.
"""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REFERENCE_DIR = ROOT / "experiments" / "deep-solar-twilight-v1"


class DeepSolarTwilightReferenceModulesTest(unittest.TestCase):
    def _run_self_test(self, filename: str) -> None:
        path = REFERENCE_DIR / filename
        proc = subprocess.run(
            [sys.executable, str(path), "--self-test"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=30,
            check=False,
        )
        self.assertEqual(
            proc.returncode,
            0,
            msg=f"{filename} self-test failed:\n{proc.stdout}",
        )

    def test_rare_event_zero_bound_reference(self) -> None:
        self._run_self_test("rare_event_zero_bound_reference.py")

    def test_serializer_zero_semantics_reference(self) -> None:
        self._run_self_test("serializer_zero_semantics_reference.py")

    def test_independent_block_zero_bound_reference(self) -> None:
        self._run_self_test("independent_block_zero_bound_reference.py")

    def test_block_independence_zero_bound_reference(self) -> None:
        self._run_self_test("block_independence_zero_bound_reference.py")

    def test_finite_hit_fixed_horizon_reference(self) -> None:
        self._run_self_test("finite_hit_fixed_horizon_reference.py")

    def test_finite_hit_heterogeneous_reference(self) -> None:
        self._run_self_test("finite_hit_heterogeneous_reference.py")


if __name__ == "__main__":
    unittest.main()
