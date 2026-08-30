#!/usr/bin/env python3
"""Solver-free planning contracts for LOWALT-STELLAR-STATE-0002.

This module deliberately has no subprocess/uvspec/libRadtran execution path.  It
materializes the result-blind training/model-selection geometry, deterministic
refinement rules, protected-coordinate generation rules, collision checks, and
contiguous-suffix support-floor decision specified by
LOW_ALTITUDE_STELLAR_TRANSPORT_STATE_AND_PROTOCOL_V2.md.
"""

from __future__ import annotations

import argparse
import itertools
import json
from fractions import Fraction
from typing import Dict, Iterable, List, Mapping, Sequence, Set, Tuple

SCIENTIFIC_STATE = "LOWALT-STELLAR-STATE-0002"
PROTOCOL_ID = "low-altitude-stellar-state-0002-result-blind-adaptive-tau-v1"

INITIAL_ALTITUDE_KNOTS = tuple(
    Fraction(x)
    for x in (
        "0.25", "0.5", "0.75", "1.0", "1.5", "2.0", "2.5", "3.0",
        "3.5", "4.0", "4.5", "5.0",
    )
)
INITIAL_ELEVATION_KNOTS = tuple(Fraction(x) for x in ("0", "500", "1250", "2000", "2500"))
INITIAL_AOD_KNOTS = tuple(Fraction(x) for x in ("0.05", "0.10", "0.20", "0.30", "0.40"))

TRAINING_FRACTIONS = (
    (Fraction(1, 3), Fraction(2, 5), Fraction(3, 7)),
    (Fraction(2, 3), Fraction(3, 5), Fraction(4, 7)),
)
PROTECTED_FRACTIONS = (
    (Fraction(2, 7), Fraction(3, 11), Fraction(5, 13)),
    (Fraction(5, 7), Fraction(8, 11), Fraction(8, 13)),
)

TRAINING_MAX_ABS_AV_MAG = Fraction(25, 10000)  # 0.0025 = 10% protected max gate
TRAINING_RMS_AV_MAG = Fraction(10, 10000)       # 0.0010 = 10% protected RMS gate
PROTECTED_MAX_ABS_AV_MAG = Fraction(25, 1000)  # 0.025
PROTECTED_RMS_AV_MAG = Fraction(10, 1000)       # 0.010
MAX_REFINEMENT_ROUNDS = 3
PICKLES_LIBRARY_NUMBERS = (1, 26, 45)
WAVELENGTH_MIN_NM = 380
WAVELENGTH_MAX_NM = 780
WAVELENGTH_STEP_NM = 1

# Previously opened low-alt protected coordinate universes.  Coordinates only;
# no residual/error value is encoded or consumed by this planning helper.
OPENED_STATE0001_V1_ALTITUDES = tuple(
    Fraction(x) for x in (
        "0.34375", "0.59375", "0.84375", "1.1875", "1.6875", "2.1875",
        "2.6875", "3.1875", "3.6875", "4.1875", "4.6875",
    )
)
OPENED_STATE0001_V1_ELEVATIONS = tuple(Fraction(x) for x in ("187.5", "781.25", "1531.25", "2187.5"))
OPENED_STATE0001_V1_AOD = tuple(Fraction(x) for x in ("0.06875", "0.1375", "0.2375", "0.3375"))

OPENED_STATE0001_V2_ALTITUDES = tuple(
    Fraction(x) for x in (
        "0.375", "0.625", "0.875", "1.25", "1.75", "2.25",
        "2.75", "3.25", "3.75", "4.25", "4.75",
    )
)
OPENED_STATE0001_V2_ELEVATIONS = tuple(Fraction(x) for x in ("250", "875", "1625", "2250"))
OPENED_STATE0001_V2_AOD = tuple(Fraction(x) for x in ("0.075", "0.15", "0.25", "0.35"))

