#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

STAGE_ID = "mystic-batch-v1"
ADAPTER_ID = "mystic-spectral-radiance-v1"
AUTHORIZATION_PATH = "experiments/mystic-batch-v1/authorization.scientific.json"
CASE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,79}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class PlanRefusal(RuntimeError):
    def __init__(self, code: str, reason: str, detail: Any | None = None) -> None:
        super().__init__(reason)
        self.code = code
        self.reason = reason
        self.detail = detail

    def as_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": 1,
            "stageId": STAGE_ID,
            "status": "REFUSED_BEFORE_RUNTIME_OR_SOLVER",
            "code": self.code,
            "reason": self.reason,
            "detail": self.detail,
        }


def dump_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def compact_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise PlanRefusal("invalid-json", f"cannot read JSON object: {path}", str(exc)) from exc
    if not isinstance(value, dict):
        raise PlanRefusal("invalid-json-object", f"expected JSON object: {path}")
    return value


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_int(value: Any, name: str, minimum: int = 0) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise PlanRefusal("invalid-integer", f"{name} must be an integer >= {minimum}", value)
    return value


def require_number(value: Any, name: str, minimum: float | None = None) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)):
        raise PlanRefusal("invalid-number", f"{name} must be finite", value)
    result = float(value)
    if minimum is not None and result < minimum:
        raise PlanRefusal("invalid-number", f"{name} must be >= {minimum}", result)
    return result


def require_sha256(value: Any, name: str) -> str:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise PlanRefusal("invalid-sha256", f"{name} must be a lowercase SHA-256 digest", value)
    return value


