#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path

SCENARIOS = ("native", "continental", "maritime", "desert", "desert_spheroids")
CONTRASTS = ("continental", "maritime", "desert", "desert_spheroids")
AOD_MIN = 0.05
AOD_MAX = 0.40
DEFAULT_LOG_TOLERANCE = 1e-4


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    import sys
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def signed_interval_miss(value: float, lo: float, hi: float) -> float:
    if lo <= value <= hi:
        return 0.0
    return value - lo if value < lo else value - hi


def _idw_bounds_multi(extrema, rows, coord_key, target_key, fixed, x_index,
                      selected, lo, hi, power, target_indices):
    """Exact scalar-IDW interval arithmetic reused across target channels.

    The frozen scalar evaluator recomputes geometry, weight intervals and the
    denominator independently for every target channel. Those quantities do
    not depend on target values. This function performs those identical
    operations once while preserving the original selected-row order and the
    exact outward-rounded numerator/denominator operation order for each
    requested target index.
    """
    target_indices = tuple(target_indices)
    params = []
    singular = []
    for index in selected:
        row = rows[index]
        coord = row[coord_key]
        constant = sum((fixed[j] - coord[j]) ** 2 for j in range(len(fixed)))
        center = coord[x_index]
        targets = {target_index: float(row[target_key][target_index]) for target_index in target_indices}
        params.append((index, constant, center, targets))
        if constant == 0.0 and lo <= center <= hi:
            singular.append((index, constant, center, targets))

    if len(singular) > 1:
        raise ArithmeticError("multiple exact-hit IDW singularities in selected set")

    if singular:
        singular_index, _, singular_center, singular_targets = singular[0]
        u_max = max(abs(lo - singular_center), abs(hi - singular_center))
        numerators = {
            target_index: extrema.Interval(singular_targets[target_index], singular_targets[target_index])
            for target_index in target_indices
        }
        denominator = extrema.Interval(1.0, 1.0)
        for index, constant, center, targets in params:
            if index == singular_index:
                continue
            qlo, _ = extrema._q_range(constant, center, lo, hi)
            if qlo <= 0:
                raise ArithmeticError("secondary singularity")
            if power == 1:
                ratio_hi = u_max / math.sqrt(qlo)
            elif power == 2:
                ratio_hi = (u_max * u_max) / qlo
            else:
                raise ValueError("unsupported IDW power")
            ratio = extrema.Interval(0.0, extrema._up(ratio_hi))
            for target_index in target_indices:
                numerators[target_index] = numerators[target_index].add(
                    ratio.mul_const(targets[target_index])
                )
            denominator = denominator.add(ratio)
        return {
            target_index: numerators[target_index].div_pos(denominator)
            for target_index in target_indices
        }

    numerators = {target_index: extrema.Interval(0.0, 0.0) for target_index in target_indices}
    denominator = extrema.Interval(0.0, 0.0)
    for _, constant, center, targets in params:
        weight = extrema._weight_interval(constant, center, lo, hi, power)
        if weight is None:
            raise ArithmeticError("unhandled singularity")
        for target_index in target_indices:
            numerators[target_index] = numerators[target_index].add(
                weight.mul_const(targets[target_index])
            )
        denominator = denominator.add(weight)
    return {
        target_index: numerators[target_index].div_pos(denominator)
        for target_index in target_indices
    }


