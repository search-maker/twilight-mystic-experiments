from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
from typing import Any

STAGE="aerosol-scenario-interpolation-validation-v1"
DERIVED_REL=Path("experiments/aerosol-family-challenge-v2-r8/derived_channels.py")
DERIVED_BLOB="ccfd04d4c21188966351f4257e92893d7ce340c7"
RAW_NAMES=("case.inp","prepared.json","runtime-report.json","randomseed","syntax-stdout.txt","syntax-stderr.txt","solver-stdout.txt","solver-stderr.txt","wavelength-grid-1nm.dat","mc.flx.spc","mc.flx.std.spc","mc.rad.spc","mc.rad.std.spc")
ALTS=("opac-continental-average","opac-maritime-clean","opac-desert","opac-desert-spheroids")
NATIVE="native-rural-ss"

class AggregateRefusal(RuntimeError): pass

def sha256_file(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''): h.update(b)
    return h.hexdigest()
def git_blob(path:Path)->str:
    b=path.read_bytes(); return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def canon(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
def module(name:str,path:Path,blob:str):
    if git_blob(path)!=blob: raise AggregateRefusal(f"bound source byte drift: {path}")
    s=importlib.util.spec_from_file_location(name,path)
    if s is None or s.loader is None: raise AggregateRefusal(f"cannot import {path}")
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
def parse(path:Path):
    wl=[]; val=[]
    for line in path.read_text().splitlines():
        p=line.split()
        if len(p)<2: continue
        try: wl.append(float(p[0])); val.append(float(p[-1]))
        except ValueError: continue
    return wl,val
def locate(root:Path,name:str)->Path:
    rows=list(root.rglob(name))
    if len(rows)!=1: raise AggregateRefusal(f"expected exactly one {name} under {root}, got {len(rows)}")
    return rows[0]
def close(a:float,b:float)->bool:
    return math.isclose(float(a),float(b),rel_tol=1e-12,abs_tol=1e-15)

def run(repository_root:Path,design_path:Path,artifact_root:Path,artifact_metadata_path:Path,workflow_run_id:int,scientific_ordinal:int):
    stage=repository_root/'experiments'/STAGE
    transport=module('asiv_transport_for_aggregate',stage/'execution_transport.py',git_blob(stage/'execution_transport.py'))
    analysis=module('asiv_analysis_for_aggregate',stage/'analysis.py',git_blob(stage/'analysis.py'))
    derived=module('asiv_derived_for_aggregate',repository_root/DERIVED_REL,DERIVED_BLOB)
    design=json.loads(design_path.read_text()); transport.validate_authorized_design(repository_root,design)
    meta=json.loads(artifact_metadata_path.read_text()); rows=meta.get('artifacts') if isinstance(meta,dict) else None
    if not isinstance(rows,list) or len(rows)!=120: raise AggregateRefusal('exact 120 current-run artifact metadata rows required')
    expected_names={f"asiv-v1-case-{c['caseId']}" for c in design['cases']}
    observed_names={str(a.get('name')) for a in rows}
    if observed_names!=expected_names or len(observed_names)!=120: raise AggregateRefusal('exact current-run case artifact name universe required')
    expected={c['caseId']:c for c in design['cases']}; normalized=[]; spectra={}; artifact_rows=[]
    run_ids=set(); ordinals=set()
    for a in rows:
        name=str(a['name']); cid=name[len('asiv-v1-case-'):]; folder=artifact_root/name
        if cid not in expected or not folder.is_dir(): raise AggregateRefusal(f'artifact folder/case mismatch: {name}')
        result_path=locate(folder,'case-result.json'); result=json.loads(result_path.read_text()); case_dir=result_path.parent; case=expected[cid]
        stored=result.get('contentSha256'); check=dict(result); check.pop('contentSha256',None)
        if stored!=canon(check): raise AggregateRefusal(f'case content hash drift: {cid}')
        required={'caseId':cid,'groupId':case['groupId'],'holdoutId':case['holdoutId'],'replicate':case['replicate'],'stateId':case['stateId'],'seed':case['seed'],'photonHistories':case['photonHistories'],'numericalMethod':case['numericalMethod'],'designCanonicalSha256':design['canonicalDesignSha256']}
        for k,v in required.items():
            if result.get(k)!=v: raise AggregateRefusal(f'case metadata drift {cid}:{k}')
        if result.get('status')!='COMPLETED' or result.get('workflowRunAttempt')!=1 or result.get('syntaxCheckCount')!=1 or result.get('solverExecutionCount')!=1 or result.get('retryPerformed') is not False or result.get('resumePerformed') is not False or result.get('githubRerun') is not False: raise AggregateRefusal(f'case execution provenance drift: {cid}')
        if result.get('workflowRunId')!=workflow_run_id or result.get('scientificOrdinal')!=scientific_ordinal: raise AggregateRefusal(f'case run/ordinal drift: {cid}')
        run_ids.add(result['workflowRunId']); ordinals.add(result['scientificOrdinal'])
        hashes=result.get('rawMemberSha256ByBasename') or {}
        for raw in RAW_NAMES:
            p=case_dir/raw
            if not p.is_file() or hashes.get(raw)!=sha256_file(p): raise AggregateRefusal(f'raw member hash mismatch: {cid}:{raw}')
        wl,rad=parse(case_dir/'mc.rad.spc'); swl,srad=parse(case_dir/'mc.rad.std.spc'); derived.validate_raw_grid(wl,rad); derived.validate_raw_grid(swl,srad)
        if len(wl)!=len(swl) or any(abs(x-y)>derived.RAW_POINT_TOLERANCE_NM for x,y in zip(wl,swl)): raise AggregateRefusal(f'raw grid mismatch: {cid}')
        channels=derived.derive_channels(wl,rad); stored_channels=result.get('channels') or {}
        for ch in ('photopicLuminanceCdM2','scotopicLuminanceScotCdM2','johnsonVEffectiveRadiance_mW_m2_nm_sr'):
            if not close(channels[ch],stored_channels.get(ch,float('nan'))): raise AggregateRefusal(f'derived channel recomputation mismatch: {cid}:{ch}')
        normalized.append({**result,'channels':channels}); spectra[(case['holdoutId'],case['replicate'],case['stateId'])]=(wl,rad)
        artifact_rows.append({'artifactId':a.get('id'),'artifactName':name,'caseId':cid,'caseResultRawSha256':sha256_file(result_path),'rawRadianceSha256':sha256_file(case_dir/'mc.rad.spc'),'rawStdRadianceSha256':sha256_file(case_dir/'mc.rad.std.spc')})
    if run_ids!={workflow_run_id} or ordinals!={scientific_ordinal}: raise AggregateRefusal('mixed run/ordinal artifact universe')
    scalar=analysis.build_scalar_truth(normalized)
    spectral=[]; unresolved_total=0
    for h in range(1,9):
        hid=f'asiv-holdout-{h:02d}'
        for rep in (1,2,3):
            nwl,nrad=spectra[(hid,rep,NATIVE)]
            for state in ALTS:
                awl,arad=spectra[(hid,rep,state)]
                if len(awl)!=len(nwl) or any(abs(a-b)>1e-9 for a,b in zip(awl,nwl)): raise AggregateRefusal('paired spectral grid drift')
                logs=[]; unresolved=0
                for a,n in zip(arad,nrad):
                    if a>0.0 and n>0.0 and math.isfinite(a) and math.isfinite(n): logs.append(math.log(a/n))
                    else: unresolved+=1
                unresolved_total+=unresolved
                spectral.append({'holdoutId':hid,'replicate':rep,'stateId':state,'rawNodeCount':len(nwl),'finiteLogRatioNodeCount':len(logs),'unresolvedNodeCount':unresolved,'meanFiniteLogRatio':sum(logs)/len(logs) if logs else None,'minimumFiniteLogRatio':min(logs) if logs else None,'maximumFiniteLogRatio':max(logs) if logs else None})
    spectral_out={'schemaVersion':1,'stageId':'asiv-v1-spectral-diagnostics','status':'COMPLETED_REQUIRED_DIAGNOSTIC_NO_SPECTRAL_PASS_CLAIM','contrastReplicateRowCount':len(spectral),'totalUnresolvedNodeCount':unresolved_total,'epsilonSubstitutionPerformed':False,'fullSpectrumInterpolationPassClaim':False,'rows':spectral}
    acquisition={'schemaVersion':1,'stageId':'asiv-v1-acquisition','status':'COMPLETE_EXACT_120_CASE_ARTIFACT_UNIVERSE','workflowRunId':workflow_run_id,'scientificOrdinal':scientific_ordinal,'caseArtifactCount':120,'groupCount':24,'holdoutCount':8,'artifactRows':artifact_rows}
    return acquisition,normalized,scalar,spectral_out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repository-root',type=Path,required=True); ap.add_argument('--execution-design',type=Path,required=True); ap.add_argument('--artifact-root',type=Path,required=True); ap.add_argument('--artifact-metadata',type=Path,required=True); ap.add_argument('--workflow-run-id',type=int,required=True); ap.add_argument('--scientific-ordinal',type=int,required=True); ap.add_argument('--output-acquisition',type=Path,required=True); ap.add_argument('--output-case-results',type=Path,required=True); ap.add_argument('--output-scalar-truth',type=Path,required=True); ap.add_argument('--output-spectral',type=Path,required=True); a=ap.parse_args()
    ac,cases,scalar,spectral=run(a.repository_root,a.execution_design,a.artifact_root,a.artifact_metadata,a.workflow_run_id,a.scientific_ordinal)
    for p,v in ((a.output_acquisition,ac),(a.output_case_results,{'schemaVersion':1,'stageId':'asiv-v1-normalized-case-results','caseCount':120,'cases':cases}),(a.output_scalar_truth,scalar),(a.output_spectral,spectral)): p.write_text(json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+'\n')
if __name__=='__main__': main()
