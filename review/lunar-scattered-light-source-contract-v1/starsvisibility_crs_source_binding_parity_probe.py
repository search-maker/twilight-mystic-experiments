#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def write_source(path: Path, wavelengths: list[float], fluxes: list[float]) -> None:
    path.write_text(
        ''.join(f'{w:.6f} {f:.12e}\n' for w, f in zip(wavelengths, fluxes)),
        encoding='utf-8',
    )


def render_input(data_dir: Path, atmosphere: Path, source: Path) -> str:
    return '\n'.join([
        f'data_files_path {data_dir}',
        f'atmosphere_file {atmosphere}',
        f'source solar {source}',
        'mol_abs_param crs',
        'wavelength 380 780',
        'sza 0',
        'no_absorption',
        'no_scattering',
        'albedo 0',
        'rte_solver disort',
        'number_of_streams 4',
        'zout TOA',
        'output_user lambda edir',
        'quiet',
        '',
    ])


def parse_lambda_edir(stdout: bytes) -> tuple[list[float], list[float]]:
    wavelengths: list[float] = []
    edir: list[float] = []
    for raw in stdout.decode('utf-8', errors='strict').splitlines():
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        fields = line.split()
        if len(fields) < 2:
            raise ValueError(f'unexpected uvspec output row: {line!r}')
        wavelength = float(fields[0])
        value = float(fields[1])
        if not math.isfinite(wavelength) or not math.isfinite(value):
            raise ValueError('non-finite uvspec output')
        wavelengths.append(wavelength)
        edir.append(value)
    if not wavelengths:
        raise ValueError('uvspec output contained no lambda/edir rows')
    return wavelengths, edir


