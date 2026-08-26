#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
from pathlib import Path
from typing import Any

STAGE_ID = "jerusalem-tishrei-elevated-site-smoke-v2"
BATCH_ID = "jerusalem-tishrei-elevated-site-smoke-v2"
SOURCE_MANIFEST = Path("experiments/jerusalem-tishrei-direct-mystic-v1/manifest.proposal.json")
SOURCE_AUTHORIZATION = Path("experiments/jerusalem-tishrei-direct-mystic-v1/authorization.cross-geometry.json")
BASE_ADAPTER = Path("experiments/mystic-batch-v1/cross_geometry_adapter.py")
GENERIC_EXECUTION_ADAPTER = Path("experiments/mystic-batch-v1/cross_geometry_execution_adapter.py")
ELEVATION_ADAPTER = Path("experiments/mystic-batch-v1/twilight_surrogate_tier1_execution_adapter.py")
SOURCE_CASE_BY_METHOD = {
    "reference-vroom": "jtm-tishrei-gamcyg-vroom-b1",
    "alis": "jtm-tishrei-gamcyg-alis-b1",
}
EXPECTED_GEOMETRY_ID = "tishrei-gamma-cyg-hr7796"
EXPECTED_V1_RUN_ID = 33003385601
EXPECTED_V1_AUTH_COMMIT = "64e4515ebb2fb53c93490a6fe1370ceb7e782206"
EXPECTED_V1_KEY = "jerusalem-tishrei-direct-mystic-v1:diagnostic:1"
EXPECTED_REPAIR_SOURCE_HEAD = "fd990dae5007b1a579424bfceb1aa93bb6c2068c"


class SmokeAdapterError(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SmokeAdapterError(f"expected JSON object: {path}")
    return value


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SmokeAdapterError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def near(a: Any, b: float, tol: float = 1e-12) -> bool:
    return isinstance(a, (int, float)) and not isinstance(a, bool) and math.isfinite(float(a)) and abs(float(a) - b) <= tol


def validate_smoke_manifest(smoke: dict[str, Any]) -> None:
    required = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "batchId": BATCH_ID,
        "status": "PREREGISTERED_INFRASTRUCTURE_SMOKE_NO_EXECUTION",
        "infrastructureOnly": True,
        "scientificExecution": False,
        "scientificDiagnostic": False,
        "scientificUseProhibited": True,
        "successDoesNotAuthorizeScientificExecution": True,
        "successDoesNotAuthorizeProduction": True,
    }
    stale = {k: (smoke.get(k), v) for k, v in required.items() if smoke.get(k) != v}
    if stale:
        raise SmokeAdapterError(f"smoke header changed: {stale}")
    source = smoke.get("sourceScientificPackage") or {}
    source_required = {
        "manifestPath": SOURCE_MANIFEST.as_posix(),
        "authorizationPath": SOURCE_AUTHORIZATION.as_posix(),
        "failedWorkflowRunId": EXPECTED_V1_RUN_ID,
        "consumedAuthorizationCommit": EXPECTED_V1_AUTH_COMMIT,
        "consumedAuthorizationOrdinal": 1,
        "consumedExecutionKey": EXPECTED_V1_KEY,
        "repairSourceHeadSha": EXPECTED_REPAIR_SOURCE_HEAD,
        "repairPr": 425,
    }
    source_stale = {k: (source.get(k), v) for k, v in source_required.items() if source.get(k) != v}
    if source_stale:
        raise SmokeAdapterError(f"source provenance changed: {source_stale}")
    limits = smoke.get("limits") or {}
    if limits != {
        "caseCount": 2,
        "maximumParallel": 2,
        "photonHistoriesPerCase": 10000,
        "maximumConfiguredPhotonHistoriesSum": 20000,
        "perCaseTimeoutSeconds": 300,
    }:
        raise SmokeAdapterError(f"smoke limits changed: {limits}")
    cases = smoke.get("cases")
    if not isinstance(cases, list) or len(cases) != 2:
        raise SmokeAdapterError("smoke must contain exactly two cases")
    if [case.get("ordinal") for case in cases] != [1, 2]:
        raise SmokeAdapterError("smoke ordinals changed")
    if {case.get("method") for case in cases} != {"reference-vroom", "alis"}:
        raise SmokeAdapterError("smoke must contain exactly VROOM and ALIS")
    if any(case.get("photonHistories") != 10000 for case in cases):
        raise SmokeAdapterError("smoke photon count changed")
    if len({case.get("seed") for case in cases}) != 2:
        raise SmokeAdapterError("smoke seeds must be unique")
    if sum(int(case.get("photonHistories", 0)) for case in cases) != 20000:
        raise SmokeAdapterError("smoke photon sum changed")
    geometry = smoke.get("frozenGeometry") or {}
    exact_geometry = {
        "geometryId": EXPECTED_GEOMETRY_ID,
        "target": {"name": "37 Gam Cyg", "catalogId": "HR 7796"},
        "sunDepressionDeg": 5.2416836635666755,
        "targetAltitudeDeg": 65.34228371339654,
        "relativeAzimuthDeg": 148.9564384037443,
        "observerElevationM": 800,
        "aod550": 0.22,
        "surfaceAlbedo": 0.15,
        "atmosphere": "AFGLUS",
        "mcSpherical": "1D",
        "molecularAbsorption": "crs",
    }
    if geometry != exact_geometry:
        raise SmokeAdapterError(f"smoke geometry changed: {geometry}")


