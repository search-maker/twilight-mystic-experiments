#!/usr/bin/env python3
from __future__ import annotations
import copy, hashlib, importlib.util, json, os, stat, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; E=ROOT/'experiments/tier2-stage1-execution-v1'; R=Path(__file__).resolve().parent

def mod(name,path):
    s=importlib.util.spec_from_file_location(name,path); assert s and s.loader; m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
A=mod('a',E/'adapter_v1.py'); X=mod('x',E/'executor_v1.py'); G=mod('g',E/'aggregate_v1.py'); U=mod('u',E/'audit_v1.py')
M=json.loads((E/'stage1-execution-manifest-v1.json').read_text())
def runtime(): return {'schemaVersion':1,'stageId':'mystic-batch-v1','scientificSolverExecuted':False,'syntaxCheckExecuted':False,**M['runtimeIdentityRequired']}
def spectrum(value): return ''.join(f'{380+i*.05:.2f} {value:.12e}\n' for i in range(8001))
def make_data(root):
    p=root/'data'; (p/'atmmod').mkdir(parents=True); (p/'solar_flux').mkdir(); (p/'atmmod/afglus.dat').write_text('\n'.join(f'{z} 1' for z in [120,100,80,60,40,30,20,15,10,7,5,3,2,1,0])+'\n'); (p/'solar_flux/atlas_plus_modtran').write_text('solar\n'); return p
def make_reference_repo(root:Path)->Path:
    repo=root/'repo'; mystic=repo/'experiments/mystic-batch-v1'; hist=repo/'experiments/full-spectrum-estimator-pilot-v2'; grid=repo/'review/full-spectrum-estimator-pilot-v2'
    mystic.mkdir(parents=True); hist.mkdir(parents=True); grid.mkdir(parents=True); (grid/'wavelength-grid-1nm.dat').write_text('380\n780\n')
    (mystic/'cross_geometry_adapter.py').write_text("""from pathlib import Path
def render_input(x,data_dir,repository_root,case_dir):
    assert x['method']=='alis' and x['wavelengthDomainNm']==[380.0,780.0]
    return '\\n'.join([f'data_files_path {data_dir}',f'atmosphere_file {data_dir/"atmmod/afglus.dat"}',f'source solar {data_dir/"solar_flux/atlas_plus_modtran"}','mol_abs_param crs','wavelength 380 780',f'mc_photons {x["photonHistories"]}',f'mc_randomseed {x["seed"]}',f'mc_basename {case_dir/"mc"}',f'mc_spectral_is {x["alisSpectralImportanceSamplingNm"]}',f'zout {x["observerElevationM"]/1000.0:.6f}','quiet'])+'\\n'
""")
    (mystic/'twilight_surrogate_tier1_execution_adapter.py').write_text("""def apply_ground_site_atm_z_grid(rendered,observer_elevation_m):
    site=observer_elevation_m/1000.0; grid=[site,120.0]; lines=[]
    for line in rendered.splitlines():
        if line.startswith('zout '): lines.extend(['atm_z_grid '+' '.join(f'{x:.6f}' for x in grid),'zout 0.000000'])
        else: lines.append(line)
    return '\\n'.join(lines)+'\\n',site,grid
""")
    (hist/'executor.py').write_text("""from pathlib import Path
REVIEW_REL=Path('review/full-spectrum-estimator-pilot-v2'); DISPATCH_BRANCH_RE=None
def execute_case(repository_root,case_id,data_dir,output_root,uvspec,runtime_report,timeout,allow_execution,runner=None,expected_dispatch_branch=None):
    import json
    manifest=json.loads((Path(REVIEW_REL)/'full-spectrum-estimator-pilot-execution-manifest-v4.json').read_text()); case=manifest['cases'][0]; d=output_root/case_id; d.mkdir(parents=True,exist_ok=False); inp=resolve_input(repository_root,case_id,data_dir,output_root); text=inp.decode(); (d/'input-resolved.txt').write_bytes(inp); (d/'runtime-report.json').write_bytes(runtime_report.read_bytes()); (d/'randomseed').write_text(str(case['seed'])+'\\n'); (d/'prepared.json').write_text('{}\\n'); run=runner; a=run([str(uvspec),'-c'],text,d,60); (d/'syntax-stdout.txt').write_text(a['stdout']); (d/'syntax-stderr.txt').write_text(a['stderr']); b=run([str(uvspec)],text,d,timeout); (d/'solver-stdout.txt').write_text(b['stdout']); (d/'solver-stderr.txt').write_text(b['stderr']); return {'workflowRunAttempt':1,'syntaxCheckCount':1,'solverExecutionCount':1,'retryPerformed':False,'resumePerformed':False,'githubRerun':False}
""")
    return repo

