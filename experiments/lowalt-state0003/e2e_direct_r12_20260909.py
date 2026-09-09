#!/usr/bin/env python3
from __future__ import annotations
import csv, ctypes, gzip, hashlib, json, math, os, shutil, struct, subprocess, sys, tarfile, urllib.request, zipfile
from pathlib import Path

CASE_ROWS = [
    ('lowalt-e2e-r12-0001','development','0.88','89.12000000','509','0.25','OFF','0'),
    ('lowalt-e2e-r12-0002','development','1.72','88.28000000','737','1.75','DEFAULT','0'),
    ('lowalt-e2e-r12-0003','development','3.08','86.92000000','509','1.75','OFF','0'),
    ('lowalt-e2e-r12-0004','development','4.44','85.56000000','737','0.25','DEFAULT','0'),
    ('lowalt-e2e-r12-0005','development','1.26','88.74000000','509','0.25','DEFAULT','0'),
    ('lowalt-e2e-r12-0006','development','3.62','86.38000000','737','1.75','OFF','0'),
    ('lowalt-e2e-r12-0007','audit','0.96','89.04000000','737','0.25','OFF','0'),
    ('lowalt-e2e-r12-0008','audit','4.18','85.82000000','509','1.75','DEFAULT','0'),
]
HEADER=['case_id','split','target_geometric_altitude_deg','source_zenith_angle_deg','wavelength_nm','observer_elevation_km','aerosol','nsza_denstab']
MATRIX_SHA='bb5b3d129a9b8c72d644ec22810d1f4e7f8d6cef9fb0c432416ee9eb3abfc9c4'
FREEZE_SHA='6f72ab93534be6a96f41db9d8f31881d03191e8388c2568b96ecac96d84274d7'
UVSPEC_SHA='2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3'
PACKAGE_SPEC='rubin-libradtran=2.0.6=py312pl5321he9373c2_1'
SOURCE_ARTIFACT_ID=8894652347
SOURCE_OUTER_SHA='db189ee5f145719ebf85c97e1c0b35eacb4963c2c19544df29f0a978b1dbd12b'
WIRE_SHA='64930cc40b6e4a37aa220520974d330fc1563796f466a649b2238131f2d69840'
SOURCE_SHA='999e47f4af4b5df6f85a6887fc105fc8f6e1a7cee89a3124f69ac8d8912c8e85'
PREREG_COMMENT_ID=5603328244
CLOSURE_COMMENT_ID=5604240894
STARS_SHA='1e74d0522f086dba634a587bb245c32bcd4fac60'
AVPS_BRANCH='repair/avps-recovery4-canonical-write-quiet-parser-v1-20260909'

