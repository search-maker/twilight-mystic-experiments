#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

STAGE_ID = "mystic-batch-v1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._:-]{2,159}$")


class GuardRefusal(RuntimeError):
    def __init__(self, code: str, reason: str, detail: Any | None = None) -> None:
        super().__init__(reason)
        self.code = code
        self.reason = reason
        self.detail = detail

    def as_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": 1,
            "stageId": STAGE_ID,
            "status": "REFUSED_BEFORE_SYNTAX_OR_SOLVER",
            "code": self.code,
            "reason": self.reason,
            "detail": self.detail,
        }


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise GuardRefusal("invalid-json", f"cannot read JSON object: {path}", str(exc)) from exc
    if not isinstance(value, dict):
        raise GuardRefusal("invalid-json-object", f"expected JSON object: {path}")
    return value


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def require_sha(value: Any, name: str) -> str:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise GuardRefusal("invalid-sha256", f"{name} must be a lowercase SHA-256 digest", value)
    return value


def require_int(value: Any, name: str, minimum: int = 0) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise GuardRefusal("invalid-integer", f"{name} must be an integer >= {minimum}", value)
    return value


def validate_relative_repo_path(path: Path, name: str) -> str:
    text = path.as_posix()
    if path.is_absolute() or ".." in path.parts or text.startswith("./"):
        raise GuardRefusal("invalid-path", f"{name} must be a normalized repository-relative path", text)
    return text


