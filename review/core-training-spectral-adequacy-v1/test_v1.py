#!/usr/bin/env python3
from __future__ import annotations
import copy, json, sys, unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
import analyze_v1 as a

class SpectralAdequacyTests(unittest.TestCase):
    def test_protocol_closed(self):
        p=json.loads(Path(__file__).with_name('protocol-v1.json').read_text()); a.validate_protocol(p)
        q=copy.deepcopy(p); q['boundaries']['protectedHoldoutOpeningAuthorized']=True
        with self.assertRaises(a.Refusal): a.validate_protocol(q)
        q=copy.deepcopy(p); q['spectralAdequacy']['numericalRankRule']='DRIFT'
        with self.assertRaises(a.Refusal): a.validate_protocol(q)
    def test_projection_is_in_three_channel_nullspace(self):
        W=np.array([[1.,0.,0.,0.],[0.,1.,0.,0.],[0.,0.,1.,0.]])
        y=np.array([2.,3.,5.,7.]); r,ch=a.projection_residual(y,W)
        self.assertTrue(np.allclose(W@r,0.0,atol=1e-12)); self.assertAlmostEqual(r[3],3.5)
    def test_resolved_lost_shape_is_retained(self):
        W=np.array([[1.,0.,0.,0.],[0.,1.,0.,0.],[0.,0.,1.,0.]])
        blocks={}
        for i in range(44):
            # Same three primary channels, but a training-resolved fourth spectral degree of freedom.
            base=np.array([1.,1.,1.,1.+0.02*i])
            blocks[f'g{i:02d}']=[base+np.array([0.,0.,0.,-1e-5]),base+np.array([0.,0.,0.,1e-5])]
        r=a.spectral_pca(blocks,W,max_components=8,threshold=1.0)
        self.assertEqual(r['numericalRank'],1); self.assertEqual(r['resolvedIndices'],[0]); self.assertEqual(r['components'].shape,(1,4))
    def test_noise_only_lost_shape_is_not_retained(self):
        W=np.array([[1.,0.,0.,0.],[0.,1.,0.,0.],[0.,0.,1.,0.]])
        blocks={}
        for i in range(44):
            d=(-1.0 if i%2 else 1.0)*1e-8
            base=np.array([1.,1.,1.,1.])
            blocks[f'g{i:02d}']=[base+np.array([0.,0.,0.,-1e-3+d]),base+np.array([0.,0.,0.,1e-3+d])]
        r=a.spectral_pca(blocks,W,max_components=8,threshold=1.0)
        self.assertEqual(r['numericalRank'],1); self.assertEqual(r['resolvedIndices'],[])

if __name__=='__main__': unittest.main()