def sha_bytes(b:bytes)->str: return hashlib.sha256(b).hexdigest()
def sha_file(p:Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()
def write_json(p:Path,x): p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def run(cmd, *, cwd=None, env=None, stdout=None, stderr=None, check=True):
    return subprocess.run(cmd,cwd=cwd,env=env,stdout=stdout,stderr=stderr,text=isinstance(stdout,int) or stdout is subprocess.PIPE,check=check)
def api_get(url:str, token:str):
    req=urllib.request.Request(url,headers={'Accept':'application/vnd.github+json','Authorization':'Bearer '+token,'X-GitHub-Api-Version':'2022-11-28'})
    with urllib.request.urlopen(req,timeout=90) as r: return json.load(r)
def api_download(url:str, token:str, out:Path):
    req=urllib.request.Request(url,headers={'Accept':'application/vnd.github+json','Authorization':'Bearer '+token,'X-GitHub-Api-Version':'2022-11-28'})
    with urllib.request.urlopen(req,timeout=180) as r, out.open('wb') as f: shutil.copyfileobj(r,f,1024*1024)
def f32(x:float)->float: return struct.unpack('<f',struct.pack('<f',float(x)))[0]
def f32bits(x:float)->int: return struct.unpack('<I',struct.pack('<f',x))[0]

def freeze(e:Path):
    matrix=e/'matrix.csv'
    with matrix.open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f,lineterminator='\n'); w.writerow(HEADER); w.writerows(CASE_ROWS)
    assert sha_file(matrix)==MATRIX_SHA,(sha_file(matrix),MATRIX_SHA)
    obj={
      'schemaVersion':1,'classification':'STATE_0003_FRESH_NONPROTECTED_END_TO_END_DIRECT_GATE_R12_FREEZE',
      'caseCount':8,'developmentCount':6,'auditCount':2,'matrixSha256':MATRIX_SHA,
      'comparison':'solver_norm_f32=f32(rfldir_f32/(abs(umu0_f32)*fbeam_f32)); reference_norm_f32=f32(source_exact_direct_attenuation_double)',
      'acceptance':'finite nonzero <=1 binary32 ULP; exact zero equal; NaN/Inf fail',
      'openingOrder':'all 6 development PASS before either audit executes',
      'protectedGeographyUsed':False,'taylorOrJerusalemUsed':False,'protectedResidualUsedForSelection':False,
      'priorScienceIdentityReused':False,'seedOrOrdinalUsed':False,'retuningAfterResultAllowed':False,
      'productionMutationAuthorized':False,'fiveDegreeSeamMutationAuthorized':False,
      'sourceArtifactId':SOURCE_ARTIFACT_ID,'sourceArtifactOuterSha256':SOURCE_OUTER_SHA,
      'wireSourceSha256':WIRE_SHA,'governingDecodedSourceSha256':SOURCE_SHA,
      'exactPackage':PACKAGE_SPEC,'uvspecSha256':UVSPEC_SHA}
    p=e/'gate-freeze.json'; write_json(p,obj); assert sha_file(p)==FREEZE_SHA,(sha_file(p),FREEZE_SHA)

def bind_runtime(e:Path):
    uvspec=shutil.which('uvspec'); assert uvspec
    actual=sha_file(Path(uvspec)); assert actual==UVSPEC_SHA,(actual,UVSPEC_SHA)
    raw=subprocess.check_output(['micromamba','list','rubin-libradtran','--json'],text=True)
    (e/'micromamba-rubin-libradtran.json').write_text(raw,encoding='utf-8'); x=json.loads(raw); rows=[]
    def walk(v):
        if isinstance(v,dict):
            if v.get('name')=='rubin-libradtran': rows.append(v)
            for z in v.values(): walk(z)
        elif isinstance(v,list):
            for z in v: walk(z)
    walk(x); specs={f"rubin-libradtran={r.get('version')}={r.get('build_string',r.get('build'))}" for r in rows if r.get('version') and r.get('build_string',r.get('build'))}
    assert specs=={PACKAGE_SPEC},specs
    data=Path(os.environ['CONDA_PREFIX'])/'share/libRadtran/data'; assert (data/'atmmod/afglus.dat').is_file()
    gdb=shutil.which('gdb'); gf=shutil.which('gfortran'); nm=shutil.which('nm'); assert gdb and gf and nm
    (e/'runtime-binding.txt').write_text(f'uvspec={uvspec}\nuvspec_sha256={actual}\npackage_spec={PACKAGE_SPEC}\ndata_dir={data}\ngdb={gdb}\ngfortran={gf}\n',encoding='utf-8')
    (e/'gdb-version.txt').write_text(subprocess.check_output([gdb,'--version'],text=True),encoding='utf-8')
    (e/'gfortran-version.txt').write_text(subprocess.check_output([gf,'--version'],text=True),encoding='utf-8')
    return Path(uvspec),data,Path(gdb),Path(gf),Path(nm)

