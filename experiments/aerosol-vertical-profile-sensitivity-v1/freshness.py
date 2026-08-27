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
validate_preauthorization = mod.validate_preauthorization
validate_authorization_review = mod.validate_authorization_review
validate_dispatch = mod.validate_dispatch
