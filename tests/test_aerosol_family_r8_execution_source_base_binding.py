from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
R8 = ROOT / "experiments" / "aerosol-family-challenge-v2-r8"
CANDIDATE = R8 / "execution-candidate"
BASE = ROOT / "experiments" / "aerosol-family-challenge-v2"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_r8_execution_guard_uses_byte_bound_base_design_source_main_sha() -> None:
    sys.path.insert(0, str(CANDIDATE))
    try:
        core = _load(R8 / "core.py", "afc2_r8_core_source_binding_test")
        guard = _load(CANDIDATE / "guard.py", "afc2_r8_guard_source_binding_test")
        base_core = _load(BASE / "core.py", "afc2_r6_core_source_binding_test")
    finally:
        sys.path.remove(str(CANDIDATE))

    base_design = json.loads(core.BASE_DESIGN_PATH.read_text())
    expected = base_design["sourceBindings"]["publicRepoMainSha"]

    assert expected == base_core.PUBLIC_REPO_MAIN_SHA
    assert guard._bound_source_base_main_sha(core) == expected
