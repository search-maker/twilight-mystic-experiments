#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

STAGE = "koomen-vroom-equivalence-sentinel-v1"
EXECUTION_KEY = "koomen-vroom-equivalence-sentinel-v1:scientific:52"
BASES = [1561000000, 1562000000, 1563000000, 1564000000, 1565000000, 1566000000]
OPERATORS = ["ciePhotopicQ", "sqmConditionalQ"]
CASES = ["baseline", "profile"]
DIRECTIONS = [0, 3, 4]
EDGES = [3, 4]
T95_DF5 = 2.570581835636305
TOL = 0.030
PASS = "VROOM_HIGH_PHOTON_EQUIVALENCE_SENTINEL_PASS"
FAIL = "VROOM_HIGH_PHOTON_EQUIVALENCE_SENTINEL_FAIL"


def mean_sd_se_ci(values):
    n = len(values)
    if n != 6:
        raise RuntimeError(f"expected six paired values, got {n}")
    mean = sum(values) / n
    sd = math.sqrt(sum((x - mean) ** 2 for x in values) / (n - 1))
    se = sd / math.sqrt(n)
    half = T95_DF5 * se
    return {
        "meanMag": mean,
        "sdMag": sd,
        "seMag": se,
        "ci95Mag": [mean - half, mean + half],
    }


def gate(stats):
    lo, hi = stats["ci95Mag"]
    return (lo <= 0.0 <= hi) or abs(stats["meanMag"]) <= TOL


def mag(q):
    if not isinstance(q, (int, float)) or not math.isfinite(q) or q <= 0:
        raise RuntimeError(f"non-finite/non-positive q: {q!r}")
    return -2.5 * math.log10(q)


def load_results(root: Path):
    paths = sorted(root.rglob("sentinel-result.json"))
    if len(paths) != 6:
        raise RuntimeError(f"expected six result files, got {len(paths)}")
    by_rep = {}
    for path in paths:
        x = json.loads(path.read_text())
        if x.get("stageId") != STAGE or x.get("executionKey") != EXECUTION_KEY or x.get("status") != "COMPLETED":
            raise RuntimeError(f"wrong result identity/status: {path}")
        rep = int(x["replicate"])
        if rep in by_rep or not 1 <= rep <= 6:
            raise RuntimeError(f"duplicate/invalid replicate {rep}")
        if int(x["seedBase"]) != BASES[rep - 1]:
            raise RuntimeError(f"seed base mismatch replicate {rep}")
        if int(x["photonsPerDirectionPerCaseMethod"]) != 2_000_000:
            raise RuntimeError("photon budget mismatch")
        if x.get("TaylorResidualUsed") is not False or x.get("historicalKoomenCorrectionComputed") is not False or x.get("productionAuthorized") is not False:
            raise RuntimeError("boundary flag changed")
        by_rep[rep] = x
    return by_rep


def q_lookup(x, method, case, operator, direction):
    hits = [r for r in x["results"][method][case] if int(r["directionIndex"]) == direction]
    if len(hits) != 1:
        raise RuntimeError(f"expected one direction {direction}, got {len(hits)}")
    return float(hits[0][operator])


