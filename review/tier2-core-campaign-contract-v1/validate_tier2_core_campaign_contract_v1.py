#!/usr/bin/env python3
from __future__ import annotations
import argparse, copy, hashlib, json, math
from pathlib import Path
from typing import Any

CID='public-tier2-v1-core-campaign-contract-v1'
STATUS='REVIEW_ONLY_TIER2_V1_CORE_CAMPAIGN_CONTRACT_NO_EXECUTION'
GOV='MYSTIC-STATE-0067'
MAIN='23583f702a00b5317c10f2254564685f416a5e84'
LEVELB='c2e91a8ca7b17fa65075652920e3b120800dc8a9206aa4c013006b9cdad68b18'
EXHAUSTED='5eacb2f5f25cb478bacef5261d51fcb1db9e1cf31be22ef2545a103763edfa54'
TRAIN0037='05e00e1ba402dc1418975ca36f5149723dc77a463271c3a11bf4d66af8bd52c0'
EXHAUSTED_IDS=['train-0003','train-0007','train-0011','train-0013','train-0019','train-0023','train-0027','train-0029','train-0031','train-0039','train-0041','train-0043','train-0047']
class Refusal(RuntimeError): pass
def req(c:bool,m:str)->None:
    if not c: raise Refusal(m)
def canon(v:Any)->bytes: return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def self_hash_null(v:dict[str,Any],field:str)->str:
    c=copy.deepcopy(v); c[field]=None; return hashlib.sha256(canon(c)).hexdigest()
def ri(i:int,b:int)->float:
    r=0.0; f=1.0/b
    while i:
        i,d=divmod(i,b); r+=d*f; f/=b
    return r
def expected_geometry(i:int)->dict[str,Any]:
    g={'geometryId':f'train-{i:04d}','sourceIndex':i}
    specs=[('sunDepressionDeg',2,2.0,18.0),('targetAltitudeDeg',3,5.0,80.0),('relativeAzimuthDeg',5,0.0,180.0),('observerElevationM',7,0.0,2500.0),('aod550',11,0.05,0.4)]
    for k,b,lo,hi in specs: g[k]=round(lo+(hi-lo)*ri(i,b),6)
    role='protected-holdout' if i%5==0 else 'surrogate-training'; g['role']=role
    g['executionStage']='PROTECTED_HOLDOUT_AFTER_MODEL_FREEZE' if role=='protected-holdout' else 'TRAINING_ACQUISITION'
    sun=g['sunDepressionDeg']; alt=g['targetAltitudeDeg']; aod=g['aod550']
    g['photonHistoriesPerBlock']=20_000_000 if sun<=8 else 50_000_000
    g['alisSpectralImportanceSamplingNm']=600.0 if sun>=10 and alt<=20 else 500.0 if sun>=10 and alt>=35 and aod>=0.25 else 550.0
    return g
def expected_geometries()->list[dict[str,Any]]:
    out=[]
    for i in range(49,97):
        g=expected_geometry(i)
        if g['sunDepressionDeg']<=10.5: out.append(g)
    return out
def expected_cases(gs:list[dict[str,Any]])->list[dict[str,Any]]:
    seed=1_900_000_001; out=[]
    for g in sorted(gs,key=lambda x:x['geometryId']):
        for block in range(1,5):
            out.append({'caseId':f"tier2-core-v1-{g['geometryId']}-b{block}",'geometryId':g['geometryId'],'role':g['role'],'executionStage':g['executionStage'],'block':block,'seed':seed,'photonHistories':g['photonHistoriesPerBlock'],'alisSpectralImportanceSamplingNm':g['alisSpectralImportanceSamplingNm'],'scientificValuesReadableBeforeRequiredFreeze':False if g['role']=='protected-holdout' else True}); seed+=1
    return out

