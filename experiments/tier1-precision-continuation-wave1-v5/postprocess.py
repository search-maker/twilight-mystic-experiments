from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
from typing import Any


def _load(name: str):
    path = Path(__file__).with_name(name + ".py")
    spec = importlib.util.spec_from_file_location("wave1_v5_" + name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def translate_results(preregistration: dict[str, Any], results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    c = _load("core")
    expected = {row["caseId"]: row for row in preregistration["cases"]}
    if len(results) != c.CASE_COUNT or {row.get("caseId") for row in results} != set(expected):
        raise c.Refusal("partial, duplicate, or unplanned v5 result set")
    translated = []
    for result in results:
        case = expected[result["caseId"]]
        row = copy.deepcopy(result)
        if row.get("seed") != case["seed"] or row.get("block") != case["block"] or row.get("role") != case["role"]:
            raise c.Refusal("v5 result provenance changed")
        row["caseId"] = case["baseCaseId"]
        translated.append(row)
    return translated


def aggregate_wave1(preregistration, results, root=None):
    c, p = _load("core"), _load("package")
    root = (root or c.repository_root()).resolve()
    p.validate_preregistration(preregistration, root)
    _, base, _, proposal, _, _ = c.proposal(root)
    aggregate = base.aggregate_wave(proposal, c.WAVE, base.CONTINUATION_GEOMETRY_IDS, translate_results(preregistration, results))
    wrapper = {
        "schemaVersion": 1,
        "stageId": "tier1-precision-continuation-wave1-aggregate-v5",
        "preregistrationSha256": preregistration["preregistrationSha256"],
        "aggregate": aggregate,
        "aggregateSha256": c.canonical_sha256(aggregate),
        "additionalExecutionAutomaticallyAuthorized": False,
    }
    wrapper["payloadSha256"] = c.canonical_sha256(wrapper)
    return wrapper


def audit_wave1(preregistration, results, aggregate_wrapper, root=None):
    c, p = _load("core"), _load("package")
    root = (root or c.repository_root()).resolve()
    p.validate_preregistration(preregistration, root)
    payload = {key: item for key, item in aggregate_wrapper.items() if key != "payloadSha256"}
    aggregate = aggregate_wrapper.get("aggregate")
    if aggregate_wrapper.get("payloadSha256") != c.canonical_sha256(payload) or not isinstance(aggregate, dict) or aggregate_wrapper.get("aggregateSha256") != c.canonical_sha256(aggregate):
        raise c.Refusal("v5 aggregate wrapper changed")
    _, base, _, proposal, _, _ = c.proposal(root)
    audit = base.audit_wave(proposal, c.WAVE, base.CONTINUATION_GEOMETRY_IDS, translate_results(preregistration, results), aggregate)
    wrapper = {
        "schemaVersion": 1,
        "stageId": "tier1-precision-continuation-wave1-independent-audit-v5",
        "preregistrationSha256": preregistration["preregistrationSha256"],
        "aggregateSha256": aggregate_wrapper["aggregateSha256"],
        "audit": audit,
        "auditSha256": c.canonical_sha256(audit),
        "independentlyRecomputedFromRawSelectedNodeRadiance": True,
        "additionalExecutionAutomaticallyAuthorized": False,
    }
    wrapper["payloadSha256"] = c.canonical_sha256(wrapper)
    return wrapper


def analyze_wave1(preregistration, aggregate_wrapper, audit_wrapper, root=None):
    c, p = _load("core"), _load("package")
    root = (root or c.repository_root()).resolve()
    p.validate_preregistration(preregistration, root)
    for wrapper, label in ((aggregate_wrapper, "aggregate"), (audit_wrapper, "audit")):
        payload = {key: item for key, item in wrapper.items() if key != "payloadSha256"}
        if wrapper.get("payloadSha256") != c.canonical_sha256(payload):
            raise c.Refusal(f"v5 {label} wrapper changed")
    _, base, _, proposal, _, _ = c.proposal(root)
    analysis = base.analyze_waves(proposal, [aggregate_wrapper["aggregate"]], [audit_wrapper["audit"]])
    value = {
        "schemaVersion": 1,
        "stageId": "tier1-precision-continuation-wave1-analysis-v5",
        "preregistrationSha256": preregistration["preregistrationSha256"],
        "aggregateSha256": aggregate_wrapper["aggregateSha256"],
        "auditSha256": audit_wrapper["auditSha256"],
        "analysis": analysis,
        "additionalExecutionAutomaticallyAuthorized": False,
        "surrogateFitAuthorized": False,
        "internalHoldoutOpened": False,
        "tier2Authorized": False,
        "productionPromotionAuthorized": False,
    }
    value["analysisSha256"] = c.canonical_sha256(value)
    return value
