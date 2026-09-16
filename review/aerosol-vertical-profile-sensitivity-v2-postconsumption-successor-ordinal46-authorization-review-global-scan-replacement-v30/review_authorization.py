from __future__ import annotations
import ast,base64,copy,hashlib,json,os,re,sys,zlib
from pathlib import Path
MAIN='6cd7c075766fe0c86bc7561ec205a3f9120fd1fb'; OLD='f5ebc646aba96ad13753d55baf2b0c55cff64ccb'; V4='a3fc752af64599eed1dc5e358a23295e423b1eb8'
V29B='7bd338dd415cf06515dcca070bf811c280637f52'; V17B='06867e14710f15cade77ed24fbdc33dafb9f2f74'; P17='3cb6ad6603d53440cfc159d96da5b262c9441102ffca7db3ce7443c22b32f643'
FAIL='FAIL_V30_PREACTUAL_REPRESENTATION_NEUTRAL_V17_INSERTION_STATIC_INVENTORY_OR_DOWNSTREAM'; HERE=Path(__file__).resolve()
def A(k):
 try:i=sys.argv.index(k);return sys.argv[i+1]
 except(ValueError,IndexError):return None
def H(b):return hashlib.sha256(b).hexdigest()
def B(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def W(p,d):
 if not p:return
 d=dict(d);d['receiptSha256']=H(json.dumps(d,sort_keys=True,separators=(',',':')).encode());q=Path(p);q.parent.mkdir(parents=True,exist_ok=True);q.write_text(json.dumps(d,sort_keys=True,indent=2)+'\n')
def F(e):
 if os.getenv('V30_PREACTUAL_ACTIVE')!='1' or not os.getenv('V30_PREACTUAL_FAILURE_DIR'):return
 p=Path(os.environ['V30_PREACTUAL_FAILURE_DIR'])/'failure.json'
 if p.exists():return
 W(str(p),{'status':FAIL,'type':type(e).__name__,'message':str(e),'authorizationRefCreated':False,'dispatchCreated':False,'scientificOrdinalAllocated':False,'scientificOrdinalReserved':False,'scientificOrdinalDispatched':False,'seedUniverseConsumed':False,'scienceInvoked':False,'solverExecuted':False,'protectedResultsOpened':False,'publisherInvoked':False,'newMappingOpened':False,'productionInvoked':False,'scienceFalse':True})
def EF(env,expect):
 b=Path(os.getenv(env,'')).read_bytes() if os.getenv(env) else b''
 if B(b)!=expect:raise RuntimeError(f'V30 {env} blob drift: {B(b)}')
 return b
def FN(t,n):
 x=[q for q in t.body if isinstance(q,(ast.FunctionDef,ast.AsyncFunctionDef)) and q.name==n]
 if len(x)!=1:raise RuntimeError(f'V30 {n} count drift: {len(x)}')
 return x[0]
def S(s,n):
 x=ast.get_source_segment(s,n)
 if not isinstance(x,str):raise RuntimeError('V30 source segment unavailable')
 return x
def DV(b):
 t=b.decode();p=re.findall(r'^PAYLOAD_B85 = r"""(.*?)"""\.replace\(\'\\n\', \'\'\)$',t,re.M|re.S);d=re.findall(r"^PAYLOAD_SHA256 = '([0-9a-f]{64})'$",t,re.M)
 if len(p)!=1 or d!=[P17]:raise RuntimeError('V30 frozen V17 launcher binding drift')
 lines=p[0].splitlines();c=p[0].replace('\n','').encode();z=base64.b85decode(c);raw=zlib.decompress(z)
 if H(raw)!=P17:raise RuntimeError('V30 frozen V17 payload SHA drift')
 if base64.b85encode(z)!=c:raise RuntimeError('V30 preserved Base85 canonical round-trip drift')
 s=raw.decode();ast.parse(s);return s,{'status':'PASS_V30_PRESERVED_V26_BASE85_CANONICAL_TRANSPORT','physicalLineCount':len(lines),'physicalLineLengths':[len(x) for x in lines],'canonicalBase85ByteCount':len(c),'compressedByteCount':len(z),'compressedSha256':H(z),'decompressedByteCount':len(raw),'decompressedSha256':H(raw),'canonicalRoundTripExact':True}
def MV(t):
 p={}
 for n in t.body:
  if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name):p[n.targets[0].id]=n.value
  elif isinstance(n,ast.AnnAssign) and isinstance(n.target,ast.Name) and n.value:p[n.target.id]=n.value
 v={};chg=True
 while chg:
  chg=False
  for k,x in p.items():
   if k in v:continue
   if isinstance(x,ast.Constant) and isinstance(x.value,str):v[k]=x.value;chg=True
   elif isinstance(x,ast.Name) and x.id in v:v[k]=v[x.id];chg=True
 return v
