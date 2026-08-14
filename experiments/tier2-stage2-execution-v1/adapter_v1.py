#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util, json
from pathlib import Path
from typing import Any
STAGE1_REL=Path('experiments/tier2-stage1-execution-v1/adapter_v1.py')
class Refusal(RuntimeError):pass
def req(c,m):
    if not c:raise Refusal(m)
def load(p):
    x=json.loads(Path(p).read_text());req(isinstance(x,dict),'object required');return x
def module(name,path):
    s=importlib.util.spec_from_file_location(name,path);req(s is not None and s.loader is not None,f'load failure {path}');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def canon(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def validate_manifest(m):
    req(m.get('manifestId')=='level-b-v1-tier2-stage2-execution-manifest-v1' and m.get('status')=='REVIEW_ONLY_FROZEN_STAGE2_MANIFEST_NO_AUTHORIZATION','stage2 manifest identity drift');req(m.get('geometryCount')==6 and m.get('caseCount')==24 and m.get('configuredPhotonHistories')==720000000,'stage2 accounting drift');req(all(c.get('role')=='protected-holdout' and c.get('executionStage')=='PROTECTED_HOLDOUT_AFTER_MODEL_FREEZE' and c.get('method')=='alis' for c in m.get('cases',[])),'non-holdout case leaked')
def render_case(manifest_path:Path,runtime_report_path:Path,case_id:str,data_dir:Path,repository_root:Path,case_dir:Path):
    m=load(manifest_path);validate_manifest(m);rows=[c for c in m['cases'] if c['caseId']==case_id];req(len(rows)==1,'case not unique');c=rows[0];gs=[g for g in m['geometries'] if g['geometryId']==c['geometryId']];req(len(gs)==1,'geometry not unique');g=gs[0];base=module('stage1_adapter',repository_root/STAGE1_REL);runtime=load(runtime_report_path);base.validate_runtime(m,runtime);x=base.inputs(m,c,g);cross=module('stage2_cross',repository_root/base.CROSS_REL);elev=module('stage2_elev',repository_root/base.ELEV_REL);rendered=cross.render_input(x,data_dir.resolve(),repository_root.resolve(),case_dir.resolve());text,site_km,grid=elev.apply_ground_site_atm_z_grid(rendered,x['observerElevationM']);req('wavelength_grid_file ' not in text,'ALIS unexpectedly emitted wavelength grid file');req(text.count('atm_z_grid ')==1 and text.count('zout 0.000000')==1,'elevated-site representation drift');req('\naltitude ' not in '\n'+text and 'mc_elevation_file' not in text,'forbidden elevation shortcut emitted');p={'schemaVersion':1,'stageId':'level-b-v1-tier2-stage2-prepared-v1','caseId':case_id,'geometryId':g['geometryId'],'block':c['block'],'role':'protected-holdout','seed':c['seed'],'photonHistories':c['photonHistories'],'alisSpectralImportanceSamplingNm':c['alisSpectralImportanceSamplingNm'],'executionManifestSha256':m['manifestSha256'],'inputResolvedSha256':hashlib.sha256(text.encode()).hexdigest(),'physicalInputCanonicalSha256':canon(x),'atmosphereGridKm':grid,'siteAltitudeKm':site_km,'zoutKmAboveLocalSurface':0.0,'observerElevationMechanism':'atm_z_grid','referenceStage1AdapterPath':STAGE1_REL.as_posix(),'inputs':x};return text,p
