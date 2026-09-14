import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/arm_stagea_decoded_time_metadata_one_shot_v1"

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

ex = load("arm_stagea_extract_v1", TOOL / "extract.py")
pf = load("arm_stagea_preflight_v1", TOOL / "preflight.py")

class ContractIdentityTests(unittest.TestCase):
    def test_exact_frozen_contract_and_priority_hashes(self):
        self.assertEqual(ex.sha256_file(TOOL / "request_contract.json"), ex.REQUEST_SHA256)
        self.assertEqual(ex.sha256_file(TOOL / "ARM_SGP_C1_stageA_priority20.csv"), ex.PRIORITY_SHA256)
        rows = ex.load_priority(TOOL / "ARM_SGP_C1_stageA_priority20.csv")
        self.assertEqual(len(rows), 20)

    def test_exact_100_row_closed_schema(self):
        self.assertEqual(len(ex.REQUIRED_COLUMNS), 19)
        self.assertEqual(len(ex.STREAMS), 5)
        request = json.loads((TOOL / "request_contract.json").read_text())
        self.assertEqual(request["outputSchema"]["rowCount"], 100)
        self.assertEqual(tuple(request["outputSchema"]["columns"]), ex.REQUIRED_COLUMNS)
        self.assertEqual(list(request["futureAllowedReadScope"]["mandatoryStreams"]), list(ex.STREAMS))

    def test_time_summary_enforces_real_brackets_and_gap(self):
        s = ex.summarize_times([90, 100, 110, 120, 130], 100, 120)
        self.assertEqual(s["sample_count_core"], 3)
        self.assertEqual(s["left_bracket_delta_s"], 0)
        self.assertEqual(s["right_bracket_delta_s"], 0)
        self.assertTrue(s["gap_pass"])
        with self.assertRaises(ex.ExtractionError):
            ex.summarize_times([101, 110, 120], 100, 120)

    def test_duplicate_and_gap_accounting(self):
        s = ex.summarize_times([0, 1, 1, 2, 10], 1, 2)
        self.assertEqual(s["duplicate_count"], 1)
        self.assertFalse(s["gap_pass"])

    def test_cli_credentials_are_refused(self):
        for argv in (["--access-token=x"], ["--user-id", "x"], ["--token=x"], ["--user=x"]):
            with self.assertRaises(SystemExit):
                ex._reject_explicit_credentials(argv)

    def test_receipt_forbidden_flags_are_fail_closed(self):
        binding = {
            "authorization_comment_id": 1,
            "workflow_path": ex.WORKFLOW_PATH,
            "workflow_blob_sha": "a" * 40,
            "main_sha": "b" * 40,
            "event": "workflow_dispatch",
            "ref": "refs/heads/main",
            "run_id": "123",
            "run_attempt": 1,
        }
        r = ex._base_receipt(binding)
        r["status"] = "FAIL_CLOSED"; r["failure_reason"] = "TEST"
        ex.validate_receipt(r)
        r["science_arrays_read"] = True
        with self.assertRaises(ex.ExtractionError): ex.validate_receipt(r)

    def test_source_contains_no_science_variable_reads_or_model_runtime(self):
        text = (TOOL / "extract.py").read_text()
        forbidden = [
            "extinction_aerosol", "beta_a_backscatter", "sasze_vis", "radiance[", "uvspec",
            "libRadtran", "MYSTIC", "Taylor", "Jerusalem", "subprocess", "os.system",
        ]
        for needle in forbidden:
            self.assertNotIn(needle, text)
        self.assertIn('ds.variables["time"]', text)
        self.assertIn('ds.variables["base_time"]', text)
        self.assertIn('ds.variables["time_offset"]', text)
        self.assertIn('name in ds.variables', text)

