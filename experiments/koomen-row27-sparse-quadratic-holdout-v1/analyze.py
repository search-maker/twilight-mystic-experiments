#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

STAGE = "koomen-row27-sparse-quadratic-holdout-v1"
EXECUTION_KEY = "koomen-row27-sparse-quadratic-holdout-v1:scientific:54"
TRAIN_EXECUTION_KEY = "koomen-row27-vroom-precision-v1:scientific:53"
TRAIN_BASES = [1571000000, 1572000000, 1573000000, 1574000000, 1575000000, 1576000000]
FRESH_BASES = [1581000000, 1582000000, 1583000000, 1584000000, 1585000000, 1586000000]
CASES = ["baseline", "profile"]
OPERATORS = ["ciePhotopicQ", "sqmConditionalQ"]
PRIMARY = "ciePhotopicQ"
SECONDARY = "sqmConditionalQ"
TRAIN_CARDINALS = {"center": 0, "edge_0": 1, "edge_90": 2, "edge_180": 3, "edge_270": 4}
HOLDOUTS = {
    10: (0.5, 0.0),
    11: (0.5, 45.0),
    12: (0.5, 90.0),
    13: (0.5, 135.0),
    14: (0.5, 180.0),
    15: (1.0, 45.0),
    16: (1.0, 135.0),
    17: (1.0, 225.0),
    18: (1.0, 315.0),
}
SYMMETRY_PAIRS = [(15, 18, "edge_045_vs_315"), (16, 17, "edge_135_vs_225")]
T95_DF5 = 2.570581835636305
THRESHOLD = 0.030
PASS = "ROW27_SPARSE_QUADRATIC_CIE_HOLDOUT_PASS"
FAIL = "ROW27_SPARSE_QUADRATIC_CIE_HOLDOUT_FAIL"


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


def gate(mean, se, ci):
    precision = se <= THRESHOLD
    consistency = (ci[0] <= 0.0 <= ci[1]) or abs(mean) <= THRESHOLD
    return precision and consistency, precision, consistency


def load_training(root: Path):
    paths = sorted(root.rglob("precision-result.json"))
    if len(paths) != 6:
        raise RuntimeError(f"expected six ordinal53 training result files, got {len(paths)}")
    out = {}
    for path in paths:
        x = json.loads(path.read_text())
        if x.get("executionKey") != TRAIN_EXECUTION_KEY or x.get("status") != "COMPLETED" or int(x.get("row", -1)) != 27:
            raise RuntimeError(f"wrong ordinal53 training identity/status: {path}")
        rep = int(x["replicate"])
        if rep in out or not 1 <= rep <= 6:
            raise RuntimeError(f"duplicate/invalid ordinal53 replicate {rep}")
        if int(x["seedBase"]) != TRAIN_BASES[rep - 1]:
            raise RuntimeError(f"ordinal53 seed mismatch replicate {rep}")
        if int(x["photonsPerDirectionPerCase"]) != 6_500_000:
            raise RuntimeError("ordinal53 photon budget mismatch")
        if x.get("method") != "mc_vroom on + mc_escape on":
            raise RuntimeError("ordinal53 method mismatch")
        for key in ("TaylorResidualUsed", "historicalKoomenCorrectionComputed", "physicalSupportEnvelopeAuthorized", "full81DirectionGridAuthorized", "productionAuthorized"):
            if x.get(key) is not False:
                raise RuntimeError(f"ordinal53 boundary changed: {key}")
        out[rep] = x
    return out


def load_fresh(root: Path):
    paths = sorted(root.rglob("holdout-result.json"))
    if len(paths) != 6:
        raise RuntimeError(f"expected six fresh holdout result files, got {len(paths)}")
    out = {}
    for path in paths:
        x = json.loads(path.read_text())
        if x.get("stageId") != STAGE or x.get("executionKey") != EXECUTION_KEY or x.get("status") != "COMPLETED" or int(x.get("row", -1)) != 27:
            raise RuntimeError(f"wrong fresh result identity/status: {path}")
        rep = int(x["replicate"])
        if rep in out or not 1 <= rep <= 6:
            raise RuntimeError(f"duplicate/invalid fresh replicate {rep}")
        if int(x["seedBase"]) != FRESH_BASES[rep - 1]:
            raise RuntimeError(f"fresh seed mismatch replicate {rep}")
        if int(x["photonsPerDirectionPerCase"]) != 6_500_000:
            raise RuntimeError("fresh photon budget mismatch")
        if x.get("method") != "mc_vroom on + mc_escape on":
            raise RuntimeError("fresh method mismatch")
        for key in ("TaylorResidualUsed", "historicalAcceptanceInvented", "exactHistoricalSpectralResponseClaimed", "physicalKoomenCorrectionComputed", "physicalSupportEnvelopeAuthorized", "full81DirectionGridAuthorized", "productionAuthorized"):
            if x.get(key) is not False:
                raise RuntimeError(f"fresh boundary changed: {key}")
        out[rep] = x
    return out


