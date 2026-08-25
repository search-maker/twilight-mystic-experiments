#!/usr/bin/env python3
"""Reconstruct the exact frozen Pickles SED bundle from authoritative source bytes.

This is a zero-solver provenance utility. It reproduces the accepted 0081
Pickles bundle schema/serialization and is judged solely by the already-frozen
bundle SHA-256. It never invokes libRadtran and never reads scientific residuals.
"""
from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import math
from pathlib import Path
from typing import Iterable

COUNT = 131
GRID = list(range(380, 781))
EXPECTED_BUNDLE_SHA256 = "85cbf41c86309b9d54d4765516167165f2d8736bcda8994337ef25d775ea11cb"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalized_type(value: str) -> str:
    return "".join(c for c in value.upper() if c.isalnum() or c == ".")


def abundance(value: str) -> str:
    text = value.strip().lower()
    return "metal-weak" if text.startswith("w") else "metal-rich" if text.startswith("r") else "normal"


def data_lines(path: Path):
    for raw in path.read_text(encoding="ascii").splitlines():
        if raw.strip() and not raw.lstrip().startswith("#"):
            yield raw


def vizier_tsv_records(path: Path, required: tuple[str, ...]) -> list[dict[str, str]] | None:
    lines = path.read_text(encoding="ascii").splitlines()
    header = None
    start = 0
    for index, raw in enumerate(lines):
        if not raw.strip() or raw.lstrip().startswith("#") or "\t" not in raw:
            continue
        cols = [item.strip() for item in raw.split("\t")]
        if all(name in cols for name in required):
            header = cols
            start = index + 1
            break
    if header is None:
        return None
    records: list[dict[str, str]] = []
    for raw in lines[start:]:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        values = [item.strip() for item in raw.split("\t")]
        if len(values) == len(header):
            records.append(dict(zip(header, values)))
    return records


def parse_synphot(path: Path) -> dict[int, dict]:
    tsv = vizier_tsv_records(path, ("num", "SpType", "LogTe", "file"))
    rows: dict[int, dict] = {}
    if tsv is not None:
        for record in tsv:
            try:
                n = int(record["num"])
                log_te = float(record["LogTe"])
            except (ValueError, TypeError):
                continue
            if not 1 <= n <= COUNT or n in rows:
                raise ValueError(f"invalid/duplicate Pickles library number: {n}")
            spectral_type = record["SpType"].strip().strip("'")
            file_base = record["file"].strip().removesuffix(".dat")
            if not spectral_type or not file_base:
                raise ValueError(f"Pickles row {n} lacks spectral type or source file")
            rows[n] = {
                "libraryNumber": n,
                "spectralType": spectral_type,
                "log10EffectiveTemperatureK": log_te,
                "sourceFileBase": file_base,
            }
    else:
        for raw in data_lines(path):
            if len(raw) < 162:
                raise ValueError(f"short synphot.dat row ({len(raw)} chars): {raw!r}")
            n = int(raw[0:3])
            if not 1 <= n <= COUNT or n in rows:
                raise ValueError(f"invalid/duplicate Pickles library number: {n}")
            spectral_type = raw[21:27].strip()
            log_te = float(raw[28:33])
            file_base = raw[156:162].strip()
            if not spectral_type or not file_base:
                raise ValueError(f"Pickles row {n} lacks spectral type or source file")
            rows[n] = {
                "libraryNumber": n,
                "spectralType": spectral_type,
                "log10EffectiveTemperatureK": log_te,
                "sourceFileBase": file_base,
            }
    expected = set(range(1, COUNT + 1))
    if set(rows) != expected:
        raise ValueError(f"synphot source must contain 1..131; missing={sorted(expected-set(rows))}")
    return rows


