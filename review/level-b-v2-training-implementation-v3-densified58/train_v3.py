#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import io
import json
import math
import os
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
REPO = 'search-maker/twilight-mystic-experiments'
G2_TRAIN = ROOT / 'review/level-b-v2-training-implementation-v2/train_v2.py'
G2_PROTOCOL = ROOT / 'review/level-b-v2-training-prefit-freeze-v2/protocol-v2.json'
PREFIT_V3 = ROOT / 'review/level-b-v2-training-prefit-freeze-v3-densified58/protocol-v3.json'
PREREG = ROOT / 'review/mystic-state-0069-local-training-densification-v1/protocol-v1.json'
EXEC_BINDING = ROOT / 'review/mystic-state-0069-ordinal23-result-v1/result-v1.json'

LEGACY_ARTIFACT_ID = 9208203541
LEGACY_ARTIFACT_DIGEST = '2fe50ed674155f440322c92d28877f5c022f0cc5fa13e1e601596a9902482815'
LEGACY_DATASET_MEMBER = 'training-representation-dataset-v2.json'
LEGACY_DATASET_FILE_SHA256 = '066d6be846fa9b3bdd7236e327894f64d52ea56aa7e7b6e6af4d51d849eb1a61'
LEGACY_DATASET_CANONICAL_SHA256 = 'bb7908426d9d545f43c082aebbaab1829a486e2962d0b9ee34a5e8bef5390133'
REPRESENTATION_MEMBER = 'spectral-representation-v2.npz'
REPRESENTATION_PACKAGE_SHA256 = '2491ac91ed924f2ba69b37ea20f48d63f51d41146cd9fe50e0bd63bfb315a763'
ORDINAL23_RUN_ID = 31814698818
ORDINAL23_HEAD_SHA = '5eead3cd62ce08a016dcc1b4126d66b4f7dfdbf0'
INVENTORY_ARTIFACT_ID = 9224754905
INVENTORY_ARTIFACT_DIGEST = '83d70c4f55e7b12d7db6d9922b4113657137a38d1167de63587afbf0c1378a23'
INVENTORY_MEMBER = 'execution-inventory-v1.json'
INVENTORY_SELF_SHA256 = 'ae2356b618679cd33cefd3115ca23cd8eff6091be5f936fc93f0fcf609a99455'
ORDINAL23_MANIFEST_SHA256 = 'eb1817b25a59af305076f0afa24d5f6ba6f4571fb4748ed638071edc4557f2ea'
GRID_SHA256 = 'b5fae53c1cc88c7f3de6e3689bc25e4a36c54033d1d1bfd6169482f30cc5b477'
FEATURES = ('sunDepressionDeg', 'targetAltitudeDeg', 'relativeAzimuthDeg', 'observerElevationM', 'aod550')
CHANNELS = ('photopicLuminanceCdM2', 'scotopicLuminanceScotCdM2', 'johnsonVEffectiveRadiance_mW_m2_nm_sr')


class Refusal(RuntimeError):
    pass


def req(condition: bool, message: str) -> None:
    if not condition:
        raise Refusal(message)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding='utf-8'))
    req(isinstance(value, dict), f'object required: {path}')
    return value


