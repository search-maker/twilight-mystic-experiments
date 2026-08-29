from __future__ import annotations

import argparse
import hashlib
import json
import math
import tarfile
from pathlib import Path, PurePosixPath
from typing import Any

STAGE_ID = "opac-afgl-rh-selection-null-audit-v1"
EXPECTED_ARCHIVE_SHA256 = "11daa1f1f4be0fd4ddf7e881ec2005498049674a1540d37b4b1e8f5e16052c7e"
EXPECTED_ARCHIVE_SIZE = 743_391_266
EXPECTED_ARCHIVE_MEMBERS = 28
EXPECTED_AFGL_SHA256 = "dab26290ed81c762ed0c607e5dc2d53393c1462a0c3a528bc5e3f5935191cfb5"
EXPECTED_CONTINENTAL_SHA256 = "fc39fda0f8ada2d0a0a872b8b62d684cfccd74f7b0655b5af2dcdec51115e469"
EXPECTED_ASSET_SHA256 = {
    "INSO": "fe10348cbe585315d6e1db382563fdc054204ad35846f371dc9d8abeead36407",
    "WASO": "b6df493b77019bf5e22456e8fb8858c5a7d502bcc02fe6fc697ebd4844f2d4f5",
    "SOOT": "44a0d2060101ca52c90ae64f005118dfba256b1f89a3049e1f758c55d634aa02",
    "SUSO": "ce0e1bba4219c60af0af14d66a280b0d3d25188276eed0951d31594b947cd472",
}
OPAC_RH_NODES = (0.0, 50.0, 70.0, 80.0, 90.0, 95.0, 98.0, 99.0)


class AuditError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def extract_frozen_archive(archive: Path, libradtran_root: Path) -> dict[str, Any]:
    if archive.stat().st_size != EXPECTED_ARCHIVE_SIZE:
        raise AuditError(f"archive size drift: {archive.stat().st_size}")
    if sha256_file(archive) != EXPECTED_ARCHIVE_SHA256:
        raise AuditError("archive SHA drift")
    with tarfile.open(archive, "r:gz") as tf:
        members = tf.getmembers()
        if len(members) != EXPECTED_ARCHIVE_MEMBERS:
            raise AuditError(f"archive member-count drift: {len(members)}")
        plan: list[tuple[tarfile.TarInfo, Path]] = []
        for member in members:
            rel = PurePosixPath(member.name)
            dest = libradtran_root.joinpath(*rel.parts)
            if rel.is_absolute() or ".." in rel.parts or not rel.parts or rel.parts[0] != "data":
                raise AuditError(f"unsafe archive member: {member.name}")
            if not member.isfile() or dest.exists():
                raise AuditError(f"non-regular/colliding archive member: {member.name}")
            plan.append((member, dest))
        for member, dest in plan:
            src = tf.extractfile(member)
            if src is None:
                raise AuditError(f"cannot stream archive member: {member.name}")
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open("xb") as out:
                while True:
                    block = src.read(1024 * 1024)
                    if not block:
                        break
                    out.write(block)
    return {"archiveSha256": EXPECTED_ARCHIVE_SHA256, "archiveByteCount": EXPECTED_ARCHIVE_SIZE, "archiveMemberCount": EXPECTED_ARCHIVE_MEMBERS}


def prepare_no_extension_aliases(data_dir: Path) -> dict[str, Any]:
    rows = []
    for species, expected_sha in EXPECTED_ASSET_SHA256.items():
        source = data_dir / "aerosol" / "OPAC" / "optprop" / f"{species.lower()}.mie.cdf"
        alias = data_dir / "aerosol" / "OPAC" / "optprop" / species
        failed1 = data_dir / "aerosol" / "OPAC" / "optprop" / f"{species}.nc"
        failed2 = data_dir / "aerosol" / "OPAC" / f"{species}.nc"
        if not source.is_file() or sha256_file(source) != expected_sha:
            raise AuditError(f"official source drift: {species}")
        if alias.exists() or failed1.exists() or failed2.exists():
            raise AuditError(f"unexpected resolver alias preexists: {species}")
        alias.write_bytes(source.read_bytes())
        if sha256_file(alias) != expected_sha or alias.read_bytes() != source.read_bytes():
            raise AuditError(f"byte-identical alias failure: {species}")
        rows.append({"species": species, "source": str(source), "alias": str(alias), "sha256": expected_sha, "byteCount": source.stat().st_size})
    return {"status": "FOUR_NO_EXTENSION_ALIASES_READY", "aliases": rows}


