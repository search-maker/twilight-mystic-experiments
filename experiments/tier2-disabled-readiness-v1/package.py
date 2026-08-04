from __future__ import annotations
import hashlib,json
class Refusal(RuntimeError):pass
def raw(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def build(full_design,runtime):
 if full_design.get('stageId')!='twilight-surrogate-training-design-v1' or full_design.get('proposalOnly') is not True or full_design.get('geometryCount')!=96 or full_design.get('caseCount')!=192:raise Refusal('full design changed')
 tiers=[x for x in full_design.get('executionTiers',[]) if x.get('tierId')=='tier-2-completion']
 if len(tiers)!=1:raise Refusal('tier-2 missing')
 ids=set(tiers[0]['geometryIds']); cids=set(tiers[0]['caseIds']); gs=[g for g in full_design['geometries'] if g['geometryId'] in ids]; cs=[c for c in full_design['cases'] if c['caseId'] in cids]
 if len(gs)!=48 or len(cs)!=96 or sum(c['photonHistories'] for c in cs)!=7320000000:raise Refusal('frozen counts changed')
 if any(c['executionTierId']!='tier-2-completion' or c['role'] not in {'surrogate-training','internal-holdout'} for c in cs):raise Refusal('role or tier changed')
 if len({c['seed'] for c in cs})!=96 or any(c['seed']<=910096 for c in cs):raise Refusal('seed boundary changed')
 return {'schemaVersion':1,'stageId':'tier2-disabled-readiness-v1','status':'READY_DISABLED_PENDING_SEPARATE_DECISION','proposalOnly':True,'scientificExecution':False,'automaticTrigger':False,'authorizationEnabled':False,'geometryCount':48,'caseCount':96,'blocksPerGeometry':2,'configuredMcPhotonsSum':7320000000,'runtimeBindingSha256':raw(runtime),'sourceDesignSha256':raw(full_design),'geometries':gs,'cases':cs,'matrix':[{'case_id':c['caseId'],'seed':c['seed'],'photon_histories':c['photonHistories'],'role':c['role']} for c in cs],'perCaseContract':{'syntaxCheckCount':1,'solverExecutionCount':1,'artifactRequired':True},'modelFittingAuthorized':False,'productionPromotionAuthorized':False}
def authorization_template(package):return {'enabled':False,'ordinal':0,'executionKey':None,'packageSha256':raw(package),'automaticTrigger':False,'tier2DecisionRecorded':False}
def audit(package,results):
 exp={c['caseId']:c for c in package['cases']};seen=set()
 for r in results:
  e=exp.get(r.get('caseId'))
  if not e or r['caseId'] in seen:raise Refusal('duplicate/unplanned')
  seen.add(r['caseId'])
  if r.get('seed')!=e['seed'] or r.get('syntaxCheckCount')!=1 or r.get('solverExecutionCount')!=1 or r.get('artifactSha256') is None:raise Refusal('case artifact contract failed')
 if seen!=set(exp):raise Refusal('missing cases')
 return {'status':'PASSED','caseCount':96,'configuredMcPhotonsSum':7320000000,'automaticTier2':False,'modelFittingAuthorized':False,'productionPromotionAuthorized':False}