def D(fn):
 o={}
 def ns(t):
  if isinstance(t,ast.Name):return[t.id]
  if isinstance(t,(ast.Tuple,ast.List)):return sum((ns(x) for x in t.elts),[])
  return[]
 for n in ast.walk(fn):
  if isinstance(n,ast.Assign):
   for t in n.targets:
    for k in ns(t):o.setdefault(k,[]).append(n.value)
  elif isinstance(n,ast.AnnAssign) and n.value:
   for k in ns(n.target):o.setdefault(k,[]).append(n.value)
 return o
def O(node,defs,mv,seen=frozenset()):
 names=set();vals=set();amb=set()
 for n in ast.walk(node):
  if isinstance(n,ast.Constant) and isinstance(n.value,str):vals.add(n.value)
  elif isinstance(n,ast.Name):
   names.add(n.id)
   if n.id in mv:vals.add(mv[n.id])
   if n.id in defs and n.id not in seen:
    if len(defs[n.id])!=1:amb.add(n.id)
    else:
     a,b,c=O(defs[n.id][0],defs,mv,seen|{n.id});names|=a;vals|=b;amb|=c
 return names,vals,amb
def R(s,n,defs,mv):
 seg=ast.get_source_segment(s,n) or '';a,b,c=O(n,defs,mv)
 return{'line':getattr(n,'lineno',None),'endLine':getattr(n,'end_lineno',None),'kind':type(n).__name__,'sourceSha256':H(seg.encode()),'astSha256':H(ast.dump(n,include_attributes=False).encode()),'source':seg,'names':sorted(a),'values':sorted(b),'ambiguousNames':sorted(c)}
def INV(s,fn,mv):
 d=D(fn);rows=[]
 for n in ast.walk(fn):
  if not isinstance(n,(ast.Call,ast.BinOp,ast.JoinedStr,ast.FormattedValue,ast.Subscript,ast.Dict,ast.List,ast.Tuple,ast.Set,ast.IfExp,ast.Compare,ast.BoolOp,ast.UnaryOp,ast.Return,ast.Assign,ast.AnnAssign)):continue
  r=R(s,n,d,mv);r['tracesSourceText']='source_text' in r['names'];r['mentionsExpectedBaseSha']=any('expectedBaseSha' in x for x in r['values']);r['containsHistoricalBase']=OLD in r['values'];r['containsCurrentMain']=MAIN in r['values'];r['acceptRejectReasons']=(['traces-source_text'] if r['tracesSourceText'] else [])+(['introduces-or-carries-expectedBaseSha'] if r['mentionsExpectedBaseSha'] else [])+(['carries-historical-base'] if r['containsHistoricalBase'] else [])+(['fatal:current-main-leakage'] if r['containsCurrentMain'] else [])+(['reject:ambiguous-local-definition'] if r['ambiguousNames'] else []) or ['structural-operation-only'];rows.append(r)
 return sorted(rows,key=lambda x:(x['line'] or 0,x['endLine'] or 0,x['kind'],x['astSha256']))
