#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
GUARD = HERE / "preauthorization_guard_v1.py"
CONTRACT = HERE / "preauthorization_contract.v1.json"
spec = importlib.util.spec_from_file_location("confirmation_preauth_guard", GUARD)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.contract = json.loads(CONTRACT.read_text())
        self.prereg = {
            "preregistrationSha256": "a801000ea0af81a109f9e0e1ec2b28befa0703e4ec47e9f85ee1b10b448a95b6",
            "executionBoundary": {"authorizationOrdinalAllocated": False, "scientificExecutionAuthorized": False},
            "caseDesign": {"cases": [{"seed": 1600000001 + i} for i in range(24)]},
        }
        self.source = {"sourceCases": [{"seed": 1000 + i} for i in range(166)]}
        self.pilot = {"candidateCases": [{"seed": 970001 + i} for i in range(44)]}
        self.branches = [{"name": "dispatch/full-spectrum-estimator-pilot-v2-ordinal16"}]
        self.runs = [{"id": 1, "event": "push", "head_branch": "dispatch/full-spectrum-estimator-pilot-v2-ordinal16", "name": "pilot", "display_title": "pilot", "path": ".github/workflows/pilot.yml"}]
        self.artifacts = [{"id": 1, "name": "full-spectrum-estimator-confirmation-v1-disabled-execution-review"}]

    def run_guard(self, **overrides):
        values = dict(
            contract=self.contract,
            prereg=self.prereg,
            source_audit=self.source,
            pilot_seed_audit=self.pilot,
            branches=self.branches,
            runs=self.runs,
            artifacts=self.artifacts,
        )
        values.update(overrides)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            return mod.build_report(repository_root=root, **values)

    def test_clean_surface_reports_next_without_allocating(self):
        report = self.run_guard()
        self.assertEqual(report["status"], "PREAUTHORIZATION_SURFACE_CLEAN_NOT_ALLOCATED")
        self.assertEqual(report["latestConsumedScientificOrdinal"], 16)
        self.assertEqual(report["nextAvailableScientificOrdinalIfAllocatedLater"], 17)
        self.assertFalse(report["authorizationOrdinalAllocated"])

    def test_confirmation_dispatch_ref_refused(self):
        with self.assertRaisesRegex(mod.PreauthorizationRefusal, "ref already exists"):
            self.run_guard(branches=self.branches + [{"name": "dispatch/full-spectrum-estimator-confirmation-v1-ordinal17"}])

    def test_confirmation_push_run_refused(self):
        bad = self.runs + [{"id": 9, "event": "push", "head_branch": "dispatch/full-spectrum-estimator-confirmation-v1-ordinal17", "name": "x", "display_title": "x", "path": ".github/workflows/x.yml"}]
        with self.assertRaisesRegex(mod.PreauthorizationRefusal, "scientific push run"):
            self.run_guard(runs=bad)

    def test_confirmation_case_artifact_refused(self):
        bad = self.artifacts + [{"id": 99, "name": "full-spectrum-estimator-confirmation-v1-case-train-0009-c1"}]
        with self.assertRaisesRegex(mod.PreauthorizationRefusal, "scientific artifact"):
            self.run_guard(artifacts=bad)

    def test_source_seed_collision_refused(self):
        bad = {"sourceCases": self.source["sourceCases"] + [{"seed": 1600000007}]}
        with self.assertRaisesRegex(mod.PreauthorizationRefusal, "source ledger"):
            self.run_guard(source_audit=bad)

    def test_pilot_seed_collision_refused(self):
        bad = {"candidateCases": self.pilot["candidateCases"] + [{"seed": 1600000014}]}
        with self.assertRaisesRegex(mod.PreauthorizationRefusal, "pilot seeds"):
            self.run_guard(pilot_seed_audit=bad)

    def test_committed_authorization_file_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "experiments/full-spectrum-estimator-confirmation-v1/authorization.ordinal17.json"
            p.parent.mkdir(parents=True)
            p.write_text("{}\n")
            with self.assertRaisesRegex(mod.PreauthorizationRefusal, "authorization file already committed"):
                mod.build_report(contract=self.contract, prereg=self.prereg, source_audit=self.source, pilot_seed_audit=self.pilot, branches=self.branches, runs=self.runs, artifacts=self.artifacts, repository_root=root)

    def test_pr_review_title_does_not_consume_ordinal(self):
        review = {"id": 44, "event": "pull_request", "head_branch": "agent/review", "display_title": "Full-spectrum estimator confirmation v1 ordinal 99 review", "name": "review", "path": ".github/workflows/review.yml"}
        report = self.run_guard(runs=self.runs + [review])
        self.assertEqual(report["latestConsumedScientificOrdinal"], 16)


if __name__ == "__main__":
    unittest.main()
