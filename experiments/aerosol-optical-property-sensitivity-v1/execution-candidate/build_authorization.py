from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
from pathlib import Path
from typing import Any


STAGE = "aerosol-optical-property-sensitivity-v1"
SHA40 = re.compile(r"^[0-9a-f]{40}$")


class BuildRefusal(RuntimeError):
    pass


def raw_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise BuildRefusal(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build(repository_root: Path, seed_proof_path: Path, main_sha: str, ordinal: int) -> dict[str, Any]:
    if SHA40.fullmatch(main_sha) is None:
        raise BuildRefusal("main SHA invalid")
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal <= 0:
        raise BuildRefusal("scientific ordinal invalid")
    stage = repository_root / "experiments" / STAGE
    evidence = repository_root / "evidence" / STAGE
    exec_dir = stage / "execution-candidate"
    seed_proof = json.loads(seed_proof_path.read_text())
    frozen_auth = load("aops_builder_frozen_auth", exec_dir / "authorization_guard.py")
    frozen_auth.validate_seed_authorization_proof(seed_proof)
    if seed_proof.get("auditedMainHead") != main_sha:
        raise BuildRefusal("seed authorization proof is not bound to exact main")
    design_mod = load("aops_builder_design", stage / "execution_design.py")
    design = design_mod.build_review_execution_design()
    freshness = load("aops_builder_freshness", exec_dir / "freshness.py")
    paths = {
        "freeze": evidence / "review-freeze.json",
        "executionContract": stage / "execution-contract.review.json",
        "adapter": stage / "adapter.py",
        "executor": exec_dir / "executor.py",
        "aggregator": exec_dir / "aggregate_results.py",
        "analysis": stage / "analysis.py",
        "analysisContract": stage / "analysis-contract.v1.json",
        "levelBAnalysis": stage / "level_b_analysis.mjs",
        "authorizationGuard": exec_dir / "authorization_guard.py",
        "freshness": exec_dir / "freshness.py",
        "transportContract": stage / "transport-contract.v1.json",
    }
    for name, path in paths.items():
        if not path.is_file():
            raise BuildRefusal(f"required authorization binding path missing: {name}: {path}")
    doc = {
        "schemaVersion": 1,
        "stageId": f"{STAGE}-authorization",
        "status": "AUTHORIZED_PENDING_SEPARATE_DISPATCH",
        "repositoryFullName": "search-maker/twilight-mystic-experiments",
        "enabled": True,
        "scientificExecutionAuthorized": True,
        "solverExecutionAuthorized": True,
        "dispatchAuthorized": False,
        "resultOpeningAuthorized": False,
        "automaticDispatch": False,
        "consumed": False,
        "executionKey": freshness.execution_key(ordinal),
        "scientificOrdinal": ordinal,
        "authorizationBranch": freshness.authorization_branch(ordinal),
        "dispatchBranch": freshness.dispatch_branch(ordinal),
        "exactAuthorizationParentCommit": main_sha,
        "exactAuthorizationCommit": None,
        "reviewPackageMainSha": main_sha,
        "reviewFreezeRawSha256": raw_sha(paths["freeze"]),
        "executionDesignCanonicalSha256": design["canonicalDesignSha256"],
        "executionContractRawSha256": raw_sha(paths["executionContract"]),
        "adapterRawSha256": raw_sha(paths["adapter"]),
        "executorRawSha256": raw_sha(paths["executor"]),
        "aggregatorRawSha256": raw_sha(paths["aggregator"]),
        "analysisRawSha256": raw_sha(paths["analysis"]),
        "analysisContractRawSha256": raw_sha(paths["analysisContract"]),
        "levelBAnalysisRawSha256": raw_sha(paths["levelBAnalysis"]),
        "authorizationGuardRawSha256": raw_sha(paths["authorizationGuard"]),
        "freshnessGuardRawSha256": raw_sha(paths["freshness"]),
        "authorizationTimeSeedProofRawSha256": raw_sha(seed_proof_path),
        "candidateSeedCanonicalSha256": seed_proof["candidateSeedCanonicalSha256"],
        "candidateRowsCanonicalSha256": seed_proof["candidateRowsCanonicalSha256"],
        "runtimeLockRawSha256": "3b5fbec964642b04c73a6423b3355dbcc4ba5e84f9614f6d74420491bacc20c5",
        "transportContractRawSha256": raw_sha(paths["transportContract"]),
        "githubRerunAllowed": False,
        "retryAllowed": False,
        "resumeAllowed": False,
        "adaptiveCaseAdditionAllowed": False,
        "postResultRuleChangeAllowed": False,
        "r8ModificationAuthorized": False,
    }
    return doc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--seed-proof", type=Path, required=True)
    parser.add_argument("--main-sha", required=True)
    parser.add_argument("--ordinal", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    doc = build(args.repository_root, args.seed_proof, args.main_sha, args.ordinal)
    args.output.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
