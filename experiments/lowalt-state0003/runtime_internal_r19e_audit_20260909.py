#!/usr/bin/env python3
from __future__ import annotations
import csv, hashlib, importlib.util, json, os
from pathlib import Path

R19D_PATH=Path(os.environ['R19D_DRIVER_PATH'])
spec=importlib.util.spec_from_file_location('r19d',R19D_PATH)
r19d=importlib.util.module_from_spec(spec); assert spec.loader is not None; spec.loader.exec_module(r19d)
core=r19d.core

AUDIT_ROWS=[r for r in core.CASE_ROWS if r[1]=='audit']
assert [r[0] for r in AUDIT_ROWS]==['r16-srcaud-0009','r16-srcaud-0010']
DEV_PASS_CLASS='STATE_0003_R19D_FRESH_NONPROTECTED_RADIUS_STATE_CORRECTED_DEVELOPMENT_PASS_8_OF_8'
DEV_PASS_CASES=['r19-srcdev-repl-0013','r16-srcdev-0002','r16-srcdev-0003','r16-srcdev-0004','r16-srcdev-0005','r16-srcdev-0006','r16-srcdev-0007','r16-srcdev-0008']
R19D_RUN_ID=34434955020
R19D_HEAD='792b8eca78a490f9fee8a20616ca97967d89d6db'
R19D_ARTIFACT_ID=10135837963
R19D_ARTIFACT_DIGEST='sha256:61985e2b28aebe5f2ed56e0d9111aea2fe3cb7d3f91dbf1cc7e5015107e41002'


