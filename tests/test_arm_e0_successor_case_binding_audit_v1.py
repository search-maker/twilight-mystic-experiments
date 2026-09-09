from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "arm_e0_successor_case_binding_audit_v1" / "audit.py"
SPEC = importlib.util.spec_from_file_location("arm_e0_successor_binding_audit", MODULE_PATH)
assert SPEC and SPEC.loader
A = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(A)


def write_local_fixture(root: Path) -> None:
    for _role, (rel, tokens) in A.LOCAL_SURFACES.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(tokens) + "\n", encoding="utf-8")


def write_frozen_fixture(root: Path) -> None:
    wrapper = root / A.FROZEN_WRAPPER_PATH
    wrapper.parent.mkdir(parents=True, exist_ok=True)
    wrapper.write_text("\n".join(A.FROZEN_WRAPPER_REQUIRED_TOKENS) + "\n", encoding="utf-8")
    runner = root / A.FROZEN_RUNNER_PATH
    runner.parent.mkdir(parents=True, exist_ok=True)
    runner.write_text("\n".join(A.FROZEN_RUNNER_REQUIRED_TOKENS) + "\n", encoding="utf-8")


class SuccessorBindingAuditTests(unittest.TestCase):
    def test_actual_repository_tree_freezes_complete_local_rebind_surface(self):
        out = A.audit_source_tree(ROOT)
        self.assertEqual(out["status"], A.STATUS)
        self.assertEqual(out["legacy_case_id"], "2017-06-16_dusk")
        self.assertEqual(
            set(out["legacy_current_tree_rebind_surfaces"]),
            set(A.LOCAL_SURFACES),
        )
        self.assertEqual(out["legacy_rebind_surface_count"], 7)
        external = out["frozen_execution_source_evidence"]
        self.assertFalse(external["verified_in_this_invocation"])
        self.assertEqual(
            external["portable_wrapper"]["git_blob_sha"],
            A.FROZEN_WRAPPER_GIT_BLOB_SHA,
        )
        self.assertTrue(external["lower_frozen_runner"]["selected_case_passthrough_capable"])
        self.assertFalse(external["lower_frozen_runner"]["legacy_case_hardpin_present"])
        self.assertFalse(out["arm_network_access_performed"])
        self.assertFalse(out["protected_sws_sasze_values_read"])
        self.assertFalse(out["stage_b_authorized"])
        self.assertFalse(out["mystic_science_authorized"])

    def test_separately_materialized_frozen_ref_verifies_wrapper_and_runner(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            write_local_fixture(root)
            write_frozen_fixture(root)
            out = A.audit_source_tree(root, root)
            external = out["frozen_execution_source_evidence"]
            self.assertTrue(external["verified_in_this_invocation"])
            self.assertEqual(external["portable_wrapper"]["legacy_binding_tokens_present"], list(A.FROZEN_WRAPPER_REQUIRED_TOKENS))
            self.assertTrue(external["lower_frozen_runner"]["selected_case_passthrough_capable"])

    def test_refuses_missing_local_legacy_binding_token(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            write_local_fixture(root)
            rel, tokens = A.LOCAL_SURFACES["authorized_run_envelope"]
            path = root / rel
            path.write_text(tokens[0] + "\n", encoding="utf-8")
            with self.assertRaises(A.AuditRefusal):
                A.audit_source_tree(root)

    def test_refuses_frozen_runner_that_acquires_legacy_case_hardpin(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            write_local_fixture(root)
            write_frozen_fixture(root)
            runner = root / A.FROZEN_RUNNER_PATH
            runner.write_text(
                "\n".join(A.FROZEN_RUNNER_REQUIRED_TOKENS + A.FROZEN_RUNNER_FORBIDDEN_TOKENS) + "\n",
                encoding="utf-8",
            )
            with self.assertRaises(A.AuditRefusal):
                A.audit_source_tree(root, root)

    def test_refuses_missing_required_local_surface(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            write_local_fixture(root)
            rel, _tokens = A.LOCAL_SURFACES["downloaded_zip_digest_gate"]
            (root / rel).unlink()
            with self.assertRaises(A.AuditRefusal):
                A.audit_source_tree(root)

    def test_report_preregisters_no_science_authority(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            write_local_fixture(root)
            out = A.audit_source_tree(root)
            self.assertGreaterEqual(len(out["successor_requirements"]), 7)
            for key in (
                "arm_network_access_performed",
                "arm_credentials_read",
                "native_file_download_performed",
                "native_file_open_performed",
                "protected_sws_sasze_values_read",
                "heldout_radiance_opening_authorized",
                "stage_b_authorized",
                "mystic_science_authorized",
                "production_authorized",
            ):
                self.assertIs(out[key], False)


if __name__ == "__main__":
    unittest.main()
