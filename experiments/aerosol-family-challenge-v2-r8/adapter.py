from __future__ import annotations
import math
from pathlib import Path
from typing import Any
from core import FAMILIES, SEASONS, NUMERICAL_METHOD, Refusal

EXPECTED_AEROSOL_KEYS=("aerosol_default","aerosol_haze","aerosol_vulcan","aerosol_season","aerosol_set_tau_at_wvl")

def aerosol_block(case:dict[str,Any])->list[str]:
    fam=case.get("aerosolFamily"); season=case.get("aerosolSeason")
    if fam not in FAMILIES or season not in SEASONS: raise Refusal("unknown aerosol family or season")
    if case.get("aerosolHazeCode")!=FAMILIES[fam] or case.get("aerosolSeasonCode")!=SEASONS[season] or case.get("aerosolVulcanCode")!=1: raise Refusal("aerosol code mismatch")
    aod=case.get("aod550")
    if isinstance(aod,bool) or not isinstance(aod,(int,float)) or not 0<=float(aod)<=5: raise Refusal("invalid AOD550")
    return ["aerosol_default",f"aerosol_haze {FAMILIES[fam]}","aerosol_vulcan 1",f"aerosol_season {SEASONS[season]}",f"aerosol_set_tau_at_wvl 550 {float(aod):.6f}"]

def assert_exact_aerosol_state(rendered:str,case:dict[str,Any])->None:
    lines=[x.strip() for x in rendered.splitlines() if x.strip()]
    expected=aerosol_block(case)
    aerosol=[x for x in lines if x.startswith("aerosol_")]
    if aerosol!=expected: raise Refusal(f"rendered aerosol surface is not exact: {aerosol!r}")

def assert_exact_spectrum_surface(rendered:str)->None:
    lines=[x.strip() for x in rendered.splitlines()]
    required=("wavelength 380 780","mc_vroom on","mc_std")
    for x in required:
        if lines.count(x)!=1: raise Refusal(f"full-spectrum directive missing/duplicate: {x}")
    grids=[x for x in lines if x.startswith("wavelength_grid_file ")]
    if len(grids)!=1 or not grids[0].endswith("wavelength-grid-1nm.dat"): raise Refusal("exact 1-nm wavelength grid is required")
    if any(x.startswith("mc_spectral_is ") for x in lines): raise Refusal("ALIS importance center is forbidden in reference-vroom-1nm challenge")

def render_case_input(case:dict[str,Any],data_dir:Path,repository_root:Path,output_root:Path)->str:
    if case.get("numericalMethod")!=NUMERICAL_METHOD: raise Refusal("numerical method drift")
    if case.get("observerElevationM")!=0.0: raise Refusal("v2 geometry requires sea-level site; do not substitute altitude/zout semantics")
    grid=(repository_root/'experiments/aerosol-family-challenge-v2/wavelength-grid-1nm.dat').resolve()
    dep=float(case["sunDepressionDeg"]); alt=float(case["targetAltitudeDeg"]); az=float(case["relativeAzimuthDeg"])
    lines=[
      f"data_files_path {data_dir.resolve()}",
      f"atmosphere_file {(data_dir/'atmmod/afglus.dat').resolve()}",
      f"source solar {(data_dir/'solar_flux/atlas_plus_modtran').resolve()}",
      "mol_abs_param crs", f"wavelength_grid_file {grid}", "wavelength 380 780",
      f"sza {90.0+dep:.6f}", "phi0 0.00", "rte_solver mystic", "mc_spherical 1D",
      f"mc_photons {case['photonHistories']}", "mc_vroom on", "mc_std", f"mc_randomseed {case['seed']}",
      f"mc_basename {(output_root/case['caseId']/'mc').resolve()}", "albedo 0.150000",
      *aerosol_block(case), "zout 0.000000", f"umu {-math.sin(math.radians(alt)):.8f}", f"phi {az:.6f}", "quiet"
    ]
    text="\n".join(lines)+"\n"; assert_exact_aerosol_state(text,case); assert_exact_spectrum_surface(text); return text

def transform_pinned_base_render(rendered:str,case:dict[str,Any])->str:
    # Defensive helper if a future execution wrapper delegates to the pinned generic adapter.
    lines=rendered.splitlines(); aeros=[x.strip() for x in lines if x.strip().startswith("aerosol_")]
    expected=["aerosol_default",f"aerosol_set_tau_at_wvl 550 {float(case['aod550']):.6f}"]
    if aeros!=expected: raise Refusal(f"base aerosol directive surface drifted; refuse instead of silently transforming: {aeros!r}")
    kept=[x for x in lines if not x.strip().startswith("aerosol_")]
    at=next((i for i,x in enumerate(kept) if x.strip().startswith("zout ")),len(kept))
    out="\n".join(kept[:at]+aerosol_block(case)+kept[at:])+"\n"; assert_exact_aerosol_state(out,case); return out
