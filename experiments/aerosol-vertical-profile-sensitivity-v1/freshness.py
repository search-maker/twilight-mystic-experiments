from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "aerosol-full-phase-function-sensitivity-v1" / "execution-candidate" / "freshness.py"
EXPECTED_BLOB = "eca41233f3e91b06dd08172d74ef990d18d9ef7d"
STAGE_ID = "aerosol-vertical-profile-sensitivity-v1"
STAGE_TOKEN = "AVPS_V1"


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


if git_blob_sha1(BASE) != EXPECTED_BLOB:
    raise RuntimeError("vertical-profile v1 refuses: bound AFPF freshness bytes changed")
spec = importlib.util.spec_from_file_location("vertical_profile_bound_afpf_freshness", BASE)
if spec is None or spec.loader is None:
    raise RuntimeError("cannot load bound AFPF freshness rules")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
mod.STAGE_ID = STAGE_ID
mod.STAGE_TOKEN = STAGE_TOKEN

FreshnessRefusal = mod.FreshnessRefusal
require = mod.require
authorization_branch = mod.authorization_branch
dispatch_branch = mod.dispatch_branch
execution_key = mod.execution_key
authorization_marker = mod.authorization_marker
consumed_marker = mod.consumed_marker
marker_regex = mod.marker_regex
positive_candidate_claims = mod.positive_candidate_claims
matching_marker = mod.matching_marker
validate_common = mod.validate_common
validate_authorization_review = mod.validate_authorization_review
validate_dispatch = mod.validate_dispatch


def validate_preauthorization(ctx: dict, ordinal: int) -> None:
    """Allow exactly one rigorously proven failed-review authorization ref to be reused.

    The generic AFPF rule requires the authorization branch to be absent. AVPS
    keeps that default, except when the stage-aware control surface has proved
    the existing head is the preserved terminal attempt-1 failed review with no
    allocation marker, dispatch, consumed marker, science run or execution-key
    use. This is identity recovery only; it does not allocate the ordinal.
    """
    validate_common(ctx, ordinal)
    require(ctx.get("currentConsumedMarkerCount") == 0, "candidate consumed marker already exists")
    reusable = ctx.get("authorizationBranchReusableAfterFailedReview") is True
    branch_exists = ctx.get("authorizationBranchExists") is True
    require(
        (not branch_exists) or reusable,
        "AVPS authorization branch already exists without rigorously preserved failed-review proof",
    )
    require(ctx.get("activeAuthorizationPathOnMainExists") is False, "active AVPS authorization path already exists on main")
    require(ctx.get("matchingAuthorizationMarkers") == 0, "authorization marker already exists before review")
    require(ctx.get("candidateSeedAuthorizationRecheckPassed") is True, "authorization-time candidate seed recheck has not passed")
