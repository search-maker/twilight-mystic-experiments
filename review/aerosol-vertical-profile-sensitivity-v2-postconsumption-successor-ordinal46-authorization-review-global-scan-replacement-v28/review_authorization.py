from __future__ import annotations
import ast,base64,copy,hashlib,json,os,re,sys,zlib
from pathlib import Path

MAIN='6cd7c075766fe0c86bc7561ec205a3f9120fd1fb'; OLD='f5ebc646aba96ad13753d55baf2b0c55cff64ccb'; V4='a3fc752af64599eed1dc5e358a23295e423b1eb8'
V5='0d7ad7030aacc1c34bca93fef6c02fd7dcf776c2'; V5BR='review/avps-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v5-20260910'
P25='e99dcdbb408db224f13411cf3fa2ba205a36fe3d768ca8176538d10ea08a86a8'; C25='9a2f6b5639c91ca89082ff92b0e0b0cb5b649e75f2dab16917bf4b2627283f2a'; P17='3cb6ad6603d53440cfc159d96da5b262c9441102ffca7db3ce7443c22b32f643'
B={'V26':'3fb03fb408897464b1be3ebd67b67b6297235cbd','V25':'0d5fae5c74eb6ab2e9afccb75559e91b5870fa5c','V24':'e4d306e01f76cc4199364bcd9d6d1a1dbffabf52','V23':'52dd4af0f78e7d8418669d98562a77584bc7ab31','V22':'98fe1ca468a44ad385005111f38dc48c89a08b9e','V17':'06867e14710f15cade77ed24fbdc33dafb9f2f74'}
HERE=Path(__file__).resolve(); FAIL='FAIL_V28_PREACTUAL_DISTRIBUTED_STATIC_DATAFLOW_OR_DOWNSTREAM'

def arg(k):
    try:i=sys.argv.index(k);return sys.argv[i+1]
    except (ValueError,IndexError):return None
def sha(x):return hashlib.sha256(x).hexdigest()
def blob(x):return hashlib.sha1(b'blob '+str(len(x)).encode()+b'\0'+x).hexdigest()
def bound(k):
    p=os.environ.get(k+'_FROZEN_REVIEWER',''); x=Path(p).read_bytes() if p else b''
    if blob(x)!=B[k]:raise RuntimeError(f'V28 {k} blob drift: {blob(x)}')
    return x
def write(path,p):
    if not path:return
    q=dict(p); raw=json.dumps(q,sort_keys=True,separators=(',',':')).encode(); q['receiptSha256']=sha(raw); Path(path).parent.mkdir(parents=True,exist_ok=True); Path(path).write_text(json.dumps(q,sort_keys=True,indent=2)+'\n')
def failure(e):
    d=os.environ.get('V28_PREACTUAL_FAILURE_DIR')
    if os.environ.get('V28_PREACTUAL_ACTIVE')!='1' or not d:return
    p=Path(d)/'failure.json'
    if p.exists():return
    write(str(p),{'status':FAIL,'type':type(e).__name__,'message':str(e),'authorizationRefCreated':False,'dispatchCreated':False,'scientificOrdinalAllocated':False,'scientificOrdinalReserved':False,'scientificOrdinalDispatched':False,'seedUniverseConsumed':False,'scienceInvoked':False,'solverExecuted':False,'protectedResultsOpened':False,'publisherInvoked':False,'newMappingOpened':False,'productionInvoked':False,'scienceFalse':True})
def fn(t,n):
    q=[x for x in t.body if isinstance(x,(ast.FunctionDef,ast.AsyncFunctionDef)) and x.name==n]
    if len(q)!=1:raise RuntimeError(f'V28 {n} count drift: {len(q)}')
    return q[0]
def seg(s,n):
    q=ast.get_source_segment(s,n)
    if not isinstance(q,str):raise RuntimeError('V28 source segment unavailable')
    return q
