#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np

STAGE = "koomen-alis-importance-screen-v1"
EXECUTION_KEY = "koomen-alis-importance-screen-v1:scientific:55"
CENTERS = [500, 550, 600]
REFERENCE = 550
CASES = ["baseline", "profile"]
OPERATORS = ["ciePhotopicQ", "sqmConditionalQ", "anchor550Q"]
PRIMARY = "ciePhotopicQ"
TARGETS = [13, 14, 15, 18]
ALL_DIRS = [0, 13, 14, 15, 18]
T_CRIT_DF5 = 2.570581835636305
TOL = 0.03


class Failure(RuntimeError):
    pass


def stats(values):
    x = np.asarray(values, dtype=float)
    if len(x) != 6 or not np.all(np.isfinite(x)):
        raise Failure("expected six finite values")
    mean = float(np.mean(x))
    sd = float(np.std(x, ddof=1))
    se = sd / math.sqrt(6.0)
    return {
        "meanMag": mean,
        "sdMag": sd,
        "seMag": se,
        "ci95Mag": [mean - T_CRIT_DF5 * se, mean + T_CRIT_DF5 * se],
    }


def mag(q):
    q = float(q)
    if not q > 0 or not math.isfinite(q):
        raise Failure("non-positive/non-finite q")
    return -2.5 * math.log10(q)


def gate(s):
    lo, hi = s["ci95Mag"]
    return bool(lo <= 0.0 <= hi or abs(s["meanMag"]) <= TOL)


def discover(root: Path):
    files = sorted(root.rglob("screen-result.json"))
    if len(files) != 6:
        raise Failure(f"expected six result files, got {len(files)}")
    by_rep = {}
    for p in files:
        r = json.loads(p.read_text())
        if r.get("stageId") != STAGE or r.get("executionKey") != EXECUTION_KEY or r.get("status") != "COMPLETED":
            raise Failure(f"wrong result identity: {p}")
        rep = int(r["replicate"])
        if rep in by_rep:
            raise Failure(f"duplicate replicate {rep}")
        if [int(x) for x in r.get("importanceCentersNm", [])] != CENTERS:
            raise Failure("center universe changed")
        if [int(x["directionIndex"]) for x in r.get("directions", [])] != ALL_DIRS:
            raise Failure("direction universe changed")
        by_rep[rep] = r
    if sorted(by_rep) != list(range(1, 7)):
        raise Failure("replicate universe changed")
    return [by_rep[i] for i in range(1, 7)]


def rec(rep, center, case, direction):
    rows = rep["results"][str(center)][case]
    hit = [x for x in rows if int(x["directionIndex"]) == direction]
    if len(hit) != 1:
        raise Failure("direction lookup failure")
    return hit[0]


def q_value(rep, center, case, direction, operator):
    q = rec(rep, center, case, direction).get(operator)
    if q is None:
        return None
    q = float(q)
    if not q > 0 or not math.isfinite(q):
        raise Failure(f"invalid q {center}/{case}/{direction}/{operator}")
    return q


