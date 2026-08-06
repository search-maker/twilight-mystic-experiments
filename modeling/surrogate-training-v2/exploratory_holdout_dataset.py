#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
import statistics
from pathlib import Path
from typing import Any

SOURCE_DATASET_RAW_SHA256 = '81db9f2c418d4b078c23586513c5ba4591f3f3a496367bd818c8701d26136c00'
SOURCE_AUDIT_RAW_SHA256 = 'a3b427bbd345e310f851d8839da4ff92931f9b747e6981700eb5a3878a38882b'
ORDINAL12_ANALYSIS_RAW_SHA256 = 'c18f9ca23c910924400360ca18c4186d30594bc1aa2d3dd07a43a6031b274237'
ORDINAL13_ANALYSIS_RAW_SHA256 = 'f21548f0c6fe043ba5600ced1f0b19fbe569be6c2bca0de24ca5894dd6b01ad1'
PROTOCOL_SHA256 = 'f8fe9d486679ef1c9179ed08c790da987bc838cd952effcdebb33862f57d8f69'
MODEL_HASH = '381323604143498619cec494d221747d0d32f37a7e7cbb811b0154b6b4f68848'
TRAINING_DATASET_SHA256 = 'eb4a5e13bb31d2eec32204574547847cb03c0723cd5cab5538ff2e12b468ded1'
SOURCE_STAGE = 'twilight-surrogate-tier-1-analysis-v2'
SOURCE_STATUS = 'TIER_1_NUMERICAL_DATASET_PARTIAL_PRECISION'
WAVE1_STAGE = 'tier1-precision-continuation-wave1-ordinal11-execution-v5'
WAVE2_STAGE = 'tier1-precision-continuation-wave2-ordinal12-execution-v1'
WAVE3_STAGE = 'tier1-precision-continuation-wave3-ordinal13-execution-v1'
OUTPUT_STAGE = 'surrogate-training-v2-exploratory-internal-holdout-dataset-v1'
OUTPUT_STATUS = 'INTERNAL_HOLDOUT_VALUES_OPENED_EXACTLY_ONCE'
ALL_IDS = tuple(f'train-{index:04d}' for index in range(1, 49))
HOLDOUT_IDS = tuple(f'train-{index:04d}' for index in range(5, 46, 5))
CONTINUATION_IDS = (
    'train-0003', 'train-0007', 'train-0009', 'train-0011', 'train-0013',
    'train-0015', 'train-0017', 'train-0019', 'train-0023', 'train-0027',
    'train-0029', 'train-0031', 'train-0033', 'train-0035', 'train-0039',
    'train-0041', 'train-0043', 'train-0045', 'train-0046', 'train-0047',
)
WAVE1_HOLDOUT_IDS = ('train-0015', 'train-0035', 'train-0045')
WAVE2_HOLDOUT_IDS = ('train-0015', 'train-0035')
WAVE3_HOLDOUT_IDS = ('train-0015', 'train-0035')
ELIGIBLE = {'PRECISION_TARGET_MET', 'PRECISION_ACCEPTED'}
EXHAUSTED = {'PRECISION_CONTINUATION_EXHAUSTED', 'PRECISION_CONTINUATION_EXHAUSTED_ZERO_HIT'}
CIE = [0.09098, 0.13902, 0.20802, 0.323, 0.503, 0.71, 0.862, 0.954, 0.995, 0.87, 0.757, 0.631, 0.503, 0.175, 0.061]

class Refusal(RuntimeError):
    pass

def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n'

def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()

def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise Refusal(f'expected object: {path}')
    return value

