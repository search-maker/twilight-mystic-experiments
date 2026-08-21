from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

STAGE_ID = "aerosol-optical-property-sensitivity-v1"
PROTOCOL_PATH = Path(__file__).resolve().parent / "protocol.review.json"
SEED_DOMAIN_MAX_EXCLUSIVE = 2_147_483_647


class Refusal(RuntimeError):
    pass


def load_protocol() -> dict[str, Any]:
    value = json.loads(PROTOCOL_PATH.read_text())
    if value.get("stageId") != STAGE_ID:
        raise Refusal("protocol stage drift")
    if value.get("status") != "REVIEW_ONLY_PREREGISTRATION_EXECUTION_DISABLED_RESULTS_NOT_OPENED":
        raise Refusal("protocol is not review-only")
    if value.get("scientificExecutionAuthorized") is not False or value.get("solverExecutionAuthorized") is not False:
        raise Refusal("review protocol unexpectedly authorizes execution")
    return value


def _states_by_id(protocol: dict[str, Any]) -> dict[str, dict[str, Any]]:
    states = protocol.get("aerosolStates")
    if not isinstance(states, list) or len(states) != 5:
        raise Refusal("exactly five aerosol states required")
    out = {str(s.get("stateId")): s for s in states if isinstance(s, dict)}
    if len(out) != 5:
        raise Refusal("aerosol state IDs missing or duplicated")
    return out


def aerosol_block(state_id: str, aod550: float) -> list[str]:
    protocol = load_protocol()
    states = _states_by_id(protocol)
    if state_id not in states:
        raise Refusal(f"unknown aerosol state: {state_id}")
    if isinstance(aod550, bool) or not isinstance(aod550, (int, float)) or float(aod550) not in (0.10, 0.30):
        raise Refusal("AOD550 must be one of the preregistered values")
    s = states[state_id]
    if s.get("aerosolHazeCode") != 1 or s.get("aerosolSeasonCode") != 1:
        raise Refusal("all sensitivity states must retain rural/spring-summer Shettle basis")
    lines = [
        "aerosol_default",
        "aerosol_haze 1",
        "aerosol_vulcan 1",
        "aerosol_season 1",
        f"aerosol_set_tau_at_wvl 550 {float(aod550):.6f}",
    ]
    kind = s.get("kind")
    ssa = s.get("ssaSet")
    gg = s.get("ggSet")
    if kind == "native-reference":
        if ssa is not None or gg is not None:
            raise Refusal("native reference must not override SSA or g")
    elif kind == "controlled-factorial":
        if ssa not in (0.85, 0.98) or gg not in (0.60, 0.80):
            raise Refusal("factorial SSA/g endpoint drift")
        lines.extend((f"aerosol_modify ssa set {ssa:.2f}", f"aerosol_modify gg set {gg:.2f}"))
    else:
        raise Refusal("unknown aerosol state kind")
    return lines


def assert_exact_aerosol_surface(rendered: str, state_id: str, aod550: float) -> None:
    lines = [line.strip() for line in rendered.splitlines() if line.strip()]
    aerosol_lines = [line for line in lines if line.startswith("aerosol_")]
    expected = aerosol_block(state_id, aod550)
    if aerosol_lines != expected:
        raise Refusal(f"aerosol directive surface drift: expected={expected!r} observed={aerosol_lines!r}")
    if sum(line.startswith("aerosol_set_tau_at_wvl ") for line in aerosol_lines) != 1:
        raise Refusal("AOD directive must occur exactly once")
    if state_id == "native-rural-ss":
        if any(line.startswith("aerosol_modify ") for line in aerosol_lines):
            raise Refusal("native reference cannot contain aerosol_modify")
    else:
        if sum(line.startswith("aerosol_modify ssa set ") for line in aerosol_lines) != 1:
            raise Refusal("factorial state requires exactly one SSA set directive")
        if sum(line.startswith("aerosol_modify gg set ") for line in aerosol_lines) != 1:
            raise Refusal("factorial state requires exactly one g set directive")


