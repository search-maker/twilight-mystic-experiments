#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import math
import sys
from pathlib import Path
from typing import Any, Sequence

BASE_PATH = Path(__file__).with_name("twilight_surrogate_tier1_atm_z_grid_probe.py")
spec = importlib.util.spec_from_file_location("tier1_atm_z_grid_probe_base", BASE_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot load base probe: {BASE_PATH}")
BASE = importlib.util.module_from_spec(spec)
spec.loader.exec_module(BASE)

STAGE_ID = "twilight-surrogate-tier-1-atm-z-grid-equivalence-proof-v2"
PREREGISTERED_TOLERANCES = BASE.PREREGISTERED_TOLERANCES
PRIMARY_SITE_ALTITUDE_KM = BASE.PRIMARY_SITE_ALTITUDE_KM
STRUCTURAL_SITE_ALTITUDES_KM = BASE.STRUCTURAL_SITE_ALTITUDES_KM


class ProofError(RuntimeError):
    pass


def render_profile_input(
    data_dir: Path,
    atmosphere: Path,
    solar_flux: Path,
    representation: str,
    site_altitude_km: float,
    grid_ascending: Sequence[float],
    resolved: bool,
) -> str:
    zouts = BASE.local_levels(grid_ascending, site_altitude_km)
    lines = [
        *BASE.common_lines(data_dir, atmosphere, solar_flux, resolved),
        *BASE.representation_lines(representation, site_altitude_km, grid_ascending),
        "rte_solver disort",
        f"number_of_streams {BASE.CONTROL_STREAMS}",
        "zout " + " ".join(BASE.format_level(value) for value in zouts),
        f"umu {BASE.CONTROL_UMU:.8f}",
        f"phi {BASE.CONTROL_PHI_DEG:.6f}",
        "output_user " + " ".join(BASE.PROFILE_COLUMNS),
        "verbose",
        "",
    ]
    return "\n".join(lines)


def expected_geometry_checks(
    rows: Sequence[dict[str, float]],
    grid: Sequence[float],
    site_altitude_km: float,
    label: str,
) -> list[dict[str, Any]]:
    # zout_sur is printed through a single-precision path. The preregistered
    # tolerance remains unchanged and is applied to A-vs-B differences. Exact
    # physical boundaries are independently checked through zout_sea, z_sur,
    # the exact surface row, and the preserved input grid.
    return [
        BASE.compare_vectors(
            f"{label}.zout_sea",
            BASE.profile_vectors(rows, "zout_sea"),
            list(grid),
            "surfaceAndOutputAltitudeKm",
        ),
        BASE.compare_vectors(
            f"{label}.z_sur",
            BASE.profile_vectors(rows, "z_sur"),
            [site_altitude_km] * len(rows),
            "surfaceAndOutputAltitudeKm",
        ),
        BASE.compare_vectors(
            f"{label}.surface-local-zout",
            [rows[0]["zout_sur"]],
            [0.0],
            "surfaceAndOutputAltitudeKm",
        ),
        BASE.compare_vectors(
            f"{label}.surface-sea-level-zout",
            [rows[0]["zout_sea"]],
            [site_altitude_km],
            "surfaceAndOutputAltitudeKm",
        ),
    ]


def validate_profile_pair(
    rows_a: Sequence[dict[str, float]],
    rows_b: Sequence[dict[str, float]],
    grid: Sequence[float],
    site_altitude_km: float,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    checks.extend(expected_geometry_checks(rows_a, grid, site_altitude_km, "A"))
    checks.extend(expected_geometry_checks(rows_b, grid, site_altitude_km, "B"))
    for field in ("zout_sur", "zout_sea", "z_sur"):
        checks.append(
            BASE.compare_vectors(
                f"A-vs-B.{field}",
                BASE.profile_vectors(rows_a, field),
                BASE.profile_vectors(rows_b, field),
                "layerBoundaryKm",
            )
        )
    for field in BASE.PROFILE_STATE_COLUMNS:
        checks.append(
            BASE.compare_vectors(
                f"A-vs-B.{field}",
                BASE.profile_vectors(rows_a, field),
                BASE.profile_vectors(rows_b, field),
                "pressureTemperatureAndNumberDensity",
            )
        )
    columns_a = BASE.gas_columns(rows_a)
    columns_b = BASE.gas_columns(rows_b)
    for field in BASE.GAS_DENSITY_COLUMNS:
        checks.append(
            BASE.compare_vectors(
                f"A-vs-B.column.{field}",
                [columns_a[field]],
                [columns_b[field]],
                "gasColumn",
            )
        )
    radiometric_checks = [
        BASE.compare_vectors(
            f"A-vs-B.{field}",
            BASE.profile_vectors(rows_a, field),
            BASE.profile_vectors(rows_b, field),
            "deterministicRadianceOrIrradiance",
        )
        for field in BASE.RADIOMETRIC_COLUMNS
    ]
    return {
        "atmosphericProfileAndColumnPassed": all(check["passed"] for check in checks),
        "deterministicControlPassed": all(
            check["passed"] for check in radiometric_checks
        ),
        "atmosphericChecks": checks,
        "radiometricChecks": radiometric_checks,
        "gasColumnsA": columns_a,
        "gasColumnsB": columns_b,
        "runtimeReportedLocalZoutPrecision": (
            "single-precision path rendered at six decimals; tolerance unchanged"
        ),
    }


def parse_resolved_optical_table(stderr: str) -> dict[str, list[float]]:
    marker = "*** optical_properties()"
    position = stderr.find(marker)
    if position < 0:
        raise ProofError("resolved optical_properties table not found")
    names = (
        "lowerBoundaryKm",
        "rayleighLayerOpticalDepth",
        "aerosolScatteringLayerOpticalDepth",
        "aerosolAbsorptionLayerOpticalDepth",
        "aerosolAsymmetry",
        "waterCloudScatteringLayerOpticalDepth",
        "waterCloudAbsorptionLayerOpticalDepth",
        "waterCloudAsymmetry",
        "iceCloudScatteringLayerOpticalDepth",
        "iceCloudAbsorptionLayerOpticalDepth",
        "iceCloudAsymmetry",
        "iceCloudFf",
        "iceCloudG1",
        "iceCloudG2",
        "iceCloudF",
        "molecularAbsorptionLayerOpticalDepth",
    )
    columns: dict[str, list[float]] = {name: [] for name in names}
    expected_index = 0
    for raw in stderr[position:].splitlines():
        pieces = [piece.strip() for piece in raw.split("|")]
        if len(pieces) != 7:
            continue
        try:
            layer_index = int(pieces[0])
        except ValueError:
            if expected_index and pieces[0] == "sum":
                break
            continue
        if layer_index != expected_index:
            if expected_index:
                break
            continue
        try:
            values = [
                float(pieces[1]),
                float(pieces[2]),
                *[float(value) for value in pieces[3].split()],
                *[float(value) for value in pieces[4].split()],
                *[float(value) for value in pieces[5].split()],
                float(pieces[6]),
            ]
        except ValueError as exc:
            raise ProofError(f"malformed optical_properties row: {raw}") from exc
        if len(values) != len(names):
            raise ProofError(
                f"unexpected optical_properties field count {len(values)}: {raw}"
            )
        if not all(math.isfinite(value) for value in values):
            raise ProofError("non-finite resolved optical property")
        for name, value in zip(names, values, strict=True):
            columns[name].append(value)
        expected_index += 1
    if not expected_index:
        raise ProofError("no resolved optical property rows parsed")
    columns["totalScatteringLayerOpticalDepth"] = [
        rayleigh + aerosol + water + ice
        for rayleigh, aerosol, water, ice in zip(
            columns["rayleighLayerOpticalDepth"],
            columns["aerosolScatteringLayerOpticalDepth"],
            columns["waterCloudScatteringLayerOpticalDepth"],
            columns["iceCloudScatteringLayerOpticalDepth"],
            strict=True,
        )
    ]
    columns["totalAbsorptionLayerOpticalDepth"] = [
        molecular + aerosol + water + ice
        for molecular, aerosol, water, ice in zip(
            columns["molecularAbsorptionLayerOpticalDepth"],
            columns["aerosolAbsorptionLayerOpticalDepth"],
            columns["waterCloudAbsorptionLayerOpticalDepth"],
            columns["iceCloudAbsorptionLayerOpticalDepth"],
            strict=True,
        )
    ]
    columns["totalLayerOpticalDepth"] = [
        scattering + absorption
        for scattering, absorption in zip(
            columns["totalScatteringLayerOpticalDepth"],
            columns["totalAbsorptionLayerOpticalDepth"],
            strict=True,
        )
    ]
    return columns


def validate_optical_pair(
    table_a: dict[str, list[float]],
    table_b: dict[str, list[float]],
    expected_grid: Sequence[float],
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    variables = sorted(set(table_a) | set(table_b))
    optical_depth_variables = {
        name
        for name in variables
        if "OpticalDepth" in name or name == "rayleighLayerOpticalDepth"
    }
    for name in variables:
        if name not in table_a or name not in table_b:
            checks.append(
                {"label": name, "passed": False, "reason": "variable-missing"}
            )
            continue
        checks.append(
            BASE.compare_vectors(
                f"A-vs-B.{name}",
                table_a[name],
                table_b[name],
                (
                    "layerBoundaryKm"
                    if name == "lowerBoundaryKm"
                    else "layerOpticalProperty"
                ),
            )
        )
        if name in optical_depth_variables:
            checks.append(
                BASE.compare_vectors(
                    f"A-vs-B.column.{name}",
                    [sum(table_a[name])],
                    [sum(table_b[name])],
                    "columnOpticalProperty",
                )
            )
    expected_layer_count = len(expected_grid) - 1
    for label, table in (("A", table_a), ("B", table_b)):
        actual_layer_count = len(table["lowerBoundaryKm"])
        checks.append(
            {
                "label": f"{label}.optical-layer-count",
                "passed": actual_layer_count == expected_layer_count,
                "actualLayerCount": actual_layer_count,
                "expectedLayerCount": expected_layer_count,
            }
        )
    return {
        "passed": all(check["passed"] for check in checks),
        "checks": checks,
        "componentsA": table_a,
        "componentsB": table_b,
        "cloudsConfigured": False,
        "allResolvedVerboseVariablesCompared": variables,
        "evidenceSource": "frozen-runtime verbose optical_properties table",
        "runtimePrintedBoundaryPrecision": (
            "four decimals; exact boundaries separately proven by profiles and inputs"
        ),
    }


def run_profile_pair(
    uvspec: Path,
    data_dir: Path,
    atmosphere: Path,
    solar_flux: Path,
    output_root: Path,
    site_altitude_km: float,
) -> dict[str, Any]:
    grid = BASE.forced_grid_ascending(atmosphere, site_altitude_km)
    runs: dict[str, Any] = {}
    parsed: dict[str, list[dict[str, float]]] = {}
    optical_tables: dict[str, dict[str, list[float]]] = {}
    for short, representation in (
        ("A", "A-explicit-altitude-control"),
        ("B", "B-atm-z-grid-candidate"),
    ):
        run_dir = output_root / f"h-{site_altitude_km:.6f}" / f"profile-{short}"
        raw = render_profile_input(
            data_dir,
            atmosphere,
            solar_flux,
            representation,
            site_altitude_km,
            grid,
            False,
        )
        resolved = render_profile_input(
            data_dir,
            atmosphere,
            solar_flux,
            representation,
            site_altitude_km,
            grid,
            True,
        )
        execution = BASE.run_uvspec(uvspec, run_dir, raw, resolved, 180)
        stdout = execution.pop("stdout")
        stderr = execution.pop("stderr")
        if execution["exitCode"] != 0 or execution["timedOut"]:
            raise ProofError(
                f"deterministic profile {short} failed at h={site_altitude_km:.6f}: "
                f"exit={execution['exitCode']} timeout={execution['timedOut']}"
            )
        rows = BASE.parse_profile_output(stdout)
        optical_table = parse_resolved_optical_table(stderr)
        if len(rows) != len(grid):
            raise ProofError(
                f"profile row count mismatch at h={site_altitude_km:.6f}, {short}: "
                f"{len(rows)} != {len(grid)}"
            )
        profile_path = run_dir / "profile-parsed.json"
        optical_path = run_dir / "resolved-optical-table.json"
        profile_path.write_text(BASE.dump(rows), encoding="utf-8")
        optical_path.write_text(BASE.dump(optical_table), encoding="utf-8")
        execution["profileParsedSha256"] = BASE.raw_sha256(profile_path)
        execution["resolvedOpticalTableSha256"] = BASE.raw_sha256(optical_path)
        runs[short] = execution
        parsed[short] = rows
        optical_tables[short] = optical_table
    decision = validate_profile_pair(parsed["A"], parsed["B"], grid, site_altitude_km)
    result = {
        "siteAltitudeKm": site_altitude_km,
        "forcedGridAscendingKm": grid,
        "forcedGridBottomKm": grid[0],
        "allOriginalLevelsAboveSitePreservedExactly": True,
        "layersBelowSiteAltitudePresent": False,
        "runs": runs,
        "decision": decision,
        "opticalTables": optical_tables,
    }
    result_path = output_root / f"h-{site_altitude_km:.6f}" / "profile-equivalence.json"
    result_path.write_text(BASE.dump(result), encoding="utf-8")
    result["resultRawSha256"] = BASE.raw_sha256(result_path)
    return result


def run_optical_pair(primary_profile: dict[str, Any], output_root: Path) -> dict[str, Any]:
    tables = primary_profile["opticalTables"]
    decision = validate_optical_pair(
        tables["A"], tables["B"], primary_profile["forcedGridAscendingKm"]
    )
    result = {
        "siteAltitudeKm": PRIMARY_SITE_ALTITUDE_KM,
        "runs": primary_profile["runs"],
        "decision": decision,
        "additionalSolverExecutionCount": 0,
        "boundary": (
            "resolved optical properties parsed from the same deterministic A/B "
            "verbose controls; no netCDF writer and no additional solver call"
        ),
    }
    result_path = (
        output_root
        / f"h-{PRIMARY_SITE_ALTITUDE_KM:.6f}"
        / "optical-equivalence.json"
    )
    result_path.write_text(BASE.dump(result), encoding="utf-8")
    result["resultRawSha256"] = BASE.raw_sha256(result_path)
    return result


def should_run_mystic(
    primary_profile: dict[str, Any],
    optical: dict[str, Any],
    structural_profiles: Sequence[dict[str, Any]],
) -> bool:
    return (
        primary_profile["decision"]["atmosphericProfileAndColumnPassed"]
        and primary_profile["decision"]["deterministicControlPassed"]
        and optical["decision"]["passed"]
        and all(
            item["decision"]["atmosphericProfileAndColumnPassed"]
            and item["decision"]["deterministicControlPassed"]
            for item in structural_profiles
        )
    )


def boundary_fields() -> dict[str, Any]:
    return {
        "candidateRepresentation": {
            "atmosphereFileRemainsProfileSource": True,
            "atmZGridBottomIsSiteAltitude": True,
            "originalAtmosphereLevelsAboveSitePreservedExactly": True,
            "explicitAltitudeForbidden": True,
            "mcElevationFileForbidden": True,
            "localSurfaceZoutKm": 0.0,
        },
        "controlGeometry": {
            "purpose": "low-SZA deterministic mechanism control only",
            "szaDeg": BASE.CONTROL_SZA_DEG,
            "wavelengthNm": BASE.CONTROL_WAVELENGTH_NM,
            "umu": BASE.CONTROL_UMU,
            "phiDeg": BASE.CONTROL_PHI_DEG,
            "notFrozenTier1TwilightGeometry": True,
        },
        "sourceProvenance": {
            "status": "SEPARATE_UNRESOLVED_OFFICIAL_ARCHIVE_HASH_MISMATCH",
            "historicCondaForgeExpectedSha256": BASE.SOURCE_ARCHIVE_EXPECTED_SHA256,
            "currentOfficialDownloadObservedSha256": (
                BASE.SOURCE_ARCHIVE_CURRENT_DOWNLOAD_SHA256
            ),
            "expectedHashChangedToMakeCiGreen": False,
            "sourceEvidenceAccepted": False,
            "behaviorEvidenceIndependentOfSourceArchiveAcceptance": True,
        },
        "scientificExecution": False,
        "scientificDatasetProduced": False,
        "surrogateTrainingUsePermitted": False,
        "authorizationPermitted": False,
        "ordinal2ScientificDispatchPermitted": False,
        "githubRerunPermitted": False,
        "maximumPermittedMysticSolverExecutionCount": 1,
        "frozenTier1InvariantsChanged": False,
    }


def proof(
    uvspec: Path,
    data_dir: Path,
    atmosphere: Path,
    solar_flux: Path,
    runtime_lock: Path,
    output_dir: Path,
    package_explicit: Path | None,
    package_json: Path | None,
) -> dict[str, Any]:
    for path, label in (
        (uvspec, "uvspec"),
        (atmosphere, "atmosphere"),
        (solar_flux, "solar flux"),
        (runtime_lock, "runtime lock"),
    ):
        if not path.is_file():
            raise ProofError(f"{label} missing: {path}")
    if not data_dir.is_dir():
        raise ProofError(f"data directory missing: {data_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    tolerance_path = output_dir / "preregistered-tolerances.json"
    tolerance_path.write_text(BASE.dump(PREREGISTERED_TOLERANCES), encoding="utf-8")

    primary_profile = run_profile_pair(
        uvspec,
        data_dir,
        atmosphere,
        solar_flux,
        output_dir,
        PRIMARY_SITE_ALTITUDE_KM,
    )
    optical = run_optical_pair(primary_profile, output_dir)
    structural_profiles = [
        run_profile_pair(
            uvspec,
            data_dir,
            atmosphere,
            solar_flux,
            output_dir,
            height,
        )
        for height in STRUCTURAL_SITE_ALTITUDES_KM
    ]
    deterministic_gate = should_run_mystic(
        primary_profile, optical, structural_profiles
    )
    mystic = (
        BASE.run_mystic_probe(
            uvspec, data_dir, atmosphere, solar_flux, output_dir
        )
        if deterministic_gate
        else {
            "status": "NOT_RUN_DETERMINISTIC_EQUIVALENCE_GATE_FAILED",
            "passed": False,
            "solverExecutionCount": 0,
            "mcPhotons": 0,
            "scientificDatasetProduced": False,
        }
    )

    profile_decision = primary_profile["decision"][
        "atmosphericProfileAndColumnPassed"
    ]
    deterministic_decision = primary_profile["decision"][
        "deterministicControlPassed"
    ]
    optical_decision = optical["decision"]["passed"]
    three_heights_decision = all(
        item["decision"]["atmosphericProfileAndColumnPassed"]
        and item["decision"]["deterministicControlPassed"]
        for item in structural_profiles
    )
    proof_passed = (
        profile_decision
        and deterministic_decision
        and optical_decision
        and three_heights_decision
        and mystic["passed"]
    )
    result = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": (
            "ATM_Z_GRID_ELEVATED_SITE_EQUIVALENCE_AND_MYSTIC_ACCEPTANCE_PROOF_PASSED"
            if proof_passed
            else "ATM_Z_GRID_ELEVATED_SITE_PROOF_FAILED"
        ),
        "proofPassed": proof_passed,
        **boundary_fields(),
        "preregisteredTolerances": PREREGISTERED_TOLERANCES,
        "preregisteredTolerancesRawSha256": BASE.raw_sha256(tolerance_path),
        "profileEquivalenceDecision": profile_decision,
        "opticalPropertyEquivalenceDecision": optical_decision,
        "deterministicControlDecision": deterministic_decision,
        "threeHeightStructuralProfileDecision": three_heights_decision,
        "mysticProbeDecision": mystic["passed"],
        "primaryProfile": primary_profile,
        "primaryOptical": optical,
        "structuralProfiles": structural_profiles,
        "mysticProbe": mystic,
        "runtime": {
            "uvspecSha256": BASE.raw_sha256(uvspec),
            "runtimeLockRawSha256": BASE.raw_sha256(runtime_lock),
            "atmosphereSha256": BASE.raw_sha256(atmosphere),
            "solarFluxSha256": BASE.raw_sha256(solar_flux),
            "packageExplicit": BASE.package_identity(package_explicit),
            "packageJson": BASE.package_identity(package_json),
        },
        "deterministicSolverExecutionCount": 6,
        "mysticSolverExecutionCount": mystic["solverExecutionCount"],
        "boundary": (
            "mechanism equivalence and one-photon MYSTIC acceptance proof only; "
            "no Tier-1 dataset, authorization, dispatch, training, Tier-2, or production claim"
        ),
    }
    report_path = output_dir / "atm-z-grid-equivalence-proof.json"
    report_path.write_text(BASE.dump(result), encoding="utf-8")
    result["reportRawSha256"] = BASE.raw_sha256(report_path)
    if not proof_passed:
        raise ProofError(
            "preregistered proof decision failed; evidence preserved with authorization false"
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--uvspec", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--atmosphere", type=Path, required=True)
    parser.add_argument("--solar-flux", type=Path, required=True)
    parser.add_argument("--runtime-lock", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--package-explicit", type=Path)
    parser.add_argument("--package-json", type=Path)
    args = parser.parse_args()
    try:
        result = proof(
            args.uvspec,
            args.data_dir,
            args.atmosphere,
            args.solar_flux,
            args.runtime_lock,
            args.output_dir,
            args.package_explicit,
            args.package_json,
        )
        print(BASE.dump(result), end="")
        return 0
    except Exception as exc:
        failure = {
            "schemaVersion": 1,
            "stageId": STAGE_ID,
            "status": "REFUSED",
            "proofPassed": False,
            "reason": str(exc),
            **boundary_fields(),
            "mysticSolverExecutionCount": 0,
        }
        try:
            args.output_dir.mkdir(parents=True, exist_ok=True)
            report_path = args.output_dir / "atm-z-grid-equivalence-proof.json"
            if not report_path.exists():
                report_path.write_text(BASE.dump(failure), encoding="utf-8")
        except Exception:
            pass
        print(BASE.dump(failure), file=sys.stderr, end="")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
