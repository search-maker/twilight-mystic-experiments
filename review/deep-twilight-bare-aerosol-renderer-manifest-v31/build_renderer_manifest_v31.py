#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
from fractions import Fraction
from pathlib import Path
from typing import Any

STAGE_ID = "deep-twilight-bare-aerosol-renderer-manifest-v31"
EXPECTED_NLYR = 49
EXPECTED_N_CAOTH = 2
EXPECTED_AEROSOL_ROW = 1
EXPECTED_SELECTOR = 2
EXPECTED_UVSPEC_SHA256 = "2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3"
EXPECTED_ROW_HASHES = {
    "dt_s": "3d6cd24f5ae073b9db0a0b77e40490c57efaab939415c8b7daa58ddfe1f8c857",
    "om_s": "f844343f6a95888185b7a9a8668c26c939864e318aee866ef377ee9c4df3ed3f",
    "g1_s": "d9d522e6b36ec7e0afe398548931e22561f59dc58e1880f1ca36c2dda85ad736",
    "g2_s": "d904e1f1e028ba9058a128a6fd724f0f9892ae8fe49c8f7dc2613183f7f8bbca",
    "f_s": "3d005be8a47ccd804feedf9feeadc6d6375f10a65bc986ebce0fb38612fa635f",
    "ds_s": "d904e1f1e028ba9058a128a6fd724f0f9892ae8fe49c8f7dc2613183f7f8bbca",
}
EXPECTED_ZPROF_HASH = "e22942aa9f35b08d6d0c8a0c6872d7ae09d5492bb8119cb446178a2bd59132a5"


