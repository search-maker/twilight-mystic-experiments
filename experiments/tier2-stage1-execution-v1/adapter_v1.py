#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util, json
from pathlib import Path
from typing import Any

MANIFEST_ID='public-tier2-v1-core-stage1-execution-manifest-v1'
RUNTIME_KEYS=('uvspecSha256','uvspecHelpSha256','libRadtranDataTreeSha256','atmosphereSha256','runtimeLockRawSha256')
CROSS_REL=Path('experiments/mystic-batch-v1/cross_geometry_adapter.py')
ELEV_REL=Path('experiments/mystic-batch-v1/twilight_surrogate_tier1_execution_adapter.py')
GRID_REL=Path('review/full-spectrum-estimator-pilot-v2/wavelength-grid-1nm.dat')
class Refusal(RuntimeError): pass
def req(c:bool,m:str)->None:
    if not c: raise Refusal(m)
def load(p:Path)->dict[str,Any]:
    x=json.loads(p.read_text(encoding='utf-8')); req(isinstance(x,dict),f'object required: {p}'); return x
def canon(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def module(name:str,path:Path):
    req(path.is_file(),f'reviewed reference missing: {path}'); s=importlib.util.spec_from_file_location(name,path); req(s is not None and s.loader is not None,f'reviewed reference load failure: {path}'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

def validate_manifest(m:dict[str,Any])->None:
    req(m.get('manifestId')==MANIFEST_ID and m.get('status')=='REVIEW_ONLY_FROZEN_STAGE1_EXECUTION_MANIFEST_NO_AUTHORIZATION','manifest identity drift')
    req(m.get('trainingOnly') is True and m.get('geometryCount')==19 and m.get('caseCount')==76 and m.get('configuredPhotonHistories')==2_120_000_000,'stage1 accounting drift')
    req((m.get('closedBoundaries') or {}).get('stage2Included') is False and (m.get('closedBoundaries') or {}).get('protectedHoldoutOpeningAuthorized') is False,'holdout boundary drift')
    req(all(c.get('role')=='surrogate-training' and c.get('executionStage')=='TRAINING_ACQUISITION' and c.get('method')=='alis' for c in m.get('cases',[])),'non-training case leaked')
def validate_runtime(m:dict[str,Any],r:dict[str,Any])->None:
    req(r.get('schemaVersion')==1 and r.get('stageId')=='mystic-batch-v1' and r.get('scientificSolverExecuted') is False and r.get('syntaxCheckExecuted') is False,'runtime header drift')
    want=m.get('runtimeIdentityRequired') or {}
    for k in RUNTIME_KEYS:req(r.get(k)==want.get(k),f'runtime identity drift: {k}')
def resolve_case(m:dict[str,Any],case_id:str)->tuple[dict[str,Any],dict[str,Any]]:
    rows=[x for x in m['cases'] if x.get('caseId')==case_id]; req(len(rows)==1,'case not unique'); c=rows[0]; gs=[x for x in m['geometries'] if x.get('geometryId')==c.get('geometryId')]; req(len(gs)==1,'geometry not unique'); return c,gs[0]
def inputs(m:dict[str,Any],c:dict[str,Any],g:dict[str,Any])->dict[str,Any]:
    f=m['frozenInputs']; out={'caseId':c['caseId'],'groupId':g['geometryId'],'method':'alis','block':c['block'],'seed':c['seed'],'photonHistories':c['photonHistories'],'sunDepressionDeg':g['sunDepressionDeg'],'targetAltitudeDeg':g['targetAltitudeDeg'],'relativeAzimuthDeg':g['relativeAzimuthDeg'],'observerElevationM':g['observerElevationM'],'aod550':g['aod550'],'albedo':f['albedo'],'wavelengthDomainNm':f['wavelengthDomainNm'],'diagnosticNodesNm':[500.0,550.0,600.0],'molecularAbsorption':f['molecularAbsorption'],'mcSpherical':f['mcSpherical'],'alisSpectralImportanceSamplingNm':c['alisSpectralImportanceSamplingNm'],'solarFlux':{'root':'libRadtranData','path':'solar_flux/atlas_plus_modtran'},'wavelengthGrid':{'root':'repository','path':GRID_REL.as_posix()},'atmosphere':{'root':'libRadtranData','path':'atmmod/afglus.dat'}}
    req(2.0<=out['sunDepressionDeg']<=10.5 and 5.0<=out['targetAltitudeDeg']<=80.0 and 0.0<=out['relativeAzimuthDeg']<=180.0 and 0.0<=out['observerElevationM']<=2500.0 and 0.05<=out['aod550']<=0.40,'physical input outside v1 design box')
    req(out['alisSpectralImportanceSamplingNm'] in (500.0,550.0,600.0) and out['wavelengthDomainNm']==[380.0,780.0] and out['molecularAbsorption']=='crs' and out['mcSpherical']=='1D','numerical/spectral input drift'); return out

def render_case(manifest_path:Path,runtime_report_path:Path,case_id:str,data_dir:Path,repository_root:Path,case_dir:Path)->tuple[str,dict[str,Any]]:
    m=load(manifest_path); r=load(runtime_report_path); validate_manifest(m); validate_runtime(m,r); c,g=resolve_case(m,case_id); x=inputs(m,c,g)
    cross=module('tier2_ref_cross_geometry',repository_root/CROSS_REL); elev=module('tier2_ref_elevation',repository_root/ELEV_REL)
    rendered=cross.render_input(x,data_dir.resolve(),repository_root.resolve(),case_dir.resolve())
    text,site_km,grid=elev.apply_ground_site_atm_z_grid(rendered,x['observerElevationM'])
    req('wavelength_grid_file ' not in text,'ALIS unexpectedly emitted wavelength grid file'); req(text.count('atm_z_grid ')==1 and text.count('zout 0.000000')==1,'elevated-site representation drift'); req('\naltitude ' not in '\n'+text and 'mc_elevation_file' not in text,'forbidden elevation shortcut emitted')
    p={'schemaVersion':1,'stageId':'public-tier2-v1-core-stage1-prepared-v1','caseId':case_id,'geometryId':g['geometryId'],'block':c['block'],'role':c['role'],'seed':c['seed'],'photonHistories':c['photonHistories'],'alisSpectralImportanceSamplingNm':c['alisSpectralImportanceSamplingNm'],'executionManifestSha256':m['manifestSha256'],'inputResolvedSha256':hashlib.sha256(text.encode()).hexdigest(),'physicalInputCanonicalSha256':canon(x),'atmosphereGridKm':grid,'siteAltitudeKm':site_km,'zoutKmAboveLocalSurface':0.0,'observerElevationMechanism':'atm_z_grid','referenceCrossGeometryAdapterPath':CROSS_REL.as_posix(),'referenceTier1AltitudeAdapterPath':ELEV_REL.as_posix(),'inputs':x}; return text,p

def prepare_case(manifest_path:Path,runtime_report_path:Path,case_id:str,data_dir:Path,repository_root:Path,output_root:Path)->dict[str,Any]:
    case_dir=output_root/case_id; case_dir.mkdir(parents=True,exist_ok=False); text,p=render_case(manifest_path,runtime_report_path,case_id,data_dir,repository_root,case_dir); (case_dir/'input-resolved.txt').write_text(text,encoding='utf-8',newline='\n'); (case_dir/'runtime-report.json').write_bytes(runtime_report_path.read_bytes()); (case_dir/'randomseed').write_text(f"{p['seed']}\n",encoding='utf-8'); (case_dir/'prepared.json').write_text(json.dumps(p,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n',encoding='utf-8'); return p
