from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

STAGE = "aerosol-vertical-profile-sensitivity-v1"
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
EXECUTION_PACKAGE_PATH = HERE / "execution_package.py"
SEED_LEDGER_PATH = HERE / "seed_ledger.py"
WAVELENGTH_GRID_PATH = ROOT / "experiments/aerosol-family-challenge-v2-r8/wavelength-grid-1nm.dat"
EXPECTED_EXECUTION_PACKAGE_BLOB = "4b588e5eb289e9074935bf4ca22a4e2c6185bdb9"
EXPECTED_DISABLED_PACKAGE_CANONICAL = "ecf7052454e47a9e047cb944f22b031473c0986e9d8b9cec1aa010d425b39cc1"
EXPECTED_WAVELENGTH_GRID_BLOB = "3bb3db96580d555ef758f57cabd6cac55b61cebb"
EXPECTED_SEED_CANONICAL = "a2e22b526dfad84d4f23c0ca8b143d028fddc7e55f78deb93a43e194ebd6c35e"
EXPECTED_ROWS_CANONICAL = "f22de8a9e30ba106759effb1170a5ca1d1e747cb2ac68293fa232dc7ed6ca683"
SEED_DOMAIN_MAX_EXCLUSIVE = 2_147_483_647
SHA64 = re.compile(r"^[0-9a-f]{64}$")