def fresh_fence(e:Path):
    gh=os.environ['GH_TOKEN']; st=os.environ['STARSVISIBILITY_READ_TOKEN']; base=os.environ['BASE_MAIN_SHA']; repo=os.environ['GITHUB_REPOSITORY']; runid=int(os.environ['GITHUB_RUN_ID'])
    subprocess.run(['git','fetch','-q','origin','main'],check=True)
    live=subprocess.check_output(['git','rev-parse','origin/main'],text=True).strip(); assert live==base,(live,base)
    issue=api_get(f'https://api.github.com/repos/{repo}/issues/60',gh); count=int(issue['comments'])
    latest=api_get(f'https://api.github.com/repos/{repo}/issues/60/comments?per_page=1&page={count}',gh); assert len(latest)==1
    prereg=api_get(f'https://api.github.com/repos/{repo}/issues/comments/{PREREG_COMMENT_ID}',gh)
    closure=api_get(f'https://api.github.com/repos/{repo}/issues/comments/{CLOSURE_COMMENT_ID}',gh)
    assert 'STATE_0003_FRESH_NONPROTECTED_END_TO_END_DIRECT_GATE_PREREGISTERED_NOT_EXECUTED' in prereg['body']
    assert 'STATE_0003_FORMAL_CLEAN_COMPILED_REFERENCE_AUDIT_PASS_12_OF_12' in closure['body']
    assert 'FORMAL_CLEAN_COMPILED_REFERENCE_AUDIT=PASS_12_OF_12' in closure['body'] or 'blocker CLOSED' in closure['body']
    stars=api_get('https://api.github.com/repos/search-maker/starsvisibility/branches/main',st); assert stars['commit']['sha']==STARS_SHA
    avps=api_get(f'https://api.github.com/repos/{repo}/branches/{AVPS_BRANCH}',gh)
    actions={}
    for status in ('in_progress','queued'):
        rs=api_get(f'https://api.github.com/repos/{repo}/actions/runs?status={status}&per_page=100',gh)['workflow_runs']
        actions[status]=[{'id':int(r['id']),'name':r.get('name'),'head_sha':r.get('head_sha'),'created_at':r.get('created_at')} for r in rs if int(r['id'])!=runid]
    write_json(e/'fresh-pre-solver-fence.json',{
      'schemaVersion':1,'issue60CommentCount':count,'issue60UpdatedAt':issue['updated_at'],'issue60LatestCommentId':int(latest[0]['id']),
      'issue60LatestCreatedAt':latest[0]['created_at'],'preregCommentId':PREREG_COMMENT_ID,'blockerClosureCommentId':CLOSURE_COMMENT_ID,
      'twilightMain':live,'starsMain':stars['commit']['sha'],'liveAvpsBranch':AVPS_BRANCH,'liveAvpsHead':avps['commit']['sha'],
      'otherActions':actions,'concurrencyPolicy':'active V1 run alone is nonblocking; no idle-only assertion',
      'protectedScienceOpened':False,'taylorOrJerusalemUsed':False,'fiveDegreeSeamChanged':False,'solverGateMayProceed':True})

