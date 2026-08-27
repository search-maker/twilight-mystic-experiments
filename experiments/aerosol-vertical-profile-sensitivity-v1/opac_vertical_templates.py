from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Iterable

STAGE_ID = "aerosol-vertical-profile-sensitivity-v1"
FREE_TROPOSPHERE_TAU550 = 0.013
STRATOSPHERE_TAU550 = 0.005
FREE_TROPOSPHERE_TOP_KM = 12.0
FREE_TROPOSPHERE_SCALE_HEIGHT_KM = 8.0
STRATOSPHERE_TOP_KM = 35.0
STRATOSPHERE_SCALE_HEIGHT_KM = 99.0

# Hess, Koepke & Schult (1998), OPAC Tables 3 and 5.
# totalTau550 includes the standard free-troposphere and stratospheric background
# for each boundary-layer aerosol type. The first-layer optical-depth share is
# therefore totalTau550 - 0.013 - 0.005.
PROFILE_STATES = {
    "opac-profile-continental-average": {
        "sourceAerosolType": "Continental average",
        "totalTau550": 0.151,
        "firstLayerTopKm": 2.0,
        "firstLayerScaleHeightKm": 8.0,
    },
    "opac-profile-maritime-clean": {
        "sourceAerosolType": "Maritime clean",
        "totalTau550": 0.096,
        "firstLayerTopKm": 2.0,
        "firstLayerScaleHeightKm": 1.0,
    },
    "opac-profile-desert": {
        "sourceAerosolType": "Desert",
        "totalTau550": 0.286,
        "firstLayerTopKm": 6.0,
        "firstLayerScaleHeightKm": 2.0,
    },
    "opac-profile-arctic": {
        "sourceAerosolType": "Arctic",
        "totalTau550": 0.063,
        "firstLayerTopKm": 2.0,
        "firstLayerScaleHeightKm": 99.0,
    },
    "opac-profile-antarctic": {
        "sourceAerosolType": "Antarctic",
        "totalTau550": 0.072,
        "firstLayerTopKm": 10.0,
        "firstLayerScaleHeightKm": 8.0,
    },
}

REFERENCE_STATE_ID = "opac-profile-continental-average"


class VerticalTemplateError(ValueError):
    pass


