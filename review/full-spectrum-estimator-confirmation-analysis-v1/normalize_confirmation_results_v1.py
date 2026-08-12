#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import zipfile
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO_REVIEW = HERE.parent
PILOT_DIR = REPO_REVIEW / 'full-spectrum-estimator-pilot-v2'
DEFAULT_CONTRACT = HERE / 'analysis-contract.v1.json'
PILOT_V6 = PILOT_DIR / 'normalize_full_spectrum_estimator_pilot_results_v6.py'
PILOT_V7 = PILOT_DIR / 'normalize_full_spectrum_estimator_pilot_results_v7.py'

CONTRACT_ID = 'public-tier1-full-spectrum-estimator-confirmation-analysis-v1'
CONTRACT_SHA = '08f30045f6f595e5e11cca5401aa4e1ea88862651ed5d7439671a538bc532cc7'
MANIFEST_ID = 'public-tier1-full-spectrum-estimator-confirmation-execution-manifest-v1'
MANIFEST_SHA = '9344ed18cfa93849d730cf080fe9f6c4c57f0cc5ea7b1be7ba9aa15d501c3fa8'
ACQUISITION_ID = 'public-tier1-full-spectrum-estimator-confirmation-acquisition-manifest-v1'
EVIDENCE_ID = 'public-tier1-full-spectrum-estimator-confirmation-normalized-evidence-v1'
EXPECTED_V6_BLOB = '8fb7c9eae30e7f2b28fdf67291f682ae2770ea9c'
EXPECTED_V7_BLOB = 'fe45136d595e6039b355d68cd2a926259af0ac40'
PRIMARY_CHANNELS = (
    'photopicLuminanceCdM2',
    'scotopicLuminanceScotCdM2',
    'johnsonVEffectiveRadiance_mW_m2_nm_sr',
)

class NormalizationRefusal(RuntimeError):
    pass

def require(condition: bool, message: str) -> None:
    if not condition:
        raise NormalizationRefusal(message)

