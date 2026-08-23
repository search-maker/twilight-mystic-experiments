from __future__ import annotations

import hashlib
import importlib.util
import re
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[3]
AOPS_DIR = ROOT / "experiments/aerosol-optical-property-sensitivity-v1/execution-candidate"
AOPS_CONTROL_BLOB = "bc6d5a565b2b98f496793b35b226a334ba6b87f4"
AOPS_GLOBAL_ORDINAL_BLOB = "27f8ac62bc8a520ab22b0215e847ef878db5aa5f"
LOCAL_FRESHNESS_BLOB = "135cde71b94c3a93ef60043bb08cab20cbf84449"
STAGE = "aerosol-full-phase-function-sensitivity-v1"
AUTHORIZATION_PATH = f"experiments/{STAGE}/authorization.json"
CASE_ARTIFACT_PREFIX = "afpf-v1-case-"


class SurfaceRefusal(RuntimeError):
    pass


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def load_bound(name: str, path: Path, expected_blob: str):
    if git_blob_sha1(path) != expected_blob:
        raise SurfaceRefusal(f"bound source byte drift: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SurfaceRefusal(f"cannot import bound source: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _failed_history_must_be_absent(payload: dict[str, Any], ordinal: int) -> dict[str, Any]:
    pattern = re.compile(
        rf"^history/{re.escape(STAGE)}-ordinal-{ordinal}-auth-review-failed-([1-9][0-9]*)$",
        re.I,
    )
    found = [str(row.get("name") or "") for row in payload.get("branches", []) if pattern.fullmatch(str(row.get("name") or ""))]
    if found:
        raise SurfaceRefusal(
            "AFPF failed-authorization recovery history exists; a separately reviewed recovery extension is required"
        )
    return {"heads": [], "prNumbers": [], "reviewRunIds": []}


def _modules():
    freshness = load_bound("afpf_freshness_for_preauth", HERE / "freshness.py", LOCAL_FRESHNESS_BLOB)
    control = load_bound("afpf_bound_aops_control_surface", AOPS_DIR / "control_surface.py", AOPS_CONTROL_BLOB)
    ordinal = load_bound("afpf_bound_aops_global_ordinal", AOPS_DIR / "global_ordinal.py", AOPS_GLOBAL_ORDINAL_BLOB)

    control.authorization_branch = freshness.authorization_branch
    control.dispatch_branch = freshness.dispatch_branch
    control.execution_key = freshness.execution_key
    control.matching_marker = freshness.matching_marker
    control.positive_candidate_claims = freshness.positive_candidate_claims
    control.consumed_marker = freshness.consumed_marker
    control.failed_authorization_history = _failed_history_must_be_absent
    control.AUTHORIZATION_PATH = AUTHORIZATION_PATH
    control.CASE_ARTIFACT_PREFIX = CASE_ARTIFACT_PREFIX
    return freshness, control, ordinal


def collect(repository: str, token: str) -> dict[str, Any]:
    _, control, _ = _modules()
    return control.collect(repository, token)


def latest_consumed_or_dispatched_ordinal(payload: dict[str, Any]) -> int | None:
    _, control, _ = _modules()
    return control.latest_consumed_or_dispatched_ordinal(payload)


def derive_next_global_ordinal(
    payload: dict[str, Any], latest_consumed: int, *, current_run_id: int | None = None
):
    _, _, ordinal = _modules()
    return ordinal.derive_next_global_ordinal(payload, latest_consumed, current_run_id=current_run_id)


def build_surface(
    payload: dict[str, Any],
    ordinal: int,
    *,
    current_run_id: int | None = None,
    candidate_seed_authorization_recheck_passed: bool,
) -> dict[str, Any]:
    freshness, control, _ = _modules()
    surface = control.build_surface(
        payload,
        ordinal,
        current_run_id=current_run_id,
        active_authorization_path_on_main_exists=False,
        candidate_code_paths_on_main_inspected=True,
        candidate_seed_authorization_recheck_passed=candidate_seed_authorization_recheck_passed,
        allow_authorization_branch=False,
        allow_dispatch_branch=False,
    )
    surface["nextAvailableScientificOrdinal"] = ordinal
    freshness.validate_preauthorization(surface, ordinal)
    return surface


def identity_for(ordinal: int) -> dict[str, str]:
    freshness, _, _ = _modules()
    return {
        "authorizationBranch": freshness.authorization_branch(ordinal),
        "dispatchBranch": freshness.dispatch_branch(ordinal),
        "executionKey": freshness.execution_key(ordinal),
    }