def isget(n,name,key,argc=None):
    return isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id==name and n.func.attr=='get' and not n.keywords and bool(n.args) and isinstance(n.args[0],ast.Constant) and n.args[0].value==key and (argc is None or len(n.args)==argc)
def eq(n):
    return (n.left,n.comparators[0]) if isinstance(n,ast.Compare) and len(n.ops)==1 and isinstance(n.ops[0],ast.Eq) and len(n.comparators)==1 else None

def payload25(x):
    t=x.decode(); m=re.findall(r'^PAYLOAD_SHA256 = [\'\"]([0-9a-f]{64})[\'\"]$',t,re.M); q=re.findall(r'^PAYLOAD_B85 = r"""(.*?)"""$',t,re.M|re.S)
    if m!=[P25] or len(q)!=1:raise RuntimeError('V28 frozen V25 launcher binding drift')
    lines=q[0].split('\n'); refusal=''
    if len(lines)!=161 or len(lines[0])!=72 or any(not z for z in lines):raise RuntimeError('V28 V25 Base85 physical drift')
    try:base64.b85decode(q[0].encode())
    except ValueError as e:refusal=str(e)
    if refusal!='bad base85 character at position 72':raise RuntimeError('V28 V25 multiline refusal drift')
    enc=''.join(lines); comp=base64.b85decode(enc.encode()); raw=zlib.decompress(comp)
    if sha(comp)!=C25 or base64.b85encode(comp).decode()!=enc or sha(raw)!=P25:raise RuntimeError('V28 V26 canonical transport drift')
    ast.parse(raw.decode())
    return {'status':'PASS_V26_PREACTUAL_BASE85_CANONICAL_TRANSPORT','physicalLineCount':161,'firstPhysicalLineLength':72,'canonicalCompressedSha256':C25,'decompressedSha256':P25,'directMultilineDecodeRefusal':refusal,'serializerRoundTripExact':True}
def payload17(x):
    t=x.decode(); q=re.findall(r'^PAYLOAD_B85 = r"""(.*?)"""\.replace\(\'\\n\', \'\'\)$',t,re.M|re.S); m=re.findall(r"^PAYLOAD_SHA256 = '([0-9a-f]{64})'$",t,re.M)
    if len(q)!=1 or m!=[P17]:raise RuntimeError('V28 V17 launcher binding drift')
    raw=zlib.decompress(base64.b85decode(q[0].replace('\n','').encode()))
    if sha(raw)!=P17:raise RuntimeError('V28 V17 payload drift')
    ast.parse(raw.decode());return raw

def meta4(m):
    h=m.get('head') or {}; b=m.get('base') or {}
    if int(m.get('number') or 0)!=1032 or m.get('state')!='open' or m.get('draft') is not True or m.get('merged_at') is not None or h.get('sha')!=V4 or b.get('ref')!='main' or b.get('sha')!=OLD or b.get('sha')==MAIN:raise RuntimeError('V28 frozen V4 metadata drift')
def fixtures4(m):
    meta4(m); out={'exactFrozenV4MetadataPasses':True}
    def bad(label,mut):
        x=copy.deepcopy(m);mut(x)
        try:meta4(x)
        except RuntimeError:out[label]=True;return
        raise RuntimeError('V28 negative V4 fixture passed '+label)
    bad('wrongHistoricalBaseFatal',lambda x:x['base'].__setitem__('sha','0'*40));bad('wrongHeadFatal',lambda x:x['head'].__setitem__('sha','0'*40));bad('wrongBaseRefFatal',lambda x:x['base'].__setitem__('ref','wrong'));bad('wrongStateFatal',lambda x:x.__setitem__('state','closed'));bad('mergedFatal',lambda x:x.__setitem__('merged_at','x'));bad('currentMainLeakageFatal',lambda x:x['base'].__setitem__('sha',MAIN));return out

