import unittest

from scripts.avps_write_quiet_parser_v1 import _write_quiet_end_records
from scripts.avps_write_quiet_parser_v1 import is_write_quiet_begin
from scripts.avps_write_quiet_parser_v1 import record_write_quiet_end
from scripts.avps_write_quiet_parser_v1 import write_quiet_end_binding


class CanonicalWriteQuietParserV1Test(unittest.TestCase):
    def test_marker_and_standalone_aliases(self):
        for key in ('begin','beginComment','begin_comment'):
            with self.subTest(key=key,surface='marker'):
                self.assertEqual(write_quiet_end_binding('WRITE_QUIET_END | stage=x | '+key+'=123'),123)
            with self.subTest(key=key,surface='standalone'):
                self.assertEqual(write_quiet_end_binding('WRITE_QUIET_END | stage=x\n'+key+'=123'),123)

    def test_structured_standalone_overrides_legacy_marker_fallback(self):
        self.assertEqual(write_quiet_end_binding('WRITE_QUIET_END | begin=999 | stage=legacy\nbeginComment=123'),123)

    def test_historical_multiline_and_legacy_one_line(self):
        self.assertEqual(write_quiet_end_binding('WRITE_QUIET_END | stage=x\nbeginComment=5562775627'),5562775627)
        self.assertEqual(write_quiet_end_binding('WRITE_QUIET_END begin=5471141095 stage=x'),5471141095)

    def test_repeated_identical_authoritative_aliases_canonicalize(self):
        self.assertEqual(write_quiet_end_binding('WRITE_QUIET_END | stage=x\nbegin=123\nbeginComment=123\nbegin_comment=123'),123)
        self.assertEqual(write_quiet_end_binding('WRITE_QUIET_END | begin=123 | beginComment=123'),123)

    def test_owner_aware_exact_first_line_grammar(self):
        self.assertEqual(write_quiet_end_binding('TOTAL_SKY_OWNER::WRITE_QUIET_END | stage=x\nbegin_comment=123'),123)
        for body in ('header\nWRITE_QUIET_END | beginComment=123','prose WRITE_QUIET_END | beginComment=123','`WRITE_QUIET_END | beginComment=123`','header\n> WRITE_QUIET_END | beginComment=123'):
            with self.subTest(body=body):
                self.assertIsNone(write_quiet_end_binding(body))
        for body in ('WRITE_QUIET_BEGIN | stage=x','TOTAL_SKY_OWNER::WRITE_QUIET_BEGIN | stage=x','ATMOSPHERE_OWNER::WRITE_QUIET_BEGIN token=x'):
            with self.subTest(body=body):
                self.assertTrue(is_write_quiet_begin(body))
        for body in ('prose WRITE_QUIET_BEGIN | stage=x','Total_Sky_OWNER::WRITE_QUIET_BEGIN | stage=x','header\nTOTAL_SKY_OWNER::WRITE_QUIET_BEGIN | stage=x'):
            with self.subTest(body=body):
                self.assertFalse(is_write_quiet_begin(body))

    def test_malformed_zero_nondecimal_conflict_fail_closed(self):
        for body in ('WRITE_QUIET_END | stage=x','WRITE_QUIET_END | stage=x\nbeginComment=0','WRITE_QUIET_END | stage=x\nbeginComment=abc','WRITE_QUIET_END | stage=x\nbegin=123\nbeginComment=124'):
            with self.subTest(body=body):
                with self.assertRaises(SystemExit):
                    write_quiet_end_binding(body)

    def test_true_duplicates_and_mismatches_fail_closed(self):
        closed=set()
        self.assertTrue(record_write_quiet_end('WRITE_QUIET_END | beginComment=123',200,{123},closed))
        with self.assertRaises(SystemExit):
            record_write_quiet_end('WRITE_QUIET_END | beginComment=123',201,{123},closed)
        with self.assertRaises(SystemExit):
            record_write_quiet_end('WRITE_QUIET_END | beginComment=999',202,{123},set())
        with self.assertRaises(SystemExit):
            record_write_quiet_end('WRITE_QUIET_END | beginComment=300',250,{300},set())

    def test_exact_historical_corrected_pair_is_only_duplicate_exception(self):
        predecessor='WRITE_QUIET_END | LUNAR_FINITE_DISK_EXEC001_FINAL_PREFLIGHT_GLOBAL_SCAN_V1 | begin_comment=5467776090 | branch=execution/lunar-finite-disk-transfer-kernel-sensitivity-v1-exec001 | head=b73d5cf4a58aee3b3e8794b396b79bbd3463f680 | run=33303099872 | attempt=1 | preflight_job=99234734783 | conclusion=success | artifact=9729769639 | digest=sha256:50b9acdf55ebe3188a3f7762c79e0365a9b5c58d5bf2c1b877244b340c9773b8 | 2026-08-30T09:22Z'
        correction_line='WRITE_QUIET_END | LUNAR_FINITE_DISK_EXEC001_FINAL_PREFLIGHT_GLOBAL_SCAN_V1 | begin=5467776090 | head=b73d5cf4a58aee3b3e8794b396b79bbd3463f680 | run=33303099872 | attempt=1 | preflight_job=99234734783 | conclusion=success | artifact=9729769639 | digest=sha256:50b9acdf55ebe3188a3f7762c79e0365a9b5c58d5bf2c1b877244b340c9773b8 | 2026-08-30T09:27Z'
        correction_prose='CORRECTED MACHINE-READABLE FENCE RELEASE: the prior END comment `5467858336` used the human-readable key `begin_comment=` whereas the frozen workflow barrier requires the literal token `begin=`. This comment changes no scientific result, seed, execution identity, threshold, or preflight evidence; it supplies the exact already-preregistered release token after the successful immutable preflight.'
        canonical=correction_line+'\n\n'+correction_prose
        closed=set()
        record_write_quiet_end(predecessor,5467858336,{5467776090},closed)
        record_write_quiet_end(canonical,5467875147,{5467776090},closed)
        record=_write_quiet_end_records(closed)[5467776090]
        self.assertEqual(record['comment_id'],5467875147)
        self.assertEqual(tuple(record['superseded_comment_ids']),(5467858336,))

        for candidate in (canonical.replace('run=33303099872','run=33303099873'),canonical.replace('`5467858336`','`5467858335`')):
            trial=set()
            record_write_quiet_end(predecessor,5467858336,{5467776090},trial)
            with self.assertRaises(SystemExit):
                record_write_quiet_end(candidate,5467875147,{5467776090},trial)

        generic=set()
        record_write_quiet_end('WRITE_QUIET_END | beginComment=123',200,{123},generic)
        with self.assertRaises(SystemExit):
            record_write_quiet_end('WRITE_QUIET_END | beginComment=123',201,{123},generic)


if __name__ == '__main__':
    unittest.main()
