#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

DESCRIPTOR_STAGE = "surrogate-training-v2-real-tier1-source-descriptor-v1"
GUARD_STAGE = "surrogate-training-v2-real-tier1-handoff-guard-v2"
DESCRIPTOR_STATUS = "IMMUTABLE_SOURCE_BOUND_FOR_HANDOFF"

CONSUMED_SOURCE_RUN_IDS = {30906913329, 30952457327}
CONSUMED_EXECUTION_KEYS = {
    "twilight-surrogate-tier-1-v1:numerical:1",
    "twilight-surrogate-tier-1-v1:numerical:2",
}
CONSUMED_AUTHORIZATION_ORDINALS = {1, 2}

REFERENCE_RUN_ID = 30905632743
REFERENCE_WORKFLOW_ID = 326688920
REFERENCE_HEAD_SHA = "9ab74efabfd34799aeeb5c9220a84639861f739d"
REFERENCE_PATH = ".github/workflows/twilight-surrogate-tier-1-proposal.yml"
REFERENCE_ARTIFACT_ID = 8890906227
REFERENCE_ARTIFACT_NAME = "twilight-surrogate-tier-1-proposal-v1"
REFERENCE_ARTIFACT_DIGEST = "sha256:899507d315ae25db88babb3f610587fca24238e7a7000038eed009c7a14af9a0"

CASE_COUNT = 96
SOURCE_ARTIFACT_COUNT = 100
SAFE_RELATIVE_PATH = re.compile(r"[A-Za-z0-9.][A-Za-z0-9._/-]*")
SAFE_ARTIFACT_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


class GuardRefusal(RuntimeError):
    pass


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise GuardRefusal(f"expected JSON object: {path}")
    return value


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
        raise GuardRefusal(f"{label} must be lowercase raw SHA-256")
    return value


def require_git_sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 40 or any(ch not in "0123456789abcdef" for ch in value):
        raise GuardRefusal(f"{label} must be lowercase 40-character git sha")
    return value


def require_digest(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(ch not in "0123456789abcdef" for ch in value[7:])
    ):
        raise GuardRefusal(f"{label} must be sha256 digest")
    return value


def require_exact(value: dict[str, Any], expected: dict[str, Any], label: str) -> None:
    changed = {key: (value.get(key), wanted) for key, wanted in expected.items() if value.get(key) != wanted}
    if changed:
        raise GuardRefusal(f"{label} changed: {changed}")


def require_exact_keys(value: dict[str, Any], keys: set[str], label: str) -> None:
    if set(value) != keys:
        raise GuardRefusal(f"{label} fields changed: missing={sorted(keys - set(value))}, extra={sorted(set(value) - keys)}")


def require_positive_int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise GuardRefusal(f"{label} must be a positive integer")
    return value


def require_safe_relative_path(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or not SAFE_RELATIVE_PATH.fullmatch(value)
        or value.startswith(("/", "\\"))
        or ".." in Path(value).parts
        or "\\" in value
    ):
        raise GuardRefusal(f"{label} must be a safe repository-relative path")
    return value


def artifact_map(payload: dict[str, Any], label: str) -> dict[str, dict[str, Any]]:
    values = payload.get("artifacts")
    if not isinstance(values, list):
        raise GuardRefusal(f"{label} artifact list missing")
    by_name: dict[str, dict[str, Any]] = {}
    ids: set[int] = set()
    for item in values:
        if not isinstance(item, dict):
            raise GuardRefusal(f"{label} artifact entry invalid")
        artifact_id = item.get("id")
        name = item.get("name")
        if not isinstance(artifact_id, int) or artifact_id < 1 or artifact_id in ids:
            raise GuardRefusal(f"{label} artifact ID duplicated or invalid")
        if not isinstance(name, str) or not SAFE_ARTIFACT_NAME.fullmatch(name) or name in by_name:
            raise GuardRefusal(f"{label} artifact name duplicated or invalid")
        if item.get("expired") is not False:
            raise GuardRefusal(f"{label} artifact expired: {name}")
        require_digest(item.get("digest"), f"{label}.{name}.digest")
        ids.add(artifact_id)
        by_name[name] = item
    return by_name


