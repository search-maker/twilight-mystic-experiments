#!/usr/bin/env python3
from __future__ import annotations

import ast
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "review" / "low-altitude-stellar-transport-v1" / "run_phase_a_exec001.py"
SPEC = importlib.util.spec_from_file_location("phase_a_exec001", P)
assert SPEC and SPEC.loader
x = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(x)


class PhaseAExec001ControlTests(unittest.TestCase):
    def test_identity_and_frozen_invocation_count(self):
        self.assertEqual(x.EXECUTION_ID, "low-altitude-stellar-phase-a-v1-exec001")
        self.assertEqual(x.EXPECTED_INVOCATIONS, 28)
        self.assertEqual(len(x.m.build_phase_a_cases()), 28)

    def test_execution_refuses_without_explicit_authorization(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(x.ExecutionRefusal):
                x.execute_campaign(
                    uvspec=Path(td) / "uvspec",
                    data_dir=Path(td), atmosphere_file=Path(td) / "atm",
                    wavelength_grid_file=Path(td) / "w", output_dir=Path(td) / "out",
                    allow_execution=False,
                )

    def test_controller_has_exactly_one_subprocess_run_site_and_no_loop_retry_primitive(self):
        source = P.read_text(encoding="utf-8")
        tree = ast.parse(source)
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
        subprocess_runs = [
            n for n in calls
            if isinstance(n.func, ast.Attribute)
            and isinstance(n.func.value, ast.Name)
            and n.func.value.id == "subprocess"
            and n.func.attr == "run"
        ]
        self.assertEqual(len(subprocess_runs), 1)
        self.assertFalse(any(isinstance(n, ast.While) for n in ast.walk(tree)))
        self.assertNotIn("sleep(", source)
        self.assertNotIn("Popen(", source)

    def test_output_directory_existing_blocks_resume(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            u = root / "uvspec"
            u.write_text("", encoding="utf-8")
            out = root / "out"
            out.mkdir()
            with self.assertRaisesRegex(x.ExecutionRefusal, "retry/resume is forbidden"):
                x.execute_campaign(
                    uvspec=u, data_dir=root, atmosphere_file=root / "atm",
                    wavelength_grid_file=root / "w", output_dir=out,
                    allow_execution=True,
                )


if __name__ == "__main__":
    unittest.main()
