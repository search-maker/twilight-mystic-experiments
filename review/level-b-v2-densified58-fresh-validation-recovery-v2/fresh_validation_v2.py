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
RECOVERY_REL = Path('review/level-b-v2-densified58-fresh-validation-recovery-v2/recovery-v2.json')
RECOVERY_ID = 'level-b-v2-densified58-fresh-validation-ordinal25-recovery-v2'
EFFECTIVE_CONTRACT_ID = 'level-b-v2-densified58-fresh-protected-validation-v2-ordinal25-recovery'
EFFECTIVE_STATUS = 'REVIEW_ONLY_FRESH_PROTECTED_VALIDATION_RECOVERY_V2_NO_AUTHORIZATION_NO_VALUES_OPENED'


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
    core = module('fresh_validation_v1_base_validator', repo_root / BASE_CORE_REL)
    core.validate_contract(base)
    return base


def validate_recovery(recovery: dict[str, Any]) -> None:
    req((recovery.get('schemaVersion'), recovery.get('recoveryId'), recovery.get('status'), recovery.get('governance')) == (
        2, RECOVERY_ID, 'REVIEW_ONLY_TRANSPORT_RECOVERY_FRESH_VALUES_STILL_SEALED', 'MYSTIC-STATE-0070'
    ), 'recovery identity drift')
    req(recovery.get('sourceMainAtRecoveryFreeze') == '5dbd6346a2caae2415d15fc44e4063541fac1634', 'recovery source-main drift')
    b = recovery['baseBindings']
    req((b['contractPath'], b['contractGitBlobSha']) == (BASE_CONTRACT_REL.as_posix(), 'aad11350311ce3768488e64ed72edc3e48646ff9'), 'base contract binding drift')
    req((b['evaluatorPath'], b['evaluatorGitBlobSha']) == (BASE_CORE_REL.as_posix(), '085f040caa6aec53aace00381035115358b21239'), 'base evaluator binding drift')
    req((b['manifestBuilderGitBlobSha'], b['adapterGitBlobSha'], b['executorGitBlobSha']) == (
        '5972fed72f38a7375251b80d841fb872c2008035',
        '5cd736d78c5b82d124b5b95548063677dbfe0ce9',
        '5bf0477f0d5100dcb73da8027233e8415ce9021c',
    ), 'execution implementation binding drift')
    req((b['modelSha256'], b['representationPackageSha256']) == (
        '91ae5811e55b3d4ef872ab672f006c4b383c6581a53de67cd018b6eb2666f9a7',
        '2491ac91ed924f2ba69b37ea20f48d63f51d41146cd9fe50e0bd63bfb315a763',
    ), 'model/representation binding drift')
    prior = recovery['ordinal24DispatchRefusal']
    req((prior['authorizationHeadSha'], prior['authorizationPullRequest'], prior['authorizationReviewRunId'], prior['allocationMarkerCommentId'], prior['dispatchRunId']) == (
        '520ff3cc5f8fee2defc1a0a950bfa7a40974479c', 194, 31840635840, 5298149901, 31840757436
    ), 'ordinal24 refusal identity drift')
    req(prior['authorizationReviewConclusion'] == 'success' and prior['dispatchRunConclusion'] == 'failure' and prior['preflightConclusion'] == 'success', 'ordinal24 refusal conclusion drift')
    req((prior['caseJobCount'], prior['terminalCaseFailureCount'], prior['evaluationConclusion'], prior['runArtifactCount']) == (24, 24, 'skipped', 25), 'ordinal24 refusal accounting drift')
    req(prior['reason'] == 'EXECUTOR_BRANCH_REGEX_ACCEPTS_SUFFIX_V1_ONLY_BUT_DISPATCH_USED_SUFFIX_V3', 'ordinal24 refusal reason drift')
    req(prior['executorAcceptedBranchRegex'] == '^dispatch/level-b-v2-densified58-fresh-validation-ordinal[1-9][0-9]*-v1$', 'executor regex record drift')
    req(prior['syntaxCheckCount'] == 0 and prior['solverExecutionCount'] == 0 and prior['protectedValuesRead'] is False and prior['ordinal22ValuesRead'] is False, 'ordinal24 science exposure drift')
    req(prior['scientificIdentityConsumed'] is True and prior['priorSeedsRetired'] is True and prior['priorReservedSeeds'] == list(range(2101000001, 2101000025)), 'ordinal24 retirement drift')
    nxt = recovery['nextScientificIdentity']
    req((nxt['scientificOrdinal'], nxt['authorizationBranch'], nxt['dispatchBranch'], nxt['executionKey']) == (
        25,
        'authorization/level-b-v2-densified58-fresh-validation-ordinal25-v1',
        'dispatch/level-b-v2-densified58-fresh-validation-ordinal25-v1',
        'level-b-v2-densified58:fresh-protected-validation:25',
    ), 'ordinal25 identity drift')
    req(nxt['reservedSeeds'] == list(range(2101000025, 2101000049)), 'ordinal25 seed drift')
    req((nxt['geometryCount'], nxt['blocksPerGeometry'], nxt['caseCount'], nxt['photonHistoriesPerBlock'], nxt['configuredPhotonHistories']) == (6, 4, 24, 40_000_000, 960_000_000), 'ordinal25 accounting drift')
    req(nxt['allocatedAtRecoveryReview'] is False and nxt['consumedAtRecoveryReview'] is False, 'recovery review allocated science')
    req(all(value is True for key, value in recovery['frozenScience'].items() if key.startswith('same')), 'frozen-science reuse flag drift')
    req(recovery['frozenScience']['modelRetuningAuthorized'] is False and recovery['frozenScience']['geometryRetuningAuthorized'] is False and recovery['frozenScience']['definitionOfDoneChangeAuthorized'] is False, 'science retuning boundary opened')
    req(all(value is False for value in recovery['reviewSurface'].values()), 'review surface opened')


