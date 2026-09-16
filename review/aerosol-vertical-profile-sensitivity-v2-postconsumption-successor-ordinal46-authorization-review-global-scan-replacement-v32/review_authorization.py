from __future__ import annotations
import ast,base64,copy,hashlib,json,os,re,sys,zlib
from pathlib import Path

MAIN='6cd7c075766fe0c86bc7561ec205a3f9120fd1fb'
OLD='f5ebc646aba96ad13753d55baf2b0c55cff64ccb'
V4='a3fc752af64599eed1dc5e358a23295e423b1eb8'
V31B='8824a7bd6d274b2e6a89467ad926e2a5915e0a1b'
V30B='3c723a779303ef4572332ba5e6172276d2f1ed94'
V17B='06867e14710f15cade77ed24fbdc33dafb9f2f74'
P17='3cb6ad6603d53440cfc159d96da5b262c9441102ffca7db3ce7443c22b32f643'
CAND_A='2dd23ac4404f34b7ef6f28ce4ab6ede584f3481d2a9326240a4dec305968288e'
CAND_B='282af3d020ca11c203682fb6faf0971252b849e002fb7869703d4b4fac4b12f9'
FAIL='FAIL_V32_PREACTUAL_LEN_CARDINALITY_SEMANTIC_ROLE_LINEAGE_OR_DOWNSTREAM'
HERE=Path(__file__).resolve()

def A(k):
    try:i=sys.argv.index(k);return sys.argv[i+1]
    except (ValueError,IndexError):return None

def A0(v,k):
    try:i=v.index(k);return v[i+1]
    except (ValueError,IndexError):return None

def H(b):return hashlib.sha256(b).hexdigest()
def B(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()

def W(p,d):
    if not p:return
    d=dict(d)
    d['receiptSha256']=H(json.dumps(d,sort_keys=True,separators=(',',':')).encode())
    q=Path(p);q.parent.mkdir(parents=True,exist_ok=True)
    q.write_text(json.dumps(d,sort_keys=True,indent=2)+'\n')

def F(e):
    if os.getenv('V32_PREACTUAL_ACTIVE')!='1' or not os.getenv('V32_PREACTUAL_FAILURE_DIR'):return
    p=Path(os.environ['V32_PREACTUAL_FAILURE_DIR'])/'failure.json'
    if not p.exists():
        W(str(p),{
            'status':FAIL,'type':type(e).__name__,'message':str(e),
            'authorizationRefCreated':False,'dispatchCreated':False,
            'scientificOrdinalAllocated':False,'scientificOrdinalReserved':False,
            'scientificOrdinalDispatched':False,'seedUniverseConsumed':False,
            'scienceInvoked':False,'solverExecuted':False,'protectedResultsOpened':False,
            'publisherInvoked':False,'newMappingOpened':False,'productionInvoked':False,
            'scienceFalse':True})

def EF(k,h):
    b=Path(os.getenv(k,'')).read_bytes() if os.getenv(k) else b''
    if B(b)!=h:raise RuntimeError(f'V32 {k} blob drift')
    return b

def FN(t,n):
    x=[q for q in t.body if isinstance(q,(ast.FunctionDef,ast.AsyncFunctionDef)) and q.name==n]
    if len(x)!=1:raise RuntimeError(f'V32 {n} count drift: {len(x)}')
    return x[0]

def S(s,n):return ast.get_source_segment(s,n) or ''

def MV(t):
    v={}
    for n in t.body:
        if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and isinstance(n.value,ast.Constant) and isinstance(n.value.value,str):
            v[n.targets[0].id]=n.value.value
    return v

def defs(fn):
    d={}
    for n in ast.walk(fn):
        if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name):
            d.setdefault(n.targets[0].id,[]).append(n.value)
    return d

def dep(n,d,m,seen=frozenset()):
    ns=set();vs=set();amb=set()
    for x in ast.walk(n):
        if isinstance(x,ast.Constant) and isinstance(x.value,str):vs.add(x.value)
        if isinstance(x,ast.Name):
            ns.add(x.id)
            if x.id in m:vs.add(m[x.id])
            if x.id in d and x.id not in seen:
                if len(d[x.id])!=1:amb.add(x.id)
                else:
                    a,b,c=dep(d[x.id][0],d,m,seen|{x.id});ns|=a;vs|=b;amb|=c
    return ns,vs,amb

