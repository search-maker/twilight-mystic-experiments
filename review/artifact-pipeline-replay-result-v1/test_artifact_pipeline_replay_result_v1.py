#!/usr/bin/env python3
import copy,importlib.util,json
from pathlib import Path
R=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('v',R/'validate_artifact_pipeline_replay_result_v1.py');v=importlib.util.module_from_spec(s);s.loader.exec_module(v)
B=json.loads((R/'artifact-pipeline-replay-result-v1.json').read_text());v.validate(B)
def bad(path,val):
 d=copy.deepcopy(B); c=d
 for k in path[:-1]: c=c[k]
 c[path[-1]]=val; d['resultSha256']=None; d['resultSha256']=v.selfhash(d); return d
M=[(['decisionSemantics','artifactReplayGateSatisfied'],False),(['decisionSemantics','newScientificExecutionAuthorized'],True),(['decisionSemantics','campaignAuthorizationIssued'],True),(['decisionSemantics','scientificOrdinalAllocated'],True),(['decisionSemantics','nextScientificOrdinal'],19),(['decisionSemantics','protectedHoldoutOpeningAuthorized'],True),(['replayRun','runAttempt'],2),(['replayRun','conclusion'],'failure'),(['replayRun','headSha'],'0'*40),(['candidateArtifact','artifactId'],1),(['candidateArtifact','githubDigest'],'sha256:'+'0'*64),(['candidateArtifact','expiredAtResultFreeze'],True),(['attestation','trainingCaseArtifactCount'],165),(['attestation','trainingGeometryCount'],38),(['attestation','holdoutValuesRead'],True),(['attestation','rawExactZeroCaseCount'],14),(['replaySurfaceResults','AGGREGATE_AND_INDEPENDENT_AUDIT'],False),(['sourceBindings','liveMainAtFreeze'],'0'*40),(['nextBoundary','globalSeedCollisionAuditRequiredBeforeAnyAuthorization'],False)]
for p,x in M:
 try:v.validate(bad(p,x))
 except v.Refusal:pass
 else:raise SystemExit(f'accepted {p}')
d=copy.deepcopy(B);d['resultSha256']='0'*64
try:v.validate(d)
except v.Refusal:pass
else:raise SystemExit('accepted selfhash tamper')
print(f'PASS: {len(M)+1} fail-closed mutations refused')
