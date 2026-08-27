#!/usr/bin/env python3
"""Training-only numerical convergence diagnostic for native stellar zenith v3.

sdisort in the exact pinned libRadtran runtime exits successfully but refuses
umu0=1.0 (SZA=0), producing no stdout. This diagnostic does not change the
scientific model. It evaluates a fixed sequence of strictly positive source
zenith angles approaching zero at four atmosphere/AOD corners, checks the exact
401-node output grid, and reports spectral/direct-optical-depth and Johnson-V
convergence relative to the smallest epsilon.

No protected holdout coordinate is opened; no model fit, acceptance gate, or
canonical epsilon is selected by this script.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import subprocess
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
NATIVE_PATH = HERE / "native_stellar_zenith_v3.py"
SZA_EPSILON_DEG = (1.0, 0.5, 0.1, 0.01, 0.001, 0.0001)
ATMOSPHERE_CORNERS = (
    (0.0, 0.05),
    (0.0, 0.40),
    (2500.0, 0.05),
    (2500.0, 0.40),
)
REPRESENTATIVE_LIBRARY_NUMBERS = (1, 26, 45)
PROTECTED_HOLDOUT_ALTITUDES = (80.9375, 83.4375, 85.9375, 88.4375)
STAGE_ID = "native-stellar-zenith-v3-epsilon-convergence-v1"


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
    rows = []
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
    if len(rows) != 24:
        raise EpsilonDiagnosticRefusal(f"expected 24 diagnostic cases, got {len(rows)}")
    if any(row["sourceZenithAngleDeg"] <= 0 for row in rows):
        raise EpsilonDiagnosticRefusal("exact SZA=0 is forbidden in epsilon diagnostic")
    if SZA_EPSILON_DEG[-1] != 0.0001:
        raise EpsilonDiagnosticRefusal("smallest epsilon drift")
    if any(any(abs(row["targetAltitudeDeg"] - h) < 1e-12 for h in PROTECTED_HOLDOUT_ALTITUDES) for row in rows):
        raise EpsilonDiagnosticRefusal("diagnostic overlaps protected holdout altitude")
    if len({(r["sourceZenithAngleDeg"], r["observerElevationM"], r["aod550"]) for r in rows}) != 24:
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


def run_case(*, native, uvspec: Path, data_dir: Path, atmosphere_file: Path,
             wavelength_grid_file: Path, row: dict[str, float], raw_dir: Path) -> dict[str, Any]:
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
    completed = subprocess.run(
        [str(uvspec)], input=input_text, text=True, capture_output=True,
        check=False, timeout=180,
    )
    key = f"sza{row['sourceZenithAngleDeg']:.4g}-e{int(row['observerElevationM'])}-a{row['aod550']:.2f}"
    (raw_dir / f"{key}.inp").write_text(input_text, encoding="utf-8")
    (raw_dir / f"{key}.stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (raw_dir / f"{key}.stderr.txt").write_text(completed.stderr, encoding="utf-8")
    if completed.returncode != 0:
        raise EpsilonDiagnosticRefusal(f"uvspec failed rc={completed.returncode} for {row}")
    parsed = native.parse_direct_transmission(completed.stdout, target_altitude_deg=row["targetAltitudeDeg"])
    if abs(parsed["sourceZenithAngleDeg"] - row["sourceZenithAngleDeg"]) > 2e-12:
        raise EpsilonDiagnosticRefusal("parsed source zenith angle drift")
    return {
        **row,
        "wavelengthNm": parsed["wavelengthNm"],
        "lineOfSightDirectTransmission": parsed["lineOfSightDirectTransmission"],
        "directOpticalDepth": parsed["directOpticalDepth"],
        "mu0": parsed["mu0"],
        "inputSha256": sha256_text(input_text),
        "stdoutSha256": sha256_text(completed.stdout),
        "stderrSha256": sha256_text(completed.stderr),
        "dataRowCount": len(parsed["wavelengthNm"]),
    }


def summarize_convergence(*, root: Path, results: list[dict[str, Any]],
                          sed_bundle_path: Path, johnson_v_path: Path) -> dict[str, Any]:
    phot, wavelength_nm, band_response, reps = _load_photometry(root, sed_bundle_path, johnson_v_path)
    groups: list[dict[str, Any]] = []
    for elevation_m, aod550 in ATMOSPHERE_CORNERS:
        rows = [r for r in results if r["observerElevationM"] == elevation_m and r["aod550"] == aod550]
        rows.sort(key=lambda r: r["sourceZenithAngleDeg"], reverse=True)
        if [r["sourceZenithAngleDeg"] for r in rows] != list(SZA_EPSILON_DEG):
            raise EpsilonDiagnosticRefusal("result epsilon sequence incomplete")
        reference = rows[-1]
        comparisons = []
        for row in rows:
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
                    "deltaAvMagVsSmallestEpsilon": av - ref_av,
                })
            comparisons.append({
                "sourceZenithAngleDeg": row["sourceZenithAngleDeg"],
                "targetAltitudeDeg": row["targetAltitudeDeg"],
                "mu0": row["mu0"],
                "dataRowCount": row["dataRowCount"],
                "maxAbsDeltaTauVsSmallestEpsilon": max(abs(x) for x in dtau),
                "rmsDeltaTauVsSmallestEpsilon": math.sqrt(sum(x * x for x in dtau) / len(dtau)),
                "maxAbsDeltaTransmissionVsSmallestEpsilon": max(abs(x) for x in dtrans),
                "maxAbsDeltaAvMagVsSmallestEpsilon": max(abs(s["deltaAvMagVsSmallestEpsilon"]) for s in sed_rows),
                "sedComparisons": sed_rows,
                "inputSha256": row["inputSha256"],
                "stdoutSha256": row["stdoutSha256"],
                "stderrSha256": row["stderrSha256"],
            })
        groups.append({
            "observerElevationM": elevation_m,
            "aod550": aod550,
            "referenceSourceZenithAngleDeg": SZA_EPSILON_DEG[-1],
            "comparisons": comparisons,
        })
    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "TRAINING_ONLY_NUMERICAL_CONVERGENCE_DIAGNOSTIC_COMPLETE",
        "exactSzaZeroKnownUnsupportedByPinnedSdisort": True,
        "sourceZenithAngleDeg": list(SZA_EPSILON_DEG),
        "atmosphereCorners": [
            {"observerElevationM": e, "aod550": a} for e, a in ATMOSPHERE_CORNERS
        ],
        "solverInvocationCount": len(results),
        "wavelengthNodeCountPerCase": 401,
        "representativeLibraryNumbers": list(REPRESENTATIVE_LIBRARY_NUMBERS),
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
    results = [
        run_case(
            native=native, uvspec=uvspec, data_dir=data_dir,
            atmosphere_file=atmosphere_file, wavelength_grid_file=wavelength_grid_file,
            row=row, raw_dir=raw_dir,
        )
        for row in cases()
    ]
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
            "solverInvocationCountIfAuthorized": 24,
            "sourceZenithAngleDeg": list(SZA_EPSILON_DEG),
            "protectedHoldoutOpened": False,
            "canonicalEpsilonSelected": False,
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
        "protectedHoldoutOpened": summary["claimBoundary"]["protectedHoldoutOpened"],
        "canonicalEpsilonSelected": summary["claimBoundary"]["canonicalEpsilonSelected"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
