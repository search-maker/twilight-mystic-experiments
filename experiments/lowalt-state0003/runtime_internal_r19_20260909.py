#!/usr/bin/env python3
from __future__ import annotations
import csv, ctypes, hashlib, json, math, os, shlex, shutil, struct, subprocess, sys
from pathlib import Path

CASE_ROWS = [
    ('r16-srcdev-0001','development','0.38','89.62','413','0.18','OFF'),
    ('r16-srcdev-0002','development','0.91','89.09','487','0.73','DEFAULT'),
    ('r16-srcdev-0003','development','1.46','88.54','557','1.21','OFF'),
    ('r16-srcdev-0004','development','2.08','87.92','621','0.31','DEFAULT'),
    ('r16-srcdev-0005','development','2.77','87.23','701','1.88','OFF'),
    ('r16-srcdev-0006','development','3.36','86.64','445','2.24','DEFAULT'),
    ('r16-srcdev-0007','development','4.09','85.91','589','0.96','OFF'),
    ('r16-srcdev-0008','development','4.86','85.14','763','1.52','DEFAULT'),
    ('r16-srcaud-0009','audit','1.19','88.81','672','2.07','DEFAULT'),
    ('r16-srcaud-0010','audit','3.73','86.27','526','0.54','OFF'),
]
HEADER=['identity','role','target_altitude_deg','sza_deg','wavelength_nm','observer_altitude_km','aerosol_mode']
MATRIX_SHA='8cc873592650dadb2f3ed0f33fc41903c69e5788750a7cf29fd9921beb7edb9a'
CONTRACT_SHA='d7ef6a8e68c436728f71eba6e616126deb9f2d485af4926da4b2a294384475ca'
UVSPEC_SHA='2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3'
PACKAGE_SPEC='rubin-libradtran=2.0.6=py312pl5321he9373c2_1'
R16_COMMENT=5608882325
R18_COMMENT=5611162910
SOURCE_SHA='999e47f4af4b5df6f85a6887fc105fc8f6e1a7cee89a3124f69ac8d8912c8e85'
STARS_SHA='1e74d0522f086dba634a587bb245c32bcd4fac60'

def sha_file(p:Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()
def write_json(p:Path,x): p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def f64bits(x:float)->int: return struct.unpack('<Q',struct.pack('<d',float(x)))[0]
def ok_tol(a:float,b:float,tol:float)->bool:
    return math.isfinite(a) and math.isfinite(b) and (abs(a-b) <= tol or abs(a-b) <= tol*max(abs(a),abs(b)))
def api_get(url:str,token:str):
    import urllib.request
    req=urllib.request.Request(url,headers={'Accept':'application/vnd.github+json','Authorization':'Bearer '+token,'X-GitHub-Api-Version':'2022-11-28','User-Agent':'lowalt-state0003-r19'})
    with urllib.request.urlopen(req,timeout=90) as r: return json.load(r)

def freeze(e:Path):
    p=e/'fresh-nonprotected-matrix.csv'
    with p.open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f,lineterminator='\n'); w.writerow(HEADER); w.writerows(CASE_ROWS)
    assert sha_file(p)==MATRIX_SHA,(sha_file(p),MATRIX_SHA)
    c=Path(os.environ['R16_CONTRACT_PATH']); assert sha_file(c)==CONTRACT_SHA,(sha_file(c),CONTRACT_SHA); shutil.copy2(c,e/'frozen-contract.json')
    write_json(e/'r19-execution-freeze.json',{'schemaVersion':1,'classification':'STATE_0003_R19_FRESH_NONPROTECTED_RUNTIME_INTERNAL_DEVELOPMENT_CAPTURE_FREEZE','r16MatrixSha256':MATRIX_SHA,'r16ContractSha256':CONTRACT_SHA,'developmentRowsAuthorized':[r[0] for r in CASE_ROWS if r[1]=='development'],'auditRows':[r[0] for r in CASE_ROWS if r[1]=='audit'],'auditOpened':False,'stoppingRule':'stop immediately on first mechanical capture failure or first frozen-contract development comparison failure; never execute audit in R19','entryUtauCapture':True,'taucNlyrCapture':True,'postDpschekinUtauCapture':True,'secondChpman2NfacFacFac2Chp2Capture':True,'dpsfluxesChAndPreReal4RfldirCapture':True,'utauReferenceRule':'exact dpschekin endpoint snap: absolute <=1e-4 then relative <=1e-6, using serial double TAUC sum','structuralComparison':'EXACT','facFac2Chp2ChTolerance':1e-10,'directFloat64Tolerance':1e-12,'postResultRetuning':'FORBIDDEN','protectedResidualSelection':'FORBIDDEN','taylorJerusalem':'FORBIDDEN','r12ConsumedIdentities':'DO_NOT_RERUN_OR_REUSE','productionBelow5Deg':'FAIL_CLOSED_UNCHANGED'})

