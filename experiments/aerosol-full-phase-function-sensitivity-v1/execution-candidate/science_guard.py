from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path
from typing import Any

STAGE = "aerosol-full-phase-function-sensitivity-v1"
EXPECTED_STATUS = "EXACT_ONE_USE_AFPF_V1_DISPATCH_AUTHORIZED"
SHA40 = re.compile(r"^[0-9a-f]{40}$")


class ScienceGuardRefusal(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ScienceGuardRefusal(message)


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ScienceGuardRefusal(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def evaluate(
    repository_root: Path,
    authorization: dict[str, Any],
    authorization_seed_proof: dict[str, Any],
    live_seed_proof: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    stage = repository_root / "experiments" / STAGE
    execd = stage / "execution-candidate"
    auth_guard = load("afpf_science_authorization_guard", execd / "authorization_guard.py")
    freshness = load("afpf_science_freshness", execd / "freshness.py")
    design_mod = load("afpf_science_execution_design", stage / "execution_design.py")

    ordinal = authorization.get("scientificOrdinal")
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal <= 0:
        raise ScienceGuardRefusal("authorization scientific ordinal invalid")
    head = str(context.get("authorizationHead") or "")
    parent = str(context.get("authorizationParent") or "")
    run_id = context.get("workflowRunId")
    require(SHA40.fullmatch(head) is not None and SHA40.fullmatch(parent) is not None,
            "authorization commit identity invalid")
    require(context.get("eventName") == "workflow_dispatch", "science must use explicit workflow_dispatch")
    require(context.get("runAttempt") == 1, "science run attempt must be exactly 1")
    require(context.get("headSha") == head, "science checkout must equal reviewed authorization head")
    require(context.get("refName") == authorization.get("dispatchBranch"), "science ref must be exact dispatch branch")
    require(context.get("dispatchBranchHeadSha") == head, "dispatch ref drift")
    require(context.get("authorizationBranchHeadSha") == head, "authorization ref drift")
    require(context.get("liveMain") == parent, "live main moved after authorization")
    require(isinstance(run_id, int) and not isinstance(run_id, bool) and run_id > 0, "workflow run ID invalid")

    try:
        auth_guard.validate_enabled_document(repository_root, authorization, parent, authorization_seed_proof)
    except Exception as exc:
        raise ScienceGuardRefusal(f"authorization document invalid: {exc}") from exc

    try:
        design_mod.validate_seed_authorization_proof(live_seed_proof, head)
    except Exception as exc:
        raise ScienceGuardRefusal(f"live pre-solver seed recheck invalid: {exc}") from exc
    require(live_seed_proof.get("candidateSeedCanonicalSha256") == authorization.get("candidateSeedCanonicalSha256"),
            "live seed canonical hash drift")
    require(live_seed_proof.get("candidateRowsCanonicalSha256") == authorization.get("candidateRowsCanonicalSha256"),
            "live seed row hash drift")

    design = design_mod.build_review_execution_design(authorization_seed_proof, parent)
    require(design.get("canonicalDesignSha256") == authorization.get("executionDesignCanonicalSha256"),
            "authorization/design canonical hash drift")

    pr = context.get("pr") or {}
    require(pr.get("state") == "open" and pr.get("draft") is True and pr.get("merged") is False,
            "authorization PR must remain Draft/open/unmerged")
    require(pr.get("headBranch") == authorization.get("authorizationBranch") and pr.get("headSha") == head,
            "authorization PR identity drift")

    review = context.get("authorizationReview") or {}
    require(review.get("status") == "AUTHORIZATION_REVIEW_PASS_ZERO_RUNTIME", "authorization review pass missing")
    require(review.get("headSha") == head and review.get("parentSha") == parent,
            "authorization review commit binding drift")
    require(review.get("prNumber") == pr.get("number"), "authorization review PR drift")
    require(review.get("runAttempt") == 1 and review.get("conclusion") == "success",
            "authorization review must be completed success attempt1")
    require(review.get("scientificRuntimeSetupPerformed") is False and review.get("scientificExecutionPerformed") is False,
            "authorization review crossed zero-runtime boundary")

    publisher_run = context.get("publisherRun") or {}
    publisher = context.get("publisherEvidence") or {}
    require(publisher_run.get("runAttempt") == 1 and publisher_run.get("status") == "completed"
            and publisher_run.get("conclusion") == "success", "publisher must be completed success attempt1")
    require(publisher.get("status") == "DISPATCH_PUBLISHED_ZERO_RUNTIME", "publisher evidence pass missing")
    require(publisher.get("scientificOrdinal") == ordinal, "publisher ordinal drift")
    require(publisher.get("authorizationHead") == head and publisher.get("authorizationParent") == parent,
            "publisher authorization identity drift")
    require(publisher.get("authorizationPr") == pr.get("number"), "publisher PR drift")
    require(publisher.get("dispatchBranchHeadSha") == head, "publisher dispatch head drift")
    require(publisher.get("scientificRuntimeSetupPerformed") is False
            and publisher.get("scientificExecutionPerformed") is False
            and publisher.get("solverExecutionPerformed") is False,
            "publisher crossed zero-runtime boundary")

    try:
        freshness.validate_dispatch(context.get("freshness") or {}, ordinal, head, post_dispatch=True)
    except Exception as exc:
        raise ScienceGuardRefusal(f"post-dispatch freshness refusal: {exc}") from exc

    auth_markers = context.get("issue60AuthorizationMarkers") or []
    consumed_markers = context.get("issue60ConsumedMarkers") or []
    expected_auth = freshness.authorization_marker(ordinal, head, parent, int(pr.get("number") or 0))
    expected_consumed = freshness.consumed_marker(ordinal)
    require(auth_markers == [expected_auth], "exact one allocation marker required")
    require(consumed_markers == [expected_consumed], "exact one consumed marker required")

    contract_path = stage / "execution-contract.review.json"
    contract_blob = git_blob_sha1(contract_path)
    require(authorization.get("byteBindings", {}).get("executionContract", {}).get("gitBlobSha1") == contract_blob,
            "authorization execution-contract binding drift")

    return {
        "schemaVersion": 1,
        "stageId": f"{STAGE}-science-guard",
        "status": EXPECTED_STATUS,
        "scientificOrdinal": ordinal,
        "workflowRunId": run_id,
        "workflowRunAttempt": 1,
        "authorizationHead": head,
        "authorizationParent": parent,
        "authorizationPr": int(pr["number"]),
        "executionKey": authorization["executionKey"],
        "designCanonicalSha256": design["canonicalDesignSha256"],
        "executionContractGitBlobSha1": contract_blob,
        "augmentedDataTreeSha256": authorization["augmentedDataTreeSha256"],
        "authorizationPrDraftOpenUnmerged": True,
        "authorizationTimeSeedRecheckPassed": True,
        "solverExecutionPermittedNow": True,
        "githubRerun": False,
        "retryPermitted": False,
        "resumePermitted": False,
        "resultOpeningAuthorizedBeforeExact360": False,
    }
