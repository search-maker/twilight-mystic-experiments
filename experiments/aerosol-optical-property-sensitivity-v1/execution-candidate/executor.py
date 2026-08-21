from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any, Callable


class ExecutionRefusal(RuntimeError):
    pass


STAGE = "aerosol-optical-property-sensitivity-v1"
EXPECTED_GUARD_STATUS = "EXACT_ONE_USE_AOPS_V1_DISPATCH_AUTHORIZED"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


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
    if contract.get("status") != "FROZEN_REVIEW_ONLY_EXECUTION_CONTRACT_NOT_AUTHORIZED":
        raise ExecutionRefusal("execution contract status drift")
    if any(contract.get(k) is not False for k in (
        "scientificExecutionAuthorized", "solverExecutionAuthorized", "resultOpeningAuthorized"
    )):
        raise ExecutionRefusal("review execution contract unexpectedly authorizes execution")
    return contract


def validate_bound_sources(repository_root: Path, contract: dict[str, Any]) -> tuple[Path, Path, Path]:
    bindings = contract["sourceBindings"]
    runner_path = repository_root / bindings["processGroupRunnerPath"]
    derived_path = repository_root / bindings["r8DerivedChannelsPath"]
    grid_path = repository_root / bindings["wavelengthGridPath"]
    for path, expected in (
        (runner_path, bindings["processGroupRunnerGitBlobSha1"]),
        (derived_path, bindings["r8DerivedChannelsGitBlobSha1"]),
        (grid_path, bindings["wavelengthGridGitBlobSha1"]),
    ):
        if git_blob_sha1(path) != expected:
            raise ExecutionRefusal(f"bound source bytes changed: {path}")
    runtime_lock = repository_root / contract["runtimeIdentity"]["runtimeLockPath"]
    if git_blob_sha1(runtime_lock) != contract["runtimeIdentity"]["runtimeLockGitBlobSha1"]:
        raise ExecutionRefusal("runtime lock Git blob drift")
    if sha256_file(runtime_lock) != contract["runtimeIdentity"]["runtimeLockRawSha256"]:
        raise ExecutionRefusal("runtime lock raw SHA drift")
    return runner_path, derived_path, grid_path


def validate_guard(
    guard: dict[str, Any],
    design: dict[str, Any],
    execution_contract_blob: str,
) -> None:
    if guard.get("status") != EXPECTED_GUARD_STATUS:
        raise ExecutionRefusal("execution guard status did not authorize AOPS v1")
    if guard.get("solverExecutionPermittedNow") is not True:
        raise ExecutionRefusal("execution guard did not permit solver")
    if guard.get("workflowRunAttempt") != 1:
        raise ExecutionRefusal("workflow attempt must be exactly 1")
    if guard.get("designCanonicalSha256") != design.get("canonicalDesignSha256"):
        raise ExecutionRefusal("guard/design canonical hash drift")
    if guard.get("executionContractGitBlobSha1") != execution_contract_blob:
        raise ExecutionRefusal("guard/execution-contract byte binding drift")
    if guard.get("authorizationPrDraftOpenUnmerged") is not True:
        raise ExecutionRefusal("authorization PR must be Draft/open/unmerged")
    if guard.get("githubRerun") is not False:
        raise ExecutionRefusal("GitHub rerun is forbidden")
    for key in ("scientificOrdinal", "workflowRunId"):
        value = guard.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ExecutionRefusal(f"invalid guard identity: {key}")