def _validate_case(case: dict[str, Any]) -> None:
    protocol = load_protocol()
    design = protocol["fixedNumericalAndPhysicalDesign"]
    if case.get("renderable") is not True or case.get("executionAuthorized") is not True:
        raise Refusal("case is review-only/non-renderable until a separately reviewed authorization binds it")
    if case.get("sunDepressionDeg") not in design["sunDepressionDeg"]:
        raise Refusal("sun depression outside preregistration")
    if case.get("aod550") not in design["aod550"]:
        raise Refusal("AOD outside preregistration")
    if case.get("replicate") not in design["replicates"]:
        raise Refusal("replicate outside preregistration")
    geometries = {g["geometryId"]: g for g in design["geometries"]}
    geo = geometries.get(case.get("geometryId"))
    if geo is None:
        raise Refusal("geometry outside preregistration")
    for key in ("targetAltitudeDeg", "relativeAzimuthDeg"):
        if float(case.get(key, float("nan"))) != float(geo[key]):
            raise Refusal(f"geometry field drift: {key}")
    if float(case.get("observerElevationM", float("nan"))) != 0.0:
        raise Refusal("observer elevation must remain 0 m")
    if case.get("photonHistories") != 20_000_000:
        raise Refusal("photon history budget drift")
    if case.get("numericalMethod") != "reference-vroom-1nm":
        raise Refusal("numerical method drift")
    seed = case.get("seed")
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 < seed < SEED_DOMAIN_MAX_EXCLUSIVE:
        raise Refusal("fresh authorized seed is required before rendering; review skeletons are intentionally non-renderable")
    state_id = str(case.get("stateId"))
    if state_id not in _states_by_id(protocol):
        raise Refusal("unknown state ID")


def render_case_input(case: dict[str, Any], data_dir: Path, repository_root: Path, output_root: Path) -> str:
    _validate_case(case)
    dep = float(case["sunDepressionDeg"])
    alt = float(case["targetAltitudeDeg"])
    az = float(case["relativeAzimuthDeg"])
    grid = (repository_root / "experiments/aerosol-family-challenge-v2/wavelength-grid-1nm.dat").resolve()
    lines = [
        f"data_files_path {data_dir.resolve()}",
        f"atmosphere_file {(data_dir / 'atmmod/afglus.dat').resolve()}",
        f"source solar {(data_dir / 'solar_flux/atlas_plus_modtran').resolve()}",
        "mol_abs_param crs",
        f"wavelength_grid_file {grid}",
        "wavelength 380 780",
        f"sza {90.0 + dep:.6f}",
        "phi0 0.00",
        "rte_solver mystic",
        "mc_spherical 1D",
        f"mc_photons {case['photonHistories']}",
        "mc_vroom on",
        "mc_std",
        f"mc_randomseed {case['seed']}",
        f"mc_basename {(output_root / case['caseId'] / 'mc').resolve()}",
        "albedo 0.150000",
        *aerosol_block(str(case["stateId"]), float(case["aod550"])),
        "zout 0.000000",
        f"umu {-math.sin(math.radians(alt)):.8f}",
        f"phi {az:.6f}",
        "quiet",
    ]
    text = "\n".join(lines) + "\n"
    assert_exact_aerosol_surface(text, str(case["stateId"]), float(case["aod550"]))
    stripped = [line.strip() for line in text.splitlines() if line.strip()]
    for required in ("wavelength 380 780", "mc_vroom on", "mc_std", "rte_solver mystic", "mc_spherical 1D"):
        if stripped.count(required) != 1:
            raise Refusal(f"required numerical directive missing/duplicate: {required}")
    if any(line.startswith("mc_spectral_is ") for line in stripped):
        raise Refusal("ALIS importance-center drift is forbidden")
    return text
