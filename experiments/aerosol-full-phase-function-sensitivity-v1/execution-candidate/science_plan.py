from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

STAGE = "aerosol-full-phase-function-sensitivity-v1"
DEPTHS = (2.0, 4.0, 6.0, 8.0)


class SciencePlanRefusal(RuntimeError):
    pass


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SciencePlanRefusal(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def build(repository_root: Path, seed_proof: dict[str, Any], authorization_parent: str) -> dict[str, Any]:
    stage = repository_root / "experiments" / STAGE
    design_mod = _load("afpf_execution_design_for_science_plan", stage / "execution_design.py")
    design = design_mod.build_review_execution_design(seed_proof, authorization_parent)
    cases = design.get("cases")
    if not isinstance(cases, list) or len(cases) != 360:
        raise SciencePlanRefusal("exact 360-case seeded design required")
    shards: dict[str, list[dict[str, str]]] = {}
    observed: set[str] = set()
    for dep in DEPTHS:
        rows = [row for row in cases if float(row.get("sunDepressionDeg")) == dep]
        if len(rows) != 90:
            raise SciencePlanRefusal(f"sun-depression {dep:g} shard must contain exactly 90 cases")
        matrix = []
        for row in sorted(rows, key=lambda item: str(item["caseId"])):
            case_id = str(row["caseId"])
            if case_id in observed:
                raise SciencePlanRefusal(f"case appears in more than one shard: {case_id}")
            observed.add(case_id)
            matrix.append({"caseId": case_id})
        shards[str(int(dep))] = matrix
    if len(observed) != 360 or observed != {str(row["caseId"]) for row in cases}:
        raise SciencePlanRefusal("four solar-depth shards do not equal the exact 360-case universe")
    plan = {
        "schemaVersion": 1,
        "stageId": f"{STAGE}-science-plan",
        "status": "EXACT_FOUR_90_CASE_SHARDS_REVIEW_DESIGN",
        "authorizationParent": authorization_parent,
        "designCanonicalSha256": design["canonicalDesignSha256"],
        "caseCount": 360,
        "groupCount": 72,
        "analysisCellCount": 24,
        "statesPerGroup": 5,
        "shardCount": 4,
        "casesPerShard": 90,
        "maxParallelPerShard": 2,
        "maximumGlobalCaseParallelism": 8,
        "shards": shards,
        "scientificExecutionAuthorizedByPlan": False,
        "resultOpeningAuthorizedByPlan": False,
    }
    plan["canonicalPlanSha256"] = canonical_sha256(plan)
    return {"plan": plan, "design": design}