def _transport_module():
    root = Path(__file__).resolve().parents[2]
    path = root / "review" / "aerosol-vertical-profile-transport-v1" / "profile_transport.py"
    spec = importlib.util.spec_from_file_location("aerosol_vertical_profile_transport_v1", path)
    if spec is None or spec.loader is None:
        raise VerticalTemplateError(f"cannot import merged profile transport foundation: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _finite(value, name: str) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise VerticalTemplateError(f"{name} must be numeric") from exc
    if not math.isfinite(out):
        raise VerticalTemplateError(f"{name} must be finite")
    return out


def _exp_integral(lo_km: float, hi_km: float, scale_height_km: float) -> float:
    if hi_km <= lo_km:
        return 0.0
    z = _finite(scale_height_km, "scale height")
    if z <= 0:
        raise VerticalTemplateError("scale height must be >0")
    return z * (math.exp(-lo_km / z) - math.exp(-hi_km / z))


def _normalized_exp_share(
    lo_km: float,
    hi_km: float,
    layer_lo_km: float,
    layer_hi_km: float,
    scale_height_km: float,
) -> float:
    overlap_lo = max(lo_km, layer_lo_km)
    overlap_hi = min(hi_km, layer_hi_km)
    if overlap_hi <= overlap_lo:
        return 0.0
    denom = _exp_integral(layer_lo_km, layer_hi_km, scale_height_km)
    if not denom > 0:
        raise VerticalTemplateError("profile component has zero normalization integral")
    return _exp_integral(overlap_lo, overlap_hi, scale_height_km) / denom


def state_component_tau550(state_id: str) -> dict[str, float]:
    try:
        state = PROFILE_STATES[state_id]
    except KeyError as exc:
        raise VerticalTemplateError(f"unknown vertical state: {state_id}") from exc
    total = float(state["totalTau550"])
    first = total - FREE_TROPOSPHERE_TAU550 - STRATOSPHERE_TAU550
    if not first > 0:
        raise VerticalTemplateError(f"nonpositive first-layer tau for {state_id}")
    return {
        "firstLayer": first,
        "freeTroposphere": FREE_TROPOSPHERE_TAU550,
        "stratosphere": STRATOSPHERE_TAU550,
        "total": total,
    }


def layer_tau_fractions(target_edges_km: Iterable[float], state_id: str) -> tuple[float, ...]:
    edges = tuple(_finite(v, "target edge") for v in target_edges_km)
    if len(edges) < 2 or any(b <= a for a, b in zip(edges, edges[1:])):
        raise VerticalTemplateError("target edges must be strictly increasing")
    if abs(edges[0]) > 1e-12:
        raise VerticalTemplateError("v1 preregistration is sea-level only; target grid must begin at 0 km")
    if edges[-1] < STRATOSPHERE_TOP_KM:
        raise VerticalTemplateError("target grid must extend to at least 35 km")
    state = PROFILE_STATES.get(state_id)
    if state is None:
        raise VerticalTemplateError(f"unknown vertical state: {state_id}")
    h = float(state["firstLayerTopKm"])
    z_first = float(state["firstLayerScaleHeightKm"])
    if not 0 < h <= FREE_TROPOSPHERE_TOP_KM:
        raise VerticalTemplateError("first-layer top outside [0,12] km")
    tau = state_component_tau550(state_id)

    raw = []
    for lo, hi in zip(edges, edges[1:]):
        first = tau["firstLayer"] * _normalized_exp_share(lo, hi, 0.0, h, z_first)
        free = tau["freeTroposphere"] * _normalized_exp_share(
            lo, hi, h, FREE_TROPOSPHERE_TOP_KM, FREE_TROPOSPHERE_SCALE_HEIGHT_KM
        )
        strat = tau["stratosphere"] * _normalized_exp_share(
            lo, hi, FREE_TROPOSPHERE_TOP_KM, STRATOSPHERE_TOP_KM, STRATOSPHERE_SCALE_HEIGHT_KM
        )
        raw.append(first + free + strat)
    total_raw = math.fsum(raw)
    if abs(total_raw - tau["total"]) > 5e-13:
        raise VerticalTemplateError(
            f"integrated OPAC template does not reproduce source total tau: {state_id}: {total_raw} vs {tau['total']}"
        )
    fractions = tuple(value / total_raw for value in raw)
    if abs(math.fsum(fractions) - 1.0) > 1e-12:
        raise VerticalTemplateError("normalized vertical fractions do not sum to one")
    if any(value < 0 for value in fractions):
        raise VerticalTemplateError("negative layer tau fraction")
    return fractions


def source_identity(state_id: str) -> dict:
    state = PROFILE_STATES.get(state_id)
    if state is None:
        raise VerticalTemplateError(f"unknown vertical state: {state_id}")
    return {
        "stageId": STAGE_ID,
        "stateId": state_id,
        "source": "Hess, Koepke & Schult 1998 OPAC Tables 3 and 5",
        "doi": "10.1175/1520-0477(1998)079<0831:OPOAAC>2.0.CO;2",
        "construction": {
            **state,
            "firstLayerTau550": state_component_tau550(state_id)["firstLayer"],
            "freeTroposphereTau550": FREE_TROPOSPHERE_TAU550,
            "freeTroposphereTopKm": FREE_TROPOSPHERE_TOP_KM,
            "freeTroposphereScaleHeightKm": FREE_TROPOSPHERE_SCALE_HEIGHT_KM,
            "stratosphereTau550": STRATOSPHERE_TAU550,
            "stratosphereBottomKm": FREE_TROPOSPHERE_TOP_KM,
            "stratosphereTopKm": STRATOSPHERE_TOP_KM,
            "stratosphereScaleHeightKm": STRATOSPHERE_SCALE_HEIGHT_KM,
        },
        "scientificInterpretation": "controlled vertical-template sensitivity; optical aerosol family is held separately fixed",
    }


def build_remapped_profile(target_edges_km: Iterable[float], state_id: str):
    edges = tuple(_finite(v, "target edge") for v in target_edges_km)
    fractions = layer_tau_fractions(edges, state_id)
    identity = source_identity(state_id)
    raw = json.dumps(identity, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    fingerprint = hashlib.sha256(raw).hexdigest()
    pt = _transport_module()
    return pt.RemappedProfile(
        target_edges_m=tuple(v * 1000.0 for v in edges),
        layer_tau_fractions=fractions,
        transported_integral=state_component_tau550(state_id)["total"],
        outside_below_policy="reject",
        outside_above_policy="zero-above-35km-by-source-definition",
        source_fingerprint_sha256=fingerprint,
    )


def render_libradtran_tau(target_edges_km: Iterable[float], state_id: str) -> str:
    pt = _transport_module()
    profile = build_remapped_profile(target_edges_km, state_id)
    return pt.render_libradtran_aerosol_tau(
        profile,
        header=f"{STAGE_ID} {state_id}; normalized OPAC-derived vertical template only; fixed optical family and AOD are external",
    )
