#!/usr/bin/env python3
"""Fetch official Pickles spectra from a validated CDS raw-file base.

Transport-only helper for MYSTIC-STATE-0080. The helper first reads the
current official VizieR TSV metadata, then probes candidate CDS archive bases
with one known Pickles spectrum. A base is admitted only if the returned bytes
parse as the documented UVILIB wavelength/flux rows and cover the expected
1150--10620 Angstrom interval. All 131 spectra are then fetched from that same
base and written byte-for-byte; no science values are transformed here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

COUNT = 131
CANDIDATE_BASES = (
    "https://cdsarc.u-strasbg.fr/ftp/J/PASP/110/863",
    "http://cdsarc.u-strasbg.fr/ftp/J/PASP/110/863",
    "https://cdsarc.u-strasbg.fr/ftp/cats/J/PASP/110/863",
    "http://cdsarc.u-strasbg.fr/ftp/cats/J/PASP/110/863",
    "https://cdsarc.cds.unistra.fr/ftp/J/PASP/110/863",
    "https://cdsarc.cds.unistra.fr/ftp/cats/J/PASP/110/863",
)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def fetch(url: str, *, attempts: int = 2, timeout: int = 45) -> bytes:
    last: Exception | None = None
    for attempt in range(attempts):
        try:
            request = Request(url, headers={"User-Agent": "MYSTIC-STATE-0080-Public-Runner/1.0"})
            with urlopen(request, timeout=timeout) as response:
                payload = response.read()
            if not payload:
                raise RuntimeError("empty response")
            return payload
        except (HTTPError, URLError, TimeoutError, RuntimeError) as exc:
            last = exc
            if attempt + 1 < attempts:
                time.sleep(1 + attempt)
    raise RuntimeError(f"fetch failed: {type(last).__name__}: {last}")


def parse_tsv_file_map(path: Path) -> dict[int, str]:
    lines = path.read_text(encoding="ascii").splitlines()
    header: list[str] | None = None
    start = 0
    for index, raw in enumerate(lines):
        if raw.startswith("#") or "\t" not in raw:
            continue
        cols = [item.strip() for item in raw.split("\t")]
        if all(name in cols for name in ("num", "file")):
            header = cols
            start = index + 1
            break
    if header is None:
        raise RuntimeError("VizieR synphot TSV header not found")
    ni, fi = header.index("num"), header.index("file")
    rows: dict[int, str] = {}
    for raw in lines[start:]:
        if not raw.strip() or raw.startswith("#"):
            continue
        cols = [item.strip() for item in raw.split("\t")]
        if len(cols) != len(header):
            continue
        try:
            number = int(cols[ni])
        except ValueError:
            continue
        if 1 <= number <= COUNT:
            name = cols[fi].removesuffix(".dat")
            if not name or number in rows:
                raise RuntimeError(f"invalid/duplicate Pickles mapping at library number {number}")
            rows[number] = name
    expected = set(range(1, COUNT + 1))
    if set(rows) != expected or len(set(rows.values())) != COUNT:
        raise RuntimeError(f"expected exact Pickles library mapping 1..131; got {len(rows)} rows")
    return rows


def validate_raw_spectrum(payload: bytes, label: str) -> tuple[int, float, float]:
    try:
        lines = payload.decode("ascii").splitlines()
    except UnicodeDecodeError as exc:
        raise RuntimeError(f"{label}: response is not ASCII") from exc
    wavelength: list[float] = []
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            w = float(parts[0])
            f = float(parts[1])
        except ValueError:
            continue
        if not (1000.0 <= w <= 30000.0) or f < 0:
            continue
        if wavelength and w <= wavelength[-1]:
            raise RuntimeError(f"{label}: non-increasing wavelength rows")
        wavelength.append(w)
    if len(wavelength) < 1000:
        raise RuntimeError(f"{label}: only {len(wavelength)} numeric spectral rows")
    if abs(wavelength[0] - 1150.0) > 1e-9 or wavelength[-1] < 10620.0 - 1e-9:
        raise RuntimeError(f"{label}: unexpected coverage {wavelength[0]}..{wavelength[-1]} Angstrom")
    return len(wavelength), wavelength[0], wavelength[-1]


def choose_base(probe_name: str) -> tuple[str, dict]:
    failures: list[dict] = []
    for base in CANDIDATE_BASES:
        url = f"{base}/{probe_name}.dat"
        try:
            payload = fetch(url)
            rows, lo, hi = validate_raw_spectrum(payload, probe_name)
            return base, {"probe": probe_name, "rowCount": rows, "firstAngstrom": lo,
                          "lastAngstrom": hi, "sha256": sha256_bytes(payload)}
        except Exception as exc:
            failures.append({"base": base, "error": str(exc)[:300]})
    raise RuntimeError("no candidate CDS raw-file base returned a valid Pickles spectrum: " + json.dumps(failures))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--synphot-tsv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    mapping = parse_tsv_file_map(args.synphot_tsv)
    probe_name = mapping[1]
    base, probe = choose_base(probe_name)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    hashes: dict[str, str] = {}
    for number in range(1, COUNT + 1):
        name = mapping[number]
        payload = fetch(f"{base}/{name}.dat", attempts=3, timeout=60)
        validate_raw_spectrum(payload, name)
        path = args.output_dir / f"{name}.dat"
        path.write_bytes(payload)
        hashes[path.name] = sha256_bytes(payload)

    result = {
        "selectedBase": base,
        "probe": probe,
        "spectrumCount": len(hashes),
        "uniqueHashes": len(set(hashes.values())),
        "firstFile": f"{mapping[1]}.dat",
        "lastFile": f"{mapping[COUNT]}.dat",
    }
    if result["spectrumCount"] != COUNT:
        raise RuntimeError("spectrum count mismatch")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
