from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any, Callable

STAGE = "aerosol-scenario-interpolation-validation-v1"
EXPECTED_GUARD_STATUS = "EXACT_ONE_USE_ASIV_V1_DISPATCH_AUTHORIZED"
PROCESS_RUNNER_REL = Path("experiments/aerosol-family-challenge-v2-r8-timeout-recovery-v1/execution-candidate/process_runner.py")
PROCESS_RUNNER_BLOB = "e23d724e99c1cf9b0b862f8ab48356bd3d9bc56c"
DERIVED_REL = Path("experiments/aerosol-family-challenge-v2-r8/derived_channels.py")
DERIVED_BLOB = "ccfd04d4c21188966351f4257e92893d7ce340c7"
GRID_REL = Path("experiments/aerosol-family-challenge-v2-r8/wavelength-grid-1nm.dat")
GRID_BLOB = "3bb3db96580d555ef758f57cabd6cac55b61cebb"
RAW_NAMES = ("case.inp","prepared.json","runtime-report.json","randomseed","syntax-stdout.txt","syntax-stderr.txt","solver-stdout.txt","solver-stderr.txt","wavelength-grid-1nm.dat","mc.flx.spc","mc.flx.std.spc","mc.rad.spc","mc.rad.std.spc")


class ExecutionRefusal(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(4*1024*1024),b''): h.update(block)
    return h.hexdigest()


def git_blob_sha1(path: Path) -> str:
    data=path.read_bytes(); return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()


def module(name: str, path: Path, expected_blob: str):
    if git_blob_sha1(path)!=expected_blob: raise ExecutionRefusal(f"bound source byte drift: {path}")
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise ExecutionRefusal(f"cannot import {path}")
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod


def parse_spectrum(path: Path) -> tuple[list[float],list[float]]:
    wl=[]; val=[]
    for line in path.read_text().splitlines():
        parts=line.split()
        if len(parts)<2: continue
        try: wl.append(float(parts[0])); val.append(float(parts[-1]))
        except ValueError: continue
    return wl,val


def validate_guard(guard: dict[str,Any], design: dict[str,Any], contract_blob: str) -> None:
    if guard.get('status')!=EXPECTED_GUARD_STATUS or guard.get('solverExecutionPermittedNow') is not True: raise ExecutionRefusal('science guard did not authorize ASIV solver')
    if guard.get('workflowRunAttempt')!=1 or guard.get('githubRerun') is not False: raise ExecutionRefusal('attempt/rerun guard drift')
    if guard.get('designCanonicalSha256')!=design.get('canonicalDesignSha256') or guard.get('executionContractGitBlobSha1')!=contract_blob: raise ExecutionRefusal('guard byte/design binding drift')
    if guard.get('authorizationPrDraftOpenUnmerged') is not True: raise ExecutionRefusal('authorization PR must remain Draft/open/unmerged')
    if guard.get('authorizationTimeSeedRecheckPassed') is not True or guard.get('authorizationTimeGeometryRecheckPassed') is not True: raise ExecutionRefusal('authorization-time freshness recheck missing')
    if guard.get('augmentedDataTreeSha256')!='5d8bbf8e6b91ec3d405dee36f21a94afbb6e5ec6cd67da2dd5dd541738199d80': raise ExecutionRefusal('OPAC tree guard drift')
    for key in ('scientificOrdinal','workflowRunId'):
        v=guard.get(key)
        if isinstance(v,bool) or not isinstance(v,int) or v<=0: raise ExecutionRefusal(f'invalid guard identity: {key}')


def validate_runtime(runtime: dict[str,Any], uvspec: Path) -> None:
    expected={
        'runtimeLockRawSha256':'3b5fbec964642b04c73a6423b3355dbcc4ba5e84f9614f6d74420491bacc20c5',
        'uvspecSha256':'2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3',
        'uvspecHelpSha256':'868aea5af762d968f6f62c4e1472916d25232ed9cab5be112d753b0823d20548',
        'libRadtranDataTreeSha256':'5d8bbf8e6b91ec3d405dee36f21a94afbb6e5ec6cd67da2dd5dd541738199d80',
        'atmosphereSha256':'dab26290ed81c762ed0c607e5dc2d53393c1462a0c3a528bc5e3f5935191cfb5',
    }
    if runtime.get('scientificSolverExecuted') is not False: raise ExecutionRefusal('runtime identity must be captured pre-solver')
    for key,want in expected.items():
        if runtime.get(key)!=want: raise ExecutionRefusal(f'runtime identity drift: {key}')
    if sha256_file(uvspec)!=expected['uvspecSha256']: raise ExecutionRefusal('uvspec byte hash drift')


