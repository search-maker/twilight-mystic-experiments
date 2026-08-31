from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

EXPECTED_STAGE = "aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery4"
EXPECTED_SEED_CANONICAL = "ddded6b2d170ca2fac8d498bdba2887446c16995df0880d948fb2be00870b3de"
EXPECTED_ROWS_CANONICAL = "c439de417520b330c037e2628df02b6955f652563300aa5ef30477abf7661a98"
EXPECTED_ORDINAL41_SEED_CANONICAL = "02f624d582e9b2caba6b920d65a5e8a8bc8fc1a2693623bc2f73abf5d3f706d2"
EXPECTED_ORDINAL42_SEED_CANONICAL = "a514212990a94a39d577bd038b631a600e18e4c0f750f781bbd7c99b897228a7"
EXPECTED_ORDINAL43_SEED_CANONICAL = "38c074fe01bd6d09fa7dc78af1ad323e2f42b606ca992c2950b8fc1f5b343a9f"
EXPECTED_ORDINAL44_SEED_CANONICAL = "d2817b1ea4f2bdc8cb1842e565b099b015e4e28c5874482629fadc450069d9bf"
EXPECTED_SUCCESSOR = 45

PROFILE_SHA256 = {
    "opac-profile-antarctic": "ee063c6dca68cf9a31d8bb9d993f1fed5cb34c8bb056ac180c97171b5d6b4f19",
    "opac-profile-arctic": "98f2fa5428c830764252fd0a2662b0f5c957fc027ffcb7bdc0a5e500dfd7d3d6",
    "opac-profile-continental-average": "ceed598f7681951cd0e6208b267beb5b41a52ab10311f37ce76f925700caff3d",
    "opac-profile-desert": "2b4d2e03c6ae3143d9bb05d2da49f57f75172dc1f24d34f7d4a4939bf9952fef",
    "opac-profile-maritime-clean": "487b67bd7dbe89d12d032fdf2b33cab545e16a2e0697170648317f1a76362a67",
}


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    ).hexdigest()


def validate_report(report: dict[str, Any], *, status: str) -> None:
    expected = {
        "status": status,
        "candidateSeedCount": 72,
        "candidateSeedCanonicalSha256": EXPECTED_SEED_CANONICAL,
        "candidateRowsCanonicalSha256": EXPECTED_ROWS_CANONICAL,
        "nextOrdinalHardCoded": False,
    }
    for key, value in expected.items():
        if report.get(key) != value:
            raise SystemExit(f"report drift {key}: {report.get(key)!r} != {value!r}")
    if report.get("nextAvailableScientificOrdinal") != EXPECTED_SUCCESSOR:
        raise SystemExit("fresh live successor is not preregistered ordinal 45")
    if report.get("occupiedMaxScientificOrdinal") != EXPECTED_SUCCESSOR - 1:
        raise SystemExit("fresh occupied ordinal surface no longer ends at 44")
    observed = {int(x) for x in report.get("consumedOrdinalsObserved", [])}
    if not {41, 42, 43, 44}.issubset(observed):
        raise SystemExit("consumed predecessor observation incomplete")
    for key in (
        "scientificOrdinalAllocated",
        "authorizationCreated",
        "dispatchCreated",
        "candidateSeedsAppliedToCases",
        "scientificExecutionAuthorized",
        "solverExecutionAuthorized",
        "resultOpeningAuthorized",
        "scientificRuntimeSetupPerformed",
        "taylorOrJerusalemUsed",
        "levelBAuthorized",
        "protectedHoldoutOpened",
        "productionAuthorized",
        "newMappingAuthorized",
    ):
        if report.get(key) is not False:
            raise SystemExit(f"report crossed protected boundary: {key}")
    given = report.get("contentSha256")
    tmp = dict(report)
    tmp.pop("contentSha256", None)
    if given != canonical_sha256(tmp):
        raise SystemExit("report content hash mismatch")


