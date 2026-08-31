#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
import urllib.error
from dataclasses import dataclass
from typing import Callable, Any

RECOVERY_ID = 'lunar-finite-disk-transfer-kernel-sensitivity-v1-exec003-transport-recovery-v1'
FRESH_EXECUTION_ID = 'lunar-finite-disk-transfer-kernel-sensitivity-v1-exec003'
CONSUMED_EXEC002 = {
    'executionId': 'lunar-finite-disk-transfer-kernel-sensitivity-v1-exec002',
    'head': 'ff5c6d434797d50d0d876429674091abf44f2987',
    'runId': 33350041283,
    'attempt': 1,
    'preflightJobId': 99361464208,
    'failure': 'TRANSIENT_GITHUB_ACTIONS_RUNS_API_HTTP_502_DURING_REPOSITORY_GLOBAL_SCAN',
    'rerunRetryResumeForbidden': True,
    'seedUniverseConsumed': True,
    'scientificResultExists': False,
}
FROZEN_SCIENCE = {
    'wavelengthNm': 550.0,
    'geometryCount': 6,
    'directionsPerGeometry': 33,
    'totalDirectionalCases': 198,
    'photonHistoriesPerDirectionalCase': 5_000_000,
    'totalPhotonHistories': 990_000_000,
    'acceptanceThreshold': None,
    'descriptiveEvaluatorUnchanged': True,
    'mandatorySpectralFollowOnNm': [450.0, 650.0, 750.0],
}
TRANSIENT_HTTP_STATUSES = frozenset({408, 429, 500, 502, 503, 504})
BACKOFF_SECONDS = (2, 5, 10)
MAX_ATTEMPTS = 1 + len(BACKOFF_SECONDS)


class RecoveryContractError(RuntimeError):
    pass


@dataclass(frozen=True)
class RetryReceipt:
    attempts: int
    transient_failures: tuple[str, ...]


def request_with_bounded_transport_retry(
    request_once: Callable[[], Any],
    *,
    sleep: Callable[[float], None] = time.sleep,
) -> tuple[Any, RetryReceipt]:
    """Retry only transport-layer failures; never reinterpret scientific failures.

    This helper is intended for read-only GitHub repository metadata enumeration
    inside the final pre-solver seed scan. It does not retry a GitHub Actions run,
    solver job, seed authorization, or scientific execution identity.
    """
    failures: list[str] = []
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return request_once(), RetryReceipt(attempt, tuple(failures))
        except urllib.error.HTTPError as exc:
            if exc.code not in TRANSIENT_HTTP_STATUSES or attempt == MAX_ATTEMPTS:
                raise
            failures.append(f'HTTP_{exc.code}')
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt == MAX_ATTEMPTS:
                raise
            failures.append(type(exc).__name__)
        sleep(BACKOFF_SECONDS[attempt - 1])
    raise AssertionError('unreachable')


def contract() -> dict[str, Any]:
    return {
        'schemaVersion': 1,
        'recoveryId': RECOVERY_ID,
        'status': 'FROZEN_SOLVER_FREE_RECOVERY_NOT_AUTHORIZED_NOT_DISPATCHED',
        'freshExecutionId': FRESH_EXECUTION_ID,
        'consumedPredecessor': CONSUMED_EXEC002,
        'frozenScience': FROZEN_SCIENCE,
        'seedPolicy': {
            'exec001SeedsReusable': False,
            'exec002SeedsReusable': False,
            'freshExec003SeedUniverseRequired': True,
            'freshRepositoryGlobalProofRequiredBeforeAuthorization': True,
            'candidateSeedsAllocatedByThisContract': False,
            'candidateSeedLiteralsIncluded': False,
        },
        'transportRetryPolicy': {
            'scope': 'READ_ONLY_GITHUB_REPOSITORY_METADATA_ENUMERATION_ONLY',
            'transientHttpStatuses': sorted(TRANSIENT_HTTP_STATUSES),
            'maxAttemptsPerMetadataRequest': MAX_ATTEMPTS,
            'backoffSeconds': list(BACKOFF_SECONDS),
            'githubActionsRunRerun': False,
            'solverRetry': False,
            'scientificExecutionRetry': False,
            'nonTransientHttpFailureFailsClosedImmediately': True,
            'exhaustedTransientFailureFailsClosed': True,
        },
        'protectedBoundaries': {
            'solverExecutionAuthorized': False,
            'seedAuthorizationCreated': False,
            'resultOpened': False,
            'finiteMoonDiskValidated': False,
            'atmosphericScatteredMoonlightEmpiricallyValidated': False,
            'totalSkyValidated': False,
            'taylorOrJerusalemResidualUsed': False,
            'productionAuthorized': False,
        },
    }


