#!/usr/bin/env python3
from __future__ import annotations

import argparse
import itertools
import math
import random
from pathlib import Path
from typing import Any

from harness import dump_json, write_jsonl


def synthetic_radiance(point: dict[str, float]) -> float:
    depression = point["sunDepressionDeg"]
    altitude = point["targetAltitudeDeg"]
    azimuth = math.radians(point["relativeAzimuthDeg"])
    aod = point["aod550"]
    elevation = point["observerElevationM"]
    log_radiance = (
        2.75
        - 0.335 * depression
        + 0.0065 * altitude
        + 0.20 * math.cos(azimuth)
        - 1.20 * aod
        + 0.000055 * elevation
        + 0.055 * math.sin(0.55 * depression)
        + 0.018 * math.cos(math.radians(2.0 * altitude))
        + 0.035 * aod * depression
    )
    return math.exp(log_radiance)


def latin_hypercube(count: int, seed: int) -> list[dict[str, float]]:
    rng = random.Random(seed)
    bounds = {
        "sunDepressionDeg": (3.0, 18.0),
        "targetAltitudeDeg": (5.0, 75.0),
        "relativeAzimuthDeg": (0.0, 180.0),
        "aod550": (0.02, 0.50),
        "observerElevationM": (0.0, 3000.0),
    }
    permutations: dict[str, list[int]] = {}
    for feature in bounds:
        order = list(range(count))
        rng.shuffle(order)
        permutations[feature] = order
    rows: list[dict[str, float]] = []
    for index in range(count):
        point: dict[str, float] = {}
        for feature, (low, high) in bounds.items():
            slot = permutations[feature][index]
            fraction = (slot + rng.random()) / count
            point[feature] = low + fraction * (high - low)
        rows.append(point)
    return rows


def make_records(points: list[dict[str, float]], prefix: str, noise_fraction: float, seed: int) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    records: list[dict[str, Any]] = []
    for index, point in enumerate(points, start=1):
        truth = synthetic_radiance(point)
        noise = rng.gauss(0.0, noise_fraction)
        observed = truth * math.exp(noise)
        records.append(
            {
                "id": f"{prefix}-{index:04d}",
                **point,
                "targetRadiance": observed,
                "targetSigma": truth * noise_fraction,
                "syntheticTruthRadiance": truth,
                "syntheticOnly": True,
            }
        )
    return records


def candidate_grid() -> list[dict[str, Any]]:
    axes = {
        "sunDepressionDeg": [4.0, 6.0, 8.0, 10.0, 12.0, 15.0, 17.0],
        "targetAltitudeDeg": [10.0, 30.0, 60.0],
        "relativeAzimuthDeg": [0.0, 90.0, 180.0],
        "aod550": [0.05, 0.15, 0.35],
        "observerElevationM": [0.0, 800.0, 2000.0],
    }
    rows: list[dict[str, Any]] = []
    keys = list(axes)
    for index, values in enumerate(itertools.product(*(axes[key] for key in keys)), start=1):
        rows.append({"id": f"candidate-{index:05d}", **dict(zip(keys, values, strict=True)), "syntheticOnly": True})
    return rows


def generate(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    train = make_records(latin_hypercube(180, 1001), "train", 0.018, 2001)
    validation = make_records(latin_hypercube(60, 1002), "validation", 0.0, 2002)
    withheld = make_records(latin_hypercube(90, 1003), "withheld", 0.0, 2003)
    candidates = candidate_grid()
    write_jsonl(output_dir / "train.jsonl", train)
    write_jsonl(output_dir / "validation.jsonl", validation)
    write_jsonl(output_dir / "withheld.jsonl", withheld)
    write_jsonl(output_dir / "candidates.jsonl", candidates)
    manifest = {
        "schemaVersion": 1,
        "stageId": "twilight-surrogate-v1",
        "syntheticOnly": True,
        "generator": "analytic-synthetic-radiance-v1",
        "counts": {
            "train": len(train),
            "validation": len(validation),
            "withheld": len(withheld),
            "candidates": len(candidates),
        },
        "boundary": "generated values are contract-test data and are not MYSTIC, observations, or scientific evidence",
    }
    (output_dir / "manifest.json").write_text(dump_json(manifest))
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(dump_json(generate(args.output_dir)), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
