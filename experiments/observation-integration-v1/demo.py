#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from contracts import canonical_sha256, validate_observation
from radiance_api import SyntheticRadianceProvider
from visibility_api import predict_visibility


def run(observation_path: Path, output_path: Path) -> dict:
    observation = validate_observation(json.loads(observation_path.read_text()))
    star = observation["starObservations"][0]
    geometry = observation["geometry"]
    conditions = observation["conditions"]
    request = {
        "schemaVersion": 1,
        "apiId": "star-visibility-integration-v1",
        "catalogMagnitude": star["catalogMagnitude"],
        "colorIndexBv": star["colorIndexBv"] if star["colorIndexBv"] is not None else 0.7,
        "extinctionMagnitude": 0.2,
        "observerAdaptationOffsetMagnitude": 0.0,
        "radianceRequest": {
            "schemaVersion": 1,
            "apiId": "twilight-radiance-spectrum-v1",
            "sunDepressionDeg": geometry["sunDepressionDeg"],
            "targetAltitudeDeg": geometry["targetAltitudeDeg"],
            "relativeAzimuthDeg": geometry["relativeAzimuthDeg"],
            "aod550": conditions["aod550Estimate"] if conditions["aod550Estimate"] is not None else 0.15,
            "observerElevationM": observation["location"]["observerElevationM"],
        },
    }
    visibility = predict_visibility(request, SyntheticRadianceProvider())
    result = {
        "schemaVersion": 1,
        "stageId": "observation-integration-v1",
        "status": "SYNTHETIC_DEMO_COMPLETE",
        "observationSha256": canonical_sha256(observation),
        "observationRole": observation["role"],
        "visibility": visibility,
        "syntheticOnly": True,
        "boundary": "demonstrates observation to radiance API to visibility API wiring only",
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--observation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.observation, args.output), indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
