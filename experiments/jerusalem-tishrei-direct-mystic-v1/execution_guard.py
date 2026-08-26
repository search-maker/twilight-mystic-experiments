#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

STAGE_ID = "cross-geometry-pilot-v1"
PURPOSE = "jerusalem-tishrei-direct-mystic-v1"
BATCH_ID = "jerusalem-tishrei-three-star-direct-mystic-v1"
EXPECTED_CASES = 12
EXPECTED_PHOTONS = 240_000_000
EXPECTED_EVENT_DEP = 5.2416836635666755
EXPECTED_AOD550 = 0.22
EXPECTED_ELEVATION_M = 800.0
EXPECTED_FIELD_FACTOR = 3.14
EXPECTED_ALBEDO = 0.15
EXPECTED_ALIS_IS_NM = 405.0
EXPECTED_APPLICATION_SHA = "e2d5b761206b6223526f6f79fcb0af5f6de3ba06"
EXPECTED_HUMAN_THRESHOLD_GIT_BLOB_SHA1 = "bb4cd0ff02159ecffe276022cec9d292c7a434a3"
EXPECTED_DERIVED_CHANNELS_GIT_BLOB_SHA1 = "ccfd04d4c21188966351f4257e92893d7ce340c7"
EXPECTED_EVIDENCE_ARTIFACT_ID = 9612259358
EXPECTED_EVIDENCE_DIGEST = "sha256:d43120ad60d2e4a502023cd187bbeffecd6364d4edc975c14c84432c3c8097c5"
EXPECTED_RUNTIME = {
    "uvspecSha256": "2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3",
    "uvspecHelpSha256": "868aea5af762d968f6f62c4e1472916d25232ed9cab5be112d753b0823d20548",
    "libRadtranDataTreeSha256": "ad30b49177e9c84e46497d69faf0c75e466996b0d0003f1de210289ae9f847d7",
    "atmosphereSha256": "dab26290ed81c762ed0c607e5dc2d53393c1462a0c3a528bc5e3f5935191cfb5",
    "runtimeLockRawSha256": "3b5fbec964642b04c73a6423b3355dbcc4ba5e84f9614f6d74420491bacc20c5",
}
EXPECTED_GEOMETRIES = {
    "tishrei-antares-hr6134": "HR 6134",
    "tishrei-rasalhague-hr6556": "HR 6556",
    "tishrei-gamma-cyg-hr7796": "HR 7796",
}
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._:-]{2,159}$")


