from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import urllib.parse
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CONTROL_DIR = Path(__file__).resolve().parent
SEED_LEDGER_PATH = CONTROL_DIR / "seed_ledger.py"
SCANNER_WRAPPER_PATH = CONTROL_DIR / "repository_global_seed_scan.py"
PREAUTH_SURFACE_PATH = ROOT / "experiments/aerosol-vertical-profile-sensitivity-v1/preauthorization_surface.py"
TRACKED_SCAN_PATH = ROOT / "review/aerosol-vertical-profile-sensitivity-v2-seed-freshness/tracked_tree_seed_scan.py"

EXPECTED_BRANCH = "review/avps-v2-postconsumption-successor-preauth-v1-20260909"
EXPECTED_BASE = "8cd85cf393e2d86a1b6d7325654747460a13e697"
EXPECTED_NEW_SEED_CANONICAL = "6ace6be3b0298f3fa35cdc522a3375c0480a4154371c15bbbf4a3f930a5d17cd"
EXPECTED_NEW_ROWS_CANONICAL = "30c0c1e38755f2c04b59448569c15c38a8b3b850c73d235ea38ce8f880d30f8b"
OLD_SEED_CANONICAL = "ddded6b2d170ca2fac8d498bdba2887446c16995df0880d948fb2be00870b3de"
OLD_AUTH_BRANCH = "authorization/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery4-ordinal-45"
OLD_DISPATCH_BRANCH = "dispatch/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery4-ordinal-45"
OLD_AUTH_HEAD = "6e095b4b1603c90dcee0943295909b30cd1b374d"
OLD_AUTH_PATH = "review/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery4-authorization-control-v1/authorization.json"
OLD_AUTH_BLOB = "96ee8299d00bd72cdb73de4583670730ce89c73b"
OLD_EXECUTION_KEY = "aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery4:numerical:45"
OLD_CONSUMED_MARKER = "ORDINAL45_AVPS_V2_POSTCONSUMPTION_RECOVERY4_DISPATCH_CONSUMED"
OLD_PUBLISHER_RUN = 34247116198
OLD_SCIENCE_RUN = 34248529569

INSTALLED_SCIENCE_PATH = ".github/workflows/avps-v2-postconsumption-recovery4-science.yml"
INSTALLED_SCIENCE_BLOB = "5c6bb98c8f6c653067aea6db4fce8c85682f044e"
INSTALLED_PUBLISHER_PATH = ".github/workflows/avps-v2-recovery4-ordinal45-final-dispatch-publisher-v3.yml"
INSTALLED_PUBLISHER_BLOB = "80eefe6339025a3e714d4b7a7c7135a3368dd4ae"
RUNTIME_BLOBS = {
    "runtime-avps-v2-recovery4-ordinal45-v1/runtime_adapter.py": "e4b690c2969fd01ecde5b08f554e47ad50b40914",
    "runtime-avps-v2-recovery4-ordinal45-v1/executor.py": "7dc38e31c19701b1a1ceef300d75105cff179290",
    "runtime-avps-v2-recovery4-ordinal45-v1/aggregator.py": "6afc8b0d21c2b5553c251dc9ca5524c795ed2646",
}
FROZEN_DESIGN = {
    "caseCount": 360,
    "commonRandomNumberGroupCount": 72,
    "statesPerGroup": 5,
    "photonHistoriesPerCase": 20_000_000,
    "lockedLibRadtranPackage": "rubin-libradtran=2.0.6=py312pl5321he9373c2_1",
    "uvspecSha256": "2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3",
    "officialOptpropArchiveSha256": "11daa1f1f4be0fd4ddf7e881ec2005498049674a1540d37b4b1e8f5e16052c7e",
    "fourAliasDataTreeSha256": "5e1814dd36cf861fd85477a97607299248f8272268df7bf428d31bbb6aa4354a",
}
ALLOWED_PATHS = sorted(
    [
        ".github/workflows/avps-v2-postconsumption-successor-preauthorization-v1.yml",
        "review/aerosol-vertical-profile-sensitivity-v2-postconsumption-successor-preauth-v1/preauthorize.py",
        "review/aerosol-vertical-profile-sensitivity-v2-postconsumption-successor-preauth-v1/repository_global_seed_scan.py",
        "review/aerosol-vertical-profile-sensitivity-v2-postconsumption-successor-preauth-v1/seed_ledger.py",
    ]
)


