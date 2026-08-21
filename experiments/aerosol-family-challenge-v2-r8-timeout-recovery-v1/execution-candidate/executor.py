from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Callable


class ExecutionRefusal(RuntimeError):
    pass

SOURCE_R8_GIT_BLOBS = {
    "core.py": "04e93e1054ba2957383749ca4f4735b231993733",
    "adapter.py": "108af0a95274ee88fccf9d51d32f88ef0186bfaf",
    "derived_channels.py": "ccfd04d4c21188966351f4257e92893d7ce340c7",
    "analysis.py": "50b64b5c8a7a9d28a1c7174c1a1fda8d7380799d",
    "analysis-contract.v3.json": "d2411cd7636d3d34a0b9132a48fbcea4ccf35d76",
    "wavelength-grid-1nm.dat": "3bb3db96580d555ef758f57cabd6cac55b61cebb",
}


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def validate_source_r8_bytes(source: Path) -> None:
    for name, expected in SOURCE_R8_GIT_BLOBS.items():
        observed = git_blob_sha1(source / name)
        if observed != expected:
            raise ExecutionRefusal(f"source R8 byte binding drift: {name}")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ExecutionRefusal(f"cannot import {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def canonical_sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def parse_spectrum(raw: bytes) -> tuple[list[float], list[float]]:
    wavelengths: list[float] = []
    values: list[float] = []
    for line in raw.decode("utf-8").splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            wavelengths.append(float(parts[0]))
            values.append(float(parts[-1]))
        except ValueError:
            continue
    return wavelengths, values


def validate_manifest(manifest: dict[str, Any]) -> None:
    if manifest.get("stageId") != "aerosol-family-challenge-v2-r8-timeout-recovery-v1":
        raise ExecutionRefusal("recovery manifest stage drift")
    if manifest.get("status") != "FROZEN_TARGETED_TIMEOUT_RECOVERY_MANIFEST_NOT_AUTHORIZED":
        raise ExecutionRefusal("recovery manifest freeze status drift")
    cases = manifest.get("cases")
    if not isinstance(cases, list) or len(cases) != 8 or manifest.get("caseCount") != 8 or manifest.get("groupCount") != 1:
        raise ExecutionRefusal("recovery manifest must contain exactly one eight-state group")
    ids = [str(row.get("caseId") or "") for row in cases]
    if len(set(ids)) != 8:
        raise ExecutionRefusal("recovery case IDs not unique")
    if {row.get("seed") for row in cases} != {371960104}:
        raise ExecutionRefusal("recovery group seed drift")
    if {row.get("sourceOrdinal34Seed") for row in cases} != {798398324}:
        raise ExecutionRefusal("source seed binding drift")
    if {row.get("groupId") for row in cases} != {"afc2-d04-g06-late-opposite-high-aerosol-aod10-r2"}:
        raise ExecutionRefusal("recovery group identity drift")
    if {row.get("photonHistories") for row in cases} != {20_000_000}:
        raise ExecutionRefusal("recovery photon budget drift")
    if manifest.get("solverTimeoutSeconds") != 7200 or manifest.get("githubJobTimeoutMinutes") != 150:
        raise ExecutionRefusal("recovery timeout budget drift")
    if manifest.get("retainedSourceCaseCountForFutureCombinedAnalysis") != 568 or manifest.get("effectiveCombinedCaseCount") != 576:
        raise ExecutionRefusal("combined acquisition cardinality drift")
    boundary = manifest.get("boundary") or {}
    if any(boundary.get(k) is not False for k in ("scientificExecutionAuthorized", "solverExecutionAuthorized", "dispatchAuthorized", "resultsOpened")):
        raise ExecutionRefusal("frozen manifest unexpectedly authorizes execution")


def execute_case(
    repository_root: Path,
    manifest_path: Path,
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
    package = repository_root / "experiments/aerosol-family-challenge-v2-r8-timeout-recovery-v1"
    source = repository_root / "experiments/aerosol-family-challenge-v2-r8"
    validate_source_r8_bytes(source)
    core = load("afc2_r8_source_core_for_timeout_recovery", source / "core.py")
    sys.modules["core"] = core
    adapter = load("afc2_r8_source_adapter_for_timeout_recovery", source / "adapter.py")
    derived = load("afc2_r8_source_derived_for_timeout_recovery", source / "derived_channels.py")
    process_runner = load("afc2_timeout_recovery_process_runner", package / "execution-candidate/process_runner.py")

    manifest = json.loads(manifest_path.read_text())
    validate_manifest(manifest)
    guard = json.loads(guard_report_path.read_text())
    if guard.get("status") != "EXACT_ONE_USE_AFC2_R8_TIMEOUT_RECOVERY_DISPATCH_AUTHORIZED" or guard.get("solverExecutionPermittedNow") is not True:
        raise ExecutionRefusal("execution guard did not authorize solver")
    if guard.get("manifestRawSha256") != sha(manifest_path):
        raise ExecutionRefusal("guard/manifest hash drift")
    if guard.get("workflowRunAttempt") != 1:
        raise ExecutionRefusal("workflow attempt drift")

    rows = [row for row in manifest["cases"] if row["caseId"] == case_id]
    if len(rows) != 1:
        raise ExecutionRefusal("case not uniquely present in recovery manifest")
    case = rows[0]
    runtime = json.loads(runtime_report_path.read_text())
    if runtime.get("scientificSolverExecuted") is not False:
        raise ExecutionRefusal("runtime identity must be pre-solver")
    required_runtime = (manifest.get("sourceBindings") or {}).get("runtimeLock") or {}
    for key in ("uvspecSha256", "uvspecHelpSha256", "libRadtranDataTreeSha256", "atmosphereSha256", "rawSha256"):
        runtime_key = "runtimeLockRawSha256" if key == "rawSha256" else key
        if runtime.get(runtime_key) != required_runtime.get(key):
            raise ExecutionRefusal(f"runtime identity drift: {runtime_key}")
    if sha(uvspec) != required_runtime.get("uvspecSha256"):
        raise ExecutionRefusal("uvspec byte hash drift")

    case_dir = output_root / case_id
    case_dir.mkdir(parents=True, exist_ok=False)
    text = adapter.render_case_input(case, data_dir, repository_root, output_root)
    case_inp = case_dir / "case.inp"
    case_inp.write_text(text, encoding="utf-8", newline="\n")
    adapter.assert_exact_aerosol_state(case_inp.read_text(), case)
    adapter.assert_exact_spectrum_surface(case_inp.read_text())
    (case_dir / "runtime-report.json").write_bytes(runtime_report_path.read_bytes())
    (case_dir / "randomseed").write_text(f"{case['seed']}\n", encoding="utf-8")
    grid = source / "wavelength-grid-1nm.dat"
    (case_dir / "wavelength-grid-1nm.dat").write_bytes(grid.read_bytes())
    prepared = {
        "schemaVersion": 1,
        "stageId": "aerosol-family-challenge-v2-r8-timeout-recovery-v1-prepared",
        "caseId": case_id,
        "sourceOrdinal34CaseId": case["sourceOrdinal34CaseId"],
        "groupId": case["groupId"],
        "analysisCellId": case["analysisCellId"],
        "replicate": case["replicate"],
        "seed": case["seed"],
        "sourceOrdinal34Seed": case["sourceOrdinal34Seed"],
        "photonHistories": case["photonHistories"],
        "aerosolFamily": case["aerosolFamily"],
        "aerosolSeason": case["aerosolSeason"],
        "caseInpSha256": sha(case_inp),
        "manifestRawSha256": sha(manifest_path),
        "guardReportRawSha256": sha(guard_report_path),
    }
    (case_dir / "prepared.json").write_text(json.dumps(prepared, indent=2, sort_keys=True) + "\n")

    run = runner or process_runner.run_process_group
    syntax = run([str(uvspec), "-c"], text, case_dir, 60, sigterm_grace_seconds=5)
    (case_dir / "syntax-stdout.txt").write_text(str(syntax.get("stdout") or ""))
    (case_dir / "syntax-stderr.txt").write_text(str(syntax.get("stderr") or ""))
    if syntax.get("processGroupIsolated") is not True:
        raise ExecutionRefusal("syntax process was not group-isolated")
    if syntax.get("timedOut") or syntax.get("exitCode") != 0:
        raise ExecutionRefusal("single syntax check failed")

    solver = run([str(uvspec)], text, case_dir, int(manifest["solverTimeoutSeconds"]), sigterm_grace_seconds=5)
    (case_dir / "solver-stdout.txt").write_text(str(solver.get("stdout") or ""))
    (case_dir / "solver-stderr.txt").write_text(str(solver.get("stderr") or ""))
    if solver.get("processGroupIsolated") is not True:
        raise ExecutionRefusal("solver process was not group-isolated")
    if solver.get("timedOut") or solver.get("exitCode") != 0:
        raise ExecutionRefusal("single solver execution failed")

    required = ("mc.flx.spc", "mc.flx.std.spc", "mc.rad.spc", "mc.rad.std.spc")
    for name in required:
        path = case_dir / name
        if not path.is_file() or path.stat().st_size == 0:
            raise ExecutionRefusal(f"required raw output missing/empty: {name}")
    wl, rad = parse_spectrum((case_dir / "mc.rad.spc").read_bytes())
    derived.validate_raw_grid(wl, rad)
    std_wl, std_rad = parse_spectrum((case_dir / "mc.rad.std.spc").read_bytes())
    derived.validate_raw_grid(std_wl, std_rad)
    if any(abs(a - b) > derived.RAW_POINT_TOLERANCE_NM for a, b in zip(wl, std_wl)):
        raise ExecutionRefusal("radiance/std wavelength grids differ")
    channels = derived.derive_channels(wl, rad)
    marginal_mc = derived.marginal_mc_std_diagnostics(wl, rad, std_rad)
    raw_names = (
        "case.inp", "prepared.json", "runtime-report.json", "randomseed",
        "syntax-stdout.txt", "syntax-stderr.txt", "solver-stdout.txt", "solver-stderr.txt",
        "wavelength-grid-1nm.dat", "mc.flx.spc", "mc.flx.std.spc", "mc.rad.spc", "mc.rad.std.spc",
    )
    result = {
        "schemaVersion": 1,
        "stageId": "aerosol-family-challenge-v2-r8-timeout-recovery-v1",
        "status": "COMPLETED",
        "caseId": case_id,
        "sourceOrdinal34CaseId": case["sourceOrdinal34CaseId"],
        "sourceOrdinal34RunId": 32447101887,
        "sourceOrdinal34Seed": case["sourceOrdinal34Seed"],
        "groupId": case["groupId"],
        "analysisCellId": case["analysisCellId"],
        "replicate": case["replicate"],
        "seed": case["seed"],
        "photonHistories": case["photonHistories"],
        "aerosolFamily": case["aerosolFamily"],
        "aerosolSeason": case["aerosolSeason"],
        "recoveryScientificOrdinal": guard["scientificOrdinal"],
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
        "caseInpSha256": sha(case_dir / "case.inp"),
        "runtimeReportRawSha256": sha(case_dir / "runtime-report.json"),
        "radianceOutputSha256": sha(case_dir / "mc.rad.spc"),
        "stdRadianceOutputSha256": sha(case_dir / "mc.rad.std.spc"),
        "rawOutputNodeCount": len(wl),
        "channels": channels,
        "marginalMcStdDiagnostics": marginal_mc,
        "rawMemberSha256ByBasename": {name: sha(case_dir / name) for name in raw_names},
    }
    result["contentSha256"] = canonical_sha(result)
    (case_dir / "case-result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result
