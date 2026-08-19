from __future__ import annotations

# Compatibility facade for review tooling that historically imported render.py by path.
# Load sibling modules explicitly so this file works even when the package directory
# (which contains a hyphen) is not importable as a normal Python package name.
import importlib.util
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent


def _load_sibling(module_name: str, filename: str):
    if module_name in sys.modules:
        return sys.modules[module_name]
    spec = importlib.util.spec_from_file_location(module_name, _HERE / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load sibling module: {filename}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_load_sibling("core", "core.py")
_adapter = _load_sibling("aerosol_family_challenge_v2_adapter", "adapter.py")

# Deliberately expose only the review/render surface.
aerosol_block = _adapter.aerosol_block
assert_exact_aerosol_state = _adapter.assert_exact_aerosol_state
assert_exact_spectrum_surface = _adapter.assert_exact_spectrum_surface
render_case_input = _adapter.render_case_input
transform_pinned_base_render = _adapter.transform_pinned_base_render
inject_aerosol_state = transform_pinned_base_render
