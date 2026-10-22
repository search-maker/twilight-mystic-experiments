from __future__ import annotations

import hashlib
import json
import types
from pathlib import Path
from typing import Any, Callable

ORIGINAL_EXECUTOR_REL = Path("experiments/aerosol-vertical-profile-sensitivity-v1/executor.py")
EXPECTED_ORIGINAL_EXECUTOR_GIT_BLOB_SHA1 = "68eb7f6916bae204e60f6a378eae25f9c2bff184"
FAILED_WORKFLOW_RUN_ID = 33137514692
RECOVERY_REASON = "EMPTY_DIAGNOSTIC_STREAM_ARTIFACT_CONTRACT_ONLY"
EMPTY_ALLOWED_DIAGNOSTIC_MEMBERS = frozenset({
    "syntax-stdout.txt",
    "syntax-stderr.txt",
    "solver-stdout.txt",
    "solver-stderr.txt",
})

OLD_SNIPPET = '''    for name in contract["rawMembersRequired"]:
        path = case_dir / name
        if not path.is_file() or path.stat().st_size == 0:
            raise ExecutionRefusal(f"required raw output/member missing or empty: {name}")
'''

NEW_SNIPPET = '''    for name in contract["rawMembersRequired"]:
        path = case_dir / name
        if not path.is_file():
            raise ExecutionRefusal(f"required raw output/member missing: {name}")
        if name not in {"syntax-stdout.txt", "syntax-stderr.txt", "solver-stdout.txt", "solver-stderr.txt"} and path.stat().st_size == 0:
            raise ExecutionRefusal(f"required scientific/raw output member empty: {name}")
'''


class RecoveryExecutionRefusal(RuntimeError):
    pass


def git_blob_sha1_bytes(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def git_blob_sha1(path: Path) -> str:
    return git_blob_sha1_bytes(path.read_bytes())


def recovery_executor_identity() -> dict[str, Any]:
    path = Path(__file__).resolve()
    return {
        "recoveryExecutorGitBlobSha1": git_blob_sha1(path),
        "authorizedOriginalExecutorGitBlobSha1": EXPECTED_ORIGINAL_EXECUTOR_GIT_BLOB_SHA1,
        "recoveryOfWorkflowRunId": FAILED_WORKFLOW_RUN_ID,
        "recoveryReason": RECOVERY_REASON,
        "emptyAllowedDiagnosticMembers": sorted(EMPTY_ALLOWED_DIAGNOSTIC_MEMBERS),
    }


def transformed_original_source(repository_root: Path) -> str:
    original = repository_root / ORIGINAL_EXECUTOR_REL
    if not original.is_file():
        raise RecoveryExecutionRefusal("authorized original AVPS executor missing")
    raw = original.read_bytes()
    actual = git_blob_sha1_bytes(raw)
    if actual != EXPECTED_ORIGINAL_EXECUTOR_GIT_BLOB_SHA1:
        raise RecoveryExecutionRefusal(
            f"authorized original AVPS executor Git blob drift: {actual}"
        )
    text = raw.decode("utf-8")
    count = text.count(OLD_SNIPPET)
    if count != 1:
        raise RecoveryExecutionRefusal(
            f"expected exactly one recoverable raw-member snippet, got {count}"
        )
    transformed = text.replace(OLD_SNIPPET, NEW_SNIPPET, 1)
    if transformed.count(NEW_SNIPPET) != 1 or OLD_SNIPPET in transformed:
        raise RecoveryExecutionRefusal("in-memory executor transformation did not bind exactly")
    compile(transformed, str(original) + "::transport-recovery", "exec")
    return transformed


def load_recovered_executor(repository_root: Path):
    source = transformed_original_source(repository_root)
    original = repository_root / ORIGINAL_EXECUTOR_REL
    module = types.ModuleType("avps_v1_authorized_executor_transport_recovery")
    module.__file__ = str(original)
    module.__package__ = None
    exec(compile(source, str(original) + "::transport-recovery", "exec"), module.__dict__)
    if not callable(getattr(module, "execute_case", None)):
        raise RecoveryExecutionRefusal("transformed authorized executor lacks execute_case")
    return module


def _rewrite_result_with_recovery_provenance(
    module: Any,
    result: dict[str, Any],
    case_result_path: Path,
) -> dict[str, Any]:
    if result.get("status") != "COMPLETED":
        raise RecoveryExecutionRefusal("authorized executor did not complete case")
    if result.get("retryPerformed") is not False or result.get("githubRerun") is not False:
        raise RecoveryExecutionRefusal("recovery must remain distinct from retry/GitHub rerun")
    if result.get("resumePerformed") is not False:
        raise RecoveryExecutionRefusal("recovery must not claim resume semantics")
    result = dict(result)
    result.pop("contentSha256", None)
    result.update({
        "transportRecovery": True,
        "recoveryOfWorkflowRunId": FAILED_WORKFLOW_RUN_ID,
        "recoveryReason": RECOVERY_REASON,
        "authorizedOriginalExecutorGitBlobSha1": EXPECTED_ORIGINAL_EXECUTOR_GIT_BLOB_SHA1,
        "recoveryExecutorGitBlobSha1": git_blob_sha1(Path(__file__).resolve()),
        "emptyDiagnosticStreamsPermittedByRecovery": sorted(EMPTY_ALLOWED_DIAGNOSTIC_MEMBERS),
        "scientificInputsChangedByRecovery": False,
        "seedAllocationChangedByRecovery": False,
        "caseUniverseChangedByRecovery": False,
        "runtimeIdentityChangedByRecovery": False,
        "resultOpeningAuthorizedByRecovery": False,
    })
    result["contentSha256"] = module.canonical_sha256(result)
    case_result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def execute_case_recovery(
    repository_root: Path,
    authorization_path: Path,
    guard_report_path: Path,
    runtime_report_path: Path,
    case_id: str,
    data_dir: Path,
    output_root: Path,
    uvspec: Path,
    *,
    allow_execution: bool = False,
    runner: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if not allow_execution:
        raise RecoveryExecutionRefusal("explicit allow_execution=True required")
    module = load_recovered_executor(repository_root)
    result = module.execute_case(
        repository_root,
        authorization_path,
        guard_report_path,
        runtime_report_path,
        case_id,
        data_dir,
        output_root,
        uvspec,
        allow_execution=True,
        runner=runner,
    )
    case_result_path = output_root / case_id / "case-result.json"
    if not case_result_path.is_file():
        raise RecoveryExecutionRefusal("authorized executor did not persist case-result.json")
    return _rewrite_result_with_recovery_provenance(module, result, case_result_path)
