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

STAGE_ID = "twilight-surrogate-tier-1-edited-atmosphere-proof-v1"
SITE_ALTITUDE_KM = 0.357143
ZOUT_LINE = "zout 0.000000"


class ProofError(RuntimeError):
    pass


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def raw_sha256(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def parse_profile(path: Path) -> tuple[list[str], list[list[float]]]:
    comments: list[str] = []
    rows: list[list[float]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            comments.append(raw)
            continue
        parts = stripped.split()
        try:
            row = [float(value) for value in parts]
        except ValueError as exc:
            raise ProofError(f"non-numeric atmosphere row: {raw}") from exc
        if len(row) < 3 or not all(math.isfinite(value) for value in row):
            raise ProofError(f"invalid atmosphere row: {raw}")
        rows.append(row)
    if len(rows) < 2:
        raise ProofError("atmosphere profile needs at least two rows")
    widths = {len(row) for row in rows}
    if len(widths) != 1:
        raise ProofError("atmosphere rows have inconsistent columns")
    altitudes = [row[0] for row in rows]
    descending = all(a > b for a, b in zip(altitudes, altitudes[1:]))
    ascending = all(a < b for a, b in zip(altitudes, altitudes[1:]))
    if not (descending or ascending):
        raise ProofError("atmosphere altitude grid is not strictly monotonic")
    return comments, rows


def interpolate_row(lower: list[float], upper: list[float], altitude_km: float) -> list[float]:
    if not lower[0] < altitude_km < upper[0]:
        raise ProofError("site altitude is not strictly bracketed")
    fraction = (altitude_km - lower[0]) / (upper[0] - lower[0])
    return [altitude_km] + [
        lower[index] + fraction * (upper[index] - lower[index])
        for index in range(1, len(lower))
    ]


def transformed_rows(rows: list[list[float]], altitude_km: float) -> tuple[list[list[float]], str]:
    if not math.isfinite(altitude_km) or altitude_km < 0:
        raise ProofError("invalid site altitude")
    descending = rows[0][0] > rows[-1][0]
    ordered = list(reversed(rows)) if descending else list(rows)
    if altitude_km < ordered[0][0] or altitude_km >= ordered[-1][0]:
        raise ProofError("site altitude outside atmosphere profile")
    exact = next((row for row in ordered if math.isclose(row[0], altitude_km, rel_tol=0.0, abs_tol=1e-12)), None)
    if exact is not None:
        bottom = list(exact)
        mode = "existing-level"
    else:
        lower = None
        upper = None
        for first, second in zip(ordered, ordered[1:]):
            if first[0] < altitude_km < second[0]:
                lower, upper = first, second
                break
        if lower is None or upper is None:
            raise ProofError("site altitude not bracketed")
        bottom = interpolate_row(lower, upper, altitude_km)
        mode = "linear-interpolation"
    kept = [row for row in ordered if row[0] > altitude_km]
    transformed = [bottom, *kept]
    if descending:
        transformed.reverse()
    altitudes = [row[0] for row in transformed]
    if descending:
        if not all(a > b for a, b in zip(altitudes, altitudes[1:])) or not math.isclose(altitudes[-1], altitude_km, abs_tol=1e-12):
            raise ProofError("transformed descending profile invalid")
    else:
        if not all(a < b for a, b in zip(altitudes, altitudes[1:])) or not math.isclose(altitudes[0], altitude_km, abs_tol=1e-12):
            raise ProofError("transformed ascending profile invalid")
    return transformed, mode


def write_profile(source: Path, destination: Path, altitude_km: float) -> dict[str, Any]:
    comments, rows = parse_profile(source)
    transformed, mode = transformed_rows(rows, altitude_km)
    destination.parent.mkdir(parents=True, exist_ok=True)
    header = [
        "# Generated proof-only atmosphere for an elevated local surface.",
        f"# Source: {source.resolve()}",
        f"# Bottom altitude above sea level: {altitude_km:.6f} km",
        "# Profiles at an inserted bottom level are linearly interpolated.",
    ]
    rendered_rows = [" ".join(f"{value:.12e}" for value in row) for row in transformed]
    destination.write_text("\n".join([*header, *comments, *rendered_rows, ""]), encoding="utf-8")
    return {
        "mode": mode,
        "sourceRowCount": len(rows),
        "transformedRowCount": len(transformed),
        "columnCount": len(rows[0]),
        "sourceMinimumAltitudeKm": min(row[0] for row in rows),
        "transformedMinimumAltitudeKm": min(row[0] for row in transformed),
        "siteAltitudeKm": altitude_km,
        "sourceAtmosphereSha256": raw_sha256(source),
        "transformedAtmosphereSha256": raw_sha256(destination),
    }


def render_deterministic(data_dir: Path, atmosphere: Path, solar_flux: Path, *, altitude_option: bool) -> str:
    lines = [
        f"data_files_path {data_dir.resolve()}",
        f"atmosphere_file {atmosphere.resolve()}",
        f"source solar {solar_flux.resolve()}",
        "mol_abs_param crs",
        "wavelength 550 550",
        "sza 30.000000",
        "phi0 0.00",
        "rte_solver disort",
        "albedo 0.150000",
        "aerosol_default",
        "aerosol_set_tau_at_wvl 550 0.081818",
    ]
    if altitude_option:
        lines.append(f"altitude {SITE_ALTITUDE_KM:.6f}")
    lines.extend([ZOUT_LINE, "output_user lambda edir edn eup", "quiet", ""])
    return "\n".join(lines)


def render_mystic(data_dir: Path, atmosphere: Path, solar_flux: Path, output_dir: Path) -> str:
    return "\n".join([
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
        ZOUT_LINE,
        "umu -0.50000000",
        "phi 36.000000",
        "quiet",
        "",
    ])


def run_uvspec(uvspec: Path, text: str, timeout: int = 180) -> tuple[subprocess.CompletedProcess[str], float]:
    start = time.monotonic()
    process = subprocess.run([str(uvspec.resolve())], input=text, text=True, capture_output=True, check=False, timeout=timeout)
    return process, time.monotonic() - start


def parse_numeric_stdout(value: str) -> list[float]:
    tokens = value.split()
    if not tokens:
        raise ProofError("deterministic solver produced empty stdout")
    try:
        result = [float(token) for token in tokens]
    except ValueError as exc:
        raise ProofError(f"non-numeric deterministic stdout: {value!r}") from exc
    if not all(math.isfinite(number) for number in result):
        raise ProofError("non-finite deterministic stdout")
    return result


def compare_vectors(reference: list[float], candidate: list[float]) -> dict[str, float]:
    if len(reference) != len(candidate):
        raise ProofError("deterministic output length changed")
    maximum_absolute = 0.0
    maximum_relative = 0.0
    for left, right in zip(reference, candidate):
        absolute = abs(left - right)
        scale = max(abs(left), abs(right), 1e-30)
        maximum_absolute = max(maximum_absolute, absolute)
        maximum_relative = max(maximum_relative, absolute / scale)
    return {"maximumAbsoluteDifference": maximum_absolute, "maximumRelativeDifference": maximum_relative}


def prove(uvspec: Path, data_dir: Path, atmosphere: Path, solar_flux: Path, runtime_lock: Path, output_dir: Path) -> dict[str, Any]:
    for path, label in ((uvspec, "uvspec"), (atmosphere, "atmosphere"), (solar_flux, "solar flux"), (runtime_lock, "runtime lock")):
        if not path.is_file():
            raise ProofError(f"{label} missing: {path}")
    if not data_dir.is_dir():
        raise ProofError(f"data directory missing: {data_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    transformed = output_dir / "afglus-site-0.357143km.dat"
    profile = write_profile(atmosphere, transformed, SITE_ALTITUDE_KM)

    reference_text = render_deterministic(data_dir, atmosphere, solar_flux, altitude_option=True)
    candidate_text = render_deterministic(data_dir, transformed, solar_flux, altitude_option=False)
    if f"altitude {SITE_ALTITUDE_KM:.6f}" not in reference_text or "\naltitude " in candidate_text:
        raise ProofError("deterministic altitude boundary rendered incorrectly")
    (output_dir / "deterministic-reference.inp").write_text(reference_text, encoding="utf-8")
    (output_dir / "deterministic-candidate.inp").write_text(candidate_text, encoding="utf-8")
    reference_process, reference_elapsed = run_uvspec(uvspec, reference_text)
    candidate_process, candidate_elapsed = run_uvspec(uvspec, candidate_text)
    (output_dir / "deterministic-reference.stdout").write_text(reference_process.stdout, encoding="utf-8")
    (output_dir / "deterministic-reference.stderr").write_text(reference_process.stderr, encoding="utf-8")
    (output_dir / "deterministic-candidate.stdout").write_text(candidate_process.stdout, encoding="utf-8")
    (output_dir / "deterministic-candidate.stderr").write_text(candidate_process.stderr, encoding="utf-8")
    if reference_process.returncode != 0 or candidate_process.returncode != 0:
        raise ProofError(f"deterministic pair failed: reference={reference_process.returncode}, candidate={candidate_process.returncode}")
    comparison = compare_vectors(parse_numeric_stdout(reference_process.stdout), parse_numeric_stdout(candidate_process.stdout))
    if comparison["maximumRelativeDifference"] > 1e-6:
        raise ProofError(f"deterministic equivalence tolerance exceeded: {comparison}")

    mystic_text = render_mystic(data_dir, transformed, solar_flux, output_dir)
    if "\naltitude " in mystic_text or mystic_text.count(ZOUT_LINE) != 1:
        raise ProofError("MYSTIC candidate must use edited atmosphere and local-surface zout only")
    mystic_input = output_dir / "mystic-candidate.inp"
    mystic_input.write_text(mystic_text, encoding="utf-8")
    mystic_process, mystic_elapsed = run_uvspec(uvspec, mystic_text)
    (output_dir / "mystic-candidate.stdout").write_text(mystic_process.stdout, encoding="utf-8")
    (output_dir / "mystic-candidate.stderr").write_text(mystic_process.stderr, encoding="utf-8")
    generated = sorted(path for path in output_dir.glob("mc*") if path.is_file())
    generated_hashes = {path.name: raw_sha256(path) for path in generated}
    generated_sizes = {path.name: path.stat().st_size for path in generated}
    for path in generated:
        path.unlink()
    if mystic_process.returncode != 0 or not generated_hashes:
        raise ProofError(f"edited-atmosphere MYSTIC probe failed: exit={mystic_process.returncode}, outputs={len(generated_hashes)}, stderr={mystic_process.stderr!r}")

    report = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "EDITED_ATMOSPHERE_EXECUTABLE_AND_DETERMINISTIC_EQUIVALENCE_PASSED",
        "siteAltitudeKm": SITE_ALTITUDE_KM,
        "observerElevationSemantics": "atmosphere-file-bottom-at-site-altitude-above-sea-level; sensor-zout-zero-at-local-surface",
        "primaryDocumentationClaim": "for an elevated site, restructure atmosphere_file so it stops at the appropriate altitude; editing the atmosphere file is an explicit alternative to altitude",
        "profileTransformation": profile,
        "deterministicComparison": {
            **comparison,
            "relativeTolerance": 1e-6,
            "referenceExitCode": reference_process.returncode,
            "candidateExitCode": candidate_process.returncode,
            "referenceElapsedSeconds": reference_elapsed,
            "candidateElapsedSeconds": candidate_elapsed,
            "referenceStdoutSha256": sha_bytes(reference_process.stdout.encode()),
            "candidateStdoutSha256": sha_bytes(candidate_process.stdout.encode()),
            "referenceStderrSha256": sha_bytes(reference_process.stderr.encode()),
            "candidateStderrSha256": sha_bytes(candidate_process.stderr.encode()),
        },
        "mysticProbe": {
            "exitCode": mystic_process.returncode,
            "elapsedSeconds": mystic_elapsed,
            "mcPhotons": 1,
            "solverExecutionCount": 1,
            "generatedOutputFileCount": len(generated_hashes),
            "generatedOutputHashes": generated_hashes,
            "generatedOutputSizes": generated_sizes,
            "generatedOutputFilesPreserved": False,
            "stdoutSha256": sha_bytes(mystic_process.stdout.encode()),
            "stderrSha256": sha_bytes(mystic_process.stderr.encode()),
        },
        "uvspecSha256": raw_sha256(uvspec),
        "runtimeLockRawSha256": raw_sha256(runtime_lock),
        "scientificExecution": False,
        "scientificDatasetProduced": False,
        "surrogateTrainingUsePermitted": False,
        "authorizationPermitted": False,
        "ordinal2ScientificDispatchPermitted": False,
        "requiredNextReview": "independently inspect the transformed profile, deterministic pair and one-photon artifact before changing the Tier-1 adapter or preparing authorization",
        "boundary": "proof-only edited-atmosphere representation; one deterministic pair and one one-photon MYSTIC compatibility probe; numerical MYSTIC files deleted",
    }
    (output_dir / "edited-atmosphere-proof.json").write_text(dump(report), encoding="utf-8")
    return report


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
        result = prove(args.uvspec, args.data_dir, args.atmosphere, args.solar_flux, args.runtime_lock, args.output_dir)
        print(dump(result), end="")
        return 0
    except Exception as exc:
        print(dump({"schemaVersion": 1, "stageId": STAGE_ID, "status": "REFUSED", "reason": str(exc)}), file=sys.stderr, end="")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
