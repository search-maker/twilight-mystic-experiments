#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import re
from pathlib import Path

ROWS = [23, 24, 25]
OLD_PHOTONS = 20_000
NEW_PHOTONS = 50_000
OLD_SEED_BASE = 941_000_000
NEW_SEED_BASES = {1: 955_000_000, 2: 956_000_000}


class Refusal(RuntimeError):
    pass


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location('frozen_taylor_v1', path)
    if spec is None or spec.loader is None:
        raise Refusal(f'cannot import {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def normalize_runtime_and_basename(text: str) -> list[str]:
    out = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith('data_files_path '):
            out.append('data_files_path <PINNED_DATA_DIR>')
        elif s.startswith('atmosphere_file '):
            out.append('atmosphere_file <PINNED_AFGLUS>')
        elif s.startswith('mc_basename '):
            out.append('mc_basename <CASE_BASENAME>')
        else:
            out.append(line)
    return out


def normalize_old_vs_fresh(text: str) -> list[str]:
    out = []
    for line in normalize_runtime_and_basename(text):
        s = line.strip()
        if s.startswith('mc_photons '):
            out.append('mc_photons <PHOTONS>')
        elif s.startswith('mc_randomseed '):
            out.append('mc_randomseed <SEED>')
        else:
            out.append(line)
    return out


def first_diff(a: list[str], b: list[str]):
    n = max(len(a), len(b))
    for i in range(n):
        av = a[i] if i < len(a) else '<MISSING>'
        bv = b[i] if i < len(b) else '<MISSING>'
        if av != bv:
            return {'lineOneBased': i + 1, 'left': av, 'right': bv}
    return None


def ray_index_from_path(path: Path) -> int | None:
    for part in reversed(path.parts):
        m = re.search(r'(?:^|[-_])ray[-_]?0*([1-9][0-9]?)(?:$|[-_])', part, flags=re.I)
        if m:
            return int(m.group(1))
    m = re.search(r'ray[-_]?0*([1-9][0-9]?)', str(path), flags=re.I)
    return int(m.group(1)) if m else None


def find_original_inputs(row_root: Path) -> dict[int, Path]:
    candidates = list(row_root.rglob('input-resolved.txt'))
    if len(candidates) != 64:
        raise Refusal(f'{row_root}: expected 64 preserved input-resolved.txt files, got {len(candidates)}')
    by = {}
    for p in candidates:
        idx = ray_index_from_path(p)
        if idx is None:
            raise Refusal(f'cannot infer ray index from {p}')
        if idx in by:
            raise Refusal(f'duplicate preserved input for ray {idx}: {by[idx]} and {p}')
        by[idx] = p
    if set(by) != set(range(1, 65)):
        raise Refusal(f'preserved ray universe mismatch: {sorted(by)}')
    return by


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--baseline-runner', type=Path, required=True)
    ap.add_argument('--observations', type=Path, required=True)
    ap.add_argument('--response', type=Path, required=True)
    ap.add_argument('--original-root', type=Path, required=True)
    ap.add_argument('--data-dir', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)

    base = load_module(args.baseline_runner)
    tables = base.load_response(args.response)
    rays = base.quadrature(tables)
    if len(rays) != 64 or {int(r['rayIndex']) for r in rays} != set(range(1, 65)):
        raise Refusal('Taylor-v1 64-ray universe drift')

    data_dir = args.data_dir.resolve()
    atmosphere = (data_dir / 'atmmod/afglus.dat').resolve()
    if not atmosphere.is_file():
        raise Refusal('pinned AFGLUS atmosphere missing')

    original_checks = []
    fresh_checks = []
    for row in ROWS:
        obs = base.load_observation(args.observations, row)
        aod = float(obs['aod550_primary_frozen'])
        row_roots = [p for p in args.original_root.iterdir() if p.is_dir() and re.search(fr'(?:^|-)row-?{row}(?:$|-)', p.name)]
        if len(row_roots) != 1:
            # actions/download-artifact may use the exact artifact name as directory.
            row_roots = [p for p in args.original_root.iterdir() if p.is_dir() and str(row) in p.name]
        if len(row_roots) != 1:
            raise Refusal(f'cannot identify unique original artifact directory for row {row}: {[p.name for p in row_roots]}')
        original_inputs = find_original_inputs(row_roots[0])

        for ray in rays:
            ray_index = int(ray['rayIndex'])
            old_seed = OLD_SEED_BASE + row * 1000 + ray_index
            reconstructed_old = base.render(
                data_dir,
                atmosphere,
                Path('/audit/reconstructed-old') / f'row-{row}' / f'ray-{ray_index:02d}',
                obs,
                ray,
                aod,
                OLD_PHOTONS,
                old_seed,
            )
            preserved_old = original_inputs[ray_index].read_text()
            left = normalize_runtime_and_basename(preserved_old)
            right = normalize_runtime_and_basename(reconstructed_old)
            diff = first_diff(left, right)
            if diff is not None:
                raise Refusal(f'row {row} ray {ray_index}: preserved-vs-reconstructed old physical input mismatch: {diff}')
            # Seed and photon identity must not have been normalized away for the old replay.
            if f'mc_randomseed {old_seed}' not in preserved_old or f'mc_photons {OLD_PHOTONS}' not in preserved_old:
                raise Refusal(f'row {row} ray {ray_index}: preserved old seed/photon identity mismatch')
            original_checks.append({'row': row, 'rayIndex': ray_index, 'oldSeed': old_seed, 'pass': True})

            old_physical = normalize_old_vs_fresh(reconstructed_old)
            for rep, seed_base in NEW_SEED_BASES.items():
                new_seed = seed_base + row * 1000 + ray_index
                fresh = base.render(
                    data_dir,
                    atmosphere,
                    Path('/audit/fresh-default') / f'rep-{rep}' / f'row-{row}' / f'ray-{ray_index:02d}',
                    obs,
                    ray,
                    aod,
                    NEW_PHOTONS,
                    new_seed,
                )
                fresh_physical = normalize_old_vs_fresh(fresh)
                diff = first_diff(old_physical, fresh_physical)
                if diff is not None:
                    raise Refusal(f'row {row} rep {rep} ray {ray_index}: old-vs-fresh physical input mismatch: {diff}')
                if f'mc_randomseed {new_seed}' not in fresh or f'mc_photons {NEW_PHOTONS}' not in fresh:
                    raise Refusal(f'row {row} rep {rep} ray {ray_index}: fresh seed/photon identity mismatch')
                fresh_checks.append({'row': row, 'replicate': rep, 'rayIndex': ray_index, 'newSeed': new_seed, 'pass': True})

    if len(original_checks) != 3 * 64:
        raise Refusal(f'old replay check count mismatch: {len(original_checks)}')
    if len(fresh_checks) != 3 * 2 * 64:
        raise Refusal(f'fresh physical check count mismatch: {len(fresh_checks)}')

    result = {
        'schemaVersion': 1,
        'stageId': 'taylor-default-input-identity-v1',
        'status': 'PHYSICAL_INPUT_IDENTITY_PASS',
        'rows': ROWS,
        'oldPhotons': OLD_PHOTONS,
        'newPhotons': NEW_PHOTONS,
        'oldSeedBase': OLD_SEED_BASE,
        'newSeedBases': NEW_SEED_BASES,
        'preservedOldVsReconstructedOldChecks': len(original_checks),
        'oldVsFreshPhysicalChecks': len(fresh_checks),
        'normalizationOldReplay': ['data_files_path','atmosphere_file','mc_basename'],
        'additionalNormalizationOldVsFresh': ['mc_photons','mc_randomseed'],
        'scientificMeaning': (
            'If PASS, the historical Taylor-v1 preserved inputs are reproduced by the frozen renderer, and the fresh default inputs '
            'used for the blocked broadband test contain no physical-input change beyond photon count and random seed.'
        ),
        'originalChecks': original_checks,
        'freshChecks': fresh_checks,
    }
    (args.output / 'audit.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({
        'status': result['status'],
        'oldChecks': result['preservedOldVsReconstructedOldChecks'],
        'freshChecks': result['oldVsFreshPhysicalChecks'],
    }, sort_keys=True))


if __name__ == '__main__':
    main()
