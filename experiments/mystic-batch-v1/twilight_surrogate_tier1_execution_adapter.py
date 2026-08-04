#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import re
from pathlib import Path
from typing import Any

STAGE_ID = "twilight-surrogate-tier-1-execution-v1"
ADAPTER_ID = "mystic-twilight-tier1-execution-v1"
BASE = Path(__file__).with_name("cross_geometry_adapter.py")
ALLOWED = {500.0, 550.0, 600.0}
ZOUT_LINE_RE = re.compile(r"(?m)^zout\s+[^\n]+$")
ATMOSPHERE_FILE_LINE_RE = re.compile(r"(?m)^atmosphere_file[ \t]+(.+?)[ \t]*$")
FORBIDDEN_ELEVATION_LINE_RE = re.compile(r"(?m)^(?:altitude|mc_elevation_file)\s+[^\n]+$")


class AdapterError(RuntimeError):
    pass


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise AdapterError(f"expected object: {path}")
    return value


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def raw(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def base_module():
    spec = importlib.util.spec_from_file_location("base", BASE)
    if spec is None or spec.loader is None:
        raise AdapterError("base adapter unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_manifest(manifest: dict[str, Any]) -> None:
    required = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "batchId": "twilight-surrogate-space-filling-v1-tier-1",
        "mode": "scientific-proposal",
        "proposalOnly": True,
        "scientificExecution": False,
        "successDoesNotAuthorizeProduction": True,
        "adapterId": ADAPTER_ID,
        "caseSpecificAlisSpectralImportanceSampling": True,
    }
    stale = {
        key: (manifest.get(key), expected)
        for key, expected in required.items()
        if manifest.get(key) != expected
    }
    if stale:
        raise AdapterError(f"manifest mismatch: {stale}")
    cases = manifest.get("cases")
    geometries = manifest.get("geometries")
    if (
        not isinstance(cases, list)
        or len(cases) != 96
        or not isinstance(geometries, list)
        or len(geometries) != 48
    ):
        raise AdapterError("tier-1 count changed")
    if [case.get("ordinal") for case in cases] != list(range(1, 97)):
        raise AdapterError("case ordinals changed")
    if len({case.get("seed") for case in cases}) != 96:
        raise AdapterError("seeds not unique")
    if sum(case.get("photonHistories", 0) for case in cases) != 6_960_000_000:
        raise AdapterError("photon sum changed")
    if any(
        case.get("method") != "alis"
        or float(case.get("alisSpectralImportanceSamplingNm", -1)) not in ALLOWED
        for case in cases
    ):
        raise AdapterError("case ALIS contract changed")


def validate_runtime(manifest: dict[str, Any], report: dict[str, Any]) -> None:
    fields = (
        "uvspecSha256",
        "uvspecHelpSha256",
        "libRadtranDataTreeSha256",
        "atmosphereSha256",
        "runtimeLockRawSha256",
    )
    if (
        report.get("schemaVersion") != 1
        or report.get("stageId") != "mystic-batch-v1"
        or report.get("scientificSolverExecuted") is not False
        or report.get("syntaxCheckExecuted") is not False
    ):
        raise AdapterError("runtime report header changed")
    stale = {
        field: (report.get(field), manifest.get("runtime", {}).get(field))
        for field in fields
        if report.get(field) != manifest.get("runtime", {}).get(field)
    }
    if stale:
        raise AdapterError(f"runtime mismatch: {stale}")


def atmosphere_altitudes_descending(path: Path) -> list[float]:
    if not path.is_file():
        raise AdapterError(f"atmosphere file missing: {path}")
    levels: list[float] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        columns = stripped.split()
        if len(columns) < 2:
            raise AdapterError(f"malformed atmosphere row: {line}")
        try:
            altitude = float(columns[0])
        except ValueError as exc:
            raise AdapterError(f"invalid atmosphere altitude: {columns[0]}") from exc
        if not math.isfinite(altitude):
            raise AdapterError("non-finite atmosphere altitude")
        levels.append(altitude)
    if len(levels) < 2:
        raise AdapterError("atmosphere has fewer than two levels")
    if any(levels[index] <= levels[index + 1] for index in range(len(levels) - 1)):
        raise AdapterError("atmosphere levels must be strictly descending")
    return levels


def forced_grid_ascending(atmosphere: Path, site_altitude_km: float) -> list[float]:
    levels = atmosphere_altitudes_descending(atmosphere)
    if not levels[-1] <= site_altitude_km < levels[0]:
        raise AdapterError("site altitude outside atmosphere grid")
    above = sorted(level for level in levels if level > site_altitude_km)
    grid = [site_altitude_km, *above]
    if len(grid) < 2 or any(grid[index] >= grid[index + 1] for index in range(len(grid) - 1)):
        raise AdapterError("atm_z_grid must be strictly ascending")
    return grid


def apply_ground_site_atm_z_grid(
    rendered: str, observer_elevation_m: Any
) -> tuple[str, float, list[float]]:
    if (
        not isinstance(observer_elevation_m, (int, float))
        or isinstance(observer_elevation_m, bool)
        or not math.isfinite(float(observer_elevation_m))
    ):
        raise AdapterError("observer elevation must be finite")
    elevation_m = float(observer_elevation_m)
    if not 0.0 <= elevation_m <= 10_000.0:
        raise AdapterError("observer elevation outside [0, 10000] m")
    zout_matches = ZOUT_LINE_RE.findall(rendered)
    if len(zout_matches) != 1:
        raise AdapterError(
            f"base input must contain exactly one zout line, found {len(zout_matches)}"
        )
    atmosphere_matches = ATMOSPHERE_FILE_LINE_RE.findall(rendered)
    if len(atmosphere_matches) != 1:
        raise AdapterError(
            "base input must contain exactly one atmosphere_file line, "
            f"found {len(atmosphere_matches)}"
        )
    forbidden = FORBIDDEN_ELEVATION_LINE_RE.findall(rendered)
    if forbidden:
        raise AdapterError(f"base input contains forbidden elevation mechanism: {forbidden}")
    atmosphere = Path(atmosphere_matches[0]).expanduser()
    if not atmosphere.is_absolute():
        raise AdapterError("rendered atmosphere_file must be absolute")
    elevation_km = elevation_m / 1000.0
    grid = forced_grid_ascending(atmosphere, elevation_km)
    grid_line = "atm_z_grid " + " ".join(f"{level:.6f}" for level in grid)
    corrected = ZOUT_LINE_RE.sub(
        f"{grid_line}\nzout 0.000000", rendered, count=1
    )
    actual = corrected.splitlines()
    if sum(line.startswith("atm_z_grid ") for line in actual) != 1:
        raise AdapterError("resolved input lacks exactly one atm_z_grid line")
    if actual.count("zout 0.000000") != 1:
        raise AdapterError("resolved input lacks exact local-surface zout")
    if any(
        line.startswith("altitude ") or line.startswith("mc_elevation_file ")
        for line in actual
    ):
        raise AdapterError("resolved input contains forbidden elevation mechanism")
    return corrected, elevation_km, grid


def prepare_case(
    manifest_path: Path,
    runtime_report_path: Path,
    case_id: str,
    data_dir: Path,
    repository_root: Path,
    output_dir: Path,
) -> dict[str, Any]:
    manifest = load(manifest_path)
    runtime = load(runtime_report_path)
    validate_manifest(manifest)
    validate_runtime(manifest, runtime)
    base = base_module()
    case, geometry = base.resolve_case(manifest, case_id)
    inputs = base.normalized_inputs(manifest, case, geometry)
    inputs["alisSpectralImportanceSamplingNm"] = float(
        case["alisSpectralImportanceSamplingNm"]
    )
    case_dir = output_dir / case_id
    case_dir.mkdir(parents=True, exist_ok=False)
    rendered = base.render_input(
        inputs,
        data_dir.resolve(),
        repository_root.resolve(),
        case_dir.resolve(),
    )
    if "observerElevationM" in inputs:
        text, site_altitude_km, atmosphere_grid_km = apply_ground_site_atm_z_grid(
            rendered, inputs["observerElevationM"]
        )
        elevation_semantics = (
            "site-altitude-above-sea-level-via-atm-z-grid; "
            "sensor-at-local-surface"
        )
        elevation_mechanism = "atm_z_grid"
        zout_km = 0.0
    else:
        # Compatibility for synthetic adapter stubs in frozen contract tests.
        # The real cross-geometry adapter always supplies observerElevationM.
        text = rendered
        site_altitude_km = None
        atmosphere_grid_km = []
        elevation_semantics = "synthetic-test-stub-without-observer-elevation"
        elevation_mechanism = None
        zout_km = None
    path = case_dir / "input-resolved.txt"
    path.write_text(text)
    result = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "adapterId": ADAPTER_ID,
        "status": "PREPARED_FOR_ONE_AUTHORIZED_TIER_1_CASE",
        "caseId": case_id,
        "groupId": case["groupId"],
        "method": "alis",
        "block": case["block"],
        "role": case["role"],
        "alisSpectralImportanceSamplingNm": inputs[
            "alisSpectralImportanceSamplingNm"
        ],
        "observerElevationSemantics": elevation_semantics,
        "observerElevationMechanism": elevation_mechanism,
        "siteAltitudeKm": site_altitude_km,
        "zoutKmAboveLocalSurface": zout_km,
        "atmosphereGridLevelCount": len(atmosphere_grid_km),
        "atmosphereGridBottomKm": (
            atmosphere_grid_km[0] if atmosphere_grid_km else None
        ),
        "atmosphereGridTopKm": (
            atmosphere_grid_km[-1] if atmosphere_grid_km else None
        ),
        "proposalRawSha256": raw(manifest_path),
        "runtimeReportRawSha256": raw(runtime_report_path),
        "baseAdapterRawSha256": raw(BASE),
        "inputResolvedSha256": text_sha(text),
        "inputs": inputs,
        "inputPath": str(path),
        "boundary": (
            "one tier-1 case prepared after runtime validation using the "
            "equivalence-proven atm_z_grid representation; execution remains "
            "delegated to guarded executor"
        ),
    }
    (case_dir / "tier1-prepared.json").write_text(dump(result))
    return result
