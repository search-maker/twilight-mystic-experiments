#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
EXECUTION_MANIFEST = ROOT / 'full-spectrum-estimator-pilot-execution-manifest-v4.json'
NORMALIZER = ROOT / 'normalize_full_spectrum_estimator_pilot_results_v6.py'
GRID = ROOT / 'wavelength-grid-1nm.dat'
EXPECTED_GRID_SHA256 = '488f6bd90c35a6f5aeffe1ef230186ae87002d42747af4fe94f07d82c5eef692'
RENDERER_ID = 'public-tier1-full-spectrum-estimator-pilot-renderer-v5'

spec = importlib.util.spec_from_file_location('pilot_normalizer_v2', NORMALIZER)
if spec is None or spec.loader is None:
    raise RuntimeError('cannot load hardened normalizer')
norm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(norm)

PATH_PLACEHOLDERS = {
    'data_files_path': '${LIBRADTRAN_DATA}',
    'atmosphere_file': '${ATMOSPHERE_FILE}',
    'solar_flux': '${SOLAR_FLUX_FILE}',
    'wavelength_grid_file': '${WAVELENGTH_GRID_1NM}',
}

class RendererRefusal(RuntimeError):
    pass


def raw_sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def raw_sha256(path: Path) -> str:
    return raw_sha256_bytes(path.read_bytes())


def canonical_sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise RendererRefusal(f'expected JSON object: {path}')
    return value


def source_input_for_geometry(source_dir: Path, geometry_id: str) -> tuple[Path, bytes, str]:
    # Deliberately use the earliest immutable block. The hardened physical fingerprint
    # independently proves it belongs to the exact frozen geometry before reuse.
    zip_path = source_dir / f'{geometry_id}-b1.zip'
    if not zip_path.is_file():
        raise RendererRefusal(f'missing historical source ZIP: {zip_path}')
    with zipfile.ZipFile(zip_path) as zf:
        matches = [name for name in zf.namelist() if Path(name).name == 'input-resolved.txt']
        if len(matches) != 1:
            raise RendererRefusal(f'{zip_path.name}: expected exactly one input-resolved.txt')
        raw = zf.read(matches[0])
    return zip_path, raw, matches[0]


def rewrite_common_paths(line: str) -> str:
    parts = line.split()
    if not parts:
        return line
    key = parts[0]
    if key == 'data_files_path':
        return f'data_files_path {PATH_PLACEHOLDERS["data_files_path"]}'
    if key == 'atmosphere_file':
        return f'atmosphere_file {PATH_PLACEHOLDERS["atmosphere_file"]}'
    if key == 'source' and len(parts) >= 3 and parts[1] == 'solar':
        return f'source solar {PATH_PLACEHOLDERS["solar_flux"]}'
    return line


