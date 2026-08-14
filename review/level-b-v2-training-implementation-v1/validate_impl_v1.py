#!/usr/bin/env python3
import json, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
IMPL=Path(__file__).with_name('implementation-v1.json')
PREFIT=ROOT/'review/level-b-v2-training-prefit-freeze-v1/protocol-v1.json'
EXPECTED_BLOB='5c5c2a6adcabc123552b20a6c32db4cf2cd4860d'

def req(c,m):
    if not c: raise RuntimeError(m)

d=json.loads(IMPL.read_text())
req((d.get('schemaVersion'),d.get('implementationId'),d.get('status'),d.get('governance'))==(1,'level-b-v2-training-implementation-v1','REVIEW_ONLY_IMPLEMENTATION_NO_REAL_TRAINING_ON_PR','MYSTIC-STATE-0068'),'implementation identity drift')
p=d['prefitFreeze']; req((p['protocolPath'],p['protocolGitBlobSha'],p['protocolId'],p['candidateCount'],p['cvFoldCount'])==('review/level-b-v2-training-prefit-freeze-v1/protocol-v1.json',EXPECTED_BLOB,'level-b-v2-training-only-prefit-freeze-v1',100,59),'prefit binding drift')
blob=subprocess.check_output(['git','hash-object',str(PREFIT)],text=True).strip(); req(blob==EXPECTED_BLOB,f'prefit blob drift: {blob}')
s=d['sourceTrainingRepresentation']; req((s['artifactId'],s['artifactDigest'],s['datasetFileSha256'],s['datasetCanonicalSha256'],s['trainingGeometryCount'])==(9208203541,'sha256:2fe50ed674155f440322c92d28877f5c022f0cc5fa13e1e601596a9902482815','066d6be846fa9b3bdd7236e327894f64d52ea56aa7e7b6e6af4d51d849eb1a61','bb7908426d9d545f43c082aebbaab1829a486e2962d0b9ee34a5e8bef5390133',44),'source binding drift')
n=d['numericalImplementation']; req((n['pythonVersion'],n['numpyVersion'],n['dtype'],n['randomnessAllowed'])==('3.12','2.3.2','float64',False),'numerical binding drift')
e=d['executionSurface']; req(e['reviewPullRequestMayDownloadRealTrainingArtifact'] is False and e['reviewPullRequestMayExecuteRealFit'] is False and e['reviewPullRequestMayExecuteSyntheticFits'] is True,'review boundary drift'); req(e['activationBranch']=='postprocess/level-b-v2-training-fit-v1' and e['githubRunAttemptRequired']==1 and e['githubRerunRetryResumeAllowed'] is False,'activation boundary drift')
b=d['boundaries']
for k in ('ordinal22ValuesMayBeRead','protectedValidationAuthorized','newMysticSolverExecutionAuthorized','productionPromotionAuthorized','workerBLaneReactivated','workerCLaneReactivated'): req(b[k] is False,f'opened boundary: {k}')
print('VALID_IMPLEMENTATION_BINDING')