Point = Tuple[Fraction, Fraction, Fraction]
Cell = Tuple[Tuple[Fraction, Fraction], Tuple[Fraction, Fraction], Tuple[Fraction, Fraction]]


def _cartesian_points(xs: Sequence[Fraction], ys: Sequence[Fraction], zs: Sequence[Fraction]) -> Set[Point]:
    return set(itertools.product(xs, ys, zs))


OPENED_PROTECTED_POINTS: Set[Point] = (
    _cartesian_points(OPENED_STATE0001_V1_ALTITUDES, OPENED_STATE0001_V1_ELEVATIONS, OPENED_STATE0001_V1_AOD)
    | _cartesian_points(OPENED_STATE0001_V2_ALTITUDES, OPENED_STATE0001_V2_ELEVATIONS, OPENED_STATE0001_V2_AOD)
)


def _between(lo: Fraction, hi: Fraction, f: Fraction) -> Fraction:
    if not (Fraction(0) < f < Fraction(1)):
        raise ValueError("interior fraction must be strictly inside (0,1)")
    if not lo < hi:
        raise ValueError("cell bounds must be strictly increasing")
    return lo + f * (hi - lo)


def cells(
    altitude_knots: Sequence[Fraction],
    elevation_knots: Sequence[Fraction],
    aod_knots: Sequence[Fraction],
) -> List[Cell]:
    def intervals(values: Sequence[Fraction]) -> List[Tuple[Fraction, Fraction]]:
        if any(b <= a for a, b in zip(values, values[1:])):
            raise ValueError("knots must be strictly increasing")
        return list(zip(values, values[1:]))

    return list(itertools.product(intervals(altitude_knots), intervals(elevation_knots), intervals(aod_knots)))


def point_in_cell(cell: Cell, fractions: Tuple[Fraction, Fraction, Fraction]) -> Point:
    return tuple(_between(bounds[0], bounds[1], f) for bounds, f in zip(cell, fractions))  # type: ignore[return-value]


def training_probe_points(
    altitude_knots: Sequence[Fraction] = INITIAL_ALTITUDE_KNOTS,
    elevation_knots: Sequence[Fraction] = INITIAL_ELEVATION_KNOTS,
    aod_knots: Sequence[Fraction] = INITIAL_AOD_KNOTS,
) -> List[Point]:
    result: List[Point] = []
    for cell in cells(altitude_knots, elevation_knots, aod_knots):
        for fractions in TRAINING_FRACTIONS:
            result.append(point_in_cell(cell, fractions))
    return result


def tensor_vertices(
    altitude_knots: Sequence[Fraction] = INITIAL_ALTITUDE_KNOTS,
    elevation_knots: Sequence[Fraction] = INITIAL_ELEVATION_KNOTS,
    aod_knots: Sequence[Fraction] = INITIAL_AOD_KNOTS,
) -> List[Point]:
    return list(itertools.product(altitude_knots, elevation_knots, aod_knots))


def protected_probe_points(
    altitude_knots: Sequence[Fraction],
    elevation_knots: Sequence[Fraction],
    aod_knots: Sequence[Fraction],
) -> List[Point]:
    """Materialize the pre-frozen protected rule after training grid freeze.

    The caller must still prove these points are disjoint from the *complete*
    training/model-selection universe accumulated over every refinement round.
    """
    result: List[Point] = []
    for cell in cells(altitude_knots, elevation_knots, aod_knots):
        (hlo, hhi), _, _ = cell
        if hhi > Fraction(5):
            raise ValueError("STATE-0002 protected generator is <5 deg only")
        for fractions in PROTECTED_FRACTIONS:
            result.append(point_in_cell(cell, fractions))
    return result


def collision_report(points: Iterable[Point], forbidden: Iterable[Point]) -> List[Point]:
    return sorted(set(points) & set(forbidden))


