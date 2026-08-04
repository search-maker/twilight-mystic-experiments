#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

STAGE_ID = "twilight-surrogate-tier-1-ordinal1-failure-audit-v2"
EXPECTED_CASES = 96
EXPECTED_PHOTONS = 6_960_000_000
FAILURE_RE = re.compile(
    r"\A\nFATAL error: altitude grid does not contain level "
    r"(?P<level>[0-9]+(?:\.[0-9]+)?)\n"
    r"which has been specified as output altitude\n"
    r"Error -1 in \(function 'setup_sample_grid', file 'cloud3d\.c', line 511\)\n"
    r"Error -1 in \(function 'setup_atmosphere3D', file 'cloud3d\.c', line 1896\)\n"
    r"Error -1 in \(function 'uvspec', file 'uvspec\.c', line 129\)\n"
    r"Error -1 during execution of uvspec\n\Z"
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


def audit(
    preflight: Path,
    cases_root: Path,
    aggregate_path: Path,
    audit_path: Path,
) -> dict[str, Any]:
    plan = load(preflight / "plan.json")
    guard = load(preflight / "authorization-guard.json")
    duplicate = load(preflight / "duplicate-run-audit.json")
    aggregate = load(aggregate_path)
    prior_audit = load(audit_path)

    if (
        plan.get("caseCount") != EXPECTED_CASES
        or plan.get("configuredMcPhotonsSum") != EXPECTED_PHOTONS
    ):
        raise AuditError("source plan counts changed")
    if (
        plan.get("authorizationOrdinal") != 1
        or plan.get("executionKey")
        != "twilight-surrogate-tier-1-v1:numerical:1"
    ):
        raise AuditError("ordinal-1 one-shot marker changed")
    if guard.get("status") != "AUTHORIZED" or duplicate.get("status") != "PASS":
        raise AuditError("source preflight gates changed")

    paths = sorted(cases_root.rglob("case-result.json"))
    if len(paths) != EXPECTED_CASES:
        raise AuditError(f"expected 96 case results, found {len(paths)}")

    seeds: set[int] = set()
    photons = 0
    hashes: dict[str, str] = {}
    prepared_hashes: dict[str, str] = {}
    input_hashes: dict[str, str] = {}
    rejected_levels_km: dict[str, float] = {}
    rendered_zout_levels_km: dict[str, float] = {}
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
        if (
            row.get("status") != "FAILED"
            or row.get("syntaxCheckCount") != 1
            or row.get("solverExecutionCount") != 1
        ):
            raise AuditError(f"case execution boundary changed: {case_id}")
        syntax = row.get("syntax")
        solver = row.get("solver")
        if (
            not isinstance(syntax, dict)
            or syntax.get("exitCode") != 0
            or syntax.get("timedOut") is not False
        ):
            raise AuditError(f"syntax did not pass: {case_id}")
        if (
            not isinstance(solver, dict)
            or solver.get("exitCode") != 255
            or solver.get("timedOut") is not False
        ):
            raise AuditError(f"solver failure boundary changed: {case_id}")
        failure = row.get("failure")
        if not isinstance(failure, dict) or failure.get("code") != "solver-failure":
            raise AuditError(f"solver failure code changed: {case_id}")
        detail = failure.get("detail")
        stderr = detail.get("stderr") if isinstance(detail, dict) else None
        stdout = detail.get("stdout") if isinstance(detail, dict) else None
        match = FAILURE_RE.fullmatch(stderr) if isinstance(stderr, str) else None
        if match is None or stdout != "":
            raise AuditError(f"uniform altitude-grid failure changed: {case_id}")

        prepared_path = path.parent / "tier1-prepared.json"
        input_path = path.parent / "input-resolved.txt"
        if not prepared_path.is_file() or not input_path.is_file():
            raise AuditError(f"ordinal-1 prepared evidence missing: {case_id}")
        prepared = load(prepared_path)
        if prepared.get("caseId") != case_id:
            raise AuditError(f"prepared case identity changed: {case_id}")
        inputs = prepared.get("inputs")
        observer_m = inputs.get("observerElevationM") if isinstance(inputs, dict) else None
        if (
            not isinstance(observer_m, (int, float))
            or isinstance(observer_m, bool)
            or not math.isfinite(float(observer_m))
        ):
            raise AuditError(f"prepared observer elevation invalid: {case_id}")

        input_text = input_path.read_text()
        input_lines = input_text.splitlines()
        zout_lines = [line for line in input_lines if line.startswith("zout ")]
        if len(zout_lines) != 1 or len(zout_lines[0].split()) != 2:
            raise AuditError(f"ordinal-1 zout evidence changed: {case_id}")
        rendered_zout_text = zout_lines[0].split()[1]
        try:
            rendered_zout = float(rendered_zout_text)
        except ValueError as exc:
            raise AuditError(f"ordinal-1 zout is not numeric: {case_id}") from exc
        expected_site_km = float(observer_m) / 1000.0
        if not math.isclose(
            rendered_zout, expected_site_km, rel_tol=0.0, abs_tol=5.1e-7
        ):
            raise AuditError(
                f"rendered ordinal-1 zout differs from observer elevation: {case_id}"
            )
        canonical_reported_levels = {
            rendered_zout_text,
            f"{rendered_zout:.6g}",
        }
        if match.group("level") not in canonical_reported_levels:
            raise AuditError(
                f"MYSTIC rejected level differs from exact rendered zout: {case_id}"
            )
        if any(
            line.startswith("altitude ")
            or line.startswith("mc_elevation_file ")
            or line.startswith("atm_z_grid ")
            for line in input_lines
        ):
            raise AuditError(f"ordinal-1 elevation mechanism changed: {case_id}")
        input_sha = raw(input_path)
        if prepared.get("inputResolvedSha256") != input_sha:
            raise AuditError(f"prepared input hash mismatch: {case_id}")
        if row.get("inputResolvedSha256") != input_sha:
            raise AuditError(f"case-result input hash mismatch: {case_id}")

        if (
            row.get("radianceOutputSha256") is not None
            or row.get("stdOutputSha256") is not None
        ):
            raise AuditError(f"unexpected scientific output hash: {case_id}")
        if (
            row.get("selectedNodeRadiance") != []
            or row.get("selectedNodeStdRadiance") != []
            or row.get("selectedPhotopicContributionCdM2") is not None
        ):
            raise AuditError(f"unexpected derived scientific value: {case_id}")
        hashes[case_id] = raw(path)
        prepared_hashes[case_id] = raw(prepared_path)
        input_hashes[case_id] = input_sha
        rejected_levels_km[case_id] = float(match.group("level"))
        rendered_zout_levels_km[case_id] = rendered_zout

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
    if any(
        aggregate.get(key) != value for key, value in expected_aggregate.items()
    ):
        raise AuditError("aggregate failure boundary changed")
    if (
        prior_audit.get("status") != "FAILED"
        or prior_audit.get("batchClassification")
        != "STRUCTURAL_OR_EXECUTION_FAILURE"
    ):
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
        "uniformFailureClass": (
            "OBSERVER_ELEVATION_MISRENDERED_AS_ZOUT_ATMOSPHERIC_LEVEL"
        ),
        "uniformFailureEvidence": {
            "fatalPrefix": "FATAL error: altitude grid does not contain level",
            "outputAltitudeMarker": "which has been specified as output altitude",
            "setupSampleGridFrame": (
                "Error -1 in (function 'setup_sample_grid', file 'cloud3d.c', line 511)"
            ),
            "rejectedLevelMatchesSixDecimalRenderedObserverElevationForAllCases": True,
            "renderedZoutMatchesObserverElevationWithinSixDecimalRendererForAllCases": True,
            "rejectedLevelMatchesCanonicalRenderedZoutForAllCases": True,
            "ordinal1InputContainsNoAltitudeOrMcElevationOrAtmZGridForAllCases": True,
        },
        "seedGovernance": {
            "sourceSeedsConsumedByAttempt": True,
            "ordinal2Policy": "FRESH_UNIQUE_SEEDS_FOR_ALL_96_CASES",
        },
        "artifactUseBoundary": {
            "permitted": [
                "failure diagnosis",
                "runtime identity comparison",
                "input and provenance audit",
            ],
            "forbidden": [
                "training",
                "scientific dataset use",
                "precision classification",
                "production readiness",
            ],
        },
        "caseResultRawSha256": hashes,
        "preparedCaseRawSha256": prepared_hashes,
        "inputResolvedRawSha256": input_hashes,
        "renderedZoutKm": rendered_zout_levels_km,
        "rejectedOutputLevelKm": rejected_levels_km,
        "preflightPlanRawSha256": raw(preflight / "plan.json"),
        "aggregateSummaryRawSha256": raw(aggregate_path),
        "independentAuditRawSha256": raw(audit_path),
        "boundary": (
            "failure audit only; no syntax check, solver, scientific execution, "
            "model fitting, authorization, or production use"
        ),
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
        result = audit(
            args.preflight,
            args.cases_root,
            args.aggregate,
            args.independent_audit,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump(result))
        print(dump(result), end="")
        return 0
    except Exception as exc:
        print(
            dump(
                {
                    "schemaVersion": 1,
                    "stageId": STAGE_ID,
                    "status": "REFUSED",
                    "reason": str(exc),
                }
            ),
            file=sys.stderr,
            end="",
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