def directional_delta(rep, center, case, direction, operator):
    qd = q_value(rep, center, case, direction, operator)
    qc = q_value(rep, center, case, 0, operator)
    if qd is None or qc is None:
        return None
    return mag(qd) - mag(qc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-root", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    reps = discover(a.results_root)
    a.output.mkdir(parents=True, exist_ok=False)

    all_q_finite_positive = True
    for r in reps:
        for center in CENTERS:
            for case in CASES:
                for d in ALL_DIRS:
                    for op in ("ciePhotopicQ", "sqmConditionalQ"):
                        q_value(r, center, case, d, op)
                    anchor = rec(r, center, case, d).get("anchor550Q")
                    if anchor is not None and (not float(anchor) > 0 or not math.isfinite(float(anchor))):
                        all_q_finite_positive = False

    directional = []
    score = {}
    for center in CENTERS:
        primary_ses = []
        for case in CASES:
            for op in OPERATORS:
                for d in TARGETS:
                    vals = [directional_delta(r, center, case, d, op) for r in reps]
                    if any(v is None for v in vals):
                        directional.append({"centerNm": center, "case": case, "operator": op, "directionIndex": d, "available": False})
                        continue
                    s = stats(vals)
                    row = {"centerNm": center, "case": case, "operator": op, "directionIndex": d, "available": True, **s}
                    directional.append(row)
                    if op == PRIMARY:
                        primary_ses.append(s["seMag"])
        if len(primary_ses) != 8:
            raise Failure("missing primary directional screening quantities")
        score[center] = {
            "worstPrimaryCieSeMag": float(max(primary_ses)),
            "medianPrimaryCieSeMag": float(np.median(primary_ses)),
        }

    equivalence = []
    eligible = {REFERENCE: all_q_finite_positive}
    failures = {500: 0, 600: 0}
    for alt in (500, 600):
        alt_pass = all_q_finite_positive
        for case in CASES:
            for d in ALL_DIRS:
                vals = [mag(q_value(r, alt, case, d, PRIMARY)) - mag(q_value(r, REFERENCE, case, d, PRIMARY)) for r in reps]
                s = stats(vals)
                passed = gate(s)
                equivalence.append({"alternativeCenterNm": alt, "case": case, "kind": "absolute_direction", "directionIndex": d, "operator": PRIMARY, "gatePass": passed, **s})
                if not passed:
                    failures[alt] += 1
                    alt_pass = False
            for d in TARGETS:
                vals = [directional_delta(r, alt, case, d, PRIMARY) - directional_delta(r, REFERENCE, case, d, PRIMARY) for r in reps]
                s = stats(vals)
                passed = gate(s)
                equivalence.append({"alternativeCenterNm": alt, "case": case, "kind": "target_minus_center_delta", "directionIndex": d, "operator": PRIMARY, "gatePass": passed, **s})
                if not passed:
                    failures[alt] += 1
                    alt_pass = False
        eligible[alt] = alt_pass

    if not eligible[REFERENCE]:
        classification = "ALIS_IMPORTANCE_SCREEN_INVALID"
        nominated = None
    else:
        candidates = [c for c in CENTERS if eligible.get(c, False)]
        nominated = min(candidates, key=lambda c: (score[c]["worstPrimaryCieSeMag"], 0 if c == REFERENCE else 1, c))
        if nominated == 500:
            classification = "ALIS_IMPORTANCE_SCREEN_NOMINATES_500"
        elif nominated == 600:
            classification = "ALIS_IMPORTANCE_SCREEN_NOMINATES_600"
        else:
            classification = "ALIS_IMPORTANCE_SCREEN_RETAINS_550"

    summary = {
        "schemaVersion": 1,
        "stageId": STAGE,
        "executionKey": EXECUTION_KEY,
        "classification": classification,
        "nominatedImportanceCenterNm": nominated,
        "referenceImportanceCenterNm": REFERENCE,
        "allQFinitePositive": all_q_finite_positive,
        "eligibility": {str(k): bool(v) for k, v in eligible.items()},
        "equivalenceFailureCount": {str(k): int(v) for k, v in failures.items()},
        "screeningScore": {str(k): v for k, v in score.items()},
        "directionalStatistics": directional,
        "expectationEquivalence": equivalence,
        "selectionBiasBoundary": "screening nomination only; fresh independent confirmation required before use",
        "TaylorResidualUsed": False,
        "ordinal54Salvage": False,
        "quadraticSurrogateRehabilitated": False,
        "historicalAcceptanceInvented": False,
        "exactHistoricalSpectralResponseClaimed": False,
        "physicalKoomenCorrectionComputed": False,
        "physicalSupportEnvelopeAuthorized": False,
        "full81DirectionGridAuthorized": False,
        "productionAuthorized": False,
    }
    (a.output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n")

    with (a.output / "compact.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["section", "centerNm", "case", "operator", "kind", "directionIndex", "meanMag", "seMag", "ci95LoMag", "ci95HiMag", "gatePass"])
        for x in directional:
            if not x.get("available"):
                continue
            w.writerow(["directional", x["centerNm"], x["case"], x["operator"], "target_minus_center", x["directionIndex"], x["meanMag"], x["seMag"], x["ci95Mag"][0], x["ci95Mag"][1], ""])
        for x in equivalence:
            w.writerow(["equivalence", x["alternativeCenterNm"], x["case"], x["operator"], x["kind"], x["directionIndex"], x["meanMag"], x["seMag"], x["ci95Mag"][0], x["ci95Mag"][1], x["gatePass"]])

    print(json.dumps({"classification": classification, "nominatedImportanceCenterNm": nominated, "score": score, "equivalenceFailures": failures}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