def acquire_source(e:Path, gf:Path):
    gh=os.environ['GH_TOKEN']; repo=os.environ['GITHUB_REPOSITORY']; s=e/'source'; s.mkdir(exist_ok=True)
    meta=api_get(f'https://api.github.com/repos/{repo}/actions/artifacts/{SOURCE_ARTIFACT_ID}',gh); write_json(s/'artifact-metadata.json',meta)
    assert int(meta['id'])==SOURCE_ARTIFACT_ID and not meta['expired'] and meta.get('digest')=='sha256:'+SOURCE_OUTER_SHA
    z=s/'source-artifact.zip'; api_download(f'https://api.github.com/repos/{repo}/actions/artifacts/{SOURCE_ARTIFACT_ID}/zip',gh,z); assert sha_file(z)==SOURCE_OUTER_SHA
    with zipfile.ZipFile(z) as q: wire=q.read('libRadtran-2.0.6.tar.gz')
    assert len(wire)==154147176 and sha_bytes(wire)==WIRE_SHA; (s/'libRadtran-2.0.6.tar.gz').write_bytes(wire)
    decoded=gzip.decompress(wire); assert len(decoded)==284387328 and sha_bytes(decoded)==SOURCE_SHA; tarpath=s/'libRadtran-2.0.6.tar'; tarpath.write_bytes(decoded)
    names=['libRadtran-2.0.6/libsrc_f/dpmisc.f','libRadtran-2.0.6/libsrc_f/DISORT.MXD']
    with tarfile.open(tarpath,'r:') as t:
        for name in names:
            member=t.getmember(name); out=s/Path(name).name
            with t.extractfile(member) as src, out.open('wb') as dst: shutil.copyfileobj(src,dst)
    lines=(s/'dpmisc.f').read_text(encoding='utf-8',errors='strict').splitlines(keepends=True)
    exact=''.join(lines[935:1740]+lines[3254:3325]); (s/'geofast_exact.f').write_text(exact,encoding='utf-8')
    wrapper="""      subroutine direct_ref(nlyr,dtauc,ssalb,utau,zd,vn,umu0,
     $     radius,expected,chout,chpout,layru,lyrcut,ncut)
      include 'DISORT.MXD'
      integer nlyr, layru, lyrcut, ncut, mxcly_arg
      integer nfac(1:mxcly), nfac2(1:mxcly), brosza
      real*8 dtauc(*), ssalb(*), zd(0:*), vn(0:*), utau
      real*8 umu0, radius, expected, chout, chpout
      real*8 fac(1:mxcly,1:mxcly), fac2(1:mxcly,1:mxcly)
      real*8 szaloc(1:mxcly,0:mxcly), szaloc2(1:mxcly,0:mxcly)
      real*8 sza_bro(mxsza), chp(1:mxcly)
      real*8 zenang,z_lay,rearth,pi,tauc(0:mxcly),abstau,taup
      integer lc
      pi=dacos(-1.d0)
      zenang=dacos(umu0)*180.d0/pi
      z_lay=0.5d0
      rearth=radius
      brosza=0
      do lc=1,mxsza
        sza_bro(lc)=0.d0
      enddo
      call geofast(brosza,sza_bro,fac,nfac,szaloc,
     $     fac2,nfac2,szaloc2,z_lay,nlyr,zd,zenang,rearth,vn)
      mxcly_arg=mxcly
      call chpman2(nlyr,zenang,dtauc,nfac,fac,nfac2,fac2,
     $     chp,mxcly_arg)
      tauc(0)=0.d0
      abstau=0.d0
      ncut=0
      do lc=1,nlyr
        if (abstau.lt.400.d0) ncut=lc
        abstau=abstau+(1.d0-ssalb(lc))*dtauc(lc)
        tauc(lc)=tauc(lc-1)+dtauc(lc)
      enddo
      lyrcut=0
      if (abstau.ge.400.d0 .and. nlyr.gt.1) lyrcut=1
      if (lyrcut.eq.0) ncut=nlyr
      layru=nlyr
      do lc=1,nlyr
        if (utau.ge.tauc(lc-1) .and. utau.le.tauc(lc)) then
          layru=lc
          goto 80
        endif
      enddo
 80   continue
      if (lyrcut.ne.0 .and. layru.gt.ncut) then
        expected=0.d0
        chout=0.d0
        chpout=chp(layru)
        return
      endif
      taup=tauc(layru-1)+dtauc(layru)/2.d0
      chout=taup/chp(layru)
      chpout=chp(layru)
      expected=dexp(-utau/chout)
      return
      end
"""
    (s/'direct_ref_wrapper.f').write_text(wrapper,encoding='utf-8')
    lib=s/'libdirect_ref.so'; subprocess.run([str(gf),'-O2','-fPIC','-ffixed-line-length-none','-shared','geofast_exact.f','direct_ref_wrapper.f','-o',lib.name],cwd=s,check=True)
    syms=subprocess.check_output(['nm','-g',lib],text=True); (s/'reference-symbols.txt').write_text(syms,encoding='utf-8')
    for sym in ('geofast_','chpman2_','direct_ref_'): assert sym in syms
    write_json(s/'source-binding.json',{'schemaVersion':1,'sourceArtifactId':SOURCE_ARTIFACT_ID,'outerSha256':sha_file(z),'wireBytes':len(wire),'wireSha256':sha_bytes(wire),'decodedBytes':len(decoded),'decodedSha256':sha_bytes(decoded),'referenceLibrarySha256':sha_file(lib),'sourceSliceSha256':sha_file(s/'geofast_exact.f')})
    return lib

