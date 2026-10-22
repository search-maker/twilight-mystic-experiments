from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

STAGE = "aerosol-vertical-profile-sensitivity-v2"
BASE_MAIN = "99ade7798627e67921139697ba1a004fa8a304bb"
ORDINAL = 41
SEED_CANONICAL = "02f624d582e9b2caba6b920d65a5e8a8bc8fc1a2693623bc2f73abf5d3f706d2"
ROWS_CANONICAL = "41f70d6a0381db6b569d3f4e17d74bb38b05cf212c2f2e432455a502f73dc670"
PREAUTH_HEAD = "a4e4700babddf0924135f5cc6ec6bfd21d8c9ec2"
PREAUTH_RUN = 33203372878
PREAUTH_ARTIFACT = 9699064164
PREAUTH_DIGEST = "sha256:b1125375bae24638375853d3724c1c96ba1572dc02e1619eff37d9fdca70b92e"
CONTROL_HEAD = "8a5d73974b02ba21fc2f010bbd911538e6981de2"
CONTROL_RUN = 33205661865
CONTROL_ARTIFACT = 9699546728
CONTROL_DIGEST = "sha256:9badcdc03bbeb181f731352afc48b75c67c14dc95a986fcf32163677d4ea972d"
LOCKED_PACKAGE = "rubin-libradtran=2.0.6=py312pl5321he9373c2_1"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA64 = re.compile(r"^[0-9a-f]{64}$")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CONTROL_DIR = ROOT / "review/aerosol-vertical-profile-sensitivity-v2-control-v1"

BOUND_BLOBS = {
    CONTROL_DIR / "control_package.py": "62bacf15d145051fcc5259a24c310eac761d0e74",
    CONTROL_DIR / "adapter.py": "c245eac2fe5b5d026e46ec4253bc377c5fde97ec",
    CONTROL_DIR / "runtime_stage.py": "0d3ac10f3ef7d22f0205854233a6c37cbba03f7c",
}


class Refusal(RuntimeError):
    pass