def bind_runtime(e:Path):
    uvspec=Path(shutil.which('uvspec') or ''); assert uvspec.is_file(); assert sha_file(uvspec)==UVSPEC_SHA,(sha_file(uvspec),UVSPEC_SHA)
    raw=subprocess.check_output(['micromamba','list','rubin-libradtran','--json'],text=True); (e/'micromamba-rubin-libradtran.json').write_text(raw,encoding='utf-8'); x=json.loads(raw); rows=[]
    def walk(v):
        if isinstance(v,dict):
            if v.get('name')=='rubin-libradtran': rows.append(v)
            for z in v.values(): walk(z)
        elif isinstance(v,list):
            for z in v: walk(z)
    walk(x); specs={f"rubin-libradtran={r.get('version')}={r.get('build_string',r.get('build'))}" for r in rows if r.get('version') and r.get('build_string',r.get('build'))}; assert specs=={PACKAGE_SPEC},specs
    data=Path(os.environ['CONDA_PREFIX'])/'share/libRadtran/data'; assert (data/'atmmod/afglus.dat').is_file(); gdb=Path(shutil.which('gdb') or ''); nm=Path(shutil.which('nm') or ''); assert gdb.is_file() and nm.is_file()
    fc=os.environ.get('FC','').strip(); assert fc; fc_cmd=shlex.split(fc)[0]; assert shutil.which(fc_cmd)
    write_json(e/'runtime-binding.json',{'uvspec':str(uvspec),'uvspecSha256':sha_file(uvspec),'packageSpec':PACKAGE_SPEC,'dataDir':str(data),'gdb':str(gdb),'fc':fc,'fflags':os.environ.get('FFLAGS','')}); return uvspec,data,gdb,nm,fc_cmd

def fresh_fence(e:Path):
    gh=os.environ['GH_TOKEN']; st=os.environ['STARSVISIBILITY_READ_TOKEN']; repo=os.environ['GITHUB_REPOSITORY']; runid=int(os.environ['GITHUB_RUN_ID'])
    issue=api_get(f'https://api.github.com/repos/{repo}/issues/60',gh); count=int(issue['comments']); latest=api_get(f'https://api.github.com/repos/{repo}/issues/60/comments?per_page=1&page={count}',gh); assert len(latest)==1
    r16=api_get(f'https://api.github.com/repos/{repo}/issues/comments/{R16_COMMENT}',gh); r18=api_get(f'https://api.github.com/repos/{repo}/issues/comments/{R18_COMMENT}',gh); assert 'STATE_0003' in r16['body'] and 'R16' in r16['body']; assert 'UTAU' in r18['body'] and 'STATE_0003' in r18['body']
    main=api_get(f'https://api.github.com/repos/{repo}/branches/main',gh)['commit']['sha']; stars=api_get('https://api.github.com/repos/search-maker/starsvisibility/branches/main',st)['commit']['sha']; assert stars==STARS_SHA,(stars,STARS_SHA); avps=api_get(f'https://api.github.com/repos/{repo}/pulls/1026',gh)
    actions={}
    for status in ('in_progress','queued'):
        rs=api_get(f'https://api.github.com/repos/{repo}/actions/runs?status={status}&per_page=100',gh)['workflow_runs']; actions[status]=[{'id':int(r['id']),'name':r.get('name'),'head_branch':r.get('head_branch'),'head_sha':r.get('head_sha')} for r in rs if int(r['id'])!=runid]
    write_json(e/'fresh-pre-solver-fence.json',{'issue60Comments':count,'latestIssue60CommentId':int(latest[0]['id']),'latestIssue60CreatedAt':latest[0]['created_at'],'r16CommentId':R16_COMMENT,'r18CommentId':R18_COMMENT,'twilightMain':main,'starsMain':stars,'avpsPr1026State':avps['state'],'avpsPr1026Draft':avps['draft'],'avpsPr1026Head':avps['head']['sha'],'otherActions':actions,'activeActionAloneIsNotAConcurrencyBlock':True,'productionBelow5Deg':'FAIL_CLOSED_UNCHANGED'})

