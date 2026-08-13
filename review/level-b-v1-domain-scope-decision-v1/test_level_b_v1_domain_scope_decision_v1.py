#!/usr/bin/env python3
from __future__ import annotations
import copy, importlib.util, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
VPATH=ROOT/'validate_level_b_v1_domain_scope_decision_v1.py'
spec=importlib.util.spec_from_file_location('validator',VPATH); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
BASE=json.loads((ROOT/'level-b-v1-domain-scope-decision-v1.json').read_text())
mod.validate_data(BASE)

def rehash(d):
    d['decisionSha256']=None
    d['decisionSha256']=mod.self_hash_null(d,'decisionSha256')

def mutate(path,value):
    d=copy.deepcopy(BASE); cur=d
    for k in path[:-1]: cur=cur[k]
    cur[path[-1]]=value; rehash(d); return d

mutations=[
 (['frozenScope','intendedPhysicalDesignBox','solarDepressionDeg','maxInclusive'],12.5),
 (['decisionSemantics','newScientificExecutionAuthorized'],True),
 (['decisionSemantics','modelFittingAuthorized'],True),
 (['decisionSemantics','ordinal19Allocated'],True),
 (['decisionSemantics','train0037Status'],'ACTIVE_CONTINUATION'),
 (['frozenScope','deploymentSupportPolicy','designBoxEqualsValidatedDeploymentSupport'],True),
 (['frozenScope','deploymentSupportPolicy','silentExtrapolationAllowed'],True),
 (['frozenScope','campaignGovernancePolicy','unitOfGovernance'],'GEOMETRY'),
 (['frozenScope','campaignGovernancePolicy','perGeometryAuthorizationDispatchLifecycleAllowed'],True),
 (['frozenScope','protectedHoldoutPolicy','sameBatchExecutionAllowedOnlyWithGenuineTechnicalSealing'],False),
 (['frozenScope','protectedHoldoutPolicy','fallbackIfGenuineSealingUnavailable','trainingJobsFirst'],100),
 (['frozenScope','computationalValidationProtocol','p90OrP95AsPrincipalStatisticAllowed'],True),
 (['frozenScope','computationalValidationProtocol','perCaseCeilingRequired'],False),
 (['frozenScope','trainingOnlySpectralAdequacyGate','requiredBeforeHoldoutOpening'],False),
 (['frozenScope','trainingOnlySpectralAdequacyGate','holdoutResultsMayTriggerRepresentationChange'],True),
 (['frozenScope','atmosphereContract','altitudeShortcutAllowed'],True),
 (['frozenScope','atmosphereContract','localSurfaceZoutKm'],2.0),
 (['frozenScope','precisionExhaustedDeepTwilightTreatment','geometryCount'],12),
 (['frozenScope','precisionExhaustedDeepTwilightTreatment','remainRefusedAsTrainingLabels'],False),
 (['frozenScope','train0037Disposition','ordinal19AllocatedOrPreassigned'],True),
 (['governanceRebase','futureV1CoreModelingMayProceedWithoutTrain0037OnlyAfterSeparateCampaignAndModelingReview'],False),
 (['nextBoundary','campaignExecutionAuthorizedNow'],True),
 (['sourceBindings','liveMainAtFreeze'],'0'*40),
]
for path,value in mutations:
    bad=mutate(path,value)
    try: mod.validate_data(bad)
    except mod.Refusal: pass
    else: raise SystemExit(f'mutation accepted: {path}')

bad=copy.deepcopy(BASE); bad['decisionSha256']='0'*64
try: mod.validate_data(bad)
except mod.Refusal: pass
else: raise SystemExit('self-hash tamper accepted')
print(f'PASS: {len(mutations)+1} independent fail-closed mutations refused')
