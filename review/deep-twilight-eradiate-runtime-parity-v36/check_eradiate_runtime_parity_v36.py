#!/usr/bin/env python3
import argparse
import hashlib
import json
import math
import pathlib
import struct
import zipfile

import numpy as np

EXPECTED_ARTIFACT_SHA256 = "4b02b09a3b83a55ca5f9deef07397f0d4b2cbcb8b1c971874652a10b91dbb2b8"
EXPECTED_ERADIATE_VERSION = "1.0.1"
EXPECTED_SOURCE_AOD = 0.15000000687427928
EXPECTED_KERNEL_AOD = 0.15000000686990067
EXPECTED_AOD_ERROR = -4.378608586819155e-12
EXPECTED_MAX_LAYER_ABS = 3.637978807091713e-12
EXPECTED_MAX_LAYER_REL = 4.76486714788013e-08
EXPECTED_CHORD_BOUND = 1.2394739747377028e-09
EXPECTED_TRANSMISSION_BOUND = 1.2394739755058506e-09
EARTH_RADIUS_KM = 6378.1
STEP_KM = 0.5


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def f32_from_word(word: str) -> float:
    return struct.unpack(">f", struct.pack(">I", int(word, 16)))[0]


def word_from_f32(value: float) -> str:
    return f"0x{struct.unpack('>I', struct.pack('>f', np.float32(value)))[0]:08x}"