def canon(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()

def raw_sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def git_blob_sha1(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(f'blob {len(raw)}\0'.encode() + raw).hexdigest()

def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    require(isinstance(value, dict), f'expected JSON object: {path}')
    return value

def self_hash(value: dict[str, Any], field: str) -> str:
    copy = dict(value)
    copy[field] = None
    return canon(copy)

def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f'cannot load module: {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def validate_contract(contract: dict[str, Any]) -> None:
    require(contract.get('contractId') == CONTRACT_ID, 'analysis contract id drift')
    require(contract.get('contractSha256') == CONTRACT_SHA, 'analysis contract exact identity drift')
    require(contract.get('contractSha256') == self_hash(contract, 'contractSha256'), 'analysis contract self-hash mismatch')
    require(contract.get('status') == 'REVIEW_ONLY_FROZEN_BEFORE_ANY_CONFIRMATION_RESULT', 'analysis contract status drift')
    manifest = contract.get('confirmationExecutionManifest') or {}
    require(manifest.get('manifestId') == MANIFEST_ID and manifest.get('manifestSha256') == MANIFEST_SHA, 'confirmation manifest binding drift')
    norm = contract.get('normalization') or {}
    require(norm.get('evidenceId') == EVIDENCE_ID and norm.get('caseCount') == 24, 'normalization contract identity drift')
    grid = norm.get('outputGrid') or {}
    require(grid == {'nodeCount': 8001, 'startNm': 380.0, 'stopNm': 780.0, 'nominalStepNm': 0.05, 'maxPointDeviationNm': 0.00005}, 'output-grid contract drift')
    require(norm.get('exactZeroPreserved') is True and norm.get('epsilonSubstitutionAllowed') is False and norm.get('holdoutValuesRead') is False, 'normalization boundary drift')
    boundary = contract.get('downstreamBoundary') or {}
    for key in ('scientificExecutionAuthorized','authorizationOrdinalAllocated','dispatchAuthorized','githubRerunAllowed','retryAllowed','resumeAllowed','modelFittingAuthorized','modelSelectionAuthorized','holdoutValidationOpeningAuthorized','tier2Authorized','productionPromotionAuthorized'):
        require(boundary.get(key) is False, f'downstream boundary drift: {key}')

def validate_code_identity(v6_path: Path = PILOT_V6, v7_path: Path = PILOT_V7) -> None:
    require(git_blob_sha1(v6_path) == EXPECTED_V6_BLOB, 'pilot v6 normalizer byte identity drift')
    require(git_blob_sha1(v7_path) == EXPECTED_V7_BLOB, 'pilot v7 normalizer byte identity drift')

def validate_manifest(manifest: dict[str, Any]) -> None:
    require(manifest.get('manifestId') == MANIFEST_ID, 'confirmation execution manifest id drift')
    supplied = manifest.get('manifestSha256')
    require(supplied == MANIFEST_SHA, 'confirmation execution manifest exact identity drift')
    require(supplied == canon({k: v for k, v in manifest.items() if k != 'manifestSha256'}), 'confirmation execution manifest self-hash mismatch')
    cases = manifest.get('cases')
    require(manifest.get('caseCount') == 24 and isinstance(cases, list) and len(cases) == 24, 'confirmation manifest case universe drift')
    require(len({c.get('caseId') for c in cases}) == 24 and len({c.get('seed') for c in cases}) == 24, 'confirmation manifest case/seed uniqueness drift')
    require(all(c.get('method') == 'alis-alt-importance' for c in cases), 'confirmation manifest contains non-ALIS case')

def validate_acquisition(acq: dict[str, Any], manifest: dict[str, Any]) -> None:
    require(acq.get('acquisitionId') == ACQUISITION_ID, 'confirmation acquisition id drift')
    supplied = acq.get('acquisitionSha256')
    require(isinstance(supplied, str) and supplied == self_hash(acq, 'acquisitionSha256'), 'confirmation acquisition self-hash mismatch')
    require(acq.get('executionManifestSha256') == MANIFEST_SHA, 'confirmation acquisition manifest binding drift')
    require(acq.get('sourceRunAttempt') == 1, 'confirmation acquisition must bind attempt 1')
    require(isinstance(acq.get('sourceRunId'), int) and acq['sourceRunId'] > 0, 'confirmation source run id missing')
    require(isinstance(acq.get('sourceOrdinal'), int) and acq['sourceOrdinal'] >= 17, 'confirmation source ordinal invalid')
    rows = acq.get('cases')
    require(acq.get('caseCount') == 24 and isinstance(rows, list) and len(rows) == 24, 'confirmation acquisition case count drift')
    expected = {c['caseId']: c for c in manifest['cases']}
    require({r.get('caseId') for r in rows} == set(expected), 'confirmation acquisition case universe drift')
    prefix = manifest['artifactContract']['artifactNamePrefix']
    seen_ids: set[int] = set()
    for row in rows:
        cid = row['caseId']
        require(row.get('artifactName') == prefix + cid, f'confirmation artifact name drift: {cid}')
        aid = row.get('artifactId')
        require(isinstance(aid, int) and aid > 0 and aid not in seen_ids, f'confirmation artifact id drift: {cid}')
        seen_ids.add(aid)
        zsha = row.get('zipSha256')
        require(isinstance(zsha, str) and len(zsha) == 64, f'confirmation ZIP hash missing: {cid}')
        require(row.get('githubDigest') == 'sha256:' + zsha, f'GitHub/ZIP digest mismatch: {cid}')

def _zip_member_map(zf: zipfile.ZipFile) -> dict[str, str]:
    out: dict[str, str] = {}
    for name in zf.namelist():
        if name.endswith('/'):
            continue
        base = Path(name).name
        require(base not in out, f'duplicate artifact member basename: {base}')
        out[base] = name
    return out

def normalize_case_zip(path: Path, expected: dict[str, Any], required_members: list[str], *, v6_module=None, v7_module=None) -> dict[str, Any]:
    v6 = v6_module or load_module('confirmation_norm_pilot_v6', PILOT_V6)
    v7 = v7_module or load_module('confirmation_norm_pilot_v7', PILOT_V7)
    zbytes = path.read_bytes()
    with zipfile.ZipFile(path) as zf:
        by_base = _zip_member_map(zf)
        require(set(by_base) == set(required_members) and len(by_base) == len(required_members), f'exact artifact member set mismatch: {expected["caseId"]}')
        raw = {base: zf.read(name) for base, name in by_base.items()}

    result = json.loads(raw['case-result.json'])
    prepared = json.loads(raw['prepared.json'])
    runtime = json.loads(raw['runtime-report.json'])
    cid = expected['caseId']
    require(result.get('schemaVersion') == 1 and result.get('stageId') == 'full-spectrum-estimator-confirmation-v1' and result.get('status') == 'COMPLETED' and result.get('caseId') == cid, f'case-result identity/status mismatch: {cid}')
    for key, want in {
        'candidateId': expected['candidateId'], 'confirmationBlock': expected['confirmationBlock'], 'workflowRunAttempt': 1,
        'syntaxCheckCount': 1, 'solverExecutionCount': 1, 'retryPerformed': False, 'resumePerformed': False,
        'githubRerun': False, 'syntaxExitCode': 0, 'solverExitCode': 0, 'syntaxTimedOut': False,
        'solverTimedOut': False, 'seed': expected['seed'], 'photonHistories': expected['photonHistories'],
    }.items():
        require(result.get(key) == want, f'case-result execution/identity drift: {cid}.{key}')
    content_sha = result.get('contentSha256')
    require(content_sha == canon({k: v for k, v in result.items() if k != 'contentSha256'}), f'case-result self-hash mismatch: {cid}')

    require(prepared.get('stageId') == 'full-spectrum-estimator-confirmation-v1-prepared' and prepared.get('caseId') == cid, f'prepared identity drift: {cid}')
    for key, want in [('candidateId', expected['candidateId']), ('geometryId', expected['geometryId']), ('method', expected['method']), ('confirmationBlock', expected['confirmationBlock']), ('seed', expected['seed']), ('photonHistories', expected['photonHistories']), ('executionManifestSha256', MANIFEST_SHA)]:
        require(prepared.get(key) == want, f'prepared binding drift: {cid}.{key}')

    v6.verify_runtime(runtime)
    input_raw = raw['input-resolved.txt']
    require(raw_sha(input_raw) == result.get('inputResolvedSha256') == prepared.get('inputResolvedSha256'), f'input hash drift: {cid}')
    require(raw_sha(raw['runtime-report.json']) == result.get('runtimeReportRawSha256'), f'runtime report hash drift: {cid}')
    require(raw_sha(raw['mc.rad.spc']) == result.get('radianceOutputSha256'), f'radiance hash drift: {cid}')
    require(raw_sha(raw['mc.rad.std.spc']) == result.get('stdRadianceOutputSha256'), f'std-radiance hash drift: {cid}')
    raw_hashes = result.get('rawMemberSha256ByBasename')
    require(isinstance(raw_hashes, dict), f'raw member hash map missing: {cid}')
    for name in required_members:
        if name == 'case-result.json':
            continue
        require(raw_hashes.get(name) == raw_sha(raw[name]), f'raw member hash drift: {cid}.{name}')

    directives = v6.parse_directives(input_raw)
    v6.verify_exact_directive_surface(input_raw, expected)
    v6.verify_input(directives, expected)
    expected_fp = v6.PHYSICAL_FINGERPRINTS.get(expected['geometryId'])
    require(expected_fp is not None and v6.physical_fingerprint(input_raw) == expected_fp, f'physical fingerprint drift: {cid}')

    wl, rad = v7.parse_spectrum_v7(raw['mc.rad.spc'], 8001, 0.05)
    swl, srad = v7.parse_spectrum_v7(raw['mc.rad.std.spc'], 8001, 0.05)
    require(swl == wl, f'std spectrum grid differs: {cid}')
    require(all(math.isfinite(x) and x >= 0 for x in srad), f'invalid std spectrum values: {cid}')
    channels = v6.channels(wl, rad)
    require(set(channels) == set(PRIMARY_CHANNELS), f'primary channel surface drift: {cid}')
    for name, value in channels.items():
        require(math.isfinite(value) and value >= 0, f'invalid normalized channel: {cid}.{name}')
    zero_by_channel = {name: value == 0.0 for name, value in channels.items()}
    return {
        'caseId': cid, 'candidateId': expected['candidateId'], 'geometryId': expected['geometryId'], 'method': expected['method'],
        'importanceCenterNm': expected['numericalMethod']['mc_spectral_is_nm'], 'confirmationBlock': expected['confirmationBlock'],
        'seed': expected['seed'], 'photonHistories': expected['photonHistories'], 'channels': channels,
        'zeroHitByChannel': zero_by_channel, 'anyPrimaryChannelZeroHit': any(zero_by_channel.values()),
        'zipSha256': raw_sha(zbytes), 'caseResultSha256': raw_sha(raw['case-result.json']),
        'inputResolvedSha256': raw_sha(input_raw), 'runtimeReportSha256': raw_sha(raw['runtime-report.json']),
        'radianceSha256': raw_sha(raw['mc.rad.spc']), 'stdRadianceSha256': raw_sha(raw['mc.rad.std.spc']),
    }

def normalize(manifest: dict[str, Any], acquisition: dict[str, Any], zip_dir: Path, contract: dict[str, Any], *, v6_module=None, v7_module=None) -> dict[str, Any]:
    validate_contract(contract)
    validate_manifest(manifest)
    validate_acquisition(acquisition, manifest)
    acq_rows = {r['caseId']: r for r in acquisition['cases']}
    required = manifest['artifactContract']['requiredMembersByMethod']['alis-alt-importance']
    rows = []
    for case in manifest['cases']:
        cid = case['caseId']
        arow = acq_rows[cid]
        path = zip_dir / (arow['artifactName'] + '.zip')
        require(path.is_file(), f'confirmation ZIP missing: {cid}')
        actual_sha = raw_sha(path.read_bytes())
        require(actual_sha == arow['zipSha256'], f'confirmation downloaded ZIP hash drift: {cid}')
        row = normalize_case_zip(path, case, required, v6_module=v6_module, v7_module=v7_module)
        require(row['zipSha256'] == arow['zipSha256'], f'confirmation ZIP binding drift after parse: {cid}')
        row['artifactId'] = arow['artifactId']; row['artifactName'] = arow['artifactName']; row['githubDigest'] = arow['githubDigest']
        rows.append(row)
    evidence = {
        'schemaVersion': 1, 'evidenceId': EVIDENCE_ID, 'evidenceSha256': None, 'status': 'CONFIRMATION_EVIDENCE_NORMALIZED',
        'analysisContractSha256': CONTRACT_SHA, 'executionManifestSha256': MANIFEST_SHA,
        'acquisitionManifestSha256': acquisition['acquisitionSha256'], 'sourceRunId': acquisition['sourceRunId'],
        'sourceRunAttempt': 1, 'sourceOrdinal': acquisition['sourceOrdinal'], 'caseCount': 24, 'cases': rows,
        'primaryChannels': list(PRIMARY_CHANNELS),
        'outputGridAdapter': {'nodeCount': 8001, 'startNm': 380.0, 'stopNm': 780.0, 'nominalStepNm': 0.05, 'maxPointDeviationNm': 0.00005},
        'exactZeroPreserved': True, 'epsilonSubstitutionPerformed': False,
        'scientificSolverReexecutedDuringNormalization': False, 'holdoutValuesRead': False,
    }
    evidence['evidenceSha256'] = self_hash(evidence, 'evidenceSha256')
    return evidence

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--execution-manifest', type=Path, required=True)
    parser.add_argument('--acquisition-manifest', type=Path, required=True)
    parser.add_argument('--zip-dir', type=Path, required=True)
    parser.add_argument('--analysis-contract', type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        validate_code_identity()
        value = normalize(load(args.execution_manifest), load(args.acquisition_manifest), args.zip_dir, load(args.analysis_contract))
        args.output.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')
        print(json.dumps({'status': value['status'], 'caseCount': value['caseCount'], 'evidenceSha256': value['evidenceSha256'], 'scientificSolverReexecutedDuringNormalization': False}, sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps({'status': 'REFUSED', 'reason': str(exc), 'scientificSolverReexecutedDuringNormalization': False}, sort_keys=True))
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
