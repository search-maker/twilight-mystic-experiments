#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, importlib.util, json
from pathlib import Path
from typing import Any

HERE=Path(__file__).resolve().parent
MANIFEST_ID='public-tier1-full-spectrum-estimator-confirmation-execution-manifest-v1'

class Refusal(RuntimeError): pass

def canon(v:Any)->str: return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def sha_bytes(v:bytes)->str: return hashlib.sha256(v).hexdigest()
def load(p:Path)->dict[str,Any]:
    v=json.loads(p.read_text())
    if not isinstance(v,dict): raise Refusal(f'expected object: {p}')
    return v

def load_pilot_normalizer(repository_root:Path):
    p=repository_root/'review/full-spectrum-estimator-pilot-v2/normalize_full_spectrum_estimator_pilot_results_v6.py'
    spec=importlib.util.spec_from_file_location('confirmation_pilot_normalizer_v6',p)
    if spec is None or spec.loader is None: raise Refusal('cannot load frozen pilot normalizer')
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def verify_manifest(m:dict[str,Any])->None:
    supplied=m.get('manifestSha256')
    if m.get('manifestId')!=MANIFEST_ID or supplied!=canon({k:v for k,v in m.items() if k!='manifestSha256'}): raise Refusal('confirmation execution manifest identity/self-hash drift')
    if m.get('status')!='DISABLED_EXECUTION_PACKAGE_REVIEW_ONLY' or m.get('caseCount')!=24: raise Refusal('confirmation execution manifest review boundary drift')
    xb=m.get('executionBoundary') or {}
    if xb.get('scientificExecutionAuthorized') is not False or xb.get('authorizationOrdinalAllocated') is not False or xb.get('dispatchBranchAllocated') is not False or xb.get('executionWorkflowPresent') is not False: raise Refusal('disabled confirmation execution boundary drift')

def _rewrite_template(source_raw:bytes, case:dict[str,Any], norm)->bytes:
    source_lines=source_raw.decode('utf-8').splitlines(); out=[]
    seen_seed=seen_basename=seen_photons=False
    for line in source_lines:
        parts=line.split()
        if not parts:
            out.append(line); continue
        if parts[0]=='mc_randomseed':
            out.append(f'mc_randomseed {case["seed"]}'); seen_seed=True
        elif parts[0]=='mc_basename':
            out.append(f'mc_basename ${{OUTPUT_DIR}}/{case["caseId"]}/mc'); seen_basename=True
        elif parts[0]=='mc_photons':
            if int(parts[1])!=int(case['photonHistories']): raise Refusal(f'source pilot template photon count drift: {case["caseId"]}')
            out.append(line); seen_photons=True
        else:
            out.append(line)
    if not (seen_seed and seen_basename and seen_photons): raise Refusal(f'source pilot template required identity directive missing: {case["caseId"]}')
    rendered=('\n'.join(out)+'\n').encode()
    src_phys=norm.physical_fingerprint(source_raw); out_phys=norm.physical_fingerprint(rendered)
    if src_phys!=out_phys: raise Refusal(f'confirmation render changed physical fingerprint: {case["caseId"]}')
    directives=norm.parse_directives(rendered)
    norm.verify_input(directives,case)
    if directives.get('seed')!=case['seed'] or directives.get('mcPhotons')!=case['photonHistories']: raise Refusal(f'confirmation render identity drift: {case["caseId"]}')
    return rendered

def render_all(repository_root:Path, manifest:dict[str,Any], output_dir:Path)->dict[str,Any]:
    verify_manifest(manifest); norm=load_pilot_normalizer(repository_root)
    if output_dir.exists(): raise Refusal(f'output directory already exists: {output_dir}')
    output_dir.mkdir(parents=True)
    reports=[]
    for case in manifest['cases']:
        if case.get('method')!='alis-alt-importance': raise Refusal('confirmation v1 permits ALIS candidates only')
        source_id=case['sourcePilotCaseId']
        source_path=repository_root/'review/full-spectrum-estimator-pilot-v2/rendered-review-v5'/source_id/'input-template.txt'
        raw=source_path.read_bytes()
        if sha_bytes(raw)!=case['sourcePilotInputTemplateSha256']: raise Refusal(f'source pilot input template byte drift: {source_id}')
        rendered=_rewrite_template(raw,case,norm)
        case_dir=output_dir/case['caseId']; case_dir.mkdir()
        (case_dir/'input-template.txt').write_bytes(rendered)
        reports.append({'caseId':case['caseId'],'sourcePilotCaseId':source_id,'sourceTemplateSha256':sha_bytes(raw),'confirmationTemplateSha256':sha_bytes(rendered),'physicalFingerprint':norm.physical_fingerprint(rendered),'seed':case['seed'],'photonHistories':case['photonHistories']})
    report={'schemaVersion':1,'renderId':'public-tier1-full-spectrum-estimator-confirmation-render-v1','manifestSha256':manifest['manifestSha256'],'caseCount':len(reports),'cases':reports,'scientificExecutionPerformed':False}
    report['renderSha256']=canon(report)
    return report

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--repository-root',type=Path,required=True); ap.add_argument('--execution-manifest',type=Path,required=True); ap.add_argument('--output-dir',type=Path,required=True); ap.add_argument('--report',type=Path,required=True); a=ap.parse_args()
    try:
        r=render_all(a.repository_root.resolve(),load(a.execution_manifest),a.output_dir); a.report.write_text(json.dumps(r,indent=2,sort_keys=True,allow_nan=False)+'\n'); print(json.dumps({'status':'PASSED','caseCount':r['caseCount'],'renderSha256':r['renderSha256'],'scientificExecutionPerformed':False},indent=2,sort_keys=True)); return 0
    except Exception as e:
        print(json.dumps({'status':'REFUSED','reason':str(e),'scientificExecutionPerformed':False},indent=2,sort_keys=True)); return 2
if __name__=='__main__': raise SystemExit(main())
