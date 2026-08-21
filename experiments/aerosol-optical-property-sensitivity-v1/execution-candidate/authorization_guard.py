from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path
from typing import Any


SHA40 = re.compile(r"^[0-9a-f]{40}$")
STAGE = "aerosol-optical-property-sensitivity-v1"
AUTH_PATH = f"experiments/{STAGE}/authorization.json"
EXPECTED_SEED_CANONICAL = "09d011f216187ad48d23e1744a0bb8b9f7c6aa65f0e1ceba1495f8440aa59366"
EXPECTED_ROWS_CANONICAL = "0fad36398515581a9cc723a2fc2c10a1b88f26882501a57a46c7868cc832da9a"
EXPECTED_RUNTIME_LOCK_RAW_SHA256 = "3b5fbec964642b04c73a6423b3355dbcc4ba5e84f9614f6d74420491bacc20c5"


class AuthorizationRefusal(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuthorizationRefusal(message)


def raw_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_freshness(path: Path):
    spec = importlib.util.spec_from_file_location("aops_v1_freshness_for_authorization", path)
    if spec is None or spec.loader is None:
        raise AuthorizationRefusal("cannot load AOPS freshness guard")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def validate_seed_authorization_proof(proof: dict[str, Any]) -> None:
    require(proof.get("stageId") == f"{STAGE}-seed-authorization-recheck", "seed authorization proof stage drift")
    require(proof.get("status") == "PASS_CANDIDATE_SEEDS_AUTHORIZATION_RECHECK_NOT_ALLOCATED", "authorization-time seed proof missing")
    require(proof.get("candidateSeedCanonicalSha256") == EXPECTED_SEED_CANONICAL, "authorization seed canonical hash drift")
    require(proof.get("candidateRowsCanonicalSha256") == EXPECTED_ROWS_CANONICAL, "authorization seed-row canonical hash drift")
    require(proof.get("candidateSeedCount") == 72, "authorization seed count drift")
    require(proof.get("allCollisionCountersZero") is True, "authorization seed collision counter drift")
    require(proof.get("exactHeadTrackedTreeByteScanPassed") is True, "authorization tracked-tree scan did not pass")
    require(proof.get("repositoryGlobalCollisionSurfaceScanPassed") is True, "authorization global seed scan did not pass")
    require(proof.get("repositoryGlobalCollisionCount") == 0, "authorization global seed collision exists")
    require(proof.get("repositoryGlobalDoubleEnumerationStable") is True, "authorization global seed enumeration unstable")
    require(proof.get("auditedBranchHeadMatchesRepositoryHead") is True, "authorization seed proof head mismatch")
    require(proof.get("scientificOrdinalAllocated") is False, "seed recheck may not allocate ordinal")
    require(proof.get("authorizationCreated") is False, "seed recheck may not create authorization")
    require(proof.get("dispatchCreated") is False, "seed recheck may not dispatch")
    require(proof.get("solverExecutionAuthorized") is False, "seed recheck may not authorize solver")


def validate_enabled_document(
    authorization: dict[str, Any],
    live_main: str,
    paths: dict[str, Path],
    seed_proof: dict[str, Any],
) -> None:
    freshness = load_freshness(paths["freshness"])
    ordinal = authorization.get("scientificOrdinal")
    require(isinstance(ordinal, int) and ordinal > 0, "authorization ordinal invalid")
    require(authorization.get("schemaVersion") == 1, "authorization schema drift")
    require(authorization.get("stageId") == f"{STAGE}-authorization", "authorization stage drift")
    require(authorization.get("status") == "AUTHORIZED_PENDING_SEPARATE_DISPATCH", "authorization status drift")
    require(authorization.get("repositoryFullName") == "search-maker/twilight-mystic-experiments", "authorization repository drift")
    require(authorization.get("enabled") is True, "authorization is not enabled")
    require(authorization.get("scientificExecutionAuthorized") is True, "scientific execution authorization missing")
    require(authorization.get("solverExecutionAuthorized") is True, "solver authorization missing")
    require(authorization.get("dispatchAuthorized") is False, "authorization document may not authorize dispatch")
    require(authorization.get("resultOpeningAuthorized") is False, "authorization document may not open results")
    require(authorization.get("automaticDispatch") is False, "automatic dispatch forbidden")
    require(authorization.get("consumed") is False, "authorization already consumed")
    require(authorization.get("executionKey") == freshness.execution_key(ordinal), "execution key drift")
    require(authorization.get("authorizationBranch") == freshness.authorization_branch(ordinal), "authorization branch drift")
    require(authorization.get("dispatchBranch") == freshness.dispatch_branch(ordinal), "dispatch branch drift")
    require(authorization.get("exactAuthorizationParentCommit") == live_main, "authorization parent is not then-live main")
    require(authorization.get("reviewPackageMainSha") == live_main, "authorization review-package main binding drift")
    require(authorization.get("exactAuthorizationCommit") is None, "authorization document must not embed its own commit SHA")

    validate_seed_authorization_proof(seed_proof)
    require(authorization.get("candidateSeedCanonicalSha256") == EXPECTED_SEED_CANONICAL, "authorization candidate seed hash drift")
    require(authorization.get("candidateRowsCanonicalSha256") == EXPECTED_ROWS_CANONICAL, "authorization candidate row hash drift")
    require(authorization.get("authorizationTimeSeedProofRawSha256") == raw_sha(paths["seedAuthorizationProof"]), "authorization seed-proof byte binding drift")

    design_mod_spec = importlib.util.spec_from_file_location("aops_v1_design_for_authorization", paths["executionDesign"])
    if design_mod_spec is None or design_mod_spec.loader is None:
        raise AuthorizationRefusal("cannot load frozen execution design")
    design_mod = importlib.util.module_from_spec(design_mod_spec)
    design_mod_spec.loader.exec_module(design_mod)
    design = design_mod.build_review_execution_design()
    require(authorization.get("executionDesignCanonicalSha256") == design.get("canonicalDesignSha256"), "authorization execution-design hash drift")

    for field, key in (
        ("reviewFreezeRawSha256", "freeze"),
        ("executionContractRawSha256", "executionContract"),
        ("adapterRawSha256", "adapter"),
        ("executorRawSha256", "executor"),
        ("aggregatorRawSha256", "aggregator"),
        ("analysisRawSha256", "analysis"),
        ("analysisContractRawSha256", "analysisContract"),
        ("levelBAnalysisRawSha256", "levelBAnalysis"),
        ("authorizationGuardRawSha256", "authorizationGuard"),
        ("freshnessGuardRawSha256", "freshness"),
    ):
        require(authorization.get(field) == raw_sha(paths[key]), f"authorization byte binding drift: {field}")

    require(authorization.get("runtimeLockRawSha256") == EXPECTED_RUNTIME_LOCK_RAW_SHA256, "runtime lock binding drift")
    for key in (
        "githubRerunAllowed",
        "retryAllowed",
        "resumeAllowed",
        "adaptiveCaseAdditionAllowed",
        "postResultRuleChangeAllowed",
        "r8ModificationAuthorized",
    ):
        require(authorization.get(key) is False, f"closed authorization boundary drift: {key}")


def preauthorize(context: dict[str, Any], ordinal: int, paths: dict[str, Path]) -> dict[str, Any]:
    freshness = load_freshness(paths["freshness"])
    seed_proof = json.loads(paths["seedAuthorizationProof"].read_text())
    validate_seed_authorization_proof(seed_proof)
    freshness.validate_preauthorization(context.get("freshness") or {}, ordinal)
    require(context.get("authorizationCreated") is False, "authorization already created")
    require(context.get("scientificRuntimeSetupPerformed") is False, "preauthorization may not set up runtime")
    require(context.get("scientificExecutionPerformed") is False, "preauthorization may not execute science")
    return {
        "status": "PREAUTHORIZATION_FRESHNESS_PASS_AUTHORIZATION_CREATION_PERMITTED",
        "scientificOrdinal": ordinal,
        "authorizationBranch": freshness.authorization_branch(ordinal),
        "dispatchBranch": freshness.dispatch_branch(ordinal),
        "executionKey": freshness.execution_key(ordinal),
        "authorizationCreationPermitted": True,
        "scientificExecutionPerformed": False,
        "ordinalAllocatedReservedOrConsumedByReview": False,
    }


def review(
    authorization: dict[str, Any],
    context: dict[str, Any],
    paths: dict[str, Path],
) -> dict[str, Any]:
    freshness = load_freshness(paths["freshness"])
    ordinal = authorization.get("scientificOrdinal")
    live_main = context.get("liveMain")
    head = context.get("headSha")
    parent = context.get("parentSha")
    pr = context.get("pr") or {}
    require(isinstance(live_main, str) and SHA40.fullmatch(live_main) is not None, "live main invalid")
    require(isinstance(head, str) and SHA40.fullmatch(head) is not None, "authorization head invalid")
    require(parent == live_main, "authorization commit parent is not then-live main")
    require(context.get("parentCount") == 1, "authorization commit must have exactly one parent")
    require(context.get("changedPaths") == [AUTH_PATH], "authorization commit must change exactly one authorization path")
    require(context.get("authorizationPath") == AUTH_PATH, "authorization path drift")
    seed_proof = json.loads(paths["seedAuthorizationProof"].read_text())
    validate_enabled_document(authorization, live_main, paths, seed_proof)
    require(pr.get("number", 0) > 0, "authorization PR number invalid")
    require(pr.get("state") == "open" and pr.get("draft") is True and pr.get("merged") is False, "authorization PR must remain Draft/open/unmerged")
    require(pr.get("headBranch") == freshness.authorization_branch(ordinal) and pr.get("baseBranch") == "main", "authorization PR branch/base drift")
    require(pr.get("headRepo") == authorization["repositoryFullName"] and pr.get("baseRepo") == authorization["repositoryFullName"], "authorization PR must be same-repository")
    require(pr.get("headSha") == head, "authorization PR head mismatch")
    require(context.get("runAttempt") == 1, "authorization review must be attempt 1")
    require(context.get("eventName") == "pull_request" and context.get("eventAction") == "opened", "authorization review must be PR opened event")
    require(context.get("scientificRuntimeSetupPerformed") is False, "authorization review may not set up scientific runtime")
    require(context.get("scientificExecutionPerformed") is False, "authorization review may not execute science")
    freshness.validate_authorization_review(context.get("freshness") or {}, ordinal, head)
    return {
        "status": "AUTHORIZATION_REVIEW_PASS_ZERO_RUNTIME",
        "scientificOrdinal": ordinal,
        "executionKey": authorization["executionKey"],
        "authorizationHead": head,
        "authorizationParent": parent,
        "authorizationPr": pr["number"],
        "scientificExecutionPerformed": False,
        "ordinalAllocatedReservedOrConsumedByReview": False,
    }
