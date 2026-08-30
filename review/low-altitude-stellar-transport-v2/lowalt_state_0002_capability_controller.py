#!/usr/bin/env python3
"""Solver-free capability/runtime contract for LOWALT-STELLAR-STATE-0002.

This module materializes the frozen fresh 20-case / 60-invocation low-altitude
capability and timing plan. It deliberately contains no process-spawning,
uvspec, or libRadtran execution path and cannot open protected results or lower
support.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from decimal import Decimal
from typing import Any

SCIENTIFIC_STATE = "LOWALT-STELLAR-STATE-0002"
PROTOCOL_ID = "lowalt-state-0002-capability-runtime-v1"
ISSUE60_THEORY_FREEZE_COMMENT = 5470357109
ISSUE60_BUDGET_FREEZE_COMMENT = 5470368706

ALTITUDE_DEG = tuple(Decimal(x) for x in ("0.30", "0.70", "1.40", "2.90", "4.60"))
OBSERVER_ELEVATION_M = tuple(Decimal(x) for x in ("0", "2500"))
AOD550 = tuple(Decimal(x) for x in ("0.05", "0.40"))
TIMING_REPETITIONS = 3
EXPECTED_CASES = 20
EXPECTED_TIMED_INVOCATIONS = 60
WAVELENGTH_MIN_NM = 380
WAVELENGTH_MAX_NM = 780
WAVELENGTH_STEP_NM = 1
INHERITED_SEAM_DEG = Decimal("5.0")
CURRENT_VALIDATED_FLOOR_DEG = Decimal("5.0")

PINNED_LIBRADTRAN_PACKAGE = "rubin-libradtran=2.0.6=py312pl5321he9373c2_1"
PINNED_UVSPEC_SHA256 = "2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3"

# Coordinate values from previously opened LOWALT-STELLAR-STATE-0001 protected
# matrices. Values only; no residual/error values are represented or consumed.
OPENED_STATE0001_PROTECTED_ALTITUDES = tuple(
    Decimal(x)
    for x in (
        "0.34375", "0.59375", "0.84375", "1.1875", "1.6875", "2.1875",
        "2.6875", "3.1875", "3.6875", "4.1875", "4.6875",
        "0.375", "0.625", "0.875", "1.25", "1.75", "2.25", "2.75",
        "3.25", "3.75", "4.25", "4.75",
    )
)
OPENED_STATE0001_TRAINING_ALTITUDES = tuple(
    Decimal(x)
    for x in (
        "0.25", "0.5", "0.75", "1.0", "1.5", "2.0", "2.5", "3.0",
        "3.5", "4.0", "4.5", "5.0",
    )
)


def _text(value: Decimal) -> str:
    return format(value, "f")


def _case_id(h: Decimal, e: Decimal, a: Decimal) -> str:
    return f"h{_text(h)}_e{int(e):04d}_a{_text(a)}"


def build_cases() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    ordinal = 0
    for h in ALTITUDE_DEG:
        for e in OBSERVER_ELEVATION_M:
            for a in AOD550:
                ordinal += 1
                rows.append(
                    {
                        "caseOrdinal": ordinal,
                        "caseId": _case_id(h, e, a),
                        "targetGeometricAltitudeDeg": _text(h),
                        "sourceZenithAngleDeg": _text(Decimal("90") - h),
                        "observerElevationM": _text(e),
                        "aod550": _text(a),
                        "freshCapabilitySpectrum": True,
                        "protectedEvidence": False,
                        "supportDecisionEvidence": False,
                    }
                )
    return rows


def build_timed_invocations() -> list[dict[str, Any]]:
    invocations: list[dict[str, Any]] = []
    ordinal = 0
    for case in build_cases():
        for repetition in range(1, TIMING_REPETITIONS + 1):
            ordinal += 1
            invocations.append(
                {
                    "invocationOrdinal": ordinal,
                    "caseId": case["caseId"],
                    "repetition": repetition,
                    "capabilitySpectrum": repetition == 1,
                    "timingOnly": repetition > 1,
                    "retryAllowed": False,
                    "resumeAllowed": False,
                    "githubRerunAllowed": False,
                }
            )
    return invocations


def collision_summary() -> dict[str, Any]:
    fresh = set(ALTITUDE_DEG)
    opened_protected = sorted(fresh.intersection(OPENED_STATE0001_PROTECTED_ALTITUDES))
    opened_training = sorted(fresh.intersection(OPENED_STATE0001_TRAINING_ALTITUDES))
    return {
        "openedState0001ProtectedAltitudeCollisionCount": len(opened_protected),
        "openedState0001TrainingAltitudeCollisionCount": len(opened_training),
        "openedState0001ProtectedAltitudeCollisions": [_text(x) for x in opened_protected],
        "openedState0001TrainingAltitudeCollisions": [_text(x) for x in opened_training],
    }


def manifest() -> dict[str, Any]:
    cases = build_cases()
    invocations = build_timed_invocations()
    payload: dict[str, Any] = {
        "scientificState": SCIENTIFIC_STATE,
        "protocolId": PROTOCOL_ID,
        "issue60TheoryFreezeComment": ISSUE60_THEORY_FREEZE_COMMENT,
        "issue60ApplicationBudgetFreezeComment": ISSUE60_BUDGET_FREEZE_COMMENT,
        "postV1Nonblocking": True,
        "solverExecutionAuthorizedByThisController": False,
        "protectedResultsAuthorized": False,
        "compactRepresentationSelected": False,
        "applicationSupportChangeAuthorized": False,
        "authoritativeExistingMinimumGeometricAltitudeDeg": _text(CURRENT_VALIDATED_FLOOR_DEG),
        "exactHorizonSupported": False,
        "targetAltitudeBasis": "topocentric-vacuum-geometric",
        "refractionAppliedInRadiativeTransfer": False,
        "freshAxes": {
            "targetGeometricAltitudeDeg": [_text(x) for x in ALTITUDE_DEG],
            "observerElevationM": [_text(x) for x in OBSERVER_ELEVATION_M],
            "aod550": [_text(x) for x in AOD550],
        },
        "freshCaseCount": len(cases),
        "timingRepetitionsPerCase": TIMING_REPETITIONS,
        "timedInvocationCount": len(invocations),
        "capabilitySpectrumCount": sum(1 for row in invocations if row["capabilitySpectrum"]),
        "timingOnlyInvocationCount": sum(1 for row in invocations if row["timingOnly"]),
        "cases": cases,
        "timedInvocations": invocations,
        "collisionAudit": collision_summary(),
        "inheritedSeam": {
            "geometricAltitudeDeg": _text(INHERITED_SEAM_DEG),
            "freshSuccessorEvidence": False,
            "mustRemainV32Authoritative": True,
        },
        "runtimeIdentity": {
            "libRadtranPackage": PINNED_LIBRADTRAN_PACKAGE,
            "uvspecSha256": PINNED_UVSPEC_SHA256,
            "wavelengthNm": [WAVELENGTH_MIN_NM, WAVELENGTH_MAX_NM, WAVELENGTH_STEP_NM],
        },
        "directTransportContract": {
            "source": "solar",
            "molecularAbsorption": "crs",
            "aerosol": "aerosol_default",
            "aerosolAodCoordinate": "aerosol_set_tau_at_wvl 550",
            "surfaceAlbedo": "0.15",
            "solver": "sdisort",
            "sdisortNscat": 1,
            "observerTruncation": "atm_z_grid begins at geometric observer elevation; zout=0",
            "outputQuantity": "transmittance",
            "outputUser": "lambda edir",
            "lineOfSightTransmission": "T_los = edir / sin(h_geo), h_geo > 0",
            "storedExactQuantityWhenFinite": "tau_los = -ln(T_los)",
        },
        "failureSemantics": {
            "zeroTransmission": "NUMERICALLY_UNRESOLVED",
            "negativeTransmission": "NUMERICALLY_UNRESOLVED",
            "nonfiniteTransmission": "NUMERICALLY_UNRESOLVED",
            "epsilonSubstitutionAllowed": False,
            "sameIdentityRetryAllowed": False,
        },
        "timingContract": {
            "runtimeVerificationBeforeTimedInvocations": True,
            "environmentSetupReportedSeparately": True,
            "warmProcessInvocationsPerCase": TIMING_REPETITIONS,
            "firstInvocationOnlyIsCapabilitySpectrum": True,
            "reportStatistics": ["median", "p95", "max", "total", "per-altitude"],
        },
        "practicalRouteFreeze": {
            "perSampleRemoteSdisortEligible": False,
            "ordinaryTimelineBaseEvaluations": 2049,
            "sevenDayAnnualSingleTargetBaseEvaluations": 108597,
            "exactCacheRequiresExactKey": True,
            "cacheQuantizationAllowed": False,
            "cacheInterpolationAllowed": False,
            "cacheMissSemantics": "FAIL_CLOSED_UNLESS_SEPARATELY_REVIEWED_EXACT_SOLVER_SERVICE",
            "futureRemoteExactRoute": "BATCHED_ORCHESTRATION_ONLY",
        },
        "forbiddenSelectionInputs": [
            "Taylor residuals",
            "Jerusalem residuals",
            "desired halachic first-seeing times",
            "MYSTIC-STATE-0077 holdout residuals",
            "LOWALT-STELLAR-STATE-0001 opened protected residuals",
        ],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    payload["manifestSha256"] = hashlib.sha256(canonical).hexdigest()
    return payload


def self_test() -> None:
    cases = build_cases()
    invocations = build_timed_invocations()
    assert len(cases) == EXPECTED_CASES
    assert len({row["caseId"] for row in cases}) == EXPECTED_CASES
    assert {Decimal(row["targetGeometricAltitudeDeg"]) for row in cases} == set(ALTITUDE_DEG)
    assert {Decimal(row["observerElevationM"]) for row in cases} == set(OBSERVER_ELEVATION_M)
    assert {Decimal(row["aod550"]) for row in cases} == set(AOD550)
    assert all(Decimal("0") < Decimal(row["targetGeometricAltitudeDeg"]) < INHERITED_SEAM_DEG for row in cases)
    assert all(
        Decimal(row["sourceZenithAngleDeg"]) == Decimal("90") - Decimal(row["targetGeometricAltitudeDeg"])
        for row in cases
    )
    collisions = collision_summary()
    assert collisions["openedState0001ProtectedAltitudeCollisionCount"] == 0
    assert collisions["openedState0001TrainingAltitudeCollisionCount"] == 0
    assert len(invocations) == EXPECTED_TIMED_INVOCATIONS
    assert sum(1 for row in invocations if row["capabilitySpectrum"]) == EXPECTED_CASES
    assert sum(1 for row in invocations if row["timingOnly"]) == EXPECTED_CASES * 2
    assert all(not row["retryAllowed"] and not row["resumeAllowed"] and not row["githubRerunAllowed"] for row in invocations)
    per_case: dict[str, list[int]] = {}
    for row in invocations:
        per_case.setdefault(row["caseId"], []).append(int(row["repetition"]))
    assert all(repetitions == [1, 2, 3] for repetitions in per_case.values())
    m = manifest()
    assert m["solverExecutionAuthorizedByThisController"] is False
    assert m["protectedResultsAuthorized"] is False
    assert m["compactRepresentationSelected"] is False
    assert m["applicationSupportChangeAuthorized"] is False
    assert m["practicalRouteFreeze"]["perSampleRemoteSdisortEligible"] is False
    assert m["exactHorizonSupported"] is False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--emit-manifest", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        print("PASS LOWALT-STELLAR-STATE-0002 capability/runtime controller self-test")
    if args.emit_manifest:
        print(json.dumps(manifest(), indent=2, sort_keys=True))
    if not args.self_test and not args.emit_manifest:
        parser.error("choose --self-test and/or --emit-manifest")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