def sha_file(p:Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()


def bind_dev_pass(e:Path):
    p=Path(os.environ['R19D_DEVELOPMENT_SUMMARY_PATH']); x=json.loads(p.read_text(encoding='utf-8'))
    assert x.get('classification')==DEV_PASS_CLASS,x.get('classification')
    assert x.get('allPass') is True and x.get('count')==8 and x.get('auditOpened') is False
    assert x.get('cases')==DEV_PASS_CASES,x.get('cases')
    assert x.get('maxFacFac2AbsDelta')==0.0 and x.get('maxChp2AbsDelta')==0.0 and x.get('maxChAbsDelta')==0.0
    assert float(x.get('maxDirectAbsDelta')) <= 1e-12
    assert x.get('allUtauEndpointPreprocessBitExact') is True
    meta=json.loads(Path(os.environ['R19D_API_BINDING_PATH']).read_text(encoding='utf-8'))
    assert meta=={'runId':R19D_RUN_ID,'headSha':R19D_HEAD,'runAttempt':1,'conclusion':'success','artifactId':R19D_ARTIFACT_ID,'artifactDigest':R19D_ARTIFACT_DIGEST}
    core.write_json(e/'bound-r19d-development-pass.json',{'schemaVersion':1,'classification':'STATE_0003_R19E_BOUND_R19D_DEVELOPMENT_PASS','r19dRunId':R19D_RUN_ID,'r19dHead':R19D_HEAD,'r19dArtifactId':R19D_ARTIFACT_ID,'r19dArtifactDigest':R19D_ARTIFACT_DIGEST,'developmentSummarySha256':sha_file(p),'developmentClassification':DEV_PASS_CLASS,'developmentCases':DEV_PASS_CASES,'developmentMaxDirectAbsDelta':x['maxDirectAbsDelta'],'developmentExactGeometry':x['maxFacFac2AbsDelta']==0.0 and x['maxChp2AbsDelta']==0.0 and x['maxChAbsDelta']==0.0,'auditWasUnopened':x['auditOpened'] is False})


def main():
    e=Path(os.environ['EVIDENCE_DIR']); e.mkdir(parents=True,exist_ok=True); (e/'cases').mkdir(exist_ok=True)
    core.freeze(e); bind_dev_pass(e)
    mp=e/'r19e-audit-matrix.csv'
    with mp.open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f,lineterminator='\n'); w.writerow(core.HEADER); w.writerows(AUDIT_ROWS)
    freeze={
      'schemaVersion':1,
      'classification':'STATE_0003_R19E_PREALLOCATED_NONPROTECTED_AUDIT_OPEN_FREEZE',
      'developmentPrerequisite':DEV_PASS_CLASS,
      'boundR19DRunId':R19D_RUN_ID,
      'boundR19DHead':R19D_HEAD,
      'boundR19DArtifactId':R19D_ARTIFACT_ID,
      'boundR19DArtifactDigest':R19D_ARTIFACT_DIGEST,
      'auditRows':[dict(zip(core.HEADER,r)) for r in AUDIT_ROWS],
      'auditRowsWerePreallocatedInR16':True,
      'auditRowsPreviouslyOpened':False,
      'auditOrder':[r[0] for r in AUDIT_ROWS],
      'stoppingRule':'stop after first audit failure; do not expose the second audit identity after a first-audit failure',
      'reference':'R19D source-exact radius-state corrected reference plus exact dpschekin UTAU endpoint preprocessing and pinned runtime-internal capture',
      'structuralComparison':'EXACT',
      'facFac2Chp2ChTolerance':1e-10,
      'directFloat64Tolerance':1e-12,
      'postResultRetuning':'FORBIDDEN',
      'protectedResidualSelection':'FORBIDDEN',
      'taylorJerusalem':'FORBIDDEN',
      'productionBelow5Deg':'FAIL_CLOSED_UNCHANGED'
    }
    core.write_json(e/'r19e-audit-freeze.json',freeze)
    core.write_json(e/'r19e-freeze-hashes.json',{'auditMatrixSha256':sha_file(mp),'auditFreezeSha256':sha_file(e/'r19e-audit-freeze.json'),'r19dDriverSha256':sha_file(R19D_PATH),'boundDevelopmentPassSha256':sha_file(e/'bound-r19d-development-pass.json')})
    uvspec,data,gdb,nm,fc=core.bind_runtime(e); core.fresh_fence(e); lib=core.prepare_reference(e,fc); syms=core.resolve_symbols(uvspec,nm,e); r19d.r19c.abi_gdb_script(*syms)
    results=[]
    for row in AUDIT_ROWS:
        x=core.run_case(e,row,uvspec,data,gdb,syms,lib)
        if x is None:
            core.write_json(e/'audit-summary.json',{'classification':'STATE_0003_R19E_NONPROTECTED_AUDIT_MECHANICAL_CAPTURE_BARRIER','failedCase':row[0],'auditResultsOpened':len(results),'results':results}); core.manifest(e); return 21
        results.append(x)
        if not x['pass']:
            core.write_json(e/'audit-summary.json',{'classification':'STATE_0003_R19E_NONPROTECTED_AUDIT_NOT_PASS','failedCase':row[0],'auditResultsOpened':len(results),'results':results}); core.manifest(e); return 23
    core.write_json(e/'audit-summary.json',{'classification':'STATE_0003_R19E_PREALLOCATED_NONPROTECTED_AUDIT_PASS_2_OF_2','count':2,'allPass':True,'maxFacFac2AbsDelta':max(x['facFac2MaxAbsDelta'] for x in results),'maxChp2AbsDelta':max(x['chp2MaxAbsDelta'] for x in results),'maxChAbsDelta':max(x['chMaxAbsDelta'] for x in results),'maxDirectAbsDelta':max(x['directAbsDelta'] for x in results),'allUtauEndpointPreprocessBitExact':all(x['utauEndpointPreprocessBitExact'] for x in results),'cases':[x['caseId'] for x in results]}); core.manifest(e); return 0

if __name__=='__main__':
    try: rc=main()
    except Exception as exc:
        e=Path(os.environ.get('EVIDENCE_DIR','/tmp/r19e')); e.mkdir(parents=True,exist_ok=True); core.write_json(e/'fatal-barrier.json',{'classification':'STATE_0003_R19E_EXECUTION_BARRIER','errorType':type(exc).__name__,'error':str(exc)}); core.manifest(e); raise
    raise SystemExit(rc)
