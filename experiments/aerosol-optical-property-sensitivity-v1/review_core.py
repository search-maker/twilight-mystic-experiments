from __future__ import annotations

import json
from itertools import product
from pathlib import Path
from typing import Any

STAGE_ID = "aerosol-optical-property-sensitivity-v1"
PROTOCOL_PATH = Path(__file__).resolve().parent / "protocol.review.json"


class Refusal(RuntimeError):
    pass


def load_protocol() -> dict[str, Any]:
    p = json.loads(PROTOCOL_PATH.read_text())
    if p.get("stageId") != STAGE_ID:
        raise Refusal("stageId drift")
    if p.get("status") != "REVIEW_ONLY_PREREGISTRATION_EXECUTION_DISABLED_RESULTS_NOT_OPENED":
        raise Refusal("review status drift")
    if any(p.get(k) is not False for k in ("scientificExecutionAuthorized", "solverExecutionAuthorized", "resultOpeningAuthorized")):
        raise Refusal("review unexpectedly authorizes execution/result opening")
    return p


def analysis_cells() -> list[dict[str, Any]]:
    p = load_protocol()
    d = p["fixedNumericalAndPhysicalDesign"]
    cells: list[dict[str, Any]] = []
    for dep, geo, aod in product(d["sunDepressionDeg"], d["geometries"], d["aod550"]):
        cells.append({
            "analysisCellId": f"aops-d{int(dep):02d}-{geo['geometryId']}-aod{int(round(float(aod)*100)):02d}",
            "sunDepressionDeg": float(dep),
            "aod550": float(aod),
            "geometryId": geo["geometryId"],
            "geometryTag": geo["geometryTag"],
            "targetAltitudeDeg": float(geo["targetAltitudeDeg"]),
            "relativeAzimuthDeg": float(geo["relativeAzimuthDeg"]),
            "observerElevationM": float(d["observerElevationM"]),
        })
    if len(cells) != 24 or len({c["analysisCellId"] for c in cells}) != 24:
        raise Refusal("analysis-cell cardinality/identity drift")
    return cells


def group_skeletons() -> list[dict[str, Any]]:
    p = load_protocol()
    reps = p["fixedNumericalAndPhysicalDesign"]["replicates"]
    groups: list[dict[str, Any]] = []
    for cell, rep in product(analysis_cells(), reps):
        groups.append({
            **cell,
            "replicate": int(rep),
            "groupId": f"{cell['analysisCellId']}-r{int(rep)}",
            "seed": None,
            "seedStatus": "UNALLOCATED_REVIEW_ONLY",
        })
    if len(groups) != 72 or len({g["groupId"] for g in groups}) != 72:
        raise Refusal("CRN group cardinality/identity drift")
    return groups


def case_skeletons() -> list[dict[str, Any]]:
    p = load_protocol()
    d = p["fixedNumericalAndPhysicalDesign"]
    states = p["aerosolStates"]
    rows: list[dict[str, Any]] = []
    for group, state in product(group_skeletons(), states):
        state_id = state["stateId"]
        rows.append({
            **group,
            "stateId": state_id,
            "caseId": f"{group['groupId']}-{state_id}",
            "aerosolKind": state["kind"],
            "ssaSet": state["ssaSet"],
            "ggSet": state["ggSet"],
            "photonHistories": int(d["photonHistoriesPerCase"]),
            "numericalMethod": d["numericalMethod"],
            "renderable": False,
            "executionAuthorized": False,
        })
    if len(rows) != 360 or len({r["caseId"] for r in rows}) != 360:
        raise Refusal("case skeleton cardinality/identity drift")
    by_group: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_group.setdefault(row["groupId"], []).append(row)
    expected_states = {s["stateId"] for s in states}
    if len(by_group) != 72:
        raise Refusal("expected 72 CRN groups")
    for group_id, members in by_group.items():
        if len(members) != 5 or {m["stateId"] for m in members} != expected_states:
            raise Refusal(f"group state-universe drift: {group_id}")
        if {m["seed"] for m in members} != {None}:
            raise Refusal(f"review group unexpectedly has a seed: {group_id}")
    return rows


def review_manifest() -> dict[str, Any]:
    p = load_protocol()
    cells = analysis_cells()
    groups = group_skeletons()
    cases = case_skeletons()
    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "REVIEW_ONLY_CASE_SKELETONS_NON_RENDERABLE_NO_SEEDS",
        "analysisCellCount": len(cells),
        "groupCount": len(groups),
        "caseCount": len(cases),
        "statesPerGroup": len(p["aerosolStates"]),
        "seedNamespace": p["commonRandomNumbers"]["freshNamespaceRequired"],
        "candidateSeedsAllocated": False,
        "scientificExecutionAuthorized": False,
        "resultOpeningAuthorized": False,
        "analysisCells": cells,
        "groups": groups,
        "cases": cases,
    }


if __name__ == "__main__":
    print(json.dumps(review_manifest(), indent=2, sort_keys=True, allow_nan=False))