def prepare_reference(e:Path,fc_cmd:str):
    src=Path(os.environ['SOURCE_ROOT']); assert (src/'libsrc_f/dpmisc.f').is_file() and (src/'libsrc_f/DISORT.MXD').is_file(); assert os.environ.get('SOURCE_ENTITY_SHA256')==SOURCE_SHA
    w=e/'reference'; w.mkdir(exist_ok=True); shutil.copy2(src/'libsrc_f/DISORT.MXD',w/'DISORT.MXD'); lines=(src/'libsrc_f/dpmisc.f').read_text(encoding='utf-8',errors='strict').splitlines(keepends=True); exact=''.join(lines[935:1740]+lines[3254:3325]); (w/'geofast_exact.f').write_text(exact,encoding='utf-8')
    wrapper=r'''      subroutine direct_ref_full(nlyr,dtauc,zd,vn,umu0,radius,
     $ nfacout,nfac2out,facout,fac2out,chpout,chout)
      include 'DISORT.MXD'
      integer nlyr,nfacout(*),nfac2out(*),mxcly_arg,brosza
      integer nfac(1:mxcly),nfac2(1:mxcly)
      real*8 dtauc(*),zd(0:*),vn(0:*),umu0,radius
      real*8 facout(*),fac2out(*),chpout(*),chout(*)
      real*8 fac(1:mxcly,1:mxcly),fac2(1:mxcly,1:mxcly)
      real*8 szaloc(1:mxcly,0:mxcly),szaloc2(1:mxcly,0:mxcly)
      real*8 sza_bro(mxsza),chp(1:mxcly),tauc(0:mxcly)
      real*8 zenang,z_lay,rearth,pi,taup
      integer i,j,idx
      pi=dacos(-1.d0)
      zenang=dacos(umu0)*180.d0/pi
      z_lay=0.5d0
      rearth=radius
      brosza=0
      do i=1,mxsza
        sza_bro(i)=0.d0
      enddo
      call geofast(brosza,sza_bro,fac,nfac,szaloc,
     $ fac2,nfac2,szaloc2,z_lay,nlyr,zd,zenang,rearth,vn)
      mxcly_arg=mxcly
      call chpman2(nlyr,zenang,dtauc,nfac,fac,nfac2,fac2,
     $ chp,mxcly_arg)
      tauc(0)=0.d0
      do i=1,nlyr
        tauc(i)=tauc(i-1)+dtauc(i)
        taup=tauc(i-1)+dtauc(i)/2.d0
        chout(i)=taup/chp(i)
        chpout(i)=chp(i)
        nfacout(i)=nfac(i)
        nfac2out(i)=nfac2(i)
      enddo
      do i=1,nlyr
        do j=1,nlyr
          idx=(i-1)*nlyr+j
          facout(idx)=fac(i,j)
          fac2out(idx)=fac2(i,j)
        enddo
      enddo
      return
      end
'''
    (w/'direct_ref_full.f').write_text(wrapper,encoding='utf-8'); cmd=[fc_cmd,*shlex.split(os.environ.get('FFLAGS','')),'-fPIC','-ffixed-line-length-none','-shared','geofast_exact.f','direct_ref_full.f','-o','libdirect_ref_full.so']; subprocess.run(cmd,cwd=w,check=True,stdout=(w/'compile.stdout').open('w'),stderr=(w/'compile.stderr').open('w')); lib=w/'libdirect_ref_full.so'; assert lib.is_file(); write_json(w/'reference-binding.json',{'sourceEntitySha256':SOURCE_SHA,'dpmiscSha256':sha_file(src/'libsrc_f/dpmisc.f'),'sourceSliceSha256':sha_file(w/'geofast_exact.f'),'librarySha256':sha_file(lib),'compileCommand':cmd}); return lib