def parse_afgl_altitudes(path: Path) -> tuple[float, ...]:
    if sha256_file(path) != EXPECTED_AFGL_SHA256:
        raise AuditError("AFGL-US SHA drift")
    altitudes = []
    for raw in path.read_text().splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        altitudes.append(float(s.split()[0]))
    if len(altitudes) != 50 or not all(altitudes[i] > altitudes[i + 1] for i in range(len(altitudes) - 1)):
        raise AuditError("AFGL-US altitude-grid drift")
    return tuple(altitudes)


def render_common(data_dir: Path, repo_root: Path) -> list[str]:
    grid = (repo_root / "experiments/aerosol-family-challenge-v2-r8/wavelength-grid-1nm.dat").resolve()
    if not grid.is_file():
        raise AuditError(f"frozen wavelength grid missing: {grid}")
    return [
        f"data_files_path {data_dir.resolve()}",
        f"atmosphere_file {(data_dir / 'atmmod/afglus.dat').resolve()}",
        f"source solar {(data_dir / 'solar_flux/atlas_plus_modtran').resolve()}",
        "mol_abs_param crs",
        f"wavelength_grid_file {grid}",
        "wavelength 550 550",
        "sza 80",
        "albedo 0.15",
        "rte_solver null",
        "zout atm_levels",
        "output_user zout rh",
    ]


def write_inputs(data_dir: Path, repo_root: Path, output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=False)
    afgl = data_dir / "atmmod" / "afglus.dat"
    altitudes = parse_afgl_altitudes(afgl)
    continental = data_dir / "aerosol" / "OPAC" / "standard_aerosol_files" / "continental_average.dat"
    if not continental.is_file() or sha256_file(continental) != EXPECTED_CONTINENTAL_SHA256:
        raise AuditError("continental_average.dat drift")
    common = render_common(data_dir, repo_root)
    rh_text = "\n".join([*common, "quiet"]) + "\n"
    mix_text = "\n".join([
        *common,
        "aerosol_default",
        "aerosol_species_library OPAC",
        "aerosol_species_file continental_average",
        "verbose",
    ]) + "\n"
    (output / "rh-only.inp").write_text(rh_text)
    (output / "continental-null-verbose.inp").write_text(mix_text)
    meta = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "NULL_SOLVER_AUDIT_INPUTS_FROZEN",
        "afglSha256": EXPECTED_AFGL_SHA256,
        "continentalAverageSha256": EXPECTED_CONTINENTAL_SHA256,
        "atmosphereAltitudesKm": list(altitudes),
        "opacRhNodesPercent": list(OPAC_RH_NODES),
        "rteSolver": "null",
        "wavelengthNm": 550.0,
        "scientificSolverExecuted": False,
        "scientificOrdinalAllocated": False,
    }
    (output / "input-manifest.json").write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n")
    return meta


def nearest_opac_rh_node(rh: float) -> float:
    distances = [(abs(rh - node), node) for node in OPAC_RH_NODES]
    distances.sort()
    if len(distances) > 1 and abs(distances[0][0] - distances[1][0]) <= 1e-10:
        raise AuditError(f"RH value is an unresolved nearest-node tie: {rh}")
    return float(distances[0][1])