def render_template(source_raw: bytes, case: dict[str, Any]) -> bytes:
    geometry_id = case['geometryId']
    historical_fp = norm.physical_fingerprint(source_raw)
    expected_fp = norm.PHYSICAL_FINGERPRINTS.get(geometry_id)
    if expected_fp is None or historical_fp != expected_fp:
        raise RendererRefusal(f'historical source input fingerprint mismatch: {geometry_id} {historical_fp}')

    source_directives = norm.parse_directives(source_raw)
    # Compare historical physical state to the frozen case before any rewrite.
    # Override only identity/method fields temporarily so the hardened verifier can
    # validate the immutable physical inputs.
    physical_probe = dict(source_directives)
    physical_probe['seed'] = case['seed']
    physical_probe['mcPhotons'] = case['photonHistories']
    if case['method'] == 'alis-alt-importance':
        physical_probe['mcVroom'] = 'off'
        physical_probe['mcSpectralIsNm'] = case['numericalMethod']['mc_spectral_is_nm']
        physical_probe.pop('wavelengthGridFile', None)
    elif case['method'] == 'reference-vroom-1nm':
        physical_probe['mcVroom'] = 'on'
        physical_probe.pop('mcSpectralIsNm', None)
        physical_probe['wavelengthGridFile'] = '/tmp/wavelength-grid-1nm.dat'
    else:
        raise RendererRefusal(f'unknown method: {case["method"]}')
    norm.verify_input(physical_probe, case)

    lines = source_raw.decode('utf-8').splitlines()
    out: list[str] = []
    inserted_grid = False
    seen_seed = seen_basename = seen_vroom = False
    seen_spectral = False
    for original in lines:
        parts = original.split()
        if not parts:
            out.append(original)
            continue
        key = parts[0]
        line = rewrite_common_paths(original)
        if key == 'mc_randomseed':
            line = f'mc_randomseed {case["seed"]}'
            seen_seed = True
        elif key == 'mc_basename':
            line = f'mc_basename ${{OUTPUT_DIR}}/{case["caseId"]}/mc'
            seen_basename = True
        elif key == 'mc_vroom':
            line = f'mc_vroom {case["numericalMethod"]["mc_vroom"]}'
            seen_vroom = True
        elif key == 'mc_spectral_is':
            seen_spectral = True
            if case['method'] == 'reference-vroom-1nm':
                continue
            line = f'mc_spectral_is {case["numericalMethod"]["mc_spectral_is_nm"]:.1f}'
        elif key == 'wavelength_grid_file':
            # Historical ALIS inputs must not supply one. Refuse rather than silently
            # accepting a preexisting method change.
            raise RendererRefusal(f'historical source unexpectedly contains wavelength_grid_file: {geometry_id}')
        elif key == 'wavelength' and case['method'] == 'reference-vroom-1nm':
            out.append(f'wavelength_grid_file {PATH_PLACEHOLDERS["wavelength_grid_file"]}')
            inserted_grid = True
        out.append(line)

    if not (seen_seed and seen_basename and seen_vroom and seen_spectral):
        raise RendererRefusal(f'historical source lacks required numerical directives: {geometry_id}')
    if case['method'] == 'reference-vroom-1nm' and not inserted_grid:
        raise RendererRefusal('failed to insert exact 1-nm grid directive')
    if case['method'] == 'alis-alt-importance' and inserted_grid:
        raise RendererRefusal('ALIS case unexpectedly inserted a wavelength grid')

    text = '\n'.join(out) + '\n'
    return text.encode('utf-8')


def resolve_template(
    template_raw: bytes,
    *,
    lib_radtran_data: Path,
    atmosphere_file: Path,
    solar_flux_file: Path,
    wavelength_grid_file: Path,
    output_dir: Path,
) -> bytes:
    text = template_raw.decode('utf-8')
    substitutions = {
        '${LIBRADTRAN_DATA}': str(lib_radtran_data.resolve()),
        '${ATMOSPHERE_FILE}': str(atmosphere_file.resolve()),
        '${SOLAR_FLUX_FILE}': str(solar_flux_file.resolve()),
        '${WAVELENGTH_GRID_1NM}': str(wavelength_grid_file.resolve()),
        '${OUTPUT_DIR}': str(output_dir.resolve()),
    }
    for token, value in substitutions.items():
        text = text.replace(token, value)
    if '${' in text:
        raise RendererRefusal('unresolved placeholder remains')
    return text.encode('utf-8')


