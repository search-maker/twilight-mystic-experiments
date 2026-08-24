from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

STAGE = "aerosol-scenario-interpolation-validation-v1"
PROTOCOL_REL = Path("review/aerosol-scenario-interpolation-validation-v1/protocol.review.json")
EXPECTED_PROTOCOL_BLOB = "27923f9d40d35b001c15b20b7909e3fcd12fd833"
STATE_ROWS = (
    ("native-rural-ss", "native-shettle-bridge", None),
    ("opac-continental-average", "opac-physically-coherent-mixture", "continental_average"),
    ("opac-maritime-clean", "opac-physically-coherent-mixture", "maritime_clean"),
    ("opac-desert", "opac-physically-coherent-mixture", "desert"),
    ("opac-desert-spheroids", "opac-physically-coherent-mixture", "desert_spheroids"),
)


class TransportRefusal(RuntimeError):
    pass


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _protocol(repository_root: Path) -> dict[str, Any]:
    path = repository_root / PROTOCOL_REL
    if git_blob_sha1(path) != EXPECTED_PROTOCOL_BLOB:
        raise TransportRefusal("ASIV protocol byte drift")
    p = json.loads(path.read_text())
    if p.get("stageId") != STAGE or p.get("status") != "REVIEW_ONLY_PREREGISTRATION_NO_SCIENTIFIC_IDENTITY_NO_EXECUTION":
        raise TransportRefusal("ASIV protocol identity drift")
    env = p.get("frozenExecutionEnvelopeIfLaterAuthorized") or {}
    expected = (env.get("holdoutGeometryCount"), env.get("scenarioStatesPerGeometry"), env.get("replicatesPerGeometryState"), env.get("commonRandomNumberGroups"), env.get("caseCount"), env.get("photonHistoriesPerCase"), env.get("configuredPhotonHistories"))
    if expected != (8, 5, 3, 24, 120, 20_000_000, 2_400_000_000):
        raise TransportRefusal(f"ASIV frozen execution envelope drift: {expected!r}")
    return p


