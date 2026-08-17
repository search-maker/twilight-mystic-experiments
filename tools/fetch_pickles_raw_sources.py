#!/usr/bin/env python3
"""Fetch and authenticate official Pickles spectra for MYSTIC-STATE-0080.

The current VizieR metadata service is used for the reviewed Pickles library
mapping. The historical CDS raw-file archive is under /pub/cats. Its legacy
HTTPS service may present an obsolete/self-signed TLS certificate, so those
public bytes are never trusted on transport alone: every downloaded spectrum
is independently checked against STScI's HTTPS Pickles atlas before it is
admitted. The CDS bytes, not the mirror bytes, are written for the private
reviewed builder/provenance path. No science values are transformed here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import ssl
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

COUNT = 131
LEGACY_CDS_BASES = (
    "https://cdsarc.u-strasbg.fr/pub/cats/J/PASP/110/863",
    "http://cdsarc.u-strasbg.fr/pub/cats/J/PASP/110/863",
    "https://cdsarc.u-strasbg.fr/ftp/J/PASP/110/863",
    "https://cdsarc.u-strasbg.fr/ftp/cats/J/PASP/110/863",
)
STSCI_BASE = "https://ssb.stsci.edu/cdbs/deliveries/etc/trds.24.3xxxx/grid/pickles/dat_uvk"


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def fetch(url: str, *, attempts: int = 2, timeout: int = 45, legacy_cds: bool = False) -> bytes:
    last: Exception | None = None
    context = ssl._create_unverified_context() if legacy_cds else ssl.create_default_context()
    for attempt in range(attempts):
        try:
            request = Request(url, headers={"User-Agent": "MYSTIC-STATE-0080-Public-Runner/1.0"})
            with urlopen(request, timeout=timeout, context=context) as response:
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


def numeric_spectrum(payload: bytes, label: str) -> tuple[list[float], list[float]]:
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
            w = float(parts[0])
            f = float(parts[1])
        except ValueError:
            continue
        if not (1000.0 <= w <= 30000.0) or not math.isfinite(f) or f < 0:
            continue
        if wavelength and w <= wavelength[-1]:
            raise RuntimeError(f"{label}: non-increasing wavelength rows")
        wavelength.append(w)
        flux.append(f)
    if len(wavelength) < 1000:
        raise RuntimeError(f"{label}: only {len(wavelength)} numeric spectral rows")
    if abs(wavelength[0] - 1150.0) > 1e-9 or wavelength[-1] < 10620.0 - 1e-9:
        raise RuntimeError(f"{label}: unexpected coverage {wavelength[0]}..{wavelength[-1]} Angstrom")
    return wavelength, flux


def mirror_equivalence(cds_payload: bytes, stsci_payload: bytes, label: str) -> dict:
    cw, cf = numeric_spectrum(cds_payload, f"CDS {label}")
    sw, sf = numeric_spectrum(stsci_payload, f"STScI {label}")
    if cw != sw:
        raise RuntimeError(f"{label}: CDS/STScI wavelength grids differ ({len(cw)} vs {len(sw)})")

    denom = sum(value * value for value in cf)
    if not denom:
        raise RuntimeError(f"{label}: zero CDS spectrum")
    scale = sum(a * b for a, b in zip(cf, sf)) / denom
    if not math.isfinite(scale) or scale <= 0:
        raise RuntimeError(f"{label}: invalid CDS/STScI scale {scale}")
    peak = max(max(sf), abs(scale) * max(cf))
    if not peak > 0:
        raise RuntimeError(f"{label}: zero comparison peak")
    max_abs_norm = max(abs(b - scale * a) for a, b in zip(cf, sf)) / peak
    rms_norm = math.sqrt(sum((b - scale * a) ** 2 for a, b in zip(cf, sf)) / len(cf)) / peak
    if max_abs_norm > 2e-5:
        raise RuntimeError(
            f"{label}: CDS/STScI spectral shape mismatch maxNorm={max_abs_norm:.9g} rmsNorm={rms_norm:.9g}"
        )
    return {
        "rowCount": len(cw),
        "firstAngstrom": cw[0],
        "lastAngstrom": cw[-1],
        "scale": scale,
        "maxNormalizedDifference": max_abs_norm,
        "rmsNormalizedDifference": rms_norm,
        "cdsSha256": sha256_bytes(cds_payload),
        "stsciSha256": sha256_bytes(stsci_payload),
    }


def stsci_payload(number: int) -> bytes:
    return fetch(f"{STSCI_BASE}/pickles_uk_{number}.ascii", attempts=3, timeout=60)


def choose_legacy_base(probe_number: int, probe_name: str) -> tuple[str, dict]:
    mirror = stsci_payload(probe_number)
    failures: list[dict] = []
    for base in LEGACY_CDS_BASES:
        try:
            payload = fetch(f"{base}/{probe_name}.dat", legacy_cds=base.startswith("https://cdsarc.u-strasbg.fr"))
            comparison = mirror_equivalence(payload, mirror, probe_name)
            comparison["mirror"] = f"STScI pickles_uk_{probe_number}.ascii"
            comparison["legacyTlsCertificateVerified"] = not base.startswith("https://cdsarc.u-strasbg.fr")
            comparison["authenticatedByIndependentMirror"] = True
            return base, comparison
        except Exception as exc:
            failures.append({"base": base, "error": str(exc)[:500]})
    raise RuntimeError("no legacy CDS base passed STScI mirror authentication: " + json.dumps(failures))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--synphot-tsv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    mapping = parse_tsv_file_map(args.synphot_tsv)
    probe_number = 1
    probe_name = mapping[probe_number]
    base, probe = choose_legacy_base(probe_number, probe_name)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    max_norm = 0.0
    max_rms = 0.0
    hashes: dict[str, str] = {}
    for number in range(1, COUNT + 1):
        name = mapping[number]
        cds_payload = fetch(
            f"{base}/{name}.dat", attempts=3, timeout=60,
            legacy_cds=base.startswith("https://cdsarc.u-strasbg.fr")
        )
        mirror = stsci_payload(number)
        comparison = mirror_equivalence(cds_payload, mirror, name)
        max_norm = max(max_norm, comparison["maxNormalizedDifference"])
        max_rms = max(max_rms, comparison["rmsNormalizedDifference"])
        path = args.output_dir / f"{name}.dat"
        path.write_bytes(cds_payload)
        hashes[path.name] = sha256_bytes(cds_payload)

    result = {
        "selectedLegacyCdsBase": base,
        "legacyTlsCertificateVerified": not base.startswith("https://cdsarc.u-strasbg.fr"),
        "authenticatedByIndependentMirror": "STScI HTTPS Pickles atlas, all 131 spectra",
        "probe": probe,
        "spectrumCount": len(hashes),
        "uniqueCdsHashes": len(set(hashes.values())),
        "maxNormalizedMirrorDifference": max_norm,
        "maxRmsNormalizedMirrorDifference": max_rms,
        "firstFile": f"{mapping[1]}.dat",
        "lastFile": f"{mapping[COUNT]}.dat",
    }
    if result["spectrumCount"] != COUNT:
        raise RuntimeError("spectrum count mismatch")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
