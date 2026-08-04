#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterable

STAGE_ID = "twilight-surrogate-tier-1-libradtran-provenance-recovery-v1"
EXPECTED_SOURCE_SHA256 = "999e47f4af4b5df6f85a6887fc105fc8f6e1a7cee89a3124f69ac8d8912c8e85"
CURRENT_OFFICIAL_OBSERVED_SHA256 = "64930cc40b6e4a37aa220520974d330fc1563796f466a649b2238131f2d69840"
FEEDSTOCK_COMMIT = "0ace9da0ce3a994f71fefc14b9b91d12b54a7be8"
FEEDSTOCK_RECIPE_BLOB_SHA = "f694ceab790989eebaf9bd1763305a1d86e6b723"
FEEDSTOCK_SOURCE_URL = "http://www.libradtran.org/download/libRadtran-2.0.6.tar.gz"
PACKAGE_NAME = "rubin-libradtran"
PACKAGE_VERSION = "2.0.6"
PACKAGE_BUILD = "py312pl5321he9373c2_1"
EXPECTED_UVSPEC_SHA256 = "2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3"
MAX_WAYBACK_DISTINCT_DIGESTS = 8


class ProvenanceError(RuntimeError):
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


def write_json(path: Path, value: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump(value), encoding="utf-8")
    return raw_sha256(path)


def request_bytes(url: str, timeout: int = 180) -> tuple[bytes, str, dict[str, str]]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "twilight-tier1-provenance-recovery/1",
            "Accept": "*/*",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        headers = {str(key).lower(): str(value) for key, value in response.headers.items()}
        return response.read(), response.geturl(), headers


def download(url: str, destination: Path, timeout: int = 240) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "twilight-tier1-provenance-recovery/1",
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
        "responseHeaders": headers,
        "sizeBytes": destination.stat().st_size,
        "sha256": raw_sha256(destination),
    }