class PreflightTests(unittest.TestCase):
    def _comments(self, blob, main):
        body = "\n".join([
            pf.AUTH_TITLE,
            f"workflow_path={pf.WORKFLOW_PATH}",
            f"workflow_blob_sha={blob}",
            f"main_sha={main}",
            "event=workflow_dispatch",
            "ref=refs/heads/main",
            "run_attempt=1",
            "one_shot=true",
            f"request_contract_sha256={pf.REQUEST_SHA256}",
            f"protected_scope={pf.EXPECTED_SCOPE}",
        ])
        return [{"id": 55, "created_at": "2026-09-14T20:00:00Z", "body": body, "author_association": "OWNER"}]

    def test_direct_exact_authorization_only(self):
        blob, main = "a" * 40, "b" * 40
        auth = pf.find_authorization(self._comments(blob, main), blob, main)
        self.assertEqual(auth["id"], 55)
        rows = self._comments(blob, main) + [{"id": 56, "created_at": "2026-09-14T20:01:00Z", "body": pf.REVOKE_TITLE, "author_association": "OWNER"}]
        with self.assertRaises(pf.Refusal): pf.find_authorization(rows, blob, main)

    def test_generic_cross_lane_mentions_do_not_poison_direct_classifier(self):
        blob, main = "a" * 40, "b" * 40
        rows = self._comments(blob, main) + [{"id": 56, "created_at": "2026-09-14T20:01:00Z", "body": "COORDINATOR::LOWALT\nARM is independent", "author_association": "OWNER"}]
        auth = pf.find_authorization(rows, blob, main)
        self.assertEqual(auth["id"], 55)

    def test_conflicting_duplicate_binding_refused(self):
        blob, main = "a" * 40, "b" * 40
        rows = self._comments(blob, main)
        rows[0]["body"] += "\nmain_sha=" + "c" * 40
        with self.assertRaises(pf.Refusal): pf.find_authorization(rows, blob, main)

    def test_unmatched_write_quiet_refused(self):
        begin = pf.WQ_BASELINE_COMMENT + 10
        rows = [{"id": begin, "created_at": "2026-09-14T20:00:00Z", "body": "AVPS_OWNER::WRITE_QUIET_BEGIN | stage=x", "author_association": "OWNER"}]
        with self.assertRaises(pf.Refusal): pf.reject_unmatched_write_quiet(rows)
        rows.append({"id": begin + 1, "created_at": "2026-09-14T20:01:00Z", "body": f"AVPS_OWNER::WRITE_QUIET_END | stage=x | beginComment={begin}", "author_association": "OWNER"})
        pf.reject_unmatched_write_quiet(rows)

    def test_write_quiet_conflicting_binding_and_stage_refused(self):
        begin = pf.WQ_BASELINE_COMMENT + 20
        base = [{"id": begin, "created_at": "2026-09-14T20:00:00Z", "body": "WRITE_QUIET_BEGIN | stage=x", "author_association": "OWNER"}]
        with self.assertRaises(pf.Refusal):
            pf.reject_unmatched_write_quiet(base + [{"id": begin+1, "created_at": "2026-09-14T20:01:00Z", "body": f"WRITE_QUIET_END | stage=x | begin={begin} | beginComment={begin+1}", "author_association": "OWNER"}])
        with self.assertRaises(pf.Refusal):
            pf.reject_unmatched_write_quiet(base + [{"id": begin+1, "created_at": "2026-09-14T20:01:00Z", "body": f"WRITE_QUIET_END | stage=y | begin={begin}", "author_association": "OWNER"}])

    def test_exact_historical_wq_correction_pair_passes_only_exactly(self):
        stage = "AVPS_V2_POSTCONSUMPTION_SUCCESSOR_ORDINAL46_AUTHORIZATION_REVIEW_GLOBAL_SCAN_REPLACEMENT_V2"
        common = ("branch=review/avps-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v2-20260910 | "
                  "head=2acc4d73c08f741ba76643057535d73b7ffc66bc | base=5028cb7c7cd585d720749f0d572aa15e2f614bf9 | "
                  "subject_pr=1026 | subject_head=5028cb7c7cd585d720749f0d572aa15e2f614bf9 | run=34443355962 | attempt=1 | job=102762814211 | terminal=FAILURE | artifact=NONE")
        rows = [
            {"id": pf._HISTORICAL_WQ_CORRECTION_BEGIN, "created_at": "2026-09-10T00:00:00Z", "body": f"WRITE_QUIET_BEGIN | {stage} | branch=review/avps-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v2-20260910", "author_association": "OWNER"},
            {"id": pf._HISTORICAL_WQ_PROSE_END, "created_at": "2026-09-10T00:01:00Z", "body": f"WRITE_QUIET_END | {stage} | {common}\n\nExact matching closure for BEGIN `{pf._HISTORICAL_WQ_CORRECTION_BEGIN}` only. Historical prose-bound closure.", "author_association": "OWNER"},
            {"id": pf._HISTORICAL_WQ_CANONICAL_END, "created_at": "2026-09-10T00:02:00Z", "body": f"WRITE_QUIET_END | {stage} | begin={pf._HISTORICAL_WQ_CORRECTION_BEGIN} | {common}\n\nCORRECTED MACHINE-READABLE FENCE RELEASE ONLY.", "author_association": "OWNER"},
        ]
        pf.reject_unmatched_write_quiet(rows)
        bad = [dict(x) for x in rows]
        bad[-1]["body"] = bad[-1]["body"].replace("head=2acc4d73c08f741ba76643057535d73b7ffc66bc", "head=" + "0"*40)
        with self.assertRaises(pf.Refusal): pf.reject_unmatched_write_quiet(bad)

    def test_preflight_refuses_arm_credentials_before_live_read(self):
        with mock.patch.dict(os.environ, {"ARM_USER_ID": "x"}, clear=False):
            with self.assertRaises(pf.Refusal): pf.build_receipt("pre")

if __name__ == "__main__": unittest.main()
