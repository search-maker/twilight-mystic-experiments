from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

STAGE = "aerosol-family-challenge-v2-r8-timeout-recovery-v1"
AUTH_PATH = f"experiments/{STAGE}/authorization.json"
MANIFEST_PATH = f"evidence/{STAGE}/manifest.frozen.json"
FREEZE_PATH = f"evidence/{STAGE}/freeze-record.json"
PROTOCOL_PATH = f"experiments/{STAGE}/protocol.review.json"
CORE_PATH = f"experiments/{STAGE}/core.py"
PROCESS_RUNNER_PATH = f"experiments/{STAGE}/execution-candidate/process_runner.py"
EXECUTOR_PATH = f"experiments/{STAGE}/execution-candidate/executor.py"
SEED_AUDIT_PATH = f"experiments/{STAGE}/execution-candidate/seed_audit.py"
AUTH_HELPER_PATH = f"experiments/{STAGE}/execution-candidate/authorization.py"
PREAUTH_WORKFLOW_PATH = ".github/workflows/aerosol-family-v2-r8-timeout-recovery-v1-preauthorization.yml"
AUTH_REVIEW_WORKFLOW_PATH = ".github/workflows/aerosol-family-v2-r8-timeout-recovery-v1-authorization-review.yml"
EXECUTION_WORKFLOW_PATH = ".github/workflows/aerosol-family-v2-r8-timeout-recovery-v1-execution.yml"
RUNTIME_LOCK_RAW_SHA256 = "3b5fbec964642b04c73a6423b3355dbcc4ba5e84f9614f6d74420491bacc20c5"

SOURCE_R8_BYTE_BINDINGS = {
    "sourceR8CoreGitBlobSha1": ("experiments/aerosol-family-challenge-v2-r8/core.py", "04e93e1054ba2957383749ca4f4735b231993733"),
    "sourceR8AdapterGitBlobSha1": ("experiments/aerosol-family-challenge-v2-r8/adapter.py", "108af0a95274ee88fccf9d51d32f88ef0186bfaf"),
    "sourceR8DerivedChannelsGitBlobSha1": ("experiments/aerosol-family-challenge-v2-r8/derived_channels.py", "ccfd04d4c21188966351f4257e92893d7ce340c7"),
    "sourceR8AnalysisGitBlobSha1": ("experiments/aerosol-family-challenge-v2-r8/analysis.py", "50b64b5c8a7a9d28a1c7174c1a1fda8d7380799d"),
    "sourceR8AnalysisContractGitBlobSha1": ("experiments/aerosol-family-challenge-v2-r8/analysis-contract.v3.json", "d2411cd7636d3d34a0b9132a48fbcea4ccf35d76"),
    "sourceR8WavelengthGridGitBlobSha1": ("experiments/aerosol-family-challenge-v2-r8/wavelength-grid-1nm.dat", "3bb3db96580d555ef758f57cabd6cac55b61cebb"),
}


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bindings(root: Path) -> dict[str, str]:
    paths = {
        "manifestRawSha256": MANIFEST_PATH,
        "freezeRecordRawSha256": FREEZE_PATH,
        "protocolRawSha256": PROTOCOL_PATH,
        "coreRawSha256": CORE_PATH,
        "processRunnerRawSha256": PROCESS_RUNNER_PATH,
        "executorRawSha256": EXECUTOR_PATH,
        "seedAuditRawSha256": SEED_AUDIT_PATH,
        "authorizationHelperRawSha256": AUTH_HELPER_PATH,
        "preauthorizationWorkflowRawSha256": PREAUTH_WORKFLOW_PATH,
        "authorizationReviewWorkflowRawSha256": AUTH_REVIEW_WORKFLOW_PATH,
        "executionWorkflowRawSha256": EXECUTION_WORKFLOW_PATH,
    }
    out = {key: sha(root / path) for key, path in paths.items()}
    for key, (rel, expected) in SOURCE_R8_BYTE_BINDINGS.items():
        observed = git_blob_sha1(root / rel)
        if observed != expected:
            raise ValueError(f"source R8 byte binding drift: {rel} expected={expected} observed={observed}")
        out[key] = observed
    return out


def make(root: Path, ordinal: int, parent: str) -> dict[str, Any]:
    if ordinal <= 34:
        raise ValueError("recovery requires a fresh ordinal above consumed ordinal 34")
    if len(parent) != 40:
        raise ValueError("authorization parent must be a full commit SHA")
    row: dict[str, Any] = {
        "schemaVersion": 1,
        "stageId": STAGE + "-authorization",
        "status": "AUTHORIZED_PENDING_SEPARATE_DISPATCH",
        "repositoryFullName": "search-maker/twilight-mystic-experiments",
        "enabled": True,
        "scientificExecutionAuthorized": True,
        "solverExecutionAuthorized": True,
        "dispatchAuthorized": False,
        "automaticDispatch": False,
        "consumed": False,
        "executionKey": f"{STAGE}:numerical:{ordinal}",
        "scientificOrdinal": ordinal,
        "authorizationBranch": f"authorization/{STAGE}-ordinal-{ordinal}",
        "dispatchBranch": f"dispatch/{STAGE}-ordinal-{ordinal}",
        "exactAuthorizationParentCommit": parent,
        "exactAuthorizationCommit": None,
        "runtimeLockRawSha256": RUNTIME_LOCK_RAW_SHA256,
        "githubRerunAllowed": False,
        "retryAllowed": False,
        "resumeAllowed": False,
        "sourceOrdinal34Reusable": False,
        "sourceOrdinal34AffectedGroupArtifactsReusable": False,
        "resultsOpenedBeforeRecoveryFreeze": False,
    }
    row.update(bindings(root))
    return row


def validate(root: Path, row: dict[str, Any], *, expected_parent: str | None = None) -> None:
    ordinal = row.get("scientificOrdinal")
    if not isinstance(ordinal, int) or ordinal <= 34:
        raise ValueError("authorization scientific ordinal invalid")
    expected = make(root, ordinal, str(row.get("exactAuthorizationParentCommit") or ""))
    if expected_parent is not None and row.get("exactAuthorizationParentCommit") != expected_parent:
        raise ValueError("authorization parent drift")
    if row != expected:
        differing = sorted(k for k in set(row) | set(expected) if row.get(k) != expected.get(k))
        raise ValueError(f"authorization document drift: {differing}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--ordinal", type=int, required=True)
    parser.add_argument("--parent", required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--validate", type=Path)
    args = parser.parse_args()
    root = args.repository_root.resolve()
    if args.validate:
        validate(root, json.loads(args.validate.read_text()), expected_parent=args.parent)
        print("AUTHORIZATION_DOCUMENT_VALID")
        return 0
    row = make(root, args.ordinal, args.parent)
    text = json.dumps(row, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