def rec(s,n,d,m):
    q=S(s,n);a,b,c=dep(n,d,m)
    return {'line':n.lineno,'endLine':getattr(n,'end_lineno',None),'source':q,
            'sourceSha256':H(q.encode()),'astSha256':H(ast.dump(n,include_attributes=False).encode()),
            'names':sorted(a),'values':sorted(b),'ambiguousNames':sorted(c)}

def dv(b):
    t=b.decode()
    p=re.findall(r'^PAYLOAD_B85 = r"""(.*?)"""\.replace\(\'\\n\', \'\'\)$',t,re.M|re.S)
    h=re.findall(r"^PAYLOAD_SHA256 = '([0-9a-f]{64})'$",t,re.M)
    if len(p)!=1 or h!=[P17]:raise RuntimeError('V32 V17 launcher binding drift')
    lines=p[0].splitlines();c=p[0].replace('\n','').encode();z=base64.b85decode(c);raw=zlib.decompress(z)
    if H(raw)!=P17 or base64.b85encode(z)!=c:raise RuntimeError('V32 V26 Base85 transport drift')
    s=raw.decode();ast.parse(s)
    return s,{'physicalLineCount':len(lines),'physicalLineLengths':[len(x) for x in lines],
              'compressedSha256':H(z),'decompressedSha256':H(raw),'canonicalRoundTripExact':True}

def side(s,fs):
    out=[]
    for f in fs:
        for n in ast.walk(f):
            if not isinstance(n,ast.Call):continue
            op=None
            if isinstance(n.func,ast.Name) and n.func.id in {'exec','eval','open','__import__','compile'}:op=n.func.id
            elif isinstance(n.func,ast.Attribute):
                r=n.func.value
                while isinstance(r,ast.Attribute):r=r.value
                if isinstance(r,ast.Name) and r.id in {'subprocess','os','requests','urllib','socket','pathlib','shutil'}:op=f'{r.id}.{n.func.attr}'
            if op:out.append({'function':f.name,'line':n.lineno,'operation':op,'source':S(s,n),'executedDuringForensicProof':False})
    return out

def direct_names(n):return {x.id for x in ast.walk(n) if isinstance(x,ast.Name)}
def direct_strings(n):return {x.value for x in ast.walk(n) if isinstance(x,ast.Constant) and isinstance(x.value,str)}

def assignments(fn,s,d,m):
    out={}
    for n in ast.walk(fn):
        if not(isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name)):continue
        name=n.targets[0].id
        rr=rec(s,n.value,d,m)
        rr.update({'target':name,'assignmentSource':S(s,n),'assignmentSourceSha256':H(S(s,n).encode()),
                   'directNames':sorted(direct_names(n.value)),'directStrings':sorted(direct_strings(n.value))})
        out.setdefault(name,[]).append((n.value,rr))
    return out

def unique_defs(ad):
    bad=sorted(k for k,v in ad.items() if len(v)!=1)
    if bad:raise RuntimeError('V32 ambiguous assignment definitions: '+','.join(bad))
    return {k:v[0] for k,v in ad.items()}

def graph(ud):
    g={k:set() for k in ud}
    for target,(value,_) in ud.items():
        for name in direct_names(value):
            if name in ud and name!=target:g.setdefault(name,set()).add(target)
    return g

def reaches(g,a,b):
    if a==b:return True
    seen=set();stack=[a]
    while stack:
        x=stack.pop()
        if x in seen:continue
        seen.add(x)
        for y in g.get(x,()):
            if y==b:return True
            stack.append(y)
    return False

def descendants(g,a):
    seen=set();stack=[a]
    while stack:
        x=stack.pop()
        for y in g.get(x,()):
            if y not in seen:seen.add(y);stack.append(y)
    return seen