class ManifestError(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_raw_hex(raw_hex: str, count: int) -> tuple[bytes, list[int]]:
    raw = bytes.fromhex(raw_hex)
    if len(raw) != 4 * count:
        raise ManifestError(f"float32 raw byte count mismatch: {len(raw)} != {4*count}")
    return raw, list(struct.unpack("<" + "I" * count, raw))


def f32_word_fraction(word: int) -> Fraction | None:
    sign = -1 if (word >> 31) else 1
    exponent = (word >> 23) & 0xFF
    mantissa = word & 0x7FFFFF
    if exponent == 0xFF:
        return None
    if exponent == 0:
        if mantissa == 0:
            return Fraction(0, 1)
        value = Fraction(mantissa, 1 << 23) * Fraction(2) ** (-126)
    else:
        value = Fraction((1 << 23) + mantissa, 1 << 23) * Fraction(2) ** (exponent - 127)
    return sign * value


def f32_word_float(word: int) -> float:
    return struct.unpack("<f", struct.pack("<I", word))[0]


def zero_encoding(word: int) -> str | None:
    if word == 0x00000000:
        return "+0"
    if word == 0x80000000:
        return "-0"
    return None


def vector_from_capture(capture: dict[str, Any], name: str) -> dict[str, Any]:
    row = capture["tables"][name]["rows"][EXPECTED_AEROSOL_ROW]
    raw, words = parse_raw_hex(row["rawBytesHex"], EXPECTED_NLYR)
    digest = sha256_bytes(raw)
    if digest != row["rawSha256"] or digest != EXPECTED_ROW_HASHES[name]:
        raise ManifestError(f"{name} raw hash mismatch: {digest}")
    return {"raw": raw, "words": words, "sha256": digest}


def hg_phase_per_sr(mu: float, g: float) -> float:
    if not (-1.0 <= mu <= 1.0 and -1.0 < g < 1.0):
        raise ManifestError("HG argument out of range")
    denom = (1.0 + g * g - 2.0 * g * mu) ** 1.5
    return (1.0 - g * g) / (4.0 * math.pi * denom)


def simpson(fn, a: float, b: float, intervals: int = 20000) -> float:
    if intervals <= 0 or intervals % 2:
        raise ManifestError("Simpson intervals must be positive/even")
    h = (b - a) / intervals
    total = fn(a) + fn(b)
    for i in range(1, intervals):
        total += (4.0 if i % 2 else 2.0) * fn(a + i * h)
    return total * h / 3.0


def hg_reference_report(g_values: list[float]) -> dict[str, Any]:
    cases = []
    for g in g_values:
        norm = 2.0 * math.pi * simpson(lambda mu: hg_phase_per_sr(mu, g), -1.0, 1.0)
        mean_mu = 2.0 * math.pi * simpson(lambda mu: mu * hg_phase_per_sr(mu, g), -1.0, 1.0)
        forward = hg_phase_per_sr(1.0, g)
        sideways = hg_phase_per_sr(0.0, g)
        backward = hg_phase_per_sr(-1.0, g)
        if abs(norm - 1.0) > 2e-9:
            raise ManifestError(f"HG normalization failure g={g}: {norm}")
        if abs(mean_mu - g) > 2e-9:
            raise ManifestError(f"HG first-moment failure g={g}: {mean_mu}")
        if g > 0 and not (forward > sideways > backward > 0.0):
            raise ManifestError(f"HG angular-order failure g={g}")
        if g == 0.0:
            iso = 1.0 / (4.0 * math.pi)
            if max(abs(forward - iso), abs(sideways - iso), abs(backward - iso)) > 1e-15:
                raise ManifestError("HG g=0 isotropic failure")
        cases.append({
            "g": g,
            "solidAngleNormalizationNumeric": norm,
            "firstMomentNumeric": mean_mu,
            "phasePerSr": {"muMinus1": backward, "mu0": sideways, "muPlus1": forward},
        })
    return {
        "status": "PASS_DETERMINISTIC_HG1_ANALYTIC_REFERENCES",
        "definition": "P(mu)=(1-g^2)/(4*pi*(1+g^2-2*g*mu)^(3/2))",
        "solidAngleNormalizationTarget": 1.0,
        "firstMomentTarget": "g",
        "cases": cases,
    }


def build(v2: dict[str, Any], v24: dict[str, Any], v30: dict[str, Any], v30_raw: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    if v2.get("status") not in {"EXACT_MYSTIC_ENTRY_RAW_OPTICAL_STATE_CAPTURED", "PASS_EXACT_MYSTIC_ENTRY_RAW_OPTICAL_STATE_ACCESSIBLE"}:
        raise ManifestError("V2 capture status mismatch")
    if v2.get("nlyr") != EXPECTED_NLYR or v2.get("nCaoth") != EXPECTED_N_CAOTH:
        raise ManifestError("V2 dimensions mismatch")
    if v2.get("mysticBodyExecuted") is not False or v2.get("photonTraced") is not False:
        raise ManifestError("V2 was not setup-only")
    if v24.get("deltaSemanticStatus") != "PASS_EXACT_BINARY":
        raise ManifestError("V24B delta semantic status mismatch")
    if v30.get("status") != "PASS_EXACT_RUNTIME_FINAL_AEROSOL_SELECTOR_CAPTURED" or v30.get("finalSelector") != EXPECTED_SELECTOR:
        raise ManifestError("V30 final selector mismatch")
    if v30.get("selectedPhaseSemantics") != "HG1":
        raise ManifestError("V30 phase semantic mismatch")
    if v30_raw.get("randomDrawGuardViolated") is not False or v30_raw.get("photonTraced") is not False:
        raise ManifestError("V30 random/photon guard mismatch")
    if v30_raw.get("selectorCandidate") != EXPECTED_SELECTOR or v30_raw.get("selectorCandidateSourceValue") != EXPECTED_SELECTOR:
        raise ManifestError("V30 raw selector mismatch")

    vectors = {name: vector_from_capture(v2, name) for name in EXPECTED_ROW_HASHES}
    zraw, zwords = parse_raw_hex(v2["zprof"]["rawBytesHex"], EXPECTED_NLYR + 1)
    if sha256_bytes(zraw) != v2["zprof"]["rawSha256"] or sha256_bytes(zraw) != EXPECTED_ZPROF_HASH:
        raise ManifestError("zprof raw hash mismatch")

    if any(word != 0x00000000 for word in vectors["ds_s"]["words"]):
        raise ManifestError("frozen aerosol ds_s is not exact +0 in every layer")
    if any(word != 0x00000000 for word in vectors["g2_s"]["words"]):
        raise ManifestError("frozen aerosol g2_s is not exact +0 in every layer")
    if any(word != 0x3F800000 for word in vectors["f_s"]["words"]):
        raise ManifestError("frozen aerosol f_s is not exact +1 in every layer")

    zfractions = [f32_word_fraction(w) for w in zwords]
    if any(v is None for v in zfractions):
        raise ManifestError("non-finite zprof")
    zvals = [v for v in zfractions if v is not None]
    if zvals[0] != 0 or zvals[-1] != 120 or any(not (a < b) for a, b in zip(zvals, zvals[1:])):
        raise ManifestError("unexpected zprof ordering/endpoints")

    dt_words = vectors["dt_s"]["words"]
    om_words = vectors["om_s"]["words"]
    g1_words = vectors["g1_s"]["words"]
    tau_fractions: list[Fraction] = []
    layers = []
    active_g = []
    for i in range(EXPECTED_NLYR):
        tau = f32_word_fraction(dt_words[i])
        ssa = f32_word_fraction(om_words[i])
        g = f32_word_fraction(g1_words[i])
        if tau is None or ssa is None or g is None:
            raise ManifestError(f"non-finite optical property at layer {i}")
        if tau < 0:
            raise ManifestError(f"negative nonzero aerosol tau at layer {i}")
        if not (Fraction(0) <= ssa <= Fraction(1)):
            raise ManifestError(f"SSA outside [0,1] at layer {i}")
        if not (Fraction(-1) <= g <= Fraction(1)):
            raise ManifestError(f"g outside [-1,1] at layer {i}")
        tau_fractions.append(tau)
        if dt_words[i] not in (0x00000000, 0x80000000) and g1_words[i] not in (0x00000000, 0x80000000):
            active_g.append(f32_word_float(g1_words[i]))
        layers.append({
            "nativeLayerIndex": i,
            "zLowerRawWord": f"0x{zwords[i]:08x}",
            "zUpperRawWord": f"0x{zwords[i+1]:08x}",
            "tauRawWord": f"0x{dt_words[i]:08x}",
            "ssaRawWord": f"0x{om_words[i]:08x}",
            "gRawWord": f"0x{g1_words[i]:08x}",
            "deltaScaleRawWord": "0x00000000",
            "tauEffectiveRawWord": f"0x{dt_words[i]:08x}",
            "ssaEffectiveRawWord": f"0x{om_words[i]:08x}",
            "phaseModel": "HG1",
            "tauZeroEncoding": zero_encoding(dt_words[i]),
            "ssaZeroEncoding": zero_encoding(om_words[i]),
            "gZeroEncoding": zero_encoding(g1_words[i]),
        })

    aod = sum(tau_fractions, Fraction(0))
    if not (Fraction(149999, 1000000) < aod < Fraction(150001, 1000000)):
        raise ManifestError(f"captured AOD sum outside strict frozen tolerance: {aod}")

    ref_g = [0.0, 0.5]
    if active_g:
        ref_g.extend([min(active_g), max(active_g)])
    unique_ref_g: list[float] = []
    for value in ref_g:
        if not any(abs(value - prior) < 1e-15 for prior in unique_ref_g):
            unique_ref_g.append(value)
    hg_report = hg_reference_report(unique_ref_g)

    manifest = {
        "schemaVersion": 31,
        "stageId": STAGE_ID,
        "status": "PASS_EXACT_BARE_AEROSOL_RENDERER_MANIFEST",
        "sourceRuntime": {
            "uvspecSha256": EXPECTED_UVSPEC_SHA256,
            "nlyr": EXPECTED_NLYR,
            "nCaoth": EXPECTED_N_CAOTH,
            "aerosolRowIndex": EXPECTED_AEROSOL_ROW,
            "finalAerosolSelector": EXPECTED_SELECTOR,
            "phaseModel": "HG1",
        },
        "translation": {
            "nativeLayerOrderPreserved": True,
            "layerLevelBinding": "layer i is emitted with captured native zprof[i] and zprof[i+1] without reordering",
            "deltaTransform": "tau_eff=dt*(1-om*ds); ssa_eff=om*(1-ds)/(1-om*ds)",
            "deltaScaleAllExactPositiveZero": True,
            "deltaTransformReducesToRawBitIdentity": True,
            "activePhaseParameter": "g1_s",
            "g2AndFNotSelectedByFrozenSampler": True,
            "rawFloat32BitsAuthoritative": True,
            "decimalDecodesAuthoritative": False,
            "signedZeroPreserved": True,
            "epsilonSubstitutionUsed": False,
        },
        "rawHashes": {**{name: vectors[name]["sha256"] for name in EXPECTED_ROW_HASHES}, "zprof": sha256_bytes(zraw)},
        "capturedAodExactRational": {"numerator": aod.numerator, "denominator": aod.denominator},
        "capturedAodFloatAuditOnly": float(aod),
        "layers": layers,
        "hgReferenceStatus": hg_report["status"],
        "rendererParityAuthorized": False,
        "korkinGateAuthorized": False,
        "deepScienceAuthorized": False,
        "levelBChanged": False,
        "protectedResultOpened": False,
        "taylorOrJerusalemUsed": False,
    }
    return manifest, hg_report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--v2", required=True, type=Path)
    ap.add_argument("--v24b", required=True, type=Path)
    ap.add_argument("--v30", required=True, type=Path)
    ap.add_argument("--v30-raw", required=True, type=Path)
    ap.add_argument("--output-dir", required=True, type=Path)
    ns = ap.parse_args()
    manifest, hg = build(load_json(ns.v2), load_json(ns.v24b), load_json(ns.v30), load_json(ns.v30_raw))
    ns.output_dir.mkdir(parents=True, exist_ok=True)
    dump_json(ns.output_dir / "renderer-manifest-v31.json", manifest)
    dump_json(ns.output_dir / "hg1-reference-report-v31.json", hg)
    print(json.dumps({"status": manifest["status"], "aod": manifest["capturedAodFloatAuditOnly"], "hgReferenceStatus": hg["status"], "layerCount": len(manifest["layers"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
