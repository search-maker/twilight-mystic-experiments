from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

STAGE = "aerosol-vertical-profile-sensitivity-v1"
AUTH_PATH = f"experiments/{STAGE}/authorization.json"
HERE = Path(__file__).resolve().parent
SHA40 = re.compile(r"^[0-9a-f]{40}$")
EXPECTED_SEED_CANONICAL = "a2e22b526dfad84d4f23c0ca8b143d028fddc7e55f78deb93a43e194ebd6c35e"
EXPECTED_ROWS_CANONICAL = "f22de8a9e30ba106759effb1170a5ca1d1e747cb2ac68293fa232dc7ed6ca683"
EXPECTED_EXECUTION_CONTROL_BLOBS = {
    "executionContract": ("experiments/aerosol-vertical-profile-sensitivity-v1/execution-contract.review.json", "230874923004115ff21f218bb0ce4d2e038d3a98"),
    "dispatchGuard": ("experiments/aerosol-vertical-profile-sensitivity-v1/dispatch_guard.py", "e95f6c30e503709ba8c3fe14dc9edeae665e5877"),
    "scienceGuard": ("experiments/aerosol-vertical-profile-sensitivity-v1/science_guard.py", "c774be7ea8655854bb85071a9fb260e21498beda"),
    "dispatchPublisherWorkflow": (".github/workflows/avps-v1-dispatch-publisher.yml", "cd8aa5151533133a33c046ad2bed2bd7e2c11089"),
    "scienceWorkflow": (".github/workflows/avps-v1-science.yml", "55f48bbdf99aac58a96bd96f6735a4e56b8b466a"),
}
EXPECTED_STARS_REPOSITORY = "search-maker/starsvisibility"
EXPECTED_STARS_COMMIT = "e0da52eb0a2d5bac333da6572f51df52ea7e676e"
EXPECTED_HUMAN_THRESHOLD_PATH = "scientific-tools/visibility-v3/human-threshold.mjs"
EXPECTED_HUMAN_THRESHOLD_GIT_BLOB = "bb4cd0ff02159ecffe276022cec9d292c7a434a3"