def validate_runtime(runtime: dict[str, Any], contract: dict[str, Any], uvspec: Path) -> None:
    if runtime.get("scientificSolverExecuted") is not False:
        raise ExecutionRefusal("runtime identity must be pre-solver")
    expected = contract["runtimeIdentity"]
    mapping = {
        "runtimeLockRawSha256": "runtimeLockRawSha256",
        "uvspecSha256": "uvspecSha256",
        "uvspecHelpSha256": "uvspecHelpSha256",
        "libRadtranDataTreeSha256": "libRadtranDataTreeSha256",
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
        raise ExecutionRefusal("--allow-execution required")

    stage_dir = repository_root / "experiments" / STAGE
    contract_path = stage_dir / "execution-contract.review.json"
    contract = load_contract(stage_dir)
    runner_path, derived_path, grid_path = validate_bound_sources(repository_root, contract)

    design_mod = load_module("aops_v1_execution_design_for_executor", stage_dir / "execution_design.py")
    adapter = load_module("aops_v1_adapter_for_executor", stage_dir / "adapter.py")
    derived = load_module("aops_v1_bound_r8_derived", derived_path)
    process_runner = load_module("aops_v1_bound_process_runner", runner_path)
    design = design_mod.build_review_execution_design()
    if design.get("status") != "REVIEW_ONLY_SEEDED_DESIGN_NON_RENDERABLE_NOT_AUTHORIZED":
        raise ExecutionRefusal("review execution design status drift")
    if design.get("caseCount") != 360 or design.get("groupCount") != 72:
        raise ExecutionRefusal("review execution design cardinality drift")

    guard = json.loads(guard_report_path.read_text())
    validate_guard(guard, design, git_blob_sha1(contract_path))
    runtime = json.loads(runtime_report_path.read_text())
    validate_runtime(runtime, contract, uvspec)

    matches = [row for row in design["cases"] if row.get("caseId") == case_id]
    if len(matches) != 1:
        raise ExecutionRefusal("case is not uniquely present in frozen review design")
    review_case = matches[0]
    case = {
        **review_case,
        "renderable": True,
        "executionAuthorized": True,
        "seedStatus": "AUTHORIZED_FRESH_GROUP_SEED",
    }

    case_dir = output_root / case_id
    case_dir.mkdir(parents=True, exist_ok=False)
    text = adapter.render_case_input(case, data_dir, repository_root, output_root)
    case_inp = case_dir / "case.inp"
    case_inp.write_text(text, encoding="utf-8", newline="\n")
    adapter.assert_exact_aerosol_surface(text, str(case["stateId"]), float(case["aod550"]))
    (case_dir / "runtime-report.json").write_bytes(runtime_report_path.read_bytes())
    (case_dir / "randomseed").write_text(f"{case['seed']}\n", encoding="utf-8")
    (case_dir / "wavelength-grid-1nm.dat").write_bytes(grid_path.read_bytes())

    prepared = {
        "schemaVersion": 1,
        "stageId": f"{STAGE}-prepared",
        "caseId": case_id,
        "groupId": case["groupId"],
        "analysisCellId": case["analysisCellId"],
        "replicate": case["replicate"],
        "stateId": case["stateId"],
        "seed": case["seed"],
        "photonHistories": case["photonHistories"],
        "designCanonicalSha256": design["canonicalDesignSha256"],
        "executionContractGitBlobSha1": git_blob_sha1(contract_path),
        "guardReportRawSha256": sha256_file(guard_report_path),
        "caseInpSha256": sha256_file(case_inp),
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
        [str(uvspec)],
        text,
        case_dir,
        int(contract["solverTimeoutSeconds"]),
        sigterm_grace_seconds=5,
    )
    (case_dir / "solver-stdout.txt").write_text(str(solver.get("stdout") or ""))
    (case_dir / "solver-stderr.txt").write_text(str(solver.get("stderr") or ""))
    if solver.get("processGroupIsolated") is not True:
        raise ExecutionRefusal("solver was not process-group isolated")
    if solver.get("timedOut") or solver.get("exitCode") != 0:
        raise ExecutionRefusal("single solver execution failed")

    for name in ("mc.flx.spc", "mc.flx.std.spc", "mc.rad.spc", "mc.rad.std.spc"):
        path = case_dir / name
        if not path.is_file() or path.stat().st_size == 0:
            raise ExecutionRefusal(f"required raw output missing or empty: {name}")

    wl, rad = parse_spectrum(case_dir / "mc.rad.spc")
    std_wl, std_rad = parse_spectrum(case_dir / "mc.rad.std.spc")
    derived.validate_raw_grid(wl, rad)
    derived.validate_raw_grid(std_wl, std_rad)
    if any(abs(a - b) > derived.RAW_POINT_TOLERANCE_NM for a, b in zip(wl, std_wl)):
        raise ExecutionRefusal("radiance/std wavelength grids differ")
    channels = derived.derive_channels(wl, rad)
    marginal_mc = derived.marginal_mc_std_diagnostics(wl, rad, std_rad)

    raw_names = tuple(contract["rawMembersRequired"])
    for name in raw_names:
        path = case_dir / name
        if not path.is_file():
            raise ExecutionRefusal(f"required raw member missing: {name}")

    result = {
        "schemaVersion": 1,
        "stageId": STAGE,
        "status": "COMPLETED",
        "caseId": case_id,
        "groupId": case["groupId"],
        "analysisCellId": case["analysisCellId"],
        "sunDepressionDeg": case["sunDepressionDeg"],
        "geometryId": case["geometryId"],
        "geometryTag": case["geometryTag"],
        "targetAltitudeDeg": case["targetAltitudeDeg"],
        "relativeAzimuthDeg": case["relativeAzimuthDeg"],
        "observerElevationM": case["observerElevationM"],
        "aod550": case["aod550"],
        "replicate": case["replicate"],
        "stateId": case["stateId"],
        "aerosolKind": case["aerosolKind"],
        "ssaSet": case["ssaSet"],
        "ggSet": case["ggSet"],
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
        "designCanonicalSha256": design["canonicalDesignSha256"],
        "executionContractGitBlobSha1": git_blob_sha1(contract_path),
        "caseInpSha256": sha256_file(case_inp),
        "runtimeReportRawSha256": sha256_file(case_dir / "runtime-report.json"),
        "radianceOutputSha256": sha256_file(case_dir / "mc.rad.spc"),
        "stdRadianceOutputSha256": sha256_file(case_dir / "mc.rad.std.spc"),
        "rawOutputNodeCount": len(wl),
        "channels": channels,
        "marginalMcStdDiagnostics": marginal_mc,
        "rawMemberSha256ByBasename": {name: sha256_file(case_dir / name) for name in raw_names},
    }
    result["contentSha256"] = canonical_sha256(result)
    (case_dir / "case-result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result