def certify_pair(extrema, base, asiv, *, alt: float, az: float, elev: float,
                 aod_lo: float, aod_hi: float, log_tolerance: float,
                 max_depth: int, max_nodes: int) -> dict:
    fixed3 = extrema._geometry_fixed(3.0, alt, az, elev)
    fixed6 = extrema._geometry_fixed(6.0, alt, az, elev)
    x_lo, x_hi = extrema._x_aod(aod_lo), extrema._x_aod(aod_hi)
    base_rows = [
        {"coord": coord, "target": target, "id": index}
        for index, (coord, target) in enumerate(zip(base["residualCoordinates"], base["residualTargets"]))
    ]

    cuts = {x_lo, x_hi}
    for fixed in (fixed3, fixed6):
        cuts.update(extrema._pairwise_crossings(fixed, base_rows, "coord", 4, x_lo, x_hi))
        cuts.update(extrema._pairwise_crossings(fixed[:3], asiv["training"], "coord", 3, x_lo, x_hi))
        for row in base_rows:
            if all(fixed[j] == row["coord"][j] for j in range(4)) and x_lo < row["coord"][4] < x_hi:
                cuts.add(row["coord"][4])
        for row in asiv["training"]:
            if all(fixed[j] == row["coord"][j] for j in range(3)) and x_lo < row["coord"][3] < x_hi:
                cuts.add(row["coord"][3])
    cuts = sorted(cuts)

    result = {
        scenario: {"outerMin": math.inf, "innerMin": math.inf, "innerMax": -math.inf, "outerMax": -math.inf}
        for scenario in SCENARIOS
    }
    failures: list[str] = []
    nodes = 0
    maximum_depth_seen = 0

    def aod_from_x(x: float) -> float:
        return AOD_MIN + x * (AOD_MAX - AOD_MIN)

    def point_values(x: float) -> dict[str, float]:
        aod = aod_from_x(x)
        p3 = extrema._point_prediction(base, asiv, 3.0, alt, az, elev, aod)
        p6 = extrema._point_prediction(base, asiv, 6.0, alt, az, elev, aod)
        return {scenario: float(p6[scenario][0]) - float(p3[scenario][0]) for scenario in SCENARIOS}

    def absorb_point(x: float) -> None:
        values = point_values(x)
        for scenario, value in values.items():
            row = result[scenario]
            row["innerMin"] = min(row["innerMin"], value)
            row["innerMax"] = max(row["innerMax"], value)
            row["outerMin"] = min(row["outerMin"], value)
            row["outerMax"] = max(row["outerMax"], value)

    for x in cuts:
        absorb_point(x)

    def neighbor_sets(fixed, lo: float, hi: float):
        midpoint = (lo + hi) / 2.0
        return (
            extrema._neighbors(extrema._base_query(fixed, midpoint), base_rows, 6, "coord", "id"),
            extrema._neighbors(extrema._asiv_query(fixed, midpoint), asiv["training"], 8, "coord", "cellId"),
        )

    def all_bounds(fixed, sun: float, lo: float, hi: float, base_selected, asiv_selected) -> dict:
        """Return all scenario bounds while reusing scenario-independent work."""
        aod_segment_lo, aod_segment_hi = aod_from_x(lo), aod_from_x(hi)
        polynomial = extrema._primary_poly_bound(base, sun, alt, az, elev, aod_segment_lo, aod_segment_hi, 0)
        residual = extrema._idw_bound(base_rows, "coord", "target", fixed, 4, base_selected, lo, hi, 1, 0)
        native = polynomial.add(residual)
        contrast_target_indices = tuple(index * 3 for index in range(len(CONTRASTS)))
        contrasts = _idw_bounds_multi(
            extrema, asiv["training"], "coord", "target", fixed[:3], 3,
            asiv_selected, lo, hi, 2, contrast_target_indices,
        )
        bounds = {"native": native}
        for contrast_index, scenario in enumerate(CONTRASTS):
            bounds[scenario] = native.add(contrasts[contrast_index * 3])
        return bounds

    def recurse(lo: float, hi: float, depth: int, selected3, selected6) -> None:
        nonlocal nodes, maximum_depth_seen
        nodes += 1
        maximum_depth_seen = max(maximum_depth_seen, depth)
        if nodes > max_nodes:
            failures.append("MAX_NODES")
            return
        bounds = {}
        maximum_width = 0.0
        bounds3 = all_bounds(fixed3, 3.0, lo, hi, *selected3)
        bounds6 = all_bounds(fixed6, 6.0, lo, hi, *selected6)
        for scenario in SCENARIOS:
            b3 = bounds3[scenario]
            b6 = bounds6[scenario]
            diff = extrema.Interval(extrema._down(b6.lo - b3.hi), extrema._up(b6.hi - b3.lo))
            bounds[scenario] = diff
            maximum_width = max(maximum_width, diff.width)
        midpoint = (lo + hi) / 2.0
        if maximum_width <= log_tolerance:
            absorb_point(midpoint)
            for scenario, interval in bounds.items():
                row = result[scenario]
                row["outerMin"] = min(row["outerMin"], interval.lo)
                row["outerMax"] = max(row["outerMax"], interval.hi)
            return
        if depth >= max_depth:
            failures.append(f"MAX_DEPTH:{lo:.17g}:{hi:.17g}")
            absorb_point(midpoint)
            for scenario, interval in bounds.items():
                row = result[scenario]
                row["outerMin"] = min(row["outerMin"], interval.lo)
                row["outerMax"] = max(row["outerMax"], interval.hi)
            return
        recurse(lo, midpoint, depth + 1, selected3, selected6)
        recurse(midpoint, hi, depth + 1, selected3, selected6)

    for lo, hi in zip(cuts, cuts[1:]):
        if hi > lo:
            selected3 = neighbor_sets(fixed3, lo, hi)
            selected6 = neighbor_sets(fixed6, lo, hi)
            recurse(lo, hi, 0, selected3, selected6)

    certified = not failures
    for scenario in SCENARIOS:
        row = result[scenario]
        row["minCertificationGap"] = row["innerMin"] - row["outerMin"]
        row["maxCertificationGap"] = row["outerMax"] - row["innerMax"]
        if row["minCertificationGap"] > log_tolerance * 1.0001 or row["maxCertificationGap"] > log_tolerance * 1.0001:
            certified = False
    return {
        "algorithmId": "CERTIFIED_SAME_AOD_SAME_SCENARIO_SHAPE_INTERVAL_BNB_V1",
        "aod550Interval": [aod_lo, aod_hi],
        "logTolerance": log_tolerance,
        "partitionBreakpoints": len(cuts),
        "branchNodes": nodes,
        "maximumDepth": maximum_depth_seen,
        "certified": certified,
        "failures": failures,
        "scenarios": result,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--base-runtime", type=Path, required=True)
    parser.add_argument("--asiv-runtime", type=Path, required=True)
    parser.add_argument("--support-evaluator", type=Path, required=True)
    parser.add_argument("--extrema-evaluator", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--log-tolerance", type=float, default=DEFAULT_LOG_TOLERANCE)
    parser.add_argument("--max-depth", type=int, default=50)
    parser.add_argument("--max-nodes", type=int, default=500000)
    args = parser.parse_args()

    dataset = json.loads(args.dataset.read_text(encoding="utf-8"))
    support_mod = load_module(args.support_evaluator, "frozen_support_for_certified_shape")
    extrema = load_module(args.extrema_evaluator, "frozen_extrema_for_certified_shape")
    base_support = support_mod.load_bound_runtime(args.base_runtime)
    base = extrema.load_base_runtime(args.base_runtime)
    asiv = extrema.load_asiv_runtime(args.asiv_runtime)

    by_key = {}
    for row in dataset["rows"]:
        key = (float(row["relativeAzimuthDeg"]), float(row["targetAltitudeDeg"]))
        by_key.setdefault(key, {})[int(row["sunDepressionDeg"])] = row

    pairs = []
    certified_evaluated = []
    for (az, alt), pair in sorted(by_key.items()):
        if 3 not in pair or 6 not in pair:
            continue
        r3, r6 = pair[3], pair[6]
        elev = float(r3["observerElevationM"])
        observed = math.log(float(r6["observedPhotopicLuminanceCdM2"]) / float(r3["observedPhotopicLuminanceCdM2"]))
        s3 = support_mod.exact_max_nearest_support_distance(
            support_coordinates=base_support["supportCoordinates"], sun_depression_deg=3.0,
            target_altitude_deg=alt, relative_azimuth_deg=az, observer_elevation_m=elev,
            aod550_min=AOD_MIN, aod550_max=AOD_MAX,
        )
        s6 = support_mod.exact_max_nearest_support_distance(
            support_coordinates=base_support["supportCoordinates"], sun_depression_deg=6.0,
            target_altitude_deg=alt, relative_azimuth_deg=az, observer_elevation_m=elev,
            aod550_min=AOD_MIN, aod550_max=AOD_MAX,
        )
        rec = {"relativeAzimuthDeg": az, "targetAltitudeDeg": alt, "observerElevationM": elev,
               "observedLogL6OverL3": observed, "d3Support": s3, "d6Support": s6}
        if not (s3["supportedAcrossEntireInterval"] and s6["supportedAcrossEntireInterval"]):
            rec["status"] = "PAIR_UNSUPPORTED_ACROSS_FULL_AOD_INTERVAL"
            pairs.append(rec)
            continue
        cert = certify_pair(extrema, base, asiv, alt=alt, az=az, elev=elev,
                            aod_lo=AOD_MIN, aod_hi=AOD_MAX, log_tolerance=args.log_tolerance,
                            max_depth=args.max_depth, max_nodes=args.max_nodes)
        rec["certification"] = cert
        if not cert["certified"]:
            rec["status"] = "CONTINUOUS_AOD_CERTIFICATION_FAILED"
            pairs.append(rec)
            continue
        lo = min(v["outerMin"] for v in cert["scenarios"].values())
        hi = max(v["outerMax"] for v in cert["scenarios"].values())
        miss = signed_interval_miss(observed, lo, hi)
        rec.update({
            "status": "CERTIFIED_CONTINUOUS_AOD_SAME_AOD_SCENARIO_SHAPE_EVALUATED",
            "modelCertifiedOuterUnionLogL6OverL3": [lo, hi],
            "signedCertifiedOuterMissLog": miss,
            "absoluteCertifiedOuterMissLog": abs(miss),
            "absoluteCertifiedOuterMissMagEquivalent": abs(miss) * 2.5 / math.log(10.0),
            "observedOutsideCertifiedOuterUnion": miss != 0.0,
            "observedMoreNegativeThanCertifiedModelUnion": observed < lo,
        })
        certified_evaluated.append(rec)
        pairs.append(rec)

    output = {
        "schemaVersion": 1,
        "diagnosticId": "koomen-1952-same-aod-scenario-twilight-shape-continuous-aod-certified-v1",
        "claimClass": "PUBLISHED_OPEN_DIAGNOSTIC_CERTIFIED_CONTINUOUS_AOD_SHAPE_NOT_FORMAL_PASS_FAIL",
        "pairCount": len(pairs),
        "certifiedEvaluatedPairCount": len(certified_evaluated),
        "certifiedOutsideCount": sum(p["observedOutsideCertifiedOuterUnion"] for p in certified_evaluated),
        "certifiedObservedMoreNegativeCount": sum(p["observedMoreNegativeThanCertifiedModelUnion"] for p in certified_evaluated),
        "pairs": pairs,
        "interpretationBoundary": {
            "sameAodWithinPair": True,
            "sameAerosolScenarioWithinPair": True,
            "continuousAodCertified": True,
            "formalPassFailAuthorized": False,
            "modelRetuningAuthorized": False,
            "strictModernRealSkyValidationClaimAuthorized": False,
            "pandoraHoldoutOpened": False,
        },
    }
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "pairCount": output["pairCount"],
        "certifiedEvaluatedPairCount": output["certifiedEvaluatedPairCount"],
        "certifiedOutsideCount": output["certifiedOutsideCount"],
        "certifiedObservedMoreNegativeCount": output["certifiedObservedMoreNegativeCount"],
    }, indent=2, sort_keys=True))
    return 0 if all(p.get("status") != "CONTINUOUS_AOD_CERTIFICATION_FAILED" for p in pairs) else 2


if __name__ == "__main__":
    raise SystemExit(main())
