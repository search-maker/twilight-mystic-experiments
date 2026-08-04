#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

STAGE_ID = "twilight-surrogate-tier-1-ordinal1-failure-audit-v1"
SOURCE_RUN_ID = 30906913329
SOURCE_HEAD_SHA = "9ab74efabfd34799aeeb5c9220a84639861f739d"
SOURCE_EXECUTION_KEY = "twilight-surrogate-tier-1-v1:numerical:1"
SOURCE_AUTHORIZATION_ORDINAL = 1
EXPECTED_CASES = 96
EXPECTED_PHOTONS = 6_960_000_000
EXPECTED_ERROR = (
    "Error, zout needs to be either TOA, SUR, CPT, model_levels, model_layers or a list of "
    "altitudes corresponding to atmospheric levels."
)


class AuditError(RuntimeError):
    pass


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise AuditError(f"expected JSON object: {path}")
    return value


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def valid_sha(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def audit(preflight: Path, cases_root: Path, aggregate: Path, independent_audit: Path) -> dict[str, Any]:
    plan = load(preflight / "plan.json")
    guard = load(preflight / "authorization-guard.json")
    duplicate = load(preflight / "duplicate-run-audit.json")
    summary = load(aggregate)
    prior_audit = load(independent_audit)

    expected_plan = {
        "caseCount": EXPECTED_CASES,
        "configuredMcPhotonsSum": EXPECTED_PHOTONS,
        "authorizationOrdinal": SOURCE_AUTHORIZATION_ORDINAL,
        "executionKey": SOURCE_EXECUTION_KEY,
        "authorizationRef": "81bbdbe17f7dcf024f49378debfd08d1317137a2",
    }
    stale = {key: (plan.get(key), expected) for key, expected in expected_plan.items() if plan.get(key) != expected}
    if stale:
        raise AuditError(f"source plan mismatch: {stale}")
    if guard.get("status") != "AUTHORIZED" or guard.get("authorizationOrdinal") != 1:
        raise AuditError("source authorization guard was not ordinal-1 authorized")
    if duplicate.get("status") != "PASS" or duplicate.get("matchingPriorRunCount") != 0:
        raise AuditError("source duplicate refusal boundary changed")

    case_paths = sorted(cases_root.rglob("case-result.json"))
    if len(case_paths) != EXPECTED_CASES:
        raise AuditError(f"expected {EXPECTED_CASES} case results, found {len(case_paths)}")

    case_ids: set[str] = set()
    seeds: set[int] = set()
    configured_photons = 0
    syntax_checks = 0
    solver_invocations = 0
    completed = 0
    timed_out = 0
    nonempty_solver_stdout = 0
    wrong_failures: list[dict[str, Any]] = []
    case_hashes: dict[str, str] = {}

    for path in case_paths:
        row = load(path)
        case_id = row.get("caseId")
        if not isinstance(case_id, str) or case_id in case_ids:
            raise AuditError(f"duplicate or invalid case ID: {case_id!r}")
        case_ids.add(case_id)
        seed = row.get("seed")
        photons = row.get("photonHistories")
        if not isinstance(seed, int) or not isinstance(photons, int):
            raise AuditError(f"invalid seed or photons: {case_id}")
        seeds.add(seed)
        configured_photons += photons
        syntax_checks += int(row.get("syntaxCheckCount", 0))
        solver_invocations += int(row.get("solverExecutionCount", 0))
        if row.get("status") == "COMPLETED":
            completed += 1
        syntax = row.get("syntax")
        solver = row.get("solver")
        if not isinstance(syntax, dict) or syntax.get("exitCode") != 0 or syntax.get("timedOut") is not False:
            wrong_failures.append({"caseId": case_id, "reason": "syntax-not-successful"})
        if not isinstance(solver, dict) or solver.get("exitCode") != 255 or solver.get("timedOut") is not False:
            wrong_failures.append({"caseId": case_id, "reason": "solver-boundary-changed", "solver": solver})
        if isinstance(solver, dict) and solver.get("timedOut"):
            timed_out += 1
        failure = row.get("failure")
        detail = failure.get("detail") if isinstance(failure, dict) else None
        stderr = detail.get("stderr") if isinstance(detail, dict) else None
        stdout = detail.get("stdout") if isinstance(detail, dict) else None
        if not isinstance(stderr, str) or EXPECTED_ERROR not in stderr:
            wrong_failures.append({"caseId": case_id, "reason": "unexpected-stderr", "stderr": stderr})
        if stdout not in {"", None}:
            nonempty_solver_stdout += 1
        for key in ("radianceOutputSha256", "stdOutputSha256"):
            if row.get(key) is not None:
                wrong_failures.append({"caseId": case_id, "reason": f"unexpected-scientific-output:{key}"})
        if row.get("selectedNodeRadiance") not in ([], None) or row.get("selectedPhotopicContributionCdM2") is not None:
            wrong_failures.append({"caseId": case_id, "reason": "unexpected-derived-science"})
        case_hashes[case_id] = raw_sha256(path)

    if len(seeds) != EXPECTED_CASES:
        raise AuditError("source seeds were not unique")
    if configured_photons != EXPECTED_PHOTONS:
        raise AuditError(f"configured photon sum changed: {configured_photons}")
    if wrong_failures:
        raise AuditError(f"case failure boundary changed: {wrong_failures[:5]}")

    expected_summary = {
        "caseCountExpected": EXPECTED_CASES,
        "caseCountCompleted": 0,
        "caseCountFailed": EXPECTED_CASES,
        "configuredMcPhotonsSum": EXPECTED_PHOTONS,
        "completedConfiguredMcPhotonsSum": 0,
    }
    stale = {key: (summary.get(key), expected) for key, expected in expected_summary.items() if summary.get(key) != expected}
    if stale:
        raise AuditError(f"aggregate mismatch: {stale}")
    if prior_audit.get("status") == "PASSED":
        raise AuditError("failed batch must not have a passing independent audit")

    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "ORDINAL_1_UNIFORMLY_FAILED_BEFORE_SCIENTIFIC_RESULT",
        "sourceRunId": SOURCE_RUN_ID,
        "sourceHeadSha": SOURCE_HEAD_SHA,
        "sourceExecutionKey": SOURCE_EXECUTION_KEY,
        "sourceAuthorizationOrdinal": SOURCE_AUTHORIZATION_ORDINAL,
        "authorizationConsumed": True,
        "githubRerunPermitted": False,
        "caseCountExpected": EXPECTED_CASES,
        "caseCountFailed": EXPECTED_CASES,
        "caseCountCompleted": completed,
        "syntaxCheckCount": syntax_checks,
        "solverInvocationCount": solver_invocations,
        "timedOutCount": timed_out,
        "nonemptySolverStdoutCount": nonempty_solver_stdout,
        "configuredMcPhotonsSum": configured_photons,
        "completedConfiguredMcPhotonsSum": 0,
        "validScientificCaseResultCount": 0,
        "uniformFailureClass": "OBSERVER_ELEVATION_MISRENDERED_AS_ZOUT_ATMOSPHERIC_LEVEL",
        "artifactUseBoundary": {
            "permitted": [
                "failure diagnosis",
                "runtime identity comparison",
                "input and provenance audit",
                "proof that no scientific case completed",
            ],
            "forbidden": [
                "surrogate training",
                "scientific aggregation as data",
                "precision classification",
                "production readiness",
                "reuse as successful continuation blocks",
            ],
        },
        "seedGovernance": {
            "sourceSeedsConsumedByAttempt": True,
            "ordinal2Policy": "FRESH_UNIQUE_SEEDS_FOR_ALL_96_CASES",
        },
        "caseResultRawSha256": case_hashes,
        "preflightPlanRawSha256": raw_sha256(preflight / "plan.json"),
        "aggregateSummaryRawSha256": raw_sha256(aggregate),
        "independentAuditRawSha256": raw_sha256(independent_audit),
        "boundary": "machine-readable audit of a failed first attempt; no syntax check, solver, scientific execution, model fitting, or authorization",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--cases-root", type=Path, required=True)
    parser.add_argument("--aggregate", type=Path, required=True)
    parser.add_argument("--independent-audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = audit(args.preflight, args.cases_root, args.aggregate, args.independent_audit)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump(result))
        print(dump(result), end="")
        return 0
    except Exception as exc:
        print(dump({"schemaVersion": 1, "stageId": STAGE_ID, "status": "REFUSED", "reason": str(exc)}), file=sys.stderr, end="")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
