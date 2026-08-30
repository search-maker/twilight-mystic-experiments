#!/usr/bin/env python3
"""Solver-free generator/parser contract for low-altitude stellar transport Phase A.

This module deliberately contains no subprocess/uvspec execution path. It may
only build the frozen case ledger, render reviewed libRadtran inputs, and parse
already-supplied deterministic direct-flux output under fail-closed semantics.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

STAGE_ID = "low-altitude-stellar-transport-v1-preexecution"
BASE_PUBLIC_MAIN = "6820eee40186f22cd4df503380c475146c284fda"
INHERITANCE_COMMENT_ID = 5467154006
WAVELENGTH_NM = tuple(range(380, 781))
PHASE_A_ALTITUDE_DEG = (0.25, 0.5, 1.0, 2.0, 3.0, 4.0, 5.0)
PHASE_A_ELEVATION_M = (0.0, 2500.0)
PHASE_A_AOD550 = (0.05, 0.40)
PHASE_B_TRAINING_ALTITUDE_DEG = (
    0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0,
)
SURFACE_ALBEDO = 0.15
MOL_ABS_PARAM = "crs"
EXPECTED_PHASE_A_CASES = 28


class LowAltitudeRefusal(RuntimeError):
    pass


def finite(name: str, value: object) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise LowAltitudeRefusal(f"{name} must be finite")
    return number


def _coord_key(h: float, e: float, a: float) -> str:
    return f"h{float(h):.2f}_e{int(round(float(e))):04d}_a{float(a):.2f}"


def build_phase_a_cases() -> list[dict[str, Any]]:
    cases = []
    ordinal = 0
    for altitude in PHASE_A_ALTITUDE_DEG:
        for elevation in PHASE_A_ELEVATION_M:
            for aod in PHASE_A_AOD550:
                ordinal += 1
                cases.append({
                    "caseOrdinal": ordinal,
                    "caseId": _coord_key(altitude, elevation, aod),
                    "targetGeometricAltitudeDeg": float(altitude),
                    "sourceZenithAngleDeg": 90.0 - float(altitude),
                    "observerElevationM": float(elevation),
                    "aod550": float(aod),
                    "seamControl": math.isclose(float(altitude), 5.0, abs_tol=0.0),
                })
    validate_case_universe(cases)
    return cases


def validate_case_universe(cases: list[dict[str, Any]]) -> None:
    if len(cases) != EXPECTED_PHASE_A_CASES:
        raise LowAltitudeRefusal(f"expected {EXPECTED_PHASE_A_CASES} Phase-A cases")
    ids = [row["caseId"] for row in cases]
    if len(set(ids)) != len(ids):
        raise LowAltitudeRefusal("Phase-A case IDs are not unique")
    altitudes = tuple(sorted({float(row["targetGeometricAltitudeDeg"]) for row in cases}))
    elevations = tuple(sorted({float(row["observerElevationM"]) for row in cases}))
    aods = tuple(sorted({float(row["aod550"]) for row in cases}))
    if altitudes != PHASE_A_ALTITUDE_DEG or elevations != PHASE_A_ELEVATION_M or aods != PHASE_A_AOD550:
        raise LowAltitudeRefusal("Phase-A coordinate freeze drift")
    if any(float(row["targetGeometricAltitudeDeg"]) <= 0.0 for row in cases):
        raise LowAltitudeRefusal("exact/below horizon is forbidden in v1")
    seam = [row for row in cases if row["seamControl"]]
    if len(seam) != 4 or any(float(row["targetGeometricAltitudeDeg"]) != 5.0 for row in seam):
        raise LowAltitudeRefusal("exact 5-degree seam/control count drift")


def case_ledger() -> dict[str, Any]:
    cases = build_phase_a_cases()
    payload = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "basePublicMain": BASE_PUBLIC_MAIN,
        "inheritanceIssue60CommentId": INHERITANCE_COMMENT_ID,
        "scientificExecutionAuthorized": False,
        "solverExecutionAuthorized": False,
        "protectedResultsOpened": False,
        "targetAltitudeBasis": "topocentric-vacuum-geometric",
        "refractionAppliedInRadiativeTransfer": False,
        "wavelengthNm": [WAVELENGTH_NM[0], WAVELENGTH_NM[-1], 1],
        "phaseACases": cases,
        "phaseBTrainingAltitudeUniverseDeg": list(PHASE_B_TRAINING_ALTITUDE_DEG),
        "failureSemantics": {
            "zeroTransmission": "NUMERICALLY_UNRESOLVED",
            "negativeTransmission": "NUMERICALLY_UNRESOLVED",
            "nonfiniteTransmission": "NUMERICALLY_UNRESOLVED",
            "epsilonSubstitutionAllowed": False,
            "sameIdentityRetryAllowed": False,
        },
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload["caseLedgerSha256"] = hashlib.sha256(canonical).hexdigest()
    return payload


def atmosphere_levels_descending(path: Path) -> list[float]:
    levels: list[float] = []
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            raise LowAltitudeRefusal(f"malformed atmosphere row: {raw!r}")
        levels.append(finite("atmosphere altitude", parts[0]))
    if len(levels) < 2 or any(levels[i] <= levels[i + 1] for i in range(len(levels) - 1)):
        raise LowAltitudeRefusal("atmosphere levels must be strictly descending")
    return levels


def elevated_site_grid_ascending(atmosphere_file: Path, observer_elevation_m: float) -> list[float]:
    elevation = finite("observerElevationM", observer_elevation_m)
    if not PHASE_A_ELEVATION_M[0] <= elevation <= PHASE_A_ELEVATION_M[-1]:
        raise LowAltitudeRefusal("observer elevation outside frozen Phase-A endpoint domain")
    site_km = elevation / 1000.0
    levels = atmosphere_levels_descending(atmosphere_file)
    if not levels[-1] <= site_km < levels[0]:
        raise LowAltitudeRefusal("site elevation outside atmosphere grid")
    grid = [site_km, *sorted(z for z in levels if z > site_km)]
    if len(grid) < 2 or any(grid[i] >= grid[i + 1] for i in range(len(grid) - 1)):
        raise LowAltitudeRefusal("atm_z_grid must be strictly ascending")
    return grid


def render_uvspec_input(*, data_dir: Path, atmosphere_file: Path, wavelength_grid_file: Path,
                        target_altitude_deg: float, observer_elevation_m: float, aod550: float) -> str:
    altitude = finite("targetGeometricAltitudeDeg", target_altitude_deg)
    elevation = finite("observerElevationM", observer_elevation_m)
    aod = finite("aod550", aod550)
    if altitude not in PHASE_A_ALTITUDE_DEG:
        raise LowAltitudeRefusal("renderer is restricted to frozen Phase-A altitude candidates")
    if elevation not in PHASE_A_ELEVATION_M:
        raise LowAltitudeRefusal("renderer is restricted to frozen Phase-A elevation endpoints")
    if aod not in PHASE_A_AOD550:
        raise LowAltitudeRefusal("renderer is restricted to frozen Phase-A AOD endpoints")
    if not altitude > 0.0:
        raise LowAltitudeRefusal("target must be above geometric horizon")
    grid = elevated_site_grid_ascending(atmosphere_file, elevation)
    lines = [
        f"data_files_path {Path(data_dir)}",
        f"atmosphere_file {Path(atmosphere_file)}",
        "source solar",
        f"mol_abs_param {MOL_ABS_PARAM}",
        f"wavelength_grid_file {Path(wavelength_grid_file)}",
        f"wavelength {WAVELENGTH_NM[0]} {WAVELENGTH_NM[-1]}",
        f"sza {90.0 - altitude:.8f}",
        f"atm_z_grid {' '.join(f'{z:.6f}' for z in grid)}",
        "zout 0.000000",
        f"albedo {SURFACE_ALBEDO:.8f}",
        "aerosol_default",
        f"aerosol_set_tau_at_wvl 550 {aod:.8f}",
        "rte_solver sdisort",
        "sdisort nscat 1",
        "output_quantity transmittance",
        "output_user lambda edir",
        "quiet",
    ]
    text = "\n".join(lines) + "\n"
    lower = text.lower()
    for forbidden in (
        "rte_solver mystic", "mc_", "aerosol_species_file", "angstrom",
        "nrefrac", "refraction", "altitude ",
    ):
        if forbidden in lower:
            raise LowAltitudeRefusal(f"forbidden directive emitted: {forbidden}")
    if text.count("aerosol_default") != 1 or text.count("aerosol_set_tau_at_wvl") != 1:
        raise LowAltitudeRefusal("aerosol directive surface drift")
    if text.count("rte_solver sdisort") != 1 or text.count("sdisort nscat 1") != 1:
        raise LowAltitudeRefusal("pseudo-spherical deterministic solver surface drift")
    return text


def parse_direct_transmission(stdout_text: str, *, target_altitude_deg: float) -> dict[str, Any]:
    altitude = finite("targetGeometricAltitudeDeg", target_altitude_deg)
    if altitude not in PHASE_A_ALTITUDE_DEG or not altitude > 0.0:
        raise LowAltitudeRefusal("parser altitude outside frozen above-horizon Phase-A universe")
    mu0 = math.sin(math.radians(altitude))
    if not math.isfinite(mu0) or not mu0 > 0.0:
        raise LowAltitudeRefusal("mu0 must be finite and strictly positive")
    wavelengths: list[int] = []
    transmission: list[float] = []
    for raw in stdout_text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            raise LowAltitudeRefusal(f"unexpected uvspec output: {raw!r}")
        wavelength = finite("wavelength", parts[0])
        edir = finite("edir", parts[1])
        ray_t = edir / mu0
        if abs(wavelength - round(wavelength)) > 1e-9:
            raise LowAltitudeRefusal("non-integral wavelength in exact 1-nm output")
        if not math.isfinite(ray_t) or not 0.0 < ray_t <= 1.000001:
            raise LowAltitudeRefusal(f"NUMERICALLY_UNRESOLVED direct transmission at {wavelength} nm")
        wavelengths.append(int(round(wavelength)))
        transmission.append(min(1.0, ray_t))
    if wavelengths != list(WAVELENGTH_NM):
        raise LowAltitudeRefusal("uvspec output grid is not exact 380..780 nm / 1 nm")
    if any(not math.isfinite(value) or not 0.0 < value <= 1.0 for value in transmission):
        raise LowAltitudeRefusal("NUMERICALLY_UNRESOLVED direct transmission spectrum")
    return {
        "wavelengthNm": wavelengths,
        "lineOfSightDirectTransmission": transmission,
        "directOpticalDepth": [-math.log(value) for value in transmission],
        "targetGeometricAltitudeDeg": altitude,
        "sourceZenithAngleDeg": 90.0 - altitude,
        "mu0": mu0,
        "positiveEpsilonSubstitutionUsed": False,
    }


def classify_numerical_floor(case_status: dict[str, str]) -> dict[str, Any]:
    expected_ids = {row["caseId"] for row in build_phase_a_cases()}
    if set(case_status) != expected_ids:
        raise LowAltitudeRefusal("Phase-A status universe incomplete or drifted")
    pass_by_altitude: dict[float, bool] = {}
    for altitude in PHASE_A_ALTITUDE_DEG:
        rows = [row for row in build_phase_a_cases() if row["targetGeometricAltitudeDeg"] == altitude]
        statuses = [case_status[row["caseId"]] for row in rows]
        unknown = [status for status in statuses if status not in {"PASS", "NUMERICALLY_UNRESOLVED"}]
        if unknown:
            raise LowAltitudeRefusal(f"unknown Phase-A status: {unknown[0]}")
        pass_by_altitude[altitude] = all(status == "PASS" for status in statuses)
    seen_pass = False
    for altitude in PHASE_A_ALTITUDE_DEG:
        passes = pass_by_altitude[altitude]
        if passes:
            seen_pass = True
        elif seen_pass:
            return {
                "status": "BLOCKED_NON_MONOTONE",
                "minimumNumericallyRepresentableAltitudeDeg": None,
                "passByAltitude": pass_by_altitude,
            }
    passing = [altitude for altitude in PHASE_A_ALTITUDE_DEG if pass_by_altitude[altitude]]
    if not passing:
        return {
            "status": "NO_SUPPORTED_CANDIDATE",
            "minimumNumericallyRepresentableAltitudeDeg": None,
            "passByAltitude": pass_by_altitude,
        }
    return {
        "status": "CONTIGUOUS_SUFFIX_PASS",
        "minimumNumericallyRepresentableAltitudeDeg": min(passing),
        "passByAltitude": pass_by_altitude,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--emit-ledger", action="store_true")
    args = parser.parse_args()
    if not args.emit_ledger:
        parser.error("review-only CLI requires --emit-ledger; no solver execution action exists")
    print(json.dumps(case_ledger(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
