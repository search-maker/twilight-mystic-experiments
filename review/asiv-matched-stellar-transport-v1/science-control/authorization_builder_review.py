#!/usr/bin/env python3
"""Review-only builder/validator for a future matched-stellar authorization.

This module does not write authorization.json and has no execution or dispatch
surface. Tests may build an authorization object in memory to prove that all
already-frozen transport, batch, asset and control bindings can be validated.
A future separate one-file authorization commit is still required.

Real authorization building/validation requires the separately activated active
workflow files to exist and to be Git-blob-identical to the frozen candidates.
Only pre-activation review tests may opt out of that active-file requirement.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
STAGE = HERE.parent
ROOT = STAGE.parents[1]
STRICT_GATE_PATH = STAGE / "execution_authorization_gate_review.py"
BATCH_PATH = STAGE / "batch_orchestration_review.py"
BATCH_CONTRACT_PATH = STAGE / "BATCH_ORCHESTRATION_CONTRACT.review.json"
EXECUTION_CONTRACT_PATH = STAGE / "EXECUTION_TRANSPORT_CONTRACT.review.json"
CONTROL_CONTRACT_PATH = HERE / "SCIENCE_CONTROL_CONTRACT.review.json"
AUTH_REVIEW_WORKFLOW_PATH = HERE / "authorization-review-workflow.yml.review"
SCIENCE_WORKFLOW_PATH = HERE / "science-workflow.yml.review"

EXPECTED_STRICT_GATE_GIT_BLOB_SHA1 = "9bbe4f8fe64f7f32dd3e3e69469a15b30f658dde"
EXPECTED_BATCH_GIT_BLOB_SHA1 = "d1c4f156967e592ee41f4c1a829e7d551a4f7ea7"
EXPECTED_BATCH_CONTRACT_GIT_BLOB_SHA1 = "7214a7e6ff969242cab20d9019ccc522ab96ddde"
EXPECTED_AUTH_REVIEW_WORKFLOW_GIT_BLOB_SHA1 = "6ed68a90f2614dd762b5484e740a146e2cb636cc"
EXPECTED_SCIENCE_WORKFLOW_GIT_BLOB_SHA1 = "396bb79f0f00b36888f809f7f3bff40d62646632"
SHA40 = re.compile(r"^[0-9a-f]{40}$")

AUTHORIZATION_BRANCH = "authorization/asiv-matched-stellar-transport-v1"
DISPATCH_BRANCH = "dispatch/asiv-matched-stellar-transport-v1"
EXECUTION_KEY = "asiv-matched-stellar-transport-v1-one-shot"
AUTHORIZATION_PATH = "review/asiv-matched-stellar-transport-v1/authorization.json"
AUTH_REVIEW_WORKFLOW_ACTIVE_PATH = ".github/workflows/asiv-matched-stellar-authorization-review-v1.yml"
SCIENCE_WORKFLOW_ACTIVE_PATH = ".github/workflows/asiv-matched-stellar-science-v1.yml"


class AuthorizationBuilderRefusal(RuntimeError):
    pass


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path, expected_blob: str, name: str):
    if git_blob_sha1(path) != expected_blob:
        raise AuthorizationBuilderRefusal(f"bound source Git blob drift: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AuthorizationBuilderRefusal(f"cannot load bound module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_strict_gate():
    return _load(STRICT_GATE_PATH, EXPECTED_STRICT_GATE_GIT_BLOB_SHA1, "matched_stellar_control_strict_gate")


def load_batch():
    if git_blob_sha1(BATCH_CONTRACT_PATH) != EXPECTED_BATCH_CONTRACT_GIT_BLOB_SHA1:
        raise AuthorizationBuilderRefusal("batch orchestration contract Git blob drift")
    return _load(BATCH_PATH, EXPECTED_BATCH_GIT_BLOB_SHA1, "matched_stellar_control_batch")


def validate_active_workflows(root: Path) -> dict[str, str]:
    root = Path(root)
    if root.resolve() != ROOT.resolve():
        raise AuthorizationBuilderRefusal("repository root drift")
    active_auth = root / AUTH_REVIEW_WORKFLOW_ACTIVE_PATH
    active_science = root / SCIENCE_WORKFLOW_ACTIVE_PATH
    if not active_auth.is_file():
        raise AuthorizationBuilderRefusal("active authorization-review workflow is absent")
    if not active_science.is_file():
        raise AuthorizationBuilderRefusal("active science workflow is absent")
    auth_blob = git_blob_sha1(active_auth)
    science_blob = git_blob_sha1(active_science)
    if auth_blob != EXPECTED_AUTH_REVIEW_WORKFLOW_GIT_BLOB_SHA1:
        raise AuthorizationBuilderRefusal("active authorization-review workflow bytes differ from frozen candidate")
    if science_blob != EXPECTED_SCIENCE_WORKFLOW_GIT_BLOB_SHA1:
        raise AuthorizationBuilderRefusal("active science workflow bytes differ from frozen candidate")
    return {
        "authorizationReviewWorkflowActiveGitBlobSha1": auth_blob,
        "scienceWorkflowActiveGitBlobSha1": science_blob,
    }


def current_control_binding() -> dict[str, Any]:
    if git_blob_sha1(AUTH_REVIEW_WORKFLOW_PATH) != EXPECTED_AUTH_REVIEW_WORKFLOW_GIT_BLOB_SHA1:
        raise AuthorizationBuilderRefusal("authorization-review workflow candidate byte drift")
    if git_blob_sha1(SCIENCE_WORKFLOW_PATH) != EXPECTED_SCIENCE_WORKFLOW_GIT_BLOB_SHA1:
        raise AuthorizationBuilderRefusal("science workflow candidate byte drift")
    if not CONTROL_CONTRACT_PATH.is_file():
        raise AuthorizationBuilderRefusal("science-control contract is not frozen")
    contract = json.loads(CONTROL_CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract.get("schemaVersion") != 1 or contract.get("stageId") != "asiv-matched-stellar-transport-v1-science-control":
        raise AuthorizationBuilderRefusal("science-control contract schema/stage drift")
    if contract.get("status") != "FROZEN_REVIEW_ONLY_SCIENCE_CONTROL_NO_AUTHORIZATION_NO_DISPATCH":
        raise AuthorizationBuilderRefusal("science-control contract unexpectedly changed authorization state")
    this_blob = git_blob_sha1(Path(__file__).resolve())
    sources = contract.get("sourceBindings") or {}
    expected_sources = {
        "authorizationBuilderGitBlobSha1": this_blob,
        "authorizationReviewWorkflowCandidateGitBlobSha1": EXPECTED_AUTH_REVIEW_WORKFLOW_GIT_BLOB_SHA1,
        "scienceWorkflowCandidateGitBlobSha1": EXPECTED_SCIENCE_WORKFLOW_GIT_BLOB_SHA1,
        "strictAuthorizationGateGitBlobSha1": EXPECTED_STRICT_GATE_GIT_BLOB_SHA1,
        "batchOrchestrationGitBlobSha1": EXPECTED_BATCH_GIT_BLOB_SHA1,
        "batchOrchestrationContractGitBlobSha1": EXPECTED_BATCH_CONTRACT_GIT_BLOB_SHA1,
    }
    for key, value in expected_sources.items():
        if sources.get(key) != value:
            raise AuthorizationBuilderRefusal(f"science-control contract binding drift: {key}")
    return {
        "authorizationBuilderGitBlobSha1": this_blob,
        "scienceControlContractGitBlobSha1": git_blob_sha1(CONTROL_CONTRACT_PATH),
        "authorizationReviewWorkflowCandidateGitBlobSha1": EXPECTED_AUTH_REVIEW_WORKFLOW_GIT_BLOB_SHA1,
        "scienceWorkflowCandidateGitBlobSha1": EXPECTED_SCIENCE_WORKFLOW_GIT_BLOB_SHA1,
        "authorizationReviewWorkflowActivePath": AUTH_REVIEW_WORKFLOW_ACTIVE_PATH,
        "scienceWorkflowActivePath": SCIENCE_WORKFLOW_ACTIVE_PATH,
        "authorizationReviewWorkflowActiveGitBlobSha1Expected": EXPECTED_AUTH_REVIEW_WORKFLOW_GIT_BLOB_SHA1,
        "scienceWorkflowActiveGitBlobSha1Expected": EXPECTED_SCIENCE_WORKFLOW_GIT_BLOB_SHA1,
        "authorizationPath": AUTHORIZATION_PATH,
        "authorizationBranch": AUTHORIZATION_BRANCH,
        "dispatchBranch": DISPATCH_BRANCH,
        "executionKey": EXECUTION_KEY,
    }


def build_authorization(root: Path, parent_main: str, *, require_active_workflows: bool = True) -> dict[str, Any]:
    root = Path(root)
    if root.resolve() != ROOT.resolve():
        raise AuthorizationBuilderRefusal("repository root drift")
    if SHA40.fullmatch(parent_main or "") is None:
        raise AuthorizationBuilderRefusal("parent main SHA invalid")
    if require_active_workflows:
        validate_active_workflows(root)
    strict = load_strict_gate()
    batch = load_batch()
    execution_contract = json.loads(EXECUTION_CONTRACT_PATH.read_text(encoding="utf-8"))
    auth = {
        "schemaVersion": 1,
        "stageId": "asiv-matched-stellar-transport-v1-execution-authorization",
        "status": "AUTHORIZED_ONE_SHOT_SCIENTIFIC_EXECUTION",
        "authorizationBranch": AUTHORIZATION_BRANCH,
        "dispatchBranch": DISPATCH_BRANCH,
        "executionKey": EXECUTION_KEY,
        "exactAuthorizationParentCommit": parent_main,
        "authorizationChangedPath": AUTHORIZATION_PATH,
        "authorizationReviewWorkflowPath": AUTH_REVIEW_WORKFLOW_ACTIVE_PATH,
        "scienceWorkflowPath": SCIENCE_WORKFLOW_ACTIVE_PATH,
        "scientificExecutionAuthorized": True,
        "solverExecutionAuthorized": True,
        "batchExecutionAuthorized": True,
        "dispatchAuthorized": False,
        "automaticDispatch": False,
        "consumed": False,
        "resultOpeningAuthorized": False,
        "productionActivationAuthorized": False,
        "pandoraHoldoutAccessAllowed": False,
        "starsvisibilityMutationAuthorized": False,
        "nativeRebuildAuthorized": False,
        "retryPermitted": False,
        "resumePermitted": False,
        "githubRerunPermitted": False,
        "partialShardInterpretationPermitted": False,
        "partialUniverseValidationPermitted": False,
        "workflowRunAttemptRequired": 1,
        "authorizationPrMustRemainDraftOpenUnmerged": True,
        "authorizationCommitMustChangeExactlyOneFile": True,
        "authorizationParentMustEqualLiveMainAtDispatch": True,
        "authorizationReviewSuccessRequiredBeforeDispatch": True,
        "dispatchBranchMustEqualAuthorizationHead": True,
        "families": list(strict.load_bound_transport().NON_NATIVE_FAMILIES),
        "nativeState": strict.load_bound_transport().NATIVE_STATE,
        "nativeRenderable": False,
        "sourceBindings": strict.current_authorization_binding(),
        "runtimeIdentity": execution_contract["runtimeIdentity"],
        "photometricValidationAssets": execution_contract["photometricValidationAssets"],
        "validationAcceptance": execution_contract["acceptance"],
        "caseUniverse": execution_contract["caseUniverse"],
        "batchBindings": batch.current_batch_binding(),
        "controlBindings": current_control_binding(),
    }
    validate_authorization(root, auth, parent_main, require_active_workflows=require_active_workflows)
    return auth


def validate_authorization(root: Path, document: dict[str, Any], expected_parent_main: str,
                           *, require_active_workflows: bool = True) -> None:
    root = Path(root)
    if root.resolve() != ROOT.resolve():
        raise AuthorizationBuilderRefusal("repository root drift")
    if SHA40.fullmatch(expected_parent_main or "") is None:
        raise AuthorizationBuilderRefusal("expected parent main SHA invalid")
    if require_active_workflows:
        validate_active_workflows(root)
    strict = load_strict_gate()
    batch = load_batch()
    strict.validate_strict_authorization(document)
    batch.validate_batch_authorization(document)
    expected = {
        "authorizationBranch": AUTHORIZATION_BRANCH,
        "dispatchBranch": DISPATCH_BRANCH,
        "executionKey": EXECUTION_KEY,
        "exactAuthorizationParentCommit": expected_parent_main,
        "authorizationChangedPath": AUTHORIZATION_PATH,
        "authorizationReviewWorkflowPath": AUTH_REVIEW_WORKFLOW_ACTIVE_PATH,
        "scienceWorkflowPath": SCIENCE_WORKFLOW_ACTIVE_PATH,
        "dispatchAuthorized": False,
        "automaticDispatch": False,
        "consumed": False,
        "workflowRunAttemptRequired": 1,
        "authorizationPrMustRemainDraftOpenUnmerged": True,
        "authorizationCommitMustChangeExactlyOneFile": True,
        "authorizationParentMustEqualLiveMainAtDispatch": True,
        "authorizationReviewSuccessRequiredBeforeDispatch": True,
        "dispatchBranchMustEqualAuthorizationHead": True,
        "controlBindings": current_control_binding(),
    }
    for key, value in expected.items():
        if document.get(key) != value:
            raise AuthorizationBuilderRefusal(f"authorization control binding/flag mismatch: {key}")


def main() -> int:
    print(json.dumps({
        "status": "REVIEW_ONLY_AUTHORIZATION_BUILDER_NO_AUTHORIZATION_FILE_CREATED",
        "authorizationPath": AUTHORIZATION_PATH,
        "authorizationBranch": AUTHORIZATION_BRANCH,
        "dispatchBranch": DISPATCH_BRANCH,
        "executionKey": EXECUTION_KEY,
        "realAuthorizationRequiresExactActiveWorkflowBytes": True,
        "scientificExecutionAuthorizedByThisFile": False,
        "solverExecutionAuthorizedByThisFile": False,
        "dispatchPerformed": False,
        "authorizationFileCreated": False,
        "pandoraHoldoutAccessAllowed": False,
        "productionAuthorized": False,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
