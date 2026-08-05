#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

STAGE_ID = "tier1-precision-continuation-wave1-ordinal11-execution-v5"
RUN_TITLE = "Tier-1 precision continuation wave 1 ordinal 11"
AUTHORIZATION_ORDINAL = 11
EXECUTION_KEY = "twilight-surrogate-tier-1-v1:numerical:11"
AUTHORIZATION_PATH = "experiments/tier1-precision-continuation-wave1-v5/authorization.ordinal11.json"
PACKAGE_PATH = "experiments/tier1-precision-continuation-wave1-v5/package.py"
BASE_EXECUTION = "experiments/tier1-precision-continuation-wave1-v4/execution.py"
CASE_COUNT = 40
BLOCKS = [3, 4]


def _base():
    root = Path(__file__).resolve().parents[2]
    path = root / BASE_EXECUTION
    spec = importlib.util.spec_from_file_location("wave1_v5_reviewed_execution", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("reviewed v4 execution module unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.STAGE_ID = STAGE_ID
    module.RUN_TITLE = RUN_TITLE
    module.AUTHORIZATION_ORDINAL = AUTHORIZATION_ORDINAL
    module.EXECUTION_KEY = EXECUTION_KEY
    module.AUTHORIZATION_PATH = AUTHORIZATION_PATH
    module.PACKAGE_PATH = PACKAGE_PATH

    def validate_authorization(auth: dict[str, Any], prereg: dict[str, Any], context: dict[str, Any]) -> None:
        expected = {
            "schemaVersion": 1,
            "stageId": "tier1-precision-continuation-wave1-authorization-v5",
            "status": "AUTHORIZED_PENDING_SEPARATE_DISPATCH",
            "authorizationOrdinal": AUTHORIZATION_ORDINAL,
            "executionKey": EXECUTION_KEY,
            "runTitle": RUN_TITLE,
            "runAttempt": 1,
            "caseCount": CASE_COUNT,
            "blocks": BLOCKS,
            "enabled": True,
            "solverExecutionAuthorized": True,
            "automaticDispatch": False,
            "dispatch": False,
            "workflowDispatchEnabled": False,
            "githubRerunAllowed": False,
            "surrogateTrainingAuthorized": False,
            "internalHoldoutOpeningAuthorized": False,
            "tier2Authorized": False,
            "productionPromotionAuthorized": False,
        }
        stale = {key: (auth.get(key), value) for key, value in expected.items() if auth.get(key) != value}
        if stale:
            raise module.Refusal(f"authorization mismatch: {stale}")
        if auth.get("preregistrationSha256") != prereg.get("preregistrationSha256"):
            raise module.Refusal("preregistration binding changed")
        if auth.get("executionSourceHeadSha") != context.get("headSha"):
            raise module.Refusal("authorization source head changed")

    module.validate_authorization = validate_authorization
    return module


def validate_context(context):
    return _base().validate_context(context)


def validate_authorization(auth, prereg, context):
    return _base().validate_authorization(auth, prereg, context)


def validate_authorization_metadata(metadata, context):
    return _base().validate_authorization_metadata(metadata, context)


def build_manifest(root, auth, context, runs, runtime, metadata):
    return _base().build_manifest(root, auth, context, runs, runtime, metadata)


def validate_manifest(manifest):
    return _base().validate_manifest(manifest)


def load_results(root):
    return _base().load_results(root)


def validate_results(manifest, results):
    return _base().validate_results(manifest, results)


def aggregate(root, manifest, results):
    return _base().aggregate(root, manifest, results)


def audit(root, manifest, results, aggregate_value):
    return _base().audit(root, manifest, results, aggregate_value)


def analyze(root, manifest, aggregate_value, audit_value):
    return _base().analyze(root, manifest, aggregate_value, audit_value)


def dump(value):
    return _base().dump(value)


def main() -> int:
    return _base().main()


if __name__ == "__main__":
    raise SystemExit(main())
