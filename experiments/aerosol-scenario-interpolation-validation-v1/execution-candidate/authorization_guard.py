from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path
from typing import Any

STAGE = "aerosol-scenario-interpolation-validation-v1"
AUTH_PATH = f"experiments/{STAGE}/authorization.json"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
EXPECTED_AUGMENTED_TREE = "5d8bbf8e6b91ec3d405dee36f21a94afbb6e5ec6cd67da2dd5dd541738199d80"
EXPECTED_OPTPROP_ARCHIVE = "11daa1f1f4be0fd4ddf7e881ec2005498049674a1540d37b4b1e8f5e16052c7e"
EXPECTED_SEED_CANONICAL = "cd04e0f7a206ca7fd49f3b00eae8de6d49ba8dc1427c21e5c7530adf03837040"
EXPECTED_ROWS_CANONICAL = "d88da58b6fe896b8324df224c5e849399b770783d4d63bb2bc4a7b01aa844e8b"
EXPECTED_SELECTED_MODEL = "0b11a1691bfd2d9e3f073c786044bacedd3e9210bcb0660c76f21c34128a61af"


class AuthorizationRefusal(RuntimeError):
    pass


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AuthorizationRefusal(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def proof_raw_sha256(proof: dict[str, Any]) -> str:
    raw = (json.dumps(proof, indent=2, sort_keys=True) + "\n").encode()
    return hashlib.sha256(raw).hexdigest()


def required_binding_paths(root: Path) -> dict[str, Path]:
    stage = root / "experiments" / STAGE
    execd = stage / "execution-candidate"
    return {
        "protocol": root / "review/aerosol-scenario-interpolation-validation-v1/protocol.review.json",
        "geometrySource": root / "review/aerosol-scenario-interpolation-validation-v1/geometry-source.review.json",
        "selectedModel": root / "review/aerosol-scenario-interpolation-validation-v1/selected-model-v1.json",
        "selectedModelEvaluator": root / "review/aerosol-scenario-interpolation-validation-v1/evaluate_selected_model_v1.py",
        "trainingSelector": root / "review/asiv-v1-training-selector-implementation/select_training_model_v1.py",
        "trainingSelectorContract": root / "review/asiv-v1-training-selector-implementation/selector-contract-v1.json",
        "executionContract": stage / "execution-contract.review.json",
        "executionTransport": stage / "execution_transport.py",
        "executionDesign": stage / "execution_design.py",
        "adapter": stage / "adapter.py",
        "analysis": stage / "analysis.py",
        "levelBRunner": stage / "level_b_runner.mjs",
        "executor": execd / "executor.py",
        "aggregator": execd / "aggregate_results.py",
        "freshness": execd / "freshness.py",
        "controlSurface": execd / "control_surface.py",
        "authorizationGuard": execd / "authorization_guard.py",
        "buildAuthorization": execd / "build_authorization.py",
        "dispatchGuard": execd / "dispatch_guard.py",
        "scienceGuard": execd / "science_guard.py",
        "preauthorizationSurface": stage / "preauthorization_surface.py",
        "seedLedger": stage / "candidate-seed-ledger.v1.json",
        "seedLedgerCode": stage / "seed_ledger.py",
        "trackedSeedScanner": stage / "tracked_tree_seed_scan.py",
        "repositoryGlobalSeedScanner": stage / "repository_global_seed_scan.py",
        "geometryCollisionAudit": stage / "geometry_collision_audit.py",
        "freshnessProofBuilder": stage / "build_freshness_proof.py",
        "runtimeOverlay": root / "experiments/aerosol-full-phase-function-sensitivity-v1/execution-candidate/runtime_overlay.py",
        "runtimeLock": root / "experiments/mystic-batch-v1/runtime-lock.micromamba.json",
        "derivedChannels": root / "experiments/aerosol-family-challenge-v2-r8/derived_channels.py",
        "wavelengthGrid": root / "experiments/aerosol-family-challenge-v2-r8/wavelength-grid-1nm.dat",
        "processRunner": root / "experiments/aerosol-family-challenge-v2-r8-timeout-recovery-v1/execution-candidate/process_runner.py",
        "elevationTransform": root / "experiments/mystic-batch-v1/twilight_surrogate_tier1_execution_adapter.py",
        "afpfReferenceAdapter": root / "experiments/aerosol-full-phase-function-sensitivity-v1/adapter.py",
        "boundHumanThreshold": root / "experiments/aerosol-full-phase-function-sensitivity-v1-analysis-recovery-v1/bound-human-threshold.mjs",
        "authorizationProposalWorkflow": root / ".github/workflows/asiv-v1-authorization-proposal.yml",
        "authorizationReviewWorkflow": root / ".github/workflows/asiv-v1-authorization-review.yml",
        "dispatchPublisherWorkflow": root / ".github/workflows/asiv-v1-dispatch-publisher.yml",
        "scientificExecutionWorkflow": root / ".github/workflows/asiv-v1-execution.yml",
    }


def build_bindings(root: Path) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for key, path in required_binding_paths(root).items():
        if not path.is_file():
            raise AuthorizationRefusal(f"required ASIV binding missing: {path}")
        out[key] = {
            "path": path.relative_to(root).as_posix(),
            "gitBlobSha1": git_blob_sha1(path),
            "rawSha256": sha256_file(path),
        }
    return out


def validate_bindings(root: Path, observed: Any) -> None:
    if observed != build_bindings(root):
        raise AuthorizationRefusal("authorization byte bindings do not match exact repository parent")


def validate_enabled_document(root: Path, auth: dict[str, Any], expected_main: str, freshness_proof: dict[str, Any]) -> dict[str, Any]:
    if SHA40.fullmatch(expected_main or "") is None:
        raise AuthorizationRefusal("expected main SHA invalid")
    stage = root / "experiments" / STAGE
    execd = stage / "execution-candidate"
    freshness = _load("asiv_freshness_for_auth_guard", execd / "freshness.py")
    design_mod = _load("asiv_design_for_auth_guard", stage / "execution_design.py")
    ordinal = auth.get("scientificOrdinal")
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal <= 0:
        raise AuthorizationRefusal("authorization scientific ordinal invalid")
    if auth.get("schemaVersion") != 1 or auth.get("stageId") != STAGE or auth.get("status") != "AUTHORIZED_PENDING_SEPARATE_DISPATCH":
        raise AuthorizationRefusal("authorization identity/status drift")
    if auth.get("authorizationBranch") != freshness.authorization_branch(ordinal) or auth.get("dispatchBranch") != freshness.dispatch_branch(ordinal) or auth.get("executionKey") != freshness.execution_key(ordinal):
        raise AuthorizationRefusal("authorization branch/execution identity drift")
    if auth.get("exactAuthorizationParentCommit") != expected_main or auth.get("reviewPackageMainSha") != expected_main:
        raise AuthorizationRefusal("authorization exact-parent binding drift")
    if auth.get("exactAuthorizationCommit") is not None:
        raise AuthorizationRefusal("authorization document must be reviewed before exact commit is assigned")
    design_mod.validate_freshness_proof(freshness_proof, expected_main)
    design = design_mod.build_review_execution_design(freshness_proof, expected_main)
    if auth.get("authorizationTimeFreshnessProofRawSha256") != proof_raw_sha256(freshness_proof):
        raise AuthorizationRefusal("authorization freshness proof raw hash drift")
    if auth.get("candidateSeedCanonicalSha256") != EXPECTED_SEED_CANONICAL or auth.get("candidateRowsCanonicalSha256") != EXPECTED_ROWS_CANONICAL:
        raise AuthorizationRefusal("authorization candidate seed identity drift")
    if auth.get("executionDesignCanonicalSha256") != design.get("canonicalDesignSha256"):
        raise AuthorizationRefusal("authorization/design canonical hash drift")
    if auth.get("selectedModelCanonicalSha256") != EXPECTED_SELECTED_MODEL or auth.get("holdoutGeometryCount") != 8 or auth.get("caseCount") != 120 or auth.get("groupCount") != 24:
        raise AuthorizationRefusal("ASIV selected-model or execution cardinality drift")
    if auth.get("augmentedDataTreeSha256") != EXPECTED_AUGMENTED_TREE or auth.get("officialOptpropArchiveSha256") != EXPECTED_OPTPROP_ARCHIVE:
        raise AuthorizationRefusal("ASIV OPAC source identity drift")
    validate_bindings(root, auth.get("byteBindings"))
    if auth.get("scientificExecutionAuthorized") is not True or auth.get("solverExecutionAuthorized") is not True:
        raise AuthorizationRefusal("authorization did not enable only the separately dispatched science guard")
    for key in ("dispatchAuthorized", "resultOpeningAuthorized", "automaticDispatch", "consumed", "githubRerunAllowed", "retryAllowed", "resumeAllowed"):
        if auth.get(key) is not False:
            raise AuthorizationRefusal(f"authorization crossed closed boundary: {key}")
    if auth.get("workflowRunAttemptRequired") != 1 or auth.get("postHoldoutRetuningAllowed") is not False or auth.get("productionAuthorized") is not False:
        raise AuthorizationRefusal("authorization attempt/retuning/production boundary drift")
    return design


def review(auth: dict[str, Any], ctx: dict[str, Any], root: Path, parent_freshness_proof: dict[str, Any]) -> dict[str, Any]:
    parent = str(ctx.get("parentSha") or "")
    head = str(ctx.get("headSha") or "")
    if SHA40.fullmatch(parent) is None or SHA40.fullmatch(head) is None:
        raise AuthorizationRefusal("authorization review commit identity invalid")
    if ctx.get("liveMain") != parent or ctx.get("parentCount") != 1:
        raise AuthorizationRefusal("authorization must be one direct child of live main")
    if ctx.get("changedPaths") != [AUTH_PATH] or ctx.get("authorizationPath") != AUTH_PATH:
        raise AuthorizationRefusal("authorization review requires exactly one changed authorization file")
    pr = ctx.get("pr") or {}
    ordinal = auth.get("scientificOrdinal")
    freshness = _load("asiv_freshness_review", root / f"experiments/{STAGE}/execution-candidate/freshness.py")
    expected_branch = freshness.authorization_branch(int(ordinal))
    if not (pr.get("state") == "open" and pr.get("draft") is True and pr.get("merged") is False and pr.get("headBranch") == expected_branch and pr.get("baseBranch") == "main" and pr.get("headRepo") == pr.get("baseRepo") and pr.get("headSha") == head):
        raise AuthorizationRefusal("authorization PR identity drift")
    if ctx.get("runAttempt") != 1 or ctx.get("eventName") != "pull_request" or ctx.get("eventAction") != "opened":
        raise AuthorizationRefusal("authorization review must be one opened attempt-1 PR run")
    if ctx.get("scientificRuntimeSetupPerformed") is not False or ctx.get("scientificExecutionPerformed") is not False:
        raise AuthorizationRefusal("authorization review crossed zero-runtime boundary")
    validate_enabled_document(root, auth, parent, parent_freshness_proof)
    design_mod = _load("asiv_design_live_review", root / f"experiments/{STAGE}/execution_design.py")
    design_mod.validate_freshness_proof(ctx.get("liveFreshnessProof") or {}, head)
    freshness.validate_authorization_review(ctx.get("freshness") or {}, int(ordinal), head)
    return {
        "status": "EXACT_ONE_FILE_ASIV_AUTHORIZATION_REVIEW_PASS_ZERO_RUNTIME",
        "scientificOrdinal": int(ordinal),
        "headSha": head,
        "parentSha": parent,
        "scientificRuntimeSetupPerformed": False,
        "scientificExecutionPerformed": False,
        "solverExecutionPerformed": False,
        "ordinalAllocatedReservedOrConsumedByReview": False,
        "authorizationTimeSeedRecheckPassed": True,
        "authorizationTimeGeometryRecheckPassed": True,
    }
