#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / 'full-spectrum-estimator-pilot-preauthorization-contract-v4.json'
EXECUTION = ROOT / 'full-spectrum-estimator-pilot-execution-manifest-v4.json'
RENDER_REPORT = ROOT / 'rendered-review-v5/renderer-review-report.json'

SHA40 = re.compile(r'^[0-9a-f]{40}$')


class Refusal(RuntimeError):
    pass


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise Refusal(f'expected object: {path}')
    return value


def raw(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canon(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    ).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Refusal(message)


def validate_static() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    contract = load(CONTRACT)
    require(
        contract.get('contractId') == 'public-tier1-full-spectrum-estimator-pilot-preauthorization-contract-v4',
        'preauthorization contract id drift',
    )
    supplied = contract.get('contractSha256')
    require(
        isinstance(supplied, str)
        and canon({k: v for k, v in contract.items() if k != 'contractSha256'}) == supplied,
        'preauthorization contract self-hash mismatch',
    )
    static_files = contract.get('staticFiles', {})
    require(isinstance(static_files, dict) and static_files, 'static file contract missing')
    got = {key: raw(ROOT / spec['path']) for key, spec in static_files.items()}
    want = {key: spec['rawSha256'] for key, spec in static_files.items()}
    require(got == want, 'static package bytes drift')

    execution = load(EXECUTION)
    require(
        execution.get('manifestSha256') == contract.get('executionManifestSha256'),
        'execution manifest binding drift',
    )
    require(
        canon({k: v for k, v in execution.items() if k != 'manifestSha256'})
        == execution.get('manifestSha256'),
        'execution manifest self-hash mismatch',
    )

    report = load(RENDER_REPORT)
    require(
        report.get('reportSha256') == contract['staticEvidenceSelfHashes']['rendererReport'],
        'renderer report binding drift',
    )
    require(
        canon({k: v for k, v in report.items() if k != 'reportSha256'}) == report.get('reportSha256'),
        'renderer report self-hash mismatch',
    )
    require(report.get('caseCount') == 44, 'renderer report case-count drift')
    require(report.get('allPhysicalFingerprintsMatchHistorical') is True, 'renderer physical fingerprint failure')
    require(report.get('executionManifestSha256') == execution['manifestSha256'], 'renderer execution binding drift')
    return contract, execution, report


def validate_review_ci(ctx: dict[str, Any], contract: dict[str, Any], review_head: str) -> None:
    ci = ctx.get('reviewPackageCi', {})
    expected = contract.get('reviewPackageCiContract', {})
    require(ci.get('headSha') == review_head, 'review-package CI head does not equal reviewed package head')
    require(ci.get('workflowPath') == expected.get('workflowPath'), 'review-package CI workflow path drift')
    require(ci.get('jobName') == expected.get('jobName'), 'review-package CI job drift')
    require(ci.get('workflowRunAttempt') == 1, 'review-package CI must be attempt 1; GitHub Re-run is not accepted')
    require(ci.get('workflowConclusion') == 'success', 'review-package CI did not succeed')
    require(ci.get('packageCompileStepConclusion') == 'success', 'review-package compile step did not succeed')
    require(ci.get('packageTestsStepConclusion') == 'success', 'review-package test step did not succeed')
    require(ci.get('packageTestCount') == expected.get('expectedTestCount'), 'review-package test-count drift')
    require(ci.get('packageTestModules') == expected.get('testModules'), 'review-package test-module universe drift')
    require(
        ci.get('checkRunnerRawSha256') == expected.get('checkRunnerRawSha256'),
        'review-package check-runner bytes drift',
    )
    require(ci.get('scientificExecutionPerformed') is False, 'scientific execution occurred during review-package CI')


def validate_global_ordinal(ctx: dict[str, Any], contract: dict[str, Any]) -> None:
    candidate = contract['candidateIdentity']['globalScientificOrdinal']
    check = ctx.get('globalOrdinalRecheck', {})
    require(check.get('candidateOrdinal') == candidate, 'fresh global ordinal candidate drift')
    require(
        check.get('latestConsumedScientificOrdinal') == contract.get('latestKnownConsumedScientificOrdinal'),
        'global scientific ordinal advanced or consumption evidence drifted',
    )
    require(check.get('nextAvailableScientificOrdinal') == candidate, 'candidate is not the fresh next global scientific ordinal')
    for key in (
        'candidateOrdinalReservationCount',
        'candidateOrdinalAuthorizationCount',
        'candidateOrdinalScientificRunCount',
        'candidateOrdinalAuthorizationBranchCount',
        'candidateOrdinalDispatchBranchCount',
        'candidateOrdinalTerminalArtifactCount',
    ):
        require(check.get(key) == 0, f'candidate global ordinal is no longer fresh: {key}')
    require(check.get('completeReviewedExecutionSurfaceInspected') is True, 'global ordinal recheck is incomplete')


def validate_common(
    ctx: dict[str, Any],
    contract: dict[str, Any],
    execution: dict[str, Any],
    report: dict[str, Any],
) -> None:
    require(ctx.get('schemaVersion') == 1, 'context schema mismatch')
    issue = ctx.get('issue60', {})
    require(issue.get('latestDirectiveToken') == 'MYSTIC-STATE-0066', 'unexpected control directive token')
    require(issue.get('supersedingDirectivePresent') is False, 'superseding control directive present')

    publication = ctx.get('publication', {})
    require(publication.get('packagePublished') is True, 'package not published to dedicated review branch')
    require(
        isinstance(publication.get('reviewPrNumber'), int) and publication['reviewPrNumber'] > 0,
        'review PR missing',
    )
    for key in ('reviewHeadSha', 'reviewBaseMainSha', 'liveMainSha'):
        require(
            isinstance(publication.get(key), str) and SHA40.fullmatch(publication[key]) is not None,
            f'invalid {key}',
        )
    require(
        publication['liveMainSha'] == publication['reviewBaseMainSha'],
        'live main moved since reviewed package base',
    )
    expected_hashes = {
        key: spec['rawSha256'] for key, spec in contract.get('staticFiles', {}).items()
    }
    require(
        publication.get('publishedFileRawSha256') == expected_hashes,
        'published review-head file hashes do not equal frozen package',
    )
    validate_review_ci(ctx, contract, publication['reviewHeadSha'])

    collision = ctx.get('collisionRecheck', {})
    for key in (
        'executionKeyCodeCollisionCount',
        'executionKeyIssueCollisionCount',
        'executionKeyPrCollisionCount',
        'authorizationBranchHistoricalRunCount',
        'dispatchBranchHistoricalRunCount',
        'exactCaseArtifactCount',
        'terminalArtifactCount',
    ):
        require(collision.get(key) == 0, f'candidate collision/reuse evidence nonzero: {key}')
    require(collision.get('authorizationBranchCurrentExists') is False, 'candidate authorization branch already exists')
    require(collision.get('dispatchBranchCurrentExists') is False, 'candidate dispatch branch already exists')
    validate_global_ordinal(ctx, contract)

    seed = ctx.get('seedRecheck', {})
    require(
        seed.get('historicalSourceCount') == 166 and seed.get('historicalUniqueSeedCount') == 166,
        'historical seed universe drift',
    )
    require(
        seed.get('candidateSeedCount') == 44 and seed.get('candidateUniqueSeedCount') == 44,
        'candidate seed universe drift',
    )
    require(
        seed.get('sourceCandidateSeedIntersectionCount') == 0
        and seed.get('sourceCandidateSeedIntersection') == [],
        'candidate seed collision',
    )
    require(
        seed.get('executionManifestSha256') == execution['manifestSha256'],
        'fresh seed recheck not bound to execution manifest v4',
    )

    runtime = ctx.get('runtimeIdentity', {})
    require(runtime == execution.get('runtimeIdentityRequired'), 'runtime identity mismatch')

    renderer = ctx.get('rendererRecheck', {})
    require(renderer.get('reportSha256') == report['reportSha256'], 'renderer report recheck drift')
    require(renderer.get('casesCanonicalSha256') == report['casesCanonicalSha256'], 'renderer case-set recheck drift')
    require(renderer.get('caseCount') == 44, 'renderer case-count recheck drift')
    require(renderer.get('allPhysicalFingerprintsMatchHistorical') is True, 'renderer/input identity recheck failed')
    require(renderer.get('allRenderedInputHashesMatchReport') is True, 'rendered input bytes do not match report')
    require(
        renderer.get('executionManifestSha256') == execution['manifestSha256'],
        'renderer recheck execution manifest drift',
    )
    require(ctx.get('candidateIdentity', {}) == contract.get('candidateIdentity'), 'candidate ordinal/key/ref/title drift')


def evaluate(ctx: dict[str, Any]) -> dict[str, Any]:
    contract, execution, report = validate_static()
    validate_common(ctx, contract, execution, report)
    mode = ctx.get('mode')
    if mode == 'PRE_AUTHORIZATION':
        require(ctx.get('authorizationCommit') in (None, {}), 'authorization commit must not exist in PRE_AUTHORIZATION mode')
        return {
            'schemaVersion': 1,
            'guardId': 'public-tier1-full-spectrum-estimator-pilot-preauthorization-guard-v4',
            'status': 'READY_TO_CREATE_SEPARATE_ONE_FILE_AUTHORIZATION_NOT_EXECUTION_AUTHORIZED',
            'mode': mode,
            'protocolSha256': contract['protocolSha256'],
            'screeningAnalysisProtocolSha256': contract['screeningAnalysisProtocolSha256'],
            'executionManifestSha256': execution['manifestSha256'],
            'candidateIdentity': contract['candidateIdentity'],
            'authorizationFileCreationPermitted': True,
            'scientificExecutionAuthorized': False,
            'dispatchPermitted': False,
            'solverExecutionPerformed': False,
        }
    if mode == 'POST_AUTHORIZATION_COMMIT':
        auth = ctx.get('authorizationCommit', {})
        publication = ctx['publication']
        candidate = contract['candidateIdentity']
        require(isinstance(auth.get('sha'), str) and SHA40.fullmatch(auth['sha']) is not None, 'authorization commit sha invalid')
        require(auth.get('parentSha') == publication['reviewHeadSha'], 'authorization commit parent is not exact reviewed package head')
        require(auth.get('branch') == candidate['authorizationBranch'], 'authorization branch drift')
        require(auth.get('merged') is False, 'authorization commit/branch must remain unmerged')
        require(auth.get('authorizationOrdinal') == candidate['globalScientificOrdinal'], 'authorization ordinal drift')
        require(auth.get('executionKey') == candidate['executionKey'], 'authorization execution key drift')
        files = auth.get('changedFiles')
        require(isinstance(files, list) and len(files) == 1, 'authorization commit must change exactly one file')
        require(files[0] == 'experiments/full-spectrum-estimator-pilot-v2/authorization.json', 'unexpected authorization file path')
        require(auth.get('scientificPayloadChanged') is False, 'authorization commit changed scientific payload')
        return {
            'schemaVersion': 1,
            'guardId': 'public-tier1-full-spectrum-estimator-pilot-preauthorization-guard-v4',
            'status': 'ONE_FILE_AUTHORIZATION_COMMIT_STRUCTURALLY_VALID_DISPATCH_STILL_REQUIRES_FRESH_DUPLICATE_RUNTIME_GUARD',
            'mode': mode,
            'protocolSha256': contract['protocolSha256'],
            'screeningAnalysisProtocolSha256': contract['screeningAnalysisProtocolSha256'],
            'executionManifestSha256': execution['manifestSha256'],
            'candidateIdentity': candidate,
            'authorizationCommitSha': auth['sha'],
            'authorizationStructureValid': True,
            'scientificExecutionAuthorized': False,
            'dispatchPermitted': False,
            'solverExecutionPerformed': False,
        }
    raise Refusal('unsupported guard mode')


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--context', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        output = evaluate(load(args.context))
        output['guardSha256'] = canon(output)
        code = 0
    except Exception as exc:
        output = {
            'schemaVersion': 1,
            'guardId': 'public-tier1-full-spectrum-estimator-pilot-preauthorization-guard-v4',
            'status': 'REFUSED',
            'reason': str(exc),
            'scientificExecutionAuthorized': False,
            'dispatchPermitted': False,
            'solverExecutionPerformed': False,
        }
        output['guardSha256'] = canon(output)
        code = 2
    if args.output:
        args.output.write_text(json.dumps(output, indent=2, sort_keys=True, allow_nan=False) + '\n')
    print(json.dumps(output, indent=2, sort_keys=True))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
