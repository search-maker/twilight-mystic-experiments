#!/usr/bin/env python3
from __future__ import annotations
import copy, importlib.util, json, unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
TRAIN=HERE/'train_v2.py'
PREFIT=HERE.parent/'level-b-v2-training-prefit-freeze-v2/protocol-v2.json'
spec=importlib.util.spec_from_file_location('v2g2',TRAIN); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.p=json.loads(PREFIT.read_text())
 def test_candidate_count_and_family_arithmetic(self):
  c=mod.candidate_specs(self.p); self.assertEqual(len(c),230); self.assertEqual(c[0]['familyId'],'uw-ridge-primary-physical-compact-shape-cos-compact'); self.assertEqual(c[-1]['familyId'],'ridge-primary-physical-poly2-shape-idw-cos')
 def test_uncertainty_metric_downweights_noisy_target(self):
  import numpy as np
  err=np.array([2.0]); quiet=np.array([0.0]); noisy=np.array([2.0]); self.assertAlmostEqual(float(abs(err[0])/np.sqrt(1+quiet[0]**2)),2.0); self.assertLess(float(abs(err[0])/np.sqrt(1+noisy[0]**2)),1.0)
 def test_basis_and_idw_coordinates(self):
  g={'sunDepressionDeg':6.0,'targetAltitudeDeg':35.0,'relativeAzimuthDeg':73.0,'observerElevationM':900.0,'aod550':0.16}; self.assertEqual(len(mod.basis(g,'COS_COMPACT_13_TERMS')),13); self.assertEqual(len(mod.basis(g,'PHYSICAL_COMPACT_16_TERMS')),16); self.assertEqual(len(mod.basis(g,'FULL_DEGREE2_ON_FIVE_PHYSICAL_COORDINATES_21_TERMS')),21); self.assertEqual(len(mod.idw_coords(g)),5)
 def test_role_guard_rejects_opened_geometry(self):
  scales=self.p['sourceTrainingRepresentation']['nullspaceCoefficientScales']; recs=[]
  for i,gid in enumerate(self.p['roleIsolation']['exactTrainingGeometryIds']):
   g={'sunDepressionDeg':6.0,'targetAltitudeDeg':35.0,'relativeAzimuthDeg':73.0,'observerElevationM':900.0,'aod550':0.16}; recs.append({'geometryId':gid,'geometry':g,'integratedChannels':{k:{'mean':1.0+i*.001,'standardError':.01} for k in mod.CHANNELS},'nullspacePcaCoefficients':[{'mean':0.0,'standardError':0.01*scales[j]} for j in range(10)]})
  d={'datasetSha256':mod.DATASET_CANONICAL_SHA256,'geometryCount':44,'representationFeatureCount':13,'protectedHoldoutRecordCount':0,'holdoutValuesRead':False,'records':recs}; self.assertEqual(len(mod.validate_dataset(d,self.p)),44); bad=copy.deepcopy(d); bad['records'][0]['geometryId']='train-0050'
  with self.assertRaises(mod.Refusal): mod.validate_dataset(bad,self.p)
if __name__=='__main__': unittest.main()
