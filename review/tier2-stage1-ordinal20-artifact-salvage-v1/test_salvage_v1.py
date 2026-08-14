#!/usr/bin/env python3
from __future__ import annotations
import copy, hashlib, json, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import salvage_v1 as s

class T(unittest.TestCase):
    def grid(self):
        toks=['380.00000','380.04999','380.10001','380.14999']
        raw='\n'.join(f'{t} 0 0 {i+1}' for i,t in enumerate(toks))+'\n'
        c={'nodeCount':4,'firstToken':toks[0],'lastToken':toks[-1],'tokenRegex':r'^[0-9]+\.[0-9]{5}$','canonicalTokenStreamSha256':hashlib.sha256(('\n'.join(toks)+'\n').encode()).hexdigest(),'legacyExpectedStepNm':0.05,'legacyStepToleranceNm':1e-7,'legacyRefusalMustReproduce':True}
        return raw.encode(),c
    def test_exact_serialized_grid_accepts(self):
        b,c=self.grid();r=s.parse_spectrum_bytes(b,c);self.assertFalse(r['legacyParserAccepts']);self.assertEqual(r['rowCount'],4)
    def test_radiance_mutation_does_not_change_grid_acceptance(self):
        b,c=self.grid();x=b.replace(b' 0 0 1\n',b' 9 8 7\n');self.assertEqual(s.parse_spectrum_bytes(b,c)['gridSha256'],s.parse_spectrum_bytes(x,c)['gridSha256'])
    def test_wavelength_mutation_refuses(self):
        b,c=self.grid();x=b.replace(b'380.10001',b'380.10002');
        with self.assertRaises(s.Refusal):s.parse_spectrum_bytes(x,c)
    def test_negative_radiance_refuses(self):
        b,c=self.grid();x=b.replace(b' 0 0 1\n',b' 0 0 -1\n');
        with self.assertRaises(s.Refusal):s.parse_spectrum_bytes(x,c)
    def test_contract_closed_boundaries(self):
        c=json.loads(Path('tier2-stage1-ordinal20-artifact-salvage-contract-v1.json').read_text());s.validate_contract(c);z=copy.deepcopy(c);z['boundaries']['protectedHoldoutOpeningAuthorized']=True
        with self.assertRaises(s.Refusal):s.validate_contract(z)

if __name__=='__main__':unittest.main()
