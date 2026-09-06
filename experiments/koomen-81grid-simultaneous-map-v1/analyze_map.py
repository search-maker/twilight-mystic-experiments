#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from pathlib import Path

STAGE = "koomen-81grid-simultaneous-map-v1"
EXECUTION_KEY = "koomen-81grid-simultaneous-map-v1:scientific:59"
ROWS = list(range(18, 28))
CASES = ["baseline", "profile"]
OPERATORS = ["ciePhotopicQ", "sqmConditionalQ"]
PRIMARY = "ciePhotopicQ"
SECONDARY = "sqmConditionalQ"
REPS = 6
BASES = [1631000000, 1632000000, 1633000000, 1634000000, 1635000000, 1636000000]
SEED_OFFSET = 997
PHOTONS_BY_ROW = {
    18: 1_000_000, 19: 1_000_000, 20: 1_000_000,
    21: 2_000_000, 22: 2_000_000, 23: 2_000_000,
    24: 5_000_000, 25: 5_000_000, 26: 5_000_000, 27: 5_000_000,
}
RINGS = [0.15, 0.30, 0.45, 0.60, 0.75]
FULL_AZ = [22.5 * i for i in range(16)]
T_CRIT = 6.712593092914674
FAMILY_SIZE = 45
FAMILY_ALPHA = 0.05
VALID = "KOOMEN_81GRID_SIMULTANEOUS_SUPPORT_MAP_VALID"
INVALID = "KOOMEN_81GRID_SIMULTANEOUS_SUPPORT_MAP_INVALID"


class Failure(RuntimeError):
    pass


def full_grid():
    out = [{"directionIndex": 0, "thetaDeg": 0.0, "relativeAzimuthDeg": 0.0, "ring": "center"}]
    idx = 0
    for radius in RINGS:
        for az in FULL_AZ:
            idx += 1
            out.append({"directionIndex": idx, "thetaDeg": radius, "relativeAzimuthDeg": az, "ring": f"r{radius:.2f}"})
    if len(out) != 81:
        raise Failure("full-grid construction changed")
    return out


def executed_indices():
    return [0] + [i for base in (1, 17, 33, 49, 65) for i in range(base, base + 9)]


def mirror_map():
    full = full_grid()
    by = {(round(d["thetaDeg"], 8), round(d["relativeAzimuthDeg"], 8)): d["directionIndex"] for d in full}
    out = {}
    for d in full:
        az = d["relativeAzimuthDeg"]
        if d["directionIndex"] == 0 or az <= 180.0:
            out[d["directionIndex"]] = d["directionIndex"]
        else:
            out[d["directionIndex"]] = by[(round(d["thetaDeg"], 8), round(360.0 - az, 8))]
    if len(out) != 81 or len(set(out.values())) != 46:
        raise Failure("mirror map changed")
    return out


def mag_delta(q_target: float, q_center: float) -> float:
    if not (math.isfinite(q_target) and math.isfinite(q_center) and q_target > 0 and q_center > 0):
        raise Failure("non-finite/non-positive Q")
    x = -2.5 * math.log10(q_target / q_center)
    if not math.isfinite(x):
        raise Failure("non-finite magnitude delta")
    return x


def summarize(vals):
    if len(vals) != REPS or any(not math.isfinite(v) for v in vals):
        raise Failure("invalid replicate vector")
    mean = statistics.fmean(vals)
    sd = statistics.stdev(vals)
    se = sd / math.sqrt(REPS)
    lo = mean - T_CRIT * se
    hi = mean + T_CRIT * se
    return {
        "n": REPS,
        "meanMag": mean,
        "sdMag": sd,
        "seMag": se,
        "simultaneous95LowMag": lo,
        "simultaneous95HighMag": hi,
    }


def abs_interval_lower(lo: float, hi: float) -> float:
    if lo <= 0.0 <= hi:
        return 0.0
    return min(abs(lo), abs(hi))