def _array_bounds(text: str, key: str) -> tuple[int, int, list[str]]:
    match = re.search(rf'"{re.escape(key)}"\s*:\s*\[', text)
    if match is None:
        raise Refusal(f'array missing: {key}')
    open_index = text.find('[', match.start())
    index = open_index + 1
    in_string = False
    escaped = False
    depth = 0
    start: int | None = None
    objects: list[str] = []
    while index < len(text):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                in_string = False
        else:
            if char == '"':
                in_string = True
            elif char == '{':
                if depth == 0:
                    start = index
                depth += 1
            elif char == '}':
                depth -= 1
                if depth < 0 or (depth == 0 and start is None):
                    raise Refusal(f'malformed object array: {key}')
                if depth == 0:
                    objects.append(text[start:index + 1])
                    start = None
            elif char == ']' and depth == 0:
                return open_index, index, objects
        index += 1
    raise Refusal(f'unterminated array: {key}')

def _identity(raw: str, label: str) -> str:
    match = re.search(r'"geometryId"\s*:\s*"([^"]+)"', raw)
    if match is None:
        raise Refusal(f'{label} identity missing')
    return match.group(1)

def load_holdout_source(path: Path) -> list[dict[str, Any]]:
    if raw_sha256(path) != SOURCE_DATASET_RAW_SHA256:
        raise Refusal('source corrected dataset raw hash changed')
    text = path.read_text(encoding='utf-8')
    left, right, objects = _array_bounds(text, 'records')
    skeleton = json.loads(text[:left] + '[]' + text[right + 1:])
    expected = {
        'schemaVersion': 2,
        'stageId': SOURCE_STAGE,
        'status': SOURCE_STATUS,
        'executionComplete': True,
        'scientificallyEligible': False,
        'surrogateTrainingAutomaticallyAuthorized': False,
    }
    stale = {key: (skeleton.get(key), wanted) for key, wanted in expected.items() if skeleton.get(key) != wanted}
    if stale:
        raise Refusal(f'source corrected dataset boundary changed: {stale}')
    identities = [_identity(raw, 'source record') for raw in objects]
    if tuple(identities) != ALL_IDS or len(set(identities)) != 48:
        raise Refusal('source geometry order or universe changed')
    rows: list[dict[str, Any]] = []
    for raw, geometry_id in zip(objects, identities, strict=True):
        role_match = re.search(r'"role"\s*:\s*"([^"]+)"', raw)
        expected_role = 'internal-holdout' if geometry_id in HOLDOUT_IDS else 'surrogate-training'
        if (role_match.group(1) if role_match else None) != expected_role:
            raise Refusal(f'source role map changed: {geometry_id}')
        if geometry_id in HOLDOUT_IDS:
            row = json.loads(raw)
            if not isinstance(row, dict) or row.get('geometryId') != geometry_id:
                raise Refusal(f'source holdout record malformed: {geometry_id}')
            rows.append(row)
    if tuple(row.get('geometryId') for row in rows) != HOLDOUT_IDS:
        raise Refusal('source holdout subset changed')
    return rows

def load_points(path: Path, expected_raw: str, selected_ids: tuple[str, ...], label: str) -> dict[str, dict[str, Any]]:
    if raw_sha256(path) != expected_raw:
        raise Refusal(f'{label} analysis raw hash changed')
    text = path.read_text(encoding='utf-8')
    _, _, objects = _array_bounds(text, 'points')
    identities = [_identity(raw, f'{label} point') for raw in objects]
    if tuple(identities) != CONTINUATION_IDS or len(set(identities)) != len(CONTINUATION_IDS):
        raise Refusal(f'{label} continuation point order or universe changed')
    selected: dict[str, dict[str, Any]] = {}
    for raw, geometry_id in zip(objects, identities, strict=True):
        if geometry_id in selected_ids:
            point = json.loads(raw)
            if not isinstance(point, dict):
                raise Refusal(f'{label} holdout point malformed: {geometry_id}')
            selected[geometry_id] = point
    if tuple(selected) != tuple(gid for gid in CONTINUATION_IDS if gid in selected_ids):
        raise Refusal(f'{label} holdout point subset changed')
    return selected

def _photopic(nodes: list[float]) -> float:
    if len(nodes) != 15:
        raise Refusal('selected-node vector must contain 15 values')
    return 683.002 * 10.0 * sum((value / 1000.0) * weight for value, weight in zip(nodes, CIE, strict=True))

