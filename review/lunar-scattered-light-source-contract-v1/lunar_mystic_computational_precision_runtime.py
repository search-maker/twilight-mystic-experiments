#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
IMPLEMENTATION = HERE / 'lunar_mystic_computational_precision.py'


def _load_registered(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'cannot import {path}')
    module = importlib.util.module_from_spec(spec)
    # Python 3.12 dataclasses resolve annotations through sys.modules while the
    # class is being decorated. Register before exec_module so dynamically
    # loaded ROLO dataclasses have normal import semantics.
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_impl = _load_registered('lunar_mystic_computational_precision_impl', IMPLEMENTATION)


def _fixed_load_module(name: str, path: Path):
    return _load_registered(name, path)


# Keep the reviewed implementation byte-for-byte intact while repairing only
# its dynamic module-loading transport. All scientific constants, frozen cases,
# thresholds and claim boundaries remain in the underlying implementation.
_impl._load_module = _fixed_load_module

LunarPrecisionError = _impl.LunarPrecisionError
load_contract = _impl.load_contract
interpolate_spectrum = _impl.interpolate_spectrum
wavelength_grid = _impl.wavelength_grid
build_lunar_source_from_runtime_atlas = _impl.build_lunar_source_from_runtime_atlas
frozen_cases = _impl.frozen_cases
prepare_inputs = _impl.prepare_inputs
evaluate_results = _impl.evaluate_results
main = _impl.main

if __name__ == '__main__':
    raise SystemExit(main())
