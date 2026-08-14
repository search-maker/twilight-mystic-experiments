#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
BASE_CONTRACT_REL = Path('review/level-b-v2-densified58-fresh-validation-v1/contract-v1.json')
BASE_CORE_REL = Path('review/level-b-v2-densified58-fresh-validation-implementation-v1/fresh_validation_v1.py')
RECOVERY_REL = Path('review/level-b-v2-densified58-fresh-validation-recovery-v3/recovery-v3.json')
RECOVERY_ID = 'level-b-v2-densified58-fresh-validation-ordinal26-recovery-v3'
EFFECTIVE_CONTRACT_ID = 'level-b-v2-densified58-fresh-protected-validation-v3-ordinal26-recovery'
EFFECTIVE_STATUS = 'REVIEW_ONLY_FRESH_PROTECTED_VALIDATION_RECOVERY_V3_NO_AUTHORIZATION_NO_VALUES_OPENED'


class Refusal(RuntimeError):
    pass


def req(condition: bool, message: str) -> None:
    if not condition:
        raise Refusal(message)


def canon(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding='utf-8'))
    req(isinstance(value, dict), f'object required: {path}')
    return value


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n', encoding='utf-8')


def module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    req(spec is not None and spec.loader is not None, f'cannot load module: {path}')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def base_contract(repo_root: Path) -> dict[str, Any]:
    base = load(repo_root / BASE_CONTRACT_REL)
    core = module('fresh_validation_v1_base_validator_v3', repo_root / BASE_CORE_REL)
    core.validate_contract(base)
    return base


def validate_recovery(r: dict[str, Any]) -> None:
    req((r.get('schemaVersion'),r.get('recoveryId'),r.get('status'),r.get('governance')) == (
        3,RECOVERY_ID,'REVIEW_ONLY_ALLOCATION_RACE_RECOVERY_FRESH_VALUES_STILL_SEALED','MYSTIC-STATE-0070'), 'recovery identity drift')
    req(r.get('sourceMainAtRecoveryFreeze') == '555802e483fd5e016e44b441acb08a6f003679f4', 'source-main drift')
    req(r['baseScientificContract'] == {'path':BASE_CONTRACT_REL.as_posix(),'gitBlobSha':'aad11350311ce3768488e64ed72edc3e48646ff9'}, 'base contract binding drift')
    req(r['frozenModel']['modelSha256'] == '91ae5811e55b3d4ef872ab672f006c4b383c6581a53de67cd018b6eb2666f9a7', 'model drift')
    req(r['frozenModel']['representationPackageSha256'] == '2491ac91ed924f2ba69b37ea20f48d63f51d41146cd9fe50e0bd63bfb315a763', 'representation drift')
    o24=r['ordinal24Refusal'];o25=r['ordinal25Refusal']
    req(o24['dispatchRunId']==31840757436 and o24['identityConsumed'] is True and o24['solverExecutionCount']==0 and o24['protectedValuesRead'] is False, 'ordinal24 refusal drift')
    req(o24['retiredSeeds']==list(range(2101000001,2101000025)), 'ordinal24 seeds drift')
    req((o25['authorizationHeadSha'],o25['authorizationPullRequest'],o25['authorizationReviewRunId'],o25['dispatchRunId']) == ('a6992ef0e4d98f8fb2f9853e23a60331d1aa4d83',198,31842836008,31842973699), 'ordinal25 refusal identity drift')
    req(o25['allocationMarkerCommentIds']==[5298386381,5298387062], 'ordinal25 duplicate marker evidence drift')
    req(o25['reason']=='TWO_BYTE_IDENTICAL_ALLOCATION_MARKER_COMMENTS_WHILE_TRANSPORT_REQUIRED_EXACTLY_ONE_COMMENT', 'ordinal25 reason drift')
    req(o25['manifestEmitted'] is False and o25['matrixEmitted'] is False and o25['runArtifactCount']==0, 'ordinal25 pre-manifest accounting drift')
    req(o25['syntaxCheckCount']==0 and o25['solverExecutionCount']==0 and o25['protectedValuesRead'] is False and o25['ordinal22ValuesRead'] is False, 'ordinal25 exposure drift')
    req(o25['identityConsumed'] is True and o25['retiredSeeds']==list(range(2101000025,2101000049)), 'ordinal25 retirement drift')
    nxt=r['nextScientificIdentity']
    req((nxt['scientificOrdinal'],nxt['authorizationBranch'],nxt['allocationLockBranch'],nxt['dispatchBranch'],nxt['executionKey']) == (
        26,'authorization/level-b-v2-densified58-fresh-validation-ordinal26-v1','allocation/level-b-v2-densified58-fresh-validation-ordinal26-v1','dispatch/level-b-v2-densified58-fresh-validation-ordinal26-v1','level-b-v2-densified58:fresh-protected-validation:26'), 'ordinal26 identity drift')
    req(nxt['reservedSeeds']==list(range(2101000049,2101000073)), 'ordinal26 seeds drift')
    req((nxt['geometryCount'],nxt['blocksPerGeometry'],nxt['caseCount'],nxt['photonHistoriesPerBlock'],nxt['configuredPhotonHistories'])==(6,4,24,40_000_000,960_000_000), 'ordinal26 accounting drift')
    req(nxt['allocatedAtRecoveryReview'] is False and nxt['consumedAtRecoveryReview'] is False, 'recovery allocated science')
    alloc=r['allocationSemantics']
    req(alloc['atomicLockRequiredBeforeMarkerWrite'] is True and alloc['allocationLockMustPointToExactAuthorizationHead'] is True, 'allocation lock semantics drift')
    req(alloc['duplicateByteIdenticalMarkerCommentsAllowed'] is True and alloc['minimumExactMarkerCopies']==1 and alloc['distinctMarkerBodiesForSameOrdinalAllowed'] is False, 'logical marker semantics drift')
    req(alloc['dispatchRequiresLockAndLogicalMarker'] is True, 'dispatch allocation semantics drift')
    req(all(v is True for k,v in r['frozenScience'].items() if k.startswith('same')), 'frozen science drift')
    req(r['frozenScience']['modelRetuningAuthorized'] is False and r['frozenScience']['geometryRetuningAuthorized'] is False and r['frozenScience']['definitionOfDoneChangeAuthorized'] is False, 'retuning boundary opened')
    req(all(v is False for v in r['reviewSurface'].values()), 'review surface opened')


