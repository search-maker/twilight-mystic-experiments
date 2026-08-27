#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util, json
from pathlib import Path
from typing import Any

BASE_REL=Path('experiments/level-b-zenith-expansion-acquisition-v1/adapter.py')
GRID_REL=Path('review/full-spectrum-estimator-pilot-v2/wavelength-grid-1nm.dat')
RUNTIME_KEYS=('uvspecSha256','uvspecHelpSha256','libRadtranDataTreeSha256','atmosphereSha256','runtimeLockRawSha256')
class Refusal(RuntimeError):pass
def req(c,m):
 if not c:raise Refusal(m)
def load(p):
 x=json.loads(Path(p).read_text());req(isinstance(x,dict),f'object required: {p}');return x
def mod(name,p):
 s=importlib.util.spec_from_file_location(name,p);req(s and s.loader,f'load failure: {p}');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def canon(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def validate_manifest(m):
 req(m.get('manifestId')=='level-b-zenith-extension-holdout-v1','manifest identity drift')
 req(m.get('scientificExecution') is True and m.get('protectedHoldout') is True and m.get('trainingOnly') is False,'holdout boundary drift')
 req(m.get('sourceModelCanonicalSha256')=='f9202b45a6540416b3cb021425b40da27e2c9adc966edd81d3608c55826a162a','model hash drift')
 req(m.get('sourceHoldoutDesignSha256')=='2a4853910c4b3eac09bccb0995c92bb2427cae5eee1291663e47469517ffa05a','holdout design drift')
 req(m.get('geometryCount')==8 and m.get('caseCount')==32 and m.get('configuredPhotonHistories')==1_280_000_000,'accounting drift')
 x=dict(m);x['manifestSha256']=None;req(m.get('manifestSha256')==hashlib.sha256(canon(x)).hexdigest(),'manifest self hash drift')
 req([c['ordinal'] for c in m['cases']]==list(range(1,33)),'ordinal drift')
 req([c['seed'] for c in m['cases']]==list(range(2_240_000_001,2_240_000_033)),'seed ledger drift')
 req(all(c['photonHistories']==40_000_000 and c['method']=='alis' and c['alisSpectralImportanceSamplingNm']==550.0 and c['role']=='protected-holdout' for c in m['cases']),'case contract drift')
 req(len({c['caseId'] for c in m['cases']})==32 and len({g['geometryId'] for g in m['geometries']})==8,'duplicate ids')
 for g in m['geometries']:
  req(80.0<float(g['targetAltitudeDeg'])<=90.0 and 2<=float(g['sunDepressionDeg'])<=10.5,'geometry domain drift')
  req(0<=float(g['relativeAzimuthDeg'])<=180 and 0<=float(g['observerElevationM'])<=2500 and .05<=float(g['aod550'])<=.40,'geometry physical drift')
  if float(g['targetAltitudeDeg'])==90.0:req(float(g['relativeAzimuthDeg'])==0.0,'frozen exact-zenith holdout azimuth drift')
def validate_runtime(m,r):
 req(r.get('schemaVersion')==1 and r.get('stageId')=='mystic-batch-v1','runtime header drift')
 req(r.get('scientificSolverExecuted') is False and r.get('syntaxCheckExecuted') is False,'runtime probe must be pre-solver')
 for k in RUNTIME_KEYS:req(r.get(k)==m['runtimeIdentityRequired'].get(k),f'runtime identity drift: {k}')
def resolve(m,cid):
 cs=[c for c in m['cases'] if c['caseId']==cid];req(len(cs)==1,'case selection');c=cs[0]
 gs=[g for g in m['geometries'] if g['geometryId']==c['geometryId']];req(len(gs)==1,'geometry selection');return c,gs[0]
def inputs(m,c,g):
 f=m['frozenInputs'];return {'caseId':c['caseId'],'groupId':g['geometryId'],'method':'alis','block':c['block'],'seed':c['seed'],'photonHistories':c['photonHistories'],'sunDepressionDeg':g['sunDepressionDeg'],'targetAltitudeDeg':g['targetAltitudeDeg'],'relativeAzimuthDeg':g['relativeAzimuthDeg'],'observerElevationM':g['observerElevationM'],'aod550':g['aod550'],'albedo':f['albedo'],'wavelengthDomainNm':[380,780],'diagnosticNodesNm':[500,550,600],'molecularAbsorption':'crs','mcSpherical':'1D','alisSpectralImportanceSamplingNm':550.0,'solarFlux':{'root':'libRadtranData','path':'solar_flux/atlas_plus_modtran'},'wavelengthGrid':{'root':'repository','path':GRID_REL.as_posix()},'atmosphere':{'root':'libRadtranData','path':'atmmod/afglus.dat'}}
def render_case(manifest_path,runtime_report_path,case_id,data_dir,repository_root,case_dir):
 m=load(manifest_path);r=load(runtime_report_path);validate_manifest(m);validate_runtime(m,r);c,g=resolve(m,case_id);x=inputs(m,c,g)
 base=mod('zenith_base_adapter',Path(repository_root)/BASE_REL);cross=base.module('holdout_cross',Path(repository_root)/base.CROSS_REL);elev=base.module('holdout_elev',Path(repository_root)/base.ELEV_REL)
 rendered=cross.render_input(x,Path(data_dir).resolve(),Path(repository_root).resolve(),Path(case_dir).resolve());text,site_km,grid=elev.apply_ground_site_atm_z_grid(rendered,x['observerElevationM'])
 req(text.count('atm_z_grid ')==1 and text.count('zout 0.000000')==1,'ground-site elevation drift');req('\naltitude ' not in '\n'+text and 'mc_elevation_file' not in text,'forbidden elevation shortcut');req('wavelength_grid_file ' not in text,'ALIS wavelength grid drift')
 if float(x['targetAltitudeDeg'])==90.0:req(text.count('umu -1.00000000')==1,'zenith umu drift')
 p={'schemaVersion':1,'stageId':'LEVEL_B_ZENITH_EXTENSION_PROTECTED_HOLDOUT_V1','caseId':case_id,'geometryId':g['geometryId'],'role':'protected-holdout','block':c['block'],'seed':c['seed'],'photonHistories':c['photonHistories'],'manifestSha256':m['manifestSha256'],'sourceModelCanonicalSha256':m['sourceModelCanonicalSha256'],'inputResolvedSha256':hashlib.sha256(text.encode()).hexdigest(),'physicalInputCanonicalSha256':hashlib.sha256(canon(x)).hexdigest(),'observerElevationMechanism':'atm_z_grid','siteAltitudeKm':site_km,'zoutKmAboveLocalSurface':0.0,'atmosphereGridKm':grid,'targetAltitudeDeg':x['targetAltitudeDeg'],'relativeAzimuthDeg':x['relativeAzimuthDeg'],'exactZenith':float(x['targetAltitudeDeg'])==90.0,'successDoesNotAuthorizeSupportExpansion':True,'successDoesNotAuthorizeProduction':True,'inputs':x};return text,p
def prepare_case(manifest_path,runtime_report_path,case_id,data_dir,repository_root,output_root):
 d=Path(output_root)/case_id;d.mkdir(parents=True,exist_ok=False);text,p=render_case(Path(manifest_path),Path(runtime_report_path),case_id,Path(data_dir),Path(repository_root),d);(d/'input-resolved.txt').write_text(text,encoding='utf-8',newline='\n');(d/'runtime-report.json').write_bytes(Path(runtime_report_path).read_bytes());(d/'prepared.json').write_text(json.dumps(p,indent=2,sort_keys=True,allow_nan=False)+'\n');return p
