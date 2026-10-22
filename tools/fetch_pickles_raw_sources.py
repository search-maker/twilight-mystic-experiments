#!/usr/bin/env python3
"""Fetch the frozen STScI/MAST Pickles Atlas source for MYSTIC-STATE-0080.

The current VizieR synphot metadata is still required and must contain exactly
Pickles library numbers 1..131 with 131 distinct historical file mappings.
Under pre-residual protocol amendment 2, STScI Reference Atlases member
`pickles_uk_N.ascii` is bound to Pickles library number N. All 131 HTTPS byte
streams are validated for basic Pickles spectral structure and written unchanged
for the private reviewed builder, which records their SHA-256 hashes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

COUNT = 131
STSCI_BASE = "https://ssb.stsci.edu/cdbs/deliveries/etc/trds.24.3xxxx/grid/pickles/dat_uvk"


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def fetch(url: str, *, attempts: int = 3, timeout: int = 60) -> bytes:
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
            header = cols; start = index + 1; break
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
    if set(rows) != expected:
        raise RuntimeError(f"expected exact Pickles library numbers 1..131; got {len(rows)} rows")
    if len(set(rows.values())) != COUNT:
        raise RuntimeError("VizieR synphot metadata does not contain 131 distinct historical file mappings")
    return rows


def validate_spectrum(payload: bytes, label: str) -> dict:
    try:
        lines = payload.decode("ascii").splitlines()
    except UnicodeDecodeError as exc:
        raise RuntimeError(f"{label}: response is not ASCII") from exc
    wavelength: list[float] = []
    flux: list[float] = []
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            w = float(parts[0]); f = float(parts[1])
        except ValueError:
            continue
        if not (1000.0 <= w <= 30000.0):
            continue
        if not math.isfinite(f) or f < 0:
            raise RuntimeError(f"{label}: invalid flux at {w} Angstrom")
        if wavelength and w <= wavelength[-1]:
            raise RuntimeError(f"{label}: non-increasing wavelength rows")
        wavelength.append(w); flux.append(f)
    if len(wavelength) < 1000:
        raise RuntimeError(f"{label}: only {len(wavelength)} numeric spectral rows")
    if wavelength[0] > 1150.0 + 1e-9 or wavelength[-1] < 10620.0 - 1e-9:
        raise RuntimeError(f"{label}: unexpected coverage {wavelength[0]}..{wavelength[-1]} Angstrom")
    return {"rowCount": len(wavelength), "firstAngstrom": wavelength[0],
            "lastAngstrom": wavelength[-1], "sha256": sha256_bytes(payload)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--synphot-tsv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    mapping = parse_tsv_file_map(args.synphot_tsv)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    hashes: dict[str, str] = {}
    coverage = None
    for number in range(1, COUNT + 1):
        filename = f"pickles_uk_{number}.ascii"
        payload = fetch(f"{STSCI_BASE}/{filename}")
        info = validate_spectrum(payload, filename)
        if coverage is None:
            coverage = {k: info[k] for k in ("rowCount", "firstAngstrom", "lastAngstrom")}
        path = args.output_dir / filename
        path.write_bytes(payload)
        hashes[filename] = info["sha256"]

    if len(hashes) != COUNT:
        raise RuntimeError("STScI Pickles spectrum count mismatch")
    result = {
        "source": "STScI/MAST Reference Atlases Pickles Atlas",
        "sourceBase": STSCI_BASE,
        "binding": "pickles_uk_N.ascii -> VizieR Pickles library number N",
        "vizierLibraryCount": len(mapping),
        "spectrumCount": len(hashes),
        "coverageExample": coverage,
        "firstFile": "pickles_uk_1.ascii",
        "lastFile": "pickles_uk_131.ascii",
        "firstSha256": hashes["pickles_uk_1.ascii"],
        "lastSha256": hashes["pickles_uk_131.ascii"],
    }
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
