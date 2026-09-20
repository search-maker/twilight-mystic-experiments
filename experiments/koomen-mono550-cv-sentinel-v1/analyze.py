#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np

STAGE = "koomen-mono550-cv-sentinel-v1"
EXECUTION_KEY = "koomen-mono550-cv-sentinel-v1:scientific:56"
REPS = 6
CASES = ["baseline", "profile"]
DIRECTIONS = [0, 14, 18]
TARGETS = [14, 18]
T95_DF5 = 2.570581835636305
TOL = 0.030
PRECISION = 0.030


class Failure(RuntimeError):
    pass


def mag(q: float) -> float:
    q = float(q)
    if not q > 0 or not math.isfinite(q):
        raise Failure(f"invalid Q {q}")
    return -2.5 * math.log10(q)


def stat(values):
    a = np.asarray(values, float)
    if len(a) != REPS or not np.all(np.isfinite(a)):
        raise Failure("invalid six-replicate vector")
    mean = float(np.mean(a))
    sd = float(np.std(a, ddof=1))
    se = sd / math.sqrt(REPS)
    return {
        "n": REPS,
        "meanMag": mean,
        "sdMag": sd,
        "seMag": se,
        "ci95LowMag": mean - T95_DF5 * se,
        "ci95HighMag": mean + T95_DF5 * se,
    }


def eq_pass(s) -> bool:
    return bool(s["ci95LowMag"] <= 0.0 <= s["ci95HighMag"] or abs(s["meanMag"]) <= TOL)


def load_results(root: Path):
    files = sorted(root.rglob("sentinel-result.json"))
    if len(files) != REPS:
        raise Failure(f"expected {REPS} result files, got {len(files)}")
    by_rep = {}
    for p in files:
        x = json.loads(p.read_text())
        if x.get("stageId") != STAGE or x.get("executionKey") != EXECUTION_KEY or x.get("status") != "COMPLETED":
            raise Failure(f"bad identity/status in {p}")
        rep = int(x.get("replicate", -1))
        if rep in by_rep or rep not in range(1, REPS + 1):
            raise Failure("duplicate/out-of-range replicate")
        if int(x.get("row", -1)) != 27:
            raise Failure("row changed")
        if int(x.get("photonsPerDirectionPerCaseArm", -1)) != 1_000_000:
            raise Failure("photon budget changed")
        if x.get("methodCommon") != "mc_vroom on + mc_escape on" or float(x.get("alisImportanceCenterNm", -1)) != 550.0 or float(x.get("monoWavelengthNm", -1)) != 550.0:
            raise Failure("estimator identity changed")
        for k in ("TaylorResidualUsed", "ordinal54Salvage", "importanceWavelengthRetuned", "physicalKoomenCorrectionComputed", "physicalSupportEnvelopeAuthorized", "full81DirectionGridAuthorized", "productionAuthorized"):
            if x.get(k) is not False:
                raise Failure(f"boundary changed: {k}")
        results = x.get("results", {})
        if set(results) != {"alis550", "mono550"}:
            raise Failure("arm universe changed")
        for arm in ("alis550", "mono550"):
            if set(results[arm]) != set(CASES):
                raise Failure("case universe changed")
            for case in CASES:
                rows = results[arm][case]
                if [int(r["directionIndex"]) for r in rows] != DIRECTIONS:
                    raise Failure("direction universe/order changed")
                for r in rows:
                    if arm == "alis550":
                        mag(r["ciePhotopicQ"])
                        mag(r["anchor550Q"])
                    else:
                        mag(r["mono550Q"])
                    if not math.isfinite(float(r["solverSeconds"])) or float(r["solverSeconds"]) < 0:
                        raise Failure("invalid runtime")
        by_rep[rep] = x
    if set(by_rep) != set(range(1, REPS + 1)):
        raise Failure("replicate universe incomplete")
    return by_rep


def row_map(x, arm, case):
    return {int(r["directionIndex"]): r for r in x["results"][arm][case]}