def require_relative_path(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise PlanRefusal("invalid-path", f"{name} must be a non-empty relative path", value)
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise PlanRefusal("invalid-path", f"{name} must not be absolute or escape its root", value)
    return path.as_posix()


def validate_manifest(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    expected = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "mode": "scientific",
        "scientificExecution": True,
        "adapterId": ADAPTER_ID,
    }
    stale = {key: (manifest.get(key), value) for key, value in expected.items() if manifest.get(key) != value}
    if stale:
        raise PlanRefusal("manifest-header", "manifest is not an executable scientific batch", stale)
    batch_id = manifest.get("batchId")
    if not isinstance(batch_id, str) or not CASE_ID_RE.fullmatch(batch_id):
        raise PlanRefusal("batch-id", "invalid batchId", batch_id)

    runtime = manifest.get("runtime")
    if not isinstance(runtime, dict):
        raise PlanRefusal("runtime", "runtime must be an object")
    if runtime.get("kind") != "micromamba-lock":
        raise PlanRefusal("runtime", "this execution workflow currently supports only micromamba-lock")
    package = runtime.get("exactPackageSpec")
    if not isinstance(package, str) or any(ch.isspace() for ch in package) or package.count("=") < 2:
        raise PlanRefusal("runtime", "runtime exactPackageSpec must identify one exact package build", package)
    for field in (
        "uvspecSha256",
        "uvspecHelpSha256",
        "libRadtranDataTreeSha256",
        "atmosphereSha256",
        "runtimeLockRawSha256",
    ):
        require_sha256(runtime.get(field), f"runtime.{field}")

    frozen = manifest.get("frozenInputs")
    if not isinstance(frozen, dict) or not frozen:
        raise PlanRefusal("frozen-inputs", "frozenInputs must be a non-empty object")
    nodes = frozen.get("diagnosticNodesNm")
    if not isinstance(nodes, list) or not nodes or any(not isinstance(node, int) or isinstance(node, bool) for node in nodes):
        raise PlanRefusal("diagnostic-nodes", "diagnosticNodesNm must be a non-empty integer array")
    if sorted(set(nodes)) != nodes:
        raise PlanRefusal("diagnostic-nodes", "diagnostic nodes must be sorted and unique")

    analysis = manifest.get("analysis")
    if not isinstance(analysis, dict) or analysis.get("metricId") != "selected-photopic-contribution-v1":
        raise PlanRefusal("analysis", "unsupported or missing analysis metric")
    weights = analysis.get("photopicWeights")
    if not isinstance(weights, list) or len(weights) != len(nodes):
        raise PlanRefusal("analysis", "photopicWeights must align with diagnosticNodesNm")
    for index, weight in enumerate(weights):
        require_number(weight, f"analysis.photopicWeights[{index}]", 0.0)
    require_number(analysis.get("wavelengthBinWidthNm"), "analysis.wavelengthBinWidthNm", 0.0)
    require_number(analysis.get("luminousEfficacyLmPerW"), "analysis.luminousEfficacyLmPerW", 0.0)
    require_number(analysis.get("radianceUnitScale"), "analysis.radianceUnitScale", 0.0)

    limits = manifest.get("limits")
    if not isinstance(limits, dict):
        raise PlanRefusal("limits", "limits must be an object")
    maximum_cases = require_int(limits.get("maximumCases"), "limits.maximumCases", 1)
    maximum_parallel = require_int(limits.get("maximumParallel"), "limits.maximumParallel", 1)
    maximum_photons = require_int(
        limits.get("maximumConfiguredMcPhotonsSum"),
        "limits.maximumConfiguredMcPhotonsSum",
        1,
    )
    timeout = require_int(limits.get("perCaseTimeoutSeconds"), "limits.perCaseTimeoutSeconds", 1)
    if maximum_parallel > maximum_cases:
        raise PlanRefusal("limits", "maximumParallel cannot exceed maximumCases")
    if timeout > 7200:
        raise PlanRefusal("limits", "perCaseTimeoutSeconds exceeds hard execution ceiling")

    raw_cases = manifest.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise PlanRefusal("cases", "cases must be a non-empty array")
    if len(raw_cases) > maximum_cases:
        raise PlanRefusal("case-ceiling", "case count exceeds maximumCases")

    seen_ids: set[str] = set()
    seen_seeds: set[int] = set()
    seen_ordinals: set[int] = set()
    cases: list[dict[str, Any]] = []
    for raw_case in raw_cases:
        if not isinstance(raw_case, dict):
            raise PlanRefusal("case", "each case must be an object")
        case_id = raw_case.get("caseId")
        if not isinstance(case_id, str) or not CASE_ID_RE.fullmatch(case_id):
            raise PlanRefusal("case-id", "invalid caseId", case_id)
        ordinal = require_int(raw_case.get("ordinal"), f"{case_id}.ordinal", 1)
        seed = require_int(raw_case.get("seed"), f"{case_id}.seed", 1)
        photons = require_int(raw_case.get("photonHistories"), f"{case_id}.photonHistories", 1)
        parameters = raw_case.get("parameters")
        if not isinstance(parameters, dict):
            raise PlanRefusal("case-parameters", f"{case_id}.parameters must be an object")
        for key in ("sunDepressionDeg", "targetAltitudeDeg", "relativeAzimuthDeg", "observerElevationM"):
            require_number(parameters.get(key), f"{case_id}.parameters.{key}")
        if case_id in seen_ids or seed in seen_seeds or ordinal in seen_ordinals:
            raise PlanRefusal(
                "duplicate-case-identity",
                "caseId, seed, and ordinal must each be unique",
                {"caseId": case_id, "seed": seed, "ordinal": ordinal},
            )
        seen_ids.add(case_id)
        seen_seeds.add(seed)
        seen_ordinals.add(ordinal)
        cases.append(
            {
                "caseId": case_id,
                "ordinal": ordinal,
                "seed": seed,
                "photonHistories": photons,
                "parameters": parameters,
            }
        )
    cases.sort(key=lambda case: case["ordinal"])
    if [case["ordinal"] for case in cases] != list(range(1, len(cases) + 1)):
        raise PlanRefusal("ordinals", "ordinals must be contiguous starting at one")
    configured_photons = sum(case["photonHistories"] for case in cases)
    if configured_photons > maximum_photons:
        raise PlanRefusal(
            "photon-ceiling",
            "configured photon sum exceeds maximumConfiguredMcPhotonsSum",
            {"configured": configured_photons, "maximum": maximum_photons},
        )
    return cases


def validate_authorization(
    manifest_path: Path,
    manifest: dict[str, Any],
    authorization_path: Path,
    adapter_path: Path,
    runtime_lock_path: Path,
    execution_workflow_path: Path,
    manifest_authorized_path: str,
) -> dict[str, Any]:
    authorization = load_json(authorization_path)
    manifest_hash = raw_sha256(manifest_path)
    required = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "authorized": True,
        "scientificExecution": True,
        "batchId": manifest["batchId"],
        "manifestPath": manifest_authorized_path,
        "manifestRawSha256": manifest_hash,
        "runtimeLockRawSha256": raw_sha256(runtime_lock_path),
        "scientificAdapterRawSha256": raw_sha256(adapter_path),
        "executionWorkflowRawSha256": raw_sha256(execution_workflow_path),
        "consumed": False,
    }
    stale = {key: (authorization.get(key), value) for key, value in required.items() if authorization.get(key) != value}
    if stale:
        raise PlanRefusal("authorization", "scientific authorization is disabled, incomplete, or stale", stale)
    require_int(authorization.get("authorizationOrdinal"), "authorization.authorizationOrdinal", 1)
    if authorization.get("exactAuthorizationCommit") is not None:
        raise PlanRefusal("authorization", "exactAuthorizationCommit must remain null to avoid self-reference")
    return authorization


