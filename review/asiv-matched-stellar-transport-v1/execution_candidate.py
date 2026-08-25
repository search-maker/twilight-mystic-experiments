#!/usr/bin/env python3
"""Render-only execution candidate for ASIV matched aerosol-family stellar transport.

This module is intentionally incapable of invoking libRadtran. It freezes the
case universe and exact uvspec input surface that a separately authorized
execution runner may consume after the Koomen/Volz lane is closed.

Scientific boundary:
- no solver execution;
- no MYSTIC execution;
- no protected holdout access;
- no starsvisibility mutation;
- no post-result retuning;
- no native MYSTIC-STATE-0081 rebuild or render path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Iterable

STAGE_ID = "asiv-matched-stellar-transport-v1"
SOURCE_STARS_MAIN = "404c255a15158ed172bb2d6a7ac97b4ea24a9f29"
SOURCE_TWILIGHT_MAIN = "5293a7d86a6ec31825da4f9dfbfc9cecfea3afc0"
SOURCE_STELLAR_RUNNER_BLOB = "a513336c5fcd6d16279e25fd257533ef45e9bbbb"
SOURCE_STELLAR_PROTOCOL_BLOB = "1e605731111e07bbbc8a0eae355d7bcbb71ae1d4"
SOURCE_ASIV_ADAPTER_BLOB = "5fd4fc92e9ee06cc7377114813a7d84f85459b66"
SOURCE_ASIV_EXECUTION_CONTRACT_BLOB = "a2c4ebac5be8daf096ca3b543fd2f994ec4146a1"
SOURCE_ASIV_OPAC_TREE_SHA256 = "5d8bbf8e6b91ec3d405dee36f21a94afbb6e5ec6cd67da2dd5dd541738199d80"

RUNTIME_LOCK_PATH = "experiments/mystic-batch-v1/runtime-lock.micromamba.json"
RUNTIME_LOCK_GIT_BLOB_SHA1 = "8573f62829371a0eb866976a5062ea61dc0767b1"
RUNTIME_LOCK_RAW_SHA256 = "3b5fbec964642b04c73a6423b3355dbcc4ba5e84f9614f6d74420491bacc20c5"
EXACT_LIBRADTRAN_PACKAGE = "rubin-libradtran=2.0.6=py312pl5321he9373c2_1"
UVSPEC_SHA256 = "2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3"
UVSPEC_HELP_SHA256 = "868aea5af762d968f6f62c4e1472916d25232ed9cab5be112d753b0823d20548"
BASE_DATA_TREE_SHA256 = "ad30b49177e9c84e46497d69faf0c75e466996b0d0003f1de210289ae9f847d7"
OFFICIAL_OPTPROP_ARCHIVE_SHA256 = "11daa1f1f4be0fd4ddf7e881ec2005498049674a1540d37b4b1e8f5e16052c7e"
AFGLUS_ATMOSPHERE_SHA256 = "dab26290ed81c762ed0c607e5dc2d53393c1462a0c3a528bc5e3f5935191cfb5"

WAVELENGTH_NM = tuple(range(380, 781))
ATMOSPHERE_NAME = "afglus"
MOL_ABS_PARAM = "crs"
SURFACE_ALBEDO = 0.15
AOD_DOMAIN = (0.05, 0.40)
ALTITUDE_DOMAIN_DEG = (5.0, 80.0)
ELEVATION_DOMAIN_M = (0.0, 2500.0)

NATIVE_STATE = "native-rural-ss"
NON_NATIVE_FAMILIES = (
    "opac-continental-average",
    "opac-maritime-clean",
    "opac-desert",
    "opac-desert-spheroids",
)
ALL_ASIV_STATES = (NATIVE_STATE, *NON_NATIVE_FAMILIES)
OPAC_SPECIES_FILE = {
    "opac-continental-average": "continental_average",
    "opac-maritime-clean": "maritime_clean",
    "opac-desert": "desert",
    "opac-desert-spheroids": "desert_spheroids",
}

ALTITUDE_KNOTS = (
    5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
    17.5, 20, 22.5, 25, 27.5, 30,
    35, 40, 45, 50, 55, 60, 65, 70, 75, 80,
)
ELEVATION_KNOTS_M = (0, 500, 1250, 2000, 2500)
AOD_KNOTS = (0.05, 0.10, 0.20, 0.30, 0.40)

VALIDATION_ALTITUDE_DEG = (
    5.666667, 7.666667, 9.666667, 12.666667, 14.666667, 19.166667,
    24.166667, 29.166667, 38.333333, 48.333333, 58.333333, 73.333333,
)
VALIDATION_ELEVATION_M = (333.333333, 875, 1625, 2291.666667)
VALIDATION_AOD550 = (0.083333333, 0.166666667, 0.266666667, 0.366666667)
SED_REPRESENTATIVE_COUNT = 3


class CandidateRefusal(RuntimeError):
    pass


def finite(name: str, value: object) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite; got {value!r}")
    return number


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def validate_case(*, family: str, target_altitude_deg: float, aod550: float,
                  observer_elevation_m: float) -> tuple[str, float, float, float]:
    if family == NATIVE_STATE:
        raise CandidateRefusal(
            "native-rural-ss is the frozen MYSTIC-STATE-0081 comparator and cannot be rendered or rebuilt by this extension"
        )
    if family not in NON_NATIVE_FAMILIES:
        raise ValueError(f"unknown non-native ASIV aerosol family: {family}")
    altitude = finite("targetAltitudeDeg", target_altitude_deg)
    aod = finite("aod550", aod550)
    elevation = finite("observerElevationM", observer_elevation_m)
    if not ALTITUDE_DOMAIN_DEG[0] <= altitude <= ALTITUDE_DOMAIN_DEG[1]:
        raise ValueError(f"targetAltitudeDeg outside frozen domain {ALTITUDE_DOMAIN_DEG}")
    if not AOD_DOMAIN[0] <= aod <= AOD_DOMAIN[1]:
        raise ValueError(f"aod550 outside frozen domain {AOD_DOMAIN}")
    if not ELEVATION_DOMAIN_M[0] <= elevation <= ELEVATION_DOMAIN_M[1]:
        raise ValueError(f"observerElevationM outside frozen domain {ELEVATION_DOMAIN_M}")
    return family, altitude, aod, elevation


def atmosphere_levels_descending(path: Path) -> list[float]:
    levels: list[float] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        columns = line.split()
        if len(columns) < 2:
            raise CandidateRefusal(f"malformed atmosphere row: {raw!r}")
        levels.append(finite("atmosphere altitude", columns[0]))
    if len(levels) < 2:
        raise CandidateRefusal("atmosphere has fewer than two altitude levels")
    if any(levels[i] <= levels[i + 1] for i in range(len(levels) - 1)):
        raise CandidateRefusal("atmosphere levels must be strictly descending")
    return levels


def elevated_site_grid_ascending(atmosphere_file: Path, observer_elevation_m: float) -> list[float]:
    elevation = finite("observerElevationM", observer_elevation_m)
    if not ELEVATION_DOMAIN_M[0] <= elevation <= ELEVATION_DOMAIN_M[1]:
        raise ValueError(f"observerElevationM outside frozen domain {ELEVATION_DOMAIN_M}")
    site_km = elevation / 1000.0
    levels = atmosphere_levels_descending(atmosphere_file)
    if not levels[-1] <= site_km < levels[0]:
        raise CandidateRefusal("site altitude outside atmosphere grid")
    grid = [site_km, *sorted(z for z in levels if z > site_km)]
    if len(grid) < 2 or any(grid[i] >= grid[i + 1] for i in range(len(grid) - 1)):
        raise CandidateRefusal("atm_z_grid must be strictly ascending")
    return grid


def aerosol_block(family: str, aod550: float) -> list[str]:
    if family == NATIVE_STATE:
        raise CandidateRefusal(
            "native-rural-ss directive provenance is retained in the precontract, but native stellar rendering is forbidden"
        )
    if family not in OPAC_SPECIES_FILE:
        raise ValueError(f"unknown non-native ASIV aerosol family: {family}")
    aod = finite("aod550", aod550)
    if not AOD_DOMAIN[0] <= aod <= AOD_DOMAIN[1]:
        raise ValueError(f"aod550 outside frozen domain {AOD_DOMAIN}")
    return [
        "aerosol_default",
        "aerosol_species_library OPAC",
        f"aerosol_species_file {OPAC_SPECIES_FILE[family]}",
        f"aerosol_set_tau_at_wvl 550 {aod:.8f}",
    ]


def render_uvspec_input(*, family: str, data_dir: Path, atmosphere_file: Path,
                        wavelength_grid_file: Path, target_altitude_deg: float,
                        aod550: float, observer_elevation_m: float) -> str:
    family, altitude, aod, elevation = validate_case(
        family=family,
        target_altitude_deg=target_altitude_deg,
        aod550=aod550,
        observer_elevation_m=observer_elevation_m,
    )
    grid = elevated_site_grid_ascending(atmosphere_file, elevation)
    lines = [
        f"data_files_path {data_dir}",
        f"atmosphere_file {atmosphere_file}",
        "source solar",
        f"mol_abs_param {MOL_ABS_PARAM}",
        f"wavelength_grid_file {wavelength_grid_file}",
        f"wavelength {WAVELENGTH_NM[0]} {WAVELENGTH_NM[-1]}",
        f"sza {90.0 - altitude:.8f}",
        f"atm_z_grid {' '.join(f'{z:.6f}' for z in grid)}",
        "zout 0.000000",
        f"albedo {SURFACE_ALBEDO:.8f}",
        *aerosol_block(family, aod),
        "rte_solver sdisort",
        "sdisort nscat 1",
        "output_quantity transmittance",
        "output_user lambda edir",
        "quiet",
    ]
    text = "\n".join(lines) + "\n"
    forbidden = (
        "rte_solver mystic",
        "mc_",
        "angstrom",
        "aerosol_angstrom",
    )
    lower = text.lower()
    if any(token in lower for token in forbidden):
        raise CandidateRefusal("forbidden stellar transport directive emitted")
    if text.count("rte_solver sdisort") != 1 or text.count("sdisort nscat 1") != 1:
        raise CandidateRefusal("deterministic direct-transport solver directive drift")
    if text.count("output_quantity transmittance") != 1 or text.count("output_user lambda edir") != 1:
        raise CandidateRefusal("direct-transmission output directive drift")
    expected_aerosol = aerosol_block(family, aod)
    actual_aerosol = [line for line in lines if line.startswith("aerosol_")]
    if actual_aerosol != expected_aerosol:
        raise CandidateRefusal("aerosol directive surface drift")
    return text


def _case_id(prefix: str, family: str, altitude: float, elevation: float, aod: float) -> str:
    def enc(value: float) -> str:
        return f"{value:.9f}".rstrip("0").rstrip(".").replace("-", "m").replace(".", "p")
    return f"{prefix}__{family}__h{enc(altitude)}__z{enc(elevation)}__aod{enc(aod)}"


def _cases(prefix: str, altitudes: Iterable[float], elevations: Iterable[float],
           aods: Iterable[float]) -> list[dict]:
    rows: list[dict] = []
    for family in NON_NATIVE_FAMILIES:
        for altitude in altitudes:
            for elevation in elevations:
                for aod in aods:
                    rows.append({
                        "caseId": _case_id(prefix, family, float(altitude), float(elevation), float(aod)),
                        "family": family,
                        "targetAltitudeDeg": float(altitude),
                        "observerElevationM": float(elevation),
                        "aod550": float(aod),
                        "solverExecutionAuthorized": False,
                    })
    return rows


def build_prefrozen_manifest() -> dict:
    training = _cases("lut", ALTITUDE_KNOTS, ELEVATION_KNOTS_M, AOD_KNOTS)
    validation = _cases("validation", VALIDATION_ALTITUDE_DEG, VALIDATION_ELEVATION_M, VALIDATION_AOD550)
    training_coords = {
        (row["family"], row["targetAltitudeDeg"], row["observerElevationM"], row["aod550"])
        for row in training
    }
    validation_coords = {
        (row["family"], row["targetAltitudeDeg"], row["observerElevationM"], row["aod550"])
        for row in validation
    }
    overlap = training_coords & validation_coords
    if overlap:
        raise CandidateRefusal(f"training/validation overlap: {sorted(overlap)[:3]}")
    if len(training) != 2700:
        raise CandidateRefusal(f"expected 2700 non-native LUT spectra, got {len(training)}")
    if len(validation) != 768:
        raise CandidateRefusal(f"expected 768 non-native validation spectra, got {len(validation)}")
    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "PREFROZEN_RENDER_ONLY_NO_SOLVER_EXECUTION",
        "sourceBindings": {
            "twilightMysticMain": SOURCE_TWILIGHT_MAIN,
            "starsvisibilityMain": SOURCE_STARS_MAIN,
            "stellarReferenceRunnerGitBlobSha1": SOURCE_STELLAR_RUNNER_BLOB,
            "stellarValidationProtocolGitBlobSha1": SOURCE_STELLAR_PROTOCOL_BLOB,
            "asivAerosolDirectiveAdapterGitBlobSha1": SOURCE_ASIV_ADAPTER_BLOB,
            "asivExecutionContractGitBlobSha1": SOURCE_ASIV_EXECUTION_CONTRACT_BLOB,
            "augmentedOpacDataTreeSha256": SOURCE_ASIV_OPAC_TREE_SHA256,
        },
        "runtimeIdentity": {
            "runtimeLockPath": RUNTIME_LOCK_PATH,
            "runtimeLockGitBlobSha1": RUNTIME_LOCK_GIT_BLOB_SHA1,
            "runtimeLockRawSha256": RUNTIME_LOCK_RAW_SHA256,
            "exactPackageSpec": EXACT_LIBRADTRAN_PACKAGE,
            "uvspecSha256": UVSPEC_SHA256,
            "uvspecHelpSha256": UVSPEC_HELP_SHA256,
            "baseDataTreeSha256": BASE_DATA_TREE_SHA256,
            "augmentedDataTreeSha256": SOURCE_ASIV_OPAC_TREE_SHA256,
            "officialOptpropArchiveSha256": OFFICIAL_OPTPROP_ARCHIVE_SHA256,
            "atmosphereSha256": AFGLUS_ATMOSPHERE_SHA256,
            "verificationRequiredBeforeAnyFutureSolverExecution": True,
        },
        "physics": {
            "atmosphere": ATMOSPHERE_NAME,
            "molAbsParam": MOL_ABS_PARAM,
            "surfaceAlbedo": SURFACE_ALBEDO,
            "wavelengthGridNm": [380, 780, 1],
            "quantity": "line-of-sight-direct-spectral-transmission",
            "storageQuantityAfterExecution": "tau=-ln(T_direct)",
            "solver": "sdisort",
            "scatteringOrder": 1,
            "mysticRequired": False,
            "randomNumbersRequired": False,
            "starOnlyAngstromCorrectionAllowed": False,
        },
        "families": list(NON_NATIVE_FAMILIES),
        "nativeComparator": {
            "stateId": NATIVE_STATE,
            "representation": "MYSTIC-STATE-0081 stellar-transport-v2",
            "rebuildAuthorized": False,
            "renderPathPresent": False,
        },
        "training": {
            "caseCount": len(training),
            "casesPerFamily": len(training) // len(NON_NATIVE_FAMILIES),
            "axes": {
                "targetAltitudeDeg": list(ALTITUDE_KNOTS),
                "observerElevationM": list(ELEVATION_KNOTS_M),
                "aod550": list(AOD_KNOTS),
            },
            "cases": training,
        },
        "validation": {
            "atmosphericCaseCount": len(validation),
            "atmosphericCasesPerFamily": len(validation) // len(NON_NATIVE_FAMILIES),
            "sedRepresentativeCount": SED_REPRESENTATIVE_COUNT,
            "johnsonVComparisonCount": len(validation) * SED_REPRESENTATIVE_COUNT,
            "johnsonVComparisonsPerFamily": (len(validation) // len(NON_NATIVE_FAMILIES)) * SED_REPRESENTATIVE_COUNT,
            "axes": {
                "targetAltitudeDeg": list(VALIDATION_ALTITUDE_DEG),
                "observerElevationM": list(VALIDATION_ELEVATION_M),
                "aod550": list(VALIDATION_AOD550),
            },
            "cases": validation,
            "acceptance": {
                "maxAbsoluteJohnsonVExtinctionErrorMag": 0.025,
                "rmsJohnsonVExtinctionErrorMag": 0.010,
                "perFamilyPassRequired": True,
                "aggregatePassCannotHideFamilyFailure": True,
            },
        },
        "authorization": {
            "solverExecutionAuthorized": False,
            "scientificExecutionAuthorized": False,
            "resultOpeningAuthorized": False,
            "pandoraHoldoutAccessAllowed": False,
            "starsvisibilityMutationAuthorized": False,
            "productionActivationAuthorized": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    manifest = sub.add_parser("manifest")
    manifest.add_argument("--output", type=Path)

    render = sub.add_parser("render")
    render.add_argument("--family", choices=NON_NATIVE_FAMILIES, required=True)
    render.add_argument("--target-altitude-deg", type=float, required=True)
    render.add_argument("--observer-elevation-m", type=float, required=True)
    render.add_argument("--aod550", type=float, required=True)
    render.add_argument("--data-dir", type=Path, required=True)
    render.add_argument("--atmosphere-file", type=Path, required=True)
    render.add_argument("--wavelength-grid-file", type=Path, required=True)
    render.add_argument("--output", type=Path)

    args = parser.parse_args()
    if args.command == "manifest":
        text = json.dumps(build_prefrozen_manifest(), indent=2, sort_keys=True, allow_nan=False) + "\n"
    else:
        text = render_uvspec_input(
            family=args.family,
            data_dir=args.data_dir,
            atmosphere_file=args.atmosphere_file,
            wavelength_grid_file=args.wavelength_grid_file,
            target_altitude_deg=args.target_altitude_deg,
            observer_elevation_m=args.observer_elevation_m,
            aod550=args.aod550,
        )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
