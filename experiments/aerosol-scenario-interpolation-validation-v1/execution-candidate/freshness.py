from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
from typing import Any

STAGE_ID = "aerosol-scenario-interpolation-validation-v1"
STAGE_TOKEN = "ASIV_V1"
ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "experiments/aerosol-full-phase-function-sensitivity-v1/execution-candidate/freshness.py"
EXPECTED_BASE_BLOB = "eca41233f3e91b06dd08172d74ef990d18d9ef7d"


class FreshnessRefusal(RuntimeError):
    pass


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _load_base():
    if git_blob_sha1(BASE) != EXPECTED_BASE_BLOB:
        raise FreshnessRefusal("bound AFPF freshness primitive byte drift")
    spec = importlib.util.spec_from_file_location("asiv_bound_afpf_freshness", BASE)
    if spec is None or spec.loader is None:
        raise FreshnessRefusal("cannot import bound AFPF freshness primitive")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.STAGE_ID = STAGE_ID
    module.STAGE_TOKEN = STAGE_TOKEN
    return module


_BASE = _load_base()
authorization_branch = _BASE.authorization_branch
dispatch_branch = _BASE.dispatch_branch
execution_key = _BASE.execution_key
authorization_marker = _BASE.authorization_marker
consumed_marker = _BASE.consumed_marker
marker_regex = _BASE.marker_regex
positive_candidate_claims = _BASE.positive_candidate_claims
matching_marker = _BASE.matching_marker


def _geometry(ctx: dict[str, Any]) -> None:
    if ctx.get("candidateGeometryAuthorizationRecheckPassed") is not True:
        raise FreshnessRefusal("authorization-time holdout geometry recheck has not passed")


def validate_preauthorization(ctx: dict[str, Any], ordinal: int) -> None:
    _BASE.validate_preauthorization(ctx, ordinal)
    _geometry(ctx)


def validate_authorization_review(ctx: dict[str, Any], ordinal: int, head_sha: str) -> None:
    _BASE.validate_authorization_review(ctx, ordinal, head_sha)
    _geometry(ctx)


def validate_dispatch(ctx: dict[str, Any], ordinal: int, head_sha: str, *, post_dispatch: bool = False) -> None:
    _BASE.validate_dispatch(ctx, ordinal, head_sha, post_dispatch=post_dispatch)
    _geometry(ctx)
