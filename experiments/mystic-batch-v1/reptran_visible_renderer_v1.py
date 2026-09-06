#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

LEGACY_CROSS = Path(__file__).with_name("cross_geometry_adapter.py")
ELEVATION_HELPER = Path(__file__).with_name("twilight_surrogate_tier1_execution_adapter.py")
CRS_LINE = "mol_abs_param crs"
REPTRAN_LINE = "mol_abs_param reptran"


class ReptranVisibleRendererError(RuntimeError):
    pass


def _load_module(name: str, path: Path):
    if not path.is_file():
        raise ReptranVisibleRendererError(f"required reviewed module missing: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ReptranVisibleRendererError(f"cannot load reviewed module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _legacy_render(
    inputs: dict[str, Any],
    data_dir: Path,
    repository_root: Path,
    case_dir: Path,
) -> str:
    if inputs.get("method") != "alis":
        raise ReptranVisibleRendererError("validated V1 REPTRAN path is ALIS-only")
    if inputs.get("molecularAbsorption") != "reptran":
        raise ReptranVisibleRendererError(
            "successor visible path requires molecularAbsorption='reptran'"
        )
    if inputs.get("mcSpherical") != "1D":
        raise ReptranVisibleRendererError("validated V1 REPTRAN path requires mc_spherical 1D")

    legacy_inputs = dict(inputs)
    legacy_inputs["molecularAbsorption"] = "crs"
    cross = _load_module("reptran_v1_legacy_cross", LEGACY_CROSS)
    rendered = cross.render_input(
        legacy_inputs,
        data_dir.resolve(),
        repository_root.resolve(),
        case_dir.resolve(),
    )
    lines = rendered.splitlines()
    if lines.count(CRS_LINE) != 1 or REPTRAN_LINE in lines:
        raise ReptranVisibleRendererError("legacy molecular-absorption line drift")
    if any(line.startswith("wavelength_grid_file ") for line in lines):
        raise ReptranVisibleRendererError("ALIS path unexpectedly emitted wavelength_grid_file")
    if lines.count("mc_vroom off") != 1:
        raise ReptranVisibleRendererError("ALIS VROOM control drift")
    if sum(line.startswith("mc_spectral_is ") for line in lines) != 1:
        raise ReptranVisibleRendererError("ALIS spectral importance-sampling control drift")
    return rendered


def render_input(
    inputs: dict[str, Any],
    data_dir: Path,
    repository_root: Path,
    case_dir: Path,
) -> str:
    """Render the reviewed visible ALIS path with default REPTRAN absorption.

    Historical CRS renderers stay byte-for-byte untouched.  This successor first
    asks the reviewed legacy renderer to construct every non-absorption directive,
    then performs one guarded line substitution and proves that no second input
    line changed.
    """

    legacy = _legacy_render(inputs, data_dir, repository_root, case_dir)
    legacy_lines = legacy.splitlines()
    reptran_lines = [REPTRAN_LINE if line == CRS_LINE else line for line in legacy_lines]
    differing = [
        (before, after)
        for before, after in zip(legacy_lines, reptran_lines)
        if before != after
    ]
    if differing != [(CRS_LINE, REPTRAN_LINE)]:
        raise ReptranVisibleRendererError(f"REPTRAN structural-difference drift: {differing}")
    if reptran_lines.count(REPTRAN_LINE) != 1 or CRS_LINE in reptran_lines:
        raise ReptranVisibleRendererError("REPTRAN molecular-absorption line not unique")
    return "\n".join(reptran_lines) + "\n"


def render_ground_site_input(
    inputs: dict[str, Any],
    data_dir: Path,
    repository_root: Path,
    case_dir: Path,
) -> tuple[str, dict[str, Any]]:
    """Render REPTRAN plus the already-reviewed local-ground elevation semantics.

    The returned proof compares fully corrected CRS and REPTRAN inputs and refuses
    unless their sole line difference is the molecular-absorption directive.
    No syntax check, uvspec process, RNG initialization, or solver execution occurs.
    """

    legacy = _legacy_render(inputs, data_dir, repository_root, case_dir)
    reptran = render_input(inputs, data_dir, repository_root, case_dir)
    elevation = _load_module("reptran_v1_elevation", ELEVATION_HELPER)
    observer_elevation_m = inputs.get("observerElevationM")
    legacy_corrected, legacy_site_km, legacy_grid = elevation.apply_ground_site_atm_z_grid(
        legacy, observer_elevation_m
    )
    reptran_corrected, site_km, grid = elevation.apply_ground_site_atm_z_grid(
        reptran, observer_elevation_m
    )

    legacy_lines = legacy_corrected.splitlines()
    reptran_lines = reptran_corrected.splitlines()
    if len(legacy_lines) != len(reptran_lines):
        raise ReptranVisibleRendererError("corrected CRS/REPTRAN line-count drift")
    differing = [
        (before, after)
        for before, after in zip(legacy_lines, reptran_lines)
        if before != after
    ]
    if differing != [(CRS_LINE, REPTRAN_LINE)]:
        raise ReptranVisibleRendererError(
            f"corrected CRS/REPTRAN structural-difference drift: {differing}"
        )
    if site_km != legacy_site_km or grid != legacy_grid:
        raise ReptranVisibleRendererError("elevation semantics differ between molecular arms")
    if reptran_lines.count(REPTRAN_LINE) != 1 or CRS_LINE in reptran_lines:
        raise ReptranVisibleRendererError("corrected REPTRAN directive drift")
    if reptran_lines.count("zout 0.000000") != 1:
        raise ReptranVisibleRendererError("local-ground zout drift")
    if sum(line.startswith("atm_z_grid ") for line in reptran_lines) != 1:
        raise ReptranVisibleRendererError("atm_z_grid drift")
    if any(
        line.startswith("altitude ") or line.startswith("mc_elevation_file ")
        for line in reptran_lines
    ):
        raise ReptranVisibleRendererError("forbidden elevation mechanism emitted")

    proof = {
        "schemaVersion": 1,
        "rendererId": "reptran-visible-renderer-v1",
        "molecularAbsorption": "reptran",
        "onlyDifferenceAgainstLegacyCrs": [[CRS_LINE, REPTRAN_LINE]],
        "method": "alis",
        "mcSpherical": "1D",
        "observerElevationMechanism": "atm_z_grid",
        "siteAltitudeKm": site_km,
        "zoutKmAboveLocalSurface": 0.0,
        "atmosphereGridKm": grid,
        "scientificSolverExecuted": False,
        "syntaxCheckExecuted": False,
        "protectedResultOpened": False,
    }
    return reptran_corrected, proof