def q_lookup(x, case, operator, direction):
    hits = [r for r in x["results"][case] if int(r["directionIndex"]) == direction]
    if len(hits) != 1:
        raise RuntimeError(f"expected one direction {direction}, got {len(hits)}")
    return float(hits[0][operator])


def validate_all_q(training, fresh):
    for rep in range(1, 7):
        for case in CASES:
            for operator in OPERATORS:
                for direction in TRAIN_CARDINALS.values():
                    mag(q_lookup(training[rep], case, operator, direction))
                for direction in [0, *HOLDOUTS.keys()]:
                    mag(q_lookup(fresh[rep], case, operator, direction))


def training_coefficients(training, rep, case, operator):
    center = mag(q_lookup(training[rep], case, operator, 0))
    delta0 = mag(q_lookup(training[rep], case, operator, 1)) - center
    delta90 = mag(q_lookup(training[rep], case, operator, 2)) - center
    delta180 = mag(q_lookup(training[rep], case, operator, 3)) - center
    delta270 = mag(q_lookup(training[rep], case, operator, 4)) - center
    return {
        "b": (delta0 - delta180) / 2.0,
        "c": (delta0 + delta180) / 2.0,
        "d": (delta90 + delta270) / 2.0,
    }


def predict(coeff, rho, phi_deg):
    ph = math.radians(phi_deg)
    u = rho * math.cos(ph)
    v = rho * math.sin(ph)
    return coeff["b"] * u + coeff["c"] * u * u + coeff["d"] * v * v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--training-root", type=Path, required=True)
    ap.add_argument("--fresh-root", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()

    training = load_training(a.training_root)
    fresh = load_fresh(a.fresh_root)
    validate_all_q(training, fresh)

    holdout_rows = []
    symmetry_rows = []
    coefficient_rows = []

    for case in CASES:
        for operator in OPERATORS:
            coeff_by_rep = [training_coefficients(training, rep, case, operator) for rep in range(1, 7)]
            coefficient_rows.append({
                "case": case,
                "operator": operator,
                "b": stats([c["b"] for c in coeff_by_rep]),
                "c": stats([c["c"] for c in coeff_by_rep]),
                "d": stats([c["d"] for c in coeff_by_rep]),
            })

            for direction, (rho, phi) in HOLDOUTS.items():
                predictions = [predict(coeff_by_rep[rep - 1], rho, phi) for rep in range(1, 7)]
                observed = []
                for rep in range(1, 7):
                    center = mag(q_lookup(fresh[rep], case, operator, 0))
                    observed.append(mag(q_lookup(fresh[rep], case, operator, direction)) - center)
                ps = stats(predictions)
                os = stats(observed)
                residual_mean = os["meanMag"] - ps["meanMag"]
                combined_se = math.sqrt(ps["seMag"] ** 2 + os["seMag"] ** 2)
                half = T95_DF5 * combined_se
                ci = [residual_mean - half, residual_mean + half]
                passed, precision, consistency = gate(residual_mean, combined_se, ci)
                holdout_rows.append({
                    "kind": "holdout_residual",
                    "case": case,
                    "operator": operator,
                    "primary": operator == PRIMARY,
                    "directionIndex": direction,
                    "rho": rho,
                    "relativeAzimuthDeg": phi,
                    "prediction": ps,
                    "observation": os,
                    "residualMeanMag": residual_mean,
                    "combinedSeMag": combined_se,
                    "residualCi95MagConservativeDf5": ci,
                    "precisionPass": precision,
                    "consistencyPass": consistency,
                    "gatePass": passed,
                })

            for d1, d2, label in SYMMETRY_PAIRS:
                diffs = []
                for rep in range(1, 7):
                    m1 = mag(q_lookup(fresh[rep], case, operator, d1))
                    m2 = mag(q_lookup(fresh[rep], case, operator, d2))
                    diffs.append(m1 - m2)
                s = stats(diffs)
                passed, precision, consistency = gate(s["meanMag"], s["seMag"], s["ci95Mag"])
                symmetry_rows.append({
                    "kind": "fresh_symmetry_difference",
                    "case": case,
                    "operator": operator,
                    "primary": operator == PRIMARY,
                    "pair": label,
                    "directionIndices": [d1, d2],
                    "difference": s,
                    "precisionPass": precision,
                    "consistencyPass": consistency,
                    "gatePass": passed,
                })

    primary_holdouts = [r for r in holdout_rows if r["primary"]]
    primary_symmetry = [r for r in symmetry_rows if r["primary"]]
    secondary_holdouts = [r for r in holdout_rows if not r["primary"]]
    secondary_symmetry = [r for r in symmetry_rows if not r["primary"]]
    if len(primary_holdouts) != 18 or len(primary_symmetry) != 4:
        raise RuntimeError("primary frozen gate count mismatch")

    primary_failures = [r for r in [*primary_holdouts, *primary_symmetry] if not r["gatePass"]]
    classification = PASS if not primary_failures else FAIL
    all_primary_se = [r["combinedSeMag"] for r in primary_holdouts] + [r["difference"]["seMag"] for r in primary_symmetry]
    secondary_failures = [r for r in [*secondary_holdouts, *secondary_symmetry] if not r["gatePass"]]

    summary = {
        "schemaVersion": 1,
        "stageId": STAGE,
        "executionKey": EXECUTION_KEY,
        "classification": classification,
        "decision": {
            "primaryOperator": PRIMARY,
            "secondaryOperator": SECONDARY,
            "allQFinitePositive": True,
            "primaryHoldoutGateCount": len(primary_holdouts),
            "primarySymmetryGateCount": len(primary_symmetry),
            "primaryTotalGateCount": len(primary_holdouts) + len(primary_symmetry),
            "primaryFailureCount": len(primary_failures),
            "primaryWorstSeMag": max(all_primary_se),
            "primaryBestSeMag": min(all_primary_se),
            "combinedSeThresholdMag": THRESHOLD,
            "secondaryFailureCountNonDecisional": len(secondary_failures),
            "secondaryNeverChangesClassification": True,
        },
        "surrogate": {
            "form": "delta(u,v)=b*u+c*u^2+d*v^2",
            "trainingSource": "immutable ordinal53 cardinal directions only",
            "freshHoldoutsRefitCoefficients": False,
            "postOrdinal53MethodologicalRedesign": True,
            "row27Only": True,
        },
        "coefficients": coefficient_rows,
        "holdouts": holdout_rows,
        "symmetry": symmetry_rows,
        "TaylorResidualUsed": False,
        "historicalAcceptanceInvented": False,
        "exactHistoricalSpectralResponseClaimed": False,
        "physicalKoomenCorrectionComputed": False,
        "physicalSupportEnvelopeAuthorized": False,
        "full81DirectionGridAuthorized": False,
        "productionAuthorized": False,
    }

    a.output.mkdir(parents=True, exist_ok=False)
    (a.output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n")
    with (a.output / "compact.csv").open("w", newline="") as f:
        fields = ["kind", "case", "operator", "primary", "direction_or_pair", "meanResidualOrDifferenceMag", "seMag", "ci95LoMag", "ci95HiMag", "precisionPass", "consistencyPass", "gatePass"]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in holdout_rows:
            w.writerow({
                "kind": r["kind"], "case": r["case"], "operator": r["operator"], "primary": r["primary"],
                "direction_or_pair": r["directionIndex"], "meanResidualOrDifferenceMag": r["residualMeanMag"], "seMag": r["combinedSeMag"],
                "ci95LoMag": r["residualCi95MagConservativeDf5"][0], "ci95HiMag": r["residualCi95MagConservativeDf5"][1],
                "precisionPass": r["precisionPass"], "consistencyPass": r["consistencyPass"], "gatePass": r["gatePass"],
            })
        for r in symmetry_rows:
            s = r["difference"]
            w.writerow({
                "kind": r["kind"], "case": r["case"], "operator": r["operator"], "primary": r["primary"],
                "direction_or_pair": r["pair"], "meanResidualOrDifferenceMag": s["meanMag"], "seMag": s["seMag"],
                "ci95LoMag": s["ci95Mag"][0], "ci95HiMag": s["ci95Mag"][1],
                "precisionPass": r["precisionPass"], "consistencyPass": r["consistencyPass"], "gatePass": r["gatePass"],
            })

    print(json.dumps({"classification": classification, "decision": summary["decision"]}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
