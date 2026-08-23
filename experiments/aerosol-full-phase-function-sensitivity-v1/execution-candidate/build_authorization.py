from __future__ import annotations

import argparse
import importlib.util
import json
import re
from pathlib import Path
from typing import Any

STAGE = "aerosol-full-phase-function-sensitivity-v1"
SHA40 = re.compile(r"^[0-9a-f]{40}$")


class BuildRefusal(RuntimeError):
    pass


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise BuildRefusal(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build(
    root: Path,
    parent_main: str,
    scientific_ordinal: int,
    preauthorization_freshness: dict[str, Any],
    seed_authorization_proof: dict[str, Any],
) -> dict[str, Any]:
    if SHA40.fullmatch(parent_main or "") is None:
        raise BuildRefusal("parent main SHA invalid")
    if isinstance(scientific_ordinal, bool) or not isinstance(scientific_ordinal, int) or scientific_ordinal <= 0:
        raise BuildRefusal("scientific ordinal invalid")
    stage = root / "experiments" / STAGE
    execd = stage / "execution-candidate"
    freshness = _load("afpf_freshness_for_build_authorization", execd / "freshness.py")
    guard = _load("afpf_authorization_guard_for_builder", execd / "authorization_guard.py")
    design_mod = _load("afpf_execution_design_for_builder", stage / "execution_design.py")

    freshness.validate_preauthorization(preauthorization_freshness, scientific_ordinal)
    design = design_mod.build_review_execution_design(seed_authorization_proof, parent_main)
    auth = {
        "schemaVersion": 1,
        "stageId": STAGE,
        "status": "AUTHORIZED_PENDING_SEPARATE_DISPATCH",
        "scientificOrdinal": scientific_ordinal,
        "authorizationBranch": freshness.authorization_branch(scientific_ordinal),
        "dispatchBranch": freshness.dispatch_branch(scientific_ordinal),
        "executionKey": freshness.execution_key(scientific_ordinal),
        "exactAuthorizationParentCommit": parent_main,
        "reviewPackageMainSha": parent_main,
        "exactAuthorizationCommit": None,
        "authorizationTimeSeedProofRawSha256": guard.seed_proof_raw_sha256(seed_authorization_proof),
        "candidateSeedCanonicalSha256": design["candidateSeedCanonicalSha256"],
        "candidateRowsCanonicalSha256": design["candidateRowsCanonicalSha256"],
        "executionDesignCanonicalSha256": design["canonicalDesignSha256"],
        "augmentedDataTreeSha256": "5d8bbf8e6b91ec3d405dee36f21a94afbb6e5ec6cd67da2dd5dd541738199d80",
        "officialOptpropArchiveSha256": "11daa1f1f4be0fd4ddf7e881ec2005498049674a1540d37b4b1e8f5e16052c7e",
        "byteBindings": guard.build_bindings(root),
        "scientificExecutionAuthorized": True,
        "solverExecutionAuthorized": True,
        "dispatchAuthorized": False,
        "resultOpeningAuthorized": False,
        "automaticDispatch": False,
        "consumed": False,
        "workflowRunAttemptRequired": 1,
        "githubRerunAllowed": False,
        "retryAllowed": False,
        "resumeAllowed": False,
    }
    guard.validate_enabled_document(root, auth, parent_main, seed_authorization_proof)
    return auth


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--parent-main", required=True)
    parser.add_argument("--scientific-ordinal", type=int, required=True)
    parser.add_argument("--freshness", type=Path, required=True)
    parser.add_argument("--seed-authorization-proof", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    auth = build(
        args.repository_root,
        args.parent_main,
        args.scientific_ordinal,
        json.loads(args.freshness.read_text()),
        json.loads(args.seed_authorization_proof.read_text()),
    )
    args.output.write_text(json.dumps(auth, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
