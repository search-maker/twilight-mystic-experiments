from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "arm_query_only_e0_successor_freeze_v1" / "freeze.py"
SPEC = importlib.util.spec_from_file_location("arm_freeze", MODULE_PATH)
assert SPEC and SPEC.loader
F = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(F)

CASES = [
    "2017-06-16_dusk", "2017-06-17_dusk", "2017-06-23_dusk", "2018-05-06_dusk",
    "2018-05-31_dusk", "2018-07-04_dusk", "2018-07-06_dusk", "2018-07-09_dusk",
    "2018-07-11_dusk", "2018-08-03_dusk", "2018-08-06_dusk", "2018-08-08_dusk",
    "2018-09-06_dusk", "2018-10-31_dusk", "2018-11-01_dusk", "2018-12-27_dusk",
    "2019-01-26_dusk", "2019-05-20_dusk", "2019-05-23_dusk", "2019-05-27_dusk",
    "2019-06-24_dusk", "2019-06-28_dusk", "2019-06-29_dusk", "2019-08-22_dusk",
    "2019-09-17_dusk",
]


def stress() -> dict:
    return {
        "schema": 1,
        "status": "EXACT_EXECUTABLE_STRESS_PASS",
        "purpose": F.QUERY_PURPOSE,
        "workflow_sha256": "1" * 64,
        "executable_sha256": "2" * 64,
        "ordered_case_manifest_sha256": F.EXPECTED_MANIFEST_SHA256,
        "event_name": "workflow_dispatch",
        "github_ref": F.AUTHORIZED_QUERY_REF,
        "github_sha": F.AUTHORIZED_QUERY_MAIN_SHA,
        "default_branch": "main",
        "issue60_comment_count": 1260,
        "issue60_latest_comment_id": 5593928098,
        "issue60_ledger_sha256": "3" * 64,
        "baseline_coordinator_comment": 5590748165,
        "arm_relevant_comment_ids_after_baseline": [5592250337, 5593928098],
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


def query(match_index: int = 2) -> dict:
    checked = []
    for i in range(1, match_index + 1):
        case = CASES[i - 1]
        checked.append({
            "ordinal": i,
            "case_id": case,
            "date": case[:10],
            "match_count": 1 if i == match_index else 0,
        })
    day = CASES[match_index - 1][:10]
    filename = f"enaswsC1.b1.{day.replace('-', '')}.000000.cdf"
    return {
        "schema": 1,
        "purpose": F.QUERY_PURPOSE,
        "status": "FIRST_NATIVE_FILENAME_RESOLVED",
        "datastream": F.DATASTREAM,
        "ordered_case_manifest_sha256": F.EXPECTED_MANIFEST_SHA256,
        "ordered_case_count": 25,
        "checked_case_count": match_index,
        "checked_cases": checked,
        "first_match": {
            "ordinal": match_index,
            "case_id": CASES[match_index - 1],
            "date": day,
            "filenames": [filename],
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


class FreezeTests(unittest.TestCase):
    def build(self, q=None, s=None, attempt=1):
        q = query() if q is None else q
        s = stress() if s is None else s
        return F.build_freeze(
            query_receipt=q,
            query_receipt_sha256="4" * 64,
            stress_receipt=s,
            stress_receipt_sha256="5" * 64,
            ordered_cases=CASES,
            workflow_run_id=34299999999,
            run_attempt=attempt,
            query_artifact_id=10090000001,
            query_artifact_digest="sha256:" + "6" * 64,
            stress_artifact_id=10090000002,
            stress_artifact_digest="sha256:" + "7" * 64,
        )

    def test_clean_first_match_freezes_only_selected_metadata(self):
        out = self.build()
        self.assertEqual(out["status"], "E0_SUCCESSOR_CASE_FROZEN")
        self.assertEqual(out["selected_ordinal"], 2)
        self.assertEqual(out["selected_case_id"], CASES[1])
        self.assertEqual(out["query_dispatch_sha"], F.AUTHORIZED_QUERY_MAIN_SHA)
        self.assertFalse(out["protected_sws_sasze_values_read"])
        self.assertFalse(out["stage_b_authorized"])
        self.assertFalse(out["native_file_download_authorized"])

    def test_refuses_exhausted_query(self):
        q = query()
        q["status"] = "EXHAUSTED_25_NO_NATIVE_FILENAME_RESOLVED"
        q["checked_case_count"] = 25
        q["checked_cases"] = [
            {"ordinal": i, "case_id": case, "date": case[:10], "match_count": 0}
            for i, case in enumerate(CASES, 1)
        ]
        q["first_match"] = None
        with self.assertRaises(F.FreezeRefusal):
            self.build(q=q)

    def test_refuses_query_error(self):
        q = query()
        q["status"] = "QUERY_ERROR_FAIL_CLOSED"
        q["checked_case_count"] = 0
        q["checked_cases"] = []
        q["first_match"] = None
        q["query_error"] = {"ordinal": 1, "case_id": CASES[0], "date": CASES[0][:10], "error_type": "TimeoutError"}
        with self.assertRaises(F.FreezeRefusal):
            self.build(q=q)

    def test_refuses_non_attempt1(self):
        with self.assertRaises(F.FreezeRefusal):
            self.build(attempt=2)

    def test_refuses_wrong_dispatch_sha(self):
        s = stress(); s["github_sha"] = "0" * 40
        with self.assertRaises(F.FreezeRefusal):
            self.build(s=s)

    def test_refuses_wrong_dispatch_ref(self):
        s = stress(); s["github_ref"] = "refs/heads/other"
        with self.assertRaises(F.FreezeRefusal):
            self.build(s=s)

    def test_refuses_stress_that_read_arm_credentials(self):
        s = stress(); s["arm_credentials_read"] = True
        with self.assertRaises(F.FreezeRefusal):
            self.build(s=s)

    def test_refuses_query_that_claims_native_download(self):
        q = query(); q["native_file_download_performed"] = True
        with self.assertRaises(F.FreezeRefusal):
            self.build(q=q)

    def test_refuses_earlier_positive(self):
        q = query(match_index=3); q["checked_cases"][0]["match_count"] = 1
        with self.assertRaises(F.FreezeRefusal):
            self.build(q=q)

    def test_refuses_wrong_case_order(self):
        q = query(); q["checked_cases"][0]["case_id"] = CASES[2]
        with self.assertRaises(F.FreezeRefusal):
            self.build(q=q)

    def test_refuses_filename_date_mismatch(self):
        q = query(); q["first_match"]["filenames"] = ["enaswsC1.b1.20170616.000000.cdf"]
        with self.assertRaises(F.FreezeRefusal):
            self.build(q=q)

    def test_refuses_query_extra_key(self):
        q = query(); q["radiance"] = 1.0
        with self.assertRaises(F.FreezeRefusal):
            self.build(q=q)

    def test_refuses_stress_extra_key(self):
        s = stress(); s["secret"] = "x"
        with self.assertRaises(F.FreezeRefusal):
            self.build(s=s)

    def test_refuses_bad_artifact_digest(self):
        q = query(); s = stress()
        with self.assertRaises(F.FreezeRefusal):
            F.build_freeze(
                query_receipt=q, query_receipt_sha256="4"*64,
                stress_receipt=s, stress_receipt_sha256="5"*64,
                ordered_cases=CASES, workflow_run_id=1, run_attempt=1,
                query_artifact_id=2, query_artifact_digest="6"*64,
                stress_artifact_id=3, stress_artifact_digest="sha256:"+"7"*64,
            )

    def test_repository_manifest_bytes_match_frozen_hash(self):
        path = ROOT / "tools" / "arm_ena_sws_query_only_availability_v1" / "ordered_25_cases.json"
        _, cases = F.load_manifest(path)
        self.assertEqual(cases, CASES)


if __name__ == "__main__":
    unittest.main()