def run_arm(*, uvspec: Path, input_text: str, out_dir: Path, arm: str) -> dict:
    inp = input_text.encode('utf-8')
    input_path = out_dir / f'arm-{arm}.inp'
    stdout_path = out_dir / f'arm-{arm}-stdout.txt'
    stderr_path = out_dir / f'arm-{arm}-stderr.txt'
    input_path.write_bytes(inp)
    completed = subprocess.run(
        [str(uvspec)],
        input=inp,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=180,
    )
    stdout_path.write_bytes(completed.stdout)
    stderr_path.write_bytes(completed.stderr)
    parsed = None
    parse_error = None
    try:
        wavelengths, edir = parse_lambda_edir(completed.stdout)
        parsed = {'wavelengthNm': wavelengths, 'edir': edir}
    except Exception as exc:
        parse_error = f'{type(exc).__name__}: {exc}'
    return {
        'exitCode': completed.returncode,
        'inputSha256': sha256_bytes(inp),
        'stdoutSha256': sha256_bytes(completed.stdout),
        'stderrSha256': sha256_bytes(completed.stderr),
        'parsed': parsed,
        'parseError': parse_error,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--uvspec', required=True, type=Path)
    parser.add_argument('--data-dir', required=True, type=Path)
    parser.add_argument('--atmosphere', required=True, type=Path)
    parser.add_argument('--runtime-report', required=True, type=Path)
    parser.add_argument('--contract', required=True, type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args()

    out_dir = args.output_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    uvspec = args.uvspec.resolve()
    data_dir = args.data_dir.resolve()
    atmosphere = args.atmosphere.resolve()
    contract_path = args.contract.resolve()
    runtime_report_path = args.runtime_report.resolve()

    contract = json.loads(contract_path.read_text(encoding='utf-8'))
    runtime = json.loads(runtime_report_path.read_text(encoding='utf-8'))
    expected_runtime = contract['exactRuntime']
    runtime_binding_ok = (
        runtime.get('uvspecSha256') == expected_runtime['uvspecSha256']
        and runtime.get('libRadtranDataTreeSha256') == expected_runtime['libRadtranDataTreeSha256']
        and runtime.get('scientificSolverExecuted') is False
    )

    wavelengths = [float(x) for x in contract['probe']['sourceGridNm']]
    flux_a = [float(x) for x in contract['probe']['armAFlux']]
    flux_b = [float(x) for x in contract['probe']['armBFlux']]
    source_a = out_dir / 'source-a.dat'
    source_b = out_dir / 'source-b.dat'
    write_source(source_a, wavelengths, flux_a)
    write_source(source_b, wavelengths, flux_b)

    arm_a = run_arm(
        uvspec=uvspec,
        input_text=render_input(data_dir, atmosphere, source_a),
        out_dir=out_dir,
        arm='a',
    )
    arm_b = run_arm(
        uvspec=uvspec,
        input_text=render_input(data_dir, atmosphere, source_b),
        out_dir=out_dir,
        arm='b',
    )

    expected_ratio = float(contract['frozenDecisionRule']['expectedArmBToArmARatio'])
    relative_tolerance = float(contract['frozenDecisionRule']['relativeTolerancePerComparisonWavelength'])
    reasons: list[str] = []
    ratios: list[float] = []
    relative_errors: list[float] = []

    if not runtime_binding_ok:
        reasons.append('EXACT_RUNTIME_BINDING_FAILED')
    if arm_a['exitCode'] != 0:
        reasons.append('ARM_A_UVSPEC_NONZERO_EXIT')
    if arm_b['exitCode'] != 0:
        reasons.append('ARM_B_UVSPEC_NONZERO_EXIT')
    if arm_a['parsed'] is None:
        reasons.append('ARM_A_OUTPUT_PARSE_FAILED')
    if arm_b['parsed'] is None:
        reasons.append('ARM_B_OUTPUT_PARSE_FAILED')

    if not reasons:
        wa = arm_a['parsed']['wavelengthNm']
        wb = arm_b['parsed']['wavelengthNm']
        ea = arm_a['parsed']['edir']
        eb = arm_b['parsed']['edir']
        if wa != wavelengths or wb != wavelengths or wa != wb:
            reasons.append('COMPARISON_WAVELENGTH_VECTOR_MISMATCH')
        elif len(ea) != len(eb) or len(ea) != len(wavelengths):
            reasons.append('OUTPUT_LENGTH_MISMATCH')
        elif any((not math.isfinite(x) or x <= 0.0) for x in ea):
            reasons.append('ARM_A_EDIR_NOT_FINITE_STRICTLY_POSITIVE')
        elif any((not math.isfinite(x) or x <= 0.0) for x in eb):
            reasons.append('ARM_B_EDIR_NOT_FINITE_STRICTLY_POSITIVE')
        else:
            ratios = [b / a for a, b in zip(ea, eb)]
            relative_errors = [abs(r / expected_ratio - 1.0) for r in ratios]
            if any(not math.isfinite(x) for x in ratios + relative_errors):
                reasons.append('NONFINITE_SOURCE_AMPLITUDE_RATIO')
            elif any(x > relative_tolerance for x in relative_errors):
                reasons.append('RATIO_OUTSIDE_EXTERNAL_PREREGISTERED_RELATIVE_TOLERANCE')

    passed = not reasons
    report = {
        'schemaVersion': 1,
        'contractId': contract['contractId'],
        'externalPreregistration': contract['externalPreregistration'],
        'status': (
            contract['frozenDecisionRule']['pass']
            if passed else contract['frozenDecisionRule']['fail']
        ),
        'classification': contract['probe']['classification'],
        'runtimeBindingPassed': runtime_binding_ok,
        'runtimeReportSha256': sha256_file(runtime_report_path),
        'contractSha256': sha256_file(contract_path),
        'uvspecSha256Observed': sha256_file(uvspec),
        'sourceA': {'sha256': sha256_file(source_a), 'fluxValues': flux_a},
        'sourceB': {'sha256': sha256_file(source_b), 'fluxValues': flux_b},
        'armA': arm_a,
        'armB': arm_b,
        'expectedArmBToArmARatio': expected_ratio,
        'relativeTolerancePerComparisonWavelength': relative_tolerance,
        'observedRatios': ratios,
        'observedRelativeErrors': relative_errors,
        'maximumObservedRelativeError': max(relative_errors) if relative_errors else None,
        'reasons': reasons,
        **contract['boundaries'],
    }
    (out_dir / 'parity-probe-report.json').write_text(
        json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8'
    )
    print(report['status'])
    if ratios:
        print('ratios=' + ','.join(f'{x:.12g}' for x in ratios))
        print(f'max_relative_error={max(relative_errors):.12g}')
    if reasons:
        print('reasons=' + ','.join(reasons))
    return 0 if passed else 2


if __name__ == '__main__':
    raise SystemExit(main())
