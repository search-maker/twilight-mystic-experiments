#!/usr/bin/env python3
from __future__ import annotations
import copy, importlib.util, json
from pathlib import Path

HERE=Path(__file__).resolve().parent
SPEC=importlib.util.spec_from_file_location('validator',HERE/'validate_tier2_stage1_authorization_implementation_v1.py')
V=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(V)
B=json.loads((HERE/'tier2-stage1-authorization-implementation-v1.json').read_text(encoding='utf-8'))
V.validate(B)

def mutated(path:list[str], value):
    d=copy.deepcopy(B); cur=d
    for key in path[:-1]: cur=cur[key]
    cur[path[-1]]=value
    d['implementationSha256']=V.selfhash(d)
    return d

def must_refuse(path:list[str], value)->None:
    try: V.validate(mutated(path,value))
    except V.Refusal: return
    raise SystemExit(f'accepted forbidden mutation: {path}={value!r}')

MUTATIONS=[
    (['schemaVersion'],2),
    (['implementationId'],'wrong'),
    (['governance'],'MYSTIC-STATE-0066'),
    (['status'],'AUTHORIZED'),
    (['sourceBindings','liveMainAtFreeze'],'0'*40),
    (['sourceBindings','tier2CoreCampaignContractSha256'],'0'*64),
    (['sourceBindings','artifactReplayResultSha256'],'0'*64),
    (['sourceBindings','artifactReplayGateStatus'],'REQUIRED_NOT_YET_SATISFIED'),
    (['sourceBindings','latestConsumedScientificOrdinal'],19),
    (['stage1Scope','trainingGeometryCount'],18),
    (['stage1Scope','trainingCaseCount'],75),
    (['stage1Scope','configuredPhotonHistories'],1),
    (['stage1Scope','derivedTrainingCaseManifestSha256'],'0'*64),
    (['stage1Scope','derivedTrainingSeedLedgerSha256'],'0'*64),
    (['stage1Scope','protectedHoldoutValuesReadable'],True),
    (['stage1Scope','protectedHoldoutExecutionAuthorized'],True),
    (['seedCollisionReviewAudit','status'],'PASSED_AUTHORIZATION'),
    (['seedCollisionReviewAudit','candidateLedgerSeedCount'],99),
    (['seedCollisionReviewAudit','selfLedgerMatchesIgnored'],False),
    (['seedCollisionReviewAudit','prepublicationSearchSnapshot','repositoryCodeExternalMatchCount'],1),
    (['seedCollisionReviewAudit','prepublicationSearchSnapshot','pullRequestExternalMatchCount'],1),
    (['seedCollisionReviewAudit','prepublicationSearchSnapshot','issue60ExternalMatchCount'],1),
    (['seedCollisionReviewAudit','trackedTreeExactHeadScanRequiredInReviewCI'],False),
    (['seedCollisionReviewAudit','knownArtifactSeedIdentityClosureMustBeRecheckedImmediatelyBeforeAuthorization'],False),
    (['seedCollisionReviewAudit','repositoryGlobalDuplicateRunSeedProvenanceGuardRequiredImmediatelyBeforeAuthorization'],False),
    (['seedCollisionReviewAudit','authorizationPermittedByThisReviewAudit'],True),
    (['authorizationTemplate','enabled'],True),
    (['authorizationTemplate','campaignAuthorizationIssued'],True),
    (['authorizationTemplate','scientificExecutionAuthorized'],True),
    (['authorizationTemplate','scientificOrdinal'],19),
    (['authorizationTemplate','authorizationRef'],'refs/heads/authorization/tier2-stage1'),
    (['authorizationTemplate','executionKey'],'tier2-stage1:19'),
    (['authorizationTemplate','workflowDispatchEnabled'],True),
    (['authorizationTemplate','modelFittingAuthorized'],True),
    (['authorizationTemplate','protectedHoldoutOpeningAuthorized'],True),
    (['nextBoundary','separateAuthorizationTransitionRequired'],False),
    (['nextBoundary','ordinal19AllocationAllowedByThisImplementation'],True),
    (['nextBoundary','scientificExecutionAutomaticAfterMerge'],True),
    (['nextBoundary','stage2RemainsClosed'],False),
]
for p,v in MUTATIONS: must_refuse(p,v)

tamper=copy.deepcopy(B); tamper['implementationSha256']='0'*64
try: V.validate(tamper)
except V.Refusal: pass
else: raise SystemExit('accepted self-hash tamper')

print(f'PASS: {len(MUTATIONS)+1} fail-closed mutations refused')
