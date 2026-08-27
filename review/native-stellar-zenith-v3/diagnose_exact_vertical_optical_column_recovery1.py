#!/usr/bin/env python3
"""Infrastructure-only recovery of exact-vertical optical-column v1.

The sole permitted input-rendering difference is canonical absolute path
resolution for the already-frozen wavelength-grid file.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
V1_PATH = HERE / "diagnose_exact_vertical_optical_column_v1.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


v1 = _load(V1_PATH, "exact_vertical_optical_column_v1_for_recovery1")

STAGE_ID = "native-stellar-zenith-exact-vertical-optical-column-recovery1"
PRIOR_RUN_ID = 33040457601
PRIOR_ARTIFACT_ID = 9633642762
PRIOR_ARTIFACT_DIGEST = "sha256:f2f6f5b0d33518a48d36312b7f4bf18bea4ae22e1ce5fba2e80775c6b063332f"
PRIOR_DISPATCH_SHA = "2663fbc3241b31e095f3fb814cecc5a60e078c0a"
FAILURE_CLASS = "PRE_SOLVER_WAVELENGTH_GRID_RELATIVE_PATH_NOT_FOUND"
EXPECTED_GRID = tuple(range(380, 781))


class RecoveryRefusal(RuntimeError):
    pass


def read_exact_grid(path: Path) -> list[int]:
    if not path.is_file():
        raise RecoveryRefusal(f"wavelength grid missing before execution: {path}")
    values: list[int] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        text = raw.strip()
        if not text:
            continue
        try:
            value = float(text)
        except ValueError as exc:
            raise RecoveryRefusal(f"invalid wavelength-grid row: {raw!r}") from exc
        if value != round(value):
            raise RecoveryRefusal(f"non-integral wavelength-grid row: {value}")
        values.append(int(value))
    if values != list(EXPECTED_GRID):
        raise RecoveryRefusal("wavelength grid is not exact 380..780 inclusive at 1 nm")
    return values


def resolve_same_grid(path: Path) -> Path:
    read_exact_grid(path)
    resolved = path.resolve(strict=True)
    if path.read_bytes() != resolved.read_bytes():
        raise RecoveryRefusal("resolved wavelength-grid bytes differ from requested file")
    return resolved


def render_pair(*, observer_elevation_m: float, aod550: float, data_dir: Path,
                atmosphere_file: Path, wavelength_grid_file: Path) -> dict[str, Any]:
    requested = Path(wavelength_grid_file)
    resolved = resolve_same_grid(requested)
    original = v1.render_uvspec_input(
        observer_elevation_m=observer_elevation_m,
        aod550=aod550,
        data_dir=data_dir,
        atmosphere_file=atmosphere_file,
        wavelength_grid_file=requested,
    )
    recovery = v1.render_uvspec_input(
        observer_elevation_m=observer_elevation_m,
        aod550=aod550,
        data_dir=data_dir,
        atmosphere_file=atmosphere_file,
        wavelength_grid_file=resolved,
    )
    original_lines = original.splitlines()
    recovery_lines = recovery.splitlines()
    if len(original_lines) != len(recovery_lines):
        raise RecoveryRefusal("renderer line count changed")
    differences = [
        (index, left, right)
        for index, (left, right) in enumerate(zip(original_lines, recovery_lines, strict=True))
        if left != right
    ]
    if len(differences) != 1:
        raise RecoveryRefusal(f"recovery renderer differs in {len(differences)} lines, expected 1")
    index, left, right = differences[0]
    prefix = "wavelength_grid_file "
    if not left.startswith(prefix) or not right.startswith(prefix):
        raise RecoveryRefusal("sole renderer difference is not wavelength_grid_file")
    if left != f"{prefix}{requested}":
        raise RecoveryRefusal("original renderer wavelength-grid path drift")
    if right != f"{prefix}{resolved}":
        raise RecoveryRefusal("recovery renderer wavelength-grid path is not canonical absolute path")
    return {
        "originalInput": original,
        "recoveryInput": recovery,
        "differenceLineIndexZeroBased": index,
        "originalGridPath": str(requested),
        "resolvedGridPath": str(resolved),
        "gridSha256": v1.sha256_file(resolved),
        "gridValues": list(EXPECTED_GRID),
    }


def validate_recovery_surface(*, data_dir: Path, atmosphere_file: Path,
                              wavelength_grid_file: Path) -> dict[str, Any]:
    rows = []
    grid_sha = None
    for elevation, aod in v1.CASE_UNIVERSE:
        pair = render_pair(
            observer_elevation_m=elevation,
            aod550=aod,
            data_dir=data_dir,
            atmosphere_file=atmosphere_file,
            wavelength_grid_file=wavelength_grid_file,
        )
        if grid_sha is None:
            grid_sha = pair["gridSha256"]
        elif pair["gridSha256"] != grid_sha:
            raise RecoveryRefusal("grid SHA drift across recovery cases")
        rows.append({
            "observerElevationM": elevation,
            "aod550": aod,
            "differenceLineIndexZeroBased": pair["differenceLineIndexZeroBased"],
            "originalGridPath": pair["originalGridPath"],
            "resolvedGridPath": pair["resolvedGridPath"],
        })
    return {
        "stageId": STAGE_ID,
        "priorRunId": PRIOR_RUN_ID,
        "priorArtifactId": PRIOR_ARTIFACT_ID,
        "priorArtifactDigest": PRIOR_ARTIFACT_DIGEST,
        "priorDispatchSha": PRIOR_DISPATCH_SHA,
        "failureClass": FAILURE_CLASS,
        "soleRecoveryChange": "CANONICAL_ABSOLUTE_WAVELENGTH_GRID_PATH",
        "gridSha256": grid_sha,
        "caseProofs": rows,
        "scientificInputsChanged": False,
        "acceptanceThresholdsChanged": False,
        "protectedHoldoutOpened": False,
        "modelFitPerformed": False,
        "productionAuthorized": False,
    }


def execute_recovery(*, root: Path, uvspec: Path, data_dir: Path, atmosphere_file: Path,
                     wavelength_grid_file: Path, sed_bundle_path: Path, johnson_v_path: Path,
                     output_dir: Path, allow_execution: bool = False) -> dict[str, Any]:
    if allow_execution is not True:
        raise RecoveryRefusal("recovery execution requires explicit allow_execution=True")
    proof = validate_recovery_surface(
        data_dir=data_dir,
        atmosphere_file=atmosphere_file,
        wavelength_grid_file=wavelength_grid_file,
    )
    resolved_grid = resolve_same_grid(Path(wavelength_grid_file))
    result = v1.execute_campaign(
        root=root,
        uvspec=uvspec,
        data_dir=data_dir,
        atmosphere_file=atmosphere_file,
        wavelength_grid_file=resolved_grid,
        sed_bundle_path=sed_bundle_path,
        johnson_v_path=johnson_v_path,
        output_dir=output_dir,
        allow_execution=True,
    )
    result["stageId"] = STAGE_ID
    result["recoveryOf"] = {
        "runId": PRIOR_RUN_ID,
        "artifactId": PRIOR_ARTIFACT_ID,
        "artifactDigest": PRIOR_ARTIFACT_DIGEST,
        "dispatchSha": PRIOR_DISPATCH_SHA,
        "failureClass": FAILURE_CLASS,
    }
    result["recoveryProof"] = proof
    if "claimBoundary" in result:
        result["claimBoundary"]["recoveryOnly"] = True
        result["claimBoundary"]["originalV1ScientificSpectrumCount"] = 0
    summary_path = Path(output_dir) / "exact-vertical-optical-column-recovery1-summary.json"
    summary_path.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--allow-execution", action="store_true")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--uvspec", type=Path)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--atmosphere-file", type=Path)
    parser.add_argument("--wavelength-grid-file", type=Path)
    parser.add_argument("--sed-bundle", type=Path)
    parser.add_argument("--johnson-v", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if not args.execute:
        print(json.dumps({
            "stageId": STAGE_ID,
            "status": "REVIEW_ONLY_NO_SOLVER_EXECUTION",
            "priorRunId": PRIOR_RUN_ID,
            "failureClass": FAILURE_CLASS,
            "soleRecoveryChange": "CANONICAL_ABSOLUTE_WAVELENGTH_GRID_PATH",
            "solverInvocationCount": v1.EXPECTED_SOLVER_CALLS,
            "maxAbsDeltaOpticalDepthLimit": v1.MAX_ABS_DELTA_TAU,
            "maxAbsDeltaAvMagLimit": v1.MAX_ABS_DELTA_AV_MAG,
            "protectedHoldoutOpened": False,
            "productionAuthorized": False,
        }, sort_keys=True))
        return 0
    required = [
        args.uvspec, args.data_dir, args.atmosphere_file, args.wavelength_grid_file,
        args.sed_bundle, args.johnson_v, args.output_dir,
    ]
    if any(value is None for value in required):
        raise RecoveryRefusal("execution requires all explicit bound paths")
    result = execute_recovery(
        root=args.root,
        uvspec=args.uvspec,
        data_dir=args.data_dir,
        atmosphere_file=args.atmosphere_file,
        wavelength_grid_file=args.wavelength_grid_file,
        sed_bundle_path=args.sed_bundle,
        johnson_v_path=args.johnson_v,
        output_dir=args.output_dir,
        allow_execution=args.allow_execution,
    )
    print(json.dumps({"status": result.get("status"), "metrics": result.get("metrics")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