def ordinal51_index(path: Path | None):
    if path is None:
        return {}
    x = json.loads(path.read_text())
    if x.get("executionKey") != "koomen-support-estimator-pilot-v1:scientific:51":
        raise RuntimeError("ordinal51 summary identity mismatch")
    out = {}
    for row in x.get("rows", []):
        if int(row.get("row", -1)) != 18:
            continue
        kind = row.get("kind")
        case = row.get("case")
        operator = row.get("operator")
        direction = int(row.get("directionIndex", -1))
        if kind == "center_method_shift" and direction == 0:
            out[("absolute_method_shift", case, operator, 0)] = float(row["seMag"])
        elif kind == "edge_delta" and direction in EDGES:
            out[("edge_delta_method_shift", case, operator, direction)] = float(row["methodShiftOnMinusOff"]["seMag"])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-root", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--ordinal51-summary", type=Path)
    a = ap.parse_args()

    by_rep = load_results(a.results_root)
    previous = ordinal51_index(a.ordinal51_summary)
    rows = []

    for case in CASES:
        for operator in OPERATORS:
            for direction in DIRECTIONS:
                shifts = []
                off_mags = []
                on_mags = []
                for rep in range(1, 7):
                    x = by_rep[rep]
                    moff = mag(q_lookup(x, "off", case, operator, direction))
                    mon = mag(q_lookup(x, "on", case, operator, direction))
                    off_mags.append(moff)
                    on_mags.append(mon)
                    shifts.append(mon - moff)
                stats = mean_sd_se_ci(shifts)
                key = ("absolute_method_shift", case, operator, direction)
                prev_se = previous.get(key)
                record = {
                    "kind": "absolute_method_shift",
                    "row": 18,
                    "case": case,
                    "operator": operator,
                    "directionIndex": direction,
                    "pairedShiftOnMinusOff": stats,
                    "methodShiftPass": gate(stats),
                    "meanOffRelativeMagnitudeNoZeropoint": sum(off_mags) / 6,
                    "meanOnRelativeMagnitudeNoZeropoint": sum(on_mags) / 6,
                    "ordinal51ComparableSeMag": prev_se,
                    "ordinal51ToOrdinal52SeRatio": (prev_se / stats["seMag"] if prev_se is not None and stats["seMag"] > 0 else None),
                }
                rows.append(record)

            for direction in EDGES:
                shifts = []
                off_delta = []
                on_delta = []
                for rep in range(1, 7):
                    x = by_rep[rep]
                    off_center = mag(q_lookup(x, "off", case, operator, 0))
                    on_center = mag(q_lookup(x, "on", case, operator, 0))
                    off_edge = mag(q_lookup(x, "off", case, operator, direction))
                    on_edge = mag(q_lookup(x, "on", case, operator, direction))
                    doff = off_edge - off_center
                    don = on_edge - on_center
                    off_delta.append(doff)
                    on_delta.append(don)
                    shifts.append(don - doff)
                stats = mean_sd_se_ci(shifts)
                key = ("edge_delta_method_shift", case, operator, direction)
                prev_se = previous.get(key)
                record = {
                    "kind": "edge_delta_method_shift",
                    "row": 18,
                    "case": case,
                    "operator": operator,
                    "directionIndex": direction,
                    "pairedShiftOnMinusOff": stats,
                    "methodShiftPass": gate(stats),
                    "offEdgeMinusCenter": mean_sd_se_ci(off_delta),
                    "onEdgeMinusCenter": mean_sd_se_ci(on_delta),
                    "ordinal51ComparableSeMag": prev_se,
                    "ordinal51ToOrdinal52SeRatio": (prev_se / stats["seMag"] if prev_se is not None and stats["seMag"] > 0 else None),
                }
                rows.append(record)

    failures = [r for r in rows if not r["methodShiftPass"]]
    comparable_ratios = [r["ordinal51ToOrdinal52SeRatio"] for r in rows if r["ordinal51ToOrdinal52SeRatio"] is not None]
    classification = PASS if not failures else FAIL
    summary = {
        "schemaVersion": 1,
        "stageId": STAGE,
        "executionKey": EXECUTION_KEY,
        "classification": classification,
        "decision": {
            "allMethodShiftGatesPass": not failures,
            "allQFinitePositive": True,
            "methodShiftToleranceMag": TOL,
            "gateCount": len(rows),
            "failureCount": len(failures),
        },
        "seScaling": {
            "comparableQuantityCount": len(comparable_ratios),
            "ordinal51ToOrdinal52SeRatioMin": min(comparable_ratios) if comparable_ratios else None,
            "ordinal51ToOrdinal52SeRatioMedian": sorted(comparable_ratios)[len(comparable_ratios) // 2] if comparable_ratios else None,
            "ordinal51ToOrdinal52SeRatioMax": max(comparable_ratios) if comparable_ratios else None,
            "note": "Ratios are descriptive only; no new precision gate was introduced.",
        },
        "rows": rows,
        "TaylorResidualUsed": False,
        "historicalKoomenCorrectionComputed": False,
        "physicalSupportEnvelopeAuthorized": False,
        "productionAuthorized": False,
    }

    a.output.mkdir(parents=True, exist_ok=False)
    (a.output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n")
    with (a.output / "compact.csv").open("w", newline="") as f:
        fieldnames = [
            "kind", "case", "operator", "directionIndex", "meanShiftMag", "seShiftMag",
            "ci95LoMag", "ci95HiMag", "methodShiftPass", "ordinal51ComparableSeMag",
            "ordinal51ToOrdinal52SeRatio",
        ]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            s = r["pairedShiftOnMinusOff"]
            w.writerow({
                "kind": r["kind"],
                "case": r["case"],
                "operator": r["operator"],
                "directionIndex": r["directionIndex"],
                "meanShiftMag": s["meanMag"],
                "seShiftMag": s["seMag"],
                "ci95LoMag": s["ci95Mag"][0],
                "ci95HiMag": s["ci95Mag"][1],
                "methodShiftPass": r["methodShiftPass"],
                "ordinal51ComparableSeMag": r["ordinal51ComparableSeMag"],
                "ordinal51ToOrdinal52SeRatio": r["ordinal51ToOrdinal52SeRatio"],
            })
    print(json.dumps({
        "classification": classification,
        "gateCount": len(rows),
        "failureCount": len(failures),
        "seScaling": summary["seScaling"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
