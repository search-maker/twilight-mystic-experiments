from __future__ import annotations
import ast,copy,hashlib,json,os,sys
from pathlib import Path

MAIN='6cd7c075766fe0c86bc7561ec205a3f9120fd1fb'
OLD='f5ebc646aba96ad13753d55baf2b0c55cff64ccb'
V4='a3fc752af64599eed1dc5e358a23295e423b1eb8'
V33B='42075f7cc8f48c1cf7588ab5404be27953a6f529'
V32B='fb055c6f24ca18c08b2fab31ab8e59f05d1a0d8a'
V30B='3c723a779303ef4572332ba5e6172276d2f1ed94'
V17B='06867e14710f15cade77ed24fbdc33dafb9f2f74'
P17='3cb6ad6603d53440cfc159d96da5b262c9441102ffca7db3ce7443c22b32f643'
CAND_A='2dd23ac4404f34b7ef6f28ce4ab6ede584f3481d2a9326240a4dec305968288e'
CAND_B='282af3d020ca11c203682fb6faf0971252b849e002fb7869703d4b4fac4b12f9'
V32_REFUSAL='V32 cardinality semantic lineage remains ambiguous: authoritative=0 distinct=1'
V33_REFUSAL='V33 control semantic lineage remains ambiguous: authoritative=0 distinct=0'
FAIL='FAIL_V34_PREACTUAL_V33_CLASSIFIER_PREDICATE_FORENSIC_OR_DOWNSTREAM'
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
    d=dict(d);d['receiptSha256']=H(json.dumps(d,sort_keys=True,separators=(',',':')).encode())
    q=Path(p);q.parent.mkdir(parents=True,exist_ok=True);q.write_text(json.dumps(d,sort_keys=True,indent=2)+'\n')

def WT(p,s):
    if not p:return
    q=Path(p);q.parent.mkdir(parents=True,exist_ok=True);q.write_text(s)

def F(e):
    if os.getenv('V34_PREACTUAL_ACTIVE')!='1' or not os.getenv('V34_PREACTUAL_FAILURE_DIR'):return
    p=Path(os.environ['V34_PREACTUAL_FAILURE_DIR'])/'failure.json'
    if not p.exists():
        W(str(p),{'status':FAIL,'type':type(e).__name__,'message':str(e),
            'authorizationRefCreated':False,'dispatchCreated':False,'scientificOrdinalAllocated':False,
            'scientificOrdinalReserved':False,'scientificOrdinalDispatched':False,'seedUniverseConsumed':False,
            'scienceInvoked':False,'solverExecuted':False,'protectedResultsOpened':False,'publisherInvoked':False,
            'newMappingOpened':False,'productionInvoked':False,'scienceFalse':True})

def file_bytes(env,blob,label):
    p=os.getenv(env)
    if not p:raise RuntimeError(f'V34 {label} path missing')
    b=Path(p).read_bytes()
    if B(b)!=blob:raise RuntimeError(f'V34 {label} blob drift')
    return b

def load_v33():
    b=file_bytes('V33_FROZEN_REVIEWER',V33B,'V33 reviewer')
    s=b.decode()
    sc={'__file__':str(HERE),'__name__':'_v34_frozen_v33_'}
    exec(compile(s,'<frozen-v33>','exec'),sc,sc)
    return b,s,sc

def flatten_and(n):
    if isinstance(n,ast.BoolOp) and isinstance(n.op,ast.And):
        out=[]
        for x in n.values:out.extend(flatten_and(x))
        return out
    return [n]

def subpath(n):
    if isinstance(n,ast.UnaryOp) and isinstance(n.op,ast.Not):return subpath(n.operand)
    keys=[];x=n
    while isinstance(x,ast.Subscript):
        sl=x.slice
        if not(isinstance(sl,ast.Constant) and isinstance(sl.value,str)):return None
        keys.append(sl.value);x=x.value
    if not(isinstance(x,ast.Name) and x.id=='r'):return None
    return list(reversed(keys))

