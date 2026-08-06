from __future__ import annotations

import copy
import importlib.util
import math
from pathlib import Path
from typing import Any


def _load_local(name: str):
    path = Path(__file__).with_name(name + ".py")
    spec = importlib.util.spec_from_file_location("wave3_v1_" + name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _state(root: Path):
    package = _load_local("package")
    core = package.load_module(root / package.WAVE2_CORE_PATH, "wave3_v1_postprocess_wave2_core")
    return package, core.proposal(root)


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
    package = _load_local("package")
    if not isinstance(wrapper, dict) or wrapper.get("stageId") != stage_id:
        raise package.Refusal(f"{label} wrapper identity changed")
    payload = {key: item for key, item in wrapper.items() if key != "payloadSha256"}
    if wrapper.get("payloadSha256") != package.canonical_sha256(payload):
        raise package.Refusal(f"{label} wrapper hash changed")
    inner = wrapper.get(inner_key)
    if not isinstance(inner, dict) or wrapper.get(inner_sha_key) != package.canonical_sha256(inner):
        raise package.Refusal(f"{label} inner payload hash changed")
    return inner


def translate_results(
    preregistration: dict[str, Any],
    results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    package = _load_local("package")
    expected = {row["caseId"]: row for row in preregistration["cases"]}
    case_count = preregistration["caseCount"]
    if len(results) != case_count or {row.get("caseId") for row in results} != set(expected):
        raise package.Refusal("partial, duplicate, or unplanned wave-three result set")
    translated = []
    for result in results:
        if not isinstance(result, dict):
            raise package.Refusal("wave-three result row is not an object")
        case = expected[result["caseId"]]
        row = copy.deepcopy(result)
        if (
            row.get("stageId") != "tier1-precision-continuation-wave3-ordinal13-execution-v1"
            or row.get("seed") != case["seed"]
            or row.get("block") != case["block"]
            or row.get("role") != case["role"]
            or row.get("photonHistories") != case["photonHistories"]
        ):
            raise package.Refusal("wave-three result provenance changed")
        if (
            row.get("status") != "COMPLETED"
            or row.get("syntaxCheckCount") != 1
            or row.get("solverExecutionCount") != 1
            or row.get("retryAllowed") is not False
            or row.get("resumeAllowed") is not False
            or row.get("fittingSurfaceExposed") is not False
        ):
            raise package.Refusal("wave-three result did not prove one successful case execution")
        supplied_content_sha = row.pop("contentSha256", None)
        if supplied_content_sha != package.canonical_sha256(row):
            raise package.Refusal("wave-three result content hash changed")
        runtime_sha = row.get("runtimeReportSha256")
        value = row.get("selectedPhotopicContributionCdM2")
        nodes = row.get("selectedNodeRadiance")
        if not _is_sha256(runtime_sha):
            raise package.Refusal("wave-three runtime report hash missing")
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(float(value))
            or value < 0
        ):
            raise package.Refusal("wave-three photopic contribution invalid")
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
            raise package.Refusal("wave-three selected-node radiance invalid")
        zero_hit = float(value) == 0.0 and all(float(node) == 0.0 for node in nodes)
        if row.get("zeroHit") is not zero_hit:
            raise package.Refusal("wave-three zero-hit semantics changed")
        for name in ("inputSha256", "radianceOutputSha256", "stdOutputSha256"):
            if not _is_sha256(row.get(name)):
                raise package.Refusal(f"wave-three {name} missing")
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


def aggregate_wave3(preregistration, results, root=None):
    package = _load_local("package")
    root = (root or package.repository_root()).resolve()
    _, state = _state(root)
    aggregate = state["base"].aggregate_wave(
        state["proposal"],
        package.WAVE,
        preregistration["geometryIds"],
        translate_results(preregistration, results),
    )
    wrapper = {
        "schemaVersion": 1,
        "stageId": "tier1-precision-continuation-wave3-aggregate-v1",
        "preregistrationSha256": preregistration["preregistrationSha256"],
        "aggregate": aggregate,
        "aggregateSha256": package.canonical_sha256(aggregate),
        "additionalExecutionAutomaticallyAuthorized": False,
    }
    wrapper["payloadSha256"] = package.canonical_sha256(wrapper)
    return wrapper


def audit_wave3(preregistration, results, aggregate_wrapper, root=None):
    package = _load_local("package")
    root = (root or package.repository_root()).resolve()
    aggregate = _validate_wrapper(
        aggregate_wrapper,
        stage_id="tier1-precision-continuation-wave3-aggregate-v1",
        inner_key="aggregate",
        inner_sha_key="aggregateSha256",
        label="wave-three aggregate",
    )
    _, state = _state(root)
    audit = state["base"].audit_wave(
        state["proposal"],
        package.WAVE,
        preregistration["geometryIds"],
        translate_results(preregistration, results),
        aggregate,
    )
    wrapper = {
        "schemaVersion": 1,
        "stageId": "tier1-precision-continuation-wave3-independent-audit-v1",
        "preregistrationSha256": preregistration["preregistrationSha256"],
        "aggregateSha256": aggregate_wrapper["aggregateSha256"],
        "audit": audit,
        "auditSha256": package.canonical_sha256(audit),
        "independentlyRecomputedFromRawSelectedNodeRadiance": True,
        "additionalExecutionAutomaticallyAuthorized": False,
    }
    wrapper["payloadSha256"] = package.canonical_sha256(wrapper)
    return wrapper


def analyze_waves(
    preregistration,
    wave1_aggregate_wrapper,
    wave1_audit_wrapper,
    wave2_aggregate_wrapper,
    wave2_audit_wrapper,
    wave3_aggregate_wrapper,
    wave3_audit_wrapper,
    root=None,
):
    package = _load_local("package")
    root = (root or package.repository_root()).resolve()
    wave1_aggregate = _validate_wrapper(
        wave1_aggregate_wrapper,
        stage_id="tier1-precision-continuation-wave1-aggregate-v5",
        inner_key="aggregate",
        inner_sha_key="aggregateSha256",
        label="wave-one aggregate",
    )
    wave1_audit = _validate_wrapper(
        wave1_audit_wrapper,
        stage_id="tier1-precision-continuation-wave1-independent-audit-v5",
        inner_key="audit",
        inner_sha_key="auditSha256",
        label="wave-one audit",
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
    wave3_aggregate = _validate_wrapper(
        wave3_aggregate_wrapper,
        stage_id="tier1-precision-continuation-wave3-aggregate-v1",
        inner_key="aggregate",
        inner_sha_key="aggregateSha256",
        label="wave-three aggregate",
    )
    wave3_audit = _validate_wrapper(
        wave3_audit_wrapper,
        stage_id="tier1-precision-continuation-wave3-independent-audit-v1",
        inner_key="audit",
        inner_sha_key="auditSha256",
        label="wave-three audit",
    )
    _, state = _state(root)
    proposal = state["proposal"]
    for label, aggregate in (
        ("wave one", wave1_aggregate),
        ("wave two", wave2_aggregate),
        ("wave three", wave3_aggregate),
    ):
        if aggregate.get("proposalSha256") != proposal["proposalSha256"]:
            raise package.Refusal(f"{label} proposal binding changed")
    analysis = state["base"].analyze_waves(
        proposal,
        [wave1_aggregate, wave2_aggregate, wave3_aggregate],
        [wave1_audit, wave2_audit, wave3_audit],
    )
    value = {
        "schemaVersion": 1,
        "stageId": "tier1-precision-continuation-wave3-analysis-v1",
        "preregistrationSha256": preregistration["preregistrationSha256"],
        "wave1AggregateSha256": wave1_aggregate_wrapper["aggregateSha256"],
        "wave1AuditSha256": wave1_audit_wrapper["auditSha256"],
        "wave2AggregateSha256": wave2_aggregate_wrapper["aggregateSha256"],
        "wave2AuditSha256": wave2_audit_wrapper["auditSha256"],
        "wave3AggregateSha256": wave3_aggregate_wrapper["aggregateSha256"],
        "wave3AuditSha256": wave3_audit_wrapper["auditSha256"],
        "analysis": analysis,
        "additionalExecutionAutomaticallyAuthorized": False,
        "surrogateFitAuthorized": False,
        "internalHoldoutOpened": False,
        "tier2Authorized": False,
        "productionPromotionAuthorized": False,
    }
    value["analysisSha256"] = package.canonical_sha256(value)
    return value
