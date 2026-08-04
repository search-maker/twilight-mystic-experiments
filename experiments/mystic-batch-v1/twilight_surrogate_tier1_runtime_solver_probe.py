#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

STAGE_ID = "twilight-surrogate-tier-1-runtime-solver-probe-v1"
EXPECTED_ALTITUDE = "altitude 0.357143"
EXPECTED_ZOUT = "zout 0.000000"
FORBIDDEN_ZOUT = "zout 0.357143"


class ProbeError(RuntimeError):
    pass


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def raw_sha256(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def render(data_dir: Path, atmosphere: Path, solar_flux: Path, output_dir: Path) -> str:
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
        "mc_randomseed 990003",
        f"mc_basename {(output_dir / 'mc').resolve()}",
        "mc_spectral_is 550.0",
        "albedo 0.150000",
        "aerosol_default",
        "aerosol_set_tau_at_wvl 550 0.081818",
        EXPECTED_ALTITUDE,
        EXPECTED_ZOUT,
        "umu -0.50000000",
        "phi 36.000000",
        "quiet",
        "",
    ])


def probe(uvspec: Path, data_dir: Path, atmosphere: Path, solar_flux: Path, runtime_lock: Path, output_dir: Path) -> dict[str, Any]:
    for path, label in ((uvspec, "uvspec"), (atmosphere, "atmosphere"), (solar_flux, "solar flux"), (runtime_lock, "runtime lock")):
        if not path.is_file():
            raise ProbeError(f"{label} missing: {path}")
    if not data_dir.is_dir():
        raise ProbeError(f"data directory missing: {data_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    text = render(data_dir, atmosphere, solar_flux, output_dir)
    if text.count(EXPECTED_ALTITUDE) != 1 or text.count(EXPECTED_ZOUT) != 1 or FORBIDDEN_ZOUT in text:
        raise ProbeError("exact altitude/zout contract not rendered")
    input_path = output_dir / "input-resolved.txt"
    input_path.write_text(text)
    start = time.monotonic()
    process = subprocess.run([str(uvspec.resolve())], input=text, text=True, capture_output=True, check=False, timeout=180)
    elapsed = time.monotonic() - start
    (output_dir / "stdout.txt").write_text(process.stdout)
    (output_dir / "stderr.txt").write_text(process.stderr)
    generated = sorted(path for path in output_dir.glob("mc*") if path.is_file())
    generated_hashes = {path.name: raw_sha256(path) for path in generated}
    generated_sizes = {path.name: path.stat().st_size for path in generated}
    for path in generated:
        path.unlink()
    accepted = process.returncode == 0 and bool(generated_hashes)
    result = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "FROZEN_RUNTIME_SOLVER_ACCEPTS_SITE_ALTITUDE_INPUT" if accepted else "FROZEN_RUNTIME_SOLVER_REJECTS_SITE_ALTITUDE_INPUT",
        "accepted": accepted,
        "scientificExecution": False,
        "scientificDatasetProduced": False,
        "surrogateTrainingUsePermitted": False,
        "syntaxCheckCount": 0,
        "solverExecutionCount": 1,
        "mcPhotons": 1,
        "exitCode": process.returncode,
        "elapsedSeconds": elapsed,
        "inputResolvedSha256": sha_bytes(text.encode()),
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
        "requiredInputLines": [EXPECTED_ALTITUDE, EXPECTED_ZOUT],
        "forbiddenInputLine": FORBIDDEN_ZOUT,
        "boundary": "one separate one-photon solver probe; hashes only, generated numerical files deleted, no dataset, no training, no authorization",
    }
    (output_dir / "solver-probe.json").write_text(dump(result))
    if not accepted:
        raise ProbeError(f"frozen runtime solver probe failed: exit={process.returncode}, outputs={len(generated_hashes)}")
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
        result = probe(args.uvspec, args.data_dir, args.atmosphere, args.solar_flux, args.runtime_lock, args.output_dir)
        print(dump(result), end="")
        return 0
    except Exception as exc:
        print(dump({"schemaVersion": 1, "stageId": STAGE_ID, "status": "REFUSED", "reason": str(exc)}), file=sys.stderr, end="")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
