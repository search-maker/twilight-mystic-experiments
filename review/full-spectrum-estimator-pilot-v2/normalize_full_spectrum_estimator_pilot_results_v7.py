#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
V6_PATH = ROOT / 'normalize_full_spectrum_estimator_pilot_results_v6.py'
CONTRACT_PATH = ROOT.parents[1] / 'experiments' / 'full-spectrum-estimator-pilot-v2' / 'postprocess-contract.ordinal16.v7.json'
EVIDENCE_ID = 'public-tier1-full-spectrum-estimator-pilot-normalized-evidence-v7'
OUTPUT_NODE_COUNT = 8001
OUTPUT_START_NM = 380.0
OUTPUT_STOP_NM = 780.0
OUTPUT_STEP_NM = 0.05
OUTPUT_GRID_POINT_TOLERANCE_NM = OUTPUT_STEP_NM / 1000.0
SOURCE_RUN_ID = 31546667072
SOURCE_HEAD_SHA = '183188bdbe5a899f5dcd1bc4e423fa385d26e3af'

spec = importlib.util.spec_from_file_location('full_spectrum_normalizer_v6', V6_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError('cannot load v6 normalizer')
v6 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v6)


def _canon(v: Any) -> bytes:
    return json.dumps(v, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def _self_hash(v: dict[str, Any], field: str) -> str:
    x = dict(v)
    x[field] = None
    return hashlib.sha256(_canon(x)).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f'expected object: {path}')
    return value


def validate_postprocess_contract(contract: dict[str, Any]) -> None:
    if contract.get('contractSha256') != _self_hash(contract, 'contractSha256'):
        raise ValueError('postprocess contract self-hash mismatch')
    exact = {
        'contractId': 'full-spectrum-estimator-pilot-v2-ordinal16-postprocess-v7',
        'status': 'POSTPROCESS_ONLY_REPLAY_PENDING_REVIEW',
        'sourceScientificRunId': SOURCE_RUN_ID,
        'sourceScientificRunAttempt': 1,
        'sourceScientificOrdinal': 16,
        'sourceScientificHeadSha': SOURCE_HEAD_SHA,
        'sourceScientificWorkflow': '.github/workflows/full-spectrum-estimator-pilot-v2-ordinal16-execution-v8.yml',
        'sourceAuthorizationPr': 125,
        'sourceCaseCount': 44,
        'sourceArtifactNamePrefix': 'full-spectrum-estimator-pilot-v2-case-',
        'frozenExecutionManifestPath': 'review/full-spectrum-estimator-pilot-v2/full-spectrum-estimator-pilot-execution-manifest-v4.json',
        'frozenAnalyzerPath': 'review/full-spectrum-estimator-pilot-v2/analyze_full_spectrum_estimator_pilot_v6.py',
        'normalizerPath': 'review/full-spectrum-estimator-pilot-v2/normalize_full_spectrum_estimator_pilot_results_v7.py',
        'solverExecutionAuthorized': False,
        'syntaxCheckAuthorized': False,
        'githubRerunOfScientificRunAllowed': False,
        'newScientificOrdinalAuthorized': False,
        'modelFittingAuthorized': False,
        'modelSelectionAuthorized': False,
        'holdoutValidationOpeningAuthorized': False,
        'tier2Authorized': False,
        'productionPromotionAuthorized': False,
    }
    for key, want in exact.items():
        if contract.get(key) != want:
            raise ValueError(f'postprocess contract drift: {key}')
    grid = contract.get('outputGridAdapter') or {}
    expected_grid = {
        'solarOutputNodeCount': OUTPUT_NODE_COUNT,
        'startNm': OUTPUT_START_NM,
        'stopNm': OUTPUT_STOP_NM,
        'nominalStepNm': OUTPUT_STEP_NM,
        'maxPointDeviationFractionOfStep': 0.001,
        'maxPointDeviationNm': OUTPUT_GRID_POINT_TOLERANCE_NM,
        'alisV6CallerNodeCount': 8001,
        'alisV6CallerStepNm': 0.05,
        'vroomCalculationGridNodeCount': 401,
        'vroomCalculationGridStepNm': 1.0,
        'vroomCalculationGridStillVerifiedByV6': True,
    }
    for key, want in expected_grid.items():
        if grid.get(key) != want:
            raise ValueError(f'postprocess output-grid contract drift: {key}')
    historical = contract.get('historicalV6Refusal') or {}
    if historical != {
        'aggregateJobId': 93975118074,
        'reason': 'output grid step mismatch',
        'all44CaseJobsSucceeded': True,
        'acquisitionBoundExactly44Artifacts': True,
    }:
        raise ValueError('historical v6 refusal binding drift')


