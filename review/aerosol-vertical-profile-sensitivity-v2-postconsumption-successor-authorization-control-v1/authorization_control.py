from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CONTROL_DIR = Path(__file__).resolve().parent
WORKFLOW_PATH = ".github/workflows/avps-v2-postconsumption-successor-authorization-control-v1.yml"
SCRIPT_PATH = "review/aerosol-vertical-profile-sensitivity-v2-postconsumption-successor-authorization-control-v1/authorization_control.py"
ALLOWED_PATHS = sorted([WORKFLOW_PATH, SCRIPT_PATH])

EXPECTED_MAIN = "8cd85cf393e2d86a1b6d7325654747460a13e697"
EXPECTED_MAIN_TREE = "0863892dbc83dfdedaea9ad3c033ca7ef8e3d51e"
CONTROL_BRANCH = "review/avps-v2-postconsumption-successor-authorization-control-v1-20260909"
CONTROL_STAGE = "AVPS_V2_POSTCONSUMPTION_SUCCESSOR_AUTHORIZATION_CONTROL_GLOBAL_SCAN_V1"
CONTROL_ARTIFACT_NAME = "vertical-profile-v2-postconsumption-successor-authorization-control-v1-proof"

SOURCE_PR = 1020
SOURCE_BRANCH = "review/avps-v2-postconsumption-successor-preauth-v1-20260909"
SOURCE_HEAD = "debd28273a448e928639ecb72331214ff2f52783"
SOURCE_GENERIC_RUN = 34397934985
SOURCE_RUN = 34397934898
SOURCE_JOB = 102622212032
SOURCE_ARTIFACT = 10123046136
SOURCE_ARTIFACT_NAME = "vertical-profile-v2-postconsumption-successor-preauthorization-proof"
SOURCE_ARTIFACT_DIGEST = "sha256:8d5f20c3e4e8e08a059e93c5a9545141838b7d1604ac7def289c64260b75282d"
SOURCE_RECEIPT_SHA = "8d8f7f96f58141aba4961833d0d4bf5f7e396229491d3ad9110c4bd7d825cc85"
SOURCE_SEED_CANONICAL = "6ace6be3b0298f3fa35cdc522a3375c0480a4154371c15bbbf4a3f930a5d17cd"
SOURCE_ROWS_CANONICAL = "30c0c1e38755f2c04b59448569c15c38a8b3b850c73d235ea38ce8f880d30f8b"
SOURCE_BLOBS = {
    ".github/workflows/avps-v2-postconsumption-successor-preauthorization-v1.yml": "e170f35c643da987d022ad109d5a90401984eba2",
    "review/aerosol-vertical-profile-sensitivity-v2-postconsumption-successor-preauth-v1/preauthorize.py": "769c85d9a5180a49d0dbd5ca1b778cde51043423",
    "review/aerosol-vertical-profile-sensitivity-v2-postconsumption-successor-preauth-v1/repository_global_seed_scan.py": "707725ff46848286e8406e5ff5e51be2081516e3",
    "review/aerosol-vertical-profile-sensitivity-v2-postconsumption-successor-preauth-v1/seed_ledger.py": "1bb52acbd902ba3b0e2fdc5e470461db5a49e9e4",
}
SOURCE_CONTROL_DIR = "review/aerosol-vertical-profile-sensitivity-v2-postconsumption-successor-preauth-v1"
ORDINAL42_AUTH_HEAD = "e627a689ada0493a8a5b9cdafc4aba0198fbabec"

OLD_AUTH_BRANCH = "authorization/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery4-ordinal-45"
OLD_DISPATCH_BRANCH = "dispatch/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery4-ordinal-45"
OLD_AUTH_HEAD = "6e095b4b1603c90dcee0943295909b30cd1b374d"
OLD_PUBLISHER_RUN = 34247116198
OLD_SCIENCE_RUN = 34248529569

INSTALLED_SCIENCE_PATH = ".github/workflows/avps-v2-postconsumption-recovery4-science.yml"
INSTALLED_PUBLISHER_PATH = ".github/workflows/avps-v2-recovery4-ordinal45-final-dispatch-publisher-v3.yml"
RUNTIME_PATHS = {
    "runtimeAdapter": "runtime-avps-v2-recovery4-ordinal45-v1/runtime_adapter.py",
    "runtimeExecutor": "runtime-avps-v2-recovery4-ordinal45-v1/executor.py",
    "runtimeAggregator": "runtime-avps-v2-recovery4-ordinal45-v1/aggregator.py",
}
TRACKED_SCAN_PATH = "review/aerosol-vertical-profile-sensitivity-v2-seed-freshness/tracked_tree_seed_scan.py"
PREAUTH_SURFACE_PATH = "experiments/aerosol-vertical-profile-sensitivity-v1/preauthorization_surface.py"

AUTHORITY_FALSE_KEYS = (
    "candidateSeedsAppliedToCases",
    "seedUniverseConsumed",
    "scientificOrdinalAllocated",
    "authorizationCreated",
    "dispatchCreated",
    "publisherInvoked",
    "scienceInvoked",
    "writeQuietEntered",
    "solverExecuted",
    "scientificRuntime",
    "protectedResultsOpened",
    "levelBOpened",
    "protectedHoldoutOpened",
    "newMappingOccurred",
    "productionOccurred",
    "taylorOrJerusalemUsed",
)


