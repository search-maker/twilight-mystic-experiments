from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path
from typing import Any

STAGE = "aerosol-full-phase-function-sensitivity-v1"
AUTH_PATH = f"experiments/{STAGE}/authorization.json"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
EXPECTED_AUGMENTED_TREE = "5d8bbf8e6b91ec3d405dee36f21a94afbb6e5ec6cd67da2dd5dd541738199d80"
EXPECTED_OPTPROP_ARCHIVE = "11daa1f1f4be0fd4ddf7e881ec2005498049674a1540d37b4b1e8f5e16052c7e"
EXPECTED_SEED_CANONICAL = "d3a3b0f8ddd6f73160e021377c66a1dd6f16ea4f7c8687db7677caf84a033a2b"
EXPECTED_ROWS_CANONICAL = "72a53f2a86be3b0d380528d9ef39893864d1f2ac9e2306611ce0c4afc88ffee4"


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


def seed_proof_raw_sha256(proof: dict[str, Any]) -> str:
    raw = (json.dumps(proof, indent=2, sort_keys=True) + "\n").encode()
    return hashlib.sha256(raw).hexdigest()


def required_binding_paths(root: Path) -> dict[str, Path]:
    stage = root / "experiments" / STAGE
    execd = stage / "execution-candidate"
    return {
        "protocol": stage / "protocol.review.json",
        "analysisContract": stage / "analysis-contract.v1.json",
        "analysis": stage / "analysis.py",
        "levelBAnalysis": stage / "level_b_analysis.mjs",
        "analysisImplementationReview": stage / "analysis-implementation.review.json",
        "reviewCore": stage / "review_core.py",
        "adapter": stage / "adapter.py",
        "executionContract": stage / "execution-contract.review.json",
        "executionTransport": stage / "execution_transport.py",
        "executionDesign": stage / "execution_design.py",
        "runtimeOverlay": execd / "runtime_overlay.py",
        "executor": execd / "executor.py",
        "aggregator": execd / "aggregate_results.py",
        "freshness": execd / "freshness.py",
        "preauthorizationSurface": execd / "preauthorization_surface.py",
        "authorizationGuard": execd / "authorization_guard.py",
        "seedLedger": stage / "candidate-seed-ledger.v1.json",
        "seedLedgerCode": stage / "seed_ledger.py",
        "trackedSeedScanner": stage / "tracked_tree_seed_scan.py",
        "repositoryGlobalSeedScanner": stage / "repository_global_seed_scan.py",
        "runtimeLock": root / "experiments/mystic-batch-v1/runtime-lock.micromamba.json",
        "derivedChannels": root / "experiments/aerosol-family-challenge-v2-r8/derived_channels.py",
        "wavelengthGrid": root / "experiments/aerosol-family-challenge-v2-r8/wavelength-grid-1nm.dat",
    }


def build_bindings(root: Path) -> dict[str, dict[str, str]]:
    bindings: dict[str, dict[str, str]] = {}
    for key, path in required_binding_paths(root).items():
        if not path.is_file():
            raise AuthorizationRefusal(f"required binding file missing: {path}")
        bindings[key] = {
            "path": path.relative_to(root).as_posix(),
            "gitBlobSha1": git_blob_sha1(path),
            "rawSha256": sha256_file(path),
        }
    return bindings


def validate_bindings(root: Path, observed: Any) -> None:
    expected = build_bindings(root)
    if observed != expected:
        raise AuthorizationRefusal("authorization byte bindings do not match exact repository parent")


def validate_seed_proof(proof: dict[str, Any], expected_main: str) -> None:
    design_mod = _load("afpf_execution_design_for_authorization_guard", root_stage() / "execution_design.py")
    try:
        design_mod.validate_seed_authorization_proof(proof, expected_main)
    except Exception as exc:
        raise AuthorizationRefusal(f"authorization-time seed proof invalid: {exc}") from exc


def root_stage() -> Path:
    return Path(__file__).resolve().parent.parent


def build_design(seed_proof: dict[str, Any], expected_main: str) -> dict[str, Any]:
    design_mod = _load("afpf_execution_design_for_authorization_guard", root_stage() / "execution_design.py")
    try:
        return design_mod.build_review_execution_design(seed_proof, expected_main)
    except Exception as exc:
        raise AuthorizationRefusal(f"seeded execution design invalid: {exc}") from exc