def validate_manifest(path: Path):
    m = json.loads(path.read_text())
    if m.get("stageId") != STAGE or m.get("executionKey") != EXECUTION_KEY or m.get("issue") != 877:
        raise Failure("wrong manifest identity")
    if m.get("rows") != ROWS or m.get("cases") != CASES:
        raise Failure("manifest universe changed")
    a = m.get("analysis", {})
    if a.get("replicateCount") != REPS or a.get("df") != 5 or a.get("familySize") != FAMILY_SIZE or float(a.get("familyAlpha")) != FAMILY_ALPHA:
        raise Failure("analysis family changed")
    if abs(float(a.get("studentTBonferroniCritical")) - T_CRIT) > 1e-14:
        raise Failure("frozen t critical changed")
    if a.get("deltaDefinition") != "-2.5*log10(Q_target/Q_center)" or a.get("sampleMeanMinMaxDecisional") is not False:
        raise Failure("analysis semantics changed")
    c = m.get("classification", {})
    if c.get("valid") != VALID or c.get("invalid") != INVALID or c.get("numericalWidthPassFailThreshold") is not None:
        raise Failure("classification contract changed")
    return m


def load_results(root: Path):
    files = sorted(root.rglob("map-result.json"))
    expected_count = len(ROWS) * len(CASES) * REPS
    if len(files) != expected_count:
        raise Failure(f"expected {expected_count} result files, got {len(files)}")
    ex = executed_indices()
    mm = mirror_map()
    by = {}
    for p in files:
        x = json.loads(p.read_text())
        if x.get("stageId") != STAGE or x.get("executionKey") != EXECUTION_KEY or x.get("status") != "COMPLETED":
            raise Failure(f"bad identity/status in {p}")
        row = int(x.get("row", -1)); rep = int(x.get("replicate", -1)); case = x.get("case")
        if row not in ROWS or rep not in range(1, REPS + 1) or case not in CASES:
            raise Failure("row/replicate/case outside frozen universe")
        key = (row, rep, case)
        if key in by:
            raise Failure(f"duplicate result {key}")
        if int(x.get("seedBase", -1)) != BASES[rep - 1] or int(x.get("derivedSharedSeedAcrossDirectionsAndCases", -1)) != BASES[rep - 1] + row * 1000 + SEED_OFFSET:
            raise Failure("seed identity changed")
        if int(x.get("photonsPerDirectionPerCase", -1)) != PHOTONS_BY_ROW[row]:
            raise Failure("photon schedule changed")
        if int(x.get("fullDirectionCount", -1)) != 81 or int(x.get("executedDirectionCount", -1)) != 46 or int(x.get("uniqueNonCenterExpectationCount", -1)) != 45:
            raise Failure("direction cardinality changed")
        got_mm = {int(k): int(v) for k, v in x.get("mirrorIndexMap", {}).items()}
        if got_mm != mm:
            raise Failure("result mirror map changed")
        if x.get("method") != "direct ALIS; mc_vroom on; mc_escape on; mc_spectral_is 550.0":
            raise Failure("result estimator changed")
        if x.get("TaylorResidualUsed") is not False or x.get("historicalAcceptanceInvented") is not False or x.get("exactHistoricalSpectralResponseClaimed") is not False or x.get("continuousSupportExtremaClaimed") is not False or x.get("rawSampledExtremaUsedDecisively") is not False or x.get("productionAuthorized") is not False:
            raise Failure("result boundary changed")
        rows = x.get("directions", [])
        if [int(r.get("directionIndex", -1)) for r in rows] != ex:
            raise Failure("executed direction universe/order changed")
        for r in rows:
            for op in OPERATORS:
                q = float(r.get(op, float("nan")))
                if not math.isfinite(q) or q <= 0:
                    raise Failure(f"invalid {op} Q at {key} direction {r.get('directionIndex')}")
        by[key] = x
    if len(by) != expected_count:
        raise Failure("result universe incomplete")
    # CRN case-pair identity check.
    for row in ROWS:
        for rep in range(1, REPS + 1):
            if by[(row, rep, "baseline")]["derivedSharedSeedAcrossDirectionsAndCases"] != by[(row, rep, "profile")]["derivedSharedSeedAcrossDirectionsAndCases"]:
                raise Failure("baseline/profile CRN seed mismatch")
    return by


