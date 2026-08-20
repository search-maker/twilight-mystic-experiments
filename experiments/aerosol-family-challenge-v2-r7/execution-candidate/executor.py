from __future__ import annotations
import hashlib, importlib.util, json, subprocess
from pathlib import Path
from typing import Any, Callable


class ExecutionRefusal(RuntimeError):
    pass


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ExecutionRefusal(f'cannot load module: {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run(command: list[str], text: str, cwd: Path, timeout: int) -> dict[str, Any]:
    try:
        result = subprocess.run(command, input=text, text=True, capture_output=True, cwd=cwd, timeout=timeout, check=False)
        return {'exitCode': result.returncode, 'timedOut': False, 'stdout': result.stdout, 'stderr': result.stderr}
    except subprocess.TimeoutExpired as exc:
        return {'exitCode': None, 'timedOut': True, 'stdout': exc.stdout or '', 'stderr': exc.stderr or ''}


def _parse_spectrum(raw: bytes) -> tuple[list[float], list[float]]:
    wavelengths: list[float] = []
    values: list[float] = []
    for line in raw.decode('utf-8').splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            wavelengths.append(float(parts[0]))
            values.append(float(parts[-1]))
        except ValueError:
            continue
    return wavelengths, values


def execute_case(
    repository_root: Path,
    manifest_path: Path,
    guard_report_path: Path,
    runtime_report_path: Path,
    case_id: str,
    data_dir: Path,
    output_root: Path,
    uvspec: Path,
    timeout_seconds: int = 1800,
    allow_execution: bool = False,
    runner: Callable[[list[str], str, Path, int], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if not allow_execution:
        raise ExecutionRefusal('--allow-execution required')
    base = repository_root / 'experiments/aerosol-family-challenge-v2-r7'
    core = _load_module('afc2_exec_core', base / 'core.py')
    # adapter imports a module literally named core.
    import sys
    sys.modules['core'] = core
    adapter = _load_module('afc2_exec_adapter', base / 'adapter.py')
    derived = _load_module('afc2_exec_derived', base / 'derived_channels.py')
    manifest = json.loads(manifest_path.read_text())
    core.validate_manifest(manifest)
    guard = json.loads(guard_report_path.read_text())
    if guard.get('status') != 'EXACT_ONE_USE_AEROSOL_FAMILY_V2_R7_DISPATCH_AUTHORIZED' or guard.get('solverExecutionPermittedNow') is not True:
        raise ExecutionRefusal('execution guard did not authorize solver')
    if guard.get('manifestRawSha256') != _sha(manifest_path):
        raise ExecutionRefusal('guard/manifest hash drift')
    rows = [c for c in manifest['cases'] if c['caseId'] == case_id]
    if len(rows) != 1:
        raise ExecutionRefusal('case not uniquely present in frozen manifest')
    case = rows[0]
    runtime = json.loads(runtime_report_path.read_text())
    if runtime.get('scientificSolverExecuted') is not False:
        raise ExecutionRefusal('runtime identity report must be pre-solver and state scientificSolverExecuted=false')
    required_runtime = manifest['sourceBindings']['runtimeLock']
    for key in ('uvspecSha256','uvspecHelpSha256','libRadtranDataTreeSha256','atmosphereSha256','rawSha256'):
        runtime_key = 'runtimeLockRawSha256' if key == 'rawSha256' else key
        if runtime.get(runtime_key) != required_runtime.get(key):
            raise ExecutionRefusal(f'runtime identity drift: {runtime_key}')
    if _sha(uvspec) != required_runtime['uvspecSha256']:
        raise ExecutionRefusal('uvspec byte hash drift')

    case_dir = output_root / case_id
    case_dir.mkdir(parents=True, exist_ok=False)
    text = adapter.render_case_input(case, data_dir, repository_root, output_root)
    case_inp = case_dir / 'case.inp'
    case_inp.write_text(text, encoding='utf-8', newline='\n')
    adapter.assert_exact_aerosol_state(case_inp.read_text(), case)
    adapter.assert_exact_spectrum_surface(case_inp.read_text())
    (case_dir / 'runtime-report.json').write_bytes(runtime_report_path.read_bytes())
    (case_dir / 'randomseed').write_text(f"{case['seed']}\n", encoding='utf-8')
    grid = base / 'wavelength-grid-1nm.dat'
    (case_dir / 'wavelength-grid-1nm.dat').write_bytes(grid.read_bytes())
    prepared = {
        'schemaVersion': 1,
        'stageId': 'aerosol-family-challenge-v2-r7-prepared',
        'caseId': case_id,
        'groupId': case['groupId'],
        'analysisCellId': case['analysisCellId'],
        'replicate': case['replicate'],
        'seed': case['seed'],
        'photonHistories': case['photonHistories'],
        'aerosolFamily': case['aerosolFamily'],
        'aerosolSeason': case['aerosolSeason'],
        'caseInpSha256': _sha(case_inp),
        'manifestRawSha256': _sha(manifest_path),
        'guardReportRawSha256': _sha(guard_report_path),
    }
    (case_dir / 'prepared.json').write_text(json.dumps(prepared, indent=2, sort_keys=True) + '\n')

    run = runner or _run
    syntax = run([str(uvspec), '-c'], text, case_dir, 60)
    (case_dir / 'syntax-stdout.txt').write_text(str(syntax['stdout']))
    (case_dir / 'syntax-stderr.txt').write_text(str(syntax['stderr']))
    if syntax.get('timedOut') or syntax.get('exitCode') != 0:
        raise ExecutionRefusal('single syntax check failed')
    solver = run([str(uvspec)], text, case_dir, timeout_seconds)
    (case_dir / 'solver-stdout.txt').write_text(str(solver['stdout']))
    (case_dir / 'solver-stderr.txt').write_text(str(solver['stderr']))
    if solver.get('timedOut') or solver.get('exitCode') != 0:
        raise ExecutionRefusal('single solver execution failed')

    required = ('mc.flx.spc','mc.flx.std.spc','mc.rad.spc','mc.rad.std.spc')
    for name in required:
        path = case_dir / name
        if not path.is_file() or path.stat().st_size == 0:
            raise ExecutionRefusal(f'required raw output missing/empty: {name}')
    wl, rad = _parse_spectrum((case_dir / 'mc.rad.spc').read_bytes())
    derived.validate_raw_grid(wl, rad)
    std_wl, std_rad = _parse_spectrum((case_dir / 'mc.rad.std.spc').read_bytes())
    derived.validate_raw_grid(std_wl, std_rad)
    if any(abs(a-b) > derived.RAW_POINT_TOLERANCE_NM for a,b in zip(wl,std_wl)):
        raise ExecutionRefusal('radiance/std wavelength grids differ')
    channels = derived.derive_channels(wl, rad)
    marginal_mc = derived.marginal_mc_std_diagnostics(wl, rad, std_rad)
    raw_names = (
        'case.inp','prepared.json','runtime-report.json','randomseed',
        'syntax-stdout.txt','syntax-stderr.txt','solver-stdout.txt','solver-stderr.txt',
        'wavelength-grid-1nm.dat','mc.flx.spc','mc.flx.std.spc','mc.rad.spc','mc.rad.std.spc',
    )
    result = {
        'schemaVersion': 1,
        'stageId': 'aerosol-family-challenge-v2-r7',
        'status': 'COMPLETED',
        'caseId': case_id,
        'groupId': case['groupId'],
        'analysisCellId': case['analysisCellId'],
        'replicate': case['replicate'],
        'seed': case['seed'],
        'photonHistories': case['photonHistories'],
        'aerosolFamily': case['aerosolFamily'],
        'aerosolSeason': case['aerosolSeason'],
        'workflowRunAttempt': 1,
        'syntaxCheckCount': 1,
        'solverExecutionCount': 1,
        'retryPerformed': False,
        'resumePerformed': False,
        'githubRerun': False,
        'syntaxExitCode': 0,
        'solverExitCode': 0,
        'syntaxTimedOut': False,
        'solverTimedOut': False,
        'caseInpSha256': _sha(case_dir / 'case.inp'),
        'runtimeReportRawSha256': _sha(case_dir / 'runtime-report.json'),
        'radianceOutputSha256': _sha(case_dir / 'mc.rad.spc'),
        'stdRadianceOutputSha256': _sha(case_dir / 'mc.rad.std.spc'),
        'rawOutputNodeCount': len(wl),
        'channels': channels,
        'marginalMcStdDiagnostics': marginal_mc,
        'rawMemberSha256ByBasename': {name: _sha(case_dir / name) for name in raw_names},
    }
    result['contentSha256'] = hashlib.sha256(json.dumps(result, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    (case_dir / 'case-result.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    return result
