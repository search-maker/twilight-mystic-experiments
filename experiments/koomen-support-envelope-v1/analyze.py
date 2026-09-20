#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from pathlib import Path

ROWS = list(range(18, 28))
REPLICATES = [1, 2, 3, 4]
CASES = ["baseline", "profile"]
OPERATORS = ["ciePhotopicQ", "sqmConditionalQ"]
T95_DF3 = 3.182446305284263


def mag_delta(q: float, q_center: float) -> float:
    if not q > 0 or not q_center > 0:
        raise RuntimeError("non-positive directional quantity")
    return -2.5 * math.log10(q / q_center)


def mean_sd_se(xs):
    xs = [float(x) for x in xs]
    if len(xs) != 4:
        raise RuntimeError(f"expected 4 independent replicates, got {len(xs)}")
    mean = statistics.fmean(xs)
    sd = statistics.stdev(xs)
    return mean, sd, sd / math.sqrt(len(xs))


def ci95(mean, se):
    half = T95_DF3 * se
    return [mean - half, mean + half]


def load_results(root: Path):
    found = {}
    for p in root.rglob("pair-result.json"):
        x = json.loads(p.read_text())
        if x.get("status") != "COMPLETED":
            continue
        if x.get("executionKey") != "koomen-support-envelope-v1:scientific:50":
            raise RuntimeError(f"wrong result execution identity in {p}")
        key = (int(x["row"]), int(x["replicate"]))
        if key in found:
            raise RuntimeError(f"duplicate result {key}")
        found[key] = x
    expected = {(r, p) for r in ROWS for p in REPLICATES}
    if set(found) != expected:
        raise RuntimeError(f"need exact 40 results; missing={sorted(expected-set(found))} extra={sorted(set(found)-expected)}")
    return found


def replicate_metrics(result, case, operator):
    rr = result["directions"][case]
    if len(rr) != 81:
        raise RuntimeError("direction count drift")
    center = [x for x in rr if int(x["directionIndex"]) == 0]
    if len(center) != 1:
        raise RuntimeError("center direction missing/nonunique")
    q0 = float(center[0][operator])
    all_deltas = []
    edge_deltas = []
    per_direction = []
    for x in rr:
        d = mag_delta(float(x[operator]), q0)
        rec = {
            "directionIndex": int(x["directionIndex"]),
            "thetaDeg": float(x["thetaDeg"]),
            "relativeAzimuthDeg": float(x["relativeAzimuthDeg"]),
            "deltaMagVsCenter": d
        }
        per_direction.append(rec)
        all_deltas.append(d)
        if abs(float(x["thetaDeg"]) - 0.75) < 1e-12:
            edge_deltas.append(d)
    if len(edge_deltas) != 16:
        raise RuntimeError("edge ring changed")
    return {
        "fullMin": min(all_deltas),
        "fullMax": max(all_deltas),
        "fullSpan": max(all_deltas) - min(all_deltas),
        "fullMaxAbs": max(abs(x) for x in all_deltas),
        "edgeMin": min(edge_deltas),
        "edgeMax": max(edge_deltas),
        "edgeSpan": max(edge_deltas) - min(edge_deltas),
        "edgeMaxAbs": max(abs(x) for x in edge_deltas),
        "perDirection": per_direction
    }


