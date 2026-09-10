#!/usr/bin/env python3
from __future__ import annotations
import csv, hashlib, importlib.util, json, os
from pathlib import Path

BASE_PATH = Path(os.environ['R19_BASE_DRIVER_PATH'])
spec = importlib.util.spec_from_file_location('r19base', BASE_PATH)
core = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(core)

CONSUMED = ['r16-srcdev-0001', 'r19-srcdev-repl-0011']
REPLACEMENT = ('r19-srcdev-repl-0012','development','0.54','89.46','733','0.39','DEFAULT')
EXEC_ROWS = [REPLACEMENT] + [r for r in core.CASE_ROWS if r[1]=='development' and r[0] != 'r16-srcdev-0001']
assert len(EXEC_ROWS) == 8
assert len({r[0] for r in EXEC_ROWS}) == 8
assert all(r[1]=='development' for r in EXEC_ROWS)
assert all(r[0] not in set(CONSUMED + ['r16-srcaud-0009','r16-srcaud-0010']) for r in EXEC_ROWS)


def abi_gdb_script(sdis, chekin, chp, flux):
    q = r'''set pagination off
set confirm off
set breakpoint pending on
python
import gdb,os,struct,hashlib,json
from pathlib import Path
d=Path(os.environ['CASE_DIR']); inf=gdb.selected_inferior()
def mem(a,n): return bytes(inf.read_memory(a,n))
def reg(name): return int(gdb.parse_and_eval('$'+name))
def i32p(a): return struct.unpack('<i',mem(a,4))[0]
def f32p(a): return struct.unpack('<f',mem(a,4))[0]
def f64p(a): return struct.unpack('<d',mem(a,8))[0]
def savej(name,x): (d/name).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def savebin(name,b): (d/name).write_bytes(b); return hashlib.sha256(b).hexdigest()
def argp(i):
    if i==1: return reg('rdi')
    if i==2: return reg('rsi')
    if i==3: return reg('rdx')
    if i==4: return reg('rcx')
    if i==5: return reg('r8')
    if i==6: return reg('r9')
    return struct.unpack('<Q',mem(reg('rsp')+8*(i-6),8))[0]
def fboolp(a): return i32p(a)!=0
pc=reg('pc'); rsp=reg('rsp'); rdi=reg('rdi'); rsi=reg('rsi'); rdx=reg('rdx'); entry=int(gdb.parse_and_eval('&@@SDIS@@'))
def outer_ptr(off): return struct.unpack('<Q',mem(rsp+off,8))[0]
nlyr=i32p(rdi); ntau=i32p(outer_ptr(24))
if not (0<nlyr<=256 and ntau==1): raise RuntimeError(('outer-shape',nlyr,ntau))
p={'utau':outer_ptr(32),'fbeam':outer_ptr(88),'umu0':outer_ptr(112),'newgeo':outer_ptr(128),'zd':outer_ptr(136),'spher':outer_ptr(144),'radius':outer_ptr(152),'planck':outer_ptr(208),'rfldir':outer_ptr(304),'nrefrac':outer_ptr(392),'ichap':outer_ptr(400),'vn':outer_ptr(408),'ndenssza':outer_ptr(416)}
h={}
for name,a,n in [('dtauc_f32le.bin',rsi,nlyr*4),('ssalb_f32le.bin',rdx,nlyr*4),('utau_entry_f32le.bin',p['utau'],4),('zd_f32le.bin',p['zd'],(nlyr+1)*4),('vn_f32le.bin',p['vn'],(nlyr+1)*4)]: h[name]=savebin(name,mem(a,n))
savej('entry-metadata.json',{'caseId':os.environ['CASE_ID'],'pcEqualsEntry':pc==entry,'nlyr':nlyr,'ntau':ntau,'fbeamF32':f32p(p['fbeam']),'umu0F32':f32p(p['umu0']),'radiusKmF32':f32p(p['radius']),'newgeoI32':i32p(p['newgeo']),'spherI32':i32p(p['spher']),'planckI32':i32p(p['planck']),'nrefrac':i32p(p['nrefrac']),'ichap':i32p(p['ichap']),'ndenssza':i32p(p['ndenssza']),'rawArraySha256':h,'captureMode':'SYSV_AMD64_BYREF_ARGUMENT_ORDINALS'})
outer_nlyr=nlyr
class OuterFinish(gdb.FinishBreakpoint):
    def __init__(self,frame,rfptr): super().__init__(frame,internal=True); self.rfptr=rfptr
    def stop(self):
        raw=mem(self.rfptr,4); savebin('final-rfldir-f32le.bin',raw); savej('outer-final.json',{'rfldirF32':struct.unpack('<f',raw)[0],'rawHex':raw.hex()}); return True
class ChekinFinish(gdb.FinishBreakpoint):
    def __init__(self,frame,up,tp,n): super().__init__(frame,internal=True); self.up=up; self.tp=tp; self.n=n
    def stop(self):
        u=f64p(self.up); ts=struct.unpack('<'+'d'*(self.n+1),mem(self.tp,8*(self.n+1))); savej('post-dpschekin.json',{'utauPost':u,'taucNlyr':ts[self.n],'taucSerial':list(ts)}); return False
class ChekinBP(gdb.Breakpoint):
    captured=False
    def stop(self):
        if ChekinBP.captured: return False
        n=i32p(argp(1)); up=argp(10); tp=argp(35)
        if n!=outer_nlyr: raise RuntimeError(('dpschekin-nlyr',n,outer_nlyr))
        u=f64p(up); ts=struct.unpack('<'+'d'*(n+1),mem(tp,8*(n+1))); savej('pre-dpschekin.json',{'utauPre':u,'taucNlyrPre':ts[n],'captureArgs':{'nlyr':1,'utau':10,'tauc':35}}); ChekinBP.captured=True; ChekinFinish(gdb.newest_frame(),up,tp,n); return False
class ChpFinish(gdb.FinishBreakpoint):
    def __init__(self,frame,num,n,cp): super().__init__(frame,internal=True); self.num=num; self.n=n; self.cp=cp
    def stop(self):
        if self.num==2: savebin('runtime-chp2-f64le.bin',mem(self.cp,8*self.n))
        return False
class ChpBP(gdb.Breakpoint):
    count=0
    def stop(self):
        ChpBP.count+=1; num=ChpBP.count
        n=i32p(argp(1)); zp=argp(2); np=argp(4); fp=argp(5); n2p=argp(6); f2p=argp(7); cp=argp(8); m=i32p(argp(9))
        if n!=outer_nlyr or not (n<=m<=4096): raise RuntimeError(('chpman2-shape',num,n,m,outer_nlyr))
        if num==2:
            nfac=struct.unpack('<'+'i'*n,mem(np,4*n)); nfac2=struct.unpack('<'+'i'*n,mem(n2p,4*n)); full=struct.unpack('<'+'d'*(m*m),mem(fp,8*m*m)); full2=struct.unpack('<'+'d'*(m*m),mem(f2p,8*m*m)); packed=[]; packed2=[]
            for i in range(n):
                for j in range(n): packed.append(full[j*m+i]); packed2.append(full2[j*m+i])
            savebin('runtime-fac-f64le.bin',struct.pack('<'+'d'*len(packed),*packed)); savebin('runtime-fac2-f64le.bin',struct.pack('<'+'d'*len(packed2),*packed2)); savebin('runtime-nfac-i32le.bin',struct.pack('<'+'i'*n,*nfac)); savebin('runtime-nfac2-i32le.bin',struct.pack('<'+'i'*n,*nfac2)); savej('second-chpman2-entry.json',{'callOrdinalWithinSdisort':num,'nlyr':n,'mxcly':m,'zenang':f64p(zp),'captureArgs':{'nlyr':1,'zenang':2,'nfac':4,'fac':5,'nfac2':6,'fac2':7,'chp':8,'mxcly':9}})
        ChpFinish(gdb.newest_frame(),num,n,cp); return False
class FluxFinish(gdb.FinishBreakpoint):
    def __init__(self,frame,rp): super().__init__(frame,internal=True); self.rp=rp
    def stop(self):
        raw=mem(self.rp,8); savebin('runtime-rfldir-f64le.bin',raw); savej('runtime-rfldir-double.json',{'rfldirFloat64':struct.unpack('<d',raw)[0]}); return False
class FluxBP(gdb.Breakpoint):
    captured=False
    def stop(self):
        if FluxBP.captured: return False
        cp=argp(1); fbp=argp(4); layp=argp(8); lcp=argp(10); ncp=argp(13); ntp=argp(16); ump=argp(21); up=argp(22); rp=argp(37)
        fb=f64p(fbp)
        if fb<=0: return False
        nt=i32p(ntp); ly=i32p(layp); nc=i32p(ncp); lc=fboolp(lcp); um=f64p(ump); u=f64p(up)
        if nt!=1 or not (1<=ly<=outer_nlyr): raise RuntimeError(('dpsfluxes-shape',nt,ly,outer_nlyr))
        ch=f64p(cp+8*(ly-1)); savebin('runtime-ch-f64le.bin',mem(cp,8*outer_nlyr)); savej('dpsfluxes-entry.json',{'fbeamFloat64':fb,'umu0Float64':um,'utauFloat64':u,'layru1':ly,'lyrcut':lc,'ncut':nc,'chAtLayru':ch,'ntau':nt,'captureArgs':{'ch':1,'fbeam':4,'layru':8,'lyrcut':10,'ncut':13,'ntau':16,'umu0':21,'utau':22,'rfldir':37}}); FluxBP.captured=True; FluxFinish(gdb.newest_frame(),rp); return False
OuterFinish(gdb.newest_frame(),p['rfldir']); ChekinBP('@@CHEKIN@@',internal=True); ChpBP('@@CHP@@',internal=True); FluxBP('@@FLUX@@',internal=True); gdb.execute('continue')
end
kill
quit
'''
    q = q.replace('@@SDIS@@', sdis).replace('@@CHEKIN@@', chekin).replace('@@CHP@@', chp).replace('@@FLUX@@', flux)
    lines=q.splitlines(); a=lines.index('python')+1; b=len(lines)-1-lines[::-1].index('end')
    compile('\n'.join(lines[a:b])+'\n','<r19c-gdb-python>','exec')
    forbidden=("ival('nlyr')","dval('fbeam')","dval('umu0')","addr('utau(1)')","addr('tauc(0)')","addr('chp(1)')","addr('ch(1)')")
    assert not any(x in q for x in forbidden), [x for x in forbidden if x in q]
    return q

