#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

STAGE_ID = "twilight-surrogate-tier-1-atm-z-grid-site-probe-v1"
SITE_ALTITUDE_KM = 0.357143
EXPECTED_ZOUT = "zout 0.000000"
FORBIDDEN_ALTITUDE_PREFIX = "altitude "
FORBIDDEN_MC_ELEVATION_PREFIX = "mc_elevation_file "


class ProbeError(RuntimeError):
    pass


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def raw_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atmosphere_altitudes(path: Path) -> list[float]:
    rows: list[float] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        columns = stripped.split()
        if len(columns) < 2:
            raise ProbeError(f"malformed atmosphere row: {raw}")
        try:
            altitude = float(columns[0])
        except ValueError as exc:
            raise ProbeError(f"invalid atmosphere altitude: {columns[0]}") from exc
        if not math.isfinite(altitude):
            raise ProbeError("non-finite atmosphere altitude")
        rows.append(altitude)
    if len(rows) < 2:
        raise ProbeError("atmosphere has fewer than two levels")
    if any(rows[index] <= rows[index + 1] for index in range(len(rows) - 1)):
        raise ProbeError("atmosphere altitudes must be strictly descending")
    return rows


def forced_grid(path: Path, site_altitude_km: float = SITE_ALTITUDE_KM) -> list[float]:
    if not math.isfinite(site_altitude_km) or site_altitude_km < 0:
        raise ProbeError("invalid site altitude")
    levels = atmosphere_altitudes(path)
    if not (levels[-1] <= site_altitude_km < levels[0]):
        raise ProbeError("site altitude outside atmosphere grid")
    selected = [value for value in levels if value > site_altitude_km]
    selected.append(site_altitude_km)
    if len(selected) < 2:
        raise ProbeError("forced grid has fewer than two levels")
    return selected


def format_level(value: float) -> str:
    return f"{value:.6f}"


def render(
    data_dir: Path,
    atmosphere: Path,
    solar_flux: Path,
    output_dir: Path,
) -> tuple[str, list[float]]:
    grid = forced_grid(atmosphere)
    grid_line = "atm_z_grid " + " ".join(format_level(value) for value in grid)
    text = "\n".join([
        f"data_files_path {data_dir.resolve()}",
        f"atmosphere_file {atmosphere.resolve()}",
        f"source solar {solar_flux.resolve()}",
        "mol_abs_param crs",
        "wavelength 380 780",
        "sza 100.000000",
        "phi0 0.00",
        "rte_solver mystic",
        "mc_spherical 1D",
        "mc_photons 1",
        "mc_vroom off",
        "mc_std",
        "mc_randomseed 990004",
        f"mc_basename {(output_dir / 'mc').resolve()}",
        "mc_spectral_is 550.0",
        "albedo 0.150000",
        "aerosol_default",
        "aerosol_set_tau_at_wvl 550 0.081818",
        grid_line,
        EXPECTED_ZOUT,
        "umu -0.50000000",
        "phi 36.000000",
        "verbose",
        "",
    ])
    lines = text.splitlines()
    if any(line.startswith(FORBIDDEN_ALTITUDE_PREFIX) for line in lines):
        raise ProbeError("explicit altitude must be absent")
    if any(line.startswith(FORBIDDEN_MC_ELEVATION_PREFIX) for line in lines):
        raise ProbeError("mc_elevation_file must be absent")
    if lines.count(EXPECTED_ZOUT) != 1:
        raise ProbeError("exact local-surface zout contract not rendered")
    if sum(line.startswith("atm_z_grid ") for line in lines) != 1:
        raise ProbeError("exact atm_z_grid contract not rendered")
    if grid[-1] != SITE_ALTITUDE_KM:
        raise ProbeError("forced grid bottom is not the site altitude")
    return text, grid


def classify(
    returncode: int,
    stderr: str,
    generated_count: int,
) -> tuple[str, bool]:
    marker = f"forced new altitude = {SITE_ALTITUDE_KM:.6f}"
    if returncode == 0 and generated_count > 0 and marker in stderr:
        return "FROZEN_RUNTIME_ACCEPTS_ATM_Z_GRID_SITE_ALTITUDE_CANDIDATE", True
    return "UNEXPECTED_ATM_Z_GRID_SITE_ALTITUDE_PROBE_RESULT", False