def analyze(by):
    ex = executed_indices()
    targets = ex[1:]
    if len(targets) != FAMILY_SIZE:
        raise Failure("unique target family changed")
    full = full_grid(); mm = mirror_map(); full_by_index = {d["directionIndex"]: d for d in full}
    unique_rows = []
    full_rows = []
    families = []

    sun_alt = {}
    for row in ROWS:
        vals = {float(by[(row, rep, "baseline")]["sunAltGeometricDeg"]) for rep in range(1, REPS + 1)}
        if len(vals) != 1:
            raise Failure("sun altitude differs between replicates")
        sun_alt[row] = vals.pop()

    for row in ROWS:
        for case in CASES:
            rep_dir = {}
            for rep in range(1, REPS + 1):
                result = by[(row, rep, case)]
                rep_dir[rep] = {int(d["directionIndex"]): d for d in result["directions"]}
            for op in OPERATORS:
                stats_by_idx = {0: {
                    "n": REPS, "meanMag": 0.0, "sdMag": 0.0, "seMag": 0.0,
                    "simultaneous95LowMag": 0.0, "simultaneous95HighMag": 0.0,
                }}
                for idx in targets:
                    vals = []
                    for rep in range(1, REPS + 1):
                        center = float(rep_dir[rep][0][op])
                        target = float(rep_dir[rep][idx][op])
                        vals.append(mag_delta(target, center))
                    s = summarize(vals)
                    stats_by_idx[idx] = s
                    d = full_by_index[idx]
                    unique_rows.append({
                        "row": row, "sunAltGeometricDeg": sun_alt[row], "case": case, "operator": op,
                        "directionIndex": idx, "thetaDeg": d["thetaDeg"], "relativeAzimuthDeg": d["relativeAzimuthDeg"],
                        **s,
                    })

                lows = [0.0] + [stats_by_idx[i]["simultaneous95LowMag"] for i in targets]
                highs = [0.0] + [stats_by_idx[i]["simultaneous95HighMag"] for i in targets]
                means = [0.0] + [stats_by_idx[i]["meanMag"] for i in targets]
                ses = [stats_by_idx[i]["seMag"] for i in targets]
                max_lower = max(lows); max_upper = max(highs)
                min_lower = min(lows); min_upper = min(highs)
                span_lower = max(0.0, max_lower - min_upper)
                span_upper = max_upper - min_lower
                max_abs_lower = max([0.0] + [abs_interval_lower(stats_by_idx[i]["simultaneous95LowMag"], stats_by_idx[i]["simultaneous95HighMag"]) for i in targets])
                max_abs_upper = max([0.0] + [max(abs(stats_by_idx[i]["simultaneous95LowMag"]), abs(stats_by_idx[i]["simultaneous95HighMag"])) for i in targets])
                if any(not math.isfinite(v) for v in (max_lower,max_upper,min_lower,min_upper,span_lower,span_upper,max_abs_lower,max_abs_upper)) or span_upper < span_lower:
                    raise Failure("invalid simultaneous bound")
                family = {
                    "row": row,
                    "sunAltGeometricDeg": sun_alt[row],
                    "case": case,
                    "operator": op,
                    "familySizeUniqueNonCenter": FAMILY_SIZE,
                    "replicateCount": REPS,
                    "df": 5,
                    "familyAlpha": FAMILY_ALPHA,
                    "studentTBonferroniCritical": T_CRIT,
                    "sampleMeanMinMagDescriptiveOnly": min(means),
                    "sampleMeanMaxMagDescriptiveOnly": max(means),
                    "sampleMeanSpanMagDescriptiveOnly": max(means) - min(means),
                    "maxSeMag": max(ses),
                    "medianSeMag": statistics.median(ses),
                    "minTrueDeltaLowerMag": min_lower,
                    "minTrueDeltaUpperMag": min_upper,
                    "maxTrueDeltaLowerMag": max_lower,
                    "maxTrueDeltaUpperMag": max_upper,
                    "spanLowerMag": span_lower,
                    "spanUpperMag": span_upper,
                    "maxAbsTrueDeltaLowerMag": max_abs_lower,
                    "maxAbsTrueDeltaUpperMag": max_abs_upper,
                    "anyNonnegativeDiscreteRadianceWeightingShiftLowerMag": min_lower,
                    "anyNonnegativeDiscreteRadianceWeightingShiftUpperMag": max_upper,
                    "coverageScope": "95% simultaneous within this row x case x operator family only; no joint 95% claim across families",
                }
                families.append(family)

                for d in full:
                    idx = d["directionIndex"]
                    src = mm[idx]
                    s = stats_by_idx[src]
                    full_rows.append({
                        "row": row, "sunAltGeometricDeg": sun_alt[row], "case": case, "operator": op,
                        "directionIndex": idx, "thetaDeg": d["thetaDeg"], "relativeAzimuthDeg": d["relativeAzimuthDeg"],
                        "executedSourceDirectionIndex": src, "mirroredByExactModelSymmetry": idx != src,
                        **s,
                    })

    if len(unique_rows) != len(ROWS) * len(CASES) * len(OPERATORS) * FAMILY_SIZE:
        raise Failure("unique statistics universe wrong")
    if len(full_rows) != len(ROWS) * len(CASES) * len(OPERATORS) * 81:
        raise Failure("full-grid statistics universe wrong")
    if len(families) != len(ROWS) * len(CASES) * len(OPERATORS):
        raise Failure("family universe wrong")
    return unique_rows, full_rows, families