def resolve_symbol(uvspec:Path,nm:Path,e:Path):
    txt=subprocess.check_output([str(nm),'-an',str(uvspec)],text=True,errors='replace'); (e/'nm-all.txt').write_text(txt,encoding='utf-8')
    found=sorted({p[-1] for line in txt.splitlines() if len((p:=line.split()))>=3 and p[-1] in {'sdisort','sdisort_'} and p[-2] in {'T','t'}})
    assert len(found)==1,found; (e/'resolved-sdisort-symbol.txt').write_text(found[0]+'\n',encoding='utf-8'); return found[0]

def build_input(data:Path,row,case:Path):
    cid,split,alt,sza,wl,site,aer,nsza=row; atm=data/'atmmod/afglus.dat'; sitef=float(site)
    levels=[]
    for raw in atm.read_text(encoding='utf-8').splitlines():
        q=raw.strip()
        if q and not q.startswith('#'): levels.append(float(q.split()[0]))
    assert len(levels)>2 and all(levels[i]>levels[i+1] for i in range(len(levels)-1))
    grid=[sitef,*sorted(z for z in levels if z>sitef)]; assert all(grid[i]<grid[i+1] for i in range(len(grid)-1))
    lines=[f'data_files_path {atm.parent.parent}',f'atmosphere_file {atm}','source solar','mol_abs_param crs',f'wavelength {int(wl)} {int(wl)}',f'sza {float(sza):.8f}','atm_z_grid '+' '.join(f'{z:.6f}' for z in grid),'zout 0.000000','albedo 0.15000000','rte_solver sdisort','sdisort nscat 1','output_quantity transmittance','output_user lambda edir','quiet']
    if aer=='DEFAULT': lines.insert(4,'aerosol_default')
    else: assert aer=='OFF'
    text='\n'.join(lines)+'\n'; low=text.lower()
    for token in ('rte_solver mystic','aerosol_set_tau','nrefrac','refraction','altitude '): assert token not in low,token
    p=case/'input.inp'; p.write_text(text,encoding='utf-8'); (case/'input.sha256').write_text(sha_file(p)+'  input.inp\n',encoding='utf-8'); return p

