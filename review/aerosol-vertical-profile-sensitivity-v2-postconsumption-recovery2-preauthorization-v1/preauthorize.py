from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
STAGE = "aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery2"
PREAUTH_BRANCH = "review/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery2-preauthorization-v1"
BASE_MAIN = "09f3fbdefea6dd5ce68fdc0010347e5bfb28ff75"
CONSUMED_ORDINALS = (41, 42)
LATEST_CONSUMED_ORDINAL = 42
EXPECTED_SEED_COUNT = 72
EXPECTED_SEED_CANONICAL = "38c074fe01bd6d09fa7dc78af1ad323e2f42b606ca992c2950b8fc1f5b343a9f"
EXPECTED_ROWS_CANONICAL = "a88b28dcfaaeb354f294d1705a0f8ddbcd061083f277a038ab8c9dace44d9954"
EXPECTED_ORDINAL41_SEED_CANONICAL = "02f624d582e9b2caba6b920d65a5e8a8bc8fc1a2693623bc2f73abf5d3f706d2"
EXPECTED_ORDINAL42_SEED_CANONICAL = "a514212990a94a39d577bd038b631a600e18e4c0f750f781bbd7c99b897228a7"

GENERIC_SCANNER = ROOT / "experiments/aerosol-family-challenge-v2/repository_global_seed_scan.py"
GENERIC_SCANNER_BLOB = "4c6d704fa24228284780bcb1dd7c52537b4c5b0d"
R8_DIR = ROOT / "experiments/aerosol-family-challenge-v2-r8/execution-candidate"
R8_FRESHNESS_BLOB = "732f803b5261e7986582dd7e0d69a66f70432b1e"
R8_ORDINAL_BLOB = "7ca8efd17ae9e7ec2baa32fe935e5173ca6d173f"
RECOVERY_LEDGER = ROOT / "review/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery2-seed-freshness-v1/seed_ledger.py"
RECOVERY_LEDGER_BLOB = "d4bdc95e9ed576fa6c70711c81d8097ddab33dbf"
SHA40 = re.compile(r"^[0-9a-f]{40}$")


