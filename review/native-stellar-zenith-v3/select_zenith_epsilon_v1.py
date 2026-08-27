#!/usr/bin/env python3
"""Mechanical evaluator for ZENITH_EPSILON_SELECTION_PROTOCOL_V1.

This code is frozen before opening the 76-case epsilon-convergence results.
It reads only the training-only diagnostic summary and either selects the
smallest already-tested SZA satisfying the preregistered rules or returns
NO_SELECTION.  It never executes a solver, opens a protected holdout, fits a
model, changes an acceptance gate, or authorizes production.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

STAGE_ID = "native-stellar-zenith-epsilon-selection-v1"
SOURCE_STAGE_ID = "native-stellar-zenith-v3-epsilon-convergence-v1"
EXPECTED_SZA = (
    1.0, 0.5, 0.1, 0.05, 0.03, 0.025, 0.0225, 0.021, 0.0205,
    0.0200, 0.0198, 0.01975, 0.0195, 0.0190, 0.018, 0.015, 0.010,
    0.001, 0.0001,
)
EXPECTED_SOLVER_CALLS = 76
EXPECTED_GROUPS = 4
SAFETY_FACTOR = 1.25
MAX_RELATIVE_AIRMASS_EXCESS = 1.0e-7
MAX_ABS_DELTA_AV_MAG = 1.0e-4


class SelectionRefusal(RuntimeError):
    pass


def _f(name: str, value: Any) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise SelectionRefusal(f"{name} must be numeric") from exc
    if not math.isfinite(out):
        raise SelectionRefusal(f"{name} must be finite")
    return out


def relative_airmass_excess(sza_deg: float) -> float:
    sza = _f("szaDeg", sza_deg)
    if not 0.0 < sza < 90.0:
        raise SelectionRefusal("candidate SZA must be strictly between 0 and 90 deg")
    return 1.0 / math.cos(math.radians(sza)) - 1.0


def _validate_source(summary: dict[str, Any]) -> None:
    if not isinstance(summary, dict):
        raise SelectionRefusal("diagnostic summary must be an object")
    if summary.get("schemaVersion") != 2:
        raise SelectionRefusal("diagnostic schema drift")
    if summary.get("stageId") != SOURCE_STAGE_ID:
        raise SelectionRefusal("diagnostic stage drift")
    if summary.get("status") != "TRAINING_ONLY_NUMERICAL_CONVERGENCE_DIAGNOSTIC_COMPLETE":
        raise SelectionRefusal("diagnostic is not complete")
    if summary.get("solverInvocationCount") != EXPECTED_SOLVER_CALLS:
        raise SelectionRefusal("diagnostic solver-call count drift")
    if tuple(summary.get("sourceZenithAngleDeg", ())) != EXPECTED_SZA:
        raise SelectionRefusal("tested SZA universe drift")
    if summary.get("allRejectedCasesMatchProvenEndpointSignature") is not True:
        raise SelectionRefusal("rejected cases do not all match proven umu0=1 endpoint signature")
    if summary.get("solverUsabilityMonotonicTowardZenithAcrossAllCorners") is not True:
        raise SelectionRefusal("solver usability is not monotonic toward zenith")
    groups = summary.get("groups")
    if not isinstance(groups, list) or len(groups) != EXPECTED_GROUPS:
        raise SelectionRefusal("atmosphere-corner group count drift")
    for group in groups:
        if group.get("solverUsabilityMonotonicTowardZenith") is not True:
            raise SelectionRefusal("per-corner solver usability is not monotonic")
        if group.get("allRejectedCasesMatchProvenEndpointSignature") is not True:
            raise SelectionRefusal("per-corner endpoint-signature gate failed")
        if not isinstance(group.get("comparisons"), list) or not group["comparisons"]:
            raise SelectionRefusal("per-corner usable comparison set missing")
    claim = summary.get("claimBoundary") or {}
    for key in (
        "protectedHoldoutOpened", "modelFitPerformed", "canonicalEpsilonSelected",
        "acceptanceGateEvaluated", "productionAuthorized", "empiricalRealSkyValidated",
        "humanFirstSeeingValidated",
    ):
        if claim.get(key) is not False:
            raise SelectionRefusal(f"diagnostic claim boundary drift: {key}")


def evaluate(summary: dict[str, Any]) -> dict[str, Any]:
    _validate_source(summary)
    groups = summary["groups"]
    rejected_boundary = _f(
        "largestSourceZenithAngleRejectedByAnyCornerDeg",
        summary.get("largestSourceZenithAngleRejectedByAnyCornerDeg"),
    )
    if rejected_boundary <= 0:
        raise SelectionRefusal("rejected SZA boundary must be positive")
    required_margin_sza = SAFETY_FACTOR * rejected_boundary

    comparison_maps: list[dict[float, dict[str, Any]]] = []
    for group in groups:
        mapping: dict[float, dict[str, Any]] = {}
        for row in group["comparisons"]:
            epsilon = _f("comparison sourceZenithAngleDeg", row.get("sourceZenithAngleDeg"))
            if epsilon in mapping:
                raise SelectionRefusal("duplicate usable comparison epsilon within corner")
            mapping[epsilon] = row
        comparison_maps.append(mapping)

    all_corner_usable = set(comparison_maps[0])
    for mapping in comparison_maps[1:]:
        all_corner_usable &= set(mapping)
    if not all_corner_usable:
        raise SelectionRefusal("no tested SZA is usable at all atmosphere corners")

    candidates: list[dict[str, Any]] = []
    for epsilon in sorted(all_corner_usable):
        if epsilon not in EXPECTED_SZA:
            raise SelectionRefusal(f"unregistered usable SZA in summary: {epsilon}")
        airmass_excess = relative_airmass_excess(epsilon)
        max_delta_av = max(
            _f("maxAbsDeltaAvMagVsSmallestUsableSza", mapping[epsilon].get("maxAbsDeltaAvMagVsSmallestUsableSza"))
            for mapping in comparison_maps
        )
        passes_margin = epsilon >= required_margin_sza
        passes_airmass = airmass_excess <= MAX_RELATIVE_AIRMASS_EXCESS
        passes_photometry = max_delta_av <= MAX_ABS_DELTA_AV_MAG
        candidates.append({
            "sourceZenithAngleDeg": epsilon,
            "physicalTargetAltitudeDegRepresented": 90.0,
            "requiredSafetyMarginSzaDeg": required_margin_sza,
            "relativePlaneParallelAirmassExcessVsExactVertical": airmass_excess,
            "maxAbsDeltaAvMagAcrossCornersAndTemplates": max_delta_av,
            "passesSafetyMargin": passes_margin,
            "passesAirmassBound": passes_airmass,
            "passesPhotometricConvergenceBound": passes_photometry,
            "eligible": passes_margin and passes_airmass and passes_photometry,
        })

    eligible = [row for row in candidates if row["eligible"]]
    selected = min(eligible, key=lambda row: row["sourceZenithAngleDeg"]) if eligible else None
    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "sourceStageId": SOURCE_STAGE_ID,
        "status": "CANONICAL_EPSILON_SELECTED_BY_PREREGISTERED_PROTOCOL" if selected else "NO_SELECTION_UNDER_PREREGISTERED_PROTOCOL",
        "protocol": {
            "safetyFactorAboveLargestRejectedSza": SAFETY_FACTOR,
            "maxRelativePlaneParallelAirmassExcess": MAX_RELATIVE_AIRMASS_EXCESS,
            "maxAbsDeltaAvMag": MAX_ABS_DELTA_AV_MAG,
            "selectionRule": "smallest-tested-all-corner-usable-SZA-passing-all-frozen-gates",
        },
        "largestSourceZenithAngleRejectedByAnyCornerDeg": rejected_boundary,
        "requiredSafetyMarginSzaDeg": required_margin_sza,
        "allCornerUsableSourceZenithAngleDeg": sorted(all_corner_usable),
        "candidateEvaluations": candidates,
        "selected": selected,
        "claimBoundary": {
            "protectedHoldoutOpened": False,
            "solverExecuted": False,
            "modelFitPerformed": False,
            "acceptanceGateEvaluated": False,
            "productionAuthorized": False,
            "empiricalRealSkyValidated": False,
            "humanFirstSeeingValidated": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = evaluate(json.loads(args.summary.read_text(encoding="utf-8")))
    text = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
