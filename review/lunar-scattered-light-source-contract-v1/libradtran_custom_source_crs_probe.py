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
    text = ''.join(f'{w:.6f} {f:.12e}\n' for w, f in zip(wavelengths, fluxes))
    path.write_text(text, encoding='utf-8')


def render_input(data_dir: Path, atmosphere: Path, source: Path) -> str:
    return '\n'.join([
        f'data_files_path {data_dir}',
        f'atmosphere_file {atmosphere}',
        f'source solar {source}',
        'mol_abs_param crs',
        'wavelength 380 780',
        'sza 0',
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
        w = float(fields[0])
        e = float(fields[1])
        if not math.isfinite(w) or not math.isfinite(e):
            raise ValueError('non-finite uvspec output')
        wavelengths.append(w)
        edir.append(e)
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
    except Exception as exc:  # report exact failure rather than hiding it
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

    wavelengths = [float(x) for x in contract['probe']['sourceWavelengthNm']]
    flux_a = [float(x) for x in contract['probe']['arms']['A']['sourceFluxValues']]
    flux_b = [float(x) for x in contract['probe']['arms']['B']['sourceFluxValues']]
    source_a = out_dir / 'source-a.dat'
    source_b = out_dir / 'source-b.dat'
    write_source(source_a, wavelengths, flux_a)
    write_source(source_b, wavelengths, flux_b)

    input_a = render_input(data_dir, atmosphere, source_a)
    input_b = render_input(data_dir, atmosphere, source_b)
    arm_a = run_arm(uvspec=uvspec, input_text=input_a, out_dir=out_dir, arm='a')
    arm_b = run_arm(uvspec=uvspec, input_text=input_b, out_dir=out_dir, arm='b')

    expected_ratio = float(contract['frozenDecisionRule']['expectedArmBToArmARatio'])
    tolerance = float(contract['frozenDecisionRule']['maximumAbsoluteRatioDeviation'])
    reasons: list[str] = []
    ratios: list[float] = []
    max_deviation = None

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
        if wa != wb:
            reasons.append('OUTPUT_WAVELENGTH_VECTOR_MISMATCH')
        elif len(ea) != len(eb) or not ea:
            reasons.append('OUTPUT_LENGTH_MISMATCH_OR_EMPTY')
        elif any((not math.isfinite(x) or x <= 0.0) for x in ea):
            reasons.append('ARM_A_EDIR_NOT_FINITE_STRICTLY_POSITIVE')
        elif any(not math.isfinite(x) for x in eb):
            reasons.append('ARM_B_EDIR_NOT_FINITE')
        else:
            ratios = [b / a for a, b in zip(ea, eb)]
            if any(not math.isfinite(x) for x in ratios):
                reasons.append('NONFINITE_SOURCE_AMPLITUDE_RATIO')
            else:
                max_deviation = max(abs(x - expected_ratio) for x in ratios)
                if max_deviation > tolerance:
                    reasons.append('SOURCE_AMPLITUDE_RATIO_OUTSIDE_FROZEN_TOLERANCE')

    passed = not reasons
    report = {
        'schemaVersion': 1,
        'contractId': contract['contractId'],
        'status': (
            'PASS_CUSTOM_SOURCE_WITH_CRS_CONSUMED_EXACT_RUNTIME'
            if passed else 'FAIL_CUSTOM_SOURCE_WITH_CRS_NOT_ADMITTED'
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
        'maximumAbsoluteRatioDeviationAllowed': tolerance,
        'observedRatios': ratios,
        'maximumAbsoluteRatioDeviationObserved': max_deviation,
        'reasons': reasons,
        'mysticExecuted': False,
        'realSkyDataOpened': False,
        'airLusiResidualOpened': False,
        'xshooterResidualOpened': False,
        'taylorOrJerusalemResidualUsed': False,
        'atmosphericScatteredMoonlightValidated': False,
        'productionAuthorized': False,
    }
    (out_dir / 'probe-report.json').write_text(
        json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8'
    )
    print(report['status'])
    if ratios:
        print(f'ratio_count={len(ratios)} max_abs_deviation={max_deviation:.12g}')
    if reasons:
        print('reasons=' + ','.join(reasons))
    return 0 if passed else 2


if __name__ == '__main__':
    raise SystemExit(main())
