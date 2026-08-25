#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

MODEL_MEMBER_SHA256 = "0b850664584244abdc781f87ce9e5b89cdab28b08a2999612b155378cbe42d79"
REPRESENTATION_SHA256 = "2491ac91ed924f2ba69b37ea20f48d63f51d41146cd9fe50e0bd63bfb315a763"
MODEL_CANONICAL_SHA256 = "c4902eb3c2ba67b12dc4ef2b9cefb67c5963a6abc104708a73b2aab5dd0163b9"
SCALES = np.asarray([
    0.27729231126929754, 0.09054255337405856, 0.04362631407125976,
    0.00791831782256918, 0.0046149233253235545, 0.002441189933423995,
    0.0015868955715692872, 0.0008860617219488324, 0.0004930249648425277,
    0.00021007512113759737,
], dtype=np.float64)
AOD_MIN = 0.05
AOD_MAX = 0.40
GRID_COUNT = 1001
MAX_SUPPORT_DISTANCE = 0.60


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def physical(g: dict) -> np.ndarray:
    aod = float(g["aod550"])
    return np.asarray([
        (float(g["sunDepressionDeg"]) - 2.0) / 8.5,
        math.sin(math.radians(float(g["targetAltitudeDeg"]))),
        math.cos(math.radians(float(g["relativeAzimuthDeg"]))),
        float(g["observerElevationM"]) / 2500.0,
        math.log(aod / 0.05) / math.log(8.0),
    ], dtype=np.float64)


def idw_coordinates(g: dict) -> np.ndarray:
    return np.asarray([
        (float(g["sunDepressionDeg"]) - 2.0) / 8.5,
        (float(g["targetAltitudeDeg"]) - 5.0) / 75.0,
        (math.cos(math.radians(float(g["relativeAzimuthDeg"]))) + 1.0) / 2.0,
        float(g["observerElevationM"]) / 2500.0,
        (float(g["aod550"]) - 0.05) / 0.35,
    ], dtype=np.float64)


def basis(g: dict) -> np.ndarray:
    s, a, c, e, o = physical(g)
    return np.asarray([
        1.0, s, a, c, e, o, s*s, a*a, c*c, o*o,
        s*a, s*c, s*o, a*c, a*o, c*o,
    ], dtype=np.float64)


def idw_predict(coords: np.ndarray, targets: np.ndarray, query: np.ndarray, k: int, power: float) -> np.ndarray:
    distances = np.linalg.norm(coords - query[None, :], axis=1)
    order = np.argsort(distances, kind="stable")
    if float(distances[order[0]]) <= 1e-15:
        return targets[int(order[0])].copy()
    selected = order[:k]
    weights = 1.0 / np.power(distances[selected], power)
    return np.sum(targets[selected] * weights[:, None], axis=0) / np.sum(weights)


def predict_13(model: dict, g: dict) -> np.ndarray:
    base = model["baseModel"]
    primary = basis(g) @ np.asarray(base["primary"]["coefficients"], dtype=np.float64)
    shape = base["shape"]
    shape_prediction = idw_predict(
        np.asarray(shape["coordinates"], dtype=np.float64),
        np.asarray(shape["targets"], dtype=np.float64),
        idw_coordinates(g),
        int(shape["neighbors"]),
        float(shape["power"]),
    )
    prediction = np.concatenate([primary, shape_prediction])
    residual = idw_predict(
        np.asarray(model["residualCoordinates"], dtype=np.float64),
        np.asarray(model["residualTargets"], dtype=np.float64),
        idw_coordinates(g),
        int(model["residualNeighbors"]),
        float(model["residualPower"]),
    )
    prediction[:3] += float(model["residualShrinkage"]) * residual
    return prediction