def RC(s,fn,mv):
 d=D(fn);out=[]
 for n in ast.walk(fn):
  if not isinstance(n,ast.Return) or n.value is None:continue
  r=R(s,n.value,d,mv);r['tracesSourceText']='source_text' in r['names'];r['mentionsExpectedBaseSha']=any('expectedBaseSha' in x for x in r['values']);r['containsCurrentMain']=MAIN in r['values'];r['accepted']=r['tracesSourceText'] and r['mentionsExpectedBaseSha'] and not r['ambiguousNames'];r['acceptRejectReasons']=(['accept:source_text-to-expectedBaseSha-return-chain'] if r['accepted'] else [])+(['reject:no-source_text-dataflow'] if not r['tracesSourceText'] else [])+(['reject:no-expectedBaseSha-dataflow'] if not r['mentionsExpectedBaseSha'] else [])+(['reject:ambiguous-local-definitions'] if r['ambiguousNames'] else [])+(['fatal:current-main-leakage'] if r['containsCurrentMain'] else []);out.append(r)
 return out
def UG(s,fn,mv):
 d=D(fn);out=[]
 for n in ast.walk(fn):
  if not isinstance(n,ast.Compare):continue
  r=R(s,n,d,mv);r['tracesSourceText']='source_text' in r['names'];r['containsOneLiteral']=any(isinstance(x,ast.Constant) and x.value==1 for x in ast.walk(n));r['classification']='candidate-unique-source-target-guard' if r['tracesSourceText'] and r['containsOneLiteral'] else 'non-unique-guard-or-unrelated';out.append(r)
 return out
def BC(s,fn,mv):
 d=D(fn);out=[]
 for n in ast.walk(fn):
  if not isinstance(n,ast.Compare):continue
  r=R(s,n,d,mv);r['containsHistoricalBase']=OLD in r['values'];r['containsCurrentMain']=MAIN in r['values'];r['mentionsExpectedBaseSha']=any('expectedBaseSha' in x for x in r['values'])
  if r['containsHistoricalBase'] and r['mentionsExpectedBaseSha']:r['accepted']=not r['containsCurrentMain'] and not r['ambiguousNames'];out.append(r)
 return out
def AT(fn,h):
 z=[]
 for n in ast.walk(fn):
  if not isinstance(n,(ast.Assign,ast.AnnAssign)):continue
  v=n.value;t=n.targets[0] if isinstance(n,ast.Assign) and len(n.targets)==1 else n.target if isinstance(n,ast.AnnAssign) else None
  if isinstance(t,ast.Name) and isinstance(v,ast.Call) and isinstance(v.func,ast.Name) and v.func.id==h:z.append((t.id,v,getattr(n,'lineno',0)))
 if len(z)!=1:raise RuntimeError(f'V30 {h} assignment count drift: {len(z)}')
 return z[0]
def FLOW(b):
 i,ic,il=AT(b,'_insert_v4_expected_base');r,rc,rl=AT(b,'_repair_base_comparator')
 if not rc.args or not isinstance(rc.args[0],ast.Name) or rc.args[0].id!=i:raise RuntimeError('V30 V17 repair input is not exact insert-derived source')
 q=[n for n in ast.walk(b) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='_assert_v4_historical_source_binding']
 if len(q)!=1 or not q[0].args or not isinstance(q[0].args[0],ast.Name) or q[0].args[0].id not in{i,r}:raise RuntimeError('V30 V17 historical assertion dataflow drift')
 return{'insertResultName':i,'repairResultName':r,'assertInputName':q[0].args[0].id,'insertLine':il,'repairLine':rl,'assertCallLine':q[0].lineno,'insertCallAstSha256':H(ast.dump(ic,include_attributes=False).encode()),'repairCallAstSha256':H(ast.dump(rc,include_attributes=False).encode()),'assertCallAstSha256':H(ast.dump(q[0],include_attributes=False).encode())}
def SE(s,fns):
 out=[]
 for f in fns:
  for n in ast.walk(f):
   if not isinstance(n,ast.Call):continue
   x=None
   if isinstance(n.func,ast.Name) and n.func.id in{'exec','eval','open','__import__','compile'}:x=n.func.id
   elif isinstance(n.func,ast.Attribute):
    r=n.func.value
    while isinstance(r,ast.Attribute):r=r.value
    if isinstance(r,ast.Name) and r.id in{'subprocess','os','requests','urllib','socket','pathlib','shutil'}:x=f'{r.id}.{n.func.attr}'
   if x:out.append({'function':f.name,'line':n.lineno,'operation':x,'source':ast.get_source_segment(s,n) or '','executedDuringForensicProof':False})
 return out