def build(args: argparse.Namespace) -> int:
    v4 = json.loads(args.v4_report.read_text())
    validate_report(v4, status="PASS_POSTCONSUMPTION_RECOVERY4_PREAUTHORIZATION_SURFACE_CLEAN_NOT_ALLOCATED")
    fresh = json.loads(args.fresh_report.read_text())
    validate_report(fresh, status="PASS_POSTCONSUMPTION_RECOVERY4_AUTHORIZATION_CONTROL_SURFACE_CLEAN_NOT_ALLOCATED")
    n = int(fresh["nextAvailableScientificOrdinal"])
    auth_branch = f"authorization/{EXPECTED_STAGE}-ordinal-{n}"
    dispatch_branch = f"dispatch/{EXPECTED_STAGE}-ordinal-{n}"
    if fresh.get("authorizationBranch") != auth_branch or fresh.get("dispatchBranch") != dispatch_branch:
        raise SystemExit("fresh branch derivation drift")

    auth = {
        "schemaVersion": 4,
        "stageId": EXPECTED_STAGE,
        "status": "AUTHORIZED_POSTCONSUMPTION_RECOVERY4_PENDING_SEPARATE_ALLOCATION_AND_DISPATCH",
        "scientificOrdinal": n,
        "nextOrdinalHardCoded": False,
        "consumedPredecessors": [
            {"scientificOrdinal": 41, "runId": 33236295233, "runAttempt": 1, "failureClass": "PRE_SOLVER_RUNTIME_SUPPORT_TRANSPORT_OMISSION_NO_SCIENTIFIC_RESULT", "reusable": False},
            {"scientificOrdinal": 42, "runId": 33259899524, "runAttempt": 1, "failureClass": "PRE_SOLVER_RELOCATED_SEED_LEDGER_PATH_CONTEXT_NO_SCIENTIFIC_RESULT", "reusable": False},
            {"scientificOrdinal": 43, "runId": 33298433506, "runAttempt": 1, "failureClass": "PRE_SOLVER_REPOSITORY_GLOBAL_SNAPSHOT_STABILITY_FAILURE_NO_SCIENTIFIC_RESULT", "reusable": False},
            {"scientificOrdinal": 44, "runId": 33334396129, "runAttempt": 1, "failureClass": "CONSUMED_PRE_SOLVER_ZERO_MYSTIC_NO_SCIENTIFIC_RESULT", "reusable": False},
        ],
        "authorizationBranch": auth_branch,
        "dispatchBranch": dispatch_branch,
        "executionKey": f"{EXPECTED_STAGE}:numerical:{n}",
        "exactAuthorizationParentCommit": args.expected_head,
        "exactAuthorizationCommit": None,
        "reviewPackageMainSha": args.base_main,
        "v4PreauthorizationPr": 765,
        "v4PreauthorizationHead": "37cf271a8be6c3e0810831fbe224d2ac00f5aacf",
        "v4PreauthorizationRunId": 33357235094,
        "v4PreauthorizationArtifactId": 9745747903,
        "v4PreauthorizationArtifactDigest": "sha256:80143a05b55e099919bcf541f5a1a09214931d8923dcb34507780b4196ea7258",
        "v4PreauthorizationFenceBeginComment": 5473721466,
        "v4PreauthorizationFenceEndComment": 5473855111,
        "v4PreauthorizationTransitionComment": 5473880087,
        "recovery4SeedGlobalControlRunId": 33352358740,
        "recovery4SeedGlobalControlArtifactId": 9744246112,
        "recovery4SeedGlobalControlArtifactDigest": "sha256:581ada9f8056d1ee73bb9bc2d81e1abdb7a9bac391e7ad889490e80af5038e27",
        "candidateSeedCount": 72,
        "candidateSeedCanonicalSha256": EXPECTED_SEED_CANONICAL,
        "candidateRowsCanonicalSha256": EXPECTED_ROWS_CANONICAL,
        "consumedOrdinal41SeedCanonicalSha256": EXPECTED_ORDINAL41_SEED_CANONICAL,
        "consumedOrdinal42SeedCanonicalSha256": EXPECTED_ORDINAL42_SEED_CANONICAL,
        "consumedOrdinal43SeedCanonicalSha256": EXPECTED_ORDINAL43_SEED_CANONICAL,
        "consumedOrdinal44SeedCanonicalSha256": EXPECTED_ORDINAL44_SEED_CANONICAL,
        "candidateSeedValuesIncluded": False,
        "candidateSeedsAppliedToTrackedCases": False,
        "candidateSeedsAuthorizedForLaterInMemoryApplication": True,
        "freshAuthorizationSeedStableContextSha256": fresh["authorizationTimeSeedRecheck"]["repositoryGlobalStableContextSha256"],
        "freshAuthorizationSeedSnapshotFenceSha256": fresh["authorizationTimeSeedRecheck"]["repositoryGlobalSnapshotFenceSha256"],
        "freshAuthorizationOrdinalObservationsCanonicalSha256": fresh["ordinalObservationsCanonicalSha256"],
        "exactFourSpeciesProfileSha256": PROFILE_SHA256,
        "fourAliasDataTreeSha256": "5e1814dd36cf861fd85477a97607299248f8272268df7bf428d31bbb6aa4354a",
        "lockedLibRadtranPackage": "rubin-libradtran=2.0.6=py312pl5321he9373c2_1",
        "uvspecSha256": "2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3",
        "baseDataTreeSha256": "ad30b49177e9c84e46497d69faf0c75e466996b0d0003f1de210289ae9f847d7",
        "archiveStagedDataTreeSha256": "5d8bbf8e6b91ec3d405dee36f21a94afbb6e5ec6cd67da2dd5dd541738199d80",
        "officialOptpropArchiveSha256": "11daa1f1f4be0fd4ddf7e881ec2005498049674a1540d37b4b1e8f5e16052c7e",
        "afglUsSha256": "dab26290ed81c762ed0c607e5dc2d53393c1462a0c3a528bc5e3f5935191cfb5",
        "caseCount": 360,
        "commonRandomNumberGroupCount": 72,
        "statesPerGroup": 5,
        "photonHistoriesPerCase": 20000000,
        "frozenScientificDesignChanged": False,
        "snapshotFenceReleaseBarrierRequired": True,
        "scientificExecutionAuthorized": True,
        "solverExecutionAuthorized": True,
        "dispatchAuthorized": False,
        "automaticDispatch": False,
        "consumed": False,
        "resultOpeningAuthorized": False,
        "levelBOpeningAuthorized": False,
        "protectedHoldoutOpeningAuthorized": False,
        "productionAuthorized": False,
        "taylorOrJerusalemFitAuthorized": False,
        "newMappingAuthorized": False,
        "githubRerunAllowed": False,
        "retryAllowed": False,
        "resumeAllowed": False,
        "workflowRunAttemptRequired": 1,
    }
    auth["authorizationDocumentContentSha256"] = canonical_sha256(auth)
    receipt = {
        "schemaVersion": 1,
        "status": "PASS_RECOVERY4_AUTHORIZATION_CONTROL_PROPOSAL_NOT_ALLOCATED_NOT_DISPATCHED",
        "controlHead": args.expected_head,
        "scientificOrdinalProposed": n,
        "nextOrdinalHardCoded": False,
        "authorizationBranchProposed": auth_branch,
        "dispatchBranchProposed": dispatch_branch,
        "candidateSeedCanonicalSha256": EXPECTED_SEED_CANONICAL,
        "candidateRowsCanonicalSha256": EXPECTED_ROWS_CANONICAL,
        "authorizationJsonSha256": hashlib.sha256((json.dumps(auth, indent=2, sort_keys=True) + "\n").encode()).hexdigest(),
        "scientificOrdinalAllocated": False,
        "authorizationBranchCreated": False,
        "dispatchCreated": False,
        "scientificRuntimeSetupPerformed": False,
        "solverExecutionPerformed": False,
        "resultOpeningPerformed": False,
        "levelBOpened": False,
        "protectedHoldoutOpened": False,
        "productionAuthorized": False,
        "taylorOrJerusalemUsed": False,
        "newMappingAuthorized": False,
    }
    receipt["contentSha256"] = canonical_sha256(receipt)
    args.authorization_output.write_text(json.dumps(auth, indent=2, sort_keys=True) + "\n")
    args.receipt_output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return 0


