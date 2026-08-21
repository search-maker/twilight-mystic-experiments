from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from typing import Any


SHA40 = re.compile(r"^[0-9a-f]{40}$")
STAGE = "aerosol-optical-property-sensitivity-v1"
AUTH_PATH = f"experiments/{STAGE}/authorization.json"
EXPECTED_SEED_CANONICAL = "09d011f216187ad48d23e1744a0bb8b9f7c6aa65f0e1ceba1495f8440aa59366"
EXPECTED_ROWS_CANONICAL = "0fad36398515581a9cc723a2fc2c10a1b88f26882501a57a46c7868cc832da9a"


class GuardRefusal(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GuardRefusal(message)


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GuardRefusal(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def evaluate(
    repository_root: Path,
    authorization: dict[str, Any],
    authorization_seed_proof: dict[str, Any],
    live_seed_proof: dict[str, Any],
    context: dict[str, Any],
    paths: dict[str, Path],
) -> dict[str, Any]:
    transport_guard = load("aops_science_transport_auth_guard", paths["authorizationTransportGuard"])
    frozen_auth_guard = load("aops_science_frozen_auth_guard", paths["authorizationGuard"])
    freshness = load("aops_science_freshness", paths["freshness"])
    design_mod = load("aops_science_design", paths["executionDesign"])
    design = design_mod.build_review_execution_design()
    head = context.get("headSha")
    parent = context.get("parentSha")
    ordinal = authorization.get("scientificOrdinal")
    require(isinstance(head, str) and SHA40.fullmatch(head) is not None, "context head SHA invalid")
    require(isinstance(parent, str) and SHA40.fullmatch(parent) is not None, "context parent SHA invalid")
    try:
        transport_guard.validate_enabled_document(repository_root, authorization, parent, paths, authorization_seed_proof)
    except Exception as exc:
        raise GuardRefusal(str(exc)) from exc
    require(context.get("githubActions") is True, "GitHub Actions context required")
    require(context.get("eventName") == "workflow_dispatch", "science requires workflow_dispatch")
    require(context.get("runAttempt") == 1, "science requires attempt 1")
    require(context.get("refName") == authorization.get("dispatchBranch"), "dispatch branch drift")
    require(context.get("dispatchBranchHeadSha") == head, "dispatch branch head drift")
    require(head == context.get("authorizationHead"), "dispatch head differs from authorization head")
    require(parent == authorization.get("exactAuthorizationParentCommit"), "authorization parent drift")
    require(context.get("authorizationCommitParentCount") == 1, "authorization commit must have one parent")
    require(context.get("authorizationCommitChangedPaths") == [AUTH_PATH], "authorization commit changed unexpected paths")
    pr = context.get("pr") or {}
    require(pr.get("state") == "open" and pr.get("draft") is True and pr.get("merged") is False, "authorization PR no longer Draft/open/unmerged")
    require(pr.get("headSha") == head and pr.get("headBranch") == authorization.get("authorizationBranch"), "authorization PR head/branch drift")
    review = context.get("authorizationReview") or {}
    require(review.get("status") == "AUTHORIZATION_REVIEW_PASS_ZERO_RUNTIME", "zero-runtime authorization review pass missing")
    require(review.get("headSha") == head and review.get("prNumber") == pr.get("number"), "authorization review identity drift")
    require(review.get("runAttempt") == 1 and review.get("conclusion") == "success", "exact successful attempt-1 authorization review required")
    require(review.get("scientificRuntimeSetupPerformed") is False and review.get("scientificExecutionPerformed") is False, "authorization review executed runtime")
    try:
        freshness.validate_dispatch(context.get("freshness") or {}, ordinal, head, post_dispatch=True)
    except Exception as exc:
        raise GuardRefusal(str(exc)) from exc
    markers = context.get("issue60Markers") or []
    require(
        len(markers) == 1
        and freshness.matching_marker(markers[0], ordinal, head, parent, int(pr.get("number") or 0)),
        "exact Issue #60 authorization marker missing or drifted",
    )
    require(context.get("priorRunsOnDispatch") == [], "dispatch identity already has prior science run")
    prior_artifacts = context.get("priorCaseArtifactNames")
    require(isinstance(prior_artifacts, list) and not any(str(x).startswith("aops-v1-case-") for x in prior_artifacts), "prior AOPS case artifact exists")
    publisher = context.get("dispatchPublisher") or {}
    require(publisher.get("status") == "AOPS_V1_DISPATCH_PUBLISHER_PASS_ACTUAL_GIT_PUSH", "successful publisher evidence missing")
    require(publisher.get("authorizationHead") == head and publisher.get("authorizationParent") == parent and publisher.get("authorizationPr") == pr.get("number"), "publisher authorization identity drift")
    require(publisher.get("dispatchBranch") == authorization.get("dispatchBranch") and publisher.get("dispatchBranchHead") == head, "publisher dispatch branch/head drift")
    require(publisher.get("actualGitPush") is True and publisher.get("currentConsumedMarkerPosted") is True, "publisher push/consumed-marker proof missing")
    require(publisher.get("scienceTriggerMode") == "EXPLICIT_WORKFLOW_DISPATCH_AFTER_ACTUAL_GIT_PUSH", "publisher science trigger mode drift")
    require(publisher.get("githubTokenPushReliedUponToTriggerScience") is False, "publisher may not rely on token push trigger")
    require(publisher.get("runAttempt") == 1 and publisher.get("conclusion") == "success", "publisher must be successful attempt 1")
    require(publisher.get("scientificRuntimeSetupPerformed") is False and publisher.get("solverExecutionPerformed") is False, "publisher performed scientific runtime")
    comments = context.get("issue60Comments") or []
    consumed = freshness.consumed_marker(ordinal)
    require(sum(1 for row in comments if str(row).strip().lower() == consumed.lower()) == 1, "exactly one dispatch consumed marker required")

    try:
        frozen_auth_guard.validate_seed_authorization_proof(live_seed_proof)
    except Exception as exc:
        raise GuardRefusal(str(exc)) from exc
    require(live_seed_proof.get("auditedMainHead") == head, "live science seed recheck must be bound to exact authorization head")
    require(live_seed_proof.get("candidateSeedCanonicalSha256") == EXPECTED_SEED_CANONICAL, "candidate seed canonical hash drift")
    require(live_seed_proof.get("candidateRowsCanonicalSha256") == EXPECTED_ROWS_CANONICAL, "candidate row canonical hash drift")
    require(live_seed_proof.get("exactHeadTrackedTreeByteScanPassed") is True, "tracked-tree seed scan not passed")
    require(live_seed_proof.get("repositoryGlobalCollisionSurfaceScanPassed") is True, "repository-global seed scan not passed")
    require(live_seed_proof.get("repositoryGlobalDoubleEnumerationStable") is True, "repository-global seed scan unstable")
    require(live_seed_proof.get("repositoryGlobalCollisionCount") == 0, "seed collision detected")
    require(live_seed_proof.get("solverExecutionAuthorized") is False, "seed audit itself may not authorize solver")

    require(design.get("caseCount") == 360 and design.get("groupCount") == 72 and design.get("analysisCellCount") == 24, "frozen design cardinality drift")
    require(design.get("scientificExecutionAuthorized") is False and design.get("solverExecutionAuthorized") is False, "review design crossed execution boundary")
    return {
        "schemaVersion": 1,
        "stageId": f"{STAGE}-execution-guard",
        "status": "EXACT_ONE_USE_AOPS_V1_DISPATCH_AUTHORIZED",
        "scientificOrdinal": ordinal,
        "workflowRunId": context.get("currentRunId"),
        "workflowRunAttempt": 1,
        "executionKey": authorization["executionKey"],
        "authorizationCommitSha": head,
        "authorizationParentCommit": parent,
        "authorizationPr": pr["number"],
        "authorizationPrDraftOpenUnmerged": True,
        "designCanonicalSha256": design["canonicalDesignSha256"],
        "executionContractGitBlobSha1": context.get("executionContractGitBlobSha1"),
        "caseCount": 360,
        "comparisonGroupCount": 72,
        "configuredPhotonHistories": 7_200_000_000,
        "solverExecutionPermittedNow": True,
        "githubRerun": False,
        "retryAllowed": False,
        "resumeAllowed": False,
        "resultOpeningAuthorizedBeforeExact360Aggregate": False,
    }