def _close(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=1e-11, abs_tol=1e-30)

def validate_result(path: Path, expected_stage: str, expected_id: str, expected_block: int) -> dict[str, Any]:
    row = load(path)
    payload = {key: item for key, item in row.items() if key != 'contentSha256'}
    if row.get('contentSha256') != canonical_sha256(payload):
        raise Refusal(f'case content hash changed: {row.get("caseId")}')
    nodes = row.get('selectedNodeRadiance')
    value = row.get('selectedPhotopicContributionCdM2')
    if (
        row.get('groupId') != expected_id
        or row.get('block') != expected_block
        or row.get('stageId') != expected_stage
        or row.get('status') != 'COMPLETED'
        or row.get('role') != 'internal-holdout'
        or row.get('syntaxCheckCount') != 1
        or row.get('solverExecutionCount') != 1
        or row.get('retryAllowed') is not False
        or row.get('resumeAllowed') is not False
        or row.get('fittingSurfaceExposed') is not False
        or not isinstance(nodes, list)
        or len(nodes) != 15
        or any(isinstance(node, bool) or not isinstance(node, (int, float)) or not math.isfinite(float(node)) or float(node) < 0 for node in nodes)
        or isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or float(value) < 0
    ):
        raise Refusal(f'holdout execution proof changed: {row.get("caseId")}')
    parsed_nodes = [float(node) for node in nodes]
    if not _close(float(value), _photopic(parsed_nodes)):
        raise Refusal(f'holdout photopic value differs from nodes: {row.get("caseId")}')
    zero_hit = float(value) == 0.0 and all(node == 0.0 for node in parsed_nodes)
    if row.get('zeroHit') is not zero_hit:
        raise Refusal(f'holdout zero-hit semantics changed: {row.get("caseId")}')
    return row

def load_result_matrix(root: Path, ids: tuple[str, ...], blocks: tuple[int, ...], stage: str) -> dict[str, dict[int, dict[str, Any]]]:
    expected = {(gid, block) for gid in ids for block in blocks}
    found: dict[str, dict[int, dict[str, Any]]] = {}
    paths = sorted(root.rglob('case-result.json'))
    if len(paths) != len(expected):
        raise Refusal(f'expected {len(expected)} {stage} holdout results, found {len(paths)}')
    for path in paths:
        raw = load(path)
        key = (raw.get('groupId'), raw.get('block'))
        if key not in expected:
            raise Refusal(f'unplanned holdout case: {raw.get("caseId")}')
        row = validate_result(path, stage, str(key[0]), int(key[1]))
        if int(key[1]) in found.setdefault(str(key[0]), {}):
            raise Refusal(f'duplicate holdout case: {key}')
        found[str(key[0])][int(key[1])] = row
    if {(gid, block) for gid, pairs in found.items() for block in pairs} != expected:
        raise Refusal(f'{stage} holdout matrix incomplete')
    return found

