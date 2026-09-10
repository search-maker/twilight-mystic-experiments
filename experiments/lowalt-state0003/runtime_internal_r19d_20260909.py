#!/usr/bin/env python3
from __future__ import annotations
import csv, hashlib, importlib.util, json, math, os, struct
from pathlib import Path

R19C_PATH=Path(os.environ['R19C_DRIVER_PATH'])
spec=importlib.util.spec_from_file_location('r19c',R19C_PATH)
r19c=importlib.util.module_from_spec(spec); assert spec.loader is not None; spec.loader.exec_module(r19c)
core=r19c.core

CONSUMED=['r16-srcdev-0001','r19-srcdev-repl-0011','r19-srcdev-repl-0012']
REPLACEMENT=('r19-srcdev-repl-0013','development','0.72','89.28','641','0.58','OFF')
EXEC_ROWS=[REPLACEMENT]+[r for r in core.CASE_ROWS if r[1]=='development' and r[0] != 'r16-srcdev-0001']
assert len(EXEC_ROWS)==8 and len({r[0] for r in EXEC_ROWS})==8
assert all(r[0] not in set(CONSUMED+['r16-srcaud-0009','r16-srcaud-0010']) for r in EXEC_ROWS)

_orig_reference_values=core.reference_values
def source_exact_reference_values(libpath:Path,case:Path,m:dict):
    # dpssetdis calls GEOFAST twice. GEOFAST mutates rearth *= 1D5; after
    # the first call dpssetdis restores rearth *= 1D-5 before the z_lay=.5
    # call that governs CHP2. Preserve that exact binary64 state propagation.
    mm=dict(m)
    r0=float(m['radiusKmF32'])
    r_after_first=(r0*1.0e5)*1.0e-5
    mm['radiusKmF32']=r_after_first
    out=_orig_reference_values(libpath,case,mm)
    out['referenceRadiusInputF64']=r0
    out['referenceRadiusAtSecondGeofastF64']=r_after_first
    out['referenceRadiusAtSecondGeofastBits']=struct.unpack('<Q',struct.pack('<d',r_after_first))[0]
    return out
core.reference_values=source_exact_reference_values


