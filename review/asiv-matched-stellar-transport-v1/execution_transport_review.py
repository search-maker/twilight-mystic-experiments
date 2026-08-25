#!/usr/bin/env python3
"""Hard-disabled execution transport review for ASIV matched stellar transport.

This module freezes the future one-shot deterministic libRadtran transport
mechanics. It is not an authorization document and no workflow in this review
branch invokes a scientific solver.

Physics/input rendering remains owned by the prefrozen execution_candidate.py.
This file only freezes runtime identity checks, one-process execution semantics,
and the exact MYSTIC-STATE-0081 direct-transmission parser convention.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
from pathlib import Path
from typing import Any, Callable

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CANDIDATE_PATH = HERE / "execution_candidate.py"
CONTRACT_PATH = HERE / "EXECUTION_TRANSPORT_CONTRACT.review.json"
OVERLAY_PATH = ROOT / "experiments/aerosol-full-phase-function-sensitivity-v1/execution-candidate/runtime_overlay.py"
PROCESS_RUNNER_PATH = ROOT / "experiments/aerosol-family-challenge-v2-r8-timeout-recovery-v1/execution-candidate/process_runner.py"
RUNTIME_LOCK_PATH = ROOT / "experiments/mystic-batch-v1/runtime-lock.micromamba.json"

EXPECTED_CANDIDATE_GIT_BLOB_SHA1 = "ec433aa3a594311738a6f6aa2b339a7e33d43447"
EXPECTED_OVERLAY_GIT_BLOB_SHA1 = "b7586825d4053f7d4a1e05f057b7c8411f76650b"
EXPECTED_PROCESS_RUNNER_GIT_BLOB_SHA1 = "e23d724e99c1cf9b0b862f8ab48356bd3d9bc56c"
EXPECTED_RUNTIME_LOCK_GIT_BLOB_SHA1 = "8573f62829371a0eb866976a5062ea61dc0767b1"
EXPECTED_RUNTIME_LOCK_RAW_SHA256 = "3b5fbec964642b04c73a6423b3355dbcc4ba5e84f9614f6d74420491bacc20c5"
EXPECTED_PACKAGE_SPEC = "rubin-libradtran=2.0.6=py312pl5321he9373c2_1"
EXPECTED_UVSPEC_SHA256 = "2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3"
EXPECTED_UVSPEC_HELP_SHA256 = "868aea5af762d968f6f62c4e1472916d25232ed9cab5be112d753b0823d20548"
EXPECTED_AUGMENTED_DATA_TREE_SHA256 = "5d8bbf8e6b91ec3d405dee36f21a94afbb6e5ec6cd67da2dd5dd541738199d80"
EXPECTED_ATMOSPHERE_SHA256 = "dab26290ed81c762ed0c607e5dc2d53393c1462a0c3a528bc5e3f5935191cfb5"
EXPECTED_WAVELENGTH_NM = tuple(range(380, 781))
CASE_TIMEOUT_SECONDS = 180

NON_NATIVE_FAMILIES = (
    "opac-continental-average",
    "opac-maritime-clean",
    "opac-desert",
    "opac-desert-spheroids",
)
NATIVE_STATE = "native-rural-ss"


class ExecutionTransportRefusal(RuntimeError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ExecutionTransportRefusal(f"cannot load bound module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_prefrozen_candidate():
    if git_blob_sha1(CANDIDATE_PATH) != EXPECTED_CANDIDATE_GIT_BLOB_SHA1:
        raise ExecutionTransportRefusal("prefrozen render candidate Git blob drift")
    return _load_module(CANDIDATE_PATH, "matched_stellar_prefrozen_render_candidate")


def load_bound_overlay_module():
    if git_blob_sha1(OVERLAY_PATH) != EXPECTED_OVERLAY_GIT_BLOB_SHA1:
        raise ExecutionTransportRefusal("OPAC runtime overlay Git blob drift")
    return _load_module(OVERLAY_PATH, "matched_stellar_bound_opac_overlay")


def load_bound_process_runner_module():
    if git_blob_sha1(PROCESS_RUNNER_PATH) != EXPECTED_PROCESS_RUNNER_GIT_BLOB_SHA1:
        raise ExecutionTransportRefusal("process-group runner Git blob drift")
    return _load_module(PROCESS_RUNNER_PATH, "matched_stellar_bound_process_runner")


def current_transport_binding() -> dict[str, str]:
    return {
        "executionTransportSha256": sha256_file(Path(__file__).resolve()),
        "executionTransportGitBlobSha1": git_blob_sha1(Path(__file__).resolve()),
        "executionCandidateSha256": sha256_file(CANDIDATE_PATH),
        "executionCandidateGitBlobSha1": git_blob_sha1(CANDIDATE_PATH),
        "executionContractSha256": sha256_file(CONTRACT_PATH),
        "executionContractGitBlobSha1": git_blob_sha1(CONTRACT_PATH),
    }


def validate_authorization_document(document: dict[str, Any]) -> None:
    if not isinstance(document, dict):
        raise ExecutionTransportRefusal("authorization must be an object")
    expected_flags = {
        "scientificExecutionAuthorized": True,
        "solverExecutionAuthorized": True,
        "resultOpeningAuthorized": False,
        "productionActivationAuthorized": False,
        "pandoraHoldoutAccessAllowed": False,
        "starsvisibilityMutationAuthorized": False,
        "nativeRebuildAuthorized": False,
        "retryPermitted": False,
        "resumePermitted": False,
        "githubRerunPermitted": False,
    }
    if document.get("schemaVersion") != 1:
        raise ExecutionTransportRefusal("authorization schema drift")
    if document.get("stageId") != "asiv-matched-stellar-transport-v1-execution-authorization":
        raise ExecutionTransportRefusal("authorization stage drift")
    if document.get("status") != "AUTHORIZED_ONE_SHOT_SCIENTIFIC_EXECUTION":
        raise ExecutionTransportRefusal("positive one-shot authorization is absent")
    for key, value in expected_flags.items():
        if document.get(key) is not value:
            raise ExecutionTransportRefusal(f"authorization flag mismatch: {key}")
    if tuple(document.get("families", ())) != NON_NATIVE_FAMILIES:
        raise ExecutionTransportRefusal("authorization aerosol-family universe drift")
    if document.get("nativeState") != NATIVE_STATE or document.get("nativeRenderable") is not False:
        raise ExecutionTransportRefusal("authorization must keep native comparator non-renderable")
    binding = current_transport_binding()
    if document.get("sourceBindings") != binding:
        raise ExecutionTransportRefusal("authorization does not bind exact execution transport bytes")
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if document.get("runtimeIdentity") != contract["runtimeIdentity"]:
        raise ExecutionTransportRefusal("authorization runtime identity drift")


def build_runtime_report(*, uvspec: Path, augmented_data_dir: Path, atmosphere_file: Path,
                         observed_package_spec: str, observed_uvspec_help_sha256: str) -> dict[str, Any]:
    if git_blob_sha1(RUNTIME_LOCK_PATH) != EXPECTED_RUNTIME_LOCK_GIT_BLOB_SHA1:
        raise ExecutionTransportRefusal("runtime-lock Git blob drift")
    if sha256_file(RUNTIME_LOCK_PATH) != EXPECTED_RUNTIME_LOCK_RAW_SHA256:
        raise ExecutionTransportRefusal("runtime-lock raw SHA-256 drift")
    if observed_package_spec != EXPECTED_PACKAGE_SPEC:
        raise ExecutionTransportRefusal("libRadtran package build drift")
    uvspec = Path(uvspec).resolve()
    atmosphere_file = Path(atmosphere_file).resolve()
    augmented_data_dir = Path(augmented_data_dir).resolve()
    if not uvspec.is_file() or sha256_file(uvspec) != EXPECTED_UVSPEC_SHA256:
        raise ExecutionTransportRefusal("uvspec SHA-256 drift")
    if observed_uvspec_help_sha256 != EXPECTED_UVSPEC_HELP_SHA256:
        raise ExecutionTransportRefusal("uvspec --help SHA-256 drift")
    if not atmosphere_file.is_file() or sha256_file(atmosphere_file) != EXPECTED_ATMOSPHERE_SHA256:
        raise ExecutionTransportRefusal("AFGLUS atmosphere SHA-256 drift")
    overlay = load_bound_overlay_module()
    tree_hash, file_count, byte_count = overlay.tree_sha256(augmented_data_dir)
    if tree_hash != EXPECTED_AUGMENTED_DATA_TREE_SHA256:
        raise ExecutionTransportRefusal("augmented OPAC data-tree SHA-256 drift")
    return {
        "schemaVersion": 1,
        "status": "MATCHED_STELLAR_RUNTIME_IDENTITY_VERIFIED",
        "runtimeLockRawSha256": EXPECTED_RUNTIME_LOCK_RAW_SHA256,
        "exactPackageSpec": observed_package_spec,
        "uvspecPath": str(uvspec),
        "uvspecSha256": EXPECTED_UVSPEC_SHA256,
        "uvspecHelpSha256": observed_uvspec_help_sha256,
        "augmentedDataDir": str(augmented_data_dir),
        "augmentedDataTreeSha256": tree_hash,
        "augmentedDataFileCount": file_count,
        "augmentedDataByteCount": byte_count,
        "atmospherePath": str(atmosphere_file),
        "atmosphereSha256": EXPECTED_ATMOSPHERE_SHA256,
        "scientificSolverExecuted": False,
    }


def validate_runtime_report(report: dict[str, Any]) -> None:
    expected = {
        "runtimeLockRawSha256": EXPECTED_RUNTIME_LOCK_RAW_SHA256,
        "exactPackageSpec": EXPECTED_PACKAGE_SPEC,
        "uvspecSha256": EXPECTED_UVSPEC_SHA256,
        "uvspecHelpSha256": EXPECTED_UVSPEC_HELP_SHA256,
        "augmentedDataTreeSha256": EXPECTED_AUGMENTED_DATA_TREE_SHA256,
        "atmosphereSha256": EXPECTED_ATMOSPHERE_SHA256,
    }
    if report.get("schemaVersion") != 1 or report.get("status") != "MATCHED_STELLAR_RUNTIME_IDENTITY_VERIFIED":
        raise ExecutionTransportRefusal("runtime report is not a verified matched-stellar preflight")
    if report.get("scientificSolverExecuted") is not False:
        raise ExecutionTransportRefusal("runtime preflight must precede scientific solver execution")
    for key, value in expected.items():
        if report.get(key) != value:
            raise ExecutionTransportRefusal(f"runtime report identity mismatch: {key}")
    if not report.get("uvspecPath") or not report.get("augmentedDataDir") or not report.get("atmospherePath"):
        raise ExecutionTransportRefusal("runtime report lacks resolved runtime paths")


def finite(name: str, value: object) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ExecutionTransportRefusal(f"{name} must be finite")
    return number


def parse_direct_transmission(stdout_text: str, *, target_altitude_deg: float) -> dict[str, Any]:
    """Exact 0081 convention: output_user lambda edir, then T_direct = edir / mu0."""
    altitude = finite("targetAltitudeDeg", target_altitude_deg)
    mu0 = math.sin(math.radians(altitude))
    if not mu0 > 0:
        raise ExecutionTransportRefusal("target must be above geometric horizon")
    wavelengths: list[float] = []
    transmission: list[float] = []
    for raw in stdout_text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            raise ExecutionTransportRefusal(f"unexpected uvspec output: {raw!r}")
        wavelength = finite("wavelength", parts[0])
        edir = finite("edir", parts[1])
        ray_t = edir / mu0
        if edir < -1e-12 or ray_t < -1e-10 or ray_t > 1.000001:
            raise ExecutionTransportRefusal(f"invalid direct transmission at {wavelength} nm: {ray_t}")
        wavelengths.append(wavelength)
        transmission.append(min(1.0, max(0.0, ray_t)))
    if wavelengths != list(EXPECTED_WAVELENGTH_NM):
        raise ExecutionTransportRefusal("uvspec output grid is not exact 380-780 nm / 1 nm")
    optical_depth: list[float] = []
    for index, value in enumerate(transmission):
        if not 0 < value <= 1:
            raise ExecutionTransportRefusal(f"non-positive direct transmission at wavelength index {index}")
        optical_depth.append(-math.log(value))
    return {
        "wavelengthNm": wavelengths,
        "lineOfSightDirectTransmission": transmission,
        "directOpticalDepth": optical_depth,
        "targetAltitudeDeg": altitude,
        "sourceZenithAngleDeg": 90.0 - altitude,
        "mu0": mu0,
    }


def execute_one_case(*, authorization: dict[str, Any], runtime_report: dict[str, Any],
                     family: str, target_altitude_deg: float, observer_elevation_m: float,
                     aod550: float, process_runner: Callable[..., dict[str, Any]] | None = None) -> dict[str, Any]:
    """Execute exactly one already-prefrozen case after external authorization.

    This function is deliberately not exposed through a CLI in the review PR.
    A future separately reviewed workflow must supply the one-file authorization,
    a verified runtime report, and the bound process-group runner.
    """
    validate_authorization_document(authorization)
    validate_runtime_report(runtime_report)
    if family == NATIVE_STATE:
        raise ExecutionTransportRefusal("native MYSTIC-STATE-0081 comparator cannot be rendered or rebuilt")
    if family not in NON_NATIVE_FAMILIES:
        raise ExecutionTransportRefusal("unknown/non-authorized aerosol family")
    candidate = load_prefrozen_candidate()
    uvspec = Path(runtime_report["uvspecPath"])
    data_dir = Path(runtime_report["augmentedDataDir"])
    atmosphere_file = Path(runtime_report["atmospherePath"])
    wavelength_grid_file = HERE / "wavelength-grid-1nm.dat"
    if not wavelength_grid_file.is_file():
        raise ExecutionTransportRefusal("frozen wavelength grid is missing")
    input_text = candidate.render_uvspec_input(
        family=family,
        data_dir=data_dir,
        atmosphere_file=atmosphere_file,
        wavelength_grid_file=wavelength_grid_file,
        target_altitude_deg=target_altitude_deg,
        observer_elevation_m=observer_elevation_m,
        aod550=aod550,
    )
    if process_runner is None:
        process_runner = load_bound_process_runner_module().run_process_group
    result = process_runner([str(uvspec)], input_text, HERE, CASE_TIMEOUT_SECONDS)
    if result.get("timedOut") is not False:
        raise ExecutionTransportRefusal("uvspec timed out; retry is forbidden")
    if result.get("exitCode") != 0:
        stderr = str(result.get("stderr", ""))[-4000:]
        raise ExecutionTransportRefusal(f"uvspec failed without retry: {stderr}")
    spectrum = parse_direct_transmission(str(result.get("stdout", "")), target_altitude_deg=target_altitude_deg)
    return {
        "schemaVersion": 1,
        "status": "MATCHED_STELLAR_CASE_EXECUTED_ONCE",
        "family": family,
        "targetAltitudeDeg": float(target_altitude_deg),
        "observerElevationM": float(observer_elevation_m),
        "aod550": float(aod550),
        "solver": "sdisort",
        "scatteringOrder": 1,
        "solverExecutionCount": 1,
        "retryPermitted": False,
        "inputSha256": sha256_bytes(input_text.encode("utf-8")),
        "rawStdoutSha256": sha256_bytes(str(result.get("stdout", "")).encode("utf-8")),
        "rawStderrSha256": sha256_bytes(str(result.get("stderr", "")).encode("utf-8")),
        "processGroupIsolated": result.get("processGroupIsolated"),
        "spectrum": spectrum,
        "claimBoundary": "computational-direct-stellar-transport-only-not-empirical-validation-not-production",
    }


def main() -> int:
    # Review-only CLI: print exact bytes that a future authorization must bind.
    # There is intentionally no execute subcommand in this review package.
    print(json.dumps({
        "status": "REVIEW_ONLY_NO_EXECUTION_CLI",
        "sourceBindings": current_transport_binding(),
        "scientificExecutionAuthorized": False,
        "solverExecutionAuthorized": False,
        "pandoraHoldoutAccessAllowed": False,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