def validate_guard(
    repository_root: Path,
    authorization_path: Path,
    manifest_path: Path,
    adapter_path: Path,
    workflow_path: Path,
    runtime_lock_path: Path,
    authorization_ref: str,
    execution_key: str,
    authorization_ordinal: int,
    require_github_context: bool = True,
) -> dict[str, Any]:
    repository_root = repository_root.resolve()
    auth_rel = validate_relative_repo_path(authorization_path, "authorization")
    manifest_rel = validate_relative_repo_path(manifest_path, "manifest")
    adapter_rel = validate_relative_repo_path(adapter_path, "adapter")
    workflow_rel = validate_relative_repo_path(workflow_path, "workflow")
    lock_rel = validate_relative_repo_path(runtime_lock_path, "runtime lock")
    authorization_abs = repository_root / auth_rel
    manifest_abs = repository_root / manifest_rel
    adapter_abs = repository_root / adapter_rel
    workflow_abs = repository_root / workflow_rel
    lock_abs = repository_root / lock_rel
    for path, label in (
        (authorization_abs, "authorization"),
        (manifest_abs, "manifest"),
        (adapter_abs, "adapter"),
        (workflow_abs, "workflow"),
        (lock_abs, "runtime lock"),
    ):
        if not path.is_file():
            raise GuardRefusal("missing-file", f"{label} file does not exist", str(path))

    if not ID_RE.fullmatch(execution_key):
        raise GuardRefusal("execution-key", "invalid execution key", execution_key)
    if authorization_ordinal < 1:
        raise GuardRefusal("authorization-ordinal", "authorization ordinal must be positive", authorization_ordinal)

    if require_github_context:
        expected_context = {
            "GITHUB_ACTIONS": "true",
            "GITHUB_EVENT_NAME": "workflow_dispatch",
            "GITHUB_RUN_ATTEMPT": "1",
        }
        stale_context = {key: (os.getenv(key), expected) for key, expected in expected_context.items() if os.getenv(key) != expected}
        if stale_context:
            raise GuardRefusal("github-context", "not exact first-attempt workflow_dispatch context", stale_context)

    authorization = load_json(authorization_abs)
    manifest = load_json(manifest_abs)
    required_auth = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "authorized": True,
        "scientificExecution": True,
        "successDoesNotAuthorizeProduction": True,
        "executionKey": execution_key,
        "batchId": manifest.get("batchId"),
        "manifestPath": manifest_rel,
        "manifestRawSha256": raw_sha256(manifest_abs),
        "runtimeLockRawSha256": raw_sha256(lock_abs),
        "scientificAdapterRawSha256": raw_sha256(adapter_abs),
        "executionWorkflowRawSha256": raw_sha256(workflow_abs),
        "authorizationOrdinal": authorization_ordinal,
        "consumed": False,
        "exactAuthorizationCommit": None,
    }
    stale = {key: (authorization.get(key), expected) for key, expected in required_auth.items() if authorization.get(key) != expected}
    if stale:
        raise GuardRefusal("authorization-stale", "authorization is missing, disabled, or stale", stale)

    if manifest.get("schemaVersion") != 1 or manifest.get("stageId") != STAGE_ID:
        raise GuardRefusal("manifest-header", "wrong manifest header")
    if manifest.get("mode") != "scientific" or manifest.get("scientificExecution") is not True:
        raise GuardRefusal("manifest-mode", "manifest is not scientific")
    cases = manifest.get("cases")
    limits = manifest.get("limits")
    if not isinstance(cases, list) or not cases:
        raise GuardRefusal("manifest-cases", "manifest cases must be a non-empty array")
    if not isinstance(limits, dict):
        raise GuardRefusal("manifest-limits", "manifest limits must be an object")
    maximum_cases = require_int(limits.get("maximumCases"), "limits.maximumCases", 1)
    maximum_parallel = require_int(limits.get("maximumParallel"), "limits.maximumParallel", 1)
    maximum_photons = require_int(limits.get("maximumConfiguredMcPhotonsSum"), "limits.maximumConfiguredMcPhotonsSum", 1)
    require_int(limits.get("perCaseTimeoutSeconds"), "limits.perCaseTimeoutSeconds", 1)
    if len(cases) > maximum_cases or maximum_parallel > maximum_cases:
        raise GuardRefusal("manifest-limits", "case or parallel ceiling violated")
    photon_sum = 0
    seen_ids: set[str] = set()
    seen_seeds: set[int] = set()
    seen_ordinals: set[int] = set()
    for case in cases:
        if not isinstance(case, dict):
            raise GuardRefusal("manifest-case", "each case must be an object")
        case_id = case.get("caseId")
        ordinal = require_int(case.get("ordinal"), "case.ordinal", 1)
        seed = require_int(case.get("seed"), "case.seed", 1)
        photons = require_int(case.get("photonHistories"), "case.photonHistories", 1)
        if not isinstance(case_id, str) or not ID_RE.fullmatch(case_id):
            raise GuardRefusal("case-id", "invalid case ID", case_id)
        if case_id in seen_ids or seed in seen_seeds or ordinal in seen_ordinals:
            raise GuardRefusal("duplicate-case", "case IDs, seeds, and ordinals must be unique")
        seen_ids.add(case_id)
        seen_seeds.add(seed)
        seen_ordinals.add(ordinal)
        photon_sum += photons
    if sorted(seen_ordinals) != list(range(1, len(cases) + 1)):
        raise GuardRefusal("case-ordinals", "ordinals must be contiguous starting at one")
    if photon_sum > maximum_photons:
        raise GuardRefusal("photon-ceiling", "configured photons exceed manifest ceiling")

    head = git(repository_root, "rev-parse", "HEAD")
    parent = git(repository_root, "rev-parse", "HEAD^")
    if head != authorization_ref:
        raise GuardRefusal("authorization-ref", "checked-out HEAD is not the supplied authorization ref", {"head": head, "input": authorization_ref})
    if authorization.get("exactAuthorizationParentCommit") != parent:
        raise GuardRefusal("authorization-parent", "authorization parent mismatch", {"actual": parent, "authorized": authorization.get("exactAuthorizationParentCommit")})
    changed = git(repository_root, "diff", "--name-only", parent, head).splitlines()
    if changed != [auth_rel]:
        raise GuardRefusal("one-purpose-commit", "authorization commit must change exactly one authorization file", changed)

    report = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "AUTHORIZED",
        "batchId": manifest["batchId"],
        "executionKey": execution_key,
        "authorizationRef": head,
        "authorizationParentCommit": parent,
        "authorizationOrdinal": authorization_ordinal,
        "manifestPath": manifest_rel,
        "manifestRawSha256": raw_sha256(manifest_abs),
        "caseCount": len(cases),
        "maximumParallel": maximum_parallel,
        "configuredMcPhotonsSum": photon_sum,
        "runtimeLockRawSha256": raw_sha256(lock_abs),
        "scientificAdapterRawSha256": raw_sha256(adapter_abs),
        "executionWorkflowRawSha256": raw_sha256(workflow_abs),
        "boundary": "authorization verified before syntax check or solver execution",
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, default=Path("."))
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--adapter", type=Path, required=True)
    parser.add_argument("--workflow", type=Path, required=True)
    parser.add_argument("--runtime-lock", type=Path, required=True)
    parser.add_argument("--authorization-ref", required=True)
    parser.add_argument("--execution-key", required=True)
    parser.add_argument("--authorization-ordinal", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = validate_guard(
            args.repository_root,
            args.authorization,
            args.manifest,
            args.adapter,
            args.workflow,
            args.runtime_lock,
            args.authorization_ref,
            args.execution_key,
            args.authorization_ordinal,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump_json(report))
        print(dump_json(report), end="")
        return 0
    except Exception as exc:
        refusal = exc.as_dict() if isinstance(exc, GuardRefusal) else GuardRefusal("unexpected-error", str(exc)).as_dict()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump_json(refusal))
        print(dump_json(refusal), end="", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
