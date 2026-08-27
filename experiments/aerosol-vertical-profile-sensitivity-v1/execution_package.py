from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any

STAGE_ID = "aerosol-vertical-profile-sensitivity-v1"
STAGE_DIR = Path(__file__).resolve().parent
ROOT = STAGE_DIR.parents[1]
EXECUTION_CANDIDATE_PATH = STAGE_DIR / "execution_candidate.py"
TEMPLATE_PATH = STAGE_DIR / "opac_vertical_templates.py"
TRANSPORT_PATH = ROOT / "review" / "aerosol-vertical-profile-transport-v1" / "profile_transport.py"
WAVELENGTH_GRID_PATH = ROOT / "experiments" / "aerosol-family-challenge-v2-r8" / "wavelength-grid-1nm.dat"

EXPECTED_GIT_BLOBS = {
    "execution_candidate.py": "ac77f6f594b74d2b6fa0ece5ad7dcb106e498976",
    "opac_vertical_templates.py": "8e8175ae771438b91fc9543b329175c193a215a4",
    "profile_transport.py": "af2d4d65371474c38791d79e2fcded696022d88d",
    "wavelength-grid-1nm.dat": "3bb3db96580d555ef758f57cabd6cac55b61cebb",
}

RUNTIME_BINDING = {
    "libRadtranVersion": "2.0.6",
    "lockedPackage": "rubin-libradtran=2.0.6=py312pl5321he9373c2_1",
    "uvspecSha256": "2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3",
    "baseDataTreeSha256": "ad30b49177e9c84e46497d69faf0c75e466996b0d0003f1de210289ae9f847d7",
    "stagedOpacDataTreeSha256": "5d8bbf8e6b91ec3d405dee36f21a94afbb6e5ec6cd67da2dd5dd541738199d80",
    "officialOptpropArchiveSha256": "11daa1f1f4be0fd4ddf7e881ec2005498049674a1540d37b4b1e8f5e16052c7e",
    "opacCustomTauCapabilityMergeCommit": "2be138d96d4e6d04b1e58dede27bb3f0130fc42e",
    "opacCustomTauCapabilityRunId": 33095258477,
    "opacCustomTauCapabilityArtifactId": 9656112795,
    "opacCustomTauCapabilityArtifactDigest": "sha256:870ee009131c3b6c737dde70bfa4ad7c4a7e85a7d91cd4b4012f2f36e23f2098",
}


class ExecutionPackageError(RuntimeError):
    pass


def _git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ExecutionPackageError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def validate_bindings() -> dict[str, str]:
    actual = {
        "execution_candidate.py": _git_blob_sha1(EXECUTION_CANDIDATE_PATH),
        "opac_vertical_templates.py": _git_blob_sha1(TEMPLATE_PATH),
        "profile_transport.py": _git_blob_sha1(TRANSPORT_PATH),
        "wavelength-grid-1nm.dat": _git_blob_sha1(WAVELENGTH_GRID_PATH),
    }
    if actual != EXPECTED_GIT_BLOBS:
        raise ExecutionPackageError(f"frozen byte binding drift: expected={EXPECTED_GIT_BLOBS} actual={actual}")
    return actual


def _execution_candidate():
    return _load("avps_disabled_execution_candidate", EXECUTION_CANDIDATE_PATH)


def _templates():
    return _load("avps_disabled_execution_templates", TEMPLATE_PATH)


def parse_afgl_altitude_edges_km(atmosphere_path: Path) -> tuple[float, ...]:
    if not atmosphere_path.is_file():
        raise ExecutionPackageError(f"AFGL atmosphere missing: {atmosphere_path}")
    levels: list[float] = []
    for raw in atmosphere_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        columns = line.split()
        if not columns:
            continue
        try:
            value = float(columns[0])
        except ValueError as exc:
            raise ExecutionPackageError(f"invalid AFGL altitude row: {raw}") from exc
        if not math.isfinite(value):
            raise ExecutionPackageError("non-finite AFGL altitude")
        levels.append(value)
    if len(levels) < 2 or any(levels[i] <= levels[i + 1] for i in range(len(levels) - 1)):
        raise ExecutionPackageError("AFGL levels must be strictly descending")
    edges = tuple(reversed(levels))
    if abs(edges[0]) > 1e-12 or edges[-1] < 35.0:
        raise ExecutionPackageError("AFGL grid does not satisfy frozen sea-level/35-km profile support")
    return edges


def build_exact_profile_bundle(atmosphere_path: Path) -> dict[str, Any]:
    validate_bindings()
    templates = _templates()
    edges = parse_afgl_altitude_edges_km(atmosphere_path)
    states = list(templates.PROFILE_STATES)
    if len(states) != 5:
        raise ExecutionPackageError("vertical-state count drift")
    profiles: dict[str, Any] = {}
    for state_id in states:
        text = templates.render_libradtran_tau(edges, state_id)
        rows = [line for line in text.splitlines() if line and not line.startswith("#")]
        if len(rows) != len(edges):
            raise ExecutionPackageError(f"tau level cardinality drift: {state_id}")
        tau = [float(line.split()[1]) for line in rows]
        if abs(tau[0]) > 1e-15 or abs(math.fsum(tau) - 1.0) > 1e-12:
            raise ExecutionPackageError(f"tau normalization/lower-bound convention drift: {state_id}")
        profiles[state_id] = {
            "relativePath": f"profiles/{state_id}.tau",
            "sha256": _sha256_bytes(text.encode("utf-8")),
            "levelCount": len(rows),
            "tauSum": math.fsum(tau),
            "text": text,
        }
    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "EXACT_AFGL_PROFILE_BUNDLE_REVIEW_ONLY",
        "afglAltitudeEdgesKm": list(edges),
        "afglLevelCount": len(edges),
        "profiles": profiles,
        "scientificExecutionAuthorized": False,
        "solverExecutionAuthorized": False,
        "resultOpeningAuthorized": False,
    }


