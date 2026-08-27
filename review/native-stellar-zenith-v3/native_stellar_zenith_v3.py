#!/usr/bin/env python3
"""Native MYSTIC-STATE-0081 stellar-transport zenith extension v3.

This module freezes the 80..90 degree extension method and can only invoke
uvspec when execute_campaign(..., allow_execution=True) is called by the
separately gated one-shot workflow. Importing it or running its contract tests
never executes a scientific solver.

Scientific invariants:
- preserve every validated v2 LUT value at <=80 deg exactly;
- add direct-optical-depth training knots at 82.5, 85, 87.5, 90 deg;
- retain the existing csc(altitude) interpolation, linear elevation and AOD;
- validate at the preregistered 3/8 point inside every new altitude interval;
- use fresh 3/8 elevation/AOD holdout coordinates;
- use the existing frozen Pickles + Johnson-V photometry and templates 1/26/45;
- keep the original 0.025 mag max / 0.010 mag RMS acceptance gates, applied
  both globally and separately to every new altitude interval;
- no MYSTIC, no random numbers, no post-result retuning.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import subprocess
from pathlib import Path
from typing import Any, Iterable

STAGE_ID = "native-stellar-zenith-v3"
MYSTIC_STATE = "MYSTIC-STATE-0081"
SOURCE_ASSET_COMMIT = "4b71445139e24236f12952ab41c791bd07a9f7db"
SOURCE_RUNTIME_SHA256 = "21eeb51fcc5287ab3bb8cb59cfe0bb0073f34e9ca1b6cc6df988c6eb5043631f"
SOURCE_SED_SHA256 = "85cbf41c86309b9d54d4765516167165f2d8736bcda8994337ef25d775ea11cb"
SOURCE_JOHNSON_V_SHA256 = "51c357eb4cb3609361759f9750ad13ae13a901970913e3a5d87bb5c45ee2db9a"
SOURCE_PROTOCOL_SHA256 = "aae80c6c958c0d3dabe9e841be50b4fca52e1b5fb717e834d361172bfed00fef"
EXACT_PACKAGE_SPEC = "rubin-libradtran=2.0.6=py312pl5321he9373c2_1"
UVSPEC_SHA256 = "2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3"
UVSPEC_HELP_SHA256 = "868aea5af762d968f6f62c4e1472916d25232ed9cab5be112d753b0823d20548"
AFGLUS_SHA256 = "dab26290ed81c762ed0c607e5dc2d53393c1462a0c3a528bc5e3f5935191cfb5"

WAVELENGTH_NM = tuple(range(380, 781))
OLD_ALTITUDE_KNOTS = (
    5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
    17.5, 20, 22.5, 25, 27.5, 30,
    35, 40, 45, 50, 55, 60, 65, 70, 75, 80,
)
NEW_TRAINING_ALTITUDE_DEG = (82.5, 85.0, 87.5, 90.0)
EXTENDED_ALTITUDE_KNOTS = (*OLD_ALTITUDE_KNOTS, *NEW_TRAINING_ALTITUDE_DEG)
ELEVATION_KNOTS_M = (0.0, 500.0, 1250.0, 2000.0, 2500.0)
AOD_KNOTS = (0.05, 0.10, 0.20, 0.30, 0.40)
VALIDATION_FRACTION = 3.0 / 8.0
VALIDATION_ALTITUDE_DEG = tuple(
    float(EXTENDED_ALTITUDE_KNOTS[i])
    + VALIDATION_FRACTION * (float(EXTENDED_ALTITUDE_KNOTS[i + 1]) - float(EXTENDED_ALTITUDE_KNOTS[i]))
    for i in range(len(OLD_ALTITUDE_KNOTS) - 1, len(EXTENDED_ALTITUDE_KNOTS) - 1)
)
VALIDATION_ELEVATION_M = tuple(
    ELEVATION_KNOTS_M[i] + VALIDATION_FRACTION * (ELEVATION_KNOTS_M[i + 1] - ELEVATION_KNOTS_M[i])
    for i in range(len(ELEVATION_KNOTS_M) - 1)
)
VALIDATION_AOD550 = tuple(
    AOD_KNOTS[i] + VALIDATION_FRACTION * (AOD_KNOTS[i + 1] - AOD_KNOTS[i])
    for i in range(len(AOD_KNOTS) - 1)
)
REPRESENTATIVE_LIBRARY_NUMBERS = (1, 26, 45)
MAX_ABS_ERROR_MAG_LIMIT = 0.025
RMS_ERROR_MAG_LIMIT = 0.010

ATMOSPHERE_NAME = "afglus"
MOL_ABS_PARAM = "crs"
SURFACE_ALBEDO = 0.15


class ZenithV3Refusal(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def finite(name: str, value: object) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ZenithV3Refusal(f"{name} must be finite")
    return number


def atmosphere_levels_descending(path: Path) -> list[float]:
    levels: list[float] = []
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            raise ZenithV3Refusal(f"malformed atmosphere row: {raw!r}")
        levels.append(finite("atmosphere altitude", parts[0]))
    if len(levels) < 2 or any(levels[i] <= levels[i + 1] for i in range(len(levels) - 1)):
        raise ZenithV3Refusal("AFGLUS atmosphere levels must be strictly descending")
    return levels


def elevated_site_grid_ascending(atmosphere_file: Path, observer_elevation_m: float) -> list[float]:
    elevation = finite("observerElevationM", observer_elevation_m)
    if not ELEVATION_KNOTS_M[0] <= elevation <= ELEVATION_KNOTS_M[-1]:
        raise ZenithV3Refusal("observer elevation outside frozen domain")
    site_km = elevation / 1000.0
    levels = atmosphere_levels_descending(atmosphere_file)
    if not levels[-1] <= site_km < levels[0]:
        raise ZenithV3Refusal("site elevation outside AFGLUS grid")
    grid = [site_km, *sorted(z for z in levels if z > site_km)]
    if len(grid) < 2 or any(grid[i] >= grid[i + 1] for i in range(len(grid) - 1)):
        raise ZenithV3Refusal("atm_z_grid must be strictly ascending")
    return grid


def render_uvspec_input(*, data_dir: Path, atmosphere_file: Path, wavelength_grid_file: Path,
                        target_altitude_deg: float, observer_elevation_m: float, aod550: float) -> str:
    altitude = finite("targetAltitudeDeg", target_altitude_deg)
    elevation = finite("observerElevationM", observer_elevation_m)
    aod = finite("aod550", aod550)
    if not 80.0 <= altitude <= 90.0:
        raise ZenithV3Refusal("zenith extension renderer is restricted to 80..90 deg")
    if not ELEVATION_KNOTS_M[0] <= elevation <= ELEVATION_KNOTS_M[-1]:
        raise ZenithV3Refusal("observer elevation outside frozen domain")
    if not AOD_KNOTS[0] <= aod <= AOD_KNOTS[-1]:
        raise ZenithV3Refusal("AOD550 outside frozen domain")
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
    for forbidden in ("rte_solver mystic", "mc_", "aerosol_species_file", "angstrom"):
        if forbidden in lower:
            raise ZenithV3Refusal(f"forbidden directive emitted: {forbidden}")
    if text.count("aerosol_default") != 1 or text.count("aerosol_set_tau_at_wvl") != 1:
        raise ZenithV3Refusal("native aerosol directive surface drift")
    return text


def parse_direct_transmission(stdout_text: str, *, target_altitude_deg: float) -> dict[str, Any]:
    altitude = finite("targetAltitudeDeg", target_altitude_deg)
    mu0 = math.sin(math.radians(altitude))
    if not mu0 > 0:
        raise ZenithV3Refusal("target must be above geometric horizon")
    wavelengths: list[int] = []
    transmission: list[float] = []
    for raw in stdout_text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            raise ZenithV3Refusal(f"unexpected uvspec output: {raw!r}")
        wavelength = finite("wavelength", parts[0])
        edir = finite("edir", parts[1])
        ray_t = edir / mu0
        if abs(wavelength - round(wavelength)) > 1e-9:
            raise ZenithV3Refusal("non-integral wavelength in exact 1-nm output")
        if edir < -1e-12 or ray_t < -1e-10 or ray_t > 1.000001:
            raise ZenithV3Refusal(f"invalid direct transmission at {wavelength} nm: {ray_t}")
        wavelengths.append(int(round(wavelength)))
        transmission.append(min(1.0, max(0.0, ray_t)))
    if wavelengths != list(WAVELENGTH_NM):
        raise ZenithV3Refusal("uvspec output grid is not exact 380..780 nm / 1 nm")
    if any(not 0 < value <= 1 for value in transmission):
        raise ZenithV3Refusal("direct transmission must be in (0,1]")
    return {
        "wavelengthNm": wavelengths,
        "lineOfSightDirectTransmission": transmission,
        "directOpticalDepth": [-math.log(value) for value in transmission],
        "targetAltitudeDeg": altitude,
        "sourceZenithAngleDeg": 90.0 - altitude,
        "mu0": mu0,
    }


def _coord_key(h: float, e: float, a: float) -> tuple[float, float, float]:
    return (round(float(h), 9), round(float(e), 9), round(float(a), 9))


def build_training_cases() -> list[dict[str, float]]:
    return [
        {"targetAltitudeDeg": float(h), "observerElevationM": float(e), "aod550": float(a)}
        for h in NEW_TRAINING_ALTITUDE_DEG for e in ELEVATION_KNOTS_M for a in AOD_KNOTS
    ]


def build_validation_cases() -> list[dict[str, float]]:
    return [
        {"targetAltitudeDeg": float(h), "observerElevationM": float(e), "aod550": float(a)}
        for h in VALIDATION_ALTITUDE_DEG for e in VALIDATION_ELEVATION_M for a in VALIDATION_AOD550
    ]


def validate_frozen_case_universe() -> None:
    training = build_training_cases()
    validation = build_validation_cases()
    if len(training) != 100:
        raise ZenithV3Refusal(f"expected 100 new training spectra, got {len(training)}")
    if len(validation) != 64:
        raise ZenithV3Refusal(f"expected 64 fresh validation spectra, got {len(validation)}")
    train_keys = {_coord_key(r["targetAltitudeDeg"], r["observerElevationM"], r["aod550"]) for r in training}
    val_keys = {_coord_key(r["targetAltitudeDeg"], r["observerElevationM"], r["aod550"]) for r in validation}
    if len(train_keys) != 100 or len(val_keys) != 64 or train_keys & val_keys:
        raise ZenithV3Refusal("training/validation coordinate universe is not unique and disjoint")
    if VALIDATION_ALTITUDE_DEG != (80.9375, 83.4375, 85.9375, 88.4375):
        raise ZenithV3Refusal("validation altitude freeze drift")


def validate_source_runtime(runtime: dict[str, Any]) -> None:
    if runtime.get("schemaVersion") != 1 or runtime.get("quantity") != "level-b-stellar-direct-optical-depth-lut":
        raise ZenithV3Refusal("source v2 runtime schema/quantity drift")
    axes = runtime.get("axes") or {}
    if tuple(float(x) for x in axes.get("targetAltitudeDeg", ())) != tuple(float(x) for x in OLD_ALTITUDE_KNOTS):
        raise ZenithV3Refusal("source v2 altitude axis drift")
    if tuple(float(x) for x in axes.get("observerElevationM", ())) != ELEVATION_KNOTS_M:
        raise ZenithV3Refusal("source v2 elevation axis drift")
    if tuple(float(x) for x in axes.get("aod550", ())) != AOD_KNOTS:
        raise ZenithV3Refusal("source v2 AOD axis drift")
    if tuple(int(x) for x in runtime.get("wavelengthNm", ())) != WAVELENGTH_NM:
        raise ZenithV3Refusal("source v2 wavelength grid drift")
    spectra = runtime.get("directOpticalDepth")
    if not isinstance(spectra, list) or len(spectra) != 675:
        raise ZenithV3Refusal("source v2 LUT must contain exactly 675 spectra")
    if any(not isinstance(row, list) or len(row) != 401 for row in spectra):
        raise ZenithV3Refusal("source v2 LUT spectral shape drift")


def build_extended_runtime(source_runtime: dict[str, Any], training_results: dict[tuple[float, float, float], dict[str, Any]]) -> dict[str, Any]:
    validate_source_runtime(source_runtime)
    expected = {_coord_key(r["targetAltitudeDeg"], r["observerElevationM"], r["aod550"]) for r in build_training_cases()}
    if set(training_results) != expected:
        raise ZenithV3Refusal("new training result universe incomplete or drifted")
    old_spectra = source_runtime["directOpticalDepth"]
    new_spectra = [
        training_results[_coord_key(h, e, a)]["directOpticalDepth"]
        for h in NEW_TRAINING_ALTITUDE_DEG for e in ELEVATION_KNOTS_M for a in AOD_KNOTS
    ]
    runtime = dict(source_runtime)
    runtime["axes"] = dict(source_runtime["axes"])
    runtime["axes"]["targetAltitudeDeg"] = list(EXTENDED_ALTITUDE_KNOTS)
    runtime["directOpticalDepth"] = [*old_spectra, *new_spectra]
    runtime["representation"] = {
        **(source_runtime.get("representation") or {}),
        "version": "stellar-transport-v3-zenith-extension",
        "altitudeKnotRule": "v2-unchanged-through-80;2.5deg-80to90",
        "targetAltitudeCoordinate": "cosecant-altitude-1-over-sin-h",
    }
    runtime["provenance"] = {
        **(source_runtime.get("provenance") or {}),
        "zenithExtensionStageId": STAGE_ID,
        "sourceV2RuntimeSha256": SOURCE_RUNTIME_SHA256,
        "sourceV2ProtocolSha256": SOURCE_PROTOCOL_SHA256,
        "oldDomainValuesUnchanged": True,
        "newSolverTrainingSpectrumCount": 100,
        "postResultRetuningPerformed": False,
        "empiricalRealSkyValidated": False,
        "humanFirstSeeingValidated": False,
        "productionAuthorized": False,
    }
    if runtime["directOpticalDepth"][:675] != old_spectra:
        raise ZenithV3Refusal("v2 spectra changed while building extension")
    if len(runtime["directOpticalDepth"]) != 775:
        raise ZenithV3Refusal("extended runtime must contain exactly 775 spectra")
    return runtime


def csc_altitude(altitude_deg: float) -> float:
    mu = math.sin(math.radians(finite("targetAltitudeDeg", altitude_deg)))
    if not mu > 0:
        raise ZenithV3Refusal("target altitude must be above horizon")
    return 1.0 / mu


def bracket(axis: Iterable[float], value: float, *, coordinate=lambda x: x) -> tuple[int, int, float]:
    values = [float(x) for x in axis]
    q = finite("interpolation coordinate", value)
    if q < values[0] or q > values[-1]:
        raise ZenithV3Refusal("interpolation coordinate outside support")
    if q == values[-1]:
        return len(values) - 2, len(values) - 1, 1.0
    lo, hi = 0, len(values) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if values[mid] <= q:
            lo = mid
        else:
            hi = mid
    c_lo, c_hi, c_q = coordinate(values[lo]), coordinate(values[hi]), coordinate(q)
    return lo, hi, (c_q - c_lo) / (c_hi - c_lo)


def _case_index(n_elevation: int, n_aod: int, ai: int, ei: int, oi: int) -> int:
    return ((ai * n_elevation) + ei) * n_aod + oi


def interpolate_optical_depth(runtime: dict[str, Any], *, target_altitude_deg: float,
                              observer_elevation_m: float, aod550: float) -> list[float]:
    axes = runtime["axes"]
    h_axis = [float(x) for x in axes["targetAltitudeDeg"]]
    e_axis = [float(x) for x in axes["observerElevationM"]]
    a_axis = [float(x) for x in axes["aod550"]]
    hb = bracket(h_axis, target_altitude_deg, coordinate=csc_altitude)
    eb = bracket(e_axis, observer_elevation_m)
    ab = bracket(a_axis, aod550)
    spectra = runtime["directOpticalDepth"]
    n_e, n_a = len(e_axis), len(a_axis)
    result = []
    for w in range(401):
        def c(hi: int, ei: int, ai: int) -> float:
            return float(spectra[_case_index(n_e, n_a, hi, ei, ai)][w])
        c000, c001 = c(hb[0], eb[0], ab[0]), c(hb[0], eb[0], ab[1])
        c010, c011 = c(hb[0], eb[1], ab[0]), c(hb[0], eb[1], ab[1])
        c100, c101 = c(hb[1], eb[0], ab[0]), c(hb[1], eb[0], ab[1])
        c110, c111 = c(hb[1], eb[1], ab[0]), c(hb[1], eb[1], ab[1])
        low_e = (c000 + (c001 - c000) * ab[2]) + ((c010 + (c011 - c010) * ab[2]) - (c000 + (c001 - c000) * ab[2])) * eb[2]
        high_e = (c100 + (c101 - c100) * ab[2]) + ((c110 + (c111 - c110) * ab[2]) - (c100 + (c101 - c100) * ab[2])) * eb[2]
        value = low_e + (high_e - low_e) * hb[2]
        if not math.isfinite(value) or value < 0:
            raise ZenithV3Refusal("interpolated direct optical depth invalid")
        result.append(value)
    return result


def _load_v1_photometry(root: Path):
    path = root / "review/asiv-matched-stellar-transport-v1/assemble_validate_matched_stellar_v1.py"
    spec = importlib.util.spec_from_file_location("native_zenith_v3_photometry", path)
    if spec is None or spec.loader is None:
        raise ZenithV3Refusal("cannot load frozen stellar photometry helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_against_fresh_holdout(*, root: Path, extended_runtime: dict[str, Any],
                                   validation_results: dict[tuple[float, float, float], dict[str, Any]],
                                   sed_bundle_path: Path, johnson_v_path: Path) -> dict[str, Any]:
    expected = {_coord_key(r["targetAltitudeDeg"], r["observerElevationM"], r["aod550"]) for r in build_validation_cases()}
    if set(validation_results) != expected:
        raise ZenithV3Refusal("fresh validation result universe incomplete or drifted")
    if sha256_file(sed_bundle_path) != SOURCE_SED_SHA256:
        raise ZenithV3Refusal("frozen Pickles SED bundle SHA-256 drift")
    if sha256_file(johnson_v_path) != SOURCE_JOHNSON_V_SHA256:
        raise ZenithV3Refusal("frozen Johnson-V asset SHA-256 drift")
    phot = _load_v1_photometry(root)
    _, wavelength_nm, band_response, representatives = phot.load_bound_photometric_assets(
        sed_bundle_path=sed_bundle_path, johnson_v_path=johnson_v_path
    )
    reps = [row for row in representatives if int(row["libraryNumber"]) in REPRESENTATIVE_LIBRARY_NUMBERS]
    if [int(row["libraryNumber"]) for row in reps] != list(REPRESENTATIVE_LIBRARY_NUMBERS):
        raise ZenithV3Refusal("representative Pickles template identity drift")

    all_deltas: list[float] = []
    interval_rows: dict[float, list[float]] = {float(h): [] for h in VALIDATION_ALTITUDE_DEG}
    cases = []
    for row in build_validation_cases():
        h, e, a = row["targetAltitudeDeg"], row["observerElevationM"], row["aod550"]
        ref = validation_results[_coord_key(h, e, a)]
        predicted_tau = interpolate_optical_depth(
            extended_runtime, target_altitude_deg=h, observer_elevation_m=e, aod550=a
        )
        predicted_t = [math.exp(-tau) for tau in predicted_tau]
        reference_t = [float(x) for x in ref["lineOfSightDirectTransmission"]]
        sed_rows = []
        for sed in reps:
            flux = [float(x) for x in sed["fluxRelative"]]
            runtime_av = phot.band_extinction_mag(
                wavelength_nm=wavelength_nm, flux_relative=flux,
                band_response=band_response, transmission=predicted_t,
            )
            reference_av = phot.band_extinction_mag(
                wavelength_nm=wavelength_nm, flux_relative=flux,
                band_response=band_response, transmission=reference_t,
            )
            delta = runtime_av - reference_av
            all_deltas.append(delta)
            interval_rows[float(h)].append(delta)
            sed_rows.append({
                "libraryNumber": int(sed["libraryNumber"]),
                "runtimeAvMag": runtime_av,
                "referenceAvMag": reference_av,
                "deltaAvMag": delta,
            })
        cases.append({**row, "sedComparisons": sed_rows})

    def metrics(values: list[float]) -> dict[str, Any]:
        max_abs = max(abs(x) for x in values)
        rms = math.sqrt(sum(x * x for x in values) / len(values))
        return {
            "comparisonCount": len(values),
            "maxAbsDeltaAvMag": max_abs,
            "rmsDeltaAvMag": rms,
            "maxAbsDeltaAvMagLimit": MAX_ABS_ERROR_MAG_LIMIT,
            "rmsDeltaAvMagLimit": RMS_ERROR_MAG_LIMIT,
            "passed": max_abs <= MAX_ABS_ERROR_MAG_LIMIT and rms <= RMS_ERROR_MAG_LIMIT,
        }

    overall = metrics(all_deltas)
    by_altitude = {str(h): metrics(values) for h, values in interval_rows.items()}
    all_pass = overall["passed"] and all(row["passed"] for row in by_altitude.values())
    result = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "COMPUTATIONAL_REFERENCE_VALIDATION_PASS" if all_pass else "COMPUTATIONAL_REFERENCE_VALIDATION_FAIL",
        "mysticState": MYSTIC_STATE,
        "sourceV2RuntimeSha256": SOURCE_RUNTIME_SHA256,
        "interpolation": "v2-csc-altitude-trilinear-direct-optical-depth-with-new-2.5deg-zenith-knots",
        "newTrainingSolverSpectrumCount": 100,
        "freshValidationAtmosphericSpectrumCount": 64,
        "johnsonVComparisonCount": len(all_deltas),
        "representativeLibraryNumbers": list(REPRESENTATIVE_LIBRARY_NUMBERS),
        "overall": overall,
        "byValidationAltitudeDeg": by_altitude,
        "cases": cases,
        "gates": {
            "globalAndEveryNewAltitudeIntervalMustPass": True,
            "maxAbsDeltaAvMag": MAX_ABS_ERROR_MAG_LIMIT,
            "rmsDeltaAvMag": RMS_ERROR_MAG_LIMIT,
            "postResultThresholdRelaxationAuthorized": False,
            "postResultRetuningAuthorized": False,
        },
        "claimBoundary": {
            "computationalReferenceValidationOnly": True,
            "oldV2DomainChanged": False,
            "empiricalRealSkyValidated": False,
            "humanFirstSeeingValidated": False,
            "productionAuthorized": False,
        },
    }
    if not all_pass:
        raise ZenithV3Refusal(json.dumps({"validationFailed": result}, sort_keys=True))
    return result


def execute_case(*, uvspec: Path, data_dir: Path, atmosphere_file: Path, wavelength_grid_file: Path,
                 row: dict[str, float]) -> dict[str, Any]:
    input_text = render_uvspec_input(
        data_dir=data_dir, atmosphere_file=atmosphere_file, wavelength_grid_file=wavelength_grid_file,
        target_altitude_deg=row["targetAltitudeDeg"], observer_elevation_m=row["observerElevationM"], aod550=row["aod550"],
    )
    completed = subprocess.run(
        [str(uvspec)], input=input_text, text=True, capture_output=True, check=False, timeout=180,
    )
    if completed.returncode != 0:
        raise ZenithV3Refusal(f"uvspec failed rc={completed.returncode}: {completed.stderr[-2000:]}")
    parsed = parse_direct_transmission(completed.stdout, target_altitude_deg=row["targetAltitudeDeg"])
    return {**row, **parsed, "inputSha256": hashlib.sha256(input_text.encode("utf-8")).hexdigest()}


def execute_campaign(*, root: Path, source_runtime_path: Path, uvspec: Path, data_dir: Path,
                     atmosphere_file: Path, wavelength_grid_file: Path, sed_bundle_path: Path,
                     johnson_v_path: Path, output_dir: Path, allow_execution: bool = False) -> dict[str, Any]:
    if allow_execution is not True:
        raise ZenithV3Refusal("scientific solver execution requires explicit allow_execution=True")
    validate_frozen_case_universe()
    if sha256_file(source_runtime_path) != SOURCE_RUNTIME_SHA256:
        raise ZenithV3Refusal("source native stellar v2 runtime SHA-256 drift")
    if sha256_file(atmosphere_file) != AFGLUS_SHA256:
        raise ZenithV3Refusal("AFGLUS atmosphere SHA-256 drift")
    if sha256_file(uvspec) != UVSPEC_SHA256:
        raise ZenithV3Refusal("uvspec SHA-256 drift")
    grid_values = [int(line) for line in Path(wavelength_grid_file).read_text().splitlines() if line.strip()]
    if grid_values != list(WAVELENGTH_NM):
        raise ZenithV3Refusal("wavelength-grid file drift")

    source_runtime = json.loads(Path(source_runtime_path).read_text(encoding="utf-8"))
    validate_source_runtime(source_runtime)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)

    training_results = {}
    for row in build_training_cases():
        result = execute_case(
            uvspec=uvspec, data_dir=data_dir, atmosphere_file=atmosphere_file,
            wavelength_grid_file=wavelength_grid_file, row=row,
        )
        training_results[_coord_key(row["targetAltitudeDeg"], row["observerElevationM"], row["aod550"])] = result
    extended_runtime = build_extended_runtime(source_runtime, training_results)

    validation_results = {}
    for row in build_validation_cases():
        result = execute_case(
            uvspec=uvspec, data_dir=data_dir, atmosphere_file=atmosphere_file,
            wavelength_grid_file=wavelength_grid_file, row=row,
        )
        validation_results[_coord_key(row["targetAltitudeDeg"], row["observerElevationM"], row["aod550"])] = result

    validation = validate_against_fresh_holdout(
        root=root, extended_runtime=extended_runtime, validation_results=validation_results,
        sed_bundle_path=sed_bundle_path, johnson_v_path=johnson_v_path,
    )
    extended_runtime["validation"] = {
        "status": validation["status"],
        "freshBandComparisonCount": validation["johnsonVComparisonCount"],
        "freshAtmosphericCaseCount": validation["freshValidationAtmosphericSpectrumCount"],
        "maxAbsDeltaAvMag": validation["overall"]["maxAbsDeltaAvMag"],
        "rmsDeltaAvMag": validation["overall"]["rmsDeltaAvMag"],
        "maxAbsDeltaAvMagLimit": MAX_ABS_ERROR_MAG_LIMIT,
        "rmsDeltaAvMagLimit": RMS_ERROR_MAG_LIMIT,
        "everyNewAltitudeIntervalPassed": all(x["passed"] for x in validation["byValidationAltitudeDeg"].values()),
        "validationStageId": STAGE_ID,
    }
    runtime_path = output_dir / "stellar-transport-v3-zenith-lut.json"
    runtime_path.write_text(json.dumps(extended_runtime, separators=(",", ":"), allow_nan=False) + "\n", encoding="utf-8")
    validation["extendedRuntimeSha256"] = sha256_file(runtime_path)
    validation["scientificSolverExecuted"] = True
    validation["solverInvocationCount"] = 164
    validation["randomNumbersUsed"] = False
    validation_path = output_dir / "native-stellar-zenith-v3-validation.json"
    validation_path.write_text(json.dumps(validation, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return {"runtimePath": str(runtime_path), "validationPath": str(validation_path), "validation": validation}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--allow-execution", action="store_true")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--source-runtime", type=Path)
    parser.add_argument("--uvspec", type=Path)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--atmosphere-file", type=Path)
    parser.add_argument("--wavelength-grid-file", type=Path)
    parser.add_argument("--sed-bundle", type=Path)
    parser.add_argument("--johnson-v", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if not args.execute:
        validate_frozen_case_universe()
        print(json.dumps({
            "status": "REVIEW_ONLY_NO_SOLVER_EXECUTION",
            "stageId": STAGE_ID,
            "newTrainingSpectrumCount": 100,
            "freshValidationSpectrumCount": 64,
            "johnsonVComparisonCount": 192,
            "newAltitudeKnotsDeg": list(NEW_TRAINING_ALTITUDE_DEG),
            "freshValidationAltitudeDeg": list(VALIDATION_ALTITUDE_DEG),
        }, sort_keys=True))
        return 0
    required = [args.source_runtime, args.uvspec, args.data_dir, args.atmosphere_file,
                args.wavelength_grid_file, args.sed_bundle, args.johnson_v, args.output_dir]
    if any(value is None for value in required):
        raise ZenithV3Refusal("execution requires all explicit bound paths")
    result = execute_campaign(
        root=args.root, source_runtime_path=args.source_runtime, uvspec=args.uvspec,
        data_dir=args.data_dir, atmosphere_file=args.atmosphere_file,
        wavelength_grid_file=args.wavelength_grid_file, sed_bundle_path=args.sed_bundle,
        johnson_v_path=args.johnson_v, output_dir=args.output_dir,
        allow_execution=args.allow_execution,
    )
    print(json.dumps({
        "status": result["validation"]["status"],
        "extendedRuntimeSha256": result["validation"]["extendedRuntimeSha256"],
        "maxAbsDeltaAvMag": result["validation"]["overall"]["maxAbsDeltaAvMag"],
        "rmsDeltaAvMag": result["validation"]["overall"]["rmsDeltaAvMag"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
