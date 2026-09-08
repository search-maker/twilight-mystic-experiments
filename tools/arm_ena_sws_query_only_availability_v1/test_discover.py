#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('arm_query_discover', ROOT / 'discover.py')
assert SPEC and SPEC.loader
D = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(D)


class FakeResponse:
    def __init__(self, payload):
        self.body = json.dumps(payload).encode('utf-8')
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        return False
    def read(self):
        return self.body


class RecordingOpener:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.requests = []
    def __call__(self, request, timeout=0):
        self.requests.append((request, timeout))
        item = self.payloads.pop(0)
        if isinstance(item, BaseException):
            raise item
        return FakeResponse(item)


class QueryOnlyTests(unittest.TestCase):
    def manifest(self):
        return D.load_manifest(ROOT / D.MANIFEST_NAME)

    def test_manifest_is_exact_and_frozen(self):
        m = self.manifest()
        self.assertEqual(len(m['ordered_case_ids']), 25)
        self.assertEqual(m['ordered_case_ids'][0], '2017-06-16_dusk')
        self.assertEqual(m['ordered_case_ids'][-1], '2019-09-17_dusk')
        self.assertEqual(D.sha256_bytes((ROOT / D.MANIFEST_NAME).read_bytes()), D.EXPECTED_MANIFEST_SHA256)

    def test_stops_at_first_exact_native_match(self):
        op = RecordingOpener([
            {'files': []},
            {'files': ['https://example.invalid/not-sws.nc']},
            {'files': [
                '/opaque/path/enaswsC1.b1.20170623.000000.cdf',
                '/opaque/path/enaswsC1.b1.20170623.120000.nc',
            ]},
            {'files': ['enaswsC1.b1.20180506.should-never-query.nc']},
        ])
        r = D.discover('uid:token', self.manifest(), opener=op)
        self.assertEqual(r['status'], 'FIRST_NATIVE_FILENAME_RESOLVED')
        self.assertEqual(r['checked_case_count'], 3)
        self.assertEqual(r['first_match']['case_id'], '2017-06-23_dusk')
        self.assertEqual(r['first_match']['filenames'], [
            'enaswsC1.b1.20170623.000000.cdf',
            'enaswsC1.b1.20170623.120000.nc',
        ])
        self.assertEqual(len(op.requests), 3)
        for req, timeout in op.requests:
            self.assertEqual(timeout, 120)
            self.assertIn('/query?', req.full_url)
            self.assertNotIn('/saveData', req.full_url)

    def test_exhausts_all_25_without_match(self):
        op = RecordingOpener([{'files': []} for _ in range(25)])
        r = D.discover('uid:token', self.manifest(), opener=op)
        self.assertEqual(r['status'], 'EXHAUSTED_25_NO_NATIVE_FILENAME_RESOLVED')
        self.assertEqual(r['checked_case_count'], 25)
        self.assertIsNone(r['first_match'])
        self.assertEqual(len(op.requests), 25)

    def test_query_error_fails_closed_and_stops(self):
        op = RecordingOpener([{'files': []}, TimeoutError('secret url should not surface'), {'files': []}])
        r = D.discover('uid:token', self.manifest(), opener=op)
        self.assertEqual(r['status'], 'QUERY_ERROR_FAIL_CLOSED')
        self.assertEqual(r['checked_case_count'], 1)
        self.assertEqual(r['query_error']['ordinal'], 2)
        self.assertEqual(r['query_error']['error_type'], 'TimeoutError')
        self.assertNotIn('secret', json.dumps(r))
        self.assertEqual(len(op.requests), 2)

    def test_url_and_wrong_date_payload_cannot_leak(self):
        op = RecordingOpener([{'data': {
            'url': 'https://adc.arm.gov/armlive/query?user=uid:SUPERSECRET&ds=enaswsC1.b1',
            'files': [
                '/opaque/enaswsC1.b1.20170617.000000.nc',
                '/opaque/enaswsauxC1.b1.20170616.000000.nc',
                '/opaque/enaswsC1.b1.20170616.000000.nc',
            ],
        }}])
        r = D.discover('uid:SUPERSECRET', self.manifest(), opener=op)
        text = json.dumps(r, sort_keys=True)
        self.assertEqual(r['first_match']['filenames'], ['enaswsC1.b1.20170616.000000.nc'])
        self.assertNotIn('SUPERSECRET', text)
        self.assertNotIn('https://', text)
        self.assertNotIn('/opaque/', text)

    def test_explicit_cli_credentials_are_refused(self):
        with self.assertRaises(SystemExit):
            D.main(['--user-id=abc', '--output', 'x.json'])
        with self.assertRaises(SystemExit):
            D.main(['--access-token', 'abc', '--output', 'x.json'])

    def test_receipt_is_closed_schema_and_all_authorities_false(self):
        op = RecordingOpener([{'files': []} for _ in range(25)])
        r = D.discover('uid:token', self.manifest(), opener=op)
        self.assertEqual(set(r), D.OUTPUT_ALLOWED_KEYS)
        for key in (
            'credentials_persisted', 'native_file_download_performed', 'native_file_open_performed',
            'protected_sws_sasze_values_read', 'stage_b_authorized', 'mystic_science_authorized',
            'production_authorized',
        ):
            self.assertIs(r[key], False)

    def test_source_has_no_native_download_or_netcdf_capability(self):
        source = (ROOT / 'discover.py').read_text(encoding='utf-8')
        for forbidden in ('/saveData', 'netCDF4', 'urlretrieve(', 'download_native(', 'Dataset('):
            self.assertNotIn(forbidden, source)
        self.assertIn('BASE_URL + "/query?"', source)

    def test_main_writes_only_sanitized_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / 'receipt.json'
            with mock.patch.dict(os.environ, {'ARM_USER_ID': 'id', 'ARM_ACCESS_TOKEN': 'tok'}, clear=False), \
                 mock.patch.object(D, '_query_payload', side_effect=lambda userpair, day, opener=D.urllib.request.urlopen: {'files': []}):
                rc = D.main(['--output', str(out)])
            self.assertEqual(rc, 0)
            obj = json.loads(out.read_text(encoding='utf-8'))
            D._validate_receipt(obj, list(self.manifest()['ordered_case_ids']))
            self.assertEqual(obj['status'], 'EXHAUSTED_25_NO_NATIVE_FILENAME_RESOLVED')


if __name__ == '__main__':
    unittest.main(verbosity=2)
