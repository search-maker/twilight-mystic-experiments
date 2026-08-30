from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

STAGE = "aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery1"
BASE_MAIN = "6f0b3f3c73b23f84951bd7b6a2bad58d00854982"
ORDINAL = 42
CONSUMED_ORDINAL = 41
CONSUMED_RUN = 33236295233
CONSUMED_SEED_CANONICAL = "02f624d582e9b2caba6b920d65a5e8a8bc8fc1a2693623bc2f73abf5d3f706d2"
SEED_HEAD = "3f9a03b913125077a37a3eb56d1c031127bdfd60"
SEED_RUN = 33242753388
SEED_ARTIFACT = 9711902664
SEED_DIGEST = "sha256:12934972f2a533c006a11012d2f2374e76873d9982dae0b1d5db656e6097b460"
SEED_CANONICAL = "a514212990a94a39d577bd038b631a600e18e4c0f750f781bbd7c99b897228a7"
ROWS_CANONICAL = "8213e65782b62d0e1a0ea51d620016fdcaa24b348e726f5570c54f7f1155a895"
PREAUTH_HEAD = "752e7c55740cdc0c6033deda71db9bc0dbb7fdf4"
PREAUTH_RUN = 33245550336
PREAUTH_CONTRACT_RUN = 33245550340
PREAUTH_ARTIFACT = 9712820519
PREAUTH_DIGEST = "sha256:5768dca0f4507c3a345f611ee4a71e1c955d3b1a6c95083add6f7030e55993de"
PREAUTH_CONTENT = "3dd8a3729ff29a6d81f8b2e7ff1fb2e5c8e88e39a010d0a1a7ee561999875ebb"
RESTORED_SUPPORT_BLOB = "095ff86f12a79dc312a51f734b0a03bd318f2337"
LOCKED_PACKAGE = "rubin-libradtran=2.0.6=py312pl5321he9373c2_1"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA64 = re.compile(r"^[0-9a-f]{64}$")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
LEDGER_PATH = ROOT / "review/aerosol-vertical-profile-sensitivity-v2-postconsumption-seed-freshness-v1/seed_ledger.py"
SUPPORT_PATH = ROOT / "review/aerosol-vertical-profile-sensitivity-v2-control-v1/rh_audit_dependency.py"

PROFILE_HASHES = {
    "opac-profile-antarctic": "ee063c6dca68cf9a31d8bb9d993f1fed5cb34c8bb056ac180c97171b5d6b4f19",
    "opac-profile-arctic": "98f2fa5428c830764252fd0a2662b0f5c957fc027ffcb7bdc0a5e500dfd7d3d6",
    "opac-profile-continental-average": "ceed598f7681951cd0e6208b267beb5b41a52ab10311f37ce76f925700caff3d",
    "opac-profile-desert": "2b4d2e03c6ae3143d9bb05d2da49f57f75172dc1f24d34f7d4a4939bf9952fef",
    "opac-profile-maritime-clean": "487b67bd7dbe89d12d032fdf2b33cab545e16a2e0697170648317f1a76362a67",
}
FROZEN_RUNTIME = {
    "fourAliasDataTreeSha256": "5e1814dd36cf861fd85477a97607299248f8272268df7bf428d31bbb6aa4354a",
    "uvspecSha256": "2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3",
    "baseDataTreeSha256": "ad30b49177e9c84e46497d69faf0c75e466996b0d0003f1de210289ae9f847d7",
    "archiveStagedDataTreeSha256": "5d8bbf8e6b91ec3d405dee36f21a94afbb6e5ec6cd67da2dd5dd541738199d80",
    "officialOptpropArchiveSha256": "11daa1f1f4be0fd4ddf7e881ec2005498049674a1540d37b4b1e8f5e16052c7e",
    "afglUsSha256": "dab26290ed81c762ed0c607e5dc2d53393c1462a0c3a528bc5e3f5935191cfb5",
}