def probe(
    uvspec: Path,
    data_dir: Path,
    atmosphere: Path,
    solar_flux: Path,
    runtime_lock: Path,
    output_dir: Path,
) -> dict[str, Any]:
    for path, label in (
        (uvspec, "uvspec"),
        (atmosphere, "atmosphere"),
        (solar_flux, "solar flux"),
        (runtime_lock, "runtime lock"),
    ):
        if not path.is_file():
            raise ProbeError(f"{label} missing: {path}")
    if not data_dir.is_dir():
        raise ProbeError(f"data directory missing: {data_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    text, grid = render(data_dir, atmosphere, solar_flux, output_dir)
    input_path = output_dir / "input-resolved.txt"
    grid_path = output_dir / "atm-z-grid.json"
    input_path.write_text(text, encoding="utf-8")
    grid_path.write_text(
        dump({
            "siteAltitudeKm": SITE_ALTITUDE_KM,
            "levelCount": len(grid),
            "levelsKmDescending": grid,
            "bottomLevelKm": grid[-1],
            "sourceAtmosphereSha256": raw_sha256(atmosphere),
        }),
        encoding="utf-8",
    )

    start = time.monotonic()
    process = subprocess.run(
        [str(uvspec.resolve())],
        input=text,
        text=True,
        capture_output=True,
        check=False,
        timeout=180,
    )
    elapsed = time.monotonic() - start
    (output_dir / "stdout.txt").write_text(process.stdout, encoding="utf-8")
    (output_dir / "stderr.txt").write_text(process.stderr, encoding="utf-8")

    generated = sorted(path for path in output_dir.glob("mc*") if path.is_file())
    generated_hashes = {path.name: raw_sha256(path) for path in generated}
    generated_sizes = {path.name: path.stat().st_size for path in generated}
    for path in generated:
        path.unlink()

    status, accepted = classify(process.returncode, process.stderr, len(generated_hashes))
    result = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": status,
        "candidateAcceptedByFrozenRuntime": accepted,
        "candidateMechanism": "atm_z_grid_with_bottom_at_site_altitude_and_no_explicit_altitude",
        "siteAltitudeKm": SITE_ALTITUDE_KM,
        "forcedGridLevelCount": len(grid),
        "forcedGridBottomKm": grid[-1],
        "explicitAltitudePresent": False,
        "mcElevationFilePresent": False,
        "localSurfaceZout": 0.0,
        "physicalEquivalenceEstablished": False,
        "authorizationPermitted": False,
        "ordinal2ScientificDispatchPermitted": False,
        "scientificExecution": False,
        "scientificDatasetProduced": False,
        "surrogateTrainingUsePermitted": False,
        "syntaxCheckCount": 0,
        "solverExecutionCount": 1,
        "mcPhotons": 1,
        "exitCode": process.returncode,
        "elapsedSeconds": elapsed,
        "inputResolvedSha256": sha_bytes(text.encode()),
        "forcedGridSha256": raw_sha256(grid_path),
        "uvspecSha256": raw_sha256(uvspec),
        "runtimeLockRawSha256": raw_sha256(runtime_lock),
        "atmosphereSha256": raw_sha256(atmosphere),
        "solarFluxSha256": raw_sha256(solar_flux),
        "stdoutSha256": sha_bytes(process.stdout.encode()),
        "stderrSha256": sha_bytes(process.stderr.encode()),
        "generatedOutputFileCount": len(generated_hashes),
        "generatedOutputHashes": generated_hashes,
        "generatedOutputSizes": generated_sizes,
        "generatedOutputFilesPreserved": False,
        "requiredNextProof": (
            "predeclare and run a bounded equivalence validation: verify the forced atmospheric profile/column and compare a deterministic supported solver using explicit altitude against MYSTIC using atm_z_grid at a non-twilight geometry before any ordinal-2 authorization"
        ),
        "boundary": (
            "one-photon executable-candidate probe only; numerical outputs deleted; runtime acceptance does not establish scientific equivalence, authorize Tier-1, or create training data"
        ),
    }
    (output_dir / "atm-z-grid-probe.json").write_text(dump(result), encoding="utf-8")
    if not accepted:
        raise ProbeError(
            f"unexpected atm_z_grid probe result: exit={process.returncode}, outputs={len(generated_hashes)}"
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--uvspec", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--atmosphere", type=Path, required=True)
    parser.add_argument("--solar-flux", type=Path, required=True)
    parser.add_argument("--runtime-lock", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = probe(
            args.uvspec,
            args.data_dir,
            args.atmosphere,
            args.solar_flux,
            args.runtime_lock,
            args.output_dir,
        )
        print(dump(result), end="")
        return 0
    except Exception as exc:
        print(
            dump({
                "schemaVersion": 1,
                "stageId": STAGE_ID,
                "status": "REFUSED",
                "reason": str(exc),
            }),
            file=sys.stderr,
            end="",
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
