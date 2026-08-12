#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

DECISION_ID = 'public-tier1-full-spectrum-estimator-confirmation-decision-v1'
DECISION_STATUS = 'REVIEW_ONLY_POST_RESULT_SCIENTIFIC_DECISION_NO_EXECUTION'
ANALYSIS_ID = 'public-tier1-full-spectrum-estimator-confirmation-analysis-v1'
ANALYSIS_SHA = '69d58846e889fcd5051cdf66db9660f40d788271c0661b6742e236494f0f179d'
EVIDENCE_SHA = '50801665ce8a00e3aa9ab019712c7fc62d0df1c7e55fb6c1568c803033353043'
ACQUISITION_SHA = '01567b262b018c2457096d658fdb6a148c0e325cc0ba78c6ecd56a9d104bf673'
ARTIFACT_SHA = '227e0fdba651ba8647846f9f3598fc4d4b40eb9ffd766d80874f584b91e59b76'
ARTIFACT_DIGEST = 'sha256:' + ARTIFACT_SHA
RESOLUTION_OPTIONS = [
    'SEPARATE_PREREGISTERED_TARGETED_ESTIMATOR_COMPARISON_OR_ACQUISITION',
    'UNCERTAINTY_AWARE_CENSORED_OR_NOISY_LABEL_WITH_FROZEN_LIKELIHOOD',
    'EXPLICIT_OOD_OR_DOMAIN_EXCLUSION',
    'UNRESOLVED_REFUSAL',
]
EXPECTED = {
    'train-0009-alis-500': {
        'geometry': 'train-0009', 'center': 500.0,
        'classification': 'CONFIRMED_AT_HISTORICAL_FINAL_TARGET',
        'decision': 'GEOMETRY_SPECIFIC_CONFIGURATION_CONFIRMED_AT_FINAL_TARGET',
        'treatment': 'CONFIGURATION_ELIGIBLE_FOR_SEPARATE_FRESH_TRAINING_ACQUISITION_DECISION',
        'zero': False, 'options': [],
    },
    'train-0013-alis-600': {
        'geometry': 'train-0013', 'center': 600.0,
        'classification': 'CONFIRMATION_PRECISION_NOT_ESTABLISHED',
        'decision': 'NOT_ADMITTED_PRECISION_NOT_ESTABLISHED',
        'treatment': 'EXCLUDE_FROM_PRECISION_ESTABLISHED_TRAINING_LABEL_UNIVERSE_AND_MARK_UNRESOLVED',
        'zero': False, 'options': RESOLUTION_OPTIONS,
    },
    'train-0014-alis-600': {
        'geometry': 'train-0014', 'center': 600.0,
        'classification': 'CONFIRMED_WITHIN_HISTORICAL_MAXIMUM',
        'decision': 'GEOMETRY_SPECIFIC_CONFIGURATION_CONFIRMED_WITHIN_HISTORICAL_MAXIMUM',
        'treatment': 'CONFIGURATION_ELIGIBLE_FOR_SEPARATE_FRESH_TRAINING_ACQUISITION_DECISION_WITH_5_PERCENT_TARGET_NOT_MET',
        'zero': False, 'options': [],
    },
    'train-0041-alis-550': {
        'geometry': 'train-0041', 'center': 550.0,
        'classification': 'CONFIRMATION_PRECISION_NOT_ESTABLISHED',
        'decision': 'NOT_ADMITTED_PRECISION_NOT_ESTABLISHED',
        'treatment': 'EXCLUDE_FROM_PRECISION_ESTABLISHED_TRAINING_LABEL_UNIVERSE_AND_MARK_UNRESOLVED',
        'zero': False, 'options': RESOLUTION_OPTIONS,
    },
    'train-0041-alis-600': {
        'geometry': 'train-0041', 'center': 600.0,
        'classification': 'CONFIRMATION_PRECISION_NOT_ESTABLISHED',
        'decision': 'NOT_ADMITTED_PRECISION_NOT_ESTABLISHED',
        'treatment': 'EXCLUDE_FROM_PRECISION_ESTABLISHED_TRAINING_LABEL_UNIVERSE_AND_MARK_UNRESOLVED',
        'zero': False, 'options': RESOLUTION_OPTIONS,
    },
    'train-0047-alis-500': {
        'geometry': 'train-0047', 'center': 500.0,
        'classification': 'CONFIRMATION_PRECISION_NOT_ESTABLISHED',
        'decision': 'NOT_ADMITTED_RARE_EVENT_EXACT_ZERO_PRECISION_NOT_ESTABLISHED',
        'treatment': 'EXCLUDE_FROM_FINITE_PRECISION_TRAINING_LABEL_UNIVERSE_AND_MARK_RARE_EVENT_UNRESOLVED',
        'zero': True, 'options': RESOLUTION_OPTIONS,
    },
}


