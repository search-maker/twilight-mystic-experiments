from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Callable

STAGE = "aerosol-vertical-profile-sensitivity-v1"
EXPECTED_GUARD_STATUS = "EXACT_ONE_USE_AVPS_V1_DISPATCH_AUTHORIZED"


class ExecutionRefusal(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ExecutionRefusal(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def parse_spectrum(path: Path) -> tuple[list[float], list[float]]:
    wavelengths: list[float] = []
    values: list[float] = []
    for raw in path.read_text().splitlines():
        parts = raw.split()
        if len(parts) < 2:
            continue
        try:
            wavelengths.append(float(parts[0]))
            values.append(float(parts[-1]))
        except ValueError:
            continue
    return wavelengths, values


def load_contract(stage_dir: Path) -> dict[str, Any]:
    path = stage_dir / "execution-contract.review.json"
    contract = json.loads(path.read_text())
    if contract.get("stageId") != f"{STAGE}-execution-contract":
        raise ExecutionRefusal("execution contract stage drift")
    if contract.get("status") != "FROZEN_REVIEW_ONLY_EXECUTION_TRANSPORT_NOT_AUTHORIZED":
        raise ExecutionRefusal("execution contract status drift")
    if any(contract.get(key) is not False for key in (
        "scientificOrdinalAllocated", "authorizationCreated", "dispatchCreated",
        "scientificExecutionAuthorized", "solverExecutionAuthorized", "resultOpeningAuthorized",
    )):
        raise ExecutionRefusal("review execution contract crossed authorization/execution boundary")
    return contract


def validate_bound_sources(repository_root: Path, contract: dict[str, Any]) -> dict[str, Path]:
    bindings = contract["sourceBindings"]
    rows = (
        ("protocolPath", "protocolGitBlobSha1"),
        ("executionCandidatePath", "executionCandidateGitBlobSha1"),
        ("executionPackagePath", "executionPackageGitBlobSha1"),
        ("adapterPath", "adapterGitBlobSha1"),
        ("analysisPath", "analysisGitBlobSha1"),
        ("levelBAnalysisPath", "levelBAnalysisGitBlobSha1"),
        ("runtimeOverlayPath", "runtimeOverlayGitBlobSha1"),
        ("processGroupRunnerPath", "processGroupRunnerGitBlobSha1"),
        ("r8DerivedChannelsPath", "r8DerivedChannelsGitBlobSha1"),
        ("r8AnalysisPath", "r8AnalysisGitBlobSha1"),
        ("wavelengthGridPath", "wavelengthGridGitBlobSha1"),
    )
    resolved: dict[str, Path] = {}
    for path_key, blob_key in rows:
        path = repository_root / bindings[path_key]
        if git_blob_sha1(path) != bindings[blob_key]:
            raise ExecutionRefusal(f"bound source bytes changed: {path}")
        resolved[path_key] = path
    executor_path = repository_root / bindings["executorPath"]
    if git_blob_sha1(executor_path) != bindings["executorGitBlobSha1"]:
        raise ExecutionRefusal("executor byte binding drift")
    resolved["executorPath"] = executor_path
    runtime_lock = repository_root / contract["runtimeIdentity"]["runtimeLockPath"]
    if git_blob_sha1(runtime_lock) != contract["runtimeIdentity"]["runtimeLockGitBlobSha1"]:
        raise ExecutionRefusal("runtime lock Git blob drift")
    if sha256_file(runtime_lock) != contract["runtimeIdentity"]["runtimeLockRawSha256"]:
        raise ExecutionRefusal("runtime lock raw SHA drift")
    return resolved


def validate_authorization(auth: dict[str, Any], contract: dict[str, Any]) -> None:
    if auth.get("stageId") != STAGE or auth.get("status") != "AUTHORIZED_PENDING_SEPARATE_DISPATCH":
        raise ExecutionRefusal("authorization stage/status drift")
    if auth.get("caseCount") != contract["expectedCaseCount"] or auth.get("commonRandomNumberGroupCount") != contract["expectedGroupCount"]:
        raise ExecutionRefusal("authorization case/group cardinality drift")
    if auth.get("statesPerGroup") != contract["expectedStatesPerGroup"]:
        raise ExecutionRefusal("authorization state cardinality drift")
    if auth.get("photonHistoriesPerCase") != contract["photonHistoriesPerCase"]:
        raise ExecutionRefusal("authorization photon budget drift")
    if auth.get("disabledExecutionPackageCanonicalSha256") != contract["disabledExecutionPackageCanonicalSha256"]:
        raise ExecutionRefusal("authorization disabled-package binding drift")
    if auth.get("exactAfglProfileTauSha256") != contract["exactAfglProfileTauSha256"]:
        raise ExecutionRefusal("authorization exact-AFGL profile binding drift")
    if auth.get("stagedOpacDataTreeSha256") != contract["runtimeIdentity"]["augmentedDataTreeSha256"]:
        raise ExecutionRefusal("authorization OPAC data-tree binding drift")
    if auth.get("uvspecSha256") != contract["runtimeIdentity"]["uvspecSha256"]:
        raise ExecutionRefusal("authorization uvspec binding drift")
    if auth.get("scientificExecutionAuthorized") is not True or auth.get("solverExecutionAuthorized") is not True:
        raise ExecutionRefusal("authorization does not permit separate science dispatch")
    for key in ("dispatchAuthorized", "resultOpeningAuthorized", "automaticDispatch", "productionAuthorized", "taylorOrJerusalemFitAuthorized"):
        if auth.get(key) is not False:
            raise ExecutionRefusal(f"authorization crossed boundary: {key}")


def validate_guard(guard: dict[str, Any], auth: dict[str, Any], execution_contract_blob: str) -> None:
    if guard.get("status") != EXPECTED_GUARD_STATUS:
        raise ExecutionRefusal("execution guard did not authorize AVPS v1")
    if guard.get("solverExecutionPermittedNow") is not True:
        raise ExecutionRefusal("execution guard did not permit solver")
    if guard.get("workflowRunAttempt") != 1:
        raise ExecutionRefusal("workflow attempt must be exactly 1")
    if guard.get("executionDesignCanonicalSha256") != auth.get("executionDesignCanonicalSha256"):
        raise ExecutionRefusal("guard/authorization design binding drift")
    if guard.get("authorizationDocumentSha256") != canonical_sha256(auth):
        raise ExecutionRefusal("guard/authorization document binding drift")
    if guard.get("executionContractGitBlobSha1") != execution_contract_blob:
        raise ExecutionRefusal("guard/execution-contract byte binding drift")
    if guard.get("authorizationPrDraftOpenUnmerged") is not True:
        raise ExecutionRefusal("authorization PR must remain Draft/open/unmerged")
    if guard.get("authorizationTimeSeedRecheckPassed") is not True:
        raise ExecutionRefusal("authorization-time seed recheck must pass")
    if guard.get("augmentedDataTreeSha256") != auth.get("stagedOpacDataTreeSha256"):
        raise ExecutionRefusal("guard augmented data-tree binding drift")
    if guard.get("githubRerun") is not False or guard.get("retryAllowed") is not False or guard.get("resumeAllowed") is not False:
        raise ExecutionRefusal("rerun/retry/resume forbidden")
    for key in ("scientificOrdinal", "workflowRunId"):
        value = guard.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ExecutionRefusal(f"invalid guard identity: {key}")
    if guard.get("scientificOrdinal") != auth.get("scientificOrdinal"):
        raise ExecutionRefusal("guard/authorization scientific ordinal drift")


def validate_runtime(runtime: dict[str, Any], contract: dict[str, Any], uvspec: Path) -> None:
    if runtime.get("scientificSolverExecuted") is not False:
        raise ExecutionRefusal("runtime identity must be pre-solver")
    expected = contract["runtimeIdentity"]
    mapping = {
        "runtimeLockRawSha256": "runtimeLockRawSha256",
        "uvspecSha256": "uvspecSha256",
        "uvspecHelpSha256": "uvspecHelpSha256",
        "libRadtranDataTreeSha256": "augmentedDataTreeSha256",
        "atmosphereSha256": "atmosphereSha256",
    }
    for runtime_key, contract_key in mapping.items():
        if runtime.get(runtime_key) != expected.get(contract_key):
            raise ExecutionRefusal(f"runtime identity drift: {runtime_key}")
    if runtime.get("exactPackageSpec") not in (None, expected.get("exactPackageSpec")):
        raise ExecutionRefusal("runtime package spec drift")
    if sha256_file(uvspec) != expected["uvspecSha256"]:
        raise ExecutionRefusal("uvspec byte hash drift")


def execute_case(
    repository_root: Path,
    authorization_path: Path,
    guard_report_path: Path,
    runtime_report_path: Path,
    case_id: str,
    data_dir: Path,
    output_root: Path,
    uvspec: Path,
    *,
    allow_execution: bool = False,
    runner: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if not allow_execution:
        raise ExecutionRefusal("explicit allow_execution=True required")

    stage_dir = repository_root / "experiments" / STAGE
    contract_path = stage_dir / "execution-contract.review.json"
    contract = load_contract(stage_dir)
    sources = validate_bound_sources(repository_root, contract)
    auth = json.loads(authorization_path.read_text())
    validate_authorization(auth, contract)
    guard = json.loads(guard_report_path.read_text())
    validate_guard(guard, auth, git_blob_sha1(contract_path))
    runtime = json.loads(runtime_report_path.read_text())
    validate_runtime(runtime, contract, uvspec)

    adapter = load_module("avps_adapter_for_executor", sources["adapterPath"])
    derived = load_module("avps_bound_r8_derived", sources["r8DerivedChannelsPath"])
    process_runner = load_module("avps_bound_process_runner", sources["processGroupRunnerPath"])
    case = adapter.authorized_case(case_id, auth)

    prepared_files = adapter.prepare_case_files(case, auth, data_dir, repository_root, output_root)
    case_dir = Path(prepared_files["caseDir"])
    case_inp = Path(prepared_files["inputPath"])
    text = case_inp.read_text()
    (case_dir / "runtime-report.json").write_bytes(runtime_report_path.read_bytes())
    (case_dir / "randomseed").write_text(f"{case['seed']}\n", encoding="utf-8")
    (case_dir / "wavelength-grid-1nm.dat").write_bytes(sources["wavelengthGridPath"].read_bytes())

    prepared = {
        "schemaVersion": 1,
        "stageId": f"{STAGE}-prepared",
        "caseId": case_id,
        "groupId": case["groupId"],
        "sunDepressionDeg": case["sunDepressionDeg"],
        "aod550": case["aod550"],
        "geometryId": case["geometryId"],
        "geometryTag": case["geometryTag"],
        "targetAltitudeDeg": case["targetAltitudeDeg"],
        "relativeAzimuthDeg": case["relativeAzimuthDeg"],
        "observerElevationM": case["observerElevationM"],
        "replicate": case["replicate"],
        "stateId": case["stateId"],
        "seed": case["seed"],
        "photonHistories": case["photonHistories"],
        "scientificOrdinal": auth["scientificOrdinal"],
        "executionDesignCanonicalSha256": auth["executionDesignCanonicalSha256"],
        "executionContractGitBlobSha1": git_blob_sha1(contract_path),
        "authorizationDocumentSha256": canonical_sha256(auth),
        "guardReportRawSha256": sha256_file(guard_report_path),
        "caseInpSha256": sha256_file(case_inp),
        "profileTauSha256": prepared_files["profileSha256"],
    }
    (case_dir / "prepared.json").write_text(json.dumps(prepared, indent=2, sort_keys=True) + "\n")

    run = runner or process_runner.run_process_group
    syntax = run([str(uvspec), "-c"], text, case_dir, 60, sigterm_grace_seconds=5)
    (case_dir / "syntax-stdout.txt").write_text(str(syntax.get("stdout") or ""))
    (case_dir / "syntax-stderr.txt").write_text(str(syntax.get("stderr") or ""))
    if syntax.get("processGroupIsolated") is not True:
        raise ExecutionRefusal("syntax check was not process-group isolated")
    if syntax.get("timedOut") or syntax.get("exitCode") != 0:
        raise ExecutionRefusal("single syntax check failed")

    solver = run(
        [str(uvspec)], text, case_dir, int(contract["solverTimeoutSeconds"]), sigterm_grace_seconds=5
    )
    (case_dir / "solver-stdout.txt").write_text(str(solver.get("stdout") or ""))
    (case_dir / "solver-stderr.txt").write_text(str(solver.get("stderr") or ""))
    if solver.get("processGroupIsolated") is not True:
        raise ExecutionRefusal("solver was not process-group isolated")
    if solver.get("timedOut") or solver.get("exitCode") != 0:
        raise ExecutionRefusal("single solver execution failed")

    for name in contract["rawMembersRequired"]:
        path = case_dir / name
        if not path.is_file() or path.stat().st_size == 0:
            raise ExecutionRefusal(f"required raw output/member missing or empty: {name}")
    profile_path = Path(prepared_files["profilePath"])
    expected_profile_hash = auth["exactAfglProfileTauSha256"][case["stateId"]]
    if sha256_file(profile_path) != expected_profile_hash:
        raise ExecutionRefusal("case profile tau hash drift")

    wl, rad = parse_spectrum(case_dir / "mc.rad.spc")
    std_wl, std_rad = parse_spectrum(case_dir / "mc.rad.std.spc")
    derived.validate_raw_grid(wl, rad)
    derived.validate_raw_grid(std_wl, std_rad)
    if any(abs(a - b) > derived.RAW_POINT_TOLERANCE_NM for a, b in zip(wl, std_wl)):
        raise ExecutionRefusal("radiance/std wavelength grids differ")
    channels = derived.derive_channels(wl, rad)
    marginal_mc = derived.marginal_mc_std_diagnostics(wl, rad, std_rad)

    raw_hashes = {name: sha256_file(case_dir / name) for name in contract["rawMembersRequired"]}
    raw_hashes[f"profiles/{case['stateId']}.tau"] = sha256_file(profile_path)
    result = {
        "schemaVersion": 1,
        "stageId": STAGE,
        "status": "COMPLETED",
        "caseId": case_id,
        "groupId": case["groupId"],
        "sunDepressionDeg": case["sunDepressionDeg"],
        "geometryId": case["geometryId"],
        "geometryTag": case["geometryTag"],
        "targetAltitudeDeg": case["targetAltitudeDeg"],
        "relativeAzimuthDeg": case["relativeAzimuthDeg"],
        "observerElevationM": case["observerElevationM"],
        "aod550": case["aod550"],
        "replicate": case["replicate"],
        "stateId": case["stateId"],
        "seed": case["seed"],
        "photonHistories": case["photonHistories"],
        "numericalMethod": case["numericalMethod"],
        "scientificOrdinal": guard["scientificOrdinal"],
        "workflowRunId": guard["workflowRunId"],
        "workflowRunAttempt": 1,
        "syntaxCheckCount": 1,
        "solverExecutionCount": 1,
        "retryPerformed": False,
        "resumePerformed": False,
        "githubRerun": False,
        "syntaxExitCode": 0,
        "solverExitCode": 0,
        "syntaxTimedOut": False,
        "solverTimedOut": False,
        "processGroupIsolation": True,
        "executionDesignCanonicalSha256": auth["executionDesignCanonicalSha256"],
        "executionContractGitBlobSha1": git_blob_sha1(contract_path),
        "disabledExecutionPackageCanonicalSha256": auth["disabledExecutionPackageCanonicalSha256"],
        "exactAfglProfileTauSha256": expected_profile_hash,
        "caseSurfaceSha256": case["caseSurfaceSha256"],
        "caseInpSha256": sha256_file(case_inp),
        "runtimeReportRawSha256": sha256_file(case_dir / "runtime-report.json"),
        "radianceOutputSha256": sha256_file(case_dir / "mc.rad.spc"),
        "stdRadianceOutputSha256": sha256_file(case_dir / "mc.rad.std.spc"),
        "rawOutputNodeCount": len(wl),
        "channels": channels,
        "radianceSpectrum": rad,
        "marginalMcStdDiagnostics": marginal_mc,
        "rawMemberSha256ByRelativePath": raw_hashes,
        "resultOpeningAuthorized": False,
    }
    result["contentSha256"] = canonical_sha256(result)
    (case_dir / "case-result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result
