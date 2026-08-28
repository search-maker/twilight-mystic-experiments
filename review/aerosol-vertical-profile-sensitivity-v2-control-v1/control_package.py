from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

STAGE = "aerosol-vertical-profile-sensitivity-v2"
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SKELETON_PATH = ROOT / "review/aerosol-vertical-profile-sensitivity-v2-prereg/build_skeleton.py"
SEED_LEDGER_PATH = ROOT / "review/aerosol-vertical-profile-sensitivity-v2-seed-freshness/seed_ledger.py"
EXPECTED_SKELETON_BLOB = "b4a4ab6917ad28f08d4980194f7b68f3961d5d59"
EXPECTED_SEED_LEDGER_BLOB = "c757507b05074340507df1ca6e76d35b44cf6090"
EXPECTED_SKELETON_CANONICAL = "a8d2d8f59aec01d82d8d98672152d00c11261660b0a69a59e2716c2edabd2b02"
EXPECTED_SEED_CANONICAL = "02f624d582e9b2caba6b920d65a5e8a8bc8fc1a2693623bc2f73abf5d3f706d2"
EXPECTED_ROWS_CANONICAL = "41f70d6a0381db6b569d3f4e17d74bb38b05cf212c2f2e432455a502f73dc670"
EXPECTED_PROFILE_SHA256 = {
    "opac-profile-continental-average": "ceed598f7681951cd0e6208b267beb5b41a52ab10311f37ce76f925700caff3d",
    "opac-profile-maritime-clean": "487b67bd7dbe89d12d032fdf2b33cab545e16a2e0697170648317f1a76362a67",
    "opac-profile-desert": "2b4d2e03c6ae3143d9bb05d2da49f57f75172dc1f24d34f7d4a4939bf9952fef",
    "opac-profile-arctic": "98f2fa5428c830764252fd0a2662b0f5c957fc027ffcb7bdc0a5e500dfd7d3d6",
    "opac-profile-antarctic": "ee063c6dca68cf9a31d8bb9d993f1fed5cb34c8bb056ac180c97171b5d6b4f19",
}
FOUR_ALIAS_DATA_TREE_SHA256 = "5e1814dd36cf861fd85477a97607299248f8272268df7bf428d31bbb6aa4354a"


class ControlRefusal(RuntimeError):
    pass