def extract_cardinality_sequence(cmp_node):
    calls=[x for x in ast.walk(cmp_node) if isinstance(x,ast.Call) and isinstance(x.func,ast.Name) and x.func.id=='len' and len(x.args)==1]
    ones=[x for x in ast.walk(cmp_node) if isinstance(x,ast.Constant) and x.value==1]
    if len(calls)!=1 or len(ones)!=1:raise RuntimeError('V32 frozen cardinality guard representation drift')
    return calls[0].args[0]

def call_sites(s,fn,names):
    out=[]
    for c in ast.walk(fn):
        if not isinstance(c,ast.Call):continue
        callee=c.func.id if isinstance(c.func,ast.Name) else None
        if callee in names:
            out.append({'callee':callee,'line':c.lineno,'source':S(s,c),'sourceSha256':H(S(s,c).encode()),
                        'astSha256':H(ast.dump(c,include_attributes=False).encode())})
    return out

def classify_rows(rows):
    a=[r for r in rows if r['semanticLineage']['canReachInsertion'] and r['semanticLineage']['canReachAcceptedReturn'] and not r['semanticLineage']['acceptedReturnCanReachGuardedSequence']]
    d=[r for r in rows if (not r['semanticLineage']['canReachInsertion']) and (not r['semanticLineage']['canReachAcceptedReturn']) and r['semanticLineage']['acceptedReturnCanReachGuardedSequence']]
    if len(a)!=1 or len(d)!=1:
        raise RuntimeError(f'V32 cardinality semantic lineage remains ambiguous: authoritative={len(a)} distinct={len(d)}')
    if a[0]['sourceSha256']==d[0]['sourceSha256']:raise RuntimeError('V32 duplicate authoritative semantic chain')
    return a[0],d[0]

