from __future__ import annotations

import hashlib
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
    MANIFEST_SHA = "c" * 64
    DESCRIPTOR_SHA = "d" * 64

    def manifest(self) -> dict:
        return {
            "schemaVersion": 1,
            "stageId": "twilight-surrogate-tier-1-execution-v1",
            "proposalOnly": True,
            "scientificExecution": False,
            "cases": [{"caseId": f"case-{index:04d}"} for index in range(96)],
        }

    def source_identity(self) -> dict:
        return {
            "id": 41000000003,
            "workflowId": 410003,
            "runNumber": 3,
            "runAttempt": 1,
            "event": "workflow_dispatch",
            "headBranch": "main",
            "headSha": "a" * 40,
            "path": ".github/workflows/twilight-surrogate-tier-1-ordinal3-execution.yml",
            "displayTitle": (
                "MYSTIC batch v1 | key=twilight-surrogate-tier-1-v1:numerical:3 | "
                f"auth={'e' * 40} | ordinal=3"
            ),
            "executionKey": "twilight-surrogate-tier-1-v1:numerical:3",
            "authorizationOrdinal": 3,
            "authorizationRef": "e" * 40,
        }

    @staticmethod
    def artifact(artifact_id: int, name: str, digest_char: str = "a") -> dict:
        return {
            "id": artifact_id,
            "name": name,
            "expired": False,
            "digest": "sha256:" + digest_char * 64,
        }

    def artifact_names(self) -> list[str]:
        prefix = "twilight-surrogate-tier-1-ordinal3-case-"
        return [
            "twilight-surrogate-tier-1-ordinal3-execution-preflight",
            "twilight-surrogate-tier-1-ordinal3-aggregate",
            "twilight-surrogate-tier-1-ordinal3-audit",
            "twilight-surrogate-tier-1-ordinal3-analysis",
            *(f"{prefix}case-{index:04d}" for index in range(96)),
        ]

    def descriptor(self) -> dict:
        return {
            "schemaVersion": 1,
            "stageId": GUARD.DESCRIPTOR_STAGE,
            "status": GUARD.DESCRIPTOR_STATUS,
            "proposalOnly": True,
            "automaticDispatch": False,
            "sourceRun": self.source_identity(),
            "sourceArtifacts": [self.artifact(index + 1, name) for index, name in enumerate(self.artifact_names())],
            "manifestRawSha256": self.MANIFEST_SHA,
            "manifestRelativePath": "evidence/ordinal3-manifest.json",
            "preflightArtifactName": "twilight-surrogate-tier-1-ordinal3-execution-preflight",
            "aggregateArtifactName": "twilight-surrogate-tier-1-ordinal3-aggregate",
            "auditArtifactName": "twilight-surrogate-tier-1-ordinal3-audit",
            "analysisArtifactName": "twilight-surrogate-tier-1-ordinal3-analysis",
            "caseArtifactPrefix": "twilight-surrogate-tier-1-ordinal3-case-",
            "caseCount": 96,
            "artifactCount": 100,
            "surrogateTrainingAuthorized": False,
            "internalHoldoutOpeningAuthorized": False,
            "tier2Authorized": False,
            "productionPromotionAuthorized": False,
            "boundary": "proposal-only exact future source binding; no dispatch or downstream authorization",
        }

    def source_run(self) -> dict:
        source = self.source_identity()
        return {
            "id": source["id"],
            "workflow_id": source["workflowId"],
            "run_number": source["runNumber"],
            "run_attempt": 1,
            "event": "workflow_dispatch",
            "status": "completed",
            "conclusion": "success",
            "head_branch": "main",
            "head_sha": source["headSha"],
            "path": source["path"],
            "display_title": source["displayTitle"],
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

    def source_artifacts(self) -> dict:
        return {
            "total_count": 100,
            "artifacts": [self.artifact(index + 1, name) for index, name in enumerate(self.artifact_names())],
        }

    def reference_artifacts(self) -> dict:
        return {
            "total_count": 1,
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
            "source_descriptor": self.descriptor(),
            "source_run": self.source_run(),
            "source_artifacts": self.source_artifacts(),
            "manifest": self.manifest(),
            "reference_run": self.reference_run(),
            "reference_artifacts": self.reference_artifacts(),
            "source_descriptor_raw_sha256": self.DESCRIPTOR_SHA,
            "manifest_raw_sha256": self.MANIFEST_SHA,
        }
        values.update(overrides)
        return GUARD.validate(**values, handoff_head_sha="b" * 40)

    def test_future_attempt1_exact_source_reaches_handoff_guard(self):
        report = self.validate()
        self.assertEqual(report["status"], "REAL_TIER1_HANDOFF_SOURCE_ACCEPTED")
        self.assertEqual(report["sourceRunId"], self.source_identity()["id"])
        self.assertEqual(report["sourceExecutionKey"], "twilight-surrogate-tier-1-v1:numerical:3")
        self.assertEqual(report["sourceAuthorizationOrdinal"], 3)
        self.assertEqual(report["sourceArtifactCount"], 100)
        self.assertEqual(report["caseArtifactCount"], 96)
        self.assertFalse(report["surrogateTrainingAuthorized"])
        self.assertFalse(report["internalHoldoutOpeningAuthorized"])
        self.assertFalse(report["tier2Authorized"])
        self.assertFalse(report["productionPromotionAuthorized"])

    def test_consumed_ordinal2_identity_is_permanently_refused(self):
        descriptor = self.descriptor()
        source = descriptor["sourceRun"]
        source.update(
            {
                "id": 30952457327,
                "executionKey": "twilight-surrogate-tier-1-v1:numerical:2",
                "authorizationOrdinal": 2,
                "displayTitle": (
                    "MYSTIC batch v1 | key=twilight-surrogate-tier-1-v1:numerical:2 | "
                    f"auth={source['authorizationRef']} | ordinal=2"
                ),
            }
        )
        with self.assertRaisesRegex(GUARD.GuardRefusal, "consumed historical"):
            self.validate(source_descriptor=descriptor)

    def test_each_consumed_identity_dimension_is_independently_refused(self):
        cases = (
            ("id", 30906913329),
            ("executionKey", "twilight-surrogate-tier-1-v1:numerical:1"),
            ("authorizationOrdinal", 1),
        )
        for field, value in cases:
            descriptor = self.descriptor()
            source = descriptor["sourceRun"]
            source[field] = value
            source["displayTitle"] = (
                f"MYSTIC batch v1 | key={source['executionKey']} | auth={source['authorizationRef']} | "
                f"ordinal={source['authorizationOrdinal']}"
            )
            if field == "authorizationOrdinal":
                descriptor["caseArtifactPrefix"] = "twilight-surrogate-tier-1-ordinal1-case-"
                for item in descriptor["sourceArtifacts"]:
                    item["name"] = item["name"].replace("ordinal3-case-", "ordinal1-case-")
            with self.subTest(field=field), self.assertRaisesRegex(GUARD.GuardRefusal, "consumed historical"):
                self.validate(source_descriptor=descriptor)

    def test_refuses_nonterminal_retried_or_failed_source(self):
        for field, value in (("status", "in_progress"), ("run_attempt", 2), ("conclusion", "failure")):
            run = self.source_run()
            run[field] = value
            with self.subTest(field=field), self.assertRaises(GUARD.GuardRefusal):
                self.validate(source_run=run)

    def test_refuses_missing_extra_or_digest_drifted_source_artifact(self):
        missing = self.source_artifacts()
        missing["artifacts"].pop()
        with self.assertRaises(GUARD.GuardRefusal):
            self.validate(source_artifacts=missing)

        extra = self.source_artifacts()
        extra["artifacts"].append(self.artifact(1001, "unexpected-artifact"))
        with self.assertRaises(GUARD.GuardRefusal):
            self.validate(source_artifacts=extra)

        drifted = self.source_artifacts()
        drifted["artifacts"][0]["digest"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(GUARD.GuardRefusal, "source artifact"):
            self.validate(source_artifacts=drifted)

        hidden_extra_page = self.source_artifacts()
        hidden_extra_page["total_count"] = 101
        with self.assertRaisesRegex(GUARD.GuardRefusal, "artifact total"):
            self.validate(source_artifacts=hidden_extra_page)

        boolean_id = self.source_artifacts()
        boolean_id["artifacts"][0]["id"] = True
        with self.assertRaisesRegex(GUARD.GuardRefusal, "artifact ID"):
            self.validate(source_artifacts=boolean_id)

    def test_refuses_descriptor_artifact_universe_or_manifest_hash_drift(self):
        descriptor = self.descriptor()
        descriptor["sourceArtifacts"].pop()
        with self.assertRaisesRegex(GUARD.GuardRefusal, "exactly 100"):
            self.validate(source_descriptor=descriptor)
        with self.assertRaisesRegex(GUARD.GuardRefusal, "manifest raw hash"):
            self.validate(manifest_raw_sha256="0" * 64)

        broad_prefix = self.descriptor()
        broad_prefix["caseArtifactPrefix"] = "twilight-surrogate-tier-1-ordinal3-"
        broad_prefix["sourceArtifacts"] = [
            {
                **item,
                "name": item["name"].replace(
                    "twilight-surrogate-tier-1-ordinal3-case-",
                    "twilight-surrogate-tier-1-ordinal3-",
                ),
            }
            for item in broad_prefix["sourceArtifacts"]
        ]
        with self.assertRaisesRegex(GUARD.GuardRefusal, "case artifact prefix"):
            self.validate(source_descriptor=broad_prefix)

    def test_refuses_reference_drift(self):
        reference = self.reference_artifacts()
        reference["artifacts"][0]["digest"] = "sha256:" + "0" * 64
        with self.assertRaises(GUARD.GuardRefusal):
            self.validate(reference_artifacts=reference)

    def test_template_is_deliberately_unbound_and_refused(self):
        template = json.loads(
            (ROOT / "modeling" / "surrogate-training-v2" / "future-tier1-source-descriptor-template.json").read_text()
        )
        with self.assertRaises(GUARD.GuardRefusal):
            GUARD.validate_descriptor(template)

    def test_descriptor_resolution_checks_raw_hash_and_exports_exact_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            descriptor_path = Path(tmp) / "descriptor.json"
            descriptor_path.write_text(json.dumps(self.descriptor(), sort_keys=True))
            digest = hashlib.sha256(descriptor_path.read_bytes()).hexdigest()
            values = GUARD.descriptor_environment(self.descriptor(), descriptor_path, digest)
            self.assertEqual(values["SOURCE_RUN_ID"], str(self.source_identity()["id"]))
            self.assertEqual(values["SOURCE_DESCRIPTOR_RAW_SHA256"], digest)
            self.assertEqual(values["SOURCE_CASE_PATTERN"], "twilight-surrogate-tier-1-ordinal3-case-*")
            with self.assertRaisesRegex(GUARD.GuardRefusal, "raw hash mismatch"):
                GUARD.descriptor_environment(self.descriptor(), descriptor_path, "0" * 64)

    def test_descriptor_repository_path_refuses_escape_and_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scoped = root / "modeling" / "surrogate-training-v2"
            scoped.mkdir(parents=True)
            descriptor = scoped / "future-tier1-source-ordinal3.json"
            descriptor.write_text("{}")
            relative = descriptor.relative_to(root)
            self.assertEqual(GUARD.validate_descriptor_repository_path(relative, root), descriptor.resolve())
            outside = root / "future-tier1-source-outside.json"
            outside.write_text("{}")
            with self.assertRaisesRegex(GUARD.GuardRefusal, "outside"):
                GUARD.validate_descriptor_repository_path(outside.relative_to(root), root)
            link = scoped / "future-tier1-source-link.json"
            try:
                link.symlink_to(descriptor)
            except OSError:
                self.skipTest("symlink creation unavailable")
            with self.assertRaisesRegex(GUARD.GuardRefusal, "non-symlink"):
                GUARD.validate_descriptor_repository_path(link.relative_to(root), root)

    def test_cli_writes_guard_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(self.manifest()))
            descriptor = self.descriptor()
            descriptor["manifestRawSha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
            descriptor_path = root / "descriptor.json"
            descriptor_path.write_text(json.dumps(descriptor))
            descriptor_sha = hashlib.sha256(descriptor_path.read_bytes()).hexdigest()
            values = {
                "source-run.json": self.source_run(),
                "source-artifacts.json": self.source_artifacts(),
                "reference-run.json": self.reference_run(),
                "reference-artifacts.json": self.reference_artifacts(),
            }
            for name, value in values.items():
                (root / name).write_text(json.dumps(value))
            output = root / "guard.json"
            args = [
                "real_handoff_guard.py",
                "--source-descriptor", str(descriptor_path),
                "--source-descriptor-raw-sha256", descriptor_sha,
                "--source-run", str(root / "source-run.json"),
                "--source-artifacts", str(root / "source-artifacts.json"),
                "--manifest", str(manifest_path),
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
    def test_workflow_is_manual_artifact_only_and_future_source_bound(self):
        path = ROOT / ".github" / "workflows" / "surrogate-training-v2-real-tier1-handoff.yml"
        text = path.read_text()
        self.assertIn("on:\n  workflow_dispatch:\n    inputs:", text)
        for forbidden_trigger in ("workflow_run:", "schedule:", "push:"):
            self.assertNotIn(forbidden_trigger, text)
        self.assertIn("source_descriptor_path:", text)
        self.assertIn("source_descriptor_raw_sha256:", text)
        self.assertNotIn('SOURCE_RUN_ID: "30952457327"', text)
        self.assertIn("--resolve-descriptor", text)
        self.assertIn("--source-descriptor-raw-sha256", text)
        self.assertIn("modeling/surrogate-training-v2/future-tier1-source-*.json", text)
        self.assertIn("git ls-files --error-unmatch", text)
        self.assertIn('test "$GITHUB_REF" = "refs/heads/main"', text)
        self.assertIn("awk '{print $1}'", text)
        self.assertIn('REFERENCE_RUN_ID: "30905632743"', text)
        self.assertIn("real_handoff_guard.py", text)
        self.assertIn("tier1_handoff.py", text)
        self.assertIn('--main-sha "$SOURCE_RUN_HEAD_SHA"', text)
        self.assertIn("sourceArtifactCount'] == 100", text)
        self.assertIn("caseArtifactCount'] == 96", text)
        self.assertIn("guard['sourceRunId'] != 30952457327", text)
        self.assertIn("surrogateTrainingAuthorized'] is False", text)
        self.assertIn("tier2Authorized'] is False", text)
        self.assertIn("productionPromotionAuthorized'] is False", text)
        for forbidden in ("mamba-org", "uvspec", "scientific_case_executor", "training.py", "--synthetic-only"):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