class Refusal(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Refusal(message)


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def run(*args: str, cwd: Path | None = None, check: bool = True, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    cp = subprocess.run(args, cwd=cwd or ROOT, text=True, capture_output=True, env=env)
    if check and cp.returncode != 0:
        raise Refusal(f"command failed rc={cp.returncode}: {' '.join(args)}\nstdout={cp.stdout}\nstderr={cp.stderr}")
    return cp


def out(*args: str, cwd: Path | None = None) -> str:
    return run(*args, cwd=cwd).stdout.strip()


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise Refusal(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def request_bytes(url: str, token: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "avps-successor-authorization-control-v1",
        },
    )
    with urllib.request.urlopen(req, timeout=90) as response:
        return response.read()


def req_json(url: str, token: str) -> Any:
    return json.loads(request_bytes(url, token))


def pages(url: str, token: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    page = 1
    sep = "&" if "?" in url else "?"
    while True:
        chunk = req_json(f"{url}{sep}per_page=100&page={page}", token)
        require(isinstance(chunk, list), f"expected paginated list from {url}")
        rows.extend(chunk)
        if len(chunk) < 100:
            return rows
        page += 1


def repo_url(repository: str, suffix: str) -> str:
    return f"https://api.github.com/repos/{repository}/{suffix.lstrip('/')}"


def branch_head(repository: str, branch: str, token: str) -> str:
    encoded = urllib.parse.quote(branch, safe="")
    row = req_json(repo_url(repository, f"branches/{encoded}"), token)
    return str((row.get("commit") or {}).get("sha") or "")


def verify_repo_identity(repository: str, token: str) -> dict[str, Any]:
    repo = req_json(repo_url(repository, ""), token)
    require(repo.get("full_name") == repository, "repository identity drift")
    require(repo.get("default_branch") == "main", "default branch drift")
    return repo


def current_pr(repository: str, pr_number: int, token: str) -> dict[str, Any]:
    return req_json(repo_url(repository, f"pulls/{pr_number}"), token)


def verify_static_control_identity(args, token: str) -> dict[str, Any]:
    require(args.event_name == "pull_request", "control requires pull_request event")
    require(args.event_action == "opened", "control requires fresh PR-open event")
    require(args.run_attempt == 1, "control identity must be attempt1")
    require(args.branch == CONTROL_BRANCH, "control branch drift")
    require(args.base == EXPECTED_MAIN, "control base drift")
    require(out("git", "rev-parse", "HEAD") == args.head, "checked-out control head drift")
    require(out("git", "rev-parse", "HEAD^{tree}") != "", "control tree unavailable")
    require(branch_head(args.repository, "main", token) == EXPECTED_MAIN, "main moved from exact control base")
    require(branch_head(args.repository, CONTROL_BRANCH, token) == args.head, "control branch head drift")
    require(run("git", "merge-base", "--is-ancestor", EXPECTED_MAIN, args.head, check=False).returncode == 0, "control head not descendant of exact main")
    require(not out("git", "rev-list", "--merges", f"{EXPECTED_MAIN}..{args.head}"), "control candidate lineage contains merge commit")
    changed = sorted(x for x in out("git", "diff", "--name-only", f"{EXPECTED_MAIN}...{args.head}").splitlines() if x)
    require(changed == ALLOWED_PATHS, f"control changed-path drift: {changed}")
    pr = current_pr(args.repository, args.pr, token)
    require(pr.get("state") == "open" and pr.get("draft") is True and pr.get("merged_at") is None, "control PR must be Draft/open/unmerged")
    require(str((pr.get("head") or {}).get("sha") or "") == args.head, "control PR head drift")
    require(str((pr.get("head") or {}).get("ref") or "") == CONTROL_BRANCH, "control PR branch drift")
    require(str((pr.get("base") or {}).get("sha") or "") == EXPECTED_MAIN, "control PR base SHA drift")
    require(str((pr.get("base") or {}).get("ref") or "") == "main", "control PR base ref drift")
    self_run = req_json(repo_url(args.repository, f"actions/runs/{args.run_id}"), token)
    require(int(self_run.get("id") or 0) == args.run_id, "control self-run id drift")
    require(int(self_run.get("run_attempt") or 0) == 1, "control self-run attempt drift")
    require(self_run.get("event") == "pull_request", "control self-run event drift")
    require(self_run.get("head_sha") == args.head and self_run.get("head_branch") == CONTROL_BRANCH, "control self-run head drift")
    require(self_run.get("path") == WORKFLOW_PATH, "control workflow registration drift")
    require(shutil.which("uvspec") is None, "uvspec unexpectedly present in zero-runtime control")
    repo = verify_repo_identity(args.repository, token)
    return {"repo": repo, "pr": pr, "selfRun": self_run, "changedPaths": changed}


def canonical_write_quiet_state(repository: str, token: str, expected_head: str, expected_begin_id: int | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    from scripts.avps_write_quiet_parser_v1 import is_write_quiet_begin, record_write_quiet_end

    rows = pages(repo_url(repository, "issues/60/comments"), token)
    begin_ids: set[int] = set()
    closed: set[int] = set()
    begin_rows: dict[int, dict[str, Any]] = {}
    for row in rows:
        body = str(row.get("body") or "")
        if record_write_quiet_end(body, int(row["id"]), begin_ids, closed):
            continue
        if is_write_quiet_begin(body):
            cid = int(row["id"])
            begin_ids.add(cid)
            begin_rows[cid] = row
    unmatched = sorted(cid for cid in begin_ids if cid not in closed)
    require(len(unmatched) == 1, f"control requires exactly its own live WRITE_QUIET fence; unmatched={unmatched}")
    begin_id = unmatched[0]
    if expected_begin_id is not None:
        require(begin_id == expected_begin_id, f"WRITE_QUIET begin changed {begin_id} != {expected_begin_id}")
    body = str(begin_rows[begin_id].get("body") or "")
    first = body.splitlines()[0].strip() if body.splitlines() else ""
    require(first.startswith(f"WRITE_QUIET_BEGIN | {CONTROL_STAGE} |"), "live WRITE_QUIET is not this control stage")
    for token_value in (f"branch={CONTROL_BRANCH}", f"head={expected_head}", f"base={EXPECTED_MAIN}"):
        require(token_value in first, f"control WRITE_QUIET marker missing {token_value}")
    state = {
        "schemaVersion": 1,
        "commentCount": len(rows),
        "tailCommentId": max((int(row["id"]) for row in rows), default=0),
        "unmatchedWriteQuietBeginIds": unmatched,
        "controlWriteQuietBeginId": begin_id,
        "canonicalParserUsed": True,
    }
    return rows, state


def source_worktree(repository: str) -> tuple[Path, Path, tempfile.TemporaryDirectory[str]]:
    temp = tempfile.TemporaryDirectory(prefix="avps-auth-control-")
    root = Path(temp.name)
    source = root / "source-preauth"
    historical42 = root / "ordinal42-auth"
    run("git", "fetch", "--no-tags", "origin", f"refs/heads/{SOURCE_BRANCH}")
    run("git", "worktree", "add", "--detach", str(source), SOURCE_HEAD)
    run("git", "worktree", "add", "--detach", str(historical42), ORDINAL42_AUTH_HEAD)
    return source, historical42, temp


def cleanup_worktrees(source: Path, historical42: Path, temp: tempfile.TemporaryDirectory[str]) -> None:
    run("git", "worktree", "remove", "--force", str(historical42), check=False)
    run("git", "worktree", "remove", "--force", str(source), check=False)
    temp.cleanup()


def verify_source_code(source: Path) -> None:
    require(out("git", "rev-parse", "HEAD", cwd=source) == SOURCE_HEAD, "source preauth worktree head drift")
    for path, blob in SOURCE_BLOBS.items():
        require(out("git", "rev-parse", f"HEAD:{path}", cwd=source) == blob, f"source preauth blob drift: {path}")


def download_source_artifact(repository: str, token: str) -> tuple[bytes, dict[str, Any]]:
    arts = req_json(repo_url(repository, f"actions/runs/{SOURCE_RUN}/artifacts?per_page=100"), token)
    candidates = [a for a in arts.get("artifacts", []) if int(a.get("id") or 0) == SOURCE_ARTIFACT]
    require(len(candidates) == 1, "source preauthorization artifact identity missing/duplicated")
    art = candidates[0]
    require(art.get("name") == SOURCE_ARTIFACT_NAME, "source artifact name drift")
    require(art.get("digest") == SOURCE_ARTIFACT_DIGEST and art.get("expired") is False, "source artifact digest/expiry drift")
    raw = request_bytes(repo_url(repository, f"actions/artifacts/{SOURCE_ARTIFACT}/zip"), token)
    require("sha256:" + hashlib.sha256(raw).hexdigest() == SOURCE_ARTIFACT_DIGEST, "downloaded source artifact byte digest drift")
    return raw, art


def source_receipt_from_zip(raw: bytes) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        names = set(zf.namelist())
        for required in ("preauthorization-receipt.json", "successor-identity-proposal.json", "candidate-seed-ledger.json"):
            require(required in names, f"source proof artifact missing {required}")
        receipt = json.loads(zf.read("preauthorization-receipt.json"))
        identity = json.loads(zf.read("successor-identity-proposal.json"))
        artifact_ledger = json.loads(zf.read("candidate-seed-ledger.json"))
    saved = receipt.get("receiptSha256")
    check = dict(receipt)
    check.pop("receiptSha256", None)
    require(saved == SOURCE_RECEIPT_SHA and canonical_sha256(check) == SOURCE_RECEIPT_SHA, "source preauth receipt self-hash drift")
    require(receipt.get("status") == "PASS_AVPS_V2_POSTCONSUMPTION_SUCCESSOR_PREAUTHORIZATION_PROPOSAL_NOT_ALLOCATED_NOT_DISPATCHED", "source preauth status drift")
    require(receipt.get("proposalPr") == SOURCE_PR and receipt.get("proposalHead") == SOURCE_HEAD and receipt.get("exactMainParent") == EXPECTED_MAIN, "source receipt PR/head/base drift")
    require(receipt.get("runId") == SOURCE_RUN and receipt.get("runAttempt") == 1, "source receipt run drift")
    require(receipt.get("candidateSeedCount") == 72, "source candidate cardinality drift")
    require(receipt.get("candidateSeedCanonicalSha256") == SOURCE_SEED_CANONICAL, "source seed canonical drift")
    require(receipt.get("candidateRowsCanonicalSha256") == SOURCE_ROWS_CANONICAL, "source rows canonical drift")
    require(receipt.get("latestPriorConsumedOrDispatchedScientificOrdinal") == 45 and receipt.get("nextAvailableScientificOrdinal") == 46, "source dynamic ordinal receipt drift")
    require(receipt.get("repositoryGlobalCollisionCount") == 0 and receipt.get("repositoryGlobalDoubleEnumerationStable") is True, "source global freshness receipt drift")
    require(all(receipt.get(key) is False for key in AUTHORITY_FALSE_KEYS), "source preauth receipt authority boundary drift")
    require(identity.get("scientificOrdinal") == 46 and identity.get("candidateSeedCanonicalSha256") == SOURCE_SEED_CANONICAL, "source identity proposal drift")
    require(all(identity.get(key) is False for key in AUTHORITY_FALSE_KEYS), "source identity authority boundary drift")
    require(artifact_ledger.get("candidateSeedCount") == 72 and artifact_ledger.get("candidateSeedCanonicalSha256") == SOURCE_SEED_CANONICAL, "artifact candidate ledger drift")
    return receipt, identity, artifact_ledger


def verify_source_api(repository: str, token: str) -> dict[str, Any]:
    pr = current_pr(repository, SOURCE_PR, token)
    require(pr.get("state") == "open" and pr.get("draft") is True and pr.get("merged_at") is None, "source PR1020 state drift")
    require(str((pr.get("head") or {}).get("sha") or "") == SOURCE_HEAD and str((pr.get("base") or {}).get("sha") or "") == EXPECTED_MAIN, "source PR1020 head/base drift")
    source_run = req_json(repo_url(repository, f"actions/runs/{SOURCE_RUN}"), token)
    require(source_run.get("status") == "completed" and source_run.get("conclusion") == "success" and source_run.get("run_attempt") == 1, "source preauth run drift")
    require(source_run.get("head_sha") == SOURCE_HEAD, "source preauth run head drift")
    jobs = req_json(repo_url(repository, f"actions/runs/{SOURCE_RUN}/jobs?per_page=100"), token)
    job_rows = [j for j in jobs.get("jobs", []) if int(j.get("id") or 0) == SOURCE_JOB]
    require(len(job_rows) == 1 and job_rows[0].get("conclusion") == "success", "source preauth job drift")
    generic = req_json(repo_url(repository, f"actions/runs/{SOURCE_GENERIC_RUN}"), token)
    require(generic.get("path") == ".github/workflows/contract.yml" and generic.get("head_sha") == SOURCE_HEAD and generic.get("run_attempt") == 1 and generic.get("conclusion") == "success", "source generic CI drift")
    raw, artifact = download_source_artifact(repository, token)
    receipt, identity, artifact_ledger = source_receipt_from_zip(raw)
    return {"pr": pr, "run": source_run, "job": job_rows[0], "generic": generic, "artifact": artifact, "receipt": receipt, "identity": identity, "artifactLedger": artifact_ledger}


def load_source_modules(source: Path, historical42: Path):
    prior = os.environ.get("AVPS_ORDINAL42_LEDGER_PATH")
    os.environ["AVPS_ORDINAL42_LEDGER_PATH"] = str(historical42 / "review/aerosol-vertical-profile-sensitivity-v2-postconsumption-seed-freshness-v1/seed_ledger.py")
    scanner_wrapper = load("avps_auth_control_source_scanner_wrapper", source / SOURCE_CONTROL_DIR / "repository_global_seed_scan.py")
    ledger_mod = load("avps_auth_control_source_seed_ledger", source / SOURCE_CONTROL_DIR / "seed_ledger.py")
    if prior is None:
        os.environ.pop("AVPS_ORDINAL42_LEDGER_PATH", None)
    else:
        os.environ["AVPS_ORDINAL42_LEDGER_PATH"] = prior
    return scanner_wrapper, ledger_mod


def validate_source_ledger(ledger_mod, historical42: Path) -> dict[str, Any]:
    prior = os.environ.get("AVPS_ORDINAL42_LEDGER_PATH")
    os.environ["AVPS_ORDINAL42_LEDGER_PATH"] = str(historical42 / "review/aerosol-vertical-profile-sensitivity-v2-postconsumption-seed-freshness-v1/seed_ledger.py")
    try:
        ledger = ledger_mod.validate_ledger()
    finally:
        if prior is None:
            os.environ.pop("AVPS_ORDINAL42_LEDGER_PATH", None)
        else:
            os.environ["AVPS_ORDINAL42_LEDGER_PATH"] = prior
    require(ledger.get("candidateSeedCount") == 72, "fresh source ledger candidate count drift")
    require(ledger.get("candidateSeedCanonicalSha256") == SOURCE_SEED_CANONICAL, "fresh source ledger seed canonical drift")
    require(ledger.get("candidateRowsCanonicalSha256") == SOURCE_ROWS_CANONICAL, "fresh source ledger rows canonical drift")
    require(len({int(x) for x in ledger.get("candidateSeeds", [])}) == 72, "fresh source ledger seed uniqueness drift")
    for ordinal in (41, 42, 43, 44, 45):
        require(ledger.get(f"overlapWithConsumedOrdinal{ordinal}SeedCount") == 0, f"successor overlap with consumed ordinal {ordinal}")
    return ledger


def run_parser_regressions() -> dict[str, Any]:
    cp = run(
        sys.executable,
        "-m",
        "unittest",
        "-v",
        "tests/test_avps_recovery4_canonical_write_quiet_parser_v1.py",
        "tests/test_avps_recovery4_ordinal45_write_quiet_parser_repair.py",
    )
    combined = cp.stdout + "\n" + cp.stderr
    require("OK" in combined, "canonical WRITE_QUIET regression did not report OK")
    return {"returnCode": cp.returncode, "stdoutSha256": hashlib.sha256(cp.stdout.encode()).hexdigest(), "stderrSha256": hashlib.sha256(cp.stderr.encode()).hexdigest()}


def stress(args) -> None:
    evidence = args.evidence_dir
    evidence.mkdir(parents=True, exist_ok=False)
    static = verify_static_control_identity(args, args.token)
    _, wq = canonical_write_quiet_state(args.repository, args.token, args.head)
    source_api = verify_source_api(args.repository, args.token)
    source, historical42, temp = source_worktree(args.repository)
    try:
        verify_source_code(source)
        scanner_wrapper, ledger_mod = load_source_modules(source, historical42)
        fixture = scanner_wrapper._run_snapshot_projection_fixtures()
        ledger = validate_source_ledger(ledger_mod, historical42)
        require(ledger.get("candidateSeedCanonicalSha256") == source_api["artifactLedger"].get("candidateSeedCanonicalSha256"), "source code/artifact seed ledger mismatch")
        parser_result = run_parser_regressions()
    finally:
        cleanup_worktrees(source, historical42, temp)
    require(branch_head(args.repository, "main", args.token) == EXPECTED_MAIN, "main moved during stress")
    require(branch_head(args.repository, CONTROL_BRANCH, args.token) == args.head, "control head moved during stress")
    _, wq_after = canonical_write_quiet_state(args.repository, args.token, args.head, wq["controlWriteQuietBeginId"])
    write_json(evidence / "static-control-identity.json", {"changedPaths": static["changedPaths"], "repoDefaultBranch": static["repo"].get("default_branch"), "pr": {"number": args.pr, "head": args.head, "base": args.base}, "run": {"id": args.run_id, "attempt": args.run_attempt, "event": args.event_name, "action": args.event_action}})
    write_json(evidence / "source-preauthorization-binding.json", {"pr": SOURCE_PR, "head": SOURCE_HEAD, "run": SOURCE_RUN, "job": SOURCE_JOB, "artifact": SOURCE_ARTIFACT, "artifactDigest": SOURCE_ARTIFACT_DIGEST, "receiptSha256": SOURCE_RECEIPT_SHA, "candidateSeedCanonicalSha256": SOURCE_SEED_CANONICAL, "candidateRowsCanonicalSha256": SOURCE_ROWS_CANONICAL})
    write_json(evidence / "source-preauthorization-receipt.json", source_api["receipt"])
    write_json(evidence / "source-successor-identity-proposal.json", source_api["identity"])
    write_json(evidence / "stress-write-quiet-pre.json", wq)
    write_json(evidence / "stress-write-quiet-post.json", wq_after)
    write_json(evidence / "stress-scanner-fixture.json", fixture)
    write_json(evidence / "stress-parser-regressions.json", parser_result)
    write_json(evidence / "stress-result.json", {
        "schemaVersion": 1,
        "status": "PASS_NON_AUTHORIZING_ACTUAL_EXECUTABLE_STRESS",
        "completeIssue60Parsed": True,
        "actualEventRefBaseDefaultBranchBound": True,
        "sourceArtifactReadbackBound": True,
        "sourceScannerProjectionFixturesPassed": True,
        "canonicalWriteQuietRegressionPassed": True,
        "candidateSeedCount": 72,
        "candidateSeedCanonicalSha256": SOURCE_SEED_CANONICAL,
        "candidateRowsCanonicalSha256": SOURCE_ROWS_CANONICAL,
        "scientificOrdinalAllocated": False,
        "authorizationCreated": False,
        "dispatchCreated": False,
        "publisherInvoked": False,
        "scienceInvoked": False,
        "solverExecuted": False,
        "protectedResultsOpened": False,
        "productionOccurred": False,
    })


def exact_head_runs(repository: str, head: str, token: str) -> list[dict[str, Any]]:
    url = repo_url(repository, f"actions/runs?head_sha={urllib.parse.quote(head, safe='')}&event=pull_request")
    payload = req_json(url, token)
    return list(payload.get("workflow_runs", []))


def await_generic(args) -> None:
    deadline = time.time() + 1800
    while True:
        require(branch_head(args.repository, "main", args.token) == EXPECTED_MAIN, "main moved while awaiting exact-head CI")
        require(branch_head(args.repository, CONTROL_BRANCH, args.token) == args.head, "control branch moved while awaiting exact-head CI")
        _, wq = canonical_write_quiet_state(args.repository, args.token, args.head)
        runs = exact_head_runs(args.repository, args.head, args.token)
        generic = [r for r in runs if r.get("path") == ".github/workflows/contract.yml" and int(r.get("run_attempt") or 0) == 1]
        if len(generic) > 1:
            raise Refusal(f"multiple exact-head generic attempt1 identities: {[r.get('id') for r in generic]}")
        generic_ok = len(generic) == 1 and generic[0].get("status") == "completed" and generic[0].get("conclusion") == "success"
        siblings = [r for r in runs if int(r.get("id") or 0) != args.run_id]
        siblings_terminal = bool(siblings) and all(r.get("status") == "completed" for r in siblings)
        if generic_ok and siblings_terminal:
            write_json(args.evidence_dir / "exact-head-ci-gate.json", {
                "schemaVersion": 1,
                "status": "PASS_EXACT_HEAD_GENERIC_ATTEMPT1_AND_SIBLING_TERMINALITY",
                "genericRunId": int(generic[0]["id"]),
                "genericConclusion": generic[0].get("conclusion"),
                "siblingRunIds": sorted(int(r["id"]) for r in siblings),
                "writeQuietBeginId": wq["controlWriteQuietBeginId"],
            })
            time.sleep(5)
            return
        if any(r.get("path") == ".github/workflows/contract.yml" and r.get("status") == "completed" and r.get("conclusion") != "success" for r in generic):
            raise Refusal("exact-head generic attempt1 CI terminal non-success")
        if time.time() >= deadline:
            raise Refusal("timed out waiting for exact-head generic attempt1/sibling terminality")
        time.sleep(10)


def tracked_tree_scan(evidence: Path, ledger: dict[str, Any]) -> dict[str, Any]:
    candidate = evidence / "candidate-seed-ledger.json"
    write_json(candidate, ledger)
    file_list = evidence / "tracked-files.nul"
    file_list.write_bytes(subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT))
    policy = evidence / "empty-self-ledger-policy.json"
    write_json(policy, {"schemaVersion": 2, "requiredTrackedSelfLedgerPaths": [], "futureEvidenceSelfLedgerPaths": []})
    output = evidence / "tracked-seed-scan.json"
    run(sys.executable, TRACKED_SCAN_PATH, "--repo-root", ".", "--file-list", str(file_list), "--candidate-seed-ledger", str(candidate), "--allow-self-ledger-json", str(policy), "--output", str(output))
    scan = json.loads(output.read_text())
    require(scan.get("candidateSeedCount") == 72, "tracked scan candidate count drift")
    require(scan.get("trackedTreeExternalCollisionCount") == 0 and scan.get("selfLedgerHitCount") == 0, "tracked-tree candidate seed collision")
    require(scan.get("exactHeadTrackedTreeByteScanPassed") is True, "tracked-tree exact-head scan did not pass")
    return scan


def verify_consumed45(repository: str, token: str) -> dict[str, Any]:
    require(branch_head(repository, OLD_AUTH_BRANCH, token) == OLD_AUTH_HEAD, "ordinal45 authorization ref drift")
    require(branch_head(repository, OLD_DISPATCH_BRANCH, token) == OLD_AUTH_HEAD, "ordinal45 dispatch ref drift")
    result: dict[str, Any] = {"authorizationHead": OLD_AUTH_HEAD}
    for label, run_id in (("publisher", OLD_PUBLISHER_RUN), ("science", OLD_SCIENCE_RUN)):
        row = req_json(repo_url(repository, f"actions/runs/{run_id}"), token)
        arts = req_json(repo_url(repository, f"actions/runs/{run_id}/artifacts?per_page=100"), token)
        require(row.get("status") == "completed" and row.get("conclusion") == "failure" and int(row.get("run_attempt") or 0) == 1, f"ordinal45 {label} run drift")
        require(int(arts.get("total_count") or 0) == 0, f"ordinal45 {label} artifact drift")
        result[label] = {"runId": run_id, "attempt": 1, "conclusion": "failure", "artifactCount": 0}
    return result


def verify_installed_blobs(identity: dict[str, Any]) -> dict[str, str]:
    expected = {
        INSTALLED_PUBLISHER_PATH: identity["sourceInstalledPublisherWorkflowBlobSha1"],
        INSTALLED_SCIENCE_PATH: identity["sourceInstalledScienceWorkflowBlobSha1"],
        RUNTIME_PATHS["runtimeAdapter"]: identity["sourceRuntimeAdapterBlobSha1"],
        RUNTIME_PATHS["runtimeExecutor"]: identity["sourceRuntimeExecutorBlobSha1"],
        RUNTIME_PATHS["runtimeAggregator"]: identity["sourceRuntimeAggregatorBlobSha1"],
    }
    for path, blob in expected.items():
        require(out("git", "rev-parse", f"HEAD:{path}") == blob, f"installed frozen byte drift: {path}")
    return expected


def dynamic_ordinal(repository: str, token: str, run_id: int, source_receipt: dict[str, Any], evidence: Path):
    preauth = load("avps_auth_control_dynamic_ordinal", ROOT / PREAUTH_SURFACE_PATH)
    payload = preauth.collect(repository, token)
    latest = preauth.latest_consumed_or_dispatched_ordinal(payload)
    candidate, observations = preauth.derive_next_global_ordinal(payload, latest, current_run_id=run_id)
    require(latest == source_receipt["latestPriorConsumedOrDispatchedScientificOrdinal"] == 45, f"latest global ordinal drift: {latest}")
    require(candidate == source_receipt["nextAvailableScientificOrdinal"] == 46, f"next global ordinal changed: {candidate}")
    auth_branch = source_receipt["authorizationBranch"]
    dispatch_branch = source_receipt["dispatchBranch"]
    execution_key = source_receipt["executionKey"]
    branch_names = {str(r.get("name") or "") for r in payload.get("branches", [])}
    require(auth_branch not in branch_names and dispatch_branch not in branch_names, "ordinal46 authorization/dispatch ref already exists")
    require(not any(str(r.get("path") or "") in {source_receipt["proposedPublisherWorkflowPath"], source_receipt["proposedScienceWorkflowPath"]} for r in payload.get("runs", [])), "ordinal46 proposed workflow run identity already exists")
    packed = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    require(execution_key not in packed, "ordinal46 execution key already appears in repository-global metadata")
    require(run("git", "grep", "-F", execution_key, check=False).returncode == 1, "ordinal46 execution key already appears in tracked bytes")
    comments = [str(r.get("body") or "").strip() for r in payload.get("issue60Comments", [])]
    require(not any(body.upper().startswith(f"ORDINAL{candidate}_") for body in comments), "ordinal46 allocation/consumption marker already exists")
    write_json(evidence / "global-ordinal-observations.json", observations)
    return payload, latest, candidate, observations


def control(args) -> None:
    evidence = args.evidence_dir
    require(evidence.exists(), "stress evidence directory missing")
    require((evidence / "stress-result.json").exists(), "NON_AUTHORIZING stress evidence missing")
    require((evidence / "exact-head-ci-gate.json").exists(), "exact-head generic CI gate missing")
    static = verify_static_control_identity(args, args.token)
    _, pre_tail = canonical_write_quiet_state(args.repository, args.token, args.head)
    source_api = verify_source_api(args.repository, args.token)
    source, historical42, temp = source_worktree(args.repository)
    try:
        verify_source_code(source)
        scanner_wrapper, ledger_mod = load_source_modules(source, historical42)
        scanner = scanner_wrapper.mod
        scanner.REVIEW_PROOF_ARTIFACT_NAME = CONTROL_ARTIFACT_NAME
        ledger = validate_source_ledger(ledger_mod, historical42)
        tracked = tracked_tree_scan(evidence, ledger)
        seeds = {int(x) for x in ledger["candidateSeeds"]}
        context, stable_sha, fence, post_counts = scanner.collect_stable(
            args.repository, 60, args.token, args.run_id, seeds, "authorization-control"
        )
        report = scanner.evaluate_context(
            context,
            seeds,
            args.run_id,
            stable_double_enumeration_passed=True,
            stable_context_sha256_value=stable_sha,
            audit_mode="authorization-control",
            expected_branch_name=CONTROL_BRANCH,
            expected_repo_head=args.head,
            snapshot_fence=fence,
            post_fence_arrival_counts=post_counts,
        )
        required = {
            "candidateSeedCount": 72,
            "repositoryGlobalCollisionCount": 0,
            "repositoryGlobalCollisionSurfaceScanPassed": True,
            "repositoryGlobalDoubleEnumerationStable": True,
            "repositoryGlobalEnumerationPassCount": 2,
            "auditedBranchHeadMatchesRepositoryHead": True,
            "repositoryGlobalPostFenceCandidateSeedCollisionCount": 0,
            "allStatePullRequestsInspected": True,
            "allStateIssuesInspected": True,
            "allRepositoryIssueCommentsInspected": True,
            "allRepositoryPullReviewCommentsInspected": True,
            "allRepositoryCommitCommentsInspected": True,
        }
        for key, value in required.items():
            require(report.get(key) == value, f"authorization-control global proof drift {key}={report.get(key)!r}")
        require(bool(report.get("repositoryGlobalStableContextSha256")) and bool(report.get("repositoryGlobalSnapshotFenceSha256")), "authorization-control snapshot hashes missing")
        require(branch_head(args.repository, CONTROL_BRANCH, args.token) == args.head, "control head moved during global scan")
        require(branch_head(args.repository, "main", args.token) == EXPECTED_MAIN, "main moved during global scan")
        require(not scanner.final_review_proof_artifacts(args.repository, args.token, args.run_id), "control proof artifact identity already exists outside current run")
    finally:
        cleanup_worktrees(source, historical42, temp)

    consumed45 = verify_consumed45(args.repository, args.token)
    installed = verify_installed_blobs(source_api["identity"])
    _, latest, candidate, observations = dynamic_ordinal(args.repository, args.token, args.run_id, source_api["receipt"], evidence)
    require(candidate == 46, "dynamic candidate is no longer ordinal46")
    _, post_tail = canonical_write_quiet_state(args.repository, args.token, args.head, pre_tail["controlWriteQuietBeginId"])
    require(branch_head(args.repository, "main", args.token) == EXPECTED_MAIN, "main moved before control receipt freeze")
    require(branch_head(args.repository, CONTROL_BRANCH, args.token) == args.head, "control head moved before control receipt freeze")

    proposal = {
        "schemaVersion": 1,
        "status": "PROPOSED_AVPS_V2_POSTCONSUMPTION_SUCCESSOR_AUTHORIZATION_NOT_ALLOCATED_NOT_RESERVED_NOT_DISPATCHED",
        "proposalOnly": True,
        "scientificOrdinal": candidate,
        "latestPriorConsumedOrDispatchedScientificOrdinal": latest,
        "authorizationBranch": source_api["receipt"]["authorizationBranch"],
        "dispatchBranch": source_api["receipt"]["dispatchBranch"],
        "executionKey": source_api["receipt"]["executionKey"],
        "proposedPublisherWorkflowPath": source_api["receipt"]["proposedPublisherWorkflowPath"],
        "proposedScienceWorkflowPath": source_api["receipt"]["proposedScienceWorkflowPath"],
        "proposedRuntimeDirectory": source_api["receipt"]["proposedRuntimeDirectory"],
        "controlBranch": CONTROL_BRANCH,
        "controlHead": args.head,
        "controlPr": args.pr,
        "exactMainParent": EXPECTED_MAIN,
        "sourcePreauthorizationPr": SOURCE_PR,
        "sourcePreauthorizationHead": SOURCE_HEAD,
        "sourcePreauthorizationRun": SOURCE_RUN,
        "sourcePreauthorizationJob": SOURCE_JOB,
        "sourcePreauthorizationArtifact": SOURCE_ARTIFACT,
        "sourcePreauthorizationArtifactDigest": SOURCE_ARTIFACT_DIGEST,
        "sourcePreauthorizationReceiptSha256": SOURCE_RECEIPT_SHA,
        "candidateSeedNamespace": source_api["receipt"]["candidateSeedNamespace"],
        "candidateSeedCount": 72,
        "candidateSeedCanonicalSha256": SOURCE_SEED_CANONICAL,
        "candidateRowsCanonicalSha256": SOURCE_ROWS_CANONICAL,
        "consumedOrdinal45SeedCanonicalSha256": source_api["receipt"]["consumedOrdinal45SeedCanonicalSha256"],
        "repositoryGlobalStableContextSha256": report["repositoryGlobalStableContextSha256"],
        "repositoryGlobalSnapshotFenceSha256": report["repositoryGlobalSnapshotFenceSha256"],
        "repositoryGlobalCollisionCount": 0,
        "repositoryGlobalDoubleEnumerationStable": True,
        "repositoryGlobalPostFenceCandidateSeedCollisionCount": 0,
        "trackedTreeExternalCollisionCount": tracked["trackedTreeExternalCollisionCount"],
        "consumedOrdinal45PublisherRun": OLD_PUBLISHER_RUN,
        "consumedOrdinal45ScienceRun": OLD_SCIENCE_RUN,
        "consumedOrdinal45AuthorizationHead": OLD_AUTH_HEAD,
        "sourceInstalledPublisherWorkflowBlobSha1": source_api["identity"]["sourceInstalledPublisherWorkflowBlobSha1"],
        "sourceInstalledScienceWorkflowBlobSha1": source_api["identity"]["sourceInstalledScienceWorkflowBlobSha1"],
        "sourceRuntimeAdapterBlobSha1": source_api["identity"]["sourceRuntimeAdapterBlobSha1"],
        "sourceRuntimeExecutorBlobSha1": source_api["identity"]["sourceRuntimeExecutorBlobSha1"],
        "sourceRuntimeAggregatorBlobSha1": source_api["identity"]["sourceRuntimeAggregatorBlobSha1"],
        "caseCount": source_api["identity"]["caseCount"],
        "commonRandomNumberGroupCount": source_api["identity"]["commonRandomNumberGroupCount"],
        "statesPerGroup": source_api["identity"]["statesPerGroup"],
        "photonHistoriesPerCase": source_api["identity"]["photonHistoriesPerCase"],
        "lockedLibRadtranPackage": source_api["identity"]["lockedLibRadtranPackage"],
        "uvspecSha256": source_api["identity"]["uvspecSha256"],
        "officialOptpropArchiveSha256": source_api["identity"]["officialOptpropArchiveSha256"],
        "fourAliasDataTreeSha256": source_api["identity"]["fourAliasDataTreeSha256"],
        "laterOneFileAuthorizationChildRequired": True,
        "independentArtifactReadbackClassificationRequired": True,
        "scientificOrdinalAllocated": False,
        "ordinalReserved": False,
        "authorizationRefCreated": False,
        "authorizationCreated": False,
        "candidateSeedsAppliedToCases": False,
        "seedUniverseConsumed": False,
        "dispatchCreated": False,
        "publisherInvoked": False,
        "scienceInvoked": False,
        "scientificExecutionAuthorized": False,
        "solverExecutionAuthorized": False,
        "scientificRuntime": False,
        "solverExecuted": False,
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
    proposal["contentSha256"] = canonical_sha256(proposal)
    write_json(evidence / "authorization-proposal.json", proposal)
    write_json(evidence / "repository-global-authorization-control-scan.json", report)
    write_json(evidence / "consumed-ordinal45-readback.json", consumed45)
    write_json(evidence / "installed-byte-readback.json", installed)
    write_json(evidence / "control-write-quiet-pre.json", pre_tail)
    write_json(evidence / "control-write-quiet-post.json", post_tail)

    receipt = {
        "schemaVersion": 1,
        "status": "PASS_AVPS_V2_POSTCONSUMPTION_SUCCESSOR_AUTHORIZATION_CONTROL_PROPOSAL_ONLY_NOT_ALLOCATED_NOT_RESERVED_NOT_DISPATCHED",
        "controlBranch": CONTROL_BRANCH,
        "controlHead": args.head,
        "controlPr": args.pr,
        "controlRunId": args.run_id,
        "controlRunAttempt": args.run_attempt,
        "exactMainParent": EXPECTED_MAIN,
        "writeQuietBeginCommentId": pre_tail["controlWriteQuietBeginId"],
        "sourcePreauthorizationHead": SOURCE_HEAD,
        "sourcePreauthorizationRun": SOURCE_RUN,
        "sourcePreauthorizationArtifact": SOURCE_ARTIFACT,
        "sourcePreauthorizationArtifactDigest": SOURCE_ARTIFACT_DIGEST,
        "sourcePreauthorizationReceiptSha256": SOURCE_RECEIPT_SHA,
        "candidateSeedCount": 72,
        "candidateSeedCanonicalSha256": SOURCE_SEED_CANONICAL,
        "candidateRowsCanonicalSha256": SOURCE_ROWS_CANONICAL,
        "latestPriorConsumedOrDispatchedScientificOrdinal": latest,
        "scientificOrdinalProposed": candidate,
        "authorizationBranchProposed": source_api["receipt"]["authorizationBranch"],
        "dispatchBranchProposed": source_api["receipt"]["dispatchBranch"],
        "repositoryGlobalCollisionCount": 0,
        "repositoryGlobalDoubleEnumerationStable": True,
        "repositoryGlobalStableContextSha256": report["repositoryGlobalStableContextSha256"],
        "repositoryGlobalSnapshotFenceSha256": report["repositoryGlobalSnapshotFenceSha256"],
        "authorizationProposalFileSha256": file_sha256(evidence / "authorization-proposal.json"),
        "stressPassed": True,
        "exactHeadGenericAttempt1Passed": True,
        "scientificOrdinalAllocated": False,
        "ordinalReserved": False,
        "authorizationRefCreated": False,
        "authorizationCreated": False,
        "candidateSeedsAppliedToCases": False,
        "seedUniverseConsumed": False,
        "dispatchCreated": False,
        "publisherInvoked": False,
        "scienceInvoked": False,
        "scientificExecutionAuthorized": False,
        "solverExecutionAuthorized": False,
        "scientificRuntime": False,
        "solverExecuted": False,
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
    write_json(evidence / "authorization-control-receipt.json", receipt)
    print(json.dumps(receipt, sort_keys=True))


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("stress", "await-generic", "control"), required=True)
    ap.add_argument("--repository", required=True)
    ap.add_argument("--token", required=True)
    ap.add_argument("--pr", type=int, required=True)
    ap.add_argument("--run-id", type=int, required=True)
    ap.add_argument("--run-attempt", type=int, required=True)
    ap.add_argument("--event-name", required=True)
    ap.add_argument("--event-action", required=True)
    ap.add_argument("--branch", required=True)
    ap.add_argument("--head", required=True)
    ap.add_argument("--base", required=True)
    ap.add_argument("--evidence-dir", type=Path, required=True)
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    if args.mode == "stress":
        stress(args)
    elif args.mode == "await-generic":
        await_generic(args)
    elif args.mode == "control":
        control(args)
    else:
        raise Refusal("unknown mode")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