def resolve_symbols(uvspec:Path,nm:Path,e:Path):
    txt=subprocess.check_output([str(nm),'-an',str(uvspec)],text=True,errors='replace'); (e/'nm-all.txt').write_text(txt,encoding='utf-8'); names={p[-1] for line in txt.splitlines() if len((p:=line.split()))>=3}; sdis=[x for x in ('sdisort','sdisort_') if x in names]; assert len(sdis)==1,sdis; need=[]
    for base in ('dpschekin','chpman2','dpsfluxes'):
        got=[x for x in (base,base+'_') if x in names]; assert len(got)==1,(base,got); need.append(got[0])
    write_json(e/'resolved-symbols.json',{'sdisort':sdis[0],'dpschekin':need[0],'chpman2':need[1],'dpsfluxes':need[2]}); return sdis[0],need[0],need[1],need[2]

def build_input(data:Path,row,case:Path):
    cid,role,alt,sza,wl,site,aer=row; atm=data/'atmmod/afglus.dat'; sitef=float(site); levels=[]
    for raw in atm.read_text(encoding='utf-8').splitlines():
        q=raw.strip()
        if q and not q.startswith('#'): levels.append(float(q.split()[0]))
    assert len(levels)>2 and all(levels[i]>levels[i+1] for i in range(len(levels)-1)); grid=[sitef,*sorted(z for z in levels if z>sitef)]; assert all(grid[i]<grid[i+1] for i in range(len(grid)-1))
    lines=[f'data_files_path {atm.parent.parent}',f'atmosphere_file {atm}','source solar','mol_abs_param crs',f'wavelength {int(wl)} {int(wl)}',f'sza {float(sza):.8f}','atm_z_grid '+' '.join(f'{z:.6f}' for z in grid),'zout 0.000000','albedo 0.15000000','rte_solver sdisort','sdisort nscat 1','output_quantity transmittance','output_user lambda edir','quiet'];
    if aer=='DEFAULT': lines.insert(4,'aerosol_default')
    else: assert aer=='OFF'
    text='\n'.join(lines)+'\n'; low=text.lower();
    for token in ('rte_solver mystic','aerosol_set_tau','nrefrac','refraction','altitude '): assert token not in low,token
    p=case/'input.inp'; p.write_text(text,encoding='utf-8'); (case/'input.sha256').write_text(sha_file(p)+'  input.inp\n',encoding='utf-8'); return p