def validate_github_context(
    authorization: dict[str, Any], authorization_path: Path, repository_root: Path, allow_test_context: bool
) -> None:
    if allow_test_context:
        return
    required_environment = {
        "GITHUB_ACTIONS": "true",
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_RUN_ATTEMPT": "1",
    }
    stale = {key: (os.getenv(key), value) for key, value in required_environment.items() if os.getenv(key) != value}
    if stale:
        raise PlanRefusal("github-context", "wrong GitHub Actions context", stale)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repository_root, text=True).strip()
    parent = subprocess.check_output(["git", "rev-parse", "HEAD^"], cwd=repository_root, text=True).strip()
    if os.getenv("INPUT_AUTHORIZATION_REF") != head:
        raise PlanRefusal("authorization-purpose", "authorization input is not checked-out HEAD")
    if authorization.get("exactAuthorizationParentCommit") != parent:
        raise PlanRefusal("authorization-purpose", "authorization parent commit mismatch")
    changed = subprocess.check_output(
        ["git", "diff", "--name-only", parent, head], cwd=repository_root, text=True
    ).splitlines()
    expected_path = authorization_path.relative_to(repository_root).as_posix()
    if changed != [expected_path] or expected_path != AUTHORIZATION_PATH:
        raise PlanRefusal("authorization-purpose", "authorization commit is not one-purpose", changed)