def stat_block(values):
    mean, sd, se = mean_sd_se(values)
    return {"meanMag": mean, "sdMag": sd, "seMag": se, "ci95Mag": ci95(mean, se)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-root", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    a.output.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(a.manifest.read_text())
    if manifest.get("executionKey") != "koomen-support-envelope-v1:scientific:50":
        raise RuntimeError("wrong manifest")
    found = load_results(a.results_root)

    summary_rows = []
    directional_rows = []
    for row in ROWS:
        first = found[(row, 1)]
        for case in CASES:
            for operator in OPERATORS:
                rep = []
                for p in REPLICATES:
                    x = found[(row, p)]
                    m = replicate_metrics(x, case, operator)
                    rep.append(m)
                    for d in m["perDirection"]:
                        directional_rows.append({
                            "row": row,
                            "replicate": p,
                            "sun_alt_geometric_deg": float(x["sunAltGeometricDeg"]),
                            "case": case,
                            "operator": operator,
                            **d
                        })
                rec = {
                    "row": row,
                    "sun_alt_geometric_deg": float(first["sunAltGeometricDeg"]),
                    "comparison_role": first["comparisonRole"],
                    "case": case,
                    "operator": operator,
                    "full_grid_sampled_min_delta_mag": stat_block([m["fullMin"] for m in rep]),
                    "full_grid_sampled_max_delta_mag": stat_block([m["fullMax"] for m in rep]),
                    "full_grid_sampled_span_mag": stat_block([m["fullSpan"] for m in rep]),
                    "full_grid_sampled_max_abs_delta_mag": stat_block([m["fullMaxAbs"] for m in rep]),
                    "edge_ring_sampled_min_delta_mag": stat_block([m["edgeMin"] for m in rep]),
                    "edge_ring_sampled_max_delta_mag": stat_block([m["edgeMax"] for m in rep]),
                    "edge_ring_sampled_span_mag": stat_block([m["edgeSpan"] for m in rep]),
                    "edge_ring_sampled_max_abs_delta_mag": stat_block([m["edgeMaxAbs"] for m in rep])
                }
                summary_rows.append(rec)

    compact = []
    for r in summary_rows:
        compact.append({
            "row": r["row"],
            "sun_alt_geometric_deg": r["sun_alt_geometric_deg"],
            "case": r["case"],
            "operator": r["operator"],
            "full_max_abs_mean_mag": r["full_grid_sampled_max_abs_delta_mag"]["meanMag"],
            "full_max_abs_se_mag": r["full_grid_sampled_max_abs_delta_mag"]["seMag"],
            "full_max_abs_ci95_low_mag": r["full_grid_sampled_max_abs_delta_mag"]["ci95Mag"][0],
            "full_max_abs_ci95_high_mag": r["full_grid_sampled_max_abs_delta_mag"]["ci95Mag"][1],
            "full_span_mean_mag": r["full_grid_sampled_span_mag"]["meanMag"],
            "edge_max_abs_mean_mag": r["edge_ring_sampled_max_abs_delta_mag"]["meanMag"]
        })

    max_row_by_group = {}
    for case in CASES:
        for operator in OPERATORS:
            candidates = [r for r in compact if r["case"] == case and r["operator"] == operator]
            worst = max(candidates, key=lambda r: r["full_max_abs_mean_mag"])
            max_row_by_group[f"{case}:{operator}"] = worst

    output = {
        "schemaVersion": 1,
        "stageId": manifest["stageId"],
        "executionKey": manifest["executionKey"],
        "classification": "DENSE_SAMPLED_SUPPORT_ENVELOPE_COMPLETE",
        "directionGrid": manifest["directionGrid"],
        "replicateCount": 4,
        "rows": summary_rows,
        "worstMeanSampledMaxAbsDeltaByCaseOperator": max_row_by_group,
        "referenceScalesMag": manifest["analysis"]["referenceScalesMag"],
        "historicalBoundary": {
            "exactWithinFieldAcceptanceRecovered": False,
            "exactInstalledSpectralResponseRecovered": False,
            "continuousExtremaProven": False,
            "weightedKoomenCorrectionReported": False,
            "fractionOf039ExplainedReported": False,
            "note": "This experiment constrains only the dense sampled directional variation inside the documented 0.75-degree support under frozen physical cases."
        },
        "productionAuthorized": False
    }
    (a.output / "summary.json").write_text(json.dumps(output, indent=2, sort_keys=True, allow_nan=False) + "\n")

    with (a.output / "compact.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(compact[0].keys()))
        w.writeheader()
        w.writerows(compact)
    with (a.output / "per_direction.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(directional_rows[0].keys()))
        w.writeheader()
        w.writerows(directional_rows)

    print(json.dumps({"classification": output["classification"], "worst": max_row_by_group}, sort_keys=True))


if __name__ == "__main__":
    main()
