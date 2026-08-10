#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json
from pathlib import Path
from typing import Any
ROOT=Path('/mnt/data'); V3=ROOT/'full-spectrum-estimator-pilot-execution-manifest-v3.json'; OUT=ROOT/'full-spectrum-estimator-pilot-execution-manifest-v4.json'
def canon(v:Any)->str: return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def raw(p:Path)->str: return hashlib.sha256(p.read_bytes()).hexdigest()
v3=json.loads(V3.read_text()); m={k:v for k,v in v3.items() if k!='manifestSha256'}
m['manifestId']='public-tier1-full-spectrum-estimator-pilot-execution-manifest-v4'; m['status']='REVIEW_ONLY_FROZEN_NO_AUTHORIZATION'
m['supersedesExecutionManifest']={'manifestId':v3['manifestId'],'manifestSha256':v3['manifestSha256'],'rawSha256':raw(V3),'executionOccurred':False,'reason':'v4 closes the preexecution raw-evidence packaging contract: exact method-specific member basenames, syntax/solver stdout+stderr, randomseed, auxiliary MYSTIC spectra, and a case-result hash map over every raw member except case-result.json. No scientific acquisition design changed.'}
common=['case-result.json','input-resolved.txt','runtime-report.json','prepared.json','randomseed','syntax-stdout.txt','syntax-stderr.txt','solver-stdout.txt','solver-stderr.txt','mc.flx.spc','mc.flx.std.spc','mc.rad.spc','mc.rad.std.spc']
alis=common+['mc.flx.is.spc','mc.is.spc','mc0.rad','mc0.rad.std']
vroom=common+['wavelength-grid-1nm.dat']
a=dict(m['artifactContract']); a['requiredMembers']=common; a['requiredMembersByMethod']={'alis-alt-importance':alis,'reference-vroom-1nm':vroom}; a['exactMemberBasenamesRequired']=True; a['unexpectedExtraMembersRefused']=True; a['rawMemberSha256MapRequiredForAllMembersExceptCaseResult']=True; a['randomseedFileMustEqualManifestSeed']=True; a['syntaxAndSolverLogsRequired']=True; a['preparedRecordRequired']=True; a['preparedRecordContract']={'schemaVersion':1,'stageId':'full-spectrum-estimator-pilot-v2-prepared','bindFields':['caseId','geometryId','method','replicate','seed','photonHistories','inputResolvedSha256','executionManifestSha256']}; a['caseResultExecutionContract']={**a['caseResultExecutionContract'],'workflowRunAttempt':1,'syntaxExitCodeExactly':0,'solverExitCodeExactly':0,'syntaxTimedOut':False,'solverTimedOut':False,'rawMemberSha256MapExact':True}
names=[f"full-spectrum-estimator-pilot-v2-case-{c['caseId']}" for c in m['cases']]; a['expectedArtifactNames']=names; a['expectedArtifactNamesSha256']=canon(names); m['artifactContract']=a
m['manifestSha256']=canon(m); OUT.write_text(json.dumps(m,indent=2,sort_keys=True,allow_nan=False)+'\n')
print(json.dumps({'manifestId':m['manifestId'],'manifestSha256':m['manifestSha256'],'rawSha256':raw(OUT),'alisMembers':len(alis),'vroomMembers':len(vroom),'caseCount':len(m['cases'])},indent=2))
