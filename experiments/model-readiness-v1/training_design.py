#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any

STAGE_ID = "twilight-surrogate-training-design-v1"
BASES = (2, 3, 5, 7, 11)
FEATURES = (
    "sunDepressionDeg",
    "targetAltitudeDeg",
    "relativeAzimuthDeg",
    "observerElevationM",
    "aod550",
)


class DesignError(RuntimeError):
    pass


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise DesignError(f"expected JSON object: {path}")
    return value


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def radical_inverse(index: int, base: int) -> float:
    result = 0.0
    factor = 1.0 / base
    while index:
        index, digit = divmod(index, base)
        result += digit * factor
        factor /= base
    return result


def load_policy(path: Path):
    spec = importlib.util.spec_from_file_location("twilight_importance_policy", path)
    if spec is None or spec.loader is None:
        raise DesignError(f"cannot load importance policy: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def finite(value: Any, name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise DesignError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise DesignError(f"{name} must be finite")
    return result


def validate_spec(spec: dict[str, Any]) -> None:
    required = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "proposalOnly": True,
        "scientificExecution": False,
        "observationValidationRequired": True,
        "blocksPerGeometry": 2,
    }
    stale = {key: (spec.get(key), expected) for key, expected in required.items() if spec.get(key) != expected}
    if stale:
        raise DesignError(f"design boundary changed: {stale}")
    count = spec.get("coreSampleCount")
    if not isinstance(count, int) or not 64 <= count <= 512:
        raise DesignError("coreSampleCount must be 64..512")
    holdout = finite(spec.get("internalHoldoutFraction"), "internalHoldoutFraction")
    if not 0.15 <= holdout <= 0.30:
        raise DesignError("internal holdout fraction must be 0.15..0.30")
    ranges = spec.get("parameterRanges")
    if not isinstance(ranges, dict) or set(ranges) != set(FEATURES):
        raise DesignError("parameter range universe changed")
    for feature in FEATURES:
        bounds = ranges[feature]
        if not isinstance(bounds, list) or len(bounds) != 2:
            raise DesignError(f"invalid range: {feature}")
        low, high = (finite(bounds[0], feature), finite(bounds[1], feature))
        if not low < high:
            raise DesignError(f"non-increasing range: {feature}")
    tiers = spec.get("executionTiers")
    if not isinstance(tiers, list) or len(tiers) != 2:
        raise DesignError("exactly two execution tiers are required")
    if [tier.get("tierId") for tier in tiers] != ["tier-1-provisional", "tier-2-completion"]:
        raise DesignError("execution tier IDs changed")
    if any(not isinstance(tier.get("geometryCount"), int) or tier["geometryCount"] < 1 for tier in tiers):
        raise DesignError("execution tier geometry counts must be positive integers")
    if sum(tier["geometryCount"] for tier in tiers) != count:
        raise DesignError("execution tier geometry counts must equal coreSampleCount")

    schedule = spec.get("photonSchedule")
    if not isinstance(schedule, list) or not schedule:
        raise DesignError("photon schedule missing")
    previous = -math.inf
    for row in schedule:
        if not isinstance(row, dict):
            raise DesignError("photon schedule row must be an object")
        maximum = finite(row.get("maximumSunDepressionDeg"), "maximumSunDepressionDeg")
        photons = row.get("photonHistoriesPerBlock")
        if maximum <= previous or not isinstance(photons, int) or photons < 10_000_000 or photons % 10_000_000:
            raise DesignError("invalid photon schedule")
        previous = maximum


def photons_for(spec: dict[str, Any], sun: float) -> int:
    for row in spec["photonSchedule"]:
        if sun <= float(row["maximumSunDepressionDeg"]):
            return int(row["photonHistoriesPerBlock"])
    raise DesignError(f"photon schedule does not cover sun depression {sun}")


