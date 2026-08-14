#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util, json, struct, tempfile, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
EXEC=ROOT/'experiments/mystic-state-0069-local-densification-v1/executor_v1.py'
BUILD=ROOT/'experiments/mystic-state-0069-local-densification-v1/build_manifest_v1.py'
PROTOCOL=ROOT/'review/mystic-state-0069-local-training-densification-v1/protocol-v1.json'
BASE=ROOT/'experiments/tier2-stage1-execution-v1/stage1-execution-manifest-v1.json'
def mod(name,path):
    s=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

class TransportTests(unittest.TestCase):
    def test_float32_wavelength_serialization_matches_frozen_hash_and_parser(self):
        e=mod('m0069_exec_test',EXEC); toks=[]
        for i in range(8001):
            x=struct.unpack('f',struct.pack('f',380.0+0.05*i))[0]; toks.append(f'{x:.5f}')
        self.assertEqual(hashlib.sha256(('\n'.join(toks)+'\n').encode()).hexdigest(),e.GRID_SHA)
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'mc.rad.spc'; p.write_text(''.join(f'{t} 1.00000000e+00\n' for t in toks),encoding='utf-8'); wl,rad=e.parse_full_spectrum(p)
            self.assertEqual(len(wl),8001); self.assertEqual(len(rad),8001); self.assertEqual(wl[0],380.0); self.assertEqual(wl[-1],780.0)
    def test_manifest_builder_exact_accounting_and_closed_boundaries(self):
        b=mod('m0069_build_test',BUILD); m=b.build(json.loads(PROTOCOL.read_text()),json.loads(BASE.read_text()))
        self.assertEqual((m['geometryCount'],m['caseCount'],m['configuredPhotonHistories']),(14,28,560000000))
        self.assertEqual([c['seed'] for c in m['cases']],list(range(2100000101,2100000129)))
        self.assertTrue(all(c['role']=='surrogate-training' for c in m['cases']))
        self.assertFalse(m['closedBoundaries']['protectedHoldoutOpeningAuthorized']); self.assertFalse(m['closedBoundaries']['modelFitAuthorized'])
    def test_dispatch_branch_regex_is_exact(self):
        e=mod('m0069_exec_branch_test',EXEC); self.assertIsNotNone(e.BRANCH_RE.fullmatch('dispatch/mystic-state-0069-ordinal23-v1')); self.assertIsNone(e.BRANCH_RE.fullmatch('dispatch/mystic-state-0069-ordinal23-v2')); self.assertIsNone(e.BRANCH_RE.fullmatch('dispatch/tier2-stage2-ordinal23-v1'))

if __name__=='__main__': unittest.main()
