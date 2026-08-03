#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

STAGE_ID = "mystic-batch-v1"


class PlanRefusal(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise PlanRefusal(f"expected JSON object: {path}")
    return value


def compact(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def build_plan(manifest_path: Path, guard_report_path: Path) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    guard = load_json(guard_report_path)
    if guard.get("status") != "AUTHORIZED" or guard.get("stageId") != STAGE_ID:
        raise PlanRefusal("authorization guard did not pass")
    if manifest.get("batchId") != guard.get("batchId"):
        raise PlanRefusal("guard batch does not match manifest")
    cases = manifest.get("cases")
    limits = manifest.get("limits")
    if not isinstance(cases, list) or not isinstance(limits, dict):
        raise PlanRefusal("manifest cases or limits malformed")
    ordered = sorted(cases, key=lambda case: case["ordinal"])
    matrix = {
        "include": [
            {
                "case_id": case["caseId"],
                "ordinal": case["ordinal"],
                "seed": case["seed"],
                "photon_histories": case["photonHistories"],
            }
            for case in ordered
        ]
    }
    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "batchId": manifest["batchId"],
        "mode": "scientific",
        "scientificExecution": True,
        "successDoesNotAuthorizeProduction": True,
        "manifestPath": str(manifest_path),
        "manifestRawSha256": guard["manifestRawSha256"],
        "authorizationRef": guard["authorizationRef"],
        "authorizationOrdinal": guard["authorizationOrdinal"],
        "executionKey": guard["executionKey"],
        "caseCount": len(ordered),
        "maximumParallel": limits["maximumParallel"],
        "perCaseTimeoutSeconds": limits["perCaseTimeoutSeconds"],
        "configuredMcPhotonsSum": sum(case["photonHistories"] for case in ordered),
        "runtimeLockRawSha256": guard["runtimeLockRawSha256"],
        "scientificAdapterRawSha256": guard["scientificAdapterRawSha256"],
        "executionWorkflowRawSha256": guard["executionWorkflowRawSha256"],
        "cases": ordered,
        "matrix": matrix,
        "boundary": "plan creation performs no syntax check and no solver execution",
    }


def write_outputs(path: Path, plan: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"matrix={compact(plan['matrix'])}\n")
        handle.write(f"max_parallel={plan['maximumParallel']}\n")
        handle.write(f"case_count={plan['caseCount']}\n")
        handle.write(f"timeout_seconds={plan['perCaseTimeoutSeconds']}\n")


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
            write_outputs(args.github_output, plan)
        print(dump({"status": "PLANNED", "batchId": plan["batchId"], "caseCount": plan["caseCount"]}), end="")
        return 0
    except Exception as exc:
        print(dump({"status": "REFUSED", "stageId": STAGE_ID, "reason": str(exc)}), end="", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