def distributed(src):
    t=ast.parse(src); ins,rep,ass,bld=[fn(t,n) for n in ('_insert_v4_expected_base','_repair_base_comparator','_assert_v4_historical_source_binding','_build_v17_effective_source')]
    ss={n:seg(src,f) for n,f in [('insert',ins),('repair',rep),('assert',ass),('builder',bld)]}
    if ss['insert'].count(OLD)!=1 or 'expectedBaseSha' not in ss['insert']:raise RuntimeError('V28 V17 insert provenance drift')
    branches=[]
    for n in ast.walk(rep):
        if not isinstance(n,ast.If):continue
        s=eq(n.test)
        if s and ((isget(s[0],'spec','version',1) and isinstance(s[1],ast.Constant) and s[1].value=='v4') or (isget(s[1],'spec','version',1) and isinstance(s[0],ast.Constant) and s[0].value=='v4')):branches.append(n)
    if len(branches)!=1:raise RuntimeError(f'V28 V17 version-v4 branch count drift: {len(branches)}')
    br=branches[0]; body=[]; els=[]
    for n in ast.walk(ast.Module(body=br.body,type_ignores=[])):
        if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and isget(n.value,'spec','expectedBaseSha',1):body.append(n.targets[0].id)
    for n in ast.walk(ast.Module(body=br.orelse,type_ignores=[])):
        if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and isinstance(n.value,ast.Name) and n.value.id=='MAIN':els.append(n.targets[0].id)
    loc=sorted(set(body)&set(els))
    if len(loc)!=1:raise RuntimeError(f'V28 V17 expected-base local ambiguity: {loc!r}')
    cm=[]
    for n in ast.walk(rep):
        s=eq(n)
        if not s:continue
        if (isget(s[0],'pbase','sha',1) and isinstance(s[1],ast.Name) and s[1].id==loc[0]) or (isget(s[1],'pbase','sha',1) and isinstance(s[0],ast.Name) and s[0].id==loc[0]):cm.append(n)
    if len(cm)!=1:raise RuntimeError(f'V28 V17 pbase comparator count drift: {len(cm)}')
    if sum(isinstance(n,ast.Constant) and n.value==OLD for n in ast.walk(ass))!=1 or not any(isinstance(n,ast.Constant) and n.value=='expectedBaseSha' for n in ast.walk(ass)):raise RuntimeError('V28 V17 immutable assertion provenance drift')
    calls=[(n.func.id,n.lineno) for n in ast.walk(bld) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id in {'_insert_v4_expected_base','_repair_base_comparator','_assert_v4_historical_source_binding'}]
    if sorted(x[0] for x in calls)!=['_assert_v4_historical_source_binding','_insert_v4_expected_base','_repair_base_comparator']:raise RuntimeError(f'V28 V17 builder call-chain drift: {calls!r}')
    side=[]
    for f in (ins,rep,ass):
        for n in ast.walk(f):
            if isinstance(n,ast.Call) and ((isinstance(n.func,ast.Name) and n.func.id in {'exec','eval','open','__import__'}) or (isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id in {'subprocess','os','requests','urllib','socket'})):side.append(n.lineno)
    if side:raise RuntimeError(f'V28 static forensic candidate side effects: {side!r}')
    rec=fn(t,'_recover_exact_v12_effective_source'); old=[]
    for n in ast.walk(rec):
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='exec':old.append(f'{n.lineno}:exec')
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=='subprocess':old.append(f'{n.lineno}:subprocess.{n.func.attr}')
    if not any(x.endswith(':exec') for x in old) or not any('subprocess.run' in x for x in old):raise RuntimeError('V28 old direct-probe negative fixture drift')
    return {'status':'PASS_V28_PREACTUAL_DISTRIBUTED_STATIC_V4_DATAFLOW','localExpectedBaseName':loc[0],'insertLine':ins.lineno,'repairLine':rep.lineno,'assertLine':ass.lineno,'builderLine':bld.lineno,'insertSha256':sha(ss['insert'].encode()),'repairSha256':sha(ss['repair'].encode()),'assertSha256':sha(ss['assert'].encode()),'builderSha256':sha(ss['builder'].encode()),'builderCalls':calls,'oldDirectProbeReachableSideEffects':old,'proofCandidateSideEffectFree':True}