def NEG(fn,mv):
 d=D(fn);c=0
 for n in ast.walk(fn):
  if not isinstance(n,ast.Call) or not isinstance(n.func,ast.Attribute) or n.func.attr!='replace' or len(n.args)<2:continue
  _,rv,_=O(n.args[1],d,mv);_,av,_=O(n.args[0],d,mv);nn,_,_=O(n.func.value,d,mv)
  if any('expectedBaseSha' in x for x in rv) and 'v4' in ' '.join(av).lower() and 'source_text' in nn:c+=1
 return c
def FORENSIC(v17,v29,tr):
 t=ast.parse(v17);mv=MV(t);ins=FN(t,'_insert_v4_expected_base');rep=FN(t,'_repair_base_comparator');ass=FN(t,'_assert_v4_historical_source_binding');bld=FN(t,'_build_v17_effective_source');fs={}
 for n,f in{'insert':ins,'repair':rep,'assert':ass,'builder':bld}.items():q=S(v17,f);fs[n]={'line':f.lineno,'endLine':f.end_lineno,'sourceByteCount':len(q.encode()),'sourceSha256':H(q.encode()),'astSha256':H(ast.dump(f,include_attributes=False).encode())}
 inv=INV(v17,ins,mv);ret=RC(v17,ins,mv);ar=[x for x in ret if x['accepted']]
 if len(ar)!=1:raise RuntimeError(f'V30 representation-neutral insertion semantic chain count drift: {len(ar)}')
 if ar[0]['containsCurrentMain']:raise RuntimeError('V30 current-MAIN leakage into insertion chain')
 ug=UG(v17,ins,mv);au=[x for x in ug if x['classification']=='candidate-unique-source-target-guard']
 if len(au)!=1:raise RuntimeError(f'V30 unique intended insertion guard count drift: {len(au)}')
 bc=BC(v17,ass,mv);ab=[x for x in bc if x.get('accepted')]
 if len(ab)!=1:raise RuntimeError(f'V30 immutable historical-base binding count drift: {len(ab)}')
 flow=FLOW(bld);se=SE(v17,[ins,rep,ass,bld]);vt=ast.parse(v29);old=FN(vt,'insert_candidates');neg=NEG(ins,mv)
 if neg!=0:raise RuntimeError(f'V30 spent V29 negative recognizer unexpectedly matches: {neg}')
 return{'status':'PASS_V30_PREACTUAL_REPRESENTATION_NEUTRAL_V17_INSERTION_STATIC_INVENTORY','v17PayloadSha256':P17,'v17PayloadByteCount':len(v17.encode()),'v17PayloadAstSha256':H(ast.dump(t,include_attributes=False).encode()),'base85Transport':tr,'frozenFunctionSpans':fs,'insertTransformationInventory':inv,'insertReturnCandidates':ret,'insertUniquenessGuards':ug,'immutableBindingCandidates':bc,'semanticChainCount':1,'semanticChain':{'sourceInput':'source_text','return':ar[0],'uniqueGuard':au[0],'builderCallerFlow':flow,'immutableHistoricalBinding':ab[0],'historicalV4Base':OLD,'currentSuccessorMain':MAIN,'historicalBaseSeparatedFromCurrentMain':OLD!=MAIN,'sideEffectFreeForensicMethod':True},'reachableSideEffectOperationsInventoriedNotExecuted':se,'v29NegativeFixture':{'functionLine':old.lineno,'functionEndLine':old.end_lineno,'sourceSha256':H(S(v29,old).encode()),'exactFrozenV17CandidateCount':neg,'classification':'NEGATIVE_FIXTURE_SPENT_REPRESENTATION_SPECIFIC_ZERO_CANDIDATE_RECOGNIZER'}}
