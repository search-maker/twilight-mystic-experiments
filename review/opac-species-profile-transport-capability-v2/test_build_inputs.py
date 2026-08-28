from __future__ import annotations

import importlib.util
import math
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODULE_PATH = HERE / "build_inputs.py"
spec = importlib.util.spec_from_file_location("opac_species_profile_capability_v2", MODULE_PATH)
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)


def main() -> None:
    assert m.STAGE_ID == "opac-species-profile-transport-capability-v2"
    assert m.SPECIES == "INSO"
    assert m.AOD550 == 0.10
    assert m.MYSTIC_PHOTONS == 500_000
    assert m.MYSTIC_SEED == 730_194_613
    assert (m.WAVELENGTH_START_NM, m.WAVELENGTH_STOP_NM) == (540, 560)

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        repo = root / "repo"
        data = root / "data"
        (repo / "experiments/aerosol-family-challenge-v2-r8").mkdir(parents=True)
        (repo / "experiments/aerosol-family-challenge-v2-r8/wavelength-grid-1nm.dat").write_text("540\n550\n560\n")
        (data / "atmmod").mkdir(parents=True)
        (data / "solar_flux").mkdir()
        atmosphere = data / "atmmod/afglus.dat"
        atmosphere.write_text("10 1\n8 1\n6 1\n4 1\n2 1\n1 1\n0 1\n")
        (data / "solar_flux/atlas_plus_modtran").write_text("fixture\n")

        heights = m.parse_afgl_heights_km(atmosphere)
        low = m.synthetic_density_shape(heights, "low")
        high = m.synthetic_density_shape(heights, "high")
        assert low != high
        assert low[-1] > low[0]
        high_peak_z = heights[max(range(len(high)), key=lambda i: high[i])]
        assert high_peak_z == 8.0
        assert math.isclose(m._trapezoid_integral_descending(heights, low), 1.0e-6, rel_tol=1e-12)
        assert math.isclose(m._trapezoid_integral_descending(heights, high), 1.0e-6, rel_tol=1e-12)

        out = root / "bundle"
        meta = m.write_bundle(atmosphere, data, repo, out)
        assert meta["scientificOrdinalAllocated"] is False
        assert meta["taylorOrJerusalemUsed"] is False
        assert meta["productionAuthorized"] is False
        assert set(meta["files"]) == {
            "inputs/disort-high.inp",
            "inputs/disort-low.inp",
            "inputs/mystic-high.inp",
            "inputs/mystic-low.inp",
            "profiles/synthetic-high-inso.dat",
            "profiles/synthetic-low-inso.dat",
        }
        for state in ("low", "high"):
            disort = (out / f"inputs/disort-{state}.inp").read_text()
            mystic = (out / f"inputs/mystic-{state}.inp").read_text()
            assert "aerosol_species_library OPAC" in disort
            assert "aerosol_species_file " in disort and " INSO" in disort
            assert "aerosol_file tau" not in disort
            assert "aerosol_file tau" not in mystic
            assert "aerosol_set_tau_at_wvl 550 0.100000" in mystic
            assert "rte_solver disort" in disort
            assert "rte_solver mystic" in mystic
            assert "mc_spherical 1D" in mystic
            assert "mc_photons 500000" in mystic
            assert "mc_randomseed 730194613" in mystic

        low_mystic = (out / "inputs/mystic-low.inp").read_text()
        high_mystic = (out / "inputs/mystic-high.inp").read_text()
        # The seed/numerical surface is paired; the profile path and basename are intentionally different.
        for required in (
            "sza 96.000000",
            "wavelength 540 560",
            "umu -0.50000000",
            "phi 90.000000",
            "mc_randomseed 730194613",
        ):
            assert required in low_mystic and required in high_mystic

    source = MODULE_PATH.read_text()
    sanitized = source.replace("taylorOrJerusalemUsed", "")
    assert "taylor" not in sanitized.lower()
    assert "jerusalem" not in sanitized.lower()
    assert '"taylorOrJerusalemUsed": False' in source
    assert "aerosol_file tau" in source  # only in an explicit refusal string/test guard
    assert "corrected capability must not combine aerosol_file with aerosol_species_file" in source
    print("OPAC species-profile transport capability v2 static tests: PASS")


if __name__ == "__main__":
    main()