core.gdb_script = abi_gdb_script


def sha_file(p:Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()


def main():
    e=Path(os.environ['EVIDENCE_DIR']); e.mkdir(parents=True,exist_ok=True); (e/'cases').mkdir(exist_ok=True)
    core.freeze(e)
    mp=e/'r19c-execution-matrix.csv'
    with mp.open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f,lineterminator='\n'); w.writerow(core.HEADER); w.writerows(EXEC_ROWS)
    freeze={
      'schemaVersion':1,
      'classification':'STATE_0003_R19C_FRESH_NONPROTECTED_ABI_CAPTURE_REPLACEMENT_FREEZE',
      'supersedesExecutionOnly':'R19/R19B after pre-result debugger plumbing barriers',
      'originalR16MatrixSha256':core.MATRIX_SHA,
      'originalR16ContractSha256':core.CONTRACT_SHA,
      'consumedWithoutOpenedScientificResult':CONSUMED,
      'consumptionPolicy':'conservative: any identity that reached the pinned sdisort entry is never reused, even when debugger stopped before solver result opening',
      'replacementIdentity':REPLACEMENT[0],
      'replacementRow':dict(zip(core.HEADER,REPLACEMENT)),
      'replacementSelectionBasis':'fresh a-priori NONPROTECTED coverage fixed before any R19C result; no protected/Taylor/Jerusalem evidence and no result-dependent selection',
      'executionOrder':[r[0] for r in EXEC_ROWS],
      'executionOrderReason':'new replacement first proves ABI capture plumbing before exposing the seven still-fresh R16 development rows',
      'runtimeCaptureMode':'SysV AMD64 Fortran by-reference argument ordinal capture; no DWARF local names required',
      'boundArgumentOrdinals':{
        'dpschekin':{'nlyr':1,'utau':10,'tauc':35},
        'chpman2':{'nlyr':1,'zenang':2,'nfac':4,'fac':5,'nfac2':6,'fac2':7,'chp':8,'mxcly':9},
        'dpsfluxes':{'ch':1,'fbeam':4,'layru':8,'lyrcut':10,'ncut':13,'ntau':16,'umu0':21,'utau':22,'rfldir':37}
      },
      'developmentRows':8,
      'auditRowsExecuted':0,
      'auditRowsRemainSealed':['r16-srcaud-0009','r16-srcaud-0010'],
      'stoppingRule':'stop on first mechanical capture barrier or first frozen-contract comparison failure; never execute audit in R19C',
      'postResultRetuning':'FORBIDDEN',
      'productionBelow5Deg':'FAIL_CLOSED_UNCHANGED'
    }
    core.write_json(e/'r19c-replacement-freeze.json',freeze)
    core.write_json(e/'r19c-freeze-hashes.json',{'executionMatrixSha256':sha_file(mp),'replacementFreezeSha256':sha_file(e/'r19c-replacement-freeze.json'),'baseDriverSha256':sha_file(BASE_PATH)})
    uvspec,data,gdb,nm,fc=core.bind_runtime(e); core.fresh_fence(e); lib=core.prepare_reference(e,fc); syms=core.resolve_symbols(uvspec,nm,e)
    abi_gdb_script(*syms)
    results=[]
    for row in EXEC_ROWS:
        x=core.run_case(e,row,uvspec,data,gdb,syms,lib)
        if x is None:
            core.write_json(e/'development-summary.json',{'classification':'STATE_0003_R19C_MECHANICAL_CAPTURE_BARRIER','failedCase':row[0],'developmentResultsOpened':len(results),'auditOpened':False,'consumedPriorIdentities':CONSUMED,'results':results}); core.manifest(e); return 21
        results.append(x)
        if not x['pass']:
            core.write_json(e/'development-summary.json',{'classification':'STATE_0003_R19C_FRESH_NONPROTECTED_RUNTIME_INTERNAL_DEVELOPMENT_NOT_PASS','failedCase':row[0],'developmentResultsOpened':len(results),'auditOpened':False,'consumedPriorIdentities':CONSUMED,'results':results}); core.manifest(e); return 23
    core.write_json(e/'development-summary.json',{'classification':'STATE_0003_R19C_FRESH_NONPROTECTED_RUNTIME_INTERNAL_DEVELOPMENT_PASS_8_OF_8','count':8,'auditOpened':False,'allPass':True,'consumedPriorIdentities':CONSUMED,'replacementIdentity':REPLACEMENT[0],'maxFacFac2AbsDelta':max(x['facFac2MaxAbsDelta'] for x in results),'maxChp2AbsDelta':max(x['chp2MaxAbsDelta'] for x in results),'maxChAbsDelta':max(x['chMaxAbsDelta'] for x in results),'maxDirectAbsDelta':max(x['directAbsDelta'] for x in results),'allUtauEndpointPreprocessBitExact':all(x['utauEndpointPreprocessBitExact'] for x in results),'cases':[x['caseId'] for x in results]}); core.manifest(e); return 0

if __name__=='__main__':
    try: rc=main()
    except Exception as exc:
        e=Path(os.environ.get('EVIDENCE_DIR','/tmp/r19c')); e.mkdir(parents=True,exist_ok=True); core.write_json(e/'fatal-barrier.json',{'classification':'STATE_0003_R19C_EXECUTION_BARRIER','errorType':type(exc).__name__,'error':str(exc),'auditOpened':False}); core.manifest(e); raise
    raise SystemExit(rc)
