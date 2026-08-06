#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

DIRECTORY = "experiments/tier1-precision-continuation-wave3-v1"
AUTHORIZATION_PATH = f"{DIRECTORY}/authorization.ordinal13.json"
AUTHORIZATION_BRANCH = "authorization/tier1-precision-continuation-wave3-ordinal13-v1"
DISPATCH_BRANCH = "dispatch/tier1-precision-continuation-wave3-ordinal13-v1"
SCIENTIFIC_WORKFLOW = ".github/workflows/tier1-precision-continuation-wave3-ordinal13-execution.yml"
RUN_TITLE = "Tier-1 precision continuation wave 3 ordinal 13"
EXECUTION_KEY = "twilight-surrogate-tier-1-v1:numerical:13"
SOURCE_ARTIFACT_ID = 8_954_776_553
SOURCE_ARTIFACT_NAME = "tier1-wave2-ordinal12-analysis"
SOURCE_ARTIFACT_DIGEST = "sha256:bd60e2ff433aa104ab84a4497310737d0b0d4695c8d454ad125d91f94efabe37"
SOURCE_RUN_ID = 31_065_046_524
SOURCE_RUN_ATTEMPT = 1
SOURCE_HEAD_SHA = "18a5746778441d57b722c740a17c94af9b56e9c9"
SOURCE_ANALYSIS_RAW_SHA256 = "c18f9ca23c910924400360ca18c4186d30594bc1aa2d3dd07a43a6031b274237"
SOURCE_ANALYSIS_SHA256 = "8e87fd440d15233dc66543a9ca011535a857b12b5602fd506f6466a900bfafc2"
PREREGISTRATION_SHA256 = "5f3664c3d4a4f6455bbf1996a492d658bcb9216989d99adeca5f92ece2ee6352"


class Refusal(RuntimeError):
    pass


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise Refusal(f"invalid JSON: {path}") from exc


def load_object(path: Path) -> dict[str, Any]:
    value = load_json(path)
    if not isinstance(value, dict):
        raise Refusal(f"expected object: {path}")
    return value


def load_rows(path: Path) -> list[dict[str, Any]]:
    value = load_json(path)
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        raise Refusal(f"expected array of objects: {path}")
    return value


