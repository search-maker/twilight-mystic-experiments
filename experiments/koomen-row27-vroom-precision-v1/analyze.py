#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

STAGE = "koomen-row27-vroom-precision-v1"
EXECUTION_KEY = "koomen-row27-vroom-precision-v1:scientific:53"
BASES = [1571000000, 1572000000, 1573000000, 1574000000, 1575000000, 1576000000]
OPERATORS = ["ciePhotopicQ", "sqmConditionalQ"]
CASES = ["baseline", "profile"]
EDGES = [1, 2, 3, 4]
T95_DF5 = 2.570581835636305
THRESHOLD = 0.030
EXPECTED_SCALING = math.sqrt(6_500_000 / 200_000)
PASS = "ROW27_VROOM_6P5M_PRECISION_PASS"
FAIL = "ROW27_VROOM_6P5M_PRECISION_FAIL"


def stats(values):
    n = len(values)
    if n != 6:
        raise RuntimeError(f"expected six values, got {n}")
    mean = sum(values) / n
    sd = math.sqrt(sum((x - mean) ** 2 for x in values) / (n - 1))
    se = sd / math.sqrt(n)
    half = T95_DF5 * se
    return {"meanMag": mean, "sdMag": sd, "seMag": se, "ci95Mag": [mean - half, mean + half]}


def mag(q):
    if not isinstance(q, (int, float)) or not math.isfinite(q) or q <= 0:
        raise RuntimeError(f"non-finite/non-positive q: {q!r}")
    return -2.5 * math.log10(q)


def load_results(root: Path):
    paths = sorted(root.rglob("precision-result.json"))
    if len(paths) != 6:
        raise RuntimeError(f"expected six result files, got {len(paths)}")
    out = {}
    for path in paths:
        x = json.loads(path.read_text())
        if x.get("stageId") != STAGE or x.get("executionKey") != EXECUTION_KEY or x.get("status") != "COMPLETED":
            raise RuntimeError(f"wrong result identity/status: {path}")
        rep = int(x["replicate"])
        if rep in out or not 1 <= rep <= 6:
            raise RuntimeError(f"duplicate/invalid replicate {rep}")
        if int(x["seedBase"]) != BASES[rep - 1]:
            raise RuntimeError(f"seed base mismatch replicate {rep}")
        if int(x["photonsPerDirectionPerCase"]) != 6_500_000:
            raise RuntimeError("photon budget mismatch")
        if x.get("method") != "mc_vroom on + mc_escape on":
            raise RuntimeError("method mismatch")
        for key in ("TaylorResidualUsed", "historicalKoomenCorrectionComputed", "physicalSupportEnvelopeAuthorized", "full81DirectionGridAuthorized", "productionAuthorized"):
            if x.get(key) is not False:
                raise RuntimeError(f"boundary changed: {key}")
        out[rep] = x
    return out


def q_lookup(x, case, operator, direction):
    hits = [r for r in x["results"][case] if int(r["directionIndex"]) == direction]
    if len(hits) != 1:
        raise RuntimeError(f"expected one direction {direction}, got {len(hits)}")
    return float(hits[0][operator])


def ordinal51_index(path: Path):
    x = json.loads(path.read_text())
    if x.get("executionKey") != "koomen-support-estimator-pilot-v1:scientific:51":
        raise RuntimeError("ordinal51 summary identity mismatch")
    out = {}
    for row in x.get("rows", []):
        if int(row.get("row", -1)) != 27 or row.get("kind") != "edge_delta":
            continue
        direction = int(row.get("directionIndex", -1))
        if direction not in EDGES:
            continue
        out[(row["case"], row["operator"], direction)] = float(row["on"]["seMag"])
    if len(out) != 16:
        raise RuntimeError(f"expected 16 matching ordinal51 VROOM edge SEs, got {len(out)}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-root", type=Path, required=True)
    ap.add_argument("--ordinal51-summary", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()

    by_rep = load_results(a.results_root)
    prior = ordinal51_index(a.ordinal51_summary)
    rows = []
    for case in CASES:
        for operator in OPERATORS:
            for direction in EDGES:
                deltas = []
                for rep in range(1, 7):
                    x = by_rep[rep]
                    center = mag(q_lookup(x, case, operator, 0))
                    edge = mag(q_lookup(x, case, operator, direction))
                    deltas.append(edge - center)
                s = stats(deltas)
                old_se = prior[(case, operator, direction)]
                ratio = old_se / s["seMag"] if s["seMag"] > 0 else None
                rows.append({
                    "row": 27,
                    "case": case,
                    "operator": operator,
                    "directionIndex": direction,
                    "edgeMinusCenter": s,
                    "precisionPass": s["seMag"] <= THRESHOLD,
                    "ordinal51Vroom200kSeMag": old_se,
                    "ordinal51ToOrdinal53SeRatio": ratio,
                    "ratioToPlanningSqrtFactor": (ratio / EXPECTED_SCALING if ratio is not None else None),
                })

    failures = [r for r in rows if not r["precisionPass"]]
    ratios = [r["ordinal51ToOrdinal53SeRatio"] for r in rows]
    observed_ses = [r["edgeMinusCenter"]["seMag"] for r in rows]
    classification = PASS if not failures else FAIL
    sorted_ratios = sorted(ratios)
    summary = {
        "schemaVersion": 1,
        "stageId": STAGE,
        "executionKey": EXECUTION_KEY,
        "classification": classification,
        "decision": {
            "allQFinitePositive": True,
            "edgeMinusCenterSeThresholdMag": THRESHOLD,
            "gateCount": len(rows),
            "failureCount": len(failures),
            "worstSeMag": max(observed_ses),
            "bestSeMag": min(observed_ses),
        },
        "scaling": {
            "planningSqrtFactor": EXPECTED_SCALING,
            "observedOrdinal51ToOrdinal53RatioMin": min(ratios),
            "observedOrdinal51ToOrdinal53RatioMedian": (sorted_ratios[7] + sorted_ratios[8]) / 2,
            "observedOrdinal51ToOrdinal53RatioMax": max(ratios),
            "descriptiveOnly": True,
        },
        "rows": rows,
        "TaylorResidualUsed": False,
        "historicalKoomenCorrectionComputed": False,
        "physicalSupportEnvelopeAuthorized": False,
        "full81DirectionGridAuthorized": False,
        "productionAuthorized": False,
    }

    a.output.mkdir(parents=True, exist_ok=False)
    (a.output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n")
    with (a.output / "compact.csv").open("w", newline="") as f:
        fields = ["case", "operator", "directionIndex", "meanMag", "seMag", "ci95LoMag", "ci95HiMag", "precisionPass", "ordinal51Vroom200kSeMag", "ordinal51ToOrdinal53SeRatio", "ratioToPlanningSqrtFactor"]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            s = r["edgeMinusCenter"]
            w.writerow({
                "case": r["case"], "operator": r["operator"], "directionIndex": r["directionIndex"],
                "meanMag": s["meanMag"], "seMag": s["seMag"], "ci95LoMag": s["ci95Mag"][0], "ci95HiMag": s["ci95Mag"][1],
                "precisionPass": r["precisionPass"], "ordinal51Vroom200kSeMag": r["ordinal51Vroom200kSeMag"],
                "ordinal51ToOrdinal53SeRatio": r["ordinal51ToOrdinal53SeRatio"], "ratioToPlanningSqrtFactor": r["ratioToPlanningSqrtFactor"],
            })
    print(json.dumps({"classification": classification, "decision": summary["decision"], "scaling": summary["scaling"]}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
