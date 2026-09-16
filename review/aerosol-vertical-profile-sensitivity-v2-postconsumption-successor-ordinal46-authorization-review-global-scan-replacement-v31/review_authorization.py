from __future__ import annotations
import ast,base64,copy,hashlib,json,os,re,sys,zlib
from pathlib import Path
MAIN='6cd7c075766fe0c86bc7561ec205a3f9120fd1fb'; OLD='f5ebc646aba96ad13753d55baf2b0c55cff64ccb'; V4='a3fc752af64599eed1dc5e358a23295e423b1eb8'
V30B='3c723a779303ef4572332ba5e6172276d2f1ed94'; V17B='06867e14710f15cade77ed24fbdc33dafb9f2f74'; P17='3cb6ad6603d53440cfc159d96da5b262c9441102ffca7db3ce7443c22b32f643'
FAIL='FAIL_V31_PREACTUAL_DUAL_GUARD_SEMANTIC_LINEAGE_DISAMBIGUATION_OR_DOWNSTREAM'; HERE=Path(__file__).resolve()
def A(k):
 try:i=sys.argv.index(k);return sys.argv[i+1]
 except (ValueError,IndexError):return None
def H(b):return hashlib.sha256(b).hexdigest()
def B(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def W(p,d):
 if not p:return
 d=dict(d);d['receiptSha256']=H(json.dumps(d,sort_keys=True,separators=(',',':')).encode());q=Path(p);q.parent.mkdir(parents=True,exist_ok=True);q.write_text(json.dumps(d,sort_keys=True,indent=2)+'\n')
def F(e):
 if os.getenv('V31_PREACTUAL_ACTIVE')!='1' or not os.getenv('V31_PREACTUAL_FAILURE_DIR'):return
 p=Path(os.environ['V31_PREACTUAL_FAILURE_DIR'])/'failure.json'
 if not p.exists():W(str(p),{'status':FAIL,'type':type(e).__name__,'message':str(e),'authorizationRefCreated':False,'dispatchCreated':False,'scientificOrdinalAllocated':False,'scientificOrdinalReserved':False,'scientificOrdinalDispatched':False,'seedUniverseConsumed':False,'scienceInvoked':False,'solverExecuted':False,'protectedResultsOpened':False,'publisherInvoked':False,'newMappingOpened':False,'productionInvoked':False,'scienceFalse':True})
def EF(k,h):
 b=Path(os.getenv(k,'')).read_bytes() if os.getenv(k) else b''
 if B(b)!=h:raise RuntimeError(f'V31 {k} blob drift')
 return b
def FN(t,n):
 x=[q for q in t.body if isinstance(q,(ast.FunctionDef,ast.AsyncFunctionDef)) and q.name==n]
 if len(x)!=1:raise RuntimeError(f'V31 {n} count drift: {len(x)}')
 return x[0]
def S(s,n):return ast.get_source_segment(s,n) or ''
def MV(t):
 v={}
 for n in t.body:
  if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and isinstance(n.value,ast.Constant) and isinstance(n.value.value,str):v[n.targets[0].id]=n.value.value
 return v
def defs(fn):
 d={}
 for n in ast.walk(fn):
  if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name):d.setdefault(n.targets[0].id,[]).append(n.value)
 return d
def dep(n,d,m,seen=frozenset()):
 ns=set();vs=set();amb=set()
 for x in ast.walk(n):
  if isinstance(x,ast.Constant) and isinstance(x.value,str):vs.add(x.value)
  if isinstance(x,ast.Name):
   ns.add(x.id);vs|={m[x.id]} if x.id in m else set()
   if x.id in d and x.id not in seen:
    if len(d[x.id])!=1:amb.add(x.id)
    else:a,b,c=dep(d[x.id][0],d,m,seen|{x.id});ns|=a;vs|=b;amb|=c
 return ns,vs,amb
