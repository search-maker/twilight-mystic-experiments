from __future__ import annotations
import ast,base64,copy,hashlib,json,os,re,sys,zlib
from pathlib import Path

B={'V26':'3fb03fb408897464b1be3ebd67b67b6297235cbd','V25':'0d5fae5c74eb6ab2e9afccb75559e91b5870fa5c','V24':'e4d306e01f76cc4199364bcd9d6d1a1dbffabf52','V23':'52dd4af0f78e7d8418669d98562a77584bc7ab31','V22':'98fe1ca468a44ad385005111f38dc48c89a08b9e','V17':'06867e14710f15cade77ed24fbdc33dafb9f2f74'}
MAIN='6cd7c075766fe0c86bc7561ec205a3f9120fd1fb'; V4='a3fc752af64599eed1dc5e358a23295e423b1eb8'; OLD='f5ebc646aba96ad13753d55baf2b0c55cff64ccb'; V5='0d7ad7030aacc1c34bca93fef6c02fd7dcf776c2'; V5BR='review/avps-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v5-20260910'
P25='e99dcdbb408db224f13411cf3fa2ba205a36fe3d768ca8176538d10ea08a86a8'; C25='9a2f6b5639c91ca89082ff92b0e0b0cb5b649e75f2dab16917bf4b2627283f2a'; P17='3cb6ad6603d53440cfc159d96da5b262c9441102ffca7db3ce7443c22b32f643'
STATUS='PASS_V27_PREACTUAL_STATIC_V4_RECOVERY_WITH_DOWNSTREAM_BLOCKER'; FAIL='FAIL_V27_PREACTUAL_STATIC_DATAFLOW_DOWNSTREAM_BLOCKER'; MSG='V27 static recovery proves V25 projection has no string-argument path to the local V4 comparator and V5 expectedBaseSha is ignored by the accepted V17 non-V4 comparator'

def arg(k):
    try:i=sys.argv.index(k);return sys.argv[i+1]
    except (ValueError,IndexError):return None

def blob(x):return hashlib.sha1(b'blob '+str(len(x)).encode()+b'\0'+x).hexdigest()
def sha(x):return hashlib.sha256(x).hexdigest()
def seg(t,n):
    s=ast.get_source_segment(t,n)
    if not s:raise RuntimeError('source segment unavailable')
    return s

def bound(k):
    p=os.environ.get(k+'_FROZEN_REVIEWER',''); x=Path(p).read_bytes() if p else b''
    if blob(x)!=B[k]:raise RuntimeError(f'V27 {k} blob drift: {blob(x)}')
    return x

def fn(tree,name):
    q=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==name]
    if len(q)!=1:raise RuntimeError(f'V27 {name} count {len(q)}')
    return q[0]
def write(path,p):
    if not path:return
    q=dict(p); raw=json.dumps(q,sort_keys=True,separators=(',',':')).encode(); q['receiptSha256']=sha(raw); Path(path).parent.mkdir(parents=True,exist_ok=True); Path(path).write_text(json.dumps(q,sort_keys=True,indent=2)+'\n')
def failure(e):
    d=os.environ.get('V27_PREACTUAL_FAILURE_DIR')
    if os.environ.get('V27_PREACTUAL_ACTIVE')!='1' or not d:return
    p=Path(d)/'failure.json'
    if not p.exists():write(str(p),{'status':FAIL,'type':type(e).__name__,'message':str(e),'authorizationRefCreated':False,'dispatchCreated':False,'scientificOrdinalAllocated':False,'scientificOrdinalReserved':False,'scientificOrdinalDispatched':False,'seedUniverseConsumed':False,'scienceInvoked':False,'solverExecuted':False,'protectedResultsOpened':False,'publisherInvoked':False,'newMappingOpened':False,'productionInvoked':False,'scienceFalse':True})

