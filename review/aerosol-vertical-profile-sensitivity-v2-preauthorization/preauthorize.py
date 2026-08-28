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
BASE_MAIN = "99ade7798627e67921139697ba1a004fa8a304bb"
STAGE = "aerosol-vertical-profile-sensitivity-v2"
PREAUTH_BRANCH = "review/aerosol-vertical-profile-sensitivity-v2-preauthorization"
EXPECTED_LATEST_CONSUMED = 40
EXPECTED_NEXT = 41
EXPECTED_SEED_COUNT = 72
EXPECTED_SEED_CANONICAL = "02f624d582e9b2caba6b920d65a5e8a8bc8fc1a2693623bc2f73abf5d3f706d2"
EXPECTED_ROWS_CANONICAL = "41f70d6a0381db6b569d3f4e17d74bb38b05cf212c2f2e432455a502f73dc670"
EXPECTED_SEED_REVIEW_HEAD = "64e7d68bd876a99aa5af49d97bcb53718238b39b"
EXPECTED_SEED_REVIEW_RUN = 33194319669
EXPECTED_SEED_REVIEW_STATUS = "PASS_CANDIDATE_SEEDS_FRESH_REVIEW_ONLY_NOT_ALLOCATED"
EXPECTED_SEED_PROOF_ARTIFACT_COUNT = 1

GENERIC_SCANNER = ROOT / "experiments" / "aerosol-family-challenge-v2" / "repository_global_seed_scan.py"
GENERIC_SCANNER_BLOB = "4c6d704fa24228284780bcb1dd7c52537b4c5b0d"
R8_DIR = ROOT / "experiments" / "aerosol-family-challenge-v2-r8" / "execution-candidate"
R8_FRESHNESS_BLOB = "732f803b5261e7986582dd7e0d69a66f70432b1e"
R8_ORDINAL_BLOB = "7ca8efd17ae9e7ec2baa32fe935e5173ca6d173f"
SHA40 = re.compile(r"^[0-9a-f]{40}$")


class Refusal(RuntimeError):
    pass


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise Refusal(f"cannot import bound module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def bound_scanner():
    if git_blob_sha1(GENERIC_SCANNER) != GENERIC_SCANNER_BLOB:
        raise Refusal("bound repository-global scanner byte drift")
    return load_module("avps_v2_preauth_bound_global_scanner", GENERIC_SCANNER)


def bound_ordinal_module():
    freshness_path = R8_DIR / "freshness.py"
    ordinal_path = R8_DIR / "preauthorization_ordinal.py"
    if git_blob_sha1(freshness_path) != R8_FRESHNESS_BLOB:
        raise Refusal("bound R8 freshness byte drift")
    if git_blob_sha1(ordinal_path) != R8_ORDINAL_BLOB:
        raise Refusal("bound R8 global-ordinal parser byte drift")
    freshness = load_module("avps_v2_preauth_bound_r8_freshness", freshness_path)
    previous = sys.modules.get("freshness")
    sys.modules["freshness"] = freshness
    try:
        ordinal = load_module("avps_v2_preauth_bound_r8_ordinal", ordinal_path)
    finally:
        if previous is None:
            sys.modules.pop("freshness", None)
        else:
            sys.modules["freshness"] = previous
    return ordinal


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    ).hexdigest()