def validate_descriptor(descriptor: dict[str, Any]) -> dict[str, Any]:
    require_exact_keys(
        descriptor,
        {
            "schemaVersion",
            "stageId",
            "status",
            "proposalOnly",
            "automaticDispatch",
            "sourceRun",
            "sourceArtifacts",
            "manifestRawSha256",
            "manifestRelativePath",
            "preflightArtifactName",
            "aggregateArtifactName",
            "auditArtifactName",
            "analysisArtifactName",
            "caseArtifactPrefix",
            "caseCount",
            "artifactCount",
            "surrogateTrainingAuthorized",
            "internalHoldoutOpeningAuthorized",
            "tier2Authorized",
            "productionPromotionAuthorized",
            "boundary",
        },
        "source descriptor",
    )
    require_exact(
        descriptor,
        {
            "schemaVersion": 1,
            "stageId": DESCRIPTOR_STAGE,
            "status": DESCRIPTOR_STATUS,
            "proposalOnly": True,
            "automaticDispatch": False,
            "caseCount": CASE_COUNT,
            "artifactCount": SOURCE_ARTIFACT_COUNT,
            "surrogateTrainingAuthorized": False,
            "internalHoldoutOpeningAuthorized": False,
            "tier2Authorized": False,
            "productionPromotionAuthorized": False,
        },
        "source descriptor",
    )
    source = descriptor.get("sourceRun")
    if not isinstance(source, dict):
        raise GuardRefusal("source descriptor run identity missing")
    require_exact_keys(
        source,
        {
            "id",
            "workflowId",
            "runNumber",
            "runAttempt",
            "event",
            "headBranch",
            "headSha",
            "path",
            "displayTitle",
            "executionKey",
            "authorizationOrdinal",
            "authorizationRef",
        },
        "source descriptor run",
    )
    run_id = require_positive_int(source.get("id"), "source descriptor run ID")
    require_positive_int(source.get("workflowId"), "source descriptor workflow ID")
    require_positive_int(source.get("runNumber"), "source descriptor run number")
    require_exact(source, {"runAttempt": 1, "event": "workflow_dispatch", "headBranch": "main"}, "source descriptor run")
    require_git_sha(source.get("headSha"), "source descriptor head SHA")
    require_git_sha(source.get("authorizationRef"), "source descriptor authorization ref")
    require_safe_relative_path(source.get("path"), "source descriptor workflow path")
    if not isinstance(source.get("displayTitle"), str) or not source["displayTitle"].strip():
        raise GuardRefusal("source descriptor display title missing")
    execution_key = source.get("executionKey")
    ordinal = source.get("authorizationOrdinal")
    if not isinstance(execution_key, str) or not execution_key.strip():
        raise GuardRefusal("source descriptor execution key missing")
    require_positive_int(ordinal, "source descriptor authorization ordinal")
    if (
        execution_key not in source["displayTitle"]
        or f"ordinal={ordinal}" not in source["displayTitle"]
        or f"auth={source['authorizationRef']}" not in source["displayTitle"]
    ):
        raise GuardRefusal("source display title does not bind execution key, authorization ref, and ordinal")
    if run_id in CONSUMED_SOURCE_RUN_IDS or execution_key in CONSUMED_EXECUTION_KEYS or ordinal in CONSUMED_AUTHORIZATION_ORDINALS:
        raise GuardRefusal("consumed historical Tier-1 source identity is permanently ineligible")

    require_sha256(descriptor.get("manifestRawSha256"), "source descriptor manifest hash")
    require_safe_relative_path(descriptor.get("manifestRelativePath"), "source descriptor manifest path")
    names = []
    for field in ("preflightArtifactName", "aggregateArtifactName", "auditArtifactName", "analysisArtifactName", "caseArtifactPrefix"):
        value = descriptor.get(field)
        if not isinstance(value, str) or not SAFE_ARTIFACT_NAME.fullmatch(value):
            raise GuardRefusal(f"source descriptor {field} invalid")
        names.append(value)
    if len(set(names[:4])) != 4:
        raise GuardRefusal("source descriptor singleton artifact names overlap")

    expected_payload = {"artifacts": descriptor.get("sourceArtifacts")}
    expected = artifact_map(expected_payload, "descriptor")
    if len(expected) != SOURCE_ARTIFACT_COUNT:
        raise GuardRefusal("source descriptor must bind exactly 100 artifacts")
    for name, item in expected.items():
        require_exact_keys(item, {"id", "name", "digest", "expired"}, f"descriptor artifact {name}")
    if not isinstance(descriptor.get("boundary"), str) or not descriptor["boundary"].strip():
        raise GuardRefusal("source descriptor boundary missing")
    return descriptor


def validate_source_run(run: dict[str, Any], descriptor: dict[str, Any]) -> None:
    source = descriptor["sourceRun"]
    require_exact(
        run,
        {
            "id": source["id"],
            "workflow_id": source["workflowId"],
            "run_number": source["runNumber"],
            "run_attempt": 1,
            "event": "workflow_dispatch",
            "status": "completed",
            "conclusion": "success",
            "head_branch": "main",
            "head_sha": source["headSha"],
            "path": source["path"],
            "display_title": source["displayTitle"],
        },
        "source run",
    )


