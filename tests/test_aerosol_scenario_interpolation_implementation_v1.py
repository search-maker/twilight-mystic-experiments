import importlib.util
import json
import pathlib
import unittest
import numpy as np

ROOT=pathlib.Path(__file__).resolve().parents[1]
MOD_PATH=ROOT/'review/aerosol-scenario-interpolation-implementation-v1/select_model_v1.py'
PROTO_PATH=ROOT/'review/aerosol-scenario-interpolation-validation-v1/protocol.review.json'
spec=importlib.util.spec_from_file_location('asiv',MOD_PATH)
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
PROTO=json.loads(PROTO_PATH.read_text())

class AerosolScenarioInterpolationImplementationV1Tests(unittest.TestCase):
    def synthetic_index(self):
        cells=[]
        for s in [2.,4.,6.,8.]:
            for alt,az,gid in [(10.,30.,'g02-early-near-low'),(30.,90.,'g04-mid-perpendicular'),(45.,180.,'g06-late-opposite-high-aerosol')]:
                for aod in [.1,.3]:
                    primary={}
                    for ci,ch in enumerate(m.CHANNELS):
                        primary[ch]={}
                        base=.02*s+.001*alt+.03*np.cos(np.radians(az))+.4*aod+.01*ci
                        for ki,c in enumerate(m.CONTRASTS):
                            v=float(base+.025*ki)
                            primary[ch][c]={'status':'FINITE_THREE_REPLICATES','mean':v,'replicateValues':[v,v,v]}
                    cells.append({'analysisCellId':f's{s}-{gid}-a{aod}','sunDepressionDeg':s,'targetAltitudeDeg':alt,'relativeAzimuthDeg':az,'aod550':aod,'primary':primary})
        return {'scientificOrdinal':38,'analysisCellCount':24,'cells':cells}
    def test_candidate_count_and_determinism(self):
        specs=m.candidate_specs(PROTO)
        self.assertEqual(len(specs),17)
        self.assertEqual(len({x['candidateId'] for x in specs}),17)
    def test_geometry_excludes_elevation(self):
        g={'sunDepressionDeg':4,'targetAltitudeDeg':30,'relativeAzimuthDeg':90,'aod550':.2,'observerElevationM':999}
        self.assertEqual(len(m.coordinate(g)),4)
    def test_training_matrix_exact_shape(self):
        r,x,y=m.extract_training(self.synthetic_index())
        self.assertEqual(len(r),24); self.assertEqual(x.shape,(24,4)); self.assertEqual(y.shape,(24,12))
    def test_selection_is_training_only_and_materializes(self):
        out=m.materialize(self.synthetic_index(),PROTO,'abc','def')
        self.assertFalse(out['holdoutValuesRead'])
        self.assertFalse(out['scientificExecutionPerformed'])
        self.assertFalse(out['solverExecutionPerformed'])
        self.assertFalse(out['ordinal39Allocated'])
        self.assertTrue(out['selectedCandidate']['eligible'])
        self.assertEqual(len(out['candidateTable']),17)
        self.assertEqual(len(out['targetNamesInOrder']),12)
        self.assertTrue(out['selfSha256'])
    def test_quantile_and_ridge_semantics_frozen(self):
        a=np.array([0.,10.,20.,30.])
        self.assertAlmostEqual(m.percentile_linear(a,.9),27.)
        x=np.asarray([[0.,0.,0.,0.],[1.,1.,1.,1.]],dtype=float)
        self.assertEqual(m.quadratic_design(x).shape,(2,15))

if __name__=='__main__': unittest.main()