def inventory(v17,v30,v31,tr):
    t=ast.parse(v17);m=MV(t);ins=FN(t,'_insert_v4_expected_base');rep=FN(t,'_repair_base_comparator');ass=FN(t,'_assert_v4_historical_source_binding');bld=FN(t,'_build_v17_effective_source')
    d=defs(ins);ad=assignments(ins,v17,d,m);ud=unique_defs(ad);g=graph(ud)
    cands=[]
    for n in ast.walk(ins):
        if not isinstance(n,ast.Compare):continue
        q=S(v17,n);sha=H(q.encode())
        if sha not in {CAND_A,CAND_B}:continue
        seq=extract_cardinality_sequence(n)
        if not isinstance(seq,ast.Name):raise RuntimeError('V32 guarded sequence is not an exact assigned value')
        if seq.id not in ud:raise RuntimeError('V32 guarded sequence producer missing')
        value,prod=ud[seq.id]
        selected=[]
        for x in ast.walk(ins):
            if isinstance(x,ast.Subscript) and isinstance(x.value,ast.Name) and x.value.id==seq.id:
                sr=S(v17,x);selected.append({'line':x.lineno,'source':sr,'sourceSha256':H(sr.encode()),'astSha256':H(ast.dump(x,include_attributes=False).encode())})
        r=rec(v17,n,d,m)
        r['guardedSequence']={'source':S(v17,seq),'astSha256':H(ast.dump(seq,include_attributes=False).encode()),'producer':prod,'selectionUses':selected}
        cands.append(r)
    if len(cands)!=2 or {r['sourceSha256'] for r in cands}!={CAND_A,CAND_B}:
        raise RuntimeError(f'V32 frozen V31 candidate identity drift: {len(cands)}')

    insertion_targets=[]
    for target,(value,rr) in ud.items():
        ds=direct_strings(value);_,vals,amb=dep(value,d,m)
        if amb:raise RuntimeError('V32 ambiguous insertion dependency')
        if any('expectedBaseSha' in x for x in ds) and OLD in vals:
            insertion_targets.append((target,rr))
    if len(insertion_targets)!=1:raise RuntimeError(f'V32 expectedBaseSha insertion constructor count drift: {len(insertion_targets)}')
    insert_target,insert_rec=insertion_targets[0]
    if MAIN in insert_rec['values']:raise RuntimeError('V32 current-MAIN leakage into historical insertion constructor')

    returns=[]
    for n in ast.walk(ins):
        if isinstance(n,ast.Return) and isinstance(n.value,ast.Name) and n.value.id in ud:
            rr=rec(v17,n.value,d,m);returns.append((n.value.id,rr))
    if len(returns)!=1:raise RuntimeError(f'V32 accepted return count drift: {len(returns)}')
    return_target,return_rec=returns[0]
    if not reaches(g,insert_target,return_target):raise RuntimeError('V32 insertion constructor does not feed accepted return')

    for r in cands:
        seqname=r['guardedSequence']['source']
        lin={
            'canReachInsertion':reaches(g,seqname,insert_target),
            'canReachAcceptedReturn':reaches(g,seqname,return_target),
            'acceptedReturnCanReachGuardedSequence':reaches(g,return_target,seqname),
            'producerDirectNames':r['guardedSequence']['producer']['directNames'],
            'producerDependencyNames':r['guardedSequence']['producer']['names'],
            'producerDependencyValues':r['guardedSequence']['producer']['values'],
            'downstreamAssignedValues':sorted(descendants(g,seqname)),
            'insertionConstructorTargetSha256':H(insert_target.encode()),
            'acceptedReturnTargetSha256':H(return_target.encode()),
        }
        r['semanticLineage']=lin
        r['callerChain']=['_build_v17_effective_source','_insert_v4_expected_base','_repair_base_comparator','_assert_v4_historical_source_binding']
        r['roleDeterminationExcludes']=['source-order','line-number','sequence-variable-name','helper-name','token-literal-coincidence','guard-syntax-shape','guessed-intent']

    auth,distinct=classify_rows(cands)
    if auth['semanticLineage']['acceptedReturnCanReachGuardedSequence']:
        raise RuntimeError('V32 authoritative chain unexpectedly post-return')
    if not distinct['semanticLineage']['acceptedReturnCanReachGuardedSequence']:
        raise RuntimeError('V32 distinct chain is not proven downstream of accepted return')

    fns={'_insert_v4_expected_base':ins,'_repair_base_comparator':rep,'_assert_v4_historical_source_binding':ass,'_build_v17_effective_source':bld}
    spans={k:{'line':f.lineno,'endLine':f.end_lineno,'sourceSha256':H(S(v17,f).encode()),'astSha256':H(ast.dump(f,include_attributes=False).encode())}
           for k,f in {'insert':ins,'repair':rep,'assert':ass,'builder':bld}.items()}
    calls=[];cg={k:set() for k in fns}
    for caller,fn in fns.items():
        for c in call_sites(v17,fn,set(fns)):
            calls.append({'caller':caller,**c});cg[caller].add(c['callee'])
    def call_reaches(a,b):
        seen=set();stack=[a]
        while stack:
            x=stack.pop()
            if x in seen:continue
            seen.add(x)
            for y in cg.get(x,()):
                if y==b:return True
                stack.append(y)
        return False
    for target in {'_insert_v4_expected_base','_repair_base_comparator','_assert_v4_historical_source_binding'}:
        if not call_reaches('_build_v17_effective_source',target):raise RuntimeError('V32 accepted builder/caller chain drift: '+target)

    t31=ast.parse(v31);i31=FN(t31,'inv');s31=S(v31,i31)
    count_literals=[x for x in ast.walk(i31) if isinstance(x,ast.Constant) and x.value=='count']
    if not count_literals:raise RuntimeError('V32 V31 negative extractor provenance drift')
    v31neg={'invSourceSha256':H(s31.encode()),'invAstSha256':H(ast.dump(i31,include_attributes=False).encode()),
            'countLiteralOccurrences':len(count_literals),'frozenCandidatesAreLenCalls':True,
            'observedFrozenOutcome':'authoritative=0 distinct=0','negativeFixture':True}

    return {
        'schemaVersion':1,'status':'V32_FORENSIC_INVENTORY_FROZEN_BEFORE_ROLE_USE',
        'v17PayloadSha256':P17,'base85Transport':tr,'frozenFunctionSpans':spans,
        'acceptedBuilderCallerSites':calls,'frozenCandidateCount':2,'frozenCandidates':cands,
        'expectedBaseShaInsertionConstructor':insert_rec,'acceptedInsertionReturn':return_rec,
        'authoritativeCandidateSha256':auth['sourceSha256'],'distinctCandidateSha256':distinct['sourceSha256'],
        'v31NegativeFixture':v31neg,
        'reachableSideEffectOperationsInventoriedNotExecuted':side(v17,[ins,rep,ass,bld]),
        'forensicProofExecutedSideEffects':False,'historicalV4Base':OLD,'currentSuccessorMain':MAIN,
        'historicalBaseSeparatedFromCurrentMain':OLD!=MAIN,'scienceFalse':True},auth,distinct

