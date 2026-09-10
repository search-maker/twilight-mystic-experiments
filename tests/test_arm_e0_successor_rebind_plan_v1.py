from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "arm_e0_successor_case_binding_audit_v1" / "build_rebind_plan_v1.py"
MANIFEST_PATH = ROOT / "tools" / "arm_ena_sws_query_only_availability_v1" / "ordered_25_cases.json"
SPEC = importlib.util.spec_from_file_location("arm_e0_successor_rebind_plan", MODULE_PATH)
assert SPEC and SPEC.loader
P = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(P)

DISPATCH_SHA = "a" * 40
DISPATCH_REF = "refs/heads/main"
AUTH_COMMENT = 6000000001
AUTH_TITLE = "COORDINATOR::SYNTHETIC_UNIT_TEST_QUERY_ONLY_AUTHORIZATION"


def ordered_cases() -> list[str]:
    _manifest, cases = P.load_manifest(MANIFEST_PATH)
    return cases


def make_query(*, ordinal: int = 3) -> dict:
    cases = ordered_cases()
    checked = []
    for i in range(1, ordinal + 1):
        case = cases[i - 1]
        checked.append(
            {
                "ordinal": i,
                "case_id": case,
                "date": case[:10],
                "match_count": 1 if i == ordinal else 0,
            }
        )
    selected = cases[ordinal - 1]
    ymd = selected[:10].replace("-", "")
    return {
        "schema": 1,
        "purpose": P.QUERY_PURPOSE,
        "status": "FIRST_NATIVE_FILENAME_RESOLVED",
        "datastream": P.DATASTREAM,
        "ordered_case_manifest_sha256": P.EXPECTED_MANIFEST_SHA256,
        "ordered_case_count": P.EXPECTED_CASE_COUNT,
        "checked_case_count": ordinal,
        "checked_cases": checked,
        "first_match": {
            "ordinal": ordinal,
            "case_id": selected,
            "date": selected[:10],
            "filenames": [f"enaswsC1.b1.{ymd}.000000.nc"],
        },
        "query_error": None,
        "credentials_persisted": False,
        "native_file_download_performed": False,
        "native_file_open_performed": False,
        "protected_sws_sasze_values_read": False,
        "stage_b_authorized": False,
        "mystic_science_authorized": False,
        "production_authorized": False,
    }


def make_stress() -> dict:
    return {
        "schema": 1,
        "status": "EXACT_EXECUTABLE_STRESS_PASS",
        "purpose": P.QUERY_PURPOSE,
        "workflow_sha256": "b" * 64,
        "executable_sha256": "c" * 64,
        "ordered_case_manifest_sha256": P.EXPECTED_MANIFEST_SHA256,
        "event_name": "workflow_dispatch",
        "github_ref": DISPATCH_REF,
        "github_sha": DISPATCH_SHA,
        "default_branch": "main",
        "issue60_comment_count": 1300,
        "issue60_latest_comment_id": 6000000000,
        "issue60_ledger_sha256": "d" * 64,
        "baseline_coordinator_comment": 5000000000,
        "arm_relevant_comment_ids_after_baseline": [5000000001],
        "write_quiet_begin_ids_after_baseline": [],
        "write_quiet_end_ids_after_baseline": [],
        "arm_network_access_performed": False,
        "arm_credentials_read": False,
        "native_file_download_performed": False,
        "native_file_open_performed": False,
        "protected_sws_sasze_values_read": False,
        "stage_b_authorized": False,
        "mystic_science_authorized": False,
        "production_authorized": False,
    }


def build(**overrides):
    kwargs = {
        "query_receipt": make_query(),
        "query_receipt_sha256": "e" * 64,
        "stress_receipt": make_stress(),
        "stress_receipt_sha256": "f" * 64,
        "ordered_cases": ordered_cases(),
        "query_authorization_comment": AUTH_COMMENT,
        "query_authorization_title": AUTH_TITLE,
        "query_dispatch_ref": DISPATCH_REF,
        "query_dispatch_sha": DISPATCH_SHA,
        "query_workflow_run_id": 7000000001,
        "query_run_attempt": 1,
        "query_artifact_id": 8000000001,
        "query_artifact_digest": "sha256:" + "1" * 64,
        "stress_artifact_id": 8000000002,
        "stress_artifact_digest": "sha256:" + "2" * 64,
    }
    kwargs.update(overrides)
    return P.build_plan(**kwargs)


