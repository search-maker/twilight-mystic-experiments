from __future__ import annotations

import hashlib
import json
from itertools import product
from pathlib import Path
from typing import Any

NAMESPACE = "aerosol-family-challenge-v2|group-seed|sha256-v1"
SIGNED_SEED_MAX_EXCLUSIVE = 2_147_483_647
SUN_DEPRESSION_DEG = (2, 4, 6, 8)
GEOMETRY_IDS = (
    "g02-early-near-low",
    "g04-mid-perpendicular",
    "g06-late-opposite-high-aerosol",
)
AOD550_VALUES = (0.10, 0.30)
REPLICATES = (1, 2, 3)


def analysis_cell_id(dep: int, geometry_id: str, aod550: float) -> str:
    return f"afc2-d{dep:02d}-{geometry_id}-aod{int(round(aod550 * 100)):02d}"


def derive_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    used: set[int] = set()
    for dep, geometry_id, aod550, replicate in product(
        SUN_DEPRESSION_DEG, GEOMETRY_IDS, AOD550_VALUES, REPLICATES
    ):
        cell_id = analysis_cell_id(dep, geometry_id, aod550)
        counter = 0
        while True:
            material = (
                f"{NAMESPACE}|analysisCellId={cell_id}|"
                f"replicate={replicate}|counter={counter}"
            )
            digest = hashlib.sha256(material.encode("utf-8")).digest()
            seed = (int.from_bytes(digest[:8], "big") % (SIGNED_SEED_MAX_EXCLUSIVE - 1)) + 1
            if seed not in used:
                break
            counter += 1
        used.add(seed)
        rows.append(
            {
                "analysisCellId": cell_id,
                "replicate": replicate,
                "collisionCounter": counter,
                "derivationMaterial": material,
                "derivationMaterialSha256": hashlib.sha256(material.encode("utf-8")).hexdigest(),
                "seed": seed,
            }
        )
    return rows


def canonical_sha256(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def build_ledger() -> dict[str, Any]:
    rows = derive_rows()
    seeds = [row["seed"] for row in rows]
    return {
        "schemaVersion": 1,
        "stageId": "aerosol-family-challenge-v2-candidate-seed-ledger",
        "status": "DETERMINISTIC_CANDIDATE_SEEDS_NOT_FRESHNESS_PROVEN",
        "namespace": NAMESPACE,
        "algorithm": "SHA-256 UTF-8 material; first 64 digest bits as big-endian integer; seed=(value mod 2147483646)+1; increment collisionCounter only for an internal duplicate",
        "seedDomain": [1, 2_147_483_646],
        "rowCount": len(rows),
        "allCollisionCountersZero": all(row["collisionCounter"] == 0 for row in rows),
        "rows": rows,
        "candidateSeeds": seeds,
        "candidateSeedCanonicalSha256": canonical_sha256(seeds),
        "authorizationPermitted": False,
    }


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    ledger = build_ledger()
    args.output.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(ledger["candidateSeedCanonicalSha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
