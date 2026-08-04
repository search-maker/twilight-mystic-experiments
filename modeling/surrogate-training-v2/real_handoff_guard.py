#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SOURCE_RUN_ID = 30952457327
SOURCE_WORKFLOW_ID = 327347956
SOURCE_RUN_NUMBER = 1
SOURCE_HEAD_SHA = "c9679a515c5f4538345d0d83252bcd8e37eb7b7e"
SOURCE_PATH = ".github/workflows/twilight-surrogate-tier-1-ordinal2-execution.yml"
SOURCE_DISPLAY_TITLE = (
    "MYSTIC batch v1 | key=twilight-surrogate-tier-1-v1:numerical:2 | "
    "auth=9f3ef4b2afd93d5ae15a45ac70c9f27e32636f88 | ordinal=2"
)

REFERENCE_RUN_ID = 30905632743
REFERENCE_WORKFLOW_ID = 326688920
REFERENCE_HEAD_SHA = "9ab74efabfd34799aeeb5c9220a84639861f739d"
REFERENCE_PATH = ".github/workflows/twilight-surrogate-tier-1-proposal.yml"
REFERENCE_ARTIFACT_ID = 8890906227
REFERENCE_ARTIFACT_NAME = "twilight-surrogate-tier-1-proposal-v1"
REFERENCE_ARTIFACT_DIGEST = "sha256:899507d315ae25db88babb3f610587fca24238e7a7000038eed009c7a14af9a0"

PREFLIGHT_ARTIFACT_NAME = "twilight-surrogate-tier-1-ordinal2-execution-preflight"
AGGREGATE_ARTIFACT_NAME = "twilight-surrogate-tier-1-ordinal2-aggregate"
AUDIT_ARTIFACT_NAME = "twilight-surrogate-tier-1-ordinal2-audit"
ANALYSIS_ARTIFACT_NAME = "twilight-surrogate-tier-1-ordinal2-analysis"
CASE_ARTIFACT_PREFIX = "twilight-surrogate-tier-1-ordinal2-case-"
CASE_COUNT = 96
SOURCE_ARTIFACT_COUNT = 100


class GuardRefusal(RuntimeError):
    pass


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise GuardRefusal(f"expected JSON object: {path}")
    return value


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


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


def validate_source_run(run: dict[str, Any]) -> None:
    require_exact(
        run,
        {
            "id": SOURCE_RUN_ID,
            "workflow_id": SOURCE_WORKFLOW_ID,
            "run_number": SOURCE_RUN_NUMBER,
            "run_attempt": 1,
            "event": "workflow_dispatch",
            "status": "completed",
            "conclusion": "success",
            "head_branch": "main",
            "head_sha": SOURCE_HEAD_SHA,
            "path": SOURCE_PATH,
            "display_title": SOURCE_DISPLAY_TITLE,
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
        if not isinstance(case_id, str) or not case_id:
            raise GuardRefusal("source manifest case ID missing")
        case_ids.append(case_id)
    if len(set(case_ids)) != CASE_COUNT:
        raise GuardRefusal("source manifest case IDs duplicated")
    return sorted(case_ids)


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
        if not isinstance(name, str) or not name or name in by_name:
            raise GuardRefusal(f"{label} artifact name duplicated or invalid")
        if item.get("expired") is not False:
            raise GuardRefusal(f"{label} artifact expired: {name}")
        require_digest(item.get("digest"), f"{label}.{name}.digest")
        ids.add(artifact_id)
        by_name[name] = item
    return by_name


def validate_source_artifacts(payload: dict[str, Any], case_ids: list[str]) -> dict[str, dict[str, Any]]:
    by_name = artifact_map(payload, "source")
    expected = {
        PREFLIGHT_ARTIFACT_NAME,
        AGGREGATE_ARTIFACT_NAME,
        AUDIT_ARTIFACT_NAME,
        ANALYSIS_ARTIFACT_NAME,
        *(f"{CASE_ARTIFACT_PREFIX}{case_id}" for case_id in case_ids),
    }
    if len(expected) != SOURCE_ARTIFACT_COUNT:
        raise GuardRefusal("internal expected artifact count is not 100")
    if set(by_name) != expected:
        missing = sorted(expected - set(by_name))
        extra = sorted(set(by_name) - expected)
        raise GuardRefusal(f"source artifact universe changed: missing={missing}, extra={extra}")
    return by_name


def validate_reference_artifacts(payload: dict[str, Any]) -> None:
    by_name = artifact_map(payload, "reference")
    if set(by_name) != {REFERENCE_ARTIFACT_NAME}:
        raise GuardRefusal("reference artifact universe changed")
    artifact = by_name[REFERENCE_ARTIFACT_NAME]
    require_exact(
        artifact,
        {
            "id": REFERENCE_ARTIFACT_ID,
            "name": REFERENCE_ARTIFACT_NAME,
            "digest": REFERENCE_ARTIFACT_DIGEST,
            "expired": False,
        },
        "reference artifact",
    )


def validate(
    source_run: dict[str, Any],
    source_artifacts: dict[str, Any],
    manifest: dict[str, Any],
    reference_run: dict[str, Any],
    reference_artifacts: dict[str, Any],
    *,
    handoff_head_sha: str,
) -> dict[str, Any]:
    require_git_sha(handoff_head_sha, "handoff workflow head SHA")
    validate_source_run(source_run)
    validate_reference_run(reference_run)
    case_ids = validate_manifest_case_ids(manifest)
    source_by_name = validate_source_artifacts(source_artifacts, case_ids)
    validate_reference_artifacts(reference_artifacts)
    return {
        "schemaVersion": 1,
        "stageId": "surrogate-training-v2-real-tier1-handoff-guard-v1",
        "status": "REAL_TIER1_HANDOFF_SOURCE_ACCEPTED",
        "sourceRunId": SOURCE_RUN_ID,
        "sourceRunHeadSha": SOURCE_HEAD_SHA,
        "sourceWorkflowId": SOURCE_WORKFLOW_ID,
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-run", type=Path, required=True)
    parser.add_argument("--source-artifacts", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--reference-run", type=Path, required=True)
    parser.add_argument("--reference-artifacts", type=Path, required=True)
    parser.add_argument("--handoff-head-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = validate(
            load(args.source_run),
            load(args.source_artifacts),
            load(args.manifest),
            load(args.reference_run),
            load(args.reference_artifacts),
            handoff_head_sha=args.handoff_head_sha,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump(report))
        print(dump(report), end="")
        return 0
    except Exception as exc:
        refusal = {
            "schemaVersion": 1,
            "stageId": "surrogate-training-v2-real-tier1-handoff-guard-v1",
            "status": "REFUSED",
            "reason": str(exc),
            "surrogateTrainingAuthorized": False,
            "productionPromotionAuthorized": False,
        }
        print(dump(refusal), file=sys.stderr, end="")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