def parse_table6(path: Path) -> dict[int, dict]:
    tsv = vizier_tsv_records(path, ("Lib", "Type", "Bmmag", "Vcmag"))
    rows: dict[int, dict] = {}
    source_rows = []
    if tsv is not None:
        for record in tsv:
            try:
                source_rows.append((int(record["Lib"]), record["Type"].strip().strip("'"),
                                    float(record["Bmmag"]), float(record["Vcmag"])))
            except (ValueError, TypeError):
                continue
    else:
        for raw in data_lines(path):
            parts = raw.split()
            if len(parts) < 6:
                raise ValueError(f"short table6.dat row: {raw!r}")
            source_rows.append((int(parts[0]), parts[1].strip("'"), float(parts[4]), float(parts[5])))
    for n, spectral_type, b_mag, v_mag in source_rows:
        if not 1 <= n <= COUNT:
            continue
        if n in rows:
            raise ValueError(f"duplicate table6 Pickles library number: {n}")
        if abs(v_mag) > 5e-4:
            raise ValueError(f"table6 Lib={n} must be normalized to Vcmag=0; got {v_mag}")
        rows[n] = {
            "libraryNumber": n,
            "spectralType": spectral_type,
            "bMinusVLandoltBmVc": b_mag - v_mag,
        }
    expected = set(range(1, COUNT + 1))
    if set(rows) != expected:
        raise ValueError(f"table6 source must contain Pickles Lib 1..131; missing={sorted(expected-set(rows))}")
    return rows


def read_spectrum(path: Path) -> tuple[list[float], list[float]]:
    wavelength: list[float] = []
    flux: list[float] = []
    for raw in path.read_text(encoding="ascii").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        parts = raw.split()
        if len(parts) < 2:
            continue
        try:
            wavelength_angstrom = float(parts[0])
            f = float(parts[1])
        except ValueError:
            continue
        if not 1000.0 <= wavelength_angstrom <= 30000.0:
            continue
        w = wavelength_angstrom / 10.0
        if not math.isfinite(w) or not math.isfinite(f) or f < 0:
            raise ValueError(f"invalid spectrum sample in {path.name}: {w}, {f}")
        if wavelength and w <= wavelength[-1]:
            raise ValueError(f"wavelengths not strictly increasing in {path.name}: {wavelength[-1]} then {w}")
        wavelength.append(w)
        flux.append(f)
    if len(wavelength) < 1000:
        raise ValueError(f"spectrum {path.name} has only {len(wavelength)} numeric science samples")
    if wavelength[0] > 115.0 + 1e-9 or wavelength[-1] < 1062.0 - 1e-9:
        raise ValueError(f"unexpected Pickles coverage in {path.name}: {wavelength[0]}..{wavelength[-1]} nm")
    return wavelength, flux


def resample(x: list[float], y: list[float], targets: Iterable[float]) -> list[float]:
    targets = list(targets)
    if targets[0] < x[0] or targets[-1] > x[-1]:
        raise ValueError("target grid outside source spectrum coverage")
    out = []
    for t in targets:
        i = bisect.bisect_left(x, t)
        if i < len(x) and abs(x[i] - t) <= 1e-12:
            out.append(y[i])
            continue
        if i == 0 or i == len(x):
            raise ValueError(f"cannot bracket wavelength {t}")
        out.append(y[i-1] + (t-x[i-1]) / (x[i]-x[i-1]) * (y[i]-y[i-1]))
    return out


def normalize_relative_flux(values: list[float]) -> list[float]:
    if not values or any(not math.isfinite(v) or v < 0 for v in values):
        raise ValueError("resampled Pickles flux must be finite and non-negative")
    scale = max(values)
    if not scale > 0:
        raise ValueError("resampled Pickles flux has no positive spectral sample")
    relative = [round(v / scale, 12) for v in values]
    if max(relative) != 1.0 or not any(v > 0 for v in relative):
        raise ValueError("relative Pickles normalization failed")
    return relative


def source_path(pickles_dir: Path, n: int, file_base: str) -> tuple[Path, str]:
    cds = pickles_dir / f"{file_base}.dat"
    stsci = pickles_dir / f"pickles_uk_{n}.ascii"
    if cds.is_file() and stsci.is_file():
        raise ValueError(f"ambiguous Pickles source for library number {n}: both CDS and STScI files present")
    if cds.is_file():
        return cds, "CDS-original-flat-file"
    if stsci.is_file():
        return stsci, "STScI-MAST-Pickles-Atlas"
    raise FileNotFoundError(
        f"missing Pickles spectrum for library number {n}: expected {cds.name} or {stsci.name}"
    )


