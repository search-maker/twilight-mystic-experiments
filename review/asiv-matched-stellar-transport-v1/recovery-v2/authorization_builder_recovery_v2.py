#!/usr/bin/env python3
"""Review-only authorization builder for matched-stellar pre-solver recovery v2.

Recovery v2 is not a rerun/resume of the failed v1 workflow. It can authorize
one new one-shot execution only after v1 is independently proven to have failed
before any stellar solver case ran. Scientific source bytes, runtime identity,
case universe and acceptance gates are inherited unchanged from v1.
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
PARSER_PATH = HERE / "micromamba_list_parser_v2.py"
CONTROL_CONTRACT_PATH = HERE / "RECOVERY_CONTROL_CONTRACT.review.json"
AUTH_REVIEW_WORKFLOW_PATH = HERE / "authorization-review-workflow-v2.yml.review"
SCIENCE_WORKFLOW_PATH = HERE / "science-workflow-v2.yml.review"

EXPECTED_STRICT_GATE_GIT_BLOB_SHA1 = "9bbe4f8fe64f7f32dd3e3e69469a15b30f658dde"
EXPECTED_BATCH_GIT_BLOB_SHA1 = "d1c4f156967e592ee41f4c1a829e7d551a4f7ea7"
EXPECTED_BATCH_CONTRACT_GIT_BLOB_SHA1 = "7214a7e6ff969242cab20d9019ccc522ab96ddde"
EXPECTED_PARSER_GIT_BLOB_SHA1 = "531a27296e7ba4747d8d28b1c4d9beef7cbbd33a"
EXPECTED_AUTH_REVIEW_WORKFLOW_GIT_BLOB_SHA1 = "a334c8d4537f4503a502978f106daf83c87a1c9e"
EXPECTED_SCIENCE_WORKFLOW_GIT_BLOB_SHA1 = "91fc9bc11102cc30db9c3ed46a2ee9290747c986"
SHA40 = re.compile(r"^[0-9a-f]{40}$")

AUTHORIZATION_BRANCH = "authorization/asiv-matched-stellar-transport-recovery-v2"
DISPATCH_BRANCH = "dispatch/asiv-matched-stellar-transport-recovery-v2"
EXECUTION_KEY = "asiv-matched-stellar-transport-recovery-v2-one-shot"
AUTHORIZATION_PATH = "review/asiv-matched-stellar-transport-v1/authorization-recovery-v2.json"
AUTH_REVIEW_WORKFLOW_ACTIVE_PATH = ".github/workflows/asiv-matched-stellar-authorization-review-recovery-v2.yml"
SCIENCE_WORKFLOW_ACTIVE_PATH = ".github/workflows/asiv-matched-stellar-science-recovery-v2.yml"
PRIOR_FAILED_RUN_ID = 32848973816
PRIOR_FAILED_RUN_HEAD_SHA = "30b7c491f9c0f7ae331d7346f8d001c74a9cb905"


class RecoveryAuthorizationBuilderRefusal(RuntimeError):
    pass


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def _load(path: Path, expected_blob: str, name: str):
    if git_blob_sha1(path) != expected_blob:
        raise RecoveryAuthorizationBuilderRefusal(f"bound source Git blob drift: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RecoveryAuthorizationBuilderRefusal(f"cannot load bound module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_strict_gate():
    return _load(STRICT_GATE_PATH, EXPECTED_STRICT_GATE_GIT_BLOB_SHA1, "matched_stellar_recovery_strict_gate")


def load_batch():
    if git_blob_sha1(BATCH_CONTRACT_PATH) != EXPECTED_BATCH_CONTRACT_GIT_BLOB_SHA1:
        raise RecoveryAuthorizationBuilderRefusal("batch orchestration contract Git blob drift")
    return _load(BATCH_PATH, EXPECTED_BATCH_GIT_BLOB_SHA1, "matched_stellar_recovery_batch")


def validate_recovery_parser() -> str:
    observed = git_blob_sha1(PARSER_PATH)
    if observed != EXPECTED_PARSER_GIT_BLOB_SHA1:
        raise RecoveryAuthorizationBuilderRefusal("micromamba recovery parser Git blob drift")
    return observed


def validate_active_workflows(root: Path) -> dict[str, str]:
    root = Path(root)
    if root.resolve() != ROOT.resolve():
        raise RecoveryAuthorizationBuilderRefusal("repository root drift")
    active_auth = root / AUTH_REVIEW_WORKFLOW_ACTIVE_PATH
    active_science = root / SCIENCE_WORKFLOW_ACTIVE_PATH
    if not active_auth.is_file() or not active_science.is_file():
        raise RecoveryAuthorizationBuilderRefusal("exact recovery active workflows are absent")
    auth_blob = git_blob_sha1(active_auth)
    science_blob = git_blob_sha1(active_science)
    if auth_blob != EXPECTED_AUTH_REVIEW_WORKFLOW_GIT_BLOB_SHA1:
        raise RecoveryAuthorizationBuilderRefusal("active recovery authorization-review workflow byte drift")
    if science_blob != EXPECTED_SCIENCE_WORKFLOW_GIT_BLOB_SHA1:
        raise RecoveryAuthorizationBuilderRefusal("active recovery science workflow byte drift")
    return {
        "authorizationReviewWorkflowActiveGitBlobSha1": auth_blob,
        "scienceWorkflowActiveGitBlobSha1": science_blob,
    }


def _load_control_contract() -> dict[str, Any]:
    if not CONTROL_CONTRACT_PATH.is_file():
        raise RecoveryAuthorizationBuilderRefusal("recovery control contract is absent")
    contract = json.loads(CONTROL_CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract.get("schemaVersion") != 1 or contract.get("stageId") != "asiv-matched-stellar-transport-presolver-recovery-v2-control":
        raise RecoveryAuthorizationBuilderRefusal("recovery control contract schema/stage drift")
    if contract.get("status") != "FROZEN_REVIEW_ONLY_PRESOLVER_RECOVERY_V2_NO_AUTHORIZATION_NO_DISPATCH":
        raise RecoveryAuthorizationBuilderRefusal("recovery control contract unexpectedly changed authorization state")
    return contract


def current_control_binding() -> dict[str, Any]:
    validate_recovery_parser()
    if git_blob_sha1(AUTH_REVIEW_WORKFLOW_PATH) != EXPECTED_AUTH_REVIEW_WORKFLOW_GIT_BLOB_SHA1:
        raise RecoveryAuthorizationBuilderRefusal("recovery authorization-review workflow candidate byte drift")
    if git_blob_sha1(SCIENCE_WORKFLOW_PATH) != EXPECTED_SCIENCE_WORKFLOW_GIT_BLOB_SHA1:
        raise RecoveryAuthorizationBuilderRefusal("recovery science workflow candidate byte drift")
    contract = _load_control_contract()
    this_blob = git_blob_sha1(Path(__file__).resolve())
    sources = contract.get("sourceBindings") or {}
    expected_sources = {
        "authorizationBuilderGitBlobSha1": this_blob,
        "micromambaParserGitBlobSha1": EXPECTED_PARSER_GIT_BLOB_SHA1,
        "authorizationReviewWorkflowCandidateGitBlobSha1": EXPECTED_AUTH_REVIEW_WORKFLOW_GIT_BLOB_SHA1,
        "scienceWorkflowCandidateGitBlobSha1": EXPECTED_SCIENCE_WORKFLOW_GIT_BLOB_SHA1,
        "strictAuthorizationGateGitBlobSha1": EXPECTED_STRICT_GATE_GIT_BLOB_SHA1,
        "batchOrchestrationGitBlobSha1": EXPECTED_BATCH_GIT_BLOB_SHA1,
        "batchOrchestrationContractGitBlobSha1": EXPECTED_BATCH_CONTRACT_GIT_BLOB_SHA1,
    }
    for key, value in expected_sources.items():
        if sources.get(key) != value:
            raise RecoveryAuthorizationBuilderRefusal(f"recovery control contract binding drift: {key}")
    evidence = contract.get("recoveryEvidence") or {}
    if evidence.get("priorRunId") != PRIOR_FAILED_RUN_ID or evidence.get("priorHeadSha") != PRIOR_FAILED_RUN_HEAD_SHA:
        raise RecoveryAuthorizationBuilderRefusal("prior v1 recovery evidence identity drift")
    if evidence.get("priorSolverExecutionObserved") is not False or evidence.get("priorScientificShardArtifactCount") != 0:
        raise RecoveryAuthorizationBuilderRefusal("recovery contract does not preserve pre-solver failure boundary")
    return {
        "authorizationBuilderGitBlobSha1": this_blob,
        "recoveryControlContractGitBlobSha1": git_blob_sha1(CONTROL_CONTRACT_PATH),
        "micromambaParserGitBlobSha1": EXPECTED_PARSER_GIT_BLOB_SHA1,
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
        "recoveryVersion": 2,
        "priorFailedScienceRunId": PRIOR_FAILED_RUN_ID,
    }


def build_authorization(root: Path, parent_main: str, *, require_active_workflows: bool = True) -> dict[str, Any]:
    root = Path(root)
    if root.resolve() != ROOT.resolve():
        raise RecoveryAuthorizationBuilderRefusal("repository root drift")
    if SHA40.fullmatch(parent_main or "") is None:
        raise RecoveryAuthorizationBuilderRefusal("parent main SHA invalid")
    if require_active_workflows:
        validate_active_workflows(root)
    strict = load_strict_gate()
    batch = load_batch()
    contract = _load_control_contract()
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
        "recoveryVersion": 2,
        "recoveryPriorRunId": PRIOR_FAILED_RUN_ID,
        "recoveryPriorRunWasPreSolverFailure": True,
        "recoveryEvidence": contract["recoveryEvidence"],
    }
    validate_authorization(root, auth, parent_main, require_active_workflows=require_active_workflows)
    return auth


def validate_authorization(root: Path, document: dict[str, Any], expected_parent_main: str,
                           *, require_active_workflows: bool = True) -> None:
    root = Path(root)
    if root.resolve() != ROOT.resolve():
        raise RecoveryAuthorizationBuilderRefusal("repository root drift")
    if SHA40.fullmatch(expected_parent_main or "") is None:
        raise RecoveryAuthorizationBuilderRefusal("expected parent main SHA invalid")
    if require_active_workflows:
        validate_active_workflows(root)
    strict = load_strict_gate()
    batch = load_batch()
    contract = _load_control_contract()
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
        "recoveryVersion": 2,
        "recoveryPriorRunId": PRIOR_FAILED_RUN_ID,
        "recoveryPriorRunWasPreSolverFailure": True,
        "recoveryEvidence": contract["recoveryEvidence"],
    }
    for key, value in expected.items():
        if document.get(key) != value:
            raise RecoveryAuthorizationBuilderRefusal(f"recovery authorization control binding/flag mismatch: {key}")


def main() -> int:
    print(json.dumps({
        "status": "REVIEW_ONLY_PRESOLVER_RECOVERY_V2_BUILDER_NO_AUTHORIZATION_FILE_CREATED",
        "authorizationPath": AUTHORIZATION_PATH,
        "authorizationBranch": AUTHORIZATION_BRANCH,
        "dispatchBranch": DISPATCH_BRANCH,
        "executionKey": EXECUTION_KEY,
        "priorFailedScienceRunId": PRIOR_FAILED_RUN_ID,
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
