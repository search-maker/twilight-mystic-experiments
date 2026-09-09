from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "arm_e0_successor_case_binding_audit_v1" / "build_rebind_plan_guarded_v2.py"
MANIFEST_PATH = ROOT / "tools" / "arm_ena_sws_query_only_availability_v1" / "ordered_25_cases.json"
SPEC = importlib.util.spec_from_file_location("arm_e0_successor_rebind_guarded_v2", MODULE_PATH)
assert SPEC and SPEC.loader
G = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(G)
P = G.P

DISPATCH_SHA = "a" * 40
DISPATCH_REF = "refs/heads/main"
BASELINE = 5000000000
AUTH_COMMENT = 6000000001
AUTH_TITLE = "COORDINATOR::ARM_REPLACEMENT_QUERY_ONLY_ONE_SHOT_AUTHORIZATION"


def ordered_cases() -> list[str]:
    _manifest, cases = P.load_manifest(MANIFEST_PATH)
    return cases


def make_query(*, ordinal: int = 3) -> dict:
    cases = ordered_cases()
    checked = []
    for i in range(1, ordinal + 1):
        case = cases[i - 1]
        checked.append({
            "ordinal": i,
            "case_id": case,
            "date": case[:10],
            "match_count": 1 if i == ordinal else 0,
        })
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
        "issue60_latest_comment_id": AUTH_COMMENT,
        "issue60_ledger_sha256": "d" * 64,
        "baseline_coordinator_comment": BASELINE,
        "arm_relevant_comment_ids_after_baseline": [5000000001, AUTH_COMMENT],
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
    return G.build_guarded_plan(**kwargs)


class GuardedRebindPlanV2Tests(unittest.TestCase):
    def test_builds_guarded_result_blind_plan(self):
        out = build()
        self.assertEqual(out["schema"], 2)
        self.assertEqual(out["status"], G.STATUS)
        self.assertTrue(out["query_authorization_bound_to_stress_ledger"])
        self.assertTrue(out["query_authorization_is_latest_arm_governance"])
        self.assertEqual(out["query_authority_binding"]["query_authorization_comment"], AUTH_COMMENT)
        self.assertFalse(out["query_authority_binding"]["legacy_authority_reused"])
        self.assertFalse(out["plan_is_authorization"])
        self.assertFalse(out["protected_sws_sasze_values_read"])
        self.assertFalse(out["stage_b_authorized"])
        self.assertFalse(out["mystic_science_authorized"])
        self.assertFalse(out["production_authorized"])

    def test_refuses_authority_absent_from_stress_arm_ledger(self):
        stress = make_stress()
        stress["arm_relevant_comment_ids_after_baseline"] = [5000000001]
        with self.assertRaises(G.GuardedPlanRefusal):
            build(stress_receipt=stress)

    def test_refuses_authority_that_is_not_latest_arm_governance(self):
        stress = make_stress()
        stress["issue60_latest_comment_id"] = AUTH_COMMENT + 1
        stress["arm_relevant_comment_ids_after_baseline"] = [5000000001, AUTH_COMMENT, AUTH_COMMENT + 1]
        with self.assertRaises(G.GuardedPlanRefusal):
            build(stress_receipt=stress)

    def test_refuses_non_arm_coordinator_title(self):
        with self.assertRaises(G.GuardedPlanRefusal):
            build(query_authorization_title="COORDINATOR::AVPS_QUERY_ONLY_AUTHORIZATION")

    def test_refuses_false_authority_title(self):
        with self.assertRaises(G.GuardedPlanRefusal):
            build(query_authorization_title="COORDINATOR::ARM_QUERY_ONLY_AUTHORITY_REMAINS_FALSE")

    def test_refuses_not_authorized_title(self):
        with self.assertRaises(G.GuardedPlanRefusal):
            build(query_authorization_title="COORDINATOR::ARM_QUERY_ONLY_NOT_AUTHORIZED")

    def test_refuses_unordered_or_duplicate_arm_governance_ids(self):
        stress = make_stress()
        stress["arm_relevant_comment_ids_after_baseline"] = [AUTH_COMMENT, 5000000001]
        with self.assertRaises(G.GuardedPlanRefusal):
            build(stress_receipt=stress)
        stress = make_stress()
        stress["arm_relevant_comment_ids_after_baseline"] = [5000000001, AUTH_COMMENT, AUTH_COMMENT]
        with self.assertRaises(G.GuardedPlanRefusal):
            build(stress_receipt=stress)

    def test_refuses_arm_governance_id_beyond_ledger_latest(self):
        stress = make_stress()
        stress["issue60_latest_comment_id"] = AUTH_COMMENT - 1
        with self.assertRaises(G.GuardedPlanRefusal):
            build(stress_receipt=stress)

    def test_refuses_consumed_legacy_authority_identity(self):
        stress = make_stress()
        stress["baseline_coordinator_comment"] = 1
        stress["issue60_latest_comment_id"] = P.LEGACY_AUTHORITY
        stress["arm_relevant_comment_ids_after_baseline"] = [P.LEGACY_AUTHORITY]
        with self.assertRaises(G.GuardedPlanRefusal):
            build(
                stress_receipt=stress,
                query_authorization_comment=P.LEGACY_AUTHORITY,
                query_authorization_title=AUTH_TITLE,
            )

    def test_v1_refusals_still_apply_after_authority_binding(self):
        with self.assertRaises(G.GuardedPlanRefusal):
            build(query_run_attempt=2)
        with self.assertRaises(G.GuardedPlanRefusal):
            build(query_dispatch_ref="refs/heads/review/arm-ena-sws-v1-stage0")


if __name__ == "__main__":
    unittest.main()