def build_bundle(pickles_dir: Path, table6_path: Path) -> dict:
    synphot = pickles_dir / "synphot.dat"
    if not synphot.is_file() or not table6_path.is_file():
        raise FileNotFoundError("authoritative Pickles synphot/table6 input is missing")
    p_rows, c_rows = parse_synphot(synphot), parse_table6(table6_path)
    templates, source_hashes, source_kinds = [], {}, set()
    label_mismatches = []
    for n in range(1, COUNT + 1):
        p, c = p_rows[n], c_rows[n]
        label_agreement = normalized_type(p["spectralType"]) == normalized_type(c["spectralType"])
        if not label_agreement:
            label_mismatches.append({
                "libraryNumber": n,
                "pickles1998SpectralType": p["spectralType"],
                "picklesDepagne2010SpectralType": c["spectralType"],
            })
        path, source_kind = source_path(pickles_dir, n, p["sourceFileBase"])
        source_kinds.add(source_kind)
        x, y = read_spectrum(path)
        if x[0] > 380 or x[-1] < 780:
            raise ValueError(f"{path.name} does not cover 380-780 nm")
        digest = sha256_file(path)
        source_hashes[path.name] = digest
        relative_flux = normalize_relative_flux(resample(x, y, GRID))
        templates.append({
            "templateId": f"pickles98:{p['sourceFileBase']}",
            "libraryNumber": n,
            "spectralType": p["spectralType"],
            "colorCalibrationSpectralType": c["spectralType"],
            "spectralTypeLabelAgreement": label_agreement,
            "abundance": abundance(p["spectralType"]),
            "log10EffectiveTemperatureK": p["log10EffectiveTemperatureK"],
            "effectiveTemperatureK": round(10 ** p["log10EffectiveTemperatureK"]),
            "bMinusVLandoltBmVc": round(c["bMinusVLandoltBmVc"], 6),
            "sourceFile": path.name,
            "sourceKind": source_kind,
            "sourceSha256": digest,
            "fluxRelative": relative_flux,
        })
    if len(source_kinds) != 1:
        raise ValueError(f"mixed Pickles spectrum source kinds are not allowed: {sorted(source_kinds)}")
    source_kind = next(iter(source_kinds))
    return {
        "schemaVersion": 1,
        "quantity": "relative-stellar-f-lambda-shape",
        "wavelengthNm": GRID,
        "wavelengthGrid": {
            "startNm": 380,
            "endNm": 780,
            "stepNm": 1,
            "resampling": "linear from Pickles atlas samples; no extra spectral information claimed",
            "normalization": "divide each template by its maximum resampled F_lambda over 380-780 nm before 12-decimal quantization; positive scale cancels in Johnson-V transmission ratio",
        },
        "colorCoordinate": {
            "field": "bMinusVLandoltBmVc",
            "system": "Pickles+Depagne 2010 Landolt Bm-Vc, Vega system, CALSPEC-calibrated zero points",
            "use": "template-shape selection only; not a catalogue magnitude correction",
        },
        "provenance": {
            "metadataJoin": {
                "key": "Pickles library number",
                "requiredLibraryNumbers": "1..131 exact",
                "spectralTypeLabelMismatchCount": len(label_mismatches),
                "spectralTypeLabelMismatches": label_mismatches,
            },
            "pickles1998": {
                "catalogId": "J/PASP/110/863",
                "synphotSha256": sha256_file(synphot),
                "spectrumCount": COUNT,
                "spectrumSourceKind": source_kind,
                "sourceSpectrumSha256": source_hashes,
                "stsciAtlasBase": "https://ssb.stsci.edu/cdbs/deliveries/etc/trds.24.3xxxx/grid/pickles/dat_uvk/" if source_kind == "STScI-MAST-Pickles-Atlas" else None,
            },
            "picklesDepagne2010": {
                "catalogId": "VI/135",
                "table": "table6",
                "table6Sha256": sha256_file(table6_path),
            },
            "builder": "scientific-tools/visibility-v3/build_pickles_sed_bundle.py",
            "sourceTransportAmendment": "STELLAR_TRANSPORT_VALIDATION_PROTOCOL_V1_AMENDMENT_2_SOURCE_TRANSPORT.md",
        },
        "templates": templates,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pickles-dir", type=Path, required=True)
    parser.add_argument("--libmags-table6", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    bundle = build_bundle(args.pickles_dir, args.libmags_table6)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    actual = sha256_file(args.output)
    print(json.dumps({
        "output": str(args.output),
        "templateCount": len(bundle["templates"]),
        "bundleSha256": actual,
        "expectedBundleSha256": EXPECTED_BUNDLE_SHA256,
        "exactHistoricalHashMatch": actual == EXPECTED_BUNDLE_SHA256,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
