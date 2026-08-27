from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

STAGE = "aerosol-vertical-profile-sensitivity-v1"
HERE = Path(__file__).resolve().parent
SHA40 = re.compile(r"^[0-9a-f]{40}$")
EXPECTED_SEED_CANONICAL = "a2e22b526dfad84d4f23c0ca8b143d028fddc7e55f78deb93a43e194ebd6c35e"
EXPECTED_ROWS_CANONICAL = "f22de8a9e30ba106759effb1170a5ca1d1e747cb2ac68293fa232dc7ed6ca683"
EXPECTED_EXECUTION_PACKAGE_BLOB = "4b588e5eb289e9074935bf4ca22a4e2c6185bdb9"
EXPECTED_DISABLED_PACKAGE_CANONICAL = "ecf7052454e47a9e047cb944f22b031473c0986e9d8b9cec1aa010d425b39cc1"
EXACT_AFGL_PROFILE_BUNDLE_ARTIFACT_ID = 9658061526
EXACT_AFGL_PROFILE_BUNDLE_ARTIFACT_DIGEST = "sha256:2061136f069e9a16fa5c5b3d0991121bb04d7a268d1b7c7f93c60d734d537b48"
EXACT_AFGL_PROFILE_SHA256 = {
    "opac-profile-continental-average": "e6c296951dfae376bf77948aa92828062ba95d7b1e9c28703befa9cffb5bf198",
    "opac-profile-maritime-clean": "5cbaf5f81f3f36bfcf9b365eaa5d892889da83453c18d58e705b3de9273adc8c",
    "opac-profile-desert": "3d8891b3b67fa8c8c6fd66861d49e9bfad8c937a176b7001c6c47a5571de21ad",
    "opac-profile-arctic": "61eed1e73ac8cc6f044b89870a6874f1d21500008c7747830a2a812bbd87919a",
    "opac-profile-antarctic": "a14460a04afd5154d931b77e55b7adce2ab41aae2e8e4c13afaa0de459aff164",
}


class DesignRefusal(RuntimeError):
    pass


