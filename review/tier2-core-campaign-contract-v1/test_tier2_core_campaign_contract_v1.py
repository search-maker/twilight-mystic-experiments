#!/usr/bin/env python3
from __future__ import annotations
import copy, importlib.util, json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('validator',ROOT/'validate_tier2_core_campaign_contract_v1.py'); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
BASE=json.loads((ROOT/'tier2-core-campaign-contract-v1.json').read_text())
mod.validate_data(BASE)
def rehash(d): d['contractSha256']=None; d['contractSha256']=mod.self_hash_null(d,'contractSha256')
def mutate(path,value):
    d=copy.deepcopy(BASE); cur=d
    for k in path[:-1]: cur=cur[k]
    cur[path[-1]]=value; rehash(d); return d
mutations=[
 (['decisionSemantics','newScientificExecutionAuthorized'],True),
 (['decisionSemantics','scientificOrdinalAllocated'],True),
 (['decisionSemantics','nextScientificOrdinal'],19),
 (['decisionSemantics','modelFittingAuthorized'],True),
 (['decisionSemantics','protectedHoldoutOpeningAuthorized'],True),
 (['coreSelection','geometryCount'],26),
 (['coreSelection','blocksPerGeometry'],2),
 (['executionStaging','mode'],'SAME_BATCH'),
 (['executionStaging','sameBatchHoldoutExecutionAllowedNow'],True),
 (['executionStaging','perGeometryAuthorizationAllowed'],True),
 (['executionStaging','stage1','scientificExecutionAuthorized'],True),
 (['executionStaging','stage2','scientificValuesReadableBeforeRequiredFreeze'],True),
 (['artifactPipelineReplayGate','requiredBeforeAnySolverJob'],False),
 (['artifactPipelineReplayGate','status'],'SATISFIED'),
 (['physicalInputContract','solarDepressionDeg','maxInclusive'],12.5),
 (['physicalInputContract','altitudeShortcutAllowed'],True),
 (['deploymentSupportContract','designBoxEqualsValidatedDeploymentSupport'],True),
 (['deploymentSupportContract','silentExtrapolationAllowed'],True),
 (['spectralTargetContract','epsilonSubstitutionAllowed'],True),
 (['spectralTargetContract','holdoutResultsMayTriggerRepresentationChange'],True),
 (['validationContract','p90OrP95AsPrincipalStatisticAllowed'],True),
 (['validationContract','perCaseCeilingRequired'],False),
 (['seedLedger','firstSeed'],1700000001),
 (['seedLedger','globalCollisionAuditStillRequiredBeforeAuthorization'],False),
 (['legacyExclusions','train0037Status'],'ACTIVE'),
 (['legacyExclusions','ordinal19AllocatedOrPreassigned'],True),
 (['legacyExclusions','precisionExhaustedRescueOrContinuationAuthorized'],True),
 (['sourceBindings','liveMainAtFreeze'],'0'*40),
]
for p,v in mutations:
    bad=mutate(p,v)
    try: mod.validate_data(bad)
    except mod.Refusal: pass
    else: raise SystemExit(f'mutation accepted: {p}')
# Direct manifest tamper with valid self-hash
bad=copy.deepcopy(BASE); bad['geometryManifest'][0]['sunDepressionDeg']=10.5; rehash(bad)
try: mod.validate_data(bad)
except mod.Refusal: pass
else: raise SystemExit('geometry manifest tamper accepted')
bad=copy.deepcopy(BASE); bad['derivedCaseManifestSha256']='0'*64; rehash(bad)
try: mod.validate_data(bad)
except mod.Refusal: pass
else: raise SystemExit('derived case-manifest digest tamper accepted')
bad=copy.deepcopy(BASE); bad['contractSha256']='0'*64
try: mod.validate_data(bad)
except mod.Refusal: pass
else: raise SystemExit('self-hash tamper accepted')
print(f'PASS: {len(mutations)+3} independent fail-closed mutations refused')
