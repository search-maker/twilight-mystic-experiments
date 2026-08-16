#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def req(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding='utf-8'))
    req(isinstance(value, dict), f'object required: {path}')
    return value


def canonical_sha(value: Any, omit: str | None = None) -> str:
    body = dict(value) if isinstance(value, dict) else value
    if isinstance(body, dict) and omit is not None:
        body.pop(omit, None)
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


d = load(HERE / 'implementation-v1.json')
p = load(ROOT / 'review/level-b-v3-training-only-prefit-freeze-v2/protocol-v2.json')
oldp = load(ROOT / 'review/level-b-v2-training-prefit-freeze-v3-densified58/protocol-v3.json')
req(d['descriptorSha256'] == canonical_sha(d, 'descriptorSha256') == '2536ec084597b9e6d9e2dabfbf7902de28c91d02b510415dc4f926e9595be104', 'descriptor self-hash drift')
req(d['governance'] == p['governance'] == 'MYSTIC-STATE-0071', 'governance drift')
req(d['sourceMain'] == '9c89c05e0c6cc099f980c675c7ab73f860782d01', 'implementation source main drift')
req(p['protocolSha256'] == canonical_sha(p, 'protocolSha256') == d['bindings']['prefitV2CanonicalSha256'] == '8e3928634c3d297974c07533bed3bbfa24783f14ed55391fd318f817282d9a8e', 'prefit v2 hash drift')
req(oldp['protocolSha256'] == canonical_sha(oldp, 'protocolSha256') == d['bindings']['legacyDensified58PrefitCanonicalSha256'] == 'eaf8d1d047fa5a336027a18b3cddd015943f4a28fd58c568fac233f819baaf73', 'legacy prefit hash drift')
paths = {
    'prefitV2GitBlobSha': ROOT / d['bindings']['prefitV2Path'],
    'legacyDensified58TrainerGitBlobSha': ROOT / d['bindings']['legacyDensified58TrainerPath'],
    'legacyGeneration2EngineGitBlobSha': ROOT / d['bindings']['legacyGeneration2EnginePath'],
    'legacyDensified58PrefitGitBlobSha': ROOT / d['bindings']['legacyDensified58PrefitPath'],
}
for field, path in paths.items():
    req(path.is_file(), f'missing bound source: {path}')
    req(git_blob_sha(path) == d['bindings'][field], f'Git blob drift: {field}')
for name, expected in d['sourceSha256'].items():
    req(file_sha(HERE / name) == expected, f'implementation source SHA drift: {name}')
req(d['syntheticReviewRequirements']['candidateCount'] == p['candidateDefinition']['candidateCountRequired'] == 145, 'candidate count binding drift')
req(d['syntheticReviewRequirements']['changedCandidateCount'] == p['candidateDefinition']['newFamily']['candidateCount'] == 144, 'changed candidate count binding drift')
req(d['syntheticReviewRequirements']['cvFoldCount'] == p['crossValidation']['totalFoldCountRequired'] == 73, 'CV count binding drift')
req(d['realExecutionSurface']['requiresExactExpandedDatasetCanonicalSha256'] == p['sourceBindings']['expandedDatasetSha256'] == '58c977acf84b6ce17717765c2052f7f9fd64e2965e5bf447eba5cc4accb30435', 'dataset binding drift')
req(d['realExecutionSurface']['requiresExactTrainingGeometryCount'] == p['roleIsolation']['trainingGeometryCountRequired'] == 58, 'training geometry count drift')
req(d['realExecutionSurface']['requiresExactCandidateCount'] == 145, 'real execution candidate count drift')
req(d['realExecutionSurface']['networkAccessImplemented'] is False, 'network surface opened')
req(d['realExecutionSurface']['scientificSolverExecutionImplemented'] is False, 'solver surface opened')
req(d['realExecutionSurface']['protectedValidationOpeningImplemented'] is False, 'protected validation surface opened')
for key, value in d['reviewBoundaries'].items():
    req(value is False, f'review boundary opened: {key}')
print('PASS: Level-B v3 implementation is exact-prefit-bound, legacy-parity-bound, synthetic-review-only, and has no network/scientific execution surface')
