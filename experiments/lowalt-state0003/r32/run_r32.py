#!/usr/bin/env python3
from __future__ import annotations

import csv
import ctypes
import hashlib
import importlib.util
import json
import math
import os
import shutil
import struct
import subprocess
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
MATRIX = HERE / 'r32-matrix.csv'
CONTRACT = HERE / 'r32-contract.json'
CAPTURE = HERE / 'r32_capture.gdb'
EXPECTED_BRANCH = 'execution/lowalt-state0003-r32-fresh-direct-subset-20260910'
AUTHORITY_COMMENT = 5623807626
OWNER_CLASSIFICATION_COMMENT = 5626431328
SOURCE_SHA = '999e47f4af4b5df6f85a6887fc105fc8f6e1a7cee89a3124f69ac8d8912c8e85'
PACKAGE_SPEC = 'rubin-libradtran=2.0.6=py312pl5321he9373c2_1'
PACKAGE_SHA = '9090033a39a7e963ecabb31d5cbd264330c64ec1c4cb5f44be2e70f10cbc54c2'
UVSPEC_SHA = '2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3'
R16_ARTIFACT_SHA = 'f9c014239fe7b9be99ee8727dbcaafe3b7b38e699e0b068e3a32d9d47ea3d481'
R16_MATRIX_SHA = '8cc873592650dadb2f3ed0f33fc41903c69e5788750a7cf29fd9921beb7edb9a'
R16_CONTRACT_SHA = 'd7ef6a8e68c436728f71eba6e616126deb9f2d485af4926da4b2a294384475ca'
STARS_MAIN_SHA = '1e74d0522f086dba634a587bb245c32bcd4fac60'


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def f32_from_hex(raw: str) -> float:
    b = bytes.fromhex(raw)
    if len(b) != 4:
        raise ValueError(('not-one-f32', len(b)))
    return struct.unpack('<f', b)[0]