def validate_data(d:dict[str,Any])->None:
    req(d.get('schemaVersion')==1 and d.get('campaignContractId')==CID and d.get('status')==STATUS and d.get('governance')==GOV,'identity/status drift')
    req(d.get('contractSha256')==self_hash_null(d,'contractSha256'),'contract self-hash drift')
    sem=d.get('decisionSemantics') or {}
    req(sem.get('contractType')=='TIER2_V1_CORE_CAMPAIGN_PREREGISTRATION_ONLY','contract type drift')
    for k in ('newScientificExecutionAuthorized','campaignAuthorizationIssued','campaignDispatchIssued','scientificOrdinalAllocated','modelFittingAuthorized','modelSelectionAuthorized','protectedHoldoutOpeningAuthorized','productionPromotionAuthorized','train0037Included','precisionExhaustedLegacyGeometriesIncludedAsLabels'):
        req(sem.get(k) is False,f'closed boundary drift: {k}')
    req(sem.get('nextScientificOrdinal') is None,'ordinal preassignment drift')
    s=d.get('sourceBindings') or {}
    req(s.get('liveMainAtFreeze')==MAIN and s.get('latestConsumedScientificOrdinal')==18,'main/ordinal binding drift')
    req(s.get('levelBDecisionSha256')==LEVELB,'Level-B binding drift')
    req(s.get('originalDesignGitBlobSha')=='e1ee465541e6b8664b34435f3698a33626eeff0f','original design blob drift')
    req(s.get('trainingDesignGeneratorGitBlobSha')=='7c0547a1a6a0f192637fc1956acb76d67334e687','generator blob drift')
    req(s.get('importancePolicyGitBlobSha')=='be61de779824af74b36f7ac479f14b6d67c2a7c1','importance-policy blob drift')
    req(s.get('legacyTier2ReadinessGitBlobSha')=='4aa3c5aefc03a1a4cd07ac38f515ddc416744db7','legacy readiness blob drift')
    req(s.get('precisionExhaustedTreatmentSha256')==EXHAUSTED and s.get('precisionExhaustedTreatmentPath')=='review/full-spectrum-precision-exhausted-treatment-v1/full-spectrum-precision-exhausted-treatment-protocol-v1.json' and s.get('precisionExhaustedTreatmentGitBlobSha')=='22d5e75ca02e246efbad5314b96f7f20218acb21' and s.get('train0037PreregistrationSha256')==TRAIN0037,'legacy treatment binding drift')
    cs=d.get('coreSelection') or {}
    req(cs=={'sourceOriginalTier':'tier-2-completion','sourceIndexRangeInclusive':[49,96],'selectionPredicate':'sunDepressionDeg <= 10.5','geometryCount':25,'trainingGeometryCount':19,'protectedHoldoutGeometryCount':6,'blocksPerGeometry':4,'caseCount':100,'trainingCaseCount':76,'protectedHoldoutCaseCount':24,'configuredPhotonHistoriesTotal':2840000000,'trainingPhotonHistories':2120000000,'protectedHoldoutPhotonHistories':720000000},'core selection/accounting drift')
    gs=expected_geometries(); req(d.get('geometryManifest')==gs,'geometry manifest differs from deterministic source design + v1 predicate')
    cases=expected_cases(gs); req(d.get('derivedCaseManifestSha256')==hashlib.sha256(canon(cases)).hexdigest(),'derived case manifest digest drift'); req((d.get('seedLedger') or {}).get('derivedSeedLedgerSha256')==hashlib.sha256(canon([{'caseId':c['caseId'],'seed':c['seed']} for c in cases])).hexdigest(),'derived seed ledger digest drift')
    req(len(gs)==25 and sum(g['role']=='surrogate-training' for g in gs)==19 and sum(g['role']=='protected-holdout' for g in gs)==6,'role count drift')
    req(sum(c['photonHistories'] for c in cases)==2840000000,'photon accounting drift')
    req(sum(c['photonHistories'] for c in cases if c['role']=='surrogate-training')==2120000000,'training photon accounting drift')
    req(sum(c['photonHistories'] for c in cases if c['role']=='protected-holdout')==720000000,'holdout photon accounting drift')
    st=d.get('executionStaging') or {}
    req(st.get('mode')=='TRAINING_FIRST_THEN_PROTECTED_HOLDOUT_AFTER_FREEZE','staging drift')
    req(st.get('sameBatchHoldoutExecutionAllowedNow') is False and st.get('sameBatchHoldoutRefusalReason')=='GENUINE_TECHNICAL_SEALING_NOT_PROVEN_AT_CONTRACT_FREEZE','holdout sealing boundary drift')
    req(st.get('perGeometryAuthorizationAllowed') is False and st.get('perGeometryDispatchAllowed') is False,'per-geometry governance reopened')
    req(st.get('futureAuthorizationShape')=='SINGLE_CAMPAIGN_CONTRACT_WITH_FAIL_CLOSED_STAGE_GATES','campaign authorization shape drift')
    req(st.get('stage1')=={'stageId':'TRAINING_ACQUISITION','geometryCount':19,'caseCount':76,'configuredPhotonHistories':2120000000,'scientificExecutionAuthorized':False,'protectedHoldoutValuesReadable':False},'stage1 drift')
    req(st.get('stage2')=={'stageId':'PROTECTED_HOLDOUT_AFTER_MODEL_FREEZE','geometryCount':6,'caseCount':24,'configuredPhotonHistories':720000000,'scientificExecutionAuthorized':False,'scientificValuesReadableBeforeRequiredFreeze':False},'stage2 drift')
    inter=st.get('interstageFreeze') or {}
    req(inter.get('requiredBeforeAnyProtectedHoldoutExecution') is True and inter.get('holdoutResultsMayChangeModelRepresentationOODOrThresholds') is False,'interstage freeze drift')
    req(inter.get('requirements')==['TRAINING_DATASET_FROZEN','TRAINING_ONLY_SPECTRAL_ADEQUACY_GATE_CLOSED','MODEL_AND_REPRESENTATION_FROZEN','VALIDATED_SUPPORT_OOD_PREDICATE_FROZEN','NUMERICAL_DEFINITION_OF_DONE_AND_THRESHOLDS_FROZEN'],'interstage requirements drift')
    rp=d.get('artifactPipelineReplayGate') or {}
    req(rp.get('requiredBeforeAnySolverJob') is True and rp.get('status')=='REQUIRED_NOT_YET_SATISFIED' and rp.get('mustUseExistingRealArtifactsOnly') is True,'artifact replay gate drift')
    req(rp.get('resultMustBeVersionedReviewedAndMerged') is True and rp.get('failureOutcome')=='NO_CAMPAIGN_AUTHORIZATION_OR_DISPATCH','artifact replay disposition drift')
    req(rp.get('mustExercise')==['INPUT_RENDER_AND_PHYSICAL_FINGERPRINT','PREPARED_CASE_BINDING','CASE_RESULT_AND_RAW_SPECTRUM_HASHING','TRANSPORT_ARTIFACT_ID_AND_DIGEST_BINDING','FULL_SPECTRUM_DERIVED_CHANNEL_REINTEGRATION','AGGREGATE_AND_INDEPENDENT_AUDIT','TRAINING_HANDOFF_ROLE_EXCLUSION'],'artifact replay surface drift')
    p=d.get('physicalInputContract') or {}
    req(p.get('skyComponent')=='CLEAR_SKY_SOLAR_TWILIGHT_ONLY','sky component drift')
    req(p.get('solarDepressionDeg')=={'minInclusive':2.0,'maxInclusive':10.5} and p.get('targetAltitudeDeg')=={'minInclusive':5.0,'maxInclusive':80.0} and p.get('relativeAzimuthDeg')=={'minInclusive':0.0,'maxInclusive':180.0} and p.get('observerElevationM')=={'minInclusive':0.0,'maxInclusive':2500.0} and p.get('aod550')=={'minInclusive':0.05,'maxInclusive':0.40},'design box drift')
    req(p.get('profileFamily')=='AFGLUS_REVIEWED_PROFILE_SEMANTICS' and p.get('aod550IsInput') is True,'atmosphere drift')
    req(p.get('observerElevationRepresentation')=='ASCENDING_ATM_Z_GRID_BOTTOM_EQUALS_PHYSICAL_OBSERVER_ELEVATION' and p.get('localSurfaceZoutKm')==0.0,'elevated-site representation drift')
    req(p.get('altitudeShortcutAllowed') is False and p.get('mcElevationFileShortcutAllowed') is False and p.get('completePhysicalInputFingerprintRequired') is True,'physical-input guard drift')
    sup=d.get('deploymentSupportContract') or {}
    req(sup=={'designBoxEqualsValidatedDeploymentSupport':False,'insideDesignBoxMayStillBeOOD':True,'validatedDeploymentSupportPredicateRequired':True,'freezeTiming':'AFTER_TRAINING_DATASET_FREEZE_BEFORE_PROTECTED_HOLDOUT_OPENING','silentExtrapolationAllowed':False,'oodOutcome':'EXPLICIT_UNSUPPORTED_OR_LEGACY_FALLBACK'},'deployment/OOD drift')
    sp=d.get('spectralTargetContract') or {}
    req(sp.get('immutableRawSpectrumRequired') is True and sp.get('rawSpectrumWavelengthRangeNm')==[380.0,780.0],'raw spectrum boundary drift')
    req(sp.get('initialPrimaryTargets')==['FULL_PHOTOPIC_LUMINANCE','FULL_SCOTOPIC_LUMINANCE','JOHNSON_V_EFFECTIVE_RADIANCE'],'primary target drift')
    req(sp.get('sOverPIsDerivedNotIndependentTarget') is True and sp.get('exactZeroPreserved') is True and sp.get('epsilonSubstitutionAllowed') is False,'zero/S-P semantics drift')
    req(sp.get('trainingOnlySpectralAdequacyGateRequired') is True and sp.get('holdoutResultsMayTriggerRepresentationChange') is False,'spectral gate drift')
    v=d.get('validationContract') or {}
    req(v.get('protectedHoldoutGeometryCount')==6 and v.get('allHoldoutsReportedIndividually') is True,'holdout validation count drift')
    req(v.get('primaryChannelPerCaseMetrics')==['SIGNED_ERROR','ABSOLUTE_RELATIVE_OR_LOG_ERROR','MYSTIC_MONTE_CARLO_UNCERTAINTY','ERROR_NORMALIZED_BY_MYSTIC_UNCERTAINTY'],'per-case metric drift')
    req(v.get('aggregateMetrics')==['MEDIAN_ABSOLUTE_OR_LOG_ERROR','WORST_CASE_ERROR','WORST_ERROR_NORMALIZED_BY_MYSTIC_UNCERTAINTY'],'aggregate metric drift')
    req(v.get('p90OrP95AsPrincipalStatisticAllowed') is False and v.get('perCaseCeilingRequired') is True and v.get('holdoutValuesMayNotSetOrRelaxThresholds') is True,'n=6/threshold rule drift')
    req(v.get('numericalThresholdsStatus')=='MUST_BE_FROZEN_IN_SEPARATE_MODEL_PROTOCOL_BEFORE_HOLDOUT_OPENING','threshold timing drift')
    sl=d.get('seedLedger') or {}
    req(sl.get('status')=='FROZEN_CANDIDATE_LEDGER_REQUIRES_PREAUTH_GLOBAL_COLLISION_RECHECK','seed ledger status drift')
    req(sl.get('assignmentRule')=='ASCENDING_GEOMETRY_ID_THEN_BLOCK_1_TO_4' and sl.get('firstSeed')==1900000001 and sl.get('lastSeed')==1900000100 and sl.get('seedCount')==100 and sl.get('allSeedsUnique') is True,'seed ledger drift')
    req(sl.get('repositoryCodeSearchPrefixAtFreeze')=='1900000' and sl.get('repositoryCodeSearchMatchesAtFreeze')==0 and sl.get('repositoryIssueSearchPrefixAtFreeze')=='1900000' and sl.get('repositoryIssueSearchMatchesAtFreeze')==0,'seed search record drift')
    req(sl.get('globalCollisionAuditStillRequiredBeforeAuthorization') is True and sl.get('collisionAuditComparisonUniverse')=='ALL_KNOWN_SCIENTIFIC_SEEDS_EXCLUDING_THIS_FROZEN_LEDGER_RECORD' and sl.get('selfLedgerMatchesIgnored') is True and sl.get('auditMustCompareEveryCandidateSeedAgainstExternalCodeIssueArtifactAndGovernanceLedgers') is True and sl.get('collisionOutcome')=='VERSION_NEW_SEED_LEDGER_AND_CAMPAIGN_CONTRACT_IF_ANY_CANDIDATE_SEED_COLLIDES_WITH_AN_EXTERNAL_PREEXISTING_OR_CONCURRENT_IDENTITY_BEFORE_ANY_RESULT_OPENING','seed collision guard drift')
    ex=d.get('legacyExclusions') or {}
    req(ex.get('train0037Status')=='DEFERRED_OUTSIDE_V1_CORE_DOMAIN' and ex.get('train0037SolarDepressionDeg')==12.25 and ex.get('train0037ScientificExecutionAuthorized') is False and ex.get('ordinal19AllocatedOrPreassigned') is False,'train0037/ordinal drift')
    req(ex.get('precisionExhaustedGeometryCount')==13 and ex.get('precisionExhaustedGeometryIds')==EXHAUSTED_IDS and ex.get('precisionExhaustedRemainRefusedAsTrainingLabels') is True and ex.get('precisionExhaustedRescueOrContinuationAuthorized') is False,'precision-exhausted treatment drift')
    req(not ({g['geometryId'] for g in gs} & set(EXHAUSTED_IDS)),'legacy exhausted geometry leaked into campaign')
    nb=d.get('nextBoundary') or {}
    req(nb=={'nextAllowedWork':'ARTIFACT_PIPELINE_REPLAY_AND_REVIEW_ONLY_CAMPAIGN_IMPLEMENTATION_PREPARATION','campaignAuthorizationAutomaticAfterMerge':False,'scientificExecutionAutomaticAfterMerge':False,'ordinal19AllocationAllowedByThisContract':False,'modelFittingAllowedByThisContract':False,'protectedHoldoutOpeningAllowedByThisContract':False},'next boundary drift')

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--contract',required=True); a=ap.parse_args()
    d=json.loads(Path(a.contract).read_text(encoding='utf-8')); validate_data(d); print('TIER2_V1_CORE_CAMPAIGN_CONTRACT_VALID'); return 0
if __name__=='__main__': raise SystemExit(main())
