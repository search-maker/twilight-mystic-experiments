#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, importlib.util, json, math, os, subprocess, time
from pathlib import Path

NODES=[470,480,490,500,510,520,530,540,560,580,590,600,610,640,660]
CIE=[0.09098,0.13902,0.20802,0.323,0.503,0.71,0.862,0.954,0.995,0.87,0.757,0.631,0.503,0.175,0.061]
class Refusal(RuntimeError):pass
def req(c,m):
    if not c:raise Refusal(m)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def load_adapter(p):
    s=importlib.util.spec_from_file_location('zenith_adapter',p); req(s and s.loader,'adapter load'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
def run(cmd,text,cwd,timeout):
    t=time.monotonic()
    try:r=subprocess.run(cmd,input=text,text=True,capture_output=True,cwd=cwd,timeout=timeout,check=False); return {'exitCode':r.returncode,'timedOut':False,'elapsedSeconds':time.monotonic()-t,'stdout':r.stdout,'stderr':r.stderr}
    except subprocess.TimeoutExpired as e:return {'exitCode':None,'timedOut':True,'elapsedSeconds':time.monotonic()-t,'stdout':e.stdout or '','stderr':e.stderr or ''}
def spectrum(path):
    rows=[]
    for line in Path(path).read_text(errors='replace').splitlines():
        p=line.split()
        if len(p)<2:continue
        try:w=float(p[0]);v=float(p[-1])
        except ValueError:continue
        if math.isfinite(w) and math.isfinite(v):rows.append((w,v))
    req(rows,'empty spectrum'); unique=sorted({round(w,8) for w,_ in rows})
    req(len(unique)==8001 and abs(unique[0]-380.0)<1e-7 and abs(unique[-1]-780.0)<1e-7,'full 8001-node spectrum grid missing')
    found={n:None for n in NODES}
    for w,v in rows:
        for n in NODES:
            if abs(w-n)<=1e-7:found[n]=v
    req(all(found[n] is not None and found[n]>=0 for n in NODES),'diagnostic spectrum node missing/invalid')
    return [found[n] for n in NODES],len(unique)
def lum(v):return 683.002*10.0*sum((x/1000.0)*w for x,w in zip(v,CIE))
def main():
    p=argparse.ArgumentParser(); p.add_argument('--manifest',type=Path,required=True);p.add_argument('--runtime-report',type=Path,required=True);p.add_argument('--adapter',type=Path,required=True);p.add_argument('--case-id',required=True);p.add_argument('--data-dir',type=Path,required=True);p.add_argument('--repository-root',type=Path,required=True);p.add_argument('--uvspec',type=Path,required=True);p.add_argument('--output-root',type=Path,required=True);p.add_argument('--timeout-seconds',type=int,required=True);a=p.parse_args()
    req(os.getenv('GITHUB_ACTIONS')=='true' and os.getenv('GITHUB_EVENT_NAME')=='pull_request' and os.getenv('GITHUB_RUN_ATTEMPT')=='1','not first-attempt pull_request execution context')
    m=load(a.manifest); cases=[c for c in m['cases'] if c['caseId']==a.case_id];req(len(cases)==1,'case selection');c=cases[0]
    ad=load_adapter(a.adapter); prop=ad.prepare_case(a.manifest,a.runtime_report,a.case_id,a.data_dir,a.repository_root,a.output_root); d=a.output_root/a.case_id; text=(d/'input-resolved.txt').read_text()
    syntax=run([str(a.uvspec),'-c'],text,d,60);(d/'syntax-stdout.txt').write_text(str(syntax['stdout']));(d/'syntax-stderr.txt').write_text(str(syntax['stderr']))
    req(not syntax['timedOut'] and syntax['exitCode']==0,'uvspec syntax check failed')
    solver=run([str(a.uvspec)],text,d,a.timeout_seconds);(d/'solver-stdout.txt').write_text(str(solver['stdout']));(d/'solver-stderr.txt').write_text(str(solver['stderr']))
    req(not solver['timedOut'] and solver['exitCode']==0,'MYSTIC solver failed')
    rad=d/'mc.rad.spc';std=d/'mc.rad.std.spc';req(rad.is_file() and std.is_file(),'MYSTIC radiance outputs missing')
    rv,nr=spectrum(rad);sv,ns=spectrum(std); req(nr==ns==8001,'spectrum grid mismatch')
    result={'schemaVersion':1,'status':'COMPLETED','executionKey':m['executionKey'],'manifestSha256':m['manifestSha256'],'caseId':a.case_id,'geometryId':c['geometryId'],'role':c['role'],'block':c['block'],'seed':c['seed'],'photonHistories':c['photonHistories'],'syntaxCheckCount':1,'solverExecutionCount':1,'inputResolvedSha256':prop['inputResolvedSha256'],'radianceOutputSha256':sha(rad),'stdOutputSha256':sha(std),'fullSpectrumNodeCount':8001,'diagnosticNodesNm':NODES,'selectedNodeRadiance':rv,'selectedNodeStdRadiance':sv,'selectedPhotopicContributionCdM2':lum(rv),'selectedPhotopicStdContributionCdM2':lum(sv),'targetAltitudeDeg':prop['targetAltitudeDeg'],'relativeAzimuthDeg':prop['relativeAzimuthDeg'],'observerElevationMechanism':prop['observerElevationMechanism'],'successDoesNotAuthorizeSupportExpansion':True,'successDoesNotAuthorizeProduction':True}
    (d/'case-result.json').write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n');print(json.dumps(result,sort_keys=True))
if __name__=='__main__':main()