def analyze(root: Path):
    by_rep = load_results(root)
    equivalence = []
    cv_rows = []
    direct_rows = []
    compact = []

    for case in CASES:
        for direction in DIRECTIONS:
            shifts = []
            for rep in range(1, REPS + 1):
                a = row_map(by_rep[rep], "alis550", case)[direction]
                m = row_map(by_rep[rep], "mono550", case)[direction]
                shifts.append(mag(m["mono550Q"]) - mag(a["anchor550Q"]))
            s = stat(shifts)
            rec = {"kind": "absolute", "case": case, "directionIndex": direction, **s}
            rec["pass"] = eq_pass(rec)
            equivalence.append(rec)
            compact.append(rec.copy())

        for target in TARGETS:
            shifts = []
            cv = []
            direct = []
            chromatic = []
            mono_delta = []
            anchor_delta = []
            for rep in range(1, REPS + 1):
                alis = row_map(by_rep[rep], "alis550", case)
                mono = row_map(by_rep[rep], "mono550", case)
                d_cie = mag(alis[target]["ciePhotopicQ"]) - mag(alis[0]["ciePhotopicQ"])
                d_a = mag(alis[target]["anchor550Q"]) - mag(alis[0]["anchor550Q"])
                d_m = mag(mono[target]["mono550Q"]) - mag(mono[0]["mono550Q"])
                d_cv = (d_cie - d_a) + d_m
                shifts.append(d_m - d_a)
                direct.append(d_cie)
                chromatic.append(d_cie - d_a)
                mono_delta.append(d_m)
                anchor_delta.append(d_a)
                cv.append(d_cv)

            es = stat(shifts)
            erec = {"kind": "directionalDelta", "case": case, "directionIndex": target, **es}
            erec["pass"] = eq_pass(erec)
            equivalence.append(erec)
            compact.append(erec.copy())

            cs = stat(cv)
            ds = stat(direct)
            xs = stat(chromatic)
            ms = stat(mono_delta)
            aas = stat(anchor_delta)
            cvrec = {
                "case": case,
                "directionIndex": target,
                "formula": "D_CV=(D_CIE-D_A)+D_M",
                **cs,
                "precisionPass": bool(cs["seMag"] <= PRECISION),
                "directAlisCie": ds,
                "alisChromaticCorrection": xs,
                "mono550Delta": ms,
                "alisAnchor550Delta": aas,
                "seImprovementRatioDirectOverCv": (ds["seMag"] / cs["seMag"]) if cs["seMag"] > 0 else None,
            }
            cv_rows.append(cvrec)
            direct_rows.append({"case": case, "directionIndex": target, **ds})
            compact.append({"kind": "controlVariate", "case": case, "directionIndex": target, **cs, "pass": cvrec["precisionPass"]})

    equivalence_failures = [r for r in equivalence if not r["pass"]]
    precision_failures = [r for r in cv_rows if not r["precisionPass"]]

    runtimes = {}
    for arm in ("alis550", "mono550"):
        vals = []
        for rep in range(1, REPS + 1):
            for case in CASES:
                for r in by_rep[rep]["results"][arm][case]:
                    vals.append(float(r["solverSeconds"]))
        runtimes[arm] = {
            "count": len(vals),
            "medianSolverSeconds": float(np.median(vals)),
            "totalSolverSeconds": float(np.sum(vals)),
        }
    runtimes["monoOverAlisMedianRatio"] = runtimes["mono550"]["medianSolverSeconds"] / runtimes["alis550"]["medianSolverSeconds"] if runtimes["alis550"]["medianSolverSeconds"] > 0 else None
    runtimes["monoOverAlisTotalRatio"] = runtimes["mono550"]["totalSolverSeconds"] / runtimes["alis550"]["totalSolverSeconds"] if runtimes["alis550"]["totalSolverSeconds"] > 0 else None

    if equivalence_failures:
        classification = "MONO550_CV_SENTINEL_NOT_EQUIVALENT"
    elif precision_failures:
        classification = "MONO550_CV_SENTINEL_EQUIVALENT_BUT_PRECISION_INELIGIBLE"
    else:
        classification = "MONO550_CV_SENTINEL_EQUIVALENT_AND_PRECISION_ELIGIBLE"

    return {
        "schemaVersion": 1,
        "stageId": STAGE,
        "executionKey": EXECUTION_KEY,
        "classification": classification,
        "validUniverse": True,
        "equivalenceQuantityCount": len(equivalence),
        "equivalenceFailureCount": len(equivalence_failures),
        "precisionQuantityCount": len(cv_rows),
        "precisionFailureCount": len(precision_failures),
        "methodConsistencyToleranceMag": TOL,
        "precisionTargetSeMag": PRECISION,
        "equivalence": equivalence,
        "controlVariate": cv_rows,
        "directAlisCie": direct_rows,
        "runtime": runtimes,
        "TaylorResidualUsed": False,
        "ordinal54Salvage": False,
        "importanceWavelengthRetuned": False,
        "physicalKoomenCorrectionComputed": False,
        "physicalSupportEnvelopeAuthorized": False,
        "full81DirectionGridAuthorized": False,
        "productionAuthorized": False,
    }, compact


def invalid_summary(error: str):
    return {
        "schemaVersion": 1,
        "stageId": STAGE,
        "executionKey": EXECUTION_KEY,
        "classification": "MONO550_CV_SENTINEL_INVALID",
        "validUniverse": False,
        "error": error,
        "TaylorResidualUsed": False,
        "ordinal54Salvage": False,
        "importanceWavelengthRetuned": False,
        "physicalKoomenCorrectionComputed": False,
        "physicalSupportEnvelopeAuthorized": False,
        "full81DirectionGridAuthorized": False,
        "productionAuthorized": False,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-root", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    compact = []
    try:
        summary, compact = analyze(a.results_root)
    except Failure as exc:
        summary = invalid_summary(str(exc))
    (a.output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n")
    if compact:
        keys = ["kind", "case", "directionIndex", "n", "meanMag", "sdMag", "seMag", "ci95LowMag", "ci95HighMag", "pass"]
        with (a.output / "compact.csv").open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
            w.writeheader()
            w.writerows(compact)
    print(json.dumps({
        "classification": summary["classification"],
        "validUniverse": summary["validUniverse"],
        "equivalenceFailureCount": summary.get("equivalenceFailureCount"),
        "precisionFailureCount": summary.get("precisionFailureCount"),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