def validate_reference_run(run: dict[str, Any]) -> None:
    require_exact(
        run,
        {
            "id": REFERENCE_RUN_ID,
            "workflow_id": REFERENCE_WORKFLOW_ID,
            "run_attempt": 1,
            "event": "push",
            "status": "completed",
            "conclusion": "success",
            "head_branch": "main",
            "head_sha": REFERENCE_HEAD_SHA,
            "path": REFERENCE_PATH,
            "name": "Twilight surrogate tier-1 proposal",
        },
        "reference run",
    )


def validate_manifest_case_ids(manifest: dict[str, Any]) -> list[str]:
    require_exact(
        manifest,
        {
            "schemaVersion": 1,
            "stageId": "twilight-surrogate-tier-1-execution-v1",
            "proposalOnly": True,
            "scientificExecution": False,
        },
        "source manifest",
    )
    cases = manifest.get("cases")
    if not isinstance(cases, list) or len(cases) != CASE_COUNT:
        raise GuardRefusal("source manifest must contain exactly 96 cases")
    case_ids: list[str] = []
    for item in cases:
        case_id = item.get("caseId") if isinstance(item, dict) else None
        if not isinstance(case_id, str) or not SAFE_ARTIFACT_NAME.fullmatch(case_id):
            raise GuardRefusal("source manifest case ID missing or invalid")
        case_ids.append(case_id)
    if len(set(case_ids)) != CASE_COUNT:
        raise GuardRefusal("source manifest case IDs duplicated")
    return sorted(case_ids)


def validate_source_artifacts(payload: dict[str, Any], descriptor: dict[str, Any], case_ids: list[str]) -> dict[str, dict[str, Any]]:
    actual = artifact_map(payload, "source")
    expected = artifact_map({"artifacts": descriptor["sourceArtifacts"]}, "descriptor")
    expected_names = {
        descriptor["preflightArtifactName"],
        descriptor["aggregateArtifactName"],
        descriptor["auditArtifactName"],
        descriptor["analysisArtifactName"],
        *(f"{descriptor['caseArtifactPrefix']}{case_id}" for case_id in case_ids),
    }
    if len(expected_names) != SOURCE_ARTIFACT_COUNT or set(expected) != expected_names:
        raise GuardRefusal("descriptor artifact universe differs from manifest")
    if set(actual) != expected_names:
        missing = sorted(expected_names - set(actual))
        extra = sorted(set(actual) - expected_names)
        raise GuardRefusal(f"source artifact universe changed: missing={missing}, extra={extra}")
    for name in sorted(expected_names):
        require_exact(
            actual[name],
            {
                "id": expected[name]["id"],
                "name": name,
                "digest": expected[name]["digest"],
                "expired": False,
            },
            f"source artifact {name}",
        )
    return actual


def validate_reference_artifacts(payload: dict[str, Any]) -> None:
    by_name = artifact_map(payload, "reference")
    if set(by_name) != {REFERENCE_ARTIFACT_NAME}:
        raise GuardRefusal("reference artifact universe changed")
    require_exact(
        by_name[REFERENCE_ARTIFACT_NAME],
        {
            "id": REFERENCE_ARTIFACT_ID,
            "name": REFERENCE_ARTIFACT_NAME,
            "digest": REFERENCE_ARTIFACT_DIGEST,
            "expired": False,
        },
        "reference artifact",
    )


def validate(
    source_descriptor: dict[str, Any],
    source_run: dict[str, Any],
    source_artifacts: dict[str, Any],
    manifest: dict[str, Any],
    reference_run: dict[str, Any],
    reference_artifacts: dict[str, Any],
    *,
    source_descriptor_raw_sha256: str,
    manifest_raw_sha256: str,
    handoff_head_sha: str,
) -> dict[str, Any]:
    require_sha256(source_descriptor_raw_sha256, "source descriptor raw hash")
    require_sha256(manifest_raw_sha256, "manifest raw hash")
    require_git_sha(handoff_head_sha, "handoff workflow head SHA")
    descriptor = validate_descriptor(source_descriptor)
    if manifest_raw_sha256 != descriptor["manifestRawSha256"]:
        raise GuardRefusal("source manifest raw hash differs from immutable descriptor")
    validate_source_run(source_run, descriptor)
    validate_reference_run(reference_run)
    case_ids = validate_manifest_case_ids(manifest)
    source_by_name = validate_source_artifacts(source_artifacts, descriptor, case_ids)
    validate_reference_artifacts(reference_artifacts)
    source = descriptor["sourceRun"]
    return {
        "schemaVersion": 2,
        "stageId": GUARD_STAGE,
        "status": "REAL_TIER1_HANDOFF_SOURCE_ACCEPTED",
        "sourceDescriptorRawSha256": source_descriptor_raw_sha256,
        "sourceManifestRawSha256": manifest_raw_sha256,
        "sourceRunId": source["id"],
        "sourceRunHeadSha": source["headSha"],
        "sourceWorkflowId": source["workflowId"],
        "sourceExecutionKey": source["executionKey"],
        "sourceAuthorizationOrdinal": source["authorizationOrdinal"],
        "sourceAuthorizationRef": source["authorizationRef"],
        "sourceRunAttempt": 1,
        "sourceArtifactCount": len(source_by_name),
        "caseArtifactCount": CASE_COUNT,
        "referenceRunId": REFERENCE_RUN_ID,
        "referenceArtifactId": REFERENCE_ARTIFACT_ID,
        "handoffWorkflowHeadSha": handoff_head_sha,
        "scientificExecutionPerformedByThisGuard": False,
        "surrogateTrainingAuthorized": False,
        "internalHoldoutOpeningAuthorized": False,
        "tier2Authorized": False,
        "productionPromotionAuthorized": False,
        "boundary": "terminal artifact-only Tier-1 v1-to-v2 handoff guard; no solver, fitting, holdout opening, Tier-2 activation, or production promotion",
    }