def gdb_script(sdis:str,chekin:str,chp:str,flux:str)->str:
    return r'''set pagination off
set confirm off
set breakpoint pending on
python
import gdb,os,struct,hashlib,json
from pathlib import Path
d=Path(os.environ['CASE_DIR']); inf=gdb.selected_inferior()
def mem(a,n): return bytes(inf.read_memory(a,n))
def addr(expr): return int(gdb.parse_and_eval('&'+expr))
def ival(expr): return int(gdb.parse_and_eval(expr))
def dval(expr): return float(gdb.parse_and_eval(expr))
def savej(name,x): (d/name).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def savebin(name,b): (d/name).write_bytes(b); return hashlib.sha256(b).hexdigest()
pc=int(gdb.parse_and_eval('$pc')); rsp=int(gdb.parse_and_eval('$rsp')); rdi=int(gdb.parse_and_eval('$rdi')); rsi=int(gdb.parse_and_eval('$rsi')); rdx=int(gdb.parse_and_eval('$rdx')); entry=int(gdb.parse_and_eval('&'''+sdis+r'''))
def ptr(off): return struct.unpack('<Q',mem(rsp+off,8))[0]
def i32p(a): return struct.unpack('<i',mem(a,4))[0]
def f32p(a): return struct.unpack('<f',mem(a,4))[0]
nlyr=i32p(rdi); ntau=i32p(ptr(24))
if not (0<nlyr<=256 and ntau==1): raise RuntimeError(('outer-shape',nlyr,ntau))
p={'utau':ptr(32),'fbeam':ptr(88),'umu0':ptr(112),'newgeo':ptr(128),'zd':ptr(136),'spher':ptr(144),'radius':ptr(152),'planck':ptr(208),'rfldir':ptr(304),'nrefrac':ptr(392),'ichap':ptr(400),'vn':ptr(408),'ndenssza':ptr(416)}
h={}
for name,a,n in [('dtauc_f32le.bin',rsi,nlyr*4),('ssalb_f32le.bin',rdx,nlyr*4),('utau_entry_f32le.bin',p['utau'],4),('zd_f32le.bin',p['zd'],(nlyr+1)*4),('vn_f32le.bin',p['vn'],(nlyr+1)*4)]: h[name]=savebin(name,mem(a,n))
savej('entry-metadata.json',{'caseId':os.environ['CASE_ID'],'pcEqualsEntry':pc==entry,'nlyr':nlyr,'ntau':ntau,'fbeamF32':f32p(p['fbeam']),'umu0F32':f32p(p['umu0']),'radiusKmF32':f32p(p['radius']),'newgeoI32':i32p(p['newgeo']),'spherI32':i32p(p['spher']),'planckI32':i32p(p['planck']),'nrefrac':i32p(p['nrefrac']),'ichap':i32p(p['ichap']),'ndenssza':i32p(p['ndenssza']),'rawArraySha256':h})
class OuterFinish(gdb.FinishBreakpoint):
    def __init__(self,frame,rfptr): super().__init__(frame,internal=True); self.rfptr=rfptr
    def stop(self):
        raw=mem(self.rfptr,4); savebin('final-rfldir-f32le.bin',raw); savej('outer-final.json',{'rfldirF32':struct.unpack('<f',raw)[0],'rawHex':raw.hex()}); return True
class ChekinFinish(gdb.FinishBreakpoint):
    def __init__(self,frame,up,tp,n): super().__init__(frame,internal=True); self.up=up; self.tp=tp; self.n=n
    def stop(self):
        u=struct.unpack('<d',mem(self.up,8))[0]; ts=struct.unpack('<'+'d'*(self.n+1),mem(self.tp,8*(self.n+1))); savej('post-dpschekin.json',{'utauPost':u,'taucNlyr':ts[self.n],'taucSerial':list(ts)}); return False
class ChekinBP(gdb.Breakpoint):
    def stop(self):
        n=ival('nlyr'); up=addr('utau(1)'); tp=addr('tauc(0)'); u=struct.unpack('<d',mem(up,8))[0]; ts=struct.unpack('<'+'d'*(n+1),mem(tp,8*(n+1))); savej('pre-dpschekin.json',{'utauPre':u,'taucNlyrPre':ts[n]}); ChekinFinish(gdb.newest_frame(),up,tp,n); return False
class ChpFinish(gdb.FinishBreakpoint):
    def __init__(self,frame,num,n,cp): super().__init__(frame,internal=True); self.num=num; self.n=n; self.cp=cp
    def stop(self):
        if self.num==2: savebin('runtime-chp2-f64le.bin',mem(self.cp,8*self.n))
        return False
class ChpBP(gdb.Breakpoint):
    count=0
    def stop(self):
        caller=(gdb.newest_frame().older().name() or '').lower() if gdb.newest_frame().older() else ''
        if 'dpssetdis' not in caller: return False
        ChpBP.count+=1; num=ChpBP.count; n=ival('nlyr'); m=ival('mxcly'); cp=addr('chp(1)')
        if num==2:
            np=addr('nfac(1)'); n2p=addr('nfac_2(1)'); fp=addr('fac(1,1)'); f2p=addr('fac_2(1,1)'); nfac=struct.unpack('<'+'i'*n,mem(np,4*n)); nfac2=struct.unpack('<'+'i'*n,mem(n2p,4*n)); full=struct.unpack('<'+'d'*(m*m),mem(fp,8*m*m)); full2=struct.unpack('<'+'d'*(m*m),mem(f2p,8*m*m)); packed=[]; packed2=[]
            for i in range(n):
                for j in range(n): packed.append(full[j*m+i]); packed2.append(full2[j*m+i])
            savebin('runtime-fac-f64le.bin',struct.pack('<'+'d'*len(packed),*packed)); savebin('runtime-fac2-f64le.bin',struct.pack('<'+'d'*len(packed2),*packed2)); savebin('runtime-nfac-i32le.bin',struct.pack('<'+'i'*n,*nfac)); savebin('runtime-nfac2-i32le.bin',struct.pack('<'+'i'*n,*nfac2)); savej('second-chpman2-entry.json',{'callOrdinalWithinDpssetdis':num,'nlyr':n,'mxcly':m,'zenang':dval('zenang')})
        ChpFinish(gdb.newest_frame(),num,n,cp); return False
class FluxFinish(gdb.FinishBreakpoint):
    def __init__(self,frame,rp): super().__init__(frame,internal=True); self.rp=rp
    def stop(self):
        raw=mem(self.rp,8); savebin('runtime-rfldir-f64le.bin',raw); savej('runtime-rfldir-double.json',{'rfldirFloat64':struct.unpack('<d',raw)[0]}); return False
class FluxBP(gdb.Breakpoint):
    captured=False
    def stop(self):
        if FluxBP.captured: return False
        fb=dval('fbeam')
        if fb<=0: return False
        n=ival('ntau'); ly=ival('layru(1)'); nc=ival('ncut'); lc=bool(gdb.parse_and_eval('lyrcut')); um=dval('umu0'); u=dval('utau(1)'); ch=dval('ch(%d)'%ly); rp=addr('rfldir(1)'); nlyr=int(os.environ['NLYR']); cp=addr('ch(1)'); savebin('runtime-ch-f64le.bin',mem(cp,8*nlyr)); savej('dpsfluxes-entry.json',{'fbeamFloat64':fb,'umu0Float64':um,'utauFloat64':u,'layru1':ly,'lyrcut':lc,'ncut':nc,'chAtLayru':ch,'ntau':n}); FluxBP.captured=True; FluxFinish(gdb.newest_frame(),rp); return False
OuterFinish(gdb.newest_frame(),p['rfldir']); ChekinBP('''+repr(chekin)+r''',internal=True); ChpBP('''+repr(chp)+r''',internal=True); FluxBP('''+repr(flux)+r''',internal=True); gdb.execute('continue')
end
kill
quit
'''

