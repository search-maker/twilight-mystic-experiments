#!/usr/bin/env python3
from __future__ import annotations
import hashlib, io, json, math, sys, unittest, zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import analyze_source_binding_fix_v1 as a

def artifact_bytes(*,gid='train-0014',rich=False,sza='99.000000',umu='-0.91433250',phi='158.400000',atm='0.102041',aod='0.148347',phi0='0.00',zout='0.000000',case_prefix=''):
    case=f'{case_prefix}{gid}-case-b1'
    text='\n'.join([
        'wavelength 380 780',f'sza {sza}',f'phi0 {phi0}','rte_solver mystic',
        'mc_basename /tmp/'+case+'/mc',f'aerosol_set_tau_at_wvl 550 {aod}',
        f'atm_z_grid {atm} 1.000000 2.000000',f'zout {zout}',f'umu {umu}',f'phi {phi}','quiet',''])
    h=hashlib.sha256(text.encode()).hexdigest()
    p={'caseId':case,'inputResolvedSha256':h,'stageId':'synthetic'}
    if rich:
        p['geometryId']=gid
        p['inputs']={
            'groupId':gid,
            'sunDepressionDeg':float(sza)-90.0,
            'targetAltitudeDeg':math.degrees(math.asin(-float(umu))),
            'relativeAzimuthDeg':float(phi),
            'observerElevationM':1000.0*float(atm)+0.0002,
            'aod550':float(aod),
        }
    b=io.BytesIO()
    with zipfile.ZipFile(b,'w') as z:
        z.writestr('input-resolved.txt',text)
        z.writestr('prepared.json',json.dumps(p))
    return b.getvalue()

class SourceBindingFixTests(unittest.TestCase):
    def test_protocol_is_closed(self):
        p=json.loads((HERE/'protocol-v1.json').read_text())
        a.validate_protocol(p)
        p['correction']['snrThresholdChanged']=True
        with self.assertRaises(a.Refusal): a.validate_protocol(p)
    def test_minimal_prepared_falls_back_to_exact_input(self):
        x=a.prepared_inputs(artifact_bytes())
        self.assertEqual(x['geometryId'],'train-0014')
        self.assertAlmostEqual(x['geometry']['sunDepressionDeg'],9.0)
        self.assertAlmostEqual(x['geometry']['targetAltitudeDeg'],math.degrees(math.asin(0.91433250)))
        self.assertAlmostEqual(x['geometry']['observerElevationM'],102.041)
        self.assertAlmostEqual(x['geometry']['aod550'],0.148347)
    def test_rich_prepared_cross_checks_serialized_input(self):
        x=a.prepared_inputs(artifact_bytes(gid='train-0052',rich=True,sza='94.750000',umu='-0.80018893',phi='74.880000',atm='1.078717',aod='0.316116',case_prefix='tier2-core-v1-'))
        self.assertEqual(x['geometryId'],'train-0052')
        self.assertAlmostEqual(x['geometry']['targetAltitudeDeg'],53.14814762939317)
        self.assertAlmostEqual(x['geometry']['observerElevationM'],1078.717)
    def test_prepared_hash_mismatch_refuses(self):
        raw=artifact_bytes()
        b=io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(raw)) as zin, zipfile.ZipFile(b,'w') as zout:
            for n in zin.namelist():
                if n=='prepared.json':
                    p=json.loads(zin.read(n)); p['inputResolvedSha256']='0'*64; zout.writestr(n,json.dumps(p))
                else: zout.writestr(n,zin.read(n))
        with self.assertRaises(a.Refusal): a.prepared_inputs(b.getvalue())
    def test_nonzero_phi0_or_zout_refuses(self):
        with self.assertRaises(a.Refusal): a.prepared_inputs(artifact_bytes(phi0='1.0'))
        with self.assertRaises(a.Refusal): a.prepared_inputs(artifact_bytes(zout='0.1'))
    def test_geometry_identity_ambiguity_refuses(self):
        raw=artifact_bytes(gid='train-0014')
        b=io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(raw)) as zin, zipfile.ZipFile(b,'w') as zout:
            for n in zin.namelist():
                if n=='prepared.json':
                    p=json.loads(zin.read(n)); p['geometryId']='train-0052'; zout.writestr(n,json.dumps(p))
                else: zout.writestr(n,zin.read(n))
        with self.assertRaises(a.Refusal): a.prepared_inputs(b.getvalue())

if __name__=='__main__': unittest.main()
