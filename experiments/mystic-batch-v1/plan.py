#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

STAGE_ID = "mystic-batch-v1"
CASE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,79}$")
BATCH_ID_RE = CASE_ID_RE
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class BatchRefusal(RuntimeError):
    def __init__(self, code: str, reason: str, detail: Any | None = None) -> None:
        super().__init__(reason)
        self.code = code
        self.reason = reason
        self.detail = detail

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": "REFUSED",
            "stageId": STAGE_ID,
            "code": self.code,
            "reason": self.reason,
            "detail": self.detail,
        }


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise BatchRefusal("invalid-json", f"cannot read JSON object: {path}", str(exc)) from exc
    if not isinstance(value, dict):
        raise BatchRefusal("invalid-json-object", f"expected JSON object: {path}")
    return value


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compact_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def dump_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def require_int(value: Any, name: str, minimum: int = 0) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise BatchRefusal("invalid-integer", f"{name} must be an integer >= {minimum}", value)
    return value


def validate_runtime(manifest: dict[str, Any], scientific: bool) -> None:
    runtime = manifest.get("runtime")
    if not isinstance(runtime, dict):
        raise BatchRefusal("runtime", "runtime must be an object")
    for field in ("python", "os", "architecture"):
        if not isinstance(runtime.get(field), str) or not runtime[field].strip():
            raise BatchRefusal("runtime", f"runtime.{field} must be a non-empty string")
    identity_fields = ("uvspecSha256", "libRadtranDataSha256", "atmosphereSha256")
    if scientific:
        if not isinstance(runtime.get("containerImageDigest"), str) or not DIGEST_RE.fullmatch(runtime["containerImageDigest"]):
            raise BatchRefusal("runtime", "scientific mode requires containerImageDigest pinned by sha256")
        for field in identity_fields:
            value = runtime.get(field)
            if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
                raise BatchRefusal("runtime", f"scientific mode requires runtime.{field}")
    else:
        if runtime.get("containerImageDigest") is not None:
            raise BatchRefusal("runtime", "synthetic manifest must not claim a scientific container digest")
        for field in identity_fields:
            if runtime.get(field) is not None:
                raise BatchRefusal("runtime", f"synthetic manifest must not claim runtime.{field}")


