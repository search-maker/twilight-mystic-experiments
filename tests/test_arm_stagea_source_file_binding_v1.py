import json
import unittest

from tools.arm_stagea_source_file_binding_v1 import verify as v


class StageASourceFileBindingV1Tests(unittest.TestCase):
    PREFIX = {
        "sasze_filterbands": "sgpsaszefilterbandsC1.a1.",
        "hsrl": "sgphsrlC1.a1.",
        "rlprofbe": "sgprlprofbeC1.c1.",
        "arscl": "sgparsclkazr1kolliasC1.c0.",
        "ceil": "sgpceilC1.b1.",
    }

    def make_rows(self):
        rows = []
        for i in range(20):
            case_id = f"2024-02-{i + 1:02d}_{'dusk' if i % 2 == 0 else 'dawn'}"
            for stream in v.continuity.EXPECTED_STREAMS:
                rows.append(
                    {
                        "case_id": case_id,
                        "stream": stream,
                        "source_files": json.dumps(
                            [f"{self.PREFIX[stream]}202402{i + 1:02d}.000000.nc"],
                            separators=(",", ":"),
                        ),
                    }
                )
        return rows

    def test_valid_exact_datastream_bindings(self):
        receipt = v.verify_source_file_bindings(self.make_rows())
        self.assertTrue(receipt["source_file_binding_valid"])
        self.assertEqual(receipt["row_count"], 100)
        self.assertEqual(receipt["case_count"], 20)
        self.assertEqual(receipt["checked_source_file_count"], 100)
        self.assertFalse(receipt["upstream_continuity_contract_pass_inferred"])
        self.assertFalse(receipt["scientific_pass_inferred"])
        self.assertFalse(receipt["heldout_sws_sasze_radiance_opened"])
        self.assertFalse(receipt["stage_b_authorized"])

    def test_stream_alias_is_accepted_but_native_prefix_stays_exact(self):
        rows = self.make_rows()
        rows[0]["stream"] = "sgpsaszefilterbandsC1.a1"
        receipt = v.verify_source_file_bindings(rows)
        self.assertTrue(receipt["source_file_binding_valid"])

    def test_rejects_full_sasze_file_under_filterbands_label(self):
        rows = self.make_rows()
        rows[0]["source_files"] = json.dumps(["sgpsaszeC1.a1.20240201.000000.nc"])
        with self.assertRaises(v.SourceBindingError):
            v.verify_source_file_bindings(rows)

    def test_rejects_sws_file_under_filterbands_label(self):
        rows = self.make_rows()
        rows[0]["source_files"] = json.dumps(["sgpswsC1.b1.20240201.000000.nc"])
        with self.assertRaises(v.SourceBindingError):
            v.verify_source_file_bindings(rows)

    def test_rejects_other_permitted_stream_file_under_wrong_label(self):
        rows = self.make_rows()
        rows[0]["source_files"] = json.dumps(["sgphsrlC1.a1.20240201.000000.nc"])
        with self.assertRaises(v.SourceBindingError):
            v.verify_source_file_bindings(rows)

    def test_rejects_local_or_absolute_path(self):
        for bad in (
            "/tmp/sgpsaszefilterbandsC1.a1.20240201.000000.nc",
            "native/sgpsaszefilterbandsC1.a1.20240201.000000.nc",
            r"C:\\data\\sgpsaszefilterbandsC1.a1.20240201.000000.nc",
        ):
            with self.subTest(bad=bad):
                rows = self.make_rows()
                rows[0]["source_files"] = json.dumps([bad])
                with self.assertRaises(v.SourceBindingError):
                    v.verify_source_file_bindings(rows)

    def test_rejects_non_native_extension(self):
        rows = self.make_rows()
        rows[0]["source_files"] = json.dumps(["sgpsaszefilterbandsC1.a1.20240201.000000.cdf"])
        with self.assertRaises(v.SourceBindingError):
            v.verify_source_file_bindings(rows)

    def test_exact_twenty_by_five_shape_is_required(self):
        rows = self.make_rows()[:-1]
        with self.assertRaises(v.SourceBindingError):
            v.verify_source_file_bindings(rows)

    def test_duplicate_case_stream_is_rejected(self):
        rows = self.make_rows()
        rows[-1] = dict(rows[0])
        with self.assertRaises(v.SourceBindingError):
            v.verify_source_file_bindings(rows)


if __name__ == "__main__":
    unittest.main()
