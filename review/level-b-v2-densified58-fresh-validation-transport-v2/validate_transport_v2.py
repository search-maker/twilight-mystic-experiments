#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
TRANSPORT = HERE / 'transport-v2.json'


def req(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit('REFUSED: ' + message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding='utf-8'))
    req(isinstance(value, dict), f'object required: {path}')
    return value


def blob(path: str) -> str:
    return subprocess.check_output(['git', 'rev-parse', 'HEAD:' + path], cwd=ROOT, text=True).strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--require-review-inert', action='store_true')
    args = ap.parse_args()
    t = load(TRANSPORT)

    req(t['schemaVersion'] == 2, 'schema')
    req(t['transportId'] == 'level-b-v2-densified58-fresh-validation-transport-v2', 'transport id')
    req(t['status'] == 'REVIEW_ONLY_AUTHORIZATION_V2_AND_DISPATCH_V2_TRANSPORT_NO_AUTHORIZATION_FILE_NO_ALLOCATION', 'status')
    req(t['governance'] == 'MYSTIC-STATE-0070', 'governance')
    req(t['sourceMainAtTransportFreeze'] == '76e6046151bb7d455128326a0e2a4feed37e5b3d', 'source main drift')

    b = t['sourceBindings']
    expected = {
        b['priorTransportV1Path']: '97b25195cbd27c81890ddf1b61de9c4df6d379e6',
        b['freshValidationContractPath']: 'aad11350311ce3768488e64ed72edc3e48646ff9',
        b['implementationContractPath']: '34e797346e937c4d1164b61cd2cc7197213aa97a',
        b['evaluatorPath']: '085f040caa6aec53aace00381035115358b21239',
        b['manifestBuilderPath']: '5972fed72f38a7375251b80d841fb872c2008035',
        b['adapterPath']: '5cd736d78c5b82d124b5b95548063677dbfe0ce9',
        b['executorPath']: '5bf0477f0d5100dcb73da8027233e8415ce9021c',
        b['trainingModelResultPath']: '28ff90afa0de1734aa0b6718bc93ebdce1ded54a',
    }
    for path, want in expected.items():
        req(blob(path) == want, f'git blob drift: {path}')
    req(b['priorTransportV1GitBlobSha'] == expected[b['priorTransportV1Path']], 'prior transport binding')
    req(b['freshValidationContractGitBlobSha'] == expected[b['freshValidationContractPath']], 'fresh contract binding')
    req(b['implementationContractGitBlobSha'] == expected[b['implementationContractPath']], 'implementation binding')
    req(b['evaluatorGitBlobSha'] == expected[b['evaluatorPath']], 'evaluator binding')
    req(b['manifestBuilderGitBlobSha'] == expected[b['manifestBuilderPath']], 'manifest binding')
    req(b['adapterGitBlobSha'] == expected[b['adapterPath']], 'adapter binding')
    req(b['executorGitBlobSha'] == expected[b['executorPath']], 'executor binding')
    req(b['trainingModelResultGitBlobSha'] == expected[b['trainingModelResultPath']], 'model result binding')
    req((b['modelArtifactId'], b['modelArtifactDigest'], b['modelCanonicalSha256']) == (9229229366, 'sha256:f4c8c68a622f7c6bdc1b9177ad31d22f673becb1f286436d54b876ceece3668a', '91ae5811e55b3d4ef872ab672f006c4b383c6581a53de67cd018b6eb2666f9a7'), 'model identity drift')
    req((b['representationArtifactId'], b['representationArtifactDigest'], b['representationPackageSha256']) == (9208203541, 'sha256:2fe50ed674155f440322c92d28877f5c022f0cc5fa13e1e601596a9902482815', '2491ac91ed924f2ba69b37ea20f48d63f51d41146cd9fe50e0bd63bfb315a763'), 'representation identity drift')

    r = t['priorAuthorizationRefusal']
    req(r == {
        'authorizationBranch': 'authorization/level-b-v2-densified58-fresh-validation-ordinal24-v1',
        'authorizationCommitSha': '1cefb761f0ec57059da0dbdfe2229d0fd0ab8e9b',
        'pullRequest': 190,
        'authorizationReviewRunId': 31838796101,
        'authorizationReviewRunAttempt': 1,
        'authorizationReviewJobId': 94890966081,
        'conclusion': 'failure',
        'reason': 'MISSING_NUMPY_DEPENDENCY_BEFORE_MANIFEST_BUILD',
        'directChildLiveMainDraftOneFileGuardsPassed': True,
        'transportValidatorPassed': True,
        'manifestBuilt': False,
        'allocationMarkerWritten': False,
        'dispatchBranchCreated': False,
        'protectedValuesRead': False,
        'scientificSolverExecutionPerformed': False,
        'scientificOrdinalAllocated': False,
        'reservedSeedsAllocated': False,
        'authorizationIdentityMayBeReused': False,
    }, 'prior authorization refusal drift')

    s = t['scientificIdentity']
    req(s['scientificOrdinal'] == 24, 'ordinal drift')
    req(s['authorizationBranch'] == 'authorization/level-b-v2-densified58-fresh-validation-ordinal24-v2', 'authorization v2 branch drift')
    req(s['dispatchBranch'] == 'dispatch/level-b-v2-densified58-fresh-validation-ordinal24-v2', 'dispatch v2 branch drift')
    req(s['executionKey'] == 'level-b-v2-densified58:fresh-protected-validation:24', 'execution key drift')
    req(s['reservedSeeds'] == list(range(2101000001, 2101000025)), 'seed set/order drift')
    req(s['allocatedAtTransportReview'] is False and s['consumedAtTransportReview'] is False, 'transport review allocation drift')

    a = t['authorizationContract']
    req(a['authorizationPath'] == 'review/level-b-v2-densified58-fresh-validation-transport-v2/authorization.json', 'authorization path drift')
    req(a['frozenNumericalDependency'] == 'numpy==2.3.2', 'numerical dependency drift')
    req(a['authorizationMustBeExactlyOneNewFile'] is True and a['authorizationCommitMustBeDirectChildOfLiveMain'] is True, 'authorization shape opened')
    req(a['authorizationPullRequestMustRemainDraftAndUnmergedThroughDispatch'] is True and a['authorizationReviewRunAttemptExactly'] == 1, 'authorization review semantics drift')
    req(a['automaticDispatch'] is False and a['allocationMarkerMayBeWrittenOnlyAfterSuccessfulAuthorizationReview'] is True and a['dispatchBranchMayBeCreatedOnlyAfterAllocationMarker'] is True, 'authorization sequencing drift')

    d = t['dispatchContract']
    req((d['geometryCount'], d['caseCount'], d['configuredPhotonHistories'], d['maxParallel']) == (6, 24, 960000000, 24), 'dispatch accounting drift')
    for key in ('dispatchHeadMustExactlyEqualAuthorizationHead','oneMatchingAllocationMarkerRequired','oneSyntaxCheckPerCase','oneSolverInvocationPerCase','evaluationRunsOnlyAfterAllCaseJobsSucceed','evaluationArtifactUploadedOnScientificPassOrFail','scientificFailureDoesNotFailOperationalWorkflow'):
        req(d[key] is True, f'dispatch requirement disabled: {key}')
    for key in ('githubRerunAllowed','retryAllowed','resumeAllowed'):
        req(d[key] is False, f'dispatch continuation opened: {key}')
    req(d['dispatchRunAttemptExactly'] == 1, 'dispatch attempt drift')

    req(all(v is True for v in t['freshnessSemantics'].values()), 'freshness semantics weakened')
    req(all(v is False for v in t['reviewSurface'].values()), 'review surface opened')
    req(all(v is False for v in t['closedBoundaries'].values()), 'closed boundary opened')

    auth_path = ROOT / a['authorizationPath']
    if args.require_review_inert:
        req(not auth_path.exists(), 'authorization file present during transport-v2 review')

    print(json.dumps({
        'status': 'PASS',
        'scientificOrdinal': 24,
        'authorizationBranch': s['authorizationBranch'],
        'dispatchBranch': s['dispatchBranch'],
        'reservedSeedCount': len(s['reservedSeeds']),
        'priorAuthorizationV1Preserved': True,
        'authorizationV2FilePresent': auth_path.exists(),
        'protectedValuesRead': False,
        'scientificSolverExecutionAuthorizedByTransportReview': False,
    }, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