def gdb_script()->str:
    return r'''set pagination off
set confirm off
python
import gdb,os,struct,hashlib,json
from pathlib import Path
d=Path(os.environ['CASE_DIR']); sym=os.environ['SDISORT_SYMBOL']; inf=gdb.selected_inferior(); pc=int(gdb.parse_and_eval('$pc')); rsp=int(gdb.parse_and_eval('$rsp')); rdi=int(gdb.parse_and_eval('$rdi')); rsi=int(gdb.parse_and_eval('$rsi')); rdx=int(gdb.parse_and_eval('$rdx')); entry=int(gdb.parse_and_eval('&'+sym))
def mem(a,n): return bytes(inf.read_memory(a,n))
def ptr(off): return struct.unpack('<Q',mem(rsp+off,8))[0]
def i32(a): return struct.unpack('<i',mem(a,4))[0]
def f32(a): return struct.unpack('<f',mem(a,4))[0]
nlyr=i32(rdi); ntau=i32(ptr(24))
if not (0<nlyr<=128 and ntau==1): raise RuntimeError((nlyr,ntau))
p={'utau':ptr(32),'fbeam':ptr(88),'umu0':ptr(112),'newgeo':ptr(128),'zd':ptr(136),'spher':ptr(144),'radius':ptr(152),'planck':ptr(208),'rfldir':ptr(304),'nrefrac':ptr(392),'ichap':ptr(400),'vn':ptr(408),'ndenssza':ptr(416)}
blobs={'dtauc_f32le.bin':mem(rsi,nlyr*4),'ssalb_f32le.bin':mem(rdx,nlyr*4),'utau_f32le.bin':mem(p['utau'],4),'zd_f32le.bin':mem(p['zd'],(nlyr+1)*4),'vn_f32le.bin':mem(p['vn'],(nlyr+1)*4)}
hashes={}
for name,data in blobs.items(): (d/name).write_bytes(data); hashes[name]=hashlib.sha256(data).hexdigest()
meta={'schemaVersion':1,'caseId':os.environ['CASE_ID'],'pcEqualsEntry':pc==entry,'resolvedEntrySymbol':sym,'nlyr':nlyr,'ntau':ntau,'fbeam':f32(p['fbeam']),'umu0':f32(p['umu0']),'radiusKm':f32(p['radius']),'newgeoRawI32':i32(p['newgeo']),'spherRawI32':i32(p['spher']),'planckRawI32':i32(p['planck']),'nrefrac':i32(p['nrefrac']),'ichap':i32(p['ichap']),'ndenssza':i32(p['ndenssza']),'rawArraySha256':hashes,'solverResultOpenedAtEntry':False,'protectedResultOpened':False}
(d/'entry-metadata.json').write_text(json.dumps(meta,indent=2,sort_keys=True)+'\n')
gdb.set_convenience_variable('saved_rfldir_ptr',gdb.Value(p['rfldir']))
end
finish
python
import gdb,os,struct,hashlib,json
from pathlib import Path
d=Path(os.environ['CASE_DIR']); inf=gdb.selected_inferior(); a=int(gdb.parse_and_eval('$saved_rfldir_ptr')); raw=bytes(inf.read_memory(a,4)); (d/'final-rfldir-f32le.bin').write_bytes(raw)
out={'schemaVersion':1,'caseId':os.environ['CASE_ID'],'rfldirF32':struct.unpack('<f',raw)[0],'rfldirRawHex':raw.hex(),'rfldirRawSha256':hashlib.sha256(raw).hexdigest(),'solverWrapperReturned':True,'solverBodyExecuted':True,'protectedResultOpened':False}
(d/'solver-direct-result.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
end
kill
quit
'''

