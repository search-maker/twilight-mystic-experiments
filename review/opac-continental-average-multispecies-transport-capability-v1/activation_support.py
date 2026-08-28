from __future__ import annotations

import hashlib
import json
import math
import tarfile
from pathlib import Path, PurePosixPath
from typing import Any

EXPECTED_ARCHIVE_SHA256 = "11daa1f1f4be0fd4ddf7e881ec2005498049674a1540d37b4b1e8f5e16052c7e"
EXPECTED_ARCHIVE_SIZE = 743_391_266
EXPECTED_ARCHIVE_MEMBERS = 28
EXPECTED_BASE_DATA_SHA256 = "ad30b49177e9c84e46497d69faf0c75e466996b0d0003f1de210289ae9f847d7"
EXPECTED_STAGED_DATA_SHA256 = "5d8bbf8e6b91ec3d405dee36f21a94afbb6e5ec6cd67da2dd5dd541738199d80"
EXPECTED_UVSPEC_SHA256 = "2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3"
EXPECTED_SPECIES_SHA256 = {
    "INSO": "fe10348cbe585315d6e1db382563fdc054204ad35846f371dc9d8abeead36407",
    "WASO": "b6df493b77019bf5e22456e8fb8858c5a7d502bcc02fe6fc697ebd4844f2d4f5",
    "SOOT": "44a0d2060101ca52c90ae64f005118dfba256b1f89a3049e1f758c55d634aa02",
    "SUSO": "ce0e1bba4219c60af0af14d66a280b0d3d25188276eed0951d31594b947cd472",
}
EXPECTED_ALIAS_PATHS = {s: f"aerosol/OPAC/optprop/{s}" for s in EXPECTED_SPECIES_SHA256}
V5_RUN_ID = 33186446347
V5_ARTIFACT_ID = 9691923455
V5_ARTIFACT_DIGEST = "sha256:fed6bb961088232e593159c4f50911758802e9209aed86e2a0eef4b403e4d9b7"
SOURCE_AUDIT_RUN_ID = 33187119926
SOURCE_AUDIT_ARTIFACT_ID = 9692162280
SOURCE_AUDIT_ARTIFACT_DIGEST = "sha256:cdcb0041a5197e31ff24520b3e653119d11c5d4a1c1b4f727e392ba7e719101e"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def extract_frozen_opac_archive(archive: Path, libradtran_root: Path) -> dict[str, Any]:
    raw = archive.read_bytes()
    if len(raw) != EXPECTED_ARCHIVE_SIZE:
        raise RuntimeError(f"OPAC archive size drift: {len(raw)}")
    if sha256_bytes(raw) != EXPECTED_ARCHIVE_SHA256:
        raise RuntimeError("OPAC archive SHA drift")
    with tarfile.open(archive, "r:gz") as tf:
        members = tf.getmembers()
        if len(members) != EXPECTED_ARCHIVE_MEMBERS:
            raise RuntimeError(f"OPAC member-count drift: {len(members)}")
        plan: list[tuple[tarfile.TarInfo, Path]] = []
        for member in members:
            rel = PurePosixPath(member.name)
            dest = libradtran_root.joinpath(*rel.parts)
            if not member.isfile() or rel.is_absolute() or ".." in rel.parts or not rel.parts or rel.parts[0] != "data" or dest.exists():
                raise RuntimeError(f"unsafe/colliding OPAC member: {member.name}")
            plan.append((member, dest))
        for member, dest in plan:
            src = tf.extractfile(member)
            if src is None:
                raise RuntimeError(f"cannot stream OPAC member: {member.name}")
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open("xb") as out:
                while True:
                    block = src.read(1024 * 1024)
                    if not block:
                        break
                    out.write(block)
    return {"schemaVersion": 1, "status": "FROZEN_OPAC_ARCHIVE_EXTRACTED", "archiveSha256": EXPECTED_ARCHIVE_SHA256, "archiveSize": EXPECTED_ARCHIVE_SIZE, "memberCount": EXPECTED_ARCHIVE_MEMBERS}


def validate_runtime_reports(base: dict[str, Any], pre: dict[str, Any], post: dict[str, Any], alias_manifest: dict[str, Any]) -> dict[str, Any]:
    if base.get("uvspecSha256") != EXPECTED_UVSPEC_SHA256:
        raise RuntimeError("uvspec SHA drift")
    if base.get("libRadtranDataTreeSha256") != EXPECTED_BASE_DATA_SHA256:
        raise RuntimeError("base data-tree SHA drift")
    if pre.get("libRadtranDataTreeSha256") != EXPECTED_STAGED_DATA_SHA256:
        raise RuntimeError("pre-alias staged tree SHA drift")
    if alias_manifest.get("status") != "FOUR_BYTE_IDENTICAL_NO_EXTENSION_OPAC_ALIASES_CREATED":
        raise RuntimeError("alias manifest status drift")
    if alias_manifest.get("species") != list(EXPECTED_SPECIES_SHA256):
        raise RuntimeError("alias species order drift")
    rows = alias_manifest.get("aliases") or []
    if len(rows) != 4 or alias_manifest.get("allByteIdentical") is not True:
        raise RuntimeError("four byte-identical aliases required")
    total_bytes = 0
    for row in rows:
        species = row.get("species")
        if species not in EXPECTED_SPECIES_SHA256:
            raise RuntimeError("unknown alias species")
        want = EXPECTED_SPECIES_SHA256[species]
        if row.get("sourceSha256") != want or row.get("aliasSha256") != want or row.get("byteIdentical") is not True:
            raise RuntimeError(f"alias provenance drift: {species}")
        if row.get("aliasRelativePath") != EXPECTED_ALIAS_PATHS[species]:
            raise RuntimeError(f"alias path drift: {species}")
        byte_count = int(row.get("byteCount") or 0)
        if byte_count <= 0:
            raise RuntimeError(f"invalid alias byte count: {species}")
        total_bytes += byte_count
    if post.get("libRadtranDataTreeSha256") == pre.get("libRadtranDataTreeSha256"):
        raise RuntimeError("post-alias data tree unexpectedly unchanged")
    if int(post.get("libRadtranDataFileCount") or 0) != int(pre.get("libRadtranDataFileCount") or 0) + 4:
        raise RuntimeError("post-alias data-file count drift")
    if int(post.get("libRadtranDataByteCount") or 0) != int(pre.get("libRadtranDataByteCount") or 0) + total_bytes:
        raise RuntimeError("post-alias data-byte count drift")
    return {
        "schemaVersion": 1,
        "status": "POST_FOUR_NO_EXTENSION_ALIASES_RUNTIME_PROVENANCE_VALIDATED",
        "preAliasDataTreeSha256": pre["libRadtranDataTreeSha256"],
        "postAliasDataTreeSha256": post["libRadtranDataTreeSha256"],
        "resolverAliases": alias_manifest,
    }