def validate_contract() -> dict[str, Any]:
    c = contract()
    if c['freshExecutionId'] == c['consumedPredecessor']['executionId']:
        raise RecoveryContractError('fresh execution identity required')
    if c['consumedPredecessor']['rerunRetryResumeForbidden'] is not True:
        raise RecoveryContractError('exec002 must remain non-rerunnable')
    if c['consumedPredecessor']['seedUniverseConsumed'] is not True:
        raise RecoveryContractError('exec002 seed universe must remain consumed')
    f = c['frozenScience']
    if (f['wavelengthNm'], f['geometryCount'], f['directionsPerGeometry'], f['totalDirectionalCases']) != (550.0, 6, 33, 198):
        raise RecoveryContractError('finite-disk design drift')
    if f['photonHistoriesPerDirectionalCase'] != 5_000_000 or f['totalPhotonHistories'] != 990_000_000:
        raise RecoveryContractError('photon budget drift')
    if f['acceptanceThreshold'] is not None or f['descriptiveEvaluatorUnchanged'] is not True:
        raise RecoveryContractError('result-dependent acceptance remains forbidden')
    if f['mandatorySpectralFollowOnNm'] != [450.0, 650.0, 750.0]:
        raise RecoveryContractError('mandatory spectral follow-on drift')
    if c['seedPolicy']['freshExec003SeedUniverseRequired'] is not True or c['seedPolicy']['candidateSeedsAllocatedByThisContract'] is not False:
        raise RecoveryContractError('fresh-seed boundary drift')
    if any(c['protectedBoundaries'].values()):
        raise RecoveryContractError('protected boundary opened')
    return c


class _FakeResponse:
    def __init__(self, payload: Any): self.payload = payload
    def __enter__(self): return self
    def __exit__(self, *args): return False


def self_test() -> dict[str, Any]:
    slept: list[float] = []
    sequence: list[Any] = [
        urllib.error.HTTPError('https://api.github.test/runs', 502, 'Bad Gateway', None, None),
        urllib.error.HTTPError('https://api.github.test/runs', 503, 'Unavailable', None, None),
        {'ok': True},
    ]
    def once():
        value = sequence.pop(0)
        if isinstance(value, BaseException):
            raise value
        return value
    value, receipt = request_with_bounded_transport_retry(once, sleep=slept.append)
    assert value == {'ok': True}
    assert receipt.attempts == 3 and receipt.transient_failures == ('HTTP_502', 'HTTP_503')
    assert slept == [2, 5]

    count = 0
    def nontransient():
        nonlocal count
        count += 1
        raise urllib.error.HTTPError('https://api.github.test/runs', 404, 'Not Found', None, None)
    try:
        request_with_bounded_transport_retry(nontransient, sleep=slept.append)
    except urllib.error.HTTPError as exc:
        assert exc.code == 404
    else:
        raise AssertionError('404 must fail closed without retry')
    assert count == 1

    exhausted = 0
    def always_502():
        nonlocal exhausted
        exhausted += 1
        raise urllib.error.HTTPError('https://api.github.test/runs', 502, 'Bad Gateway', None, None)
    exhausted_sleeps: list[float] = []
    try:
        request_with_bounded_transport_retry(always_502, sleep=exhausted_sleeps.append)
    except urllib.error.HTTPError as exc:
        assert exc.code == 502
    else:
        raise AssertionError('exhausted transient failures must fail closed')
    assert exhausted == MAX_ATTEMPTS and exhausted_sleeps == list(BACKOFF_SECONDS)

    c = validate_contract()
    return {
        'status': 'PASS_EXEC003_TRANSPORT_RECOVERY_SELF_TEST',
        'freshExecutionId': c['freshExecutionId'],
        'maxMetadataRequestAttempts': MAX_ATTEMPTS,
        'solverExecuted': False,
        'seedAuthorized': False,
        'resultOpened': False,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument('command', choices=('validate', 'self-test'))
    p.add_argument('--json', action='store_true')
    args = p.parse_args()
    payload = validate_contract() if args.command == 'validate' else self_test()
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(payload.get('status', 'PASS'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