class Refusal(RuntimeError):
    def __init__(self, code: str, reason: str, detail: Any | None = None) -> None:
        super().__init__(reason)
        self.code = code
        self.reason = reason
        self.detail = detail

    def as_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": 1,
            "stageId": STAGE_ID,
            "scientificPurpose": PURPOSE,
            "status": "REFUSED_BEFORE_SYNTAX_OR_SOLVER",
            "code": self.code,
            "reason": self.reason,
            "detail": self.detail,
        }


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except Exception as exc:
        raise Refusal("json", f"cannot read JSON: {path}", str(exc)) from exc
    if not isinstance(value, dict):
        raise Refusal("json-shape", f"expected object: {path}")
    return value


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def git_blob_sha1(root: Path, rel: str) -> str:
    try:
        return git(root, "rev-parse", f"HEAD:{Path(rel).as_posix()}")
    except Exception as exc:
        raise Refusal("git-blob", f"cannot resolve Git blob for {rel}", str(exc)) from exc


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise Refusal("module", f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def require_file(root: Path, rel: str, name: str) -> Path:
    p = Path(rel)
    if p.is_absolute() or ".." in p.parts:
        raise Refusal("path", f"invalid {name} path", rel)
    q = root / p
    if not q.is_file():
        raise Refusal("missing-file", f"missing {name}", rel)
    return q


def near(actual: Any, expected: float, tol: float = 1e-12) -> bool:
    return isinstance(actual, (int, float)) and not isinstance(actual, bool) and math.isfinite(float(actual)) and abs(float(actual) - expected) <= tol


def require_exact_path(value: Any, root: str, path: str, code: str, case_id: str) -> None:
    if value != {"root": root, "path": path}:
        raise Refusal(code, "normalized data path changed", {"caseId": case_id, "actual": value, "expected": {"root": root, "path": path}})


def validate(args: argparse.Namespace) -> dict[str, Any]:
    root = args.repository_root.resolve()
    app_root = args.application_root.resolve()

    expected_context = {
        "GITHUB_ACTIONS": "true",
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_RUN_ATTEMPT": "1",
    }
    stale_context = {k: (os.getenv(k), v) for k, v in expected_context.items() if os.getenv(k) != v}
    if stale_context:
        raise Refusal("github-context", "not exact first-attempt workflow_dispatch context", stale_context)
    if args.application_sha != EXPECTED_APPLICATION_SHA or git(app_root, "rev-parse", "HEAD") != EXPECTED_APPLICATION_SHA:
        raise Refusal("application-sha", "application checkout is not exact frozen SHA")
    if not ID_RE.fullmatch(args.execution_key):
        raise Refusal("execution-key", "invalid execution key", args.execution_key)
    if args.authorization_ordinal < 1:
        raise Refusal("authorization-ordinal", "authorization ordinal must be positive")

    paths = {
        "authorization": args.authorization,
        "proposal": args.proposal,
        "evidence": args.evidence,
        "analysisContract": args.analysis_contract,
        "proposalAdapter": args.proposal_adapter,
        "executionAdapter": args.execution_adapter,
        "executionWorkflow": args.execution_workflow,
        "runtimeLock": args.runtime_lock,
        "plan": args.plan,
        "analysisDriver": args.analysis_driver,
        "visibilityHelper": args.visibility_helper,
        "derivedChannels": args.derived_channels,
        "executor": args.executor,
        "aggregate": args.aggregate,
        "audit": args.audit,
        "authorizationProposalBuilder": args.authorization_proposal_builder,
    }
    abs_paths = {k: require_file(root, v, k) for k, v in paths.items()}
    human_threshold = require_file(app_root, args.human_threshold, "humanThreshold")

    human_blob = git_blob_sha1(app_root, args.human_threshold)
    derived_blob = git_blob_sha1(root, args.derived_channels)
    if human_blob != EXPECTED_HUMAN_THRESHOLD_GIT_BLOB_SHA1:
        raise Refusal("human-threshold-git-blob", "frozen human-threshold Git blob mismatch", human_blob)
    if derived_blob != EXPECTED_DERIVED_CHANNELS_GIT_BLOB_SHA1:
        raise Refusal("derived-channels-git-blob", "frozen derived-channel Git blob mismatch", derived_blob)

    manifest = load_json(abs_paths["proposal"])
    evidence = load_json(abs_paths["evidence"])
    contract = load_json(abs_paths["analysisContract"])
    authorization = load_json(abs_paths["authorization"])
    adapter = load_module("jerusalem_tishrei_proposal_adapter", abs_paths["proposalAdapter"])
    try:
        adapter.validate_manifest(manifest)
    except Exception as exc:
        raise Refusal("manifest-adapter-validation", "frozen adapter rejected manifest", str(exc)) from exc

    if manifest.get("stageId") != STAGE_ID or manifest.get("batchId") != BATCH_ID or manifest.get("proposalOnly") is not True or manifest.get("scientificExecution") is not False:
        raise Refusal("manifest-header", "wrong manifest execution boundary")
    event = manifest.get("preregisteredEvent") or {}
    event_atmosphere = event.get("atmosphere") or {}
    event_semantics = event.get("threeStarSemantics") or {}
    if not near(event.get("sunDepressionDeg"), EXPECTED_EVENT_DEP) or not near(event_atmosphere.get("aod550"), EXPECTED_AOD550):
        raise Refusal("event", "frozen event depression/AOD changed", event)
    if not near(event_semantics.get("fieldFactorBaseline"), EXPECTED_FIELD_FACTOR):
        raise Refusal("field-factor", "F=3.14 baseline changed")
    if event_semantics.get("requiredCount") != 3 or event_semantics.get("stabilitySeconds") != 60 or event_semantics.get("magnitudeBasis") != "effective" or not near(event_semantics.get("magnitudeThreshold"), 1.7):
        raise Refusal("three-star-semantics", "frozen Three-Star semantics changed", event_semantics)

    runtime = manifest.get("runtime") or {}
    runtime_stale = {k: (runtime.get(k), v) for k, v in EXPECTED_RUNTIME.items() if runtime.get(k) != v}
    if runtime_stale:
        raise Refusal("runtime-identity", "frozen runtime identity changed", runtime_stale)

    frozen = manifest.get("frozenInputs") or {}
    if frozen.get("wavelengthDomainNm") != [380, 780] or frozen.get("molecularAbsorption") != "crs" or frozen.get("mcSpherical") != "1D":
        raise Refusal("frozen-rt-contract", "frozen RT contract changed", frozen)
    if not near(frozen.get("alisSpectralImportanceSamplingNm"), EXPECTED_ALIS_IS_NM) or not near(frozen.get("albedo"), EXPECTED_ALBEDO):
        raise Refusal("frozen-numerics", "frozen ALIS/albedo inputs changed", frozen)
    data_paths = frozen.get("dataPaths") or {}
    if data_paths.get("solarFlux") != {"root": "libRadtranData", "path": "solar_flux/atlas_plus_modtran"} or data_paths.get("wavelengthGrid") != {"root": "repository", "path": "experiments/reference-vroom-v1/wavelength-grid.dat"} or data_paths.get("atmosphere") != {"root": "libRadtranData", "path": "atmmod/afglus.dat"}:
        raise Refusal("frozen-data-paths", "frozen data paths changed", data_paths)

    geometries = manifest.get("geometries")
    cases = manifest.get("cases")
    limits = manifest.get("limits") or {}
    if not isinstance(geometries, list) or len(geometries) != 3:
        raise Refusal("geometry-count", "expected exactly 3 geometries")
    if not isinstance(cases, list) or len(cases) != EXPECTED_CASES:
        raise Refusal("case-count", "expected exactly 12 cases")
    geometry_by_id = {g.get("geometryId"): g for g in geometries if isinstance(g, dict)}
    if set(geometry_by_id) != set(EXPECTED_GEOMETRIES):
        raise Refusal("geometry-ids", "wrong frozen geometry set", sorted(geometry_by_id))
    geometry_by_catalog: dict[str, dict[str, Any]] = {}
    for geometry_id, catalog_id in EXPECTED_GEOMETRIES.items():
        g = geometry_by_id[geometry_id]
        if (g.get("target") or {}).get("catalogId") != catalog_id:
            raise Refusal("geometry-target", "geometry target identity changed", {"geometryId": geometry_id, "target": g.get("target")})
        if not near(g.get("sunDepressionDeg"), EXPECTED_EVENT_DEP) or not near(g.get("observerElevationM"), EXPECTED_ELEVATION_M) or not near(g.get("aod550"), EXPECTED_AOD550):
            raise Refusal("geometry-physics", "frozen geometry physics changed", geometry_id)
        geometry_by_catalog[catalog_id] = g

    if limits != {"maximumCases": 12, "maximumParallel": 6, "maximumConfiguredMcPhotonsSum": EXPECTED_PHOTONS, "perCaseTimeoutSeconds": 900}:
        raise Refusal("limits", "frozen limits changed", limits)
    if [c.get("ordinal") for c in cases if isinstance(c, dict)] != list(range(1, 13)):
        raise Refusal("case-ordinals", "case ordinals must be exactly 1..12")
    case_ids = [c.get("caseId") for c in cases if isinstance(c, dict)]
    seeds = [c.get("seed") for c in cases if isinstance(c, dict)]
    if len(set(case_ids)) != 12 or len(set(seeds)) != 12:
        raise Refusal("case-identity", "case IDs and seeds must be globally unique")
    if any(c.get("photonHistories") != 20_000_000 for c in cases if isinstance(c, dict)) or sum(c.get("photonHistories", 0) for c in cases if isinstance(c, dict)) != EXPECTED_PHOTONS:
        raise Refusal("photon-accounting", "expected exactly 20M photons per case and 240M total")
    if Counter(c.get("method") for c in cases if isinstance(c, dict)) != Counter({"alis": 6, "reference-vroom": 6}):
        raise Refusal("method-count", "expected six ALIS and six reference-VROOM cases")
    if any(c.get("groupId") not in geometry_by_id for c in cases if isinstance(c, dict)):
        raise Refusal("case-group", "a case references a non-frozen geometry")

    normalized_by_group: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for case in cases:
        try:
            resolved_case, geometry = adapter.resolve_case(manifest, case["caseId"])
            inputs = adapter.normalized_inputs(manifest, resolved_case, geometry)
        except Exception as exc:
            raise Refusal("normalized-inputs", "adapter could not resolve frozen case", {"caseId": case.get("caseId"), "reason": str(exc)}) from exc
        case_id = inputs["caseId"]
        normalized_by_group[inputs["groupId"]].append(inputs)
        expected_numeric = {
            "sunDepressionDeg": EXPECTED_EVENT_DEP,
            "observerElevationM": EXPECTED_ELEVATION_M,
            "aod550": EXPECTED_AOD550,
            "albedo": EXPECTED_ALBEDO,
            "alisSpectralImportanceSamplingNm": EXPECTED_ALIS_IS_NM,
        }
        stale_numeric = {k: (inputs.get(k), v) for k, v in expected_numeric.items() if not near(inputs.get(k), v)}
        if stale_numeric:
            raise Refusal("normalized-physics", "normalized physical input changed", {"caseId": case_id, "stale": stale_numeric})
        if inputs.get("mcSpherical") != "1D" or inputs.get("molecularAbsorption") != "crs" or inputs.get("wavelengthDomainNm") != [380, 780]:
            raise Refusal("normalized-rt-contract", "normalized RT contract changed", {"caseId": case_id})
        require_exact_path(inputs.get("atmosphere"), "libRadtranData", "atmmod/afglus.dat", "normalized-atmosphere", case_id)
        require_exact_path(inputs.get("solarFlux"), "libRadtranData", "solar_flux/atlas_plus_modtran", "normalized-solar-flux", case_id)
        require_exact_path(inputs.get("wavelengthGrid"), "repository", "experiments/reference-vroom-v1/wavelength-grid.dat", "normalized-wavelength-grid", case_id)

    if set(normalized_by_group) != set(geometry_by_id):
        raise Refusal("group-set", "case groups do not exactly match geometry IDs", {"cases": sorted(normalized_by_group), "geometries": sorted(geometry_by_id)})
    expected_signature = Counter({("alis", 1): 1, ("alis", 2): 1, ("reference-vroom", 1): 1, ("reference-vroom", 2): 1})
    for group_id, group_cases in normalized_by_group.items():
        signature = Counter((c["method"], c["block"]) for c in group_cases)
        if len(group_cases) != 4 or signature != expected_signature:
            raise Refusal("group-replicates", "each geometry must have one block 1 and one block 2 per method", {"groupId": group_id, "count": len(group_cases), "signature": {f"{k[0]}:{k[1]}": v for k, v in signature.items()}})

    source = evidence.get("source") or {}
    if source.get("artifactId") != EXPECTED_EVIDENCE_ARTIFACT_ID or source.get("artifactDigest") != EXPECTED_EVIDENCE_DIGEST:
        raise Refusal("evidence-source", "event evidence provenance changed", source)
    ev = evidence.get("event") or {}
    if evidence.get("applicationMainSha") != EXPECTED_APPLICATION_SHA or not near(ev.get("sunDepressionDeg"), EXPECTED_EVENT_DEP) or not near(ev.get("observerElevationM"), EXPECTED_ELEVATION_M) or not near(ev.get("aod550"), EXPECTED_AOD550) or not near(ev.get("fieldFactor"), EXPECTED_FIELD_FACTOR):
        raise Refusal("evidence-event", "event evidence boundary changed", ev)
    if ev.get("requiredCount") != 3 or ev.get("stabilitySeconds") != 60 or ev.get("magnitudeBasis") != "effective" or not near(ev.get("magnitudeThreshold"), 1.7):
        raise Refusal("evidence-semantics", "event evidence Three-Star semantics changed", ev)
    stars = evidence.get("stars")
    if not isinstance(stars, list) or {s.get("catalogId") for s in stars if isinstance(s, dict)} != set(geometry_by_catalog):
        raise Refusal("evidence-stars", "event evidence star set changed")
    for star in stars:
        catalog_id = star["catalogId"]
        g = geometry_by_catalog[catalog_id]
        eg = star.get("eventGeometry") or {}
        if not near(eg.get("targetAltitudeDeg"), float(g["targetAltitudeDeg"])) or not near(eg.get("relativeAzimuthDeg"), float(g["relativeAzimuthDeg"])):
            raise Refusal("evidence-geometry", "evidence/manifest geometry mismatch", catalog_id)
        if not near((star.get("stellar") or {}).get("apparentVMagAtEye"), float(g["levelBEventSample"]["apparentVMagAtEye"])) or not near((star.get("visibility") or {}).get("limitingVMagnitude"), float(g["levelBEventSample"]["limitingVMagnitude"])) or not near((star.get("visibility") or {}).get("visibilityMarginMag"), float(g["levelBEventSample"]["visibilityMarginMag"])):
            raise Refusal("evidence-level-b-sample", "evidence/manifest Level-B sample mismatch", catalog_id)
        channels = star.get("skyChannels") or {}
        for key in ("photopic", "scotopic", "johnsonV"):
            channel = channels.get(key) or {}
            if channel.get("available") is not True or not isinstance(channel.get("value"), (int, float)) or not math.isfinite(float(channel["value"])) or float(channel["value"]) <= 0:
                raise Refusal("evidence-channel", f"missing or invalid frozen {key} channel", catalog_id)
        spectral = channels.get("spectral") or {}
        if spectral.get("available") is not False or spectral.get("reason") != "VALIDATED_V3_PRIMARY_PROVIDER_SPECTRAL_RUNTIME_NOT_IMPLEMENTED":
            raise Refusal("evidence-spectral-boundary", "Level-B spectral boundary changed", catalog_id)
    comparison_boundary = evidence.get("comparisonBoundary") or {}
    if comparison_boundary.get("fullSpectrumLevelBValidationClaimAllowed") is not False or comparison_boundary.get("noParameterTuning") is not True or comparison_boundary.get("productionAuthorized") is not False:
        raise Refusal("evidence-claim-boundary", "event evidence claim boundary changed", comparison_boundary)

    if contract.get("analysisId") != "jerusalem-tishrei-direct-mystic-level-b-comparison-v1" or contract.get("scientificExecution") is not False:
        raise Refusal("analysis-contract", "wrong analysis contract header")
    contract_inputs = contract.get("inputs") or {}
    if contract_inputs.get("applicationMainSha") != EXPECTED_APPLICATION_SHA or contract_inputs.get("humanThresholdGitBlobSha1") != EXPECTED_HUMAN_THRESHOLD_GIT_BLOB_SHA1 or contract_inputs.get("derivedChannelsGitBlobSha1") != EXPECTED_DERIVED_CHANNELS_GIT_BLOB_SHA1:
        raise Refusal("analysis-bindings", "analysis code/application bindings changed", contract_inputs)
    sky_only = contract.get("skyOnlyVisibilitySubstitution") or {}
    if sky_only.get("fieldFactor") != EXPECTED_FIELD_FACTOR or sky_only.get("branch") != "full" or sky_only.get("noParameterTuning") is not True:
        raise Refusal("analysis-F", "analysis F/branch/no-tuning boundary changed", sky_only)
    alis_role = (contract.get("methodRoles") or {}).get("alis") or {}
    if alis_role.get("expectedOutputGrid") != {"nodeCount": 8001, "startNm": 380.0, "stopNm": 780.0, "stepNm": 0.05}:
        raise Refusal("alis-grid", "full-spectrum ALIS grid contract changed", alis_role.get("expectedOutputGrid"))
    vroom_role = (contract.get("methodRoles") or {}).get("referenceVroom") or {}
    if not str(vroom_role.get("forbiddenUse", "")).startswith("do not derive"):
        raise Refusal("vroom-boundary", "sparse VROOM full-channel prohibition changed")
    structural = contract.get("structuralRequirements") or {}
    expected_structural = {
        "all12CasesExactlyOnce": True,
        "syntaxCheckExactlyOncePerCase": True,
        "solverExecutionExactlyOncePerCase": True,
        "retryAllowed": False,
        "resumeAllowed": False,
        "rerunAllowed": False,
        "runtimeIdentityMustMatchFrozenLock": True,
        "aodMustRemainAt550nm": True,
        "aod550": EXPECTED_AOD550,
        "observerElevationM": 800,
        "surfaceAlbedo": EXPECTED_ALBEDO,
        "mcSpherical": "1D",
        "atmosphere": "AFGLUS",
        "scalarRadianceBoundary": True,
    }
    structural_stale = {k: (structural.get(k), v) for k, v in expected_structural.items() if structural.get(k) != v}
    if structural_stale:
        raise Refusal("analysis-structural", "analysis structural requirements changed", structural_stale)
    claim = contract.get("claimBoundary") or {}
    if claim.get("noParameterTuning") is not True or claim.get("fullSpectrumLevelBValidated") is not False or claim.get("productionAuthorized") is not False or claim.get("measuredRealSkyValidated") is not False or claim.get("humanFirstSeeingValidated") is not False or claim.get("pandoraOpened") is not False:
        raise Refusal("analysis-boundary", "analysis claim boundary changed", claim)

    if "aerosol_set_tau_at_wvl 550" not in abs_paths["executionAdapter"].read_text():
        raise Refusal("aod-wavelength", "execution adapter no longer binds aerosol tau at 550 nm")

    required_auth = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "scientificPurpose": PURPOSE,
        "authorized": True,
        "scientificExecution": True,
        "scientificDiagnostic": True,
        "successDoesNotAuthorizeProduction": True,
        "executionKey": args.execution_key,
        "batchId": BATCH_ID,
        "proposalPath": args.proposal,
        "proposalRawSha256": raw_sha256(abs_paths["proposal"]),
        "levelBEvidenceRawSha256": raw_sha256(abs_paths["evidence"]),
        "analysisContractRawSha256": raw_sha256(abs_paths["analysisContract"]),
        "proposalAdapterRawSha256": raw_sha256(abs_paths["proposalAdapter"]),
        "executionAdapterRawSha256": raw_sha256(abs_paths["executionAdapter"]),
        "executionWorkflowRawSha256": raw_sha256(abs_paths["executionWorkflow"]),
        "runtimeLockRawSha256": raw_sha256(abs_paths["runtimeLock"]),
        "planRawSha256": raw_sha256(abs_paths["plan"]),
        "analysisDriverRawSha256": raw_sha256(abs_paths["analysisDriver"]),
        "visibilityHelperRawSha256": raw_sha256(abs_paths["visibilityHelper"]),
        "derivedChannelsRawSha256": raw_sha256(abs_paths["derivedChannels"]),
        "humanThresholdRawSha256": raw_sha256(human_threshold),
        "executorRawSha256": raw_sha256(abs_paths["executor"]),
        "aggregateRawSha256": raw_sha256(abs_paths["aggregate"]),
        "auditRawSha256": raw_sha256(abs_paths["audit"]),
        "authorizationProposalBuilderRawSha256": raw_sha256(abs_paths["authorizationProposalBuilder"]),
        "authorizationOrdinal": args.authorization_ordinal,
        "consumed": False,
        "exactAuthorizationCommit": None,
    }
    stale_auth = {k: (authorization.get(k), v) for k, v in required_auth.items() if authorization.get(k) != v}
    if stale_auth:
        raise Refusal("authorization-stale", "authorization disabled, missing, or hash-stale", stale_auth)

    head = git(root, "rev-parse", "HEAD")
    parent = git(root, "rev-parse", "HEAD^")
    if head != args.authorization_ref:
        raise Refusal("authorization-ref", "HEAD is not supplied authorization ref", {"head": head, "input": args.authorization_ref})
    if authorization.get("exactAuthorizationParentCommit") != parent:
        raise Refusal("authorization-parent", "authorization parent mismatch", {"actual": parent, "bound": authorization.get("exactAuthorizationParentCommit")})
    changed = git(root, "diff", "--name-only", parent, head).splitlines()
    if changed != [args.authorization]:
        raise Refusal("one-purpose-commit", "authorization commit must change exactly the active authorization file", changed)

    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "scientificPurpose": PURPOSE,
        "status": "AUTHORIZED",
        "batchId": BATCH_ID,
        "executionKey": args.execution_key,
        "authorizationRef": head,
        "authorizationParentCommit": parent,
        "authorizationOrdinal": args.authorization_ordinal,
        "proposalPath": args.proposal,
        "proposalRawSha256": raw_sha256(abs_paths["proposal"]),
        "levelBEvidenceRawSha256": raw_sha256(abs_paths["evidence"]),
        "analysisContractRawSha256": raw_sha256(abs_paths["analysisContract"]),
        "executionAdapterRawSha256": raw_sha256(abs_paths["executionAdapter"]),
        "runtimeLockRawSha256": raw_sha256(abs_paths["runtimeLock"]),
        "executionWorkflowRawSha256": raw_sha256(abs_paths["executionWorkflow"]),
        "caseCount": EXPECTED_CASES,
        "configuredMcPhotonsSum": EXPECTED_PHOTONS,
        "maximumParallel": 6,
        "perCaseTimeoutSeconds": 900,
        "applicationSha": EXPECTED_APPLICATION_SHA,
        "humanThresholdGitBlobSha1": human_blob,
        "derivedChannelsGitBlobSha1": derived_blob,
        "boundary": "one-purpose exact-event authorization verified before syntax check or solver execution; F=3.14 and no-tuning boundary preserved",
    }


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repository-root", type=Path, default=Path("."))
    p.add_argument("--application-root", type=Path, required=True)
    p.add_argument("--application-sha", required=True)
    for name in ("authorization", "proposal", "evidence", "analysis-contract", "proposal-adapter", "execution-adapter", "execution-workflow", "runtime-lock", "plan", "analysis-driver", "visibility-helper", "derived-channels", "executor", "aggregate", "audit", "authorization-proposal-builder"):
        p.add_argument(f"--{name}", required=True)
    p.add_argument("--human-threshold", required=True)
    p.add_argument("--authorization-ref", required=True)
    p.add_argument("--execution-key", required=True)
    p.add_argument("--authorization-ordinal", type=int, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    try:
        report = validate(args)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump(report))
        print(dump(report), end="")
        return 0
    except Exception as exc:
        report = exc.as_dict() if isinstance(exc, Refusal) else Refusal("unexpected", str(exc)).as_dict()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump(report))
        print(dump(report), end="", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