def peval(n,row):
    if isinstance(n,ast.Name):
        if n.id=='r':return row
        raise RuntimeError('V34 predicate references non-row name: '+n.id)
    if isinstance(n,ast.Constant):return n.value
    if isinstance(n,ast.Subscript):return peval(n.value,row)[peval(n.slice,row)]
    if isinstance(n,ast.UnaryOp) and isinstance(n.op,ast.Not):return not bool(peval(n.operand,row))
    if isinstance(n,ast.BoolOp) and isinstance(n.op,ast.And):return all(bool(peval(x,row)) for x in n.values)
    if isinstance(n,ast.BoolOp) and isinstance(n.op,ast.Or):return any(bool(peval(x,row)) for x in n.values)
    if isinstance(n,ast.Compare) and len(n.ops)==1 and len(n.comparators)==1:
        a=peval(n.left,row);b=peval(n.comparators[0],row);op=n.ops[0]
        if isinstance(op,ast.Eq):return a==b
        if isinstance(op,ast.NotEq):return a!=b
        if isinstance(op,ast.Is):return a is b
        if isinstance(op,ast.IsNot):return a is not b
    raise RuntimeError('V34 unsupported frozen V33 predicate AST: '+ast.dump(n,include_attributes=False))

def predicate_specs(v33src,v33):
    t=ast.parse(v33src);fn=v33['FN'](t,'classify_rows');roles={}
    for st in fn.body:
        if not(isinstance(st,ast.Assign) and len(st.targets)==1 and isinstance(st.targets[0],ast.Name) and st.targets[0].id in {'a','d'} and isinstance(st.value,ast.ListComp)):continue
        role='authoritative' if st.targets[0].id=='a' else 'distinct'
        if len(st.value.generators)!=1 or len(st.value.generators[0].ifs)!=1:raise RuntimeError('V34 frozen V33 classifier comprehension shape drift')
        atoms=flatten_and(st.value.generators[0].ifs[0]);arr=[]
        for i,n in enumerate(atoms):
            src=ast.get_source_segment(v33src,n) or '';path=subpath(n)
            if not src or path is None:raise RuntimeError('V34 frozen V33 classifier predicate provenance unresolved')
            arr.append({'role':role,'ordinal':i,'source':src,'sourceUtf8ByteLength':len(src.encode()),
                'sourceSha256':H(src.encode()),'ast':ast.dump(n,include_attributes=False),
                'astSha256':H(ast.dump(n,include_attributes=False).encode()),'requiredInputPath':path,'node':n})
        roles[role]=arr
    if set(roles)!={'authoritative','distinct'} or any(len(v)!=4 for v in roles.values()):raise RuntimeError('V34 frozen V33 classifier predicate inventory drift')
    fsrc=ast.get_source_segment(v33src,fn) or ''
    frozen={'function':'classify_rows','source':fsrc,'sourceUtf8ByteLength':len(fsrc.encode()),'sourceSha256':H(fsrc.encode()),
        'ast':ast.dump(fn,include_attributes=False),'astSha256':H(ast.dump(fn,include_attributes=False).encode()),
        'roles':{k:[{x:y for x,y in p.items() if x!='node'} for p in v] for k,v in roles.items()}}
    return roles,frozen

