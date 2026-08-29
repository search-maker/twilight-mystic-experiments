from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path
from typing import Any

STAGE = "aerosol-vertical-profile-sensitivity-v2"
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PACKAGE_PATH = HERE / "control_package.py"
SKELETON_PATH = ROOT / "review/aerosol-vertical-profile-sensitivity-v2-prereg/build_skeleton.py"
SEED_LEDGER_PATH = ROOT / "review/aerosol-vertical-profile-sensitivity-v2-seed-freshness/seed_ledger.py"
WAVELENGTH_GRID_PATH = ROOT / "experiments/aerosol-family-challenge-v2-r8/wavelength-grid-1nm.dat"
EXPECTED_SKELETON_BLOB = "b4a4ab6917ad28f08d4980194f7b68f3961d5d59"
EXPECTED_SEED_LEDGER_BLOB = "c757507b05074340507df1ca6e76d35b44cf6090"
EXPECTED_WAVELENGTH_GRID_BLOB = "3bb3db96580d555ef758f57cabd6cac55b61cebb"
EXPECTED_SEED_CANONICAL = "02f624d582e9b2caba6b920d65a5e8a8bc8fc1a2693623bc2f73abf5d3f706d2"
EXPECTED_ROWS_CANONICAL = "41f70d6a0381db6b569d3f4e17d74bb38b05cf212c2f2e432455a502f73dc670"
EXPECTED_PROFILE_SHA256 = {
    "opac-profile-continental-average": "ceed598f7681951cd0e6208b267beb5b41a52ab10311f37ce76f925700caff3d",
    "opac-profile-maritime-clean": "487b67bd7dbe89d12d032fdf2b33cab545e16a2e0697170648317f1a76362a67",
    "opac-profile-desert": "2b4d2e03c6ae3143d9bb05d2da49f57f75172dc1f24d34f7d4a4939bf9952fef",
    "opac-profile-arctic": "98f2fa5428c830764252fd0a2662b0f5c957fc027ffcb7bdc0a5e500dfd7d3d6",
    "opac-profile-antarctic": "ee063c6dca68cf9a31d8bb9d993f1fed5cb34c8bb056ac180c97171b5d6b4f19",
}
EXPECTED_FOUR_ALIAS_TREE_SHA256 = "5e1814dd36cf861fd85477a97607299248f8272268df7bf428d31bbb6aa4354a"
SEED_DOMAIN_MAX_EXCLUSIVE = 2_147_483_647


class AdapterRefusal(RuntimeError):
    pass


