#!/usr/bin/env python3
"""Review-only batch orchestration for ASIV matched stellar transport.

This file freezes deterministic sharding and complete-set artifact semantics for
the 3468 already-prefrozen non-native stellar transport cases. It has no solver
CLI and does not authorize scientific execution.

Future execution must preserve:
- candidate manifest order exactly;
- 75 training shards x 36 cases and 24 validation shards x 32 cases;
- one-shot/no-retry semantics inherited from the strict one-case gate;
- no shard mixing training and validation;
- no partial-shard or partial-universe validation/interpretation.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any, Callable

HERE = Path(__file__).resolve().parent
CANDIDATE_PATH = HERE / "execution_candidate.py"
STRICT_GATE_PATH = HERE / "execution_authorization_gate_review.py"
VALIDATOR_PATH = HERE / "assemble_validate_matched_stellar_v1.py"
BATCH_CONTRACT_PATH = HERE / "BATCH_ORCHESTRATION_CONTRACT.review.json"

EXPECTED_CANDIDATE_GIT_BLOB_SHA1 = "ec433aa3a594311738a6f6aa2b339a7e33d43447"
EXPECTED_STRICT_GATE_GIT_BLOB_SHA1 = "9bbe4f8fe64f7f32dd3e3e69469a15b30f658dde"
EXPECTED_VALIDATOR_GIT_BLOB_SHA1 = "9492ca0297136654bdacc81bf0fa2c90d63108b9"
EXPECTED_BATCH_MANIFEST_CANONICAL_SHA256 = "1756c756e1e865c729a3d93a1084c6081a5eefa6a05f4e874bdaed84e8359663"

TRAINING_SHARD_COUNT = 75
TRAINING_CASES_PER_SHARD = 36
VALIDATION_SHARD_COUNT = 24
VALIDATION_CASES_PER_SHARD = 32
TOTAL_SHARD_COUNT = 99
TOTAL_CASE_COUNT = 3468


class BatchOrchestrationRefusal(RuntimeError):
    pass


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


def _load_bound_module(path: Path, expected_blob: str, name: str):
    if git_blob_sha1(path) != expected_blob:
        raise BatchOrchestrationRefusal(f"bound source Git blob drift: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise BatchOrchestrationRefusal(f"cannot load bound module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_candidate():
    return _load_bound_module(CANDIDATE_PATH, EXPECTED_CANDIDATE_GIT_BLOB_SHA1, "matched_stellar_batch_candidate")


def load_strict_gate():
    return _load_bound_module(STRICT_GATE_PATH, EXPECTED_STRICT_GATE_GIT_BLOB_SHA1, "matched_stellar_batch_strict_gate")


def load_validator():
    return _load_bound_module(VALIDATOR_PATH, EXPECTED_VALIDATOR_GIT_BLOB_SHA1, "matched_stellar_batch_validator")


def _shard_role_cases(role: str, rows: list[dict[str, Any]], shard_count: int,
                      cases_per_shard: int) -> list[dict[str, Any]]:
    if len(rows) != shard_count * cases_per_shard:
        raise BatchOrchestrationRefusal(f"{role} cardinality does not divide into frozen shards")
    out: list[dict[str, Any]] = []
    for shard_index in range(shard_count):
        start = shard_index * cases_per_shard
        chunk = rows[start:start + cases_per_shard]
        case_ids = [str(row.get("caseId")) for row in chunk]
        if len(case_ids) != len(set(case_ids)):
            raise BatchOrchestrationRefusal(f"duplicate caseId inside {role} shard {shard_index}")
        out.append({
            "shardId": f"{role}-{shard_index:03d}",
            "role": role,
            "shardIndex": shard_index,
            "caseCount": cases_per_shard,
            "caseIds": case_ids,
        })
    return out


def build_batch_manifest() -> dict[str, Any]:
    candidate = load_candidate()
    source = candidate.build_prefrozen_manifest()
    training = list(source["training"]["cases"])
    validation = list(source["validation"]["cases"])
    if len(training) != 2700 or len(validation) != 768:
        raise BatchOrchestrationRefusal("prefrozen candidate case cardinality drift")
    shards = [
        *_shard_role_cases("training", training, TRAINING_SHARD_COUNT, TRAINING_CASES_PER_SHARD),
        *_shard_role_cases("validation", validation, VALIDATION_SHARD_COUNT, VALIDATION_CASES_PER_SHARD),
    ]
    flat = [case_id for shard in shards for case_id in shard["caseIds"]]
    expected = [str(row["caseId"]) for row in training] + [str(row["caseId"]) for row in validation]
    if flat != expected:
        raise BatchOrchestrationRefusal("batch sharding does not preserve exact candidate manifest order")
    if len(flat) != TOTAL_CASE_COUNT or len(set(flat)) != TOTAL_CASE_COUNT:
        raise BatchOrchestrationRefusal("batch sharding must cover 3468 unique cases exactly once")
    manifest = {
        "schemaVersion": 1,
        "stageId": "asiv-matched-stellar-transport-v1-batch-orchestration",
        "status": "PREFROZEN_BATCH_SHARDS_NO_SOLVER_EXECUTION",
        "totalCaseCount": TOTAL_CASE_COUNT,
        "shardCount": TOTAL_SHARD_COUNT,
        "roles": {
            "training": {"caseCount": 2700, "shardCount": TRAINING_SHARD_COUNT, "casesPerShard": TRAINING_CASES_PER_SHARD},
            "validation": {"caseCount": 768, "shardCount": VALIDATION_SHARD_COUNT, "casesPerShard": VALIDATION_CASES_PER_SHARD},
        },
        "shards": shards,
    }
    observed = canonical_sha256(manifest)
    if observed != EXPECTED_BATCH_MANIFEST_CANONICAL_SHA256:
        raise BatchOrchestrationRefusal(
            f"batch manifest canonical hash drift: {observed} != {EXPECTED_BATCH_MANIFEST_CANONICAL_SHA256}"
        )
    return manifest


def current_batch_binding() -> dict[str, Any]:
    batch = build_batch_manifest()
    contract = json.loads(BATCH_CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract.get("schemaVersion") != 1 or contract.get("stageId") != batch["stageId"]:
        raise BatchOrchestrationRefusal("batch contract schema/stage drift")
    if contract.get("status") != "FROZEN_REVIEW_ONLY_BATCH_ORCHESTRATION_NO_AUTHORIZATION":
        raise BatchOrchestrationRefusal("batch review contract unexpectedly changed authorization state")
    this_blob = git_blob_sha1(Path(__file__).resolve())
    if contract.get("sourceBindings", {}).get("batchOrchestrationGitBlobSha1") != this_blob:
        raise BatchOrchestrationRefusal("batch contract does not bind current batch orchestrator bytes")
    return {
        "batchOrchestrationGitBlobSha1": this_blob,
        "batchContractGitBlobSha1": git_blob_sha1(BATCH_CONTRACT_PATH),
        "batchManifestCanonicalSha256": EXPECTED_BATCH_MANIFEST_CANONICAL_SHA256,
        "totalShardCount": TOTAL_SHARD_COUNT,
        "totalCaseCount": TOTAL_CASE_COUNT,
    }


def validate_batch_authorization(document: dict[str, Any]) -> None:
    gate = load_strict_gate()
    gate.validate_strict_authorization(document)
    if document.get("batchExecutionAuthorized") is not True:
        raise BatchOrchestrationRefusal("batch execution is not positively authorized")
    if document.get("partialShardInterpretationPermitted") is not False:
        raise BatchOrchestrationRefusal("partial shard interpretation must remain forbidden")
    if document.get("partialUniverseValidationPermitted") is not False:
        raise BatchOrchestrationRefusal("partial universe validation must remain forbidden")
    if document.get("batchBindings") != current_batch_binding():
        raise BatchOrchestrationRefusal("authorization does not bind exact batch contract/orchestrator/manifest")


def shard_rows(shard_id: str) -> tuple[str, list[dict[str, Any]]]:
    candidate = load_candidate()
    source = candidate.build_prefrozen_manifest()
    batch = build_batch_manifest()
    matches = [row for row in batch["shards"] if row["shardId"] == shard_id]
    if len(matches) != 1:
        raise BatchOrchestrationRefusal(f"unknown/non-unique shardId: {shard_id}")
    shard = matches[0]
    role = str(shard["role"])
    by_id = {str(row["caseId"]): row for row in source[role]["cases"]}
    rows = [by_id[case_id] for case_id in shard["caseIds"]]
    if [str(row["caseId"]) for row in rows] != shard["caseIds"]:
        raise BatchOrchestrationRefusal("shard case lookup/order drift")
    return role, rows


def execute_shard_strict(*, shard_id: str, authorization: dict[str, Any],
                         runtime_report: dict[str, Any], output_root: Path,
                         process_runner: Callable[..., dict[str, Any]] | None = None,
                         allow_execution: bool = False) -> dict[str, Any]:
    """Future execution primitive; unavailable unless all external gates are positive."""
    if allow_execution is not True:
        raise BatchOrchestrationRefusal("explicit allow_execution=True is required")
    validate_batch_authorization(authorization)
    gate = load_strict_gate()
    role, rows = shard_rows(shard_id)
    output_root = Path(output_root)
    if output_root.exists():
        raise BatchOrchestrationRefusal("shard output root must not already exist")
    partial = output_root.with_name(output_root.name + ".partial")
    if partial.exists():
        raise BatchOrchestrationRefusal("partial shard output already exists; resume is forbidden")
    partial.mkdir(parents=True, exist_ok=False)
    results: list[dict[str, Any]] = []
    for row in rows:
        result = gate.execute_one_case_strict(
            authorization=authorization,
            runtime_report=runtime_report,
            family=str(row["family"]),
            target_altitude_deg=float(row["targetAltitudeDeg"]),
            observer_elevation_m=float(row["observerElevationM"]),
            aod550=float(row["aod550"]),
            process_runner=process_runner,
        )
        payload = dict(result)
        payload["caseId"] = str(row["caseId"])
        payload["caseRole"] = role
        case_path = partial / f"{row['caseId']}.json"
        case_path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
        results.append(payload)
    expected_count = TRAINING_CASES_PER_SHARD if role == "training" else VALIDATION_CASES_PER_SHARD
    if len(results) != expected_count:
        raise BatchOrchestrationRefusal("completed shard cardinality drift")
    summary = {
        "schemaVersion": 1,
        "stageId": "asiv-matched-stellar-transport-v1-complete-shard",
        "status": "COMPLETE_SHARD_EXECUTED_ONCE",
        "shardId": shard_id,
        "role": role,
        "caseCount": len(results),
        "caseIds": [str(row["caseId"]) for row in rows],
        "batchManifestCanonicalSha256": EXPECTED_BATCH_MANIFEST_CANONICAL_SHA256,
        "retryPermitted": False,
        "resumePermitted": False,
        "githubRerunPermitted": False,
        "partialShardInterpretationPermitted": False,
    }
    (partial / "shard-result.json").write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    partial.rename(output_root)
    return summary


def collect_complete_case_payloads(shard_roots: list[Path]) -> list[dict[str, Any]]:
    """Flatten only a complete exact-99-shard artifact universe for validation."""
    batch = build_batch_manifest()
    expected = {str(row["shardId"]): row for row in batch["shards"]}
    seen: dict[str, Path] = {}
    for root_raw in shard_roots:
        root = Path(root_raw)
        summary_path = root / "shard-result.json"
        if not summary_path.is_file():
            raise BatchOrchestrationRefusal("shard artifact missing shard-result.json")
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        shard_id = str(summary.get("shardId"))
        if shard_id in seen:
            raise BatchOrchestrationRefusal(f"duplicate shard artifact: {shard_id}")
        if shard_id not in expected:
            raise BatchOrchestrationRefusal(f"unexpected shard artifact: {shard_id}")
        frozen = expected[shard_id]
        if summary.get("status") != "COMPLETE_SHARD_EXECUTED_ONCE":
            raise BatchOrchestrationRefusal(f"incomplete shard status: {shard_id}")
        if summary.get("role") != frozen["role"] or summary.get("caseIds") != frozen["caseIds"]:
            raise BatchOrchestrationRefusal(f"shard membership/order drift: {shard_id}")
        if int(summary.get("caseCount", -1)) != int(frozen["caseCount"]):
            raise BatchOrchestrationRefusal(f"shard case count drift: {shard_id}")
        if summary.get("batchManifestCanonicalSha256") != EXPECTED_BATCH_MANIFEST_CANONICAL_SHA256:
            raise BatchOrchestrationRefusal(f"shard manifest binding drift: {shard_id}")
        if any(summary.get(key) is not False for key in ("retryPermitted", "resumePermitted", "githubRerunPermitted", "partialShardInterpretationPermitted")):
            raise BatchOrchestrationRefusal(f"shard retry/resume/partial semantics drift: {shard_id}")
        seen[shard_id] = root
    if set(seen) != set(expected):
        missing = sorted(set(expected) - set(seen))
        raise BatchOrchestrationRefusal(f"partial shard universe forbidden; missing {len(missing)} of 99 shards")
    payloads: list[dict[str, Any]] = []
    for shard in batch["shards"]:
        root = seen[shard["shardId"]]
        for case_id in shard["caseIds"]:
            path = root / f"{case_id}.json"
            if not path.is_file():
                raise BatchOrchestrationRefusal(f"case artifact missing: {case_id}")
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("caseId") != case_id or payload.get("caseRole") != shard["role"]:
                raise BatchOrchestrationRefusal(f"case artifact identity drift: {case_id}")
            payloads.append(payload)
    if len(payloads) != TOTAL_CASE_COUNT:
        raise BatchOrchestrationRefusal("complete case payload count drift")
    return payloads


def validate_complete_universe(*, shard_roots: list[Path], sed_bundle_path: Path,
                               johnson_v_path: Path) -> dict[str, Any]:
    payloads = collect_complete_case_payloads(shard_roots)
    validator = load_validator()
    return validator.assemble_and_validate(
        case_payloads=payloads,
        sed_bundle_path=Path(sed_bundle_path),
        johnson_v_path=Path(johnson_v_path),
    )


def main() -> int:
    batch = build_batch_manifest()
    print(json.dumps({
        "status": "REVIEW_ONLY_BATCH_ORCHESTRATION_NO_EXECUTION_CLI",
        "batchManifestCanonicalSha256": EXPECTED_BATCH_MANIFEST_CANONICAL_SHA256,
        "shardCount": batch["shardCount"],
        "totalCaseCount": batch["totalCaseCount"],
        "scientificExecutionAuthorized": False,
        "solverExecutionAuthorized": False,
        "partialResultInterpretationPermitted": False,
        "pandoraHoldoutAccessAllowed": False,
        "productionAuthorized": False,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