def sha_file(p:Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()


def main():
    e=Path(os.environ['EVIDENCE_DIR']); e.mkdir(parents=True,exist_ok=True); (e/'cases').mkdir(exist_ok=True)
    core.freeze(e)
    mp=e/'r19d-execution-matrix.csv'
    with mp.open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f,lineterminator='\n'); w.writerow(core.HEADER); w.writerows(EXEC_ROWS)
    source_binding={
      'schemaVersion':1,
      'classification':'STATE_0003_R19D_SOURCE_EXACT_SECOND_GEOFAST_RADIUS_STATE_BINDING',
      'sourceRule':'first GEOFAST mutates REARTH by *1D5; DPSSETDIS restores by *1D-5; second GEOFAST therefore consumes the post-roundtrip binary64 REARTH state',
      'referenceImplementation':'pass ((captured radius)*1e5)*1e-5 as the starting km radius to the standalone second-GEOFAST reference; its internal GEOFAST *1e5 then matches runtime second-call geometry',
      'empiricalOffsetOrFit':False,
      'toleranceChanged':False,
      'protectedResidualUsed':False,
      'r19cExistingNonprotectedDiagnosticOnly':'the already-open R19C replacement confirmed this source-derived correction makes FAC/FAC2/CHP2/CH bit-exact; it is not reused as R19D execution evidence',
      'productionBelow5Deg':'FAIL_CLOSED_UNCHANGED'
    }
    core.write_json(e/'r19d-radius-state-binding.json',source_binding)
    freeze={
      'schemaVersion':1,
      'classification':'STATE_0003_R19D_FRESH_NONPROTECTED_RADIUS_STATE_CORRECTED_DEVELOPMENT_FREEZE',
      'originalR16MatrixSha256':core.MATRIX_SHA,
      'originalR16ContractSha256':core.CONTRACT_SHA,
      'consumedWithoutReuse':CONSUMED,
      'replacementIdentity':REPLACEMENT[0],
      'replacementRow':dict(zip(core.HEADER,REPLACEMENT)),
      'replacementSelectionBasis':'fresh a-priori NONPROTECTED low-altitude coverage fixed before any R19D result; no protected/Taylor/Jerusalem evidence and no result-dependent selection',
      'executionOrder':[r[0] for r in EXEC_ROWS],
      'executionOrderReason':'fresh replacement first validates the source-derived radius-state correction before exposing the seven still-fresh R16 development rows',
      'referenceCorrection':'source-exact first-GEOFAST REARTH binary64 roundtrip propagated into second GEOFAST',
      'developmentRows':8,
      'auditRowsExecuted':0,
      'auditRowsRemainSealed':['r16-srcaud-0009','r16-srcaud-0010'],
      'stoppingRule':'stop on first mechanical capture barrier or first frozen-contract comparison failure; never execute audit in R19D',
      'postResultRetuning':'FORBIDDEN',
      'productionBelow5Deg':'FAIL_CLOSED_UNCHANGED'
    }
    core.write_json(e/'r19d-freeze.json',freeze)
    core.write_json(e/'r19d-freeze-hashes.json',{'executionMatrixSha256':sha_file(mp),'freezeSha256':sha_file(e/'r19d-freeze.json'),'radiusBindingSha256':sha_file(e/'r19d-radius-state-binding.json'),'r19cDriverSha256':sha_file(R19C_PATH)})
    uvspec,data,gdb,nm,fc=core.bind_runtime(e); core.fresh_fence(e); lib=core.prepare_reference(e,fc); syms=core.resolve_symbols(uvspec,nm,e); r19c.abi_gdb_script(*syms)
    results=[]
    for row in EXEC_ROWS:
        x=core.run_case(e,row,uvspec,data,gdb,syms,lib)
        if x is None:
            core.write_json(e/'development-summary.json',{'classification':'STATE_0003_R19D_MECHANICAL_CAPTURE_BARRIER','failedCase':row[0],'developmentResultsOpened':len(results),'auditOpened':False,'consumedPriorIdentities':CONSUMED,'results':results}); core.manifest(e); return 21
        results.append(x)
        if not x['pass']:
            core.write_json(e/'development-summary.json',{'classification':'STATE_0003_R19D_FRESH_NONPROTECTED_RADIUS_STATE_CORRECTED_DEVELOPMENT_NOT_PASS','failedCase':row[0],'developmentResultsOpened':len(results),'auditOpened':False,'consumedPriorIdentities':CONSUMED,'results':results}); core.manifest(e); return 23
    core.write_json(e/'development-summary.json',{'classification':'STATE_0003_R19D_FRESH_NONPROTECTED_RADIUS_STATE_CORRECTED_DEVELOPMENT_PASS_8_OF_8','count':8,'auditOpened':False,'allPass':True,'consumedPriorIdentities':CONSUMED,'replacementIdentity':REPLACEMENT[0],'maxFacFac2AbsDelta':max(x['facFac2MaxAbsDelta'] for x in results),'maxChp2AbsDelta':max(x['chp2MaxAbsDelta'] for x in results),'maxChAbsDelta':max(x['chMaxAbsDelta'] for x in results),'maxDirectAbsDelta':max(x['directAbsDelta'] for x in results),'allUtauEndpointPreprocessBitExact':all(x['utauEndpointPreprocessBitExact'] for x in results),'cases':[x['caseId'] for x in results]}); core.manifest(e); return 0

if __name__=='__main__':
    try: rc=main()
    except Exception as exc:
        e=Path(os.environ.get('EVIDENCE_DIR','/tmp/r19d')); e.mkdir(parents=True,exist_ok=True); core.write_json(e/'fatal-barrier.json',{'classification':'STATE_0003_R19D_EXECUTION_BARRIER','errorType':type(exc).__name__,'error':str(exc),'auditOpened':False}); core.manifest(e); raise
    raise SystemExit(rc)