def candidate_count(src):
    t=ast.parse(src); total=0
    for f in [n for n in t.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]:
        for br in [n for n in ast.walk(f) if isinstance(n,ast.If)]:
            q=eq(br.test)
            if not q or not ((isget(q[0],'spec','version',1) and isinstance(q[1],ast.Constant) and q[1].value=='v4') or (isget(q[1],'spec','version',1) and isinstance(q[0],ast.Constant) and q[0].value=='v4')):continue
            body=[]; els=[]
            for n in ast.walk(ast.Module(body=br.body,type_ignores=[])):
                if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and isget(n.value,'spec','expectedBaseSha',1):body.append(n.targets[0].id)
            for n in ast.walk(ast.Module(body=br.orelse,type_ignores=[])):
                if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and isinstance(n.value,ast.Name) and n.value.id=='MAIN':els.append(n.targets[0].id)
            for local in set(body)&set(els):
                comps=0
                for n in ast.walk(f):
                    z=eq(n)
                    if z and ((isget(z[0],'pbase','sha',1) and isinstance(z[1],ast.Name) and z[1].id==local) or (isget(z[1],'pbase','sha',1) and isinstance(z[0],ast.Name) and z[0].id==local)):comps+=1
                if comps==1:total+=1
    return total
def semantic_fixtures():
    s="""def f(spec,pbase):\n if spec.get('version') == 'v4':\n  x=spec.get('expectedBaseSha')\n else:\n  x=MAIN\n return pbase.get('sha') == x\n"""
    zero=s.replace("x=spec.get('expectedBaseSha')","x=MAIN",1); multi=s+s.replace('def f(','def g(',1); comments='# '+s.replace('\n','\n# ')
    if candidate_count(s)!=1 or candidate_count(zero)!=0 or candidate_count(multi)!=2 or candidate_count(comments)!=0:raise RuntimeError('V28 semantic fixture drift')
    return {'exactDistributedShapePositive':True,'zeroSemanticCandidateFatal':True,'multipleSemanticCandidatesFatal':True,'commentsTemplatesNoiseCannotSatisfy':True,'oldJointTokenRequirementRejected':True}

def lift(raw,ou,nu,ol,nl,name):
    if blob(raw)!=B[name]:raise RuntimeError('V28 lift blob drift '+name)
    s=raw.decode(); q=s.replace(ou,nu).replace(ol,nl)
    if q==s:raise RuntimeError('V28 lift produced no change '+name)
    compile(q,'<v28-lift-'+name+'>','exec'); scope={'__file__':str(HERE),'__name__':'_v28_lift_'+name.lower()+'_'};exec(compile(q,'<v28-lift-'+name+'>','exec'),scope,scope);return scope,q.encode()
def patch_v5_block(original):
    def wrapped(indent):
        raw=original(indent)
        if not isinstance(raw,bytes):raise RuntimeError('V28 lifted V23 patch return drift')
        start=indent+b'_v28_base_compares = []\n'; end=indent+b"if len(_v28_base_compares) != 1: raise RuntimeError(f'V28 immutable-base comparator count drift: {len(_v28_base_compares)}')\n"
        a=raw.find(start); b=raw.find(end)
        if a<0 or b<0 or raw.find(start,a+1)>=0 or raw.find(end,b+1)>=0 or b<a:raise RuntimeError('V28 V23 direct-comparator proof span drift')
        b+=len(end); repl=indent+b'# V28 distributed V4 comparator proof was bound statically to exact V17 source/dataflow before generated execution.\n'
        out=raw[:a]+repl+raw[b:]
        if out.count(repl)!=1 or b'_v28_base_compares' in out:raise RuntimeError('V28 V23 proof-span replacement drift')
        return out
    return wrapped