def close(a: float, b: float, *, abs_tol: float) -> bool:
    return math.isclose(a, b, rel_tol=0.0, abs_tol=abs_tol)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--artifact", required=True)
    p.add_argument("--report", required=True)
    args = p.parse_args()

    artifact = pathlib.Path(args.artifact)
    report_path = pathlib.Path(args.report)
    artifact_sha = sha256_file(artifact)
    assert artifact_sha == EXPECTED_ARTIFACT_SHA256, (artifact_sha, EXPECTED_ARTIFACT_SHA256)

    with zipfile.ZipFile(artifact) as zf:
        manifest = json.loads(zf.read("render/renderer-manifest-v31.json"))

    assert len(manifest["layers"]) == 49
    assert manifest["rendererParityAuthorized"] is False
    assert manifest["deepScienceAuthorized"] is False
    assert manifest["korkinGateAuthorized"] is False

    layers = []
    for row in manifest["layers"]:
        assert row["phaseModel"] == "HG1"
        assert row["deltaScaleRawWord"] == "0x00000000"
        assert row["tauEffectiveRawWord"].lower() == row["tauRawWord"].lower()
        assert row["ssaEffectiveRawWord"].lower() == row["ssaRawWord"].lower()
        tau = f32_from_word(row["tauRawWord"])
        ssa = f32_from_word(row["ssaRawWord"])
        g = f32_from_word(row["gRawWord"])
        zlo = f32_from_word(row["zLowerRawWord"])
        zhi = f32_from_word(row["zUpperRawWord"])
        assert zhi > zlo
        assert close(zlo * 2.0, round(zlo * 2.0), abs_tol=0.0)
        assert close(zhi * 2.0, round(zhi * 2.0), abs_tol=0.0)
        layers.append(
            {
                "i": row["nativeLayerIndex"],
                "tau": tau,
                "ssa": ssa,
                "g": g,
                "zlo": zlo,
                "zhi": zhi,
                "tau_word": row["tauRawWord"].lower(),
                "ssa_word": row["ssaRawWord"].lower(),
                "g_word": row["gRawWord"].lower(),
            }
        )

    widths = [x["zhi"] - x["zlo"] for x in layers]
    width_counts = {str(w): widths.count(w) for w in sorted(set(widths))}
    assert width_counts == {"1.0": 25, "2.5": 10, "5.0": 14}

    levels = np.arange(0.0, 120.0 + STEP_KM, STEP_KM, dtype=np.float64)
    assert levels.size == 241
    sigma32 = np.full(240, np.nan, dtype=np.float32)
    ssa32 = np.full(240, np.nan, dtype=np.float32)
    g32 = np.full(240, np.nan, dtype=np.float32)
    source_index = np.full(240, -1, dtype=np.int32)

    layer_abs_errors = []
    layer_rel_errors = []
    exact_integrated_count = 0
    chord_bound = 0.0
    source_aod = 0.0

    active_g_words = sorted({x["g_word"] for x in layers if x["tau"] != 0.0})
    g_component_index = {word: i for i, word in enumerate(active_g_words)}
    one_hot = np.zeros((len(active_g_words), 240), dtype=np.float64)

    for x in layers:
        dz = x["zhi"] - x["zlo"]
        start = int(round(x["zlo"] / STEP_KM))
        stop = int(round(x["zhi"] / STEP_KM))
        assert stop > start
        assert close(start * STEP_KM, x["zlo"], abs_tol=0.0)
        assert close(stop * STEP_KM, x["zhi"], abs_tol=0.0)
        sigma64 = x["tau"] / dz
        sigma_kernel = np.float32(sigma64)
        sigma32[start:stop] = sigma_kernel
        ssa32[start:stop] = np.float32(x["ssa"])
        g32[start:stop] = np.float32(x["g"])
        source_index[start:stop] = x["i"]

        assert word_from_f32(np.float32(x["ssa"])) == x["ssa_word"]
        assert word_from_f32(np.float32(x["g"])) == x["g_word"]

        if x["tau"] == 0.0:
            assert x["tau_word"] in {"0x00000000", "0x80000000"}
            assert float(sigma_kernel) == 0.0
        else:
            one_hot[g_component_index[x["g_word"]], start:stop] = 1.0

        reconstructed_tau = float(sigma_kernel) * dz
        err = reconstructed_tau - x["tau"]
        layer_abs_errors.append(abs(err))
        layer_rel_errors.append(abs(err) / abs(x["tau"]) if x["tau"] != 0.0 else 0.0)
        if reconstructed_tau == x["tau"]:
            exact_integrated_count += 1
        source_aod += x["tau"]

        coeff_err = abs(float(sigma_kernel) - sigma64)
        max_shell_chord = 2.0 * math.sqrt((EARTH_RADIUS_KM + x["zhi"]) ** 2 - (EARTH_RADIUS_KM + x["zlo"]) ** 2)
        chord_bound += coeff_err * max_shell_chord

    assert not np.isnan(sigma32).any()
    assert not np.isnan(ssa32).any()
    assert not np.isnan(g32).any()
    assert (source_index >= 0).all()
    assert np.all(one_hot.sum(axis=0)[sigma32 != 0.0] == 1.0)
    assert np.all(one_hot.sum(axis=0)[sigma32 == 0.0] == 0.0)

    kernel_aod = float(np.sum(sigma32.astype(np.float64) * STEP_KM))
    aod_error = kernel_aod - source_aod
    max_layer_abs = max(layer_abs_errors)
    max_layer_rel = max(layer_rel_errors)
    transmission_bound = math.expm1(chord_bound)

    assert close(source_aod, EXPECTED_SOURCE_AOD, abs_tol=1e-18)
    assert close(kernel_aod, EXPECTED_KERNEL_AOD, abs_tol=1e-18)
    assert close(aod_error, EXPECTED_AOD_ERROR, abs_tol=1e-18)
    assert close(max_layer_abs, EXPECTED_MAX_LAYER_ABS, abs_tol=1e-18)
    assert close(max_layer_rel, EXPECTED_MAX_LAYER_REL, abs_tol=1e-20)
    assert exact_integrated_count == 32
    assert close(chord_bound, EXPECTED_CHORD_BOUND, abs_tol=1e-18)
    assert close(transmission_bound, EXPECTED_TRANSMISSION_BOUND, abs_tol=1e-18)

    # Runtime pin and no-render Eradiate/Mitsuba construction checks.
    import eradiate
    assert eradiate.__version__ == EXPECTED_ERADIATE_VERSION, eradiate.__version__
    eradiate.set_mode("mono_polarized")
    import mitsuba as mi
    from eradiate.scenes.geometry import SphericalShellGeometry
    from eradiate.scenes.phase import BlendPhaseFunction, HenyeyGreensteinPhaseFunction
    from eradiate.units import unit_registry as ureg

    geometry = SphericalShellGeometry(
        ground_altitude=0.0 * ureg.km,
        toa_altitude=120.0 * ureg.km,
        zgrid=levels * ureg.km,
    )
    assert geometry.zgrid.n_layers == 240
    assert close(geometry.planet_radius.m_as(ureg.km), EARTH_RADIUS_KM, abs_tol=0.0)

    # Exercise the exact kernel representation classes without loading a scene or rendering.
    sigma_grid = mi.VolumeGrid(sigma32.reshape(1, 1, -1))
    albedo_grid = mi.VolumeGrid(ssa32.reshape(1, 1, -1))
    assert sigma_grid is not None and albedo_grid is not None

    components = [
        HenyeyGreensteinPhaseFunction(g=f32_from_word(word)) for word in active_g_words
    ]
    blend = BlendPhaseFunction(components=components, weights=one_hot, geometry=geometry)
    assert blend.weights.shape == one_hot.shape
    assert np.array_equal(blend.weights, one_hot)
    template = blend.template
    serialized = json.dumps({k: str(v) for k, v in template.items()}, sort_keys=True)
    assert "sphericalcoordsvolume" in serialized
    assert "nearest" in serialized

    zero_rows = [x for x in layers if x["tau"] == 0.0]
    assert len(zero_rows) == 3
    assert all(x["tau_word"] == "0x80000000" for x in zero_rows)
    assert all(x["ssa_word"] == "0x00000000" for x in zero_rows)
    assert all(x["g_word"] == "0x00000000" for x in zero_rows)

    report = {
        "schema": "deep-twilight-eradiate-runtime-parity-v36-report",
        "classification": "PASS_ZERO_RESULT_RUNTIME_TRANSLATION_PARITY",
        "artifactSha256": artifact_sha,
        "eradiateVersion": eradiate.__version__,
        "mitsubaVariant": mi.variant(),
        "rendererExecuted": False,
        "sceneLoaded": False,
        "solverExecuted": False,
        "photonsTraced": 0,
        "sourceLayers": 49,
        "commonLatticeCells": 240,
        "uniqueActiveHgComponents": len(active_g_words),
        "sourceAod": source_aod,
        "kernelGridAod": kernel_aod,
        "aodSignedError": aod_error,
        "maxLayerAbsIntegratedTauError": max_layer_abs,
        "maxLayerRelIntegratedTauError": max_layer_rel,
        "exactIntegratedTauLayers": exact_integrated_count,
        "ssaFloat32WordRoundtripExact": True,
        "gFloat32WordRoundtripExact": True,
        "sourceZeroLayers": len(zero_rows),
        "sourceNegativeZeroTauWordsPreserved": True,
        "oneHotActiveCellsExact": True,
        "zeroScatteringCellsAllWeightsZero": True,
        "straightChordAbsTauErrorConservativeUpperBound": chord_bound,
        "directTransmissionRelativeErrorConservativeUpperBound": transmission_bound,
        "rendererParityRuntimeQAPassed": True,
        "korkinGateAuthorized": False,
        "deepScienceAuthorized": False,
        "protectedResultOpeningAuthorized": False,
        "levelBChangeAuthorized": False,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
