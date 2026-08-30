#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
CONTRACT = HERE / 'lunar-mystic-secondary-aod550-anchor-compatibility-v1.json'
PARENT_RUNTIME = HERE / 'lunar_mystic_computational_precision_runtime.py'
LUNAR_INPUT = HERE / 'lunar_mystic_input.py'


class LunarAnchorCompatibilityError(RuntimeError):
    pass


def _load_registered(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise LunarAnchorCompatibilityError(f'cannot import {path}')
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_contract(path: Path = CONTRACT) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('contractId') != 'lunar-mystic-secondary-aod550-anchor-compatibility-v1':
        raise LunarAnchorCompatibilityError('contract identity drift')
    if data.get('status') != 'FROZEN_TRANSPORT_COMPATIBILITY_PROBE_ONLY':
        raise LunarAnchorCompatibilityError('contract status drift')
    trigger = data.get('triggerEvidence') or {}
    if trigger.get('failedExecutionRunId') != 33296335660 or trigger.get('failedExecutionRunAttempt') != 1:
        raise LunarAnchorCompatibilityError('failed execution identity drift')
    if trigger.get('resultArtifactId') != 9727543649:
        raise LunarAnchorCompatibilityError('failed execution artifact drift')
    if trigger.get('resultArtifactDigest') != 'sha256:312e36383886adea928f02b87a86bccc1723eef438d1512b8d634cb0725a0392':
        raise LunarAnchorCompatibilityError('failed execution digest drift')
    if trigger.get('immutableClassification') != 'EXECUTION_INCOMPLETE':
        raise LunarAnchorCompatibilityError('failed execution classification drift')
    probe = data.get('probeDesign') or {}
    if probe.get('targetWavelengthNm') != [450.0, 650.0, 750.0]:
        raise LunarAnchorCompatibilityError('probe wavelength drift')
    if probe.get('technicalAnchorWavelengthNm') != 550.0:
        raise LunarAnchorCompatibilityError('anchor wavelength drift')
    if probe.get('photonHistoriesPerOutputWavelength') != 500000:
        raise LunarAnchorCompatibilityError('probe photon budget drift')
    seeds = probe.get('freshProbeSeeds')
    if seeds != [28763001, 28763002, 28763003] or len(set(seeds)) != 3:
        raise LunarAnchorCompatibilityError('probe seed drift')
    if set(seeds).intersection(trigger.get('failedExecutionSeedsConsumedAndForbidden') or []):
        raise LunarAnchorCompatibilityError('consumed exec001 seed reuse')
    protected = data.get('protectedBoundaries') or {}
    for key, value in protected.items():
        if value is not False:
            raise LunarAnchorCompatibilityError(f'protected boundary drift: {key}')
    return data


def probe_cases(contract: dict[str, Any] | None = None) -> tuple[dict[str, Any], ...]:
    contract = contract or load_contract()
    physical = contract['frozenPhysicalState']
    probe = contract['probeDesign']
    out = []
    for target, seed in zip(probe['targetWavelengthNm'], probe['freshProbeSeeds']):
        out.append({
            'caseId': f'w{int(target)}-anchor550',
            'targetWavelengthNm': float(target),
            'anchorWavelengthNm': float(probe['technicalAnchorWavelengthNm']),
            'randomSeed': int(seed),
            'photonHistories': int(probe['photonHistoriesPerOutputWavelength']),
            'moonZenithDeg': float(physical['moonZenithDeg']),
            'targetAltitudeDeg': float(physical['targetAltitudeDeg']),
            'targetRelativeAzimuthToMoonDeg': float(physical['targetRelativeAzimuthToMoonDeg']),
            'observerElevationM': float(physical['observerElevationM']),
            'aod550': float(physical['aod550']),
            'albedo': float(physical['lambertianAlbedo']),
        })
    return tuple(out)


def _numeric_source_rows(path: Path) -> list[tuple[float, str]]:
    rows = []
    for raw in path.read_text(encoding='utf-8').splitlines():
        parts = raw.split()
        if len(parts) < 2:
            continue
        try:
            wavelength = float(parts[0])
            value = float(parts[1])
        except ValueError:
            continue
        if not math.isfinite(wavelength) or not math.isfinite(value) or value < 0:
            raise LunarAnchorCompatibilityError('invalid frozen source row')
        rows.append((wavelength, raw))
    return rows


def write_sparse_anchor_source(full_source: Path, target_nm: float, destination: Path, anchor_nm: float = 550.0) -> dict[str, Any]:
    wanted = sorted({float(target_nm), float(anchor_nm)})
    if len(wanted) != 2:
        raise LunarAnchorCompatibilityError('target may not equal technical anchor')
    found: dict[float, str] = {}
    for wavelength, raw in _numeric_source_rows(full_source):
        if wavelength in wanted:
            if wavelength in found:
                raise LunarAnchorCompatibilityError(f'duplicate frozen source row at {wavelength}')
            found[wavelength] = raw
    if sorted(found) != wanted:
        raise LunarAnchorCompatibilityError(f'frozen source does not contain exact nodes {wanted}')
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text('\n'.join(found[w] for w in wanted) + '\n', encoding='utf-8')
    return {
        'targetWavelengthNm': float(target_nm),
        'anchorWavelengthNm': float(anchor_nm),
        'wavelengthRowsNm': wanted,
        'rowCount': 2,
        'copiedExactFrozenSourceRows': True,
        'interpolationApplied': False,
        'renormalizationApplied': False,
    }


def convert_reviewed_input_to_anchor_grid(text: str, target_nm: float, anchor_nm: float = 550.0) -> str:
    lo, hi = sorted((float(target_nm), float(anchor_nm)))
    if lo == hi:
        raise LunarAnchorCompatibilityError('target may not equal technical anchor')
    if text.count('wavelength 380 780') != 1:
        raise LunarAnchorCompatibilityError('reviewed wavelength line drift')
    if text.count(f'mc_spectral_is {anchor_nm:.1f}') != 1:
        raise LunarAnchorCompatibilityError('reviewed ALIS anchor line drift')
    lines = []
    for line in text.splitlines():
        if line == 'wavelength 380 780':
            lines.append(f'wavelength {lo:.1f} {hi:.1f}')
        elif line == f'mc_spectral_is {anchor_nm:.1f}':
            continue
        else:
            lines.append(line)
    rendered = '\n'.join(lines) + '\n'
    expected_range = f'wavelength {lo:.1f} {hi:.1f}'
    if rendered.count(expected_range) != 1:
        raise LunarAnchorCompatibilityError('anchor-inclusive wavelength range drift')
    if not (lo <= anchor_nm <= hi and lo <= target_nm <= hi):
        raise LunarAnchorCompatibilityError('target/anchor not contained in wavelength interval')
    if 'mc_spectral_is' in rendered:
        raise LunarAnchorCompatibilityError('mc_spectral_is remained enabled')
    if rendered.count('aerosol_set_tau_at_wvl 550 0.100000') != 1:
        raise LunarAnchorCompatibilityError('frozen AOD550 normalization drift')
    if rendered.count('mc_std') != 1:
        raise LunarAnchorCompatibilityError('mc_std drift')
    return rendered


def _runtime_identity(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding='utf-8'))
    return {
        'uvspecSha256': data.get('uvspecSha256'),
        'libRadtranDataTreeSha256': data.get('libRadtranDataTreeSha256'),
    }


