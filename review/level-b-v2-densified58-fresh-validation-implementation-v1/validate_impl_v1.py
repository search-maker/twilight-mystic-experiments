#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
IMPL=HERE/'implementation-v1.json'
CONTRACT=ROOT/'review/level-b-v2-densified58-fresh-validation-v1/contract-v1.json'
MODEL_RESULT=ROOT/'review/level-b-v2-training-fit-result-v3-densified58/result-v3.json'
TRAINER=ROOT/'review/level-b-v2-training-implementation-v3-densified58/train_v3.py'
OLD_EVAL=ROOT/'review/tier2-stage2-protected-holdout-v1/stage2_v1.py'
OLD_ADAPTER=ROOT/'experiments/tier2-stage2-execution-v1/adapter_v1.py'
OLD_EXECUTOR=ROOT/'experiments/tier2-stage2-execution-v1/executor_v1.py'
OLD_MANIFEST=ROOT/'experiments/tier2-stage2-execution-v1/build_manifest_v1.py'
EXPECTED={
 CONTRACT:'aad11350311ce3768488e64ed72edc3e48646ff9',
 MODEL_RESULT:'28ff90afa0de1734aa0b6718bc93ebdce1ded54a',
 TRAINER:'013768b9cb32050e698bc7b884921cbd5f1674e2',
 OLD_EVAL:'59cbff54a6393f138ac44fdbb553842f38e6db60',
 OLD_ADAPTER:'3b6c5f84dcc9948b1e02271c8469bcc5c461af97',
 OLD_EXECUTOR:'e55041b281501a837a6a4ed7c112036e7a1c810a',
 OLD_MANIFEST:'223d14cc13078534849e85a76970d39fff13238c',
}

def req(c,m):
    if not c: raise SystemExit('REFUSED: '+m)
def blob(path): return subprocess.check_output(['git','rev-parse','HEAD:'+str(path.relative_to(ROOT))],cwd=ROOT,text=True).strip()

d=json.loads(IMPL.read_text())
req((d.get('schemaVersion'),d.get('implementationId'),d.get('status'),d.get('governance'))==(1,'level-b-v2-densified58-fresh-validation-implementation-v1','REVIEW_ONLY_SYNTHETIC_AND_TRANSPORT_IMPLEMENTATION_NO_FRESH_VALUES_NO_AUTHORIZATION','MYSTIC-STATE-0070'),'implementation identity drift')
req(d.get('sourceMainAtImplementationReview')=='a3936735f2aaa1ada4d98ba37f02adab1b560b15','implementation base drift')
for path,want in EXPECTED.items(): req(blob(path)==want,f'git blob drift: {path}')
req(d['freshValidationContract']['gitBlobSha']==EXPECTED[CONTRACT] and d['freshValidationContract']['candidateScientificOrdinal']==24 and d['freshValidationContract']['reservedSeedFirst']==2101000001 and d['freshValidationContract']['reservedSeedLast']==2101000024,'contract binding drift')
req(d['frozenModel']['trainingResultBindingGitBlobSha']==EXPECTED[MODEL_RESULT] and d['frozenModel']['trainerGitBlobSha']==EXPECTED[TRAINER] and d['frozenModel']['modelCanonicalSha256']=='91ae5811e55b3d4ef872ab672f006c4b383c6581a53de67cd018b6eb2666f9a7','model binding drift')
ref=d['referenceImplementation']
req(ref['oldStage2EvaluatorGitBlobSha']==EXPECTED[OLD_EVAL] and ref['oldStage2AdapterGitBlobSha']==EXPECTED[OLD_ADAPTER] and ref['oldStage2ExecutorGitBlobSha']==EXPECTED[OLD_EXECUTOR] and ref['oldStage2ManifestBuilderGitBlobSha']==EXPECTED[OLD_MANIFEST],'reference binding drift')
req(d['frozenRepresentation']['artifactId']==9208203541 and d['frozenRepresentation']['packageSha256']=='2491ac91ed924f2ba69b37ea20f48d63f51d41146cd9fe50e0bd63bfb315a763','representation binding drift')
review=d['reviewSurface']; req(review['mayDownloadTrainingArtifacts'] is True and review['mayUseSyntheticCaseSpectra'] is True,'review safe inputs drift')
for k in ('mayReadFreshProtectedValues','mayExecuteMystic','mayCreateAuthorization','mayCreateDispatch'): req(review[k] is False,f'review boundary opened: {k}')
future=d['futureAuthorization']; req(future['separateOneFileDirectChildAuthorizationRequiredAfterImplementationMerge'] is True and future['authorizationMustRepeatLiveOrdinalAndSeedFreshnessProof'] is True and future['dispatchMustBeExactAuthorizationHead'] is True and future['allocationCheckpointInIssue60RequiredBeforeDispatch'] is True,'future auth guards drift')
req(future['protectedValidationAuthorizedNow'] is False and future['scientificSolverExecutionAuthorizedNow'] is False,'future auth prematurely opened')
for k,v in d['boundaries'].items(): req(v is False,f'closed implementation boundary opened: {k}')
contract=json.loads(CONTRACT.read_text()); req(contract['modelAndEvaluation']['frozenTrainingMeanBaselineTransformedPrimary']==[0.3993901995212697,1.7062844994448103,-3.8475190646906268],'baseline vector drift'); req(contract['modelAndEvaluation']['aggregatePrimaryMeanAbsoluteLogErrorMustBeAtMostFractionOfFrozenTrainingMeanBaseline']==0.7,'baseline ratio drift')
req(not (HERE/'authorization.json').exists(),'authorization file present in implementation review')
print('VALID_0070_FRESH_VALIDATION_IMPLEMENTATION_V1')