def git_blob_sha1(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise Refusal(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def validate_bound_sources() -> tuple[Any, Any, Any]:
    for path, expected in BOUND_BLOBS.items():
        if not path.is_file() or git_blob_sha1(path) != expected:
            raise Refusal(f"bound #600 source byte drift: {path}")
    return (
        _load("avps_v2_auth_control_package", CONTROL_DIR / "control_package.py"),
        _load("avps_v2_auth_adapter", CONTROL_DIR / "adapter.py"),
        _load("avps_v2_auth_runtime", CONTROL_DIR / "runtime_stage.py"),
    )


def _verify_self_hash(obj: dict[str, Any], field: str) -> None:
    expected = obj.get(field)
    if not isinstance(expected, str) or SHA64.fullmatch(expected) is None:
        raise Refusal(f"missing/malformed {field}")
    q = dict(obj)
    q.pop(field, None)
    if canonical_sha256(q) != expected:
        raise Refusal(f"self-hash drift: {field}")


def validate_preauthorization(report: dict[str, Any]) -> None:
    _verify_self_hash(report, "contentSha256")
    expected = {
        "stageId": f"{STAGE}-preauthorization",
        "status": "PASS_V2_PREAUTHORIZATION_SURFACE_CLEAN_NOT_ALLOCATED",
        "auditedHead": PREAUTH_HEAD,
        "baseMain": BASE_MAIN,
        "latestConsumedScientificOrdinal": 40,
        "globalOrdinalMaxObserved": 40,
        "nextAvailableScientificOrdinal": ORDINAL,
        "authorizationBranch": f"authorization/{STAGE}-ordinal-{ORDINAL}",
        "dispatchBranch": f"dispatch/{STAGE}-ordinal-{ORDINAL}",
        "candidateSeedCount": 72,
        "candidateSeedCanonicalSha256": SEED_CANONICAL,
        "candidateRowsCanonicalSha256": ROWS_CANONICAL,
        "scientificOrdinalAllocated": False,
        "authorizationCreated": False,
        "dispatchCreated": False,
        "candidateSeedsAppliedToCases": False,
        "scientificExecutionAuthorized": False,
        "solverExecutionAuthorized": False,
        "resultOpeningAuthorized": False,
        "scientificRuntimeSetupPerformed": False,
        "levelBAuthorized": False,
        "productionAuthorized": False,
    }
    for key, value in expected.items():
        if report.get(key) != value:
            raise Refusal(f"preauthorization drift: {key}")


def validate_control_receipt(receipt: dict[str, Any]) -> None:
    _verify_self_hash(receipt, "contentSha256")
    expected = {
        "stageId": f"{STAGE}-control-v1-review",
        "status": "PASS_DISABLED_V2_CONTROL_PACKAGE_REVIEW_NO_ORDINAL_NO_AUTHORIZATION_NO_SOLVER",
        "reviewHead": CONTROL_HEAD,
        "workflowRunId": CONTROL_RUN,
        "workflowRunAttempt": 1,
        "caseCount": 360,
        "groupCount": 72,
        "statesPerGroup": 5,
        "candidateSeedCount": 72,
        "candidateSeedCanonicalSha256": SEED_CANONICAL,
        "candidateRowsCanonicalSha256": ROWS_CANONICAL,
        "candidateSeedValuesIncluded": False,
        "trackedCandidateSeedCollisionCount": 0,
        "scientificOrdinalAllocated": False,
        "authorizationCreated": False,
        "dispatchCreated": False,
        "candidateSeedsAppliedToCases": False,
        "scientificExecutionAuthorized": False,
        "solverExecutionAuthorized": False,
        "libRadtranInstalled": False,
        "libRadtranExecuted": False,
        "resultOpeningAuthorized": False,
        "productionAuthorized": False,
    }
    for key, value in expected.items():
        if receipt.get(key) != value:
            raise Refusal(f"#600 receipt drift: {key}")


def validate_live_surface(surface: dict[str, Any], control_head: str) -> None:
    if SHA40.fullmatch(control_head or "") is None:
        raise Refusal("control head malformed")
    expected = {
        "status": "PASS_AUTHORIZATION_CONTROL_LIVE_SURFACE_NOT_ALLOCATED",
        "reviewHead": control_head,
        "latestConsumedScientificOrdinal": 40,
        "globalOrdinalMaxObserved": 40,
        "nextAvailableScientificOrdinal": ORDINAL,
        "candidateSeedCount": 72,
        "candidateSeedCanonicalSha256": SEED_CANONICAL,
        "candidateRowsCanonicalSha256": ROWS_CANONICAL,
        "repositoryGlobalCollisionCount": 0,
        "repositoryGlobalDoubleEnumerationStable": True,
        "authorizationBranchExists": False,
        "dispatchBranchExists": False,
        "ordinal41IssueMarkerExists": False,
        "scientificOrdinalAllocated": False,
    }
    for key, value in expected.items():
        if surface.get(key) != value:
            raise Refusal(f"live authorization-control surface drift: {key}")
    for key in ("repositoryGlobalStableContextSha256", "repositoryGlobalSnapshotFenceSha256", "ordinalObservationsCanonicalSha256"):
        value = surface.get(key)
        if not isinstance(value, str) or SHA64.fullmatch(value) is None:
            raise Refusal(f"live surface hash missing/malformed: {key}")


def build_document(
    control_head: str,
    preauthorization: dict[str, Any],
    control_receipt: dict[str, Any],
    live_surface: dict[str, Any],
) -> dict[str, Any]:
    package_mod, adapter, runtime = validate_bound_sources()
    validate_preauthorization(preauthorization)
    validate_control_receipt(control_receipt)
    validate_live_surface(live_surface, control_head)

    package = package_mod.build_disabled_package()
    if package.get("caseCount") != 360 or package.get("groupCount") != 72 or package.get("statesPerGroup") != 5:
        raise Refusal("disabled package cardinality drift")
    if package.get("candidateSeedValuesIncluded") is not False:
        raise Refusal("disabled package serialized candidate seeds")
    if package.get("scientificOrdinalAllocated") is not False or package.get("authorizationCreated") is not False:
        raise Refusal("disabled package crossed authorization boundary")
    if package.get("candidateSeedCanonicalSha256") != SEED_CANONICAL or package.get("candidateRowsCanonicalSha256") != ROWS_CANONICAL:
        raise Refusal("disabled package seed identity drift")

    profile_hashes = dict(adapter.EXPECTED_PROFILE_SHA256)
    if len(profile_hashes) != 5:
        raise Refusal("profile hash universe drift")

    doc = {
        "schemaVersion": 1,
        "stageId": STAGE,
        "status": "AUTHORIZED_PENDING_SEPARATE_DISPATCH",
        "scientificOrdinal": ORDINAL,
        "authorizationBranch": f"authorization/{STAGE}-ordinal-{ORDINAL}",
        "dispatchBranch": f"dispatch/{STAGE}-ordinal-{ORDINAL}",
        "executionKey": f"{STAGE}:numerical:{ORDINAL}",
        "exactAuthorizationParentCommit": control_head,
        "reviewPackageMainSha": BASE_MAIN,
        "exactAuthorizationCommit": None,
        "preauthorizationHead": PREAUTH_HEAD,
        "preauthorizationRunId": PREAUTH_RUN,
        "preauthorizationArtifactId": PREAUTH_ARTIFACT,
        "preauthorizationArtifactDigest": PREAUTH_DIGEST,
        "preauthorizationReportContentSha256": preauthorization["contentSha256"],
        "disabledControlReviewHead": CONTROL_HEAD,
        "disabledControlReviewRunId": CONTROL_RUN,
        "disabledControlReviewArtifactId": CONTROL_ARTIFACT,
        "disabledControlReviewArtifactDigest": CONTROL_DIGEST,
        "disabledControlReviewReceiptContentSha256": control_receipt["contentSha256"],
        "authorizationControlLiveSurfaceSha256": canonical_sha256(live_surface),
        "authorizationControlRepositoryGlobalStableContextSha256": live_surface["repositoryGlobalStableContextSha256"],
        "authorizationControlRepositoryGlobalSnapshotFenceSha256": live_surface["repositoryGlobalSnapshotFenceSha256"],
        "authorizationControlOrdinalObservationsCanonicalSha256": live_surface["ordinalObservationsCanonicalSha256"],
        "candidateSeedCount": 72,
        "candidateSeedCanonicalSha256": SEED_CANONICAL,
        "candidateRowsCanonicalSha256": ROWS_CANONICAL,
        "candidateSeedValuesIncluded": False,
        "candidateSeedsAppliedToTrackedCases": False,
        "candidateSeedsAuthorizedForLaterInMemoryApplication": True,
        "disabledControlPackageCanonicalSha256": package["canonicalPackageSha256"],
        "exactFourSpeciesProfileSha256": profile_hashes,
        "fourAliasDataTreeSha256": adapter.EXPECTED_FOUR_ALIAS_TREE_SHA256,
        "lockedLibRadtranPackage": LOCKED_PACKAGE,
        "uvspecSha256": runtime.EXPECTED_UVSPEC_SHA256,
        "baseDataTreeSha256": runtime.EXPECTED_BASE_DATA_TREE_SHA256,
        "archiveStagedDataTreeSha256": runtime.EXPECTED_ARCHIVE_STAGED_TREE_SHA256,
        "officialOptpropArchiveSha256": runtime.EXPECTED_ARCHIVE_SHA256,
        "afglUsSha256": runtime.EXPECTED_AFGL_SHA256,
        "caseCount": 360,
        "commonRandomNumberGroupCount": 72,
        "statesPerGroup": 5,
        "photonHistoriesPerCase": 20_000_000,
        "scientificExecutionAuthorized": True,
        "solverExecutionAuthorized": True,
        "dispatchAuthorized": False,
        "automaticDispatch": False,
        "consumed": False,
        "resultOpeningAuthorized": False,
        "productionAuthorized": False,
        "taylorOrJerusalemFitAuthorized": False,
        "githubRerunAllowed": False,
        "retryAllowed": False,
        "resumeAllowed": False,
        "workflowRunAttemptRequired": 1,
    }
    doc["authorizationDocumentContentSha256"] = canonical_sha256(doc)
    return doc


def validate_document(
    auth: dict[str, Any],
    control_head: str,
    preauthorization: dict[str, Any],
    control_receipt: dict[str, Any],
    live_surface: dict[str, Any],
) -> None:
    expected = build_document(control_head, preauthorization, control_receipt, live_surface)
    if auth != expected:
        raise Refusal("authorization document does not exactly match frozen expected document")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--control-head", required=True)
    ap.add_argument("--preauthorization", type=Path, required=True)
    ap.add_argument("--control-receipt", type=Path, required=True)
    ap.add_argument("--live-surface", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    doc = build_document(
        args.control_head,
        json.loads(args.preauthorization.read_text()),
        json.loads(args.control_receipt.read_text()),
        json.loads(args.live_surface.read_text()),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
