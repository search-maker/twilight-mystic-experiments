from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "modeling" / "surrogate-training-v2" / "real_handoff_guard.py"
SPEC = importlib.util.spec_from_file_location("real_handoff_guard", MODULE_PATH)
assert SPEC and SPEC.loader
GUARD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GUARD)


class RealHandoffGuardTests(unittest.TestCase):
    def manifest(self) -> dict:
        return {
            "schemaVersion": 1,
            "stageId": "twilight-surrogate-tier-1-execution-v1",
            "proposalOnly": True,
            "scientificExecution": False,
            "cases": [{"caseId": f"case-{index:04d}"} for index in range(96)],
        }

    def source_run(self) -> dict:
        return {
            "id": GUARD.SOURCE_RUN_ID,
            "workflow_id": GUARD.SOURCE_WORKFLOW_ID,
            "run_number": GUARD.SOURCE_RUN_NUMBER,
            "run_attempt": 1,
            "event": "workflow_dispatch",
            "status": "completed",
            "conclusion": "success",
            "head_branch": "main",
            "head_sha": GUARD.SOURCE_HEAD_SHA,
            "path": GUARD.SOURCE_PATH,
            "display_title": GUARD.SOURCE_DISPLAY_TITLE,
        }

    def reference_run(self) -> dict:
        return {
            "id": GUARD.REFERENCE_RUN_ID,
            "workflow_id": GUARD.REFERENCE_WORKFLOW_ID,
            "run_attempt": 1,
            "event": "push",
            "status": "completed",
            "conclusion": "success",
            "head_branch": "main",
            "head_sha": GUARD.REFERENCE_HEAD_SHA,
            "path": GUARD.REFERENCE_PATH,
            "name": "Twilight surrogate tier-1 proposal",
        }

    @staticmethod
    def artifact(artifact_id: int, name: str, digest_char: str = "a") -> dict:
        return {
            "id": artifact_id,
            "name": name,
            "expired": False,
            "digest": "sha256:" + digest_char * 64,
        }

    def source_artifacts(self) -> dict:
        names = [
            GUARD.PREFLIGHT_ARTIFACT_NAME,
            GUARD.AGGREGATE_ARTIFACT_NAME,
            GUARD.AUDIT_ARTIFACT_NAME,
            GUARD.ANALYSIS_ARTIFACT_NAME,
            *(f"{GUARD.CASE_ARTIFACT_PREFIX}case-{index:04d}" for index in range(96)),
        ]
        return {"artifacts": [self.artifact(index + 1, name) for index, name in enumerate(names)]}

    def reference_artifacts(self) -> dict:
        return {
            "artifacts": [
                {
                    "id": GUARD.REFERENCE_ARTIFACT_ID,
                    "name": GUARD.REFERENCE_ARTIFACT_NAME,
                    "expired": False,
                    "digest": GUARD.REFERENCE_ARTIFACT_DIGEST,
                }
            ]
        }

    def validate(self, **overrides):
        values = {
            "source_run": self.source_run(),
            "source_artifacts": self.source_artifacts(),
            "manifest": self.manifest(),
            "reference_run": self.reference_run(),
            "reference_artifacts": self.reference_artifacts(),
        }
        values.update(overrides)
        return GUARD.validate(**values, handoff_head_sha="b" * 40)

    def test_accepts_exact_terminal_source(self):
        report = self.validate()
        self.assertEqual(report["status"], "REAL_TIER1_HANDOFF_SOURCE_ACCEPTED")
        self.assertEqual(report["sourceArtifactCount"], 100)
        self.assertEqual(report["caseArtifactCount"], 96)
        self.assertFalse(report["surrogateTrainingAuthorized"])
        self.assertFalse(report["productionPromotionAuthorized"])

    def test_refuses_nonterminal_or_retried_source(self):
        for field, value in (("status", "in_progress"), ("run_attempt", 2), ("conclusion", "failure")):
            run = self.source_run()
            run[field] = value
            with self.subTest(field=field), self.assertRaises(GUARD.GuardRefusal):
                self.validate(source_run=run)

    def test_refuses_missing_or_extra_source_artifact(self):
        missing = self.source_artifacts()
        missing["artifacts"].pop()
        with self.assertRaises(GUARD.GuardRefusal):
            self.validate(source_artifacts=missing)

        extra = self.source_artifacts()
        extra["artifacts"].append(self.artifact(1001, "unexpected-artifact"))
        with self.assertRaises(GUARD.GuardRefusal):
            self.validate(source_artifacts=extra)

    def test_refuses_reference_drift(self):
        reference = self.reference_artifacts()
        reference["artifacts"][0]["digest"] = "sha256:" + "0" * 64
        with self.assertRaises(GUARD.GuardRefusal):
            self.validate(reference_artifacts=reference)

    def test_cli_writes_guard_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            values = {
                "source-run.json": self.source_run(),
                "source-artifacts.json": self.source_artifacts(),
                "manifest.json": self.manifest(),
                "reference-run.json": self.reference_run(),
                "reference-artifacts.json": self.reference_artifacts(),
            }
            for name, value in values.items():
                (root / name).write_text(json.dumps(value))
            output = root / "guard.json"
            args = [
                "real_handoff_guard.py",
                "--source-run", str(root / "source-run.json"),
                "--source-artifacts", str(root / "source-artifacts.json"),
                "--manifest", str(root / "manifest.json"),
                "--reference-run", str(root / "reference-run.json"),
                "--reference-artifacts", str(root / "reference-artifacts.json"),
                "--handoff-head-sha", "b" * 40,
                "--output", str(output),
            ]
            import sys
            old = sys.argv
            try:
                sys.argv = args
                self.assertEqual(GUARD.main(), 0)
            finally:
                sys.argv = old
            self.assertEqual(json.loads(output.read_text())["status"], "REAL_TIER1_HANDOFF_SOURCE_ACCEPTED")


class RealHandoffWorkflowTests(unittest.TestCase):
    def test_workflow_is_manual_artifact_only_and_exactly_bound(self):
        path = ROOT / ".github" / "workflows" / "surrogate-training-v2-real-tier1-handoff.yml"
        text = path.read_text()
        self.assertIn("on:\n  workflow_dispatch:", text)
        for forbidden_trigger in ("workflow_run:", "schedule:", "push:"):
            self.assertNotIn(forbidden_trigger, text)
        self.assertIn('SOURCE_RUN_ID: "30952457327"', text)
        self.assertIn('SOURCE_RUN_HEAD_SHA: "c9679a515c5f4538345d0d83252bcd8e37eb7b7e"', text)
        self.assertIn('REFERENCE_RUN_ID: "30905632743"', text)
        self.assertIn("real_handoff_guard.py", text)
        self.assertIn("tier1_handoff.py", text)
        self.assertIn("--main-sha \"$SOURCE_RUN_HEAD_SHA\"", text)
        self.assertIn("sourceArtifactCount'] == 100", text)
        self.assertIn("caseArtifactCount'] == 96", text)
        self.assertIn("authorizationPermitted'] is False", text)
        self.assertIn("tier2AutomaticallyPermitted'] is False", text)
        self.assertIn("productionPromotionAuthorized'] is False", text)
        for forbidden in ("mamba-org", "uvspec", "scientific_case_executor", "training.py", "--synthetic-only"):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
