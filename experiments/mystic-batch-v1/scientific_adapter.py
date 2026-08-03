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

STAGE_ID = "mystic-batch-v1"
ADAPTER_ID = "mystic-spectral-radiance-v1"
CASE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,79}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class AdapterRefusal(RuntimeError):
    def __init__(self, code: str, reason: str, detail: Any | None = None) -> None:
        super().__init__(reason)
        self.code = code
        self.reason = reason
        self.detail = detail

    def as_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": 1,
            "stageId": STAGE_ID,
            "adapterId": ADAPTER_ID,
            "status": "REFUSED",
            "code": self.code,
            "reason": self.reason,
            "detail": self.detail,
        }


def dump_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise AdapterRefusal("invalid-json", f"cannot read JSON object: {path}", str(exc)) from exc
    if not isinstance(value, dict):
        raise AdapterRefusal("invalid-json-object", f"expected JSON object: {path}")
    return value


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def require_number(value: Any, name: str, minimum: float | None = None, maximum: float | None = None) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)):
        raise AdapterRefusal("invalid-number", f"{name} must be a finite number", value)
    number = float(value)
    if minimum is not None and number < minimum:
        raise AdapterRefusal("number-range", f"{name} must be >= {minimum}", number)
    if maximum is not None and number > maximum:
        raise AdapterRefusal("number-range", f"{name} must be <= {maximum}", number)
    return number


def require_int(value: Any, name: str, minimum: int = 0) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise AdapterRefusal("invalid-integer", f"{name} must be an integer >= {minimum}", value)
    return value


