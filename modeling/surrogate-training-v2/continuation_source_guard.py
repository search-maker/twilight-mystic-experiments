#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

SOURCE_RUN_ID = 31_065_046_524
SOURCE_RUN_ATTEMPT = 1
SOURCE_MAIN_SHA = "0ef7e011e00a4c4badcafb2f6ca06256026b1746"
SOURCE_AUTHORIZATION_REF = "18a5746778441d57b722c740a17c94af9b56e9c9"
SOURCE_AUTHORIZATION_ORDINAL = 12
SOURCE_EXECUTION_KEY = "twilight-surrogate-tier-1-v1:numerical:12"
SOURCE_TITLE = "Tier-1 precision continuation wave 2 ordinal 12"
SOURCE_BRANCH = "dispatch/tier1-precision-continuation-wave2-ordinal12-v1"
SOURCE_PREREGISTRATION_SHA256 = "3231c2e5842fb6d4af90ef8329c7f42cf0d9b707493b48de598e35ecf950f050"
SOURCE_SEEDS_SHA256 = "e69bcf733a5c937d7fb01137b62f34997de67d32678d23519b6e80054bdc4f3f"
CASE_COUNT = 32
GEOMETRY_COUNT = 16
BLOCKS = [5, 6]
MAX_CONFIGURED_PHOTON_HISTORIES = 4_600_000_000