def validate_manifest(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    if manifest.get("schemaVersion") != 1 or manifest.get("stageId") != STAGE_ID:
        raise BatchRefusal("manifest-header", "wrong schemaVersion or stageId")
    batch_id = manifest.get("batchId")
    if not isinstance(batch_id, str) or not BATCH_ID_RE.fullmatch(batch_id):
        raise BatchRefusal("batch-id", "invalid batchId", batch_id)
    mode = manifest.get("mode")
    if mode not in {"synthetic", "scientific"}:
        raise BatchRefusal("mode", "mode must be synthetic or scientific", mode)
    scientific = mode == "scientific"
    if manifest.get("scientificExecution") is not scientific:
        raise BatchRefusal("scientific-flag", "scientificExecution must exactly match mode")
    validate_runtime(manifest, scientific)

    frozen_inputs = manifest.get("frozenInputs")
    if not isinstance(frozen_inputs, dict) or not frozen_inputs:
        raise BatchRefusal("frozen-inputs", "frozenInputs must be a non-empty object")

    limits = manifest.get("limits")
    if not isinstance(limits, dict):
        raise BatchRefusal("limits", "limits must be an object")
    maximum_cases = require_int(limits.get("maximumCases"), "limits.maximumCases", 1)
    maximum_parallel = require_int(limits.get("maximumParallel"), "limits.maximumParallel", 1)
    maximum_photons = require_int(
        limits.get("maximumConfiguredMcPhotonsSum"),
        "limits.maximumConfiguredMcPhotonsSum",
        0,
    )
    require_int(limits.get("perCaseTimeoutSeconds"), "limits.perCaseTimeoutSeconds", 1)
    if maximum_parallel > maximum_cases:
        raise BatchRefusal("limits", "maximumParallel cannot exceed maximumCases")

    raw_cases = manifest.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise BatchRefusal("cases", "cases must be a non-empty array")
    if len(raw_cases) > maximum_cases:
        raise BatchRefusal("case-ceiling", "case count exceeds maximumCases")

    case_ids: set[str] = set()
    seeds: set[int] = set()
    ordinals: set[int] = set()
    normalized: list[dict[str, Any]] = []
    for raw_case in raw_cases:
        if not isinstance(raw_case, dict):
            raise BatchRefusal("case", "each case must be an object")
        case_id = raw_case.get("caseId")
        if not isinstance(case_id, str) or not CASE_ID_RE.fullmatch(case_id):
            raise BatchRefusal("case-id", "invalid caseId", case_id)
        ordinal = require_int(raw_case.get("ordinal"), f"{case_id}.ordinal", 1)
        seed = require_int(raw_case.get("seed"), f"{case_id}.seed", 1)
        photons = require_int(raw_case.get("photonHistories"), f"{case_id}.photonHistories", 1)
        if case_id in case_ids or seed in seeds or ordinal in ordinals:
            raise BatchRefusal(
                "duplicate-case-identity",
                "caseId, seed, and ordinal must each be unique",
                {"caseId": case_id, "seed": seed, "ordinal": ordinal},
            )
        case_ids.add(case_id)
        seeds.add(seed)
        ordinals.add(ordinal)
        normalized.append(
            {
                "ordinal": ordinal,
                "caseId": case_id,
                "seed": seed,
                "photonHistories": photons,
            }
        )

    normalized.sort(key=lambda item: item["ordinal"])
    expected_ordinals = list(range(1, len(normalized) + 1))
    actual_ordinals = [item["ordinal"] for item in normalized]
    if actual_ordinals != expected_ordinals:
        raise BatchRefusal("ordinals", "ordinals must be contiguous starting at one", actual_ordinals)
    photon_sum = sum(item["photonHistories"] for item in normalized)
    if photon_sum > maximum_photons:
        raise BatchRefusal(
            "photon-ceiling",
            "configured photon sum exceeds maximumConfiguredMcPhotonsSum",
            {"configured": photon_sum, "maximum": maximum_photons},
        )
    return normalized


def validate_authorization(
    manifest: dict[str, Any], authorization: dict[str, Any], manifest_sha256: str, allow_synthetic: bool
) -> None:
    if authorization.get("schemaVersion") != 1 or authorization.get("stageId") != STAGE_ID:
        raise BatchRefusal("authorization-header", "wrong authorization schemaVersion or stageId")
    if manifest["mode"] == "synthetic":
        if not allow_synthetic:
            raise BatchRefusal("synthetic-flag", "--allow-synthetic is required")
        if authorization.get("authorized") is not False:
            raise BatchRefusal("synthetic-authorization", "synthetic contract requires authorization to remain disabled")
        if authorization.get("scientificExecution") is not False:
            raise BatchRefusal("synthetic-authorization", "synthetic contract cannot carry scientific authorization")
        if authorization.get("consumed") is not False:
            raise BatchRefusal("synthetic-authorization", "disabled authorization must remain unconsumed")
        return

    required = {
        "authorized": True,
        "scientificExecution": True,
        "batchId": manifest["batchId"],
        "manifestRawSha256": manifest_sha256,
        "consumed": False,
    }
    stale = {key: (authorization.get(key), expected) for key, expected in required.items() if authorization.get(key) != expected}
    if stale:
        raise BatchRefusal("scientific-authorization", "scientific authorization is missing or stale", stale)
    require_int(authorization.get("authorizationOrdinal"), "authorization.authorizationOrdinal", 1)
    raise BatchRefusal(
        "scientific-adapter-not-installed",
        "scientific execution is intentionally disabled until a separately reviewed runtime adapter is installed",
    )


def build_plan(manifest_path: Path, authorization_path: Path, allow_synthetic: bool) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    authorization = load_json(authorization_path)
    cases = validate_manifest(manifest)
    manifest_sha256 = raw_sha256(manifest_path)
    validate_authorization(manifest, authorization, manifest_sha256, allow_synthetic)
    limits = manifest["limits"]
    matrix = {
        "include": [
            {
                "case_id": case["caseId"],
                "ordinal": case["ordinal"],
                "seed": case["seed"],
                "photon_histories": case["photonHistories"],
            }
            for case in cases
        ]
    }
    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "batchId": manifest["batchId"],
        "mode": manifest["mode"],
        "scientificExecution": False,
        "syntheticContractOnly": True,
        "manifestPath": str(manifest_path),
        "manifestRawSha256": manifest_sha256,
        "caseCount": len(cases),
        "maximumParallel": limits["maximumParallel"],
        "maximumConfiguredMcPhotonsSum": limits["maximumConfiguredMcPhotonsSum"],
        "configuredMcPhotonsSum": sum(case["photonHistories"] for case in cases),
        "perCaseTimeoutSeconds": limits["perCaseTimeoutSeconds"],
        "runtime": manifest["runtime"],
        "frozenInputs": manifest["frozenInputs"],
        "cases": cases,
        "matrix": matrix,
    }


def write_github_output(path: Path, plan: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"matrix={compact_json(plan['matrix'])}\n")
        handle.write(f"manifest_sha256={plan['manifestRawSha256']}\n")
        handle.write(f"max_parallel={plan['maximumParallel']}\n")
        handle.write(f"case_count={plan['caseCount']}\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--github-output", type=Path)
    parser.add_argument("--allow-synthetic", action="store_true")
    args = parser.parse_args()
    try:
        plan = build_plan(args.manifest, args.authorization, args.allow_synthetic)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump_json(plan))
        if args.github_output:
            write_github_output(args.github_output, plan)
        print(dump_json({"status": "PLANNED", "batchId": plan["batchId"], "caseCount": plan["caseCount"]}), end="")
        return 0
    except BatchRefusal as exc:
        print(dump_json(exc.as_dict()), end="")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
