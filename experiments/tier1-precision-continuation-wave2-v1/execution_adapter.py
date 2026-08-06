#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

STAGE_ID = "tier1-precision-continuation-wave2-ordinal12-execution-v1"
BASE_ADAPTER = "experiments/mystic-batch-v1/cross_geometry_adapter.py"
ELEVATION_ADAPTER = "experiments/mystic-batch-v1/twilight_surrogate_tier1_execution_adapter.py"
PILOT_MANIFEST = "experiments/mystic-batch-v1/manifest.cross-geometry-pilot.proposal.json"
CASE_COUNT = 32
BLOCKS = (5, 6)


class AdapterRefusal(RuntimeError):
    pass


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AdapterRefusal(f"adapter module unavailable: {path}")
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def apply_ground_site_atm_z_grid(
    rendered: str,
    observer_elevation_m: Any,
    repository_root: Path,
) -> tuple[str, float, list[float]]:
    elevation_path = repository_root / ELEVATION_ADAPTER
    elevation = _module(elevation_path, "wave2_reviewed_elevation_adapter")
    try:
        corrected, site_altitude_km, atmosphere_grid_km = elevation.apply_ground_site_atm_z_grid(
            rendered, observer_elevation_m
        )
    except Exception as exc:
        raise AdapterRefusal(f"reviewed atm_z_grid correction refused input: {exc}") from exc
    lines = [line.strip() for line in corrected.splitlines()]
    if sum(line.startswith("atm_z_grid ") for line in lines) != 1:
        raise AdapterRefusal("corrected input lacks exactly one atm_z_grid line")
    if lines.count("zout 0.000000") != 1:
        raise AdapterRefusal("corrected input lacks exact local-surface zout")
    if any(line.startswith("altitude ") or line.startswith("mc_elevation_file ") for line in lines):
        raise AdapterRefusal("corrected input contains forbidden elevation mechanism")
    if (
        len(atmosphere_grid_km) < 2
        or atmosphere_grid_km[0] != site_altitude_km
        or any(
            atmosphere_grid_km[index] >= atmosphere_grid_km[index + 1]
            for index in range(len(atmosphere_grid_km) - 1)
        )
    ):
        raise AdapterRefusal("corrected atmosphere grid is not strictly ascending")
    return corrected, site_altitude_km, atmosphere_grid_km


def prepare_case(
    manifest_path: Path,
    runtime_report_path: Path,
    case_id: str,
    data_dir: Path,
    repository_root: Path,
    output_root: Path,
) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    runtime = json.loads(runtime_report_path.read_text(encoding="utf-8"))
    if manifest.get("stageId") != STAGE_ID or manifest.get("caseCount") != CASE_COUNT:
        raise AdapterRefusal("execution manifest changed")
    required_runtime = tuple(manifest.get("runtime", {}))
    if any(runtime.get(key) != manifest["runtime"].get(key) for key in required_runtime):
        raise AdapterRefusal("runtime hash drift")
    matches = [case for case in manifest["cases"] if case.get("caseId") == case_id]
    if len(matches) != 1:
        raise AdapterRefusal("case must occur exactly once")
    case = matches[0]
    if case.get("block") not in BLOCKS or case.get("role") not in (
        "surrogate-training",
        "internal-holdout",
    ):
        raise AdapterRefusal("case contract changed")
    pilot_path = repository_root / PILOT_MANIFEST
    pilot = json.loads(pilot_path.read_text(encoding="utf-8"))
    frozen = pilot.get("frozenInputs")
    if not isinstance(frozen, dict):
        raise AdapterRefusal("frozen solver inputs unavailable")
    synthetic_case = dict(case)
    synthetic_case["method"] = "alis"
    synthetic_case["ordinal"] = case["caseOrdinal"]
    geometry = dict(case["geometry"])
    proposal = {
        "frozenInputs": frozen,
        "cases": [synthetic_case],
        "geometries": [geometry],
    }
    base_path = repository_root / BASE_ADAPTER
    base = _module(base_path, "wave2_base_adapter")
    inputs = base.normalized_inputs(proposal, synthetic_case, geometry)
    inputs["alisSpectralImportanceSamplingNm"] = float(case["alisSpectralImportanceSamplingNm"])
    if "observerElevationM" not in inputs:
        raise AdapterRefusal("observer elevation missing from rendered case")
    case_dir = output_root / case_id
    case_dir.mkdir(parents=True, exist_ok=False)
    rendered = base.render_input(
        inputs,
        data_dir.resolve(),
        repository_root.resolve(),
        case_dir.resolve(),
    )
    corrected, site_altitude_km, atmosphere_grid_km = apply_ground_site_atm_z_grid(
        rendered, inputs["observerElevationM"], repository_root
    )
    if corrected.count("mc_randomseed ") != 1 or corrected.count("mc_photons ") != 1:
        raise AdapterRefusal("rendered execution identity is ambiguous")
    if (
        f"mc_randomseed {case['seed']}" not in corrected
        or f"mc_photons {case['photonHistories']}" not in corrected
    ):
        raise AdapterRefusal("rendered seed or photon budget changed")
    input_path = case_dir / "input-resolved.txt"
    input_path.write_text(corrected, encoding="utf-8", newline="\n")
    prepared = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "PREPARED_FOR_EXACTLY_ONE_AUTHORIZED_CASE",
        "caseId": case_id,
        "groupId": case["groupId"],
        "block": case["block"],
        "role": case["role"],
        "seed": case["seed"],
        "photonHistories": case["photonHistories"],
        "observerElevationSemantics": "site-altitude-above-sea-level-via-atm-z-grid; sensor-at-local-surface",
        "observerElevationMechanism": "atm_z_grid",
        "siteAltitudeKm": site_altitude_km,
        "zoutKmAboveLocalSurface": 0.0,
        "atmosphereGridLevelCount": len(atmosphere_grid_km),
        "atmosphereGridBottomKm": atmosphere_grid_km[0],
        "atmosphereGridTopKm": atmosphere_grid_km[-1],
        "manifestRawSha256": raw_sha256(manifest_path),
        "runtimeReportRawSha256": raw_sha256(runtime_report_path),
        "pilotManifestRawSha256": raw_sha256(pilot_path),
        "baseAdapterRawSha256": raw_sha256(base_path),
        "elevationAdapterRawSha256": raw_sha256(repository_root / ELEVATION_ADAPTER),
        "inputResolvedSha256": hashlib.sha256(corrected.encode()).hexdigest(),
        "inputPath": str(input_path),
        "fittingSurfaceExposed": False,
        "boundary": "input rendering only with reviewed atm_z_grid elevated-site representation; no syntax check or solver execution",
    }
    (case_dir / "prepared.json").write_text(
        dump(prepared), encoding="utf-8", newline="\n"
    )
    return prepared