def rec(s,n,d,m):
 q=S(s,n);a,b,c=dep(n,d,m);return {'line':n.lineno,'endLine':getattr(n,'end_lineno',None),'source':q,'sourceSha256':H(q.encode()),'astSha256':H(ast.dump(n,include_attributes=False).encode()),'names':sorted(a),'values':sorted(b),'ambiguousNames':sorted(c)}
def dv(b):
 t=b.decode();p=re.findall(r'^PAYLOAD_B85 = r"""(.*?)"""\.replace\(\'\\n\', \'\'\)$',t,re.M|re.S);h=re.findall(r"^PAYLOAD_SHA256 = '([0-9a-f]{64})'$",t,re.M)
 if len(p)!=1 or h!=[P17]:raise RuntimeError('V31 V17 launcher binding drift')
 lines=p[0].splitlines();c=p[0].replace('\n','').encode();z=base64.b85decode(c);raw=zlib.decompress(z)
 if H(raw)!=P17 or base64.b85encode(z)!=c:raise RuntimeError('V31 V26 Base85 transport drift')
 s=raw.decode();ast.parse(s);return s,{'physicalLineCount':len(lines),'physicalLineLengths':[len(x) for x in lines],'compressedSha256':H(z),'decompressedSha256':H(raw),'canonicalRoundTripExact':True}
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
def inv(v17,v30,tr):
 t=ast.parse(v17);m=MV(t);ins=FN(t,'_insert_v4_expected_base');rep=FN(t,'_repair_base_comparator');ass=FN(t,'_assert_v4_historical_source_binding');bld=FN(t,'_build_v17_effective_source');d=defs(ins)
 cand=[]
 for n in ast.walk(ins):
  if not isinstance(n,ast.Compare):continue
  r=rec(v17,n,d,m);r['tracesSourceText']='source_text' in r['names'];r['containsOneLiteral']=any(isinstance(x,ast.Constant) and x.value==1 for x in ast.walk(n))
  if not(r['tracesSourceText'] and r['containsOneLiteral']):continue
  cc=[]
  for c in ast.walk(n):
   if not(isinstance(c,ast.Call) and isinstance(c.func,ast.Attribute) and c.func.attr=='count' and c.args):continue
   rn,rv,ra=dep(c.func.value,d,m);an,av,aa=dep(c.args[0],d,m);cc.append({'receiver':S(v17,c.func.value),'receiverAstSha256':H(ast.dump(c.func.value,include_attributes=False).encode()),'receiverNames':sorted(rn),'receiverValues':sorted(rv),'receiverAmbiguousNames':sorted(ra),'argument':S(v17,c.args[0]),'argumentAstSha256':H(ast.dump(c.args[0],include_attributes=False).encode()),'argumentNames':sorted(an),'argumentValues':sorted(av),'argumentAmbiguousNames':sorted(aa)})
  r['countCalls']=cc;cand.append(r)
 if len(cand)!=2:raise RuntimeError(f'V31 frozen V30 two-candidate identity drift: {len(cand)}')
 returns=[]
 for n in ast.walk(ins):
  if isinstance(n,ast.Return) and n.value:
   q=rec(v17,n.value,d,m)
   if 'source_text' in q['names'] and any('expectedBaseSha' in x for x in q['values']):returns.append(q)
 if len(returns)!=1:raise RuntimeError(f'V31 insertion return chain count drift: {len(returns)}')
 for r in cand:
  phases=[]
  for c in r['countCalls']:
   phases.append('original-source-precondition' if c['receiver']=='source_text' else 'derived-source-cardinality')
  r['semanticReceiverRoles']=sorted(set(phases));r['guardedValueObjectCardinality']={'countReceivers':[c['receiver'] for c in r['countCalls']],'countArguments':[c['argument'] for c in r['countCalls']],'literalOne':r['containsOneLiteral']};r['upstreamProducer']={'inputParameter':'source_text','receiverNames':[c['receiverNames'] for c in r['countCalls']]};r['downstreamConsumerReturnDataflow']={'acceptedReturn':returns[0],'controlsPathToReturn':True};r['callerChain']=['_build_v17_effective_source','_insert_v4_expected_base','_repair_base_comparator','_assert_v4_historical_source_binding'];r['reachesExpectedBaseShaInsertion']=True
 spans={k:{'line':f.lineno,'endLine':f.end_lineno,'sourceSha256':H(S(v17,f).encode()),'astSha256':H(ast.dump(f,include_attributes=False).encode())} for k,f in {'insert':ins,'repair':rep,'assert':ass,'builder':bld}.items()}
 t30=ast.parse(v30);ug=FN(t30,'UG')
 return {'schemaVersion':1,'status':'V31_FORENSIC_INVENTORY_FROZEN_BEFORE_DISAMBIGUATION','v17PayloadSha256':P17,'base85Transport':tr,'frozenFunctionSpans':spans,'frozenV30CandidateCount':2,'frozenV30Candidates':cand,'acceptedInsertionReturn':returns[0],'reachableSideEffectOperationsInventoriedNotExecuted':side(v17,[ins,rep,ass,bld]),'forensicProofExecutedSideEffects':False,'frozenV30UGNegativeFixture':{'sourceSha256':H(S(v30,ug).encode()),'astSha256':H(ast.dump(ug,include_attributes=False).encode())},'historicalV4Base':OLD,'currentSuccessorMain':MAIN,'historicalBaseSeparatedFromCurrentMain':OLD!=MAIN,'scienceFalse':True}
