#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    from twilight_surrogate_tier1_ordinal2_execution_guard import (
        AUTHORIZATION_ORDINAL,
        EXECUTION_KEY,
        GuardError,
        build_expected_authorization,
        dump,
        load,
        validate_evidence,
    )
except ModuleNotFoundError:
    import importlib.util
    _guard_path = Path(__file__).with_name(
        "twilight_surrogate_tier1_ordinal2_execution_guard.py"
    )
    _spec = importlib.util.spec_from_file_location("ordinal2_execution_guard", _guard_path)
    if _spec is None or _spec.loader is None:
        raise
    _guard = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_guard)
    AUTHORIZATION_ORDINAL = _guard.AUTHORIZATION_ORDINAL
    EXECUTION_KEY = _guard.EXECUTION_KEY
    GuardError = _guard.GuardError
    build_expected_authorization = _guard.build_expected_authorization
    dump = _guard.dump
    load = _guard.load
    validate_evidence = _guard.validate_evidence

STAGE_ID = "twilight-surrogate-tier-1-ordinal2-authorization-proposal-v1"


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def build(
    root: Path,
    template_path: Path,
    active_path: Path,
    evidence_dir: Path,
    metadata_dir: Path,
    comments_path: Path,
) -> dict[str, Any]:
    template = load(root / template_path)
    active = load(root / active_path)
    if active != template:
        raise GuardError("active ordinal-2 authorization differs from disabled template")
    evidence = validate_evidence(evidence_dir, metadata_dir, comments_path)
    parent = git(root, "rev-parse", "HEAD")
    authorization = build_expected_authorization(root, template, evidence, parent)
    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "PROPOSAL_ONLY_NOT_AUTHORIZATION",
        "executionAuthorizedByProposal": False,
        "scientificExecution": False,
        "authorizationPath": active_path.as_posix(),
        "exactAuthorizationParentCommit": parent,
        "executionKey": EXECUTION_KEY,
        "authorizationOrdinal": AUTHORIZATION_ORDINAL,
        "caseCount": 96,
        "geometryCount": 48,
        "configuredMcPhotonsSum": 6_960_000_000,
        "freshSeedCount": 96,
        "sourceSeedOverlapCount": 0,
        "authorization": authorization,
        "boundary": "proposal only; no authorization commit, workflow dispatch, syntax check, solver execution, model fitting, Tier-2, or production use",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--authorization-template", type=Path, required=True)
    parser.add_argument("--active-authorization", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--metadata-dir", type=Path, required=True)
    parser.add_argument("--issue-comments", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = build(
            args.repository_root.resolve(),
            args.authorization_template,
            args.active_authorization,
            args.evidence_dir,
            args.metadata_dir,
            args.issue_comments,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump(result))
        print(dump(result), end="")
        return 0
    except Exception as exc:
        refusal = {"schemaVersion": 1, "stageId": STAGE_ID, "status": "REFUSED", "reason": str(exc)}
        print(json.dumps(refusal, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