def build_plan(
    manifest_path: Path,
    authorization_path: Path,
    adapter_path: Path,
    runtime_lock_path: Path,
    execution_workflow_path: Path,
    repository_root: Path,
    allow_test_context: bool = False,
) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    cases = validate_manifest(manifest)
    try:
        manifest_authorized_path = manifest_path.resolve().relative_to(repository_root.resolve()).as_posix()
    except ValueError as exc:
        raise PlanRefusal("manifest-path", "scientific manifest must be inside the checked-out repository", str(manifest_path)) from exc
    authorization = validate_authorization(
        manifest_path,
        manifest,
        authorization_path,
        adapter_path,
        runtime_lock_path,
        execution_workflow_path,
        manifest_authorized_path,
    )
    validate_github_context(authorization, authorization_path, repository_root, allow_test_context)

    manifest_hash = raw_sha256(manifest_path)
    ordinal = authorization["authorizationOrdinal"]
    if os.getenv("INPUT_BATCH_ID") and os.getenv("INPUT_BATCH_ID") != manifest["batchId"]:
        raise PlanRefusal("workflow-input", "batch ID input does not match manifest")
    if os.getenv("INPUT_MANIFEST_SHA256") and os.getenv("INPUT_MANIFEST_SHA256") != manifest_hash:
        raise PlanRefusal("workflow-input", "manifest hash input does not match manifest")
    if os.getenv("INPUT_AUTHORIZATION_ORDINAL") and os.getenv("INPUT_AUTHORIZATION_ORDINAL") != str(ordinal):
        raise PlanRefusal("workflow-input", "authorization ordinal input does not match authorization")

    limits = manifest["limits"]
    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "AUTHORIZED_PLAN",
        "scientificExecution": True,
        "successDoesNotAuthorizeProduction": True,
        "batchId": manifest["batchId"],
        "manifestPath": manifest_authorized_path,
        "manifestRawSha256": manifest_hash,
        "authorizationPath": authorization_path.as_posix(),
        "authorizationOrdinal": ordinal,
        "authorizationCommit": os.getenv("INPUT_AUTHORIZATION_REF"),
        "caseCount": len(cases),
        "maximumParallel": limits["maximumParallel"],
        "perCaseTimeoutSeconds": limits["perCaseTimeoutSeconds"],
        "maximumConfiguredMcPhotonsSum": limits["maximumConfiguredMcPhotonsSum"],
        "configuredMcPhotonsSum": sum(case["photonHistories"] for case in cases),
        "runtime": manifest["runtime"],
        "frozenInputs": manifest["frozenInputs"],
        "analysis": manifest["analysis"],
        "cases": cases,
        "matrix": {
            "include": [
                {
                    "case_id": case["caseId"],
                    "ordinal": case["ordinal"],
                    "seed": case["seed"],
                    "photon_histories": case["photonHistories"],
                }
                for case in cases
            ]
        },
        "exactHashes": {
            "adapter": raw_sha256(adapter_path),
            "runtimeLock": raw_sha256(runtime_lock_path),
            "executionWorkflow": raw_sha256(execution_workflow_path),
        },
        "boundary": "authorization and exact plan only; no runtime installation, syntax check, or solver execution",
    }


def write_github_output(path: Path, plan: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"matrix={compact_json(plan['matrix'])}\n")
        handle.write(f"max_parallel={plan['maximumParallel']}\n")
        handle.write(f"case_count={plan['caseCount']}\n")
        handle.write(f"per_case_timeout={plan['perCaseTimeoutSeconds']}\n")
        handle.write(f"manifest_path={plan['manifestPath']}\n")
        handle.write(f"manifest_sha256={plan['manifestRawSha256']}\n")
        handle.write(f"package_spec={plan['runtime']['exactPackageSpec']}\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--adapter", type=Path, required=True)
    parser.add_argument("--runtime-lock", type=Path, required=True)
    parser.add_argument("--execution-workflow", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--github-output", type=Path)
    parser.add_argument("--allow-test-context", action="store_true")
    args = parser.parse_args()
    try:
        plan = build_plan(
            args.manifest,
            args.authorization,
            args.adapter,
            args.runtime_lock,
            args.execution_workflow,
            args.repository_root,
            args.allow_test_context,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump_json(plan))
        if args.github_output:
            write_github_output(args.github_output, plan)
        print(dump_json({"status": "AUTHORIZED_PLAN", "batchId": plan["batchId"], "caseCount": plan["caseCount"]}), end="")
        return 0
    except PlanRefusal as exc:
        print(dump_json(exc.as_dict()), end="", file=sys.stderr)
        return 2
    except Exception as exc:
        print(dump_json(PlanRefusal("unexpected-error", str(exc)).as_dict()), end="", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
