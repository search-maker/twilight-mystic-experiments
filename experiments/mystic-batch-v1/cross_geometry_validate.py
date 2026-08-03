#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

STAGE_ID = "cross-geometry-pilot-v1"
METHODS = {"reference-vroom", "alis"}
EXPECTED_RUNTIME = {
    "uvspecSha256": "2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3",
    "uvspecHelpSha256": "868aea5af762d968f6f62c4e1472916d25232ed9cab5be112d753b0823d20548",
    "libRadtranDataTreeSha256": "ad30b49177e9c84e46497d69faf0c75e466996b0d0003f1de210289ae9f847d7",
    "atmosphereSha256": "dab26290ed81c762ed0c607e5dc2d53393c1462a0c3a528bc5e3f5935191cfb5",
    "runtimeLockRawSha256": "3b5fbec964642b04c73a6423b3355dbcc4ba5e84f9614f6d74420491bacc20c5"
}


class ValidationFailure(RuntimeError):
    pass


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValidationFailure(f"expected object: {path}")
    return value


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def validate(manifest_path: Path, contract_path: Path, authorization_path: Path, adapter_path: Path) -> dict[str, Any]:
    manifest = load(manifest_path)
    contract = load(contract_path)
    authorization = load(authorization_path)
    header = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "mode": "scientific-proposal",
        "proposalOnly": True,
        "scientificExecution": False,
        "successDoesNotAuthorizeProduction": True,
        "adapterId": "mystic-cross-geometry-v1"
    }
    stale = {key: (manifest.get(key), expected) for key, expected in header.items() if manifest.get(key) != expected}
    if stale:
        raise ValidationFailure(f"manifest header mismatch: {stale}")
    if contract.get("stageId") != STAGE_ID or contract.get("status") != "PROPOSAL_ONLY_NOT_AUTHORIZATION" or contract.get("screeningOnly") is not True:
        raise ValidationFailure("contract is not frozen screening-only proposal")
    expected_authorization = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "authorized": False,
        "scientificExecution": False,
        "executionKey": None,
        "manifestRawSha256": None,
        "contractRawSha256": None,
        "adapterRawSha256": None,
        "executionWorkflowRawSha256": None,
        "exactAuthorizationParentCommit": None,
        "exactAuthorizationCommit": None,
        "authorizationOrdinal": 0,
        "consumed": False,
        "note": "Proposal-only template. It does not authorize syntax checks, uvspec, MYSTIC, or workflow dispatch."
    }
    if authorization != expected_authorization:
        raise ValidationFailure("authorization template is not exactly disabled")
    runtime = manifest.get("runtime")
    if not isinstance(runtime, dict):
        raise ValidationFailure("runtime missing")
    runtime_mismatch = {key: (runtime.get(key), expected) for key, expected in EXPECTED_RUNTIME.items() if runtime.get(key) != expected}
    if runtime_mismatch:
        raise ValidationFailure(f"runtime identity mismatch: {runtime_mismatch}")

    geometries = manifest.get("geometries")
    cases = manifest.get("cases")
    limits = manifest.get("limits")
    if not isinstance(geometries, list) or len(geometries) != 6 or not isinstance(cases, list) or len(cases) != 24 or not isinstance(limits, dict):
        raise ValidationFailure("expected exactly 6 geometries and 24 cases")
    geometry_ids = [geometry.get("geometryId") for geometry in geometries]
    if len(set(geometry_ids)) != 6:
        raise ValidationFailure("geometry IDs must be unique")
    if [case.get("ordinal") for case in cases] != list(range(1, 25)):
        raise ValidationFailure("case ordinals must be contiguous")
    case_ids = [case.get("caseId") for case in cases]
    seeds = [case.get("seed") for case in cases]
    if len(set(case_ids)) != 24 or len(set(seeds)) != 24:
        raise ValidationFailure("case IDs and seeds must be globally unique")
    if any(case.get("photonHistories") != 20_000_000 for case in cases):
        raise ValidationFailure("pilot photons per block changed")
    if sum(case["photonHistories"] for case in cases) != 480_000_000:
        raise ValidationFailure("photon total changed")
    if limits != {"maximumCases": 24, "maximumParallel": 6, "maximumConfiguredMcPhotonsSum": 480000000, "perCaseTimeoutSeconds": 900}:
        raise ValidationFailure("limits changed")

    counts = Counter((case.get("groupId"), case.get("method")) for case in cases)
    expected_pairs = {(geometry_id, method) for geometry_id in geometry_ids for method in METHODS}
    if set(counts) != expected_pairs or any(counts[pair] != 2 for pair in expected_pairs):
        raise ValidationFailure("each geometry must have two blocks per method")
    for geometry_id in geometry_ids:
        for method in METHODS:
            blocks = sorted(case.get("block") for case in cases if case.get("groupId") == geometry_id and case.get("method") == method)
            if blocks != [1, 2]:
                raise ValidationFailure(f"wrong blocks for {geometry_id}/{method}: {blocks}")

    depths = {float(geometry["sunDepressionDeg"]) for geometry in geometries}
    altitudes = [float(geometry["targetAltitudeDeg"]) for geometry in geometries]
    azimuths = {float(geometry["relativeAzimuthDeg"]) for geometry in geometries}
    aods = {float(geometry["aod550"]) for geometry in geometries}
    if depths != {4.0, 8.0, 12.0} or min(altitudes) > 10.0 or max(altitudes) < 45.0:
        raise ValidationFailure("early/mid/late or low/high coverage changed")
    if not ({30.0, 90.0, 180.0} <= azimuths) or aods != {0.15, 0.30}:
        raise ValidationFailure("azimuth or aerosol coverage changed")
    bridge = next((geometry for geometry in geometries if geometry.get("geometryId") == "g01-reference-bridge"), None)
    if bridge != {"geometryId": "g01-reference-bridge", "sunDepressionDeg": 12.0, "targetAltitudeDeg": 10.0, "relativeAzimuthDeg": 120.0, "observerElevationM": 0.0, "aod550": 0.15}:
        raise ValidationFailure("reference bridge changed")

    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "PROPOSAL_VALIDATED_NO_EXECUTION",
        "manifestRawSha256": raw_sha256(manifest_path),
        "contractRawSha256": raw_sha256(contract_path),
        "adapterRawSha256": raw_sha256(adapter_path),
        "geometryCount": 6,
        "caseCount": 24,
        "configuredMcPhotonsSum": 480_000_000,
        "boundary": contract["boundary"]
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--adapter", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = validate(args.manifest, args.contract, args.authorization, args.adapter)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(dump(result))
        print(dump(result), end="")
        return 0
    except Exception as exc:
        print(dump({"status": "REFUSED", "stageId": STAGE_ID, "reason": str(exc)}), end="", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