def canonical_sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n', encoding='utf-8')


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    req(spec is not None and spec.loader is not None, f'cannot load module: {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


v2 = load_module('level_b_v2_generation2_engine', G2_TRAIN)


def effective_protocol(p3: dict[str, Any]) -> dict[str, Any]:
    g2 = load_json(G2_PROTOCOL)
    req(p3.get('protocolId') == 'level-b-v2-training-only-prefit-freeze-v3-densified58', 'v3 protocol identity drift')
    req(p3.get('protocolSha256') == 'eaf8d1d047fa5a336027a18b3cddd015943f4a28fd58c568fac233f819baaf73', 'v3 protocol hash drift')
    req(p3['modelSelection']['candidateCountRequired'] == g2['modelSelection']['candidateCountRequired'] == 230, 'candidate count drift')
    out = copy.deepcopy(g2)
    out['protocolId'] = p3['protocolId']
    out['modelSelection']['crossValidationFolds'] = copy.deepcopy(p3['modelSelection']['crossValidationFolds'])
    out['modelSelection']['selectionData'] = p3['modelSelection']['selectionData']
    out['modelSelection']['noEligibleCandidateOutcome'] = p3['modelSelection']['noEligibleCandidateOutcome']
    out['roleIsolation']['exactTrainingGeometryIds'] = list(p3['roleIsolation']['exactExpandedTrainingGeometryIds'])
    out['roleIsolation']['openedV1ProtectedDiagnosticOnlyGeometryIds'] = list(p3['roleIsolation']['openedOrdinal22DiagnosticOnlyGeometryIds'])
    out['roleIsolation']['openedV1ProtectedValuesAllowed'] = False
    return out


def folds58(recs: list[dict[str, Any]], p: dict[str, Any], enforce_counts: bool = True) -> list[dict[str, Any]]:
    req(len(recs) == 58, '58 records required for densified folds')
    order = sorted(range(len(recs)), key=lambda i: str(recs[i]['geometryId']))
    out: list[dict[str, Any]] = []
    for k in range(5):
        val = [idx for pos, idx in enumerate(order) if pos % 5 == k]
        vs = set(val)
        out.append({'name': f'balanced-{k}', 'kind': 'balanced', 'fit': [i for i in range(len(recs)) if i not in vs], 'val': val})
    for name, pred in v2.boundary_predicates():
        val = [i for i, record in enumerate(recs) if pred(record['geometry'])]
        vs = set(val)
        out.append({'name': name, 'kind': 'boundary', 'fit': [i for i in range(len(recs)) if i not in vs], 'val': val})
    for i in order:
        out.append({'name': f'loo-{recs[i]["geometryId"]}', 'kind': 'loo', 'fit': [j for j in range(len(recs)) if j != i], 'val': [i]})
    cv = p['modelSelection']['crossValidationFolds']
    req(len(out) == 73, 'fold count drift')
    req([len(x['val']) for x in out[:5]] == cv['expectedBalancedFoldCounts'], 'balanced counts drift')
    if enforce_counts:
        req({x['name']: len(x['val']) for x in out[5:15]} == cv['expectedBoundaryFoldCounts'], 'boundary counts drift')
    return out


def evaluate_candidate58(recs: list[dict[str, Any]], spec: dict[str, Any], p: dict[str, Any], scales: np.ndarray, enforce_counts: bool = True) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    loo_primary: list[float] = []
    loo_single: list[float] = []
    loo_raw: list[float] = []
    loo_ua: list[float] = []
    loo_uasing: list[float] = []
    loo_base: list[float] = []
    for fold in folds58(recs, p, enforce_counts):
        fit = [recs[i] for i in fold['fit']]
        model = v2.fit_candidate(fit, spec, scales)
        base = np.mean(np.vstack([v2.targets_and_shape_se(r, scales)[0] for r in fit]), axis=0)
        primary: list[float] = []
        single: list[float] = []
        raw: list[float] = []
        ua: list[float] = []
        uasing: list[float] = []
        basep: list[float] = []
        for i in fold['val']:
            truth, uncertainty = v2.targets_and_shape_se(recs[i], scales)
            pred = v2.predict(model, recs[i]['geometry'])
            pe = np.abs(pred[:3] - truth[:3])
            se = pred[3:] - truth[3:]
            denom = np.sqrt(1.0 + uncertainty * uncertainty)
            primary.append(float(np.mean(pe)))
            single.append(float(np.max(pe)))
            raw.append(float(np.sqrt(np.mean(se * se))))
            ua.append(float(np.sqrt(np.mean((se / denom) ** 2)))
            uasing.append(float(np.max(np.abs(se) / denom)))
            basep.append(float(np.mean(np.abs(base[:3] - truth[:3]))))
        row = {
            'fold': fold['name'],
            'kind': fold['kind'],
            'count': len(fold['val']),
            'primaryMale': float(np.mean(primary)),
            'worstSinglePrimaryLogError': max(single),
            'rawShapeNrmse': float(np.mean(raw)),
            'uncertaintyAdjustedShapeNrmse': float(np.mean(ua)),
            'worstUncertaintyAdjustedSingleCoefficientError': max(uasing),
        }
        rows.append(row)
        if fold['kind'] == 'loo':
            loo_primary += primary
            loo_single += single
            loo_raw += raw
            loo_ua += ua
            loo_uasing += uasing
            loo_base += basep
    req(len(loo_primary) == 58, 'LOO count drift')
    boundary = [x for x in rows if x['kind'] == 'boundary']
    baseline = float(np.mean(loo_base))
    mean_primary = float(np.mean(loo_primary))
    mean_raw = float(np.mean(loo_raw))
    improvement = 1.0 - mean_primary / baseline
    values = {
        'looMeanPrimaryMale': mean_primary,
        'looWorstSinglePrimaryLogError': max(loo_single),
        'looMeanRawShapeNrmse': mean_raw,
        'looWorstRawShapeNrmseReportOnly': max(loo_raw),
        'looWorstUncertaintyAdjustedShapeNrmse': max(loo_ua),
        'looWorstUncertaintyAdjustedSingleCoefficientError': max(loo_uasing),
        'boundaryWorstPrimaryMale': max(x['primaryMale'] for x in boundary),
        'boundaryWorstRawShapeNrmse': max(x['rawShapeNrmse'] for x in boundary),
        'looFoldMatchedTrainingMeanBaselinePrimaryMale': baseline,
        'looPrimaryImprovementVsBaselineFraction': improvement,
    }
    gates = p['modelSelection']['trainingOnlyReadinessGates']
    checks = {
        'looMeanPrimary': values['looMeanPrimaryMale'] <= gates['looMeanPrimaryMaleMax'],
        'looWorstSinglePrimary': values['looWorstSinglePrimaryLogError'] <= gates['looWorstSinglePrimaryLogErrorMax'],
        'looMeanRawShape': values['looMeanRawShapeNrmse'] <= gates['looMeanRawShapeNrmseMax'],
        'looWorstUncertaintyAdjustedShape': values['looWorstUncertaintyAdjustedShapeNrmse'] <= gates['looWorstUncertaintyAdjustedShapeNrmseMax'],
        'looWorstUncertaintyAdjustedSingleCoefficient': values['looWorstUncertaintyAdjustedSingleCoefficientError'] <= gates['looWorstUncertaintyAdjustedSingleCoefficientErrorMax'],
        'boundaryWorstPrimary': values['boundaryWorstPrimaryMale'] <= gates['boundaryWorstPrimaryMaleMax'],
        'boundaryWorstRawShape': values['boundaryWorstRawShapeNrmse'] <= gates['boundaryWorstRawShapeNrmseMax'],
        'looPrimaryBaselineImprovement': values['looPrimaryImprovementVsBaselineFraction'] >= gates['looPrimaryMustBeatFoldMatchedTrainingMeanBaselineByFraction'],
    }
    score = max(
        values['looMeanPrimaryMale'] / 0.25,
        values['looWorstSinglePrimaryLogError'] / 0.9,
        values['looMeanRawShapeNrmse'] / 1.0,
        values['looWorstUncertaintyAdjustedShapeNrmse'] / 1.45,
        values['looWorstUncertaintyAdjustedSingleCoefficientError'] / 3.0,
        values['boundaryWorstPrimaryMale'] / 0.30,
        values['boundaryWorstRawShapeNrmse'] / 1.45,
    ) + 0.10 * ((values['looMeanPrimaryMale'] / 0.25) + (values['looMeanRawShapeNrmse'] / 1.0))
    return {**spec, **values, 'eligible': all(checks.values()), 'gateChecks': checks, 'selectionScore': float(score), 'foldMetrics': rows}


def select58(recs: list[dict[str, Any]], p: dict[str, Any], enforce_counts: bool = True) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    scales = np.asarray(p['sourceTrainingRepresentation']['nullspaceCoefficientScales'], dtype=np.float64)
    results = [evaluate_candidate58(recs, spec, p, scales, enforce_counts) for spec in v2.candidate_specs(p)]
    eligible = sorted([x for x in results if x['eligible']], key=v2.ranking_key)
    return (eligible[0] if eligible else None), sorted(results, key=lambda x: (not x['eligible'], *v2.ranking_key(x)))


def stats2(values: list[float]) -> dict[str, Any]:
    req(len(values) == 2 and all(math.isfinite(x) for x in values), 'exactly two finite blocks required')
    a = np.asarray(values, dtype=np.float64)
    mean = float(np.mean(a))
    sample_std = float(np.std(a, ddof=1))
    standard_error = sample_std / math.sqrt(2.0)
    return {
        'mean': mean,
        'sampleStd': sample_std,
        'standardError': standard_error,
        'relativeStandardError': abs(standard_error / mean) if mean != 0.0 else None,
    }


def parse_spectrum_bytes(raw: bytes) -> tuple[np.ndarray, np.ndarray, str]:
    tokens: list[str] = []
    values: list[float] = []
    for line in raw.decode('utf-8', errors='strict').splitlines():
        parts = line.split()
        if not parts:
            continue
        req(len(parts) >= 2 and len(parts[0].split('.')) == 2 and len(parts[0].split('.')[1]) == 5, 'spectrum serialization drift')
        row = [float(x) for x in parts]
        req(all(math.isfinite(x) for x in row) and all(x >= 0.0 for x in row[1:]), 'invalid spectrum value')
        tokens.append(parts[0])
        values.append(row[-1])
    req(len(tokens) == 8001 and tokens[0] == '380.00000' and tokens[-1] == '780.00000', 'spectrum grid count/endpoints drift')
    token_sha = sha256_bytes(('\n'.join(tokens) + '\n').encode())
    req(token_sha == GRID_SHA256, 'spectrum token grid drift')
    wl = np.asarray([float(x) for x in tokens], dtype=np.float64)
    y = np.asarray(values, dtype=np.float64)
    req(np.all(np.diff(wl) > 0.0), 'spectrum order drift')
    return wl, y, sha256_bytes(raw)


def project_block(y: np.ndarray, W: np.ndarray, grand: np.ndarray, components: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    req(W.ndim == 2 and W.shape[0] == 3 and y.ndim == 1 and W.shape[1] == y.shape[0], 'projection dimension drift')
    req(grand.shape == y.shape and components.ndim == 2 and components.shape == (10, y.shape[0]), 'frozen representation dimension drift')
    channels = W @ y
    req(channels[0] > 0.0 and np.all(np.isfinite(channels)), 'nonpositive/nonfinite primary channel')
    normalized = y / channels[0]
    gram = W @ W.T
    projection = W.T @ np.linalg.solve(gram, W @ normalized)
    residual = normalized - projection
    req(float(np.max(np.abs(W @ residual))) < 1e-9, 'nullspace projection drift')
    coeff = (residual - grand) @ components.T
    req(coeff.shape == (10,) and np.all(np.isfinite(coeff)), 'PCA coefficient drift')
    return channels, coeff


def record_from_two_blocks(geometry_id: str, geometry: dict[str, Any], block_spectra: list[np.ndarray], W: np.ndarray, grand: np.ndarray, components: np.ndarray) -> dict[str, Any]:
    req(len(block_spectra) == 2, 'two ordinal23 blocks required')
    channels: list[np.ndarray] = []
    coeffs: list[np.ndarray] = []
    for y in block_spectra:
        ch, coeff = project_block(y, W, grand, components)
        channels.append(ch)
        coeffs.append(coeff)
    ca = np.vstack(channels)
    pa = np.vstack(coeffs)
    return {
        'geometryId': geometry_id,
        'geometry': {k: float(geometry[k]) for k in FEATURES},
        'blockCount': 2,
        'integratedChannels': {CHANNELS[j]: stats2(ca[:, j].tolist()) for j in range(3)},
        'nullspacePcaCoefficients': [stats2(pa[:, j].tolist()) for j in range(10)],
    }


def find_member(z: zipfile.ZipFile, basename: str) -> str:
    hits = [name for name in z.namelist() if Path(name).name == basename]
    req(len(hits) == 1, f'exactly one {basename} required in artifact')
    return hits[0]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req_obj, fp, code, msg, headers, newurl):
        return None


def api_json(url: str, token: str) -> dict[str, Any]:
    req(token, 'GITHUB_TOKEN required')
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
        'User-Agent': 'level-b-v2-densified58-v3',
    }
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as response:
        value = json.loads(response.read())
    req(isinstance(value, dict), 'GitHub API object required')
    return value


def download_artifact_zip(artifact_id: int, expected_digest: str, token: str) -> bytes:
    meta = api_json(f'https://api.github.com/repos/{REPO}/actions/artifacts/{artifact_id}', token)
    req(meta.get('expired') is False, f'artifact expired: {artifact_id}')
    actual_digest = str(meta.get('digest') or '')
    wanted = expected_digest if expected_digest.startswith('sha256:') else 'sha256:' + expected_digest
    req(actual_digest == wanted, f'artifact digest drift: {artifact_id}')
    headers = {'Authorization': f'Bearer {token}', 'User-Agent': 'level-b-v2-densified58-v3'}
    opener = urllib.request.build_opener(NoRedirect)
    request = urllib.request.Request(f'https://api.github.com/repos/{REPO}/actions/artifacts/{artifact_id}/zip', headers=headers)
    location: str | None = None
    try:
        response = opener.open(request, timeout=60)
    except urllib.error.HTTPError as error:
        req(error.code in (301, 302, 303, 307, 308) and error.headers.get('Location'), f'artifact redirect missing: {artifact_id}')
        location = error.headers['Location']
    else:
        with response:
            blob = response.read()
        req(sha256_bytes(blob) == wanted.split(':', 1)[1], f'artifact ZIP digest drift: {artifact_id}')
        return blob
    with urllib.request.urlopen(urllib.request.Request(location, headers={'User-Agent': 'level-b-v2-densified58-v3'}), timeout=120) as response:
        blob = response.read()
    req(sha256_bytes(blob) == wanted.split(':', 1)[1], f'artifact ZIP digest drift: {artifact_id}')
    return blob


def run_artifacts(token: str) -> list[dict[str, Any]]:
    data = api_json(f'https://api.github.com/repos/{REPO}/actions/runs/{ORDINAL23_RUN_ID}/artifacts?per_page=100', token)
    artifacts = data.get('artifacts') or []
    req(isinstance(artifacts, list) and len(artifacts) == 30, 'ordinal23 run artifact count drift')
    return artifacts


def load_legacy_representation(token: str, g2_protocol: dict[str, Any]) -> tuple[dict[str, Any], np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[dict[str, Any]]]:
    blob = download_artifact_zip(LEGACY_ARTIFACT_ID, LEGACY_ARTIFACT_DIGEST, token)
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        dataset_raw = z.read(find_member(z, LEGACY_DATASET_MEMBER))
        npz_raw = z.read(find_member(z, REPRESENTATION_MEMBER))
    req(sha256_bytes(dataset_raw) == LEGACY_DATASET_FILE_SHA256, 'legacy dataset file SHA drift')
    req(sha256_bytes(npz_raw) == REPRESENTATION_PACKAGE_SHA256, 'frozen representation package SHA drift')
    dataset = json.loads(dataset_raw)
    legacy_records = v2.validate_dataset(dataset, g2_protocol, dataset_raw)
    req(dataset.get('datasetSha256') == LEGACY_DATASET_CANONICAL_SHA256, 'legacy dataset canonical SHA drift')
    with np.load(io.BytesIO(npz_raw), allow_pickle=False) as package:
        wavelength = np.asarray(package['wavelength_nm'], dtype=np.float64)
        W = np.asarray(package['integration_weights'], dtype=np.float64)
        grand = np.asarray(package['grand_mean_nullspace_residual'], dtype=np.float64)
        components = np.asarray(package['selected_nullspace_pca_components'], dtype=np.float64)
        indices = np.asarray(package['resolved_pca_indices'], dtype=np.int64)
    req(wavelength.shape == (8001,) and W.shape == (3, 8001) and grand.shape == (8001,) and components.shape == (10, 8001) and indices.shape == (10,), 'frozen representation array shape drift')
    req(np.all(np.isfinite(W)) and np.all(np.isfinite(grand)) and np.all(np.isfinite(components)), 'nonfinite frozen representation array')
    source_cases = dataset.get('sourceCases') or []
    req(len(source_cases) == 138, 'legacy source case count drift')
    return dataset, wavelength, W, grand, components, source_cases


def load_inventory(token: str) -> dict[str, Any]:
    blob = download_artifact_zip(INVENTORY_ARTIFACT_ID, INVENTORY_ARTIFACT_DIGEST, token)
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        raw = z.read(find_member(z, INVENTORY_MEMBER))
    inventory = json.loads(raw)
    got = inventory.get('inventorySha256')
    body = dict(inventory)
    body.pop('inventorySha256', None)
    req(got == INVENTORY_SELF_SHA256 == canonical_sha(body), 'ordinal23 inventory self-hash drift')
    req((inventory.get('workflowRunId'), inventory.get('workflowRunAttempt'), inventory.get('headSha')) == (ORDINAL23_RUN_ID, 1, ORDINAL23_HEAD_SHA), 'ordinal23 inventory run identity drift')
    req((inventory.get('geometryCount'), inventory.get('caseCount'), inventory.get('configuredPhotonHistories')) == (14, 28, 560000000), 'ordinal23 inventory size drift')
    req(inventory.get('manifestSha256') == ORDINAL23_MANIFEST_SHA256, 'ordinal23 manifest binding drift')
    req(inventory.get('ordinal22ValuesRead') is False and inventory.get('protectedValidationOpened') is False and inventory.get('modelFitPerformed') is False, 'ordinal23 inventory boundary drift')
    return inventory


def derive_expanded_dataset(token: str, p3: dict[str, Any], effective: dict[str, Any]) -> dict[str, Any]:
    prereg = load_json(PREREG)
    execution = load_json(EXEC_BINDING)
    req(execution.get('status') == 'ORDINAL23_TRAINING_DENSIFICATION_EXECUTION_COMPLETE_NO_FITTING', 'ordinal23 execution binding status drift')
    req(execution['scientificBoundaries']['ordinal22ValuesRead'] is False and execution['scientificBoundaries']['modelFitPerformed'] is False, 'execution binding boundary drift')
    legacy, wavelength, W, grand, components, legacy_source_cases = load_legacy_representation(token, load_json(G2_PROTOCOL))
    inventory = load_inventory(token)
    inv_cases = inventory.get('cases') or []
    req(len(inv_cases) == 28, 'inventory case count drift')
    prereg_cases = prereg['execution']['cases']
    req({x['caseId'] for x in inv_cases} == {x['caseId'] for x in prereg_cases} and len({x['caseId'] for x in inv_cases}) == 28, 'inventory/prereg case universe drift')
    prereg_by_case = {x['caseId']: x for x in prereg_cases}
    geometry_by_id = {x['geometryId']: x['geometry'] for x in prereg['design']['geometries']}
    req(sorted(geometry_by_id) == list(p3['roleIsolation']['ordinal23NewTrainingGeometryIds']), 'preregistered geometry IDs drift')
    artifacts = run_artifacts(token)
    by_name = {str(a['name']): a for a in artifacts}
    req(len(by_name) == 30, 'duplicate run artifact name')
    expected_names = {f'm0069-ordinal23-case-{x["caseId"]}' for x in inv_cases}
    expected_names |= {f'm0069-ordinal23-inventory-{ORDINAL23_HEAD_SHA}', f'm0069-ordinal23-preflight-{ORDINAL23_HEAD_SHA}'}
    req(set(by_name) == expected_names, 'ordinal23 run artifact name universe drift')
    blocks: dict[str, list[tuple[int, np.ndarray]]] = {gid: [] for gid in geometry_by_id}
    new_source_cases: list[dict[str, Any]] = []
    for inv in inv_cases:
        case_id = inv['caseId']
        case = prereg_by_case[case_id]
        req((inv['geometryId'], inv['block'], inv['seed']) == (case['geometryId'], case['block'], case['seed']), f'inventory/prereg case drift: {case_id}')
        name = f'm0069-ordinal23-case-{case_id}'
        meta = by_name[name]
        req(meta.get('expired') is False, f'case artifact expired: {case_id}')
        workflow_run = meta.get('workflow_run') or {}
        req((workflow_run.get('id'), workflow_run.get('head_sha')) == (ORDINAL23_RUN_ID, ORDINAL23_HEAD_SHA), f'case artifact run drift: {case_id}')
        digest = str(meta.get('digest') or '')
        req(digest.startswith('sha256:'), f'case artifact digest missing: {case_id}')
        blob = download_artifact_zip(int(meta['id']), digest, token)
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            rad_raw = z.read(find_member(z, 'mc.rad.spc'))
            std_raw = z.read(find_member(z, 'mc.rad.std.spc'))
            result_raw = z.read(find_member(z, 'case-result.json'))
            prepared_raw = z.read(find_member(z, 'prepared.json'))
        req(sha256_bytes(rad_raw) == inv['radianceSha256'], f'radiance hash drift: {case_id}')
        req(sha256_bytes(std_raw) == inv['stdRadianceSha256'], f'std radiance hash drift: {case_id}')
        wl, radiance, _ = parse_spectrum_bytes(rad_raw)
        swl, _, _ = parse_spectrum_bytes(std_raw)
        req(np.array_equal(wl, wavelength) and np.array_equal(swl, wavelength), f'wavelength identity drift: {case_id}')
        result = json.loads(result_raw)
        result_hash = result.get('contentSha256')
        result_body = dict(result)
        result_body.pop('contentSha256', None)
        req(result_hash == inv['caseResultSha256'] == canonical_sha(result_body), f'case-result hash drift: {case_id}')
        req(result.get('status') == 'COMPLETED' and result.get('role') == 'surrogate-training' and result.get('workflowRunAttempt') == 1, f'case completion drift: {case_id}')
        req(result.get('syntaxCheckCount') == 1 and result.get('solverExecutionCount') == 1 and result.get('retryPerformed') is False and result.get('resumePerformed') is False and result.get('githubRerun') is False, f'case one-use drift: {case_id}')
        req(result.get('protectedHoldoutValueExposed') is False and result.get('modelFittingSurfaceExposed') is False, f'case boundary drift: {case_id}')
        prepared = json.loads(prepared_raw)
        req((prepared.get('caseId'), prepared.get('geometryId'), prepared.get('block'), prepared.get('seed')) == (case_id, case['geometryId'], case['block'], case['seed']), f'prepared identity drift: {case_id}')
        req(prepared.get('role') == 'surrogate-training' and prepared.get('protectedHoldoutValueExposed') is False, f'prepared role drift: {case_id}')
        inputs = prepared.get('inputs') or {}
        geometry = geometry_by_id[case['geometryId']]
        for feature in FEATURES:
            req(float(inputs[feature]) == float(geometry[feature]), f'prepared geometry drift: {case_id} {feature}')
        blocks[case['geometryId']].append((int(case['block']), radiance))
        new_source_cases.append({
            'cohort': 'mystic-state-0069-ordinal23-training-densification',
            'geometryId': case['geometryId'],
            'block': int(case['block']),
            'caseId': case_id,
            'artifactId': int(meta['id']),
            'artifactDigest': digest,
            'sourceRunId': ORDINAL23_RUN_ID,
            'sourceRunAttempt': 1,
            'sourceHeadSha': ORDINAL23_HEAD_SHA,
            'radianceSha256': inv['radianceSha256'],
            'stdRadianceSha256': inv['stdRadianceSha256'],
            'caseResultSha256': inv['caseResultSha256'],
            'wavelengthTokenGridSha256': GRID_SHA256,
        })
    new_records: list[dict[str, Any]] = []
    for gid in sorted(blocks):
        rows = sorted(blocks[gid], key=lambda x: x[0])
        req([x[0] for x in rows] == [1, 2], f'ordinal23 block identity drift: {gid}')
        new_records.append(record_from_two_blocks(gid, geometry_by_id[gid], [x[1] for x in rows], W, grand, components))
    legacy_records = legacy['records']
    req([x['geometryId'] for x in legacy_records] == effective['roleIsolation']['exactTrainingGeometryIds'][:44], 'legacy record order drift')
    records = legacy_records + new_records
    expected_ids = p3['roleIsolation']['exactExpandedTrainingGeometryIds']
    req([x['geometryId'] for x in records] == expected_ids and len(records) == 58, 'expanded training record identity drift')
    req(not set(expected_ids) & set(p3['roleIsolation']['openedOrdinal22DiagnosticOnlyGeometryIds']), 'opened ordinal22 geometry entered training')
    for record in records:
        v2.targets_and_shape_se(record, np.asarray(effective['sourceTrainingRepresentation']['nullspaceCoefficientScales'], dtype=np.float64))
    source_cases = legacy_source_cases + sorted(new_source_cases, key=lambda x: (x['geometryId'], x['block'], x['caseId']))
    req(len(source_cases) == 166, 'expanded source case count drift')
    dataset = {
        'schemaVersion': 3,
        'stageId': 'level-b-v2-densified58-training-representation-v3',
        'status': 'FROZEN_58_GEOMETRY_TRAINING_REPRESENTATION_ORDINAL23_OPENED_FOR_TRAINING_ONLY_NO_ORDINAL22',
        'protocolId': p3['protocolId'],
        'geometryCount': 58,
        'sourceCaseArtifactCount': 166,
        'representationFeatureCount': 13,
        'mandatoryIntegratedChannelCount': 3,
        'nullspacePcaComponentCount': 10,
        'legacy44DatasetCanonicalSha256': LEGACY_DATASET_CANONICAL_SHA256,
        'frozenRepresentationPackageSha256': REPRESENTATION_PACKAGE_SHA256,
        'ordinal23InventorySha256': INVENTORY_SELF_SHA256,
        'ordinal23ManifestSha256': ORDINAL23_MANIFEST_SHA256,
        'ordinal23WorkflowRunId': ORDINAL23_RUN_ID,
        'records': records,
        'sourceCases': source_cases,
        'protectedHoldoutRecordCount': 0,
        'ordinal22ValuesRead': False,
        'ordinal23TrainingValuesRead': True,
        'representationBasisRefitPerformed': False,
        'integrationWeightRecomputationPerformed': False,
        'pcaRecomputationPerformed': False,
        'scientificSolverExecutionPerformedByThisStage': False,
    }
    dataset['datasetSha256'] = canonical_sha(dataset)
    return dataset


def synthetic_records(p: dict[str, Any]) -> list[dict[str, Any]]:
    scales = np.asarray(p['sourceTrainingRepresentation']['nullspaceCoefficientScales'], dtype=np.float64)
    recs: list[dict[str, Any]] = []
    suns = [2, 3, 4, 6, 8.5, 9, 10, 10.5]
    alts = [5, 10, 20, 30, 50, 65, 70, 80]
    azs = [0, 30, 60, 90, 150, 160, 180]
    elevs = [0, 250, 500, 1000, 2000, 2250, 2500]
    aods = [.05, .08, .10, .20, .35, .38, .40]
    for i in range(58):
        geometry = {
            'sunDepressionDeg': suns[i % 8],
            'targetAltitudeDeg': alts[(i * 3) % 8],
            'relativeAzimuthDeg': azs[(i * 5) % 7],
            'observerElevationM': elevs[(i * 2) % 7],
            'aod550': aods[(i * 4) % 7],
        }
        x = v2.basis(geometry, 'PHYSICAL_COMPACT_16_TERMS')
        y = np.zeros(13, dtype=np.float64)
        y[:3] = [.5 + .8 * x[1] - .2 * x[2] + .1 * x[3], 1 + .7 * x[1] - .15 * x[2] + .08 * x[3], -1.2 + .75 * x[1] - .18 * x[2] + .09 * x[3]]
        for j in range(10):
            y[3 + j] = (.15 / (j + 1)) * x[1] + (.08 / (j + 1)) * x[2] - (.04 / (j + 1)) * x[3]
        channels = {key: {'mean': float(math.exp(y[j])), 'standardError': float(math.exp(y[j]) * .02)} for j, key in enumerate(CHANNELS)}
        pcs = [{'mean': float(y[3 + j] * scales[j]), 'standardError': float((.05 + .02 * ((i + j) % 3)) * scales[j])} for j in range(10)]
        recs.append({'geometryId': f'synthetic-{i:04d}', 'geometry': geometry, 'integratedChannels': channels, 'nullspacePcaCoefficients': pcs})
    return recs


def execute(p3: dict[str, Any], output: Path) -> None:
    req(np.__version__ == '2.3.2', f'numpy version drift: {np.__version__}')
    token = os.environ.get('GITHUB_TOKEN', '')
    req(token, 'GITHUB_TOKEN required')
    effective = effective_protocol(p3)
    dataset = derive_expanded_dataset(token, p3, effective)
    records = dataset['records']
    best, ranking = select58(records, effective, enforce_counts=True)
    selection = {
        'schemaVersion': 3,
        'stageId': 'level-b-v2-training-selection-v3-densified58',
        'status': 'TRAINING_ONLY_DENSIFIED58_SELECTION_COMPLETE' if best else 'NO_DENSIFIED58_CANDIDATE_PASSES_TRAINING_ONLY_READINESS',
        'protocolId': p3['protocolId'],
        'protocolSha256': p3['protocolSha256'],
        'sourceExpandedDatasetSha256': dataset['datasetSha256'],
        'trainingGeometryCount': 58,
        'sourceCaseArtifactCount': 166,
        'candidateCount': len(ranking),
        'cvFoldCount': 73,
        'eligibleCandidateCount': sum(x['eligible'] for x in ranking),
        'selectedCandidate': None if best is None else {k: best[k] for k in best if k in ('familyId', 'kind', 'complexityRank', 'primaryBasis', 'shapeBasis', 'primaryRidge', 'shapeRidge', 'neighbors', 'power', 'selectionScore')},
        'candidates': ranking,
        'generation2ResultRemainsFailed': True,
        'ordinal22ValuesRead': False,
        'ordinal23TrainingValuesRead': True,
        'protectedValidationOpened': False,
    }
    selection['selectionSha256'] = canonical_sha(selection)
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / 'training-representation-dataset-v3-densified58.json', dataset)
    write_json(output / 'training-selection-v3-densified58.json', selection)
    if best is None:
        result = {
            'schemaVersion': 3,
            'stageId': 'level-b-v2-training-fit-result-v3-densified58',
            'status': 'TRAINING_ONLY_DENSIFIED58_NO_ELIGIBLE_CANDIDATE_NO_MODEL_FROZEN',
            'expandedDatasetSha256': dataset['datasetSha256'],
            'trainingSelectionSha256': selection['selectionSha256'],
            'modelArtifactWritten': False,
            'generation2ResultRemainsFailed': True,
            'ordinal22ValuesRead': False,
            'ordinal23TrainingValuesRead': True,
            'protectedValidationAuthorized': False,
            'freshProtectedValidationSourceRequired': True,
            'newMysticSolverExecutionAuthorized': False,
            'productionPromotionAuthorized': False,
            'workerBLaneReactivated': False,
            'workerCLaneReactivated': False,
        }
        result['resultSha256'] = canonical_sha(result)
        write_json(output / 'training-fit-result-v3-densified58.json', result)
        return
    scales = np.asarray(effective['sourceTrainingRepresentation']['nullspaceCoefficientScales'], dtype=np.float64)
    model = v2.fit_candidate(records, best, scales)
    artifact = {
        'schemaVersion': 3,
        'stageId': 'level-b-v2-model-artifact-v3-densified58',
        'status': 'TRAINING_ONLY_DENSIFIED58_MODEL_FROZEN_PENDING_FRESH_VALIDATION_SOURCE',
        'protocolId': p3['protocolId'],
        'protocolSha256': p3['protocolSha256'],
        'trainingGeometryCount': 58,
        'sourceExpandedDatasetSha256': dataset['datasetSha256'],
        'selectedSpec': {k: best[k] for k in best if k in ('familyId', 'kind', 'complexityRank', 'primaryBasis', 'shapeBasis', 'primaryRidge', 'shapeRidge', 'neighbors', 'power')},
        'model': model,
        'nullspaceCoefficientScales': scales.tolist(),
        'trainingSelectionSha256': selection['selectionSha256'],
        'generation2ResultRemainsFailed': True,
        'ordinal22ValuesRead': False,
        'ordinal23TrainingValuesRead': True,
        'protectedHoldoutRecordCount': 0,
        'protectedValidationAuthorized': False,
        'freshProtectedValidationSourceRequired': True,
        'productionPromotionAuthorized': False,
    }
    artifact['modelSha256'] = canonical_sha(artifact)
    write_json(output / 'model-artifact-v3-densified58.json', artifact)
    metrics = {k: best[k] for k in ('selectionScore', 'looMeanPrimaryMale', 'looWorstSinglePrimaryLogError', 'looMeanRawShapeNrmse', 'looWorstRawShapeNrmseReportOnly', 'looWorstUncertaintyAdjustedShapeNrmse', 'looWorstUncertaintyAdjustedSingleCoefficientError', 'boundaryWorstPrimaryMale', 'boundaryWorstRawShapeNrmse', 'looPrimaryImprovementVsBaselineFraction')}
    result = {
        'schemaVersion': 3,
        'stageId': 'level-b-v2-training-fit-result-v3-densified58',
        'status': 'TRAINING_ONLY_DENSIFIED58_MODEL_FROZEN_PENDING_FRESH_VALIDATION_SOURCE',
        'expandedDatasetSha256': dataset['datasetSha256'],
        'trainingSelectionSha256': selection['selectionSha256'],
        'modelArtifactWritten': True,
        'modelSha256': artifact['modelSha256'],
        'selectedSpec': artifact['selectedSpec'],
        'selectedTrainingMetrics': metrics,
        'generation2ResultRemainsFailed': True,
        'ordinal22ValuesRead': False,
        'ordinal23TrainingValuesRead': True,
        'protectedValidationAuthorized': False,
        'freshProtectedValidationSourceRequired': True,
        'newMysticSolverExecutionAuthorized': False,
        'productionPromotionAuthorized': False,
        'workerBLaneReactivated': False,
        'workerCLaneReactivated': False,
    }
    result['resultSha256'] = canonical_sha(result)
    write_json(output / 'training-fit-result-v3-densified58.json', result)


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd', required=True)
    synthetic = sub.add_parser('synthetic')
    synthetic.add_argument('--protocol', type=Path, required=True)
    real = sub.add_parser('execute')
    real.add_argument('--protocol', type=Path, required=True)
    real.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        p3 = load_json(args.protocol)
        effective = effective_protocol(p3)
        if args.cmd == 'synthetic':
            recs = synthetic_records(effective)
            best, ranking = select58(recs, effective, enforce_counts=False)
            req(len(ranking) == 230, 'synthetic candidate count drift')
            req(best is not None, 'synthetic no eligible candidate')
            print(json.dumps({'status': 'SYNTHETIC_PASS', 'trainingGeometryCount': 58, 'candidateCount': len(ranking), 'cvFoldCount': len(folds58(recs, effective, enforce_counts=False)), 'selected': best['familyId']}, sort_keys=True))
        else:
            execute(p3, args.output)
        return 0
    except Exception as error:
        print(json.dumps({'status': 'REFUSED', 'reason': str(error)}, sort_keys=True), file=os.sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
