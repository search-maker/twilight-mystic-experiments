#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

BATCH_ID = "jerusalem-tishrei-three-star-direct-mystic-v1"
EXPECTED_AOD550 = 0.22
EXPECTED_OBSERVER_ELEVATION_M = 800.0
AOD550_DIRECTIVE_PREFIX = "aerosol_set_tau_at_wvl 550 "
GENERIC_ADAPTER = Path(__file__).parents[1] / "mystic-batch-v1" / "cross_geometry_execution_adapter.py"
ELEVATION_ADAPTER = Path(__file__).parents[1] / "mystic-batch-v1" / "twilight_surrogate_tier1_execution_adapter.py"


class TishreiAdapterRefusal(RuntimeError):
    pass


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise TishreiAdapterRefusal(f"cannot load reviewed adapter: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_generic_adapter():
    return _load_module("tishrei_generic_cross_geometry_execution_adapter", GENERIC_ADAPTER)


def load_elevation_adapter():
    return _load_module("tishrei_reviewed_ground_site_elevation_adapter", ELEVATION_ADAPTER)


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def validate_rendered_aod550_binding(text: str, expected_aod550: Any) -> None:
    try:
        aod = float(expected_aod550)
    except (TypeError, ValueError) as exc:
        raise TishreiAdapterRefusal(f"invalid normalized AOD550: {expected_aod550}") from exc
    if abs(aod - EXPECTED_AOD550) > 1e-12:
        raise TishreiAdapterRefusal(f"Tishrei AOD550 changed: expected {EXPECTED_AOD550}, got {aod}")
    expected = f"{AOD550_DIRECTIVE_PREFIX}{aod:.6f}"
    directives = [line.strip() for line in text.splitlines() if line.strip().startswith("aerosol_set_tau_at_wvl")]
    if directives != [expected]:
        raise TishreiAdapterRefusal(f"rendered AOD550 binding mismatch: expected exactly {expected!r}, got {directives!r}")


def validate_ground_site_rendering(
    base_text: str,
    corrected_text: str,
    observer_elevation_m: Any,
    site_altitude_km: float,
    atmosphere_grid_km: list[float],
) -> None:
    try:
        elevation_m = float(observer_elevation_m)
    except (TypeError, ValueError) as exc:
        raise TishreiAdapterRefusal(f"invalid observer elevation: {observer_elevation_m}") from exc
    if abs(elevation_m - EXPECTED_OBSERVER_ELEVATION_M) > 1e-12:
        raise TishreiAdapterRefusal(
            f"Tishrei observer elevation changed: expected {EXPECTED_OBSERVER_ELEVATION_M}, got {elevation_m}"
        )
    if base_text.splitlines().count("zout 0.800000") != 1:
        raise TishreiAdapterRefusal("unexpected pre-repair base elevation representation")
    if abs(site_altitude_km - 0.8) > 1e-12:
        raise TishreiAdapterRefusal(f"reviewed elevation adapter returned wrong site altitude: {site_altitude_km}")
    if not atmosphere_grid_km or abs(float(atmosphere_grid_km[0]) - 0.8) > 1e-12:
        raise TishreiAdapterRefusal("atm_z_grid does not start at the frozen 0.8 km site altitude")
    lines = corrected_text.splitlines()
    grid_lines = [line for line in lines if line.startswith("atm_z_grid ")]
    if len(grid_lines) != 1 or lines.count("zout 0.000000") != 1:
        raise TishreiAdapterRefusal("corrected input lacks exact atm_z_grid/local-surface zout representation")
    if any(line.startswith("zout 0.800000") for line in lines):
        raise TishreiAdapterRefusal("absolute zout 0.8 survived elevation repair")
    if any(line.startswith("altitude ") or line.startswith("mc_elevation_file ") for line in lines):
        raise TishreiAdapterRefusal("forbidden elevation shortcut emitted")


def prepare_case(
    proposal_path: Path,
    runtime_report_path: Path,
    case_id: str,
    data_dir: Path,
    repository_root: Path,
    output_dir: Path,
) -> dict[str, Any]:
    generic = load_generic_adapter()
    elevation = load_elevation_adapter()
    prepared = generic.prepare_case(
        proposal_path,
        runtime_report_path,
        case_id,
        data_dir,
        repository_root,
        output_dir,
    )
    if prepared.get("batchId") != BATCH_ID:
        raise TishreiAdapterRefusal(f"wrong batchId: {prepared.get('batchId')}")
    inputs = prepared.get("inputs")
    if not isinstance(inputs, dict):
        raise TishreiAdapterRefusal("normalized inputs missing from generic prepared record")
    input_path = Path(prepared.get("inputPath", ""))
    if not input_path.is_file():
        raise TishreiAdapterRefusal(f"resolved input missing: {input_path}")

    base_text = input_path.read_text(encoding="utf-8")
    validate_rendered_aod550_binding(base_text, inputs.get("aod550"))
    base_input_sha256 = text_sha256(base_text)
    if prepared.get("inputResolvedSha256") != base_input_sha256:
        raise TishreiAdapterRefusal("generic prepared input hash does not match rendered base input")

    corrected_text, site_altitude_km, atmosphere_grid_km = elevation.apply_ground_site_atm_z_grid(
        base_text,
        inputs.get("observerElevationM"),
    )
    validate_ground_site_rendering(
        base_text,
        corrected_text,
        inputs.get("observerElevationM"),
        site_altitude_km,
        atmosphere_grid_km,
    )
    validate_rendered_aod550_binding(corrected_text, inputs.get("aod550"))

    corrected_sha256 = text_sha256(corrected_text)
    input_path.write_text(corrected_text, encoding="utf-8", newline="\n")
    prepared.update(
        {
            "status": "PREPARED_FOR_ONE_AUTHORIZED_CASE_WITH_REVIEWED_GROUND_SITE_ELEVATION",
            "baseInputResolvedSha256BeforeElevationRepair": base_input_sha256,
            "inputResolvedSha256": corrected_sha256,
            "observerElevationSemantics": "site-altitude-above-sea-level-via-atm-z-grid; sensor-at-local-surface",
            "observerElevationMechanism": "atm_z_grid",
            "siteAltitudeKm": site_altitude_km,
            "zoutKmAboveLocalSurface": 0.0,
            "atmosphereGridKm": atmosphere_grid_km,
            "reviewedElevationAdapterPath": ELEVATION_ADAPTER.as_posix(),
            "elevationRepairBoundary": (
                "representation-only repair after failed authorization-1 run: frozen observer elevation remains 800 m; "
                "AFGLUS is truncated/regridded with site altitude as the bottom atm_z_grid level and zout is local-surface 0 km"
            ),
        }
    )
    prepared_path = input_path.parent / "cross-geometry-prepared.json"
    prepared_path.write_text(
        json.dumps(prepared, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return prepared