def statistics_from(values: list[float], node_mean: list[float], point: dict[str, Any], geometry_id: str) -> dict[str, Any]:
    point_values = point.get('valuesCdM2')
    if not isinstance(point_values, list) or len(point_values) != len(values):
        raise Refusal(f'analysis values incomplete: {geometry_id}')
    if any(not _close(left, float(right)) for left, right in zip(values, point_values, strict=True)):
        raise Refusal(f'analysis/result value mismatch: {geometry_id}')
    mean = statistics.fmean(values)
    sample_std = statistics.stdev(values)
    zero_count = sum(value == 0.0 for value in values)
    rsem = None if zero_count else sample_std / math.sqrt(len(values)) / mean
    rsem_status = 'NOT_COMPUTED_ZERO_HIT_PRESENT' if zero_count else 'COMPUTED'
    point_rsem = point.get('relativeStandardErrorOfMean')
    if (rsem is None) != (point_rsem is None) or (rsem is not None and not _close(rsem, float(point_rsem))):
        raise Refusal(f'analysis RSEM mismatch: {geometry_id}')
    if point.get('relativeStandardErrorStatus') != rsem_status:
        raise Refusal(f'analysis RSEM status mismatch: {geometry_id}')
    if point.get('zeroHitBlockCount') != zero_count or not _close(float(point.get('zeroHitBlockFraction')), zero_count / len(values)):
        raise Refusal(f'analysis zero-hit mismatch: {geometry_id}')
    nonzero = [value for value in values if value != 0.0]
    point_nonzero = point.get('nonzeroBlockValuesCdM2')
    if not isinstance(point_nonzero, list) or len(point_nonzero) != len(nonzero) or any(not _close(left, float(right)) for left, right in zip(nonzero, point_nonzero, strict=True)):
        raise Refusal(f'analysis nonzero values mismatch: {geometry_id}')
    return {
        'blockCount': len(values),
        'valuesCdM2': values,
        'meanCdM2': mean,
        'sampleStdCdM2': sample_std,
        'relativeStandardErrorOfMean': rsem,
        'relativeStandardErrorStatus': rsem_status,
        'zeroHitBlockCount': zero_count,
        'zeroHitBlockFraction': zero_count / len(values),
        'nonzeroBlockValuesCdM2': nonzero,
        'nodeMeanRadiance': node_mean,
    }

def update_through_b6(source: dict[str, Any], point: dict[str, Any], wave1: dict[int, dict[str, Any]], wave2: dict[int, dict[str, Any]] | None) -> dict[str, Any]:
    gid = source['geometryId']
    rows = [wave1[3], wave1[4]] + ([] if wave2 is None else [wave2[5], wave2[6]])
    expected_blocks = 2 + len(rows)
    if point.get('blockCount') != expected_blocks or point.get('role') != 'internal-holdout':
        raise Refusal(f'ordinal12 holdout point block/role changed: {gid}')
    source_stats = source.get('statistics')
    source_values = source_stats.get('valuesCdM2') if isinstance(source_stats, dict) else None
    source_nodes = source_stats.get('nodeMeanRadiance') if isinstance(source_stats, dict) else None
    source_cases = source.get('caseIds')
    if not isinstance(source_values, list) or len(source_values) != 2 or not isinstance(source_nodes, list) or len(source_nodes) != 15 or not isinstance(source_cases, list) or len(source_cases) != 2:
        raise Refusal(f'source b1-b2 holdout evidence changed: {gid}')
    values = [float(v) for v in source_values] + [float(row['selectedPhotopicContributionCdM2']) for row in rows]
    node_mean = [(2.0 * float(old) + sum(float(row['selectedNodeRadiance'][i]) for row in rows)) / expected_blocks for i, old in enumerate(source_nodes)]
    classification = point.get('classification')
    if classification not in ELIGIBLE | EXHAUSTED:
        raise Refusal(f'ordinal12 holdout classification changed: {gid}')
    eligible = classification in ELIGIBLE
    if point.get('scientificallyEligible') is not eligible:
        raise Refusal(f'ordinal12 holdout eligibility mismatch: {gid}')
    record = copy.deepcopy(source)
    record['caseIds'] = list(source_cases) + [row['caseId'] for row in rows]
    record['classification'] = classification
    record['numericalStatus'] = point.get('numericalStatus')
    record['scientificallyEligible'] = eligible
    record['eligibleForProvisionalFit'] = False
    record['statistics'] = statistics_from(values, node_mean, point, gid)
    record['zeroHitCaseIds'] = list(source.get('zeroHitCaseIds') or []) + [row['caseId'] for row in rows if row.get('zeroHit')]
    bindings = dict(record.get('sourceBindings') or {})
    bindings.update({
        'sourceCorrectedDatasetRawSha256': SOURCE_DATASET_RAW_SHA256,
        'sourceCorrectedAuditRawSha256': SOURCE_AUDIT_RAW_SHA256,
        'ordinal12AnalysisRawSha256': ORDINAL12_ANALYSIS_RAW_SHA256,
        'continuationCaseContentSha256ByCaseId': {row['caseId']: row['contentSha256'] for row in rows},
    })
    record['sourceBindings'] = bindings
    return record