def descriptor_environment(descriptor: dict[str, Any], descriptor_path: Path, supplied_raw_sha256: str) -> dict[str, str]:
    actual_sha = raw_sha256(descriptor_path)
    require_sha256(supplied_raw_sha256, "supplied source descriptor raw hash")
    if actual_sha != supplied_raw_sha256:
        raise GuardRefusal("supplied source descriptor raw hash mismatch")
    value = validate_descriptor(descriptor)
    source = value["sourceRun"]
    return {
        "SOURCE_DESCRIPTOR_RAW_SHA256": actual_sha,
        "SOURCE_RUN_ID": str(source["id"]),
        "SOURCE_RUN_HEAD_SHA": source["headSha"],
        "SOURCE_PREFLIGHT_ARTIFACT": value["preflightArtifactName"],
        "SOURCE_CASE_PATTERN": f"{value['caseArtifactPrefix']}*",
        "SOURCE_AGGREGATE_ARTIFACT": value["aggregateArtifactName"],
        "SOURCE_AUDIT_ARTIFACT": value["auditArtifactName"],
        "SOURCE_ANALYSIS_ARTIFACT": value["analysisArtifactName"],
        "SOURCE_MANIFEST_RELATIVE_PATH": value["manifestRelativePath"],
    }


def write_github_env(path: Path, values: dict[str, str]) -> None:
    with path.open("a") as stream:
        stream.write("".join(f"{key}={value}\n" for key, value in sorted(values.items())))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-descriptor", type=Path, required=True)
    parser.add_argument("--source-descriptor-raw-sha256", required=True)
    parser.add_argument("--resolve-descriptor", action="store_true")
    parser.add_argument("--github-env", type=Path)
    parser.add_argument("--source-run", type=Path)
    parser.add_argument("--source-artifacts", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--reference-run", type=Path)
    parser.add_argument("--reference-artifacts", type=Path)
    parser.add_argument("--handoff-head-sha")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        descriptor = load(args.source_descriptor)
        actual_descriptor_sha = raw_sha256(args.source_descriptor)
        require_sha256(args.source_descriptor_raw_sha256, "supplied source descriptor raw hash")
        if actual_descriptor_sha != args.source_descriptor_raw_sha256:
            raise GuardRefusal("supplied source descriptor raw hash mismatch")
        if args.resolve_descriptor:
            if args.github_env is None:
                raise GuardRefusal("--github-env is required with --resolve-descriptor")
            values = descriptor_environment(descriptor, args.source_descriptor, args.source_descriptor_raw_sha256)
            write_github_env(args.github_env, values)
            print(dump({"status": "IMMUTABLE_SOURCE_DESCRIPTOR_RESOLVED", **values}), end="")
            return 0
        required_paths = (args.source_run, args.source_artifacts, args.manifest, args.reference_run, args.reference_artifacts, args.output)
        if any(path is None for path in required_paths) or args.handoff_head_sha is None:
            raise GuardRefusal("full validation paths and handoff head SHA are required")
        assert args.source_run and args.source_artifacts and args.manifest and args.reference_run and args.reference_artifacts and args.output
        report = validate(
            descriptor,
            load(args.source_run),
            load(args.source_artifacts),
            load(args.manifest),
            load(args.reference_run),
            load(args.reference_artifacts),
            source_descriptor_raw_sha256=actual_descriptor_sha,
            manifest_raw_sha256=raw_sha256(args.manifest),
            handoff_head_sha=args.handoff_head_sha,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump(report))
        print(dump(report), end="")
        return 0
    except Exception as exc:
        refusal = {
            "schemaVersion": 2,
            "stageId": GUARD_STAGE,
            "status": "REFUSED",
            "reason": str(exc),
            "surrogateTrainingAuthorized": False,
            "tier2Authorized": False,
            "productionPromotionAuthorized": False,
        }
        print(dump(refusal), file=sys.stderr, end="")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
