from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools" / "arm_ena_sws_e0_postartifact_v1" / "verify_authorized_run_envelope_v1.py"
SPEC = importlib.util.spec_from_file_location("arm_e0_run_envelope", SOURCE)
assert SPEC is not None and SPEC.loader is not None
V = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(V)

RUN_ID = 424242
ARTIFACT_ID = 515151
DIGEST = "sha256:" + "a" * 64


def valid_run() -> dict:
    return {
        "id": RUN_ID,
        "event": "workflow_dispatch",
        "run_attempt": 1,
        "head_branch": V.FROZEN_BRANCH,
        "head_sha": V.FROZEN_HEAD,
        "path": V.WORKFLOW_PATH,
        "status": "completed",
        "conclusion": "success",
        "previous_attempt_url": None,
    }


def valid_artifacts() -> dict:
    return {
        "total_count": 1,
        "artifacts": [{
            "id": ARTIFACT_ID,
            "name": V.ARTIFACT_NAME,
            "expired": False,
            "digest": DIGEST,
            "workflow_run": {
                "id": RUN_ID,
                "head_branch": V.FROZEN_BRANCH,
                "head_sha": V.FROZEN_HEAD,
            },
        }],
    }


def valid_inventory() -> dict:
    return {
        "total_count": 1,
        "workflow_runs": [{
            "id": RUN_ID,
            "event": "workflow_dispatch",
            "run_attempt": 1,
            "head_branch": V.FROZEN_BRANCH,
            "head_sha": V.FROZEN_HEAD,
            "path": V.WORKFLOW_PATH,
        }],
    }


class AuthorizedRunEnvelopeTests(unittest.TestCase):
    def test_clean_envelope_passes_and_never_authorizes_science(self):
        result = V.verify_envelope(valid_run(), valid_artifacts(), valid_inventory())
        self.assertEqual(result["status"], "ARM_E0_AUTHORIZED_RUN_ENVELOPE_VERIFIED")
        self.assertEqual(result["authority_comment"], 5575796491)
        self.assertEqual(result["execution_branch"], V.FROZEN_BRANCH)
        self.assertEqual(result["execution_head"], V.FROZEN_HEAD)
        self.assertEqual(result["artifact_digest"], DIGEST)
        self.assertEqual(result["duplicate_e0_dispatches"], 0)
        self.assertFalse(result["protected_results_opened"])
        self.assertFalse(result["stage_b_authorized"])
        self.assertFalse(result["heldout_radiance_opening_authorized"])
        self.assertFalse(result["science_execution_authorized"])

    def test_run_identity_and_attempt_must_be_exact(self):
        cases = {
            "event": ("event", "push"),
            "attempt": ("run_attempt", 2),
            "branch": ("head_branch", "main"),
            "head": ("head_sha", "0" * 40),
            "path": ("path", ".github/workflows/other.yml"),
            "status": ("status", "in_progress"),
            "conclusion": ("conclusion", "failure"),
        }
        for label, (key, value) in cases.items():
            with self.subTest(label=label):
                run = valid_run()
                run[key] = value
                with self.assertRaises(V.EnvelopeVerificationError):
                    V.verify_envelope(run, valid_artifacts(), valid_inventory())

    def test_rerun_marker_is_refused_even_if_attempt_field_is_one(self):
        run = valid_run()
        run["previous_attempt_url"] = "https://api.github.test/attempts/0"
        with self.assertRaisesRegex(V.EnvelopeVerificationError, "rerun/retry"):
            V.verify_envelope(run, valid_artifacts(), valid_inventory())

    def test_dispatch_inventory_must_be_complete_and_unique(self):
        incomplete = valid_inventory()
        incomplete["total_count"] = 2
        with self.assertRaisesRegex(V.EnvelopeVerificationError, "not complete"):
            V.verify_envelope(valid_run(), valid_artifacts(), incomplete)

        duplicate = valid_inventory()
        second = copy.deepcopy(duplicate["workflow_runs"][0])
        second["id"] = RUN_ID + 1
        duplicate["workflow_runs"].append(second)
        duplicate["total_count"] = 2
        with self.assertRaisesRegex(V.EnvelopeVerificationError, "exactly one"):
            V.verify_envelope(valid_run(), valid_artifacts(), duplicate)

    def test_inventory_cannot_hide_head_drift_or_wrong_attempt(self):
        for key, value in (("head_sha", "f" * 40), ("run_attempt", 2), ("id", RUN_ID + 7)):
            with self.subTest(key=key):
                inventory = valid_inventory()
                inventory["workflow_runs"][0][key] = value
                with self.assertRaises(V.EnvelopeVerificationError):
                    V.verify_envelope(valid_run(), valid_artifacts(), inventory)

    def test_artifact_set_is_exactly_one_and_named(self):
        missing = {"total_count": 0, "artifacts": []}
        with self.assertRaisesRegex(V.EnvelopeVerificationError, "exactly one artifact"):
            V.verify_envelope(valid_run(), missing, valid_inventory())

        wrong = valid_artifacts()
        wrong["artifacts"][0]["name"] = "wrong-artifact"
        with self.assertRaisesRegex(V.EnvelopeVerificationError, "artifact name mismatch"):
            V.verify_envelope(valid_run(), wrong, valid_inventory())

        extra = valid_artifacts()
        extra["artifacts"].append(copy.deepcopy(extra["artifacts"][0]))
        extra["artifacts"][1]["id"] = ARTIFACT_ID + 1
        extra["total_count"] = 2
        with self.assertRaisesRegex(V.EnvelopeVerificationError, "exactly one artifact"):
            V.verify_envelope(valid_run(), extra, valid_inventory())

    def test_artifact_must_be_live_digest_bound_to_exact_run_and_head(self):
        mutations = (
            ("expired", True),
            ("digest", None),
            ("digest", "sha256:" + "A" * 64),
        )
        for key, value in mutations:
            with self.subTest(key=key, value=value):
                payload = valid_artifacts()
                payload["artifacts"][0][key] = value
                with self.assertRaises(V.EnvelopeVerificationError):
                    V.verify_envelope(valid_run(), payload, valid_inventory())

        for key, value in (("id", RUN_ID + 1), ("head_branch", "main"), ("head_sha", "e" * 40)):
            with self.subTest(workflow_run_key=key):
                payload = valid_artifacts()
                payload["artifacts"][0]["workflow_run"][key] = value
                with self.assertRaises(V.EnvelopeVerificationError):
                    V.verify_envelope(valid_run(), payload, valid_inventory())

    def test_artifact_count_metadata_cannot_be_inconsistent(self):
        payload = valid_artifacts()
        payload["total_count"] = 2
        with self.assertRaisesRegex(V.EnvelopeVerificationError, "total_count"):
            V.verify_envelope(valid_run(), payload, valid_inventory())


if __name__ == "__main__":
    unittest.main()