def update_through_b8(source: dict[str, Any], point: dict[str, Any], pair: dict[int, dict[str, Any]]) -> dict[str, Any]:
    gid = source['geometryId']
    if point.get('blockCount') != 8 or point.get('role') != 'internal-holdout':
        raise Refusal(f'ordinal13 holdout point block/role changed: {gid}')
    values = point.get('valuesCdM2')
    nonzero = point.get('nonzeroBlockValuesCdM2')
    if not isinstance(values, list) or len(values) != 8 or not isinstance(nonzero, list):
        raise Refusal(f'ordinal13 holdout values incomplete: {gid}')
    for offset, block in enumerate((7, 8), start=6):
        if not _close(float(values[offset]), float(pair[block]['selectedPhotopicContributionCdM2'])):
            raise Refusal(f'ordinal13 holdout value mismatch: {gid} b{block}')
    old_stats = source.get('statistics')
    old_nodes = old_stats.get('nodeMeanRadiance') if isinstance(old_stats, dict) else None
    if not isinstance(old_nodes, list) or len(old_nodes) != 15 or old_stats.get('blockCount') != 6:
        raise Refusal(f'source b1-b6 holdout evidence changed: {gid}')
    nodes7 = [float(v) for v in pair[7]['selectedNodeRadiance']]
    nodes8 = [float(v) for v in pair[8]['selectedNodeRadiance']]
    node_mean = [(6.0 * float(old) + left + right) / 8.0 for old, left, right in zip(old_nodes, nodes7, nodes8, strict=True)]
    classification = point.get('classification')
    if classification not in ELIGIBLE | EXHAUSTED:
        raise Refusal(f'ordinal13 holdout classification changed: {gid}')
    eligible = classification in ELIGIBLE
    if point.get('scientificallyEligible') is not eligible:
        raise Refusal(f'ordinal13 holdout eligibility mismatch: {gid}')
    record = copy.deepcopy(source)
    record['caseIds'] = list(source['caseIds']) + [pair[7]['caseId'], pair[8]['caseId']]
    record['classification'] = classification
    record['numericalStatus'] = point.get('numericalStatus')
    record['scientificallyEligible'] = eligible
    record['eligibleForProvisionalFit'] = False
    record['statistics'] = statistics_from([float(v) for v in values], node_mean, point, gid)
    source_zero = list(source.get('zeroHitCaseIds') or [])
    wave3_zero = [pair[b]['caseId'] for b in (7, 8) if pair[b].get('zeroHit')]
    combined = source_zero + wave3_zero
    if len(set(combined)) != len(combined) or len(combined) != record['statistics']['zeroHitBlockCount']:
        raise Refusal(f'ordinal13 holdout zero-hit identities changed: {gid}')
    record['zeroHitCaseIds'] = combined
    bindings = dict(record.get('sourceBindings') or {})
    bindings.update({
        'terminalAnalysisRawSha256': ORDINAL13_ANALYSIS_RAW_SHA256,
        'wave3CaseResultContentSha256ByCaseId': {pair[b]['caseId']: pair[b]['contentSha256'] for b in (7, 8)},
    })
    record['sourceBindings'] = bindings
    return record

