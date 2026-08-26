#!/usr/bin/env python3
from __future__ import annotations
import copy, hashlib, importlib.util, json
from pathlib import Path
from typing import Any

CROSS_REL=Path('experiments/mystic-batch-v1/cross_geometry_adapter.py')
ELEV_REL=Path('experiments/mystic-batch-v1/twilight_surrogate_tier1_execution_adapter.py')
GRID_REL=Path('review/full-spectrum-estimator-pilot-v2/wavelength-grid-1nm.dat')
MANIFEST_ID='level-b-zenith-expansion-acquisition-v1'
RUNTIME_KEYS=('uvspecSha256','uvspecHelpSha256','libRadtranDataTreeSha256','atmosphereSha256','runtimeLockRawSha256')
TRAINING_ROLES={'boundary-training','zenith-extension-training','zenith-training'}
DIAGNOSTIC_ROLE='zenith-azimuth-invariance-diagnostic'

class Refusal(RuntimeError): pass
def req(c:bool,m:str)->None:
    if not c: raise Refusal(m)
def load(p:Path)->dict[str,Any]:
    x=json.loads(p.read_text(encoding='utf-8')); req(isinstance(x,dict),f'object required: {p}'); return x
def module(name:str,path:Path):
    req(path.is_file(),f'reviewed reference missing: {path}'); s=importlib.util.spec_from_file_location(name,path); req(s is not None and s.loader is not None,f'load failure: {path}'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
def canon(v:Any)->bytes:return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def selfhash(v:dict[str,Any],field:str)->str:
    x=copy.deepcopy(v); x[field]=None; return hashlib.sha256(canon(x)).hexdigest()

def validate_manifest(m:dict[str,Any])->None:
    req(m.get('manifestId')==MANIFEST_ID,'manifest identity drift')
    req(m.get('scientificExecution') is True and m.get('trainingOnly') is True,'manifest execution boundary drift')
    req(m.get('successDoesNotAuthorizeProduction') is True and m.get('successDoesNotAuthorizeSupportExpansion') is True,'promotion boundary drift')
    req(m.get('geometryCount')==18 and m.get('caseCount')==72 and m.get('configuredPhotonHistories')==2_040_000_000,'manifest accounting drift')
    req(m.get('manifestSha256')==selfhash(m,'manifestSha256'),'manifest self hash drift')
    geoms=m.get('geometries'); cases=m.get('cases')
    req(isinstance(geoms,list) and len(geoms)==18 and isinstance(cases,list) and len(cases)==72,'geometry/case universe drift')
    req(len({g['geometryId'] for g in geoms})==18 and len({c['caseId'] for c in cases})==72,'duplicate geometry/case')
    req([c.get('ordinal') for c in cases]==list(range(1,73)),'case ordinal drift')
    req([c.get('seed') for c in cases]==list(range(2_230_000_001,2_230_000_073)),'seed ledger drift')
    req(all(c.get('method')=='alis' and c.get('alisSpectralImportanceSamplingNm')==550.0 for c in cases),'ALIS contract drift')
    for g in geoms:
        alt=float(g['targetAltitudeDeg']); az=float(g['relativeAzimuthDeg']); role=g['role']
        req(80.0 <= alt <= 90.0,'altitude outside acquisition range')
        req(2.0 <= float(g['sunDepressionDeg']) <= 10.5,'sun depression outside Level-B design range')
        req(0.0 <= az <= 180.0 and 0.0 <= float(g['observerElevationM']) <= 2500.0 and 0.05 <= float(g['aod550']) <= 0.40,'physical geometry outside design bounds')
        req(role in TRAINING_ROLES|{DIAGNOSTIC_ROLE},'unknown role')
        if alt==90.0 and role in TRAINING_ROLES: req(az==0.0,'exact-zenith training must use canonical azimuth 0')
        if role==DIAGNOSTIC_ROLE: req(alt==90.0 and az in {90.0,180.0},'invariance diagnostic geometry drift')

def validate_runtime(m:dict[str,Any],r:dict[str,Any])->None:
    req(r.get('schemaVersion')==1 and r.get('stageId')=='mystic-batch-v1','runtime header drift')
    req(r.get('scientificSolverExecuted') is False and r.get('syntaxCheckExecuted') is False,'runtime probe must be pre-solver')
    want=m['runtimeIdentityRequired']
    for k in RUNTIME_KEYS:req(r.get(k)==want.get(k),f'runtime identity drift: {k}')

def resolve_case(m:dict[str,Any],case_id:str):
    cs=[c for c in m['cases'] if c['caseId']==case_id]; req(len(cs)==1,'case not unique'); c=cs[0]
    gs=[g for g in m['geometries'] if g['geometryId']==c['geometryId']]; req(len(gs)==1,'geometry not unique'); return c,gs[0]

def inputs(m,c,g):
    f=m['frozenInputs']
    return {
      'caseId':c['caseId'],'groupId':g['geometryId'],'method':'alis','block':c['block'],'seed':c['seed'],'photonHistories':c['photonHistories'],
      'sunDepressionDeg':g['sunDepressionDeg'],'targetAltitudeDeg':g['targetAltitudeDeg'],'relativeAzimuthDeg':g['relativeAzimuthDeg'],
      'observerElevationM':g['observerElevationM'],'aod550':g['aod550'],'albedo':f['albedo'],'wavelengthDomainNm':[380,780],
      'diagnosticNodesNm':[500,550,600],'molecularAbsorption':'crs','mcSpherical':'1D','alisSpectralImportanceSamplingNm':550.0,
      'solarFlux':{'root':'libRadtranData','path':'solar_flux/atlas_plus_modtran'},
      'wavelengthGrid':{'root':'repository','path':GRID_REL.as_posix()},'atmosphere':{'root':'libRadtranData','path':'atmmod/afglus.dat'},
    }

def render_case(manifest_path:Path,runtime_report_path:Path,case_id:str,data_dir:Path,repository_root:Path,case_dir:Path):
    m=load(manifest_path); r=load(runtime_report_path); validate_manifest(m); validate_runtime(m,r); c,g=resolve_case(m,case_id); x=inputs(m,c,g)
    cross=module('zenith_cross',repository_root/CROSS_REL); elev=module('zenith_elev',repository_root/ELEV_REL)
    rendered=cross.render_input(x,data_dir.resolve(),repository_root.resolve(),case_dir.resolve())
    text,site_km,grid=elev.apply_ground_site_atm_z_grid(rendered,x['observerElevationM'])
    req(text.count('atm_z_grid ')==1 and text.count('zout 0.000000')==1,'ground-site elevation representation drift')
    req('\naltitude ' not in '\n'+text and 'mc_elevation_file' not in text,'forbidden elevation shortcut emitted')
    req('wavelength_grid_file ' not in text,'ALIS unexpectedly emitted wavelength_grid_file')
    if float(x['targetAltitudeDeg'])==90.0:
        req(text.count('umu -1.00000000')==1,'exact zenith must render exact umu -1')
    p={'schemaVersion':1,'stageId':'LEVEL_B_ZENITH_EXPANSION_ACQUISITION_V1','caseId':case_id,'geometryId':g['geometryId'],'role':g['role'],
       'block':c['block'],'seed':c['seed'],'photonHistories':c['photonHistories'],'manifestSha256':m['manifestSha256'],
       'inputResolvedSha256':hashlib.sha256(text.encode()).hexdigest(),'physicalInputCanonicalSha256':hashlib.sha256(canon(x)).hexdigest(),
       'observerElevationMechanism':'atm_z_grid','siteAltitudeKm':site_km,'zoutKmAboveLocalSurface':0.0,'atmosphereGridKm':grid,
       'targetAltitudeDeg':x['targetAltitudeDeg'],'relativeAzimuthDeg':x['relativeAzimuthDeg'],'exactZenith':float(x['targetAltitudeDeg'])==90.0,
       'zenithAzimuthIsCoordinateOnlyNotPhysicalAtExact90':float(x['targetAltitudeDeg'])==90.0,'inputs':x,
       'successDoesNotAuthorizeSupportExpansion':True,'successDoesNotAuthorizeProduction':True}
    return text,p

def prepare_case(manifest_path:Path,runtime_report_path:Path,case_id:str,data_dir:Path,repository_root:Path,output_root:Path):
    case_dir=output_root/case_id; case_dir.mkdir(parents=True,exist_ok=False)
    text,p=render_case(manifest_path,runtime_report_path,case_id,data_dir,repository_root,case_dir)
    (case_dir/'input-resolved.txt').write_text(text,encoding='utf-8',newline='\n')
    (case_dir/'runtime-report.json').write_bytes(runtime_report_path.read_bytes())
    (case_dir/'prepared.json').write_text(json.dumps(p,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')
    return p