def reference_values(libpath:Path,case:Path,m:dict):
    n=int(m['nlyr'])
    def f32arr(name,count):
        b=(case/name).read_bytes(); assert len(b)==4*count; return struct.unpack('<'+'f'*count,b)
    dt=f32arr('dtauc_f32le.bin',n); zd=f32arr('zd_f32le.bin',n+1); vn=f32arr('vn_f32le.bin',n+1); D=ctypes.c_double; I=ctypes.c_int; AD=D*n; AZ=D*(n+1); AI=I*n; AP=D*(n*n); a_dt=AD(*map(float,dt)); a_z=AZ(*map(float,zd)); a_v=AZ(*map(float,vn)); ni=I(n); um=D(float(m['umu0F32'])); rr=D(float(m['radiusKmF32'])); nf=AI(); nf2=AI(); fac=AP(); fac2=AP(); chp=AD(); ch=AD(); lib=ctypes.CDLL(str(libpath)); lib.direct_ref_full_(ctypes.byref(ni),a_dt,a_z,a_v,ctypes.byref(um),ctypes.byref(rr),nf,nf2,fac,fac2,chp,ch); return {'dtauc':list(map(float,dt)),'nfac':list(nf),'nfac2':list(nf2),'fac':list(fac),'fac2':list(fac2),'chp2':list(chp),'ch':list(ch)}
def unpack(case:Path,name,fmt,count):
    b=(case/name).read_bytes(); sz=struct.calcsize('<'+fmt)*count; assert len(b)==sz,(name,len(b),sz); return list(struct.unpack('<'+fmt*count,b))