def execute_case(repository_root: Path, design_path: Path, guard_path: Path, runtime_path: Path, case_id: str, data_dir: Path, output_root: Path, uvspec: Path, *, allow_execution: bool=False, runner: Callable[...,dict[str,Any]]|None=None) -> dict[str,Any]:
    if not allow_execution: raise ExecutionRefusal('explicit allow_execution=True required')
    stage=repository_root/'experiments'/STAGE
    contract_path=stage/'execution-contract.review.json'
    contract=json.loads(contract_path.read_text())
    if contract.get('status')!='FROZEN_REVIEW_ONLY_EXECUTION_CORE_NO_AUTHORIZATION': raise ExecutionRefusal('execution contract status drift')
    transport=module('asiv_transport_for_executor',stage/'execution_transport.py',git_blob_sha1(stage/'execution_transport.py'))
    design=json.loads(design_path.read_text()); transport.validate_authorized_design(repository_root,design)
    guard=json.loads(guard_path.read_text()); validate_guard(guard,design,git_blob_sha1(contract_path))
    runtime=json.loads(runtime_path.read_text()); validate_runtime(runtime,uvspec)
    matches=[row for row in design['cases'] if row.get('caseId')==case_id]
    if len(matches)!=1: raise ExecutionRefusal('case not uniquely present in frozen design')
    review_case=matches[0]
    case={**review_case,'renderable':True,'executionAuthorized':True,'seedStatus':'AUTHORIZED_FRESH_GROUP_SEED'}
    adapter_path=stage/'adapter.py'; adapter=module('asiv_adapter_for_executor',adapter_path,git_blob_sha1(adapter_path))
    derived=module('asiv_bound_derived',repository_root/DERIVED_REL,DERIVED_BLOB)
    process=module('asiv_bound_process_runner',repository_root/PROCESS_RUNNER_REL,PROCESS_RUNNER_BLOB)
    if git_blob_sha1(repository_root/GRID_REL)!=GRID_BLOB: raise ExecutionRefusal('wavelength grid byte drift')
    case_dir=output_root/case_id; case_dir.mkdir(parents=True,exist_ok=False)
    text,elev=adapter.render_case_input(case,data_dir,repository_root,output_root)
    case_inp=case_dir/'case.inp'; case_inp.write_text(text,encoding='utf-8',newline='\n')
    (case_dir/'runtime-report.json').write_bytes(runtime_path.read_bytes()); (case_dir/'randomseed').write_text(f"{case['seed']}\n")
    (case_dir/'wavelength-grid-1nm.dat').write_bytes((repository_root/GRID_REL).read_bytes())
    prepared={'schemaVersion':1,'stageId':f'{STAGE}-prepared','caseId':case_id,'groupId':case['groupId'],'holdoutId':case['holdoutId'],'replicate':case['replicate'],'stateId':case['stateId'],'seed':case['seed'],'photonHistories':case['photonHistories'],'designCanonicalSha256':design['canonicalDesignSha256'],'executionContractGitBlobSha1':git_blob_sha1(contract_path),'caseInpSha256':sha256_file(case_inp),**elev}
    (case_dir/'prepared.json').write_text(json.dumps(prepared,indent=2,sort_keys=True)+'\n')
    run=runner or process.run_process_group
    syntax=run([str(uvspec),'-c'],text,case_dir,60,sigterm_grace_seconds=5)
    (case_dir/'syntax-stdout.txt').write_text(str(syntax.get('stdout') or '')); (case_dir/'syntax-stderr.txt').write_text(str(syntax.get('stderr') or ''))
    if syntax.get('processGroupIsolated') is not True or syntax.get('timedOut') or syntax.get('exitCode')!=0: raise ExecutionRefusal('single syntax check failed')
    solver=run([str(uvspec)],text,case_dir,7200,sigterm_grace_seconds=5)
    (case_dir/'solver-stdout.txt').write_text(str(solver.get('stdout') or '')); (case_dir/'solver-stderr.txt').write_text(str(solver.get('stderr') or ''))
    if solver.get('processGroupIsolated') is not True or solver.get('timedOut') or solver.get('exitCode')!=0: raise ExecutionRefusal('single solver execution failed')
    for name in ('mc.flx.spc','mc.flx.std.spc','mc.rad.spc','mc.rad.std.spc'):
        p=case_dir/name
        if not p.is_file() or p.stat().st_size==0: raise ExecutionRefusal(f'required raw output missing/empty: {name}')
    wl,rad=parse_spectrum(case_dir/'mc.rad.spc'); swl,srad=parse_spectrum(case_dir/'mc.rad.std.spc')
    derived.validate_raw_grid(wl,rad); derived.validate_raw_grid(swl,srad)
    if any(abs(a-b)>derived.RAW_POINT_TOLERANCE_NM for a,b in zip(wl,swl)): raise ExecutionRefusal('radiance/std wavelength grids differ')
    channels=derived.derive_channels(wl,rad); mcdiag=derived.marginal_mc_std_diagnostics(wl,rad,srad)
    for name in RAW_NAMES:
        if not (case_dir/name).is_file(): raise ExecutionRefusal(f'required evidence member missing: {name}')
    result={'schemaVersion':1,'stageId':STAGE,'status':'COMPLETED','caseId':case_id,'groupId':case['groupId'],'holdoutId':case['holdoutId'],'sunDepressionDeg':case['sunDepressionDeg'],'targetAltitudeDeg':case['targetAltitudeDeg'],'relativeAzimuthDeg':case['relativeAzimuthDeg'],'observerElevationM':case['observerElevationM'],'aod550':case['aod550'],'replicate':case['replicate'],'stateId':case['stateId'],'aerosolKind':case['aerosolKind'],'opacMixture':case.get('opacMixture'),'seed':case['seed'],'photonHistories':case['photonHistories'],'numericalMethod':case['numericalMethod'],'scientificOrdinal':guard['scientificOrdinal'],'workflowRunId':guard['workflowRunId'],'workflowRunAttempt':1,'syntaxCheckCount':1,'solverExecutionCount':1,'retryPerformed':False,'resumePerformed':False,'githubRerun':False,'processGroupIsolation':True,'designCanonicalSha256':design['canonicalDesignSha256'],'executionContractGitBlobSha1':git_blob_sha1(contract_path),'runtimeReportRawSha256':sha256_file(case_dir/'runtime-report.json'),'rawOutputNodeCount':len(wl),'channels':channels,'marginalMcStdDiagnostics':mcdiag,'rawMemberSha256ByBasename':{name:sha256_file(case_dir/name) for name in RAW_NAMES}}
    result['contentSha256']=canonical_sha256(result); (case_dir/'case-result.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n'); return result
