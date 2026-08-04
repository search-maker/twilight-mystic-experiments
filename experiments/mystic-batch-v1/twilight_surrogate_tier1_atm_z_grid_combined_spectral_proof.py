#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, Sequence

PROOF_PATH = Path(__file__).with_name(
    "twilight_surrogate_tier1_atm_z_grid_equivalence_proof.py"
)
spec = importlib.util.spec_from_file_location(
    "tier1_atm_z_grid_equivalence_proof_base", PROOF_PATH
)
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot load equivalence proof: {PROOF_PATH}")
PROOF = importlib.util.module_from_spec(spec)
spec.loader.exec_module(PROOF)
BASE = PROOF.BASE

STAGE_ID = "twilight-surrogate-tier-1-atm-z-grid-combined-spectral-proof-v3"
MYSTIC_WAVELENGTH_START_NM = 380.0
MYSTIC_WAVELENGTH_END_NM = 780.0
MYSTIC_IMPORTANCE_WAVELENGTH_NM = 550.0
ALIS_MARKER_FRAGMENT = "ALIS calculation wavelength: 550"


class CombinedProofError(RuntimeError):
    pass


def validate_immutable_contract() -> None:
    if BASE.CONTROL_WAVELENGTH_NM != 550.0:
        raise CombinedProofError("deterministic control wavelength changed")
    if not (
        MYSTIC_WAVELENGTH_START_NM
        < MYSTIC_IMPORTANCE_WAVELENGTH_NM
        < MYSTIC_WAVELENGTH_END_NM
    ):
        raise CombinedProofError(
            "MYSTIC ALIS importance wavelength must be strictly inside the interval"
        )
    if BASE.MYSTIC_PHOTONS != 1:
        raise CombinedProofError("combined proof must remain exactly one photon")
    if BASE.MYSTIC_SEED != 990004:
        raise CombinedProofError("combined proof diagnostic seed changed")


def corrected_render_mystic_input(
    data_dir: Path,
    atmosphere: Path,
    solar_flux: Path,
    output_dir: Path,
    grid_ascending: Sequence[float],
    resolved: bool,
) -> str:
    validate_immutable_contract()
    basename = BASE.path_value(output_dir / "mc", "${OUTPUT_DIR}/mc", resolved)
    common = BASE.common_lines(data_dir, atmosphere, solar_flux, resolved)
    wavelength_lines = [
        index for index, line in enumerate(common) if line.startswith("wavelength ")
    ]
    if wavelength_lines != [4]:
        raise CombinedProofError(
            f"unexpected deterministic common wavelength placement: {wavelength_lines}"
        )
    common[wavelength_lines[0]] = (
        f"wavelength {MYSTIC_WAVELENGTH_START_NM:.1f} "
        f"{MYSTIC_WAVELENGTH_END_NM:.1f}"
    )
    lines = [
        *common,
        *BASE.representation_lines(
            "B-atm-z-grid-candidate",
            BASE.PRIMARY_SITE_ALTITUDE_KM,
            grid_ascending,
        ),
        "rte_solver mystic",
        "mc_spherical 1D",
        f"mc_photons {BASE.MYSTIC_PHOTONS}",
        "mc_vroom off",
        "mc_std",
        f"mc_randomseed {BASE.MYSTIC_SEED}",
        f"mc_basename {basename}",
        f"mc_spectral_is {MYSTIC_IMPORTANCE_WAVELENGTH_NM:.1f}",
        BASE.EXPECTED_ZOUT,
        f"umu {BASE.CONTROL_UMU:.8f}",
        f"phi {BASE.CONTROL_PHI_DEG:.6f}",
        "verbose",
        "",
    ]
    text = "\n".join(lines)
    actual = text.splitlines()
    if any(line.startswith(prefix) for line in actual for prefix in BASE.FORBIDDEN_PREFIXES):
        raise CombinedProofError(
            "combined candidate input contains a forbidden altitude mechanism"
        )
    if actual.count(BASE.EXPECTED_ZOUT) != 1:
        raise CombinedProofError("combined candidate input lacks exact local-surface zout")
    if sum(line.startswith("atm_z_grid ") for line in actual) != 1:
        raise CombinedProofError("combined candidate input lacks exact atm_z_grid")
    expected_wavelength = (
        f"wavelength {MYSTIC_WAVELENGTH_START_NM:.1f} "
        f"{MYSTIC_WAVELENGTH_END_NM:.1f}"
    )
    if actual.count(expected_wavelength) != 1:
        raise CombinedProofError("combined candidate input lacks Tier-1 spectral domain")
    expected_importance = f"mc_spectral_is {MYSTIC_IMPORTANCE_WAVELENGTH_NM:.1f}"
    if actual.count(expected_importance) != 1:
        raise CombinedProofError("combined candidate input lacks exact ALIS importance wavelength")
    return text


