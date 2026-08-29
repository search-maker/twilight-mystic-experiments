from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Callable

STAGE = "aerosol-vertical-profile-sensitivity-v2"
EXPECTED_GUARD_STATUS = "EXACT_ONE_USE_AVPS_V2_DISPATCH_AUTHORIZED"
EXPECTED_AUTH_HEAD = "d5f5e4d9d19d7ede573fecae68565a92baabbec3"
EXPECTED_AUTH_PR = 604
EXPECTED_ORDINAL = 41
EXPECTED_EXECUTION_KEY = "aerosol-vertical-profile-sensitivity-v2:numerical:41"
EXPECTED_SEED_CANONICAL = "02f624d582e9b2caba6b920d65a5e8a8bc8fc1a2693623bc2f73abf5d3f706d2"
EXPECTED_FOUR_ALIAS_TREE = "5e1814dd36cf861fd85477a97607299248f8272268df7bf428d31bbb6aa4354a"
EXPECTED_UVSPEC = "2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3"
EXPECTED_AFGL = "dab26290ed81c762ed0c607e5dc2d53393c1462a0c3a528bc5e3f5935191cfb5"
EXPECTED_PROFILE_SHA256 = {
    "opac-profile-continental-average": "ceed598f7681951cd0e6208b267beb5b41a52ab10311f37ce76f925700caff3d",
    "opac-profile-maritime-clean": "487b67bd7dbe89d12d032fdf2b33cab545e16a2e0697170648317f1a76362a67",
    "opac-profile-desert": "2b4d2e03c6ae3143d9bb05d2da49f57f75172dc1f24d34f7d4a4939bf9952fef",
    "opac-profile-arctic": "98f2fa5428c830764252fd0a2662b0f5c957fc027ffcb7bdc0a5e500dfd7d3d6",
    "opac-profile-antarctic": "ee063c6dca68cf9a31d8bb9d993f1fed5cb34c8bb056ac180c97171b5d6b4f19",
}

CONTRACT_PATH = Path("review/aerosol-vertical-profile-sensitivity-v2-execution-control-v1/execution-contract.review.json")
AUTH_PATH = Path("review/aerosol-vertical-profile-sensitivity-v2-authorization-control-v4/authorization.json")
ADAPTER_PATH = Path("review/aerosol-vertical-profile-sensitivity-v2-control-v1/adapter.py")
RUNTIME_STAGE_PATH = Path("review/aerosol-vertical-profile-sensitivity-v2-control-v1/runtime_stage.py")
PROCESS_RUNNER_PATH = Path("experiments/aerosol-family-challenge-v2-r8-timeout-recovery-v1/execution-candidate/process_runner.py")
DERIVED_CHANNELS_PATH = Path("experiments/aerosol-family-challenge-v2-r8/derived_channels.py")
WAVELENGTH_GRID_PATH = Path("experiments/aerosol-family-challenge-v2-r8/wavelength-grid-1nm.dat")

EXPECTED_BLOBS = {
    CONTRACT_PATH: "a7a87a3cd7b1ebffbe693d14443f906a0aed6ff2",
    AUTH_PATH: "dcfbd39081abe8e98604eedd48a1d934cea5483a",
    ADAPTER_PATH: "c245eac2fe5b5d026e46ec4253bc377c5fde97ec",
    RUNTIME_STAGE_PATH: "0d3ac10f3ef7d22f0205854233a6c37cbba03f7c",
    PROCESS_RUNNER_PATH: "e23d724e99c1cf9b0b862f8ab48356bd3d9bc56c",
    DERIVED_CHANNELS_PATH: "ccfd04d4c21188966351f4257e92893d7ce340c7",
    WAVELENGTH_GRID_PATH: "3bb3db96580d555ef758f57cabd6cac55b61cebb",
}

RAW_MEMBERS_REQUIRED = (
    "case.inp",
    "prepared.json",
    "runtime-report.json",
    "randomseed",
    "syntax-stdout.txt",
    "syntax-stderr.txt",
    "solver-stdout.txt",
    "solver-stderr.txt",
    "wavelength-grid-1nm.dat",
    "mc.flx.spc",
    "mc.flx.std.spc",
    "mc.rad.spc",
    "mc.rad.std.spc",
)