def compare_case(case:Path,libpath:Path):
    lib=ctypes.CDLL(str(libpath)); m=json.load(open(case/'entry-metadata.json')); sol=json.load(open(case/'solver-direct-result.json')); n=int(m['nlyr'])
    def vals(name,count):
        b=(case/name).read_bytes(); assert len(b)==4*count; return struct.unpack('<'+'f'*count,b)
    dt=vals('dtauc_f32le.bin',n); ss=vals('ssalb_f32le.bin',n); ut=vals('utau_f32le.bin',1)[0]; zd=vals('zd_f32le.bin',n+1); vn=vals('vn_f32le.bin',n+1)
    A=ctypes.c_double*n; AZ=ctypes.c_double*(n+1); a_dt=A(*map(float,dt)); a_ss=A(*map(float,ss)); a_z=AZ(*map(float,zd)); a_v=AZ(*map(float,vn))
    ni=ctypes.c_int(n); c_ut=ctypes.c_double(float(ut)); c_umu=ctypes.c_double(float(m['umu0'])); c_r=ctypes.c_double(float(m['radiusKm'])); exp=ctypes.c_double(); ch=ctypes.c_double(); chp=ctypes.c_double(); lay=ctypes.c_int(); ly=ctypes.c_int(); nc=ctypes.c_int()
    lib.direct_ref_(ctypes.byref(ni),a_dt,a_ss,ctypes.byref(c_ut),a_z,a_v,ctypes.byref(c_umu),ctypes.byref(c_r),ctypes.byref(exp),ctypes.byref(ch),ctypes.byref(chp),ctypes.byref(lay),ctypes.byref(ly),ctypes.byref(nc))
    rf=float(sol['rfldirF32']); beam=float(m['fbeam']); umu=float(m['umu0']); assert all(math.isfinite(x) for x in (rf,beam,umu,exp.value,ch.value,chp.value)) and beam>0 and umu!=0
    solver_norm=f32(rf/(abs(umu)*beam)); ref_norm=f32(exp.value)
    if solver_norm==0.0 or ref_norm==0.0: ulp=0 if solver_norm==0.0 and ref_norm==0.0 else 2**32-1; ok=(ulp==0)
    else: assert solver_norm>0 and ref_norm>0; ulp=abs(f32bits(solver_norm)-f32bits(ref_norm)); ok=ulp<=1
    out={'schemaVersion':1,'caseId':m['caseId'],'solverRfldirF32':rf,'fbeamF32':beam,'umu0F32':umu,'utauF32':float(ut),'referenceAttenuationFloat64':exp.value,'referenceChFloat64':ch.value,'referenceChp2Float64':chp.value,'referenceLayru':lay.value,'referenceLyrcut':ly.value,'referenceNcut':nc.value,'solverNormalizedF32':solver_norm,'referenceNormalizedF32':ref_norm,'solverNormalizedBits':f32bits(solver_norm),'referenceNormalizedBits':f32bits(ref_norm),'ulpDistance':ulp,'acceptanceUlps':1,'exactZeroSemantics':True,'pass':ok,'protectedResultOpened':False,'taylorOrJerusalemUsed':False}
    write_json(case/'comparison.json',out); return out

def run_case(e:Path,row,uvspec:Path,data:Path,gdb:Path,symbol:str,lib:Path,gdbfile:Path):
    cid,split,*_=row; case=e/'cases'/cid; case.mkdir(parents=True,exist_ok=True); (case/'case-row.csv').write_text(','.join(row)+'\n',encoding='utf-8'); inp=build_input(data,row,case)
    env=os.environ.copy(); env['CASE_DIR']=str(case); env['CASE_ID']=cid; env['SDISORT_SYMBOL']=symbol
    with (case/'gdb.txt').open('w',encoding='utf-8') as gout:
        proc=subprocess.run([str(gdb),'-q','-batch','-ex',f'file {uvspec}','-ex',f'break {symbol}','-ex',f'run < {inp} > {case/"inferior.stdout"} 2> {case/"inferior.stderr"}','-x',str(gdbfile)],env=env,stdout=gout,stderr=subprocess.STDOUT)
    (case/'gdb-exit-code.txt').write_text(str(proc.returncode)+'\n',encoding='utf-8'); assert proc.returncode==0
    assert (case/'inferior.stdout').stat().st_size==0 and (case/'inferior.stderr').stat().st_size==0
    m=json.load(open(case/'entry-metadata.json')); assert m['pcEqualsEntry'] and m['ntau']==1 and m['radiusKm']==6370.0 and m['nrefrac']==0 and m['ichap']==1 and m['ndenssza']==0 and m['newgeoRawI32']!=0 and m['spherRawI32']!=0 and m['planckRawI32']==0 and m['fbeam']>0
    return compare_case(case,lib)

def manifest(e:Path):
    lines=[]
    for p in sorted(x for x in e.rglob('*') if x.is_file() and x.name!='evidence-manifest.sha256'): lines.append(f'{sha_file(p)}  {p.relative_to(e).as_posix()}')
    (e/'evidence-manifest.sha256').write_text('\n'.join(lines)+'\n',encoding='utf-8')

