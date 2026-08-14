#!/usr/bin/env python3
from __future__ import annotations
import copy
import importlib.util
import json
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parent
TRAIN=HERE/'train_v1.py'
PREFIT=HERE.parent/'level-b-v2-training-prefit-freeze-v1/protocol-v1.json'
spec=importlib.util.spec_from_file_location('v2train',TRAIN); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

class V2ImplementationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol=json.loads(PREFIT.read_text())

    def test_candidate_count_and_order(self):
        c=mod.candidate_specs(self.protocol)
        self.assertEqual(len(c),100)
        self.assertEqual(c[0]['familyId'],'split-ridge-cos-compact')
        self.assertEqual(c[0]['primaryRidge'],1e-5)
        self.assertEqual(c[0]['shapeRidge'],1e-5)
        self.assertEqual(c[-1]['familyId'],'split-ridge-physical-poly2')
        self.assertEqual(c[-1]['primaryRidge'],0.1)
        self.assertEqual(c[-1]['shapeRidge'],0.1)

    def test_basis_dimensions(self):
        g={'sunDepressionDeg':6.0,'targetAltitudeDeg':35.0,'relativeAzimuthDeg':73.0,'observerElevationM':900.0,'aod550':0.16}
        expected={'COS_COMPACT_13_TERMS':13,'PHYSICAL_COMPACT_16_TERMS':16,'PHYSICAL_COMPACT_16_PLUS_S_A_O_CUBICS_19_TERMS':19,'FULL_DEGREE2_ON_FIVE_PHYSICAL_COORDINATES_21_TERMS':21}
        for name,n in expected.items(): self.assertEqual(len(mod.basis(g,name)),n)

    def test_synthetic_fold_counts(self):
        recs=mod.synthetic_records(); f=mod.folds(recs,self.protocol,enforce_expected_counts=False)
        self.assertEqual(len(f),59)
        self.assertEqual([len(x['val']) for x in f[:5]],[9,9,9,9,8])
        self.assertEqual(sum(1 for x in f if x['kind']=='loo'),44)

    def test_real_dataset_role_guard_rejects_opened_geometry(self):
        scales=self.protocol['sourceTrainingRepresentation']['nullspaceCoefficientScales']
        records=[]
        for i,gid in enumerate(self.protocol['roleIsolation']['exactTrainingGeometryIds']):
            g={'sunDepressionDeg':6.0,'targetAltitudeDeg':35.0,'relativeAzimuthDeg':73.0,'observerElevationM':900.0,'aod550':0.16}
            records.append({'geometryId':gid,'geometry':g,'integratedChannels':{k:{'mean':1.0+i*0.001} for k in mod.CHANNELS},'nullspacePcaCoefficients':[{'mean':0.0} for _ in scales]})
        d={'datasetSha256':mod.DATASET_CANONICAL_SHA256,'geometryCount':44,'representationFeatureCount':13,'protectedHoldoutRecordCount':0,'holdoutValuesRead':False,'records':records}
        self.assertEqual(len(mod.validate_dataset(d,self.protocol)),44)
        bad=copy.deepcopy(d); bad['records'][0]['geometryId']='train-0050'
        with self.assertRaises(mod.Refusal): mod.validate_dataset(bad,self.protocol)

if __name__=='__main__': unittest.main()
