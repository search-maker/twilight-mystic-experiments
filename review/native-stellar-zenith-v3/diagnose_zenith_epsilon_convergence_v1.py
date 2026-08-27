#!/usr/bin/env python3
"""Training-only near-zenith numerical diagnostic for native stellar transport.

The pinned SDISORT runtime returns code 0 but no spectrum when its internal
``umu0`` rounds to exactly 1.0.  Exact SZA=0 is already proven unsupported, and
a separate v3.1 recovery proved SZA=0.001 deg is also rejected.  This diagnostic
therefore maps the numerical transition with a frozen set of strictly positive
source zenith angles at four atmosphere/AOD corners.

Crucially, a solver endpoint refusal is *data*, not a reason to abort the
campaign: every case is executed once, raw input/stdout/stderr are retained,
and each case is classified usable/rejected.  Spectral and Johnson-V
convergence is computed only among usable cases, relative to the smallest
usable SZA at that atmosphere corner.

No protected holdout coordinate is opened; no model fit, acceptance gate,
canonical epsilon, production activation, empirical real-sky claim, or human
first-seeing claim is authorized by this script.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import subprocess
from pathlib import Path
from typing import Any, Callable

HERE = Path(__file__).resolve().parent
NATIVE_PATH = HERE / "native_stellar_zenith_v3.py"

# Broad convergence points plus a tight bracket around the float32-like
# umu0->1 transition suggested by the exact failure evidence.  The sequence is
# fixed before opening these diagnostic results and is strictly decreasing.
SZA_EPSILON_DEG = (
    1.0,
    0.5,
    0.1,
    0.05,
    0.03,
    0.025,
    0.0225,
    0.021,
    0.0205,
    0.0200,
    0.0198,
    0.01975,
    0.0195,
    0.0190,
    0.018,
    0.015,
    0.010,
    0.001,
    0.0001,
)
ATMOSPHERE_CORNERS = (
    (0.0, 0.05),
    (0.0, 0.40),
    (2500.0, 0.05),
    (2500.0, 0.40),
)
REPRESENTATIVE_LIBRARY_NUMBERS = (1, 26, 45)
PROTECTED_HOLDOUT_ALTITUDES = (80.9375, 83.4375, 85.9375, 88.4375)
STAGE_ID = "native-stellar-zenith-v3-epsilon-convergence-v1"
EXACT_ZERO_DIAGNOSTIC_RUN_ID = 33034345605
FAILED_V31_RECOVERY_RUN_ID = 33035467761
KNOWN_ENDPOINT_STDERR = "Error,  Does not work for umu0=1.0"
EXPECTED_CASE_COUNT = len(SZA_EPSILON_DEG) * len(ATMOSPHERE_CORNERS)


class EpsilonDiagnosticRefusal(RuntimeError):
    pass


def load_native():
    spec = importlib.util.spec_from_file_location("native_stellar_zenith_v3_epsdiag", NATIVE_PATH)
    if spec is None or spec.loader is None:
        raise EpsilonDiagnosticRefusal("cannot load frozen native stellar zenith v3 module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def cases() -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    for elevation_m, aod550 in ATMOSPHERE_CORNERS:
        for sza_deg in SZA_EPSILON_DEG:
            rows.append({
                "sourceZenithAngleDeg": float(sza_deg),
                "targetAltitudeDeg": float(90.0 - sza_deg),
                "observerElevationM": float(elevation_m),
                "aod550": float(aod550),
            })
    return rows


def validate_case_universe() -> None:
    rows = cases()
    if len(rows) != EXPECTED_CASE_COUNT or EXPECTED_CASE_COUNT != 76:
        raise EpsilonDiagnosticRefusal(f"expected 76 diagnostic cases, got {len(rows)}")
    if any(row["sourceZenithAngleDeg"] <= 0 for row in rows):
        raise EpsilonDiagnosticRefusal("exact SZA=0 is forbidden in epsilon diagnostic")
    if not all(SZA_EPSILON_DEG[i] > SZA_EPSILON_DEG[i + 1] for i in range(len(SZA_EPSILON_DEG) - 1)):
        raise EpsilonDiagnosticRefusal("epsilon sequence must decrease strictly toward zenith")
    if SZA_EPSILON_DEG[-1] != 0.0001:
        raise EpsilonDiagnosticRefusal("smallest epsilon drift")
    if 0.0200 not in SZA_EPSILON_DEG or 0.01975 not in SZA_EPSILON_DEG:
        raise EpsilonDiagnosticRefusal("near-transition bracket drift")
    if any(any(abs(row["targetAltitudeDeg"] - h) < 1e-12 for h in PROTECTED_HOLDOUT_ALTITUDES) for row in rows):
        raise EpsilonDiagnosticRefusal("diagnostic overlaps protected holdout altitude")
    if len({(r["sourceZenithAngleDeg"], r["observerElevationM"], r["aod550"]) for r in rows}) != EXPECTED_CASE_COUNT:
        raise EpsilonDiagnosticRefusal("diagnostic coordinate duplication")


def _load_photometry(root: Path, sed_bundle_path: Path, johnson_v_path: Path):
    native = load_native()
    if native.sha256_file(sed_bundle_path) != native.SOURCE_SED_SHA256:
        raise EpsilonDiagnosticRefusal("frozen Pickles SED SHA-256 drift")
    if native.sha256_file(johnson_v_path) != native.SOURCE_JOHNSON_V_SHA256:
        raise EpsilonDiagnosticRefusal("frozen Johnson-V SHA-256 drift")
    phot = native._load_v1_photometry(root)
    _, wavelength_nm, band_response, representatives = phot.load_bound_photometric_assets(
        sed_bundle_path=sed_bundle_path,
        johnson_v_path=johnson_v_path,
    )
    reps = [row for row in representatives if int(row["libraryNumber"]) in REPRESENTATIVE_LIBRARY_NUMBERS]
    if [int(row["libraryNumber"]) for row in reps] != list(REPRESENTATIVE_LIBRARY_NUMBERS):
        raise EpsilonDiagnosticRefusal("representative Pickles identity drift")
    return phot, wavelength_nm, band_response, reps


def _structural_wavelengths(stdout_text: str) -> list[float]:
    wavelengths: list[float] = []
    for raw in stdout_text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        try:
            wavelengths.append(float(parts[0]))
        except (IndexError, ValueError):
            return []
    return wavelengths


def classify_solver_output(*, native, stdout_text: str, stderr_text: str,
                           return_code: int, target_altitude_deg: float) -> dict[str, Any]:
    """Classify one solver call without aborting on the known zenith endpoint."""
    wavelengths = _structural_wavelengths(stdout_text)
    base = {
        "solverReturnCode": int(return_code),
        "stdoutByteCount": len(stdout_text.encode("utf-8")),
        "stderrByteCount": len(stderr_text.encode("utf-8")),
        "dataRowCount": len(wavelengths),
        "firstWavelengthNm": wavelengths[0] if wavelengths else None,
        "lastWavelengthNm": wavelengths[-1] if wavelengths else None,
        "stderrTail": stderr_text[-2000:],
        "knownUmu0EqualsOneRefusal": KNOWN_ENDPOINT_STDERR in stderr_text,
    }
    if return_code != 0:
        return {**base, "solverUsable": False, "failureKind": "NONZERO_RETURN_CODE"}
    try:
        parsed = native.parse_direct_transmission(stdout_text, target_altitude_deg=target_altitude_deg)
    except Exception as exc:
        return {
            **base,
            "solverUsable": False,
            "failureKind": "STRICT_SPECTRUM_PARSE_REFUSAL",
            "failure": str(exc),
        }
    return {
        **base,
        "solverUsable": True,
        "failureKind": None,
        "wavelengthNm": parsed["wavelengthNm"],
        "lineOfSightDirectTransmission": parsed["lineOfSightDirectTransmission"],
        "directOpticalDepth": parsed["directOpticalDepth"],
        "mu0": parsed["mu0"],
    }


def run_case(*, native, uvspec: Path, data_dir: Path, atmosphere_file: Path,
             wavelength_grid_file: Path, row: dict[str, float], raw_dir: Path,
             process_runner: Callable[..., Any] = subprocess.run) -> dict[str, Any]:
    input_text = native.render_uvspec_input(
        data_dir=data_dir,
        atmosphere_file=atmosphere_file,
        wavelength_grid_file=wavelength_grid_file,
        target_altitude_deg=row["targetAltitudeDeg"],
        observer_elevation_m=row["observerElevationM"],
        aod550=row["aod550"],
    )
    expected_sza = f"sza {row['sourceZenithAngleDeg']:.8f}\n"
    if expected_sza not in input_text:
        raise EpsilonDiagnosticRefusal(f"renderer SZA mismatch for {row}: expected {expected_sza.strip()}")
    if "sza 0.00000000\n" in input_text:
        raise EpsilonDiagnosticRefusal("exact SZA=0 accidentally rendered")
    completed = process_runner(
        [str(uvspec)], input=input_text, text=True, capture_output=True,
        check=False, timeout=180,
    )
    key = f"sza{row['sourceZenithAngleDeg']:.5g}-e{int(row['observerElevationM'])}-a{row['aod550']:.2f}"
    (raw_dir / f"{key}.inp").write_text(input_text, encoding="utf-8")
    (raw_dir / f"{key}.stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (raw_dir / f"{key}.stderr.txt").write_text(completed.stderr, encoding="utf-8")
    classified = classify_solver_output(
        native=native,
        stdout_text=completed.stdout,
        stderr_text=completed.stderr,
        return_code=completed.returncode,
        target_altitude_deg=row["targetAltitudeDeg"],
    )
    result = {
        **row,
        **classified,
        "inputSha256": sha256_text(input_text),
        "stdoutSha256": sha256_text(completed.stdout),
        "stderrSha256": sha256_text(completed.stderr),
    }
    (raw_dir / f"{key}.json").write_text(
        json.dumps({k: v for k, v in result.items() if k not in {"wavelengthNm", "lineOfSightDirectTransmission", "directOpticalDepth"}},
                   indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return result


def _usability_monotonic(rows: list[dict[str, Any]]) -> bool:
    """As SZA decreases, usable may switch True->False at most once."""
    seen_rejected = False
    for row in rows:
        if row["solverUsable"]:
            if seen_rejected:
                return False
        else:
            seen_rejected = True
    return True


def summarize_convergence(*, root: Path, results: list[dict[str, Any]],
                          sed_bundle_path: Path, johnson_v_path: Path) -> dict[str, Any]:
    phot, wavelength_nm, band_response, reps = _load_photometry(root, sed_bundle_path, johnson_v_path)
    groups: list[dict[str, Any]] = []
    usable_by_epsilon: dict[float, list[bool]] = {float(e): [] for e in SZA_EPSILON_DEG}
    total_usable = 0
    total_rejected = 0

    for elevation_m, aod550 in ATMOSPHERE_CORNERS:
        rows = [r for r in results if r["observerElevationM"] == elevation_m and r["aod550"] == aod550]
        rows.sort(key=lambda r: r["sourceZenithAngleDeg"], reverse=True)
        if [r["sourceZenithAngleDeg"] for r in rows] != list(SZA_EPSILON_DEG):
            raise EpsilonDiagnosticRefusal("result epsilon sequence incomplete")
        for row in rows:
            usable_by_epsilon[float(row["sourceZenithAngleDeg"])].append(bool(row["solverUsable"]))
        usable = [r for r in rows if r["solverUsable"]]
        rejected = [r for r in rows if not r["solverUsable"]]
        if not usable:
            raise EpsilonDiagnosticRefusal(f"no usable near-zenith case at atmosphere corner {(elevation_m, aod550)}")
        if any(r["dataRowCount"] != 401 for r in usable):
            raise EpsilonDiagnosticRefusal("usable solver case lacks exact 401-node spectrum")
        reference = usable[-1]  # smallest SZA that this corner's solver accepts
        comparisons: list[dict[str, Any]] = []
        for row in usable:
            dtau = [float(a) - float(b) for a, b in zip(row["directOpticalDepth"], reference["directOpticalDepth"])]
            dtrans = [float(a) - float(b) for a, b in zip(row["lineOfSightDirectTransmission"], reference["lineOfSightDirectTransmission"])]
            sed_rows = []
            for sed in reps:
                flux = [float(x) for x in sed["fluxRelative"]]
                av = phot.band_extinction_mag(
                    wavelength_nm=wavelength_nm,
                    flux_relative=flux,
                    band_response=band_response,
                    transmission=row["lineOfSightDirectTransmission"],
                )
                ref_av = phot.band_extinction_mag(
                    wavelength_nm=wavelength_nm,
                    flux_relative=flux,
                    band_response=band_response,
                    transmission=reference["lineOfSightDirectTransmission"],
                )
                sed_rows.append({
                    "libraryNumber": int(sed["libraryNumber"]),
                    "avMag": av,
                    "referenceAvMag": ref_av,
                    "deltaAvMagVsSmallestUsableSza": av - ref_av,
                })
            comparisons.append({
                "sourceZenithAngleDeg": row["sourceZenithAngleDeg"],
                "targetAltitudeDeg": row["targetAltitudeDeg"],
                "mu0": row["mu0"],
                "dataRowCount": row["dataRowCount"],
                "maxAbsDeltaTauVsSmallestUsableSza": max(abs(x) for x in dtau),
                "rmsDeltaTauVsSmallestUsableSza": math.sqrt(sum(x * x for x in dtau) / len(dtau)),
                "maxAbsDeltaTransmissionVsSmallestUsableSza": max(abs(x) for x in dtrans),
                "maxAbsDeltaAvMagVsSmallestUsableSza": max(abs(s["deltaAvMagVsSmallestUsableSza"]) for s in sed_rows),
                "sedComparisons": sed_rows,
                "inputSha256": row["inputSha256"],
                "stdoutSha256": row["stdoutSha256"],
                "stderrSha256": row["stderrSha256"],
            })
        total_usable += len(usable)
        total_rejected += len(rejected)
        groups.append({
            "observerElevationM": elevation_m,
            "aod550": aod550,
            "smallestSolverUsableSourceZenithAngleDeg": reference["sourceZenithAngleDeg"],
            "largestSolverRejectedSourceZenithAngleDeg": max((r["sourceZenithAngleDeg"] for r in rejected), default=None),
            "solverUsabilityMonotonicTowardZenith": _usability_monotonic(rows),
            "usableCaseCount": len(usable),
            "rejectedCaseCount": len(rejected),
            "rejectedCases": [
                {
                    "sourceZenithAngleDeg": r["sourceZenithAngleDeg"],
                    "targetAltitudeDeg": r["targetAltitudeDeg"],
                    "failureKind": r["failureKind"],
                    "knownUmu0EqualsOneRefusal": r["knownUmu0EqualsOneRefusal"],
                    "dataRowCount": r["dataRowCount"],
                    "stderrTail": r["stderrTail"],
                    "stdoutSha256": r["stdoutSha256"],
                    "stderrSha256": r["stderrSha256"],
                }
                for r in rejected
            ],
            "comparisons": comparisons,
        })

    all_corner_valid_eps = [
        epsilon for epsilon in SZA_EPSILON_DEG
        if len(usable_by_epsilon[float(epsilon)]) == len(ATMOSPHERE_CORNERS)
        and all(usable_by_epsilon[float(epsilon)])
    ]
    any_corner_rejected_eps = [
        epsilon for epsilon in SZA_EPSILON_DEG
        if len(usable_by_epsilon[float(epsilon)]) == len(ATMOSPHERE_CORNERS)
        and not all(usable_by_epsilon[float(epsilon)])
    ]
    if not all_corner_valid_eps:
        raise EpsilonDiagnosticRefusal("no SZA is solver-usable across all atmosphere corners")
    smallest_all_corner_valid = min(all_corner_valid_eps)
    largest_any_corner_rejected = max(any_corner_rejected_eps) if any_corner_rejected_eps else None
    monotonic_all = all(group["solverUsabilityMonotonicTowardZenith"] for group in groups)

    return {
        "schemaVersion": 2,
        "stageId": STAGE_ID,
        "status": "TRAINING_ONLY_NUMERICAL_CONVERGENCE_DIAGNOSTIC_COMPLETE",
        "exactSzaZeroKnownUnsupportedByPinnedSdisort": True,
        "exactZeroDiagnosticRunId": EXACT_ZERO_DIAGNOSTIC_RUN_ID,
        "sza0p001RecoveryFailureRunId": FAILED_V31_RECOVERY_RUN_ID,
        "knownEndpointStderr": KNOWN_ENDPOINT_STDERR,
        "sourceZenithAngleDeg": list(SZA_EPSILON_DEG),
        "atmosphereCorners": [
            {"observerElevationM": e, "aod550": a} for e, a in ATMOSPHERE_CORNERS
        ],
        "solverInvocationCount": len(results),
        "solverUsableCaseCount": total_usable,
        "solverRejectedCaseCount": total_rejected,
        "usableWavelengthNodeCountPerCase": 401,
        "representativeLibraryNumbers": list(REPRESENTATIVE_LIBRARY_NUMBERS),
        "smallestSourceZenithAngleValidAcrossAllCornersDeg": smallest_all_corner_valid,
        "largestSourceZenithAngleRejectedByAnyCornerDeg": largest_any_corner_rejected,
        "solverUsabilityMonotonicTowardZenithAcrossAllCorners": monotonic_all,
        "groups": groups,
        "claimBoundary": {
            "trainingOnlyNumericalDiagnostic": True,
            "protectedHoldoutOpened": False,
            "modelFitPerformed": False,
            "canonicalEpsilonSelected": False,
            "acceptanceGateEvaluated": False,
            "productionAuthorized": False,
            "empiricalRealSkyValidated": False,
            "humanFirstSeeingValidated": False,
        },
    }


def execute(*, root: Path, uvspec: Path, data_dir: Path, atmosphere_file: Path,
            wavelength_grid_file: Path, sed_bundle_path: Path, johnson_v_path: Path,
            output_dir: Path, allow_execution: bool) -> dict[str, Any]:
    if allow_execution is not True:
        raise EpsilonDiagnosticRefusal("diagnostic execution requires --allow-execution")
    validate_case_universe()
    native = load_native()
    native.validate_frozen_case_universe()
    if native.sha256_file(uvspec) != native.UVSPEC_SHA256:
        raise EpsilonDiagnosticRefusal("uvspec SHA-256 drift")
    if native.sha256_file(atmosphere_file) != native.AFGLUS_SHA256:
        raise EpsilonDiagnosticRefusal("AFGLUS SHA-256 drift")
    grid_values = [int(line) for line in Path(wavelength_grid_file).read_text().splitlines() if line.strip()]
    if grid_values != list(native.WAVELENGTH_NM):
        raise EpsilonDiagnosticRefusal("wavelength grid drift")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)
    raw_dir = output_dir / "raw"
    raw_dir.mkdir()
    results: list[dict[str, Any]] = []
    for row in cases():
        results.append(run_case(
            native=native, uvspec=uvspec, data_dir=data_dir,
            atmosphere_file=atmosphere_file, wavelength_grid_file=wavelength_grid_file,
            row=row, raw_dir=raw_dir,
        ))
    summary = summarize_convergence(
        root=root, results=results,
        sed_bundle_path=sed_bundle_path, johnson_v_path=johnson_v_path,
    )
    (output_dir / "epsilon-convergence-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--allow-execution", action="store_true")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--uvspec", type=Path)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--atmosphere-file", type=Path)
    parser.add_argument("--wavelength-grid-file", type=Path)
    parser.add_argument("--sed-bundle", type=Path)
    parser.add_argument("--johnson-v", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if not args.execute:
        validate_case_universe()
        print(json.dumps({
            "status": "REVIEW_ONLY_NO_SOLVER_EXECUTION",
            "stageId": STAGE_ID,
            "solverInvocationCountIfAuthorized": EXPECTED_CASE_COUNT,
            "sourceZenithAngleDeg": list(SZA_EPSILON_DEG),
            "protectedHoldoutOpened": False,
            "canonicalEpsilonSelected": False,
            "acceptanceGateEvaluated": False,
        }, sort_keys=True))
        return 0
    required = [args.uvspec, args.data_dir, args.atmosphere_file, args.wavelength_grid_file,
                args.sed_bundle, args.johnson_v, args.output_dir]
    if any(x is None for x in required):
        raise EpsilonDiagnosticRefusal("execution requires all explicit paths")
    summary = execute(
        root=args.root, uvspec=args.uvspec, data_dir=args.data_dir,
        atmosphere_file=args.atmosphere_file, wavelength_grid_file=args.wavelength_grid_file,
        sed_bundle_path=args.sed_bundle, johnson_v_path=args.johnson_v,
        output_dir=args.output_dir, allow_execution=args.allow_execution,
    )
    print(json.dumps({
        "status": summary["status"],
        "solverInvocationCount": summary["solverInvocationCount"],
        "solverUsableCaseCount": summary["solverUsableCaseCount"],
        "solverRejectedCaseCount": summary["solverRejectedCaseCount"],
        "smallestSourceZenithAngleValidAcrossAllCornersDeg": summary["smallestSourceZenithAngleValidAcrossAllCornersDeg"],
        "largestSourceZenithAngleRejectedByAnyCornerDeg": summary["largestSourceZenithAngleRejectedByAnyCornerDeg"],
        "protectedHoldoutOpened": summary["claimBoundary"]["protectedHoldoutOpened"],
        "canonicalEpsilonSelected": summary["claimBoundary"]["canonicalEpsilonSelected"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