class SuccessorRebindPlanTests(unittest.TestCase):
    def test_actual_manifest_identity_is_frozen(self):
        manifest, cases = P.load_manifest(MANIFEST_PATH)
        self.assertEqual(manifest["purpose"], P.QUERY_PURPOSE)
        self.assertEqual(len(cases), 25)
        self.assertEqual(cases[0], "2017-06-16_dusk")

    def test_builds_result_blind_plan_without_granting_execution(self):
        out = build()
        self.assertEqual(out["status"], P.PLAN_STATUS)
        self.assertTrue(out["result_blind"])
        self.assertFalse(out["plan_is_authorization"])
        self.assertEqual(out["selected_ordinal"], 3)
        self.assertEqual(out["selected_case_id"], ordered_cases()[2])
        self.assertEqual(out["frozen_e0_source_head"], P.FROZEN_E0_SOURCE_HEAD)
        self.assertEqual(out["frozen_e0_event_universe_sha256"], P.FROZEN_E0_UNIVERSE_SHA256)
        self.assertEqual(out["rebind_surface_count"], 7)
        self.assertEqual(len(out["rebind_surfaces"]), 7)
        self.assertTrue(out["fresh_e0_execution_authorization_required"])
        self.assertFalse(out["automatic_rebind_application_performed"])
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

    def test_refuses_exhausted_query(self):
        query = make_query()
        query["status"] = "EXHAUSTED_25_NO_NATIVE_FILENAME_RESOLVED"
        with self.assertRaises(P.PlanRefusal):
            build(query_receipt=query)

    def test_refuses_query_error_status(self):
        query = make_query()
        query["status"] = "QUERY_ERROR_FAIL_CLOSED"
        query["query_error"] = "synthetic"
        with self.assertRaises(P.PlanRefusal):
            build(query_receipt=query)

    def test_refuses_earlier_positive_before_claimed_first_match(self):
        query = make_query(ordinal=3)
        query["checked_cases"][0]["match_count"] = 1
        with self.assertRaises(P.PlanRefusal):
            build(query_receipt=query)

    def test_refuses_wrong_date_filename(self):
        query = make_query()
        query["first_match"]["filenames"] = ["enaswsC1.b1.20990101.000000.nc"]
        with self.assertRaises(P.PlanRefusal):
            build(query_receipt=query)

    def test_refuses_query_schema_widening(self):
        query = make_query()
        query["unexpected"] = "widening"
        with self.assertRaises(P.PlanRefusal):
            build(query_receipt=query)

    def test_refuses_nonfresh_attempt(self):
        with self.assertRaises(P.PlanRefusal):
            build(query_run_attempt=2)

    def test_refuses_stress_dispatch_identity_mismatch(self):
        stress = make_stress()
        stress["github_sha"] = "9" * 40
        with self.assertRaises(P.PlanRefusal):
            build(stress_receipt=stress)

    def test_refuses_forbidden_query_activity_flag(self):
        query = make_query()
        query["native_file_download_performed"] = True
        with self.assertRaises(P.PlanRefusal):
            build(query_receipt=query)

    def test_refuses_forbidden_stress_activity_flag(self):
        stress = make_stress()
        stress["arm_credentials_read"] = True
        with self.assertRaises(P.PlanRefusal):
            build(stress_receipt=stress)

    def test_refuses_non_coordinator_authorization_title(self):
        with self.assertRaises(P.PlanRefusal):
            build(query_authorization_title="ARM_OWNER::NOT_AUTHORITY")

    def test_refuses_non_main_query_dispatch_ref(self):
        with self.assertRaises(P.PlanRefusal):
            build(query_dispatch_ref="refs/heads/review/arm-ena-sws-v1-stage0")

    def test_plan_does_not_reuse_legacy_e0_authority_as_future_authority(self):
        out = build()
        self.assertEqual(out["legacy_authority_must_not_be_reused"], P.LEGACY_AUTHORITY)
        serialized = str(out["rebind_surfaces"])
        self.assertNotIn(str(P.LEGACY_AUTHORITY), serialized)
        self.assertNotIn("fresh_e0_authorization_comment", out)

    def test_input_objects_are_not_mutated(self):
        query = make_query()
        stress = make_stress()
        q_before = copy.deepcopy(query)
        s_before = copy.deepcopy(stress)
        build(query_receipt=query, stress_receipt=stress)
        self.assertEqual(query, q_before)
        self.assertEqual(stress, s_before)


if __name__ == "__main__":
    unittest.main()