def render_all(
    execution_manifest_path: Path,
    source_dir: Path,
    output_dir: Path,
    lib_radtran_data: Path,
    atmosphere_file: Path,
    solar_flux_file: Path,
    wavelength_grid_file: Path,
) -> dict[str, Any]:
    manifest = load(execution_manifest_path)
    supplied = manifest.get('manifestSha256')
    if supplied != norm.EXEC_SHA or norm.canon({k:v for k,v in manifest.items() if k != 'manifestSha256'}) != supplied:
        raise RendererRefusal('execution manifest identity/self-hash mismatch')
    if raw_sha256(wavelength_grid_file) != EXPECTED_GRID_SHA256:
        raise RendererRefusal('1-nm wavelength grid bytes drift')

    output_dir.mkdir(parents=True, exist_ok=False)
    rows = []
    source_cache: dict[str, tuple[Path, bytes, str]] = {}
    for case in manifest['cases']:
        geometry_id = case['geometryId']
        if geometry_id not in source_cache:
            source_cache[geometry_id] = source_input_for_geometry(source_dir, geometry_id)
        source_zip, source_raw, source_member = source_cache[geometry_id]
        template_raw = render_template(source_raw, case)
        resolved_raw = resolve_template(
            template_raw,
            lib_radtran_data=lib_radtran_data,
            atmosphere_file=atmosphere_file,
            solar_flux_file=solar_flux_file,
            wavelength_grid_file=wavelength_grid_file,
            output_dir=output_dir,
        )
        norm.verify_exact_directive_surface(resolved_raw, case)
        directives = norm.parse_directives(resolved_raw)
        norm.verify_input(directives, case)
        fingerprint = norm.physical_fingerprint(resolved_raw)
        expected_fp = norm.PHYSICAL_FINGERPRINTS[geometry_id]
        if fingerprint != expected_fp:
            raise RendererRefusal(f'rendered physical fingerprint drift: {case["caseId"]}')
        if case['method'] == 'reference-vroom-1nm':
            if raw_sha256(wavelength_grid_file) != case['numericalMethod']['wavelengthGridRawSha256']:
                raise RendererRefusal('case-bound VROOM grid hash mismatch')
        case_dir = output_dir / case['caseId']
        case_dir.mkdir()
        template_path = case_dir / 'input-template.txt'
        resolved_path = case_dir / 'input-resolved-review.txt'
        template_path.write_bytes(template_raw)
        resolved_path.write_bytes(resolved_raw)
        rows.append({
            'caseId': case['caseId'],
            'geometryId': geometry_id,
            'method': case['method'],
            'seed': case['seed'],
            'photonHistories': case['photonHistories'],
            'importanceCenterNm': case['numericalMethod'].get('mc_spectral_is_nm'),
            'historicalSourceZip': str(source_zip),
            'historicalSourceZipSha256': raw_sha256(source_zip),
            'historicalSourceInputMember': source_member,
            'historicalSourceInputSha256': raw_sha256_bytes(source_raw),
            'physicalFingerprintSha256': fingerprint,
            'inputTemplateSha256': raw_sha256_bytes(template_raw),
            'inputResolvedReviewSha256': raw_sha256_bytes(resolved_raw),
        })

    if len(rows) != 44 or len({r['caseId'] for r in rows}) != 44:
        raise RendererRefusal('renderer did not produce exact 44-case universe')
    report = {
        'schemaVersion': 1,
        'rendererId': RENDERER_ID,
        'status': 'RENDERED_AND_REVIEW_VERIFIED_NO_SOLVER_EXECUTION',
        'executionManifestSha256': supplied,
        'hardenedNormalizerRawSha256': raw_sha256(NORMALIZER),
        'physicalInputAuditRawSha256': norm.PHYSICAL_AUDIT_SHA,
        'wavelengthGridRawSha256': raw_sha256(wavelength_grid_file),
        'caseCount': len(rows),
        'uniqueCaseCount': len({r['caseId'] for r in rows}),
        'uniqueSeedCount': len({r['seed'] for r in rows}),
        'allPhysicalFingerprintsMatchHistorical': True,
        'solverExecutionPerformed': False,
        'authorizationPermitted': False,
        'fittingAuthorized': False,
        'holdoutOpeningAuthorized': False,
        'tier2Authorized': False,
        'productionAuthorization': False,
        'cases': rows,
    }
    report['casesCanonicalSha256'] = canonical_sha(rows)
    report['reportSha256'] = canonical_sha(report)
    (output_dir / 'renderer-review-report.json').write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + '\n')
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--execution-manifest', type=Path, default=EXECUTION_MANIFEST)
    ap.add_argument('--source-dir', type=Path, default=ROOT)
    ap.add_argument('--output-dir', type=Path, required=True)
    ap.add_argument('--lib-radtran-data', type=Path, required=True)
    ap.add_argument('--atmosphere-file', type=Path, required=True)
    ap.add_argument('--solar-flux-file', type=Path, required=True)
    ap.add_argument('--wavelength-grid-file', type=Path, default=GRID)
    args = ap.parse_args()
    try:
        result = render_all(args.execution_manifest, args.source_dir, args.output_dir, args.lib_radtran_data, args.atmosphere_file, args.solar_flux_file, args.wavelength_grid_file)
        print(json.dumps({'status': result['status'], 'caseCount': result['caseCount'], 'reportSha256': result['reportSha256']}, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({'status': 'REFUSED', 'reason': str(exc)}, indent=2))
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