def test_adapter_and_executor():
    with tempfile.TemporaryDirectory() as td:
        t=Path(td); repo=make_reference_repo(t); data=make_data(t); rp=t/'runtime.json'; rp.write_text(json.dumps(runtime())); u=t/'uvspec'; u.write_text('#!/bin/sh\nexit 0\n'); u.chmod(u.stat().st_mode|stat.S_IXUSR); out=t/'out'; case=M['cases'][0]
        prep=A.prepare_case(E/'stage1-execution-manifest-v1.json',rp,case['caseId'],data,repo,out); text=(out/case['caseId']/'input-resolved.txt').read_text(); assert 'atm_z_grid ' in text and 'zout 0.000000' in text and '\naltitude ' not in '\n'+text and 'mc_elevation_file' not in text; assert f"mc_randomseed {case['seed']}" in text and prep['referenceCrossGeometryAdapterPath'].endswith('cross_geometry_adapter.py')
        out2=t/'exec'; calls=[]
        def runner(cmd,text,cwd,timeout):
            calls.append(cmd)
            if '-c' not in cmd:
                (cwd/'mc.rad.spc').write_text(spectrum(1e-6)); (cwd/'mc.rad.std.spc').write_text(spectrum(1e-7))
                for n in M['artifactContract']['requiredMembers']:
                    if n in {'case-result.json','input-resolved.txt','runtime-report.json','prepared.json','randomseed','syntax-stdout.txt','syntax-stderr.txt','solver-stdout.txt','solver-stderr.txt','mc.rad.spc','mc.rad.std.spc'}: continue
                    (cwd/n).write_text('raw\n')
            return {'exitCode':0,'timedOut':False,'stdout':'','stderr':''}
        old={k:os.environ.get(k) for k in ['GITHUB_ACTIONS','GITHUB_EVENT_NAME','GITHUB_RUN_ATTEMPT','GITHUB_REF_NAME']}; os.environ.update({'GITHUB_ACTIONS':'true','GITHUB_EVENT_NAME':'push','GITHUB_RUN_ATTEMPT':'1','GITHUB_REF_NAME':'dispatch/tier2-stage1-ordinal19-v2'})
        try:r=X.execute_case(E/'stage1-execution-manifest-v1.json',rp,E/'adapter_v1.py',case['caseId'],data,repo,u,out2,900,True,'dispatch/tier2-stage1-ordinal19-v2',runner)
        finally:
            for k,v in old.items():
                if v is None: os.environ.pop(k,None)
                else: os.environ[k]=v
        assert r['status']=='COMPLETED' and r['workflowRunAttempt']==1 and r['syntaxCheckCount']==1 and r['solverExecutionCount']==1 and len(calls)==2 and r['protectedHoldoutValueExposed'] is False and r['historicalExecutorPath'].endswith('executor.py')

def write_case(root,c,zero=False):
    d=root/c['caseId']; d.mkdir(parents=True); val=0.0 if zero else c['block']*1e-7
    for n in M['artifactContract']['requiredMembers']:
        if n=='case-result.json': continue
        if n=='mc.rad.spc': (d/n).write_text(spectrum(val))
        elif n=='mc.rad.std.spc': (d/n).write_text(spectrum(0.0 if zero else val/10))
        else: (d/n).write_text('x\n')
    raw={n:hashlib.sha256((d/n).read_bytes()).hexdigest() for n in M['artifactContract']['requiredMembers'] if n!='case-result.json'}
    r={'schemaVersion':1,'stageId':'public-tier2-v1-core-stage1-execution-v1','status':'COMPLETED','caseId':c['caseId'],'geometryId':c['geometryId'],'block':c['block'],'role':'surrogate-training','workflowRunAttempt':1,'syntaxCheckCount':1,'solverExecutionCount':1,'retryPerformed':False,'resumePerformed':False,'githubRerun':False,'syntaxExitCode':0,'solverExitCode':0,'syntaxTimedOut':False,'solverTimedOut':False,'seed':c['seed'],'photonHistories':c['photonHistories'],'executionManifestSha256':M['manifestSha256'],'inputResolvedSha256':raw['input-resolved.txt'],'physicalInputCanonicalSha256':'a'*64,'runtimeReportRawSha256':raw['runtime-report.json'],'radianceOutputSha256':raw['mc.rad.spc'],'stdRadianceOutputSha256':raw['mc.rad.std.spc'],'rawMemberSha256ByBasename':raw,'rawSpectrumNodeCount':8001,'rawAllZero':zero,'fittingSurfaceExposed':False,'protectedHoldoutValueExposed':False}; r['contentSha256']=G.canon(r); (d/'case-result.json').write_text(json.dumps(r,sort_keys=True,separators=(',',':'))+'\n')
def test_full_training_postprocess():
    with tempfile.TemporaryDirectory() as td:
        t=Path(td); cases=t/'cases'
        for i,c in enumerate(M['cases']): write_case(cases,c,zero=(i==0))
        agg=G.build(M,cases); assert agg['caseCount']==76 and agg['trainingGeometryCount']==19 and agg['protectedHoldoutRecordCount']==0 and agg['rawExactZeroCaseIds']==[M['cases'][0]['caseId']]
        audit=U.audit(M,agg,cases,E); assert audit['status']=='PASSED' and audit['caseCountAudited']==76 and audit['holdoutValuesRead'] is False
        assert audit['independentlyRecomputedGeometryRecords']==19
        bad=copy.deepcopy(agg); bad['records'][0]['channelsMean']['photopicLuminanceCdM2'] += 1.0; bad['aggregateSha256']=G.canon({k:v for k,v in bad.items() if k!='aggregateSha256'})
        try: U.audit(M,bad,cases,E)
        except U.Refusal: pass
        else: raise AssertionError('independent audit accepted tampered geometry record with valid aggregate selfhash')
        ap=t/'aggregate.json'; up=t/'audit.json'; hp=t/'handoff.json'; ap.write_text(json.dumps(agg)); up.write_text(json.dumps(audit)); import subprocess; subprocess.check_call(['python',str(E/'handoff_v1.py'),'--manifest',str(E/'stage1-execution-manifest-v1.json'),'--aggregate',str(ap),'--audit',str(up),'--output',str(hp)]); h=json.loads(hp.read_text()); assert h['trainingGeometryCount']==19 and h['protectedHoldoutRecordCount']==0 and h['modelFittingAuthorized'] is False

def test_context_refusal():
    try:X.validate_context(True,'dispatch/tier2-stage1-ordinal19-v2')
    except Exception: pass
    else: raise AssertionError('non-GitHub context accepted')
if __name__=='__main__':
    test_adapter_and_executor(); test_full_training_postprocess(); test_context_refusal(); print('PASS: transport adapter/executor/full-spectrum aggregate/audit/handoff synthetic chain')