def build_seedless_design(repository_root: Path) -> dict[str, Any]:
    p = _protocol(repository_root)
    holdouts = (p.get("freshHoldoutGeometrySelection") or {}).get("selectedGeometries") or []
    if len(holdouts) != 8 or [row.get("holdoutId") for row in holdouts] != [f"asiv-holdout-{i:02d}" for i in range(1, 9)]:
        raise TransportRefusal("exact eight frozen holdouts required")
    groups: list[dict[str, Any]] = []
    cases: list[dict[str, Any]] = []
    for row in holdouts:
        hid = str(row["holdoutId"])
        geometry = dict(row["geometry"])
        required = ("sunDepressionDeg", "targetAltitudeDeg", "relativeAzimuthDeg", "observerElevationM", "aod550")
        if any(key not in geometry for key in required):
            raise TransportRefusal(f"holdout geometry incomplete: {hid}")
        for replicate in (1, 2, 3):
            group_id = f"{hid}|replicate={replicate}"
            group = {
                "groupId": group_id,
                "holdoutId": hid,
                "replicate": replicate,
                **geometry,
                "nearestTrainingGeometryId": row["nearestTrainingGeometryId"],
                "nearestTrainingDistance": row["nearestTrainingDistance"],
                "normalizedCoordinates": row["normalizedCoordinates"],
                "seed": None,
                "seedStatus": "UNALLOCATED_REVIEW_ONLY",
                "renderable": False,
                "executionAuthorized": False,
            }
            groups.append(group)
            for state_id, aerosol_kind, mixture in STATE_ROWS:
                cases.append({
                    "caseId": f"{hid}-r{replicate}-{state_id}",
                    "groupId": group_id,
                    "holdoutId": hid,
                    "replicate": replicate,
                    "stateId": state_id,
                    "aerosolKind": aerosol_kind,
                    "opacMixture": mixture,
                    **geometry,
                    "seed": None,
                    "seedStatus": "UNALLOCATED_REVIEW_ONLY",
                    "photonHistories": 20_000_000,
                    "numericalMethod": "reference-vroom-1nm",
                    "augmentedDataTreeSha256": "5d8bbf8e6b91ec3d405dee36f21a94afbb6e5ec6cd67da2dd5dd541738199d80",
                    "renderable": False,
                    "executionAuthorized": False,
                })
    if len(groups) != 24 or len(cases) != 120:
        raise TransportRefusal("ASIV seedless design cardinality drift")
    if len({row["groupId"] for row in groups}) != 24 or len({row["caseId"] for row in cases}) != 120:
        raise TransportRefusal("ASIV identity duplication")
    for group in groups:
        members = [row for row in cases if row["groupId"] == group["groupId"]]
        if len(members) != 5 or {row["stateId"] for row in members} != {row[0] for row in STATE_ROWS}:
            raise TransportRefusal(f"ASIV five-state group drift: {group['groupId']}")
    result = {
        "schemaVersion": 1,
        "stageId": f"{STAGE}-execution-transport-design",
        "status": "REVIEW_ONLY_SEEDLESS_NON_RENDERABLE_NO_AUTHORIZATION",
        "holdoutCount": 8,
        "groupCount": 24,
        "caseCount": 120,
        "statesPerGroup": 5,
        "configuredPhotonHistories": 2_400_000_000,
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


def validate_authorized_design(repository_root: Path, design: dict[str, Any]) -> None:
    seedless = build_seedless_design(repository_root)
    if design.get("stageId") != seedless["stageId"] or design.get("status") != "CANDIDATE_SEEDED_DESIGN_FRESHNESS_PROVEN_REVIEW_ONLY":
        raise TransportRefusal("authorized-design precursor status drift")
    if (design.get("holdoutCount"), design.get("groupCount"), design.get("caseCount"), design.get("statesPerGroup"), design.get("configuredPhotonHistories")) != (8, 24, 120, 5, 2_400_000_000):
        raise TransportRefusal("authorized-design precursor cardinality drift")
    if design.get("candidateSeedsAllocated") is not True or design.get("candidateSeedFreshnessProven") is not True:
        raise TransportRefusal("candidate-seed freshness not proven")
    for key in ("scientificOrdinalAllocated", "authorizationCreated", "dispatchCreated", "scientificExecutionAuthorized", "solverExecutionAuthorized", "resultOpeningAuthorized"):
        if design.get(key) is not False:
            raise TransportRefusal(f"review design crossed allocation/execution boundary: {key}")
    stored = design.get("canonicalDesignSha256")
    check = dict(design); check.pop("canonicalDesignSha256", None)
    if stored != canonical_sha256(check):
        raise TransportRefusal("authorized-design precursor canonical hash mismatch")
    base_groups = {row["groupId"]: row for row in seedless["groups"]}
    actual_groups = {str(row.get("groupId")): row for row in design.get("groups") or []}
    if set(actual_groups) != set(base_groups):
        raise TransportRefusal("group universe drift")
    seeds: set[int] = set()
    for gid, base in base_groups.items():
        row = actual_groups[gid]
        for key, value in base.items():
            if key not in {"seed", "seedStatus"} and row.get(key) != value:
                raise TransportRefusal(f"group metadata drift: {gid}:{key}")
        seed = row.get("seed")
        if isinstance(seed, bool) or not isinstance(seed, int) or not 0 < seed < 2_147_483_647:
            raise TransportRefusal(f"invalid group seed: {gid}")
        if row.get("seedStatus") != "CANDIDATE_FRESHNESS_PROVEN_REVIEW_ONLY":
            raise TransportRefusal(f"group seed status drift: {gid}")
        seeds.add(seed)
    if len(seeds) != 24:
        raise TransportRefusal("group seeds must be unique")
    base_cases = {row["caseId"]: row for row in seedless["cases"]}
    actual_cases = {str(row.get("caseId")): row for row in design.get("cases") or []}
    if set(actual_cases) != set(base_cases):
        raise TransportRefusal("case universe drift")
    for cid, base in base_cases.items():
        row = actual_cases[cid]
        for key, value in base.items():
            if key not in {"seed", "seedStatus"} and row.get(key) != value:
                raise TransportRefusal(f"case metadata drift: {cid}:{key}")
        group_seed = actual_groups[row["groupId"]]["seed"]
        if row.get("seed") != group_seed or row.get("seedStatus") != "CANDIDATE_FRESHNESS_PROVEN_REVIEW_ONLY":
            raise TransportRefusal(f"CRN seed-sharing drift: {cid}")


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(build_seedless_design(root), indent=2, sort_keys=True))