class Refusal(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Refusal(message)


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    cp = subprocess.run(args, cwd=ROOT, text=True, capture_output=True)
    if check and cp.returncode != 0:
        raise Refusal(f"command failed rc={cp.returncode}: {' '.join(args)}\nstdout={cp.stdout}\nstderr={cp.stderr}")
    return cp


def out(*args: str) -> str:
    return run(*args).stdout.strip()


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise Refusal(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def issue60_tail(scanner, repository: str, token: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    from scripts.avps_write_quiet_parser_v1 import is_write_quiet_begin, record_write_quiet_end

    rows = scanner.pages(f"https://api.github.com/repos/{repository}/issues/60/comments", token)
    begin_ids: set[int] = set()
    closed: set[int] = set()
    begins: list[int] = []
    for row in rows:
        body = str(row.get("body") or "")
        if record_write_quiet_end(body, row["id"], begin_ids, closed):
            continue
        if is_write_quiet_begin(body):
            cid = int(row["id"])
            begin_ids.add(cid)
            begins.append(cid)
    unmatched = [cid for cid in begins if cid not in closed]
    require(not unmatched, f"live WRITE_QUIET blocks successor preauthorization: {unmatched}")
    state = {
        "schemaVersion": 1,
        "commentCount": len(rows),
        "tailCommentId": max((int(row["id"]) for row in rows), default=0),
        "unmatchedWriteQuietBeginIds": [],
        "canonicalParserUsed": True,
    }
    return rows, state


def verify_static_identity(scanner, args, token: str) -> dict[str, Any]:
    require(args.branch == EXPECTED_BRANCH, "proposal branch name drift")
    require(args.expected_main == EXPECTED_BASE, "proposal expected-main drift")
    require(args.run_attempt == 1, "preauthorization must be attempt1")
    require(args.event_name == "pull_request", "preauthorization must use pull_request event")
    require(out("git", "rev-parse", "HEAD") == args.head, "checked-out proposal head drift")
    require(scanner.final_expected_branch_head(args.repository, "main", token) == EXPECTED_BASE, "main moved before preauthorization")
    require(scanner.final_expected_branch_head(args.repository, EXPECTED_BRANCH, token) == args.head, "proposal branch head drift")
    require(run("git", "merge-base", "--is-ancestor", EXPECTED_BASE, args.head, check=False).returncode == 0, "proposal head does not descend from exact main")
    require(not out("git", "rev-list", "--merges", f"{EXPECTED_BASE}..{args.head}"), "proposal lineage contains merge commit")
    changed = sorted(line for line in out("git", "diff", "--name-only", f"{EXPECTED_BASE}...{args.head}").splitlines() if line)
    require(changed == ALLOWED_PATHS, f"proposal changed-path drift: {changed}")
    for path, blob in {
        INSTALLED_SCIENCE_PATH: INSTALLED_SCIENCE_BLOB,
        INSTALLED_PUBLISHER_PATH: INSTALLED_PUBLISHER_BLOB,
        **RUNTIME_BLOBS,
    }.items():
        require(out("git", "rev-parse", f"HEAD:{path}") == blob, f"frozen installed blob drift: {path}")
    require(shutil.which("uvspec") is None, "uvspec unexpectedly available in zero-runtime preauthorization")

    quoted = urllib.parse.quote(str(args.pr), safe="")
    pr = scanner.req_json(f"https://api.github.com/repos/{args.repository}/pulls/{quoted}", token)
    require(pr.get("state") == "open" and pr.get("draft") is True and pr.get("merged_at") is None, "proposal PR state drift")
    require(str((pr.get("head") or {}).get("sha") or "") == args.head, "proposal PR head SHA drift")
    require(str((pr.get("head") or {}).get("ref") or "") == EXPECTED_BRANCH, "proposal PR head ref drift")
    require(str((pr.get("base") or {}).get("sha") or "") == EXPECTED_BASE, "proposal PR base SHA drift")
    require(str((pr.get("base") or {}).get("ref") or "") == "main", "proposal PR base ref drift")
    self_run = scanner.req_json(f"https://api.github.com/repos/{args.repository}/actions/runs/{args.run_id}", token)
    require(int(self_run.get("id") or 0) == args.run_id, "self run id drift")
    require(int(self_run.get("run_attempt") or 0) == 1, "self run attempt drift")
    require(self_run.get("event") == "pull_request", "self run event drift")
    require(self_run.get("head_sha") == args.head and self_run.get("head_branch") == EXPECTED_BRANCH, "self run head identity drift")
    require(self_run.get("path") == ".github/workflows/avps-v2-postconsumption-successor-preauthorization-v1.yml", "self workflow registration drift")
    return {"pr": pr, "selfRun": self_run, "changedPaths": changed}


def derive_seed_ledger(evidence: Path) -> tuple[dict[str, Any], set[int]]:
    ledger_mod = load("avps_v2_successor_seed_ledger", SEED_LEDGER_PATH)
    ledger = ledger_mod.validate_ledger()
    seeds = {int(value) for value in ledger.get("candidateSeeds", [])}
    require(ledger.get("candidateSeedCount") == 72 and len(seeds) == 72, "successor seed cardinality drift")
    require(ledger.get("candidateSeedCanonicalSha256") == EXPECTED_NEW_SEED_CANONICAL, "successor seed canonical drift")
    require(ledger.get("candidateRowsCanonicalSha256") == EXPECTED_NEW_ROWS_CANONICAL, "successor rows canonical drift")
    require(ledger.get("consumedOrdinal45SeedCanonicalSha256") == OLD_SEED_CANONICAL, "consumed ordinal45 seed canonical drift")
    for ordinal in (41, 42, 43, 44, 45):
        require(ledger.get(f"overlapWithConsumedOrdinal{ordinal}SeedCount") == 0, f"successor seed overlap with consumed ordinal {ordinal}")
    false_keys = (
        "candidateSeedFreshnessProven",
        "candidateSeedsAppliedToCases",
        "seedUniverseConsumed",
        "scientificOrdinalAllocated",
        "authorizationCreated",
        "dispatchCreated",
        "publisherInvoked",
        "scienceInvoked",
        "writeQuietEntered",
        "scientificRuntimeSetupPerformed",
        "scientificExecutionPerformed",
        "solverExecutionAuthorized",
        "resultOpeningAuthorized",
        "levelBOpeningAuthorized",
        "protectedHoldoutOpeningAuthorized",
        "productionAuthorized",
        "taylorOrJerusalemFitAuthorized",
        "newMappingAuthorized",
    )
    require(all(ledger.get(key) is False for key in false_keys), "successor ledger authority boundary drift")
    write_json(evidence / "candidate-seed-ledger.json", ledger)
    return ledger, seeds


def tracked_tree_scan(evidence: Path) -> dict[str, Any]:
    file_list = evidence / "tracked-files.nul"
    file_list.write_bytes(subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT))
    policy = evidence / "empty-self-ledger-policy.json"
    write_json(policy, {"schemaVersion": 2, "requiredTrackedSelfLedgerPaths": [], "futureEvidenceSelfLedgerPaths": []})
    output = evidence / "tracked-seed-scan.json"
    run(
        sys.executable,
        str(TRACKED_SCAN_PATH),
        "--repo-root",
        ".",
        "--file-list",
        str(file_list),
        "--candidate-seed-ledger",
        str(evidence / "candidate-seed-ledger.json"),
        "--allow-self-ledger-json",
        str(policy),
        "--output",
        str(output),
    )
    scan = json.loads(output.read_text())
    require(scan.get("candidateSeedCount") == 72, "tracked-tree candidate cardinality drift")
    require(scan.get("trackedTreeExternalCollisionCount") == 0, "tracked-tree successor seed collision")
    require(scan.get("selfLedgerHitCount") == 0, "tracked-tree self-ledger hit drift")
    require(scan.get("exactHeadTrackedTreeByteScanPassed") is True, "exact-head tracked-tree scan did not pass")
    return scan


def global_seed_scan(scanner, args, token: str, seeds: set[int], evidence: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    context, stable_sha, fence, post_counts = scanner.collect_stable(
        args.repository,
        60,
        token,
        args.run_id,
        seeds,
        "review-freeze",
    )
    report = scanner.evaluate_context(
        context,
        seeds,
        args.run_id,
        stable_double_enumeration_passed=True,
        stable_context_sha256_value=stable_sha,
        audit_mode="review-freeze",
        expected_branch_name=EXPECTED_BRANCH,
        expected_repo_head=args.head,
        snapshot_fence=fence,
        post_fence_arrival_counts=post_counts,
    )
    require(scanner.final_expected_branch_head(args.repository, EXPECTED_BRANCH, token) == args.head, "proposal branch moved during global scan")
    require(scanner.final_expected_branch_head(args.repository, "main", token) == EXPECTED_BASE, "main moved during global scan")
    require(not scanner.final_review_proof_artifacts(args.repository, token, args.run_id), "successor proof artifact identity already exists outside current run")
    required = {
        "candidateSeedCount": 72,
        "repositoryGlobalCollisionCount": 0,
        "repositoryGlobalCollisionSurfaceScanPassed": True,
        "repositoryGlobalDoubleEnumerationStable": True,
        "repositoryGlobalEnumerationPassCount": 2,
        "auditedBranchHeadMatchesRepositoryHead": True,
        "priorReviewProofArtifactCount": 0,
        "reviewProofIdentityFresh": True,
        "allStatePullRequestsInspected": True,
        "allStateIssuesInspected": True,
        "allRepositoryIssueCommentsInspected": True,
        "allRepositoryPullReviewCommentsInspected": True,
        "allRepositoryCommitCommentsInspected": True,
        "repositoryGlobalPostFenceCandidateSeedCollisionCount": 0,
    }
    for key, value in required.items():
        require(report.get(key) == value, f"repository-global proof drift {key}={report.get(key)!r}")
    require(bool(report.get("repositoryGlobalStableContextSha256")), "stable global context hash missing")
    require(bool(report.get("repositoryGlobalSnapshotFenceSha256")), "global snapshot fence hash missing")
    write_json(evidence / "repository-global-seed-scan.json", report)
    return context, report


def fetch_consumed_ordinal45(scanner, repository: str, token: str, context: dict[str, Any], evidence: Path) -> dict[str, Any]:
    for branch in (OLD_AUTH_BRANCH, OLD_DISPATCH_BRANCH):
        require(scanner.final_expected_branch_head(repository, branch, token) == OLD_AUTH_HEAD, f"consumed ordinal45 ref drift: {branch}")
    run("git", "fetch", "--no-tags", "origin", f"refs/heads/{OLD_AUTH_BRANCH}:refs/remotes/origin/{OLD_AUTH_BRANCH}", f"refs/heads/{OLD_DISPATCH_BRANCH}:refs/remotes/origin/{OLD_DISPATCH_BRANCH}")
    require(out("git", "rev-parse", f"origin/{OLD_AUTH_BRANCH}") == OLD_AUTH_HEAD, "ordinal45 auth ref fetch drift")
    require(out("git", "rev-parse", f"origin/{OLD_DISPATCH_BRANCH}") == OLD_AUTH_HEAD, "ordinal45 dispatch ref fetch drift")
    require(out("git", "rev-parse", f"{OLD_AUTH_HEAD}:{OLD_AUTH_PATH}") == OLD_AUTH_BLOB, "ordinal45 authorization blob drift")
    old_auth = json.loads(out("git", "show", f"{OLD_AUTH_HEAD}:{OLD_AUTH_PATH}"))
    require(old_auth.get("scientificOrdinal") == 45, "ordinal45 authorization ordinal drift")
    require(old_auth.get("executionKey") == OLD_EXECUTION_KEY, "ordinal45 execution key drift")
    require(old_auth.get("candidateSeedCanonicalSha256") == OLD_SEED_CANONICAL, "ordinal45 authorization seed canonical drift")
    write_json(evidence / "ordinal45-authorization.json", old_auth)

    runs = {}
    for label, run_id in (("publisher", OLD_PUBLISHER_RUN), ("science", OLD_SCIENCE_RUN)):
        row = scanner.req_json(f"https://api.github.com/repos/{repository}/actions/runs/{run_id}", token)
        arts = scanner.req_json(f"https://api.github.com/repos/{repository}/actions/runs/{run_id}/artifacts?per_page=100", token)
        require(int(row.get("id") or 0) == run_id, f"ordinal45 {label} run id drift")
        require(int(row.get("run_attempt") or 0) == 1, f"ordinal45 {label} run attempt drift")
        require(row.get("status") == "completed" and row.get("conclusion") == "failure", f"ordinal45 {label} run terminal drift")
        require(int(arts.get("total_count") or 0) == 0, f"ordinal45 {label} artifact cardinality drift")
        write_json(evidence / f"ordinal45-{label}-run.json", row)
        write_json(evidence / f"ordinal45-{label}-artifacts.json", arts)
        runs[label] = row

    comments = [str(row.get("body") or "").strip() for row in context.get("issue60Comments", [])]
    require(sum(body.startswith(OLD_CONSUMED_MARKER) for body in comments) == 1, "ordinal45 consumed marker cardinality drift")
    return {"authorization": old_auth, "runs": runs}


def derive_ordinal_and_identity(scanner, args, token: str, context: dict[str, Any], report: dict[str, Any], ledger: dict[str, Any], evidence: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    preauth = load("avps_successor_preauthorization_surface", PREAUTH_SURFACE_PATH)
    payload = preauth.collect(args.repository, token)
    latest = preauth.latest_consumed_or_dispatched_ordinal(payload)
    require(isinstance(latest, int) and latest >= 45, f"global latest consumed/dispatch ordinal omits consumed AVPS45: {latest!r}")
    candidate, observations = preauth.derive_next_global_ordinal(payload, latest, current_run_id=args.run_id)
    require(isinstance(candidate, int) and candidate > latest, "derived successor ordinal is not strictly newer than global latest")
    obs45 = [row for row in observations if int(row.get("ordinal") or 0) == 45]
    require(bool(obs45), "authoritative global ordinal observations omit consumed ordinal45")

    auth_branch = f"authorization/aerosol-vertical-profile-sensitivity-v2-postconsumption-successor-ordinal-{candidate}"
    dispatch_branch = f"dispatch/aerosol-vertical-profile-sensitivity-v2-postconsumption-successor-ordinal-{candidate}"
    execution_key = f"aerosol-vertical-profile-sensitivity-v2-postconsumption-successor:numerical:{candidate}"
    publisher_workflow = f".github/workflows/avps-v2-postconsumption-successor-ordinal-{candidate}-final-dispatch-publisher-v1.yml"
    science_workflow = f".github/workflows/avps-v2-postconsumption-successor-ordinal-{candidate}-science.yml"
    runtime_dir = f"runtime-avps-v2-postconsumption-successor-ordinal{candidate}-v1"

    branch_names = {str(row.get("name") or "") for row in payload.get("branches", [])}
    require(auth_branch not in branch_names and dispatch_branch not in branch_names, "fresh successor auth/dispatch ref already exists")
    require(not any(str(row.get("path") or "") in {publisher_workflow, science_workflow} for row in payload.get("runs", [])), "fresh successor workflow run identity already exists")
    packed = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    require(execution_key not in packed, "fresh successor execution key already appears on repository-global metadata")
    grep = run("git", "grep", "-F", execution_key, check=False)
    require(grep.returncode == 1, "fresh successor execution key already appears in tracked repository bytes")
    comments = [str(row.get("body") or "").strip() for row in payload.get("issue60Comments", [])]
    require(not any(body.upper().startswith(f"ORDINAL{candidate}_") for body in comments), "fresh successor ordinal already has Issue60 allocation/consumption marker")

    ordinal = {
        "schemaVersion": 1,
        "status": "PASS_AVPS_V2_SUCCESSOR_DYNAMIC_GLOBAL_ORDINAL_NOT_ALLOCATED",
        "latestPriorConsumedOrDispatchedScientificOrdinal": latest,
        "nextAvailableScientificOrdinal": candidate,
        "globalOrdinalObservationCount": len(observations),
        "ordinal45ObservationCount": len(obs45),
        "scientificOrdinalAllocated": False,
        "authorizationCreated": False,
        "dispatchCreated": False,
    }
    write_json(evidence / "global-ordinal-observations.json", observations)
    write_json(evidence / "dynamic-global-ordinal.json", ordinal)

    identity: dict[str, Any] = {
        "schemaVersion": 1,
        "status": "PROPOSED_AVPS_V2_POSTCONSUMPTION_SUCCESSOR_IDENTITY_NOT_ALLOCATED_NOT_DISPATCHED",
        "scientificOrdinal": candidate,
        "authorizationBranch": auth_branch,
        "dispatchBranch": dispatch_branch,
        "executionKey": execution_key,
        "proposedPublisherWorkflowPath": publisher_workflow,
        "proposedScienceWorkflowPath": science_workflow,
        "proposedRuntimeDirectory": runtime_dir,
        "proposalBranch": EXPECTED_BRANCH,
        "proposalHead": args.head,
        "proposalPr": args.pr,
        "exactMainParent": EXPECTED_BASE,
        "sourceInstalledPublisherWorkflowPath": INSTALLED_PUBLISHER_PATH,
        "sourceInstalledPublisherWorkflowBlobSha1": INSTALLED_PUBLISHER_BLOB,
        "sourceInstalledScienceWorkflowPath": INSTALLED_SCIENCE_PATH,
        "sourceInstalledScienceWorkflowBlobSha1": INSTALLED_SCIENCE_BLOB,
        "sourceRuntimeAdapterBlobSha1": RUNTIME_BLOBS["runtime-avps-v2-recovery4-ordinal45-v1/runtime_adapter.py"],
        "sourceRuntimeExecutorBlobSha1": RUNTIME_BLOBS["runtime-avps-v2-recovery4-ordinal45-v1/executor.py"],
        "sourceRuntimeAggregatorBlobSha1": RUNTIME_BLOBS["runtime-avps-v2-recovery4-ordinal45-v1/aggregator.py"],
        "candidateSeedNamespace": ledger["namespace"],
        "candidateSeedCount": 72,
        "candidateSeedCanonicalSha256": ledger["candidateSeedCanonicalSha256"],
        "candidateRowsCanonicalSha256": ledger["candidateRowsCanonicalSha256"],
        "consumedOrdinal45SeedCanonicalSha256": ledger["consumedOrdinal45SeedCanonicalSha256"],
        **FROZEN_DESIGN,
        "repositoryGlobalStableContextSha256": report["repositoryGlobalStableContextSha256"],
        "repositoryGlobalSnapshotFenceSha256": report["repositoryGlobalSnapshotFenceSha256"],
        "repositoryGlobalCollisionCount": 0,
        "repositoryGlobalDoubleEnumerationStable": True,
        "consumedOrdinal45PublisherRun": OLD_PUBLISHER_RUN,
        "consumedOrdinal45ScienceRun": OLD_SCIENCE_RUN,
        "consumedOrdinal45AuthorizationBranch": OLD_AUTH_BRANCH,
        "consumedOrdinal45DispatchBranch": OLD_DISPATCH_BRANCH,
        "consumedOrdinal45AuthorizationHead": OLD_AUTH_HEAD,
        "consumedOrdinal45ExecutionKey": OLD_EXECUTION_KEY,
        "candidateSeedsAppliedToCases": False,
        "seedUniverseConsumed": False,
        "scientificOrdinalAllocated": False,
        "authorizationCreated": False,
        "dispatchCreated": False,
        "publisherInvoked": False,
        "scienceInvoked": False,
        "writeQuietEntered": False,
        "solverExecuted": False,
        "scientificRuntime": False,
        "protectedResultsOpened": False,
        "levelBOpened": False,
        "protectedHoldoutOpened": False,
        "newMappingOccurred": False,
        "productionOccurred": False,
        "taylorOrJerusalemUsed": False,
        "githubRerunAllowed": False,
        "retryAllowed": False,
        "resumeAllowed": False,
    }
    identity["contentSha256"] = canonical_sha256(identity)
    write_json(evidence / "successor-identity-proposal.json", identity)
    return ordinal, identity


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repository", required=True)
    ap.add_argument("--token", required=True)
    ap.add_argument("--pr", type=int, required=True)
    ap.add_argument("--run-id", type=int, required=True)
    ap.add_argument("--run-attempt", type=int, required=True)
    ap.add_argument("--event-name", required=True)
    ap.add_argument("--branch", required=True)
    ap.add_argument("--head", required=True)
    ap.add_argument("--expected-main", required=True)
    ap.add_argument("--evidence-dir", type=Path, required=True)
    args = ap.parse_args()
    evidence = args.evidence_dir
    evidence.mkdir(parents=True, exist_ok=False)

    scanner_wrapper = load("avps_successor_scanner_wrapper", SCANNER_WRAPPER_PATH)
    scanner = scanner_wrapper.mod
    identity_meta = verify_static_identity(scanner, args, args.token)
    write_json(evidence / "pr.json", identity_meta["pr"])
    write_json(evidence / "self-run.json", identity_meta["selfRun"])
    write_json(evidence / "changed-paths.json", identity_meta["changedPaths"])

    run(
        sys.executable,
        "-m",
        "unittest",
        "-v",
        "tests/test_avps_recovery4_canonical_write_quiet_parser_v1.py",
        "tests/test_avps_recovery4_ordinal45_write_quiet_parser_repair.py",
    )
    _, pre_tail = issue60_tail(scanner, args.repository, args.token)
    write_json(evidence / "issue60-pre-tail.json", pre_tail)

    ledger, seeds = derive_seed_ledger(evidence)
    tracked_tree_scan(evidence)
    context, report = global_seed_scan(scanner, args, args.token, seeds, evidence)
    fetch_consumed_ordinal45(scanner, args.repository, args.token, context, evidence)
    ordinal, identity = derive_ordinal_and_identity(scanner, args, args.token, context, report, ledger, evidence)

    _, post_tail = issue60_tail(scanner, args.repository, args.token)
    require(post_tail["commentCount"] >= pre_tail["commentCount"], "Issue60 comment count regressed")
    require(post_tail["tailCommentId"] >= pre_tail["tailCommentId"], "Issue60 tail id regressed")
    write_json(evidence / "issue60-post-tail.json", post_tail)
    require(scanner.final_expected_branch_head(args.repository, "main", args.token) == EXPECTED_BASE, "main moved before receipt freeze")
    require(scanner.final_expected_branch_head(args.repository, EXPECTED_BRANCH, args.token) == args.head, "proposal branch moved before receipt freeze")

    receipt: dict[str, Any] = {
        "schemaVersion": 1,
        "status": "PASS_AVPS_V2_POSTCONSUMPTION_SUCCESSOR_PREAUTHORIZATION_PROPOSAL_NOT_ALLOCATED_NOT_DISPATCHED",
        "proposalBranch": EXPECTED_BRANCH,
        "proposalHead": args.head,
        "proposalPr": args.pr,
        "exactMainParent": EXPECTED_BASE,
        "runId": args.run_id,
        "runAttempt": args.run_attempt,
        "candidateSeedNamespace": ledger["namespace"],
        "candidateSeedCount": 72,
        "candidateSeedCanonicalSha256": ledger["candidateSeedCanonicalSha256"],
        "candidateRowsCanonicalSha256": ledger["candidateRowsCanonicalSha256"],
        "consumedOrdinal45SeedCanonicalSha256": ledger["consumedOrdinal45SeedCanonicalSha256"],
        "latestPriorConsumedOrDispatchedScientificOrdinal": ordinal["latestPriorConsumedOrDispatchedScientificOrdinal"],
        "nextAvailableScientificOrdinal": ordinal["nextAvailableScientificOrdinal"],
        "authorizationBranch": identity["authorizationBranch"],
        "dispatchBranch": identity["dispatchBranch"],
        "executionKey": identity["executionKey"],
        "proposedPublisherWorkflowPath": identity["proposedPublisherWorkflowPath"],
        "proposedScienceWorkflowPath": identity["proposedScienceWorkflowPath"],
        "proposedRuntimeDirectory": identity["proposedRuntimeDirectory"],
        "sourceInstalledPublisherWorkflowBlobSha1": INSTALLED_PUBLISHER_BLOB,
        "sourceInstalledScienceWorkflowBlobSha1": INSTALLED_SCIENCE_BLOB,
        "sourceRuntimeAdapterBlobSha1": identity["sourceRuntimeAdapterBlobSha1"],
        "sourceRuntimeExecutorBlobSha1": identity["sourceRuntimeExecutorBlobSha1"],
        "sourceRuntimeAggregatorBlobSha1": identity["sourceRuntimeAggregatorBlobSha1"],
        "repositoryGlobalCollisionCount": report["repositoryGlobalCollisionCount"],
        "repositoryGlobalDoubleEnumerationStable": report["repositoryGlobalDoubleEnumerationStable"],
        "repositoryGlobalStableContextSha256": report["repositoryGlobalStableContextSha256"],
        "repositoryGlobalSnapshotFenceSha256": report["repositoryGlobalSnapshotFenceSha256"],
        "repositoryGlobalPostFenceArrivalCounts": report["repositoryGlobalPostFenceArrivalCounts"],
        "issue60PreTailCommentId": pre_tail["tailCommentId"],
        "issue60PostTailCommentId": post_tail["tailCommentId"],
        "ordinal45PublisherRunFrozen": OLD_PUBLISHER_RUN,
        "ordinal45ScienceRunFrozen": OLD_SCIENCE_RUN,
        "candidateSeedsAppliedToCases": False,
        "seedUniverseConsumed": False,
        "scientificOrdinalAllocated": False,
        "authorizationCreated": False,
        "dispatchCreated": False,
        "publisherInvoked": False,
        "scienceInvoked": False,
        "writeQuietEntered": False,
        "solverExecuted": False,
        "scientificRuntime": False,
        "protectedResultsOpened": False,
        "levelBOpened": False,
        "protectedHoldoutOpened": False,
        "newMappingOccurred": False,
        "productionOccurred": False,
        "taylorOrJerusalemUsed": False,
        "githubRerunAllowed": False,
        "retryAllowed": False,
        "resumeAllowed": False,
    }
    receipt["receiptSha256"] = canonical_sha256(receipt)
    write_json(evidence / "preauthorization-receipt.json", receipt)
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