def refine_grid_from_failing_cells(
    altitude_knots: Sequence[Fraction],
    elevation_knots: Sequence[Fraction],
    aod_knots: Sequence[Fraction],
    failing_cells: Iterable[Cell],
) -> Tuple[Tuple[Fraction, ...], Tuple[Fraction, ...], Tuple[Fraction, ...]]:
    """Apply the frozen conservative all-axis midpoint refinement rule."""
    h: Set[Fraction] = set(altitude_knots)
    e: Set[Fraction] = set(elevation_knots)
    a: Set[Fraction] = set(aod_knots)
    for cell in failing_cells:
        (hlo, hhi), (elo, ehi), (alo, ahi) = cell
        h.add((hlo + hhi) / 2)
        e.add((elo + ehi) / 2)
        a.add((alo + ahi) / 2)
    return tuple(sorted(h)), tuple(sorted(e)), tuple(sorted(a))


def minimum_supported_floor_from_altitude_slices(
    altitude_knots: Sequence[Fraction],
    slice_pass: Mapping[Tuple[Fraction, Fraction], bool],
    suffix_global_pass: Mapping[Fraction, bool],
) -> Fraction:
    """Mechanical preregistered contiguous-suffix support decision.

    `slice_pass[(lo,hi)]` is the frozen max+RMS decision for that altitude cell.
    `suffix_global_pass[lo]` is the frozen max+RMS decision over all protected
    comparisons from `lo` through <5 deg.  No residual magnitude is inspected.
    """
    intervals = list(zip(altitude_knots, altitude_knots[1:]))
    if not intervals or altitude_knots[-1] != Fraction(5):
        raise ValueError("altitude grid must terminate exactly at 5 deg")

    contiguous_lows: List[Fraction] = []
    for interval in reversed(intervals):
        if not slice_pass.get(interval, False):
            break
        contiguous_lows.append(interval[0])

    if not contiguous_lows:
        return Fraction(5)

    # Smallest lower boundary in the passing suffix whose preregistered
    # suffix-global aggregate also passes.  If a wider aggregate fails, a
    # narrower higher suffix may still be eligible under the frozen rule.
    for lo in sorted(contiguous_lows):
        if suffix_global_pass.get(lo, False):
            return lo

    return Fraction(5)


def _fraction_text(x: Fraction) -> str:
    if x.denominator == 1:
        return str(x.numerator)
    return f"{x.numerator}/{x.denominator}"


def _point_json(point: Point) -> Dict[str, str]:
    return {
        "targetGeometricAltitudeDeg": _fraction_text(point[0]),
        "observerElevationMeters": _fraction_text(point[1]),
        "aod550": _fraction_text(point[2]),
    }


def initial_plan() -> Dict[str, object]:
    training = training_probe_points()
    vertices = tensor_vertices()
    collisions = collision_report(training, OPENED_PROTECTED_POINTS)
    return {
        "scientificState": SCIENTIFIC_STATE,
        "protocolId": PROTOCOL_ID,
        "solverExecutionAuthorized": False,
        "protectedResultsAuthorized": False,
        "applicationSupportChangeAuthorized": False,
        "representation": {
            "quantity": "direct-optical-depth-tau=-ln(T)",
            "coordinates": ["targetGeometricAltitudeDeg", "observerElevationMeters", "aod550"],
            "interpolation": "multilinear",
            "cscExtrapolationBelow5": False,
        },
        "initialGrid": {
            "altitudeKnots": [_fraction_text(x) for x in INITIAL_ALTITUDE_KNOTS],
            "elevationKnots": [_fraction_text(x) for x in INITIAL_ELEVATION_KNOTS],
            "aodKnots": [_fraction_text(x) for x in INITIAL_AOD_KNOTS],
            "tensorVertexCount": len(vertices),
        },
        "training": {
            "probeFractions": [[_fraction_text(v) for v in f] for f in TRAINING_FRACTIONS],
            "probeCountInitialRound": len(training),
            "maxAbsAvMag": float(TRAINING_MAX_ABS_AV_MAG),
            "rmsAvMag": float(TRAINING_RMS_AV_MAG),
            "maxRefinementRounds": MAX_REFINEMENT_ROUNDS,
            "collisionCountAgainstOpenedState0001Protected": len(collisions),
            "probes": [_point_json(p) for p in training],
        },
        "protectedRule": {
            "materialized": False,
            "probeFractions": [[_fraction_text(v) for v in f] for f in PROTECTED_FRACTIONS],
            "maxAbsAvMag": float(PROTECTED_MAX_ABS_AV_MAG),
            "rmsAvMag": float(PROTECTED_RMS_AV_MAG),
            "picklesLibraryNumbers": list(PICKLES_LIBRARY_NUMBERS),
            "minimumSupportedAltitudeRule": "maximal-contiguous-passing-suffix-to-5deg-with-suffix-global-gate",
        },
        "spectral": {
            "minNm": WAVELENGTH_MIN_NM,
            "maxNm": WAVELENGTH_MAX_NM,
            "stepNm": WAVELENGTH_STEP_NM,
        },
        "exactHorizonSupported": False,
        "authoritativeExistingMinimumGeometricAltitudeDeg": 5.0,
    }


