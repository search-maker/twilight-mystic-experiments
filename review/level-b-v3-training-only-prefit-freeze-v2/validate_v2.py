#!/usr/bin/env python3
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent

def load(p): return json.loads(p.read_text(encoding='utf-8'))
def csha(o,field):
    x=dict(o); x.pop(field,None)
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def req(c,m):
    if not c: raise SystemExit(m)

p=load(HERE/'protocol-v2.json')
c=load(HERE/'correction-v1.json')
v1=load(ROOT/'review/level-b-v3-training-only-prefit-freeze-v1/protocol-v1.json')
req(p['protocolSha256']==csha(p,'protocolSha256'),'protocol v2 self hash drift')
req(c['correctionSha256']==csha(c,'correctionSha256'),'correction self hash drift')
req(p['governance']==c['governance']=='MYSTIC-STATE-0071','governance drift')
req(p['protocolId']=='level-b-v3-training-only-prefit-freeze-v2','protocol id drift')
req(p['sourceMainAtFreeze']=='90b3afc7274ea574c1f8a80d440b6ed1364944b9','source main drift')
req(v1['protocolSha256']==p['sourceBindings']['priorPrefitProtocolSha256']==c['priorProtocolSha256']=='48e3f47caedacff6e60304beed7d49e58f03ed0ee906bd7cdf3a54c0bd945199','v1 binding drift')
req(c['supersedingProtocolSha256']==p['protocolSha256'],'v2 binding drift')
for key in ('trainingOnlyReadinessGates','crossValidation','roleIsolation','targetsAndRepresentation','closedBoundaries','exitRules'):
    req(p[key]==v1[key],f'non-clarification drift: {key}')
req(p['candidateDefinition']['candidateCountRequired']==v1['candidateDefinition']['candidateCountRequired']==145,'candidate count drift')
for key in ('primaryRidgeValues','residualNeighbors','residualPowers','residualShrinkage','shapePredictorFixed','primaryBasis','primaryPredictionDefinition','familyId','kind','candidateCount'):
    req(p['candidateDefinition']['newFamily'][key]==v1['candidateDefinition']['newFamily'][key],f'candidate grid drift: {key}')
req(p['candidateDefinition']['control']['primaryRidge']==v1['candidateDefinition']['control']['primaryRidge']==1e-5,'control primary drift')
req(p['candidateDefinition']['control']['shapeNeighbors']==4 and p['candidateDefinition']['control']['shapePower']==1.0,'control shape drift')
req(p['candidateDefinition']['control']['complexityRank']==7,'control complexity rank drift')
new=p['candidateDefinition']['newFamily']
req(new['complexityRank']==9,'new family complexity rank drift')
req(new['residualCoordinateSystems']['PHYSICAL_NORMALIZED_IDW_COORDINATES']==['(sunDepressionDeg-2.0)/8.5','sin(targetAltitudeDeg*pi/180.0)','(cos(relativeAzimuthDeg*pi/180.0)+1.0)/2.0','observerElevationM/2500.0','log(aod550/0.05)/log(8.0)'],'physical residual coordinates drift')
req(new['residualCoordinateSystems']['V1_IDW_COS_COORDINATES']==['(sunDepressionDeg-2.0)/8.5','(targetAltitudeDeg-5.0)/75.0','(cos(relativeAzimuthDeg*pi/180.0)+1.0)/2.0','observerElevationM/2500.0','(aod550-0.05)/0.35'],'v1 residual coordinates drift')
req(new['residualDistanceMetric']=='EUCLIDEAN_L2_FLOAT64','distance semantics drift')
req(new['residualNeighborOrdering']=='ASCENDING_DISTANCE_STABLE_PRESERVE_FIT_RECORD_ORDER_ON_EQUAL_DISTANCE','neighbor ordering drift')
req(new['residualExactMatchDefinition'].startswith('IF_FLOAT64_DISTANCE_EQUALS_EXACTLY_0.0'),'exact match drift')
req(new['residualWeightDefinition']=='FOR_NONZERO_NEIGHBORS_WEIGHT=1/(distance**power); NORMALIZE_WEIGHTS_TO_SUM_1','weight semantics drift')
req(new['residualDefinition']=='TRUTH_PRIMARY_NATURAL_LOG_TARGET_MINUS_BASE_COMPACT_RIDGE_PRIMARY_PREDICTION_ON_SAME_FIT_RECORD','residual sign drift')
req(new['finalPrimaryPrediction']=='BASE_COMPACT_RIDGE_PRIMARY_PREDICTION_PLUS_RESIDUAL_SHRINKAGE_TIMES_IDW_RESIDUAL_VECTOR','prediction semantics drift')
req(p['selection']['complexityRankDefinition']=={'control':7,'newResidualIdwFamily':9},'selection complexity rank drift')
req(p['selection']['lexicographicHyperparametersForNewFamily']==['residualCoordinateSystem','primaryRidge','residualNeighbors','residualPower','residualShrinkage'],'hyperparameter tie tuple drift')
req(p['selection']['exactTieBehavior']=='CONTROL_WINS_ANY_NUMERIC_TIE_BECAUSE_CONTROL_COMPLEXITY_RANK_7_PRECEDES_NEW_FAMILY_RANK_9','tie behavior drift')
req(p['executionOrder']['priorPrefitV1MayAuthorizeFit'] is False and p['executionOrder']['prefitV2SupersedesV1BeforeAnyChangedFit'] is True,'supersession drift')
req(c['changedFitOccurredBeforeCorrection'] is False and c['trainingArtifactDownloadedAfterPrefitV1Merge'] is False and c['ordinal27ReadForCorrection'] is False,'correction timing/leakage drift')
for k in ('candidateCountChanged','candidateHyperparameterGridChanged','trainingDataChanged','crossValidationChanged','readinessGatesChanged','targetRepresentationChanged'):
    req(c[k] is False,f'correction changed frozen science: {k}')
print('PASS: MYSTIC-STATE-0071 prefit v2 only clarifies deterministic complexity/angle/distance/tie semantics before any changed fit')