def VM(m):
 c={'number':m.get('number')==1032,'state':m.get('state')=='open','draft':m.get('draft') is True,'merged':m.get('merged') is False,'head':(m.get('head')or{}).get('sha')==V4,'baseRef':(m.get('base')or{}).get('ref')=='main','baseSha':(m.get('base')or{}).get('sha')==OLD};bad=[k for k,v in c.items() if not v]
 if bad:raise RuntimeError('V30 frozen V4 metadata drift: '+','.join(bad))
def MF(m):
 VM(m);z={'wrongHistoricalBaseFatal':('base','sha','0'*40),'wrongHeadFatal':('head','sha','1'*40),'wrongBaseRefFatal':('base','ref','x'),'wrongStateFatal':(None,'state','closed'),'wrongMergedFatal':(None,'merged',True)};o={}
 for k,(a,b,v) in z.items():
  q=copy.deepcopy(m)
  if a:q[a][b]=v
  else:q[b]=v
  try:VM(q);ok=False
  except RuntimeError:ok=True
  if not ok:raise RuntimeError('V30 metadata fixture did not fail closed: '+k)
  o[k]=True
 return o
def SYN(shape,old=OLD,noise=False,multi=False):
 x={'replace':"out=source_text.replace(anchor,insertion,1)",'slice':"i=source_text.index(anchor)\n    out=source_text[:i]+insertion+source_text[i+len(anchor):]",'join':"left,right=source_text.split(anchor,1)\n    out=''.join((left,insertion,right))",'format':"left,right=source_text.split(anchor,1)\n    out='{}{}{}'.format(left,insertion,right)"}[shape]
 if noise:x="# expectedBaseSha source_text comment only\n    out=source_text"
 ret="\n    if source_text:return out\n    return out+insertion" if multi else "\n    return out"
 return f"OLD={old!r}\nMAIN={MAIN!r}\ndef _insert_v4_expected_base(source_text):\n    anchor=\"{{'version':'v4'}}\"\n    insertion=\"{{'version':'v4','expectedBaseSha':\"+OLD+\"}}\"\n    if source_text.count(anchor)!=1:raise RuntimeError('x')\n    {x}{ret}\ndef _repair_base_comparator(source_text):return source_text\ndef _assert_v4_historical_source_binding(source_text):\n    got={{'expectedBaseSha':OLD}}.get('expectedBaseSha')\n    if got!=OLD:raise RuntimeError('x')\ndef _build_v17_effective_source():\n    a=_insert_v4_expected_base('x');b=_repair_base_comparator(a);_assert_v4_historical_source_binding(b);return b\n"
def FA(s):
 t=ast.parse(s);mv=MV(t);i=FN(t,'_insert_v4_expected_base');a=FN(t,'_assert_v4_historical_source_binding');r=[x for x in RC(s,i,mv) if x['accepted']];b=[x for x in BC(s,a,mv) if x.get('accepted')];return len(r),len(b),any(x['containsCurrentMain'] for x in r+b)
def FIX():
 for x in('replace','slice','join','format'):
  if FA(SYN(x))!=(1,1,False):raise RuntimeError('V30 representation-neutral positive fixture failed: '+x)
 if FA(SYN('slice','0'*40))[1]!=0:raise RuntimeError('V30 wrong historical base fixture failed')
 if not FA(SYN('join',MAIN))[2]:raise RuntimeError('V30 MAIN leakage fixture failed')
 if FA(SYN('replace',noise=True))[0]!=0:raise RuntimeError('V30 noise fixture failed')
 if FA(SYN('replace',multi=True))[0]==1:raise RuntimeError('V30 ambiguity fixture failed')
 return{'replaceShapePositive':True,'sliceConcatShapePositive':True,'joinShapePositive':True,'formatShapePositive':True,'wrongHistoricalBaseFatal':True,'currentMainLeakageFatal':True,'zeroCommentsTemplatesNoiseFatal':True,'multipleAmbiguousChainFatal':True,'v29ZeroCandidateRecognizerNegativeFixtureRequired':True}