def payload25(x):
    t=x.decode(); m=re.findall(r'^PAYLOAD_SHA256 = [\'\"]([0-9a-f]{64})[\'\"]$',t,re.M)
    if m!=[P25]:raise RuntimeError('V27 V25 payload SHA binding drift')
    q=re.findall(r'^PAYLOAD_B85 = r"""(.*?)"""$',t,re.M|re.S)
    if len(q)!=1:raise RuntimeError('V27 V25 Base85 block drift')
    lines=q[0].split('\n')
    if len(lines)!=161 or len(lines[0])!=72 or any(not z for z in lines):raise RuntimeError('V27 V25 Base85 physical drift')
    refusal='';
    try:base64.b85decode(q[0].encode())
    except ValueError as e:refusal=str(e)
    if refusal!='bad base85 character at position 72':raise RuntimeError('V27 V25 multiline refusal drift')
    enc=''.join(lines); comp=base64.b85decode(enc.encode())
    if sha(comp)!=C25 or base64.b85encode(comp).decode()!=enc:raise RuntimeError('V27 V25 canonical transport drift')
    raw=zlib.decompress(comp)
    if sha(raw)!=P25:raise RuntimeError('V27 V25 payload drift')
    ast.parse(raw.decode())
    return raw,{'status':'PASS_V26_PREACTUAL_BASE85_CANONICAL_TRANSPORT','physicalLineCount':161,'firstPhysicalLineLength':72,'canonicalCompressedSha256':C25,'decompressedSha256':P25,'directMultilineDecodeRefusal':refusal,'serializerRoundTripExact':True}
def payload17(x):
    t=x.decode(); q=re.findall(r'^PAYLOAD_B85 = r"""(.*?)"""\.replace\(\'\\n\', \'\'\)$',t,re.M|re.S); m=re.findall(r"^PAYLOAD_SHA256 = '([0-9a-f]{64})'$",t,re.M)
    if len(q)!=1 or m!=[P17]:raise RuntimeError('V27 V17 launcher binding drift')
    raw=zlib.decompress(base64.b85decode(q[0].replace('\n','').encode()))
    if sha(raw)!=P17:raise RuntimeError('V27 V17 payload drift')
    ast.parse(raw.decode());return raw

def meta4(m):
    h=m.get('head') or {}; b=m.get('base') or {}
    if int(m.get('number') or 0)!=1032 or m.get('state')!='open' or m.get('draft') is not True or m.get('merged_at') is not None or h.get('sha')!=V4 or b.get('ref')!='main' or b.get('sha')!=OLD or b.get('sha')==MAIN:raise RuntimeError('V27 frozen V4 metadata drift')
def meta5(m):
    h=m.get('head') or {}; b=m.get('base') or {}
    if int(m.get('number') or 0)!=1033 or m.get('state')!='open' or m.get('draft') is not True or m.get('merged_at') is not None or h.get('sha')!=V5 or h.get('ref')!=V5BR or b.get('ref')!='main' or b.get('sha')!=OLD or b.get('sha')==MAIN:raise RuntimeError('V27 frozen V5 metadata drift')
def fixtures(m):
    meta4(m); out={}
    def bad(label,mut):
        x=copy.deepcopy(m);mut(x)
        try:meta4(x)
        except RuntimeError:out[label]=True;return
        raise RuntimeError('V27 negative metadata fixture passed '+label)
    bad('wrongHistoricalBaseFatal',lambda x:x['base'].__setitem__('sha','0'*40));bad('wrongHeadFatal',lambda x:x['head'].__setitem__('sha','0'*40));bad('wrongBaseRefFatal',lambda x:x['base'].__setitem__('ref','wrong'));bad('wrongStateFatal',lambda x:x.__setitem__('state','closed'));bad('mergedFatal',lambda x:x.__setitem__('merged_at','x'));bad('currentMainLeakageFatal',lambda x:x['base'].__setitem__('sha',MAIN));out['exactFrozenV4MetadataPasses']=True;return out

def local_candidate(src):
    tr=ast.parse(src); hits=0
    for f in [n for n in tr.body if isinstance(n,ast.FunctionDef) and n.name=='_validate_spent_bundle']:
        s=seg(src,f)
        need=("if spec.get('version') == 'v4':","_spent_expected_base_sha = spec.get('expectedBaseSha')","else:","_spent_expected_base_sha = MAIN","pbase.get('sha') == _spent_expected_base_sha")
        if all(z in s for z in need):hits+=1
    return hits
def semantic_fixtures():
    s="""def _validate_spent_bundle(spec,pbase):\n    if spec.get('version') == 'v4':\n        _spent_expected_base_sha = spec.get('expectedBaseSha')\n    else:\n        _spent_expected_base_sha = MAIN\n    return pbase.get('sha') == _spent_expected_base_sha and pbase.get('ref') == 'main'\n"""
    if local_candidate(s)!=1 or local_candidate(s.replace("_spent_expected_base_sha = spec.get('expectedBaseSha')","_spent_expected_base_sha = MAIN",1))!=0 or local_candidate(s+s)!=2 or local_candidate("# "+s.replace('\n','\n# '))!=0:raise RuntimeError('V27 semantic fixtures drift')
    return {'exactAcceptedSemanticPositive':True,'zeroSemanticCandidateFatal':True,'multipleSemanticCandidatesFatal':True,'commentsTemplatesNoiseIgnored':True,'currentMainLeakageFatal':True,'fixtureSha256':sha(s.encode())}

