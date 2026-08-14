import json, math, pathlib, sys, unittest
import numpy as np
ROOT=pathlib.Path(__file__).parent
sys.path.insert(0,str(ROOT))
import train_v1 as m
P=json.loads((ROOT/'protocol-v1.json').read_text())
class Tests(unittest.TestCase):
    def test_protocol(self): m.validate_protocol(P)
    def test_basis_dimensions(self):
        g={'sunDepressionDeg':6,'targetAltitudeDeg':40,'relativeAzimuthDeg':90,'observerElevationM':1000,'aod550':.2}
        self.assertEqual(len(m.basis(g,'COS_COMPACT_13_TERMS')),13)
        self.assertEqual(len(m.basis(g,'PHYSICAL_COMPACT_16_TERMS')),16)
        self.assertEqual(len(m.basis(g,'FULL_DEGREE2_ON_FIVE_COS_COORDINATES_21_TERMS')),21)
    def test_support(self):
        train=[{'sunDepressionDeg':6,'targetAltitudeDeg':40,'relativeAzimuthDeg':90,'observerElevationM':1000,'aod550':.2}]
        ok,d=m.support(train[0],train); self.assertTrue(ok); self.assertEqual(d,0)
        bad=dict(train[0]); bad['sunDepressionDeg']=10.6; ok,d=m.support(bad,train); self.assertFalse(ok); self.assertTrue(math.isinf(d))
    def test_exact_match_idw(self):
        recs=m.synthetic_records(); scales=P['sourceRepresentation']['nullspaceCoefficientScales']; model=m.fit_idw(recs,4,2,scales); got=m.predict(model,recs[3]['geometry']); want=m.targets(recs[3],scales); self.assertTrue(np.array_equal(got,want))
    def test_folds(self): self.assertEqual(len(m.folds(m.synthetic_records())),15)
    def test_synthetic_selection_deterministic(self):
        recs=m.synthetic_records(); a,ra=m.select(recs,P); b,rb=m.select(recs,P); self.assertEqual(a['familyId'],b['familyId']); self.assertEqual(a['hyperparameters'],b['hyperparameters']); self.assertEqual(a['selectionScore'],b['selectionScore']); self.assertEqual(len(ra),23)
    def test_zero_primary_refuses(self):
        rec=m.synthetic_records(44)[0]; rec['integratedChannels'][m.CHANNELS[0]]['mean']=0.0
        with self.assertRaises(m.Refusal): m.targets(rec,P['sourceRepresentation']['nullspaceCoefficientScales'])
if __name__=='__main__': unittest.main()
