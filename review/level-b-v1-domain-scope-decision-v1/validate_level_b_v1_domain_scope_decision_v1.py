#!/usr/bin/env python3
from __future__ import annotations
import argparse, copy, hashlib, json
from pathlib import Path
from typing import Any

DID='public-level-b-v1-domain-scope-decision-v1'
STATUS='REVIEW_ONLY_LEVEL_B_V1_DOMAIN_SCOPE_DECISION_NO_SCIENCE'
GOV='MYSTIC-STATE-0067'
MAIN='80523d8a59b0c2b4682559e5020410d1962d31d7'
ADMISSION_SHA='439f11900d82148e3af61be46071f1ae5910a73ae552f33949e6cdc58eabe10c'
EXHAUSTED_SHA='5eacb2f5f25cb478bacef5261d51fcb1db9e1cf31be22ef2545a103763edfa54'
TRAIN0037_PREREG='05e00e1ba402dc1418975ca36f5149723dc77a463271c3a11bf4d66af8bd52c0'

class Refusal(RuntimeError): pass
def req(c:bool,m:str)->None:
    if not c: raise Refusal(m)
def canon(v:Any)->str:
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def self_hash_null(v:dict[str,Any],field:str)->str:
    c=copy.deepcopy(v); c[field]=None; return canon(c)

