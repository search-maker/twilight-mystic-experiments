#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
V6_PATH = ROOT / 'analyze_full_spectrum_estimator_pilot_v6.py'
NORM7_PATH = ROOT / 'normalize_full_spectrum_estimator_pilot_results_v7.py'
DEFAULT_V7_CONTRACT = ROOT.parents[1] / 'experiments' / 'full-spectrum-estimator-pilot-v2' / 'postprocess-contract.ordinal16.v7.json'
DEFAULT_V8_CONTRACT = ROOT.parents[1] / 'experiments' / 'full-spectrum-estimator-pilot-v2' / 'postprocess-analyzer-contract.ordinal16.v8.json'

V7_EVIDENCE_ID = 'public-tier1-full-spectrum-estimator-pilot-normalized-evidence-v7'
V6_EVIDENCE_ID = 'public-tier1-full-spectrum-estimator-pilot-normalized-evidence-v6'
ANALYSIS_ID = 'public-tier1-full-spectrum-estimator-pilot-analysis-v7-compat-v8'
EXPECTED_V7_EVIDENCE_SHA256 = 'd0979b6827f80e2f2b76f62340a72dcec14a3cb016b9645680c38da0d5fcf0f5'
EXPECTED_V7_CONTRACT_SHA256 = 'd7d9c98e5676689959dcc3ffca4778925728df819d3fdbc7e39bfa9be92069a3'
EXPECTED_SOURCE_RUN_ID = 31546667072
EXPECTED_SOURCE_RUN_ATTEMPT = 1
EXPECTED_SOURCE_HEAD_SHA = '183188bdbe5a899f5dcd1bc4e423fa385d26e3af'
EXPECTED_CASE_COUNT = 44
EXPECTED_V6_BLOB_SHA1 = '693add1506ae6acc5d749ef0fe110c386cac35f7'
EXPECTED_NORM7_BLOB_SHA1 = 'fe45136d595e6039b355d68cd2a926259af0ac40'
EXPECTED_V7_CONTRACT_BLOB_SHA1 = '47e90aa128942276e1510305449bb3c58930032e'


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'cannot load module: {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


v6 = _load_module('full_spectrum_analyzer_v6', V6_PATH)
norm7 = _load_module('full_spectrum_normalizer_v7', NORM7_PATH)


def canon(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    ).hexdigest()


def git_blob_sha1(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(f'blob {len(raw)}\0'.encode() + raw).hexdigest()


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f'expected object: {path}')
    return value


def _self_hash(value: dict[str, Any], field: str) -> str:
    copy_value = copy.deepcopy(value)
    copy_value[field] = None
    return canon(copy_value)


def validate_code_identity(v7_contract_path: Path) -> None:
    if git_blob_sha1(V6_PATH) != EXPECTED_V6_BLOB_SHA1:
        raise ValueError('frozen v6 analyzer byte identity drift')
    if git_blob_sha1(NORM7_PATH) != EXPECTED_NORM7_BLOB_SHA1:
        raise ValueError('normalizer v7 byte identity drift')
    if git_blob_sha1(v7_contract_path) != EXPECTED_V7_CONTRACT_BLOB_SHA1:
        raise ValueError('postprocess v7 contract byte identity drift')


def validate_v8_contract(contract: dict[str, Any]) -> None:
    if contract.get('contractSha256') != _self_hash(contract, 'contractSha256'):
        raise ValueError('postprocess analyzer v8 contract self-hash mismatch')
    expected = {
        'schemaVersion': 1,
        'contractId': 'full-spectrum-estimator-pilot-v2-ordinal16-postprocess-analyzer-v8',
        'status': 'POSTPROCESS_ANALYZER_COMPATIBILITY_PENDING_REVIEW',
        'sourceScientificRunId': EXPECTED_SOURCE_RUN_ID,
        'sourceScientificRunAttempt': EXPECTED_SOURCE_RUN_ATTEMPT,
        'sourceScientificOrdinal': 16,
        'sourceScientificHeadSha': EXPECTED_SOURCE_HEAD_SHA,
        'sourceScientificCaseCount': EXPECTED_CASE_COUNT,
        'sourcePostprocessV7RunId': 31554217669,
        'sourcePostprocessV7RunAttempt': 1,
        'sourcePostprocessV7HeadSha': '2abd77f5a3786e4d6b8d8b96abd34263a8108843',
        'sourcePostprocessV7Branch': 'postprocess/full-spectrum-estimator-pilot-v2-ordinal16-v7',
        'sourcePostprocessV7Workflow': '.github/workflows/full-spectrum-estimator-pilot-v2-ordinal16-postprocess-v7.yml',
        'sourcePostprocessV7Conclusion': 'failure',
        'sourcePostprocessV7Refusal': 'normalized evidence identity/boundary drift',
        'normalizedEvidenceV7Sha256': EXPECTED_V7_EVIDENCE_SHA256,
        'postprocessV7ContractSha256': EXPECTED_V7_CONTRACT_SHA256,
        'postprocessV7ContractGitBlobSha1': EXPECTED_V7_CONTRACT_BLOB_SHA1,
        'normalizerV7GitBlobSha1': EXPECTED_NORM7_BLOB_SHA1,
        'frozenAnalyzerV6GitBlobSha1': EXPECTED_V6_BLOB_SHA1,
        'frozenAnalyzerV6Path': 'review/full-spectrum-estimator-pilot-v2/analyze_full_spectrum_estimator_pilot_v6.py',
        'normalizerV7Path': 'review/full-spectrum-estimator-pilot-v2/normalize_full_spectrum_estimator_pilot_results_v7.py',
        'compatibilityAnalyzerPath': 'review/full-spectrum-estimator-pilot-v2/analyze_full_spectrum_estimator_pilot_v7_compat.py',
        'solverExecutionAuthorized': False,
        'syntaxCheckAuthorized': False,
        'githubRerunOfScientificRunAllowed': False,
        'githubRerunOfPostprocessV7Allowed': False,
        'newScientificOrdinalAuthorized': False,
        'modelFittingAuthorized': False,
        'modelSelectionAuthorized': False,
        'holdoutValidationOpeningAuthorized': False,
        'tier2Authorized': False,
        'productionPromotionAuthorized': False,
    }
    if set(contract) != set(expected) | {'contractSha256'}:
        raise ValueError('postprocess analyzer v8 contract key-set drift')
    for key, wanted in expected.items():
        if contract.get(key) != wanted:
            raise ValueError(f'postprocess analyzer v8 contract drift: {key}')


