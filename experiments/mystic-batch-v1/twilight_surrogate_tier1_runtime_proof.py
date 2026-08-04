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

STAGE_ID = "twilight-surrogate-tier-1-runtime-proof-v1"
EXPECTED_ALTITUDE = "altitude 0.357143"
EXPECTED_ZOUT = "zout 0.000000"
FORBIDDEN_ZOUT = "zout 0.357143"


class RuntimeProofError(RuntimeError):
    pass


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def render(data_dir: Path, atmosphere: Path, solar_flux: Path, output_dir: Path) -> str:
    return "\n".join(
        [
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
            "mc_randomseed 990002",
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
        ]
    )


def prove(uvspec: Path, data_dir: Path, atmosphere: Path, solar_flux: Path, runtime_lock: Path, output_dir: Path) -> dict[str, Any]:
    for path, label in ((uvspec, "uvspec"), (atmosphere, "atmosphere"), (solar_flux, "solar flux"), (runtime_lock, "runtime lock")):
        if not path.is_file():
            raise RuntimeProofError(f"{label} missing: {path}")
    if not data_dir.is_dir():
        raise RuntimeProofError(f"data directory missing: {data_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    text = render(data_dir, atmosphere, solar_flux, output_dir)
    if text.count(EXPECTED_ALTITUDE) != 1 or text.count(EXPECTED_ZOUT) != 1 or FORBIDDEN_ZOUT in text:
        raise RuntimeProofError("exact altitude/zout contract not rendered")
    input_path = output_dir / "input-resolved.txt"
    input_path.write_text(text)
    start = time.monotonic()
    process = subprocess.run([str(uvspec.resolve()), "-c"], input=text, text=True, capture_output=True, check=False, timeout=120)
    elapsed = time.monotonic() - start
    (output_dir / "stdout.txt").write_text(process.stdout)
    (output_dir / "stderr.txt").write_text(process.stderr)
    accepted = process.returncode == 0
    decision = "FROZEN_RUNTIME_ACCEPTS_SITE_ALTITUDE_INPUT" if accepted else "FROZEN_RUNTIME_REJECTS_SITE_ALTITUDE_INPUT"
    result = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": decision,
        "accepted": accepted,
        "scientificExecution": False,
        "scientificDatasetProduced": False,
        "surrogateTrainingUsePermitted": False,
        "syntaxCheckCount": 1,
        "solverExecutionCount": 0,
        "exitCode": process.returncode,
        "elapsedSeconds": elapsed,
        "inputPath": str(input_path),
        "inputResolvedSha256": text_sha256(text),
        "uvspecSha256": raw_sha256(uvspec),
        "runtimeLockRawSha256": raw_sha256(runtime_lock),
        "atmosphereSha256": raw_sha256(atmosphere),
        "solarFluxSha256": raw_sha256(solar_flux),
        "stdoutSha256": text_sha256(process.stdout),
        "stderrSha256": text_sha256(process.stderr),
        "requiredInputLines": [EXPECTED_ALTITUDE, EXPECTED_ZOUT],
        "forbiddenInputLine": FORBIDDEN_ZOUT,
        "boundary": "one real uvspec syntax check in the frozen runtime; no solver execution, no scientific result, no dataset, no training",
    }
    (output_dir / "runtime-proof.json").write_text(dump(result))
    if not accepted:
        raise RuntimeProofError(f"frozen runtime syntax check failed with exit code {process.returncode}")
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
        result = prove(args.uvspec, args.data_dir, args.atmosphere, args.solar_flux, args.runtime_lock, args.output_dir)
        print(dump(result), end="")
        return 0
    except Exception as exc:
        print(dump({"schemaVersion": 1, "stageId": STAGE_ID, "status": "REFUSED", "reason": str(exc)}), file=sys.stderr, end="")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
