#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util, json
from pathlib import Path
from typing import Any

CONTRACT_REL=Path('review/tier2-stage2-protected-holdout-v1/contract-v1.json')
CORE_REL=Path('review/tier2-stage2-protected-holdout-v1/stage2_v1.py')
CROSS_REL=Path('experiments/mystic-batch-v1/cross_geometry_adapter.py')
ELEV_REL=Path('experiments/mystic-batch-v1/twilight_surrogate_tier1_execution_adapter.py')
GRID_REL=Path('review/full-spectrum-estimator-pilot-v2/wavelength-grid-1nm.dat')
RUNTIME_KEYS=('uvspecSha256','uvspecHelpSha256','libRadtranDataTreeSha256','atmosphereSha256','runtimeLockRawSha256')
class Refusal(RuntimeError): pass
def req(c:bool,m:str)->None:
    if not c: raise Refusal(m)
def load(p:Path)->dict[str,Any]:
    x=json.loads(p.read_text(encoding='utf-8')); req(isinstance(x,dict),f'object required: {p}'); return x
def module(name:str,path:Path):
    req(path.is_file(),f'reviewed reference missing: {path}'); s=importlib.util.spec_from_file_location(name,path); req(s is not None and s.loader is not None,f'reference load failure: {path}'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
def canon(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def validate_runtime(contract:dict[str,Any],runtime:dict[str,Any])->None:
    req(runtime.get('schemaVersion')==1 and runtime.get('stageId')=='mystic-batch-v1' and runtime.get('scientificSolverExecuted') is False and runtime.get('syntaxCheckExecuted') is False,'runtime report header drift')
    want=contract['runtimeIdentityRequired']
    for k in RUNTIME_KEYS:req(runtime.get(k)==want.get(k),f'runtime identity drift: {k}')

def resolve(contract:dict[str,Any],case_id:str)->tuple[dict[str,Any],dict[str,Any]]:
    core=module('stage2_core',Path(__file__).resolve().parents[2]/CORE_REL); cases=core.expected_cases(contract); rows=[x for x in cases if x['caseId']==case_id]; req(len(rows)==1,'case not unique'); c=rows[0]; gs=[x for x in contract['stage2Scope']['geometries'] if x['geometryId']==c['geometryId']]; req(len(gs)==1,'geometry not unique'); return c,gs[0]
def physical_inputs(contract:dict[str,Any],c:dict[str,Any],g:dict[str,Any])->dict[str,Any]:
    out={'caseId':c['caseId'],'groupId':g['geometryId'],'method':'alis','block':c['block'],'seed':c['seed'],'photonHistories':c['photonHistories'],'sunDepressionDeg':g['sunDepressionDeg'],'targetAltitudeDeg':g['targetAltitudeDeg'],'relativeAzimuthDeg':g['relativeAzimuthDeg'],'observerElevationM':g['observerElevationM'],'aod550':g['aod550'],'albedo':0.15,'wavelengthDomainNm':[380.0,780.0],'diagnosticNodesNm':[500.0,550.0,600.0],'molecularAbsorption':'crs','mcSpherical':'1D','alisSpectralImportanceSamplingNm':c['alisSpectralImportanceSamplingNm'],'solarFlux':{'root':'libRadtranData','path':'solar_flux/atlas_plus_modtran'},'wavelengthGrid':{'root':'repository','path':GRID_REL.as_posix()},'atmosphere':{'root':'libRadtranData','path':'atmmod/afglus.dat'}}
    req(2<=out['sunDepressionDeg']<=10.5 and 5<=out['targetAltitudeDeg']<=80 and 0<=out['relativeAzimuthDeg']<=180 and 0<=out['observerElevationM']<=2500 and .05<=out['aod550']<=.4,'physical input outside frozen v1 design box'); req(out['alisSpectralImportanceSamplingNm'] in (500.0,550.0,600.0),'ALIS importance wavelength drift'); return out

def render_case(contract_path:Path,runtime_path:Path,case_id:str,data_dir:Path,repository_root:Path,case_dir:Path)->tuple[str,dict[str,Any]]:
    contract=load(contract_path); core=module('stage2_core_validate',repository_root/CORE_REL); core.validate_contract(contract); runtime=load(runtime_path); validate_runtime(contract,runtime); c,g=resolve(contract,case_id); x=physical_inputs(contract,c,g)
    cross=module('stage2_ref_cross',repository_root/CROSS_REL); elev=module('stage2_ref_elev',repository_root/ELEV_REL); rendered=cross.render_input(x,data_dir.resolve(),repository_root.resolve(),case_dir.resolve()); text,site_km,grid=elev.apply_ground_site_atm_z_grid(rendered,x['observerElevationM'])
    req('wavelength_grid_file ' not in text,'ALIS unexpectedly emitted wavelength grid file'); req(text.count('atm_z_grid ')==1 and text.count('zout 0.000000')==1,'elevated-site representation drift'); req('\naltitude ' not in '\n'+text and 'mc_elevation_file' not in text,'forbidden elevation shortcut emitted')
    prep={'schemaVersion':1,'stageId':'level-b-v1-tier2-stage2-prepared-v1','caseId':case_id,'geometryId':g['geometryId'],'block':c['block'],'role':'protected-holdout','seed':c['seed'],'photonHistories':c['photonHistories'],'alisSpectralImportanceSamplingNm':c['alisSpectralImportanceSamplingNm'],'contractId':contract['contractId'],'inputResolvedSha256':hashlib.sha256(text.encode()).hexdigest(),'physicalInputCanonicalSha256':canon(x),'atmosphereGridKm':grid,'siteAltitudeKm':site_km,'zoutKmAboveLocalSurface':0.0,'observerElevationMechanism':'atm_z_grid','referenceCrossGeometryAdapterPath':CROSS_REL.as_posix(),'referenceTier1AltitudeAdapterPath':ELEV_REL.as_posix(),'inputs':x}; return text,prep
