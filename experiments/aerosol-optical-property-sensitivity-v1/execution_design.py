from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
STAGE_DIR = Path(__file__).resolve().parent
PROOF_PATH = ROOT / "evidence/aerosol-optical-property-sensitivity-v1/seed-freshness-proof.json"


class Refusal(RuntimeError):
    pass


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise Refusal(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def build_review_execution_design() -> dict[str, Any]:
    review_core = _load("aops_review_core_for_execution_design", STAGE_DIR / "review_core.py")
    seed_mod = _load("aops_seed_ledger_for_execution_design", STAGE_DIR / "seed_ledger.py")
    ledger = seed_mod.validate_ledger()
    proof = json.loads(PROOF_PATH.read_text())
    if proof.get("status") != "PASS_CANDIDATE_SEEDS_REVIEW_FRESHNESS_NOT_AUTHORIZED":
        raise Refusal("candidate seed review freshness proof missing")
    if proof.get("candidateSeedCanonicalSha256") != ledger.get("candidateSeedCanonicalSha256"):
        raise Refusal("seed proof/ledger canonical hash drift")
    if proof.get("candidateRowsCanonicalSha256") != ledger.get("candidateRowsCanonicalSha256"):
        raise Refusal("seed proof/row canonical hash drift")
    if proof.get("authorizationTimeRecheckStillRequired") is not True:
        raise Refusal("authorization-time seed recheck requirement was lost")
    if proof.get("repositoryGlobalCollisionCount") != 0 or proof.get("trackedTreeExternalCollisionCount") != 0:
        raise Refusal("candidate seed freshness proof contains collision")

    seed_rows = seed_mod.derive_rows()
    seed_by_group_key = {(row["analysisCellId"], int(row["replicate"])): int(row["seed"]) for row in seed_rows}
    if len(seed_by_group_key) != 72:
        raise Refusal("seed mapping cardinality drift")

    groups = []
    for row in review_core.group_skeletons():
        key = (str(row["analysisCellId"]), int(row["replicate"]))
        if key not in seed_by_group_key:
            raise Refusal(f"candidate seed missing for {key}")
        groups.append({
            **row,
            "seed": seed_by_group_key[key],
            "seedStatus": "CANDIDATE_FRESHNESS_PROVEN_REVIEW_ONLY",
            "renderable": False,
            "executionAuthorized": False,
        })

    group_seed = {str(row["groupId"]): int(row["seed"]) for row in groups}
    cases = []
    for row in review_core.case_skeletons():
        seed = group_seed.get(str(row["groupId"]))
        if seed is None:
            raise Refusal(f"group seed missing for {row['groupId']}")
        cases.append({
            **row,
            "seed": seed,
            "seedStatus": "CANDIDATE_FRESHNESS_PROVEN_REVIEW_ONLY",
            "renderable": False,
            "executionAuthorized": False,
        })

    if len(groups) != 72 or len(cases) != 360:
        raise Refusal("review execution design cardinality drift")
    by_group: dict[str, list[dict[str, Any]]] = {}
    for case in cases:
        by_group.setdefault(str(case["groupId"]), []).append(case)
    if len(by_group) != 72:
        raise Refusal("review execution design group count drift")
    for group_id, members in by_group.items():
        if len(members) != 5 or len({int(m["seed"]) for m in members}) != 1:
            raise Refusal(f"CRN seed-sharing drift: {group_id}")
        if any(m.get("renderable") is not False or m.get("executionAuthorized") is not False for m in members):
            raise Refusal(f"review design crossed execution boundary: {group_id}")

    result = {
        "schemaVersion": 1,
        "stageId": "aerosol-optical-property-sensitivity-v1-execution-design",
        "status": "REVIEW_ONLY_SEEDED_DESIGN_NON_RENDERABLE_NOT_AUTHORIZED",
        "candidateSeedLedgerCanonicalSha256": ledger["candidateSeedCanonicalSha256"],
        "candidateRowsCanonicalSha256": ledger["candidateRowsCanonicalSha256"],
        "seedFreshnessProofAuditedHead": proof["auditedHead"],
        "authorizationTimeSeedRecheckRequired": True,
        "analysisCellCount": 24,
        "groupCount": 72,
        "caseCount": 360,
        "statesPerGroup": 5,
        "groups": groups,
        "cases": cases,
        "scientificOrdinalAllocated": False,
        "authorizationCreated": False,
        "dispatchCreated": False,
        "scientificExecutionAuthorized": False,
        "solverExecutionAuthorized": False,
        "resultOpeningAuthorized": False,
    }
    result["canonicalDesignSha256"] = canonical_sha256(result)
    return result


if __name__ == "__main__":
    d = build_review_execution_design()
    print(json.dumps({
        "status": d["status"],
        "analysisCellCount": d["analysisCellCount"],
        "groupCount": d["groupCount"],
        "caseCount": d["caseCount"],
        "canonicalDesignSha256": d["canonicalDesignSha256"],
    }, sort_keys=True))
