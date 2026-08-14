#!/usr/bin/env python3
from __future__ import annotations
import copy, importlib.util, json
from pathlib import Path
R=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('v',R/'validate_transport_v1.py'); v=importlib.util.module_from_spec(s); s.loader.exec_module(v)
B=json.loads((R/'tier2-stage1-execution-transport-v1.json').read_text()); v.validate(B)
def mutate(path,value):
    d=copy.deepcopy(B); x=d
    for k in path[:-1]: x=x[k]
    x[path[-1]]=value; d['contractSha256']=None; d['contractSha256']=v.selfhash(d); return d
M=[
 (['sourceBindings','latestConsumedScientificOrdinal'],20),(['sourceBindings','campaignContractSha256'],'0'*64),(['sourceBindings','stage1ImplementationSha256'],'0'*64),(['sourceBindings','artifactReplayResultSha256'],'0'*64),
 (['runtimeIdentityRequired','uvspecSha256'],'0'*64),(['runtimeIdentityRequired','exactPackageSpec'],'latest'),(['frozenStage1','geometryCount'],20),(['frozenStage1','caseCount'],100),(['frozenStage1','configuredPhotonHistories'],1),(['frozenStage1','manifestSha256'],'0'*64),(['frozenStage1','protectedHoldoutValuesReadable'],True),(['frozenStage1','stage2Included'],True),
 (['seedAudit','candidateFirstSeed'],1),(['seedAudit','candidateLastSeed'],2),(['seedAudit','candidateSeedCount'],99),(['seedAudit','all100MustBeRecheckedAtAuthorizationAndDispatch'],False),
 (['authorization','separateOneFileAuthorizationCommitRequired'],False),(['authorization','repositoryGlobalBranchesRunsArtifactsIssue60RecheckRequired'],False),(['authorization','trackedTreeAll100SeedRecheckRequired'],False),
 (['recovery','priorFailedPresolverDispatch','runId'],0),(['recovery','priorFailedPresolverDispatch','caseJobCount'],1),(['recovery','priorFailedPresolverDispatch','solverExecutionCount'],1),(['recovery','priorFailedPresolverDispatch','allowedArtifacts'],[]),
 (['workflows','workflowDispatchAllowed'],True),(['workflows','githubRerunAllowed'],True),(['executionBoundary','transportMergeAuthorizesScience'],True),(['executionBoundary','scientificOrdinalAllocated'],True),(['executionBoundary','authorizationIssued'],True),(['executionBoundary','dispatchIssued'],True),(['executionBoundary','protectedHoldoutOpeningAuthorized'],True),(['executionBoundary','stage2Authorized'],True),(['executionBoundary','modelFittingAuthorized'],True),(['nextBoundary','ordinal20AllocationAllowedByTransport'],True),(['nextBoundary','automaticDispatchAfterTransportMerge'],True)]
for path,value in M:
    try:v.validate(mutate(path,value))
    except v.Refusal: pass
    else: raise AssertionError(f'mutation accepted: {path}')
print(f'PASS: {len(M)} fail-closed transport mutations refused')