def self_test() -> None:
    assert INITIAL_ALTITUDE_KNOTS[-1] == Fraction(5)
    assert INITIAL_ALTITUDE_KNOTS[0] == Fraction(1, 4)
    assert set(TRAINING_FRACTIONS).isdisjoint(set(PROTECTED_FRACTIONS))

    training = training_probe_points()
    vertices = tensor_vertices()
    assert len(vertices) == 12 * 5 * 5
    assert len(training) == 11 * 4 * 4 * 2
    assert len(set(training)) == len(training)
    assert not collision_report(training, OPENED_PROTECTED_POINTS)
    assert not collision_report(training, vertices)

    protected = protected_probe_points(INITIAL_ALTITUDE_KNOTS, INITIAL_ELEVATION_KNOTS, INITIAL_AOD_KNOTS)
    assert len(protected) == 11 * 4 * 4 * 2
    assert len(set(protected)) == len(protected)
    assert not collision_report(protected, OPENED_PROTECTED_POINTS)
    assert not collision_report(protected, training)
    assert not collision_report(protected, vertices)

    all_intervals = list(zip(INITIAL_ALTITUDE_KNOTS, INITIAL_ALTITUDE_KNOTS[1:]))
    all_pass = {i: True for i in all_intervals}
    all_suffix = {i[0]: True for i in all_intervals}
    assert minimum_supported_floor_from_altitude_slices(INITIAL_ALTITUDE_KNOTS, all_pass, all_suffix) == Fraction(1, 4)

    top_fail = dict(all_pass)
    top_fail[all_intervals[-1]] = False
    assert minimum_supported_floor_from_altitude_slices(INITIAL_ALTITUDE_KNOTS, top_fail, all_suffix) == Fraction(5)

    mid_fail = dict(all_pass)
    mid_fail[all_intervals[5]] = False
    expected = all_intervals[6][0]
    assert minimum_supported_floor_from_altitude_slices(INITIAL_ALTITUDE_KNOTS, mid_fail, all_suffix) == expected

    # Failure of a wider suffix-global aggregate may only move the floor up;
    # it can never jump across a failing cell or claim below it.
    suffix = dict(all_suffix)
    suffix[all_intervals[6][0]] = False
    expected_higher = all_intervals[7][0]
    assert minimum_supported_floor_from_altitude_slices(INITIAL_ALTITUDE_KNOTS, mid_fail, suffix) == expected_higher


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--emit-initial-plan", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        print("PASS LOWALT-STELLAR-STATE-0002 solver-free planning self-test")
    if args.emit_initial_plan:
        print(json.dumps(initial_plan(), indent=2, sort_keys=True))
    if not args.self_test and not args.emit_initial_plan:
        parser.error("choose --self-test and/or --emit-initial-plan")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