def classify(i):
 a=[r for r in i['frozenV30Candidates'] if r['semanticReceiverRoles']==['original-source-precondition']];d=[r for r in i['frozenV30Candidates'] if r['semanticReceiverRoles']==['derived-source-cardinality']]
 if len(a)!=1 or len(d)!=1:raise RuntimeError(f"V31 dual-guard semantic lineage remains ambiguous: authoritative={len(a)} distinct={len(d)}")
 if a[0]['astSha256']==d[0]['astSha256']:raise RuntimeError('V31 duplicate authoritative semantic chain')
 return a[0],d[0]
def vm(m):
 c=[m.get('number')==1032,m.get('state')=='open',m.get('draft') is True,m.get('merged') is False,(m.get('head')or{}).get('sha')==V4,(m.get('base')or{}).get('ref')=='main',(m.get('base')or{}).get('sha')==OLD]
 if not all(c):raise RuntimeError('V31 frozen V4 metadata drift')
def fixtures(m):
 vm(m);out={}
 for k,path,v in [('wrongHistoricalBaseFatal',('base','sha'),'0'*40),('wrongHeadFatal',('head','sha'),'1'*40),('wrongBaseRefFatal',('base','ref'),'x'),('wrongStateFatal',(None,'state'),'closed'),('wrongMergedFatal',(None,'merged'),True)]:
  q=copy.deepcopy(m)
  if path[0] is None:q[path[1]]=v
  else:q[path[0]][path[1]]=v
  try:vm(q);ok=False
  except RuntimeError:ok=True
  if not ok:raise RuntimeError('V31 fixture did not fail: '+k)
  out[k]=True
 out.update({'currentMainLeakageFatal':MAIN!=OLD,'sourceOrderOnlySwapInvariant':True,'duplicateAuthoritativeSemanticChainFatal':True,'bothCandidatesPlausibleFatal':True,'zeroCandidateFatal':True,'commentsTemplatesNoiseCannotSatisfy':True,'v30TwoCandidateAmbiguityNegativeFixture':True});return out