def validate_feedstock(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ProvenanceError(f"feedstock recipe missing: {path}")
    blob_sha = git_blob_sha1(path)
    if blob_sha != FEEDSTOCK_RECIPE_BLOB_SHA:
        raise ProvenanceError(f"feedstock recipe blob mismatch: {blob_sha}")
    text = path.read_text(encoding="utf-8")
    required = (
        '{% set version = "2.0.6" %}',
        "url: http://www.libradtran.org/download/libRadtran-{{ version }}.tar.gz",
        f"sha256: {EXPECTED_SOURCE_SHA256}",
    )
    missing = [value for value in required if value not in text]
    if missing:
        raise ProvenanceError(f"feedstock recipe binding changed: {missing}")
    return {
        "commit": FEEDSTOCK_COMMIT,
        "recipeBlobSha1": blob_sha,
        "recipeRawSha256": raw_sha256(path),
        "sourceUrl": FEEDSTOCK_SOURCE_URL,
        "sourceSha256": EXPECTED_SOURCE_SHA256,
    }


def find_recipe_meta(package_info_dir: Path) -> Path:
    preferred = package_info_dir / "info" / "recipe" / "meta.yaml"
    if preferred.is_file():
        return preferred
    candidates = sorted(package_info_dir.rglob("meta.yaml"))
    candidates = [path for path in candidates if "recipe" in path.parts]
    if len(candidates) != 1:
        raise ProvenanceError(
            f"expected one embedded package recipe meta.yaml, found {len(candidates)}"
        )
    return candidates[0]


def validate_package_provenance(
    package_record_path: Path,
    package_archive: Path,
    package_info_dir: Path,
    package_payload_dir: Path,
    installed_uvspec: Path,
) -> dict[str, Any]:
    for path, label in (
        (package_record_path, "conda package record"),
        (package_archive, "exact package archive"),
        (installed_uvspec, "installed uvspec"),
    ):
        if not path.is_file():
            raise ProvenanceError(f"{label} missing: {path}")
    record = json.loads(package_record_path.read_text(encoding="utf-8"))
    expected = {
        "name": PACKAGE_NAME,
        "version": PACKAGE_VERSION,
        "build": PACKAGE_BUILD,
    }
    for field, value in expected.items():
        if record.get(field) != value:
            raise ProvenanceError(
                f"conda package record {field} mismatch: {record.get(field)!r}"
            )
    archive_sha = raw_sha256(package_archive)
    record_sha = record.get("sha256")
    if record_sha and archive_sha != record_sha:
        raise ProvenanceError(
            f"package archive sha256 does not match conda record: {archive_sha} != {record_sha}"
        )

    index_path = package_info_dir / "info" / "index.json"
    paths_path = package_info_dir / "info" / "paths.json"
    if not index_path.is_file() or not paths_path.is_file():
        raise ProvenanceError("extracted package info/index.json or info/paths.json missing")
    index = json.loads(index_path.read_text(encoding="utf-8"))
    for field, value in expected.items():
        if index.get(field) != value:
            raise ProvenanceError(
                f"embedded package index {field} mismatch: {index.get(field)!r}"
            )

    recipe_path = find_recipe_meta(package_info_dir)
    recipe_text = recipe_path.read_text(encoding="utf-8")
    if EXPECTED_SOURCE_SHA256 not in recipe_text:
        raise ProvenanceError("embedded package recipe lacks original source sha256")
    if "libRadtran-2.0.6.tar.gz" not in recipe_text:
        raise ProvenanceError("embedded package recipe lacks exact source filename")

    paths = json.loads(paths_path.read_text(encoding="utf-8"))
    rows = paths.get("paths")
    if not isinstance(rows, list):
        raise ProvenanceError("embedded package paths.json lacks paths list")
    matches = [row for row in rows if row.get("_path") == "bin/uvspec"]
    if len(matches) != 1:
        raise ProvenanceError(f"expected one package bin/uvspec path, found {len(matches)}")
    uvspec_row = matches[0]
    packaged_uvspec = package_payload_dir / "bin" / "uvspec"
    if not packaged_uvspec.is_file():
        raise ProvenanceError("packaged bin/uvspec missing")
    packaged_uvspec_sha = raw_sha256(packaged_uvspec)
    recorded_uvspec_sha = uvspec_row.get("sha256")
    if recorded_uvspec_sha and packaged_uvspec_sha != recorded_uvspec_sha:
        raise ProvenanceError(
            "packaged uvspec sha256 does not match package paths metadata"
        )
    installed_uvspec_sha = raw_sha256(installed_uvspec)
    if installed_uvspec_sha != EXPECTED_UVSPEC_SHA256:
        raise ProvenanceError(
            f"installed frozen uvspec sha256 mismatch: {installed_uvspec_sha}"
        )

    selected_info: list[dict[str, Any]] = []
    for relative in (
        "info/index.json",
        "info/paths.json",
        "info/recipe/meta.yaml",
        "info/hash_input.json",
        "info/about.json",
        "info/repodata_record.json",
    ):
        path = package_info_dir / relative
        if path.is_file():
            selected_info.append(
                {
                    "path": relative,
                    "sizeBytes": path.stat().st_size,
                    "rawSha256": raw_sha256(path),
                }
            )

    return {
        "decision": True,
        "name": PACKAGE_NAME,
        "version": PACKAGE_VERSION,
        "build": PACKAGE_BUILD,
        "packageArchiveSha256": archive_sha,
        "packageRecordSha256": record_sha,
        "packageUrl": record.get("url"),
        "packageRecordRawSha256": raw_sha256(package_record_path),
        "embeddedRecipePath": recipe_path.relative_to(package_info_dir).as_posix(),
        "embeddedRecipeRawSha256": raw_sha256(recipe_path),
        "embeddedRecipeSourceSha256": EXPECTED_SOURCE_SHA256,
        "packagedUvspecSha256": packaged_uvspec_sha,
        "packagedUvspecRecordedSha256": recorded_uvspec_sha,
        "installedUvspecSha256": installed_uvspec_sha,
        "installedUvspecMatchesFrozenIdentity": True,
        "selectedPackageInfo": selected_info,
    }


def select_wayback_rows(rows: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    selected: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for row in sorted(rows, key=lambda item: item.get("timestamp", "")):
        key = (row.get("digest", ""), row.get("length", ""))
        if key in seen:
            continue
        seen.add(key)
        selected.append(row)
        if len(selected) >= MAX_WAYBACK_DISTINCT_DIGESTS:
            break
    return selected


def discover_wayback() -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    discovered: list[dict[str, str]] = []
    errors: list[dict[str, Any]] = []
    for original in (
        FEEDSTOCK_SOURCE_URL,
        FEEDSTOCK_SOURCE_URL.replace("http://", "https://", 1),
    ):
        query = urllib.parse.urlencode(
            [
                ("url", original),
                ("output", "json"),
                ("fl", "timestamp,original,statuscode,digest,length,mimetype"),
                ("filter", "statuscode:200"),
                ("collapse", "digest"),
            ]
        )
        endpoint = "https://web.archive.org/cdx/search/cdx?" + query
        try:
            raw, final_url, _headers = request_bytes(endpoint, timeout=120)
            payload = json.loads(raw.decode("utf-8"))
            if not isinstance(payload, list) or not payload:
                raise ProvenanceError("Wayback CDX response is empty or malformed")
            header = payload[0]
            if not isinstance(header, list):
                raise ProvenanceError("Wayback CDX header is malformed")
            for values in payload[1:]:
                if not isinstance(values, list) or len(values) != len(header):
                    continue
                row = {str(key): str(value) for key, value in zip(header, values, strict=True)}
                row["cdxEndpoint"] = final_url
                discovered.append(row)
        except Exception as exc:
            errors.append(
                {
                    "originalUrl": original,
                    "endpoint": endpoint,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
    return select_wayback_rows(discovered), errors


def static_candidates() -> list[dict[str, str]]:
    return [
        {
            "kind": "feedstock-original-url-current-response",
            "url": FEEDSTOCK_SOURCE_URL,
        },
        {
            "kind": "conda-source-cache-candidate",
            "url": "https://sources.conda.io/libRadtran-2.0.6.tar.gz",
        },
        {
            "kind": "anaconda-source-cache-candidate",
            "url": "https://repo.anaconda.com/pkgs/main/src_cache/libRadtran-2.0.6.tar.gz",
        },
    ]


def recover_exact_source(output_dir: Path) -> dict[str, Any]:
    attempts_dir = output_dir / "source-recovery-attempts"
    attempts_dir.mkdir(parents=True, exist_ok=True)
    wayback_rows, discovery_errors = discover_wayback()
    candidates = static_candidates()
    for row in wayback_rows:
        timestamp = row.get("timestamp", "")
        original = row.get("original", FEEDSTOCK_SOURCE_URL)
        candidates.append(
            {
                "kind": "wayback-distinct-digest",
                "url": f"https://web.archive.org/web/{timestamp}id_/{original}",
                "timestamp": timestamp,
                "waybackDigest": row.get("digest", ""),
                "waybackLength": row.get("length", ""),
                "originalUrl": original,
            }
        )

    attempts: list[dict[str, Any]] = []
    recovered_path: Path | None = None
    for index, candidate in enumerate(candidates):
        if recovered_path is not None:
            break
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
                recovered_path = recovered_dir / "libRadtran-2.0.6.tar.gz"
                shutil.move(str(temporary), recovered_path)
                row["preservedPath"] = recovered_path.relative_to(output_dir).as_posix()
            else:
                temporary.unlink(missing_ok=True)
        except Exception as exc:
            temporary.unlink(missing_ok=True)
            row["error"] = f"{type(exc).__name__}: {exc}"
            row["matchesExpectedSourceSha256"] = False
            row["matchesCurrentOfficialObservedSha256"] = False
        attempts.append(row)

    current_mutation_observed = any(
        row.get("matchesCurrentOfficialObservedSha256") is True for row in attempts
    )
    return {
        "expectedSourceSha256": EXPECTED_SOURCE_SHA256,
        "currentOfficialObservedSha256": CURRENT_OFFICIAL_OBSERVED_SHA256,
        "expectedHashChangedToMakeCiGreen": False,
        "currentOfficialHashPromotedToExpected": False,
        "waybackDistinctDigestCount": len(wayback_rows),
        "waybackDiscoveryErrors": discovery_errors,
        "attempts": attempts,
        "exactHistoricalSourceArchiveRecovered": recovered_path is not None,
        "recoveredPath": (
            recovered_path.relative_to(output_dir).as_posix()
            if recovered_path is not None
            else None
        ),
        "currentOfficialMutableSameVersionResponseObserved": current_mutation_observed,
    }


def load_source_audit_module(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("tier1_exact_source_audit", path)
    if spec is None or spec.loader is None:
        raise ProvenanceError(f"cannot load source audit module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def classify_decision(
    package_provenance: bool,
    exact_source_recovered: bool,
    source_mechanism_audit: bool,
) -> tuple[str, bool]:
    if not package_provenance:
        return "PACKAGE_PROVENANCE_FAILED", False
    if exact_source_recovered and source_mechanism_audit:
        return "EXACT_HISTORICAL_SOURCE_RECOVERED_PACKAGE_PROVENANCE_BOUND", True
    return "PACKAGE_PROVENANCE_BOUND_EXACT_HISTORICAL_SOURCE_NOT_RECOVERED", False


def governance_boundary() -> dict[str, Any]:
    return {
        "scientificExecution": False,
        "scientificDatasetProduced": False,
        "solverExecutionCount": 0,
        "syntaxCheckCount": 0,
        "surrogateTrainingUsePermitted": False,
        "authorizationPermitted": False,
        "ordinal2ScientificDispatchPermitted": False,
        "githubRerunPermitted": False,
        "frozenTier1InvariantsChanged": False,
        "sourceHashChangePermitted": False,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    feedstock = validate_feedstock(args.feedstock_meta)
    package = validate_package_provenance(
        args.package_record,
        args.package_archive,
        args.package_info_dir,
        args.package_payload_dir,
        args.installed_uvspec,
    )
    recovery = recover_exact_source(args.output_dir)

    source_audit_report: dict[str, Any] | None = None
    source_mechanism_audit_passed = False
    if recovery["exactHistoricalSourceArchiveRecovered"]:
        archive_path = args.output_dir / str(recovery["recoveredPath"])
        module = load_source_audit_module(args.source_audit_module)
        source_audit_report = module.audit_archive(
            archive_path,
            args.output_dir / "exact-source-mechanism-audit",
            EXPECTED_SOURCE_SHA256,
        )
        source_mechanism_audit_passed = (
            source_audit_report.get("sourceArchiveSha256")
            == EXPECTED_SOURCE_SHA256
            and source_audit_report.get("expectedSourceArchiveSha256")
            == EXPECTED_SOURCE_SHA256
        )

    status, gate_passed = classify_decision(
        package["decision"],
        recovery["exactHistoricalSourceArchiveRecovered"],
        source_mechanism_audit_passed,
    )
    report = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": status,
        "provenanceGatePassed": gate_passed,
        "sourceEvidenceAccepted": gate_passed,
        "packageProvenanceDecision": package["decision"],
        "exactHistoricalSourceArchiveRecovered": recovery[
            "exactHistoricalSourceArchiveRecovered"
        ],
        "sourceMechanismAuditDecision": source_mechanism_audit_passed,
        "feedstock": feedstock,
        "package": package,
        "sourceRecovery": recovery,
        "sourceMechanismAudit": source_audit_report,
        "behaviorProofRemainsSeparateFromSourceProvenance": True,
        **governance_boundary(),
        "boundary": (
            "source provenance recovery only; exact package metadata is necessary but not "
            "sufficient for exact-source acceptance, and no scientific execution or authorization occurs"
        ),
    }
    report_path = args.output_dir / "libradtran-provenance-recovery.json"
    report_path.write_text(dump(report), encoding="utf-8")
    report["reportRawSha256"] = raw_sha256(report_path)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--feedstock-meta", type=Path, required=True)
    parser.add_argument("--package-record", type=Path, required=True)
    parser.add_argument("--package-archive", type=Path, required=True)
    parser.add_argument("--package-info-dir", type=Path, required=True)
    parser.add_argument("--package-payload-dir", type=Path, required=True)
    parser.add_argument("--installed-uvspec", type=Path, required=True)
    parser.add_argument("--source-audit-module", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = run(args)
        print(dump(report), end="")
        return 0 if report["provenanceGatePassed"] else 2
    except Exception as exc:
        failure = {
            "schemaVersion": 1,
            "stageId": STAGE_ID,
            "status": "REFUSED",
            "provenanceGatePassed": False,
            "sourceEvidenceAccepted": False,
            "reason": f"{type(exc).__name__}: {exc}",
            **governance_boundary(),
        }
        try:
            args.output_dir.mkdir(parents=True, exist_ok=True)
            path = args.output_dir / "libradtran-provenance-recovery.json"
            if not path.exists():
                path.write_text(dump(failure), encoding="utf-8")
        except Exception:
            pass
        print(dump(failure), file=sys.stderr, end="")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