def compare_case(case:Path,libpath:Path):
    m=json.load(open(case/'entry-metadata.json')); n=int(m['nlyr']); ref=reference_values(libpath,case,m); rn=unpack(case,'runtime-nfac-i32le.bin','i',n); rn2=unpack(case,'runtime-nfac2-i32le.bin','i',n); rf=unpack(case,'runtime-fac-f64le.bin','d',n*n); rf2=unpack(case,'runtime-fac2-f64le.bin','d',n*n); rchp=unpack(case,'runtime-chp2-f64le.bin','d',n); rch=unpack(case,'runtime-ch-f64le.bin','d',n); structural=(rn==ref['nfac'] and rn2==ref['nfac2']); facmax=max([0.0]+[abs(a-b) for a,b in zip(rf,ref['fac'])]+[abs(a-b) for a,b in zip(rf2,ref['fac2'])]); facok=all(ok_tol(a,b,1e-10) for a,b in zip(rf,ref['fac'])) and all(ok_tol(a,b,1e-10) for a,b in zip(rf2,ref['fac2'])); chpmax=max([0.0]+[abs(a-b) for a,b in zip(rchp,ref['chp2'])]); chp_ok=all(ok_tol(a,b,1e-10) for a,b in zip(rchp,ref['chp2'])); chmax=max([0.0]+[abs(a-b) for a,b in zip(rch,ref['ch'])]); ch_ok=all(ok_tol(a,b,1e-10) for a,b in zip(rch,ref['ch'])); pre=json.load(open(case/'pre-dpschekin.json')); post=json.load(open(case/'post-dpschekin.json')); flux=json.load(open(case/'dpsfluxes-entry.json')); rd=json.load(open(case/'runtime-rfldir-double.json')); serial=0.0
    for x in ref['dtauc']: serial += x
    ue=float(pre['utauPre']); expected_u=ue
    if abs(expected_u-serial)<=1e-4: expected_u=serial
    if serial>0 and abs((expected_u-serial)/serial)<=1e-6: expected_u=serial
    utau_exact=(f64bits(float(post['utauPost']))==f64bits(expected_u) and f64bits(float(post['taucNlyr']))==f64bits(serial) and f64bits(float(flux['utauFloat64']))==f64bits(expected_u)); ly=int(flux['layru1']); assert 1<=ly<=n; expected_att=0.0 if bool(flux['lyrcut']) and ly>int(flux['ncut']) else math.exp(-expected_u/ref['ch'][ly-1]); denom=abs(float(flux['umu0Float64']))*float(flux['fbeamFloat64']); runtime_att=float(rd['rfldirFloat64'])/denom if denom else 0.0; direct_ok=(runtime_att==0.0 and expected_att==0.0) or (runtime_att!=0.0 and expected_att!=0.0 and ok_tol(runtime_att,expected_att,1e-12)); out={'schemaVersion':1,'caseId':m['caseId'],'structuralExact':structural,'facFac2MaxAbsDelta':facmax,'facFac2Pass':facok,'chp2MaxAbsDelta':chpmax,'chp2Pass':chp_ok,'chMaxAbsDelta':chmax,'chPass':ch_ok,'utauEndpointPreprocessBitExact':utau_exact,'entryUtauFloat64':ue,'serialTaucNlyrFloat64':serial,'postDpschekinUtauFloat64':float(post['utauPost']),'layru':ly,'runtimeNormalizedDirectFloat64':runtime_att,'referenceDirectAttenuationFloat64':expected_att,'directPass':direct_ok,'directAbsDelta':abs(runtime_att-expected_att),'frozenFacChTolerance':1e-10,'frozenDirectTolerance':1e-12}; out['pass']=all((structural,facok,chp_ok,ch_ok,utau_exact,direct_ok)); write_json(case/'comparison.json',out); return out

