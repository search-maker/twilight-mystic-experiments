from __future__ import annotations

import json
from itertools import product
from pathlib import Path
from typing import Any

STAGE_ID = "aerosol-full-phase-function-sensitivity-v1"
PROTOCOL_PATH = Path(__file__).resolve().parent / "protocol.review.json"


class Refusal(RuntimeError):
    pass


def load_protocol() -> dict[str, Any]:
    p = json.loads(PROTOCOL_PATH.read_text())
    if p.get("stageId") != STAGE_ID:
        raise Refusal("stageId drift")
    if p.get("status") != "REVIEW_ONLY_PREREGISTRATION_EXECUTION_DISABLED_RESULTS_NOT_OPENED":
        raise Refusal("review status drift")
    for key in (
        "scientificExecutionAuthorized",
        "solverExecutionAuthorized",
        "resultOpeningAuthorized",
        "candidateSeedsAllocated",
        "scientificOrdinalAllocated",
    ):
        if p.get(key) is not False:
            raise Refusal(f"review boundary drift: {key}")
    return p


def analysis_cells() -> list[dict[str, Any]]:
    p = load_protocol()
    d = p["fixedNumericalAndPhysicalDesign"]
    cells: list[dict[str, Any]] = []
    for dep, geo, aod in product(d["sunDepressionDeg"], d["geometries"], d["aod550"]):
        cells.append({
            "analysisCellId": f"afpf-d{int(dep):02d}-{geo['geometryId']}-aod{int(round(float(aod)*100)):02d}",
            "sunDepressionDeg": float(dep),
            "aod550": float(aod),
            "geometryId": str(geo["geometryId"]),
            "geometryTag": str(geo["geometryTag"]),
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
    rows: list[dict[str, Any]] = []
    for cell, rep in product(analysis_cells(), reps):
        rows.append({
            **cell,
            "replicate": int(rep),
            "groupId": f"{cell['analysisCellId']}-r{int(rep)}",
            "seed": None,
            "seedStatus": "UNALLOCATED_REVIEW_ONLY",
        })
    if len(rows) != 72 or len({r["groupId"] for r in rows}) != 72:
        raise Refusal("CRN group cardinality/identity drift")
    return rows


def case_skeletons() -> list[dict[str, Any]]:
    p = load_protocol()
    d = p["fixedNumericalAndPhysicalDesign"]
    states = p["aerosolStates"]
    if not isinstance(states, list) or len(states) != 5:
        raise Refusal("exact five-state review universe required")
    state_ids = [str(s["stateId"]) for s in states]
    if len(set(state_ids)) != 5:
        raise Refusal("state IDs duplicated")
    rows: list[dict[str, Any]] = []
    for group, state in product(group_skeletons(), states):
        state_id = str(state["stateId"])
        rows.append({
            **group,
            "stateId": state_id,
            "caseId": f"{group['groupId']}-{state_id}",
            "aerosolKind": str(state["kind"]),
            "opacMixture": state.get("opacMixture"),
            "photonHistories": int(d["photonHistoriesPerCase"]),
            "numericalMethod": str(d["numericalMethod"]),
            "augmentedDataTreeSha256": p["runtimeAndOpticalPropertyBinding"]["augmentedStagedDataTreeSha256"],
            "renderable": False,
            "executionAuthorized": False,
        })
    if len(rows) != 360 or len({r["caseId"] for r in rows}) != 360:
        raise Refusal("case skeleton cardinality/identity drift")
    expected_states = set(state_ids)
    by_group: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_group.setdefault(str(row["groupId"]), []).append(row)
    if len(by_group) != 72:
        raise Refusal("expected 72 CRN groups")
    for group_id, members in by_group.items():
        if len(members) != 5 or {m["stateId"] for m in members} != expected_states:
            raise Refusal(f"group state-universe drift: {group_id}")
        if {m["seed"] for m in members} != {None}:
            raise Refusal(f"review group unexpectedly has seed: {group_id}")
        if any(m["renderable"] is not False or m["executionAuthorized"] is not False for m in members):
            raise Refusal(f"review group crossed execution boundary: {group_id}")
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
        "configuredPhotonHistories": sum(int(row["photonHistories"]) for row in cases),
        "seedNamespace": p["commonRandomNumbers"]["freshNamespaceRequired"],
        "candidateSeedsAllocated": False,
        "scientificOrdinalAllocated": False,
        "scientificExecutionAuthorized": False,
        "resultOpeningAuthorized": False,
        "analysisCells": cells,
        "groups": groups,
        "cases": cases,
    }


if __name__ == "__main__":
    print(json.dumps(review_manifest(), indent=2, sort_keys=True, allow_nan=False))
