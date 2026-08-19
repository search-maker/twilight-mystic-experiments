#!/usr/bin/env python3
"""Extract the exact public Pickles source files from official CDS tar archives.

This is transport-only tooling for MYSTIC-STATE-0080. It does not transform
scientific data: selected tar members are copied byte-for-byte into runner temp.
The private application builder remains responsible for parsing, validation,
resampling, and source-byte hashing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import tarfile
from pathlib import Path, PurePosixPath

COUNT = 131


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def regular_members_by_basename(archive: tarfile.TarFile) -> dict[str, list[tarfile.TarInfo]]:
    out: dict[str, list[tarfile.TarInfo]] = {}
    for member in archive.getmembers():
        if not member.isfile():
            continue
        base = PurePosixPath(member.name).name
        out.setdefault(base, []).append(member)
    return out


def unique_member(index: dict[str, list[tarfile.TarInfo]], basename: str) -> tarfile.TarInfo:
    matches = index.get(basename, [])
    if len(matches) != 1:
        raise RuntimeError(f"expected exactly one tar member named {basename!r}; got {len(matches)}")
    return matches[0]


def member_bytes(archive: tarfile.TarFile, member: tarfile.TarInfo) -> bytes:
    stream = archive.extractfile(member)
    if stream is None:
        raise RuntimeError(f"unable to read tar member {member.name!r}")
    payload = stream.read()
    if not payload:
        raise RuntimeError(f"empty tar member {member.name!r}")
    return payload


def parse_synphot_file_bases(payload: bytes) -> dict[int, str]:
    try:
        lines = payload.decode("ascii").splitlines()
    except UnicodeDecodeError as exc:
        raise RuntimeError("synphot.dat is not ASCII") from exc
    rows: dict[int, str] = {}
    for raw in lines:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if len(raw) < 162:
            raise RuntimeError(f"short fixed-width synphot.dat row ({len(raw)} chars)")
        try:
            number = int(raw[0:3])
        except ValueError as exc:
            raise RuntimeError(f"invalid synphot.dat library number field: {raw[0:3]!r}") from exc
        if not 1 <= number <= COUNT or number in rows:
            raise RuntimeError(f"invalid/duplicate Pickles library number {number}")
        name = raw[156:162].strip()
        if not name:
            raise RuntimeError(f"Pickles library number {number} has empty source file field")
        rows[number] = name
    expected = set(range(1, COUNT + 1))
    if set(rows) != expected:
        raise RuntimeError(f"synphot.dat must contain exact library numbers 1..131; missing={sorted(expected-set(rows))}")
    if len(set(rows.values())) != COUNT:
        raise RuntimeError("synphot.dat does not map to 131 unique spectrum filenames")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pickles-tar", type=Path, required=True)
    parser.add_argument("--libmags-tar", type=Path, required=True)
    parser.add_argument("--pickles-dir", type=Path, required=True)
    parser.add_argument("--table6-output", type=Path, required=True)
    args = parser.parse_args()

    args.pickles_dir.mkdir(parents=True, exist_ok=True)
    args.table6_output.parent.mkdir(parents=True, exist_ok=True)

    with tarfile.open(args.pickles_tar, mode="r:gz") as archive:
        index = regular_members_by_basename(archive)
        synphot_member = unique_member(index, "synphot.dat")
        synphot = member_bytes(archive, synphot_member)
        rows = parse_synphot_file_bases(synphot)
        (args.pickles_dir / "synphot.dat").write_bytes(synphot)
        copied = []
        for number in range(1, COUNT + 1):
            basename = f"{rows[number]}.dat"
            member = unique_member(index, basename)
            payload = member_bytes(archive, member)
            (args.pickles_dir / basename).write_bytes(payload)
            copied.append(basename)

    with tarfile.open(args.libmags_tar, mode="r:gz") as archive:
        index = regular_members_by_basename(archive)
        table6_member = unique_member(index, "table6.dat")
        args.table6_output.write_bytes(member_bytes(archive, table6_member))

    result = {
        "picklesArchiveSha256": sha256(args.pickles_tar),
        "libmagsArchiveSha256": sha256(args.libmags_tar),
        "synphotSha256": sha256(args.pickles_dir / "synphot.dat"),
        "table6Sha256": sha256(args.table6_output),
        "spectrumCount": len(copied),
        "firstSpectrum": copied[0],
        "lastSpectrum": copied[-1],
    }
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