def render_case_science_surface(case: dict[str, Any]) -> list[str]:
    if case.get("seed") is not None or case.get("seedStatus") != "UNALLOCATED_REVIEW_ONLY":
        raise ExecutionPackageError("review surface refuses allocated seed")
    if case.get("renderable") is not False or case.get("executionAuthorized") is not False:
        raise ExecutionPackageError("review surface refuses renderable/authorized case")
    dep = float(case["sunDepressionDeg"])
    alt = float(case["targetAltitudeDeg"])
    az = float(case["relativeAzimuthDeg"])
    aerosol = list(case["aerosolDirectives"])
    expected_prefix = [
        "aerosol_default",
        "aerosol_species_library OPAC",
        "aerosol_species_file continental_average",
    ]
    if aerosol[:3] != expected_prefix:
        raise ExecutionPackageError("OPAC aerosol prefix drift")
    if sum(line.startswith("aerosol_file tau profiles/") for line in aerosol) != 1:
        raise ExecutionPackageError("custom tau directive drift")
    if aerosol[-1] != f"aerosol_set_tau_at_wvl 550 {float(case['aod550']):.6f}":
        raise ExecutionPackageError("AOD normalization order drift")
    if any(line.startswith("aerosol_modify ") for line in aerosol):
        raise ExecutionPackageError("SSA/g modification forbidden")
    return [
        "data_files_path <EXACT_STAGED_OPAC_DATA_TREE>/",
        "atmosphere_file <EXACT_STAGED_OPAC_DATA_TREE>/atmmod/afglus.dat",
        "source solar <EXACT_STAGED_OPAC_DATA_TREE>/solar_flux/atlas_plus_modtran",
        "mol_abs_param crs",
        "wavelength_grid_file <REPOSITORY>/experiments/aerosol-family-challenge-v2-r8/wavelength-grid-1nm.dat",
        "wavelength 380 780",
        f"sza {90.0 + dep:.6f}",
        "phi0 0.000000",
        "rte_solver mystic",
        "mc_spherical 1D",
        f"mc_photons {int(case['photonHistories'])}",
        "mc_vroom on",
        "mc_std",
        "mc_randomseed <UNALLOCATED_FRESH_GROUP_SEED>",
        "mc_basename <CASE_OUTPUT_DIR>/mc",
        f"albedo {float(case['surfaceAlbedo']):.6f}",
        *aerosol,
        "zout 0.000000",
        f"umu {-math.sin(math.radians(alt)):.8f}",
        f"phi {az:.6f}",
        "quiet",
    ]


def build_disabled_execution_package() -> dict[str, Any]:
    bindings = validate_bindings()
    skeleton = _execution_candidate().build_review_execution_skeleton()
    cases = skeleton.get("cases") or []
    if len(cases) != 360 or skeleton.get("groupCount") != 72:
        raise ExecutionPackageError("frozen skeleton cardinality drift")
    packaged_cases: list[dict[str, Any]] = []
    for case in cases:
        surface = render_case_science_surface(case)
        packaged_cases.append({
            "caseId": case["caseId"],
            "groupId": case["groupId"],
            "stateId": case["stateId"],
            "seed": None,
            "seedStatus": "UNALLOCATED_REVIEW_ONLY",
            "caseSurface": surface,
            "caseSurfaceSha256": _canonical_sha256(surface),
            "renderable": False,
            "executionAuthorized": False,
            "resultOpeningAuthorized": False,
        })
    if len({row["caseSurfaceSha256"] for row in packaged_cases}) != 120:
        # Three CRN replicates deliberately share the same pre-seed scientific surface.
        raise ExecutionPackageError("unexpected pre-seed science-surface cardinality")
    package = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "DISABLED_EXECUTION_PACKAGE_REVIEW_ONLY_SEEDS_UNALLOCATED",
        "sourceSkeletonCanonicalSha256": skeleton["canonicalSkeletonSha256"],
        "sourceBindings": bindings,
        "runtimeBinding": dict(RUNTIME_BINDING),
        "caseCount": 360,
        "groupCount": 72,
        "distinctPreSeedScienceSurfaceCount": 120,
        "candidateSeedCount": 72,
        "candidateSeedCanonicalSha256": "a2e22b526dfad84d4f23c0ca8b143d028fddc7e55f78deb93a43e194ebd6c35e",
        "candidateRowsCanonicalSha256": "f22de8a9e30ba106759effb1170a5ca1d1e747cb2ac68293fa232dc7ed6ca683",
        "candidateSeedsAppliedToCases": False,
        "scientificOrdinal": None,
        "scientificExecutionAuthorized": False,
        "solverExecutionAuthorized": False,
        "resultOpeningAuthorized": False,
        "productionAuthorized": False,
        "cases": packaged_cases,
    }
    package["canonicalPackageSha256"] = _canonical_sha256(package)
    return package


if __name__ == "__main__":
    print(json.dumps(build_disabled_execution_package(), indent=2, sort_keys=True))