def build(spec: dict[str, Any], policy_path: Path) -> dict[str, Any]:
    validate_spec(spec)
    policy = load_policy(policy_path)
    ranges = spec["parameterRanges"]
    geometries: list[dict[str, Any]] = []
    seen: set[tuple[float, ...]] = set()
    for sample_index in range(1, spec["coreSampleCount"] + 1):
        geometry: dict[str, Any] = {"geometryId": f"train-{sample_index:04d}"}
        key_values: list[float] = []
        for feature, base in zip(FEATURES, BASES):
            low, high = map(float, ranges[feature])
            value = round(low + (high - low) * radical_inverse(sample_index, base), 6)
            geometry[feature] = value
            key_values.append(value)
        key = tuple(key_values)
        if key in seen:
            raise DesignError("duplicate space-filling geometry")
        seen.add(key)
        geometry["alisSpectralImportanceSamplingNm"] = float(policy.alis_importance_nm(geometry))
        geometry["photonHistoriesPerBlock"] = photons_for(spec, geometry["sunDepressionDeg"])
        geometries.append(geometry)

    holdout_every = max(2, round(1.0 / float(spec["internalHoldoutFraction"])))
    training_ids: list[str] = []
    holdout_ids: list[str] = []
    cases: list[dict[str, Any]] = []
    ordinal = 0
    seed_base = int(spec["seedBase"])
    tier_boundaries = []
    running = 0
    for tier in spec["executionTiers"]:
        running += tier["geometryCount"]
        tier_boundaries.append((running, tier["tierId"]))
    tier_geometry_ids: dict[str, list[str]] = {tier["tierId"]: [] for tier in spec["executionTiers"]}
    tier_case_ids: dict[str, list[str]] = {tier["tierId"]: [] for tier in spec["executionTiers"]}

    for index, geometry in enumerate(geometries, start=1):
        tier_id = next(tier for boundary, tier in tier_boundaries if index <= boundary)
        geometry["executionTierId"] = tier_id
        tier_geometry_ids[tier_id].append(geometry["geometryId"])
        target = holdout_ids if index % holdout_every == 0 else training_ids
        target.append(geometry["geometryId"])
        for block in range(1, spec["blocksPerGeometry"] + 1):
            ordinal += 1
            case_id = f"{geometry['geometryId']}-alis-b{block}"
            tier_case_ids[tier_id].append(case_id)
            cases.append({
                "ordinal": ordinal,
                "caseId": case_id,
                "groupId": geometry["geometryId"],
                "method": "alis",
                "block": block,
                "seed": seed_base + ordinal,
                "photonHistories": geometry["photonHistoriesPerBlock"],
                "alisSpectralImportanceSamplingNm": geometry["alisSpectralImportanceSamplingNm"],
                "role": "internal-holdout" if target is holdout_ids else "surrogate-training",
                "executionTierId": tier_id,
            })
    if set(training_ids) & set(holdout_ids):
        raise DesignError("training and holdout overlap")
    total = sum(case["photonHistories"] for case in cases)
    tier_summaries = []
    for tier in spec["executionTiers"]:
        tier_id = tier["tierId"]
        tier_cases = [case for case in cases if case["executionTierId"] == tier_id]
        tier_summaries.append({
            **tier,
            "geometryIds": tier_geometry_ids[tier_id],
            "caseIds": tier_case_ids[tier_id],
            "caseCount": len(tier_cases),
            "configuredMcPhotonsSum": sum(case["photonHistories"] for case in tier_cases),
            "scientificExecution": False,
        })
    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "batchId": "twilight-surrogate-space-filling-v1",
        "mode": "scientific-proposal",
        "proposalOnly": True,
        "scientificExecution": False,
        "successDoesNotAuthorizeProduction": True,
        "observationValidationRequired": True,
        "target": "spectral twilight sky radiance and photopic sky luminance",
        "method": "alis",
        "sampling": {
            "kind": "deterministic-halton",
            "dimensions": list(FEATURES),
            "coreSampleCount": len(geometries),
            "internalHoldoutFractionRequested": spec["internalHoldoutFraction"],
            "trainingGeometryCount": len(training_ids),
            "holdoutGeometryCount": len(holdout_ids),
        },
        "importanceSamplingPolicy": {
            "purpose": "variance reduction only",
            "unbiasednessBoundary": "policy may change Monte Carlo variance but not the expected physical result",
            "allowedReferenceNm": [500.0, 550.0, 600.0],
        },
        "parameterRanges": ranges,
        "photonSchedule": spec["photonSchedule"],
        "executionTiers": tier_summaries,
        "blocksPerGeometry": spec["blocksPerGeometry"],
        "geometryCount": len(geometries),
        "caseCount": len(cases),
        "configuredMcPhotonsSum": total,
        "trainingGeometryIds": training_ids,
        "internalHoldoutGeometryIds": holdout_ids,
        "externalValidationAnchorIds": sorted(spec["externalValidationAnchorIds"]),
        "geometries": geometries,
        "cases": cases,
        "adaptiveContinuation": {
            "metric": "relativeStandardErrorOfMean",
            "target": 0.05,
            "maximum": 0.08,
            "rule": "increase photons or add fresh blocks only for geometries failing precision; never change a computed mean merely to force agreement",
            "automaticScientificExecution": False,
        },
        "surrogateTrainingAutomaticallyAuthorized": False,
        "productionModelReady": False,
        "boundary": "proposal-only training design; six reference anchors remain excluded from fitting and observation validation remains mandatory",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--importance-policy", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = build(load(args.spec), args.importance_policy)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump(result))
        print(dump({key: result[key] for key in ("stageId", "geometryCount", "caseCount", "configuredMcPhotonsSum")}), end="")
        return 0
    except Exception as exc:
        print(dump({"status": "REFUSED", "stageId": STAGE_ID, "reason": str(exc)}), file=sys.stderr, end="")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
