from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path
from typing import Any


R8_DIR = Path(__file__).resolve().parents[2] / "aerosol-family-challenge-v2-r8" / "execution-candidate"
R8_FRESHNESS_BLOB = "732f803b5261e7986582dd7e0d69a66f70432b1e"
R8_PREAUTH_ORDINAL_BLOB = "7ca8efd17ae9e7ec2baa32fe935e5173ca6d173f"


class GlobalOrdinalRefusal(RuntimeError):
    pass


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GlobalOrdinalRefusal(f"cannot import {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _bound_r8_modules():
    freshness_path = R8_DIR / "freshness.py"
    ordinal_path = R8_DIR / "preauthorization_ordinal.py"
    if git_blob_sha1(freshness_path) != R8_FRESHNESS_BLOB:
        raise GlobalOrdinalRefusal("bound R8 freshness bytes changed")
    if git_blob_sha1(ordinal_path) != R8_PREAUTH_ORDINAL_BLOB:
        raise GlobalOrdinalRefusal("bound R8 preauthorization ordinal bytes changed")
    r8_freshness = load_module("aops_bound_r8_freshness", freshness_path)
    previous = sys.modules.get("freshness")
    sys.modules["freshness"] = r8_freshness
    try:
        r8_ordinal = load_module("aops_bound_r8_global_ordinal", ordinal_path)
    finally:
        if previous is None:
            sys.modules.pop("freshness", None)
        else:
            sys.modules["freshness"] = previous
    return r8_freshness, r8_ordinal


def authoritative_global_ordinal_observations(
    payload: dict[str, Any],
    *,
    current_run_id: int | None = None,
) -> list[dict[str, Any]]:
    _, mod = _bound_r8_modules()
    return mod.authoritative_global_ordinal_observations(payload, current_run_id=current_run_id)


def derive_next_global_ordinal(
    payload: dict[str, Any],
    latest_consumed: int,
    *,
    current_run_id: int | None = None,
):
    _, mod = _bound_r8_modules()
    return mod.derive_next_global_ordinal(payload, latest_consumed, current_run_id=current_run_id)
