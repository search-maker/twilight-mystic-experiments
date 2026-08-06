from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_base():
    path = Path(__file__).with_name('exploratory_holdout_real_evaluation.py')
    spec = importlib.util.spec_from_file_location('exploratory_holdout_real_evaluation_base', path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


base = _load_base()
_original_module = base.module


def module(path: Path, name: str):
    if path.name == 'exploratory_holdout_dataset.py':
        path = path.with_name('exploratory_holdout_dataset_exact.py')
    return _original_module(path, name)


base.module = module
main = base.main
assert_no_prior_claim = base.assert_no_prior_claim
evaluate_once = base.evaluate_once
CLAIM_NAME = base.CLAIM_NAME
MODEL_HASH = base.MODEL_HASH
PROTOCOL_SHA256 = base.PROTOCOL_SHA256
CASES = base.CASES
ANALYSES = base.ANALYSES

if __name__ == '__main__':
    raise SystemExit(main())