def build_rows(v17,v33,tr):
    t=ast.parse(v17);m=v33['MV'](t);ins=v33['FN'](t,'_insert_v4_expected_base');rep=v33['FN'](t,'_repair_base_comparator');ass=v33['FN'](t,'_assert_v4_historical_source_binding');bld=v33['FN'](t,'_build_v17_effective_source')
    d=v33['defs'](ins);ad=v33['assignments'](ins,v17,d,m);ud=v33['unique_defs'](ad);vg=v33['value_graph'](ud);cfg=v33['build_cfg'](ins)
    insertion=[]
    for target,(stmt,value,rr) in ud.items():
        ds=v33['direct_strings'](value);_,vals,amb=v33['dep'](value,d,m)
        if amb:raise RuntimeError('V34 ambiguous insertion dependency')
        if any('expectedBaseSha' in x for x in ds) and OLD in vals:insertion.append((target,stmt,value,rr))
    if len(insertion)!=1:raise RuntimeError(f'V34 expectedBaseSha insertion constructor count drift: {len(insertion)}')
    insert_target,insert_stmt,insert_value,insert_rec=insertion[0]
    if MAIN in insert_rec['values']:raise RuntimeError('V34 current-MAIN leakage into historical insertion constructor')
    returns=[n for n in ast.walk(ins) if isinstance(n,ast.Return) and isinstance(n.value,ast.Name) and n.value.id in ud]
    if len(returns)!=1:raise RuntimeError(f'V34 accepted return count drift: {len(returns)}')
    ret=returns[0];return_target=ret.value.id;return_rec=v33['rec'](v17,ret.value,d,m)
    if not v33['reaches'](vg,insert_target,return_target):raise RuntimeError('V34 insertion constructor does not feed accepted return')
    rows=[]
    for n in ast.walk(ins):
        if not isinstance(n,ast.Compare):continue
        src=v33['S'](v17,n);sha=H(src.encode())
        if sha not in {CAND_A,CAND_B}:continue
        seq=v33['extract_cardinality_sequence'](n)
        if not isinstance(seq,ast.Name) or seq.id not in ud:raise RuntimeError('V34 guarded sequence producer unresolved')
        st,_,prod=ud[seq.id];iff=v33['containing_if'](ins,n);iid=id(iff);br=cfg['branches'].get(iid)
        if not br:raise RuntimeError('V34 candidate branch missing from frozen V33 CFG')
        ti=v33['graph_reaches'](cfg,br['true'],id(insert_stmt));fi=v33['graph_reaches'](cfg,br['false'],id(insert_stmt))
        trr=v33['graph_reaches'](cfg,br['true'],id(ret));frr=v33['graph_reaches'](cfg,br['false'],id(ret))
        r=v33['rec'](v17,n,d,m);selected=[]
        for x in ast.walk(ins):
            if isinstance(x,ast.Subscript) and isinstance(x.value,ast.Name) and x.value.id==seq.id:
                sr=v33['S'](v17,x);selected.append({'line':x.lineno,'source':sr,'sourceSha256':H(sr.encode()),'astSha256':H(ast.dump(x,include_attributes=False).encode())})
        r['guardedSequence']={'source':v33['S'](v17,seq),'astSha256':H(ast.dump(seq,include_attributes=False).encode()),'producer':prod,'selectionUses':selected}
        r['basicBlockGuard']={'function':'_insert_v4_expected_base',**v33['stmt_record'](v17,iff),'branchEdges':{'true':None if br['true'] is None else v33['stmt_record'](v17,cfg['nodes'][br['true']]),'false':None if br['false'] is None else v33['stmt_record'](v17,cfg['nodes'][br['false']])}}
        r['controlLineage']={'trueBranchReachesInsertion':ti,'falseBranchReachesInsertion':fi,'controlsInsertion':ti!=fi,
            'trueBranchReachesAcceptedReturn':trr,'falseBranchReachesAcceptedReturn':frr,'controlsAcceptedReturn':trr!=frr,
            'insertionDominatesGuard':id(insert_stmt) in cfg['dom'][iid],
            'guardDominatesInsertion':iid in cfg['dom'][id(insert_stmt)],'guardDominatesAcceptedReturn':iid in cfg['dom'][id(ret)]}
        downstream=[]
        for name in sorted(v33['descendants'](vg,seq.id)):
            if name in ud:downstream.append({'target':name,'assignment':ud[name][2]})
        r['dataLineage']={'guardedSequenceCanReachInsertionByValue':v33['reaches'](vg,seq.id,insert_target),
            'guardedSequenceCanReachAcceptedReturnByValue':v33['reaches'](vg,seq.id,return_target),
            'acceptedReturnCanReachGuardedSequence':v33['reaches'](vg,return_target,seq.id),
            'downstreamConsumers':downstream,'acceptedReturn':v33['stmt_record'](v17,ret),'insertionAssignment':v33['stmt_record'](v17,insert_stmt)}
        r['callerChain']=['_build_v17_effective_source','_insert_v4_expected_base','_repair_base_comparator','_assert_v4_historical_source_binding'];rows.append(r)
    if len(rows)!=2 or {r['sourceSha256'] for r in rows}!={CAND_A,CAND_B}:raise RuntimeError(f'V34 frozen candidate identity drift: {len(rows)}')
    effects=v33['side'](v17,[ins,rep,ass,bld])
    spans={k:{'line':f.lineno,'endLine':f.end_lineno,'source':v33['S'](v17,f),'sourceSha256':H(v33['S'](v17,f).encode()),'ast':ast.dump(f,include_attributes=False),'astSha256':H(ast.dump(f,include_attributes=False).encode())} for k,f in {'insert':ins,'repair':rep,'assert':ass,'builder':bld}.items()}
    snap=v33['cfg_snapshot'](v17,cfg)
    frozen={'v17PayloadSha256':P17,'base85Transport':tr,'frozenFunctionSpans':spans,'insertFunctionControlFlowGraph':snap,
        'expectedBaseShaInsertionConstructor':insert_rec,'acceptedInsertionReturn':return_rec,'frozenCandidates':rows,
        'reachableSideEffectOperationsInventoriedNotExecuted':effects,'forensicProofExecutedSideEffects':False,
        'historicalV4Base':OLD,'currentSuccessorMain':MAIN,'historicalBaseSeparatedFromCurrentMain':OLD!=MAIN,'scienceFalse':True}
    return rows,frozen

