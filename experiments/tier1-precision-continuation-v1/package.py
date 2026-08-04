from __future__ import annotations
import hashlib,json,math
TARGET=.05; ACCEPT=.08; INITIAL_BLOCKS=2; MAX_TOTAL_BLOCKS=8; SEED_BASE=930000
class Refusal(RuntimeError): pass
def sha(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def classify(r):
 if not isinstance(r,(int,float)) or not math.isfinite(r) or r<0: raise Refusal('invalid RSEM')
 return 'PRECISION_TARGET_MET' if r<=TARGET else 'PRECISION_ACCEPTED' if r<=ACCEPT else 'ADAPTIVE_CONTINUATION_REQUIRED'
def validate_source(dataset,aggregate,audit,provenance):
 required={'geometryCount':48,'caseCount':96,'configuredMcPhotonsSum':6960000000,'blocksPerGeometry':2}
 if any(dataset.get(k)!=v for k,v in required.items()): raise Refusal('dataset contract changed')
 if aggregate.get('classification')!='BATCH_NUMERICALLY_COMPLETE' or aggregate.get('caseCountCompleted')!=96: raise Refusal('aggregate failed')
 if audit.get('status')!='PASSED' or audit.get('caseResultCount')!=96: raise Refusal('audit failed')
 if provenance.get('runAttempt')!=1 or provenance.get('artifactsComplete') is not True or provenance.get('hashesValid') is not True or provenance.get('seedsValid') is not True or provenance.get('photonAccountingValid') is not True: raise Refusal('provenance failed')
 rows=dataset.get('records')
 if not isinstance(rows,list) or len(rows)!=48: raise Refusal('record count changed')
 return rows
def build(dataset,aggregate,audit,provenance):
 rows=validate_source(dataset,aggregate,audit,provenance); used={c['seed'] for c in dataset.get('cases',[]) if isinstance(c,dict) and 'seed' in c}; cases=[]; points=[]; ordinal=0
 for row in sorted(rows,key=lambda x:x['geometryId']):
  gid=row['geometryId']; r=float(row['statistics']['relativeStandardErrorOfMean']); c=classify(r); add=0
  if c=='ADAPTIVE_CONTINUATION_REQUIRED': add=max(1,min(MAX_TOTAL_BLOCKS-INITIAL_BLOCKS,math.ceil(INITIAL_BLOCKS*(r/TARGET)**2)-INITIAL_BLOCKS))
  fresh=[]
  for block in range(INITIAL_BLOCKS+1,INITIAL_BLOCKS+add+1):
   ordinal+=1; seed=SEED_BASE+ordinal
   if seed in used: raise Refusal('seed reuse')
   used.add(seed); fresh.append(seed); cases.append({'caseId':f'{gid}-continuation-b{block}','groupId':gid,'block':block,'seed':seed,'role':row['role'],'photonHistories':row['statistics'].get('photonHistoriesPerBlock'),'proposalOnly':True})
  points.append({'geometryId':gid,'sourceClassification':c,'sourceRsem':r,'additionalBlockCount':add,'maximumTotalBlocks':MAX_TOTAL_BLOCKS,'freshSeeds':fresh})
 return {'schemaVersion':1,'stageId':'tier1-precision-continuation-proposal-v1','status':'PROPOSAL_ONLY_NOT_AUTHORIZATION','proposalOnly':True,'scientificExecution':False,'automaticDispatch':False,'githubRerunAllowed':False,'thresholds':{'target':TARGET,'acceptedMaximum':ACCEPT},'hardCapTotalBlocks':MAX_TOTAL_BLOCKS,'sourceDatasetSha256':sha(dataset),'points':points,'cases':cases,'authorizationEnabled':False,'surrogateFitAuthorized':False,'productionPromotionAuthorized':False}
def authorization_template(proposal): return {'enabled':False,'ordinal':0,'executionKey':None,'proposalSha256':sha(proposal),'automaticDispatch':False}
def audit_results(proposal,results):
 expected={c['caseId']:c for c in proposal['cases']}; seen=set(); grouped={}
 for r in results:
  cid=r.get('caseId'); e=expected.get(cid)
  if not e or cid in seen: raise Refusal('unplanned or duplicate result')
  seen.add(cid)
  if r.get('seed')!=e['seed'] or r.get('status')!='COMPLETED' or r.get('syntaxCheckCount')!=1 or r.get('solverExecutionCount')!=1: raise Refusal('case contract failed')
  grouped.setdefault(e['groupId'],[]).append(float(r['value']))
 if seen!=set(expected): raise Refusal('missing result')
 return {'status':'PASSED','caseCount':len(results),'groups':sorted(grouped),'automaticAuthorization':False,'productionPromotion':False}