def expected_postprocess_adapter(v7_contract: dict[str, Any]) -> dict[str, Any]:
    return {
        'contractId': v7_contract['contractId'],
        'contractSha256': v7_contract['contractSha256'],
        'sourceScientificRunId': EXPECTED_SOURCE_RUN_ID,
        'sourceScientificRunAttempt': EXPECTED_SOURCE_RUN_ATTEMPT,
        'sourceScientificHeadSha': EXPECTED_SOURCE_HEAD_SHA,
        'historicalNormalizerVersion': 6,
        'historicalNormalizerStatus': 'REFUSED',
        'historicalNormalizerReason': 'output grid step mismatch',
        'normalizerVersion': 7,
        'outputGridSource': 'extraterrestrial solar spectrum serialization',
        'outputNodeCount': 8001,
        'outputNominalStepNm': 0.05,
        'outputPointToleranceNm': 5e-05,
        'vroomCalculationGridStillVerifiedByV6': True,
        'scientificSolverReexecuted': False,
        'holdoutValuesRead': False,
    }


def build_v6_compatibility_view(
    evidence_v7: dict[str, Any],
    v7_contract: dict[str, Any],
    v8_contract: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    norm7.validate_postprocess_contract(v7_contract)
    validate_v8_contract(v8_contract)

    if v7_contract.get('contractSha256') != EXPECTED_V7_CONTRACT_SHA256:
        raise ValueError('postprocess v7 contract identity drift')
    if evidence_v7.get('evidenceId') != V7_EVIDENCE_ID:
        raise ValueError('normalized v7 evidence identity drift')
    if evidence_v7.get('protocolSha256') != v6.ACQUISITION_PROTOCOL_SHA:
        raise ValueError('normalized v7 acquisition protocol drift')
    if evidence_v7.get('executionManifestSha256') != v6.EXEC_SHA:
        raise ValueError('normalized v7 execution manifest drift')
    if evidence_v7.get('caseCount') != EXPECTED_CASE_COUNT:
        raise ValueError('normalized v7 case-count drift')
    if evidence_v7.get('holdoutValuesRead') is not False:
        raise ValueError('normalized v7 protected-boundary drift')

    supplied_sha = evidence_v7.get('evidenceSha256')
    if supplied_sha != v6.canon({k: v for k, v in evidence_v7.items() if k != 'evidenceSha256'}):
        raise ValueError('normalized v7 evidence self-hash mismatch')
    if supplied_sha != EXPECTED_V7_EVIDENCE_SHA256:
        raise ValueError('normalized v7 evidence exact identity drift')
    if v8_contract.get('normalizedEvidenceV7Sha256') != supplied_sha:
        raise ValueError('v8 contract does not bind exact normalized v7 evidence')

    adapter = evidence_v7.get('postprocessAdapter')
    expected_adapter = expected_postprocess_adapter(v7_contract)
    if not isinstance(adapter, dict) or adapter != expected_adapter:
        raise ValueError('normalized v7 postprocess adapter provenance drift')

    compatibility = copy.deepcopy(evidence_v7)
    compatibility.pop('postprocessAdapter', None)
    compatibility['evidenceId'] = V6_EVIDENCE_ID
    compatibility.pop('evidenceSha256', None)
    compatibility['evidenceSha256'] = v6.canon(compatibility)
    return compatibility, supplied_sha


def validate_case_universe(acquisition: dict[str, Any], evidence_v7: dict[str, Any]) -> None:
    acquisition_rows = acquisition.get('cases')
    evidence_rows = evidence_v7.get('cases')
    if not isinstance(acquisition_rows, list) or len(acquisition_rows) != EXPECTED_CASE_COUNT:
        raise ValueError('acquisition case universe drift')
    if not isinstance(evidence_rows, list) or len(evidence_rows) != EXPECTED_CASE_COUNT:
        raise ValueError('normalized v7 evidence case universe drift')
    expected = {row.get('caseId'): row for row in acquisition_rows}
    if None in expected or len(expected) != EXPECTED_CASE_COUNT:
        raise ValueError('acquisition case identity drift')
    if {row.get('caseId') for row in evidence_rows} != set(expected):
        raise ValueError('normalized v7 evidence case identity drift')
    for row in evidence_rows:
        case_id = row['caseId']
        source = expected[case_id]
        for key in ('geometryId', 'method', 'replicate', 'seed', 'photonHistories'):
            if row.get(key) != source.get(key):
                raise ValueError(f'normalized v7 evidence/acquisition case mismatch: {case_id}.{key}')
        if row.get('importanceCenterNm') != source.get('importanceCenterNm'):
            raise ValueError(f'normalized v7 evidence/acquisition case mismatch: {case_id}.importanceCenterNm')


def analyze_v7_compat(
    acquisition: dict[str, Any],
    analysis_protocol: dict[str, Any],
    admission: dict[str, Any],
    evidence_v7: dict[str, Any],
    v7_contract: dict[str, Any],
    v8_contract: dict[str, Any],
) -> dict[str, Any]:
    validate_case_universe(acquisition, evidence_v7)
    compatibility, original_v7_sha = build_v6_compatibility_view(evidence_v7, v7_contract, v8_contract)
    compatibility_sha = compatibility['evidenceSha256']
    frozen_v6_result = v6.analyze(acquisition, analysis_protocol, admission, compatibility)
    if frozen_v6_result.get('normalizedEvidenceSha256') != compatibility_sha:
        raise ValueError('frozen v6 analyzer compatibility binding drift')

    result = {
        'schemaVersion': 1,
        'analysisId': ANALYSIS_ID,
        'status': 'PILOT_SCREENING_ANALYZED_VIA_FROZEN_V6_COMPATIBILITY',
        'sourceScientificRunId': EXPECTED_SOURCE_RUN_ID,
        'sourceScientificRunAttempt': EXPECTED_SOURCE_RUN_ATTEMPT,
        'sourceScientificOrdinal': 16,
        'sourceScientificHeadSha': EXPECTED_SOURCE_HEAD_SHA,
        'sourceCaseCount': EXPECTED_CASE_COUNT,
        'normalizedEvidenceV7Sha256': original_v7_sha,
        'compatibilityEvidenceV6Sha256': compatibility_sha,
        'postprocessV7ContractSha256': v7_contract['contractSha256'],
        'postprocessAnalyzerV8ContractSha256': v8_contract['contractSha256'],
        'frozenV6AnalysisSha256': frozen_v6_result['analysisSha256'],
        'frozenV6AnalysisId': frozen_v6_result['analysisId'],
        'screeningStatus': frozen_v6_result['status'],
        'classificationCounts': frozen_v6_result['classificationCounts'],
        'scientificSolverReexecuted': False,
        'holdoutValuesRead': False,
        'modelFittingAuthorized': False,
        'modelSelectionAuthorized': False,
        'holdoutOpeningAuthorized': False,
        'tier2Authorized': False,
        'productionAuthorization': False,
        'screeningAnalysisV6': frozen_v6_result,
    }
    result['analysisSha256'] = v6.canon(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--acquisition-protocol', type=Path, required=True)
    parser.add_argument('--analysis-protocol', type=Path, required=True)
    parser.add_argument('--admission-report', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--postprocess-contract-v7', type=Path, default=DEFAULT_V7_CONTRACT)
    parser.add_argument('--compatibility-contract', type=Path, default=DEFAULT_V8_CONTRACT)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        validate_code_identity(args.postprocess_contract_v7)
        value = analyze_v7_compat(
            load(args.acquisition_protocol),
            load(args.analysis_protocol),
            load(args.admission_report),
            load(args.evidence),
            load(args.postprocess_contract_v7),
            load(args.compatibility_contract),
        )
        args.output.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')
        print(json.dumps({
            'status': value['status'],
            'analysisSha256': value['analysisSha256'],
            'normalizedEvidenceV7Sha256': value['normalizedEvidenceV7Sha256'],
            'compatibilityEvidenceV6Sha256': value['compatibilityEvidenceV6Sha256'],
            'classificationCounts': value['classificationCounts'],
            'scientificSolverReexecuted': False,
        }, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps({
            'status': 'REFUSED',
            'reason': str(exc),
            'scientificSolverReexecuted': False,
        }, indent=2, sort_keys=True))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
