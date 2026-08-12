#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
DEFAULT_CONTRACT = HERE / 'analysis-contract.v1.json'
CONTRACT_ID = 'public-tier1-full-spectrum-estimator-confirmation-analysis-v1'
CONTRACT_SHA = '08f30045f6f595e5e11cca5401aa4e1ea88862651ed5d7439671a538bc532cc7'
PREREG_SHA = 'a801000ea0af81a109f9e0e1ec2b28befa0703e4ec47e9f85ee1b10b448a95b6'
MANIFEST_SHA = '9344ed18cfa93849d730cf080fe9f6c4c57f0cc5ea7b1be7ba9aa15d501c3fa8'
EVIDENCE_ID = 'public-tier1-full-spectrum-estimator-confirmation-normalized-evidence-v1'
ANALYSIS_ID = 'public-tier1-full-spectrum-estimator-confirmation-analysis-v1'
PRIMARY_CHANNELS = (
    'photopicLuminanceCdM2',
    'scotopicLuminanceScotCdM2',
    'johnsonVEffectiveRadiance_mW_m2_nm_sr',
)

class AnalysisRefusal(RuntimeError):
    pass

def require(condition: bool, message: str) -> None:
    if not condition:
        raise AnalysisRefusal(message)

def canon(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()

def self_hash(value: dict[str, Any], field: str) -> str:
    copy = dict(value)
    copy[field] = None
    return canon(copy)

def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    require(isinstance(value, dict), f'expected JSON object: {path}')
    return value

def validate_contract(contract: dict[str, Any]) -> None:
    require(contract.get('contractId') == CONTRACT_ID and contract.get('contractSha256') == CONTRACT_SHA, 'analysis contract identity drift')
    require(contract.get('contractSha256') == self_hash(contract, 'contractSha256'), 'analysis contract self-hash mismatch')
    prereg_binding = contract.get('confirmationPreregistration') or {}
    require(prereg_binding.get('preregistrationSha256') == PREREG_SHA, 'analysis contract preregistration binding drift')
    manifest_binding = contract.get('confirmationExecutionManifest') or {}
    require(manifest_binding.get('manifestSha256') == MANIFEST_SHA, 'analysis contract execution-manifest binding drift')
    ev = contract.get('confirmationEvaluation') or {}
    require(ev.get('primaryChannels') == list(PRIMARY_CHANNELS), 'primary channel contract drift')
    require(ev.get('freshBlocksPerCandidateExactly') == 4, 'confirmation block-count contract drift')
    require(ev.get('historicalFinalTargetRsem') == 0.05 and ev.get('historicalMaximumAcceptedRsem') == 0.08, 'confirmation RSEM thresholds drift')
    require(ev.get('screeningBlocksMayEnterConfirmationStatistics') is False and ev.get('automaticExtensionBeyondFourBlocks') is False and ev.get('automaticGlobalEstimatorSelection') is False, 'confirmation analysis boundary drift')
    boundary = contract.get('downstreamBoundary') or {}
    for key in ('scientificExecutionAuthorized','authorizationOrdinalAllocated','dispatchAuthorized','githubRerunAllowed','retryAllowed','resumeAllowed','modelFittingAuthorized','modelSelectionAuthorized','holdoutValidationOpeningAuthorized','tier2Authorized','productionPromotionAuthorized'):
        require(boundary.get(key) is False, f'downstream boundary drift: {key}')

def validate_prereg(prereg: dict[str, Any]) -> None:
    supplied = prereg.get('preregistrationSha256')
    require(supplied == PREREG_SHA and supplied == self_hash(prereg, 'preregistrationSha256'), 'confirmation preregistration identity/self-hash drift')
    require(prereg.get('status') == 'REVIEW_ONLY_FROZEN_BEFORE_ANY_CONFIRMATION_RESULT', 'confirmation preregistration status drift')
    evalp = prereg.get('confirmationEvaluation') or {}
    require(evalp.get('primaryChannels') == list(PRIMARY_CHANNELS), 'prereg primary channel drift')
    require(evalp.get('historicalFinalTargetRsem') == 0.05 and evalp.get('historicalMaximumAcceptedRsem') == 0.08, 'prereg RSEM threshold drift')
    require(evalp.get('confirmationBlocksOnly') is True and evalp.get('screeningBlocksExcludedFromFinalPrecisionGate') is True and evalp.get('automaticExtensionBeyondFirstConfirmation') is False and evalp.get('automaticGlobalEstimatorSelection') is False, 'prereg confirmation boundary drift')

def validate_evidence(evidence: dict[str, Any], prereg: dict[str, Any]) -> None:
    require(evidence.get('evidenceId') == EVIDENCE_ID and evidence.get('status') == 'CONFIRMATION_EVIDENCE_NORMALIZED', 'normalized confirmation evidence identity/status drift')
    require(evidence.get('analysisContractSha256') == CONTRACT_SHA and evidence.get('executionManifestSha256') == MANIFEST_SHA, 'normalized evidence binding drift')
    require(evidence.get('evidenceSha256') == self_hash(evidence, 'evidenceSha256'), 'normalized evidence self-hash mismatch')
    require(evidence.get('sourceRunAttempt') == 1 and isinstance(evidence.get('sourceRunId'), int) and evidence['sourceRunId'] > 0, 'normalized evidence source run drift')
    require(isinstance(evidence.get('sourceOrdinal'), int) and evidence['sourceOrdinal'] >= 17, 'normalized evidence source ordinal drift')
    require(evidence.get('caseCount') == 24 and isinstance(evidence.get('cases'), list) and len(evidence['cases']) == 24, 'normalized evidence case count drift')
    require(evidence.get('primaryChannels') == list(PRIMARY_CHANNELS), 'normalized evidence primary-channel surface drift')
    require(evidence.get('exactZeroPreserved') is True and evidence.get('epsilonSubstitutionPerformed') is False and evidence.get('scientificSolverReexecutedDuringNormalization') is False and evidence.get('holdoutValuesRead') is False, 'normalized evidence protected boundary drift')

    expected_cases = {c['caseId']: c for c in prereg['caseDesign']['cases']}
    rows = evidence['cases']
    require({r.get('caseId') for r in rows} == set(expected_cases), 'normalized evidence contains non-confirmation/missing cases')
    for row in rows:
        cid = row['caseId']; expected = expected_cases[cid]
        for key in ('candidateId','geometryId','method','confirmationBlock','seed','photonHistories'):
            require(row.get(key) == expected.get(key), f'normalized evidence/prereg mismatch: {cid}.{key}')
        require(row.get('importanceCenterNm') == expected.get('importanceCenterNm'), f'normalized evidence/prereg mismatch: {cid}.importanceCenterNm')
        channels = row.get('channels')
        require(isinstance(channels, dict) and set(channels) == set(PRIMARY_CHANNELS), f'normalized evidence channel drift: {cid}')
        zero_map = row.get('zeroHitByChannel')
        require(isinstance(zero_map, dict) and set(zero_map) == set(PRIMARY_CHANNELS), f'normalized evidence zero-map drift: {cid}')
        for name in PRIMARY_CHANNELS:
            value = channels[name]
            require(isinstance(value, (int, float)) and math.isfinite(value) and value >= 0, f'normalized evidence invalid channel value: {cid}.{name}')
            require(zero_map[name] is (value == 0.0), f'normalized evidence zero-map/value drift: {cid}.{name}')
        require(row.get('anyPrimaryChannelZeroHit') is any(zero_map.values()), f'normalized evidence aggregate zero flag drift: {cid}')

def channel_statistics(values: list[float]) -> dict[str, Any]:
    require(len(values) == 4, 'confirmation channel requires exactly four blocks')
    require(all(math.isfinite(x) and x >= 0 for x in values), 'confirmation channel contains invalid value')
    mean = sum(values) / 4.0
    sample_std = statistics.stdev(values)
    rsem = None if mean <= 0 else sample_std / math.sqrt(4.0) / mean
    return {'values': values, 'mean': mean, 'sampleStd': sample_std, 'rsem': rsem, 'anyExactZero': any(x == 0.0 for x in values)}

def classify(stats_by_channel: dict[str, dict[str, Any]]) -> str:
    if any(s['anyExactZero'] or s['mean'] <= 0 or s['rsem'] is None or not math.isfinite(s['rsem']) for s in stats_by_channel.values()):
        return 'CONFIRMATION_PRECISION_NOT_ESTABLISHED'
    rsems = [stats_by_channel[ch]['rsem'] for ch in PRIMARY_CHANNELS]
    if all(r <= 0.05 for r in rsems):
        return 'CONFIRMED_AT_HISTORICAL_FINAL_TARGET'
    if all(r <= 0.08 for r in rsems):
        return 'CONFIRMED_WITHIN_HISTORICAL_MAXIMUM'
    return 'CONFIRMATION_PRECISION_NOT_ESTABLISHED'

def analyze(prereg: dict[str, Any], evidence: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    validate_contract(contract); validate_prereg(prereg); validate_evidence(evidence, prereg)
    rows_by_candidate: dict[str, list[dict[str, Any]]] = {}
    for row in evidence['cases']:
        rows_by_candidate.setdefault(row['candidateId'], []).append(row)
    candidates = prereg['candidates']
    require(set(rows_by_candidate) == {c['candidateId'] for c in candidates}, 'confirmation candidate universe drift')
    reports = []
    counts = {'CONFIRMED_AT_HISTORICAL_FINAL_TARGET': 0, 'CONFIRMED_WITHIN_HISTORICAL_MAXIMUM': 0, 'CONFIRMATION_PRECISION_NOT_ESTABLISHED': 0}
    for candidate in candidates:
        cid = candidate['candidateId']
        rows = sorted(rows_by_candidate[cid], key=lambda r: r['confirmationBlock'])
        require([r['confirmationBlock'] for r in rows] == [1,2,3,4], f'confirmation block identity drift: {cid}')
        stats = {ch: channel_statistics([float(r['channels'][ch]) for r in rows]) for ch in PRIMARY_CHANNELS}
        classification = classify(stats); counts[classification] += 1
        reports.append({
            'candidateId': cid, 'geometryId': candidate['geometryId'], 'method': candidate['method'],
            'importanceCenterNm': candidate['importanceCenterNm'], 'confirmationBlockCount': 4,
            'confirmationCaseIds': [r['caseId'] for r in rows],
            'screeningCaseIdsExcludedFromStatistics': list(candidate['pilotCaseIds']),
            'screeningClassification': candidate['screeningClassification'],
            'statisticsByPrimaryChannel': stats, 'classification': classification,
        })
    result = {
        'schemaVersion': 1, 'analysisId': ANALYSIS_ID, 'analysisSha256': None,
        'status': 'CONFIRMATION_ANALYZED_NO_AUTOMATIC_DOWNSTREAM_TRANSITION',
        'analysisContractSha256': CONTRACT_SHA, 'confirmationPreregistrationSha256': PREREG_SHA,
        'confirmationExecutionManifestSha256': MANIFEST_SHA, 'normalizedEvidenceSha256': evidence['evidenceSha256'],
        'sourceRunId': evidence['sourceRunId'], 'sourceRunAttempt': 1, 'sourceOrdinal': evidence['sourceOrdinal'],
        'candidateCount': 6, 'freshBlockCount': 24, 'primaryChannels': list(PRIMARY_CHANNELS),
        'classificationCounts': counts, 'candidateReports': reports,
        'screeningBlocksIncludedInConfirmationStatistics': False, 'automaticExtensionPerformed': False,
        'automaticGlobalEstimatorSelectionPerformed': False, 'modelFittingPerformed': False,
        'modelSelectionPerformed': False, 'holdoutValuesRead': False, 'tier2TransitionPerformed': False,
        'productionPromotionPerformed': False,
        'nextStep': 'separate reviewed scientific decision after immutable confirmation analysis; no automatic fitting/model-selection/holdout/Tier-2/production transition',
    }
    result['analysisSha256'] = self_hash(result, 'analysisSha256')
    return result

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--preregistration', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--analysis-contract', type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        value = analyze(load(args.preregistration), load(args.evidence), load(args.analysis_contract))
        args.output.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')
        print(json.dumps({'status': value['status'], 'analysisSha256': value['analysisSha256'], 'classificationCounts': value['classificationCounts'], 'automaticGlobalEstimatorSelectionPerformed': False}, sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps({'status': 'REFUSED', 'reason': str(exc), 'automaticGlobalEstimatorSelectionPerformed': False}, sort_keys=True))
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
