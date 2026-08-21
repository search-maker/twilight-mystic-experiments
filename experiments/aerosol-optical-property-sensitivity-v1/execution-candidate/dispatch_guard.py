from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from typing import Any


SHA40 = re.compile(r"^[0-9a-f]{40}$")


class DispatchRefusal(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise DispatchRefusal(message)


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise DispatchRefusal(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def evaluate(
    repository_root: Path,
    authorization: dict[str, Any],
    seed_proof: dict[str, Any],
    context: dict[str, Any],
    paths: dict[str, Path],
    *,
    post_dispatch: bool = False,
) -> dict[str, Any]:
    transport_guard = load("aops_dispatch_transport_auth_guard", paths["authorizationTransportGuard"])
    freshness = load("aops_dispatch_freshness", paths["freshness"])
    ordinal = authorization.get("scientificOrdinal")
    head = context.get("authorizationHead")
    parent = context.get("authorizationParent")
    pr = context.get("pr") or {}
    review = context.get("authorizationReview") or {}
    require(isinstance(head, str) and SHA40.fullmatch(head) is not None, "authorization head invalid")
    require(isinstance(parent, str) and SHA40.fullmatch(parent) is not None, "authorization parent invalid")
    require(context.get("liveMain") == parent, "live main moved after authorization review")
    try:
        transport_guard.validate_enabled_document(repository_root, authorization, parent, paths, seed_proof)
    except Exception as exc:
        raise DispatchRefusal(str(exc)) from exc
    require(pr.get("state") == "open" and pr.get("draft") is True and pr.get("merged") is False, "authorization PR no longer Draft/open/unmerged")
    require(pr.get("headBranch") == authorization["authorizationBranch"] and pr.get("headSha") == head, "authorization PR head/branch drift")
    require(review.get("status") == "AUTHORIZATION_REVIEW_PASS_ZERO_RUNTIME", "zero-runtime authorization review pass missing")
    require(review.get("headSha") == head and review.get("prNumber") == pr.get("number"), "authorization review identity drift")
    require(review.get("runAttempt") == 1 and review.get("conclusion") == "success", "exact successful attempt-1 authorization review required")
    require(review.get("scientificRuntimeSetupPerformed") is False and review.get("scientificExecutionPerformed") is False, "authorization review was not zero-runtime")
    try:
        freshness.validate_dispatch(context.get("freshness") or {}, ordinal, head, post_dispatch=post_dispatch)
    except Exception as exc:
        raise DispatchRefusal(str(exc)) from exc
    markers = context.get("issue60Markers") or []
    good = [m for m in markers if freshness.matching_marker(m, ordinal, head, parent, int(pr.get("number") or 0))]
    require(len(good) == 1 and len(markers) == 1, "exactly one exact Issue #60 authorization marker required")
    if post_dispatch:
        require(context.get("dispatchBranchHeadSha") == head, "dispatch branch does not point to reviewed authorization head")
    return {
        "schemaVersion": 1,
        "stageId": "aerosol-optical-property-sensitivity-v1-dispatch-guard",
        "status": "DISPATCH_TRANSITION_VALID" if post_dispatch else "DISPATCH_ELIGIBLE_NOT_CREATED",
        "scientificOrdinal": ordinal,
        "executionKey": authorization["executionKey"],
        "authorizationHead": head,
        "authorizationParent": parent,
        "authorizationPr": pr["number"],
        "dispatchBranchMayPointTo": head,
        "scientificExecutionPerformed": False,
        "solverExecutionPerformed": False,
    }
