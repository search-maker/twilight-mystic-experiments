from __future__ import annotations

import copy
import importlib.util
import math
from pathlib import Path
from typing import Any


def _load(name: str):
    path = Path(__file__).with_name(name + ".py")
    spec = importlib.util.spec_from_file_location("wave2_v1_" + name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _validate_wrapper(
    wrapper: dict[str, Any],
    *,
    stage_id: str,
    inner_key: str,
    inner_sha_key: str,
    label: str,
) -> dict[str, Any]:
    c = _load("core")
    if not isinstance(wrapper, dict) or wrapper.get("stageId") != stage_id:
        raise c.Refusal(f"{label} wrapper identity changed")
    payload = {key: item for key, item in wrapper.items() if key != "payloadSha256"}
    if wrapper.get("payloadSha256") != c.canonical_sha256(payload):
        raise c.Refusal(f"{label} wrapper hash changed")
    inner = wrapper.get(inner_key)
    if not isinstance(inner, dict) or wrapper.get(inner_sha_key) != c.canonical_sha256(inner):
        raise c.Refusal(f"{label} inner payload hash changed")
    return inner


def translate_results(
    preregistration: dict[str, Any],
    results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    c = _load("core")
    expected = {row["caseId"]: row for row in preregistration["cases"]}
    if len(results) != c.CASE_COUNT or {row.get("caseId") for row in results} != set(expected):
        raise c.Refusal("partial, duplicate, or unplanned wave-two result set")
    translated = []
    for result in results:
        if not isinstance(result, dict):
            raise c.Refusal("wave-two result row is not an object")
        case = expected[result["caseId"]]
        row = copy.deepcopy(result)
        if (
            row.get("stageId") != "tier1-precision-continuation-wave2-ordinal12-execution-v1"
            or row.get("seed") != case["seed"]
            or row.get("block") != case["block"]
            or row.get("role") != case["role"]
            or row.get("photonHistories") != case["photonHistories"]
        ):
            raise c.Refusal("wave-two result provenance changed")
        if (
            row.get("status") != "COMPLETED"
            or row.get("syntaxCheckCount") != 1
            or row.get("solverExecutionCount") != 1
            or row.get("retryAllowed") is not False
            or row.get("resumeAllowed") is not False
            or row.get("fittingSurfaceExposed") is not False
        ):
            raise c.Refusal("wave-two result did not prove one successful case execution")
        supplied_content_sha = row.pop("contentSha256", None)
        computed_content_sha = c.canonical_sha256(row)
        if supplied_content_sha != computed_content_sha:
            raise c.Refusal("wave-two result content hash changed")
        runtime_sha = row.get("runtimeReportSha256")
        value = row.get("selectedPhotopicContributionCdM2")
        nodes = row.get("selectedNodeRadiance")
        if not _is_sha256(runtime_sha):
            raise c.Refusal("wave-two runtime report hash missing")
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(float(value))
            or value < 0
        ):
            raise c.Refusal("wave-two photopic contribution invalid")
        if (
            not isinstance(nodes, list)
            or len(nodes) != 15
            or any(
                not isinstance(node, (int, float))
                or isinstance(node, bool)
                or not math.isfinite(float(node))
                or node < 0
                for node in nodes
            )
        ):
            raise c.Refusal("wave-two selected-node radiance invalid")
        zero_hit = float(value) == 0.0 and all(float(node) == 0.0 for node in nodes)
        if row.get("zeroHit") is not zero_hit:
            raise c.Refusal("wave-two zero-hit semantics changed")
        for name in ("inputSha256", "radianceOutputSha256", "stdOutputSha256"):
            if not _is_sha256(row.get(name)):
                raise c.Refusal(f"wave-two {name} missing")
        row["caseId"] = case["baseCaseId"]
        row["alisSpectralImportanceSamplingNm"] = case[
            "alisSpectralImportanceSamplingNm"
        ]
        row["geometrySha256"] = case["geometrySha256"]
        row["syntax"] = {"exitCode": 0, "timedOut": False}
        row["solver"] = {"exitCode": 0, "timedOut": False}
        row["artifactSha256"] = supplied_content_sha
        row["runtimeSha256"] = runtime_sha
        row["valueCdM2"] = float(value)
        translated.append(row)
    return translated


def aggregate_wave2(preregistration, results, root=None):
    c, p = _load("core"), _load("package")
    root = (root or c.repository_root()).resolve()
    p.validate_preregistration(preregistration, root)
    state = c.proposal(root)
    aggregate = state["base"].aggregate_wave(
        state["proposal"],
        c.WAVE,
        c.ACTIVE_GEOMETRY_IDS,
        translate_results(preregistration, results),
    )
    wrapper = {
        "schemaVersion": 1,
        "stageId": "tier1-precision-continuation-wave2-aggregate-v1",
        "preregistrationSha256": preregistration["preregistrationSha256"],
        "aggregate": aggregate,
        "aggregateSha256": c.canonical_sha256(aggregate),
        "additionalExecutionAutomaticallyAuthorized": False,
    }
    wrapper["payloadSha256"] = c.canonical_sha256(wrapper)
    return wrapper


def audit_wave2(preregistration, results, aggregate_wrapper, root=None):
    c, p = _load("core"), _load("package")
    root = (root or c.repository_root()).resolve()
    p.validate_preregistration(preregistration, root)
    aggregate = _validate_wrapper(
        aggregate_wrapper,
        stage_id="tier1-precision-continuation-wave2-aggregate-v1",
        inner_key="aggregate",
        inner_sha_key="aggregateSha256",
        label="wave-two aggregate",
    )
    state = c.proposal(root)
    audit = state["base"].audit_wave(
        state["proposal"],
        c.WAVE,
        c.ACTIVE_GEOMETRY_IDS,
        translate_results(preregistration, results),
        aggregate,
    )
    wrapper = {
        "schemaVersion": 1,
        "stageId": "tier1-precision-continuation-wave2-independent-audit-v1",
        "preregistrationSha256": preregistration["preregistrationSha256"],
        "aggregateSha256": aggregate_wrapper["aggregateSha256"],
        "audit": audit,
        "auditSha256": c.canonical_sha256(audit),
        "independentlyRecomputedFromRawSelectedNodeRadiance": True,
        "additionalExecutionAutomaticallyAuthorized": False,
    }
    wrapper["payloadSha256"] = c.canonical_sha256(wrapper)
    return wrapper


def analyze_waves(
    preregistration,
    source_aggregate_wrapper,
    source_audit_wrapper,
    wave2_aggregate_wrapper,
    wave2_audit_wrapper,
    root=None,
):
    c, p = _load("core"), _load("package")
    root = (root or c.repository_root()).resolve()
    p.validate_preregistration(preregistration, root)
    source_aggregate = _validate_wrapper(
        source_aggregate_wrapper,
        stage_id="tier1-precision-continuation-wave1-aggregate-v5",
        inner_key="aggregate",
        inner_sha_key="aggregateSha256",
        label="source wave-one aggregate",
    )
    source_audit = _validate_wrapper(
        source_audit_wrapper,
        stage_id="tier1-precision-continuation-wave1-independent-audit-v5",
        inner_key="audit",
        inner_sha_key="auditSha256",
        label="source wave-one audit",
    )
    wave2_aggregate = _validate_wrapper(
        wave2_aggregate_wrapper,
        stage_id="tier1-precision-continuation-wave2-aggregate-v1",
        inner_key="aggregate",
        inner_sha_key="aggregateSha256",
        label="wave-two aggregate",
    )
    wave2_audit = _validate_wrapper(
        wave2_audit_wrapper,
        stage_id="tier1-precision-continuation-wave2-independent-audit-v1",
        inner_key="audit",
        inner_sha_key="auditSha256",
        label="wave-two audit",
    )
    state = c.proposal(root)
    proposal = state["proposal"]
    if source_aggregate.get("proposalSha256") != proposal["proposalSha256"]:
        raise c.Refusal("source wave-one proposal binding changed")
    if wave2_aggregate.get("proposalSha256") != proposal["proposalSha256"]:
        raise c.Refusal("wave-two proposal binding changed")
    analysis = state["base"].analyze_waves(
        proposal,
        [source_aggregate, wave2_aggregate],
        [source_audit, wave2_audit],
    )
    value = {
        "schemaVersion": 1,
        "stageId": "tier1-precision-continuation-wave2-analysis-v1",
        "preregistrationSha256": preregistration["preregistrationSha256"],
        "sourceWave1AggregateSha256": source_aggregate_wrapper["aggregateSha256"],
        "sourceWave1AuditSha256": source_audit_wrapper["auditSha256"],
        "wave2AggregateSha256": wave2_aggregate_wrapper["aggregateSha256"],
        "wave2AuditSha256": wave2_audit_wrapper["auditSha256"],
        "analysis": analysis,
        "additionalExecutionAutomaticallyAuthorized": False,
        "surrogateFitAuthorized": False,
        "internalHoldoutOpened": False,
        "tier2Authorized": False,
        "productionPromotionAuthorized": False,
    }
    value["analysisSha256"] = c.canonical_sha256(value)
    return value