def effective_contract(r: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    validate_recovery(r)
    base=base_contract(repo_root);p=copy.deepcopy(base)
    p['schemaVersion']=3;p['contractId']=EFFECTIVE_CONTRACT_ID;p['status']=EFFECTIVE_STATUS;p['sourceMainAtFreeze']=r['sourceMainAtRecoveryFreeze']
    p['executionEnvelope']['candidateScientificOrdinal']=26
    p['executionEnvelope']['reservedSeeds']=list(r['nextScientificIdentity']['reservedSeeds'])
    p['executionEnvelope']['scientificOrdinalAllocated']=False
    p['recoveryProvenance']={
        'recoveryId':RECOVERY_ID,
        'ordinal24DispatchRunId':31840757436,
        'ordinal25DispatchRunId':31842973699,
        'ordinal25DuplicateMarkerCommentIds':[5298386381,5298387062],
        'ordinal24ProtectedValuesRead':False,
        'ordinal25ProtectedValuesRead':False,
        'ordinal24SolverExecutionCount':0,
        'ordinal25SolverExecutionCount':0,
        'ordinal24SeedsRetired':True,
        'ordinal25SeedsRetired':True,
        'nextScientificOrdinal':26,
        'nextAuthorizationBranch':r['nextScientificIdentity']['authorizationBranch'],
        'nextAllocationLockBranch':r['nextScientificIdentity']['allocationLockBranch'],
        'nextDispatchBranch':r['nextScientificIdentity']['dispatchBranch'],
        'nextExecutionKey':r['nextScientificIdentity']['executionKey'],
        'allocationMarkerSemantics':'ONE_LOGICAL_IDENTITY_ALLOW_BYTE_IDENTICAL_DUPLICATE_COPIES',
    }
    validate_contract(p,r,repo_root);return p


def validate_contract(p: dict[str, Any], r: dict[str, Any], repo_root: Path) -> None:
    validate_recovery(r);base=base_contract(repo_root)
    req((p.get('schemaVersion'),p.get('contractId'),p.get('status'),p.get('governance'),p.get('sourceMainAtFreeze')) == (3,EFFECTIVE_CONTRACT_ID,EFFECTIVE_STATUS,'MYSTIC-STATE-0070',r['sourceMainAtRecoveryFreeze']), 'effective contract identity drift')
    for key in ('authorization','boundaries','failureSemantics','geometrySelection','modelAndEvaluation','runtimeIdentityRequired','sourceBindings'):
        req(p[key]==base[key],f'frozen base subtree drift: {key}')
    be=copy.deepcopy(base['executionEnvelope']);ne=copy.deepcopy(p['executionEnvelope'])
    for env in (be,ne):
        env.pop('candidateScientificOrdinal',None);env.pop('reservedSeeds',None);env.pop('scientificOrdinalAllocated',None)
    req(ne==be,'execution envelope changed beyond identity/seeds')
    req(p['executionEnvelope']['candidateScientificOrdinal']==26 and p['executionEnvelope']['reservedSeeds']==list(range(2101000049,2101000073)) and p['executionEnvelope']['scientificOrdinalAllocated'] is False, 'ordinal26 effective envelope drift')


def expected_cases(p: dict[str, Any], r: dict[str, Any], repo_root: Path) -> list[dict[str, Any]]:
    validate_contract(p,r,repo_root);geoms=p['geometrySelection']['selectedGeometries'];seeds=p['executionEnvelope']['reservedSeeds'];out=[];cursor=0
    for g in geoms:
        suffix=str(g['geometryId']).removeprefix('v0070-')
        for block in range(1,5):
            seed=int(seeds[cursor]);cursor+=1
            out.append({'caseId':f'v0070-o26-{suffix}-b{block}','geometryId':g['geometryId'],'block':block,'seed':seed,'photonHistories':40_000_000,'alisSpectralImportanceSamplingNm':550.0})
    req(cursor==24 and len(out)==24,'ordinal26 case construction drift')
    req([x['seed'] for x in out]==list(range(2101000049,2101000073)),'ordinal26 case seed order drift')
    req(len({x['caseId'] for x in out})==24,'ordinal26 duplicate case id');return out


def patched_base_core(r: dict[str, Any], repo_root: Path):
    base=module('fresh_validation_v1_reused_math_v3',repo_root/BASE_CORE_REL)
    base.validate_contract=lambda p:validate_contract(p,r,repo_root)
    base.expected_cases=lambda p:expected_cases(p,r,repo_root)
    return base


def evaluate(r: dict[str, Any], cases_root: Path, model_dir: Path, representation_dir: Path, repo_root: Path, output: Path) -> dict[str, Any]:
    p=effective_contract(r,repo_root);base=patched_base_core(r,repo_root);result=base.evaluate(p,cases_root,model_dir,representation_dir,repo_root,output)
    result.pop('resultSha256',None);result['schemaVersion']=3;result['stageId']='LEVEL_B_V2_DENSIFIED58_FRESH_PROTECTED_VALIDATION_EVALUATION_V3_ORDINAL26_RECOVERY';result['recoveryId']=RECOVERY_ID;result['scientificOrdinal']=26
    result['ordinal24DispatchRunId']=31840757436;result['ordinal25DispatchRunId']=31842973699;result['ordinal24ProtectedValuesRead']=False;result['ordinal25ProtectedValuesRead']=False;result['ordinal24SolverExecutionCount']=0;result['ordinal25SolverExecutionCount']=0
    result['resultSha256']=canon(result);write(output,result);return result


def main() -> int:
    ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest='cmd',required=True)
    v=sub.add_parser('validate');v.add_argument('--recovery',type=Path,required=True);v.add_argument('--repo-root',type=Path,default=ROOT)
    c=sub.add_parser('cases');c.add_argument('--recovery',type=Path,required=True);c.add_argument('--repo-root',type=Path,default=ROOT)
    e=sub.add_parser('evaluate');e.add_argument('--recovery',type=Path,required=True);e.add_argument('--cases-root',type=Path,required=True);e.add_argument('--model-dir',type=Path,required=True);e.add_argument('--representation-dir',type=Path,required=True);e.add_argument('--repo-root',type=Path,required=True);e.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    try:
        r=load(args.recovery);p=effective_contract(r,args.repo_root)
        if args.cmd=='validate':print(json.dumps({'status':'PASS','recoveryId':RECOVERY_ID,'scientificOrdinal':26,'caseCount':len(expected_cases(p,r,args.repo_root)),'protectedValuesRead':False,'solverExecutionAuthorized':False},sort_keys=True))
        elif args.cmd=='cases':print(json.dumps(expected_cases(p,r,args.repo_root),sort_keys=True,separators=(',',':')))
        else:evaluate(r,args.cases_root,args.model_dir,args.representation_dir,args.repo_root,args.output)
        return 0
    except Exception as error:
        print(json.dumps({'status':'REFUSED','reason':str(error)},sort_keys=True),file=__import__('sys').stderr);return 2


if __name__=='__main__':
    raise SystemExit(main())
