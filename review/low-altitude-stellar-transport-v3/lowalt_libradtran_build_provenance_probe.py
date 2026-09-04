#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

STAGE_ID = "lowalt-libradtran-build-provenance-probe-v1"
EXPECTED_SOURCE_SHA256 = "999e47f4af4b5df6f85a6887fc105fc8f6e1a7cee89a3124f69ac8d8912c8e85"
CURRENT_OFFICIAL_OBSERVED_SHA256 = "64930cc40b6e4a37aa220520974d330fc1563796f466a649b2238131f2d69840"
EXPECTED_PACKAGE_SHA256 = "9090033a39a7e963ecabb31d5cbd264330c64ec1c4cb5f44be2e70f10cbc54c2"
EXPECTED_UVSPEC_SHA256 = "2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3"
EXPECTED_FEEDSTOCK_PRODUCER = "52d709673d44aa958680321ea745d30b58ecf103"
EXPECTED_FEEDSTOCK_REMOTE = "https://github.com/conda-forge/rubin-libradtran-feedstock"
EXPECTED_FLOW_RUN_ID = "azure_20260301.2.1"
EXPECTED_BUILD_SCRIPT_BLOB_SHA1 = "e796f81c8e5a258d0b5c41fb80d92b015015d30a"
EXPECTED_RENDERED_CONFIG_SHA256 = "14218a2f76d2a8d8b09443f8bd5805de69d11a9f11a80dd1cb226a5f8dbcbd7a"
PACKAGE_NAME = "rubin-libradtran"
PACKAGE_VERSION = "2.0.6"
PACKAGE_BUILD = "py312pl5321he9373c2_1"
SOURCE_FILENAME = "libRadtran-2.0.6.tar.gz"
SOURCE_CACHE_URL = f"https://sources.conda.io/{SOURCE_FILENAME}"
WAYBACK_AVAILABILITY = "https://archive.org/wayback/available"
WAYBACK_TARGET_TIMESTAMP = "20250903160541"
MAX_WAYBACK_DOWNLOADS = 1


