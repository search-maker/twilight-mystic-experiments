#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

SOURCE_RUN_ID = 31_065_046_524
SOURCE_RUN_ATTEMPT = 1
SOURCE_HEAD_SHA = "18a5746778441d57b722c740a17c94af9b56e9c9"
SOURCE_ARTIFACT_ID = 8_954_776_553
SOURCE_ARTIFACT_NAME = "tier1-wave2-ordinal12-analysis"
SOURCE_ARTIFACT_DIGEST = "sha256:bd60e2ff433aa104ab84a4497310737d0b0d4695c8d454ad125d91f94efabe37"
SOURCE_ANALYSIS_RAW_SHA256 = "c18f9ca23c910924400360ca18c4186d30594bc1aa2d3dd07a43a6031b274237"
SOURCE_ANALYSIS_SHA256 = "8e87fd440d15233dc66543a9ca011535a857b12b5602fd506f6466a900bfafc2"
SOURCE_PREREGISTRATION_SHA256 = "3231c2e5842fb6d4af90ef8329c7f42cf0d9b707493b48de598e35ecf950f050"
SOURCE_WAVE1_AGGREGATE_SHA256 = "59f8469bf43009da141bb4845ffee7a7d2ba1b1ef8fee943629ab8497f3202bb"
SOURCE_WAVE1_AUDIT_SHA256 = "35faf7d6967b9f879f8cb877bfdf4f6b764066f39e411b05fdad380315548d9b"
SOURCE_WAVE2_AGGREGATE_SHA256 = "5f1c343054c77966ab426b5c19628499bff4ee5f983bcf20e3e61eb68897ad69"
SOURCE_WAVE2_AUDIT_SHA256 = "62f312a83e1016ae52d9afe452b884976c43a37bc3c65206c5c5dd7b2202d3f7"
ACTIVE_GEOMETRY_IDS = (
    "train-0003", "train-0007", "train-0011", "train-0013", "train-0015",
    "train-0019", "train-0023", "train-0027", "train-0029", "train-0031",
    "train-0035", "train-0039", "train-0041", "train-0043", "train-0047",
)
RESOLVED_GEOMETRIES = {
    "train-0009": (6, "PRECISION_ACCEPTED"),
    "train-0017": (4, "PRECISION_ACCEPTED"),
    "train-0033": (4, "PRECISION_TARGET_MET"),
    "train-0045": (4, "PRECISION_TARGET_MET"),
    "train-0046": (4, "PRECISION_TARGET_MET"),
}
EXPECTED_ZERO_HIT_COUNTS = {"train-0039": 1, "train-0047": 2}


class Refusal(RuntimeError):
    pass


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise Refusal(f"invalid terminal analysis JSON: {path}") from exc
    if not isinstance(value, dict):
        raise Refusal("terminal analysis must be an object")
    return value