class Refusal(RuntimeError):
    pass


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    ).hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise Refusal(f"cannot import bound module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def bound_scanner():
    if git_blob_sha1(GENERIC_SCANNER) != GENERIC_SCANNER_BLOB:
        raise Refusal("bound repository-global scanner byte drift")
    return load_module("avps_v2_recovery2_preauth_global_scanner", GENERIC_SCANNER)


def bound_ordinal_module():
    freshness_path = R8_DIR / "freshness.py"
    ordinal_path = R8_DIR / "preauthorization_ordinal.py"
    if git_blob_sha1(freshness_path) != R8_FRESHNESS_BLOB:
        raise Refusal("bound R8 freshness byte drift")
    if git_blob_sha1(ordinal_path) != R8_ORDINAL_BLOB:
        raise Refusal("bound R8 global-ordinal parser byte drift")
    freshness = load_module("avps_v2_recovery2_bound_r8_freshness", freshness_path)
    previous = sys.modules.get("freshness")
    sys.modules["freshness"] = freshness
    try:
        ordinal = load_module("avps_v2_recovery2_bound_r8_ordinal", ordinal_path)
    finally:
        if previous is None:
            sys.modules.pop("freshness", None)
        else:
            sys.modules["freshness"] = previous
    return ordinal


def recovery_ledger() -> dict[str, Any]:
    if git_blob_sha1(RECOVERY_LEDGER) != RECOVERY_LEDGER_BLOB:
        raise Refusal("recovery2 candidate-ledger byte drift")
    ledger = load_module("avps_v2_recovery2_preauth_seed_ledger", RECOVERY_LEDGER).validate_ledger()
    expected = {
        "candidateSeedCount": EXPECTED_SEED_COUNT,
        "candidateSeedCanonicalSha256": EXPECTED_SEED_CANONICAL,
        "candidateRowsCanonicalSha256": EXPECTED_ROWS_CANONICAL,
        "consumedOrdinal41SeedCanonicalSha256": EXPECTED_ORDINAL41_SEED_CANONICAL,
        "consumedOrdinal42SeedCanonicalSha256": EXPECTED_ORDINAL42_SEED_CANONICAL,
        "overlapWithConsumedOrdinal41SeedCount": 0,
        "overlapWithConsumedOrdinal42SeedCount": 0,
        "historicalOrdinal42LedgerValidatedAtNativePath": True,
    }
    for key, value in expected.items():
        if ledger.get(key) != value:
            raise Refusal(f"recovery2 candidate ledger drift: {key}")
    if len(set(int(x) for x in ledger.get("candidateSeeds", []))) != EXPECTED_SEED_COUNT:
        raise Refusal("recovery2 candidate seed uniqueness/cardinality drift")
    for key in (
        "candidateSeedsAppliedToCases",
        "scientificOrdinalAllocated",
        "authorizationCreated",
        "dispatchCreated",
        "solverExecutionAuthorized",
        "resultOpeningAuthorized",
        "productionAuthorized",
    ):
        if ledger.get(key) is not False:
            raise Refusal(f"recovery2 candidate ledger crossed boundary: {key}")
    return ledger


def validate_seed_recheck(report: dict[str, Any], expected_head: str) -> dict[str, Any]:
    if SHA40.fullmatch(expected_head) is None:
        raise Refusal("expected head must be a 40-character lowercase SHA")
    expected = {
        "auditMode": "authorization-recheck",
        "candidateSeedCount": EXPECTED_SEED_COUNT,
        "repositoryGlobalCollisionCount": 0,
        "repositoryGlobalCollisionSurfaceScanPassed": True,
        "repositoryGlobalDoubleEnumerationStable": True,
        "auditedBranchName": PREAUTH_BRANCH,
        "repositoryHeadExpected": expected_head,
        "auditedBranchHeadShaObserved": expected_head,
        "auditedBranchHeadMatchesRepositoryHead": True,
        "priorReviewProofArtifactCount": 1,
        "repositoryGlobalPostFenceCandidateSeedCollisionCount": 0,
    }
    for key, value in expected.items():
        if report.get(key) != value:
            raise Refusal(f"authorization-time seed recheck drift: {key}: {report.get(key)!r} != {value!r}")
    stable = report.get("repositoryGlobalStableContextSha256")
    fence = report.get("repositoryGlobalSnapshotFenceSha256")
    if not isinstance(stable, str) or re.fullmatch(r"[0-9a-f]{64}", stable) is None:
        raise Refusal("authorization-time stable-context SHA missing/malformed")
    if not isinstance(fence, str) or re.fullmatch(r"[0-9a-f]{64}", fence) is None:
        raise Refusal("authorization-time snapshot-fence SHA missing/malformed")
    return {
        "auditMode": report["auditMode"],
        "candidateSeedCount": report["candidateSeedCount"],
        "repositoryGlobalCollisionCount": report["repositoryGlobalCollisionCount"],
        "repositoryGlobalDoubleEnumerationStable": report["repositoryGlobalDoubleEnumerationStable"],
        "repositoryGlobalStableContextSha256": stable,
        "repositoryGlobalSnapshotFenceSha256": fence,
        "repositoryGlobalPostFenceArrivalCounts": report.get("repositoryGlobalPostFenceArrivalCounts") or {},
        "priorReviewProofArtifactCount": report["priorReviewProofArtifactCount"],
    }


def ordinal_surface(payload: dict[str, Any], current_run_id: int | None) -> dict[str, Any]:
    ordinal = bound_ordinal_module()
    observations = ordinal.authoritative_global_ordinal_observations(payload, current_run_id=current_run_id)
    if not observations:
        raise Refusal("no authoritative global scientific ordinal observations")
    consumed = sorted({
        int(row["ordinal"])
        for row in observations
        if row.get("reason") == "exact-consumed-marker"
    })
    for required in CONSUMED_ORDINALS:
        if required not in consumed:
            raise Refusal(f"consumed ordinal {required} is no longer observed as exactly consumed")
    occupied = sorted({int(row["ordinal"]) for row in observations})
    occupied_max = max(occupied)
    if occupied_max < LATEST_CONSUMED_ORDINAL:
        raise Refusal("global ordinal surface regressed below consumed ordinal 42")
    next_ordinal = occupied_max + 1
    if next_ordinal <= LATEST_CONSUMED_ORDINAL:
        raise Refusal("derived successor ordinal is not newer than consumed ordinal 42")

    auth_branch = f"authorization/{STAGE}-ordinal-{next_ordinal}"
    dispatch_branch = f"dispatch/{STAGE}-ordinal-{next_ordinal}"
    branch_names = [str(row.get("name") or "") for row in payload.get("branches", [])]
    if auth_branch in branch_names or dispatch_branch in branch_names:
        raise Refusal("proposed recovery2 authorization/dispatch branch already exists")
    marker_prefix = f"ORDINAL{next_ordinal}_"
    if any(
        str(row.get("body") or "").strip().upper().startswith(marker_prefix)
        for row in payload.get("issue60Comments", [])
    ):
        raise Refusal("Issue #60 already contains an exact-looking marker for proposed successor ordinal")

    return {
        "consumedScientificOrdinalsRequired": list(CONSUMED_ORDINALS),
        "latestConsumedScientificOrdinal": LATEST_CONSUMED_ORDINAL,
        "consumedOrdinalsObserved": consumed,
        "occupiedScientificOrdinalsObserved": occupied,
        "occupiedMaxScientificOrdinal": occupied_max,
        "nextAvailableScientificOrdinal": next_ordinal,
        "authorizationBranch": auth_branch,
        "dispatchBranch": dispatch_branch,
        "observationCount": len(observations),
        "ordinalObservationsCanonicalSha256": canonical_sha256(observations),
        "observations": observations,
    }


def build_report(
    payload: dict[str, Any],
    seed_global_report: dict[str, Any],
    expected_head: str,
    current_run_id: int | None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    seed = validate_seed_recheck(seed_global_report, expected_head)
    ledger = recovery_ledger()
    ordinal = ordinal_surface(payload, current_run_id)
    observations = ordinal.pop("observations")
    report = {
        "schemaVersion": 1,
        "stageId": f"{STAGE}-preauthorization",
        "status": "PASS_POSTCONSUMPTION_RECOVERY2_PREAUTHORIZATION_SURFACE_CLEAN_NOT_ALLOCATED",
        "auditedHead": expected_head,
        "baseMain": BASE_MAIN,
        **ordinal,
        "candidateSeedCount": EXPECTED_SEED_COUNT,
        "candidateSeedCanonicalSha256": EXPECTED_SEED_CANONICAL,
        "candidateRowsCanonicalSha256": EXPECTED_ROWS_CANONICAL,
        "consumedOrdinal41SeedCanonicalSha256": EXPECTED_ORDINAL41_SEED_CANONICAL,
        "consumedOrdinal42SeedCanonicalSha256": EXPECTED_ORDINAL42_SEED_CANONICAL,
        "overlapWithConsumedOrdinal41SeedCount": int(ledger["overlapWithConsumedOrdinal41SeedCount"]),
        "overlapWithConsumedOrdinal42SeedCount": int(ledger["overlapWithConsumedOrdinal42SeedCount"]),
        "authorizationTimeSeedRecheck": seed,
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
        "githubRerunAllowed": False,
        "separateAuthorizationReviewRequired": True,
        "nextOrdinalHardCoded": False,
    }
    report["contentSha256"] = canonical_sha256(report)
    return report, observations


def collect_payload(repository: str, token: str) -> tuple[Any, dict[str, Any]]:
    scanner = bound_scanner()
    return scanner, scanner.collect(repository, 60, token)


def final_verify(
    repository: str,
    token: str,
    expected_head: str,
    current_run_id: int | None,
    report: dict[str, Any],
) -> None:
    scanner, payload = collect_payload(repository, token)
    current = ordinal_surface(payload, current_run_id)
    observations = current.pop("observations")
    if current["ordinalObservationsCanonicalSha256"] != report.get("ordinalObservationsCanonicalSha256"):
        raise Refusal("global ordinal observation surface changed after preauthorization build")
    for key in (
        "latestConsumedScientificOrdinal",
        "occupiedMaxScientificOrdinal",
        "nextAvailableScientificOrdinal",
        "authorizationBranch",
        "dispatchBranch",
    ):
        if current.get(key) != report.get(key):
            raise Refusal(f"global ordinal final recheck drift: {key}")
    if scanner.final_expected_branch_head(repository, PREAUTH_BRANCH, token) != expected_head:
        raise Refusal("preauthorization branch moved before final verification")
    if canonical_sha256(observations) != report.get("ordinalObservationsCanonicalSha256"):
        raise Refusal("final ordinal observation hash mismatch")


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--repository", required=True)
    build.add_argument("--seed-global-report", type=Path, required=True)
    build.add_argument("--expected-head", required=True)
    build.add_argument("--current-run-id", type=int, required=True)
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--observations-output", type=Path, required=True)
    verify = sub.add_parser("verify")
    verify.add_argument("--repository", required=True)
    verify.add_argument("--expected-head", required=True)
    verify.add_argument("--current-run-id", type=int, required=True)
    verify.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN required")
    if args.command == "build":
        _, payload = collect_payload(args.repository, token)
        report, observations = build_report(
            payload,
            json.loads(args.seed_global_report.read_text()),
            args.expected_head,
            args.current_run_id,
        )
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        args.observations_output.write_text(json.dumps(observations, indent=2, sort_keys=True) + "\n")
        return 0

    report = json.loads(args.report.read_text())
    if report.get("status") != "PASS_POSTCONSUMPTION_RECOVERY2_PREAUTHORIZATION_SURFACE_CLEAN_NOT_ALLOCATED":
        raise Refusal("preauthorization report is not PASS")
    final_verify(args.repository, token, args.expected_head, args.current_run_id, report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