def git_blob_sha1(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ControlRefusal(f"cannot load bound module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def bound_inputs() -> tuple[dict[str, Any], dict[str, Any]]:
    if git_blob_sha1(SKELETON_PATH) != EXPECTED_SKELETON_BLOB:
        raise ControlRefusal("v2 skeleton builder byte drift")
    if git_blob_sha1(SEED_LEDGER_PATH) != EXPECTED_SEED_LEDGER_BLOB:
        raise ControlRefusal("v2 seed ledger byte drift")
    skeleton = _load("avps_v2_control_skeleton", SKELETON_PATH).build_review_skeleton()
    ledger = _load("avps_v2_control_seed_ledger", SEED_LEDGER_PATH).validate_ledger()
    if skeleton.get("canonicalSkeletonSha256") != EXPECTED_SKELETON_CANONICAL:
        raise ControlRefusal("v2 skeleton canonical drift")
    if skeleton.get("caseCount") != 360 or skeleton.get("groupCount") != 72 or skeleton.get("statesPerGroup") != 5:
        raise ControlRefusal("v2 skeleton cardinality drift")
    if skeleton.get("seedCount") != 0 or skeleton.get("scientificOrdinal") is not None:
        raise ControlRefusal("v2 skeleton crossed allocation boundary")
    if skeleton.get("profileSha256") != EXPECTED_PROFILE_SHA256:
        raise ControlRefusal("v2 profile-hash universe drift")
    if skeleton.get("fourAliasDataTreeSha256") != FOUR_ALIAS_DATA_TREE_SHA256:
        raise ControlRefusal("v2 four-alias data-tree identity drift")
    if ledger.get("candidateSeedCount") != 72:
        raise ControlRefusal("candidate seed count drift")
    if ledger.get("candidateSeedCanonicalSha256") != EXPECTED_SEED_CANONICAL:
        raise ControlRefusal("candidate seed canonical drift")
    if ledger.get("candidateRowsCanonicalSha256") != EXPECTED_ROWS_CANONICAL:
        raise ControlRefusal("candidate row canonical drift")
    if ledger.get("candidateSeedsAppliedToCases") is not False or ledger.get("scientificOrdinalAllocated") is not False:
        raise ControlRefusal("candidate ledger crossed allocation boundary")
    return skeleton, ledger


def build_disabled_package() -> dict[str, Any]:
    skeleton, ledger = bound_inputs()
    groups = []
    for row in skeleton["groups"]:
        groups.append({
            "groupId": row["groupId"],
            "caseIds": list(row["caseIds"]),
            "stateIds": list(row["stateIds"]),
            "seedStatus": "CANDIDATE_EXISTS_ARTIFACT_ONLY_NOT_APPLIED",
            "scientificOrdinal": None,
            "executionAuthorized": False,
        })
    cases = []
    for row in skeleton["cases"]:
        surface = list(row["preSeedScienceSurface"])
        if any(line.startswith("aerosol_file ") for line in surface):
            raise ControlRefusal("legacy/custom aerosol_file directive leaked into v2 package")
        expected_species = f"aerosol_species_file profiles/{row['stateId']}.four-species.dat INSO WASO SOOT SUSO"
        if surface.count(expected_species) != 1:
            raise ControlRefusal(f"four-species surface drift: {row['caseId']}")
        if surface.count("mc_randomseed <UNALLOCATED_FRESH_AVPS_V2_GROUP_SEED>") != 1:
            raise ControlRefusal("seed placeholder cardinality drift")
        cases.append({
            "caseId": row["caseId"],
            "groupId": row["groupId"],
            "stateId": row["stateId"],
            "profileRelativePath": row["profileRelativePath"],
            "profileSha256": row["profileSha256"],
            "preSeedScienceSurface": surface,
            "preSeedScienceSurfaceSha256": row["preSeedScienceSurfaceSha256"],
            "seedStatus": "CANDIDATE_EXISTS_ARTIFACT_ONLY_NOT_APPLIED",
            "scientificOrdinal": None,
            "renderable": False,
            "executionAuthorized": False,
            "resultOpeningAuthorized": False,
        })
    if len(groups) != 72 or len(cases) != 360:
        raise ControlRefusal("disabled package cardinality drift")
    if len({r["caseId"] for r in cases}) != 360 or len({r["groupId"] for r in groups}) != 72:
        raise ControlRefusal("disabled package identity collision")
    if any(not r["caseId"].startswith("avps-v2-") for r in cases):
        raise ControlRefusal("legacy case namespace leaked into v2 package")
    out = {
        "schemaVersion": 1,
        "stageId": f"{STAGE}-disabled-control-package",
        "status": "REVIEW_ONLY_DISABLED_PACKAGE_NO_ORDINAL_NO_AUTHORIZATION_NO_SOLVER",
        "sourceSkeletonGitBlobSha1": EXPECTED_SKELETON_BLOB,
        "sourceSkeletonCanonicalSha256": EXPECTED_SKELETON_CANONICAL,
        "sourceSeedLedgerGitBlobSha1": EXPECTED_SEED_LEDGER_BLOB,
        "candidateSeedCount": 72,
        "candidateSeedCanonicalSha256": EXPECTED_SEED_CANONICAL,
        "candidateRowsCanonicalSha256": EXPECTED_ROWS_CANONICAL,
        "candidateSeedValuesIncluded": False,
        "profileSha256": dict(EXPECTED_PROFILE_SHA256),
        "fourAliasDataTreeSha256": FOUR_ALIAS_DATA_TREE_SHA256,
        "caseCount": 360,
        "groupCount": 72,
        "statesPerGroup": 5,
        "groups": groups,
        "cases": cases,
        "scientificOrdinal": None,
        "scientificOrdinalAllocated": False,
        "authorizationCreated": False,
        "dispatchCreated": False,
        "candidateSeedsAppliedToCases": False,
        "scientificExecutionAuthorized": False,
        "solverExecutionAuthorized": False,
        "resultOpeningAuthorized": False,
        "productionAuthorized": False,
    }
    out["canonicalPackageSha256"] = canonical_sha256(out)
    return out


def review_summary() -> dict[str, Any]:
    p = build_disabled_package()
    return {
        "status": p["status"],
        "caseCount": p["caseCount"],
        "groupCount": p["groupCount"],
        "candidateSeedCount": p["candidateSeedCount"],
        "candidateSeedCanonicalSha256": p["candidateSeedCanonicalSha256"],
        "candidateRowsCanonicalSha256": p["candidateRowsCanonicalSha256"],
        "profileSha256": p["profileSha256"],
        "canonicalPackageSha256": p["canonicalPackageSha256"],
        "scientificOrdinalAllocated": p["scientificOrdinalAllocated"],
        "authorizationCreated": p["authorizationCreated"],
        "solverExecutionAuthorized": p["solverExecutionAuthorized"],
    }


if __name__ == "__main__":
    print(json.dumps(review_summary(), indent=2, sort_keys=True))
