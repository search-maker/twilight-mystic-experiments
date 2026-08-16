#!/usr/bin/env python3
import hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent

def load(p): return json.loads(p.read_text(encoding='utf-8'))
def csha(o, field):
    x=dict(o); x.pop(field,None)
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def req(c,m):
    if not c: raise SystemExit(m)

a=load(HERE/'training-audit-v1.json')
p=load(HERE/'protocol-v1.json')
old=load(ROOT/'review/level-b-v2-training-prefit-freeze-v3-densified58/protocol-v3.json')
old2=load(ROOT/'review/level-b-v2-training-prefit-freeze-v2/protocol-v2.json')
result=load(ROOT/'review/level-b-v2-training-fit-result-v3-densified58/result-v3.json')
req(a['auditSha256']==csha(a,'auditSha256'),'audit self hash drift')
req(p['protocolSha256']==csha(p,'protocolSha256'),'protocol self hash drift')
req(a['status']=='TRAINING_ONLY_AUDIT_NO_ORDINAL27_INPUT_NO_CHANGED_FIT','audit status drift')
req(p['status']=='REVIEW_ONLY_PREFIT_FREEZE_NO_CHANGED_FIT_NO_ORDINAL27_VALUES','protocol status drift')
req(a['governance']==p['governance']=='MYSTIC-STATE-0071','governance drift')
req(p['sourceMainAtFreeze']=='8b46321e9dfa16754292967b0af8c53003e13724','source main drift')
req(p['sourceBindings']['expandedDatasetSha256']==result['datasetOutcome']['expandedDatasetSha256']=='58c977acf84b6ce17717765c2052f7f9fd64e2965e5bf447eba5cc4accb30435','dataset drift')
req(p['sourceBindings']['trainingSelectionSha256']==result['selectionOutcome']['trainingSelectionSha256']=='bed37ced8faa837b7adbd532fe7358e447aea76a1a4f064d4bdcef7cb6326a8a','selection drift')
req(p['sourceBindings']['frozenV2ModelSha256']==result['selectionOutcome']['modelSha256']=='91ae5811e55b3d4ef872ab672f006c4b383c6581a53de67cd018b6eb2666f9a7','model drift')
req(p['sourceBindings']['sourceDensified58PrefitProtocolSha256']==old['protocolSha256']=='eaf8d1d047fa5a336027a18b3cddd015943f4a28fd58c568fac233f819baaf73','source protocol drift')
req(p['sourceBindings']['trainingAuditSha256']==a['auditSha256'],'audit binding drift')
req(p['sourceBindings']['trainingArtifactId']==result['artifact']['id']==9229229366,'training artifact id drift')
req(p['sourceBindings']['trainingArtifactDigest']==result['artifact']['digest']=='sha256:f4c8c68a622f7c6bdc1b9177ad31d22f673becb1f286436d54b876ceece3668a','training artifact digest drift')
req(p['roleIsolation']['trainingGeometryIds']==old['roleIsolation']['exactExpandedTrainingGeometryIds'],'58 role set drift')
req(len(p['roleIsolation']['trainingGeometryIds'])==58,'58 training ids required')
req(p['roleIsolation']['protectedRecordCountRequired']==0 and not p['roleIsolation']['ordinal27ValuesAllowed'] and not p['roleIsolation']['ordinal27GeometryCoordinatesAllowedForSelection'],'ordinal27 isolation drift')
req(p['trainingOnlyReadinessGates']['looMeanPrimaryMaleMax']==old2['modelSelection']['trainingOnlyReadinessGates']['looMeanPrimaryMaleMax']==0.25,'mean primary gate drift')
for k,v in old2['modelSelection']['trainingOnlyReadinessGates'].items():
    req(p['trainingOnlyReadinessGates'][k]==v,f'gate drift: {k}')
req(p['crossValidation']['totalFoldCountRequired']==old['modelSelection']['crossValidationFolds']['totalFoldCountRequired']==73,'fold count drift')
req(p['crossValidation']['balancedFoldCounts']==old['modelSelection']['crossValidationFolds']['expectedBalancedFoldCounts'],'balanced folds drift')
req(p['crossValidation']['boundaryFoldCounts']==old['modelSelection']['crossValidationFolds']['expectedBoundaryFoldCounts'],'boundary folds drift')
new=p['candidateDefinition']['newFamily']
calc=len(new['primaryRidgeValues'])*len(new['residualCoordinateSystems'])*len(new['residualNeighbors'])*len(new['residualPowers'])*len(new['residualShrinkage'])
req(calc==new['candidateCount']==144,'new candidate count drift')
req(p['candidateDefinition']['candidateCountRequired']==1+calc==145,'total candidate count drift')
req(p['candidateDefinition']['control']['primaryRidge']==1e-5 and p['candidateDefinition']['control']['shapeNeighbors']==4 and p['candidateDefinition']['control']['shapePower']==1.0,'control drift')
req(p['selection']['newCandidateMustStrictlyOutrankControl'] and p['selection']['shapeMetricsMustBeIdenticalAcrossAllCandidates'],'selection safety drift')
for k,v in p['closedBoundaries'].items():
    if k.endswith('Authorized') or k.endswith('Reactivated') or k.startswith('newProtected') or k=='ordinal27MayBeReusedAsValidation': req(v is False,f'closed boundary opened: {k}')
req(not p['executionOrder']['reviewPullRequestMayFitModel'] and not p['executionOrder']['reviewPullRequestMayDownloadTrainingArtifact'] and not p['executionOrder']['reviewPullRequestMayReadOrdinal27'],'review surface opened')
req(a['antiLeakage']['ordinal27ValuesIngestedByThisAudit'] is False and a['antiLeakage']['ordinal27GeometryCoordinatesIngestedByThisAudit'] is False,'audit leakage flag')
fs={x['familyId']:x for x in a['existingCandidateFamilySummary']}
req(fs['ridge-primary-physical-compact-shape-idw-cos']['eligibleCandidateCount']==9,'eligible family count drift')
req(all(x['eligibleCandidateCount']==0 for k,x in fs.items() if k!='ridge-primary-physical-compact-shape-idw-cos'),'unexpected eligible legacy family')
req(abs(fs['ridge-primary-physical-poly2-shape-idw-cos']['bestMetrics']['boundaryWorstPrimaryMale']-0.49363544156049183)<1e-15,'poly2 boundary audit drift')
print('PASS: MYSTIC-STATE-0071 Level-B v3 training-only pre-fit freeze is review-only, 58-training-only, ordinal27-isolated, and gate-preserving')
