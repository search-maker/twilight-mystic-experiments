#!/usr/bin/env python3
import argparse,copy,hashlib,json
from pathlib import Path
class Refusal(RuntimeError): pass
def req(c,m):
    if not c: raise Refusal(m)
def canon(v): return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def selfhash(d):
    x=copy.deepcopy(d); x['resultSha256']=None; return hashlib.sha256(canon(x)).hexdigest()
EXPECTED_RESULT='ea682afb1c5f1e1f18cdca1c2bc61be2701f9364dabbc6a9723d9ffc6e48349d'
ZERO=['train-0039-precision-continuation-wave2-v1-b5','train-0047-alis-b1','train-0047-precision-continuation-wave2-v1-b6','train-0047-precision-continuation-wave3-v1-b8']
SURF=['INPUT_RENDER_AND_PHYSICAL_FINGERPRINT','PREPARED_CASE_BINDING','CASE_RESULT_AND_RAW_SPECTRUM_HASHING','TRANSPORT_ARTIFACT_ID_AND_DIGEST_BINDING','FULL_SPECTRUM_DERIVED_CHANNEL_REINTEGRATION','AGGREGATE_AND_INDEPENDENT_AUDIT','TRAINING_HANDOFF_ROLE_EXCLUSION']
def validate(d):
    req(d.get('schemaVersion')==1 and d.get('resultId')=='public-artifact-pipeline-replay-result-v1','identity')
    req(d.get('governance')=='MYSTIC-STATE-0067' and d.get('status')=='REVIEW_ONLY_ARTIFACT_PIPELINE_REPLAY_RESULT_BINDING_NO_SCIENCE','status')
    req(d.get('resultSha256')==EXPECTED_RESULT==selfhash(d),'selfhash')
    s=d['sourceBindings']; req(s=={'liveMainAtFreeze':'17117e4120eac2bcefcefea7fa3c19d88712b063','preregistrationMergedCommit':'17117e4120eac2bcefcefea7fa3c19d88712b063','preregistrationReviewedHead':'dda9170a902b04b365d3602484b01b3dfac34528','preregistrationProtocolPath':'review/artifact-pipeline-replay-v1/artifact-pipeline-replay-protocol-v1.json','preregistrationProtocolSha256':'7e7ba291fc633be96cb51dc36dae7b0ad6fb9eda0ae90d839f915f591aca608d','tier2CoreCampaignContractSha256':'5043929fdf13aaf90c9face0c380b514999a52a7226079807969a74469764f93'},'source bindings')
    r=d['replayRun']; req(r=={'runId':31699141872,'runAttempt':1,'event':'pull_request','status':'completed','conclusion':'success','headSha':'dda9170a902b04b365d3602484b01b3dfac34528','workflowPath':'.github/workflows/artifact-pipeline-replay-v1-review.yml'},'run')
    a=d['candidateArtifact']; req(a=={'artifactId':9180525837,'name':'artifact-pipeline-replay-v1-candidate','sizeInBytes':68996,'expiredAtResultFreeze':False,'zipSha256':'cbfe39fc05da10509a419b6d619f5387110aa47992e4fcc69ae6df1c64190dd1','githubDigest':'sha256:cbfe39fc05da10509a419b6d619f5387110aa47992e4fcc69ae6df1c64190dd1'},'artifact')
    f=d['candidateFiles']; req(f['artifact-pipeline-replay-attestation.json']=={'rawSha256':'4bf6be072a3faa2c569110eea8a7f55f860032a41d9c6fc1a63791c638686809','sizeBytes':3886} and f['training-handoff-replay.json']=={'rawSha256':'30222629289c71f7659cda8f875b3118d855f29f0b2f7e875d6cee42f7f9c4e4','sizeBytes':339850} and f['transport-manifest.json']=={'rawSha256':'c2d4bea6b7d12562ed21db3fbe8ab9bc4771e433594be9d381e179d82dbd3ee7','sizeBytes':94251},'candidate files')
    at=d['attestation']; req(at['attestationSha256']=='0623a4b9ce3441e633dbae79fef61a32a15e8900efa27739645b4febf74c1d9f' and at['replayHeadSha']=='dda9170a902b04b365d3602484b01b3dfac34528' and at['githubPullRequestMergeTestSha']=='b3a8060415da83ae6eab198695edfc5aa08eeb7f','attestation identity')
    req(at['transportManifestSha256']=='0dbbe58c6e08e84438a1c878f1d04ae04d645554b87fdb78d84e99c958d34c27' and at['replayDatasetSha256']=='b7323ec1c6fbf8d82c32430c5b387d7f68a457b44b15d1ae53cd9b89cfb5c361' and at['physicalInputFingerprintManifestSha256']=='cb9f2fb9d7a2dae0a65fc2cf072c9f385897ba04c5ee00a807d65abc09481437','result hashes')
    req((at['trainingCaseArtifactCount'],at['trainingGeometryCount'],at['internalHoldoutGeometryCountExcluded'],at['holdoutValuesRead'],at['holdoutRecordCount'])==(166,39,9,False,0),'universe')
    req(at['rawExactZeroCaseCount']==4 and at['rawExactZeroCaseIds']==ZERO and at['rawExactZeroCaseSetSha256']=='ccd9fcc9daa8b7984da0764d76210ea7d121e9d146b0bf469f05fd5110fcd0a4','zeros')
    req(d['replaySurfaceResults']=={k:True for k in SURF},'surfaces')
    sem=d['decisionSemantics']; req(sem['artifactReplayGateSatisfied'] is True and sem['artifactReplayGateStatus']=='SATISFIED_BY_REVIEWED_EXISTING_ARTIFACT_REPLAY','gate')
    for k in ['campaignAuthorizationIssued','campaignDispatchIssued','newScientificExecutionAuthorized','scientificOrdinalAllocated','modelFittingAuthorized','modelSelectionAuthorized','protectedHoldoutOpeningAuthorized','productionPromotionAuthorized','train0037ExecutionAuthorized']: req(sem[k] is False,k)
    req(sem['nextScientificOrdinal'] is None,'ordinal')
    nb=d['nextBoundary']; req(nb['nextAllowedWork']=='PREPARE_REVIEW_ONLY_TIER2_STAGE1_AUTHORIZATION_IMPLEMENTATION_WITH_FRESH_GLOBAL_SEED_COLLISION_AUDIT','next')
    req(nb['campaignAuthorizationAutomaticAfterMerge'] is False and nb['scientificExecutionAutomaticAfterMerge'] is False and nb['ordinal19AllocationAllowedByThisResult'] is False and nb['globalSeedCollisionAuditRequiredBeforeAnyAuthorization'] is True and nb['protectedHoldoutOpeningAllowedByThisResult'] is False and nb['modelFittingAllowedByThisResult'] is False,'next boundaries')
def main():
    p=argparse.ArgumentParser();p.add_argument('--result',required=True);a=p.parse_args();validate(json.loads(Path(a.result).read_text()));print('ARTIFACT_PIPELINE_REPLAY_RESULT_VALID')
if __name__=='__main__': main()
