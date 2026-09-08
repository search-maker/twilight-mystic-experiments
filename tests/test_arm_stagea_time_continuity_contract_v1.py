import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.arm_stagea_time_continuity_contract_v1 import verify as v


class StageATimeContinuityContractV1Tests(unittest.TestCase):
    def make_priority(self, root: Path) -> Path:
        path = root / "ARM_SGP_C1_stageA_priority20.csv"
        fields = ["local_civil_date", "event", "t_minus6_utc", "t_minus8_utc"]
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for i in range(20):
                day = i + 1
                w.writerow(
                    {
                        "local_civil_date": f"2024-02-{day:02d}",
                        "event": "dusk" if i % 2 == 0 else "dawn",
                        "t_minus6_utc": f"2024-02-{day:02d}T00:10:00.000000Z",
                        "t_minus8_utc": f"2024-02-{day:02d}T00:20:00.000000Z",
                    }
                )
        return path

    def make_rows(self):
        rows = []
        for i in range(20):
            day = i + 1
            event = "dusk" if i % 2 == 0 else "dawn"
            case_id = f"2024-02-{day:02d}_{event}"
            for stream in v.EXPECTED_STREAMS:
                rows.append(
                    {
                        "case_id": case_id,
                        "stream": stream,
                        "core_start_utc": f"2024-02-{day:02d}T00:10:00.000000Z",
                        "core_end_utc": f"2024-02-{day:02d}T00:20:00.000000Z",
                        "source_files": json.dumps([f"{stream}.{day:02d}.nc"], separators=(",", ":")),
                        "source_sha256s": json.dumps([hashlib.sha256(f"{stream}-{day}".encode()).hexdigest()], separators=(",", ":")),
                        "decoded_time_basis": "time + units/calendar",
                        "code_version": "2.6.7" if stream == "hsrl" else "",
                        "sample_count_core": "10",
                        "left_bracket_utc": f"2024-02-{day:02d}T00:09:59.000000Z",
                        "right_bracket_utc": f"2024-02-{day:02d}T00:20:01.000000Z",
                        "left_bracket_delta_s": "1.0",
                        "right_bracket_delta_s": "1.0",
                        "median_positive_cadence_s": "10.0",
                        "max_gap_s": "20.0",
                        "duplicate_count": "0",
                        "nonfinite_or_masked_count": "0",
                        "continuity_pass": "PASS",
                        "failure_reason": "",
                    }
                )
        return rows

    def write_pair(self, root: Path, rows):
        csv_path = root / "stageA_actual_time_continuity_v2.csv"
        json_path = root / "stageA_actual_time_continuity_v2.json"
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=v.REQUIRED_COLUMNS)
            w.writeheader()
            w.writerows(rows)
        json_rows = []
        for row in rows:
            item = dict(row)
            item["source_files"] = json.loads(item["source_files"])
            item["source_sha256s"] = json.loads(item["source_sha256s"])
            json_rows.append(item)
        json_path.write_text(json.dumps(json_rows, indent=2) + "\n", encoding="utf-8")
        return csv_path, json_path

    def run_contract(self, mutate=None):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        priority = self.make_priority(root)
        rows = self.make_rows()
        if mutate:
            mutate(rows)
        csv_path, json_path = self.write_pair(root, rows)
        priority_hash = hashlib.sha256(priority.read_bytes()).hexdigest()
        with mock.patch.object(v, "EXPECTED_PRIORITY_SHA256", priority_hash):
            cases = v.load_priority_cases(priority)
            csv_rows = v.load_csv_rows(csv_path)
            json_rows = v.load_json_rows(json_path)
            v.verify_json_equivalence(csv_rows, json_rows)
            return v.verify_rows(csv_rows, cases)

    def test_valid_all_pass_contract(self):
        receipt = self.run_contract()
        self.assertTrue(receipt["artifact_contract_valid"])
        self.assertEqual(receipt["row_count"], 100)
        self.assertEqual(receipt["case_pass_count"], 20)
        self.assertFalse(receipt["scientific_pass_inferred"])
        self.assertFalse(receipt["heldout_radiance_opening_authorized"])
        self.assertFalse(receipt["stage_b_authorized"])
        self.assertFalse(receipt["science_execution_authorized"])

    def test_real_fail_row_is_preserved_not_promoted(self):
        def mutate(rows):
            rows[0]["continuity_pass"] = "FAIL"
            rows[0]["failure_reason"] = "source native gap exceeds frozen gate"
            rows[0]["max_gap_s"] = "21.0"

        receipt = self.run_contract(mutate)
        self.assertTrue(receipt["artifact_contract_valid"])
        self.assertEqual(receipt["case_pass_count"], 19)
        self.assertEqual(receipt["case_fail_count"], 1)
        self.assertFalse(receipt["missing_native_data_counts_as_pass"])

    def test_declared_pass_cannot_exceed_two_cadence_gap(self):
        def mutate(rows):
            rows[0]["max_gap_s"] = "20.0001"

        with self.assertRaises(v.ContractError):
            self.run_contract(mutate)

    def test_declared_pass_requires_brackets_on_both_sides(self):
        def mutate(rows):
            rows[0]["left_bracket_utc"] = "2024-02-01T00:10:01.000000Z"
            rows[0]["left_bracket_delta_s"] = "0.0"

        with self.assertRaises(v.ContractError):
            self.run_contract(mutate)

    def test_hsrl_pass_requires_corrected_267(self):
        def mutate(rows):
            hsrl = next(row for row in rows if row["stream"] == "hsrl")
            hsrl["code_version"] = "2.6.5"

        with self.assertRaises(v.ContractError):
            self.run_contract(mutate)

    def test_time_coverage_metadata_cannot_be_decode_basis(self):
        def mutate(rows):
            rows[0]["decoded_time_basis"] = "global time_coverage_start/end"

        with self.assertRaises(v.ContractError):
            self.run_contract(mutate)

    def test_source_hash_pairing_is_required(self):
        def mutate(rows):
            rows[0]["source_sha256s"] = json.dumps([])

        with self.assertRaises(v.ContractError):
            self.run_contract(mutate)

    def test_fail_requires_reason(self):
        def mutate(rows):
            rows[0]["continuity_pass"] = "FAIL"

        with self.assertRaises(v.ContractError):
            self.run_contract(mutate)

    def test_exact_case_stream_matrix_required(self):
        def mutate(rows):
            rows[-1]["stream"] = "ceil" if rows[-1]["stream"] != "ceil" else "hsrl"

        with self.assertRaises(v.ContractError):
            self.run_contract(mutate)


if __name__ == "__main__":
    unittest.main()