def proof(v4,v5):
    x26,x25,x24,x23,x22,x17=[bound(k) for k in ('V26','V25','V24','V23','V22','V17')]
    if 'PASS_V26_PREACTUAL_BASE85_CANONICAL_TRANSPORT' not in x26.decode():raise RuntimeError('V27 V26 transport proof surface drift')
    p25,transport=payload25(x25); p17=payload17(x17); t25=p25.decode(); t17=p17.decode(); t24=x24.decode();t23=x23.decode();t22=x22.decode()
    meta4(v4);meta5(v5); mf=fixtures(v4);sf=semantic_fixtures()
    tr17=ast.parse(t17); r=fn(tr17,'_repair_base_comparator'); a=fn(tr17,'_assert_v4_historical_source_binding'); b=fn(tr17,'_build_v17_effective_source'); rs=seg(t17,r);as_=seg(t17,a);bs=seg(t17,b)
    accepted=("if spec.get('version') == 'v4':","_spent_expected_base_sha = spec.get('expectedBaseSha')",f"req(_spent_expected_base_sha == '{OLD}', 'v4 historical creation-base binding drift')","_spent_expected_base_sha = MAIN","pbase.get('sha') == _spent_expected_base_sha")
    if any(z not in rs or z not in as_ for z in accepted):raise RuntimeError('V27 accepted V17 comparator/dataflow drift')
    if bs.count('_rbr_assignments(effective)')!=1:raise RuntimeError('V27 V17 injection anchor drift')
    parents={c:p for p in ast.walk(tr17) for c in ast.iter_child_nodes(p)}; calls=[]
    for n in ast.walk(tr17):
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='_build_v17_effective_source':
            q=n
            while q in parents and not isinstance(parents[q],(ast.FunctionDef,ast.AsyncFunctionDef)):q=parents[q]
            f=parents.get(q);calls.append({'line':n.lineno,'function':getattr(f,'name','<module>'),'argCount':len(n.args),'keywordCount':len(n.keywords)})
    if len(calls)!=2 or any(c['argCount'] or c['keywordCount'] for c in calls) or sorted(c['function'] for c in calls)!=['_run_proof_only','main']:raise RuntimeError('V27 V17 builder caller drift')
    f25=fn(ast.parse(t25),'_fault_matcher');c25=fn(ast.parse(t25),'_capture_baseline_mismatch');i25=fn(ast.parse(t25),'_insert_repair'); fs,cs,is_=seg(t25,f25),seg(t25,c25),seg(t25,i25)
    if any(z not in fs for z in ('immutable-base comparator count drift','_enclosing_function(node, parents)','callers.append')):raise RuntimeError('V27 V25 fault matcher drift')
    if any(z not in cs for z in ('exec(compile(builder','entry()','original(*new_args, **new_kwargs)',"os.environ['V25_PREACTUAL_FAILURE_DIR']")):raise RuntimeError('V27 V25 direct-probe drift')
    ra=[n for n in ast.parse(t25).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='REPAIR_HELPERS' for t in n.targets)]
    if len(ra)!=1 or not isinstance(ra[0].value,ast.Constant):raise RuntimeError('V27 V25 repair helper drift')
    rh=ra[0].value.value
    if any(z not in rh for z in ('enumerate(_args)','list(_kwargs.items())','_V25_ORIGINAL_IMMUTABLE_BASE_MATCHER(*_args, **_kwargs)')):raise RuntimeError('V27 V25 projection wrapper drift')
    if sum(c['argCount']+c['keywordCount'] for c in calls)!=0:raise RuntimeError('V27 projection opportunity drift')
    v23s=seg(t23,fn(ast.parse(t23),'_v5_patch_block'))
    if "spec', 'expectedBaseSha', 2" not in v23s or "_right.args[1].id != 'MAIN'" not in v23s or "expectedBaseSha': 'f5ebc646aba96ad13753d55baf2b0c55cff64ccb'" not in v23s:raise RuntimeError('V27 V23 matcher/patch drift')
    if '_spent_expected_base_sha =' in v23s:raise RuntimeError('V27 V23 patch unexpectedly contains accepted local comparator')
    s22=seg(t22,fn(ast.parse(t22),'_build_v22_builder_bytes'));s24=seg(t24,fn(ast.parse(t24),'_prepare_builder'))
    if any(z not in s22 for z in ('_generated_effective_rbr_call_stmt(lifted_tree)','block = _rebind_block(indent)',"patched = b''.join(lines[:index]) + block + b''.join(lines[index:])")):raise RuntimeError('V27 V22 injection provenance drift')
    if any(z not in s24 for z in ('def combined_rebind(indent: bytes)','extra = v5_patch_builder(indent)','return base + extra')):raise RuntimeError('V27 V24 injection provenance drift')
    recover=fn(tr17,'_recover_exact_v12_effective_source'); rec=seg(t17,recover)
    side=[]
    for n in ast.walk(recover):
        if isinstance(n,ast.Call):
            if isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=='subprocess':side.append(f'{n.lineno}:subprocess.{n.func.attr}')
            if isinstance(n.func,ast.Name) and n.func.id=='exec':side.append(f'{n.lineno}:exec')
    if not any('subprocess.run' in z for z in side) or not any(z.endswith(':exec') for z in side):raise RuntimeError('V27 old path side-effect inventory drift')
    if OLD==MAIN:raise RuntimeError('V27 historical/current base aliases')
    return {'schemaVersion':1,'status':STATUS,'causeV24CountZero':'V23/V24 matcher expects direct spec.get(expectedBaseSha, MAIN), while accepted V17 comparator uses local _spent_expected_base_sha selected by version branch','uniqueStaticV4Recovery':True,'semanticV4CandidateCount':1,'acceptedV4ExpectedBase':OLD,'currentMain':MAIN,'v4CurrentMainLeakage':False,'v17RepairFunctionLine':r.lineno,'v17RepairFunctionSha256':sha(rs.encode()),'v17AssertFunctionLine':a.lineno,'v17AssertFunctionSha256':sha(as_.encode()),'v17BuilderFunctionLine':b.lineno,'v17BuilderFunctionSha256':sha(bs.encode()),'v17BuilderCallers':calls,'v22InjectionFunctionSha256':sha(s22.encode()),'v24CombinedRebindFunctionSha256':sha(s24.encode()),'v25FaultMatcherFunctionSha256':sha(fs.encode()),'v25DirectProbeFunctionSha256':sha(cs.encode()),'v25RepairInsertionFunctionSha256':sha(is_.encode()),'oldDirectProbeReachableExternalRuntimeOperations':side,'oldDirectProbeNegativeFixture':True,'forensicProofExecutesRecoveredReviewerCode':False,'forensicProofInvokesRecoveredComparatorHelper':False,'forensicProofInvokesNetworkSubprocessProcessRuntimeProbe':False,'v25ProjectionWrapperStringArgumentOpportunityCount':0,'v25ProjectionWrapperCanReachLocalEffectiveComparator':False,'v5PatchAddsExpectedBaseSha':True,'v5PatchChangesAcceptedComparator':False,'v5ExpectedUnderAcceptedV17Dataflow':MAIN,'v5ActualFrozenHistoricalBase':OLD,'v5PatchSemanticallyEffective':False,'predictedV5RefusalAfterComparatorProofRepair':'v5 PR base drift','transport':transport,'metadataFixtures':mf,'semanticFixtures':sf,'commentsTemplatesNoiseCannotSatisfy':True,'zeroMultipleAmbiguousCandidatesFatal':True,'authorizationRefCreated':False,'dispatchCreated':False,'scientificOrdinalAllocated':False,'scientificOrdinalReserved':False,'scientificOrdinalDispatched':False,'seedUniverseConsumed':False,'scienceInvoked':False,'solverExecuted':False,'protectedResultsOpened':False,'publisherInvoked':False,'newMappingOpened':False,'productionInvoked':False,'scienceFalse':True}

def main():
    if '--v27-proof-only' not in sys.argv:raise RuntimeError('V27 PRE-ACTUAL forensic-only; ACTUAL forbidden until static proof is clean')
    try:
        p4,p5=arg('--v4-metadata'),arg('--v5-metadata')
        if not p4 or not p5:raise RuntimeError('V27 frozen metadata inputs missing')
        q=proof(json.loads(Path(p4).read_text()),json.loads(Path(p5).read_text()));write(arg('--v27-forensic-proof-out'),q);raise RuntimeError(MSG)
    except BaseException as e:failure(e);raise
if __name__=='__main__':main()