class AdapterRefusal(RuntimeError):
    pass


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AdapterRefusal(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _package() -> dict[str, Any]:
    if git_blob_sha1(EXECUTION_PACKAGE_PATH) != EXPECTED_EXECUTION_PACKAGE_BLOB:
        raise AdapterRefusal("execution package byte drift")
    if git_blob_sha1(WAVELENGTH_GRID_PATH) != EXPECTED_WAVELENGTH_GRID_BLOB:
        raise AdapterRefusal("wavelength-grid byte drift")
    mod = _load("avps_adapter_execution_package", EXECUTION_PACKAGE_PATH)
    package = mod.build_disabled_execution_package()
    if package.get("canonicalPackageSha256") != EXPECTED_DISABLED_PACKAGE_CANONICAL:
        raise AdapterRefusal("execution package canonical drift")
    return package


def _seed_by_group() -> dict[str, int]:
    mod = _load("avps_adapter_seed_ledger", SEED_LEDGER_PATH)
    ledger = mod.validate_ledger()
    if ledger.get("candidateSeedCanonicalSha256") != EXPECTED_SEED_CANONICAL:
        raise AdapterRefusal("candidate seed canonical drift")
    if ledger.get("candidateRowsCanonicalSha256") != EXPECTED_ROWS_CANONICAL:
        raise AdapterRefusal("candidate seed row canonical drift")
    rows = mod.derive_rows()
    out = {str(row["groupId"]): int(row["seed"]) for row in rows}
    if len(out) != 72 or len(set(out.values())) != 72:
        raise AdapterRefusal("candidate seed mapping cardinality/uniqueness drift")
    if any(not 0 < seed < SEED_DOMAIN_MAX_EXCLUSIVE for seed in out.values()):
        raise AdapterRefusal("candidate seed outside libRadtran domain")
    return out


def validate_authorization_bindings(auth: dict[str, Any]) -> None:
    if auth.get("stageId") != STAGE or auth.get("status") != "AUTHORIZED_PENDING_SEPARATE_DISPATCH":
        raise AdapterRefusal("authorization stage/status drift")
    if auth.get("disabledExecutionPackageBlobSha1") != EXPECTED_EXECUTION_PACKAGE_BLOB:
        raise AdapterRefusal("authorization execution-package blob drift")
    if auth.get("disabledExecutionPackageCanonicalSha256") != EXPECTED_DISABLED_PACKAGE_CANONICAL:
        raise AdapterRefusal("authorization execution-package canonical drift")
    if auth.get("candidateSeedCanonicalSha256") != EXPECTED_SEED_CANONICAL:
        raise AdapterRefusal("authorization seed canonical drift")
    if auth.get("candidateRowsCanonicalSha256") != EXPECTED_ROWS_CANONICAL:
        raise AdapterRefusal("authorization row canonical drift")
    if auth.get("caseCount") != 360 or auth.get("commonRandomNumberGroupCount") != 72 or auth.get("statesPerGroup") != 5:
        raise AdapterRefusal("authorization cardinality drift")
    if auth.get("photonHistoriesPerCase") != 20_000_000:
        raise AdapterRefusal("authorization photon budget drift")
    if auth.get("scientificExecutionAuthorized") is not True or auth.get("solverExecutionAuthorized") is not True:
        raise AdapterRefusal("authorization does not permit separately dispatched solver execution")
    for key in ("dispatchAuthorized", "resultOpeningAuthorized", "automaticDispatch", "productionAuthorized", "taylorOrJerusalemFitAuthorized"):
        if auth.get(key) is not False:
            raise AdapterRefusal(f"authorization crossed boundary: {key}")
    if not isinstance(auth.get("scientificOrdinal"), int) or auth["scientificOrdinal"] <= 0:
        raise AdapterRefusal("authorization scientific ordinal invalid")
    tau = auth.get("exactAfglProfileTauSha256")
    if not isinstance(tau, dict) or len(tau) != 5 or any(SHA64.fullmatch(str(v)) is None for v in tau.values()):
        raise AdapterRefusal("authorization exact-AFGL tau binding drift")


def authorized_case(case_id: str, auth: dict[str, Any]) -> dict[str, Any]:
    validate_authorization_bindings(auth)
    package = _package()
    matches = [row for row in package["cases"] if row.get("caseId") == case_id]
    if len(matches) != 1:
        raise AdapterRefusal(f"expected exactly one frozen case: {case_id}")
    base = dict(matches[0])
    seed_map = _seed_by_group()
    group_id = str(base["groupId"])
    if group_id not in seed_map:
        raise AdapterRefusal("frozen case group has no candidate seed")
    base["seed"] = seed_map[group_id]
    base["seedStatus"] = "AUTHORIZED_FRESH_GROUP_SEED_PENDING_DISPATCH"
    base["renderable"] = True
    base["executionAuthorized"] = True
    base["resultOpeningAuthorized"] = False
    base["scientificOrdinal"] = int(auth["scientificOrdinal"])
    return base


def exact_profile_texts(data_dir: Path, auth: dict[str, Any]) -> dict[str, str]:
    validate_authorization_bindings(auth)
    mod = _load("avps_adapter_profile_bundle", EXECUTION_PACKAGE_PATH)
    bundle = mod.build_exact_profile_bundle(data_dir / "atmmod/afglus.dat")
    expected = auth["exactAfglProfileTauSha256"]
    texts: dict[str, str] = {}
    for state_id, row in bundle["profiles"].items():
        if row.get("sha256") != expected.get(state_id):
            raise AdapterRefusal(f"exact-AFGL tau byte drift: {state_id}")
        texts[state_id] = str(row["text"])
    if set(texts) != set(expected):
        raise AdapterRefusal("exact-AFGL state universe drift")
    return texts


def render_case_input(case: dict[str, Any], auth: dict[str, Any], data_dir: Path, repository_root: Path, output_root: Path) -> str:
    validate_authorization_bindings(auth)
    if case.get("renderable") is not True or case.get("executionAuthorized") is not True:
        raise AdapterRefusal("case is not authorized/renderable")
    seed = case.get("seed")
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 < seed < SEED_DOMAIN_MAX_EXCLUSIVE:
        raise AdapterRefusal("case seed invalid")
    state_id = str(case.get("stateId") or "")
    if state_id not in auth["exactAfglProfileTauSha256"]:
        raise AdapterRefusal("case state outside exact-AFGL profile universe")
    case_dir = (output_root / str(case["caseId"])).resolve()
    grid = WAVELENGTH_GRID_PATH.resolve()
    raw_surface = list(case.get("caseSurface") or [])
    if len(raw_surface) < 20:
        raise AdapterRefusal("frozen case surface missing")
    replacements = {
        "data_files_path <EXACT_STAGED_OPAC_DATA_TREE>/": f"data_files_path {data_dir.resolve()}",
        "atmosphere_file <EXACT_STAGED_OPAC_DATA_TREE>/atmmod/afglus.dat": f"atmosphere_file {(data_dir / 'atmmod/afglus.dat').resolve()}",
        "source solar <EXACT_STAGED_OPAC_DATA_TREE>/solar_flux/atlas_plus_modtran": f"source solar {(data_dir / 'solar_flux/atlas_plus_modtran').resolve()}",
        "wavelength_grid_file <REPOSITORY>/experiments/aerosol-family-challenge-v2-r8/wavelength-grid-1nm.dat": f"wavelength_grid_file {grid}",
        "mc_randomseed <UNALLOCATED_FRESH_GROUP_SEED>": f"mc_randomseed {seed}",
        "mc_basename <CASE_OUTPUT_DIR>/mc": f"mc_basename {(case_dir / 'mc').resolve()}",
    }
    lines = [replacements.get(line, line) for line in raw_surface]
    unresolved = [line for line in lines if "<" in line or ">" in line]
    if unresolved:
        raise AdapterRefusal(f"unresolved execution placeholder(s): {unresolved}")
    if sum(line.startswith("aerosol_file tau profiles/") for line in lines) != 1:
        raise AdapterRefusal("custom tau directive cardinality drift")
    if f"aerosol_file tau profiles/{state_id}.tau" not in lines:
        raise AdapterRefusal("case tau state/path drift")
    if any(line.startswith("aerosol_modify ") for line in lines):
        raise AdapterRefusal("SSA/g modification forbidden")
    required = (
        "rte_solver mystic", "mc_spherical 1D", "mc_vroom on", "mc_std",
        "wavelength 380 780", "aerosol_species_library OPAC", "aerosol_species_file continental_average",
    )
    if any(lines.count(item) != 1 for item in required):
        raise AdapterRefusal("required frozen directive missing/duplicated")
    if lines.count(f"mc_randomseed {seed}") != 1:
        raise AdapterRefusal("authorized seed directive drift")
    if lines.count(f"mc_photons {int(case['photonHistories'])}") != 1 or int(case["photonHistories"]) != 20_000_000:
        raise AdapterRefusal("photon directive drift")
    return "\n".join(lines) + "\n"


def prepare_case_files(case: dict[str, Any], auth: dict[str, Any], data_dir: Path, repository_root: Path, output_root: Path) -> dict[str, Any]:
    case_dir = output_root / str(case["caseId"])
    case_dir.mkdir(parents=True, exist_ok=False)
    profiles_dir = case_dir / "profiles"
    profiles_dir.mkdir()
    profile_texts = exact_profile_texts(data_dir, auth)
    state_id = str(case["stateId"])
    profile_path = profiles_dir / f"{state_id}.tau"
    profile_path.write_text(profile_texts[state_id], encoding="utf-8")
    rendered = render_case_input(case, auth, data_dir, repository_root, output_root)
    input_path = case_dir / "case.inp"
    input_path.write_text(rendered, encoding="utf-8")
    return {
        "caseDir": str(case_dir.resolve()),
        "inputPath": str(input_path.resolve()),
        "profilePath": str(profile_path.resolve()),
        "profileSha256": hashlib.sha256(profile_path.read_bytes()).hexdigest(),
        "inputSha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
    }
