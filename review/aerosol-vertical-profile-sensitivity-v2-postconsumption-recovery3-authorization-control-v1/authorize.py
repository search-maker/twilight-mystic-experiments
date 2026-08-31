from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

V3_HEAD = "ec8af2af3e4eff1c9afd51d2d42a2b93698ab51a"
V3_PATH = "review/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3-preauthorization-v3/preauthorize.py"
V3_BLOB = "286b489911ce83f4eb6d6f0817f3c6271731a036"
CONTROL_BRANCH = "review/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3-authorization-control-v1"
EXPECTED_SEED_CANONICAL = "d2817b1ea4f2bdc8cb1842e565b099b015e4e28c5874482629fadc450069d9bf"
EXPECTED_ROWS_CANONICAL = "b6a519eadacdb99ea53c52d483c8acfeba05829643cb988de21682a53fc47896"
EXPECTED_ORDINAL41_SEED_CANONICAL = "02f624d582e9b2caba6b920d65a5e8a8bc8fc1a2693623bc2f73abf5d3f706d2"
EXPECTED_ORDINAL42_SEED_CANONICAL = "a514212990a94a39d577bd038b631a600e18e4c0f750f781bbd7c99b897228a7"
EXPECTED_ORDINAL43_SEED_CANONICAL = "38c074fe01bd6d09fa7dc78af1ad323e2f42b606ca992c2950b8fc1f5b343a9f"

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


def _load_v3():
    base = os.environ.get("AVPS_AUTH_CONTROL_BASE_MAIN")
    if not base or len(base) != 40:
        raise SystemExit("AVPS_AUTH_CONTROL_BASE_MAIN must be exact live main")
    got = subprocess.check_output(["git", "rev-parse", f"{V3_HEAD}:{V3_PATH}"], text=True).strip()
    if got != V3_BLOB:
        raise SystemExit(f"bound v3 preauthorization source drift: {got} != {V3_BLOB}")
    source = subprocess.check_output(["git", "show", f"{V3_HEAD}:{V3_PATH}"], text=True)
    temp = Path(os.environ.get("RUNNER_TEMP") or ".") / "avps-recovery3-bound-v3-preauthorize.py"
    temp.write_text(source)
    spec = importlib.util.spec_from_file_location("avps_recovery3_auth_control_bound_v3", temp)
    if spec is None or spec.loader is None:
        raise SystemExit("cannot load exact v3 preauthorization source")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    root = Path(__file__).resolve().parents[2]
    module.ROOT = root
    module.GENERIC_SCANNER = root / "experiments/aerosol-family-challenge-v2/repository_global_seed_scan.py"
    module.R8_DIR = root / "experiments/aerosol-family-challenge-v2-r8/execution-candidate"
    module.RECOVERY_LEDGER = root / "review/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3-seed-freshness-v1/seed_ledger.py"
    module.PREAUTH_BRANCH = CONTROL_BRANCH
    module.BASE_MAIN = base
    return module


def validate_v4(report: dict[str, Any]) -> None:
    expected = {
        "status": "PASS_POSTCONSUMPTION_RECOVERY3_PREAUTHORIZATION_SURFACE_CLEAN_NOT_ALLOCATED",
        "candidateSeedCount": 72,
        "candidateSeedCanonicalSha256": EXPECTED_SEED_CANONICAL,
        "candidateRowsCanonicalSha256": EXPECTED_ROWS_CANONICAL,
        "consumedOrdinal41SeedCanonicalSha256": EXPECTED_ORDINAL41_SEED_CANONICAL,
        "consumedOrdinal42SeedCanonicalSha256": EXPECTED_ORDINAL42_SEED_CANONICAL,
        "consumedOrdinal43SeedCanonicalSha256": EXPECTED_ORDINAL43_SEED_CANONICAL,
        "nextOrdinalHardCoded": False,
    }
    for key, value in expected.items():
        if report.get(key) != value:
            raise SystemExit(f"V4 proof drift {key}: {report.get(key)!r} != {value!r}")
    if not str(report.get("stageId") or "").endswith("-preauthorization-v4"):
        raise SystemExit("V4 stage identity drift")
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
    ):
        if report.get(key) is not False:
            raise SystemExit(f"V4 proof crossed boundary: {key}")
    given = report.get("contentSha256")
    tmp = dict(report)
    tmp.pop("contentSha256", None)
    if given != canonical_sha256(tmp):
        raise SystemExit("V4 preauthorization content hash mismatch")