class Refusal(RuntimeError):
    pass


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def git_blob_sha1(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise Refusal(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def verify_self_hash(obj: dict[str, Any], field: str = "contentSha256") -> None:
    value = obj.get(field)
    if not isinstance(value, str) or SHA64.fullmatch(value) is None:
        raise Refusal(f"missing/malformed {field}")
    copy = dict(obj)
    copy.pop(field, None)
    if canonical_sha256(copy) != value:
        raise Refusal(f"self-hash drift: {field}")


def validate_recovery_ledger() -> dict[str, Any]:
    ledger = _load("avps_v2_recovery1_authorization_ledger", LEDGER_PATH).validate_ledger()
    expected = {
        "candidateSeedCount": 72,
        "candidateSeedCanonicalSha256": SEED_CANONICAL,
        "candidateRowsCanonicalSha256": ROWS_CANONICAL,
        "consumedOrdinal41SeedCanonicalSha256": CONSUMED_SEED_CANONICAL,
        "overlapWithConsumedOrdinal41SeedCount": 0,
        "candidateSeedsAppliedToCases": False,
        "scientificOrdinalAllocated": False,
        "authorizationCreated": False,
        "solverExecutionAuthorized": False,
        "resultOpeningAuthorized": False,
    }
    for key, value in expected.items():
        if ledger.get(key) != value:
            raise Refusal(f"recovery ledger drift: {key}")
    if len(set(ledger.get("candidateSeeds") or [])) != 72:
        raise Refusal("recovery candidate seed uniqueness drift")
    return ledger


def validate_preauthorization(report: dict[str, Any]) -> None:
    verify_self_hash(report)
    expected = {
        "schemaVersion": 1,
        "stageId": f"{STAGE}-preauthorization",
        "status": "PASS_POSTCONSUMPTION_RECOVERY1_PREAUTHORIZATION_SURFACE_CLEAN_NOT_ALLOCATED",
        "auditedHead": PREAUTH_HEAD,
        "baseMain": BASE_MAIN,
        "consumedScientificOrdinal": CONSUMED_ORDINAL,
        "occupiedMaxScientificOrdinal": CONSUMED_ORDINAL,
        "nextAvailableScientificOrdinal": ORDINAL,
        "authorizationBranch": f"authorization/{STAGE}-ordinal-{ORDINAL}",
        "dispatchBranch": f"dispatch/{STAGE}-ordinal-{ORDINAL}",
        "candidateSeedCount": 72,
        "candidateSeedCanonicalSha256": SEED_CANONICAL,
        "candidateRowsCanonicalSha256": ROWS_CANONICAL,
        "consumedOrdinal41SeedCanonicalSha256": CONSUMED_SEED_CANONICAL,
        "overlapWithConsumedOrdinal41SeedCount": 0,
        "scientificOrdinalAllocated": False,
        "authorizationCreated": False,
        "dispatchCreated": False,
        "candidateSeedsAppliedToCases": False,
        "scientificExecutionAuthorized": False,
        "solverExecutionAuthorized": False,
        "resultOpeningAuthorized": False,
        "scientificRuntimeSetupPerformed": False,
        "taylorOrJerusalemUsed": False,
        "levelBAuthorized": False,
        "protectedHoldoutOpened": False,
        "productionAuthorized": False,
        "separateAuthorizationReviewRequired": True,
        "nextOrdinalHardCoded": False,
        "contentSha256": PREAUTH_CONTENT,
    }
    for key, value in expected.items():
        if report.get(key) != value:
            raise Refusal(f"preauthorization drift: {key}: {report.get(key)!r} != {value!r}")
    seed = report.get("authorizationTimeSeedRecheck") or {}
    if seed.get("repositoryGlobalCollisionCount") != 0 or seed.get("repositoryGlobalDoubleEnumerationStable") is not True:
        raise Refusal("preauthorization seed surface is not clean/stable")
    if any(int(v or 0) != 0 for v in (seed.get("repositoryGlobalPostFenceArrivalCounts") or {}).values()):
        raise Refusal("preauthorization snapshot had post-fence arrivals")


def validate_bound_runtime() -> None:
    if not SUPPORT_PATH.is_file() or git_blob_sha1(SUPPORT_PATH) != RESTORED_SUPPORT_BLOB:
        raise Refusal("restored frozen runtime support byte drift")


def build_document(control_head: str, preauthorization: dict[str, Any], live_surface: dict[str, Any]) -> dict[str, Any]:
    if SHA40.fullmatch(control_head or "") is None:
        raise Refusal("control head malformed")
    validate_preauthorization(preauthorization)
    validate_recovery_ledger()
    validate_bound_runtime()
    expected_live = {
        "status": "PASS_RECOVERY1_AUTHORIZATION_CONTROL_LIVE_SURFACE_NOT_ALLOCATED",
        "consumedOrdinal": CONSUMED_ORDINAL,
        "occupiedMaxScientificOrdinal": CONSUMED_ORDINAL,
        "nextAvailableScientificOrdinal": ORDINAL,
        "authorizationBranchExists": False,
        "dispatchBranchExists": False,
        "allocationMarkerExists": False,
        "consumedMarkerExists": False,
        "candidateSeedCollisionCount": 0,
        "scientificOrdinalAllocated": False,
    }
    for key, value in expected_live.items():
        if live_surface.get(key) != value:
            raise Refusal(f"live surface drift: {key}")
    for key in ("ordinalObservationsCanonicalSha256", "repositoryGlobalStableContextSha256"):
        if not isinstance(live_surface.get(key), str) or SHA64.fullmatch(live_surface[key]) is None:
            raise Refusal(f"live surface hash missing/malformed: {key}")

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
        "consumedPredecessorScientificOrdinal": CONSUMED_ORDINAL,
        "consumedPredecessorRunId": CONSUMED_RUN,
        "consumedPredecessorRunAttempt": 1,
        "consumedPredecessorSeedCanonicalSha256": CONSUMED_SEED_CANONICAL,
        "consumedPredecessorReusable": False,
        "preauthorizationHead": PREAUTH_HEAD,
        "preauthorizationRunId": PREAUTH_RUN,
        "preauthorizationRunAttempt": 1,
        "preauthorizationContractRunId": PREAUTH_CONTRACT_RUN,
        "preauthorizationArtifactId": PREAUTH_ARTIFACT,
        "preauthorizationArtifactDigest": PREAUTH_DIGEST,
        "preauthorizationReportContentSha256": PREAUTH_CONTENT,
        "seedReviewHead": SEED_HEAD,
        "seedReviewRunId": SEED_RUN,
        "seedReviewRunAttempt": 1,
        "seedReviewArtifactId": SEED_ARTIFACT,
        "seedReviewArtifactDigest": SEED_DIGEST,
        "candidateSeedCount": 72,
        "candidateSeedCanonicalSha256": SEED_CANONICAL,
        "candidateRowsCanonicalSha256": ROWS_CANONICAL,
        "candidateSeedValuesIncluded": False,
        "candidateSeedsAppliedToTrackedCases": False,
        "candidateSeedsAuthorizedForLaterInMemoryApplication": True,
        "restoredRuntimeSupportGitBlobSha1": RESTORED_SUPPORT_BLOB,
        "exactFourSpeciesProfileSha256": dict(PROFILE_HASHES),
        "lockedLibRadtranPackage": LOCKED_PACKAGE,
        **FROZEN_RUNTIME,
        "authorizationControlLiveSurfaceSha256": canonical_sha256(live_surface),
        "authorizationControlOrdinalObservationsCanonicalSha256": live_surface["ordinalObservationsCanonicalSha256"],
        "authorizationControlRepositoryGlobalStableContextSha256": live_surface["repositoryGlobalStableContextSha256"],
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
        "levelBAuthorized": False,
        "protectedHoldoutOpened": False,
        "productionAuthorized": False,
        "taylorOrJerusalemFitAuthorized": False,
        "githubRerunAllowed": False,
        "retryAllowed": False,
        "resumeAllowed": False,
        "workflowRunAttemptRequired": 1,
    }
    doc["authorizationDocumentContentSha256"] = canonical_sha256(doc)
    return doc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--control-head", required=True)
    parser.add_argument("--preauthorization", type=Path, required=True)
    parser.add_argument("--live-surface", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    doc = build_document(
        args.control_head,
        json.loads(args.preauthorization.read_text()),
        json.loads(args.live_surface.read_text()),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
