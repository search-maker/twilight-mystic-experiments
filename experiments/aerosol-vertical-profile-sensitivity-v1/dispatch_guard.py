from __future__ import annotations

import hashlib
import importlib.util
import re
import sys
from pathlib import Path
from typing import Any

STAGE = "aerosol-vertical-profile-sensitivity-v1"
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
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def evaluate(
    repository_root: Path,
    authorization: dict[str, Any],
    preauthorization_report: dict[str, Any],
    authorization_seed_proof: dict[str, Any],
    context: dict[str, Any],
    *,
    preauthorization_artifact_id: int,
    preauthorization_artifact_digest: str,
    post_dispatch: bool = False,
) -> dict[str, Any]:
    stage = repository_root / "experiments" / STAGE
    authorization_guard = load("avps_dispatch_authorization_guard", stage / "authorization_guard.py")
    freshness = load("avps_dispatch_freshness", stage / "freshness.py")

    ordinal = authorization.get("scientificOrdinal")
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal <= 0:
        raise DispatchRefusal("authorization scientific ordinal invalid")
    head = str(context.get("authorizationHead") or "")
    parent = str(context.get("authorizationParent") or "")
    pr = context.get("pr") or {}
    review = context.get("authorizationReview") or {}
    require(SHA40.fullmatch(head) is not None, "authorization head invalid")
    require(SHA40.fullmatch(parent) is not None, "authorization parent invalid")
    require(context.get("liveMain") == parent, "live main moved after authorization review")

    try:
        authorization_guard.validate_enabled_document(
            repository_root,
            authorization,
            parent,
            preauthorization_report,
            authorization_seed_proof,
            preauthorization_artifact_id=preauthorization_artifact_id,
            preauthorization_artifact_digest=preauthorization_artifact_digest,
        )
    except Exception as exc:
        raise DispatchRefusal(f"authorization document invalid: {exc}") from exc

    contract_path = stage / "execution-contract.review.json"
    control = authorization.get("executionControlBindings") or {}
    require(control.get("executionContractGitBlobSha1") == git_blob_sha1(contract_path),
            "authorization execution-contract binding drift")
    require(control.get("dispatchGuardGitBlobSha1") == git_blob_sha1(Path(__file__)),
            "authorization dispatch-guard binding drift")

    require(pr.get("state") == "open" and pr.get("draft") is True and pr.get("merged") is False,
            "authorization PR no longer Draft/open/unmerged")
    require(pr.get("headBranch") == authorization.get("authorizationBranch") and pr.get("headSha") == head,
            "authorization PR head/branch drift")
    require(review.get("status") == "AUTHORIZATION_REVIEW_PASS_ZERO_RUNTIME",
            "zero-runtime authorization review pass missing")
    require(review.get("headSha") == head and review.get("parentSha") == parent,
            "authorization review commit binding drift")
    require(review.get("scientificOrdinal") == ordinal,
            "authorization review ordinal drift")
    require(review.get("candidateSeedAuthorizationRecheckPassed") is True,
            "authorization-head seed recheck evidence missing")
    require(review.get("scientificRuntimeSetupPerformed") is False
            and review.get("scientificExecutionPerformed") is False
            and review.get("solverExecutionPerformed") is False,
            "authorization review was not zero-runtime")
    require(context.get("authorizationReviewRunAttempt") == 1
            and context.get("authorizationReviewRunConclusion") == "success",
            "exact successful attempt-1 authorization review required")

    try:
        freshness.validate_dispatch(context.get("freshness") or {}, int(ordinal), head, post_dispatch=post_dispatch)
    except Exception as exc:
        raise DispatchRefusal(f"dispatch freshness refusal: {exc}") from exc

    markers = context.get("issue60AuthorizationMarkers") or []
    require(isinstance(markers, list), "Issue #60 authorization markers must be a list")
    expected_marker = freshness.authorization_marker(int(ordinal), head, parent, int(pr.get("number") or 0))
    require(markers == [expected_marker], "exactly one exact Issue #60 authorization allocation marker required")

    consumed = context.get("issue60ConsumedMarkers") or []
    require(isinstance(consumed, list), "Issue #60 consumed markers must be a list")
    expected_consumed = freshness.consumed_marker(int(ordinal))
    if post_dispatch:
        require(context.get("dispatchBranchHeadSha") == head,
                "dispatch branch does not point to reviewed authorization head")
        require(consumed == [expected_consumed], "exactly one dispatch-consumed marker required after git push")
    else:
        require(consumed == [], "dispatch-consumed marker must not exist before git push")

    return {
        "schemaVersion": 1,
        "stageId": f"{STAGE}-dispatch-guard",
        "status": "DISPATCH_TRANSITION_VALID" if post_dispatch else "DISPATCH_ELIGIBLE_NOT_CREATED",
        "scientificOrdinal": int(ordinal),
        "executionKey": authorization["executionKey"],
        "authorizationHead": head,
        "authorizationParent": parent,
        "authorizationPr": int(pr["number"]),
        "dispatchBranchMayPointTo": head,
        "executionContractGitBlobSha1": git_blob_sha1(contract_path),
        "scientificRuntimeSetupPerformed": False,
        "scientificExecutionPerformed": False,
        "solverExecutionPerformed": False,
        "resultOpeningPerformed": False,
    }