class GuardRefusal(RuntimeError):
    pass


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GuardRefusal(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise GuardRefusal(f"expected object: {path}")
    return value


def _exact(value: dict[str, Any], expected: dict[str, Any], label: str) -> None:
    stale = {key: (value.get(key), wanted) for key, wanted in expected.items() if value.get(key) != wanted}
    if stale:
        raise GuardRefusal(f"{label} boundary changed: {stale}")


def _sealed(value: dict[str, Any], field: str, label: str) -> None:
    supplied = value.get(field)
    payload = {key: item for key, item in value.items() if key != field}
    if supplied != canonical_sha256(payload):
        raise GuardRefusal(f"{label} self-hash changed")


def _wrapper(
    value: dict[str, Any],
    *,
    stage_id: str,
    inner_key: str,
    inner_sha_key: str,
    label: str,
) -> dict[str, Any]:
    if value.get("stageId") != stage_id:
        raise GuardRefusal(f"{label} stage changed")
    _sealed(value, "payloadSha256", label)
    inner = value.get(inner_key)
    if not isinstance(inner, dict) or value.get(inner_sha_key) != canonical_sha256(inner):
        raise GuardRefusal(f"{label} inner hash changed")
    return inner


def validate(
    *,
    run: dict[str, Any],
    artifacts: dict[str, Any],
    manifest: dict[str, Any],
    aggregate: dict[str, Any],
    audit: dict[str, Any],
    analysis: dict[str, Any],
) -> dict[str, Any]:
    _exact(
        run,
        {
            "id": SOURCE_RUN_ID,
            "status": "completed",
            "conclusion": "success",
            "event": "push",
            "run_attempt": SOURCE_RUN_ATTEMPT,
            "display_title": SOURCE_TITLE,
            "head_branch": SOURCE_BRANCH,
            "head_sha": SOURCE_AUTHORIZATION_REF,
        },
        "source run",
    )
    values = artifacts.get("artifacts")
    if not isinstance(values, list):
        raise GuardRefusal("source artifact list missing")
    names = [item.get("name") for item in values if isinstance(item, dict)]
    if len(values) != 36 or len(set(names)) != 36:
        raise GuardRefusal(f"source artifact universe must be exactly 36, observed {len(values)}")
    expected_names = {
        "tier1-wave2-ordinal12-execution-manifest",
        "tier1-wave2-ordinal12-aggregate",
        "tier1-wave2-ordinal12-audit",
        "tier1-wave2-ordinal12-analysis",
    }
    case_names = [name for name in names if isinstance(name, str) and name.startswith("tier1-wave2-ordinal12-case-")]
    if len(case_names) != CASE_COUNT or not expected_names <= set(names):
        raise GuardRefusal("source artifacts are incomplete")
    for item in values:
        if not isinstance(item, dict):
            raise GuardRefusal("source artifact entry is malformed")
        digest = item.get("digest")
        if (
            item.get("expired") is not False
            or not isinstance(item.get("id"), int)
            or not isinstance(item.get("name"), str)
            or not isinstance(digest, str)
            or not digest.startswith("sha256:")
            or len(digest) != 71
        ):
            raise GuardRefusal(f"source artifact metadata invalid: {item.get('name')}")

    _sealed(manifest, "manifestSha256", "execution manifest")
    _exact(
        manifest,
        {
            "stageId": "tier1-precision-continuation-wave2-ordinal12-execution-v1",
            "status": "AUTHORIZED_FOR_ONE_ATTEMPT1_EXECUTION",
            "displayTitle": SOURCE_TITLE,
            "authorizationRef": SOURCE_AUTHORIZATION_REF,
            "authorizationOrdinal": SOURCE_AUTHORIZATION_ORDINAL,
            "executionKey": SOURCE_EXECUTION_KEY,
            "runId": SOURCE_RUN_ID,
            "runAttempt": SOURCE_RUN_ATTEMPT,
            "eventName": "push",
            "triggerBranch": SOURCE_BRANCH,
            "headBranch": "main",
            "headSha": SOURCE_MAIN_SHA,
            "blocks": BLOCKS,
            "wave": 2,
            "geometryCount": GEOMETRY_COUNT,
            "caseCount": CASE_COUNT,
            "maximumConfiguredPhotonHistories": MAX_CONFIGURED_PHOTON_HISTORIES,
            "githubRerunAllowed": False,
            "retryAllowed": False,
            "resumeAllowed": False,
            "automaticNextWave": False,
            "surrogateTrainingAuthorized": False,
            "internalHoldoutOpeningAuthorized": False,
            "tier2Authorized": False,
            "productionPromotionAuthorized": False,
        },
        "execution manifest",
    )
    if manifest.get("sourceBindings", {}).get("preregistrationSha256") != SOURCE_PREREGISTRATION_SHA256:
        raise GuardRefusal("preregistration binding changed")
    if manifest.get("seedProof", {}).get("wave2SeedsSha256") != SOURCE_SEEDS_SHA256:
        raise GuardRefusal("wave-two seed binding changed")
    duplicate = manifest.get("duplicateRunAudit")
    if not isinstance(duplicate, dict) or duplicate.get("status") != "NO_PRIOR_MATCHING_RUN" or duplicate.get("matchingRuns") != []:
        raise GuardRefusal("duplicate-run audit changed")
    cases = manifest.get("cases")
    if (
        not isinstance(cases, list)
        or len(cases) != CASE_COUNT
        or len({case.get("caseId") for case in cases if isinstance(case, dict)}) != CASE_COUNT
        or len({case.get("seed") for case in cases if isinstance(case, dict)}) != CASE_COUNT
        or {case.get("block") for case in cases if isinstance(case, dict)} != set(BLOCKS)
    ):
        raise GuardRefusal("manifest case or seed universe changed")

    aggregate_inner = _wrapper(
        aggregate,
        stage_id="tier1-precision-continuation-wave2-aggregate-v1",
        inner_key="aggregate",
        inner_sha_key="aggregateSha256",
        label="wave-two aggregate",
    )
    _exact(
        aggregate_inner,
        {
            "status": "COMPLETED",
            "classification": "CONTINUATION_WAVE_EXECUTION_COMPLETE",
            "executionComplete": True,
            "caseCountPlanned": CASE_COUNT,
            "caseCountObserved": CASE_COUNT,
            "configuredPhotonHistories": MAX_CONFIGURED_PHOTON_HISTORIES,
            "executionFailures": [],
            "structuralFailures": [],
            "additionalExecutionAutomaticallyAuthorized": False,
        },
        "wave-two aggregate",
    )
    audit_inner = _wrapper(
        audit,
        stage_id="tier1-precision-continuation-wave2-independent-audit-v1",
        inner_key="audit",
        inner_sha_key="auditSha256",
        label="wave-two audit",
    )
    _exact(
        audit_inner,
        {
            "status": "PASSED",
            "caseResultCount": CASE_COUNT,
            "failures": [],
            "independentlyRecomputedFromRawSelectedNodeRadiance": True,
            "additionalExecutionAutomaticallyAuthorized": False,
        },
        "wave-two audit",
    )
    if audit.get("aggregateSha256") != aggregate.get("aggregateSha256"):
        raise GuardRefusal("audit/aggregate binding changed")
    _exact(
        analysis,
        {
            "stageId": "tier1-precision-continuation-wave2-analysis-v1",
            "wave2AggregateSha256": aggregate["aggregateSha256"],
            "wave2AuditSha256": audit["auditSha256"],
            "additionalExecutionAutomaticallyAuthorized": False,
            "surrogateFitAuthorized": False,
            "internalHoldoutOpened": False,
            "tier2Authorized": False,
            "productionPromotionAuthorized": False,
        },
        "two-wave analysis",
    )
    _sealed(analysis, "analysisSha256", "two-wave analysis")
    body = analysis.get("analysis")
    if not isinstance(body, dict) or body.get("status") != "CONTINUATION_ANALYZED":
        raise GuardRefusal("two-wave analysis incomplete")
    points = body.get("points")
    if not isinstance(points, list) or len(points) != 20:
        raise GuardRefusal("two-wave analysis geometry universe changed")
    return {
        "schemaVersion": 1,
        "stageId": "surrogate-training-v2-continuation-source-guard-v1",
        "status": "TERMINAL_ORDINAL12_SOURCE_ACCEPTED_FOR_HANDOFF_DECISION",
        "sourceRunId": SOURCE_RUN_ID,
        "sourceRunAttempt": SOURCE_RUN_ATTEMPT,
        "sourceMainSha": SOURCE_MAIN_SHA,
        "sourceAuthorizationRef": SOURCE_AUTHORIZATION_REF,
        "sourceAuthorizationOrdinal": SOURCE_AUTHORIZATION_ORDINAL,
        "sourceExecutionKey": SOURCE_EXECUTION_KEY,
        "sourceArtifactCount": len(values),
        "sourceCaseArtifactCount": len(case_names),
        "nextWaveGeometryIds": body.get("nextWaveGeometryIds"),
        "exhaustedGeometryIds": body.get("exhaustedGeometryIds"),
        "scientificallyEligible": body.get("scientificallyEligible"),
        "surrogateTrainingAuthorized": False,
        "internalHoldoutOpeningAuthorized": False,
        "tier2Authorized": False,
        "productionPromotionAuthorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--aggregate", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--analysis", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = validate(
            run=load(args.run),
            artifacts=load(args.artifacts),
            manifest=load(args.manifest),
            aggregate=load(args.aggregate),
            audit=load(args.audit),
            analysis=load(args.analysis),
        )
        result["runRawSha256"] = raw_sha256(args.run)
        result["artifactListRawSha256"] = raw_sha256(args.artifacts)
        result["manifestRawSha256"] = raw_sha256(args.manifest)
        result["aggregateRawSha256"] = raw_sha256(args.aggregate)
        result["auditRawSha256"] = raw_sha256(args.audit)
        result["analysisRawSha256"] = raw_sha256(args.analysis)
        result["reportSha256"] = canonical_sha256(result)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump(result), encoding="utf-8", newline="\n")
        return 0
    except Exception as exc:
        print(dump({"status": "REFUSED", "reason": str(exc)}), end="")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
