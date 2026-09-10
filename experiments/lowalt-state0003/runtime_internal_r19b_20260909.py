#!/usr/bin/env python3
from __future__ import annotations
import csv, hashlib, importlib.util, json, os
from pathlib import Path

BASE_PATH = Path(os.environ['R19_BASE_DRIVER_PATH'])
spec = importlib.util.spec_from_file_location('r19base', BASE_PATH)
core = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(core)

CONSUMED = 'r16-srcdev-0001'
REPLACEMENT = ('r19-srcdev-repl-0011','development','0.63','89.37','673','0.47','OFF')
EXEC_ROWS = [REPLACEMENT] + [r for r in core.CASE_ROWS if r[1]=='development' and r[0] != CONSUMED]
assert len(EXEC_ROWS) == 8
assert len({r[0] for r in EXEC_ROWS}) == 8
assert all(r[1]=='development' for r in EXEC_ROWS)
assert all(r[0] not in {CONSUMED,'r16-srcaud-0009','r16-srcaud-0010'} for r in EXEC_ROWS)

_old_gdb_script = core.gdb_script
def fixed_gdb_script(sdis, chekin, chp, flux):
    text = _old_gdb_script(sdis, chekin, chp, flux)
    bad = "entry=int(gdb.parse_and_eval('&%s))" % sdis
    good = "entry=int(gdb.parse_and_eval('&%s'))" % sdis
    if bad not in text:
        raise RuntimeError(('expected-r19-gdb-syntax-defect-not-found', bad))
    text = text.replace(bad, good, 1)
    lines = text.splitlines()
    a = lines.index('python') + 1
    b = len(lines) - 1 - lines[::-1].index('end')
    compile('\n'.join(lines[a:b])+'\n', '<r19b-gdb-python>', 'exec')
    return text
core.gdb_script = fixed_gdb_script

def sha_file(p:Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def main():
    e=Path(os.environ['EVIDENCE_DIR']); e.mkdir(parents=True,exist_ok=True); (e/'cases').mkdir(exist_ok=True)
    core.freeze(e)
    mp=e/'r19b-execution-matrix.csv'
    with mp.open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f,lineterminator='\n'); w.writerow(core.HEADER); w.writerows(EXEC_ROWS)
    replacement_freeze={
      'schemaVersion':1,
      'classification':'STATE_0003_R19B_FRESH_NONPROTECTED_MECHANICAL_REPLACEMENT_FREEZE',
      'supersedesExecutionOnly':'R19 development execution after pre-body GDB syntax barrier',
      'originalR16MatrixSha256':core.MATRIX_SHA,
      'originalR16ContractSha256':core.CONTRACT_SHA,
      'consumedWithoutOpenedResult':CONSUMED,
      'consumptionReason':'pinned sdisort entry breakpoint was reached before debugger-script parse failure; solver body/result not opened; identity is conservatively never reused',
      'replacementIdentity':REPLACEMENT[0],
      'replacementRow':dict(zip(core.HEADER,REPLACEMENT)),
      'replacementSelectionBasis':'fresh coverage row fixed after a purely mechanical pre-body failure; no R19 scientific result existed or was opened; no protected/Taylor/Jerusalem evidence used',
      'executionOrder':[r[0] for r in EXEC_ROWS],
      'executionOrderReason':'fresh replacement first proves debugger plumbing before exposing the seven still-fresh R16 development rows',
      'developmentRows':8,
      'auditRowsExecuted':0,
      'auditRowsRemainSealed':['r16-srcaud-0009','r16-srcaud-0010'],
      'stoppingRule':'stop on first mechanical capture barrier or first frozen-contract comparison failure; never execute audit in R19B',
      'postResultRetuning':'FORBIDDEN',
      'productionBelow5Deg':'FAIL_CLOSED_UNCHANGED'
    }
    core.write_json(e/'r19b-replacement-freeze.json',replacement_freeze)
    core.write_json(e/'r19b-freeze-hashes.json',{'executionMatrixSha256':sha_file(mp),'replacementFreezeSha256':sha_file(e/'r19b-replacement-freeze.json'),'baseDriverSha256':sha_file(BASE_PATH)})
    uvspec,data,gdb,nm,fc=core.bind_runtime(e); core.fresh_fence(e); lib=core.prepare_reference(e,fc); syms=core.resolve_symbols(uvspec,nm,e)
    results=[]
    for row in EXEC_ROWS:
        x=core.run_case(e,row,uvspec,data,gdb,syms,lib)
        if x is None:
            core.write_json(e/'development-summary.json',{'classification':'STATE_0003_R19B_MECHANICAL_CAPTURE_BARRIER','failedCase':row[0],'developmentResultsOpened':len(results),'auditOpened':False,'consumedOriginalR16Dev0001':True,'results':results}); core.manifest(e); return 21
        results.append(x)
        if not x['pass']:
            core.write_json(e/'development-summary.json',{'classification':'STATE_0003_R19B_FRESH_NONPROTECTED_RUNTIME_INTERNAL_DEVELOPMENT_NOT_PASS','failedCase':row[0],'developmentResultsOpened':len(results),'auditOpened':False,'consumedOriginalR16Dev0001':True,'results':results}); core.manifest(e); return 23
    core.write_json(e/'development-summary.json',{'classification':'STATE_0003_R19B_FRESH_NONPROTECTED_RUNTIME_INTERNAL_DEVELOPMENT_PASS_8_OF_8','count':8,'auditOpened':False,'allPass':True,'consumedOriginalR16Dev0001':True,'replacementIdentity':REPLACEMENT[0],'maxFacFac2AbsDelta':max(x['facFac2MaxAbsDelta'] for x in results),'maxChp2AbsDelta':max(x['chp2MaxAbsDelta'] for x in results),'maxChAbsDelta':max(x['chMaxAbsDelta'] for x in results),'maxDirectAbsDelta':max(x['directAbsDelta'] for x in results),'allUtauEndpointPreprocessBitExact':all(x['utauEndpointPreprocessBitExact'] for x in results),'cases':[x['caseId'] for x in results]}); core.manifest(e); return 0

if __name__=='__main__':
    try: rc=main()
    except Exception as exc:
        e=Path(os.environ.get('EVIDENCE_DIR','/tmp/r19b')); e.mkdir(parents=True,exist_ok=True); core.write_json(e/'fatal-barrier.json',{'classification':'STATE_0003_R19B_EXECUTION_BARRIER','errorType':type(exc).__name__,'error':str(exc),'auditOpened':False}); core.manifest(e); raise
    raise SystemExit(rc)