def require_relative_path(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AdapterRefusal("invalid-path", f"{name} must be a non-empty relative path", value)
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise AdapterRefusal("invalid-path", f"{name} must not be absolute or escape its root", value)
    return path.as_posix()


def require_rooted_path(value: Any, name: str) -> dict[str, str]:
    if not isinstance(value, dict):
        raise AdapterRefusal("invalid-path", f"{name} must be an object with root and path", value)
    root = value.get("root")
    if root not in {"libRadtranData", "repository"}:
        raise AdapterRefusal("invalid-path-root", f"{name}.root is unsupported", root)
    return {"root": root, "path": require_relative_path(value.get("path"), f"{name}.path")}


def require_sha256(value: Any, name: str) -> str:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise AdapterRefusal("invalid-sha256", f"{name} must be a lowercase SHA-256 hex digest", value)
    return value


def resolve_case(manifest: dict[str, Any], case_id: str) -> dict[str, Any]:
    if not CASE_ID_RE.fullmatch(case_id):
        raise AdapterRefusal("case-id", "invalid case ID", case_id)
    cases = manifest.get("cases")
    if not isinstance(cases, list):
        raise AdapterRefusal("cases", "manifest.cases must be an array")
    matches = [case for case in cases if isinstance(case, dict) and case.get("caseId") == case_id]
    if len(matches) != 1:
        raise AdapterRefusal("case-selection", "case ID must occur exactly once", {"caseId": case_id, "matches": len(matches)})
    return matches[0]


def validate_manifest_header(manifest: dict[str, Any]) -> None:
    expected = {"schemaVersion": 1, "stageId": STAGE_ID, "mode": "scientific", "scientificExecution": True}
    stale = {key: (manifest.get(key), value) for key, value in expected.items() if manifest.get(key) != value}
    if stale:
        raise AdapterRefusal("manifest-header", "manifest is not a scientific MYSTIC batch manifest", stale)
    if manifest.get("adapterId") != ADAPTER_ID:
        raise AdapterRefusal("adapter-id", "manifest adapterId is unsupported", manifest.get("adapterId"))
    batch_id = manifest.get("batchId")
    if not isinstance(batch_id, str) or not CASE_ID_RE.fullmatch(batch_id):
        raise AdapterRefusal("batch-id", "invalid batchId", batch_id)


def validate_runtime_claims(manifest: dict[str, Any]) -> dict[str, str]:
    runtime = manifest.get("runtime")
    if not isinstance(runtime, dict):
        raise AdapterRefusal("runtime", "runtime must be an object")
    kind = runtime.get("kind")
    if kind not in {"container", "micromamba-lock"}:
        raise AdapterRefusal("runtime-kind", "runtime.kind must be container or micromamba-lock", kind)
    claims = {
        "uvspecSha256": require_sha256(runtime.get("uvspecSha256"), "runtime.uvspecSha256"),
        "uvspecHelpSha256": require_sha256(runtime.get("uvspecHelpSha256"), "runtime.uvspecHelpSha256"),
        "libRadtranDataTreeSha256": require_sha256(runtime.get("libRadtranDataTreeSha256"), "runtime.libRadtranDataTreeSha256"),
        "atmosphereSha256": require_sha256(runtime.get("atmosphereSha256"), "runtime.atmosphereSha256"),
        "runtimeLockRawSha256": require_sha256(runtime.get("runtimeLockRawSha256"), "runtime.runtimeLockRawSha256"),
    }
    if kind == "container":
        digest = runtime.get("containerImageDigest")
        if not isinstance(digest, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
            raise AdapterRefusal("container-digest", "container runtime requires an image pinned by sha256", digest)
    else:
        package = runtime.get("exactPackageSpec")
        if not isinstance(package, str) or "=" not in package or any(ch.isspace() for ch in package):
            raise AdapterRefusal("package-spec", "micromamba runtime requires one exact package build spec", package)
        if runtime.get("containerImageDigest") is not None:
            raise AdapterRefusal("runtime-claim", "micromamba-lock runtime must not claim a container digest")
    return claims


def validate_runtime_report(report: dict[str, Any], claims: dict[str, str]) -> None:
    if report.get("schemaVersion") != 1 or report.get("stageId") != STAGE_ID:
        raise AdapterRefusal("runtime-report", "wrong runtime report header")
    if report.get("scientificSolverExecuted") is not False:
        raise AdapterRefusal("runtime-report", "runtime identity report must state that no scientific solver executed")
    mapping = {
        "uvspecSha256": "uvspecSha256",
        "uvspecHelpSha256": "uvspecHelpSha256",
        "libRadtranDataTreeSha256": "libRadtranDataTreeSha256",
        "atmosphereSha256": "atmosphereSha256",
        "runtimeLockRawSha256": "runtimeLockRawSha256",
    }
    stale = {claim_key: (report.get(report_key), claims[claim_key]) for claim_key, report_key in mapping.items() if report.get(report_key) != claims[claim_key]}
    if stale:
        raise AdapterRefusal("runtime-identity", "runtime report does not match manifest claims", stale)


def normalized_scientific_inputs(manifest: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    frozen = manifest.get("frozenInputs")
    if not isinstance(frozen, dict):
        raise AdapterRefusal("frozen-inputs", "frozenInputs must be an object")
    paths = frozen.get("dataPaths")
    if not isinstance(paths, dict):
        raise AdapterRefusal("data-paths", "frozenInputs.dataPaths must be an object")
    wavelength_domain = frozen.get("wavelengthDomainNm")
    if not isinstance(wavelength_domain, list) or len(wavelength_domain) != 2 or any(not isinstance(item, int) or isinstance(item, bool) for item in wavelength_domain):
        raise AdapterRefusal("wavelength-domain", "wavelengthDomainNm must contain two integer endpoints")
    start_nm, end_nm = wavelength_domain
    if not (200 <= start_nm < end_nm <= 5000):
        raise AdapterRefusal("wavelength-domain", "wavelength domain is outside the supported range", wavelength_domain)
    nodes = frozen.get("diagnosticNodesNm")
    if not isinstance(nodes, list) or not nodes or any(not isinstance(node, int) or isinstance(node, bool) for node in nodes):
        raise AdapterRefusal("diagnostic-nodes", "diagnosticNodesNm must be a non-empty integer array")
    if sorted(set(nodes)) != nodes or nodes[0] < start_nm or nodes[-1] > end_nm:
        raise AdapterRefusal("diagnostic-nodes", "diagnostic nodes must be unique, sorted, and inside the wavelength domain")
    parameters = case.get("parameters")
    if not isinstance(parameters, dict):
        raise AdapterRefusal("case-parameters", "scientific case requires a parameters object", case.get("caseId"))
    altitude = require_number(parameters.get("targetAltitudeDeg"), "targetAltitudeDeg", 0.0, 90.0)
    return {
        "caseId": case.get("caseId"),
        "ordinal": require_int(case.get("ordinal"), "case.ordinal", 1),
        "seed": require_int(case.get("seed"), "case.seed", 1),
        "photonHistories": require_int(case.get("photonHistories"), "case.photonHistories", 1),
        "sunDepressionDeg": require_number(parameters.get("sunDepressionDeg"), "sunDepressionDeg", -5.0, 30.0),
        "targetAltitudeDeg": altitude,
        "relativeAzimuthDeg": require_number(parameters.get("relativeAzimuthDeg"), "relativeAzimuthDeg", 0.0, 360.0),
        "observerElevationM": require_number(parameters.get("observerElevationM"), "observerElevationM", 0.0, 10000.0),
        "aod550": require_number(parameters.get("aod550", frozen.get("aod550")), "aod550", 0.0, 5.0),
        "albedo": require_number(parameters.get("albedo", frozen.get("albedo")), "albedo", 0.0, 1.0),
        "wavelengthStartNm": start_nm,
        "wavelengthEndNm": end_nm,
        "diagnosticNodesNm": nodes,
        "molecularAbsorption": frozen.get("molecularAbsorption"),
        "mcSpherical": frozen.get("mcSpherical"),
        "mcVroom": frozen.get("mcVroom"),
        "solarFlux": require_rooted_path(paths.get("solarFlux"), "dataPaths.solarFlux"),
        "wavelengthGrid": require_rooted_path(paths.get("wavelengthGrid"), "dataPaths.wavelengthGrid"),
        "atmosphere": require_rooted_path(paths.get("atmosphere"), "dataPaths.atmosphere"),
    }


def resolve_rooted_path(spec: dict[str, str], data_dir: Path, repository_root: Path) -> Path:
    root = data_dir if spec["root"] == "libRadtranData" else repository_root
    return (root / spec["path"]).resolve()


def render_uvspec_input(inputs: dict[str, Any], data_dir: Path, repository_root: Path, case_dir: Path) -> str:
    if inputs["molecularAbsorption"] != "crs":
        raise AdapterRefusal("molecular-absorption", "only mol_abs_param crs is supported")
    if inputs["mcSpherical"] != "1D":
        raise AdapterRefusal("mc-spherical", "only mc_spherical 1D is supported")
    if inputs["mcVroom"] not in {"on", "off"}:
        raise AdapterRefusal("mc-vroom", "mcVroom must be on or off")
    sza = 90.0 + inputs["sunDepressionDeg"]
    umu = -math.sin(math.radians(inputs["targetAltitudeDeg"]))
    solar_flux = resolve_rooted_path(inputs["solarFlux"], data_dir, repository_root)
    wavelength_grid = resolve_rooted_path(inputs["wavelengthGrid"], data_dir, repository_root)
    atmosphere = resolve_rooted_path(inputs["atmosphere"], data_dir, repository_root)
    for path, label in ((solar_flux, "solar flux"), (wavelength_grid, "wavelength grid"), (atmosphere, "atmosphere")):
        if not path.is_file():
            raise AdapterRefusal("missing-input-file", f"{label} file not found", str(path))
    basename = case_dir / "mc"
    lines = [
        f"data_files_path {data_dir}",
        f"atmosphere_file {atmosphere}",
        f"source solar {solar_flux}",
        "mol_abs_param crs",
        f"wavelength_grid_file {wavelength_grid}",
        f"wavelength {inputs['wavelengthStartNm']} {inputs['wavelengthEndNm']}",
        f"sza {sza:.6f}",
        "phi0 0.00",
        "rte_solver mystic",
        "mc_spherical 1D",
        f"mc_photons {inputs['photonHistories']}",
        f"mc_vroom {inputs['mcVroom']}",
        "mc_std",
        f"mc_randomseed {inputs['seed']}",
        f"mc_basename {basename}",
        f"albedo {inputs['albedo']:.6f}",
        "aerosol_default",
        f"aerosol_set_tau_at_wvl 550 {inputs['aod550']:.6f}",
        f"zout {inputs['observerElevationM'] / 1000.0:.6f}",
        f"umu {umu:.8f}",
        f"phi {inputs['relativeAzimuthDeg']:.6f}",
        "quiet",
    ]
    return "\n".join(lines) + "\n"


def prepare_case(manifest_path: Path, runtime_report_path: Path, case_id: str, data_dir: Path, repository_root: Path, output_dir: Path) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    validate_manifest_header(manifest)
    claims = validate_runtime_claims(manifest)
    runtime_report = load_json(runtime_report_path)
    validate_runtime_report(runtime_report, claims)
    case = resolve_case(manifest, case_id)
    inputs = normalized_scientific_inputs(manifest, case)
    case_dir = output_dir / case_id
    case_dir.mkdir(parents=True, exist_ok=False)
    rendered = render_uvspec_input(inputs, data_dir.resolve(), repository_root.resolve(), case_dir.resolve())
    input_path = case_dir / "input-resolved.txt"
    input_path.write_text(rendered)
    proposal = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "adapterId": ADAPTER_ID,
        "status": "PREPARED_NO_SOLVER",
        "scientificSolverExecuted": False,
        "batchId": manifest["batchId"],
        "caseId": case_id,
        "manifestRawSha256": raw_sha256(manifest_path),
        "runtimeReportRawSha256": raw_sha256(runtime_report_path),
        "inputResolvedSha256": text_sha256(rendered),
        "inputs": inputs,
        "inputPath": str(input_path),
        "boundary": "prepared and hashed exact uvspec input only; no syntax check and no solver execution",
    }
    (case_dir / "case-proposal.json").write_text(dump_json(proposal))
    return proposal


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--runtime-report", type=Path, required=True)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = prepare_case(args.manifest, args.runtime_report, args.case_id, args.data_dir, args.repository_root, args.output_dir)
        print(dump_json(result), end="")
        return 0
    except AdapterRefusal as exc:
        print(dump_json(exc.as_dict()), end="", file=sys.stderr)
        return 2
    except Exception as exc:
        refusal = AdapterRefusal("unexpected-error", str(exc)).as_dict()
        print(dump_json(refusal), end="", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