def corrected_run_mystic_probe(
    uvspec: Path,
    data_dir: Path,
    atmosphere: Path,
    solar_flux: Path,
    output_root: Path,
) -> dict[str, Any]:
    validate_immutable_contract()
    grid = BASE.forced_grid_ascending(atmosphere, BASE.PRIMARY_SITE_ALTITUDE_KM)
    run_dir = (
        output_root
        / f"h-{BASE.PRIMARY_SITE_ALTITUDE_KM:.6f}"
        / "mystic-B-tier1-spectrum-one-photon"
    )
    raw = corrected_render_mystic_input(
        data_dir, atmosphere, solar_flux, run_dir, grid, False
    )
    resolved = corrected_render_mystic_input(
        data_dir, atmosphere, solar_flux, run_dir, grid, True
    )
    execution = BASE.run_uvspec(uvspec, run_dir, raw, resolved, 180)
    stdout = execution.pop("stdout")
    stderr = execution.pop("stderr")
    generated = sorted(
        path
        for path in run_dir.iterdir()
        if path.is_file() and path.name.startswith("mc")
    )
    generated_rows = [
        {
            "filename": path.name,
            "sizeBytes": path.stat().st_size,
            "rawSha256": BASE.raw_sha256(path),
        }
        for path in generated
    ]
    for path in generated:
        path.unlink()
    surface_marker = (
        f"forced new altitude = {BASE.PRIMARY_SITE_ALTITUDE_KM:.6f}"
    )
    surface_marker_observed = surface_marker in stderr
    alis_marker_observed = ALIS_MARKER_FRAGMENT in stderr
    passed = (
        execution["exitCode"] == 0
        and not execution["timedOut"]
        and BASE.ALTITUDE_REJECTION_FRAGMENT not in stderr
        and surface_marker_observed
        and alis_marker_observed
        and bool(generated_rows)
    )
    result = {
        "status": (
            "MYSTIC_ACCEPTS_EQUIVALENCE_VALIDATED_ATM_Z_GRID_WITH_TIER1_SPECTRAL_DOMAIN"
            if passed
            else "MYSTIC_ATM_Z_GRID_TIER1_SPECTRAL_ACCEPTANCE_PROBE_FAILED"
        ),
        "passed": passed,
        "siteAltitudeKm": BASE.PRIMARY_SITE_ALTITUDE_KM,
        "localSurfaceZoutKm": 0.0,
        "outputLevelInterpretation": {
            "localSurfaceHeightKm": 0.0,
            "aboveSeaLevelKm": BASE.PRIMARY_SITE_ALTITUDE_KM,
            "binding": (
                "validated deterministic B profile at identical atm_z_grid and zout semantics"
            ),
        },
        "spectralConfiguration": {
            "wavelengthDomainNm": [
                MYSTIC_WAVELENGTH_START_NM,
                MYSTIC_WAVELENGTH_END_NM,
            ],
            "alisImportanceWavelengthNm": MYSTIC_IMPORTANCE_WAVELENGTH_NM,
            "alisReferenceStrictlyInsideDomain": True,
            "matchesFrozenTier1Domain": True,
            "singleWavelengthEndpointCrashConfigurationUsed": False,
            "alisMarkerObserved": alis_marker_observed,
        },
        "atmosphereStartsAtSiteAltitude": (
            grid[0] == BASE.PRIMARY_SITE_ALTITUDE_KM
        ),
        "layersBelowSiteAltitudePresent": False,
        "explicitAltitudePresent": False,
        "mcElevationFilePresent": False,
        "surfaceMarkerObserved": surface_marker_observed,
        "altitudeRejectionObserved": BASE.ALTITUDE_REJECTION_FRAGMENT in stderr,
        "generatedFiles": generated_rows,
        "generatedFilesPreserved": False,
        "scientificDatasetProduced": False,
        "solverExecutionCount": 1,
        "mcPhotons": BASE.MYSTIC_PHOTONS,
        "mcRandomSeed": BASE.MYSTIC_SEED,
        "execution": execution,
        "stdoutSha256": BASE.sha_bytes(stdout.encode("utf-8")),
        "stderrSha256": BASE.sha_bytes(stderr.encode("utf-8")),
    }
    result_path = run_dir / "mystic-probe.json"
    result_path.write_text(BASE.dump(result), encoding="utf-8")
    result["resultRawSha256"] = BASE.raw_sha256(result_path)
    return result


def install_corrected_mystic_boundary() -> None:
    validate_immutable_contract()
    PROOF.STAGE_ID = STAGE_ID
    BASE.render_mystic_input = corrected_render_mystic_input
    BASE.run_mystic_probe = corrected_run_mystic_probe


def main() -> int:
    install_corrected_mystic_boundary()
    return PROOF.main()


if __name__ == "__main__":
    raise SystemExit(main())
