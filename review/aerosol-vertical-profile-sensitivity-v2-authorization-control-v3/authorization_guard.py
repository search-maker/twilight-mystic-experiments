from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

STAGE = "aerosol-vertical-profile-sensitivity-v2"
ORDINAL = 41
BASE_MAIN = "99ade7798627e67921139697ba1a004fa8a304bb"
AUTH_PATH = "review/aerosol-vertical-profile-sensitivity-v2-authorization-control-v3/authorization.json"
CONTROL_BRANCH = "review/aerosol-vertical-profile-sensitivity-v2-authorization-control-v3"
AUTH_BRANCH = f"authorization/{STAGE}-ordinal-{ORDINAL}"
DISPATCH_BRANCH = f"dispatch/{STAGE}-ordinal-{ORDINAL}"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BUILDER = HERE / "build_authorization.py"
PREAUTH = ROOT / "review/aerosol-vertical-profile-sensitivity-v2-preauthorization/preauthorize.py"
EXPECTED_BUILDER_BLOB = "6905eb13c06f99775f044ae7b3c05aaf8543edb7"
EXPECTED_PREAUTH_BLOB = "0258f7d7d1f3678860d6d1cae3b17363c58c2079"


class Refusal(RuntimeError):
    pass


def git_blob_sha1(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _load(name: str, path: Path, expected_blob: str):
    if not path.is_file() or git_blob_sha1(path) != expected_blob:
        raise Refusal(f"bound source byte drift: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise Refusal(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def builder():
    return _load("avps_v2_bound_authorization_builder_v3", BUILDER, EXPECTED_BUILDER_BLOB)


def preauth_module():
    return _load("avps_v2_bound_preauthorize_v3", PREAUTH, EXPECTED_PREAUTH_BLOB)


def validate_review_context(auth: dict[str, Any], ctx: dict[str, Any]) -> None:
    head = str(ctx.get("headSha") or "")
    parent = str(ctx.get("parentSha") or "")
    base_head = str(ctx.get("baseHeadSha") or "")
    if any(SHA40.fullmatch(x) is None for x in (head, parent, base_head)):
        raise Refusal("authorization commit identity malformed")
    if ctx.get("parentCount") != 1 or parent != base_head:
        raise Refusal("authorization must be one direct child of exact live control head")
    if ctx.get("baseBranch") != CONTROL_BRANCH or ctx.get("headBranch") != AUTH_BRANCH:
        raise Refusal("authorization PR branch/base identity drift")
    if ctx.get("state") != "open" or ctx.get("draft") is not True or ctx.get("merged") is not False:
        raise Refusal("authorization PR must remain Draft/open/unmerged")
    if ctx.get("headRepo") != ctx.get("baseRepo"):
        raise Refusal("authorization PR must be same-repository")
    if ctx.get("changedPaths") != [AUTH_PATH]:
        raise Refusal("authorization child must change exactly authorization.json")
    if ctx.get("eventName") != "pull_request" or ctx.get("eventAction") != "opened" or ctx.get("runAttempt") != 1:
        raise Refusal("authorization review must be attempt-1 opened PR run")
    if ctx.get("scientificRuntimeSetupPerformed") is not False or ctx.get("scientificExecutionPerformed") is not False:
        raise Refusal("authorization review crossed runtime boundary")
    if auth.get("scientificOrdinal") != ORDINAL or auth.get("authorizationBranch") != AUTH_BRANCH or auth.get("dispatchBranch") != DISPATCH_BRANCH:
        raise Refusal("authorization document identity drift")
    if auth.get("exactAuthorizationParentCommit") != parent:
        raise Refusal("authorization document/control-parent drift")


def _allowed_self_observation(row: dict[str, Any], payload: dict[str, Any], branch: str, head: str, pr_number: int) -> bool:
    surface = str(row.get("surface") or "")
    identity = str(row.get("id") or "")
    if surface == "branch" and identity == branch:
        return True
    if surface in ("pull-request", "pull-request-prose") and identity == str(pr_number):
        return True
    if surface == "workflow-run":
        for run in payload.get("runs", []):
            if str(run.get("id") or "") != identity:
                continue
            return str(run.get("head_branch") or "") == branch and str(run.get("head_sha") or "") == head
    return False


def authorization_review_ordinal_surface(
    payload: dict[str, Any], *, head: str, pr_number: int, current_run_id: int
) -> dict[str, Any]:
    if SHA40.fullmatch(head or "") is None or pr_number <= 0 or current_run_id <= 0:
        raise Refusal("authorization-review identity input malformed")
    pre = preauth_module()
    ordinal_mod = pre.bound_ordinal_module()
    observations = ordinal_mod.authoritative_global_ordinal_observations(payload, current_run_id=current_run_id)
    consumed = [int(r["ordinal"]) for r in observations if r.get("reason") == "exact-consumed-marker"]
    if not consumed or max(consumed) != 40:
        raise Refusal("latest exact consumed ordinal is no longer 40")

    nonself: list[dict[str, Any]] = []
    allowed_self: list[dict[str, Any]] = []
    for row in observations:
        n = int(row["ordinal"])
        if n == ORDINAL and _allowed_self_observation(row, payload, AUTH_BRANCH, head, pr_number):
            allowed_self.append(row)
        else:
            nonself.append(row)

    illegal_41 = [r for r in nonself if int(r["ordinal"]) == ORDINAL]
    if illegal_41:
        raise Refusal(f"independent ordinal-41 reservation/allocation surface exists: {illegal_41[:5]}")
    observed_max = max(int(r["ordinal"]) for r in nonself)
    if observed_max != 40:
        raise Refusal(f"non-self authoritative ordinal surface moved: {observed_max}")

    branch_names = [str(r.get("name") or "") for r in payload.get("branches", [])]
    if DISPATCH_BRANCH in branch_names:
        raise Refusal("ordinal-41 dispatch branch already exists")
    issue60 = [str(r.get("body") or "").strip() for r in payload.get("issue60Comments", [])]
    if any(body.upper().startswith("ORDINAL41_") for body in issue60):
        raise Refusal("Issue #60 already contains an ordinal-41 allocation/consumption marker")

    return {
        "status": "PASS_AUTHORIZATION_REVIEW_SELF_IDENTITY_ONLY_ORDINAL_41_NOT_ALLOCATED",
        "latestConsumedScientificOrdinal": 40,
        "nonSelfGlobalOrdinalMaxObserved": 40,
        "scientificOrdinal": ORDINAL,
        "allowedSelfObservationCount": len(allowed_self),
        "independentOrdinal41ObservationCount": 0,
        "dispatchBranchExists": False,
        "ordinal41IssueMarkerExists": False,
        "nonSelfOrdinalObservationsCanonicalSha256": hashlib.sha256(
            json.dumps(nonself, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest(),
    }


def validate_exact_document(
    auth: dict[str, Any],
    control_head: str,
    preauthorization: dict[str, Any],
    control_receipt: dict[str, Any],
    live_surface: dict[str, Any],
) -> None:
    builder().validate_document(auth, control_head, preauthorization, control_receipt, live_surface)


def main() -> int:
    print(json.dumps({
        "status": "AUTHORIZATION_GUARD_V3_REVIEW_ONLY_NO_SOLVER",
        "stageId": STAGE,
        "scientificOrdinalAllocated": False,
        "dispatchAuthorized": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