def parse_rh_output(path: Path, expected_altitudes_desc: tuple[float, ...]) -> list[dict[str, float]]:
    rows = []
    for line_no, raw in enumerate(path.read_text(errors="strict").splitlines(), 1):
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split()
        if len(parts) != 2:
            raise AuditError(f"unexpected RH output row {line_no}: {raw!r}")
        try:
            z, rh = map(float, parts)
        except ValueError as exc:
            raise AuditError(f"nonnumeric RH output row {line_no}") from exc
        if not math.isfinite(z) or not math.isfinite(rh) or rh < 0:
            raise AuditError(f"invalid RH output row {line_no}")
        rows.append({"altitudeKm": z, "relativeHumidityPercent": rh, "nearestOpacRhNodePercent": nearest_opac_rh_node(rh)})
    if len(rows) != len(expected_altitudes_desc):
        raise AuditError(f"RH row count drift: {len(rows)} vs {len(expected_altitudes_desc)}")
    got = [row["altitudeKm"] for row in rows]
    expected = list(expected_altitudes_desc)
    if got != expected and got != list(reversed(expected)):
        raise AuditError("RH output altitude grid differs from AFGL-US atm_levels")
    if got == list(reversed(expected)):
        rows.reverse()
    return rows


def freeze_report(evidence: Path, input_manifest: dict[str, Any]) -> dict[str, Any]:
    rh_rows = parse_rh_output(evidence / "rh-only.out", tuple(input_manifest["atmosphereAltitudesKm"]))
    mix_rows = parse_rh_output(evidence / "continental-null.out", tuple(input_manifest["atmosphereAltitudesKm"]))
    if rh_rows != mix_rows:
        raise AuditError("background RH changed when continental_average aerosol was enabled")
    verbose_path = evidence / "continental-null.verbose.err"
    if not verbose_path.is_file() or verbose_path.stat().st_size <= 0:
        raise AuditError("verbose null-solver evidence missing/empty")
    unique_nodes = sorted({row["nearestOpacRhNodePercent"] for row in rh_rows})
    report = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "PASS_RUNTIME_AFGL_RH_AND_NEAREST_OPAC_NODE_PROFILE_FROZEN",
        "rteSolver": "null",
        "nullSolverBoundary": "libRadtran NULL solver sets up optical properties and postprocessing but does not solve the radiative transfer equation",
        "wavelengthNm": 550.0,
        "afglSha256": input_manifest["afglSha256"],
        "continentalAverageSha256": input_manifest["continentalAverageSha256"],
        "runtimeRhProfile": rh_rows,
        "nearestOpacRhNodesUsed": unique_nodes,
        "rhOnlyStdoutSha256": sha256_file(evidence / "rh-only.out"),
        "continentalStdoutSha256": sha256_file(evidence / "continental-null.out"),
        "continentalVerboseStderrSha256": sha256_file(verbose_path),
        "continentalVerboseLineCount": len(verbose_path.read_text(errors="replace").splitlines()),
        "scientificRadiativeTransferSolved": False,
        "mysticExecuted": False,
        "scientificOrdinalAllocated": False,
        "taylorOrJerusalemUsed": False,
        "productionAuthorized": False,
        "interpretationBoundary": "The nearest-node column is a preregistered deterministic mapping of runtime-reported RH to the frozen OPAC RH coordinate set. Raw verbose output is preserved separately; optical-profile parsing remains a later evidence step if needed.",
    }
    canonical = json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    report["contentSha256"] = hashlib.sha256(canonical).hexdigest()
    (evidence / "rh-selection-report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--archive", type=Path, required=True)
    p.add_argument("--runtime-root", type=Path, required=True)
    p.add_argument("--repo-root", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    f = sub.add_parser("freeze")
    f.add_argument("--evidence", type=Path, required=True)
    f.add_argument("--manifest", type=Path, required=True)
    args = ap.parse_args()
    if args.cmd == "prepare":
        archive_meta = extract_frozen_archive(args.archive, args.runtime_root / "share" / "libRadtran")
        data_dir = args.runtime_root / "share" / "libRadtran" / "data"
        aliases = prepare_no_extension_aliases(data_dir)
        meta = write_inputs(data_dir, args.repo_root, args.output)
        meta["archive"] = archive_meta
        meta["resolverAliases"] = aliases
        (args.output / "input-manifest.json").write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n")
        print(json.dumps(meta, sort_keys=True))
    else:
        meta = json.loads(args.manifest.read_text())
        print(json.dumps(freeze_report(args.evidence, meta), sort_keys=True))


if __name__ == "__main__":
    main()
