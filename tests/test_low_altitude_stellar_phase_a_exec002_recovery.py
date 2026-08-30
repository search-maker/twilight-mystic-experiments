#!/usr/bin/env python3
from __future__ import annotations

import ast
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "review" / "low-altitude-stellar-transport-v1" / "run_phase_a_exec002.py"
SPEC = importlib.util.spec_from_file_location("phase_a_exec002", P)
assert SPEC and SPEC.loader
x = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(x)


class PhaseAExec002RecoveryTests(unittest.TestCase):
    def test_fresh_identity_parent_binding_and_same_science_ledger(self):
        self.assertEqual(x.EXECUTION_ID, "low-altitude-stellar-phase-a-v1-exec002")
        self.assertEqual(x.PARENT_FAILED_EXECUTION_ID, "low-altitude-stellar-phase-a-v1-exec001")
        self.assertEqual(x.PARENT_FAILED_RUN, 33297281047)
        self.assertEqual(x.PARENT_FAILED_JOB, 99219023542)
        self.assertEqual(x.EXPECTED_INVOCATIONS, 28)
        self.assertEqual(len(x.m.build_phase_a_cases()), 28)
        self.assertEqual(x.m.PHASE_A_ALTITUDE_DEG, (0.25, 0.5, 1.0, 2.0, 3.0, 4.0, 5.0))
        self.assertEqual(x.m.PHASE_A_ELEVATION_M, (0.0, 2500.0))
        self.assertEqual(x.m.PHASE_A_AOD550, (0.05, 0.40))

    def test_execution_requires_fresh_explicit_authorization(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(x.ExecutionRefusal):
                x.execute_campaign(
                    uvspec=Path(td)/"uvspec", data_dir=Path(td),
                    atmosphere_file=Path(td)/"atm", wavelength_grid_file=Path(td)/"w",
                    output_dir=Path(td)/"out", allow_execution=False,
                )

    def test_exactly_one_solver_call_site_and_no_loop_retry(self):
        source=P.read_text(encoding="utf-8")
        tree=ast.parse(source)
        runs=[]
        for n in ast.walk(tree):
            if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name):
                if n.func.value.id=="subprocess" and n.func.attr=="run": runs.append(n)
        self.assertEqual(len(runs),1)
        self.assertFalse(any(isinstance(n,ast.While) for n in ast.walk(tree)))
        self.assertNotIn("Popen(",source)
        self.assertNotIn("sleep(",source)

    def test_existing_output_blocks_reuse(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); u=root/"uvspec"; u.write_text("",encoding="utf-8"); out=root/"out"; out.mkdir()
            with self.assertRaisesRegex(x.ExecutionRefusal,"retry/resume is forbidden"):
                x.execute_campaign(uvspec=u,data_dir=root,atmosphere_file=root/"atm",wavelength_grid_file=root/"w",output_dir=out,allow_execution=True)


if __name__ == "__main__":
    unittest.main()
