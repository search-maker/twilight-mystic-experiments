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
        q=copy.deepcopy(p); q['representation']['coefficientDefinition']='DRIFT'
        with self.assertRaises(a.Refusal): a.validate_protocol(q)
        q=copy.deepcopy(p); q['boundaries']['protectedHoldoutOpeningAuthorized']=True
        with self.assertRaises(a.Refusal): a.validate_protocol(q)
    def test_zero_mean_coefficient_uncertainty_is_json_safe_null(self):
        s=a.stats([0.0,0.0,0.0,0.0])
        self.assertEqual(s['mean'],0.0); self.assertIsNone(s['relativeStandardError'])
        json.dumps(s,allow_nan=False)
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
        self.assertEqual(r['numericalRank'],10); self.assertEqual(len(r['resolvedIndices']),10); self.assertEqual(r['components'].shape,(10,13))
        self.assertLess(float(np.max(np.abs(W@r['components'].T))),1e-12)
        grand=r['grandMeanResidual']; centered=[]
        for gid in sorted(blocks):
            mean_res=np.mean(np.vstack([v1.projection_residual(y,W)[0] for y in blocks[gid]]),axis=0)
            centered.append((mean_res-grand)@r['components'].T)
        self.assertTrue(np.allclose(np.mean(np.vstack(centered),axis=0),0.0,atol=1e-12))

if __name__=='__main__': unittest.main()