def main():
    e=Path(os.environ['EVIDENCE_DIR']); e.mkdir(parents=True,exist_ok=True); (e/'cases').mkdir(exist_ok=True); (e/'source').mkdir(exist_ok=True)
    freeze(e); uvspec,data,gdb,gf,nm=bind_runtime(e); fresh_fence(e); lib=acquire_source(e,gf); symbol=resolve_symbol(uvspec,nm,e)
    gdbfile=e/'e2e_capture.gdb'; gdbfile.write_text(gdb_script(),encoding='utf-8')
    results=[]
    for row in CASE_ROWS:
        if row[1]=='development':
            x=run_case(e,row,uvspec,data,gdb,symbol,lib,gdbfile); results.append((row,x));
            if not x['pass']:
                write_json(e/'development-summary.json',{'schemaVersion':1,'classification':'STATE_0003_E2E_DIRECT_R12_DEVELOPMENT_NOT_PASS','failedCase':row[0],'auditOpened':False,'results':[y for _,y in results]}); manifest(e); return 23
    dev=[x for r,x in results]; write_json(e/'development-summary.json',{'schemaVersion':1,'classification':'STATE_0003_E2E_DIRECT_R12_DEVELOPMENT_PASS_6_OF_6','count':6,'maxUlpDistance':max(x['ulpDistance'] for x in dev),'allPass':True,'auditStillUnopened':True,'cases':[x['caseId'] for x in dev]})
    for row in CASE_ROWS:
        if row[1]=='audit':
            x=run_case(e,row,uvspec,data,gdb,symbol,lib,gdbfile); results.append((row,x));
            if not x['pass']:
                write_json(e/'final-summary.json',{'schemaVersion':1,'classification':'STATE_0003_FRESH_NONPROTECTED_END_TO_END_DIRECT_GATE_R12_NOT_PASS','failedCase':row[0],'developmentPass':6,'auditOpened':True,'results':[y for _,y in results]}); manifest(e); return 24
    dev=[x for r,x in results if r[1]=='development']; audit=[x for r,x in results if r[1]=='audit']
    summary={'schemaVersion':1,'classification':'STATE_0003_FRESH_NONPROTECTED_END_TO_END_DIRECT_GATE_R12_PASS','matrixSha256':MATRIX_SHA,'gateFreezeSha256':FREEZE_SHA,'developmentPass':len(dev),'auditPass':len(audit),'totalPass':len(results),'maxUlpDistance':max(x['ulpDistance'] for _,x in results),'sourceArtifactId':SOURCE_ARTIFACT_ID,'governingSourceSha256':SOURCE_SHA,'uvspecSha256':UVSPEC_SHA,'protectedResultsOpened':0,'taylorOrJerusalemUsed':False,'protectedGeographyUsed':False,'seedOrOrdinalUsed':False,'productionChanged':False,'v1FiveDegreeSeamChanged':False,'cases':[{'caseId':x['caseId'],'split':r[1],'ulpDistance':x['ulpDistance'],'solverNormalizedF32':x['solverNormalizedF32'],'referenceNormalizedF32':x['referenceNormalizedF32']} for r,x in results]}
    write_json(e/'final-summary.json',summary); manifest(e); print(json.dumps({k:v for k,v in summary.items() if k!='cases'},sort_keys=True)); return 0

if __name__=='__main__':
    try: rc=main()
    except Exception as exc:
        e=Path(os.environ.get('EVIDENCE_DIR','/tmp/lowalt_e2e_r12')); e.mkdir(parents=True,exist_ok=True); write_json(e/'fatal-barrier.json',{'schemaVersion':1,'classification':'STATE_0003_E2E_DIRECT_R12_EXECUTION_BARRIER','errorType':type(exc).__name__,'error':str(exc),'auditMayHaveOpened':any((e/'cases'/r[0]/'comparison.json').exists() for r in CASE_ROWS if r[1]=='audit')}); manifest(e); raise
    raise SystemExit(rc)