def build(source_dataset: Path, source_audit: Path, ordinal12_analysis: Path, ordinal13_analysis: Path, wave1_root: Path, wave2_root: Path, wave3_root: Path) -> dict[str, Any]:
    if raw_sha256(source_audit) != SOURCE_AUDIT_RAW_SHA256:
        raise Refusal('source corrected audit raw hash changed')
    rows = load_holdout_source(source_dataset)
    points12 = load_points(ordinal12_analysis, ORDINAL12_ANALYSIS_RAW_SHA256, WAVE1_HOLDOUT_IDS, 'ordinal12')
    points13 = load_points(ordinal13_analysis, ORDINAL13_ANALYSIS_RAW_SHA256, WAVE3_HOLDOUT_IDS, 'ordinal13')
    wave1 = load_result_matrix(wave1_root, WAVE1_HOLDOUT_IDS, (3, 4), WAVE1_STAGE)
    wave2 = load_result_matrix(wave2_root, WAVE2_HOLDOUT_IDS, (5, 6), WAVE2_STAGE)
    wave3 = load_result_matrix(wave3_root, WAVE3_HOLDOUT_IDS, (7, 8), WAVE3_STAGE)
    output: list[dict[str, Any]] = []
    for source in rows:
        gid = source['geometryId']
        record = copy.deepcopy(source)
        if gid in WAVE1_HOLDOUT_IDS:
            record = update_through_b6(record, points12[gid], wave1[gid], wave2.get(gid))
        if gid in WAVE3_HOLDOUT_IDS:
            record = update_through_b8(record, points13[gid], wave3[gid])
        if record.get('role') != 'internal-holdout':
            raise Refusal(f'holdout role changed: {gid}')
        stats = record.get('statistics')
        mean = stats.get('meanCdM2') if isinstance(stats, dict) else None
        if isinstance(mean, bool) or not isinstance(mean, (int, float)) or not math.isfinite(float(mean)) or float(mean) <= 0:
            raise Refusal(f'holdout target unavailable: {gid}')
        output.append(record)
    counts: dict[int, int] = {}
    for row in output:
        count = int(row['statistics']['blockCount'])
        counts[count] = counts.get(count, 0) + 1
    if counts != {2: 6, 4: 1, 8: 2}:
        raise Refusal(f'holdout block-count distribution changed: {counts}')
    value = {
        'schemaVersion': 1,
        'stageId': OUTPUT_STAGE,
        'status': OUTPUT_STATUS,
        'protocolSha256': PROTOCOL_SHA256,
        'sourceModelHash': MODEL_HASH,
        'sourceTrainingDatasetSha256': TRAINING_DATASET_SHA256,
        'sourceCorrectedDatasetRawSha256': SOURCE_DATASET_RAW_SHA256,
        'sourceCorrectedAuditRawSha256': SOURCE_AUDIT_RAW_SHA256,
        'ordinal12AnalysisRawSha256': ORDINAL12_ANALYSIS_RAW_SHA256,
        'ordinal13AnalysisRawSha256': ORDINAL13_ANALYSIS_RAW_SHA256,
        'holdoutGeometryIds': list(HOLDOUT_IDS),
        'holdoutRecordCount': 9,
        'holdoutValuesIncluded': True,
        'internalHoldoutOpenedExactlyOnce': True,
        'selectionFromHoldoutForbidden': True,
        'thresholdTuningFromHoldoutForbidden': True,
        'blockCountDistribution': {str(k): v for k, v in sorted(counts.items())},
        'records': output,
    }
    value['holdoutDatasetSha256'] = canonical_sha256(value)
    return value

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-dataset', type=Path, required=True)
    parser.add_argument('--source-audit', type=Path, required=True)
    parser.add_argument('--ordinal12-analysis', type=Path, required=True)
    parser.add_argument('--ordinal13-analysis', type=Path, required=True)
    parser.add_argument('--wave1-results-root', type=Path, required=True)
    parser.add_argument('--wave2-results-root', type=Path, required=True)
    parser.add_argument('--wave3-results-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        value = build(args.source_dataset, args.source_audit, args.ordinal12_analysis, args.ordinal13_analysis, args.wave1_results_root, args.wave2_results_root, args.wave3_results_root)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump(value), encoding='utf-8', newline='\n')
        return 0
    except Exception as exc:
        print(dump({'status': 'REFUSED', 'reason': str(exc)}), end='')
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
