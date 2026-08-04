#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

STAGE_ID = "cross-geometry-selected-reference-confirmation-v1"
GENERIC_STAGE_ID = "mystic-batch-v1"


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def compact(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def build_plan(manifest_path: Path, guard_path: Path) -> dict[str, Any]:
    manifest = load(manifest_path)
    guard = load(guard_path)
    if guard.get("status") != "AUTHORIZED" or guard.get("stageId") != STAGE_ID:
        raise ValueError("confirmation guard did not pass")
    if manifest.get("stageId") != STAGE_ID or manifest.get("batchId") != guard.get("batchId"):
        raise ValueError("confirmation manifest and guard do not match")
    cases = manifest.get("cases")
    limits = manifest.get("limits")
    if not isinstance(cases, list) or not isinstance(limits, dict):
        raise ValueError("confirmation cases or limits malformed")
    ordered = sorted(cases, key=lambda case: case["ordinal"])
    matrix = {
        "include": [
            {
                "case_id": case["caseId"],
                "ordinal": case["ordinal"],
                "seed": case["seed"],
                "photon_histories": case["photonHistories"],
                "group_id": case["groupId"],
                "method": case["method"],
                "block": case["block"],
                "purpose": case["purpose"],
                "alis_reference_nm": case.get("alisSpectralImportanceSamplingNm", 0),
            }
            for case in ordered
        ]
    }
    return {
        "schemaVersion": 1,
        "stageId": GENERIC_STAGE_ID,
        "scientificPurpose": STAGE_ID,
        "batchId": manifest["batchId"],
        "mode": "scientific",
        "scientificExecution": True,
        "scientificDiagnostic": True,
        "successDoesNotAuthorizeProduction": True,
        "manifestPath": str(manifest_path),
        "manifestRawSha256": guard["promotedManifestRawSha256"],
        "scientificAdapterRawSha256": guard["executionAdapterRawSha256"],
        "runtimeLockRawSha256": guard["runtimeLockRawSha256"],
        "executionWorkflowRawSha256": guard["executionWorkflowRawSha256"],
        "authorizationRef": guard["authorizationRef"],
        "authorizationOrdinal": guard["authorizationOrdinal"],
        "executionKey": guard["executionKey"],
        "sourceRunId": guard["sourceRunId"],
        "sourceFinalAnalysisRawSha256": guard["sourceFinalAnalysisRawSha256"],
        "sourceProposalRawSha256": guard["sourceProposalRawSha256"],
        "sourceReadinessRawSha256": guard["sourceReadinessRawSha256"],
        "caseCount": len(ordered),
        "maximumParallel": limits["maximumParallel"],
        "perCaseTimeoutSeconds": limits["perCaseTimeoutSeconds"],
        "configuredMcPhotonsSum": sum(case["photonHistories"] for case in ordered),
        "cases": ordered,
        "matrix": matrix,
        "boundary": "exact held-out confirmation matrix; no syntax or solver execution occurs during planning",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--guard-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()
    try:
        plan = build_plan(args.manifest, args.guard_report)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump(plan))
        if args.github_output:
            with args.github_output.open("a", encoding="utf-8") as handle:
                handle.write(f"matrix={compact(plan['matrix'])}\n")
                handle.write(f"max_parallel={plan['maximumParallel']}\n")
                handle.write(f"case_count={plan['caseCount']}\n")
                handle.write(f"timeout_seconds={plan['perCaseTimeoutSeconds']}\n")
        print(dump({"status": "PLANNED", "stageId": STAGE_ID, "caseCount": plan["caseCount"]}), end="")
        return 0
    except Exception as exc:
        print(dump({"status": "REFUSED", "stageId": STAGE_ID, "reason": str(exc)}), end="", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
