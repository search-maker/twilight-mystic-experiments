#!/usr/bin/env python3
"""Complete-set LUT assembly and fresh Johnson-V validation for matched stellar v1.

Review/analysis only: this module never invokes libRadtran or any subprocess.
It consumes the complete future one-shot execution artifact universe frozen by
PR #363/#364, builds one 0081-compatible optical-depth LUT per non-native OPAC
family, and compares interpolation against all fresh off-knot reference spectra.

No partial result interpretation is allowed. Every one of the 2700 training
spectra and 768 validation spectra must be present exactly once before metrics
are emitted.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
from pathlib import Path
from typing import Any, Iterable

HERE = Path(__file__).resolve().parent
CANDIDATE_PATH = HERE / "execution_candidate.py"
EXPECTED_CANDIDATE_GIT_BLOB_SHA1 = "ec433aa3a594311738a6f6aa2b339a7e33d43447"
EXPECTED_SED_BUNDLE_SHA256 = "85cbf41c86309b9d54d4765516167165f2d8736bcda8994337ef25d775ea11cb"
EXPECTED_JOHNSON_V_RAW_SHA256 = "51c357eb4cb3609361759f9750ad13ae13a901970913e3a5d87bb5c45ee2db9a"
EXPECTED_WAVELENGTH_NM = tuple(range(380, 781))
MAX_ABS_ERROR_MAG_LIMIT = 0.025
RMS_ERROR_MAG_LIMIT = 0.010


class ValidationRefusal(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def load_candidate():
    if git_blob_sha1(CANDIDATE_PATH) != EXPECTED_CANDIDATE_GIT_BLOB_SHA1:
        raise ValidationRefusal("prefrozen render/manifest candidate Git blob drift")
    spec = importlib.util.spec_from_file_location("matched_stellar_validation_candidate", CANDIDATE_PATH)
    if spec is None or spec.loader is None:
        raise ValidationRefusal("cannot load prefrozen candidate")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def canonicalize_johnson_v_bandpass(raw: dict[str, Any]) -> tuple[list[float], list[float]]:
    wavelengths = raw.get("wavelengthNm")
    response = raw.get("response")
    if wavelengths != list(EXPECTED_WAVELENGTH_NM):
        raise ValidationRefusal("Johnson-V wavelength grid drift")
    if not isinstance(response, list) or len(response) != 411:
        raise ValidationRefusal("frozen Johnson-V response must contain exactly 411 raw samples")
    active = [float(value) for value in response[:401]]
    tail = response[401:]
    if len(tail) != 10 or any(float(value) != 0.0 for value in tail):
        raise ValidationRefusal("Johnson-V compatibility tail must be exactly ten zeros")
    if any(not math.isfinite(value) or value < 0 for value in active):
        raise ValidationRefusal("Johnson-V active response is invalid")
    if not max(active) > 0:
        raise ValidationRefusal("Johnson-V active response has no positive support")
    return [float(value) for value in wavelengths], active


def validate_sed_bundle(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    if bundle.get("schemaVersion") != 1 or bundle.get("quantity") != "relative-stellar-f-lambda-shape":
        raise ValidationRefusal("Pickles SED bundle schema/quantity drift")
    if bundle.get("wavelengthNm") != list(EXPECTED_WAVELENGTH_NM):
        raise ValidationRefusal("Pickles SED wavelength grid drift")
    templates = bundle.get("templates")
    if not isinstance(templates, list) or len(templates) != 131:
        raise ValidationRefusal("Pickles SED bundle must contain exactly 131 templates")
    seen: set[int] = set()
    for template in templates:
        number = int(template.get("libraryNumber"))
        if number in seen or not 1 <= number <= 131:
            raise ValidationRefusal("Pickles library-number universe drift")
        seen.add(number)
        flux = template.get("fluxRelative")
        if not isinstance(flux, list) or len(flux) != 401:
            raise ValidationRefusal(f"Pickles template {number} spectral length drift")
        if any(not math.isfinite(float(value)) or float(value) < 0 for value in flux):
            raise ValidationRefusal(f"Pickles template {number} contains invalid flux")
        color = float(template.get("bMinusVLandoltBmVc"))
        if not math.isfinite(color):
            raise ValidationRefusal(f"Pickles template {number} color is nonfinite")
    if seen != set(range(1, 132)):
        raise ValidationRefusal("Pickles library-number universe must be 1..131 exact")
    return templates


def select_three_pickles_representatives(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    templates = validate_sed_bundle(bundle)
    normal = [template for template in templates if template.get("abundance") == "normal"]
    if not normal:
        raise ValidationRefusal("no normal-abundance Pickles templates")
    minimum = min(
        normal,
        key=lambda row: (float(row["bMinusVLandoltBmVc"]), int(row["libraryNumber"])),
    )
    maximum_color = max(float(row["bMinusVLandoltBmVc"]) for row in normal)
    maximum = min(
        (row for row in normal if float(row["bMinusVLandoltBmVc"]) == maximum_color),
        key=lambda row: int(row["libraryNumber"]),
    )
    near = min(
        normal,
        key=lambda row: (abs(float(row["bMinusVLandoltBmVc"]) - 0.65), int(row["libraryNumber"])),
    )
    selected = [minimum, near, maximum]
    if len({int(row["libraryNumber"]) for row in selected}) != 3:
        raise ValidationRefusal("deterministic representative rule did not yield three distinct templates")
    return selected


def load_bound_photometric_assets(*, sed_bundle_path: Path, johnson_v_path: Path) -> tuple[dict[str, Any], list[float], list[float], list[dict[str, Any]]]:
    if sha256_file(sed_bundle_path) != EXPECTED_SED_BUNDLE_SHA256:
        raise ValidationRefusal("Pickles SED bundle SHA-256 drift")
    if sha256_file(johnson_v_path) != EXPECTED_JOHNSON_V_RAW_SHA256:
        raise ValidationRefusal("Johnson-V raw asset SHA-256 drift")
    bundle = load_json(sed_bundle_path)
    band = load_json(johnson_v_path)
    wavelengths, response = canonicalize_johnson_v_bandpass(band)
    representatives = select_three_pickles_representatives(bundle)
    return bundle, wavelengths, response, representatives


def _case_key(family: str, altitude: float, elevation: float, aod: float) -> tuple[str, float, float, float]:
    return (str(family), round(float(altitude), 9), round(float(elevation), 9), round(float(aod), 9))


def validate_executed_case(payload: dict[str, Any]) -> tuple[str, float, float, float]:
    if payload.get("schemaVersion") != 1 or payload.get("status") != "MATCHED_STELLAR_CASE_EXECUTED_ONCE":
        raise ValidationRefusal("case artifact status/schema drift")
    if payload.get("solver") != "sdisort" or int(payload.get("scatteringOrder", -1)) != 1:
        raise ValidationRefusal("case solver/scattering-order drift")
    if int(payload.get("solverExecutionCount", -1)) != 1 or payload.get("retryPermitted") is not False:
        raise ValidationRefusal("case is not one-shot/no-retry evidence")
    family = str(payload.get("family"))
    altitude = float(payload.get("targetAltitudeDeg"))
    elevation = float(payload.get("observerElevationM"))
    aod = float(payload.get("aod550"))
    if any(not math.isfinite(value) for value in (altitude, elevation, aod)):
        raise ValidationRefusal("case coordinate is nonfinite")
    spectrum = payload.get("spectrum") or {}
    if spectrum.get("wavelengthNm") != list(EXPECTED_WAVELENGTH_NM):
        raise ValidationRefusal("case wavelength grid drift")
    transmission = spectrum.get("lineOfSightDirectTransmission")
    tau = spectrum.get("directOpticalDepth")
    if not isinstance(transmission, list) or not isinstance(tau, list) or len(transmission) != 401 or len(tau) != 401:
        raise ValidationRefusal("case spectral length drift")
    for index, (t_raw, tau_raw) in enumerate(zip(transmission, tau)):
        t = float(t_raw)
        optical_depth = float(tau_raw)
        if not (math.isfinite(t) and 0 < t <= 1 and math.isfinite(optical_depth) and optical_depth >= 0):
            raise ValidationRefusal(f"invalid case spectral value at {index}")
        if abs(math.exp(-optical_depth) - t) > 2e-14:
            raise ValidationRefusal(f"case T/tau inconsistency at {index}")
    return family, altitude, elevation, aod


def classify_complete_case_universe(case_payloads: Iterable[dict[str, Any]]) -> tuple[Any, dict[str, dict[tuple[str, float, float, float], dict[str, Any]]]]:
    candidate = load_candidate()
    manifest = candidate.build_prefrozen_manifest()
    expected: dict[tuple[str, float, float, float], tuple[str, dict[str, Any]]] = {}
    for role in ("training", "validation"):
        for row in manifest[role]["cases"]:
            key = _case_key(row["family"], row["targetAltitudeDeg"], row["observerElevationM"], row["aod550"])
            if key in expected:
                raise ValidationRefusal("prefrozen manifest contains duplicate physical case")
            expected[key] = (role, row)
    if len(expected) != 3468:
        raise ValidationRefusal(f"prefrozen case universe must contain 3468 cases; got {len(expected)}")

    actual: dict[tuple[str, float, float, float], dict[str, Any]] = {}
    for payload in case_payloads:
        family, altitude, elevation, aod = validate_executed_case(payload)
        key = _case_key(family, altitude, elevation, aod)
        if key in actual:
            raise ValidationRefusal(f"duplicate executed case: {key}")
        if key not in expected:
            raise ValidationRefusal(f"executed case outside prefrozen universe: {key}")
        actual[key] = payload
    missing = sorted(set(expected) - set(actual))
    if missing:
        raise ValidationRefusal(f"partial results forbidden; missing {len(missing)} of 3468 prefrozen cases")
    if len(actual) != 3468:
        raise ValidationRefusal("complete executed case cardinality drift")

    by_role: dict[str, dict[tuple[str, float, float, float], dict[str, Any]]] = {"training": {}, "validation": {}}
    for key, payload in actual.items():
        role = expected[key][0]
        by_role[role][key] = payload
    if len(by_role["training"]) != 2700 or len(by_role["validation"]) != 768:
        raise ValidationRefusal("training/validation cardinality drift")
    return manifest, by_role


def build_family_runtimes(manifest: dict[str, Any], training: dict[tuple[str, float, float, float], dict[str, Any]]) -> dict[str, dict[str, Any]]:
    families = tuple(manifest["families"])
    runtimes: dict[str, dict[str, Any]] = {}
    for family in families:
        rows = [row for row in manifest["training"]["cases"] if row["family"] == family]
        if len(rows) != 675:
            raise ValidationRefusal(f"training case count drift for {family}")
        spectra = []
        for row in rows:
            key = _case_key(family, row["targetAltitudeDeg"], row["observerElevationM"], row["aod550"])
            payload = training[key]
            spectra.append([float(value) for value in payload["spectrum"]["directOpticalDepth"]])
        runtimes[family] = {
            "schemaVersion": 1,
            "quantity": "level-b-stellar-direct-optical-depth-lut",
            "wavelengthNm": list(EXPECTED_WAVELENGTH_NM),
            "axes": {
                "targetAltitudeDeg": list(manifest["training"]["axes"]["targetAltitudeDeg"]),
                "observerElevationM": list(manifest["training"]["axes"]["observerElevationM"]),
                "aod550": list(manifest["training"]["axes"]["aod550"]),
            },
            "storageOrder": "targetAltitudeDeg-major, observerElevationM-middle, aod550-minor",
            "directOpticalDepth": spectra,
            "atmosphereContract": {
                "atmosphere": "afglus",
                "aerosolFamily": family,
                "surfaceAlbedo": 0.15,
                "molAbsParam": "crs",
            },
            "interpolation": {
                "quantity": "direct-optical-depth",
                "targetAltitudeCoordinate": "cosecant-altitude-1-over-sin-h",
                "observerElevationCoordinate": "linear-meters",
                "aod550Coordinate": "linear",
            },
        }
    return runtimes


def _csc_altitude(altitude: float) -> float:
    mu = math.sin(math.radians(float(altitude)))
    if not mu > 0:
        raise ValidationRefusal("target altitude must be above horizon")
    return 1.0 / mu


def _bracket(axis: list[float], value: float, coordinate=lambda x: x) -> tuple[int, int, float]:
    value = float(value)
    if value < axis[0] or value > axis[-1]:
        raise ValidationRefusal("interpolation coordinate outside LUT support")
    if value == axis[-1]:
        return len(axis) - 2, len(axis) - 1, 1.0
    lo, hi = 0, len(axis) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if axis[mid] <= value:
            lo = mid
        else:
            hi = mid
    c_lo, c_hi, c_value = coordinate(axis[lo]), coordinate(axis[hi]), coordinate(value)
    span = c_hi - c_lo
    return lo, hi, 0.0 if span == 0 else (c_value - c_lo) / span


def _runtime_case_index(runtime: dict[str, Any], ai: int, ei: int, oi: int) -> int:
    n_e = len(runtime["axes"]["observerElevationM"])
    n_o = len(runtime["axes"]["aod550"])
    return ((ai * n_e) + ei) * n_o + oi


def interpolate_optical_depth(runtime: dict[str, Any], *, target_altitude_deg: float, observer_elevation_m: float, aod550: float) -> list[float]:
    axes = runtime["axes"]
    ab = _bracket([float(v) for v in axes["targetAltitudeDeg"]], target_altitude_deg, _csc_altitude)
    eb = _bracket([float(v) for v in axes["observerElevationM"]], observer_elevation_m)
    ob = _bracket([float(v) for v in axes["aod550"]], aod550)
    result: list[float] = []
    for w in range(401):
        def c(ai: int, ei: int, oi: int) -> float:
            return float(runtime["directOpticalDepth"][_runtime_case_index(runtime, ai, ei, oi)][w])
        c000, c001 = c(ab[0], eb[0], ob[0]), c(ab[0], eb[0], ob[1])
        c010, c011 = c(ab[0], eb[1], ob[0]), c(ab[0], eb[1], ob[1])
        c100, c101 = c(ab[1], eb[0], ob[0]), c(ab[1], eb[0], ob[1])
        c110, c111 = c(ab[1], eb[1], ob[0]), c(ab[1], eb[1], ob[1])
        c00 = c000 + (c001 - c000) * ob[2]
        c01 = c010 + (c011 - c010) * ob[2]
        c10 = c100 + (c101 - c100) * ob[2]
        c11 = c110 + (c111 - c110) * ob[2]
        c0 = c00 + (c01 - c00) * eb[2]
        c1 = c10 + (c11 - c10) * eb[2]
        value = c0 + (c1 - c0) * ab[2]
        if not math.isfinite(value) or value < 0:
            raise ValidationRefusal("interpolated optical depth is invalid")
        result.append(value)
    return result


def _trapezoid_integral(x: list[float], y: list[float]) -> float:
    total = 0.0
    for index in range(len(x) - 1):
        total += 0.5 * (y[index] + y[index + 1]) * (x[index + 1] - x[index])
    return total


def band_extinction_mag(*, wavelength_nm: list[float], flux_relative: list[float], band_response: list[float], transmission: list[float]) -> float:
    if not (len(wavelength_nm) == len(flux_relative) == len(band_response) == len(transmission) == 401):
        raise ValidationRefusal("band integration spectral length mismatch")
    unattenuated = []
    attenuated = []
    for s_raw, r_raw, t_raw in zip(flux_relative, band_response, transmission):
        s, r, t = float(s_raw), float(r_raw), float(t_raw)
        if not (math.isfinite(s) and s >= 0 and math.isfinite(r) and r >= 0 and math.isfinite(t) and 0 <= t <= 1):
            raise ValidationRefusal("invalid band integration input")
        unattenuated.append(s * r)
        attenuated.append(s * r * t)
    denominator = _trapezoid_integral(wavelength_nm, unattenuated)
    if not denominator > 0:
        raise ValidationRefusal("stellar spectrum x band response has zero integral")
    numerator = _trapezoid_integral(wavelength_nm, attenuated)
    transmission_fraction = numerator / denominator
    if not (transmission_fraction > 0 and transmission_fraction <= 1):
        raise ValidationRefusal(f"band transmission must be in (0,1]; got {transmission_fraction}")
    return -2.5 * math.log10(transmission_fraction)


def validate_family_runtimes(*, manifest: dict[str, Any], runtimes: dict[str, dict[str, Any]], validation: dict[tuple[str, float, float, float], dict[str, Any]], wavelength_nm: list[float], band_response: list[float], representatives: list[dict[str, Any]]) -> dict[str, Any]:
    family_results: dict[str, Any] = {}
    for family in manifest["families"]:
        runtime = runtimes[family]
        deltas: list[float] = []
        cases: list[dict[str, Any]] = []
        rows = [row for row in manifest["validation"]["cases"] if row["family"] == family]
        if len(rows) != 192:
            raise ValidationRefusal(f"validation case count drift for {family}")
        for row in rows:
            key = _case_key(family, row["targetAltitudeDeg"], row["observerElevationM"], row["aod550"])
            reference = validation[key]
            predicted_tau = interpolate_optical_depth(
                runtime,
                target_altitude_deg=row["targetAltitudeDeg"],
                observer_elevation_m=row["observerElevationM"],
                aod550=row["aod550"],
            )
            predicted_t = [math.exp(-value) for value in predicted_tau]
            reference_t = [float(value) for value in reference["spectrum"]["lineOfSightDirectTransmission"]]
            sed_rows = []
            for sed in representatives:
                flux = [float(value) for value in sed["fluxRelative"]]
                runtime_av = band_extinction_mag(
                    wavelength_nm=wavelength_nm,
                    flux_relative=flux,
                    band_response=band_response,
                    transmission=predicted_t,
                )
                reference_av = band_extinction_mag(
                    wavelength_nm=wavelength_nm,
                    flux_relative=flux,
                    band_response=band_response,
                    transmission=reference_t,
                )
                delta = runtime_av - reference_av
                deltas.append(delta)
                sed_rows.append({
                    "libraryNumber": int(sed["libraryNumber"]),
                    "runtimeAvMag": runtime_av,
                    "referenceAvMag": reference_av,
                    "deltaAvMag": delta,
                })
            cases.append({
                "targetAltitudeDeg": float(row["targetAltitudeDeg"]),
                "observerElevationM": float(row["observerElevationM"]),
                "aod550": float(row["aod550"]),
                "sedComparisons": sed_rows,
            })
        if len(deltas) != 576:
            raise ValidationRefusal(f"Johnson-V comparison count drift for {family}")
        max_abs = max(abs(value) for value in deltas)
        rms = math.sqrt(sum(value * value for value in deltas) / len(deltas))
        passed = max_abs <= MAX_ABS_ERROR_MAG_LIMIT and rms <= RMS_ERROR_MAG_LIMIT
        family_results[family] = {
            "comparisonCount": len(deltas),
            "maxAbsDeltaAvMag": max_abs,
            "rmsDeltaAvMag": rms,
            "maxAbsDeltaAvMagLimit": MAX_ABS_ERROR_MAG_LIMIT,
            "rmsDeltaAvMagLimit": RMS_ERROR_MAG_LIMIT,
            "passed": passed,
            "cases": cases,
        }
    return family_results


def assemble_and_validate(*, case_payloads: Iterable[dict[str, Any]], sed_bundle_path: Path, johnson_v_path: Path) -> dict[str, Any]:
    manifest, by_role = classify_complete_case_universe(case_payloads)
    _, wavelength_nm, band_response, representatives = load_bound_photometric_assets(
        sed_bundle_path=sed_bundle_path,
        johnson_v_path=johnson_v_path,
    )
    runtimes = build_family_runtimes(manifest, by_role["training"])
    family_results = validate_family_runtimes(
        manifest=manifest,
        runtimes=runtimes,
        validation=by_role["validation"],
        wavelength_nm=wavelength_nm,
        band_response=band_response,
        representatives=representatives,
    )
    all_pass = all(result["passed"] for result in family_results.values())
    return {
        "schemaVersion": 1,
        "stageId": "asiv-matched-stellar-transport-v1-complete-validation",
        "status": "COMPUTATIONAL_REFERENCE_VALIDATION_PASS" if all_pass else "COMPUTATIONAL_REFERENCE_VALIDATION_FAIL",
        "completeCaseUniverseRequired": True,
        "trainingSpectrumCount": len(by_role["training"]),
        "validationAtmosphericSpectrumCount": len(by_role["validation"]),
        "johnsonVComparisonCount": sum(result["comparisonCount"] for result in family_results.values()),
        "representatives": [
            {
                "libraryNumber": int(row["libraryNumber"]),
                "spectralType": row.get("spectralType"),
                "bMinusVLandoltBmVc": float(row["bMinusVLandoltBmVc"]),
                "abundance": row.get("abundance"),
            }
            for row in representatives
        ],
        "familyResults": family_results,
        "allFamiliesPassed": all_pass,
        "gates": {
            "perFamilyMaxAbsDeltaAvMag": MAX_ABS_ERROR_MAG_LIMIT,
            "perFamilyRmsDeltaAvMag": RMS_ERROR_MAG_LIMIT,
            "aggregatePassCannotHideFamilyFailure": True,
        },
        "runtimeLuts": runtimes,
        "claimBoundary": {
            "computationalSoftwareScienceValidationOnly": True,
            "empiricalRealSkyValidated": False,
            "humanFirstSeeingValidated": False,
            "fullSpectrumSkyScenarioValidated": False,
            "productionAuthorized": False,
            "pandoraHoldoutOpened": False,
            "postResultRetuningAuthorized": False,
        },
    }


def main() -> int:
    # Deliberately no CLI that opens future execution artifacts in this review PR.
    print(json.dumps({
        "status": "REVIEW_ONLY_COMPLETE_SET_VALIDATOR_NOT_EXECUTED",
        "expectedTrainingSpectra": 2700,
        "expectedValidationAtmosphericSpectra": 768,
        "expectedJohnsonVComparisons": 2304,
        "perFamilyGates": {
            "maxAbsDeltaAvMag": MAX_ABS_ERROR_MAG_LIMIT,
            "rmsDeltaAvMag": RMS_ERROR_MAG_LIMIT,
        },
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