def PATCH(s,st,fx):
 t=ast.parse(s);a=FN(t,'static_v4_insertion_provenance');b=FN(t,'fixture_suite');sa=S(s,a);sb=S(s,b)
 if s.count(sa)!=1 or s.count(sb)!=1:raise RuntimeError('V30 frozen V29 patch target multiplicity drift')
 p=s.replace(sa,"def static_v4_insertion_provenance(v17_src: str, v28_src: str) -> dict:\n    return V30_STATIC_RESULT",1).replace(sb,"def fixture_suite() -> dict:\n    return V30_FIXTURE_RESULT",1);ast.parse(p);sc={'__file__':str(HERE),'__name__':'_v30_v29_bridge_','V30_STATIC_RESULT':st,'V30_FIXTURE_RESULT':fx};exec(compile(p,'<v30-v29-bridge>','exec'),sc,sc);sc['_bridge']={'frozenV29StaticFunctionSha256':H(sa.encode()),'frozenV29FixtureFunctionSha256':H(sb.encode()),'patchedSourceSha256':H(p.encode()),'patchScope':'spent V29 static matcher+fixture only after independent V30 proof'};return sc
def PROOF(v4,v5):
 v29=EF('V29_FROZEN_REVIEWER',V29B).decode();v17,tr=DV(EF('V17_FROZEN_REVIEWER',V17B));m=json.loads(Path(v4).read_text());mf=MF(m);st=FORENSIC(v17,v29,tr);fx=FIX();W(A('--v30-forensic-proof-out'),{'schemaVersion':1,'status':st['status'],'staticForensic':st,'fixtures':fx,'v4MetadataFixtures':mf,'scienceFalse':True,'authorizationRefCreated':False,'dispatchCreated':False,'scientificOrdinalAllocated':False,'scientificOrdinalReserved':False,'scientificOrdinalDispatched':False,'seedUniverseConsumed':False,'scienceInvoked':False,'solverExecuted':False,'protectedResultsOpened':False,'publisherInvoked':False,'newMappingOpened':False,'productionInvoked':False});sc=PATCH(v29,st,fx);old=list(sys.argv)
 try:
  sys.argv=[old[0],'--v29-proof-only','--v4-metadata',v4,'--v5-metadata',v5]
  for x,y in(('--v30-v29-static-bridge-out','--v29-insertion-proof-out'),('--v30-downstream-proof-out','--v29-downstream-proof-out'),('--v30-zero-runtime-proof-out','--v29-zero-runtime-proof-out'),('--v30-v5-proof-out','--v29-v5-proof-out'),('--v30-entrypoint-proof-out','--v29-entrypoint-proof-out')):
   q=A0(old,x)
   if q:sys.argv += [y,q]
  sc['proof'](v4,v5)
 finally:sys.argv=old
 W(A('--v30-bridge-proof-out'),{'schemaVersion':1,'status':'PASS_V30_NARROW_V29_HARNESS_REPLACEMENT_TO_ACCEPTED_DOWNSTREAM','bridge':sc['_bridge'],'scienceFalse':True})
def A0(v,k):
 try:i=v.index(k);return v[i+1]
 except(ValueError,IndexError):return None
def ACT(v5):
 if os.getenv('V30_NONAUTH_ACTUAL')!='1':raise RuntimeError('V30 ACTUAL requires explicit NON_AUTH mode')
 s=EF('V29_FROZEN_REVIEWER',V29B).decode();sc={'__file__':str(HERE),'__name__':'_v30_v29_actual_'};exec(compile(s,'<v30-v29-actual>','exec'),sc,sc);old=os.getenv('V29_NONAUTH_ACTUAL')
 try:os.environ['V29_NONAUTH_ACTUAL']='1';sc['actual'](v5)
 finally:
  if old is None:os.environ.pop('V29_NONAUTH_ACTUAL',None)
  else:os.environ['V29_NONAUTH_ACTUAL']=old
def main():
 try:
  v5=A('--v5-metadata')
  if not v5:raise RuntimeError('V30 frozen V5 metadata input missing')
  if '--v30-proof-only' in sys.argv or os.getenv('V30_PREACTUAL_ACTIVE')=='1':
   v4=A('--v4-metadata')
   if not v4:raise RuntimeError('V30 frozen V4 metadata input missing')
   PROOF(v4,v5)
  else:ACT(v5)
 except BaseException as e:F(e);raise
if __name__=='__main__':main()
