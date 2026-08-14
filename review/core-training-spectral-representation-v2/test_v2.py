#!/usr/bin/env python3
from __future__ import annotations
import copy, importlib.util, json, math, sys, unittest
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE))
import analyze_v2 as a

def load_v1():
    p=ROOT/'review/core-training-spectral-adequacy-v1/analyze_v1.py'; s=importlib.util.spec_from_file_location('v1_test_module',p); assert s and s.loader; m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

class SpectralRepresentationV2Tests(unittest.TestCase):
    def test_protocol_is_closed_and_exactly_ten(self):
        p=json.loads((HERE/'protocol-v2.json').read_text()); a.validate_protocol(p)
        q=copy.deepcopy(p); q['representation']['expectedResolvedNullspacePcaComponentCount']=9
        with self.assertRaises(a.Refusal): a.validate_protocol(q)
        q=copy.deepcopy(p); q['boundaries']['protectedHoldoutOpeningAuthorized']=True
        with self.assertRaises(a.Refusal): a.validate_protocol(q)
    def test_v1_refuses_same_ten_component_fixture_and_v2_rule_retains_all_ten(self):
        v1=load_v1(); W=np.zeros((3,13),dtype=np.float64); W[0,0]=W[1,1]=W[2,2]=1.0
        blocks={}
        for i in range(44):
            coeff=np.array([math.cos(math.pi*(i+0.5)*(j+1)/44.0) for j in range(10)],dtype=np.float64)
            mean=np.concatenate([np.ones(3),1.0+0.01*coeff])
            noise=np.concatenate([np.zeros(3),np.array([(j+1)*1e-6 for j in range(10)],dtype=np.float64)])
            blocks[f'g{i:02d}']=[mean-noise,mean+noise]
        with self.assertRaises(v1.Refusal): v1.spectral_pca(blocks,W,max_components=8,threshold=1.0)
        r=v1.spectral_pca(blocks,W,max_components=10,threshold=1.0)
        self.assertEqual(r['numericalRank'],10); self.assertEqual(r['resolvedIndices'],list(range(10))); self.assertEqual(r['components'].shape,(10,13))
        self.assertLess(float(np.max(np.abs(W@r['components'].T))),1e-12)

if __name__=='__main__': unittest.main()