def build(args: argparse.Namespace) -> int:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN required")
    v4 = json.loads(args.v4_report.read_text())
    validate_v4(v4)
    module = _load_v3()
    _, payload = module.collect_payload(args.repository, token)
    fresh, observations = module.build_report(
        payload,
        json.loads(args.seed_global_report.read_text()),
        args.expected_head,
        args.current_run_id,
    )
    n = int(fresh["nextAvailableScientificOrdinal"])
    if fresh.get("nextOrdinalHardCoded") is not False:
        raise SystemExit("fresh successor ordinal was hard-coded")
    if n != int(fresh["occupiedMaxScientificOrdinal"]) + 1 or n <= 43:
        raise SystemExit("fresh dynamic successor rule failed")
    auth_branch = str(fresh["authorizationBranch"])
    dispatch_branch = str(fresh["dispatchBranch"])
    if auth_branch != f"authorization/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3-ordinal-{n}":
        raise SystemExit("authorization branch derivation drift")
    if dispatch_branch != f"dispatch/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3-ordinal-{n}":
        raise SystemExit("dispatch branch derivation drift")

    auth = {
        "schemaVersion": 4,
        "stageId": "aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3",
        "status": "AUTHORIZED_POSTCONSUMPTION_RECOVERY3_PENDING_SEPARATE_ALLOCATION_AND_DISPATCH",
        "scientificOrdinal": n,
        "nextOrdinalHardCoded": False,
        "consumedPredecessors": [
            {"scientificOrdinal": 41, "runId": 33236295233, "runAttempt": 1, "failureClass": "PRE_SOLVER_RUNTIME_SUPPORT_TRANSPORT_OMISSION_NO_SCIENTIFIC_RESULT", "reusable": False},
            {"scientificOrdinal": 42, "runId": 33259899524, "runAttempt": 1, "failureClass": "PRE_SOLVER_RELOCATED_SEED_LEDGER_PATH_CONTEXT_NO_SCIENTIFIC_RESULT", "reusable": False},
            {"scientificOrdinal": 43, "runId": 33298433506, "runAttempt": 1, "failureClass": "PRE_SOLVER_REPOSITORY_GLOBAL_SNAPSHOT_STABILITY_FAILURE_NO_SCIENTIFIC_RESULT", "reusable": False},
        ],
        "authorizationBranch": auth_branch,
        "dispatchBranch": dispatch_branch,
        "executionKey": f"aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3:numerical:{n}",
        "exactAuthorizationParentCommit": args.expected_head,
        "exactAuthorizationCommit": None,
        "reviewPackageMainSha": os.environ["AVPS_AUTH_CONTROL_BASE_MAIN"],
        "v4PreauthorizationPr": int(os.environ["V4_PR"]),
        "v4PreauthorizationHead": os.environ["V4_HEAD"],
        "v4PreauthorizationRunId": int(os.environ["V4_RUN"]),
        "v4PreauthorizationArtifactId": int(os.environ["V4_ARTIFACT"]),
        "v4PreauthorizationArtifactDigest": os.environ["V4_DIGEST"],
        "v4PreauthorizationTransitionComment": int(os.environ["V4_TRANSITION_COMMENT"]),
        "seedReviewPr": int(os.environ["SEED_PROOF_PR"]),
        "seedReviewHead": os.environ["SEED_PROOF_HEAD"],
        "seedReviewRunId": int(os.environ["SEED_PROOF_RUN"]),
        "seedReviewArtifactId": int(os.environ["SEED_PROOF_ARTIFACT"]),
        "seedReviewArtifactDigest": os.environ["SEED_PROOF_DIGEST"],
        "candidateSeedCount": 72,
        "candidateSeedCanonicalSha256": EXPECTED_SEED_CANONICAL,
        "candidateRowsCanonicalSha256": EXPECTED_ROWS_CANONICAL,
        "consumedOrdinal41SeedCanonicalSha256": EXPECTED_ORDINAL41_SEED_CANONICAL,
        "consumedOrdinal42SeedCanonicalSha256": EXPECTED_ORDINAL42_SEED_CANONICAL,
        "consumedOrdinal43SeedCanonicalSha256": EXPECTED_ORDINAL43_SEED_CANONICAL,
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
        "githubRerunAllowed": False,
        "retryAllowed": False,
        "resumeAllowed": False,
        "workflowRunAttemptRequired": 1,
    }
    auth["authorizationDocumentContentSha256"] = canonical_sha256(auth)
    receipt = {
        "schemaVersion": 1,
        "status": "PASS_RECOVERY3_AUTHORIZATION_CONTROL_PROPOSAL_NOT_ALLOCATED_NOT_DISPATCHED",
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
    }
    receipt["contentSha256"] = canonical_sha256(receipt)
    args.fresh_report.write_text(json.dumps(fresh, indent=2, sort_keys=True) + "\n")
    args.observations_output.write_text(json.dumps(observations, indent=2, sort_keys=True) + "\n")
    args.authorization_output.write_text(json.dumps(auth, indent=2, sort_keys=True) + "\n")
    args.receipt_output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return 0


def verify(args: argparse.Namespace) -> int:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN required")
    module = _load_v3()
    fresh = json.loads(args.fresh_report.read_text())
    auth = json.loads(args.authorization_output.read_text())
    receipt = json.loads(args.receipt_output.read_text())
    module.final_verify(args.repository, token, args.expected_head, args.current_run_id, fresh)
    n = int(fresh["nextAvailableScientificOrdinal"])
    if auth.get("scientificOrdinal") != n or receipt.get("scientificOrdinalProposed") != n:
        raise SystemExit("proposal ordinal drift from fresh global surface")
    if auth.get("nextOrdinalHardCoded") is not False or receipt.get("nextOrdinalHardCoded") is not False:
        raise SystemExit("proposal hard-coded successor ordinal")
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
    b.add_argument("--repository", required=True)
    b.add_argument("--seed-global-report", type=Path, required=True)
    b.add_argument("--v4-report", type=Path, required=True)
    b.add_argument("--expected-head", required=True)
    b.add_argument("--current-run-id", type=int, required=True)
    b.add_argument("--fresh-report", type=Path, required=True)
    b.add_argument("--observations-output", type=Path, required=True)
    b.add_argument("--authorization-output", type=Path, required=True)
    b.add_argument("--receipt-output", type=Path, required=True)
    v = sub.add_parser("verify")
    v.add_argument("--repository", required=True)
    v.add_argument("--expected-head", required=True)
    v.add_argument("--current-run-id", type=int, required=True)
    v.add_argument("--fresh-report", type=Path, required=True)
    v.add_argument("--authorization-output", type=Path, required=True)
    v.add_argument("--receipt-output", type=Path, required=True)
    args = parser.parse_args()
    return build(args) if args.command == "build" else verify(args)


if __name__ == "__main__":
    raise SystemExit(main())