def validate_data(d:dict[str,Any])->None:
    req(d.get('decisionId')==DID,'decision id drift')
    req(d.get('schemaVersion')==1 and d.get('governance')==GOV and d.get('status')==STATUS,'schema/governance/status drift')
    req(d.get('decisionSha256')==self_hash_null(d,'decisionSha256'),'decision self-hash drift')
    s=d.get('sourceBindings') or {}
    req(s.get('liveMainAtFreeze')==MAIN,'live main binding drift')
    req(s.get('latestConsumedScientificOrdinal')==18,'latest ordinal drift')
    req(s.get('admittedTrainingGeometryCount')==25,'admitted training count drift')
    req(s.get('sourceAdmissionDecisionSha256')==ADMISSION_SHA,'source admission decision drift')
    req(s.get('precisionExhaustedTreatmentSha256')==EXHAUSTED_SHA,'precision-exhausted treatment binding drift')
    req(s.get('train0037PreregistrationSha256')==TRAIN0037_PREREG,'train0037 preregistration binding drift')

    sem=d.get('decisionSemantics') or {}
    req(sem.get('decisionType')=='LEVEL_B_V1_DOMAIN_AND_OOD_SCOPE_ONLY','decision type drift')
    for k in ('campaignExecutionAuthorized','modelFittingAuthorized','modelSelectionAuthorized','newScientificExecutionAuthorized','ordinal19Allocated','productionPromotionAuthorized','protectedHoldoutOpeningAuthorized','tier2ScientificExecutionAuthorized'):
        req(sem.get(k) is False,f'closed decision boundary drift: {k}')
    req(sem.get('train0037Status')=='DEFERRED_OUTSIDE_V1_CORE_DOMAIN','train0037 decision drift')

    f=d.get('frozenScope') or {}
    box=f.get('intendedPhysicalDesignBox') or {}
    req(box.get('solarDepressionDeg')=={'minInclusive':2.0,'maxInclusive':10.5},'solar core drift')
    req(box.get('targetAltitudeDeg')=={'minInclusive':5.0,'maxInclusive':80.0},'target altitude drift')
    req(box.get('relativeAzimuthDeg')=={'minInclusive':0.0,'maxInclusive':180.0},'relative azimuth drift')
    req(box.get('observerElevationM')=={'minInclusive':0.0,'maxInclusive':2500.0},'observer elevation drift')
    req(box.get('aod550')=={'minInclusive':0.05,'maxInclusive':0.40},'AOD drift')
    req(box.get('skyComponent')=='CLEAR_SKY_SOLAR_TWILIGHT_ONLY','sky component drift')

    atm=f.get('atmosphereContract') or {}
    req(atm.get('profileFamily')=='AFGLUS_REVIEWED_PROFILE_SEMANTICS' and atm.get('aod550IsInput') is True,'atmosphere family drift')
    req(atm.get('observerElevationRepresentation')=='ASCENDING_ATM_Z_GRID_BOTTOM_EQUALS_PHYSICAL_OBSERVER_ELEVATION','elevated-site representation drift')
    req(atm.get('localSurfaceZoutKm')==0.0,'zout drift')
    req(atm.get('altitudeShortcutAllowed') is False and atm.get('mcElevationFileShortcutAllowed') is False,'elevated-site shortcut drift')
    req(atm.get('completePhysicalInputFingerprintRequired') is True,'physical fingerprint boundary drift')
    req(atm.get('ozoneIsIndependentCampaignDimension') is False and atm.get('waterVaporIsIndependentCampaignDimension') is False,'unrepresented atmosphere dimension drift')
    req(atm.get('unrepresentedAtmospherePolicy')=='FIXED_BY_CONTRACT_OR_OOD_EXTERNAL_CONDITION','atmosphere OOD policy drift')

    sup=f.get('deploymentSupportPolicy') or {}
    req(sup.get('designBoxEqualsValidatedDeploymentSupport') is False,'design/support conflation')
    req(sup.get('validatedDeploymentSupportPredicateRequired') is True,'validated support predicate missing')
    req(sup.get('insideDesignBoxMayStillBeOOD') is True and sup.get('silentExtrapolationAllowed') is False,'OOD behavior drift')
    req(sup.get('oodOutcome')=='EXPLICIT_UNSUPPORTED_OR_LEGACY_FALLBACK','OOD outcome drift')
    req(sup.get('validatedSupportPredicateFreezeTiming')=='AFTER_TRAINING_DATASET_FREEZE_BEFORE_HOLDOUT_OPENING','support freeze timing drift')

    gov=f.get('campaignGovernancePolicy') or {}
    req(gov.get('unitOfGovernance')=='SCIENTIFIC_CAMPAIGN','campaign governance unit drift')
    req(gov.get('perGeometryAuthorizationDispatchLifecycleAllowed') is False,'per-geometry lifecycle reopened')
    req(gov.get('campaignContractRequiredBeforeAnyNewAcquisition') is True,'campaign contract gate drift')
    req(gov.get('singleFrozenGeometryManifestRequired') is True and gov.get('singleDeterministicSeedLedgerRequired') is True and gov.get('singleAuthorizationAndDispatchRequired') is True,'campaign structure drift')

    h=f.get('protectedHoldoutPolicy') or {}
    req(h.get('protectedHoldoutGeometryCount')==6,'holdout count drift')
    req(h.get('sameBatchExecutionAllowedOnlyWithGenuineTechnicalSealing') is True,'holdout sealing weakened')
    req(h.get('ordinaryTrainingOrModelSelectionIdentityMayReadScientificValues') is False,'holdout access boundary weakened')
    req(h.get('trainingAggregateIncludesHoldoutValues') is False,'holdout leaked into training aggregate')
    req(h.get('modelRepresentationOODAndDefinitionOfDoneFrozenBeforeOpening') is True,'model freeze gate drift')
    fb=h.get('fallbackIfGenuineSealingUnavailable') or {}
    req(fb=={'trainingJobsFirst':76,'holdoutJobsAfterModelFreeze':24,'holdoutScientificValuesRemainUnavailableUntilFreeze':True},'holdout fallback drift')

    val=f.get('computationalValidationProtocol') or {}
    req(val.get('holdoutGeometryCount')==6 and val.get('allHoldoutsReportedIndividually') is True,'validation universe drift')
    req(val.get('primaryChannelPerCaseMetrics')==['SIGNED_ERROR','ABSOLUTE_RELATIVE_OR_LOG_ERROR','MYSTIC_MONTE_CARLO_UNCERTAINTY','ERROR_NORMALIZED_BY_MYSTIC_UNCERTAINTY'],'per-case validation metrics drift')
    req(val.get('aggregateMetrics')==['MEDIAN_ABSOLUTE_OR_LOG_ERROR','WORST_CASE_ERROR','WORST_ERROR_NORMALIZED_BY_MYSTIC_UNCERTAINTY'],'aggregate validation metrics drift')
    req(val.get('p90OrP95AsPrincipalStatisticAllowed') is False and val.get('perCaseCeilingRequired') is True,'n=6 validation rule drift')
    req(val.get('numericalPassFailThresholdsFrozenBeforeHoldoutOpening') is True,'validation threshold freeze drift')

    sp=f.get('trainingOnlySpectralAdequacyGate') or {}
    req(sp.get('requiredBeforeHoldoutOpening') is True,'spectral adequacy gate removed')
    req(sp.get('initialIntegratedTargets')==['FULL_PHOTOPIC_LUMINANCE','FULL_SCOTOPIC_LUMINANCE','JOHNSON_V_EFFECTIVE_RADIANCE'],'initial target drift')
    req(sp.get('full380To780NmSpectraPreservedAsImmutableEvidence') is True,'full-spectrum evidence preservation drift')
    req(sp.get('holdoutResultsMayTriggerRepresentationChange') is False,'holdout-driven representation tuning reopened')

    t=f.get('train0037Disposition') or {}
    req(t.get('solarDepressionDeg')==12.25 and t.get('status')=='DEFERRED_OUTSIDE_V1_CORE_DOMAIN','train0037 disposition drift')
    req(t.get('frozenPreregistrationPreserved') is True and t.get('preregistrationSha256')==TRAIN0037_PREREG,'train0037 frozen design drift')
    req(t.get('scientificExecutionAuthorized') is False and t.get('ordinal19AllocatedOrPreassigned') is False,'train0037 execution/ordinal boundary drift')

    ex=f.get('precisionExhaustedDeepTwilightTreatment') or {}
    req(ex.get('geometryCount')==13 and ex.get('existingTreatmentSha256')==EXHAUSTED_SHA,'precision exhausted universe drift')
    req(ex.get('remainRefusedAsTrainingLabels') is True and ex.get('rescueOrContinuationAuthorized') is False,'precision exhausted treatment weakened')

    staged=f.get('stagedFutureExpansion') or {}
    req(staged.get('v1CoreSolarDepressionDeg')=={'minInclusive':2.0,'maxInclusive':10.5},'staged v1 core drift')
    req(staged.get('transitionBandSolarDepressionDeg')=={'minExclusive':10.5,'maxInclusive':12.5},'transition band drift')
    req(staged.get('deepTwilightSolarDepressionDeg')=={'minExclusive':12.5},'deep twilight band drift')
    req(staged.get('expansionRequiresSeparateReviewedCampaign') is True,'future expansion gate drift')

    rb=d.get('governanceRebase') or {}
    req(rb.get('sourceAdmissionDecisionSha256')==ADMISSION_SHA,'rebase source drift')
    req(rb.get('supersededPriorRule')=='MODEL_FITTING_REQUIRES_TRAIN0037_FINAL_TREATMENT','prior rule identity drift')
    req(rb.get('replacementRule')=='TRAIN0037_IS_DEFERRED_OUTSIDE_V1_CORE_AND_IS_NOT_A_PREREQUISITE_FOR_A_FUTURE_SEPARATELY_REVIEWED_V1_CORE_MODELING_PROTOCOL','replacement rule drift')
    req(rb.get('futureV1CoreModelingMayProceedWithoutTrain0037OnlyAfterSeparateCampaignAndModelingReview') is True,'future modeling rebase drift')
    req(rb.get('noModelFittingAuthorizedByThisDecision') is True,'model fitting accidentally authorized by rebase')

    nb=d.get('nextBoundary') or {}
    req(nb.get('nextAllowedGovernanceWork')=='PREPARE_SINGLE_TIER2_CORE_CAMPAIGN_CONTRACT_AFTER_THIS_SCOPE_DECISION_IS_REVIEWED_AND_MERGED','next governance boundary drift')
    req(nb.get('artifactPipelineReplayRequiredBeforeAnyNewSolverJob') is True,'artifact replay gate removed')
    req(nb.get('campaignExecutionAuthorizedNow') is False and nb.get('noAutomaticTransition') is True and nb.get('ordinal19AllocationAllowedNow') is False,'next boundary opened')

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--decision',required=True); a=ap.parse_args()
    d=json.loads(Path(a.decision).read_text(encoding='utf-8'))
    validate_data(d)
    print('LEVEL_B_V1_DOMAIN_SCOPE_DECISION_VALID')
    return 0
if __name__=='__main__': raise SystemExit(main())
