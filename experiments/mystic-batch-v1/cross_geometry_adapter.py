#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

STAGE_ID = "cross-geometry-pilot-v1"
ADAPTER_ID = "mystic-cross-geometry-v1"
METHODS = {"reference-vroom", "alis"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class ProposalRefusal(RuntimeError):
    pass


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ProposalRefusal(f"expected JSON object: {path}")
    return value


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def require_number(value: Any, name: str, minimum: float, maximum: float) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)):
        raise ProposalRefusal(f"{name} must be finite")
    number = float(value)
    if not minimum <= number <= maximum:
        raise ProposalRefusal(f"{name} outside [{minimum}, {maximum}]")
    return number


def rooted_path(spec: Any, name: str) -> dict[str, str]:
    if not isinstance(spec, dict) or spec.get("root") not in {"libRadtranData", "repository"}:
        raise ProposalRefusal(f"invalid rooted path: {name}")
    path = spec.get("path")
    if not isinstance(path, str) or not path or Path(path).is_absolute() or ".." in Path(path).parts:
        raise ProposalRefusal(f"invalid relative path: {name}")
    return {"root": spec["root"], "path": Path(path).as_posix()}


def validate_manifest(manifest: dict[str, Any]) -> None:
    required = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "mode": "scientific-proposal",
        "proposalOnly": True,
        "scientificExecution": False,
        "successDoesNotAuthorizeProduction": True,
        "adapterId": ADAPTER_ID,
    }
    stale = {key: (manifest.get(key), expected) for key, expected in required.items() if manifest.get(key) != expected}
    if stale:
        raise ProposalRefusal(f"manifest header mismatch: {stale}")
    runtime = manifest.get("runtime")
    if not isinstance(runtime, dict):
        raise ProposalRefusal("runtime missing")
    for field in ("uvspecSha256", "uvspecHelpSha256", "libRadtranDataTreeSha256", "atmosphereSha256", "runtimeLockRawSha256"):
        if not isinstance(runtime.get(field), str) or not SHA256_RE.fullmatch(runtime[field]):
            raise ProposalRefusal(f"invalid runtime hash: {field}")


