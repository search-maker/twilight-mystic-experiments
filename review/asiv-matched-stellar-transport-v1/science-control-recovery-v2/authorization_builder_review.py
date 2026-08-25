#!/usr/bin/env python3
"""Recovery-v2 authorization builder for the matched-stellar one-shot execution.

This is control/governance only. It reuses the already-frozen strict transport and
99-shard batch gates without changing scientific cases, runtime hashes, assets or
acceptance thresholds. Recovery v2 exists only because workflow run 32848973816
failed before solver execution while parsing micromamba 2.9 JSON metadata.
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

EXPECTED_STRICT_GATE_GIT_BLOB_SHA1 = "9bbe4f8fe64f7f32dd3e3e69469a15b30f658dde"
EXPECTED_BATCH_GIT_BLOB_SHA1 = "d1c4f156967e592ee41f4c1a829e7d551a4f7ea7"
EXPECTED_BATCH_CONTRACT_GIT_BLOB_SHA1 = "7214a7e6ff969242cab20d9019ccc522ab96ddde"
EXPECTED_AUTH_REVIEW_WORKFLOW_GIT_BLOB_SHA1 = "f9fefa51ae73a55d91c937fc652a5aa3e3b03c51"
EXPECTED_SCIENCE_WORKFLOW_GIT_BLOB_SHA1 = "e272da7d2dc497f1d06537d7796ef3af2092c965"
SHA40 = re.compile(r"^[0-9a-f]{40}$")

AUTHORIZATION_BRANCH = "authorization/asiv-matched-stellar-transport-recovery-v2"
DISPATCH_BRANCH = "dispatch/asiv-matched-stellar-transport-recovery-v2"
EXECUTION_KEY = "asiv-matched-stellar-transport-recovery-v2-one-shot"
AUTHORIZATION_PATH = "review/asiv-matched-stellar-transport-v1/authorization-recovery-v2.json"
AUTH_REVIEW_WORKFLOW_ACTIVE_PATH = ".github/workflows/asiv-matched-stellar-authorization-review-recovery-v2.yml"
SCIENCE_WORKFLOW_ACTIVE_PATH = ".github/workflows/asiv-matched-stellar-science-recovery-v2.yml"
RECOVERY_FROM_RUN_ID = 32848973816
RECOVERY_REASON = "PRE_SOLVER_MICROMAMBA_METADATA_PARSER_FAILURE"


class AuthorizationBuilderRefusal(RuntimeError):
    pass


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


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
    return _load(STRICT_GATE_PATH, EXPECTED_STRICT_GATE_GIT_BLOB_SHA1, "matched_stellar_recovery_v2_strict_gate")


def load_batch():
    if git_blob_sha1(BATCH_CONTRACT_PATH) != EXPECTED_BATCH_CONTRACT_GIT_BLOB_SHA1:
        raise AuthorizationBuilderRefusal("batch orchestration contract Git blob drift")
    return _load(BATCH_PATH, EXPECTED_BATCH_GIT_BLOB_SHA1, "matched_stellar_recovery_v2_batch")


def validate_active_workflows(root: Path) -> dict[str, str]:
    root = Path(root)
    if root.resolve() != ROOT.resolve():
        raise AuthorizationBuilderRefusal("repository root drift")
    active_auth = root / AUTH_REVIEW_WORKFLOW_ACTIVE_PATH
    active_science = root / SCIENCE_WORKFLOW_ACTIVE_PATH
    if not active_auth.is_file() or not active_science.is_file():
        raise AuthorizationBuilderRefusal("recovery-v2 active workflow missing")
    auth_blob = git_blob_sha1(active_auth)
    science_blob = git_blob_sha1(active_science)
    if auth_blob != EXPECTED_AUTH_REVIEW_WORKFLOW_GIT_BLOB_SHA1:
        raise AuthorizationBuilderRefusal("recovery authorization-review workflow byte drift")
    if science_blob != EXPECTED_SCIENCE_WORKFLOW_GIT_BLOB_SHA1:
        raise AuthorizationBuilderRefusal("recovery science workflow byte drift")
    return {
        "authorizationReviewWorkflowActiveGitBlobSha1": auth_blob,
        "scienceWorkflowActiveGitBlobSha1": science_blob,
    }


def current_control_binding() -> dict[str, Any]:
    if not CONTROL_CONTRACT_PATH.is_file():
        raise AuthorizationBuilderRefusal("recovery control contract is not frozen")
    contract = json.loads(CONTROL_CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract.get("schemaVersion") != 1 or contract.get("stageId") != "asiv-matched-stellar-transport-recovery-v2-science-control":
        raise AuthorizationBuilderRefusal("recovery control contract schema/stage drift")
    if contract.get("status") != "FROZEN_RECOVERY_V2_CONTROL_PRE_SOLVER_INFRASTRUCTURE_FIX":
        raise AuthorizationBuilderRefusal("recovery control contract status drift")
    if contract.get("recoveryFromRunId") != RECOVERY_FROM_RUN_ID or contract.get("recoveryReason") != RECOVERY_REASON:
        raise AuthorizationBuilderRefusal("recovery provenance drift")
    this_blob = git_blob_sha1(Path(__file__).resolve())
    sources = contract.get("sourceBindings") or {}
    expected_sources = {
        "authorizationBuilderGitBlobSha1": this_blob,
        "authorizationReviewWorkflowGitBlobSha1": EXPECTED_AUTH_REVIEW_WORKFLOW_GIT_BLOB_SHA1,
        "scienceWorkflowGitBlobSha1": EXPECTED_SCIENCE_WORKFLOW_GIT_BLOB_SHA1,
        "strictAuthorizationGateGitBlobSha1": EXPECTED_STRICT_GATE_GIT_BLOB_SHA1,
        "batchOrchestrationGitBlobSha1": EXPECTED_BATCH_GIT_BLOB_SHA1,
        "batchOrchestrationContractGitBlobSha1": EXPECTED_BATCH_CONTRACT_GIT_BLOB_SHA1,
    }
    for key, value in expected_sources.items():
        if sources.get(key) != value:
            raise AuthorizationBuilderRefusal(f"recovery control contract binding drift: {key}")
    return {
        "authorizationBuilderGitBlobSha1": this_blob,
        "scienceControlContractGitBlobSha1": git_blob_sha1(CONTROL_CONTRACT_PATH),
        "authorizationReviewWorkflowActiveGitBlobSha1Expected": EXPECTED_AUTH_REVIEW_WORKFLOW_GIT_BLOB_SHA1,
        "scienceWorkflowActiveGitBlobSha1Expected": EXPECTED_SCIENCE_WORKFLOW_GIT_BLOB_SHA1,
        "authorizationReviewWorkflowActivePath": AUTH_REVIEW_WORKFLOW_ACTIVE_PATH,
        "scienceWorkflowActivePath": SCIENCE_WORKFLOW_ACTIVE_PATH,
        "authorizationPath": AUTHORIZATION_PATH,
        "authorizationBranch": AUTHORIZATION_BRANCH,
        "dispatchBranch": DISPATCH_BRANCH,
        "executionKey": EXECUTION_KEY,
        "recoveryFromRunId": RECOVERY_FROM_RUN_ID,
        "recoveryReason": RECOVERY_REASON,
    }


def build_authorization(root: Path, parent_main: str) -> dict[str, Any]:
    root = Path(root)
    if root.resolve() != ROOT.resolve():
        raise AuthorizationBuilderRefusal("repository root drift")
    if SHA40.fullmatch(parent_main or "") is None:
        raise AuthorizationBuilderRefusal("parent main SHA invalid")
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
        "recoveryFromRunId": RECOVERY_FROM_RUN_ID,
        "recoveryReason": RECOVERY_REASON,
        "priorRunSolverExecutionPerformed": False,
        "priorRunScientificShardArtifactCount": 0,
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
    validate_authorization(root, auth, parent_main)
    return auth


def validate_authorization(root: Path, document: dict[str, Any], expected_parent_main: str) -> None:
    root = Path(root)
    if root.resolve() != ROOT.resolve():
        raise AuthorizationBuilderRefusal("repository root drift")
    if SHA40.fullmatch(expected_parent_main or "") is None:
        raise AuthorizationBuilderRefusal("expected parent main SHA invalid")
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
        "recoveryFromRunId": RECOVERY_FROM_RUN_ID,
        "recoveryReason": RECOVERY_REASON,
        "priorRunSolverExecutionPerformed": False,
        "priorRunScientificShardArtifactCount": 0,
        "controlBindings": current_control_binding(),
    }
    for key, value in expected.items():
        if document.get(key) != value:
            raise AuthorizationBuilderRefusal(f"recovery authorization control binding/flag mismatch: {key}")


def main() -> int:
    print(json.dumps({
        "status": "RECOVERY_V2_REVIEW_ONLY_NO_AUTHORIZATION_FILE_CREATED",
        "authorizationPath": AUTHORIZATION_PATH,
        "authorizationBranch": AUTHORIZATION_BRANCH,
        "dispatchBranch": DISPATCH_BRANCH,
        "executionKey": EXECUTION_KEY,
        "recoveryFromRunId": RECOVERY_FROM_RUN_ID,
        "recoveryReason": RECOVERY_REASON,
        "scientificExecutionAuthorizedByThisFile": False,
        "solverExecutionAuthorizedByThisFile": False,
        "dispatchPerformed": False,
        "pandoraHoldoutAccessAllowed": False,
        "productionAuthorized": False,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