def lifted24(v24):
    s=v24.decode().replace('V24','V28').replace('v24','v28'); compile(s,'<v28-lifted-v24>','exec'); scope={'__file__':str(HERE),'__name__':'_v28_lifted_v24_'};exec(compile(s,'<v28-lifted-v24>','exec'),scope,scope)
    old=scope.get('_load_lifted_scope')
    if not callable(old):raise RuntimeError('V28 lifted V24 loader missing')
    def loader(env,*args,**kwargs):
        sc,raw=old(env,*args,**kwargs)
        if env=='V23_FROZEN_REVIEWER':
            f=sc.get('_v5_patch_block')
            if not callable(f):raise RuntimeError('V28 lifted V23 patch helper missing')
            sc['_v5_patch_block']=patch_v5_block(f)
        return sc,raw
    scope['_load_lifted_scope']=loader
    return scope

def proof(v4path,v5path,out):
    v26,v25,v24,_v23,_v22,v17=[bound(k) for k in ('V26','V25','V24','V23','V22','V17')]
    if 'PASS_V26_PREACTUAL_BASE85_CANONICAL_TRANSPORT' not in v26.decode():raise RuntimeError('V28 V26 accepted transport proof surface drift')
    transport=payload25(v25); d=distributed(payload17(v17).decode()); m4=json.loads(Path(v4path).read_text()); fx=fixtures4(m4); sem=semantic_fixtures(); sc=lifted24(v24)
    run=sc.get('_run')
    if not callable(run):raise RuntimeError('V28 lifted V24 entry missing')
    old=list(sys.argv); outs={f:arg(f) for f in ('--v28-zero-runtime-proof-out','--v28-v5-proof-out','--v28-entrypoint-proof-out')}
    try:
        sys.argv=[sys.argv[0],'--v28-proof-only','--v5-metadata',v5path]
        for f,val in outs.items():
            if val:sys.argv += [f,val]
        os.environ['V28_PREACTUAL_ACTIVE']='1'; run()
    finally:sys.argv=old
    write(out,{'schemaVersion':1,'status':'PASS_V28_PREACTUAL_DISTRIBUTED_STATIC_V4_DATAFLOW_AND_DOWNSTREAM','transport':transport,'distributedV4Dataflow':d,'v4MetadataFixtures':fx,'semanticFixtures':sem,'controlledActualEquivalentPreactualPassed':True,'authorizationRefCreated':False,'dispatchCreated':False,'scientificOrdinalAllocated':False,'scientificOrdinalReserved':False,'scientificOrdinalDispatched':False,'seedUniverseConsumed':False,'scienceInvoked':False,'solverExecuted':False,'protectedResultsOpened':False,'publisherInvoked':False,'newMappingOpened':False,'productionInvoked':False,'scienceFalse':True})
def actual(v5path):
    if os.environ.get('V28_NONAUTH_ACTUAL')!='1':raise RuntimeError('V28 ACTUAL requires explicit NON_AUTH mode')
    sc=lifted24(bound('V24'));run=sc.get('_run')
    if not callable(run):raise RuntimeError('V28 lifted V24 ACTUAL entry missing')
    old=list(sys.argv)
    try:sys.argv=[sys.argv[0],'--v5-metadata',v5path];run()
    finally:sys.argv=old

def main():
    try:
        v5=arg('--v5-metadata')
        if not v5:raise RuntimeError('V28 frozen V5 metadata input missing')
        if '--v28-proof-only' in sys.argv or os.environ.get('V28_PREACTUAL_ACTIVE')=='1':
            v4=arg('--v4-metadata')
            if not v4:raise RuntimeError('V28 frozen V4 metadata input missing')
            proof(v4,v5,arg('--v28-forensic-proof-out'));return
        actual(v5)
    except BaseException as e:failure(e);raise
if __name__=='__main__':main()
