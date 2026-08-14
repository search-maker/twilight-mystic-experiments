#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

CORE_REL = Path('review/level-b-v2-densified58-fresh-validation-recovery-v2/fresh_validation_v2.py')
RECOVERY_REL = Path('review/level-b-v2-densified58-fresh-validation-recovery-v2/recovery-v2.json')
REQUIRED = ['case-result.json','input-resolved.txt','runtime-report.json','prepared.json','randomseed','syntax-stdout.txt','syntax-stderr.txt','solver-stdout.txt','solver-stderr.txt','mc.flx.spc','mc.flx.std.spc','mc.rad.spc','mc.rad.std.spc','mc.flx.is.spc','mc.is.spc','mc0.rad','mc0.rad.std']


class Refusal(RuntimeError):
    pass


def req(condition: bool, message: str) -> None:
    if not condition:
        raise Refusal(message)


def canon(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def selfhash(value: dict[str, Any]) -> str:
    body = copy.deepcopy(value)
    body['manifestSha256'] = None
    return canon(body)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding='utf-8'))
    req(isinstance(value, dict), f'object required: {path}')
    return value


def module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    req(spec is not None and spec.loader is not None, f'cannot load module: {path}')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build(repo_root: Path, recovery: dict[str, Any]) -> dict[str, Any]:
    core = module('fresh_validation_recovery_v2', repo_root / CORE_REL)
    contract = core.effective_contract(recovery, repo_root)
    cases: list[dict[str, Any]] = []
    for index, case in enumerate(core.expected_cases(contract, recovery, repo_root), 1):
        row = dict(case)
        row.update({
            'ordinalWithinValidation': index,
            'role': 'protected-holdout',
            'executionStage': 'FRESH_PROTECTED_HOLDOUT_AFTER_DENSIFIED58_MODEL_FREEZE',
            'method': 'alis',
            'groupId': case['geometryId'],
            'expectedOutputGrid': {
                'nodeCount': 8001,
                'startNm': 380.0,
                'stopNm': 780.0,
                'canonicalTokenGridSha256': 'b5fae53c1cc88c7f3de6e3689bc25e4a36c54033d1d1bfd6169482f30cc5b477',
            },
        })
        cases.append(row)
    geometries: list[dict[str, Any]] = []
    for selected in contract['geometrySelection']['selectedGeometries']:
        geometries.append({
            'geometryId': selected['geometryId'],
            **selected['geometry'],
            'normalizedCoordinates': selected['normalizedCoordinates'],
            'nearestTrainingDistance': selected['nearestTrainingDistance'],
            'nearestOpenedOrdinal22GeometryDistance': selected['nearestOpenedOrdinal22GeometryDistance'],
            'role': 'protected-holdout',
            'executionStage': 'FRESH_PROTECTED_HOLDOUT_AFTER_DENSIFIED58_MODEL_FREEZE',
        })
    manifest: dict[str, Any] = {
        'schemaVersion': 2,
        'manifestId': 'level-b-v2-densified58-fresh-validation-execution-manifest-v1',
        'manifestSha256': None,
        'status': 'REVIEW_ONLY_FROZEN_FRESH_VALIDATION_MANIFEST_NO_AUTHORIZATION',
        'governance': 'MYSTIC-STATE-0070',
        'stageId': 'LEVEL_B_V2_DENSIFIED58_FRESH_PROTECTED_VALIDATION_V2_ORDINAL25_RECOVERY',
        'trainingOnly': False,
        'sourceContractId': contract['contractId'],
        'sourceRecoveryId': recovery['recoveryId'],
        'scientificOrdinalCandidate': 25,
        'ordinal24DispatchRunId': 31840757436,
        'ordinal24ProtectedValuesRead': False,
        'ordinal24SolverExecutionCount': 0,
        'runtimeIdentityRequired': contract['runtimeIdentityRequired'],
        'runtimePackage': {
            'runner': 'ubuntu-24.04',
            'python': '3.12.4',
            'exactPackageSpec': 'rubin-libradtran=2.0.6=py312pl5321he9373c2_1',
            'setupAction': 'mamba-org/setup-micromamba@v2',
        },
        'frozenInputs': {
            'wavelengthDomainNm': [380.0,780.0],
            'molecularAbsorption': 'crs',
            'mcSpherical': '1D',
            'albedo': 0.15,
            'solarFlux': 'atlas_plus_modtran',
            'atmosphereProfile': 'AFGLUS',
            'observerElevationRepresentation': 'ASCENDING_ATM_Z_GRID_BOTTOM_EQUALS_PHYSICAL_OBSERVER_ELEVATION',
            'localSurfaceZoutKm': 0.0,
            'altitudeShortcutAllowed': False,
            'mcElevationFileShortcutAllowed': False,
            'exactZeroPreserved': True,
            'epsilonSubstitutionAllowed': False,
        },
        'geometryCount': 6,
        'caseCount': 24,
        'configuredPhotonHistories': 960_000_000,
        'geometries': geometries,
        'cases': cases,
        'artifactContract': {
            'artifactNamePrefix': 'level-b-v2-v0070-o25-case-',
            'oneImmutableArtifactPerCase': True,
            'exactCaseArtifactUniverseRequired': True,
            'requiredMembers': REQUIRED,
            'rawMemberSha256MapExact': True,
            'rawCaseResultSelfHashRequired': True,
            'githubZipDigestRequired': True,
            'fullSpectrumRequired': True,
            'fullSpectrumNodeCount': 8001,
        },
        'executionLimits': {
            'workflowAttemptExactly': 1,
            'syntaxChecksPerCaseExactly': 1,
            'solverExecutionsPerCaseExactly': 1,
            'automaticRetryCountMaximum': 0,
            'resumeAllowed': False,
            'githubRerunAllowed': False,
            'maxParallel': 24,
        },
        'closedUntilAuthorization': {
            'scientificOrdinalAllocated': False,
            'protectedHoldoutOpeningAuthorized': False,
            'holdoutValuesMayBeRead': False,
            'scientificSolverExecutionAuthorized': False,
            'productionPromotionAuthorized': False,
            'workerBLaneReactivated': False,
            'workerCLaneReactivated': False,
        },
    }
    req([case['seed'] for case in cases] == list(range(2101000025, 2101000049)), 'manifest seed order drift')
    req(len({case['caseId'] for case in cases}) == 24, 'manifest case id collision')
    manifest['manifestSha256'] = selfhash(manifest)
    return manifest


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo-root', type=Path, required=True)
    ap.add_argument('--recovery', type=Path, default=RECOVERY_REL)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    try:
        recovery = load(args.recovery)
        manifest = build(args.repo_root, recovery)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + '\n', encoding='utf-8')
        print(manifest['manifestSha256'])
        return 0
    except Exception as error:
        print(json.dumps({'status':'REFUSED','reason':str(error)}, sort_keys=True))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