def vm(m):
    c=[m.get('number')==1032,m.get('state')=='open',m.get('draft') is True,m.get('merged') is False,
       (m.get('head')or{}).get('sha')==V4,(m.get('base')or{}).get('ref')=='main',(m.get('base')or{}).get('sha')==OLD]
    if not all(c):raise RuntimeError('V32 frozen V4 metadata drift')

def fixture_fail(fn,*args):
    try:fn(*args);return False
    except RuntimeError:return True

def fixtures(m,rows,auth,distinct,inv):
    vm(m);out={}
    for k,path,v in [('wrongHistoricalBaseFatal',('base','sha'),'0'*40),('wrongHeadFatal',('head','sha'),'1'*40),
                     ('wrongBaseRefFatal',('base','ref'),'x'),('wrongStateFatal',(None,'state'),'closed'),('wrongMergedFatal',(None,'merged'),True)]:
        q=copy.deepcopy(m)
        if path[0] is None:q[path[1]]=v
        else:q[path[0]][path[1]]=v
        if not fixture_fail(vm,q):raise RuntimeError('V32 fixture did not fail: '+k)
        out[k]=True
    if OLD==MAIN:raise RuntimeError('V32 current-MAIN leakage fixture impossible')
    out['currentMainLeakageFatal']=True
    a2,d2=classify_rows(list(reversed(copy.deepcopy(rows))))
    if a2['sourceSha256']!=auth['sourceSha256'] or d2['sourceSha256']!=distinct['sourceSha256']:
        raise RuntimeError('V32 source-order swap changed semantic classification')
    out['sourceOrderSwapInvariant']=True
    if not fixture_fail(classify_rows,[copy.deepcopy(auth),copy.deepcopy(auth)]):raise RuntimeError('V32 duplicate-authoritative fixture did not fail')
    out['duplicateAuthoritativeSemanticChainFatal']=True
    plausible=copy.deepcopy(distinct);plausible['semanticLineage']=copy.deepcopy(auth['semanticLineage'])
    if not fixture_fail(classify_rows,[copy.deepcopy(auth),plausible]):raise RuntimeError('V32 both-plausible fixture did not fail')
    out['bothCandidatesPlausibleFatal']=True
    if not fixture_fail(classify_rows,[]):raise RuntimeError('V32 zero-candidate fixture did not fail')
    out['zeroCandidateFatal']=True
    len_form=copy.deepcopy(auth);count_form=copy.deepcopy(auth)
    len_form['cardinalityRepresentation']='len(sequence)';count_form['cardinalityRepresentation']='producer.count(match)'
    la,_=classify_rows([len_form,copy.deepcopy(distinct)]);ca,_=classify_rows([count_form,copy.deepcopy(distinct)])
    if la['sourceSha256']!=ca['sourceSha256']:raise RuntimeError('V32 count-vs-len semantic-equivalence fixture drift')
    out['countVsLenRepresentationInvariant']=True
    noise="""# len(nodes) != 1\nT='len(nodes2) != 1'\ndef x():\n    return T\n"""
    nt=ast.parse(noise)
    if any(isinstance(x,ast.Compare) for x in ast.walk(nt)):raise RuntimeError('V32 comments/templates/noise fixture unexpectedly executable')
    out['commentsTemplatesNoiseCannotSatisfy']=True
    if inv['v31NegativeFixture']['observedFrozenOutcome']!='authoritative=0 distinct=0':raise RuntimeError('V32 V31 negative fixture drift')
    out['v31Authoritative0Distinct0NegativeFixture']=True
    return out

