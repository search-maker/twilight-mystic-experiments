#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import tarfile
import urllib.request
from pathlib import Path, PurePosixPath
from typing import Any

STAGE_ID = "twilight-surrogate-tier-1-libradtran-source-audit-v1"
SOURCE_URL = "https://www.libradtran.org/download/libRadtran-2.0.6.tar.gz"
SOURCE_SHA256 = "999e47f4af4b5df6f85a6887fc105fc8f6e1a7cee89a3124f69ac8d8912c8e85"
FEEDSTOCK_REPOSITORY = "conda-forge/rubin-libradtran-feedstock"
FEEDSTOCK_COMMIT = "0ace9da0ce3a994f71fefc14b9b91d12b54a7be8"
FEEDSTOCK_RECIPE_PATH = "recipe/meta.yaml"
FEEDSTOCK_RECIPE_BLOB_SHA = "f694ceab790989eebaf9bd1763305a1d86e6b723"
SELECTED_SUFFIXES = (
    "src_py/lex_starter.l",
    "src/cloud3d.c",
    "src/elevation2d.c",
    "src/atmosphere.c",
)


class SourceAuditError(RuntimeError):
    pass


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "twilight-tier1-source-audit/1"},
    )
    with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as output:
        shutil.copyfileobj(response, output)


def safe_member_name(name: str) -> PurePosixPath:
    value = PurePosixPath(name)
    if value.is_absolute() or ".." in value.parts:
        raise SourceAuditError(f"unsafe tar member: {name}")
    return value


def locate_members(archive: tarfile.TarFile) -> dict[str, tarfile.TarInfo]:
    matches: dict[str, list[tarfile.TarInfo]] = {
        suffix: [] for suffix in SELECTED_SUFFIXES
    }
    for member in archive.getmembers():
        path = safe_member_name(member.name)
        if not member.isfile():
            continue
        normalized = path.as_posix()
        for suffix in SELECTED_SUFFIXES:
            if normalized == suffix or normalized.endswith("/" + suffix):
                matches[suffix].append(member)
    selected: dict[str, tarfile.TarInfo] = {}
    for suffix, rows in matches.items():
        if len(rows) != 1:
            raise SourceAuditError(
                f"expected exactly one {suffix}, found {len(rows)}"
            )
        selected[suffix] = rows[0]
    return selected


def require(pattern: str, value: str, label: str) -> None:
    if re.search(
        pattern,
        value,
        flags=re.IGNORECASE | re.MULTILINE | re.DOTALL,
    ) is None:
        raise SourceAuditError(f"source evidence changed: {label}")


def audit_archive(
    archive_path: Path,
    output_dir: Path,
    expected_sha256: str = SOURCE_SHA256,
) -> dict[str, Any]:
    actual_sha = sha256_file(archive_path)
    if actual_sha != expected_sha256:
        raise SourceAuditError(
            f"source archive sha256 mismatch: {actual_sha}"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    preserved = output_dir / "primary-source"
    if preserved.exists():
        shutil.rmtree(preserved)
    preserved.mkdir(parents=True)

    texts: dict[str, str] = {}
    files: list[dict[str, Any]] = []
    with tarfile.open(archive_path, "r:gz") as archive:
        selected = locate_members(archive)
        for suffix in SELECTED_SUFFIXES:
            member = selected[suffix]
            handle = archive.extractfile(member)
            if handle is None:
                raise SourceAuditError(f"cannot read {member.name}")
            raw = handle.read()
            target = preserved / suffix
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            texts[suffix] = raw.decode("utf-8", errors="strict")
            files.append(
                {
                    "archivePath": member.name,
                    "preservedPath": target.relative_to(output_dir).as_posix(),
                    "rawSha256": sha256_bytes(raw),
                    "sizeBytes": len(raw),
                }
            )

    lex = texts["src_py/lex_starter.l"]
    cloud = texts["src/cloud3d.c"]
    elevation = texts["src/elevation2d.c"]
    atmosphere = texts["src/atmosphere.c"]

    require(
        r"Input\.rte\.solver\s*==\s*SOLVER_MONTECARLO.*"
        r"Input\.alt\.altitude\s*!=\s*NOT_DEFINED_FLOAT",
        lex,
        "explicit Monte Carlo altitude guard",
    )
    require(
        r"option altitude does not work with.*solver montecarlo.*"
        r"Use mc_elevation_file",
        lex,
        "exact altitude rejection",
    )
    require(
        r"FN_MC_ELEVATION",
        cloud,
        "mc_elevation_file filename binding",
    )
    require(
        r"setup_elevation2D\s*\(",
        cloud,
        "2D elevation loader call",
    )
    require(
        r"elev2D\s*=\s*1",
        cloud,
        "2D elevation activation",
    )
    require(
        r"setup_elevation2D\s*\(",
        elevation,
        "2D elevation implementation",
    )
    require(
        r"input\.alt\.altitude",
        atmosphere,
        "separate atmosphere altitude path",
    )

    report = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": (
            "EXACT_SOURCE_MECHANISMS_DISTINCT_"
            "EQUIVALENCE_NOT_ESTABLISHED"
        ),
        "sourceUrl": SOURCE_URL,
        "sourceArchiveSha256": actual_sha,
        "expectedSourceArchiveSha256": expected_sha256,
        "feedstock": {
            "repository": FEEDSTOCK_REPOSITORY,
            "commit": FEEDSTOCK_COMMIT,
            "recipePath": FEEDSTOCK_RECIPE_PATH,
            "recipeBlobSha": FEEDSTOCK_RECIPE_BLOB_SHA,
        },
        "primarySourceFiles": files,
        "monteCarloAltitudeExplicitlyRejected": True,
        "mcElevationLoadedAsSeparate2DTopographyMechanism": True,
        "atmosphereAltitudeHandledBySeparateSourcePath": True,
        "siteAltitudeEquivalenceEstablished": False,
        "localSurfaceSensorEquivalenceEstablished": False,
        "scientificExecution": False,
        "scientificDatasetProduced": False,
        "syntaxCheckCount": 0,
        "solverExecutionCount": 0,
        "authorizationPermitted": False,
        "ordinal2ScientificDispatchPermitted": False,
        "boundary": (
            "exact-source audit only; source separation is evidence against "
            "assuming equivalence, not proof of a replacement geometry"
        ),
        "requiredNextProof": (
            "scientifically validate an executable elevated-site "
            "representation in the frozen runtime, then verify it with a "
            "separate one-photon probe before authorization"
        ),
    }
    (output_dir / "source-audit.json").write_text(
        dump(report),
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-archive", type=Path)
    parser.add_argument("--source-url", default=SOURCE_URL)
    parser.add_argument("--expected-sha256", default=SOURCE_SHA256)
    args = parser.parse_args()
    try:
        if args.source_archive is None:
            args.output_dir.mkdir(parents=True, exist_ok=True)
            archive_path = args.output_dir / "libRadtran-2.0.6.tar.gz"
            download(args.source_url, archive_path)
        else:
            archive_path = args.source_archive
        report = audit_archive(
            archive_path,
            args.output_dir,
            args.expected_sha256,
        )
        print(dump(report), end="")
        return 0
    except Exception as exc:
        print(
            dump(
                {
                    "schemaVersion": 1,
                    "stageId": STAGE_ID,
                    "status": "REFUSED",
                    "reason": str(exc),
                }
            ),
            file=sys.stderr,
            end="",
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