def geometry_map(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    geometries = manifest.get("geometries")
    if not isinstance(geometries, list):
        raise ProposalRefusal("geometries must be an array")
    result: dict[str, dict[str, Any]] = {}
    for geometry in geometries:
        if not isinstance(geometry, dict) or not isinstance(geometry.get("geometryId"), str):
            raise ProposalRefusal("invalid geometry")
        geometry_id = geometry["geometryId"]
        if geometry_id in result:
            raise ProposalRefusal(f"duplicate geometry: {geometry_id}")
        result[geometry_id] = geometry
    return result


def resolve_case(manifest: dict[str, Any], case_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    cases = manifest.get("cases")
    if not isinstance(cases, list):
        raise ProposalRefusal("cases must be an array")
    matches = [case for case in cases if isinstance(case, dict) and case.get("caseId") == case_id]
    if len(matches) != 1:
        raise ProposalRefusal(f"case must occur exactly once: {case_id}")
    case = matches[0]
    method = case.get("method")
    if method not in METHODS:
        raise ProposalRefusal(f"unsupported method: {method}")
    geometries = geometry_map(manifest)
    group_id = case.get("groupId")
    if group_id not in geometries:
        raise ProposalRefusal(f"case group has no geometry: {group_id}")
    return case, geometries[group_id]


def resolve_path(spec: dict[str, str], data_dir: Path, repository_root: Path) -> Path:
    root = data_dir if spec["root"] == "libRadtranData" else repository_root
    path = (root / spec["path"]).resolve()
    if not path.is_file():
        raise ProposalRefusal(f"input file missing: {path}")
    return path


def normalized_inputs(manifest: dict[str, Any], case: dict[str, Any], geometry: dict[str, Any]) -> dict[str, Any]:
    frozen = manifest.get("frozenInputs")
    if not isinstance(frozen, dict):
        raise ProposalRefusal("frozenInputs missing")
    paths = frozen.get("dataPaths")
    if not isinstance(paths, dict):
        raise ProposalRefusal("dataPaths missing")
    photons = case.get("photonHistories")
    seed = case.get("seed")
    if not isinstance(photons, int) or photons < 1 or not isinstance(seed, int) or seed < 1:
        raise ProposalRefusal("invalid seed or photons")
    return {
        "caseId": case["caseId"],
        "groupId": case["groupId"],
        "method": case["method"],
        "block": case["block"],
        "seed": seed,
        "photonHistories": photons,
        "sunDepressionDeg": require_number(geometry.get("sunDepressionDeg"), "sunDepressionDeg", 0.0, 30.0),
        "targetAltitudeDeg": require_number(geometry.get("targetAltitudeDeg"), "targetAltitudeDeg", 0.0, 90.0),
        "relativeAzimuthDeg": require_number(geometry.get("relativeAzimuthDeg"), "relativeAzimuthDeg", 0.0, 360.0),
        "observerElevationM": require_number(geometry.get("observerElevationM"), "observerElevationM", 0.0, 10000.0),
        "aod550": require_number(geometry.get("aod550"), "aod550", 0.0, 5.0),
        "albedo": require_number(frozen.get("albedo"), "albedo", 0.0, 1.0),
        "wavelengthDomainNm": frozen.get("wavelengthDomainNm"),
        "diagnosticNodesNm": frozen.get("diagnosticNodesNm"),
        "molecularAbsorption": frozen.get("molecularAbsorption"),
        "mcSpherical": frozen.get("mcSpherical"),
        "alisSpectralImportanceSamplingNm": require_number(
            frozen.get("alisSpectralImportanceSamplingNm"),
            "alisSpectralImportanceSamplingNm",
            380.0,
            780.0,
        ),
        "solarFlux": rooted_path(paths.get("solarFlux"), "solarFlux"),
        "wavelengthGrid": rooted_path(paths.get("wavelengthGrid"), "wavelengthGrid"),
        "atmosphere": rooted_path(paths.get("atmosphere"), "atmosphere"),
    }


def render_input(inputs: dict[str, Any], data_dir: Path, repository_root: Path, case_dir: Path) -> str:
    if inputs["molecularAbsorption"] != "crs" or inputs["mcSpherical"] != "1D":
        raise ProposalRefusal("unsupported molecular absorption or spherical mode")
    domain = inputs["wavelengthDomainNm"]
    nodes = inputs["diagnosticNodesNm"]
    if domain != [380, 780] or not isinstance(nodes, list) or not nodes:
        raise ProposalRefusal("unsupported wavelength contract")
    solar_flux = resolve_path(inputs["solarFlux"], data_dir, repository_root)
    atmosphere = resolve_path(inputs["atmosphere"], data_dir, repository_root)
    wavelength_grid = resolve_path(inputs["wavelengthGrid"], data_dir, repository_root)
    sza = 90.0 + inputs["sunDepressionDeg"]
    umu = -math.sin(math.radians(inputs["targetAltitudeDeg"]))
    lines = [
        f"data_files_path {data_dir.resolve()}",
        f"atmosphere_file {atmosphere}",
        f"source solar {solar_flux}",
        "mol_abs_param crs",
    ]
    if inputs["method"] == "reference-vroom":
        lines.append(f"wavelength_grid_file {wavelength_grid}")
    lines.extend([
        "wavelength 380 780",
        f"sza {sza:.6f}",
        "phi0 0.00",
        "rte_solver mystic",
        "mc_spherical 1D",
        f"mc_photons {inputs['photonHistories']}",
        "mc_vroom on" if inputs["method"] == "reference-vroom" else "mc_vroom off",
        "mc_std",
        f"mc_randomseed {inputs['seed']}",
        f"mc_basename {(case_dir / 'mc').resolve()}",
    ])
    if inputs["method"] == "alis":
        lines.append(f"mc_spectral_is {inputs['alisSpectralImportanceSamplingNm']:.1f}")
    lines.extend([
        f"albedo {inputs['albedo']:.6f}",
        "aerosol_default",
        f"aerosol_set_tau_at_wvl 550 {inputs['aod550']:.6f}",
        f"zout {inputs['observerElevationM'] / 1000.0:.6f}",
        f"umu {umu:.8f}",
        f"phi {inputs['relativeAzimuthDeg']:.6f}",
        "quiet",
    ])
    return "\n".join(lines) + "\n"


def prepare_case(manifest_path: Path, case_id: str, data_dir: Path, repository_root: Path, output_dir: Path) -> dict[str, Any]:
    manifest = load(manifest_path)
    validate_manifest(manifest)
    case, geometry = resolve_case(manifest, case_id)
    inputs = normalized_inputs(manifest, case, geometry)
    case_dir = output_dir / case_id
    case_dir.mkdir(parents=True, exist_ok=False)
    text = render_input(inputs, data_dir, repository_root, case_dir)
    input_path = case_dir / "input-resolved.txt"
    input_path.write_text(text)
    proposal = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
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
        "boundary": "exact input rendering only; no syntax check, uvspec process, or solver execution",
    }
    (case_dir / "case-proposal.json").write_text(dump(proposal))
    return proposal


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(dump(prepare_case(args.manifest, args.case_id, args.data_dir, args.repository_root, args.output_dir)), end="")
        return 0
    except Exception as exc:
        print(dump({"status": "REFUSED", "stageId": STAGE_ID, "reason": str(exc)}), end="", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
