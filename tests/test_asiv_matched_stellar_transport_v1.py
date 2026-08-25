from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "review/asiv-matched-stellar-transport-v1/execution_candidate.py"


def load_candidate():
    spec = importlib.util.spec_from_file_location("asiv_matched_stellar_candidate", CANDIDATE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_candidate_is_render_only_and_case_counts_are_frozen():
    mod = load_candidate()
    payload = mod.build_prefrozen_manifest()
    assert payload["status"] == "PREFROZEN_RENDER_ONLY_NO_SOLVER_EXECUTION"
    assert payload["training"]["caseCount"] == 2700
    assert payload["training"]["casesPerFamily"] == 675
    assert payload["validation"]["atmosphericCaseCount"] == 768
    assert payload["validation"]["atmosphericCasesPerFamily"] == 192
    assert payload["validation"]["johnsonVComparisonCount"] == 2304
    assert payload["validation"]["johnsonVComparisonsPerFamily"] == 576
    assert payload["authorization"] == {
        "solverExecutionAuthorized": False,
        "scientificExecutionAuthorized": False,
        "resultOpeningAuthorized": False,
        "pandoraHoldoutAccessAllowed": False,
        "starsvisibilityMutationAuthorized": False,
        "productionActivationAuthorized": False,
    }
    assert {row["family"] for row in payload["training"]["cases"]} == set(mod.NON_NATIVE_FAMILIES)
    assert {row["family"] for row in payload["validation"]["cases"]} == set(mod.NON_NATIVE_FAMILIES)
    assert all(row["solverExecutionAuthorized"] is False for row in payload["training"]["cases"])
    assert all(row["solverExecutionAuthorized"] is False for row in payload["validation"]["cases"])


def test_validation_grid_is_fresh_relative_to_0081_v2_acceptance_axes():
    mod = load_candidate()
    old_alt = {
        5.333333, 7.333333, 9.333333, 12.333333, 14.333333, 18.333333,
        23.333333, 28.333333, 36.666667, 46.666667, 56.666667, 71.666667,
    }
    old_elev = {166.666667, 750, 1500, 2166.666667}
    old_aod = {0.066666667, 0.133333333, 0.233333333, 0.333333333}
    assert old_alt.isdisjoint(set(mod.VALIDATION_ALTITUDE_DEG))
    assert old_elev.isdisjoint(set(mod.VALIDATION_ELEVATION_M))
    assert old_aod.isdisjoint(set(mod.VALIDATION_AOD550))
    assert set(mod.VALIDATION_ALTITUDE_DEG).isdisjoint(set(mod.ALTITUDE_KNOTS))
    assert set(mod.VALIDATION_ELEVATION_M).isdisjoint(set(mod.ELEVATION_KNOTS_M))
    assert set(mod.VALIDATION_AOD550).isdisjoint(set(mod.AOD_KNOTS))


def test_exact_asiv_opac_directive_surface():
    mod = load_candidate()
    expected = {
        "opac-continental-average": "continental_average",
        "opac-maritime-clean": "maritime_clean",
        "opac-desert": "desert",
        "opac-desert-spheroids": "desert_spheroids",
    }
    for family, species in expected.items():
        assert mod.aerosol_block(family, 0.2) == [
            "aerosol_default",
            "aerosol_species_library OPAC",
            f"aerosol_species_file {species}",
            "aerosol_set_tau_at_wvl 550 0.20000000",
        ]
    assert mod.aerosol_block("native-rural-ss", 0.2) == [
        "aerosol_default",
        "aerosol_haze 1",
        "aerosol_vulcan 1",
        "aerosol_season 1",
        "aerosol_set_tau_at_wvl 550 0.20000000",
    ]


def test_rendered_non_native_input_matches_direct_transport_contract(tmp_path: Path):
    mod = load_candidate()
    atmosphere = tmp_path / "afglus.dat"
    atmosphere.write_text(
        "120 1\n100 1\n80 1\n60 1\n40 1\n20 1\n10 1\n5 1\n2 1\n1 1\n0 1\n",
        encoding="utf-8",
    )
    grid = tmp_path / "wavelength-1nm.dat"
    grid.write_text("\n".join(str(w) for w in range(380, 781)) + "\n", encoding="ascii")
    text = mod.render_uvspec_input(
        family="opac-maritime-clean",
        data_dir=tmp_path,
        atmosphere_file=atmosphere,
        wavelength_grid_file=grid,
        target_altitude_deg=12.666667,
        observer_elevation_m=875,
        aod550=0.166666667,
    )
    assert "wavelength 380 780" in text
    assert "mol_abs_param crs" in text
    assert "zout 0.000000" in text
    assert "albedo 0.15000000" in text
    assert "aerosol_species_library OPAC" in text
    assert "aerosol_species_file maritime_clean" in text
    assert "aerosol_set_tau_at_wvl 550 0.16666667" in text
    assert "rte_solver sdisort" in text
    assert "sdisort nscat 1" in text
    assert "output_quantity transmittance" in text
    assert "output_user lambda edir" in text
    assert "rte_solver mystic" not in text.lower()
    assert "mc_" not in text.lower()
    assert "angstrom" not in text.lower()


def test_native_rebuild_is_refused_by_default():
    mod = load_candidate()
    with pytest.raises(mod.CandidateRefusal):
        mod.validate_case(
            family="native-rural-ss",
            target_altitude_deg=20,
            observer_elevation_m=0,
            aod550=0.1,
        )


def test_source_contains_no_solver_invocation_surface():
    source = CANDIDATE.read_text(encoding="utf-8")
    assert "import subprocess" not in source
    assert "subprocess." not in source
    assert "find_uvspec" not in source
    assert "run_reference(" not in source
    assert "UVSPEC" not in source
