#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util, json
from pathlib import Path
from typing import Any

STAGE1_REL=Path('experiments/tier2-stage1-execution-v1/adapter_v1.py')
MANIFEST_ID='mystic-state-0069-local-densification-execution-manifest-v1'
class Refusal(RuntimeError): pass
def req(c:bool,m:str)->None:
    if not c: raise Refusal(m)
def load(p:Path)->dict[str,Any]:
    x=json.loads(p.read_text(encoding='utf-8')); req(isinstance(x,dict),f'object required: {p}'); return x
def module(name:str,path:Path):
    s=importlib.util.spec_from_file_location(name,path); req(s is not None and s.loader is not None,f'load failure: {path}'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
def canon(v:Any)->str: return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def validate_manifest(m:dict[str,Any])->None:
    req(m.get('manifestId')==MANIFEST_ID and m.get('status')=='REVIEW_ONLY_FROZEN_TRAINING_DENSIFICATION_MANIFEST_NO_AUTHORIZATION','manifest identity drift')
    req(m.get('governance')=='MYSTIC-STATE-0069' and m.get('trainingOnly') is True,'governance/training boundary drift')
    req((m.get('scientificOrdinal'),m.get('geometryCount'),m.get('caseCount'),m.get('configuredPhotonHistories'))==(23,14,28,560000000),'manifest accounting drift')
    req(all(c.get('role')=='surrogate-training' and c.get('executionStage')=='TRAINING_DENSIFICATION' and c.get('method')=='alis' for c in m.get('cases',[])),'non-training case leaked')
    b=m.get('closedBoundaries') or {}; req(b.get('ordinal22ValuesMayBeRead') is False and b.get('protectedHoldoutOpeningAuthorized') is False and b.get('modelFitAuthorized') is False,'closed boundary opened')

def render_case(manifest_path:Path,runtime_report_path:Path,case_id:str,data_dir:Path,repository_root:Path,case_dir:Path):
    m=load(manifest_path); validate_manifest(m); rows=[c for c in m['cases'] if c.get('caseId')==case_id]; req(len(rows)==1,'case not unique'); c=rows[0]; gs=[g for g in m['geometries'] if g.get('geometryId')==c.get('geometryId')]; req(len(gs)==1,'geometry not unique'); g=gs[0]
    base=module('m0069_stage1_adapter',repository_root/STAGE1_REL); runtime=load(runtime_report_path); base.validate_runtime(m,runtime); x=base.inputs(m,c,g)
    cross=module('m0069_cross',repository_root/base.CROSS_REL); elev=module('m0069_elev',repository_root/base.ELEV_REL); rendered=cross.render_input(x,data_dir.resolve(),repository_root.resolve(),case_dir.resolve()); text,site_km,grid=elev.apply_ground_site_atm_z_grid(rendered,x['observerElevationM'])
    req('wavelength_grid_file ' not in text,'ALIS unexpectedly emitted wavelength grid file'); req(text.count('atm_z_grid ')==1 and text.count('zout 0.000000')==1,'elevated-site representation drift'); req('\naltitude ' not in '\n'+text and 'mc_elevation_file' not in text,'forbidden elevation shortcut emitted')
    p={'schemaVersion':1,'stageId':'mystic-state-0069-local-densification-prepared-v1','caseId':case_id,'geometryId':g['geometryId'],'block':c['block'],'role':'surrogate-training','seed':c['seed'],'photonHistories':c['photonHistories'],'alisSpectralImportanceSamplingNm':c['alisSpectralImportanceSamplingNm'],'executionManifestSha256':m['manifestSha256'],'inputResolvedSha256':hashlib.sha256(text.encode()).hexdigest(),'physicalInputCanonicalSha256':canon(x),'atmosphereGridKm':grid,'siteAltitudeKm':site_km,'zoutKmAboveLocalSurface':0.0,'observerElevationMechanism':'atm_z_grid','referenceStage1AdapterPath':STAGE1_REL.as_posix(),'inputs':x,'protectedHoldoutValueExposed':False}; return text,p