def table(rows,specs):
    out=[]
    for r in rows:
        for role in ('authoritative','distinct'):
            entries=[]
            for p in specs[role]:
                ok=bool(peval(p['node'],r));entries.append({'predicateOrdinal':p['ordinal'],'predicateSource':p['source'],'predicateSourceSha256':p['sourceSha256'],'predicateAstSha256':p['astSha256'],'requiredInputPath':p['requiredInputPath'],'observedValue':ok,'outcome':'PASS' if ok else 'FAIL','rejectReason':None if ok else 'required predicate evaluated false'})
            false=[e for e in entries if not e['observedValue']]
            out.append({'candidateSourceSha256':r['sourceSha256'],'candidateSource':r['source'],'role':role,'predicates':entries,'roleAcceptedByFrozenV33Predicates':not false,
                'firstFailingPredicate':None if not false else false[0],'failureSetOrderInvariant':sorted({e['predicateAstSha256'] for e in false})})
    return out

def semantic_anchors(rows):
    auth=[];distinct=[]
    for r in rows:
        c=r['controlLineage'];d=r['dataLineage'];sel=r['guardedSequence']['selectionUses']
        aa=(c['controlsInsertion'] and c['guardDominatesInsertion'] and not c['insertionDominatesGuard'] and not d['acceptedReturnCanReachGuardedSequence'] and bool(sel))
        dd=((not c['controlsInsertion']) and c['insertionDominatesGuard'] and not c['guardDominatesInsertion'] and d['acceptedReturnCanReachGuardedSequence'] and bool(sel))
        if aa:auth.append(r)
        if dd:distinct.append(r)
    if len(auth)!=1 or len(distinct)!=1 or auth[0]['sourceSha256']==distinct[0]['sourceSha256']:raise RuntimeError(f'V34 independent semantic anchors ambiguous: authoritative={len(auth)} distinct={len(distinct)}')
    return auth[0],distinct[0]

def false_specs(row,specs):return [p for p in specs if not bool(peval(p['node'],row))]