def parse_numeric_grid(path: Path) -> tuple[tuple[float, ...], tuple[tuple[float, ...], ...]]:
    if not path.is_file() or path.stat().st_size <= 0:
        raise RuntimeError(f"missing/empty numeric output: {path}")
    grid: list[float] = []
    rows: list[tuple[float, ...]] = []
    for line_no, raw in enumerate(path.read_text(errors="strict").splitlines(), 1):
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        try:
            vals = tuple(float(x) for x in s.split())
        except ValueError as exc:
            raise RuntimeError(f"non-numeric output row {path}:{line_no}") from exc
        if len(vals) < 2 or any(not math.isfinite(v) for v in vals):
            raise RuntimeError(f"invalid/non-finite output row {path}:{line_no}")
        grid.append(vals[0])
        rows.append(vals)
    if not rows:
        raise RuntimeError(f"no numeric rows in {path}")
    return tuple(grid), tuple(rows)


def validate_output_pair(low: Path, high: Path, label: str) -> dict[str, Any]:
    low_grid, low_rows = parse_numeric_grid(low)
    high_grid, high_rows = parse_numeric_grid(high)
    if low_grid != high_grid:
        raise RuntimeError(f"{label} LOW/HIGH wavelength grid mismatch")
    low_sha = hashlib.sha256(low.read_bytes()).hexdigest()
    high_sha = hashlib.sha256(high.read_bytes()).hexdigest()
    if low_sha == high_sha or low_rows == high_rows:
        raise RuntimeError(f"{label} LOW/HIGH outputs are identical")
    return {"label": label, "rowCount": len(low_rows), "grid": list(low_grid), "lowSha256": low_sha, "highSha256": high_sha, "outputsDiffer": True}


def _file_sha(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def freeze_capability_report(evidence: Path, run_id: int) -> dict[str, Any]:
    pre = json.loads((evidence / "pre-alias-runtime-report.json").read_text()) if (evidence / "pre-alias-runtime-report.json").is_file() else {}
    post = json.loads((evidence / "post-alias-runtime-report.json").read_text()) if (evidence / "post-alias-runtime-report.json").is_file() else {}
    manifest = json.loads((evidence / "input-manifest.json").read_text()) if (evidence / "input-manifest.json").is_file() else {}
    disort_validation = None
    mystic_validation = None
    try:
        disort_validation = validate_output_pair(evidence / "disort-low.out", evidence / "disort-high.out", "DISORT")
    except RuntimeError:
        pass
    try:
        mystic_validation = validate_output_pair(evidence / "mystic-low-mc.rad.spc", evidence / "mystic-high-mc.rad.spc", "MYSTIC_MC_RAD")
    except RuntimeError:
        pass
    disort_diff = bool(disort_validation and disort_validation.get("outputsDiffer"))
    mystic_diff = bool(mystic_validation and mystic_validation.get("outputsDiffer"))
    aliases = manifest.get("resolverAliases") or {}
    four_aliases = len(aliases.get("aliases") or []) == 4 and aliases.get("allByteIdentical") is True
    out = {
        "schemaVersion": 1,
        "stageId": "opac-continental-average-multispecies-transport-capability-v1",
        "status": "PASS_FOUR_CONTINENTAL_SPECIES_REACH_DISORT_AND_MYSTIC" if four_aliases and disort_diff and mystic_diff else "FAILED_BEFORE_REQUIRED_FOUR_SPECIES_COMPARISONS",
        "workflowRunId": int(run_id),
        "workflowRunAttempt": 1,
        "preAliasDataTreeSha256": pre.get("libRadtranDataTreeSha256"),
        "postAliasDataTreeSha256": post.get("libRadtranDataTreeSha256"),
        "resolverAliases": aliases,
        "continentalAverageSourceEvidence": manifest.get("continentalAverageSourceEvidence"),
        "disortValidation": disort_validation,
        "mysticValidation": mystic_validation,
        "disortOutputsDiffer": disort_diff,
        "mysticRadianceOutputsDiffer": mystic_diff,
        "mysticLowStdSha256": _file_sha(evidence / "mystic-low-mc.rad.std.spc"),
        "mysticHighStdSha256": _file_sha(evidence / "mystic-high-mc.rad.std.spc"),
        "scientificOrdinalAllocated": False,
        "taylorOrJerusalemUsed": False,
        "productionAuthorized": False,
        "levelBInferenceAuthorized": False,
        "scientificCompositionClaim": False,
        "humidityInterpretationAuthorized": False,
    }
    raw = json.dumps(out, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    out["contentSha256"] = hashlib.sha256(raw).hexdigest()
    (evidence / "capability-report.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    return out