class ProbeError(RuntimeError):
    pass


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def raw_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_blob_sha1(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(
        f"blob {len(raw)}\0".encode() + raw,
        usedforsecurity=False,
    ).hexdigest()


def request_json(url: str, timeout: int = 45) -> tuple[Any, str]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "lowalt-libradtran-provenance-probe/1",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8")), response.geturl()


def download(url: str, destination: Path, timeout: int = 240) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "lowalt-libradtran-provenance-probe/1",
            "Accept": "*/*",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response, destination.open("wb") as output:
        shutil.copyfileobj(response, output)
        final_url = response.geturl()
        headers = {str(key).lower(): str(value) for key, value in response.headers.items()}
    return {
        "requestedUrl": url,
        "finalUrl": final_url,
        "sizeBytes": destination.stat().st_size,
        "sha256": raw_sha256(destination),
        "responseHeaders": headers,
    }


def validate_package(
    package_archive: Path,
    package_info_dir: Path,
    package_payload_dir: Path,
    installed_uvspec: Path,
) -> dict[str, Any]:
    archive_sha = raw_sha256(package_archive)
    if archive_sha != EXPECTED_PACKAGE_SHA256:
        raise ProbeError(f"exact package archive mismatch: {archive_sha}")

    info = package_info_dir / "info"
    index = json.loads((info / "index.json").read_text(encoding="utf-8"))
    for key, expected in {
        "name": PACKAGE_NAME,
        "version": PACKAGE_VERSION,
        "build": PACKAGE_BUILD,
    }.items():
        if index.get(key) != expected:
            raise ProbeError(f"package index {key} mismatch: {index.get(key)!r}")

    about = json.loads((info / "about.json").read_text(encoding="utf-8"))
    extra = about.get("extra") or {}
    if extra.get("remote_url") != EXPECTED_FEEDSTOCK_REMOTE:
        raise ProbeError(f"feedstock remote mismatch: {extra.get('remote_url')!r}")
    if extra.get("sha") != EXPECTED_FEEDSTOCK_PRODUCER:
        raise ProbeError(f"actual package producer commit mismatch: {extra.get('sha')!r}")
    if extra.get("flow_run_id") != EXPECTED_FLOW_RUN_ID:
        raise ProbeError(f"producer flow run mismatch: {extra.get('flow_run_id')!r}")

    recipe = info / "recipe"
    meta = (recipe / "meta.yaml").read_text(encoding="utf-8")
    if EXPECTED_SOURCE_SHA256 not in meta or SOURCE_FILENAME not in meta:
        raise ProbeError("embedded rendered recipe lost historical source binding")
    build_script = recipe / "build.sh"
    build_blob = git_blob_sha1(build_script)
    if build_blob != EXPECTED_BUILD_SCRIPT_BLOB_SHA1:
        raise ProbeError(f"embedded build.sh blob mismatch: {build_blob}")
    rendered_config = recipe / "conda_build_config.yaml"
    rendered_config_sha = raw_sha256(rendered_config)
    if rendered_config_sha != EXPECTED_RENDERED_CONFIG_SHA256:
        raise ProbeError(f"rendered conda config mismatch: {rendered_config_sha}")

    hash_input = json.loads((info / "hash_input.json").read_text(encoding="utf-8"))
    expected_hash_inputs = {
        "c_compiler": "gcc",
        "c_compiler_version": "13",
        "cxx_compiler": "gxx",
        "cxx_compiler_version": "13",
        "fortran_compiler": "gfortran",
        "fortran_compiler_version": "13",
        "c_stdlib": "sysroot",
        "c_stdlib_version": "2.17",
        "libnetcdf": "4.10.0",
        "target_platform": "linux-64",
        "python": "3.12.* *_cpython",
    }
    for key, expected in expected_hash_inputs.items():
        if hash_input.get(key) != expected:
            raise ProbeError(f"hash input {key} mismatch: {hash_input.get(key)!r}")

    paths = json.loads((info / "paths.json").read_text(encoding="utf-8"))
    rows = paths.get("paths")
    if not isinstance(rows, list):
        raise ProbeError("package paths metadata missing list")
    uvspec_rows = [row for row in rows if row.get("_path") == "bin/uvspec"]
    if len(uvspec_rows) != 1 or uvspec_rows[0].get("sha256") != EXPECTED_UVSPEC_SHA256:
        raise ProbeError("package paths metadata does not bind exact uvspec")

    packaged_uvspec = package_payload_dir / "bin" / "uvspec"
    packaged_uvspec_sha = raw_sha256(packaged_uvspec)
    installed_uvspec_sha = raw_sha256(installed_uvspec)
    if packaged_uvspec_sha != EXPECTED_UVSPEC_SHA256:
        raise ProbeError(f"packaged uvspec mismatch: {packaged_uvspec_sha}")
    if installed_uvspec_sha != EXPECTED_UVSPEC_SHA256:
        raise ProbeError(f"installed uvspec mismatch: {installed_uvspec_sha}")

    return {
        "decision": True,
        "packageArchiveSha256": archive_sha,
        "packageProducerCommit": extra["sha"],
        "packageProducerRemote": extra["remote_url"],
        "packageProducerFlowRunId": extra["flow_run_id"],
        "embeddedBuildScriptBlobSha1": build_blob,
        "renderedCondaBuildConfigSha256": rendered_config_sha,
        "embeddedSourceSha256": EXPECTED_SOURCE_SHA256,
        "packagedUvspecSha256": packaged_uvspec_sha,
        "installedUvspecSha256": installed_uvspec_sha,
        "hashInputs": {key: hash_input[key] for key in expected_hash_inputs},
    }


def wayback_snapshot_candidates() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    found: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []
    seen: set[str] = set()
    originals = [
        f"http://www.libradtran.org/download/{SOURCE_FILENAME}",
        f"https://www.libradtran.org/download/{SOURCE_FILENAME}",
    ]
    for original in originals:
        query = urllib.parse.urlencode(
            {"url": original, "timestamp": WAYBACK_TARGET_TIMESTAMP}
        )
        endpoint = f"{WAYBACK_AVAILABILITY}?{query}"
        try:
            payload, final_url = request_json(endpoint)
            snapshot = ((payload or {}).get("archived_snapshots") or {}).get("closest") or {}
            if snapshot.get("available") is not True or not snapshot.get("url"):
                errors.append(
                    {
                        "endpoint": final_url,
                        "error": "no available closest snapshot",
                        "originalUrl": original,
                    }
                )
                continue
            timestamp = str(snapshot.get("timestamp") or "")
            snapshot_url = str(snapshot["url"])
            if timestamp:
                raw_url = f"https://web.archive.org/web/{timestamp}id_/{original}"
            else:
                raw_url = snapshot_url
            if raw_url in seen:
                continue
            seen.add(raw_url)
            found.append(
                {
                    "kind": "wayback-availability-near-hash-correction",
                    "url": raw_url,
                    "snapshotUrl": snapshot_url,
                    "timestamp": timestamp,
                    "originalUrl": original,
                    "availabilityEndpoint": final_url,
                }
            )
        except Exception as exc:
            errors.append(
                {
                    "endpoint": endpoint,
                    "error": f"{type(exc).__name__}: {exc}",
                    "originalUrl": original,
                }
            )
    return found[:MAX_WAYBACK_DOWNLOADS], errors


def recover_source(output_dir: Path) -> dict[str, Any]:
    attempts_dir = output_dir / "source-attempts"
    attempts_dir.mkdir(parents=True, exist_ok=True)
    candidates: list[dict[str, str]] = [
        {"kind": "conda-source-cache-reprobe", "url": SOURCE_CACHE_URL},
    ]
    wayback, discovery_errors = wayback_snapshot_candidates()
    candidates.extend(wayback)

    attempts: list[dict[str, Any]] = []
    recovered: Path | None = None
    for index, candidate in enumerate(candidates):
        temporary = attempts_dir / f"candidate-{index:02d}.tar.gz"
        row: dict[str, Any] = {**candidate, "attemptIndex": index}
        try:
            result = download(candidate["url"], temporary)
            row.update(result)
            row["matchesExpectedSourceSha256"] = (
                result["sha256"] == EXPECTED_SOURCE_SHA256
            )
            row["matchesCurrentOfficialObservedSha256"] = (
                result["sha256"] == CURRENT_OFFICIAL_OBSERVED_SHA256
            )
            if row["matchesExpectedSourceSha256"]:
                recovered_dir = output_dir / "recovered-exact-source"
                recovered_dir.mkdir(parents=True, exist_ok=True)
                recovered = recovered_dir / SOURCE_FILENAME
                shutil.move(str(temporary), recovered)
                row["preservedPath"] = recovered.relative_to(output_dir).as_posix()
                attempts.append(row)
                break
            temporary.unlink(missing_ok=True)
        except Exception as exc:
            temporary.unlink(missing_ok=True)
            row["error"] = f"{type(exc).__name__}: {exc}"
            row["matchesExpectedSourceSha256"] = False
            row["matchesCurrentOfficialObservedSha256"] = False
        attempts.append(row)

    return {
        "expectedSourceSha256": EXPECTED_SOURCE_SHA256,
        "currentOfficialObservedSha256": CURRENT_OFFICIAL_OBSERVED_SHA256,
        "sourceHashChangedOrRelaxed": False,
        "waybackTargetTimestamp": WAYBACK_TARGET_TIMESTAMP,
        "waybackDiscoveryErrors": discovery_errors,
        "attempts": attempts,
        "exactHistoricalSourceArchiveRecovered": recovered is not None,
        "recoveredPath": (
            recovered.relative_to(output_dir).as_posix() if recovered else None
        ),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    package = validate_package(
        args.package_archive,
        args.package_info_dir,
        args.package_payload_dir,
        args.installed_uvspec,
    )
    source = recover_source(args.output_dir)
    report = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": (
            "EXACT_SOURCE_RECOVERED"
            if source["exactHistoricalSourceArchiveRecovered"]
            else "EXACT_PACKAGE_PRODUCER_BOUND_SOURCE_BYTES_STILL_UNRECOVERED"
        ),
        "packageProducerProvenancePassed": package["decision"],
        "sourceProvenanceGatePassed": source["exactHistoricalSourceArchiveRecovered"],
        "solverEquivalencePromotionPermitted": False,
        "scientificExecution": False,
        "solverExecutionCount": 0,
        "protectedResultOpened": False,
        "avpsStateMutated": False,
        "v1SeamChanged": False,
        "expectedSourceHashChanged": False,
        "package": package,
        "sourceRecovery": source,
        "boundary": (
            "POST_V1 provenance probe only; exact-source recovery is evidence, not "
            "solver-equivalence or science authorization"
        ),
    }
    path = args.output_dir / "lowalt-libradtran-build-provenance-probe.json"
    path.write_text(dump(report), encoding="utf-8")
    report["reportRawSha256"] = raw_sha256(path)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-archive", type=Path, required=True)
    parser.add_argument("--package-info-dir", type=Path, required=True)
    parser.add_argument("--package-payload-dir", type=Path, required=True)
    parser.add_argument("--installed-uvspec", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = run(args)
        print(dump(report), end="")
        return 0
    except Exception as exc:
        failure = {
            "schemaVersion": 1,
            "stageId": STAGE_ID,
            "status": "REFUSED",
            "packageProducerProvenancePassed": False,
            "sourceProvenanceGatePassed": False,
            "solverEquivalencePromotionPermitted": False,
            "scientificExecution": False,
            "solverExecutionCount": 0,
            "protectedResultOpened": False,
            "avpsStateMutated": False,
            "v1SeamChanged": False,
            "expectedSourceHashChanged": False,
            "reason": f"{type(exc).__name__}: {exc}",
        }
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (
            args.output_dir / "lowalt-libradtran-build-provenance-probe.json"
        ).write_text(dump(failure), encoding="utf-8")
        print(dump(failure), file=sys.stderr, end="")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
