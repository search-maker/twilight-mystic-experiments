from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from freshness import (
    authorization_branch,
    dispatch_branch,
    execution_key,
    validate_authorization_review,
    validate_preauthorization,
)

SHA40 = re.compile(r'^[0-9a-f]{40}$')


class AuthorizationRefusal(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuthorizationRefusal(message)


def raw_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_enabled_document(
    authorization: dict[str, Any],
    live_main: str,
    paths: dict[str, Path],
) -> None:
    ordinal = authorization.get('scientificOrdinal')
    require(isinstance(ordinal, int) and ordinal > 0, 'authorization ordinal invalid')
    require(authorization.get('schemaVersion') == 1, 'authorization schema drift')
    require(authorization.get('stageId') == 'aerosol-family-challenge-v2-authorization', 'authorization stage drift')
    require(authorization.get('status') == 'AUTHORIZED_PENDING_SEPARATE_DISPATCH', 'authorization status drift')
    require(authorization.get('enabled') is True, 'authorization is not enabled')
    require(authorization.get('scientificExecutionAuthorized') is True, 'scientific execution authorization missing')
    require(authorization.get('solverExecutionAuthorized') is True, 'solver authorization missing')
    require(authorization.get('dispatchAuthorized') is False, 'authorization document may not itself authorize dispatch')
    require(authorization.get('automaticDispatch') is False, 'automatic dispatch forbidden')
    require(authorization.get('consumed') is False, 'authorization already consumed')
    require(authorization.get('executionKey') == execution_key(ordinal), 'execution key drift')
    require(authorization.get('authorizationBranch') == authorization_branch(ordinal), 'authorization branch drift')
    require(authorization.get('dispatchBranch') == dispatch_branch(ordinal), 'dispatch branch drift')
    require(authorization.get('exactAuthorizationParentCommit') == live_main, 'authorization parent is not then-live main')
    require(authorization.get('exactAuthorizationCommit') is None, 'authorization document must not embed own commit SHA')
    require(authorization.get('repositoryFullName') == 'search-maker/twilight-mystic-experiments', 'authorization repository drift')
    for field, key in (
        ('manifestRawSha256', 'manifest'),
        ('freezeRecordRawSha256', 'freeze'),
        ('transportContractRawSha256', 'transport'),
        ('adapterRawSha256', 'adapter'),
        ('executorRawSha256', 'executor'),
        ('workflowRawSha256', 'workflow'),
        ('authorizationGuardRawSha256', 'authorizationGuard'),
        ('dispatchGuardRawSha256', 'dispatchGuard'),
        ('freshnessGuardRawSha256', 'freshness'),
        ('authorizationReviewWorkflowRawSha256', 'authorizationReviewWorkflow'),
    ):
        require(authorization.get(field) == raw_sha(paths[key]), f'authorization byte binding drift: {field}')
    require(authorization.get('runtimeLockRawSha256') == '3b5fbec964642b04c73a6423b3355dbcc4ba5e84f9614f6d74420491bacc20c5', 'runtime lock binding drift')
    for key in (
        'githubRerunAllowed', 'retryAllowed', 'resumeAllowed',
        'protectedHoldoutOpeningAuthorized', 'modelFittingAuthorized',
        'modelSelectionAuthorized', 'tier2Authorized', 'productionPromotionAuthorized',
    ):
        require(authorization.get(key) is False, f'closed authorization boundary drift: {key}')


def preauthorize(context: dict[str, Any], ordinal: int) -> dict[str, Any]:
    validate_preauthorization(context.get('freshness') or {}, ordinal)
    require(context.get('authorizationCreated') is False, 'authorization already created')
    require(context.get('scientificRuntimeSetupPerformed') is False, 'preauthorization review may not set up scientific runtime')
    require(context.get('scientificExecutionPerformed') is False, 'preauthorization review may not execute scientific process')
    return {
        'status': 'PREAUTHORIZATION_FRESHNESS_PASS_AUTHORIZATION_CREATION_PERMITTED',
        'scientificOrdinal': ordinal,
        'authorizationBranch': authorization_branch(ordinal),
        'dispatchBranch': dispatch_branch(ordinal),
        'executionKey': execution_key(ordinal),
        'authorizationCreationPermitted': True,
        'scientificExecutionPerformed': False,
        'ordinalAllocatedReservedOrConsumedByReview': False,
    }


def review(
    authorization: dict[str, Any],
    context: dict[str, Any],
    paths: dict[str, Path],
) -> dict[str, Any]:
    ordinal = authorization.get('scientificOrdinal')
    live_main = context.get('liveMain')
    head = context.get('headSha')
    parent = context.get('parentSha')
    pr = context.get('pr') or {}
    require(isinstance(live_main, str) and SHA40.fullmatch(live_main) is not None, 'live main invalid')
    require(isinstance(head, str) and SHA40.fullmatch(head) is not None, 'authorization head invalid')
    require(parent == live_main, 'authorization commit parent is not then-live main')
    require(context.get('parentCount') == 1, 'authorization commit must have exactly one parent')
    require(context.get('changedPaths') == [context.get('authorizationPath')], 'authorization commit must change exactly one authorization path')
    require(context.get('authorizationPath') == 'experiments/aerosol-family-challenge-v2/authorization.json', 'authorization path drift')
    validate_enabled_document(authorization, live_main, paths)
    require(pr.get('number', 0) > 0, 'authorization PR number invalid')
    require(pr.get('state') == 'open' and pr.get('draft') is True and pr.get('merged') is False, 'authorization PR must remain Draft/open/unmerged')
    require(pr.get('headBranch') == authorization_branch(ordinal) and pr.get('baseBranch') == 'main', 'authorization PR branch/base drift')
    require(pr.get('headRepo') == authorization['repositoryFullName'] and pr.get('baseRepo') == authorization['repositoryFullName'], 'authorization PR must be same-repository')
    require(pr.get('headSha') == head, 'authorization PR head mismatch')
    require(context.get('runAttempt') == 1, 'authorization review must be attempt 1')
    require(context.get('eventName') == 'pull_request' and context.get('eventAction') == 'opened', 'authorization review must be PR opened event')
    require(context.get('scientificRuntimeSetupPerformed') is False, 'authorization review may not set up scientific runtime')
    require(context.get('scientificExecutionPerformed') is False, 'authorization review may not execute scientific process')
    validate_authorization_review(context.get('freshness') or {}, ordinal, head)
    return {
        'status': 'AUTHORIZATION_REVIEW_PASS_ZERO_RUNTIME',
        'scientificOrdinal': ordinal,
        'executionKey': authorization['executionKey'],
        'authorizationHead': head,
        'authorizationParent': parent,
        'authorizationPr': pr['number'],
        'scientificExecutionPerformed': False,
        'ordinalAllocatedReservedOrConsumedByReview': False,
    }
