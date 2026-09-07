from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("verifier", HERE / "verify_oneevent_e0_artifact_v1.py")
assert SPEC and SPEC.loader
V = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(V)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(x, sort_keys=True) + "\n" for x in rows), encoding="utf-8")


def make_universe_bytes() -> bytes:
    out = ["case_id,local_civil_date,event,t_minus8_utc,t_minus7_utc,t_minus6_utc\r\n"]
    for i in range(906):
        case = V.PROBE_CASE_ID if i == 100 else f"fixture-{i:04d}_dusk"
        date = "2017-06-16" if i == 100 else "2017-01-01"
        out.append(
            f"{case},{date},dusk,2017-06-17T01:00:00Z,"
            "2017-06-17T00:55:00Z,2017-06-17T00:50:00Z\r\n"
        )
    return "".join(out).encode("utf-8")


class ArtifactFixture:
    def __init__(self, root: Path, disposition: str = "E0_PASS_BLIND_CANDIDATE"):
        self.root = root
        universe = root / "ena_sws_e0_event_universe.csv"
        universe.write_bytes(make_universe_bytes())
        self.fixture_universe_sha = sha256(universe)

        write_jsonl(root / "ena_sws_e0_query_manifest.jsonl", [{
            "case_id": V.PROBE_CASE_ID,
            "datastream": V.EXPECTED_DATASTREAM,
            "date": "20170616",
            "start": "2017-06-16",
            "end_exclusive": "2017-06-17",
            "filenames": ["enaswsC1.b1.20170616.000000.cdf"],
            "credentials_persisted": False,
        }])

        source_sha = "1" * 64
        write_jsonl(root / "ena_sws_e0_stream_schema.jsonl", [{
            "kind": "sws",
            "source_file": "enaswsC1.b1.20170616.000000.cdf",
            "source_sha256": source_sha,
            "dod_version": "fixture",
            "process_version": "fixture",
            "protected_variable_values_read": False,
            "variables": [{
                "name": "time",
                "dtype": "float64",
                "dimensions": ["time"],
                "shape": [10],
                "protected_photometric_values": False,
                "safe_qc_values_allowed": False,
                "long_name": "time",
                "standard_name": "time",
                "units": "seconds since fixture",
            }],
        }])

        write_jsonl(root / "ena_sws_e0_stream_ledger.jsonl", [{
            "case_id": V.PROBE_CASE_ID,
            "event": "dusk",
            "disposition": disposition,
            "protected_variable_values_read": False,
            "raw_sws_files_retained": False,
        }])

        write_jsonl(root / "ena_sws_e0_stream_provenance.jsonl", [{
            "case_id": V.PROBE_CASE_ID,
            "source_files": [{
                "filename": "enaswsC1.b1.20170616.000000.cdf",
                "size_bytes": 123,
                "sha256": source_sha,
            }],
            "e0_auditor_sha256": "2" * 64,
            "collector_sha256": "3" * 64,
            "protected_variable_values_read": False,
            "raw_sws_files_retained": False,
        }])

        (root / "ena_sws_e0_stream_summary.json").write_text(json.dumps({
            "schema": 1,
            "protocol": V.EXPECTED_PROTOCOL,
            "candidate_event_count": 906,
            "processed_event_count": 1,
            "remaining_event_count": 905,
            "disposition_counts": {disposition: 1},
            "raw_sws_files_retained": False,
            "protected_variable_values_read": False,
            "stage_b_authorized": False,
        }, sort_keys=True) + "\n", encoding="utf-8")
        self.refresh_receipt()

    def refresh_receipt(self) -> None:
        files = []
        for p in sorted(x for x in self.root.iterdir() if x.is_file() and x.name != "probe_receipt.json"):
            files.append({"relative_path": p.name, "size_bytes": p.stat().st_size, "sha256": sha256(p)})
        (self.root / "probe_receipt.json").write_text(json.dumps({
            "schema": 4,
            "purpose": V.EXPECTED_PURPOSE,
            "frozen_event_universe_sha256": V.FROZEN_UNIVERSE_SHA256,
            "probe_case_id": V.PROBE_CASE_ID,
            "processed_event_count": 1,
            "actual_sws_native_schema_inspected": True,
            "protected_variable_values_read": False,
            "raw_sws_files_retained": False,
            "credentials_persisted": False,
            "credentials_source": "environment_presence_only",
            "transport_errors_sanitized": True,
            "stage_b_authorized": False,
            "files": files,
        }, sort_keys=True) + "\n", encoding="utf-8")


class VerifyOneEventArtifactTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)
        self.orig_universe = V.FROZEN_UNIVERSE_SHA256
        self.fx = ArtifactFixture(self.root)
        V.FROZEN_UNIVERSE_SHA256 = self.fx.fixture_universe_sha
        self.fx.refresh_receipt()

    def tearDown(self):
        V.FROZEN_UNIVERSE_SHA256 = self.orig_universe
        self.td.cleanup()

    def reset_fixture(self, disposition: str) -> None:
        self.td.cleanup()
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)
        V.FROZEN_UNIVERSE_SHA256 = self.orig_universe
        self.fx = ArtifactFixture(self.root, disposition=disposition)
        V.FROZEN_UNIVERSE_SHA256 = self.fx.fixture_universe_sha
        self.fx.refresh_receipt()

    def test_clean_fixture_passes_and_never_authorizes_stage_b(self):
        result = V.verify(self.root)
        self.assertEqual(result["status"], "SAFE_E0_ONEEVENT_SANITIZED_ARTIFACT_VERIFIED")
        self.assertTrue(result["e0_blind_candidate_pass"])
        self.assertFalse(result["stage_b_authorized"])
        self.assertFalse(result["heldout_radiance_opening_authorized"])

    def test_nonpass_structural_qc_disposition_is_preserved_not_promoted(self):
        self.reset_fixture("E0_TIMING_FAIL")
        result = V.verify(self.root)
        self.assertEqual(result["e0_disposition"], "E0_TIMING_FAIL")
        self.assertFalse(result["e0_blind_candidate_pass"])
        self.assertFalse(result["stage_b_authorized"])

    def test_missing_never_counts_as_good(self):
        self.reset_fixture("SOURCE_FILE_MISSING")
        with self.assertRaises(V.VerificationError):
            V.verify(self.root)

    def test_refuses_raw_native_payload(self):
        (self.root / "leak.nc").write_bytes(b"not really netcdf")
        self.fx.refresh_receipt()
        with self.assertRaises(V.VerificationError):
            V.verify(self.root)

    def test_refuses_manifest_hash_mismatch(self):
        target = self.root / "ena_sws_e0_stream_summary.json"
        target.write_text(target.read_text(encoding="utf-8") + " ", encoding="utf-8")
        with self.assertRaises(V.VerificationError):
            V.verify(self.root)

    def test_refuses_manifest_path_traversal(self):
        path = self.root / "probe_receipt.json"
        receipt = json.loads(path.read_text(encoding="utf-8"))
        receipt["files"][0]["relative_path"] = "../escape.txt"
        path.write_text(json.dumps(receipt), encoding="utf-8")
        with self.assertRaises(V.VerificationError):
            V.verify(self.root)

    def test_refuses_stage_b_true(self):
        path = self.root / "ena_sws_e0_stream_summary.json"
        summary = json.loads(path.read_text(encoding="utf-8"))
        summary["stage_b_authorized"] = True
        path.write_text(json.dumps(summary), encoding="utf-8")
        self.fx.refresh_receipt()
        with self.assertRaises(V.VerificationError):
            V.verify(self.root)

    def test_refuses_protected_values_read_true(self):
        path = self.root / "ena_sws_e0_stream_schema.jsonl"
        rows = V.read_jsonl(path)
        rows[0]["protected_variable_values_read"] = True
        write_jsonl(path, rows)
        self.fx.refresh_receipt()
        with self.assertRaises(V.VerificationError):
            V.verify(self.root)

    def test_refuses_secret_bearing_url_text(self):
        path = self.root / "ena_sws_e0_query_manifest.jsonl"
        row = V.read_jsonl(path)[0]
        row["error"] = "https://adc.arm.gov/armlive/query?user=abc:secret&ds=enaswsC1.b1"
        write_jsonl(path, [row])
        self.fx.refresh_receipt()
        with self.assertRaises(V.VerificationError):
            V.verify(self.root)

    def test_refuses_unexpected_schema_value_key(self):
        path = self.root / "ena_sws_e0_stream_schema.jsonl"
        rows = V.read_jsonl(path)
        rows[0]["variables"][0]["values"] = [1, 2, 3]
        write_jsonl(path, rows)
        self.fx.refresh_receipt()
        with self.assertRaises(V.VerificationError):
            V.verify(self.root)


if __name__ == "__main__":
    unittest.main()
