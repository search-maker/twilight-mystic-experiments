#!/usr/bin/env python3
import json, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
IMPL=Path(__file__).with_name('implementation-v2.json')
PREFIT=ROOT/'review/level-b-v2-training-prefit-freeze-v2/protocol-v2.json'
G1=ROOT/'review/level-b-v2-training-fit-result-v1/result-v1.json'
PREFIT_BLOB='91ab4c109a209d3ee9ee24e327c554739cd9dd6c'
G1_BLOB='c7ca202d55113b59369a4e74a94cc80cc47eca71'
def req(c,m):
    if not c: raise RuntimeError(m)
d=json.loads(IMPL.read_text())
req((d.get('schemaVersion'),d.get('implementationId'),d.get('status'),d.get('governance'))==(2,'level-b-v2-training-implementation-v2','REVIEW_ONLY_GENERATION2_IMPLEMENTATION_NO_REAL_TRAINING_ON_PR','MYSTIC-STATE-0068'),'implementation identity drift')
req(d.get('sourceMainAtImplementationReview')=='3c119d6b4b820900bd3e9b67c3b6ef8d60127298','implementation base drift')
p=d['prefitFreeze']; req((p['protocolPath'],p['protocolGitBlobSha'],p['protocolId'],p['candidateCount'],p['cvFoldCount'])==('review/level-b-v2-training-prefit-freeze-v2/protocol-v2.json',PREFIT_BLOB,'level-b-v2-training-only-prefit-freeze-v2',230,59),'prefit binding drift')
req(subprocess.check_output(['git','hash-object',str(PREFIT)],text=True).strip()==PREFIT_BLOB,'prefit blob drift')
g=d['generation1Result']; req((g['path'],g['gitBlobSha'],g['status'],g['remainsFailed'])==('review/level-b-v2-training-fit-result-v1/result-v1.json',G1_BLOB,'TRAINING_ONLY_NO_ELIGIBLE_CANDIDATE_NO_MODEL_FROZEN',True),'generation1 binding drift'); req(subprocess.check_output(['git','hash-object',str(G1)],text=True).strip()==G1_BLOB,'generation1 result blob drift')
s=d['sourceTrainingRepresentation']; req((s['artifactId'],s['artifactDigest'],s['datasetFileSha256'],s['datasetCanonicalSha256'],s['trainingGeometryCount'],s['protectedRecordCount'])==(9208203541,'sha256:2fe50ed674155f440322c92d28877f5c022f0cc5fa13e1e601596a9902482815','066d6be846fa9b3bdd7236e327894f64d52ea56aa7e7b6e6af4d51d849eb1a61','bb7908426d9d545f43c082aebbaab1829a486e2962d0b9ee34a5e8bef5390133',44,0),'source binding drift')
n=d['numericalImplementation']; req((n['pythonVersion'],n['numpyVersion'],n['dtype'],n['randomnessAllowed'])==('3.12','2.3.2','float64',False),'numerical drift')
e=d['executionSurface']; req(e['reviewPullRequestMayDownloadRealTrainingArtifact'] is False and e['reviewPullRequestMayExecuteRealFit'] is False and e['reviewPullRequestMayExecuteSyntheticFits'] is True,'review execution boundary drift'); req((e['activationBranch'],e['activationFile'],e['githubRunAttemptRequired'],e['githubRerunRetryResumeAllowed'])==('postprocess/level-b-v2-training-fit-v2','review/level-b-v2-training-implementation-v2/activation.json',1,False),'activation binding drift')
b=d['boundaries']; req(b['generation1ResultRemainsFailed'] is True,'generation1 retroactive state drift')
for k in ('ordinal22ValuesMayBeRead','protectedValidationAuthorized','newMysticSolverExecutionAuthorized','productionPromotionAuthorized','workerBLaneReactivated','workerCLaneReactivated'): req(b[k] is False,f'opened boundary: {k}')
print('VALID_IMPLEMENTATION_V2_BINDING')