def git_blob_sha1(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AdapterRefusal(f"cannot load bound module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _package() -> dict[str, Any]:
    package = _load("avps_v2_adapter_package", PACKAGE_PATH).build_disabled_package()
    if package.get("caseCount") != 360 or package.get("groupCount") != 72:
        raise AdapterRefusal("disabled package cardinality drift")
    if package.get("scientificOrdinalAllocated") is not False or package.get("authorizationCreated") is not False:
        raise AdapterRefusal("disabled package crossed authorization boundary")
    return package


def _skeleton() -> dict[str, Any]:
    if git_blob_sha1(SKELETON_PATH) != EXPECTED_SKELETON_BLOB:
        raise AdapterRefusal("v2 skeleton byte drift")
    value = _load("avps_v2_adapter_skeleton", SKELETON_PATH).build_review_skeleton()
    if value.get("caseCount") != 360 or value.get("groupCount") != 72:
        raise AdapterRefusal("v2 skeleton cardinality drift")
    return value


def _seed_map() -> dict[str, int]:
    if git_blob_sha1(SEED_LEDGER_PATH) != EXPECTED_SEED_LEDGER_BLOB:
        raise AdapterRefusal("v2 seed ledger byte drift")
    module = _load("avps_v2_adapter_seed_ledger", SEED_LEDGER_PATH)
    ledger = module.validate_ledger()
    if ledger.get("candidateSeedCanonicalSha256") != EXPECTED_SEED_CANONICAL or ledger.get("candidateRowsCanonicalSha256") != EXPECTED_ROWS_CANONICAL:
        raise AdapterRefusal("candidate seed identity drift")
    rows = module.derive_rows()
    out = {str(row["groupId"]): int(row["seed"]) for row in rows}
    if len(out) != 72 or len(set(out.values())) != 72:
        raise AdapterRefusal("candidate seed mapping cardinality/uniqueness drift")
    if any(not 0 < seed < SEED_DOMAIN_MAX_EXCLUSIVE for seed in out.values()):
        raise AdapterRefusal("candidate seed outside libRadTran signed-32-bit domain")
    return out


def validate_authorization(auth: dict[str, Any]) -> None:
    package = _package()
    if auth.get("stageId") != STAGE or auth.get("status") != "AUTHORIZED_PENDING_SEPARATE_DISPATCH":
        raise AdapterRefusal("authorization stage/status drift")
    ordinal = auth.get("scientificOrdinal")
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal <= 0:
        raise AdapterRefusal("authorization scientific ordinal invalid")
    if auth.get("caseCount") != 360 or auth.get("commonRandomNumberGroupCount") != 72 or auth.get("statesPerGroup") != 5:
        raise AdapterRefusal("authorization cardinality drift")
    if auth.get("candidateSeedCount") != 72:
        raise AdapterRefusal("authorization candidate-seed count drift")
    if auth.get("candidateSeedCanonicalSha256") != EXPECTED_SEED_CANONICAL or auth.get("candidateRowsCanonicalSha256") != EXPECTED_ROWS_CANONICAL:
        raise AdapterRefusal("authorization candidate-seed identity drift")
    if auth.get("disabledControlPackageCanonicalSha256") != package.get("canonicalPackageSha256"):
        raise AdapterRefusal("authorization disabled-package binding drift")
    if auth.get("exactFourSpeciesProfileSha256") != EXPECTED_PROFILE_SHA256:
        raise AdapterRefusal("authorization profile-hash binding drift")
    if auth.get("fourAliasDataTreeSha256") != EXPECTED_FOUR_ALIAS_TREE_SHA256:
        raise AdapterRefusal("authorization four-alias data-tree drift")
    if auth.get("scientificExecutionAuthorized") is not True or auth.get("solverExecutionAuthorized") is not True:
        raise AdapterRefusal("authorization does not permit later separate solver dispatch")
    for key in ("dispatchAuthorized", "automaticDispatch", "resultOpeningAuthorized", "productionAuthorized", "taylorOrJerusalemFitAuthorized"):
        if auth.get(key) is not False:
            raise AdapterRefusal(f"authorization crossed forbidden boundary: {key}")


def authorized_case_universe(auth: dict[str, Any]) -> list[dict[str, Any]]:
    validate_authorization(auth)
    package = _package()
    skeleton = _skeleton()
    seed_map = _seed_map()
    packaged = {str(row["caseId"]): row for row in package["cases"]}
    full = {str(row["caseId"]): row for row in skeleton["cases"]}
    if len(packaged) != 360 or set(packaged) != set(full):
        raise AdapterRefusal("package/skeleton case universe drift")
    cases: list[dict[str, Any]] = []
    for case_id in sorted(full):
        src = full[case_id]
        pkg = packaged[case_id]
        if pkg.get("groupId") != src.get("groupId") or pkg.get("stateId") != src.get("stateId"):
            raise AdapterRefusal("package/skeleton identity mismatch")
        if pkg.get("preSeedScienceSurfaceSha256") != src.get("preSeedScienceSurfaceSha256"):
            raise AdapterRefusal("package/skeleton surface hash mismatch")
        group_id = str(src["groupId"])
        if group_id not in seed_map:
            raise AdapterRefusal("case group missing candidate seed")
        row = dict(src)
        row["seed"] = seed_map[group_id]
        row["seedStatus"] = "AUTHORIZED_FRESH_GROUP_SEED_PENDING_DISPATCH"
        row["scientificOrdinal"] = int(auth["scientificOrdinal"])
        row["renderable"] = True
        row["executionAuthorized"] = True
        row["resultOpeningAuthorized"] = False
        cases.append(row)
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in cases:
        groups.setdefault(str(row["groupId"]), []).append(row)
    if len(groups) != 72 or any(len(rows) != 5 for rows in groups.values()):
        raise AdapterRefusal("authorized CRN group cardinality drift")
    if any(len({r["stateId"] for r in rows}) != 5 for rows in groups.values()):
        raise AdapterRefusal("authorized state identity drift")
    if any(len({r["seed"] for r in rows}) != 1 for rows in groups.values()):
        raise AdapterRefusal("authorized CRN pairing drift")
    if len({rows[0]["seed"] for rows in groups.values()}) != 72:
        raise AdapterRefusal("authorized group seed uniqueness drift")
    return cases


def _profile_source(profile_dir: Path, state_id: str) -> Path:
    if state_id not in EXPECTED_PROFILE_SHA256:
        raise AdapterRefusal("unknown profile state")
    path = profile_dir / f"{state_id}.four-species.dat"
    if not path.is_file() or sha256_file(path) != EXPECTED_PROFILE_SHA256[state_id]:
        raise AdapterRefusal(f"exact four-species profile missing/drifted: {state_id}")
    return path


def render_case_input(case: dict[str, Any], data_dir: Path, repository_root: Path, case_dir: Path) -> str:
    if case.get("renderable") is not True or case.get("executionAuthorized") is not True:
        raise AdapterRefusal("case is not authorized/renderable")
    seed = case.get("seed")
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 < seed < SEED_DOMAIN_MAX_EXCLUSIVE:
        raise AdapterRefusal("authorized seed invalid")
    surface = list(case.get("preSeedScienceSurface") or [])
    state_id = str(case.get("stateId") or "")
    replacements = {
        "data_files_path <EXACT_FOUR_ALIAS_DATA_TREE>/": f"data_files_path {data_dir.resolve()}",
        "atmosphere_file <EXACT_FOUR_ALIAS_DATA_TREE>/atmmod/afglus.dat": f"atmosphere_file {(data_dir / 'atmmod/afglus.dat').resolve()}",
        "source solar <EXACT_FOUR_ALIAS_DATA_TREE>/solar_flux/atlas_plus_modtran": f"source solar {(data_dir / 'solar_flux/atlas_plus_modtran').resolve()}",
        "wavelength_grid_file <REPOSITORY>/experiments/aerosol-family-challenge-v2-r8/wavelength-grid-1nm.dat": f"wavelength_grid_file {(repository_root / 'experiments/aerosol-family-challenge-v2-r8/wavelength-grid-1nm.dat').resolve()}",
        "mc_randomseed <UNALLOCATED_FRESH_AVPS_V2_GROUP_SEED>": f"mc_randomseed {seed}",
        "mc_basename <CASE_OUTPUT_DIR>/mc": f"mc_basename {(case_dir / 'mc').resolve()}",
    }
    lines = [replacements.get(line, line) for line in surface]
    unresolved = [line for line in lines if "<" in line or ">" in line]
    if unresolved:
        raise AdapterRefusal(f"unresolved execution placeholders: {unresolved}")
    if any(line.startswith("aerosol_file ") for line in lines):
        raise AdapterRefusal("legacy/custom aerosol_file directive forbidden")
    species_line = f"aerosol_species_file profiles/{state_id}.four-species.dat INSO WASO SOOT SUSO"
    if lines.count(species_line) != 1:
        raise AdapterRefusal("exact four-species directive drift")
    required = ("rte_solver mystic", "mc_spherical 1D", "mc_vroom on", "mc_std", "wavelength 380 780", "aerosol_species_library OPAC")
    if any(lines.count(item) != 1 for item in required):
        raise AdapterRefusal("required frozen MYSTIC directive missing/duplicated")
    if lines.count(f"mc_randomseed {seed}") != 1 or lines.count("mc_photons 20000000") != 1:
        raise AdapterRefusal("seed/photon directive drift")
    return "\n".join(lines) + "\n"


def prepare_case_files(case: dict[str, Any], auth: dict[str, Any], data_dir: Path, repository_root: Path, profile_dir: Path, output_root: Path) -> dict[str, Any]:
    validate_authorization(auth)
    if int(case.get("scientificOrdinal") or 0) != int(auth["scientificOrdinal"]):
        raise AdapterRefusal("case/authorization ordinal drift")
    case_dir = output_root / str(case["caseId"])
    case_dir.mkdir(parents=True, exist_ok=False)
    profiles_dir = case_dir / "profiles"
    profiles_dir.mkdir()
    src = _profile_source(profile_dir, str(case["stateId"]))
    dst = profiles_dir / src.name
    shutil.copyfile(src, dst)
    if sha256_file(dst) != EXPECTED_PROFILE_SHA256[str(case["stateId"])]:
        raise AdapterRefusal("copied profile byte drift")
    if git_blob_sha1(WAVELENGTH_GRID_PATH) != EXPECTED_WAVELENGTH_GRID_BLOB:
        raise AdapterRefusal("wavelength-grid byte drift")
    text = render_case_input(case, data_dir, repository_root, case_dir)
    input_path = case_dir / "case.inp"
    input_path.write_text(text, encoding="utf-8", newline="\n")
    return {
        "caseDir": str(case_dir.resolve()),
        "inputPath": str(input_path.resolve()),
        "inputSha256": sha256_file(input_path),
        "profilePath": str(dst.resolve()),
        "profileSha256": sha256_file(dst),
        "caseId": case["caseId"],
        "groupId": case["groupId"],
        "stateId": case["stateId"],
        "scientificOrdinal": auth["scientificOrdinal"],
    }


def review_summary() -> dict[str, Any]:
    p = _package()
    _skeleton()
    ledger = _load("avps_v2_adapter_seed_review", SEED_LEDGER_PATH).validate_ledger()
    return {
        "status": "REVIEW_ONLY_ADAPTER_BOUND_AUTHORIZATION_REQUIRED_NO_CASE_RENDERED",
        "disabledControlPackageCanonicalSha256": p["canonicalPackageSha256"],
        "caseCount": p["caseCount"],
        "groupCount": p["groupCount"],
        "candidateSeedCount": ledger["candidateSeedCount"],
        "candidateSeedCanonicalSha256": EXPECTED_SEED_CANONICAL,
        "candidateRowsCanonicalSha256": EXPECTED_ROWS_CANONICAL,
        "exactFourSpeciesProfileSha256": EXPECTED_PROFILE_SHA256,
        "fourAliasDataTreeSha256": EXPECTED_FOUR_ALIAS_TREE_SHA256,
        "scientificOrdinalAllocated": False,
        "authorizationCreated": False,
        "solverExecutionAuthorized": False,
    }


if __name__ == "__main__":
    print(json.dumps(review_summary(), indent=2, sort_keys=True))
