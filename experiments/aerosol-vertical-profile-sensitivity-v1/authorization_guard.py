from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path
from typing import Any

STAGE = "aerosol-vertical-profile-sensitivity-v1"
AUTH_PATH = f"experiments/{STAGE}/authorization.json"
HERE = Path(__file__).resolve().parent
SHA40 = re.compile(r"^[0-9a-f]{40}$")
EXPECTED_SEED_CANONICAL = "a2e22b526dfad84d4f23c0ca8b143d028fddc7e55f78deb93a43e194ebd6c35e"
EXPECTED_ROWS_CANONICAL = "f22de8a9e30ba106759effb1170a5ca1d1e747cb2ac68293fa232dc7ed6ca683"
EXPECTED_AUGMENTED_TREE = "5d8bbf8e6b91ec3d405dee36f21a94afbb6e5ec6cd67da2dd5dd541738199d80"
EXPECTED_OPTPROP_ARCHIVE = "11daa1f1f4be0fd4ddf7e881ec2005498049674a1540d37b4b1e8f5e16052c7e"


class AuthorizationRefusal(RuntimeError):
    pass


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AuthorizationRefusal(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def seed_proof_raw_sha256(proof: dict[str, Any]) -> str:
    raw = (json.dumps(proof, indent=2, sort_keys=True) + "\n").encode()
    return hashlib.sha256(raw).hexdigest()


def validate_preauthorization_report(
    report: dict[str, Any],
    *,
    expected_parent: str,
    expected_ordinal: int,
) -> None:
    if report.get("stageId") != f"{STAGE}-preauthorization":
        raise AuthorizationRefusal("preauthorization stage drift")
    if report.get("status") != "PREAUTHORIZATION_SURFACE_CLEAN_NOT_ALLOCATED":
        raise AuthorizationRefusal("preauthorization status drift")
    if report.get("exactMainSha") != expected_parent:
        raise AuthorizationRefusal("preauthorization parent binding drift")
    if report.get("nextAvailableScientificOrdinal") != expected_ordinal:
        raise AuthorizationRefusal("preauthorization ordinal drift")
    if report.get("candidateSeedCount") != 72:
        raise AuthorizationRefusal("preauthorization seed count drift")
    if report.get("candidateSeedCanonicalSha256") != EXPECTED_SEED_CANONICAL:
        raise AuthorizationRefusal("preauthorization seed canonical drift")
    if report.get("candidateRowsCanonicalSha256") != EXPECTED_ROWS_CANONICAL:
        raise AuthorizationRefusal("preauthorization row canonical drift")
    if report.get("trackedTreeExternalCollisionCount") != 0 or report.get("repositoryGlobalCollisionCount") != 0:
        raise AuthorizationRefusal("preauthorization seed collision exists")
    if report.get("repositoryGlobalDoubleEnumerationStable") is not True:
        raise AuthorizationRefusal("preauthorization global enumeration unstable")
    for key in (
        "scientificOrdinalAllocated", "authorizationCreated", "dispatchCreated",
        "candidateSeedsAppliedToCases", "scientificRuntimeSetupPerformed",
        "scientificExecutionPerformed", "solverExecutionPerformed", "resultOpeningPerformed",
    ):
        if report.get(key) is not False:
            raise AuthorizationRefusal(f"preauthorization crossed boundary: {key}")


def build_expected_document(
    root: Path,
    parent_main: str,
    scientific_ordinal: int,
    preauthorization_report: dict[str, Any],
    seed_authorization_proof: dict[str, Any],
    *,
    preauthorization_artifact_id: int,
    preauthorization_artifact_digest: str,
) -> dict[str, Any]:
    if SHA40.fullmatch(parent_main or "") is None:
        raise AuthorizationRefusal("parent main SHA invalid")
    if isinstance(scientific_ordinal, bool) or not isinstance(scientific_ordinal, int) or scientific_ordinal <= 0:
        raise AuthorizationRefusal("scientific ordinal invalid")
    if not isinstance(preauthorization_artifact_id, int) or preauthorization_artifact_id <= 0:
        raise AuthorizationRefusal("preauthorization artifact ID invalid")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", preauthorization_artifact_digest or ""):
        raise AuthorizationRefusal("preauthorization artifact digest invalid")

    validate_preauthorization_report(
        preauthorization_report,
        expected_parent=parent_main,
        expected_ordinal=scientific_ordinal,
    )
    design_mod = _load("avps_execution_design_for_authorization", HERE / "execution_design.py")
    design_mod.validate_seed_authorization_proof(seed_authorization_proof, parent_main)
    design = design_mod.build_review_execution_design(seed_authorization_proof, parent_main)
    freshness = _load("avps_freshness_for_authorization", HERE / "freshness.py")

    return {
        "schemaVersion": 1,
        "stageId": STAGE,
        "status": "AUTHORIZED_PENDING_SEPARATE_DISPATCH",
        "scientificOrdinal": scientific_ordinal,
        "authorizationBranch": freshness.authorization_branch(scientific_ordinal),
        "dispatchBranch": freshness.dispatch_branch(scientific_ordinal),
        "executionKey": freshness.execution_key(scientific_ordinal),
        "exactAuthorizationParentCommit": parent_main,
        "reviewPackageMainSha": parent_main,
        "exactAuthorizationCommit": None,
        "preauthorizationRunId": int(preauthorization_report["runId"]),
        "preauthorizationRunAttempt": int(preauthorization_report["runAttempt"]),
        "preauthorizationArtifactId": preauthorization_artifact_id,
        "preauthorizationArtifactDigest": preauthorization_artifact_digest,
        "preauthorizationReportSha256": str(preauthorization_report["reportSha256"]),
        "authorizationTimeSeedProofRawSha256": seed_proof_raw_sha256(seed_authorization_proof),
        "candidateSeedCount": 72,
        "candidateSeedCanonicalSha256": EXPECTED_SEED_CANONICAL,
        "candidateRowsCanonicalSha256": EXPECTED_ROWS_CANONICAL,
        "executionDesignCanonicalSha256": design["canonicalDesignSha256"],
        "caseCount": 360,
        "commonRandomNumberGroupCount": 72,
        "statesPerGroup": 5,
        "photonHistoriesPerCase": 20_000_000,
        "augmentedDataTreeSha256": EXPECTED_AUGMENTED_TREE,
        "officialOptpropArchiveSha256": EXPECTED_OPTPROP_ARCHIVE,
        "scientificExecutionAuthorized": True,
        "solverExecutionAuthorized": True,
        "dispatchAuthorized": False,
        "resultOpeningAuthorized": False,
        "automaticDispatch": False,
        "consumed": False,
        "workflowRunAttemptRequired": 1,
        "githubRerunAllowed": False,
        "retryAllowed": False,
        "resumeAllowed": False,
        "productionAuthorized": False,
        "taylorOrJerusalemFitAuthorized": False,
    }


def validate_enabled_document(
    root: Path,
    auth: dict[str, Any],
    parent_main: str,
    preauthorization_report: dict[str, Any],
    seed_authorization_proof: dict[str, Any],
    *,
    preauthorization_artifact_id: int,
    preauthorization_artifact_digest: str,
) -> dict[str, Any]:
    ordinal = auth.get("scientificOrdinal")
    expected = build_expected_document(
        root,
        parent_main,
        ordinal,
        preauthorization_report,
        seed_authorization_proof,
        preauthorization_artifact_id=preauthorization_artifact_id,
        preauthorization_artifact_digest=preauthorization_artifact_digest,
    )
    if auth != expected:
        raise AuthorizationRefusal("authorization document does not exactly match frozen expected document")
    design_mod = _load("avps_execution_design_for_authorization_validation", HERE / "execution_design.py")
    return design_mod.build_review_execution_design(seed_authorization_proof, parent_main)


def review(
    auth: dict[str, Any],
    ctx: dict[str, Any],
    root: Path,
    preauthorization_report: dict[str, Any],
    seed_authorization_proof: dict[str, Any],
    *,
    preauthorization_artifact_id: int,
    preauthorization_artifact_digest: str,
) -> dict[str, Any]:
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
    freshness = _load("avps_freshness_for_authorization_review", HERE / "freshness.py")
    expected_branch = freshness.authorization_branch(ordinal)
    if not (
        pr.get("state") == "open" and pr.get("draft") is True and pr.get("merged") is False
        and pr.get("headBranch") == expected_branch and pr.get("baseBranch") == "main"
        and pr.get("headRepo") == pr.get("baseRepo") and pr.get("headSha") == head
    ):
        raise AuthorizationRefusal("authorization PR identity drift")
    if ctx.get("runAttempt") != 1 or ctx.get("eventName") != "pull_request" or ctx.get("eventAction") != "opened":
        raise AuthorizationRefusal("authorization review must be opened attempt-1 PR run")
    if ctx.get("scientificRuntimeSetupPerformed") is not False or ctx.get("scientificExecutionPerformed") is not False:
        raise AuthorizationRefusal("authorization review crossed zero-runtime boundary")
    design = validate_enabled_document(
        root,
        auth,
        parent,
        preauthorization_report,
        seed_authorization_proof,
        preauthorization_artifact_id=preauthorization_artifact_id,
        preauthorization_artifact_digest=preauthorization_artifact_digest,
    )
    freshness.validate_authorization_review(ctx.get("freshness") or {}, ordinal, head)
    return {
        "status": "EXACT_ONE_FILE_AVPS_V1_AUTHORIZATION_REVIEW_PASS_ZERO_RUNTIME",
        "scientificOrdinal": ordinal,
        "headSha": head,
        "parentSha": parent,
        "caseCount": design["caseCount"],
        "groupCount": design["groupCount"],
        "scientificRuntimeSetupPerformed": False,
        "scientificExecutionPerformed": False,
        "solverExecutionPerformed": False,
        "ordinalAllocatedReservedOrConsumedByReview": False,
    }