class AuthorizationRefusal(RuntimeError):
    pass


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AuthorizationRefusal(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _execution_control_bindings(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    actual: dict[str, str] = {}
    for key, (relative, expected) in EXPECTED_EXECUTION_CONTROL_BLOBS.items():
        path = root / relative
        if not path.is_file():
            raise AuthorizationRefusal(f"execution-control source missing: {relative}")
        blob = _git_blob_sha1(path)
        if blob != expected:
            raise AuthorizationRefusal(f"execution-control byte drift: {relative}")
        actual[key] = blob

    contract_path = root / EXPECTED_EXECUTION_CONTROL_BLOBS["executionContract"][0]
    contract = json.loads(contract_path.read_text())
    if contract.get("stageId") != f"{STAGE}-execution-contract":
        raise AuthorizationRefusal("execution contract stage drift")
    if contract.get("status") != "FROZEN_REVIEW_ONLY_EXECUTION_TRANSPORT_NOT_AUTHORIZED":
        raise AuthorizationRefusal("execution contract status drift")
    if any(contract.get(key) is not False for key in (
        "candidateSeedsAllocated", "scientificOrdinalAllocated", "authorizationCreated",
        "dispatchCreated", "scientificExecutionAuthorized", "solverExecutionAuthorized",
        "resultOpeningAuthorized",
    )):
        raise AuthorizationRefusal("execution contract crossed review boundary")
    if (contract.get("expectedCaseCount"), contract.get("expectedGroupCount"), contract.get("expectedAnalysisCellCount"),
        contract.get("expectedStatesPerGroup"), contract.get("expectedPrimaryContrastCount")) != (360, 72, 24, 5, 4):
        raise AuthorizationRefusal("execution contract cardinality drift")
    if contract.get("photonHistoriesPerCase") != 20_000_000 or contract.get("fieldFactor") != 3.14:
        raise AuthorizationRefusal("execution contract F/photon drift")

    orchestration = contract.get("orchestrationBindings") or {}
    if orchestration.get("dispatchPublisherWorkflowGitBlobSha1") != actual["dispatchPublisherWorkflow"]:
        raise AuthorizationRefusal("contract/publisher workflow binding drift")
    if orchestration.get("scienceWorkflowGitBlobSha1") != actual["scienceWorkflow"]:
        raise AuthorizationRefusal("contract/science workflow binding drift")
    if (orchestration.get("caseShards"), orchestration.get("casesPerShard"), orchestration.get("maxParallelPerShard"),
        orchestration.get("maximumConcurrentCaseJobs")) != (4, 90, 2, 8):
        raise AuthorizationRefusal("execution orchestration cardinality drift")
    if orchestration.get("aggregateRequiresAllFourShardsSuccess") is not True:
        raise AuthorizationRefusal("aggregate success gate drift")

    external = contract.get("externalLevelBBinding") or {}
    expected_external = {
        "repository": EXPECTED_STARS_REPOSITORY,
        "ref": EXPECTED_STARS_COMMIT,
        "path": EXPECTED_HUMAN_THRESHOLD_PATH,
        "expectedGitBlobSha1": EXPECTED_HUMAN_THRESHOLD_GIT_BLOB,
        "fieldFactor": 3.14,
        "branch": "full",
    }
    if external != expected_external:
        raise AuthorizationRefusal("external Level-B binding drift")

    control = {
        "executionContractPath": EXPECTED_EXECUTION_CONTROL_BLOBS["executionContract"][0],
        "executionContractGitBlobSha1": actual["executionContract"],
        "dispatchGuardPath": EXPECTED_EXECUTION_CONTROL_BLOBS["dispatchGuard"][0],
        "dispatchGuardGitBlobSha1": actual["dispatchGuard"],
        "scienceGuardPath": EXPECTED_EXECUTION_CONTROL_BLOBS["scienceGuard"][0],
        "scienceGuardGitBlobSha1": actual["scienceGuard"],
        "dispatchPublisherWorkflowPath": EXPECTED_EXECUTION_CONTROL_BLOBS["dispatchPublisherWorkflow"][0],
        "dispatchPublisherWorkflowGitBlobSha1": actual["dispatchPublisherWorkflow"],
        "scienceWorkflowPath": EXPECTED_EXECUTION_CONTROL_BLOBS["scienceWorkflow"][0],
        "scienceWorkflowGitBlobSha1": actual["scienceWorkflow"],
    }
    return control, expected_external


def seed_proof_raw_sha256(proof: dict[str, Any]) -> str:
    raw = (json.dumps(proof, indent=2, sort_keys=True) + "\n").encode()
    return hashlib.sha256(raw).hexdigest()


def validate_preauthorization_report(
    report: dict[str, Any], *, expected_parent: str, expected_ordinal: int
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
    if re.fullmatch(r"sha256:[0-9a-f]{64}", preauthorization_artifact_digest or "") is None:
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
    control_bindings, external_level_b = _execution_control_bindings(root)

    runtime = dict(design.get("runtimeBinding") or {})
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
        "disabledExecutionPackageBlobSha1": design["sourceDisabledExecutionPackageBlobSha1"],
        "disabledExecutionPackageCanonicalSha256": design["sourceDisabledExecutionPackageCanonicalSha256"],
        "exactAfglProfileBundleArtifactId": design["exactAfglProfileBundleArtifactId"],
        "exactAfglProfileBundleArtifactDigest": design["exactAfglProfileBundleArtifactDigest"],
        "exactAfglProfileTauSha256": design["exactAfglProfileTauSha256"],
        "lockedLibRadtranPackage": runtime.get("lockedPackage"),
        "uvspecSha256": runtime.get("uvspecSha256"),
        "baseDataTreeSha256": runtime.get("baseDataTreeSha256"),
        "stagedOpacDataTreeSha256": runtime.get("stagedOpacDataTreeSha256"),
        "officialOptpropArchiveSha256": runtime.get("officialOptpropArchiveSha256"),
        "executionControlBindings": control_bindings,
        "externalLevelBBinding": external_level_b,
        "caseCount": 360,
        "commonRandomNumberGroupCount": 72,
        "statesPerGroup": 5,
        "photonHistoriesPerCase": 20_000_000,
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
        "disabledExecutionPackageCanonicalSha256": design["sourceDisabledExecutionPackageCanonicalSha256"],
        "exactAfglProfileBundleArtifactDigest": design["exactAfglProfileBundleArtifactDigest"],
        "executionContractGitBlobSha1": auth["executionControlBindings"]["executionContractGitBlobSha1"],
        "dispatchPublisherWorkflowGitBlobSha1": auth["executionControlBindings"]["dispatchPublisherWorkflowGitBlobSha1"],
        "scienceWorkflowGitBlobSha1": auth["executionControlBindings"]["scienceWorkflowGitBlobSha1"],
        "scientificRuntimeSetupPerformed": False,
        "scientificExecutionPerformed": False,
        "solverExecutionPerformed": False,
        "ordinalAllocatedReservedOrConsumedByReview": False,
    }