def exact_support(model: dict, sun: float, alt: float, az: float, elev: float) -> dict:
    coords = np.asarray(model["residualCoordinates"], dtype=np.float64)
    fixed = np.asarray([
        (sun - 2.0) / 8.5,
        (alt - 5.0) / 75.0,
        (math.cos(math.radians(az)) + 1.0) / 2.0,
        elev / 2500.0,
    ], dtype=np.float64)
    constants = np.sum((coords[:, :4] - fixed[None, :]) ** 2, axis=1)
    centers = coords[:, 4]
    candidates = {0.0, 1.0}
    for i in range(len(centers)):
        for j in range(i + 1, len(centers)):
            denominator = 2.0 * (centers[j] - centers[i])
            if abs(denominator) <= 1e-15:
                continue
            x = -(constants[i] - constants[j] + centers[i]**2 - centers[j]**2) / denominator
            if 0.0 <= x <= 1.0:
                candidates.add(float(x))
    worst_distance = -1.0
    worst_x = 0.0
    for x in candidates:
        distance = float(np.sqrt(constants + (x - centers)**2).min())
        if distance > worst_distance:
            worst_distance, worst_x = distance, x
    return {
        "algorithmId": "EXACT_PAIRWISE_LOWER_ENVELOPE_V1",
        "candidateCount": len(candidates),
        "aod550Interval": [AOD_MIN, AOD_MAX],
        "maximumNearestFrozenTrainingDistance": worst_distance,
        "worstAod550": AOD_MIN + (AOD_MAX - AOD_MIN) * worst_x,
        "maximumAllowedDistance": MAX_SUPPORT_DISTANCE,
        "supportedAcrossEntireInterval": worst_distance <= MAX_SUPPORT_DISTANCE + 1e-12,
        "gridApproximationUsed": False,
        "targetRadianceUsed": False,
    }


