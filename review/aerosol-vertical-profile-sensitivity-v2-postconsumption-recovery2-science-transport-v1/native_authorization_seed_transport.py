from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


class Refusal(RuntimeError):
    pass


def run(*args: str, cwd: Path | None = None) -> str:
    p = subprocess.run(args, cwd=cwd, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return p.stdout.strip()


def git_blob_sha1(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise Refusal(f"cannot import authorization-bound seed ledger: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def inside(root: Path, relative: str) -> Path:
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts:
        raise Refusal("seed-ledger path must be repository-relative and may not contain '..'")
    root_r = root.resolve()
    path = (root_r / rel).resolve()
    try:
        path.relative_to(root_r)
    except ValueError as exc:
        raise Refusal("seed-ledger path escaped authorization worktree") from exc
    if not path.is_file():
        raise Refusal(f"seed-ledger native path is missing: {relative}")
    return path


def add_detached_worktree(repo: Path, destination: Path, head: str) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    run("git", "worktree", "add", "--detach", str(destination), head, cwd=repo)
    observed = run("git", "rev-parse", "HEAD", cwd=destination)
    if observed != head:
        raise Refusal(f"detached worktree head drift: {observed} != {head}")


def remove_worktree(repo: Path, destination: Path) -> None:
    if destination.exists():
        subprocess.run(["git", "worktree", "remove", "--force", str(destination)], cwd=repo, check=False)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", type=Path, default=Path("."))
    ap.add_argument("--authorization-head", required=True)
    ap.add_argument("--authorization-parent", required=True)
    ap.add_argument("--authorization-ledger-path", required=True)
    ap.add_argument("--authorization-ledger-blob", required=True)
    ap.add_argument("--candidate-seed-sha256", required=True)
    ap.add_argument("--candidate-rows-sha256", required=True)
    ap.add_argument("--historical-head", required=True)
    ap.add_argument("--historical-ledger-path", required=True)
    ap.add_argument("--historical-ledger-blob", required=True)
    ap.add_argument("--historical-env", default="AVPS_ORDINAL42_LEDGER_PATH")
    ap.add_argument("--work-root", type=Path, required=True)
    ap.add_argument("--output-ledger", type=Path, required=True)
    ap.add_argument("--output-context", type=Path, required=True)
    args = ap.parse_args()

    repo = args.repo_root.resolve()
    if run("git", "rev-parse", "--show-toplevel", cwd=repo) != str(repo):
        raise Refusal("repo-root must be the exact Git worktree root")

    auth_worktree = args.work_root.resolve() / "authorization-native"
    historical_worktree = args.work_root.resolve() / "historical-native"
    args.work_root.resolve().mkdir(parents=True, exist_ok=True)

    original_env = os.environ.get(args.historical_env)
    try:
        add_detached_worktree(repo, auth_worktree, args.authorization_head)
        parents = run("git", "rev-list", "--parents", "-n", "1", "HEAD", cwd=auth_worktree).split()
        if len(parents) != 2 or parents[1] != args.authorization_parent:
            raise Refusal(f"authorization parent drift: {parents[1:]!r}")

        add_detached_worktree(repo, historical_worktree, args.historical_head)
        auth_path = inside(auth_worktree, args.authorization_ledger_path)
        historical_path = inside(historical_worktree, args.historical_ledger_path)

        for worktree, relative, path, expected_blob, label in (
            (auth_worktree, args.authorization_ledger_path, auth_path, args.authorization_ledger_blob, "authorization"),
            (historical_worktree, args.historical_ledger_path, historical_path, args.historical_ledger_blob, "historical"),
        ):
            run("git", "ls-files", "--error-unmatch", relative, cwd=worktree)
            git_blob = run("git", "hash-object", relative, cwd=worktree)
            raw_blob = git_blob_sha1(path)
            if git_blob != expected_blob or raw_blob != expected_blob:
                raise Refusal(f"{label} seed-ledger blob drift: git={git_blob} raw={raw_blob} expected={expected_blob}")

        os.environ[args.historical_env] = str(historical_path)
        module = load_module(auth_path, "avps_recovery_native_authorization_seed_ledger")
        if not hasattr(module, "validate_ledger"):
            raise Refusal("authorization-bound seed ledger has no validate_ledger()")
        ledger: Any = module.validate_ledger()
        if not isinstance(ledger, dict):
            raise Refusal("validate_ledger() did not return an object")
        if ledger.get("candidateSeedCount") != 72:
            raise Refusal("candidate seed cardinality drift")
        if ledger.get("candidateSeedCanonicalSha256") != args.candidate_seed_sha256:
            raise Refusal("candidate seed canonical identity drift")
        if ledger.get("candidateRowsCanonicalSha256") != args.candidate_rows_sha256:
            raise Refusal("candidate rows canonical identity drift")
        if ledger.get("overlapWithConsumedOrdinal41SeedCount") != 0:
            raise Refusal("candidate seeds overlap consumed ordinal 41")
        if ledger.get("overlapWithConsumedOrdinal42SeedCount") != 0:
            raise Refusal("candidate seeds overlap consumed ordinal 42")
        if ledger.get("historicalOrdinal42LedgerValidatedAtNativePath") is not True:
            raise Refusal("authorization ledger did not prove native historical ordinal-42 validation")

        args.output_ledger.parent.mkdir(parents=True, exist_ok=True)
        args.output_context.parent.mkdir(parents=True, exist_ok=True)
        args.output_ledger.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n")
        context = {
            "schemaVersion": 1,
            "status": "PASS_NATIVE_AUTHORIZATION_SEED_TRANSPORT_NO_RELOCATION",
            "authorizationHead": args.authorization_head,
            "authorizationParent": args.authorization_parent,
            "authorizationLedgerPath": args.authorization_ledger_path,
            "authorizationLedgerGitBlobSha1": args.authorization_ledger_blob,
            "authorizationLedgerValidatedAtNativePath": True,
            "historicalHead": args.historical_head,
            "historicalLedgerPath": args.historical_ledger_path,
            "historicalLedgerGitBlobSha1": args.historical_ledger_blob,
            "historicalDependencyValidatedAtNativePath": True,
            "historicalEnvironmentVariable": args.historical_env,
            "candidateSeedCount": 72,
            "candidateSeedCanonicalSha256": args.candidate_seed_sha256,
            "candidateRowsCanonicalSha256": args.candidate_rows_sha256,
            "relocatedBeforeValidation": False,
            "scientificRuntimeSetupPerformed": False,
            "solverExecutionPerformed": False,
            "resultOpeningPerformed": False,
        }
        args.output_context.write_text(json.dumps(context, indent=2, sort_keys=True) + "\n")
        return 0
    finally:
        if original_env is None:
            os.environ.pop(args.historical_env, None)
        else:
            os.environ[args.historical_env] = original_env
        remove_worktree(repo, auth_worktree)
        remove_worktree(repo, historical_worktree)


if __name__ == "__main__":
    raise SystemExit(main())
