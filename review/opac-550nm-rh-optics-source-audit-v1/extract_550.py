from __future__ import annotations

import argparse
import hashlib
import json
import math
import tarfile
from pathlib import Path

EXPECTED_ARCHIVE_SHA256 = "11daa1f1f4be0fd4ddf7e881ec2005498049674a1540d37b4b1e8f5e16052c7e"
EXPECTED_ARCHIVE_SIZE = 743_391_266
EXPECTED_ARCHIVE_MEMBERS = 28
EXPECTED_AFGL_SHA256 = "dab26290ed81c762ed0c607e5dc2d53393c1462a0c3a528bc5e3f5935191cfb5"
ASSETS = {
    "INSO": ("data/aerosol/OPAC/optprop/inso.mie.cdf", "fe10348cbe585315d6e1db382563fdc054204ad35846f371dc9d8abeead36407", [0.0]),
    "WASO": ("data/aerosol/OPAC/optprop/waso.mie.cdf", "b6df493b77019bf5e22456e8fb8858c5a7d502bcc02fe6fc697ebd4844f2d4f5", [0.0, 50.0, 70.0, 80.0, 90.0, 95.0, 98.0, 99.0]),
    "SOOT": ("data/aerosol/OPAC/optprop/soot.mie.cdf", "44a0d2060101ca52c90ae64f005118dfba256b1f89a3049e1f758c55d634aa02", [0.0]),
    "SUSO": ("data/aerosol/OPAC/optprop/suso.mie.cdf", "ce0e1bba4219c60af0af14d66a280b0d3d25188276eed0951d31594b947cd472", [0.0, 50.0, 70.0, 80.0, 90.0, 95.0, 98.0, 99.0]),
}