class Refusal(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Refusal(message)


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    ).hexdigest()


def self_hash(value: dict[str, Any], field: str) -> str:
    copy = dict(value)
    copy[field] = None
    return canonical_hash(copy)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    require(isinstance(value, dict), f'expected object: {path}')
    return value


def validate_analysis(analysis: dict[str, Any]) -> dict[str, dict[str, Any]]:
    require(analysis.get('analysisId') == ANALYSIS_ID, 'analysis id drift')
    require(analysis.get('analysisSha256') == ANALYSIS_SHA, 'analysis identity drift')
    require(analysis.get('analysisSha256') == self_hash(analysis, 'analysisSha256'), 'analysis self-hash mismatch')
    require(analysis.get('normalizedEvidenceSha256') == EVIDENCE_SHA, 'normalized evidence binding drift')
    require(
        analysis.get('sourceRunId') == 31561567317
        and analysis.get('sourceRunAttempt') == 1
        and analysis.get('sourceOrdinal') == 17,
        'source run/ordinal drift',
    )
    require(analysis.get('candidateCount') == 6 and analysis.get('freshBlockCount') == 24, 'analysis universe drift')
    require(
        analysis.get('status') == 'CONFIRMATION_ANALYZED_NO_AUTOMATIC_DOWNSTREAM_TRANSITION',
        'analysis status drift',
    )
    require(
        analysis.get('classificationCounts')
        == {
            'CONFIRMATION_PRECISION_NOT_ESTABLISHED': 4,
            'CONFIRMED_AT_HISTORICAL_FINAL_TARGET': 1,
            'CONFIRMED_WITHIN_HISTORICAL_MAXIMUM': 1,
        },
        'classification counts drift',
    )
    for key in (
        'automaticExtensionPerformed',
        'automaticGlobalEstimatorSelectionPerformed',
        'modelFittingPerformed',
        'modelSelectionPerformed',
        'holdoutValuesRead',
        'tier2TransitionPerformed',
        'productionPromotionPerformed',
        'screeningBlocksIncludedInConfirmationStatistics',
    ):
        require(analysis.get(key) is False, f'protected boundary drift: {key}')

    reports = analysis.get('candidateReports')
    require(isinstance(reports, list) and len(reports) == 6, 'candidate reports drift')
    by_id = {report.get('candidateId'): report for report in reports}
    require(set(by_id) == set(EXPECTED), 'candidate id drift')

    for candidate_id, expected in EXPECTED.items():
        report = by_id[candidate_id]
        require(
            report.get('geometryId') == expected['geometry']
            and report.get('importanceCenterNm') == expected['center']
            and report.get('method') == 'alis-alt-importance',
            f'candidate metadata drift: {candidate_id}',
        )
        require(report.get('classification') == expected['classification'], f'candidate classification drift: {candidate_id}')
        stats = report.get('statisticsByPrimaryChannel') or {}
        require(len(stats) == 3, f'channel universe drift: {candidate_id}')
        observed_zero = any(bool(channel.get('anyExactZero')) for channel in stats.values())
        require(observed_zero is expected['zero'], f'exact-zero drift: {candidate_id}')
        for channel_name, channel in stats.items():
            rsem = channel.get('rsem')
            require(
                isinstance(rsem, (int, float)) and math.isfinite(rsem) and rsem >= 0,
                f'invalid RSEM: {candidate_id}.{channel_name}',
            )
    return by_id


