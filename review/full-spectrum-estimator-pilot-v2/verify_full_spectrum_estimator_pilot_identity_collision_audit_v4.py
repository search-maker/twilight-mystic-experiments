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
    execution_path = root / "full-spectrum-estimator-pilot-execution-manifest-v4.json"
    seed_path = root / "full-spectrum-estimator-pilot-seed-collision-audit-v4.json"
    audit = load(root / "full-spectrum-estimator-pilot-identity-collision-audit-v4.json")
    execution = load(execution_path)
    seed = load(seed_path)
    if audit.get("auditSha256") != canon({k: v for k, v in audit.items() if k != "auditSha256"}):
        raise ValueError("identity audit canonical self-hash mismatch")
    if audit.get("executionManifestSelfHash") != execution.get("manifestSha256") or audit.get("executionManifestRawSha256") != raw(execution_path):
        raise ValueError("identity audit execution-manifest binding drift")
    if audit.get("seedCollisionAuditSelfHash") != seed.get("auditSha256") or audit.get("seedCollisionAuditRawSha256") != raw(seed_path):
        raise ValueError("identity audit seed binding drift")
    candidate = audit.get("candidateIdentity", {})
    expected = {
        "globalScientificOrdinal": 14,
        "executionKey": "full-spectrum-estimator-pilot-v2:numerical:14",
        "authorizationBranch": "authorization/full-spectrum-estimator-pilot-v2-ordinal14",
        "dispatchBranch": "dispatch/full-spectrum-estimator-pilot-v2-ordinal14",
        "workflowDisplayTitle": "Full-spectrum estimator pilot v2 ordinal 14",
        "status": "CANDIDATE_ONLY_NOT_RESERVED_NOT_AUTHORIZED",
    }
    if candidate != expected:
        raise ValueError("candidate identity drift")
    checks = audit.get("reviewSurfaceChecks", {})
    if any(value != 0 for value in checks.values()):
        raise ValueError("review-time identity collision count is nonzero")
    decision = audit.get("collisionDecision", {})
    if any(value is not False for value in decision.values()):
        raise ValueError("review-time collision decision drift")
    if audit.get("latestKnownConsumedScientificOrdinal") != 13:
        raise ValueError("review-time consumed ordinal context drift")
    if not audit.get("requiredRechecksBeforeAnyAuthorization"):
        raise ValueError("fresh preauthorization recheck requirement missing")
    for key in ("authorizationPermitted", "dispatchPermitted", "solverExecutionPerformed", "scientificExecutionAuthorized", "fittingAuthorized", "holdoutOpeningAuthorized", "tier2Authorized", "productionAuthorization"):
        if audit.get(key) is not False:
            raise ValueError(f"identity audit boundary unexpectedly open: {key}")
    return {"status": "PASSED_REVIEW_TIME_ONLY_RECHECK_REQUIRED", "auditSha256": audit["auditSha256"], "candidateOrdinal": 14, "reserved": False, "authorized": False}


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
