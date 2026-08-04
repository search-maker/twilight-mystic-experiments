#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util, json
from pathlib import Path
from typing import Any
STAGE_ID='twilight-surrogate-tier-1-execution-v1';ADAPTER_ID='mystic-twilight-tier1-execution-v1';BASE=Path(__file__).with_name('cross_geometry_adapter.py');ALLOWED={500.0,550.0,600.0}
class AdapterError(RuntimeError):pass
def load(p:Path)->dict[str,Any]:
 v=json.loads(p.read_text());
 if not isinstance(v,dict):raise AdapterError(f'expected object: {p}')
 return v
def dump(v:Any)->str:return json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+'\n'
def raw(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def text_sha(s:str)->str:return hashlib.sha256(s.encode()).hexdigest()
def base_module():
 spec=importlib.util.spec_from_file_location('base',BASE)
 if spec is None or spec.loader is None:raise AdapterError('base adapter unavailable')
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def validate_manifest(m:dict[str,Any])->None:
 required={'schemaVersion':1,'stageId':STAGE_ID,'batchId':'twilight-surrogate-space-filling-v1-tier-1','mode':'scientific-proposal','proposalOnly':True,'scientificExecution':False,'successDoesNotAuthorizeProduction':True,'adapterId':ADAPTER_ID,'caseSpecificAlisSpectralImportanceSampling':True}
 stale={k:(m.get(k),v) for k,v in required.items() if m.get(k)!=v}
 if stale:raise AdapterError(f'manifest mismatch: {stale}')
 cases=m.get('cases');geometries=m.get('geometries')
 if not isinstance(cases,list) or len(cases)!=96 or not isinstance(geometries,list) or len(geometries)!=48:raise AdapterError('tier-1 count changed')
 if [c.get('ordinal') for c in cases]!=list(range(1,97)):raise AdapterError('case ordinals changed')
 if len({c.get('seed') for c in cases})!=96:raise AdapterError('seeds not unique')
 if sum(c.get('photonHistories',0) for c in cases)!=6960000000:raise AdapterError('photon sum changed')
 if any(c.get('method')!='alis' or float(c.get('alisSpectralImportanceSamplingNm',-1)) not in ALLOWED for c in cases):raise AdapterError('case ALIS contract changed')
def validate_runtime(m:dict[str,Any],r:dict[str,Any])->None:
 fields=('uvspecSha256','uvspecHelpSha256','libRadtranDataTreeSha256','atmosphereSha256','runtimeLockRawSha256')
 if r.get('schemaVersion')!=1 or r.get('stageId')!='mystic-batch-v1' or r.get('scientificSolverExecuted') is not False or r.get('syntaxCheckExecuted') is not False:raise AdapterError('runtime report header changed')
 stale={f:(r.get(f),m.get('runtime',{}).get(f)) for f in fields if r.get(f)!=m.get('runtime',{}).get(f)}
 if stale:raise AdapterError(f'runtime mismatch: {stale}')
def prepare_case(manifest_path:Path,runtime_report_path:Path,case_id:str,data_dir:Path,repository_root:Path,output_dir:Path)->dict[str,Any]:
 m,r=load(manifest_path),load(runtime_report_path);validate_manifest(m);validate_runtime(m,r);base=base_module();case,geometry=base.resolve_case(m,case_id);inputs=base.normalized_inputs(m,case,geometry);inputs['alisSpectralImportanceSamplingNm']=float(case['alisSpectralImportanceSamplingNm']);case_dir=output_dir/case_id;case_dir.mkdir(parents=True,exist_ok=False);text=base.render_input(inputs,data_dir.resolve(),repository_root.resolve(),case_dir.resolve());path=case_dir/'input-resolved.txt';path.write_text(text);out={'schemaVersion':1,'stageId':STAGE_ID,'adapterId':ADAPTER_ID,'status':'PREPARED_FOR_ONE_AUTHORIZED_TIER_1_CASE','caseId':case_id,'groupId':case['groupId'],'method':'alis','block':case['block'],'role':case['role'],'alisSpectralImportanceSamplingNm':inputs['alisSpectralImportanceSamplingNm'],'proposalRawSha256':raw(manifest_path),'runtimeReportRawSha256':raw(runtime_report_path),'baseAdapterRawSha256':raw(BASE),'inputResolvedSha256':text_sha(text),'inputs':inputs,'inputPath':str(path),'boundary':'one tier-1 case prepared after runtime validation; execution remains delegated to guarded executor'};(case_dir/'tier1-prepared.json').write_text(dump(out));return out
