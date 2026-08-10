#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def canon(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def raw(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def verify(root: Path) -> dict[str, Any]:
    protocol_path = root / "full-spectrum-estimator-pilot-preregistration-v2.json"
    execution_path = root / "full-spectrum-estimator-pilot-execution-manifest-v4.json"
    audit = load(root / "full-spectrum-estimator-pilot-seed-collision-audit-v4.json")
    protocol = load(protocol_path)
    execution = load(execution_path)
    if audit.get("auditSha256") != canon({k: v for k, v in audit.items() if k != "auditSha256"}):
        raise ValueError("seed audit canonical self-hash mismatch")
    if audit.get("pilotProtocolSha256") != protocol.get("protocolSha256") or audit.get("pilotPreregistrationRawSha256") != raw(protocol_path):
        raise ValueError("seed audit protocol binding drift")
    if audit.get("executionManifestSha256") != execution.get("manifestSha256") or audit.get("executionManifestRawSha256") != raw(execution_path):
        raise ValueError("seed audit execution-manifest binding drift")
    source = audit.get("sourceCases")
    candidate = audit.get("candidateCases")
    if not isinstance(source, list) or len(source) != 166 or audit.get("sourceCasesCanonicalSha256") != canon(source):
        raise ValueError("seed audit source-case universe drift")
    if not isinstance(candidate, list) or len(candidate) != 44 or audit.get("candidateCasesCanonicalSha256") != canon(candidate):
        raise ValueError("seed audit candidate-case universe drift")
    source_seeds = [row.get("seed") for row in source]
    candidate_seeds = [row.get("seed") for row in candidate]
    if len(set(source_seeds)) != 166 or len(set(candidate_seeds)) != 44:
        raise ValueError("seed audit uniqueness drift")
    if set(source_seeds) & set(candidate_seeds):
        raise ValueError("seed audit source/candidate intersection is no longer empty")
    result = audit.get("collisionResults", {})
    if result.get("sourceCandidateSeedIntersectionCount") != 0 or result.get("sourceCandidateSeedIntersection") != [] or result.get("localExactSourceCollisionAuditPassed") is not True:
        raise ValueError("seed audit collision decision drift")
    universe = audit.get("exactSourceUniverse", {})
    if universe.get("expectedCaseCount") != 166 or universe.get("observedCaseCount") != 166 or universe.get("sourceUniqueSeedCount") != 166:
        raise ValueError("seed audit source counts drift")
    candidates = audit.get("candidateUniverse", {})
    if candidates.get("candidateCaseCount") != 44 or candidates.get("candidateUniqueSeedCount") != 44:
        raise ValueError("seed audit candidate counts drift")
    for key in ("authorizationPermitted", "solverExecutionPerformed", "scientificExecutionAuthorized", "fittingAuthorized", "holdoutOpeningAuthorized", "tier2Authorized", "productionAuthorization"):
        if audit.get(key) is not False:
            raise ValueError(f"seed audit boundary unexpectedly open: {key}")
    return {"status": "PASSED_FROZEN_EVIDENCE_ONLY", "auditSha256": audit["auditSha256"], "historicalSeedCount": 166, "candidateSeedCount": 44, "intersectionCount": 0}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    try:
        print(json.dumps(verify(args.root.resolve()), indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "REFUSED", "reason": str(exc)}, indent=2, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
