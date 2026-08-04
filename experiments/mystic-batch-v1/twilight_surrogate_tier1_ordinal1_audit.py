#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

STAGE_ID = "twilight-surrogate-tier-1-ordinal1-failure-audit-v1"
EXPECTED_CASES = 96
EXPECTED_PHOTONS = 6_960_000_000
FAILURE_RE = re.compile(
    r"^FATAL error: altitude grid does not contain level [0-9]+(?:\.[0-9]+)?\n"
    r"which has been specified as output altitude\n"
)


class AuditError(RuntimeError):
    pass


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise AuditError(f"expected JSON object: {path}")
    return value


def raw(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def audit(preflight: Path, cases_root: Path, aggregate_path: Path, audit_path: Path) -> dict[str, Any]:
    plan = load(preflight / "plan.json")
    guard = load(preflight / "authorization-guard.json")
    duplicate = load(preflight / "duplicate-run-audit.json")
    aggregate = load(aggregate_path)
    prior_audit = load(audit_path)

    if plan.get("caseCount") != EXPECTED_CASES or plan.get("configuredMcPhotonsSum") != EXPECTED_PHOTONS:
        raise AuditError("source plan counts changed")
    if plan.get("authorizationOrdinal") != 1 or plan.get("executionKey") != "twilight-surrogate-tier-1-v1:numerical:1":
        raise AuditError("ordinal-1 one-shot marker changed")
    if guard.get("status") != "AUTHORIZED" or duplicate.get("status") != "PASS":
        raise AuditError("source preflight gates changed")

    paths = sorted(cases_root.rglob("case-result.json"))
    if len(paths) != EXPECTED_CASES:
        raise AuditError(f"expected 96 case results, found {len(paths)}")

    seeds: set[int] = set()
    photons = 0
    hashes: dict[str, str] = {}
    for path in paths:
        row = load(path)
        case_id = row.get("caseId")
        if not isinstance(case_id, str) or case_id in hashes:
            raise AuditError("duplicate or invalid case ID")
        seed = row.get("seed")
        count = row.get("photonHistories")
        if not isinstance(seed, int) or not isinstance(count, int):
            raise AuditError(f"invalid seed or photons: {case_id}")
        seeds.add(seed)
        photons += count
        if row.get("status") != "FAILED" or row.get("syntaxCheckCount") != 1 or row.get("solverExecutionCount") != 1:
            raise AuditError(f"case execution boundary changed: {case_id}")
        syntax = row.get("syntax")
        solver = row.get("solver")
        if not isinstance(syntax, dict) or syntax.get("exitCode") != 0 or syntax.get("timedOut") is not False:
            raise AuditError(f"syntax did not pass: {case_id}")
        if not isinstance(solver, dict) or solver.get("exitCode") != 255 or solver.get("timedOut") is not False:
            raise AuditError(f"solver failure boundary changed: {case_id}")
        failure = row.get("failure")
        detail = failure.get("detail") if isinstance(failure, dict) else None
        stderr = detail.get("stderr") if isinstance(detail, dict) else None
        stdout = detail.get("stdout") if isinstance(detail, dict) else None
        if not isinstance(stderr, str) or FAILURE_RE.match(stderr) is None or stdout != "":
            raise AuditError(f"uniform altitude-grid failure changed: {case_id}")
        if row.get("radianceOutputSha256") is not None or row.get("stdOutputSha256") is not None:
            raise AuditError(f"unexpected scientific output hash: {case_id}")
        if row.get("selectedNodeRadiance") != [] or row.get("selectedPhotopicContributionCdM2") is not None:
            raise AuditError(f"unexpected derived scientific value: {case_id}")
        hashes[case_id] = raw(path)

    if len(seeds) != EXPECTED_CASES or photons != EXPECTED_PHOTONS:
        raise AuditError("seed uniqueness or photon accounting changed")
    expected_aggregate = {
        "caseCountPlanned": EXPECTED_CASES,
        "caseCountCompleted": 0,
        "caseCountFailed": EXPECTED_CASES,
        "configuredMcPhotonsSum": EXPECTED_PHOTONS,
        "completedConfiguredMcPhotonsSum": 0,
        "syntaxCheckCount": EXPECTED_CASES,
        "solverExecutionCount": EXPECTED_CASES,
        "classification": "STRUCTURAL_OR_EXECUTION_FAILURE",
        "status": "FAILED",
    }
    if any(aggregate.get(key) != value for key, value in expected_aggregate.items()):
        raise AuditError("aggregate failure boundary changed")
    if prior_audit.get("status") != "FAILED" or prior_audit.get("batchClassification") != "STRUCTURAL_OR_EXECUTION_FAILURE":
        raise AuditError("independent audit failure boundary changed")

    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "ORDINAL_1_UNIFORMLY_FAILED_BEFORE_SCIENTIFIC_RESULT",
        "sourceRunId": 30906913329,
        "sourceHeadSha": "9ab74efabfd34799aeeb5c9220a84639861f739d",
        "sourceExecutionKey": "twilight-surrogate-tier-1-v1:numerical:1",
        "sourceAuthorizationOrdinal": 1,
        "authorizationConsumed": True,
        "githubRerunPermitted": False,
        "caseCountFailed": EXPECTED_CASES,
        "caseCountCompleted": 0,
        "syntaxCheckCount": EXPECTED_CASES,
        "solverInvocationCount": EXPECTED_CASES,
        "timedOutCount": 0,
        "configuredMcPhotonsSum": EXPECTED_PHOTONS,
        "completedConfiguredMcPhotonsSum": 0,
        "validScientificCaseResultCount": 0,
        "uniformFailureClass": "OBSERVER_ELEVATION_MISRENDERED_AS_ZOUT_ATMOSPHERIC_LEVEL",
        "seedGovernance": {"sourceSeedsConsumedByAttempt": True, "ordinal2Policy": "FRESH_UNIQUE_SEEDS_FOR_ALL_96_CASES"},
        "artifactUseBoundary": {
            "permitted": ["failure diagnosis", "runtime identity comparison", "input and provenance audit"],
            "forbidden": ["training", "scientific dataset use", "precision classification", "production readiness"],
        },
        "caseResultRawSha256": hashes,
        "preflightPlanRawSha256": raw(preflight / "plan.json"),
        "aggregateSummaryRawSha256": raw(aggregate_path),
        "independentAuditRawSha256": raw(audit_path),
        "boundary": "failure audit only; no syntax check, solver, scientific execution, model fitting, authorization, or production use",
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
