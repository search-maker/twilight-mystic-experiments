from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

STAGE_DIR = Path(__file__).resolve().parent
SEED_DOMAIN_MAX_EXCLUSIVE = 2_147_483_647


class TransportRefusal(RuntimeError):
    pass


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise TransportRefusal(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def build_seedless_transport_design() -> dict[str, Any]:
    review_core = _load("afpf_review_core_for_transport", STAGE_DIR / "review_core.py")
    source = review_core.review_manifest()
    if source.get("status") != "REVIEW_ONLY_CASE_SKELETONS_NON_RENDERABLE_NO_SEEDS":
        raise TransportRefusal("review manifest status drift")
    if source.get("analysisCellCount") != 24 or source.get("groupCount") != 72 or source.get("caseCount") != 360:
        raise TransportRefusal("review manifest cardinality drift")
    if source.get("candidateSeedsAllocated") is not False:
        raise TransportRefusal("review manifest unexpectedly contains candidate seeds")
    groups = []
    for row in source["groups"]:
        if row.get("seed") is not None or row.get("seedStatus") != "UNALLOCATED_REVIEW_ONLY":
            raise TransportRefusal("seedless group drift")
        groups.append({**row, "renderable": False, "executionAuthorized": False})
    cases = []
    for row in source["cases"]:
        if row.get("seed") is not None or row.get("renderable") is not False or row.get("executionAuthorized") is not False:
            raise TransportRefusal("seedless case crossed transport boundary")
        cases.append(dict(row))
    result = {
        "schemaVersion": 1,
        "stageId": "aerosol-full-phase-function-sensitivity-v1-execution-transport-design",
        "status": "REVIEW_ONLY_EXECUTION_TRANSPORT_NON_RENDERABLE_NO_SEEDS",
        "analysisCellCount": 24,
        "groupCount": 72,
        "caseCount": 360,
        "statesPerGroup": 5,
        "configuredPhotonHistories": source["configuredPhotonHistories"],
        "seedNamespace": source["seedNamespace"],
        "groups": groups,
        "cases": cases,
        "candidateSeedsAllocated": False,
        "candidateSeedFreshnessProven": False,
        "scientificOrdinalAllocated": False,
        "authorizationCreated": False,
        "dispatchCreated": False,
        "scientificExecutionAuthorized": False,
        "solverExecutionAuthorized": False,
        "resultOpeningAuthorized": False,
    }
    result["canonicalDesignSha256"] = canonical_sha256(result)
    return result


def bind_unproven_candidate_seed_map(seed_by_group: dict[str, int]) -> dict[str, Any]:
    """Bind a future candidate seed map without claiming freshness or authorization.

    This function deliberately does not derive seeds. A later seed-review stage must supply
    an exact 72-group map and separately prove repository-global freshness before any design
    may acquire the future execution status expected by the executor.
    """
    seedless = build_seedless_transport_design()
    expected_group_ids = {str(row["groupId"]) for row in seedless["groups"]}
    if set(seed_by_group) != expected_group_ids:
        raise TransportRefusal("candidate seed map must cover the exact 72-group universe")
    values = list(seed_by_group.values())
    if any(isinstance(v, bool) or not isinstance(v, int) or not 0 < v < SEED_DOMAIN_MAX_EXCLUSIVE for v in values):
        raise TransportRefusal("candidate seed map contains invalid seed")
    if len(set(values)) != 72:
        raise TransportRefusal("candidate group seeds must be unique")

    groups = []
    for row in seedless["groups"]:
        seed = int(seed_by_group[str(row["groupId"])])
        groups.append({
            **row,
            "seed": seed,
            "seedStatus": "CANDIDATE_BOUND_FRESHNESS_NOT_YET_PROVEN",
            "renderable": False,
            "executionAuthorized": False,
        })
    group_seed = {str(row["groupId"]): int(row["seed"]) for row in groups}
    cases = []
    for row in seedless["cases"]:
        seed = group_seed[str(row["groupId"])]
        cases.append({
            **row,
            "seed": seed,
            "seedStatus": "CANDIDATE_BOUND_FRESHNESS_NOT_YET_PROVEN",
            "renderable": False,
            "executionAuthorized": False,
        })
    by_group: dict[str, list[dict[str, Any]]] = {}
    for row in cases:
        by_group.setdefault(str(row["groupId"]), []).append(row)
    if len(by_group) != 72:
        raise TransportRefusal("seed-bound group count drift")
    for group_id, members in by_group.items():
        if len(members) != 5 or len({int(row["seed"]) for row in members}) != 1:
            raise TransportRefusal(f"CRN seed-sharing drift: {group_id}")
        if any(row.get("renderable") is not False or row.get("executionAuthorized") is not False for row in members):
            raise TransportRefusal(f"seed-bound review design crossed authorization boundary: {group_id}")

    result = {
        **seedless,
        "status": "REVIEW_ONLY_CANDIDATE_SEEDS_BOUND_FRESHNESS_NOT_PROVEN_NON_RENDERABLE",
        "groups": groups,
        "cases": cases,
        "candidateSeedsAllocated": True,
        "candidateSeedFreshnessProven": False,
    }
    result.pop("canonicalDesignSha256", None)
    result["canonicalDesignSha256"] = canonical_sha256(result)
    return result


def _without_seed_fields(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key not in {"seed", "seedStatus"}}


def validate_future_fresh_seeded_design(design: dict[str, Any]) -> None:
    seedless = build_seedless_transport_design()
    if design.get("stageId") != "aerosol-full-phase-function-sensitivity-v1-execution-transport-design":
        raise TransportRefusal("future seeded design stage drift")
    if design.get("status") != "CANDIDATE_SEEDED_DESIGN_FRESHNESS_PROVEN_REVIEW_ONLY":
        raise TransportRefusal("future seeded design freshness status missing")
    if design.get("analysisCellCount") != 24 or design.get("groupCount") != 72 or design.get("caseCount") != 360:
        raise TransportRefusal("future seeded design cardinality drift")
    if design.get("statesPerGroup") != 5:
        raise TransportRefusal("future seeded design state cardinality drift")
    if design.get("configuredPhotonHistories") != seedless["configuredPhotonHistories"]:
        raise TransportRefusal("future seeded design photon-budget drift")
    if design.get("seedNamespace") != seedless["seedNamespace"]:
        raise TransportRefusal("future seeded design seed-namespace drift")
    if design.get("candidateSeedsAllocated") is not True or design.get("candidateSeedFreshnessProven") is not True:
        raise TransportRefusal("future seeded design lacks freshness proof state")
    if design.get("authorizationTimeSeedRecheckRequired") is not True:
        raise TransportRefusal("authorization-time seed recheck requirement missing")
    if any(design.get(key) is not False for key in (
        "scientificOrdinalAllocated", "authorizationCreated", "dispatchCreated",
        "scientificExecutionAuthorized", "solverExecutionAuthorized", "resultOpeningAuthorized",
    )):
        raise TransportRefusal("future seeded review design crossed allocation/execution boundary")
    stored = design.get("canonicalDesignSha256")
    check = dict(design)
    check.pop("canonicalDesignSha256", None)
    if stored != canonical_sha256(check):
        raise TransportRefusal("future seeded design canonical hash mismatch")

    cases = design.get("cases")
    groups = design.get("groups")
    if not isinstance(cases, list) or len(cases) != 360 or not isinstance(groups, list) or len(groups) != 72:
        raise TransportRefusal("future seeded design rows missing")

    expected_groups = {str(row["groupId"]): row for row in seedless["groups"]}
    actual_groups = {str(row.get("groupId")): row for row in groups if isinstance(row, dict)}
    if len(actual_groups) != 72 or set(actual_groups) != set(expected_groups):
        raise TransportRefusal("future seeded design group identity universe drift")
    observed_group_seeds: set[int] = set()
    for group_id, expected in expected_groups.items():
        actual = actual_groups[group_id]
        if _without_seed_fields(actual) != _without_seed_fields(expected):
            raise TransportRefusal(f"future seeded group preregistered metadata drift: {group_id}")
        seed = actual.get("seed")
        if isinstance(seed, bool) or not isinstance(seed, int) or not 0 < seed < SEED_DOMAIN_MAX_EXCLUSIVE:
            raise TransportRefusal(f"future seeded group contains invalid seed: {group_id}")
        if actual.get("seedStatus") != "CANDIDATE_FRESHNESS_PROVEN_REVIEW_ONLY":
            raise TransportRefusal(f"future seeded group freshness status drift: {group_id}")
        observed_group_seeds.add(seed)
    if len(observed_group_seeds) != 72:
        raise TransportRefusal("future seeded group seeds must be unique")

    expected_cases = {str(row["caseId"]): row for row in seedless["cases"]}
    actual_cases = {str(row.get("caseId")): row for row in cases if isinstance(row, dict)}
    if len(actual_cases) != 360 or set(actual_cases) != set(expected_cases):
        raise TransportRefusal("future seeded design case identity universe drift")
    expected_state_ids = {
        "native-rural-ss",
        "opac-continental-average",
        "opac-maritime-clean",
        "opac-desert",
        "opac-desert-spheroids",
    }
    by_group: dict[str, list[dict[str, Any]]] = {}
    for case_id, expected in expected_cases.items():
        actual = actual_cases[case_id]
        if _without_seed_fields(actual) != _without_seed_fields(expected):
            raise TransportRefusal(f"future seeded case preregistered metadata drift: {case_id}")
        seed = actual.get("seed")
        if isinstance(seed, bool) or not isinstance(seed, int) or not 0 < seed < SEED_DOMAIN_MAX_EXCLUSIVE:
            raise TransportRefusal(f"future seeded case contains invalid seed: {case_id}")
        if actual.get("seedStatus") != "CANDIDATE_FRESHNESS_PROVEN_REVIEW_ONLY":
            raise TransportRefusal(f"future seeded case freshness status drift: {case_id}")
        by_group.setdefault(str(actual.get("groupId")), []).append(actual)
    if len(by_group) != 72:
        raise TransportRefusal("future seeded design group universe drift")
    for group_id, members in by_group.items():
        if len(members) != 5 or {str(row.get("stateId")) for row in members} != expected_state_ids:
            raise TransportRefusal(f"future seeded group state universe drift: {group_id}")
        seeds = {int(row["seed"]) for row in members}
        if len(seeds) != 1:
            raise TransportRefusal(f"future seeded CRN seed-sharing drift: {group_id}")
        group_seed = int(actual_groups[group_id]["seed"])
        if seeds != {group_seed}:
            raise TransportRefusal(f"future seeded group/case seed binding drift: {group_id}")


if __name__ == "__main__":
    value = build_seedless_transport_design()
    print(json.dumps({
        "status": value["status"],
        "analysisCellCount": value["analysisCellCount"],
        "groupCount": value["groupCount"],
        "caseCount": value["caseCount"],
        "candidateSeedsAllocated": value["candidateSeedsAllocated"],
        "canonicalDesignSha256": value["canonicalDesignSha256"],
    }, sort_keys=True))