def prepare_probe(*, data_dir: Path, atmosphere_file: Path, atlas_path: Path, runtime_report: Path, output_root: Path) -> dict[str, Any]:
    contract = load_contract()
    parent_runtime = _load_registered('lunar_anchor_parent_runtime', PARENT_RUNTIME)
    lunar_input = _load_registered('lunar_anchor_input_renderer', LUNAR_INPUT)
    output_root.mkdir(parents=True, exist_ok=True)
    full_source = output_root / 'frozen-lunar-source-380-780nm.dat'
    source_meta = parent_runtime.build_lunar_source_from_runtime_atlas(atlas_path, full_source)
    identity = _runtime_identity(runtime_report)
    required = contract['sourceAndRuntime']
    if identity['uvspecSha256'] != required['uvspecSha256']:
        raise LunarAnchorCompatibilityError('uvspec runtime hash drift')
    if identity['libRadtranDataTreeSha256'] != required['libRadtranDataTreeSha256']:
        raise LunarAnchorCompatibilityError('libRadtran data tree hash drift')
    prepared = []
    for case in probe_cases(contract):
        case_dir = output_root / case['caseId']
        case_dir.mkdir(parents=True, exist_ok=True)
        sparse_source = case_dir / 'lunar-source-target-plus-550.dat'
        sparse_meta = write_sparse_anchor_source(full_source, case['targetWavelengthNm'], sparse_source, case['anchorWavelengthNm'])
        base, base_meta = lunar_input.render_lunar_mystic_input(
            data_dir=data_dir,
            atmosphere_file=atmosphere_file,
            lunar_source_file=sparse_source,
            moon_zenith_deg=case['moonZenithDeg'],
            target_altitude_deg=case['targetAltitudeDeg'],
            target_relative_azimuth_to_moon_deg=case['targetRelativeAzimuthToMoonDeg'],
            observer_elevation_m=case['observerElevationM'],
            aod550=case['aod550'],
            albedo=case['albedo'],
            photon_histories=case['photonHistories'],
            random_seed=case['randomSeed'],
            case_dir=case_dir,
            runtime_identity=identity,
            alis_importance_nm=case['anchorWavelengthNm'],
        )
        rendered = convert_reviewed_input_to_anchor_grid(base, case['targetWavelengthNm'], case['anchorWavelengthNm'])
        input_path = case_dir / 'case.inp'
        input_path.write_text(rendered, encoding='utf-8')
        item = {
            **case,
            'inputPath': str(input_path),
            'sparseSourcePath': str(sparse_source),
            'sparseSourceMetadata': sparse_meta,
            'baseRenderMetadata': base_meta,
        }
        (case_dir / 'prepared.json').write_text(json.dumps(item, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        prepared.append(item)
    manifest = {
        'schemaVersion': 1,
        'contractId': contract['contractId'],
        'status': 'PREPARED_TRANSPORT_COMPATIBILITY_PROBE_NO_RESULTS',
        'fullFrozenSource': source_meta,
        'caseCount': len(prepared),
        'cases': prepared,
        'solverExecutedByPreparation': False,
        'precisionClassificationAllowed': False,
        'empiricalValidationClaim': False,
        'productionAuthorized': False,
    }
    (output_root / 'prepared-manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return manifest


def _read_wavelength_value(path: Path, wavelength_nm: float) -> float:
    matches = []
    for raw in path.read_text(encoding='utf-8', errors='strict').splitlines():
        parts = raw.split()
        if len(parts) < 2:
            continue
        try:
            wavelength = float(parts[0])
            value = float(parts[-1])
        except ValueError:
            continue
        if not math.isfinite(wavelength) or not math.isfinite(value):
            raise LunarAnchorCompatibilityError(f'nonfinite output row in {path}')
        if abs(wavelength - wavelength_nm) <= 5e-4:
            matches.append(value)
    if len(matches) != 1:
        raise LunarAnchorCompatibilityError(f'expected exactly one {wavelength_nm} nm row in {path}, found {len(matches)}')
    return matches[0]


def evaluate_probe(result_root: Path) -> dict[str, Any]:
    contract = load_contract()
    failures = []
    rows = []
    for case in probe_cases(contract):
        case_dir = result_root / case['caseId']
        exit_path = case_dir / 'uvspec.exitcode'
        if not exit_path.is_file():
            failures.append(f'MISSING_EXITCODE:{case["caseId"]}')
            rows.append({**case, 'exitCode': None})
            continue
        exit_code = int(exit_path.read_text(encoding='utf-8').strip())
        item = {**case, 'exitCode': exit_code}
        if exit_code != 0:
            failures.append(f'NONZERO_UVSPEC_EXIT:{case["caseId"]}:{exit_code}')
            rows.append(item)
            continue
        rad_path = case_dir / 'mc.rad.spc'
        std_path = case_dir / 'mc.rad.std.spc'
        if not rad_path.is_file() or not std_path.is_file():
            failures.append(f'MISSING_MYSTIC_OUTPUT:{case["caseId"]}')
            rows.append(item)
            continue
        target_rad = _read_wavelength_value(rad_path, case['targetWavelengthNm'])
        target_std = _read_wavelength_value(std_path, case['targetWavelengthNm'])
        anchor_rad = _read_wavelength_value(rad_path, case['anchorWavelengthNm'])
        anchor_std = _read_wavelength_value(std_path, case['anchorWavelengthNm'])
        item.update({
            'targetRadiance': target_rad,
            'targetMcStd': target_std,
            'anchor550RadianceDiagnosticOnly': anchor_rad,
            'anchor550McStdDiagnosticOnly': anchor_std,
        })
        if target_rad <= 0 or not math.isfinite(target_rad):
            failures.append(f'NONPOSITIVE_TARGET_RADIANCE:{case["caseId"]}')
        if target_std <= 0 or not math.isfinite(target_std):
            failures.append(f'NONPOSITIVE_TARGET_MCSTD:{case["caseId"]}')
        rows.append(item)
    passed = not failures
    report = {
        'schemaVersion': 1,
        'contractId': contract['contractId'],
        'status': 'PASS_TRANSPORT_COMPATIBILITY_ONLY' if passed else 'FAIL_TRANSPORT_COMPATIBILITY',
        'transportCompatibilityPassed': passed,
        'failures': failures,
        'cases': rows,
        'probeOutputsUsedForPrecisionClassification': False,
        'secondaryComputationalPrecisionValidated': False,
        'toaSourceValidated': False,
        'atmosphericScatteredMoonlightEmpiricallyValidated': False,
        'finiteMoonDiskValidated': False,
        'totalSkyValidated': False,
        'productionAuthorized': False,
    }
    (result_root / 'compatibility-report.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--evaluate', action='store_true')
    parser.add_argument('--data-dir', type=Path)
    parser.add_argument('--atmosphere-file', type=Path)
    parser.add_argument('--atlas-file', type=Path)
    parser.add_argument('--runtime-report', type=Path)
    parser.add_argument('--output-root', type=Path, required=True)
    args = parser.parse_args()
    if args.prepare == args.evaluate:
        parser.error('choose exactly one of --prepare or --evaluate')
    if args.prepare:
        for name in ('data_dir', 'atmosphere_file', 'atlas_file', 'runtime_report'):
            if getattr(args, name) is None:
                parser.error(f'--{name.replace("_", "-")} required with --prepare')
        prepare_probe(
            data_dir=args.data_dir,
            atmosphere_file=args.atmosphere_file,
            atlas_path=args.atlas_file,
            runtime_report=args.runtime_report,
            output_root=args.output_root,
        )
        return 0
    report = evaluate_probe(args.output_root)
    return 0 if report['transportCompatibilityPassed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
