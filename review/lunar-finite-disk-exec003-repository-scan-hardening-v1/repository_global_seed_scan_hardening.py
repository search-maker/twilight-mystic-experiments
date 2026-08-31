from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

BASE_SCANNER_PATH = Path('experiments/aerosol-family-challenge-v2/repository_global_seed_scan.py')
BASE_SCANNER_GIT_BLOB_SHA = '4c6d704fa24228284780bcb1dd7c52537b4c5b0d'
STABILITY_ONLY_DYNAMIC_KEYS = frozenset({'pushed_at'})


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def _load_base():
    observed = _git_blob_sha(BASE_SCANNER_PATH)
    if observed != BASE_SCANNER_GIT_BLOB_SHA:
        raise RuntimeError(
            f'bound repository-global scanner bytes changed: expected {BASE_SCANNER_GIT_BLOB_SHA}, observed {observed}'
        )
    spec = importlib.util.spec_from_file_location('lunar_exec003_repository_global_seed_scan_base', BASE_SCANNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError('cannot import bound repository-global scanner')
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


base = _load_base()


def _canonical_stability_value(value: Any) -> Any:
    """Canonicalize only for two-pass stability; never for seed-collision scanning."""
    if isinstance(value, dict):
        return {
            name: _canonical_stability_value(value[name])
            for name in sorted(value)
            if name not in base.MUTABLE_OPERATIONAL_KEYS
            and name not in STABILITY_ONLY_DYNAMIC_KEYS
        }
    if isinstance(value, list):
        normalized = [_canonical_stability_value(item) for item in value]
        return sorted(
            normalized,
            key=lambda item: json.dumps(
                item, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False
            ),
        )
    return value


def canonical_stability_context(context: dict[str, Any], current_run_id: int | None = None) -> dict[str, Any]:
    filtered = base._without_current_audit_self_metadata(context, current_run_id)
    return {key: _canonical_stability_value(filtered[key]) for key in base.SURFACE_KEYS}


def stable_context_sha256(context: dict[str, Any], current_run_id: int | None = None) -> str:
    normalized = canonical_stability_context(context, current_run_id)
    return hashlib.sha256(
        json.dumps(
            normalized, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False
        ).encode()
    ).hexdigest()


def _row_identity(surface: str, row: dict[str, Any]) -> str:
    if surface == 'branches':
        value = str(row.get('name') or '')
    else:
        value = str(row.get('id') or row.get('number') or '')
    return value or '<missing-stable-id>'


def _row_fingerprint(row: dict[str, Any]) -> str:
    canonical = _canonical_stability_value(row)
    return hashlib.sha256(
        json.dumps(
            canonical, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False
        ).encode()
    ).hexdigest()[:16]


def stability_diff_summary(
    first: dict[str, Any],
    second: dict[str, Any],
    current_run_id: int | None = None,
) -> list[str]:
    """Return bounded surface/row diagnostics without rendering row contents."""
    a = canonical_stability_context(first, current_run_id)
    b = canonical_stability_context(second, current_run_id)
    changed: list[str] = []
    for surface in base.SURFACE_KEYS:
        left = {_row_identity(surface, row): _row_fingerprint(row) for row in a[surface]}
        right = {_row_identity(surface, row): _row_fingerprint(row) for row in b[surface]}
        identities = sorted(set(left) | set(right))
        surface_changes = [
            identity for identity in identities if left.get(identity) != right.get(identity)
        ]
        if surface_changes:
            rendered = ','.join(surface_changes[:12])
            suffix = f',+{len(surface_changes) - 12}more' if len(surface_changes) > 12 else ''
            changed.append(f'{surface}[{rendered}{suffix}]')
    return changed


def require_two_pass_stability(
    first: dict[str, Any],
    second: dict[str, Any],
    current_run_id: int | None = None,
) -> str:
    first_sha = stable_context_sha256(first, current_run_id)
    second_sha = stable_context_sha256(second, current_run_id)
    if first_sha != second_sha:
        changed = stability_diff_summary(first, second, current_run_id)
        detail = ';'.join(changed) if changed else '<unresolved>'
        raise RuntimeError(
            'snapshot-fenced repository-global metadata changed between two complete enumerations; '
            f'changed={detail}; refuse this audit and start a fresh attempt-1 workflow run'
        )
    return second_sha


def install_into_bound_scanner():
    """Patch stability comparison only; raw collision canonicalization/scanning stays untouched."""
    base.require_two_pass_stability = require_two_pass_stability
    return base


def main() -> int:
    return install_into_bound_scanner().main()


if __name__ == '__main__':
    raise SystemExit(main())
