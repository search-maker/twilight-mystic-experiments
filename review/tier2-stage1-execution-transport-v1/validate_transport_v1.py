#!/usr/bin/env python3
from __future__ import annotations
import argparse, copy, hashlib, json
from pathlib import Path
from typing import Any
CID='public-tier2-v1-core-stage1-execution-transport-v1'; STATUS='REVIEW_ONLY_EXECUTION_TRANSPORT_NO_AUTHORIZATION_NO_SCIENCE'; GOV='MYSTIC-STATE-0067'
MAIN='d3d9de3c1e46ae8fb1c1f9a4e03ade68973da19a'; CAM='5043929fdf13aaf90c9face0c380b514999a52a7226079807969a74469764f93'; IMP='e7d688754333d9b1d1a7266fec995e821f0c78abaa5631987e3fa8e2526c6fed'; REP='ea682afb1c5f1e1f18cdca1c2bc61be2701f9364dabbc6a9723d9ffc6e48349d'; MAN='7351a47582ca0a328059256566b24ce10c0e6ff5d802f53ff35e133540a83819'
class Refusal(RuntimeError):pass
def req(c,m):
    if not c: raise Refusal(m)
def canon(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def selfhash(d):
    x=copy.deepcopy(d);x['contractSha256']=None;return canon(x)
def raw(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def validate(d:dict[str,Any],repo_root:Path|None=None)->None:
    req((d.get('schemaVersion'),d.get('contractId'),d.get('status'),d.get('governance'))==(1,CID,STATUS,GOV),'identity/status drift'); req(d.get('contractSha256')==selfhash(d),'contract selfhash drift')
    s=d.get('sourceBindings') or {}; req(s.get('liveMainAtFreeze')==MAIN and s.get('latestConsumedScientificOrdinal')==19,'main/ordinal drift'); req(s.get('campaignContractSha256')==CAM and s.get('stage1ImplementationSha256')==IMP and s.get('artifactReplayResultSha256')==REP,'source selfhash binding drift')
    req(s.get('campaignContractGitBlobSha')=='dc69f67829cf7412e8e9374f005d92842bd500ca' and s.get('stage1ImplementationGitBlobSha')=='276b9fb82eeb1564ae7f406c85d03a80a8373b8a' and s.get('artifactReplayResultGitBlobSha')=='4dd550f6a9b31c3a67a213feb51a4209a0b25f40','source blob binding drift')
    req(s.get('replayHistoricalBuilderGitBlobSha')=='9bc53956fc4a49935ba2957087d8bf4203b7e8be' and s.get('referenceFullSpectrumPilotExecutorGitBlobSha')=='4d4ee9af433157182185784ded162fb139c9fa2d' and s.get('referenceTier1AltitudeAdapterGitBlobSha')=='b00252709ca9ea41c6bf8b3ab59f8cdb8a2fc7bd' and s.get('referenceCrossGeometryAdapterGitBlobSha')=='8d4416fceb323876b24fb98bfa6192cb235a6d4b','historical pipeline binding drift')
    req(s.get('runtimeProbeGitBlobSha')=='519115a4dd382b8ae82ae4c820398c9f4388a139' and s.get('runtimeLockGitBlobSha')=='8573f62829371a0eb866976a5062ea61dc0767b1','runtime source blob drift')
    r=d.get('runtimeIdentityRequired') or {}; req(r=={'libRadtranVersion':'2.0.6-MYSTIC','uvspecSha256':'2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3','uvspecHelpSha256':'868aea5af762d968f6f62c4e1472916d25232ed9cab5be112d753b0823d20548','libRadtranDataTreeSha256':'ad30b49177e9c84e46497d69faf0c75e466996b0d0003f1de210289ae9f847d7','atmosphereSha256':'dab26290ed81c762ed0c607e5dc2d53393c1462a0c3a528bc5e3f5935191cfb5','runtimeLockRawSha256':'3b5fbec964642b04c73a6423b3355dbcc4ba5e84f9614f6d74420491bacc20c5','exactPackageSpec':'rubin-libradtran=2.0.6=py312pl5321he9373c2_1','python':'3.12.4','runner':'ubuntu-24.04'},'runtime identity drift')
    f=d.get('frozenStage1') or {}; req((f.get('geometryCount'),f.get('caseCount'),f.get('configuredPhotonHistories'),f.get('manifestSha256'))==(19,76,2_120_000_000,MAN),'stage1 manifest/accounting drift'); req(f.get('derivedTrainingCaseManifestSha256')=='8651ec7e9b430c418cc5717afa221513e2a4ebff55f2caefddf8730c20a1ee89' and f.get('derivedTrainingSeedLedgerSha256')=='a5905c464fee13dc388ca57310f29fcd97379f7974a71cd50d745abe096b61ad','stage1 derived hashes drift'); req(f.get('protectedHoldoutGeometryCountExcluded')==6 and f.get('protectedHoldoutCaseCountExcluded')==24 and f.get('protectedHoldoutValuesReadable') is False and f.get('stage2Included') is False,'holdout exclusion drift')
    a=d.get('authorization') or {}; req(a.get('path')=='experiments/tier2-stage1-execution-v1/authorization.json' and a.get('fileMustBeAbsentInTransportReviewAndMergedTransport') is True and a.get('separateOneFileAuthorizationCommitRequired') is True and a.get('expectedFieldNames')==['schemaVersion','status','enabled','scientificOrdinal','authorizationBranch','dispatchBranch','executionKey','manifestSha256','transportContractSha256','exactAuthorizationParentCommit','scientificExecutionAuthorized','dispatchAuthorized','automaticDispatch','githubRerunAllowed','retryAllowed','resumeAllowed','solverExecutionPerformed','protectedHoldoutOpeningAuthorized','modelFittingAuthorized','modelSelectionAuthorized','productionPromotionAuthorized','stage2Authorized'],'authorization path/shape drift'); req(a.get('freshNextOrdinalDerivedFromRepositoryGlobalHistory') is True and a.get('repositoryGlobalBranchesRunsArtifactsIssue60RecheckRequired') is True and a.get('trackedTreeAll100SeedRecheckRequired') is True,'authorization guard drift')
    seed=d.get('seedAudit') or {}; req((seed.get('candidateFirstSeed'),seed.get('candidateLastSeed'),seed.get('candidateSeedCount'),seed.get('stage1SeedCount'),seed.get('reservedStage2SeedCount'))==(1_900_000_001,1_900_000_100,100,76,24),'seed ledger drift'); req(seed.get('all100MustBeRecheckedAtAuthorizationAndDispatch') is True and seed.get('numericUnderscoreNormalizationRequired') is True and seed.get('allowedIssue60SelfLedgerCommentIds')==[5279964834],'seed recheck drift')
    rec=((d.get('recovery') or {}).get('priorFailedPresolverDispatch') or {})
    req(rec.get('scientificOrdinal')==19 and rec.get('identityVersion')==3 and rec.get('branch')=='dispatch/tier2-stage1-ordinal19-v3' and rec.get('executionKey')=='tier2-core-stage1-v3:numerical:19','recovery identity drift')
    req(rec.get('headSha')=='66ed95ab7801a2b3a20bd54a4dced53bf6f9ee5c' and rec.get('runId')==31761751524 and rec.get('runAttempt')==1 and rec.get('conclusion')=='failure','recovery run binding drift')
    req(rec.get('caseJobCount')==0 and rec.get('caseArtifactCount')==0 and rec.get('solverExecutionCount')==0 and rec.get('failureClass')=='MATRIX_ARRAY_PLANNING_ZERO_CASE_JOBS','recovery pre-solver classification drift')
    req(rec.get('allowedArtifacts')==[{'artifactId':9204873878,'name':'tier2-stage1-preflight-66ed95ab7801a2b3a20bd54a4dced53bf6f9ee5c','digest':'sha256:e46f82583f766b7ba72980d6a265829f3744077e54a4e5356ab2e9aef28f1429'},{'artifactId':9204877503,'name':'tier2-stage1-aggregate-66ed95ab7801a2b3a20bd54a4dced53bf6f9ee5c','digest':'sha256:1a2ae921828174b9e1f8f4f0c0dc124116180dbcfd82f7c64075ea1f348efd39'}],'recovery artifact binding drift')
    w=d.get('workflows') or {}; req(w.get('executionTrigger')=='push branch dispatch/tier2-stage1-* only' and w.get('workflowDispatchAllowed') is False and w.get('githubRerunAllowed') is False,'workflow boundary drift')
    e=d.get('executionBoundary') or {}
    for k in ('transportMergeAuthorizesScience','scientificOrdinalAllocated','authorizationIssued','dispatchIssued','solverExecutionPerformed','modelFittingAuthorized','modelSelectionAuthorized','protectedHoldoutOpeningAuthorized','stage2Authorized','productionPromotionAuthorized'): req(e.get(k) is False,f'closed transport boundary drift: {k}')
    req(d.get('nextBoundary')=={'nextAllowedWork':'MERGE_TRANSPORT_AFTER_EXACT_HEAD_ATTEMPT1_REVIEW_THEN_CREATE_SEPARATE_ONE_FILE_STAGE1_AUTHORIZATION_IDENTITY_IF_FRESH_GLOBAL_GUARDS_PASS','ordinal20AllocationAllowedByTransport':False,'automaticDispatchAfterTransportMerge':False,'stage2RemainsClosed':True},'next boundary drift')
    if repo_root:
        comps=d.get('components') or {}; req(comps,'component hashes missing')
        for name,spec in comps.items():
            p=repo_root/spec['path']; req(p.is_file(),f'component missing: {name}'); req(raw(p)==spec['rawSha256'],f'component raw hash drift: {name}')
        m=json.loads((repo_root/'experiments/tier2-stage1-execution-v1/stage1-execution-manifest-v1.json').read_text()); x=copy.deepcopy(m); x['manifestSha256']=None; req(m.get('manifestSha256')==canon(x)==MAN,'frozen manifest selfhash drift'); req(len(m.get('geometries',[]))==19 and len(m.get('cases',[]))==76 and all(c.get('role')=='surrogate-training' for c in m['cases']),'frozen manifest role universe drift')
def main():
    p=argparse.ArgumentParser();p.add_argument('--contract',type=Path,required=True);p.add_argument('--repo-root',type=Path);a=p.parse_args()
    try:d=json.loads(a.contract.read_text());validate(d,a.repo_root.resolve() if a.repo_root else None);print('TIER2_STAGE1_EXECUTION_TRANSPORT_VALID');return 0
    except Exception as e:print(f'REFUSED: {e}');return 2
if __name__=='__main__':raise SystemExit(main())