def _seed_review_checkpoint_count(payload: dict[str, Any]) -> int:
    count = 0
    for row in payload.get("issue60Comments", []):
        body = str(row.get("body") or "")
        if not body.startswith("AEROSOL-VERTICAL-PROFILE-V2-CANDIDATE-SEED-FRESHNESS-REVIEW\n"):
            continue
        required = (
            f"audited_head={EXPECTED_SEED_REVIEW_HEAD}",
            f"run={EXPECTED_SEED_REVIEW_RUN}",
            f"status={EXPECTED_SEED_REVIEW_STATUS}",
            f"candidate_seed_count={EXPECTED_SEED_COUNT}",
            f"candidate_seed_canonical_sha256={EXPECTED_SEED_CANONICAL}",
            f"candidate_rows_canonical_sha256={EXPECTED_ROWS_CANONICAL}",
            "scientific_ordinal_allocated=false",
            "candidate_seeds_applied=false",
            "authorization_time_recheck_required=true",
        )
        if all(item in body for item in required):
            count += 1
    return count


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
        "priorReviewProofArtifactCount": EXPECTED_SEED_PROOF_ARTIFACT_COUNT,
        "repositoryGlobalPostFenceCandidateSeedCollisionCount": 0,
    }
    for key, value in expected.items():
        if report.get(key) != value:
            raise Refusal(f"authorization-time seed recheck drift: {key}: {report.get(key)!r} != {value!r}")
    stable = report.get("repositoryGlobalStableContextSha256")
    fence = report.get("repositoryGlobalSnapshotFenceSha256")
    if not isinstance(stable, str) or re.fullmatch(r"[0-9a-f]{64}", stable) is None:
        raise Refusal("authorization-time global seed stable-context SHA missing/malformed")
    if not isinstance(fence, str) or re.fullmatch(r"[0-9a-f]{64}", fence) is None:
        raise Refusal("authorization-time global seed snapshot-fence SHA missing/malformed")
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
    consumed = [int(row["ordinal"]) for row in observations if row.get("reason") == "exact-consumed-marker"]
    if not consumed:
        raise Refusal("no exact global consumed marker observed")
    latest_consumed = max(consumed)
    observed_max = max(int(row["ordinal"]) for row in observations)
    if latest_consumed != EXPECTED_LATEST_CONSUMED:
        raise Refusal(f"latest consumed scientific ordinal moved: {latest_consumed}")
    if observed_max != EXPECTED_LATEST_CONSUMED:
        raise Refusal(f"authoritative global ordinal surface is no longer clean after consumed {latest_consumed}: max={observed_max}")

    next_ordinal = latest_consumed + 1
    if next_ordinal != EXPECTED_NEXT:
        raise Refusal(f"unexpected next ordinal: {next_ordinal}")
    auth_branch = f"authorization/{STAGE}-ordinal-{next_ordinal}"
    dispatch_branch = f"dispatch/{STAGE}-ordinal-{next_ordinal}"
    branch_names = [str(row.get("name") or "") for row in payload.get("branches", [])]
    if auth_branch in branch_names or dispatch_branch in branch_names:
        raise Refusal("proposed v2 authorization/dispatch branch already exists")
    if any(str(row.get("body") or "").strip().upper().startswith(f"ORDINAL{next_ordinal}_") for row in payload.get("issue60Comments", [])):
        raise Refusal("Issue #60 already contains an exact-looking marker for the proposed ordinal")
    checkpoint_count = _seed_review_checkpoint_count(payload)
    if checkpoint_count != 1:
        raise Refusal(f"expected exactly one #598 seed-freshness Issue #60 checkpoint, got {checkpoint_count}")
    return {
        "latestConsumedScientificOrdinal": latest_consumed,
        "globalOrdinalMaxObserved": observed_max,
        "nextAvailableScientificOrdinal": next_ordinal,
        "authorizationBranch": auth_branch,
        "dispatchBranch": dispatch_branch,
        "seedReviewCheckpointCount": checkpoint_count,
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
    ordinal = ordinal_surface(payload, current_run_id)
    observations = ordinal.pop("observations")
    report = {
        "schemaVersion": 1,
        "stageId": f"{STAGE}-preauthorization",
        "status": "PASS_V2_PREAUTHORIZATION_SURFACE_CLEAN_NOT_ALLOCATED",
        "auditedHead": expected_head,
        "baseMain": BASE_MAIN,
        **ordinal,
        "candidateSeedCount": EXPECTED_SEED_COUNT,
        "candidateSeedCanonicalSha256": EXPECTED_SEED_CANONICAL,
        "candidateRowsCanonicalSha256": EXPECTED_ROWS_CANONICAL,
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
        "productionAuthorized": False,
        "githubRerunAllowed": False,
        "separateAuthorizationReviewRequired": True,
    }
    report["contentSha256"] = canonical_sha256(report)
    return report, observations


def collect_payload(repository: str, token: str) -> tuple[Any, dict[str, Any]]:
    scanner = bound_scanner()
    return scanner, scanner.collect(repository, 60, token)


def final_verify(repository: str, token: str, expected_head: str, current_run_id: int | None, report: dict[str, Any]) -> None:
    scanner, payload = collect_payload(repository, token)
    current = ordinal_surface(payload, current_run_id)
    observations = current.pop("observations")
    if current["ordinalObservationsCanonicalSha256"] != report.get("ordinalObservationsCanonicalSha256"):
        raise Refusal("global ordinal observation surface changed after preauthorization build")
    for key in ("latestConsumedScientificOrdinal", "globalOrdinalMaxObserved", "nextAvailableScientificOrdinal", "authorizationBranch", "dispatchBranch"):
        if current.get(key) != report.get(key):
            raise Refusal(f"global ordinal final recheck drift: {key}")
    if scanner.final_expected_branch_head(repository, PREAUTH_BRANCH, token) != expected_head:
        raise Refusal("preauthorization branch moved before final verification")
    if canonical_sha256(observations) != report.get("ordinalObservationsCanonicalSha256"):
        raise Refusal("final ordinal observation hash mismatch")


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build")
    b.add_argument("--repository", required=True)
    b.add_argument("--seed-global-report", type=Path, required=True)
    b.add_argument("--expected-head", required=True)
    b.add_argument("--current-run-id", type=int, required=True)
    b.add_argument("--output", type=Path, required=True)
    b.add_argument("--observations-output", type=Path, required=True)
    v = sub.add_parser("verify")
    v.add_argument("--repository", required=True)
    v.add_argument("--expected-head", required=True)
    v.add_argument("--current-run-id", type=int, required=True)
    v.add_argument("--report", type=Path, required=True)
    args = ap.parse_args()
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
    if report.get("status") != "PASS_V2_PREAUTHORIZATION_SURFACE_CLEAN_NOT_ALLOCATED":
        raise Refusal("preauthorization report is not PASS")
    final_verify(args.repository, token, args.expected_head, args.current_run_id, report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