def _git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise DesignRefusal(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def validate_seed_authorization_proof(proof: dict[str, Any], expected_main: str) -> None:
    if SHA40.fullmatch(expected_main or "") is None:
        raise DesignRefusal("expected main SHA invalid")
    if proof.get("stageId") != f"{STAGE}-seed-authorization-recheck":
        raise DesignRefusal("seed proof stage drift")
    if proof.get("status") != "PASS_CANDIDATE_SEEDS_AUTHORIZATION_RECHECK_NOT_ALLOCATED":
        raise DesignRefusal("authorization-time seed proof missing")
    if proof.get("auditedMainHead") != expected_main or proof.get("auditedBranchHeadMatchesRepositoryHead") is not True:
        raise DesignRefusal("seed proof exact-main binding drift")
    if proof.get("candidateSeedCount") != 72:
        raise DesignRefusal("candidate seed count drift")
    if proof.get("candidateSeedCanonicalSha256") != EXPECTED_SEED_CANONICAL:
        raise DesignRefusal("candidate seed canonical hash drift")
    if proof.get("candidateRowsCanonicalSha256") != EXPECTED_ROWS_CANONICAL:
        raise DesignRefusal("candidate row canonical hash drift")
    if proof.get("allCollisionCountersZero") is not True:
        raise DesignRefusal("candidate seed collision counter drift")
    if proof.get("candidateSeedLiteralsTrackedInGit") is not False:
        raise DesignRefusal("candidate seed literals unexpectedly tracked")
    if proof.get("exactHeadTrackedTreeByteScanPassed") is not True or proof.get("trackedTreeExternalCollisionCount") != 0:
        raise DesignRefusal("tracked-tree seed scan did not pass")
    if proof.get("repositoryGlobalCollisionSurfaceScanPassed") is not True or proof.get("repositoryGlobalCollisionCount") != 0:
        raise DesignRefusal("repository-global seed scan did not pass")
    if proof.get("repositoryGlobalDoubleEnumerationStable") is not True:
        raise DesignRefusal("repository-global enumeration unstable")
    if int(proof.get("priorReviewProofArtifactCount") or 0) < 1:
        raise DesignRefusal("prior review proof artifact missing")
    for key in (
        "scientificOrdinalAllocated", "authorizationCreated", "dispatchCreated",
        "candidateSeedsAppliedToCases", "scientificExecutionAuthorized",
        "solverExecutionAuthorized", "resultOpeningAuthorized", "productionAuthorized",
    ):
        if proof.get(key) is not False:
            raise DesignRefusal(f"seed proof crossed control boundary: {key}")


def _frozen_disabled_package() -> dict[str, Any]:
    path = HERE / "execution_package.py"
    if _git_blob_sha1(path) != EXPECTED_EXECUTION_PACKAGE_BLOB:
        raise DesignRefusal("merged disabled execution package byte drift")
    mod = _load("avps_execution_package_for_seeded_design", path)
    package = mod.build_disabled_execution_package()
    if package.get("canonicalPackageSha256") != EXPECTED_DISABLED_PACKAGE_CANONICAL:
        raise DesignRefusal("disabled execution package canonical hash drift")
    if package.get("status") != "DISABLED_EXECUTION_PACKAGE_REVIEW_ONLY_SEEDS_UNALLOCATED":
        raise DesignRefusal("disabled execution package status drift")
    if package.get("caseCount") != 360 or package.get("groupCount") != 72:
        raise DesignRefusal("disabled execution package cardinality drift")
    if package.get("candidateSeedCanonicalSha256") != EXPECTED_SEED_CANONICAL:
        raise DesignRefusal("disabled package seed canonical drift")
    if package.get("candidateRowsCanonicalSha256") != EXPECTED_ROWS_CANONICAL:
        raise DesignRefusal("disabled package row canonical drift")
    if package.get("candidateSeedsAppliedToCases") is not False or package.get("scientificOrdinal") is not None:
        raise DesignRefusal("disabled package crossed allocation boundary")
    if any(row.get("seed") is not None or row.get("executionAuthorized") is not False for row in package.get("cases", [])):
        raise DesignRefusal("disabled package unexpectedly contains allocated/executable case")
    return package


def build_review_execution_design(seed_proof: dict[str, Any], expected_main: str) -> dict[str, Any]:
    validate_seed_authorization_proof(seed_proof, expected_main)
    package = _frozen_disabled_package()
    seed_mod = _load("avps_seed_ledger_for_seeded_design", HERE / "seed_ledger.py")
    ledger = seed_mod.validate_ledger()
    rows = seed_mod.derive_rows()
    if ledger.get("candidateSeedCanonicalSha256") != EXPECTED_SEED_CANONICAL:
        raise DesignRefusal("ledger seed canonical hash drift")
    if ledger.get("candidateRowsCanonicalSha256") != EXPECTED_ROWS_CANONICAL:
        raise DesignRefusal("ledger row canonical hash drift")
    seed_by_group = {str(row["groupId"]): int(row["seed"]) for row in rows}
    if len(seed_by_group) != 72:
        raise DesignRefusal("candidate group seed mapping drift")

    design = copy.deepcopy(package)
    design["status"] = "CANDIDATE_SEEDED_DESIGN_FRESHNESS_PROVEN_REVIEW_ONLY"
    design["sourceDisabledExecutionPackageBlobSha1"] = EXPECTED_EXECUTION_PACKAGE_BLOB
    design["sourceDisabledExecutionPackageCanonicalSha256"] = EXPECTED_DISABLED_PACKAGE_CANONICAL
    design["exactAfglProfileBundleArtifactId"] = EXACT_AFGL_PROFILE_BUNDLE_ARTIFACT_ID
    design["exactAfglProfileBundleArtifactDigest"] = EXACT_AFGL_PROFILE_BUNDLE_ARTIFACT_DIGEST
    design["exactAfglProfileTauSha256"] = dict(EXACT_AFGL_PROFILE_SHA256)
    design["seedCount"] = 72
    design["candidateSeedFreshnessProven"] = True
    design["authorizationTimeSeedRecheckRequired"] = True
    design["seedAuthorizationProofAuditedMain"] = expected_main
    design["candidateSeedsAppliedToCases"] = True
    design["scientificOrdinal"] = None
    design["scientificExecutionAuthorized"] = False
    design["solverExecutionAuthorized"] = False
    design["resultOpeningAuthorized"] = False
    design["productionAuthorized"] = False

    groups = []
    for gid in sorted(seed_by_group):
        groups.append({
            "groupId": gid,
            "candidateSeed": seed_by_group[gid],
            "seedStatus": "CANDIDATE_FRESHNESS_PROVEN_REVIEW_ONLY",
            "executionAuthorized": False,
        })
    design["groups"] = groups

    for case in design["cases"]:
        gid = str(case["groupId"])
        if gid not in seed_by_group:
            raise DesignRefusal(f"missing candidate seed for group {gid}")
        case["seed"] = seed_by_group[gid]
        case["seedStatus"] = "CANDIDATE_FRESHNESS_PROVEN_REVIEW_ONLY"
        case["renderable"] = False
        case["executionAuthorized"] = False
        case["resultOpeningAuthorized"] = False

    if len(design["groups"]) != 72 or len(design["cases"]) != 360:
        raise DesignRefusal("seeded design cardinality drift")
    if len({row["candidateSeed"] for row in design["groups"]}) != 72:
        raise DesignRefusal("candidate group seed uniqueness drift")
    if any(case["seed"] is None for case in design["cases"]):
        raise DesignRefusal("seeded design contains unseeded case")
    if any(case["renderable"] is not False or case["executionAuthorized"] is not False for case in design["cases"]):
        raise DesignRefusal("authorization-review design must remain nonrenderable")

    design.pop("canonicalPackageSha256", None)
    design["canonicalDesignSha256"] = canonical_sha256(design)
    return design