def validate_consumed_v1(root: Path, smoke: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    source_manifest_path = root / Path(smoke["sourceScientificPackage"]["manifestPath"])
    source_auth_path = root / Path(smoke["sourceScientificPackage"]["authorizationPath"])
    source = load_json(source_manifest_path)
    auth = load_json(source_auth_path)
    if source.get("batchId") != "jerusalem-tishrei-three-star-direct-mystic-v1":
        raise SmokeAdapterError("wrong source scientific batch")
    event = source.get("preregisteredEvent") or {}
    if not near(event.get("sunDepressionDeg"), 5.2416836635666755):
        raise SmokeAdapterError("source event depression changed")
    if not near((event.get("atmosphere") or {}).get("aod550"), 0.22):
        raise SmokeAdapterError("source AOD550 changed")
    if (event.get("threeStarSemantics") or {}).get("fieldFactorBaseline") != 3.14:
        raise SmokeAdapterError("source F=3.14 changed")
    expected_auth = {
        "authorized": False,
        "scientificExecution": False,
        "scientificDiagnostic": False,
        "consumed": True,
        "authorizationOrdinal": 1,
        "executionKey": EXPECTED_V1_KEY,
        "exactAuthorizationCommit": EXPECTED_V1_AUTH_COMMIT,
    }
    stale = {k: (auth.get(k), v) for k, v in expected_auth.items() if auth.get(k) != v}
    if stale:
        raise SmokeAdapterError(f"v1 authorization is not exact consumed archive: {stale}")
    if str(EXPECTED_V1_RUN_ID) not in str(auth.get("note", "")):
        raise SmokeAdapterError("consumed v1 authorization no longer records failed run")
    return source, auth


def physical_projection(inputs: dict[str, Any]) -> dict[str, Any]:
    return {
        key: inputs[key]
        for key in (
            "sunDepressionDeg",
            "targetAltitudeDeg",
            "relativeAzimuthDeg",
            "observerElevationM",
            "aod550",
            "wavelengthDomainNm",
            "diagnosticNodesNm",
            "molecularAbsorption",
            "mcSpherical",
            "alisSpectralImportanceSamplingNm",
            "albedo",
            "dataPaths",
            "method",
        )
    }


def prepare_case(
    smoke_manifest_path: Path,
    runtime_report_path: Path,
    case_id: str,
    data_dir: Path,
    repository_root: Path,
    output_root: Path,
) -> dict[str, Any]:
    root = repository_root.resolve()
    smoke = load_json(smoke_manifest_path)
    validate_smoke_manifest(smoke)
    source, _auth = validate_consumed_v1(root, smoke)
    base = load_module("tishrei_smoke_base_adapter", root / BASE_ADAPTER)
    generic_execution = load_module("tishrei_smoke_generic_execution_adapter", root / GENERIC_EXECUTION_ADAPTER)
    elevation = load_module("tishrei_smoke_elevation_adapter", root / ELEVATION_ADAPTER)
    runtime = load_json(runtime_report_path)
    generic_execution.validate_runtime(source, runtime)

    matches = [case for case in smoke["cases"] if case.get("caseId") == case_id]
    if len(matches) != 1:
        raise SmokeAdapterError(f"smoke case must occur exactly once: {case_id}")
    smoke_case = matches[0]
    method = smoke_case["method"]
    source_case, geometry = base.resolve_case(source, SOURCE_CASE_BY_METHOD[method])
    if geometry.get("geometryId") != EXPECTED_GEOMETRY_ID:
        raise SmokeAdapterError("source case did not resolve frozen Gamma Cyg geometry")
    source_inputs = base.normalized_inputs(source, source_case, geometry)
    synthetic_case = {
        "caseId": case_id,
        "groupId": geometry["geometryId"],
        "method": method,
        "block": 1,
        "seed": smoke_case["seed"],
        "photonHistories": smoke_case["photonHistories"],
    }
    smoke_inputs = base.normalized_inputs(source, synthetic_case, geometry)
    if physical_projection(smoke_inputs) != physical_projection(source_inputs):
        raise SmokeAdapterError("smoke changed frozen physical/numerical inputs")
    if smoke_inputs["photonHistories"] != 10000:
        raise SmokeAdapterError("smoke photon count was not applied")
    if smoke_inputs["seed"] != smoke_case["seed"]:
        raise SmokeAdapterError("smoke seed was not applied")

    case_dir = output_root / case_id
    case_dir.mkdir(parents=True, exist_ok=False)
    base_text = base.render_input(smoke_inputs, data_dir.resolve(), root, case_dir.resolve())
    corrected_text, site_altitude_km, atmosphere_grid_km = elevation.apply_ground_site_atm_z_grid(
        base_text,
        smoke_inputs["observerElevationM"],
    )
    if base_text.splitlines().count("zout 0.800000") != 1:
        raise SmokeAdapterError("smoke baseline did not reproduce old 0.8 km absolute zout")
    lines = corrected_text.splitlines()
    if lines.count("zout 0.000000") != 1 or sum(line.startswith("atm_z_grid ") for line in lines) != 1:
        raise SmokeAdapterError("smoke repaired elevation representation malformed")
    if abs(site_altitude_km - 0.8) > 1e-12 or not atmosphere_grid_km or abs(atmosphere_grid_km[0] - 0.8) > 1e-12:
        raise SmokeAdapterError("smoke site altitude/grid bottom changed")
    if corrected_text.count("aerosol_set_tau_at_wvl 550 0.220000") != 1:
        raise SmokeAdapterError("smoke AOD550 binding changed")
    if "altitude " in corrected_text or "mc_elevation_file" in corrected_text:
        raise SmokeAdapterError("smoke emitted forbidden elevation shortcut")

    input_path = case_dir / "input-resolved.txt"
    input_path.write_text(corrected_text, encoding="utf-8", newline="\n")
    prepared = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "PREPARED_INFRASTRUCTURE_SMOKE_ONLY",
        "infrastructureOnly": True,
        "scientificUseProhibited": True,
        "caseId": case_id,
        "method": method,
        "seed": smoke_case["seed"],
        "photonHistories": smoke_case["photonHistories"],
        "sourceScientificCaseId": source_case["caseId"],
        "sourceScientificManifestRawSha256": raw_sha256(root / SOURCE_MANIFEST),
        "sourceConsumedAuthorizationRawSha256": raw_sha256(root / SOURCE_AUTHORIZATION),
        "smokeManifestRawSha256": raw_sha256(smoke_manifest_path),
        "runtimeReportRawSha256": raw_sha256(runtime_report_path),
        "baseInputBeforeElevationRepairSha256": text_sha256(base_text),
        "inputResolvedSha256": text_sha256(corrected_text),
        "observerElevationM": 800.0,
        "observerElevationMechanism": "atm_z_grid",
        "siteAltitudeKm": site_altitude_km,
        "zoutKmAboveLocalSurface": 0.0,
        "atmosphereGridLevelCount": len(atmosphere_grid_km),
        "atmosphereGridBottomKm": atmosphere_grid_km[0],
        "atmosphereGridTopKm": atmosphere_grid_km[-1],
        "inputPath": str(input_path),
        "boundary": "infrastructure smoke input only; low-photon output is prohibited from scientific interpretation",
    }
    (case_dir / "smoke-prepared.json").write_text(json.dumps(prepared, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return prepared