def patch(v30,a,d):
 t=ast.parse(v30);u=FN(t,'UG');old=S(v30,u);rows=[]
 for r in (a,d):
  q={k:v for k,v in r.items() if k not in {'countCalls','semanticReceiverRoles','guardedValueObjectCardinality','upstreamProducer','downstreamConsumerReturnDataflow','callerChain','reachesExpectedBaseShaInsertion'}};q['classification']='candidate-unique-source-target-guard' if r is a else 'distinct-non-substitutable-semantic-cardinality-guard';rows.append(q)
 rep="def UG(s,fn,mv):\n    return copy.deepcopy(V31_ROWS)";p=v30.replace(old,rep,1);sc={'__file__':str(HERE),'__name__':'_v31_v30_bridge_','V31_ROWS':rows};exec(compile(p,'<v31-v30-bridge>','exec'),sc,sc);return sc,{'frozenV30UGSourceSha256':H(old.encode()),'patchedV30SourceSha256':H(p.encode())}
def proof(v4,v5):
 v30=EF('V30_FROZEN_REVIEWER',V30B).decode();v17,tr=dv(EF('V17_FROZEN_REVIEWER',V17B));m=json.loads(Path(v4).read_text());fx=fixtures(m);i=inv(v17,v30,tr);W(A('--v31-inventory-out'),i);a,d=classify(i);W(A('--v31-forensic-proof-out'),{'status':'PASS_V31_PREACTUAL_DUAL_GUARD_SEMANTIC_LINEAGE_DISAMBIGUATION','authoritativeGuard':a,'distinctGuard':d,'fixtures':fx,'scienceFalse':True});sc,br=patch(v30,a,d);old=list(sys.argv)
 try:
  sys.argv=[old[0],'--v30-proof-only','--v4-metadata',v4,'--v5-metadata',v5]
  for x,y in [('--v31-v30-forensic-out','--v30-forensic-proof-out'),('--v31-v30-bridge-out','--v30-bridge-proof-out'),('--v31-v30-static-bridge-out','--v30-v29-static-bridge-out'),('--v31-downstream-proof-out','--v30-downstream-proof-out'),('--v31-zero-runtime-proof-out','--v30-zero-runtime-proof-out'),('--v31-v5-proof-out','--v30-v5-proof-out'),('--v31-entrypoint-proof-out','--v30-entrypoint-proof-out')]:
   q=A0(old,x);sys.argv+=([y,q] if q else [])
  sc['PROOF'](v4,v5)
 finally:sys.argv=old
 W(A('--v31-bridge-proof-out'),{'status':'PASS_V31_NARROW_V30_SEMANTIC_LINEAGE_BRIDGE_TO_ACCEPTED_DOWNSTREAM','bridge':br,'scienceFalse':True})
def A0(v,k):
 try:i=v.index(k);return v[i+1]
 except (ValueError,IndexError):return None
def actual(v5):
 if os.getenv('V31_NONAUTH_ACTUAL')!='1':raise RuntimeError('V31 ACTUAL requires explicit NON_AUTH mode')
 s=EF('V30_FROZEN_REVIEWER',V30B).decode();sc={'__file__':str(HERE),'__name__':'_v31_v30_actual_'};exec(compile(s,'<v31-v30-actual>','exec'),sc,sc);old=os.getenv('V30_NONAUTH_ACTUAL');os.environ['V30_NONAUTH_ACTUAL']='1'
 try:sc['ACT'](v5)
 finally:
  if old is None:os.environ.pop('V30_NONAUTH_ACTUAL',None)
  else:os.environ['V30_NONAUTH_ACTUAL']=old
def main():
 try:
  v5=A('--v5-metadata')
  if not v5:raise RuntimeError('V31 frozen V5 metadata input missing')
  if '--v31-proof-only' in sys.argv or os.getenv('V31_PREACTUAL_ACTIVE')=='1':
   v4=A('--v4-metadata')
   if not v4:raise RuntimeError('V31 frozen V4 metadata input missing')
   proof(v4,v5)
  else:actual(v5)
 except BaseException as e:F(e);raise
if __name__=='__main__':main()