def repair_diagnosis(rows,specs,auth,distinct):
    fa=false_specs(auth,specs['authoritative']);fd=false_specs(distinct,specs['distinct'])
    if len(fa)!=1 or len(fd)!=1:raise RuntimeError(f'V34 classifier defect count is not uniquely one per anchored role: authoritative={len(fa)} distinct={len(fd)}')
    pa,pd=fa[0],fd[0]
    if pa['astSha256']!=pd['astSha256'] or pa['requiredInputPath']!=pd['requiredInputPath']:raise RuntimeError('V34 anchored roles fail different V33 classifier predicates')
    if pa['requiredInputPath']!=['controlLineage','controlsAcceptedReturn']:raise RuntimeError('V34 unique failing predicate is not statically proven orthogonal return-control predicate')
    for base,label in ((auth,'authoritative'),(distinct,'distinct')):
        q0=copy.deepcopy(base);q1=copy.deepcopy(base);q0['controlLineage']['controlsAcceptedReturn']=False;q1['controlLineage']['controlsAcceptedReturn']=True
        other=copy.deepcopy(distinct if label=='authoritative' else auth)
        a0,d0=semantic_anchors([q0,other]);a1,d1=semantic_anchors([q1,copy.deepcopy(other)])
        target=base['sourceSha256'];got0=(a0 if label=='authoritative' else d0)['sourceSha256'];got1=(a1 if label=='authoritative' else d1)['sourceSha256']
        if got0!=target or got1!=target:raise RuntimeError('V34 failing predicate is not orthogonal to exact semantic anchor')
    return {'status':'UNIQUE_MINIMAL_V33_CLASSIFIER_MISMATCH_DEMONSTRATED','sharedFailingPredicateSource':pa['source'],'sharedFailingPredicateSourceSha256':pa['sourceSha256'],
        'sharedFailingPredicateAstSha256':pa['astSha256'],'requiredInputPath':pa['requiredInputPath'],'authoritativeObservedValue':peval(pa['node'],auth),'distinctObservedValue':peval(pd['node'],distinct),
        'correction':'remove this orthogonal predicate from both role conjunctions; do not invert or synthesize role evidence',
        'correctionUniquenessBasis':'exact independent producer/control/data anchors remain invariant under both values of the field; every other frozen V33 role predicate passes on its anchored role'},pa['astSha256']

def classify_repaired(rows,specs,drop_ast,order_reverse=False):
    got={}
    for role in ('authoritative','distinct'):
        pp=[p for p in specs[role] if p['astSha256']!=drop_ast]
        if len(pp)!=3:raise RuntimeError('V34 repaired predicate cardinality drift')
        if order_reverse:pp=list(reversed(pp))
        got[role]=[r for r in rows if all(bool(peval(p['node'],r)) for p in pp)]
    if len(got['authoritative'])!=1 or len(got['distinct'])!=1:raise RuntimeError(f"V34 repaired semantic lineage ambiguous: authoritative={len(got['authoritative'])} distinct={len(got['distinct'])}")
    a=got['authoritative'][0];d=got['distinct'][0]
    if a['sourceSha256']==d['sourceSha256']:raise RuntimeError('V34 duplicate repaired role chain')
    return a,d

def fixture_fail(fn,*args,**kwargs):
    try:fn(*args,**kwargs);return False
    except RuntimeError:return True

def metadata_fixtures(v33,m):
    v33['vm'](m);out={}
    for k,path,val in [('wrongHistoricalBaseFatal',('base','sha'),'0'*40),('wrongHeadFatal',('head','sha'),'1'*40),('wrongBaseRefFatal',('base','ref'),'x'),('wrongStateFatal',(None,'state'),'closed'),('wrongMergedFatal',(None,'merged'),True)]:
        q=copy.deepcopy(m)
        if path[0] is None:q[path[1]]=val
        else:q[path[0]][path[1]]=val
        if not fixture_fail(v33['vm'],q):raise RuntimeError('V34 metadata fixture did not fail: '+k)
        out[k]=True
    return out

