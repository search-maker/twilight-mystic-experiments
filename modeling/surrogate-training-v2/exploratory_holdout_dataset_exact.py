from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any


def _load_base():
    path = Path(__file__).with_name('exploratory_holdout_dataset.py')
    spec = importlib.util.spec_from_file_location('exploratory_holdout_dataset_base', path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


base = _load_base()
ORDINAL12_IDS = tuple(getattr(base, 'ORDINAL12_IDS', getattr(base, 'CONTINUATION_IDS', ())))
ORDINAL13_IDS = tuple(getattr(base, 'ORDINAL13_IDS', (
    'train-0003', 'train-0007', 'train-0011', 'train-0013', 'train-0015',
    'train-0019', 'train-0023', 'train-0027', 'train-0029', 'train-0031',
    'train-0035', 'train-0039', 'train-0041', 'train-0043', 'train-0047',
)))

if not hasattr(base, 'ORDINAL13_IDS'):
    _original_load_points = base.load_points

    def load_points(path: Path, expected_raw: str, selected_ids: tuple[str, ...], label: str) -> dict[str, dict[str, Any]]:
        universe = ORDINAL12_IDS if label == 'ordinal12' else ORDINAL13_IDS if label == 'ordinal13' else None
        if universe is None:
            raise base.Refusal(f'unknown holdout analysis universe: {label}')
        prior = base.CONTINUATION_IDS
        base.CONTINUATION_IDS = universe
        try:
            return _original_load_points(path, expected_raw, selected_ids, label)
        finally:
            base.CONTINUATION_IDS = prior

    base.load_points = load_points

build = base.build
dump = base.dump
canonical_sha256 = base.canonical_sha256
raw_sha256 = base.raw_sha256
Refusal = base.Refusal
_photopic = base._photopic
_close = base._close

for _name in dir(base):
    if not _name.startswith('_') and _name not in globals():
        globals()[_name] = getattr(base, _name)