def valid_sha(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 40
        and all(character in "0123456789abcdef" for character in value)
    )


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise Refusal(f"module unavailable: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def modules(root: Path):
    directory = root / DIRECTORY
    trigger = load_module(directory / "trigger_execution.py", "wave3_authorization_review_trigger")
    package = load_module(directory / "package.py", "wave3_authorization_review_package")
    binding = load_module(directory / "terminal_binding.py", "wave3_authorization_review_binding")
    return trigger, package, binding


def validate_scientific_workflow(root: Path) -> str:
    path = root / SCIENTIFIC_WORKFLOW
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise Refusal("ordinal-13 scientific workflow is unavailable on the reviewed source") from exc
    required = (
        "run-name: " + RUN_TITLE,
        "push:",
        DISPATCH_BRANCH,
        "test \"$GITHUB_RUN_ATTEMPT\" = 1",
        "test \"$SOURCE_SHA\" = \"$LIVE_MAIN\"",
        AUTHORIZATION_PATH,
        "terminal_trigger_execution.py manifest",
        "trigger_case_executor.py",
        "--allow-" + "execution",
        "githubRerunAllowed",
    )
    missing = [token for token in required if token not in text]
    forbidden = (
        "workflow_" + "dispatch:",
        "pull_request:",
        "schedule:",
        "repository_dispatch:",
    )
    found = [token for token in forbidden if token in text]
    if missing or found:
        raise Refusal(f"scientific workflow identity changed; missing={missing}; forbidden={found}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_artifact_metadata(value: dict[str, Any]) -> None:
    expected = {
        "id": SOURCE_ARTIFACT_ID,
        "name": SOURCE_ARTIFACT_NAME,
        "expired": False,
        "digest": SOURCE_ARTIFACT_DIGEST,
    }
    stale = {
        key: (value.get(key), expected_value)
        for key, expected_value in expected.items()
        if value.get(key) != expected_value
    }
    run = value.get("workflow_run")
    if not isinstance(run, dict):
        stale["workflow_run"] = (run, "object")
    else:
        expected_run = {
            "id": SOURCE_RUN_ID,
            "head_branch": "dispatch/tier1-precision-continuation-wave2-ordinal12-v1",
            "head_sha": SOURCE_HEAD_SHA,
        }
        run_stale = {
            key: (run.get(key), expected_value)
            for key, expected_value in expected_run.items()
            if run.get(key) != expected_value
        }
        if run_stale:
            stale["workflow_run"] = run_stale
    if stale:
        raise Refusal(f"ordinal-12 source artifact metadata changed: {stale}")


def validate_commit_metadata(metadata: dict[str, Any], mode: str) -> None:
    head = metadata.get("authorizationHead")
    parent = metadata.get("authorizationParent")
    live_main = metadata.get("liveMain")
    expected = {
        "authorizationBranch": AUTHORIZATION_BRANCH,
        "authorizationParent": live_main,
        "parentCount": 1,
        "changedFiles": [AUTHORIZATION_PATH],
        "dispatchBranchExists": False,
    }
    stale = {
        key: (metadata.get(key), expected_value)
        for key, expected_value in expected.items()
        if metadata.get(key) != expected_value
    }
    if not valid_sha(head) or not valid_sha(parent) or not valid_sha(live_main):
        stale["shaShape"] = ((head, parent, live_main), "three lowercase 40-character SHAs")
    if head == parent:
        stale["authorizationHead"] = (head, "must differ from parent")
    if mode == "dry-review" and metadata.get("authorizationBranchExists") is not False:
        stale["authorizationBranchExists"] = (
            metadata.get("authorizationBranchExists"),
            False,
        )
    if mode == "actual-authorization" and metadata.get("authorizationBranchExists") is not True:
        stale["authorizationBranchExists"] = (
            metadata.get("authorizationBranchExists"),
            True,
        )
    if stale:
        raise Refusal(f"authorization commit identity changed: {stale}")


def validate_no_prior_identity(rows: list[dict[str, Any]]) -> dict[str, Any]:
    matches = []
    for row in rows:
        title_match = row.get("display_title") == RUN_TITLE
        branch_match = row.get("head_branch") == DISPATCH_BRANCH
        if title_match or branch_match:
            matches.append(
                {
                    "id": row.get("id"),
                    "displayTitle": row.get("display_title"),
                    "event": row.get("event"),
                    "status": row.get("status"),
                    "conclusion": row.get("conclusion"),
                    "attempt": row.get("run_attempt"),
                    "headBranch": row.get("head_branch"),
                    "headSha": row.get("head_sha"),
                }
            )
    if matches:
        raise Refusal(f"ordinal-13 scientific identity already exists: {matches}")
    return {
        "inspectedRunCount": len(rows),
        "matchingRunCount": 0,
        "matchingRuns": [],
    }


def validate_authorization(
    root: Path,
    authorization: dict[str, Any],
    source_analysis_path: Path,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    trigger, package, binding = modules(root)
    binding_report = binding.validate_path(source_analysis_path)
    source_analysis = package.load_json(source_analysis_path)
    preregistration = package.build_preregistration(source_analysis, source_analysis_path, root)
    expected_scope = {
        "geometryCount": 15,
        "caseCount": 30,
        "blocks": [7, 8],
        "preregistrationSha256": PREREGISTRATION_SHA256,
        "sourceAnalysisRawSha256": SOURCE_ANALYSIS_RAW_SHA256,
        "sourceAnalysisSha256": SOURCE_ANALYSIS_SHA256,
    }
    stale_scope = {
        key: (preregistration.get(key), expected_value)
        for key, expected_value in expected_scope.items()
        if preregistration.get(key) != expected_value
    }
    if stale_scope:
        raise Refusal(f"terminal preregistration changed: {stale_scope}")

    base = trigger._base(root)
    context = {
        "eventName": "push",
        "triggerBranch": DISPATCH_BRANCH,
        "runAttempt": 1,
        "displayTitle": RUN_TITLE,
        "authorizationOrdinal": 13,
        "executionKey": EXECUTION_KEY,
        "headBranch": "main",
        "headSha": metadata["authorizationParent"],
        "authorizationRef": metadata["authorizationHead"],
        "runId": 1,
    }
    base.validate_context(context)
    base.validate_authorization(authorization, preregistration, context)
    base.validate_authorization_metadata(
        {
            "authorizationCommit": metadata["authorizationHead"],
            "authorizationParent": metadata["authorizationParent"],
            "changedFiles": metadata["changedFiles"],
            "parentCount": metadata["parentCount"],
        },
        context,
    )

    expected_extra = {
        "sourceArtifactId": SOURCE_ARTIFACT_ID,
        "sourceArtifactDigest": SOURCE_ARTIFACT_DIGEST,
        "triggerBranch": DISPATCH_BRANCH,
        "triggerEvent": "push",
    }
    stale_extra = {
        key: (authorization.get(key), expected_value)
        for key, expected_value in expected_extra.items()
        if authorization.get(key) != expected_value
    }
    allowed_keys = {
        "schemaVersion", "stageId", "status", "authorizationOrdinal", "executionKey",
        "runTitle", "runAttempt", "wave", "blocks", "geometryCount", "caseCount",
        "enabled", "solverExecutionAuthorized", "automaticDispatch", "dispatch",
        "workflowDispatchEnabled", "triggerBranch", "triggerEvent", "githubRerunAllowed",
        "surrogateTrainingAuthorized", "internalHoldoutOpeningAuthorized", "tier2Authorized",
        "productionPromotionAuthorized", "sourceRunId", "sourceRunAttempt", "sourceMainSha",
        "sourceAuthorizationRef", "sourceExecutionKey", "sourceArtifactId",
        "sourceArtifactDigest", "preregistrationSha256", "sourceAnalysisRawSha256",
        "sourceAnalysisSha256", "executionSourceHeadSha",
    }
    unknown = sorted(set(authorization) - allowed_keys)
    missing = sorted(allowed_keys - set(authorization))
    if stale_extra or unknown or missing:
        raise Refusal(
            f"authorization extended binding changed: stale={stale_extra}; unknown={unknown}; missing={missing}"
        )
    return {
        "bindingReportSha256": binding_report["reportSha256"],
        "preregistrationSha256": preregistration["preregistrationSha256"],
        "wave3SeedsSha256": preregistration["seedProof"]["wave3SeedsSha256"],
        "geometryIds": preregistration["geometryIds"],
        "geometryCount": preregistration["geometryCount"],
        "caseCount": preregistration["caseCount"],
        "authorizationCanonicalSha256": canonical_sha256(authorization),
    }


def review(
    root: Path,
    mode: str,
    authorization_path: Path,
    source_analysis_path: Path,
    source_artifact_metadata_path: Path,
    scientific_runs_path: Path,
    commit_metadata_path: Path,
) -> dict[str, Any]:
    root = root.resolve()
    if mode not in {"dry-review", "actual-authorization"}:
        raise Refusal(f"unsupported review mode: {mode}")
    authorization = load_object(authorization_path)
    artifact_metadata = load_object(source_artifact_metadata_path)
    rows = load_rows(scientific_runs_path)
    commit_metadata = load_object(commit_metadata_path)
    validate_artifact_metadata(artifact_metadata)
    validate_commit_metadata(commit_metadata, mode)
    duplicate = validate_no_prior_identity(rows)
    workflow_raw_sha256 = validate_scientific_workflow(root)
    scope = validate_authorization(root, authorization, source_analysis_path, commit_metadata)
    report: dict[str, Any] = {
        "schemaVersion": 1,
        "stageId": "tier1-precision-continuation-wave3-authorization-review-v1",
        "status": (
            "EXACT_ORDINAL13_AUTHORIZATION_REVIEW_PASSED"
            if mode == "actual-authorization"
            else "ORDINAL13_AUTHORIZATION_REVIEWER_DRY_CONTRACT_PASSED"
        ),
        "mode": mode,
        "authorizationBranch": AUTHORIZATION_BRANCH,
        "authorizationHead": commit_metadata["authorizationHead"],
        "authorizationParent": commit_metadata["authorizationParent"],
        "liveMain": commit_metadata["liveMain"],
        "authorizationPath": AUTHORIZATION_PATH,
        "authorizationCanonicalSha256": scope["authorizationCanonicalSha256"],
        "authorizationOrdinal": 13,
        "executionKey": EXECUTION_KEY,
        "runTitle": RUN_TITLE,
        "runAttempt": 1,
        "triggerEvent": "push",
        "dispatchBranch": DISPATCH_BRANCH,
        "dispatchBranchExists": False,
        "scientificWorkflowRawSha256": workflow_raw_sha256,
        "sourceRunId": SOURCE_RUN_ID,
        "sourceRunAttempt": SOURCE_RUN_ATTEMPT,
        "sourceArtifactId": SOURCE_ARTIFACT_ID,
        "sourceArtifactDigest": SOURCE_ARTIFACT_DIGEST,
        "sourceAnalysisRawSha256": SOURCE_ANALYSIS_RAW_SHA256,
        "sourceAnalysisSha256": SOURCE_ANALYSIS_SHA256,
        "terminalBindingReportSha256": scope["bindingReportSha256"],
        "preregistrationSha256": scope["preregistrationSha256"],
        "wave3SeedsSha256": scope["wave3SeedsSha256"],
        "geometryIds": scope["geometryIds"],
        "geometryCount": scope["geometryCount"],
        "caseCount": scope["caseCount"],
        "blocks": [7, 8],
        "duplicateRunAudit": duplicate,
        "authorizationAllocated": mode == "actual-authorization",
        "dispatchAllocated": False,
        "scientificSolverExecutions": 0,
        "githubRerunAllowed": False,
        "surrogateTrainingAuthorized": False,
        "internalHoldoutOpeningAuthorized": False,
        "tier2Authorized": False,
        "productionPromotionAuthorized": False,
    }
    report["reportSha256"] = canonical_sha256(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--mode", choices=("dry-review", "actual-authorization"), required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--source-analysis", type=Path, required=True)
    parser.add_argument("--source-artifact-metadata", type=Path, required=True)
    parser.add_argument("--scientific-runs", type=Path, required=True)
    parser.add_argument("--commit-metadata", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = review(
            args.root,
            args.mode,
            args.authorization,
            args.source_analysis,
            args.source_artifact_metadata,
            args.scientific_runs,
            args.commit_metadata,
        )
    except Exception as exc:
        print(json.dumps({"status": "REFUSED", "reason": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