def fixtures(v33,v32src,m,rows,specs,auth,distinct,drop_ast,frozen):
    out=metadata_fixtures(v33,m)
    if OLD==MAIN or MAIN in frozen['expectedBaseShaInsertionConstructor']['values']:raise RuntimeError('V34 current-MAIN leakage fixture failed')
    out['currentMainLeakageFatal']=True
    try:v33['classify_rows'](copy.deepcopy(rows));raise RuntimeError('V34 exact V33 negative unexpectedly passed')
    except RuntimeError as e:
        if str(e)!=V33_REFUSAL:raise
    out['exactV33Authoritative0Distinct0NegativeFixture']=True
    t32=ast.parse(v32src);c32=v33['FN'](t32,'classify_rows');s32=ast.get_source_segment(v32src,c32) or ''
    if 'canReachInsertion' not in s32 or 'acceptedReturnCanReachGuardedSequence' not in s32:raise RuntimeError('V34 exact V32 negative source drift')
    out['exactV32Authoritative0Distinct1NegativeFixture']={'observedFrozenOutcome':V32_REFUSAL,'classifyRowsSourceSha256':H(s32.encode()),'classifyRowsAstSha256':H(ast.dump(c32,include_attributes=False).encode())}
    a,d=classify_repaired(rows,specs,drop_ast);ar,dr=classify_repaired(list(reversed(copy.deepcopy(rows))),specs,drop_ast)
    if (a['sourceSha256'],d['sourceSha256'])!=(ar['sourceSha256'],dr['sourceSha256']):raise RuntimeError('V34 source-order invariance failed')
    out['sourceOrderInvariant']=True
    ao,do=classify_repaired(rows,specs,drop_ast,False);ax,dx=classify_repaired(rows,specs,drop_ast,True)
    if (ao['sourceSha256'],do['sourceSha256'])!=(ax['sourceSha256'],dx['sourceSha256']):raise RuntimeError('V34 predicate-evaluation-order invariance failed')
    out['predicateEvaluationOrderInvariant']=True
    if not fixture_fail(classify_repaired,[copy.deepcopy(auth),copy.deepcopy(auth)],specs,drop_ast):raise RuntimeError('V34 duplicate-authoritative fixture did not fail')
    out['duplicateAuthoritativeFatal']=True
    plausible=copy.deepcopy(distinct);plausible['controlLineage']=copy.deepcopy(auth['controlLineage']);plausible['dataLineage']=copy.deepcopy(auth['dataLineage'])
    if not fixture_fail(classify_repaired,[copy.deepcopy(auth),plausible],specs,drop_ast):raise RuntimeError('V34 both-plausible fixture did not fail')
    out['bothPlausibleFatal']=True
    if not fixture_fail(classify_repaired,[],specs,drop_ast):raise RuntimeError('V34 zero fixture did not fail')
    out['zeroFatal']=True
    if auth['dataLineage']['guardedSequenceCanReachInsertionByValue']:raise RuntimeError('V34 authoritative-control-without-RHS positive drift')
    out['authoritativeControlWithoutRhsPositive']=True
    fake=copy.deepcopy(auth);fake['controlLineage']['controlsInsertion']=False;fake['dataLineage']['guardedSequenceCanReachInsertionByValue']=True
    if not fixture_fail(classify_repaired,[fake,copy.deepcopy(distinct)],specs,drop_ast):raise RuntimeError('V34 value-dependency-without-control negative did not fail')
    out['valueDependencyWithoutControlNegative']=True
    len_form=copy.deepcopy(auth);count_form=copy.deepcopy(auth);len_form['cardinalityRepresentation']='len(sequence)';count_form['cardinalityRepresentation']='producer.count(match)'
    la,ld=classify_repaired([len_form,copy.deepcopy(distinct)],specs,drop_ast);ca,cd=classify_repaired([count_form,copy.deepcopy(distinct)],specs,drop_ast)
    if la['sourceSha256']!=ca['sourceSha256'] or ld['sourceSha256']!=cd['sourceSha256']:raise RuntimeError('V34 count-vs-len representation equivalence failed')
    out['countVsLenRepresentationEquivalent']=True
    noise="# len(nodes) != 1\nT='len(nodes2) != 1'\ndef x():\n    return T\n"
    if any(isinstance(x,ast.Compare) for x in ast.walk(ast.parse(noise))):raise RuntimeError('V34 comments/templates/noise unexpectedly executable')
    out['commentsTemplatesNoiseCannotSatisfy']=True
    return out