def _caller_profile(node_count: int, step: float) -> str:
    if node_count == 8001 and abs(float(step) - 0.05) <= 1e-12:
        return 'alis-alt-importance'
    if node_count == 401 and abs(float(step) - 1.0) <= 1e-12:
        return 'reference-vroom-1nm-calculation-grid'
    raise ValueError(f'unsupported v6 output-grid caller contract: node_count={node_count} step={step}')


def parse_spectrum_v7(raw: bytes, node_count: int, step: float) -> tuple[list[float], list[float]]:
    _caller_profile(node_count, step)
    wavelengths: list[float] = []
    radiance: list[float] = []
    for line in raw.decode('utf-8').splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            wavelength = float(parts[0])
            value = float(parts[-1])
        except ValueError:
            continue
        if not math.isfinite(wavelength) or not math.isfinite(value) or value < 0:
            raise ValueError('spectrum contains invalid number')
        wavelengths.append(wavelength)
        radiance.append(value)

    if len(wavelengths) != OUTPUT_NODE_COUNT:
        raise ValueError(f'output grid mismatch: {len(wavelengths)}')
    if abs(wavelengths[0] - OUTPUT_START_NM) > OUTPUT_GRID_POINT_TOLERANCE_NM or abs(wavelengths[-1] - OUTPUT_STOP_NM) > OUTPUT_GRID_POINT_TOLERANCE_NM:
        raise ValueError('output grid endpoint mismatch')
    for index, wavelength in enumerate(wavelengths):
        expected = OUTPUT_START_NM + index * OUTPUT_STEP_NM
        if abs(wavelength - expected) > OUTPUT_GRID_POINT_TOLERANCE_NM:
            raise ValueError(f'output grid point mismatch at index {index}: got {wavelength} expected {expected}')
        if index and not wavelengths[index - 1] < wavelength:
            raise ValueError(f'output grid not strictly increasing at index {index}')
    return wavelengths, radiance


def normalize_v7(execution_manifest: dict[str, Any], acquisition_manifest: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    validate_postprocess_contract(contract)
    original = v6.parse_spectrum
    v6.parse_spectrum = parse_spectrum_v7
    try:
        evidence = v6.normalize(execution_manifest, acquisition_manifest)
    finally:
        v6.parse_spectrum = original
    evidence['evidenceId'] = EVIDENCE_ID
    evidence['postprocessAdapter'] = {
        'contractId': contract['contractId'],
        'contractSha256': contract['contractSha256'],
        'sourceScientificRunId': SOURCE_RUN_ID,
        'sourceScientificRunAttempt': 1,
        'sourceScientificHeadSha': SOURCE_HEAD_SHA,
        'historicalNormalizerVersion': 6,
        'historicalNormalizerStatus': 'REFUSED',
        'historicalNormalizerReason': 'output grid step mismatch',
        'normalizerVersion': 7,
        'outputGridSource': 'extraterrestrial solar spectrum serialization',
        'outputNodeCount': OUTPUT_NODE_COUNT,
        'outputNominalStepNm': OUTPUT_STEP_NM,
        'outputPointToleranceNm': OUTPUT_GRID_POINT_TOLERANCE_NM,
        'vroomCalculationGridStillVerifiedByV6': True,
        'scientificSolverReexecuted': False,
        'holdoutValuesRead': False,
    }
    evidence.pop('evidenceSha256', None)
    evidence['evidenceSha256'] = v6.canon(evidence)
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--execution-manifest', type=Path, required=True)
    parser.add_argument('--acquisition-manifest', type=Path, required=True)
    parser.add_argument('--postprocess-contract', type=Path, default=CONTRACT_PATH)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        value = normalize_v7(_load(args.execution_manifest), _load(args.acquisition_manifest), _load(args.postprocess_contract))
        args.output.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')
        print(json.dumps({'status': value['status'], 'caseCount': value['caseCount'], 'evidenceSha256': value['evidenceSha256'], 'normalizerVersion': 7, 'scientificSolverReexecuted': False}, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps({'status': 'REFUSED', 'reason': str(exc), 'normalizerVersion': 7, 'scientificSolverReexecuted': False}, indent=2, sort_keys=True))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
