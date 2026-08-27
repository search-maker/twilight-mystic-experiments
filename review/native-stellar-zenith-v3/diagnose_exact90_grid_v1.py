#!/usr/bin/env python3
"""One-case exact-zenith stdout-grid diagnostic for native stellar zenith v3.

This diagnostic does not fit, validate, or alter the scientific model. It runs
exactly the first 90-degree training coordinate from the frozen v3 universe:
altitude=90 deg, observer elevation=0 m, AOD550=0.05. It preserves the exact
rendering method and writes raw input/stdout/stderr plus a structural wavelength
grid report so a failed strict parser can be diagnosed without opening any
protected holdout result.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
NATIVE_PATH = HERE / "native_stellar_zenith_v3.py"
CASE = {"targetAltitudeDeg": 90.0, "observerElevationM": 0.0, "aod550": 0.05}
EXPECTED_WAVELENGTHS = list(range(380, 781))


class DiagnosticRefusal(RuntimeError):
    pass


def load_native():
    spec = importlib.util.spec_from_file_location("native_stellar_zenith_v3_diag", NATIVE_PATH)
    if spec is None or spec.loader is None:
        raise DiagnosticRefusal("cannot load frozen native stellar zenith v3 module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def summarize_stdout_grid(stdout_text: str) -> dict[str, Any]:
    wavelengths: list[float] = []
    malformed: list[dict[str, Any]] = []
    for line_no, raw in enumerate(stdout_text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            malformed.append({"lineNumber": line_no, "text": raw})
            continue
        try:
            value = float(parts[0])
        except ValueError:
            malformed.append({"lineNumber": line_no, "text": raw})
            continue
        if not math.isfinite(value):
            malformed.append({"lineNumber": line_no, "text": raw})
            continue
        wavelengths.append(value)

    integral = [int(round(x)) for x in wavelengths if abs(x - round(x)) <= 1e-9]
    non_integral = [x for x in wavelengths if abs(x - round(x)) > 1e-9]
    counts = Counter(integral)
    missing = [w for w in EXPECTED_WAVELENGTHS if counts.get(w, 0) == 0]
    duplicates = {str(w): n for w, n in sorted(counts.items()) if n > 1}
    extras = [w for w in sorted(counts) if w < 380 or w > 780]
    exact = (
        not malformed
        and not non_integral
        and integral == EXPECTED_WAVELENGTHS
    )
    return {
        "schemaVersion": 1,
        "stageId": "native-stellar-zenith-v3-exact90-grid-diagnostic-v1",
        "status": "EXACT_380_780_1NM" if exact else "OUTPUT_GRID_MISMATCH_OBSERVED",
        "case": CASE,
        "nonCommentDataRowCount": len(wavelengths),
        "integralWavelengthRowCount": len(integral),
        "firstWavelength": wavelengths[0] if wavelengths else None,
        "lastWavelength": wavelengths[-1] if wavelengths else None,
        "missingExpectedWavelengthNm": missing,
        "duplicateIntegralWavelengthRows": duplicates,
        "extraIntegralWavelengthNm": extras,
        "nonIntegralWavelengthValues": non_integral,
        "malformedDataRows": malformed,
        "orderedGridEqualsExactExpected": exact,
        "radiometricAcceptanceEvaluated": False,
        "modelFitPerformed": False,
        "protectedHoldoutOpened": False,
        "productionAuthorized": False,
    }


def execute(*, uvspec: Path, data_dir: Path, atmosphere_file: Path,
            wavelength_grid_file: Path, output_dir: Path, allow_execution: bool) -> dict[str, Any]:
    if allow_execution is not True:
        raise DiagnosticRefusal("diagnostic solver execution requires --allow-execution")
    native = load_native()
    native.validate_frozen_case_universe()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)
    input_text = native.render_uvspec_input(
        data_dir=data_dir,
        atmosphere_file=atmosphere_file,
        wavelength_grid_file=wavelength_grid_file,
        target_altitude_deg=CASE["targetAltitudeDeg"],
        observer_elevation_m=CASE["observerElevationM"],
        aod550=CASE["aod550"],
    )
    if "sza 0.00000000\n" not in input_text:
        raise DiagnosticRefusal("exact-zenith diagnostic did not render sza 0")
    completed = subprocess.run(
        [str(uvspec)], input=input_text, text=True, capture_output=True,
        check=False, timeout=180,
    )
    (output_dir / "case.inp").write_text(input_text, encoding="utf-8")
    (output_dir / "case.stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (output_dir / "case.stderr.txt").write_text(completed.stderr, encoding="utf-8")
    if completed.returncode != 0:
        raise DiagnosticRefusal(f"uvspec diagnostic failed rc={completed.returncode}")
    summary = summarize_stdout_grid(completed.stdout)
    summary.update({
        "solver": "sdisort",
        "scatteringOrder": 1,
        "solverInvocationCount": 1,
        "inputSha256": sha256_bytes(input_text.encode("utf-8")),
        "stdoutSha256": sha256_bytes(completed.stdout.encode("utf-8")),
        "stderrSha256": sha256_bytes(completed.stderr.encode("utf-8")),
    })
    (output_dir / "grid-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--allow-execution", action="store_true")
    parser.add_argument("--uvspec", type=Path)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--atmosphere-file", type=Path)
    parser.add_argument("--wavelength-grid-file", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if not args.execute:
        native = load_native()
        native.validate_frozen_case_universe()
        print(json.dumps({
            "status": "REVIEW_ONLY_NO_SOLVER_EXECUTION",
            "stageId": "native-stellar-zenith-v3-exact90-grid-diagnostic-v1",
            "case": CASE,
            "protectedHoldoutOpened": False,
        }, sort_keys=True))
        return 0
    required = [args.uvspec, args.data_dir, args.atmosphere_file,
                args.wavelength_grid_file, args.output_dir]
    if any(x is None for x in required):
        raise DiagnosticRefusal("execution requires all explicit paths")
    summary = execute(
        uvspec=args.uvspec, data_dir=args.data_dir,
        atmosphere_file=args.atmosphere_file,
        wavelength_grid_file=args.wavelength_grid_file,
        output_dir=args.output_dir, allow_execution=args.allow_execution,
    )
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