class AuditError(RuntimeError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def extract_assets(archive: Path, outdir: Path) -> dict[str, dict]:
    if archive.stat().st_size != EXPECTED_ARCHIVE_SIZE:
        raise AuditError(f"archive size drift: {archive.stat().st_size}")
    if sha256_file(archive) != EXPECTED_ARCHIVE_SHA256:
        raise AuditError("archive SHA drift")
    wanted = {rel: (species, digest) for species, (rel, digest, _hum) in ASSETS.items()}
    found: dict[str, dict] = {}
    with tarfile.open(archive, "r:gz") as tf:
        members = tf.getmembers()
        if len(members) != EXPECTED_ARCHIVE_MEMBERS:
            raise AuditError(f"archive member-count drift: {len(members)}")
        for member in members:
            if member.name not in wanted:
                continue
            if not member.isfile():
                raise AuditError(f"wanted member is not a regular file: {member.name}")
            src = tf.extractfile(member)
            if src is None:
                raise AuditError(f"cannot stream member: {member.name}")
            raw = src.read()
            species, expected = wanted[member.name]
            digest = sha256_bytes(raw)
            if digest != expected:
                raise AuditError(f"asset SHA drift: {species}: {digest}")
            dest = outdir / f"{species}.cdf"
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(raw)
            found[species] = {
                "archiveMember": member.name,
                "sha256": digest,
                "byteCount": len(raw),
            }
    if set(found) != set(ASSETS):
        raise AuditError(f"missing assets: {sorted(set(ASSETS) - set(found))}")
    return found


def _attrs(var) -> dict[str, object]:
    out = {}
    for name in var.ncattrs():
        value = var.getncattr(name)
        if isinstance(value, bytes):
            value = value.decode("utf-8", "replace")
        elif hasattr(value, "tolist"):
            value = value.tolist()
        out[name] = value
    return out


def _array(var):
    import numpy as np
    arr = np.ma.asarray(var[:], dtype=float)
    if np.ma.isMaskedArray(arr):
        arr = arr.filled(np.nan)
    return np.asarray(arr, dtype=float)


def audit_species(path: Path, species: str, expected_humidity: list[float]) -> dict:
    import numpy as np
    from netCDF4 import Dataset

    with Dataset(path, "r") as ds:
        required = {"wavelen", "hum", "ext", "ssa", "rho"}
        missing = sorted(required - set(ds.variables))
        if missing:
            raise AuditError(f"{species}: missing variables {missing}")
        wav = ds.variables["wavelen"]
        hum = ds.variables["hum"]
        ext = ds.variables["ext"]
        ssa = ds.variables["ssa"]
        rho = ds.variables["rho"]

        if list(wav.dimensions) != ["nlam"] or list(hum.dimensions) != ["nhum"]:
            raise AuditError(f"{species}: coordinate dimension drift")
        for name, var in (("ext", ext), ("ssa", ssa), ("rho", rho)):
            if list(var.dimensions) != ["nlam", "nhum"]:
                raise AuditError(f"{species}: {name} dimension drift: {var.dimensions}")

        attrs = {name: _attrs(var) for name, var in (("wavelen", wav), ("hum", hum), ("ext", ext), ("ssa", ssa), ("rho", rho))}
        expected_attrs = {
            "wavelen": ("wavelength", "micrometer"),
            "hum": ("relative humidity", "per cent"),
            "ext": ("extinction coefficient", "km^-1 / (g/m^3)"),
            "ssa": ("single scattering albedo", "-"),
            "rho": ("density of medium", "g/cm^3"),
        }
        for name, (long_name, units) in expected_attrs.items():
            if attrs[name].get("long_name") != long_name or attrs[name].get("units") != units:
                raise AuditError(f"{species}: {name} metadata drift: {attrs[name]}")

        wav_values = _array(wav).reshape(-1)
        hum_values = _array(hum).reshape(-1)
        if wav_values.size != 61:
            raise AuditError(f"{species}: wavelength count drift: {wav_values.size}")
        if hum_values.tolist() != expected_humidity:
            raise AuditError(f"{species}: humidity nodes drift: {hum_values.tolist()}")
        matches = np.flatnonzero(np.isclose(wav_values, 0.55, rtol=0.0, atol=1e-12))
        if matches.size != 1:
            raise AuditError(f"{species}: expected exactly one 0.55 micrometer coordinate, got {matches.tolist()}")
        wi = int(matches[0])
        if wi != 6 or float(wav_values[wi]) != 0.55:
            raise AuditError(f"{species}: 550 nm coordinate/index drift: index={wi} value={wav_values[wi]}")

        ext_values = _array(ext)
        ssa_values = _array(ssa)
        rho_values = _array(rho)
        expected_shape = (61, len(expected_humidity))
        for name, arr in (("ext", ext_values), ("ssa", ssa_values), ("rho", rho_values)):
            if arr.shape != expected_shape:
                raise AuditError(f"{species}: {name} shape drift: {arr.shape}")
        ext550 = np.asarray(ext_values[wi, :], dtype=float).reshape(-1)
        ssa550 = np.asarray(ssa_values[wi, :], dtype=float).reshape(-1)
        rho550 = np.asarray(rho_values[wi, :], dtype=float).reshape(-1)
        if not np.all(np.isfinite(ext550)) or not np.all(ext550 > 0):
            raise AuditError(f"{species}: nonpositive/nonfinite 550-nm extinction coefficients")
        if not np.all(np.isfinite(ssa550)) or not np.all((ssa550 >= 0) & (ssa550 <= 1)):
            raise AuditError(f"{species}: invalid 550-nm SSA")
        if not np.all(np.isfinite(rho550)) or not np.all(rho550 > 0):
            raise AuditError(f"{species}: invalid 550-nm density values")

        rows = []
        for i, rh in enumerate(hum_values):
            rows.append({
                "humidityPercent": float(rh),
                "extinctionCoefficient": float(ext550[i]),
                "singleScatteringAlbedo": float(ssa550[i]),
                "mediumDensity_g_cm3": float(rho550[i]),
            })
        return {
            "dataModel": ds.data_model,
            "wavelengthVariable": "wavelen",
            "wavelengthUnits": "micrometer",
            "wavelengthIndex": wi,
            "wavelengthMicrometer": float(wav_values[wi]),
            "wavelengthNm": 550.0,
            "humidityVariable": "hum",
            "humidityUnits": "per cent",
            "extinctionVariable": "ext",
            "extinctionUnits": "km^-1 / (g/m^3)",
            "ssaVariable": "ssa",
            "rhoVariable": "rho",
            "rows": rows,
        }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive", type=Path, required=True)
    ap.add_argument("--afgl", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    if sha256_file(args.afgl) != EXPECTED_AFGL_SHA256:
        raise AuditError("AFGL-US SHA drift")
    args.output.mkdir(parents=True, exist_ok=False)
    assets_dir = args.output / "assets"
    assets = extract_assets(args.archive, assets_dir)
    at550 = {
        species: audit_species(assets_dir / f"{species}.cdf", species, expected_hum)
        for species, (_rel, _sha, expected_hum) in ASSETS.items()
    }
    report = {
        "schemaVersion": 1,
        "stageId": "opac-550nm-rh-optics-exact-values-audit-v1",
        "status": "PASS_EXACT_550NM_RH_OPTICAL_VALUES_FROZEN",
        "archive": {
            "sha256": EXPECTED_ARCHIVE_SHA256,
            "byteCount": EXPECTED_ARCHIVE_SIZE,
            "memberCount": EXPECTED_ARCHIVE_MEMBERS,
        },
        "afglUsSha256": EXPECTED_AFGL_SHA256,
        "assets": assets,
        "at550nm": at550,
        "uvspecInvoked": False,
        "syntaxCheckExecuted": False,
        "scientificSolverExecuted": False,
        "scientificOrdinalAllocated": False,
        "taylorOrJerusalemUsed": False,
        "productionAuthorized": False,
        "interpretationBoundary": "Exact source values only. No runtime RH selection, interpolation, mass-scaling renderer, scientific vertical profile, or effect-size inference is authorized here.",
    }
    canonical = json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    report["contentSha256"] = hashlib.sha256(canonical).hexdigest()
    out = args.output / "550nm-exact-values.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "contentSha256": report["contentSha256"], "at550nm": at550}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
