from __future__ import annotations

import hashlib
import json
from itertools import product
from pathlib import Path
from typing import Any

STAGE_ID = "aerosol-optical-property-sensitivity-v1"
NAMESPACE = "aerosol-optical-property-sensitivity-v1|group-seed|sha256-v1"
SEED_DOMAIN_MAX_EXCLUSIVE = 2_147_483_647
PROTOCOL_PATH = Path(__file__).resolve().parent / "protocol.review.json"
LEDGER_PATH = Path(__file__).resolve().parent / "candidate-seed-ledger.v1.json"


class Refusal(RuntimeError):
    pass


def canonical_sha256(value: Any) -> str:
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(data).hexdigest()


def derive_rows() -> list[dict[str, Any]]:
    p = json.loads(PROTOCOL_PATH.read_text())
    if p.get("stageId") != STAGE_ID:
        raise Refusal("protocol stage drift")
    if p["commonRandomNumbers"].get("freshNamespaceRequired") != NAMESPACE:
        raise Refusal("seed namespace drift")
    d = p["fixedNumericalAndPhysicalDesign"]
    rows: list[dict[str, Any]] = []
    used: set[int] = set()
    for dep, geo, aod, rep in product(d["sunDepressionDeg"], d["geometries"], d["aod550"], d["replicates"]):
        cell = f"aops-d{int(dep):02d}-{geo['geometryId']}-aod{int(round(float(aod)*100)):02d}"
        counter = 0
        while True:
            material = f"{NAMESPACE}|analysisCellId={cell}|replicate={int(rep)}|counter={counter}"
            digest = hashlib.sha256(material.encode()).digest()
            seed = (int.from_bytes(digest[:8], "big") % (SEED_DOMAIN_MAX_EXCLUSIVE - 1)) + 1
            if seed not in used:
                break
            counter += 1
        used.add(seed)
        rows.append({
            "analysisCellId": cell,
            "replicate": int(rep),
            "collisionCounter": counter,
            "derivationMaterialSha256": hashlib.sha256(material.encode()).hexdigest(),
            "seed": seed,
        })
    if len(rows) != 72 or len(used) != 72:
        raise Refusal("candidate seed cardinality drift")
    return rows


def validate_ledger() -> dict[str, Any]:
    ledger = json.loads(LEDGER_PATH.read_text())
    rows = derive_rows()
    seeds = [int(row["seed"]) for row in rows]
    if ledger.get("schemaVersion") != 1 or ledger.get("stageId") != STAGE_ID + "-candidate-seeds":
        raise Refusal("candidate seed ledger identity drift")
    if ledger.get("status") != "CANDIDATE_ONLY_NOT_APPLIED_NOT_AUTHORIZED":
        raise Refusal("candidate seed ledger status drift")
    if ledger.get("namespace") != NAMESPACE:
        raise Refusal("candidate seed ledger namespace drift")
    if ledger.get("candidateSeedCount") != 72 or ledger.get("candidateSeeds") != seeds:
        raise Refusal("candidate seed ledger values drift")
    if ledger.get("candidateFirstSeed") != seeds[0] or ledger.get("candidateLastSeed") != seeds[-1]:
        raise Refusal("candidate seed endpoints drift")
    if ledger.get("allCollisionCountersZero") is not True or any(row["collisionCounter"] != 0 for row in rows):
        raise Refusal("candidate seed collision-counter drift")
    if ledger.get("candidateSeedCanonicalSha256") != canonical_sha256(seeds):
        raise Refusal("candidate seed canonical hash drift")
    if ledger.get("candidateRowsCanonicalSha256") != canonical_sha256(rows):
        raise Refusal("candidate row canonical hash drift")
    if ledger.get("appliedToCaseSkeletons") is not False or ledger.get("scientificOrdinalAllocated") is not False:
        raise Refusal("candidate ledger crossed allocation boundary")
    if ledger.get("authorizationPermitted") is not False or ledger.get("solverExecutionAuthorized") is not False:
        raise Refusal("candidate ledger crossed execution boundary")
    return ledger


if __name__ == "__main__":
    value = validate_ledger()
    print(json.dumps({
        "status": "PASS_CANDIDATE_LEDGER_DETERMINISTIC_NOT_AUTHORIZED",
        "candidateSeedCount": value["candidateSeedCount"],
        "candidateSeedCanonicalSha256": value["candidateSeedCanonicalSha256"],
    }, sort_keys=True))
