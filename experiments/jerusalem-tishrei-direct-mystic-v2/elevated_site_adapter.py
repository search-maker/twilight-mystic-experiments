#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

PACKAGE = Path("experiments/jerusalem-tishrei-direct-mystic-v2")
GENERIC_ADAPTER = Path("experiments/mystic-batch-v1/cross_geometry_adapter.py")
BATCH_ID = "jerusalem-tishrei-three-star-direct-mystic-v2"
ADAPTER_ID = "jerusalem-tishrei-elevated-site-v2"
SITE_ALTITUDE_KM = 0.8
SENSOR_ALTITUDE_ABOVE_SURFACE_KM = 0.0
AOD550 = 0.22
REQUIRED_ALTITUDE = "altitude 0.800000"
REQUIRED_ZOUT = "zout 0.000000"
FORBIDDEN_V1_ZOUT = "zout 0.800000"
REQUIRED_AOD = "aerosol_set_tau_at_wvl 550 0.220000"


class V2Refusal(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise V2Refusal(f"expected JSON object: {path}")
    return value


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("generic_cross_geometry_adapter", path)
    if spec is None or spec.loader is None:
        raise V2Refusal(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_v2_manifest(manifest: dict[str, Any], generic: Any) -> None:
    generic.validate_manifest(manifest)
    if manifest.get("batchId") != BATCH_ID:
        raise V2Refusal("wrong v2 batchId")
    revision = manifest.get("revisionReason") or {}
    if revision.get("supersedesBatchId") != "jerusalem-tishrei-three-star-direct-mystic-v1":
        raise V2Refusal("v2 must explicitly supersede failed v1")
    if revision.get("supersededWorkflowRunId") != 33003385601 or revision.get("retryOfV1") is not False:
        raise V2Refusal("v2 must be a new experiment, not a v1 retry")
    frozen = manifest.get("frozenInputs") or {}
    vertical = frozen.get("verticalGeometryContract") or {}
    expected = {
        "siteAltitudeKmAboveSeaLevel": SITE_ALTITUDE_KM,
        "sensorAltitudeKmAboveSurface": SENSOR_ALTITUDE_ABOVE_SURFACE_KM,
        "requiredAltitudeDirective": REQUIRED_ALTITUDE,
        "requiredZoutDirective": REQUIRED_ZOUT,
        "forbiddenLegacyDirective": FORBIDDEN_V1_ZOUT,
        "aod550Reference": "integral from user-defined altitude to TOA",
        "aerosolProfileAtNonzeroAltitude": "default libRadtran behavior: aerosol profile starts at model surface; no aerosol_profile_modtran option",
        "documentationBinding": "libRadtran 2.0.6 User's Guide: altitude, zout, aerosol_set_tau_at_wvl",
    }
    stale = {k: (vertical.get(k), v) for k, v in expected.items() if vertical.get(k) != v}
    if stale:
        raise V2Refusal(f"vertical geometry contract drift: {stale}")
    event = manifest.get("preregisteredEvent") or {}
    if event.get("threeStarSemantics", {}).get("fieldFactorBaseline") != 3.14:
        raise V2Refusal("F=3.14 changed")
    if event.get("sunDepressionDeg") != 5.2416836635666755:
        raise V2Refusal("event solar depression changed")
    if event.get("site", {}).get("observerElevationM") != 800:
        raise V2Refusal("site elevation changed")
    if event.get("atmosphere", {}).get("aod550") != AOD550:
        raise V2Refusal("event AOD550 changed")
    geometries = manifest.get("geometries") or []
    cases = manifest.get("cases") or []
    if len(geometries) != 3 or len(cases) != 12:
        raise V2Refusal("v2 geometry/case count changed")
    if any(g.get("observerElevationM") != 800 or g.get("aod550") != AOD550 for g in geometries):
        raise V2Refusal("geometry elevation/AOD drift")
    if any(not str(c.get("caseId", "")).startswith("jtm2-") for c in cases):
        raise V2Refusal("v2 must use fresh case IDs")
    if any(int(c.get("seed", 0)) < 89000 for c in cases):
        raise V2Refusal("v2 must use fresh seed namespace")
    if sum(int(c.get("photonHistories", 0)) for c in cases) != 240_000_000:
        raise V2Refusal("v2 configured scientific photon sum changed")


def render_input(inputs: dict[str, Any], data_dir: Path, repository_root: Path, case_dir: Path, generic: Any) -> str:
    text = generic.render_input(inputs, data_dir, repository_root, case_dir)
    old = f"zout {float(inputs['observerElevationM']) / 1000.0:.6f}"
    if old != FORBIDDEN_V1_ZOUT or text.count(old) != 1:
        raise V2Refusal(f"unexpected generic vertical directive before v2 rewrite: {old}")
    text = text.replace(old, f"{REQUIRED_ALTITUDE}\n{REQUIRED_ZOUT}", 1)
    if REQUIRED_ALTITUDE not in text or REQUIRED_ZOUT not in text or FORBIDDEN_V1_ZOUT in text:
        raise V2Refusal("v2 elevated-site rewrite failed")
    if text.count(REQUIRED_ALTITUDE) != 1 or text.count(REQUIRED_ZOUT) != 1:
        raise V2Refusal("v2 vertical directives must occur exactly once")
    if REQUIRED_AOD not in text:
        raise V2Refusal("AOD550 must remain explicitly bound at 550 nm")
    if "aerosol_profile_modtran" in text:
        raise V2Refusal("aerosol_profile_modtran is not part of the frozen v2 contract")
    return text


def prepare_case(manifest_path: Path, case_id: str, data_dir: Path, repository_root: Path, output_dir: Path) -> dict[str, Any]:
    generic = load_module(repository_root / GENERIC_ADAPTER)
    manifest = load_json(manifest_path)
    validate_v2_manifest(manifest, generic)
    case, geometry = generic.resolve_case(manifest, case_id)
    inputs = generic.normalized_inputs(manifest, case, geometry)
    case_dir = output_dir / case_id
    case_dir.mkdir(parents=True, exist_ok=False)
    text = render_input(inputs, data_dir, repository_root, case_dir, generic)
    input_path = case_dir / "input-resolved.txt"
    input_path.write_text(text)
    report = {
        "schemaVersion": 1,
        "stageId": "cross-geometry-pilot-v1",
        "adapterId": ADAPTER_ID,
        "status": "PREPARED_NO_SYNTAX_OR_SOLVER",
        "proposalOnly": True,
        "scientificExecution": False,
        "caseId": case_id,
        "groupId": case["groupId"],
        "method": case["method"],
        "manifestRawSha256": raw_sha256(manifest_path),
        "inputResolvedSha256": text_sha256(text),
        "inputs": inputs,
        "verticalGeometry": {
            "siteAltitudeKmAboveSeaLevel": SITE_ALTITUDE_KM,
            "sensorAltitudeKmAboveSurface": SENSOR_ALTITUDE_ABOVE_SURFACE_KM,
            "altitudeDirective": REQUIRED_ALTITUDE,
            "zoutDirective": REQUIRED_ZOUT,
            "legacyZout08Present": FORBIDDEN_V1_ZOUT in text,
            "aodDirective": REQUIRED_AOD,
        },
        "boundary": "exact v2 input rendering only; no syntax check, uvspec process, MYSTIC solver, parameter tuning, or production authorization",
    }
    (case_dir / "case-proposal.json").write_text(dump(report))
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = prepare_case(args.manifest, args.case_id, args.data_dir, args.repository_root.resolve(), args.output_dir)
        print(dump(report), end="")
        return 0
    except Exception as exc:
        print(dump({"status": "REFUSED", "adapterId": ADAPTER_ID, "reason": str(exc)}), end="", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