def validate_structure(value: dict[str, Any]) -> dict[str, Any]:
    expected_top = {
        "schemaVersion": 1,
        "stageId": "tier1-precision-continuation-wave2-analysis-v1",
        "analysisSha256": SOURCE_ANALYSIS_SHA256,
        "preregistrationSha256": SOURCE_PREREGISTRATION_SHA256,
        "sourceWave1AggregateSha256": SOURCE_WAVE1_AGGREGATE_SHA256,
        "sourceWave1AuditSha256": SOURCE_WAVE1_AUDIT_SHA256,
        "wave2AggregateSha256": SOURCE_WAVE2_AGGREGATE_SHA256,
        "wave2AuditSha256": SOURCE_WAVE2_AUDIT_SHA256,
        "additionalExecutionAutomaticallyAuthorized": False,
        "surrogateFitAuthorized": False,
        "internalHoldoutOpened": False,
        "tier2Authorized": False,
        "productionPromotionAuthorized": False,
    }
    stale = {
        key: (value.get(key), expected)
        for key, expected in expected_top.items()
        if value.get(key) != expected
    }
    if stale:
        raise Refusal(f"ordinal-12 terminal binding changed: {stale}")

    body = value.get("analysis")
    if not isinstance(body, dict):
        raise Refusal("ordinal-12 terminal analysis body missing")
    expected_body = {
        "schemaVersion": 2,
        "stageId": "tier1-precision-continuation-analysis-v2",
        "status": "CONTINUATION_ANALYZED",
        "nextWaveGeometryIds": list(ACTIVE_GEOMETRY_IDS),
        "exhaustedGeometryIds": [],
        "scientificallyEligible": False,
        "additionalExecutionAutomaticallyAuthorized": False,
        "surrogateFitAuthorized": False,
        "productionPromotionAuthorized": False,
    }
    stale = {
        key: (body.get(key), expected)
        for key, expected in expected_body.items()
        if body.get(key) != expected
    }
    if stale:
        raise Refusal(f"ordinal-12 terminal analysis scope changed: {stale}")

    points = body.get("points")
    if not isinstance(points, list) or len(points) != 20:
        raise Refusal("ordinal-12 continuation point universe changed")
    by_id: dict[str, dict[str, Any]] = {}
    for point in points:
        if not isinstance(point, dict):
            raise Refusal("ordinal-12 point is malformed")
        geometry_id = point.get("geometryId")
        if not isinstance(geometry_id, str) or not geometry_id or geometry_id in by_id:
            raise Refusal("ordinal-12 point identity missing or duplicated")
        by_id[geometry_id] = point

    expected_ids = set(ACTIVE_GEOMETRY_IDS) | set(RESOLVED_GEOMETRIES)
    if set(by_id) != expected_ids:
        raise Refusal("ordinal-12 continuation geometry universe changed")

    for geometry_id in ACTIVE_GEOMETRY_IDS:
        point = by_id[geometry_id]
        expected_zero_hits = EXPECTED_ZERO_HIT_COUNTS.get(geometry_id, 0)
        expected = {
            "blockCount": 6,
            "capReached": False,
            "classification": "ADAPTIVE_CONTINUATION_REQUIRED",
            "scientificallyEligible": False,
            "zeroHitBlockCount": expected_zero_hits,
        }
        stale = {
            key: (point.get(key), expected_value)
            for key, expected_value in expected.items()
            if point.get(key) != expected_value
        }
        if stale:
            raise Refusal(f"active terminal point changed for {geometry_id}: {stale}")

    for geometry_id, (block_count, classification) in RESOLVED_GEOMETRIES.items():
        point = by_id[geometry_id]
        expected = {
            "blockCount": block_count,
            "capReached": False,
            "classification": classification,
            "scientificallyEligible": True,
            "zeroHitBlockCount": 0,
        }
        stale = {
            key: (point.get(key), expected_value)
            for key, expected_value in expected.items()
            if point.get(key) != expected_value
        }
        if stale:
            raise Refusal(f"resolved terminal point changed for {geometry_id}: {stale}")

    return {
        "schemaVersion": 1,
        "stageId": "tier1-precision-continuation-wave3-terminal-binding-v1",
        "status": "ORDINAL12_TERMINAL_SOURCE_EXACTLY_BOUND",
        "sourceRunId": SOURCE_RUN_ID,
        "sourceRunAttempt": SOURCE_RUN_ATTEMPT,
        "sourceHeadSha": SOURCE_HEAD_SHA,
        "sourceArtifactId": SOURCE_ARTIFACT_ID,
        "sourceArtifactName": SOURCE_ARTIFACT_NAME,
        "sourceArtifactDigest": SOURCE_ARTIFACT_DIGEST,
        "sourceAnalysisSha256": SOURCE_ANALYSIS_SHA256,
        "geometryIds": list(ACTIVE_GEOMETRY_IDS),
        "geometryCount": len(ACTIVE_GEOMETRY_IDS),
        "caseCount": 2 * len(ACTIVE_GEOMETRY_IDS),
        "blocks": [7, 8],
        "zeroHitGeometryIds": sorted(EXPECTED_ZERO_HIT_COUNTS),
        "exhaustedGeometryIds": [],
        "scientificExecution": False,
        "authorizationAllocated": False,
        "dispatchEnabled": False,
    }


def validate_path(path: Path) -> dict[str, Any]:
    observed_raw = raw_sha256(path)
    if observed_raw != SOURCE_ANALYSIS_RAW_SHA256:
        raise Refusal(
            f"ordinal-12 analysis raw hash changed: {(observed_raw, SOURCE_ANALYSIS_RAW_SHA256)}"
        )
    value = load_json(path)
    payload = {key: item for key, item in value.items() if key != "analysisSha256"}
    if canonical_sha256(payload) != SOURCE_ANALYSIS_SHA256:
        raise Refusal("ordinal-12 analysis canonical self-hash changed")
    report = validate_structure(value)
    report["sourceAnalysisRawSha256"] = observed_raw
    report["reportSha256"] = canonical_sha256(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-analysis", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        report = validate_path(args.source_analysis)
    except Exception as exc:
        print(json.dumps({"status": "REFUSED", "reason": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8", newline="\n")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