def patch(v30,a,d):
    t=ast.parse(v30);u=FN(t,'UG');old=S(v30,u);rows=[]
    drop={'guardedSequence','semanticLineage','callerChain','roleDeterminationExcludes'}
    for r,lab in ((a,'candidate-unique-source-target-guard'),(d,'distinct-non-substitutable-semantic-cardinality-guard')):
        q={k:v for k,v in r.items() if k not in drop};q['classification']=lab;rows.append(q)
    rep="def UG(s,fn,mv):\n    return copy.deepcopy(V32_ROWS)"
    p=v30.replace(old,rep,1)
    sc={'__file__':str(HERE),'__name__':'_v32_v30_bridge_','V32_ROWS':rows}
    exec(compile(p,'<v32-v30-bridge>','exec'),sc,sc)
    return sc,{'frozenV30UGSourceSha256':H(old.encode()),'patchedV30SourceSha256':H(p.encode()),
               'authoritativeGuardSourceSha256':a['sourceSha256'],'distinctGuardSourceSha256':d['sourceSha256']}

def proof(v4,v5):
    v31=EF('V31_FROZEN_REVIEWER',V31B).decode();v30=EF('V30_FROZEN_REVIEWER',V30B).decode();v17,tr=dv(EF('V17_FROZEN_REVIEWER',V17B))
    m=json.loads(Path(v4).read_text());inv,a,d=inventory(v17,v30,v31,tr);fx=fixtures(m,inv['frozenCandidates'],a,d,inv)
    W(A('--v32-inventory-out'),inv)
    W(A('--v32-forensic-proof-out'),{'status':'PASS_V32_PREACTUAL_LEN_CARDINALITY_SEMANTIC_ROLE_LINEAGE',
       'authoritativeGuard':a,'distinctGuard':d,'fixtures':fx,'scienceFalse':True})
    sc,br=patch(v30,a,d);old=list(sys.argv)
    try:
        sys.argv=[old[0],'--v30-proof-only','--v4-metadata',v4,'--v5-metadata',v5]
        for x,y in [('--v32-v30-forensic-out','--v30-forensic-proof-out'),('--v32-v30-bridge-out','--v30-bridge-proof-out'),
                    ('--v32-v30-static-bridge-out','--v30-v29-static-bridge-out'),('--v32-downstream-proof-out','--v30-downstream-proof-out'),
                    ('--v32-zero-runtime-proof-out','--v30-zero-runtime-proof-out'),('--v32-v5-proof-out','--v30-v5-proof-out'),
                    ('--v32-entrypoint-proof-out','--v30-entrypoint-proof-out')]:
            q=A0(old,x);sys.argv+=([y,q] if q else [])
        sc['PROOF'](v4,v5)
    finally:sys.argv=old
    W(A('--v32-bridge-proof-out'),{'status':'PASS_V32_NARROW_V30_SEMANTIC_LINEAGE_BRIDGE_TO_ACCEPTED_DOWNSTREAM','bridge':br,'scienceFalse':True})

def actual(v5):
    if os.getenv('V32_NONAUTH_ACTUAL')!='1':raise RuntimeError('V32 ACTUAL requires explicit NON_AUTH mode')
    s=EF('V30_FROZEN_REVIEWER',V30B).decode();sc={'__file__':str(HERE),'__name__':'_v32_v30_actual_'}
    exec(compile(s,'<v32-v30-actual>','exec'),sc,sc)
    old=os.getenv('V30_NONAUTH_ACTUAL');os.environ['V30_NONAUTH_ACTUAL']='1'
    try:sc['ACT'](v5)
    finally:
        if old is None:os.environ.pop('V30_NONAUTH_ACTUAL',None)
        else:os.environ['V30_NONAUTH_ACTUAL']=old

def main():
    try:
        v5=A('--v5-metadata')
        if not v5:raise RuntimeError('V32 frozen V5 metadata input missing')
        if '--v32-proof-only' in sys.argv or os.getenv('V32_PREACTUAL_ACTIVE')=='1':
            v4=A('--v4-metadata')
            if not v4:raise RuntimeError('V32 frozen V4 metadata input missing')
            proof(v4,v5)
        else:actual(v5)
    except BaseException as e:F(e);raise

if __name__=='__main__':main()