def proof(v4,v5):
    v33b,v33src,v33=load_v33();v32b=file_bytes('V32_FROZEN_REVIEWER',V32B,'V32 reviewer');v32src=v32b.decode()
    v17b=file_bytes('V17_FROZEN_REVIEWER',V17B,'V17 reviewer');v17,tr=v33['dv'](v17b)
    if H(v17.encode())!=P17:raise RuntimeError('V34 reconstructed V17 payload SHA drift')
    WT(A('--v34-v17-source-out'),v17)
    specs,classifier=predicate_specs(v33src,v33);rows,frozen=build_rows(v17,v33,tr)
    frozen['v33ReviewerBlobSha1']=B(v33b);frozen['v33ReviewerSha256']=H(v33b);frozen['v33Classifier']=classifier
    frozen['v17DecodedSourceSha256']=H(v17.encode());frozen['v17DecodedSourceUtf8ByteLength']=len(v17.encode());frozen['v17DecodedAstSha256']=H(ast.dump(ast.parse(v17),include_attributes=True).encode())
    decision=table(rows,specs)
    forensic={'schemaVersion':1,'status':'V34_FORENSIC_TABLE_FROZEN_BEFORE_REPAIR','frozen':frozen,'candidatePredicateDecisionTable':decision,
        'candidateCount':len(rows),'candidateIdentities':sorted(r['sourceSha256'] for r in rows),'scienceFalse':True}
    W(A('--v34-forensic-table-out'),forensic)
    if frozen['reachableSideEffectOperationsInventoriedNotExecuted']:raise RuntimeError('V34 side-effect freedom unproven for frozen V17 provenance surface')
    auth,distinct=semantic_anchors(rows);diagnosis,drop_ast=repair_diagnosis(rows,specs,auth,distinct)
    ra,rd=classify_repaired(rows,specs,drop_ast)
    if ra['sourceSha256']!=auth['sourceSha256'] or rd['sourceSha256']!=distinct['sourceSha256']:raise RuntimeError('V34 repaired classifier diverges from independent semantic anchors')
    m=json.loads(Path(v4).read_text());fx=fixtures(v33,v32src,m,rows,specs,auth,distinct,drop_ast,frozen)
    W(A('--v34-forensic-proof-out'),{'status':'PASS_V34_PREACTUAL_UNIQUE_V33_CLASSIFIER_PREDICATE_REPAIR','diagnosis':diagnosis,'authoritativeGuard':auth,'distinctGuard':distinct,'fixtures':fx,'scienceFalse':True})
    v30src=file_bytes('V30_FROZEN_REVIEWER',V30B,'V30 reviewer').decode();sc,br=v33['patch'](v30src,auth,distinct);old=list(sys.argv)
    try:
        sys.argv=[old[0],'--v30-proof-only','--v4-metadata',v4,'--v5-metadata',v5]
        for x,y in [('--v34-v30-forensic-out','--v30-forensic-proof-out'),('--v34-v30-bridge-out','--v30-bridge-proof-out'),('--v34-v30-static-bridge-out','--v30-v29-static-bridge-out'),('--v34-downstream-proof-out','--v30-downstream-proof-out'),('--v34-zero-runtime-proof-out','--v30-zero-runtime-proof-out'),('--v34-v5-proof-out','--v30-v5-proof-out'),('--v34-entrypoint-proof-out','--v30-entrypoint-proof-out')]:
            q=A0(old,x);sys.argv+=([y,q] if q else [])
        sc['PROOF'](v4,v5)
    finally:sys.argv=old
    W(A('--v34-bridge-proof-out'),{'status':'PASS_V34_NARROW_V33_CLASSIFIER_REPAIR_TO_ACCEPTED_V30_DOWNSTREAM','bridge':br,'scienceFalse':True})

def actual(v5):
    if os.getenv('V34_NONAUTH_ACTUAL')!='1':raise RuntimeError('V34 ACTUAL requires explicit NON_AUTH mode')
    s=file_bytes('V30_FROZEN_REVIEWER',V30B,'V30 reviewer').decode();sc={'__file__':str(HERE),'__name__':'_v34_v30_actual_'};exec(compile(s,'<v34-v30-actual>','exec'),sc,sc)
    old=os.getenv('V30_NONAUTH_ACTUAL');os.environ['V30_NONAUTH_ACTUAL']='1'
    try:sc['ACT'](v5)
    finally:
        if old is None:os.environ.pop('V30_NONAUTH_ACTUAL',None)
        else:os.environ['V30_NONAUTH_ACTUAL']=old

def main():
    try:
        v5=A('--v5-metadata')
        if not v5:raise RuntimeError('V34 frozen V5 metadata input missing')
        if '--v34-proof-only' in sys.argv or os.getenv('V34_PREACTUAL_ACTIVE')=='1':
            v4=A('--v4-metadata')
            if not v4:raise RuntimeError('V34 frozen V4 metadata input missing')
            proof(v4,v5)
        else:actual(v5)
    except BaseException as e:F(e);raise

if __name__=='__main__':main()
