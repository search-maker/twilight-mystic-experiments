#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SOURCE_STAGE_ID = "cross-geometry-pilot-v1"
GENERIC_STAGE_ID = "mystic-batch-v1"
LANE_ID = "jerusalem-tammuz-direct-mystic-v2"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

class PlanError(RuntimeError):
    pass

def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise PlanError(f"expected JSON object: {path}")
    return value

def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"

def compact(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)

def require_hash(source: dict[str, Any], field: str) -> str:
    value = source.get(field)
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise PlanError(f"missing or invalid hash binding: {field}")
    return value

def build_plan(proposal_path: Path, guard_report_path: Path) -> dict[str, Any]:
    proposal = load(proposal_path)
    guard = load(guard_report_path)
    if guard.get("status") != "AUTHORIZED_TAMMUZ_V2_AFTER_FORMAL_SMOKE_PASS" or guard.get("laneId") != LANE_ID or guard.get("stageId") != SOURCE_STAGE_ID:
        raise PlanError("Tammuz v2 authorization guard did not pass")
    if proposal.get("stageId") != SOURCE_STAGE_ID or proposal.get("batchId") != guard.get("batchId"):
        raise PlanError("source proposal and Tammuz v2 guard do not match")
    cases = proposal.get("cases")
    limits = proposal.get("limits")
    if not isinstance(cases, list) or len(cases) != 12 or not isinstance(limits, dict):
        raise PlanError("expected exact 12-case source proposal")
    ordered = sorted(cases, key=lambda case: case["ordinal"])
    if [case.get("ordinal") for case in ordered] != list(range(1, 13)):
        raise PlanError("source case ordinals changed")
    if sum(int(case.get("photonHistories", 0)) for case in ordered) != 240_000_000:
        raise PlanError("source photon accounting changed")
    matrix = {"include": [{
        "case_id": case["caseId"],
        "ordinal": case["ordinal"],
        "seed": case["seed"],
        "photon_histories": case["photonHistories"],
        "group_id": case["groupId"],
        "method": case["method"],
        "block": case["block"],
    } for case in ordered]}
    return {
        "schemaVersion": 1,
        "stageId": GENERIC_STAGE_ID,
        "scientificPurpose": LANE_ID,
        "sourceScientificStageId": SOURCE_STAGE_ID,
        "batchId": proposal["batchId"],
        "mode": "scientific",
        "scientificExecution": True,
        "successDoesNotAuthorizeProduction": True,
        "manifestPath": str(proposal_path),
        "manifestRawSha256": require_hash(guard, "proposalRawSha256"),
        "authorizationRef": guard["authorizationRef"],
        "authorizationOrdinal": guard["authorizationOrdinal"],
        "executionKey": guard["executionKey"],
        "scientificAdapterRawSha256": require_hash(guard, "executionAdapterRawSha256"),
        "runtimeLockRawSha256": require_hash(guard, "runtimeLockRawSha256"),
        "executionWorkflowRawSha256": require_hash(guard, "executionWorkflowRawSha256"),
        "requiredSmokeRunId": guard["requiredSmokeRunId"],
        "requiredSmokeAuditArtifactId": guard["requiredSmokeAuditArtifactId"],
        "caseCount": len(ordered),
        "maximumParallel": limits["maximumParallel"],
        "perCaseTimeoutSeconds": limits["perCaseTimeoutSeconds"],
        "configuredMcPhotonsSum": sum(case["photonHistories"] for case in ordered),
        "cases": ordered,
        "matrix": matrix,
        "boundary": "Tammuz v2 plan promotes only the exact transformed-row 12-case/240M proposal after one-purpose authorization and consumed formal 800m infrastructure smoke; no syntax or solver is executed by planning",
    }

def write_outputs(path: Path, plan: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"matrix={compact(plan['matrix'])}\n")
        handle.write(f"max_parallel={plan['maximumParallel']}\n")
        handle.write(f"case_count={plan['caseCount']}\n")
        handle.write(f"timeout_seconds={plan['perCaseTimeoutSeconds']}\n")

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--proposal", type=Path, required=True)
    parser.add_argument("--guard-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()
    try:
        plan = build_plan(args.proposal, args.guard_report)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump(plan), encoding="utf-8")
        if args.github_output:
            write_outputs(args.github_output, plan)
        print(dump({"status":"PLANNED","laneId":LANE_ID,"caseCount":plan["caseCount"],"configuredMcPhotonsSum":plan["configuredMcPhotonsSum"]}), end="")
        return 0
    except Exception as exc:
        print(dump({"status":"REFUSED","laneId":LANE_ID,"reason":str(exc)}), end="", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
