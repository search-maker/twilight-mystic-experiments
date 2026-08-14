#!/usr/bin/env python3
import hashlib, json, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'review/level-b-v2-training-prefit-freeze-v3-densified58/protocol-v3.json'
GEN2=ROOT/'review/level-b-v2-training-prefit-freeze-v2/protocol-v2.json'
TERM=ROOT/'review/level-b-v2-training-fit-result-v2/result-v2.json'
EXEC=ROOT/'review/mystic-state-0069-ordinal23-result-v1/result-v1.json'
PREREG=ROOT/'review/mystic-state-0069-local-training-densification-v1/protocol-v1.json'

def req(c,m):
    if not c: raise SystemExit('REFUSED: '+m)
def load(p): return json.loads(Path(p).read_text())
def canon_sha(d, field):
    q=dict(d); q.pop(field,None)
    return hashlib.sha256(json.dumps(q,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def git_blob(path):
    return subprocess.check_output(['git','rev-parse','HEAD:'+str(path.relative_to(ROOT))],cwd=ROOT,text=True).strip()

p=load(P); g=load(GEN2); t=load(TERM); e=load(EXEC); r=load(PREREG)
req(p['schemaVersion']==3,'schema')
req(p['protocolId']=='level-b-v2-training-only-prefit-freeze-v3-densified58','protocol id')
req(p['status']=='REVIEW_ONLY_DENSIFIED58_PREFIT_FREEZE_NO_ORDINAL23_VALUES_READ_NO_FITTING','status')
req(canon_sha(p,'protocolSha256')==p['protocolSha256'],'protocol self hash')
req(p['sourceMainAtFreeze']=='cb8cb3f67fd48fcf2645bfdaef5ff0adf8345311','freeze source main')

s=p['sourceBindings']
expected_blobs={
 GEN2:'91ab4c109a209d3ee9ee24e327c554739cd9dd6c',
 TERM:'70161120e96afa3bbfd7a16239f8233ad159e266',
 EXEC:'958fbfa72d36cad0082075d9048a7a1caa2fadcd',
 PREREG:'d47bceb9b415ca8ebf14f6014207fd1310b4809c'}
for path,sha in expected_blobs.items(): req(git_blob(path)==sha,f'git blob drift: {path}')
req(s['ordinal23PreregistrationGitBlobSha']==expected_blobs[PREREG],'prereg blob binding')
req(s['ordinal23PreregistrationProtocolSelfSha256']=='e8ae35255147312c04f29f49d19e7599c1eeb5b2d3f035d2e93c93753cc5f022','prereg self-hash binding')
prereg_canonical_sha=hashlib.sha256(json.dumps(r,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
req(prereg_canonical_sha==s['ordinal23PreregistrationProtocolSelfSha256'],'prereg canonical self-hash drift')

req(t['status']=='TRAINING_ONLY_GENERATION2_NO_ELIGIBLE_CANDIDATE_NO_MODEL_FROZEN','terminal status drift')
req(t['selectionOutcome']['candidateCount']==230 and t['selectionOutcome']['eligibleCandidateCount']==0,'terminal outcome drift')
req(t['selectionOutcome']['modelArtifactWritten'] is False,'terminal model existence drift')
req(t['closedBoundaries']['ordinal22ValuesRead'] is False,'terminal ordinal22 drift')

req(e['status']=='ORDINAL23_TRAINING_DENSIFICATION_EXECUTION_COMPLETE_NO_FITTING','execution binding status')
req(e['execution']['workflowRunId']==31814698818 and e['execution']['workflowRunAttempt']==1,'run identity')
req((e['execution']['geometryCount'],e['execution']['caseCount'],e['execution']['configuredPhotonHistories'])==(14,28,560000000),'execution size')
req(e['execution']['rerunRetryResumeOccurred'] is False,'execution retry drift')
req(e['scientificBoundaries']['modelFitPerformed'] is False and e['scientificBoundaries']['ordinal22ValuesRead'] is False,'execution boundary')
req((e['inventoryArtifact']['artifactId'],e['inventoryArtifact']['inventorySelfSha256'],e['inventoryArtifact']['manifestSha256'])==(9224754905,'ae2356b618679cd33cefd3115ca23cd8eff6091be5f936fc93f0fcf609a99455','eb1817b25a59af305076f0afa24d5f6ba6f4571fb4748ed638071edc4557f2ea'),'inventory binding')

rg=r['design']['geometries']; rc=r['execution']['cases']
req(len(rg)==14 and len(rc)==28,'prereg sizes')
new_ids=[x['geometryId'] for x in rg]
req(new_ids==[f'train-{i:04d}' for i in range(101,115)],'new geometry ids')
req([x['seed'] for x in rc]==list(range(2100000101,2100000129)),'seed order')
req(all(x['role']=='surrogate-training' and x['photonHistories']==20000000 and x['method']=='alis' and x['alisSpectralImportanceSamplingNm']==550.0 for x in rc),'case physics/budget')
req(sum(x['photonHistories'] for x in rc)==560000000,'total histories')
req(r['design']['adaptivePointAdditionAllowed'] is False and r['execution']['adaptiveContinuationAllowed'] is False,'adaptive design closed')

ri=p['roleIsolation']; old=g['roleIsolation']['exactTrainingGeometryIds']; protected=g['roleIsolation']['openedV1ProtectedDiagnosticOnlyGeometryIds']
req(ri['legacy44TrainingGeometryIds']==old and len(old)==44,'legacy ids')
req(ri['ordinal23NewTrainingGeometryIds']==new_ids,'new ids binding')
expanded=sorted(old+new_ids)
req(ri['exactExpandedTrainingGeometryIds']==expanded and len(expanded)==58 and len(set(expanded))==58,'expanded ids')
req(not set(expanded)&set(protected),'protected geometry leaked')
req(ri['protectedRecordCountRequired']==0 and ri['ordinal22ValuesAllowed'] is False,'role closure')

re=p['representationExtension']
req((re['legacyGeometryCount'],re['newGeometryCount'],re['expandedGeometryCount'])==(44,14,58),'geometry counts')
req((re['legacySourceCaseCount'],re['newSourceCaseCount'],re['expandedSourceCaseCount'])==(138,28,166),'case counts')
req((re['mandatoryIntegratedChannelCount'],re['nullspacePcaComponentCount'],re['totalTargetCount'])==(3,10,13),'target dimensions')
for k in ('basisRefitAllowed','integrationWeightRecomputationAllowed','pcaRecomputationAllowed','rawResamplingAllowed','rawSmoothingAllowed','ordinal22MayInfluenceRepresentation'):
    req(re[k] is False,f'representation boundary {k}')
req(re['legacy44RecordsMustRemainValueExact'] is True,'legacy values mutable')
req(s['frozenRepresentationArtifactId']==9208203541 and s['frozenRepresentationPackageSha256']=='2491ac91ed924f2ba69b37ea20f48d63f51d41146cd9fe50e0bd63bfb315a763','frozen rep source')
req(s['legacy44DatasetCanonicalSha256']=='bb7908426d9d545f43c082aebbaab1829a486e2962d0b9ee34a5e8bef5390133','legacy dataset canonical')

ms=p['modelSelection']; gm=g['modelSelection']
req(ms['candidateCountRequired']==gm['candidateCountRequired']==230,'candidate count')
req(ms['candidateDefinition']=='COPY_EXACT_GENERATION2_CANDIDATE_FAMILIES_WITHOUT_CHANGE','candidate copy rule')
req(ms['selectionScoreDefinition']=='COPY_EXACT_GENERATION2_SELECTION_SCORE_WITHOUT_CHANGE','score copy rule')
req(ms['tieBreakDefinition']=='COPY_EXACT_GENERATION2_TIE_BREAK_WITHOUT_CHANGE','tie copy rule')
req(ms['trainingOnlyReadinessGatesDefinition']=='COPY_EXACT_GENERATION2_GATES_WITHOUT_CHANGE','gate copy rule')
req(ms['numericalImplementationDefinition']=='COPY_EXACT_GENERATION2_NUMERICAL_IMPLEMENTATION_WITHOUT_CHANGE','numerics copy rule')
semantics={k:gm[k] for k in ('candidateFamilies','selectionScore','tieBreak','trainingOnlyReadinessGates')}
sem_sha=hashlib.sha256(json.dumps(semantics,sort_keys=True,separators=(',',':')).encode()).hexdigest()

geom={x['geometryId']:x['geometry'] for x in rg}
old_counts=gm['crossValidationFolds']['expectedBoundaryFoldCounts']; new_delta={'sun-shallow':3,'sun-deep-core':0,'az-low':13,'az-high':0,'alt-low':14,'alt-high':0,'aod-low':0,'aod-high':0,'elev-low':1,'elev-high':0}
expected={k:old_counts[k]+new_delta[k] for k in old_counts}
cv=ms['crossValidationFolds']
req(cv['expectedBoundaryFoldCounts']==expected,'boundary fold counts')
req(cv['expectedBalancedFoldCounts']==[12,12,12,11,11],'balanced counts')
req(cv['totalFoldCountRequired']==73 and cv['leaveOneGeometryOut']=='EXACTLY_58_SINGLE_GEOMETRY_VALIDATION_FOLDS','fold universe')
preds={
 'sun-shallow':lambda x:x['sunDepressionDeg']<=4.0,
 'sun-deep-core':lambda x:8.5<=x['sunDepressionDeg']<=10.5,
 'az-low':lambda x:x['relativeAzimuthDeg']<=60.0,
 'az-high':lambda x:x['relativeAzimuthDeg']>=150.0,
 'alt-low':lambda x:x['targetAltitudeDeg']<=20.0,
 'alt-high':lambda x:x['targetAltitudeDeg']>=65.0,
 'aod-low':lambda x:x['aod550']<=0.10,
 'aod-high':lambda x:x['aod550']>=0.35,
 'elev-low':lambda x:x['observerElevationM']<=500.0,
 'elev-high':lambda x:x['observerElevationM']>=2000.0}
req({k:sum(fn(x) for x in geom.values()) for k,fn in preds.items()}==new_delta,'new-point boundary deltas')

xo=p['executionOrder']; cb=p['closedBoundaries']
req(xo['reviewPullRequestMayReadOrdinal23ScientificValues'] is False and xo['reviewPullRequestMayFitModel'] is False,'review stage opened')
req(xo['implementationReviewMustBeSyntheticOnly'] is True and xo['separateImplementationReviewAfterFreezeMergeRequired'] is True,'implementation gate')
req(xo['separateOneUsePostprocessActivationAfterImplementationMergeRequired'] is True and xo['noRerunRetryResume'] is True,'activation gate')
for k in ('newMysticSolverExecutionAuthorized','ordinal22ValuesMayBeRead','protectedValidationAuthorized','productionPromotionAuthorized','workerBLaneReactivated','workerCLaneReactivated'):
    req(cb[k] is False,f'closed boundary opened: {k}')

print(json.dumps({'status':'PASS','protocolSha256':p['protocolSha256'],'generation2ModelSemanticsSha256':sem_sha,'expandedTrainingGeometryCount':58,'candidateCount':230,'cvFoldCount':73,'ordinal23ScientificValuesRead':False,'modelFitPerformed':False},sort_keys=True))