def run_case(e:Path,row,uvspec:Path,data:Path,gdb:Path,symbols,libpath:Path):
    cid,role,*_=row; assert role=='development'; case=e/'cases'/cid; case.mkdir(parents=True,exist_ok=False); (case/'case-row.csv').write_text(','.join(row)+'\n',encoding='utf-8'); inp=build_input(data,row,case); sdis,chekin,chp,flux=symbols; gs=case/'capture.gdb'; gs.write_text(gdb_script(sdis,chekin,chp,flux),encoding='utf-8'); gridline=next(x for x in inp.read_text().splitlines() if x.startswith('atm_z_grid ')); nlyr=len(gridline.split())-2; env=os.environ.copy(); env['CASE_DIR']=str(case); env['CASE_ID']=cid; env['NLYR']=str(nlyr)
    with (case/'gdb.txt').open('w',encoding='utf-8') as gout: proc=subprocess.run([str(gdb),'-q','-batch','-ex',f'file {uvspec}','-ex',f'break {sdis}','-ex',f'run < {inp} > {case/"inferior.stdout"} 2> {case/"inferior.stderr"}','-x',str(gs)],env=env,stdout=gout,stderr=subprocess.STDOUT)
    (case/'gdb-exit-code.txt').write_text(str(proc.returncode)+'\n'); required=['entry-metadata.json','pre-dpschekin.json','post-dpschekin.json','second-chpman2-entry.json','runtime-chp2-f64le.bin','runtime-fac-f64le.bin','runtime-fac2-f64le.bin','runtime-nfac-i32le.bin','runtime-nfac2-i32le.bin','dpsfluxes-entry.json','runtime-ch-f64le.bin','runtime-rfldir-double.json','outer-final.json']
    if proc.returncode!=0 or any(not (case/x).exists() for x in required):
        missing=[x for x in required if not (case/x).exists()]; write_json(case/'mechanical-barrier.json',{'gdbExitCode':proc.returncode,'missing':missing,'solverResultMayHaveOpened':(case/'outer-final.json').exists(),'auditOpened':False}); return None
    mm=json.load(open(case/'entry-metadata.json')); assert mm['pcEqualsEntry'] and mm['ntau']==1 and mm['radiusKmF32']==6370.0 and mm['nrefrac']==0 and mm['ichap']==1 and mm['ndenssza']==0 and mm['newgeoI32']!=0 and mm['spherI32']!=0 and mm['planckI32']==0; return compare_case(case,libpath)
def manifest(e:Path):
    rows=[]
    for p in sorted(x for x in e.rglob('*') if x.is_file() and x.name!='evidence-manifest.sha256'): rows.append(f'{sha_file(p)}  {p.relative_to(e).as_posix()}')
    (e/'evidence-manifest.sha256').write_text('\n'.join(rows)+'\n')
def main():
    e=Path(os.environ['EVIDENCE_DIR']); e.mkdir(parents=True,exist_ok=True); (e/'cases').mkdir(exist_ok=True); freeze(e); uvspec,data,gdb,nm,fc=bind_runtime(e); fresh_fence(e); lib=prepare_reference(e,fc); syms=resolve_symbols(uvspec,nm,e); results=[]
    for row in CASE_ROWS:
        if row[1]!='development': continue
        x=run_case(e,row,uvspec,data,gdb,syms,lib)
        if x is None: write_json(e/'development-summary.json',{'classification':'STATE_0003_R19_MECHANICAL_CAPTURE_BARRIER','failedCase':row[0],'developmentResultsOpened':len(results),'auditOpened':False}); manifest(e); return 21
        results.append(x)
        if not x['pass']: write_json(e/'development-summary.json',{'classification':'STATE_0003_R19_FRESH_NONPROTECTED_RUNTIME_INTERNAL_DEVELOPMENT_NOT_PASS','failedCase':row[0],'developmentResultsOpened':len(results),'auditOpened':False,'results':results}); manifest(e); return 23
    write_json(e/'development-summary.json',{'classification':'STATE_0003_R19_FRESH_NONPROTECTED_RUNTIME_INTERNAL_DEVELOPMENT_PASS_8_OF_8','count':8,'auditOpened':False,'allPass':True,'maxFacFac2AbsDelta':max(x['facFac2MaxAbsDelta'] for x in results),'maxChp2AbsDelta':max(x['chp2MaxAbsDelta'] for x in results),'maxChAbsDelta':max(x['chMaxAbsDelta'] for x in results),'maxDirectAbsDelta':max(x['directAbsDelta'] for x in results),'allUtauEndpointPreprocessBitExact':all(x['utauEndpointPreprocessBitExact'] for x in results),'cases':[x['caseId'] for x in results]}); manifest(e); return 0
if __name__=='__main__':
    try: rc=main()
    except Exception as exc:
        e=Path(os.environ.get('EVIDENCE_DIR','/tmp/r19')); e.mkdir(parents=True,exist_ok=True); write_json(e/'fatal-barrier.json',{'classification':'STATE_0003_R19_EXECUTION_BARRIER','errorType':type(exc).__name__,'error':str(exc),'auditOpened':False}); manifest(e); raise
    raise SystemExit(rc)