class ExecutionRefusal(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_blob_sha1(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ExecutionRefusal(f"cannot import bound module: {path}")
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


def validate_bound_sources(repository_root: Path) -> None:
    for relative, expected in EXPECTED_BLOBS.items():
        path = repository_root / relative
        if not path.is_file() or git_blob_sha1(path) != expected:
            raise ExecutionRefusal(f"bound source bytes changed: {relative}")


def load_contract(repository_root: Path) -> dict[str, Any]:
    path = repository_root / CONTRACT_PATH
    contract = json.loads(path.read_text())
    if contract.get("status") != "REVIEW_ONLY_EXECUTION_CONTROL_FROZEN_DISPATCH_NOT_AUTHORIZED":
        raise ExecutionRefusal("execution-control contract status drift")
    if int(contract.get("scientificOrdinal") or 0) != EXPECTED_ORDINAL:
        raise ExecutionRefusal("execution-control ordinal drift")
    if contract.get("executionKey") != EXPECTED_EXECUTION_KEY:
        raise ExecutionRefusal("execution-control key drift")
    if contract.get("authorizationHead") != EXPECTED_AUTH_HEAD or int(contract.get("authorizationPr") or 0) != EXPECTED_AUTH_PR:
        raise ExecutionRefusal("execution-control authorization binding drift")
    if contract.get("dispatchCreated") is not False or contract.get("scientificExecutionPerformed") is not False:
        raise ExecutionRefusal("execution-control review crossed dispatch/science boundary")
    design = contract.get("caseDesign") or {}
    if (design.get("expectedCaseCount"), design.get("expectedGroupCount"), design.get("expectedStatesPerGroup")) != (360, 72, 5):
        raise ExecutionRefusal("execution-control case cardinality drift")
    if design.get("photonHistoriesPerCase") != 20_000_000:
        raise ExecutionRefusal("execution-control photon budget drift")
    if design.get("attemptRequired") != 1 or design.get("retryPermitted") is not False or design.get("resumePermitted") is not False or design.get("githubRerunPermitted") is not False:
        raise ExecutionRefusal("execution-control one-shot boundary weakened")
    return contract


def validate_authorization(auth: dict[str, Any]) -> None:
    if auth.get("stageId") != STAGE or auth.get("status") != "AUTHORIZED_PENDING_SEPARATE_DISPATCH":
        raise ExecutionRefusal("authorization stage/status drift")
    if int(auth.get("scientificOrdinal") or 0) != EXPECTED_ORDINAL or auth.get("executionKey") != EXPECTED_EXECUTION_KEY:
        raise ExecutionRefusal("authorization identity drift")
    if auth.get("authorizationBranch") != "authorization/aerosol-vertical-profile-sensitivity-v2-ordinal-41":
        raise ExecutionRefusal("authorization branch drift")
    if auth.get("dispatchBranch") != "dispatch/aerosol-vertical-profile-sensitivity-v2-ordinal-41":
        raise ExecutionRefusal("dispatch branch contract drift")
    if auth.get("candidateSeedCanonicalSha256") != EXPECTED_SEED_CANONICAL or auth.get("candidateSeedCount") != 72:
        raise ExecutionRefusal("authorization candidate-seed identity drift")
    if auth.get("candidateSeedValuesIncluded") is not False or auth.get("candidateSeedsAppliedToTrackedCases") is not False:
        raise ExecutionRefusal("candidate seeds leaked into tracked authorization state")
    if auth.get("exactFourSpeciesProfileSha256") != EXPECTED_PROFILE_SHA256:
        raise ExecutionRefusal("authorization four-species profile identity drift")
    if auth.get("fourAliasDataTreeSha256") != EXPECTED_FOUR_ALIAS_TREE:
        raise ExecutionRefusal("authorization four-alias data-tree drift")
    if auth.get("uvspecSha256") != EXPECTED_UVSPEC:
        raise ExecutionRefusal("authorization uvspec drift")
    if auth.get("caseCount") != 360 or auth.get("commonRandomNumberGroupCount") != 72 or auth.get("statesPerGroup") != 5:
        raise ExecutionRefusal("authorization cardinality drift")
    if auth.get("photonHistoriesPerCase") != 20_000_000:
        raise ExecutionRefusal("authorization photon budget drift")
    if auth.get("scientificExecutionAuthorized") is not True or auth.get("solverExecutionAuthorized") is not True:
        raise ExecutionRefusal("authorization does not permit later one-shot science")
    for key in ("dispatchAuthorized", "automaticDispatch", "resultOpeningAuthorized", "productionAuthorized", "taylorOrJerusalemFitAuthorized"):
        if auth.get(key) is not False:
            raise ExecutionRefusal(f"authorization crossed forbidden boundary: {key}")
    for key in ("githubRerunAllowed", "retryAllowed", "resumeAllowed"):
        if auth.get(key) is not False:
            raise ExecutionRefusal(f"authorization one-shot boundary weakened: {key}")


def validate_guard(guard: dict[str, Any]) -> None:
    if guard.get("status") != EXPECTED_GUARD_STATUS:
        raise ExecutionRefusal("one-use v2 science guard did not authorize execution")
    if int(guard.get("scientificOrdinal") or 0) != EXPECTED_ORDINAL:
        raise ExecutionRefusal("guard ordinal drift")
    if guard.get("executionKey") != EXPECTED_EXECUTION_KEY:
        raise ExecutionRefusal("guard execution key drift")
    if guard.get("authorizationHead") != EXPECTED_AUTH_HEAD or int(guard.get("authorizationPr") or 0) != EXPECTED_AUTH_PR:
        raise ExecutionRefusal("guard authorization binding drift")
    if guard.get("dispatchBranch") != "dispatch/aerosol-vertical-profile-sensitivity-v2-ordinal-41" or guard.get("dispatchBranchHeadSha") != EXPECTED_AUTH_HEAD:
        raise ExecutionRefusal("guard dispatch identity drift")
    if guard.get("workflowRunAttempt") != 1:
        raise ExecutionRefusal("workflow attempt must be exactly one")
    run_id = guard.get("workflowRunId")
    if isinstance(run_id, bool) or not isinstance(run_id, int) or run_id <= 0:
        raise ExecutionRefusal("guard workflow run id invalid")
    if guard.get("allocationMarkerCount") != 1 or guard.get("consumedMarkerCount") != 1:
        raise ExecutionRefusal("guard allocation/consumption marker cardinality drift")
    if guard.get("candidateSeedCanonicalSha256") != EXPECTED_SEED_CANONICAL:
        raise ExecutionRefusal("guard candidate-seed identity drift")
    if guard.get("preSolverRepositoryGlobalSeedRecheckPassed") is not True:
        raise ExecutionRefusal("pre-solver repository-global seed recheck missing")
    if guard.get("fourAliasDataTreeSha256") != EXPECTED_FOUR_ALIAS_TREE:
        raise ExecutionRefusal("guard four-alias runtime drift")
    if guard.get("solverExecutionPermittedNow") is not True:
        raise ExecutionRefusal("guard did not permit solver now")
    if guard.get("githubRerun") is not False or guard.get("retryAllowed") is not False or guard.get("resumeAllowed") is not False:
        raise ExecutionRefusal("guard rerun/retry/resume boundary weakened")


def validate_runtime(runtime: dict[str, Any], uvspec: Path) -> None:
    if runtime.get("status") != "PASS_FROZEN_BASE_ARCHIVE_AND_FOUR_ALIAS_RUNTIME_IDENTITIES":
        raise ExecutionRefusal("v2 runtime identity report status drift")
    if runtime.get("scientificSolverExecuted") is not False:
        raise ExecutionRefusal("runtime identity report must be pre-solver")
    if runtime.get("uvspecSha256") != EXPECTED_UVSPEC:
        raise ExecutionRefusal("runtime uvspec identity drift")
    if runtime.get("fourAliasDataTreeSha256") != EXPECTED_FOUR_ALIAS_TREE:
        raise ExecutionRefusal("runtime four-alias data-tree drift")
    if runtime.get("afglSha256") != EXPECTED_AFGL:
        raise ExecutionRefusal("runtime AFGL-US identity drift")
    if not uvspec.is_file() or sha256_file(uvspec) != EXPECTED_UVSPEC:
        raise ExecutionRefusal("uvspec byte hash drift")


def select_authorized_case(adapter: Any, auth: dict[str, Any], case_id: str) -> dict[str, Any]:
    cases = adapter.authorized_case_universe(auth)
    hits = [row for row in cases if row.get("caseId") == case_id]
    if len(cases) != 360 or len(hits) != 1:
        raise ExecutionRefusal("authorized v2 case universe/case selection drift")
    case = hits[0]
    if case.get("seedStatus") != "AUTHORIZED_FRESH_GROUP_SEED_PENDING_DISPATCH":
        raise ExecutionRefusal("authorized in-memory seed status drift")
    return case


def execute_case(
    repository_root: Path,
    authorization_path: Path,
    guard_report_path: Path,
    runtime_report_path: Path,
    profile_dir: Path,
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

    validate_bound_sources(repository_root)
    contract = load_contract(repository_root)
    auth = json.loads(authorization_path.read_text())
    validate_authorization(auth)
    guard = json.loads(guard_report_path.read_text())
    validate_guard(guard)
    runtime = json.loads(runtime_report_path.read_text())
    validate_runtime(runtime, uvspec)

    adapter = load_module("avps_v2_executor_adapter", repository_root / ADAPTER_PATH)
    derived = load_module("avps_v2_executor_derived", repository_root / DERIVED_CHANNELS_PATH)
    process_runner = load_module("avps_v2_executor_process_runner", repository_root / PROCESS_RUNNER_PATH)
    case = select_authorized_case(adapter, auth, case_id)

    prepared_files = adapter.prepare_case_files(case, auth, data_dir, repository_root, profile_dir, output_root)
    case_dir = Path(prepared_files["caseDir"])
    case_inp = Path(prepared_files["inputPath"])
    profile_path = Path(prepared_files["profilePath"])
    text = case_inp.read_text()

    (case_dir / "runtime-report.json").write_bytes(runtime_report_path.read_bytes())
    (case_dir / "randomseed").write_text(f"{case['seed']}\n", encoding="utf-8")
    (case_dir / "wavelength-grid-1nm.dat").write_bytes((repository_root / WAVELENGTH_GRID_PATH).read_bytes())

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
        "scientificOrdinal": EXPECTED_ORDINAL,
        "executionKey": EXPECTED_EXECUTION_KEY,
        "authorizationHead": EXPECTED_AUTH_HEAD,
        "candidateSeedCanonicalSha256": EXPECTED_SEED_CANONICAL,
        "executionControlContractGitBlobSha1": git_blob_sha1(repository_root / CONTRACT_PATH),
        "authorizationDocumentSha256": canonical_sha256(auth),
        "guardReportRawSha256": sha256_file(guard_report_path),
        "caseInpSha256": sha256_file(case_inp),
        "fourSpeciesProfileSha256": prepared_files["profileSha256"],
        "fourAliasDataTreeSha256": EXPECTED_FOUR_ALIAS_TREE,
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

    solver_timeout = 7200
    syntax_count = 1
    solver = run([str(uvspec)], text, case_dir, solver_timeout, sigterm_grace_seconds=5)
    (case_dir / "solver-stdout.txt").write_text(str(solver.get("stdout") or ""))
    (case_dir / "solver-stderr.txt").write_text(str(solver.get("stderr") or ""))
    if solver.get("processGroupIsolated") is not True:
        raise ExecutionRefusal("solver was not process-group isolated")
    if solver.get("timedOut") or solver.get("exitCode") != 0:
        raise ExecutionRefusal("single solver execution failed")

    for name in RAW_MEMBERS_REQUIRED:
        path = case_dir / name
        if not path.is_file() or path.stat().st_size == 0:
            raise ExecutionRefusal(f"required raw output/member missing or empty: {name}")
    expected_profile_hash = EXPECTED_PROFILE_SHA256[str(case["stateId"])]
    if sha256_file(profile_path) != expected_profile_hash:
        raise ExecutionRefusal("case explicit four-species profile hash drift")
    if "aerosol_species_file profiles/" not in text or " INSO WASO SOOT SUSO" not in text:
        raise ExecutionRefusal("explicit four-species transport directive missing")
    if any(line.startswith("aerosol_file ") for line in text.splitlines()):
        raise ExecutionRefusal("legacy aerosol_file tau transport unexpectedly present")

    wl, rad = parse_spectrum(case_dir / "mc.rad.spc")
    std_wl, std_rad = parse_spectrum(case_dir / "mc.rad.std.spc")
    derived.validate_raw_grid(wl, rad)
    derived.validate_raw_grid(std_wl, std_rad)
    if any(abs(a - b) > derived.RAW_POINT_TOLERANCE_NM for a, b in zip(wl, std_wl)):
        raise ExecutionRefusal("radiance/std wavelength grids differ")
    channels = derived.derive_channels(wl, rad)
    marginal_mc = derived.marginal_mc_std_diagnostics(wl, rad, std_rad)

    raw_hashes = {name: sha256_file(case_dir / name) for name in RAW_MEMBERS_REQUIRED}
    profile_member = f"profiles/{case['stateId']}.four-species.dat"
    raw_hashes[profile_member] = sha256_file(profile_path)
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
        "scientificOrdinal": EXPECTED_ORDINAL,
        "executionKey": EXPECTED_EXECUTION_KEY,
        "workflowRunId": guard["workflowRunId"],
        "workflowRunAttempt": 1,
        "syntaxCheckCount": syntax_count,
        "solverExecutionCount": 1,
        "retryPerformed": False,
        "resumePerformed": False,
        "githubRerun": False,
        "syntaxExitCode": 0,
        "solverExitCode": 0,
        "syntaxTimedOut": False,
        "solverTimedOut": False,
        "processGroupIsolation": True,
        "authorizationHead": EXPECTED_AUTH_HEAD,
        "candidateSeedCanonicalSha256": EXPECTED_SEED_CANONICAL,
        "executionControlContractGitBlobSha1": git_blob_sha1(repository_root / CONTRACT_PATH),
        "fourSpeciesProfileSha256": expected_profile_hash,
        "fourSpeciesProfileRelativePath": profile_member,
        "fourAliasDataTreeSha256": EXPECTED_FOUR_ALIAS_TREE,
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
        "productionAuthorized": False,
    }
    result["contentSha256"] = canonical_sha256(result)
    (case_dir / "case-result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def review_summary(repository_root: Path) -> dict[str, Any]:
    validate_bound_sources(repository_root)
    contract = load_contract(repository_root)
    auth = json.loads((repository_root / AUTH_PATH).read_text())
    validate_authorization(auth)
    adapter = load_module("avps_v2_executor_review_adapter", repository_root / ADAPTER_PATH)
    cases = adapter.authorized_case_universe(auth)
    if len(cases) != 360 or len({row["groupId"] for row in cases}) != 72:
        raise ExecutionRefusal("review authorized universe drift")
    # Seeds are deliberately kept in memory. The review output emits only their canonical identity.
    return {
        "status": "REVIEW_ONLY_V2_EXECUTOR_PARITY_PASS_NO_SOLVER",
        "scientificOrdinal": EXPECTED_ORDINAL,
        "executionKey": EXPECTED_EXECUTION_KEY,
        "authorizationHead": EXPECTED_AUTH_HEAD,
        "caseCount": 360,
        "groupCount": 72,
        "statesPerGroup": 5,
        "candidateSeedCanonicalSha256": EXPECTED_SEED_CANONICAL,
        "candidateSeedValuesSerialized": False,
        "explicitFourSpeciesTransportRequired": True,
        "fourAliasDataTreeSha256": EXPECTED_FOUR_ALIAS_TREE,
        "solverExecutionPerformed": False,
        "dispatchCreated": False,
        "resultsOpened": False,
        "productionAuthorized": False,
        "nextRequiredStage": contract["reviewBoundary"]["nextRequiredStage"],
    }


if __name__ == "__main__":
    print(json.dumps(review_summary(Path.cwd()), indent=2, sort_keys=True))