def validate_enabled_document(root: Path, auth: dict[str, Any], expected_main: str, seed_proof: dict[str, Any]) -> dict[str, Any]:
    if SHA40.fullmatch(expected_main or "") is None:
        raise AuthorizationRefusal("expected main SHA invalid")
    freshness = _load("afpf_freshness_for_authorization_guard", root / f"experiments/{STAGE}/execution-candidate/freshness.py")
    ordinal = auth.get("scientificOrdinal")
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal <= 0:
        raise AuthorizationRefusal("authorization scientific ordinal invalid")
    if auth.get("schemaVersion") != 1 or auth.get("stageId") != STAGE:
        raise AuthorizationRefusal("authorization identity drift")
    if auth.get("status") != "AUTHORIZED_PENDING_SEPARATE_DISPATCH":
        raise AuthorizationRefusal("authorization status drift")
    if auth.get("authorizationBranch") != freshness.authorization_branch(ordinal):
        raise AuthorizationRefusal("authorization branch drift")
    if auth.get("dispatchBranch") != freshness.dispatch_branch(ordinal):
        raise AuthorizationRefusal("dispatch branch drift")
    if auth.get("executionKey") != freshness.execution_key(ordinal):
        raise AuthorizationRefusal("execution key drift")
    if auth.get("exactAuthorizationParentCommit") != expected_main or auth.get("reviewPackageMainSha") != expected_main:
        raise AuthorizationRefusal("authorization parent/main binding drift")
    if auth.get("exactAuthorizationCommit") is not None:
        raise AuthorizationRefusal("authorization document must be reviewed before exact commit is assigned")
    design = build_design(seed_proof, expected_main)
    if auth.get("authorizationTimeSeedProofRawSha256") != seed_proof_raw_sha256(seed_proof):
        raise AuthorizationRefusal("authorization seed proof raw hash drift")
    if auth.get("candidateSeedCanonicalSha256") != EXPECTED_SEED_CANONICAL:
        raise AuthorizationRefusal("authorization candidate seed canonical hash drift")
    if auth.get("candidateRowsCanonicalSha256") != EXPECTED_ROWS_CANONICAL:
        raise AuthorizationRefusal("authorization candidate row canonical hash drift")
    if auth.get("executionDesignCanonicalSha256") != design.get("canonicalDesignSha256"):
        raise AuthorizationRefusal("authorization/design canonical hash drift")
    if auth.get("augmentedDataTreeSha256") != EXPECTED_AUGMENTED_TREE:
        raise AuthorizationRefusal("authorization augmented data-tree drift")
    if auth.get("officialOptpropArchiveSha256") != EXPECTED_OPTPROP_ARCHIVE:
        raise AuthorizationRefusal("authorization official optprop archive drift")
    validate_bindings(root, auth.get("byteBindings"))
    if auth.get("scientificExecutionAuthorized") is not True or auth.get("solverExecutionAuthorized") is not True:
        raise AuthorizationRefusal("authorization did not enable the separately dispatched science guard")
    required_false = (
        "dispatchAuthorized", "resultOpeningAuthorized", "automaticDispatch", "consumed",
        "githubRerunAllowed", "retryAllowed", "resumeAllowed",
    )
    if any(auth.get(key) is not False for key in required_false):
        raise AuthorizationRefusal("authorization crossed dispatch/result/retry boundary")
    if auth.get("workflowRunAttemptRequired") != 1:
        raise AuthorizationRefusal("authorization attempt requirement drift")
    return design


def review(auth: dict[str, Any], ctx: dict[str, Any], root: Path, seed_proof: dict[str, Any]) -> dict[str, Any]:
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
    expected_branch = _load(
        "afpf_freshness_branch_for_authorization_guard",
        root / f"experiments/{STAGE}/execution-candidate/freshness.py",
    ).authorization_branch(ordinal)
    if not (
        pr.get("state") == "open" and pr.get("draft") is True and pr.get("merged") is False
        and pr.get("headBranch") == expected_branch and pr.get("baseBranch") == "main"
        and pr.get("headRepo") == pr.get("baseRepo") and pr.get("headSha") == head
    ):
        raise AuthorizationRefusal("authorization PR identity drift")
    if ctx.get("runAttempt") != 1 or ctx.get("eventName") != "pull_request" or ctx.get("eventAction") != "opened":
        raise AuthorizationRefusal("authorization review must be one opened attempt-1 PR run")
    if ctx.get("scientificRuntimeSetupPerformed") is not False or ctx.get("scientificExecutionPerformed") is not False:
        raise AuthorizationRefusal("authorization review crossed zero-runtime boundary")
    validate_enabled_document(root, auth, parent, seed_proof)
    freshness = _load("afpf_freshness_review_for_authorization_guard", root / f"experiments/{STAGE}/execution-candidate/freshness.py")
    freshness.validate_authorization_review(ctx.get("freshness") or {}, ordinal, head)
    return {
        "status": "EXACT_ONE_FILE_AFPF_AUTHORIZATION_REVIEW_PASS_ZERO_RUNTIME",
        "scientificOrdinal": ordinal,
        "headSha": head,
        "parentSha": parent,
        "scientificRuntimeSetupPerformed": False,
        "scientificExecutionPerformed": False,
        "solverExecutionPerformed": False,
        "ordinalAllocatedReservedOrConsumedByReview": False,
    }