def invalid_summary(error: str):
    return {
        "schemaVersion": 1,
        "stageId": STAGE,
        "executionKey": EXECUTION_KEY,
        "classification": INVALID,
        "validUniverse": False,
        "error": error,
        "TaylorResidualUsed": False,
        "historicalAcceptanceInvented": False,
        "exactHistoricalSpectralResponseClaimed": False,
        "continuousSupportExtremaClaimed": False,
        "rawSampledExtremaUsedDecisively": False,
        "productionAuthorized": False,
    }


def write_csv(path: Path, rows):
    if not rows:
        return
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--results-root", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    unique_rows = []; full_rows = []
    try:
        validate_manifest(a.manifest)
        by = load_results(a.results_root)
        unique_rows, full_rows, families = analyze(by)
        primary = [f for f in families if f["operator"] == PRIMARY]
        secondary = [f for f in families if f["operator"] == SECONDARY]
        summary = {
            "schemaVersion": 1,
            "stageId": STAGE,
            "executionKey": EXECUTION_KEY,
            "classification": VALID,
            "validUniverse": True,
            "rows": ROWS,
            "cases": CASES,
            "operators": {"primary": PRIMARY, "secondary": SECONDARY},
            "replicateCount": REPS,
            "fullGridDirectionCount": 81,
            "executedUniqueDirectionCount": 46,
            "uniqueNonCenterFamilySize": FAMILY_SIZE,
            "mirroredDirectionCount": 35,
            "modelSymmetry": "expectation(phi)=expectation(360-phi) under frozen horizontally homogeneous spherical-1D model",
            "familyAlpha": FAMILY_ALPHA,
            "familyDf": 5,
            "studentTBonferroniCritical": T_CRIT,
            "familyCoverageScope": "separate 95% simultaneous family for each row x case x operator; no joint 95% claim across the 40 families",
            "photonSchedule": PHOTONS_BY_ROW,
            "maximumSolverCalls": 5520,
            "maximumConfiguredPhotonHistories": 16008000000,
            "primaryCieFamilies": primary,
            "secondarySqmFamilies": secondary,
            "familyCount": len(families),
            "primaryFamilyCount": len(primary),
            "secondaryFamilyCount": len(secondary),
            "terminalConsequence": "numerical Koomen discrete-support mapping route closes at preregistered precision; no post-result estimator/photon/geometry tuning",
            "interpretation": {
                "established": "conditional discrete 81-grid model angular variation with per-family simultaneous uncertainty under baseline and CAMS-proxy cases; 35 directions reconstructed only by exact frozen-model mirror symmetry",
                "notEstablished": "exact historical acceptance weighting; exact installed P22+green-filter response; exact temporal integration; calibration uncertainty; historical H convention; continuous-field extrema; causal fraction of Taylor-Koomen gap; production or Level-B correction"
            },
            "TaylorResidualUsed": False,
            "historicalAcceptanceInvented": False,
            "exactHistoricalSpectralResponseClaimed": False,
            "continuousSupportExtremaClaimed": False,
            "rawSampledExtremaUsedDecisively": False,
            "productionAuthorized": False,
        }
    except Exception as exc:
        summary = invalid_summary(str(exc))

    (a.output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n")
    if unique_rows:
        write_csv(a.output / "unique-direction-stats.csv", unique_rows)
    if full_rows:
        write_csv(a.output / "full-grid-stats.csv", full_rows)
    print(json.dumps({
        "classification": summary["classification"],
        "validUniverse": summary["validUniverse"],
        "familyCount": summary.get("familyCount"),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