def f32_plus_one_hex(raw: str) -> str:
    b = bytes.fromhex(raw)
    if len(b) % 4:
        raise ValueError(('bad-f32-array', len(b)))
    vals = struct.unpack('<' + 'f' * (len(b) // 4), b)
    return b''.join(struct.pack('<f', float(v) + 1.0) for v in vals).hex()


def api_get(url: str, token: str):
    req = urllib.request.Request(
        url,
        headers={
            'Accept': 'application/vnd.github+json',
            'Authorization': 'Bearer ' + token,
            'X-GitHub-Api-Version': '2022-11-28',
            'User-Agent': 'lowalt-state0003-r32',
        },
    )
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.load(r)


def load_core():
    p = Path(os.environ['R19_BASE_DRIVER_PATH'])
    spec = importlib.util.spec_from_file_location('r19_core_for_r32', p)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def load_rows(path: Path):
    with path.open(newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def validate_freeze(core, evidence: Path) -> tuple[list[dict], dict]:
    rows = load_rows(MATRIX)
    contract = json.loads(CONTRACT.read_text(encoding='utf-8'))
    if len(rows) != 10:
        raise RuntimeError(('r32-row-count', len(rows)))
    if [r['role'] for r in rows] != ['development'] * 8 + ['audit'] * 2:
        raise RuntimeError('r32-role-partition-drift')
    if len({r['identity'] for r in rows}) != 10:
        raise RuntimeError('r32-identity-duplicate')
    if any(not r['identity'].startswith('r32-fresh-') for r in rows):
        raise RuntimeError('r32-identity-namespace-drift')
    if any(r['identity'].startswith(('r29-', 'r31-')) for r in rows):
        raise RuntimeError('historical-identity-reuse')

    r16 = [dict(zip(core.HEADER, r)) for r in core.CASE_ROWS]
    for i, (new, old) in enumerate(zip(rows, r16)):
        if new['role'] != old['role']:
            raise RuntimeError(('role-derivation', i))
        if new['target_altitude_deg'] != old['target_altitude_deg'] or new['sza_deg'] != old['sza_deg']:
            raise RuntimeError(('geometry-derivation', i))
        if new['wavelength_nm'] != r16[(i + 3) % 10]['wavelength_nm']:
            raise RuntimeError(('wavelength-derivation', i))
        if new['observer_altitude_km'] != r16[(i + 5) % 10]['observer_altitude_km']:
            raise RuntimeError(('observer-derivation', i))
        expected_aer = 'DEFAULT' if old['aerosol_mode'] == 'OFF' else 'OFF'
        if new['aerosol_mode'] != expected_aer:
            raise RuntimeError(('aerosol-derivation', i))
        if abs((90.0 - float(new['target_altitude_deg'])) - float(new['sza_deg'])) > 1e-12:
            raise RuntimeError(('sza-altitude-relation', i))
        if not (0.30 <= float(new['target_altitude_deg']) < 5.0):
            raise RuntimeError(('low-alt-domain', i))
        if not (380 <= int(new['wavelength_nm']) <= 780):
            raise RuntimeError(('wavelength-domain', i))

    acc = contract['acceptance']
    required = {
        'developmentRows': 8,
        'auditRows': 2,
        'auditOpenRule': 'ONLY_AFTER_EXACT_8_OF_8_DEVELOPMENT_PASS',
        'ordinaryNullVsSdisortDTAUC': 'BYTE_EXACT',
        'ordinaryNullVsSdisortSSALB': 'BYTE_EXACT',
        'ordinaryNullVsSdisortZD': 'BYTE_EXACT',
        'nullDerivedVsSdisortUTAU': 'BYTE_EXACT_AFTER_EXACT_SOURCE_SETOUT_TRANSITION',
        'nullDerivedVsSdisortVN': 'BYTE_EXACT_AFTER_EXACT_SOURCE_PLUS_ONE_TRANSITION',
        'radiusKmF32': 6370.0,
        'nrefrac': 0,
        'ichap': 1,
        'ndenssza': 0,
        'facFac2Chp2ChAbsOrRelTolerance': 1e-10,
        'directFloat64AbsOrRelTolerance': 1e-12,
    }
    for k, v in required.items():
        if acc.get(k) != v:
            raise RuntimeError(('contract-drift', k, acc.get(k), v))
    if contract.get('authorityComment') != AUTHORITY_COMMENT:
        raise RuntimeError('authority-comment-drift')
    if contract.get('sourceEntitySha256') != SOURCE_SHA or contract.get('uvspecSha256') != UVSPEC_SHA:
        raise RuntimeError('source-runtime-contract-drift')
    if contract.get('packageSpec') != PACKAGE_SPEC or contract.get('packageSha256') != PACKAGE_SHA:
        raise RuntimeError('package-contract-drift')
    if contract.get('r16MatrixSha256') != R16_MATRIX_SHA or contract.get('r16ContractSha256') != R16_CONTRACT_SHA:
        raise RuntimeError('r16-contract-binding-drift')
    if contract.get('r16ImmutableArtifactSha256') != R16_ARTIFACT_SHA:
        raise RuntimeError('r16-artifact-binding-drift')
    if contract.get('productionFloorDeg') != 5.0 or not str(contract.get('productionBelowFloor', '')).startswith('FAIL_CLOSED'):
        raise RuntimeError('production-boundary-drift')
    if contract.get('generalNullVsSdisortEquivalenceClaimed') is not False:
        raise RuntimeError('general-equivalence-overclaim')

    r16_matrix = Path(os.environ['R16_MATRIX_PATH'])
    r16_contract = Path(os.environ['R16_CONTRACT_PATH'])
    if sha256(r16_matrix) != R16_MATRIX_SHA or sha256(r16_contract) != R16_CONTRACT_SHA:
        raise RuntimeError('immutable-r16-bytes-drift')
    if r16_matrix.read_text(encoding='utf-8').splitlines()[1:] != [','.join(r) for r in core.CASE_ROWS]:
        raise RuntimeError('r19-core-vs-r16-artifact-matrix-drift')

    frozen = {
        'schemaVersion': 1,
        'classification': 'LOWALT_R32_EXACT_PRE_RESULT_FREEZE_BOUND',
        'branch': os.environ['GITHUB_REF_NAME'],
        'headSha': os.environ['GITHUB_SHA'],
        'matrixSha256': sha256(MATRIX),
        'contractSha256': sha256(CONTRACT),
        'captureSha256': sha256(CAPTURE),
        'runnerSha256': sha256(Path(__file__)),
        'r16ArtifactZipSha256': sha256(Path(os.environ['R16_ARTIFACT_ZIP'])),
        'r16MatrixSha256': sha256(r16_matrix),
        'r16ContractSha256': sha256(r16_contract),
        'developmentIdentities': [r['identity'] for r in rows[:8]],
        'sealedAuditIdentities': [r['identity'] for r in rows[8:]],
        'auditOpened': False,
        'scientificResultOpened': False,
        'postResultRetuning': 'FORBIDDEN',
        'protectedResidualSelection': False,
        'taylorJerusalemSelection': False,
        'productionBelow5Deg': 'FAIL_CLOSED_UNCHANGED',
    }
    write_json(evidence / 'freeze-receipt.json', frozen)
    return rows, contract


def render_input(data: Path, row: dict, mode: str, case: Path) -> Path:
    atm = data / 'atmmod/afglus.dat'
    site = float(row['observer_altitude_km'])
    levels = []
    for raw in atm.read_text(encoding='utf-8').splitlines():
        q = raw.strip()
        if q and not q.startswith('#'):
            levels.append(float(q.split()[0]))
    if not (len(levels) > 2 and all(levels[i] > levels[i + 1] for i in range(len(levels) - 1))):
        raise RuntimeError('afglus-grid-order')
    grid = [site, *sorted(z for z in levels if z > site)]
    if not all(grid[i] < grid[i + 1] for i in range(len(grid) - 1)):
        raise RuntimeError('constructed-grid-order')
    lines = [
        f'data_files_path {atm.parent.parent}',
        f'atmosphere_file {atm}',
        'source solar',
        'mol_abs_param crs',
        f'wavelength {int(row["wavelength_nm"])} {int(row["wavelength_nm"])}',
        f'sza {float(row["sza_deg"]):.8f}',
        'atm_z_grid ' + ' '.join(f'{z:.6f}' for z in grid),
        'zout 0.000000',
        'albedo 0.15000000',
    ]
    if row['aerosol_mode'] == 'DEFAULT':
        lines.insert(4, 'aerosol_default')
    elif row['aerosol_mode'] != 'OFF':
        raise RuntimeError(('bad-aerosol-mode', row['aerosol_mode']))
    if mode == 'sdisort':
        lines += ['rte_solver sdisort', 'sdisort nscat 1']
    elif mode == 'null':
        lines += ['rte_solver null']
    else:
        raise RuntimeError(('bad-mode', mode))
    lines += ['output_quantity transmittance', 'output_user lambda edir', 'quiet']
    text = '\n'.join(lines) + '\n'
    low = text.lower()
    for token in ('mystic', 'aerosol_set_tau', 'nrefrac ', 'refraction ', 'taylor', 'jerusalem', 'protected'):
        if token in low:
            raise RuntimeError(('forbidden-input-token', token))
    p = case / f'{mode}.inp'
    p.write_text(text, encoding='utf-8')
    return p


def nm_symbols(uvspec: Path, nm: Path, evidence: Path) -> dict[str, str]:
    txt = subprocess.check_output([str(nm), '-an', str(uvspec)], text=True, errors='replace')
    (evidence / 'nm-all.txt').write_text(txt, encoding='utf-8')
    names = {parts[-1] for line in txt.splitlines() if len((parts := line.split())) >= 3}
    def one(*choices):
        got = [x for x in choices if x in names]
        if len(got) != 1:
            raise RuntimeError(('symbol-resolution', choices, got))
        return got[0]
    out = {
        'setup': one('setup_and_call_solver'),
        'optical': one('optical_properties'),
        'sdisort': one('sdisort', 'sdisort_'),
        'setout': one('setout', 'setout_'),
    }
    write_json(evidence / 'r32-symbols.json', out)
    return out


def gdb_capture(uvspec: Path, gdb: Path, symbols: dict[str, str], inp: Path, outdir: Path, role: str, mapping: Path | None) -> int:
    outdir.mkdir(parents=True, exist_ok=False)
    env = os.environ.copy()
    env.update({
        'R32_CAPTURE_ROLE': role,
        'R32_CASE_DIR': str(outdir),
        'R32_SETUP_SYMBOL': symbols['setup'],
        'R32_OPTICAL_SYMBOL': symbols['optical'],
        'R32_SDISORT_SYMBOL': symbols['sdisort'],
        'R32_SETOUT_SYMBOL': symbols['setout'],
    })
    if mapping is not None:
        env['R32_MAPPING_PATH'] = str(mapping)
    cmd = [
        str(gdb), '-q', '-batch',
        '-ex', f'file {uvspec}',
        '-ex', f'break {symbols["setup"]}',
        '-ex', f'run < {inp} > {outdir / "inferior.stdout"} 2> {outdir / "inferior.stderr"}',
        '-x', str(CAPTURE),
    ]
    with (outdir / 'gdb.log').open('w', encoding='utf-8') as f:
        proc = subprocess.run(cmd, env=env, stdout=f, stderr=subprocess.STDOUT)
    (outdir / 'gdb-exit-code.txt').write_text(str(proc.returncode) + '\n', encoding='utf-8')
    return proc.returncode


def raws(candidates) -> list[str]:
    return [x['rawHex'] for x in candidates if 'rawHex' in x]


def has_raw(candidates, target: str) -> bool:
    return target in raws(candidates)


def compare_pair(case: Path, row: dict, role: str) -> dict:
    sd = json.loads((case / 'sdisort' / 'sdisort-entry.json').read_text())
    se = json.loads((case / 'sdisort' / 'setout-entry.json').read_text())
    sc = json.loads((case / 'sdisort' / 'common-route.json').read_text())
    nu = json.loads((case / 'null' / 'null-common.json').read_text())
    nc = json.loads((case / 'null' / 'common-route.json').read_text())

    checks = {}
    checks['commonPcOffsetExact'] = sc['postOpticalOffsetFromSetup'] == nc['postOpticalOffsetFromSetup']
    checks['commonPreMutationBoth'] = not sc['solverSpecificMutationExecutedBeforeCapture'] and not nc['solverSpecificMutationExecutedBeforeCapture']
    checks['shapeExact'] = sd['nlyr'] == nu['nlyr'] and sd['ntau'] == nu['nzout'] == 1
    checks['dtaucByteExact'] = has_raw(nu['dtaucCandidates'], sd['dtaucHex']) and se['dtaucHex'] == sd['dtaucHex']
    checks['ssalbByteExact'] = has_raw(nu['ssalbCandidates'], sd['ssalbHex'])
    checks['zdByteExact'] = has_raw(nu['zdCandidates'], sd['zdHex']) and se['zdHex'] == sd['zdHex']
    checks['setoutPreUtauFromNullByteExact'] = has_raw(nu['utauCandidates'], se['utauPreHex'])
    checks['setoutFrozenZoutZero'] = all(v == 0.0 for v in struct.unpack('<' + 'f' * (len(bytes.fromhex(se['zoutHex'])) // 4), bytes.fromhex(se['zoutHex'])))
    checks['utauExactSourceTransitionObserved'] = checks['dtaucByteExact'] and checks['zdByteExact'] and checks['setoutPreUtauFromNullByteExact'] and sd['setoutEntryCapturedBeforeSdisort']
    transformed_vn = [f32_plus_one_hex(x) for x in raws(nu['refindCandidates'])]
    checks['vnPlusOneByteExact'] = sd['vnHex'] in transformed_vn
    checks['fbeamBitExact'] = nu['fbeamHex'] == sd['fbeamHex']
    checks['umu0BitExact'] = nu['umu0Hex'] == sd['umu0Hex']
    checks['newgeoExact'] = nu['newgeo'] == sd['newgeo'] == 1
    checks['spherExactSolverTransition'] = nu['spher'] == 0 and sd['spher'] == 1
    checks['planckExact'] = nu['planck'] == sd['planck'] == 0
    checks['radiusExact'] = f32_from_hex(sd['radiusHex']) == 6370.0
    checks['nrefracExact'] = sd['nrefrac'] == 0
    checks['ichapExact'] = sd['ichap'] == 1
    checks['ndensszaExact'] = sd['ndenssza'] == 0
    checks['sdisortBodyNotExecuted'] = sd['bodyInstructionExecutedAfterEntryCapture'] is False
    checks['finiteFbeamUmu0'] = math.isfinite(f32_from_hex(sd['fbeamHex'])) and math.isfinite(f32_from_hex(sd['umu0Hex']))
    passed = all(checks.values())
    out = {
        'schemaVersion': 1,
        'identity': row['identity'],
        'role': role,
        'checks': checks,
        'pass': passed,
        'nlyr': sd['nlyr'],
        'nullCandidateCounts': {
            'dtauc': len(raws(nu['dtaucCandidates'])),
            'ssalb': len(raws(nu['ssalbCandidates'])),
            'zd': len(raws(nu['zdCandidates'])),
            'utau': len(raws(nu['utauCandidates'])),
            'refind': len(raws(nu['refindCandidates'])),
        },
        'claimBoundary': 'direct-subset NULL ordinary state -> exact source transition -> SDISORT entry only; no general NULL-vs-SDISORT equivalence',
    }
    write_json(case / 'comparison.json', out)
    return out


def run_pair(root: Path, row: dict, uvspec: Path, data: Path, gdb: Path, symbols: dict[str, str], role: str) -> dict:
    case = root / row['identity']
    case.mkdir(parents=True, exist_ok=False)
    write_json(case / 'row.json', row)
    null_inp = render_input(data, row, 'null', case)
    sdis_inp = render_input(data, row, 'sdisort', case)
    if gdb_capture(uvspec, gdb, symbols, sdis_inp, case / 'sdisort', 'sdisort', None) != 0:
        raise RuntimeError(('sdisort-capture-failed', row['identity']))
    mapping = case / 'sdisort' / 'abi-mapping.json'
    if not mapping.is_file():
        raise RuntimeError(('mapping-missing', row['identity']))
    if gdb_capture(uvspec, gdb, symbols, null_inp, case / 'null', 'null', mapping) != 0:
        raise RuntimeError(('null-capture-failed', row['identity']))
    return compare_pair(case, row, role)


def source_order_stress(core, evidence: Path, stress_case: Path, fc_cmd: str) -> dict:
    lib = core.prepare_reference(evidence, fc_cmd)
    sd = json.loads((stress_case / 'sdisort' / 'sdisort-entry.json').read_text())
    scratch = evidence / 'source-order-stress'
    scratch.mkdir(exist_ok=False)
    (scratch / 'dtauc_f32le.bin').write_bytes(bytes.fromhex(sd['dtaucHex']))
    (scratch / 'zd_f32le.bin').write_bytes(bytes.fromhex(sd['zdHex']))
    (scratch / 'vn_f32le.bin').write_bytes(bytes.fromhex(sd['vnHex']))
    radius = f32_from_hex(sd['radiusHex'])
    radius_second = (radius * 1.0e5) * 1.0e-5
    m = {
        'nlyr': sd['nlyr'],
        'umu0F32': f32_from_hex(sd['umu0Hex']),
        'radiusKmF32': radius_second,
    }
    vals = core.reference_values(lib, scratch, m)
    for name in ('fac', 'fac2', 'chp2', 'ch'):
        if not vals[name] or not all(math.isfinite(float(x)) for x in vals[name]):
            raise RuntimeError(('nonfinite-source-order', name))
    serial = 0.0
    for x in vals['dtauc']:
        serial += float(x)
    report = {
        'schemaVersion': 1,
        'classification': 'R32_MECHANICAL_SOURCE_ORDER_REFERENCE_EXECUTED_CLEAN',
        'sourceEntitySha256': SOURCE_SHA,
        'nlyr': sd['nlyr'],
        'radiusEntryF32': radius,
        'radiusAtSecondGeofastF64': radius_second,
        'serialReal8Tauc': serial,
        'finiteFacFac2Chp2Ch': True,
        'geofastChpman2ReferenceLibrarySha256': sha256(lib),
        'opPathFastAndChapmanExecutedByExactSourceReference': True,
        'scientificIdentityUsed': False,
        'scientificResultOpened': False,
    }
    write_json(evidence / 'source-order-stress.json', report)
    return report


def fresh_control_fence(evidence: Path) -> dict:
    gh = os.environ['GH_TOKEN']
    stars_token = os.environ['STARSVISIBILITY_READ_TOKEN']
    repo = os.environ['GITHUB_REPOSITORY']
    runid = int(os.environ['GITHUB_RUN_ID'])
    issue = api_get(f'https://api.github.com/repos/{repo}/issues/60', gh)
    count = int(issue['comments'])
    page = (count - 1) // 100 + 1
    tail = api_get(f'https://api.github.com/repos/{repo}/issues/60/comments?per_page=100&page={page}', gh)
    lowalt = [r for r in tail if int(r['id']) >= AUTHORITY_COMMENT and ('LOWALT' in r.get('body', '').upper() or 'LOW-ALTITUDE' in r.get('body', '').upper())]
    forbidden_new = []
    for r in lowalt:
        cid = int(r['id'])
        if cid in (AUTHORITY_COMMENT, OWNER_CLASSIFICATION_COMMENT):
            continue
        first = (r.get('body') or '').splitlines()[0].upper()
        if first.startswith('COORDINATOR::LOWALT') or 'WRITE_QUIET_BEGIN' in first:
            forbidden_new.append({'id': cid, 'first': first})
    main = api_get(f'https://api.github.com/repos/{repo}/branches/main', gh)['commit']['sha']
    stars = api_get('https://api.github.com/repos/search-maker/starsvisibility/branches/main', stars_token)['commit']['sha']
    other = {}
    for status in ('in_progress', 'queued'):
        rs = api_get(f'https://api.github.com/repos/{repo}/actions/runs?status={status}&per_page=100', gh)['workflow_runs']
        other[status] = [
            {'id': int(r['id']), 'name': r.get('name'), 'head_branch': r.get('head_branch'), 'head_sha': r.get('head_sha')}
            for r in rs if int(r['id']) != runid
        ]
    out = {
        'schemaVersion': 1,
        'issue60CommentCount': count,
        'latestIssue60CommentId': int(tail[-1]['id']) if tail else None,
        'newerLowAltCoordinatorRestrictions': forbidden_new,
        'twilightMain': main,
        'starsMain': stars,
        'otherMutableActions': other,
        'activeActionAloneIsNotBlocker': True,
        'productionBelow5Deg': 'FAIL_CLOSED_UNCHANGED',
    }
    write_json(evidence / 'fresh-pre-development-fence.json', out)
    if forbidden_new:
        raise RuntimeError(('newer-lowalt-authority', forbidden_new))
    if stars != STARS_MAIN_SHA:
        raise RuntimeError(('stars-main-drift', stars, STARS_MAIN_SHA))
    return out


def manifest(root: Path) -> None:
    lines = []
    for p in sorted(x for x in root.rglob('*') if x.is_file() and x.name != 'manifest.sha256'):
        lines.append(f'{sha256(p)}  {p.relative_to(root).as_posix()}')
    (root / 'manifest.sha256').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main() -> int:
    if os.environ.get('GITHUB_REF_NAME') != EXPECTED_BRANCH:
        raise RuntimeError(('branch-drift', os.environ.get('GITHUB_REF_NAME')))
    evidence = Path(os.environ['R32_EVIDENCE_DIR'])
    if evidence.exists():
        raise RuntimeError(('stale-workspace', str(evidence)))
    evidence.mkdir(parents=True)
    (evidence / 'cases').mkdir()
    core = load_core()
    rows, contract = validate_freeze(core, evidence)
    uvspec, data, gdb, nm, fc_cmd = core.bind_runtime(evidence)
    symbols = nm_symbols(uvspec, nm, evidence)

    source_root = Path(os.environ['SOURCE_ROOT'])
    solve = source_root / 'src/solve_rte.c'
    dps = source_root / 'libsrc_f/dpsdisort.f'
    dpmisc = source_root / 'libsrc_f/dpmisc.f'
    for p in (solve, dps, dpmisc):
        if not p.is_file():
            raise RuntimeError(('missing-exact-source-file', str(p)))
    solve_text = solve.read_text(encoding='utf-8', errors='strict')
    for anchor in (
        'status = optical_properties (input, output, 0.0, ir, iv1, iv2, ib, verbose, skip_optical_properties)',
        'F77_FUNC (setout, SETOUT)',
        'case SOLVER_NULL:',
        'output->atm.microphys.refind[iv][lu] += 1.',
    ):
        if anchor not in solve_text:
            raise RuntimeError(('source-anchor-drift', anchor))
    dps_text = dps.read_text(encoding='utf-8', errors='strict').upper()
    for anchor in ('ABSCUT', 'LYRCUT', 'DEXP', 'CHPMAN2'):
        if anchor not in dps_text:
            raise RuntimeError(('dpsdisort-anchor-drift', anchor))
    write_json(evidence / 'source-anchor-stress.json', {
        'solveRteSha256': sha256(solve),
        'dpsdisortSha256': sha256(dps),
        'dpmiscSha256': sha256(dpmisc),
        'requiredAnchorsPresent': True,
        'protectedTaylorJerusalemPathUsed': False,
    })

    stress_spec = contract['mechanicalStress']
    stress_row = {
        'identity': stress_spec['identity'],
        'role': stress_spec['role'],
        'target_altitude_deg': stress_spec['target_altitude_deg'],
        'sza_deg': stress_spec['sza_deg'],
        'wavelength_nm': stress_spec['wavelength_nm'],
        'observer_altitude_km': stress_spec['observer_altitude_km'],
        'aerosol_mode': stress_spec['aerosol_mode'],
    }
    stress_result = run_pair(evidence / 'cases', stress_row, uvspec, data, gdb, symbols, 'mechanical')
    if not stress_result['pass']:
        write_json(evidence / 'pre-run-stress.json', {'classification': 'R32_PRE_RUN_EXACT_EXECUTABLE_STRESS_FAIL', 'result': stress_result, 'developmentOpened': False, 'auditOpened': False})
        manifest(evidence)
        return 31
    source_order = source_order_stress(core, evidence, evidence / 'cases' / stress_row['identity'], fc_cmd)
    fence = fresh_control_fence(evidence)
    pre = {
        'schemaVersion': 1,
        'classification': 'R32_PRE_RUN_EXACT_EXECUTABLE_STRESS_PASS',
        'captureStress': stress_result,
        'sourceOrderStress': source_order,
        'fence': fence,
        'resultBlindReceiptPersistedBeforeDevelopment': True,
        'developmentOpened': False,
        'auditOpened': False,
    }
    write_json(evidence / 'pre-run-stress.json', pre)
    with (evidence / 'pre-run-stress.json').open('rb') as f:
        os.fsync(f.fileno())

    dev_results = []
    for row in rows[:8]:
        result = run_pair(evidence / 'cases', row, uvspec, data, gdb, symbols, 'development')
        dev_results.append(result)
        if not result['pass']:
            write_json(evidence / 'development-summary.json', {
                'classification': 'LOWALT_R32_DEVELOPMENT_NOT_PASS',
                'failedIdentity': row['identity'],
                'developmentOpenedCount': len(dev_results),
                'auditOpened': False,
                'results': dev_results,
                'retuningPerformed': False,
                'productionBelow5Deg': 'FAIL_CLOSED_UNCHANGED',
            })
            manifest(evidence)
            return 41
    write_json(evidence / 'development-summary.json', {
        'classification': 'LOWALT_R32_DEVELOPMENT_PASS_8_OF_8',
        'developmentOpenedCount': 8,
        'allPass': True,
        'auditOpened': False,
        'results': dev_results,
        'retuningPerformed': False,
        'productionBelow5Deg': 'FAIL_CLOSED_UNCHANGED',
    })

    audit_results = []
    for row in rows[8:]:
        result = run_pair(evidence / 'cases', row, uvspec, data, gdb, symbols, 'audit')
        audit_results.append(result)
        if not result['pass']:
            write_json(evidence / 'audit-summary.json', {
                'classification': 'LOWALT_R32_SEALED_AUDIT_NOT_PASS',
                'auditOpenedOnlyAfterDevelopment8Of8': True,
                'failedIdentity': row['identity'],
                'auditOpenedCount': len(audit_results),
                'results': audit_results,
                'retuningPerformed': False,
                'productionBelow5Deg': 'FAIL_CLOSED_UNCHANGED',
            })
            manifest(evidence)
            return 51
    write_json(evidence / 'audit-summary.json', {
        'classification': 'LOWALT_R32_SEALED_AUDIT_PASS_2_OF_2',
        'auditOpenedOnlyAfterDevelopment8Of8': True,
        'auditOpenedCount': 2,
        'allPass': True,
        'results': audit_results,
        'retuningPerformed': False,
        'productionBelow5Deg': 'FAIL_CLOSED_UNCHANGED_PENDING_SEPARATE_PRODUCTION_TRANSITION',
    })
    write_json(evidence / 'completion-receipt.json', {
        'schemaVersion': 1,
        'classification': 'LOWALT_R32_FROZEN_DIRECT_SUBSET_GATE_PASS_8_DEV_PLUS_2_SEALED_AUDIT',
        'developmentPass': '8/8',
        'sealedAuditPass': '2/2',
        'generalNullVsSdisortEquivalenceClaimed': False,
        'productionMutationPerformed': False,
        'productionBelow5Deg': 'FAIL_CLOSED_UNCHANGED_PENDING_SEPARATE_AUTHORITY',
        'protectedScienceOpened': False,
        'taylorJerusalemUsed': False,
        'retuningPerformed': False,
    })
    manifest(evidence)
    return 0


if __name__ == '__main__':
    try:
        rc = main()
    except Exception as exc:
        e = Path(os.environ.get('R32_EVIDENCE_DIR', '/tmp/r32-evidence'))
        e.mkdir(parents=True, exist_ok=True)
        write_json(e / 'fatal-barrier.json', {
            'classification': 'LOWALT_R32_MECHANICAL_OR_GOVERNANCE_BARRIER',
            'errorType': type(exc).__name__,
            'error': str(exc),
            'auditOpened': False,
            'retuningPerformed': False,
            'productionBelow5Deg': 'FAIL_CLOSED_UNCHANGED',
        })
        manifest(e)
        raise
    raise SystemExit(rc)