def effective_contract(recovery: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    validate_recovery(recovery)
    base = base_contract(repo_root)
    p = copy.deepcopy(base)
    p['schemaVersion'] = 2
    p['contractId'] = EFFECTIVE_CONTRACT_ID
    p['status'] = EFFECTIVE_STATUS
    p['sourceMainAtFreeze'] = recovery['sourceMainAtRecoveryFreeze']
    p['executionEnvelope']['candidateScientificOrdinal'] = 25
    p['executionEnvelope']['reservedSeeds'] = list(recovery['nextScientificIdentity']['reservedSeeds'])
    p['executionEnvelope']['scientificOrdinalAllocated'] = False
    p['recoveryProvenance'] = {
        'recoveryId': RECOVERY_ID,
        'ordinal24DispatchRunId': recovery['ordinal24DispatchRefusal']['dispatchRunId'],
        'ordinal24RefusalReason': recovery['ordinal24DispatchRefusal']['reason'],
        'ordinal24ProtectedValuesRead': False,
        'ordinal24SolverExecutionCount': 0,
        'ordinal24SeedsRetired': True,
        'nextScientificOrdinal': 25,
        'nextAuthorizationBranch': recovery['nextScientificIdentity']['authorizationBranch'],
        'nextDispatchBranch': recovery['nextScientificIdentity']['dispatchBranch'],
        'nextExecutionKey': recovery['nextScientificIdentity']['executionKey'],
    }
    validate_contract(p, recovery, repo_root)
    return p


def validate_contract(p: dict[str, Any], recovery: dict[str, Any], repo_root: Path) -> None:
    validate_recovery(recovery)
    base = base_contract(repo_root)
    req((p.get('schemaVersion'), p.get('contractId'), p.get('status'), p.get('governance'), p.get('sourceMainAtFreeze')) == (
        2, EFFECTIVE_CONTRACT_ID, EFFECTIVE_STATUS, 'MYSTIC-STATE-0070', recovery['sourceMainAtRecoveryFreeze']
    ), 'effective contract identity drift')
    for key in ('authorization', 'boundaries', 'failureSemantics', 'geometrySelection', 'modelAndEvaluation', 'runtimeIdentityRequired', 'sourceBindings'):
        req(p[key] == base[key], f'frozen base subtree drift: {key}')
    base_env = copy.deepcopy(base['executionEnvelope'])
    new_env = copy.deepcopy(p['executionEnvelope'])
    for env in (base_env, new_env):
        env.pop('candidateScientificOrdinal', None)
        env.pop('reservedSeeds', None)
        env.pop('scientificOrdinalAllocated', None)
    req(new_env == base_env, 'execution envelope changed beyond identity/seeds')
    req(p['executionEnvelope']['candidateScientificOrdinal'] == 25, 'effective ordinal drift')
    req(p['executionEnvelope']['reservedSeeds'] == list(range(2101000025, 2101000049)), 'effective seeds drift')
    req(p['executionEnvelope']['scientificOrdinalAllocated'] is False, 'effective contract allocated ordinal')
    req(p.get('recoveryProvenance') == {
        'recoveryId': RECOVERY_ID,
        'ordinal24DispatchRunId': 31840757436,
        'ordinal24RefusalReason': 'EXECUTOR_BRANCH_REGEX_ACCEPTS_SUFFIX_V1_ONLY_BUT_DISPATCH_USED_SUFFIX_V3',
        'ordinal24ProtectedValuesRead': False,
        'ordinal24SolverExecutionCount': 0,
        'ordinal24SeedsRetired': True,
        'nextScientificOrdinal': 25,
        'nextAuthorizationBranch': 'authorization/level-b-v2-densified58-fresh-validation-ordinal25-v1',
        'nextDispatchBranch': 'dispatch/level-b-v2-densified58-fresh-validation-ordinal25-v1',
        'nextExecutionKey': 'level-b-v2-densified58:fresh-protected-validation:25',
    }, 'recovery provenance drift')


def expected_cases(p: dict[str, Any], recovery: dict[str, Any], repo_root: Path) -> list[dict[str, Any]]:
    validate_contract(p, recovery, repo_root)
    geoms = p['geometrySelection']['selectedGeometries']
    seeds = p['executionEnvelope']['reservedSeeds']
    out: list[dict[str, Any]] = []
    cursor = 0
    for g in geoms:
        suffix = str(g['geometryId']).removeprefix('v0070-')
        for block in range(1, 5):
            seed = int(seeds[cursor]); cursor += 1
            out.append({
                'caseId': f'v0070-o25-{suffix}-b{block}',
                'geometryId': g['geometryId'],
                'block': block,
                'seed': seed,
                'photonHistories': 40_000_000,
                'alisSpectralImportanceSamplingNm': 550.0,
            })
    req(cursor == 24 and len(out) == 24, 'ordinal25 case construction drift')
    req([x['seed'] for x in out] == list(range(2101000025, 2101000049)), 'ordinal25 case seed order drift')
    req(len({x['caseId'] for x in out}) == 24, 'ordinal25 duplicate case id')
    return out


def patched_base_core(recovery: dict[str, Any], repo_root: Path):
    base = module('fresh_validation_v1_reused_math', repo_root / BASE_CORE_REL)
    base.validate_contract = lambda p: validate_contract(p, recovery, repo_root)
    base.expected_cases = lambda p: expected_cases(p, recovery, repo_root)
    return base


def evaluate(recovery: dict[str, Any], cases_root: Path, model_dir: Path, representation_dir: Path, repo_root: Path, output: Path) -> dict[str, Any]:
    p = effective_contract(recovery, repo_root)
    base = patched_base_core(recovery, repo_root)
    result = base.evaluate(p, cases_root, model_dir, representation_dir, repo_root, output)
    result['schemaVersion'] = 2
    result['stageId'] = 'LEVEL_B_V2_DENSIFIED58_FRESH_PROTECTED_VALIDATION_EVALUATION_V2_ORDINAL25_RECOVERY'
    result['recoveryId'] = RECOVERY_ID
    result['scientificOrdinal'] = 25
    result['ordinal24DispatchRunId'] = 31840757436
    result['ordinal24ProtectedValuesRead'] = False
    result['ordinal24SolverExecutionCount'] = 0
    result['resultSha256'] = None
    result['resultSha256'] = canon(result)
    write(output, result)
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    v = sub.add_parser('validate'); v.add_argument('--recovery', type=Path, required=True); v.add_argument('--repo-root', type=Path, default=ROOT)
    c = sub.add_parser('cases'); c.add_argument('--recovery', type=Path, required=True); c.add_argument('--repo-root', type=Path, default=ROOT)
    e = sub.add_parser('evaluate'); e.add_argument('--recovery', type=Path, required=True); e.add_argument('--cases-root', type=Path, required=True); e.add_argument('--model-dir', type=Path, required=True); e.add_argument('--representation-dir', type=Path, required=True); e.add_argument('--repo-root', type=Path, required=True); e.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    try:
        recovery = load(args.recovery)
        p = effective_contract(recovery, args.repo_root)
        if args.cmd == 'validate':
            print(json.dumps({'status':'PASS','recoveryId':RECOVERY_ID,'scientificOrdinal':25,'caseCount':len(expected_cases(p,recovery,args.repo_root)),'protectedValuesRead':False,'solverExecutionAuthorized':False}, sort_keys=True))
        elif args.cmd == 'cases':
            print(json.dumps(expected_cases(p,recovery,args.repo_root), sort_keys=True, separators=(',', ':')))
        else:
            evaluate(recovery, args.cases_root, args.model_dir, args.representation_dir, args.repo_root, args.output)
        return 0
    except Exception as error:
        print(json.dumps({'status':'REFUSED','reason':str(error)}, sort_keys=True), file=__import__('sys').stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