def verify(args: argparse.Namespace) -> int:
    fresh = json.loads(args.fresh_report.read_text())
    validate_report(fresh, status="PASS_POSTCONSUMPTION_RECOVERY4_AUTHORIZATION_CONTROL_SURFACE_CLEAN_NOT_ALLOCATED")
    auth = json.loads(args.authorization_output.read_text())
    receipt = json.loads(args.receipt_output.read_text())
    if auth.get("scientificOrdinal") != EXPECTED_SUCCESSOR or receipt.get("scientificOrdinalProposed") != EXPECTED_SUCCESSOR:
        raise SystemExit("proposal ordinal drift")
    if auth.get("newMappingAuthorized") is not False or receipt.get("newMappingAuthorized") is not False:
        raise SystemExit("richer Level-B mapping unexpectedly authorized")
    for key in (
        "scientificOrdinalAllocated",
        "authorizationBranchCreated",
        "dispatchCreated",
        "scientificRuntimeSetupPerformed",
        "solverExecutionPerformed",
        "resultOpeningPerformed",
        "levelBOpened",
        "protectedHoldoutOpened",
        "productionAuthorized",
        "taylorOrJerusalemUsed",
    ):
        if receipt.get(key) is not False:
            raise SystemExit(f"control boundary crossed: {key}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build")
    b.add_argument("--v4-report", type=Path, required=True)
    b.add_argument("--fresh-report", type=Path, required=True)
    b.add_argument("--expected-head", required=True)
    b.add_argument("--base-main", required=True)
    b.add_argument("--authorization-output", type=Path, required=True)
    b.add_argument("--receipt-output", type=Path, required=True)
    v = sub.add_parser("verify")
    v.add_argument("--fresh-report", type=Path, required=True)
    v.add_argument("--authorization-output", type=Path, required=True)
    v.add_argument("--receipt-output", type=Path, required=True)
    args = parser.parse_args()
    return build(args) if args.command == "build" else verify(args)


if __name__ == "__main__":
    raise SystemExit(main())