def signed_miss(value: float, lo: float, hi: float) -> float:
    if lo <= value <= hi:
        return 0.0
    return value - lo if value < lo else value - hi


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--precontract", type=Path, required=True)
    parser.add_argument("--model-artifact", type=Path, required=True)
    parser.add_argument("--representation-npz", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if sha256(args.model_artifact) != MODEL_MEMBER_SHA256:
        raise ValueError("model artifact member SHA-256 drift")
    if sha256(args.representation_npz) != REPRESENTATION_SHA256:
        raise ValueError("spectral representation SHA-256 drift")
    artifact = json.loads(args.model_artifact.read_text(encoding="utf-8"))
    model = artifact["model"]
    if model.get("modelCanonicalSha256") != MODEL_CANONICAL_SHA256:
        raise ValueError("model canonical SHA-256 drift")
    dataset = json.loads(args.dataset.read_text(encoding="utf-8"))
    contract = json.loads(args.precontract.read_text(encoding="utf-8"))
    if contract.get("status") != "FROZEN_BEFORE_MODEL_EVALUATION_DIAGNOSTIC_ONLY_NOT_CERTIFIED":
        raise ValueError("Volz precontract not frozen")
    selection = dataset["frozenModelDomainSelection"]
    if selection.get("selectionFrozenBeforeModelEvaluation") is not True:
        raise ValueError("Volz selection not frozen")

    rep = np.load(args.representation_npz)
    wavelengths = rep["wavelength_nm"]
    exact = np.flatnonzero(wavelengths == 477.0)
    if len(exact) != 1:
        raise ValueError("exact 477 nm representation node required")
    index = int(exact[0])
    weights = rep["integration_weights"]
    gram_inverse = np.linalg.inv(weights @ weights.T)
    weight_column = weights[:, index]
    grand_477 = float(rep["grand_mean_nullspace_residual"][index])
    component_477 = rep["selected_nullspace_pca_components"][:, index]

    def radiance_477(sun: float, aod: float) -> float:
        g = {
            "sunDepressionDeg": sun,
            "targetAltitudeDeg": float(selection["targetAltitudeDeg"]),
            "relativeAzimuthDeg": float(selection["relativeAzimuthDeg"]),
            "observerElevationM": float(selection["observerElevationM"]),
            "aod550": aod,
        }
        prediction = predict_13(model, g)
        channels = np.exp(prediction[:3])
        normalized_channels = channels / channels[0]
        rowspace_477 = float(weight_column @ (gram_inverse @ normalized_channels))
        coefficients = prediction[3:] * SCALES
        residual_477 = grand_477 + float(coefficients @ component_477)
        return float(channels[0] * (rowspace_477 + residual_477))

    published = {int(row["sunDepressionDeg"]): float(row["log10GstOverFsunPlus8"]) for row in dataset["publishedRows"]}
    depths = [int(x) for x in selection["sunDepressionDeg"]]
    support = {
        d: exact_support(model, float(d), float(selection["targetAltitudeDeg"]),
                         float(selection["relativeAzimuthDeg"]), float(selection["observerElevationM"]))
        for d in depths
    }
    aod_grid = np.linspace(AOD_MIN, AOD_MAX, GRID_COUNT)
    radiance = {d: np.asarray([radiance_477(float(d), float(aod)) for aod in aod_grid]) for d in depths}

    def evaluate_pair(a: int, b: int) -> dict:
        observed = math.log(10.0) * (published[b] - published[a])
        rec = {
            "depthA": a,
            "depthB": b,
            "observedLogRatioBOverA": observed,
            "depthASupport": support[a],
            "depthBSupport": support[b],
        }
        if not (support[a]["supportedAcrossEntireInterval"] and support[b]["supportedAcrossEntireInterval"]):
            rec["status"] = "PAIR_UNSUPPORTED_ACROSS_FULL_AOD_INTERVAL"
            return rec
        if np.any(radiance[a] <= 0.0) or np.any(radiance[b] <= 0.0):
            rec["status"] = "FAIL_CLOSED_NONPOSITIVE_RECONSTRUCTED_RADIANCE"
            rec["nonpositiveGridPointCount"] = int(np.count_nonzero((radiance[a] <= 0.0) | (radiance[b] <= 0.0)))
            return rec
        ratios = np.log(radiance[b] / radiance[a])
        lo, hi = float(np.min(ratios)), float(np.max(ratios))
        miss = signed_miss(observed, lo, hi)
        rec.update({
            "status": "DENSE_GRID_NATIVE_SAME_AOD_477_SHAPE_DIAGNOSTIC_EVALUATED",
            "modelLogRatioGridRange": [lo, hi],
            "aodAtGridMinimum": float(aod_grid[int(np.argmin(ratios))]),
            "aodAtGridMaximum": float(aod_grid[int(np.argmax(ratios))]),
            "signedGridMissLog": miss,
            "absoluteGridMissLog": abs(miss),
            "absoluteGridMissMagEquivalent": abs(miss) * 2.5 / math.log(10.0),
            "observedInsideGridRange": miss == 0.0,
        })
        return rec

    anchor_pairs = [evaluate_pair(int(selection["anchorSunDepressionDeg"]), int(d)) for d in selection["anchorPairDepthsDeg"]]
    adjacent_pairs = [evaluate_pair(int(a), int(b)) for a, b in selection["adjacentPairsDeg"]]
    evaluated_adjacent = [p for p in adjacent_pairs if p["status"].endswith("EVALUATED")]
    output = {
        "schemaVersion": 1,
        "diagnosticId": "volz-1969-gst-477-native-spectral-shape-grid-v1",
        "claimClass": "PUBLISHED_OPEN_SPECTRAL_SHAPE_DIAGNOSTIC_NATIVE_ONLY_DENSE_GRID_NOT_CERTIFIED",
        "modelCanonicalSha256": MODEL_CANONICAL_SHA256,
        "wavelengthNm": 477.0,
        "aodGrid": {"minimum": AOD_MIN, "maximum": AOD_MAX, "count": GRID_COUNT, "sameAodWithinEachPair": True},
        "supportByDepth": {str(k): v for k, v in support.items()},
        "reconstructedRadiance477GridSummary": {
            str(d): {"minimum": float(np.min(radiance[d])), "maximum": float(np.max(radiance[d])), "nonpositiveCount": int(np.count_nonzero(radiance[d] <= 0.0))}
            for d in depths
        },
        "anchorPairs": anchor_pairs,
        "adjacentPairs": adjacent_pairs,
        "evaluatedAdjacentPairCount": len(evaluated_adjacent),
        "evaluatedAdjacentOutsideCount": sum(not p["observedInsideGridRange"] for p in evaluated_adjacent),
        "evaluatedAdjacentSignedMissNegativeCount": sum(p["signedGridMissLog"] < 0.0 for p in evaluated_adjacent),
        "interpretationBoundary": {
            "nativeAerosolOnly": True,
            "asivSpectralScenariosApplied": False,
            "absoluteRadianceComparisonAuthorized": False,
            "formalPassFailAuthorized": False,
            "continuousAodShapeCertificationAuthorized": False,
            "modelRetuningAuthorized": False,
            "strictModernRealSkyValidationClaimAuthorized": False,
        },
    }
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "evaluatedAdjacentPairCount": output["evaluatedAdjacentPairCount"],
        "evaluatedAdjacentOutsideCount": output["evaluatedAdjacentOutsideCount"],
        "evaluatedAdjacentSignedMissNegativeCount": output["evaluatedAdjacentSignedMissNegativeCount"],
        "supportedDepths": [d for d in depths if support[d]["supportedAcrossEntireInterval"]],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