def validate_decision(decision: dict[str, Any], reports: dict[str, dict[str, Any]]) -> None:
    require(decision.get('schemaVersion') == 1, 'decision schema drift')
    require(decision.get('decisionId') == DECISION_ID, 'decision id drift')
    require(decision.get('status') == DECISION_STATUS, 'decision status drift')
    require(decision.get('governance') == 'MYSTIC-STATE-0067', 'governance drift')
    require(decision.get('decisionSha256') == self_hash(decision, 'decisionSha256'), 'decision self-hash mismatch')

    source = decision.get('sourceConfirmation') or {}
    require(source.get('repository') == 'search-maker/twilight-mystic-experiments', 'source repository drift')
    require(
        source.get('runId') == 31561567317
        and source.get('runAttempt') == 1
        and source.get('scientificOrdinal') == 17,
        'decision source run drift',
    )
    require(source.get('headSha') == 'c6de39a570f113ff82c86576aeed2fdcf1498e14', 'decision source head drift')
    require(source.get('aggregateJobId') == 94010476759, 'aggregate job binding drift')
    require(
        source.get('analysisArtifactId') == 9128583943
        and source.get('analysisArtifactName') == 'full-spectrum-estimator-confirmation-v1-ordinal17-analysis'
        and source.get('analysisArtifactDigest') == ARTIFACT_DIGEST
        and source.get('analysisArtifactDownloadedZipSha256') == ARTIFACT_SHA,
        'artifact binding drift',
    )
    require(source.get('acquisitionManifestSha256') == ACQUISITION_SHA, 'acquisition binding drift')
    require(
        source.get('analysisSha256') == ANALYSIS_SHA
        and source.get('normalizedEvidenceSha256') == EVIDENCE_SHA,
        'analysis/evidence binding drift',
    )
    require(
        source.get('analysisStatus') == 'CONFIRMATION_ANALYZED_NO_AUTOMATIC_DOWNSTREAM_TRANSITION',
        'analysis status binding drift',
    )
    require(
        source.get('analysisContractSha256') == '08f30045f6f595e5e11cca5401aa4e1ea88862651ed5d7439671a538bc532cc7'
        and source.get('confirmationPreregistrationSha256') == 'a801000ea0af81a109f9e0e1ec2b28befa0703e4ec47e9f85ee1b10b448a95b6'
        and source.get('executionManifestSha256') == '9344ed18cfa93849d730cf080fe9f6c4c57f0cc5ea7b1be7ba9aa15d501c3fa8',
        'frozen contract binding drift',
    )

    semantics = decision.get('decisionSemantics') or {}
    require(
        semantics.get('decisionType') == 'GEOMETRY_SPECIFIC_NUMERICAL_CONFIGURATION_INTERPRETATION_ONLY',
        'decision type drift',
    )
    for key in (
        'globalImportanceCenterSelected',
        'globalEstimatorSelected',
        'methodsOrCentersAveraged',
        'confirmationValuesConvertedToTrainingEvidence',
        'freshTrainingSeedsOrOrdinalAllocated',
        'newScientificExecutionAuthorized',
        'modelFittingAuthorized',
        'modelSelectionAuthorized',
        'protectedHoldoutOpeningAuthorized',
        'tier2Authorized',
        'productionPromotionAuthorized',
    ):
        require(semantics.get(key) is False, f'downstream authorization drift: {key}')

    frozen = decision.get('frozenInterpretation') or {}
    require(
        frozen.get('historicalFinalTargetRsem') == 0.05
        and frozen.get('historicalMaximumAcceptedRsem') == 0.08,
        'threshold drift',
    )
    require(
        frozen.get('candidateCount') == 6
        and frozen.get('confirmedAtFinalTargetCount') == 1
        and frozen.get('confirmedWithinHistoricalMaximumCount') == 1
        and frozen.get('precisionNotEstablishedCount') == 4,
        'decision count drift',
    )
    require(frozen.get('exactZeroPolicy') == 'PRESERVE_EXACT_ZERO_NO_EPSILON', 'zero policy drift')
    require(
        frozen.get('screeningBlocksIncludedInConfirmationStatistics') is False
        and frozen.get('automaticExtensionPerformed') is False,
        'confirmation boundary drift',
    )

    rows = frozen.get('candidateDecisions')
    require(isinstance(rows, list) and len(rows) == 6, 'decision candidate rows drift')
    by_id = {row.get('candidateId'): row for row in rows}
    require(set(by_id) == set(EXPECTED), 'decision candidate universe drift')

    for candidate_id, expected in EXPECTED.items():
        row = by_id[candidate_id]
        require(
            row.get('geometryId') == expected['geometry']
            and row.get('importanceCenterNm') == expected['center']
            and row.get('method') == 'alis-alt-importance',
            f'decision metadata drift: {candidate_id}',
        )
        require(
            row.get('sourceConfirmationClassification') == expected['classification']
            and row.get('decision') == expected['decision'],
            f'decision mapping drift: {candidate_id}',
        )
        require(row.get('currentTrainingTreatment') == expected['treatment'], f'treatment drift: {candidate_id}')
        require(row.get('futureResolutionOptions') == expected['options'], f'resolution options drift: {candidate_id}')
        require(
            row.get('configurationScope') == 'EXACT_GEOMETRY_AND_FROZEN_PHYSICAL_INPUTS_ONLY',
            f'scope drift: {candidate_id}',
        )
        require(row.get('globalEstimatorUseAuthorized') is False, f'global-use drift: {candidate_id}')
        require(row.get('confirmationValuesAdmittedAsTrainingLabels') is False, f'confirmation-as-training drift: {candidate_id}')
        require(row.get('freshTrainingExecutionRequiredBeforeAnyTrainingLabelUse') is True, f'fresh-training boundary drift: {candidate_id}')
        require(row.get('exactZeroObserved') is expected['zero'], f'decision exact-zero drift: {candidate_id}')
        maximum_rsem = max(channel['rsem'] for channel in reports[candidate_id]['statisticsByPrimaryChannel'].values())
        require(
            abs(float(row.get('maximumPrimaryChannelRsem')) - maximum_rsem) < 1e-15,
            f'max RSEM drift: {candidate_id}',
        )

    next_boundary = decision.get('nextBoundary') or {}
    require(next_boundary.get('noAutomaticTransition') is True, 'next-boundary drift')
    require(
        next_boundary.get('confirmedConfigurationUse')
        == 'MAY_BE_REFERENCED_ONLY_BY_A_FUTURE_SEPARATELY_REVIEWED_FRESH_TRAINING_ACQUISITION_OR_REPAIR_CONTRACT_FOR_THE_EXACT_GEOMETRY',
        'confirmed-use boundary drift',
    )
    require(
        next_boundary.get('unresolvedGeometryUse')
        == 'REFUSE_AS_PRECISION_ESTABLISHED_TRAINING_LABEL_UNTIL_SEPARATELY_RESOLVED_OR_EXPLICITLY_EXCLUDED_OOD',
        'unresolved-use boundary drift',
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--analysis', type=Path, required=True)
    parser.add_argument('--decision', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()

    try:
        analysis = load(args.analysis)
        decision = load(args.decision)
        reports = validate_analysis(analysis)
        validate_decision(decision, reports)
        result = {
            'status': 'PASS',
            'analysisSha256': analysis['analysisSha256'],
            'decisionSha256': decision['decisionSha256'],
            'candidateCount': 6,
            'automaticDownstreamTransition': False,
        }
        if args.output:
            args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception as exc:
        result = {
            'status': 'REFUSED',
            'reason': str(exc),
            'automaticDownstreamTransition': False,
        }
        if args.output:
            args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
        print(json.dumps(result, sort_keys=True))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
