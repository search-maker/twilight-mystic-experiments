from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
import re
import statistics
from pathlib import Path
from typing import Any

MODEL_PATH = "modeling/surrogate-training-v2/exploratory_noisy_label_training_exact.py"
SOURCE_STAGE = "surrogate-training-v2-wave2-training-only-dataset-v1"
SOURCE_STATUS = "AUDITED_B1_B6_TRAINING_ONLY_DATASET_HOLDOUT_UNOPENED"
SOURCE_DATASET_SHA256 = "f7fd12ac5921c039de3418960a5f3d94ea4820c549247390ff47c316b1111271"
SOURCE_DATASET_RAW_SHA256 = "a6fd419ac79ae491896c22627a0d0605a5f688261ae8f03ef594517bb073c7ae"
SOURCE_CONTRACT_HEAD_SHA = "f41f18af6c0c802cc4bad35186bd864f9680f81b"
SOURCE_CONTRACT_RUN_ID = 31_078_099_534
SOURCE_CONTRACT_ARTIFACT_ID = 8_958_327_171
SOURCE_CONTRACT_ARTIFACT_ZIP_SHA256 = "b98b1275ac68cde7f162f27805e3bd5accfb47775df89e7e76a05376f44c21a6"
OUTPUT_STAGE = "surrogate-training-v2-exploratory-terminal-training-dataset-v1"
OUTPUT_STATUS = "TERMINAL_TRAINING_ONLY_DATASET_HOLDOUT_UNOPENED"
RESULT_STAGE = "tier1-precision-continuation-wave3-ordinal13-execution-v1"
TRAINING_IDS = tuple(
    f"train-{index:04d}" for index in range(1, 49) if index % 5 != 0
)
HOLDOUT_IDS = tuple(
    f"train-{index:04d}" for index in range(1, 49) if index % 5 == 0
)
CONTINUATION_IDS = (
    "train-0003", "train-0007", "train-0009", "train-0011", "train-0013",
    "train-0015", "train-0017", "train-0019", "train-0023", "train-0027",
    "train-0029", "train-0031", "train-0033", "train-0035", "train-0039",
    "train-0041", "train-0043", "train-0045", "train-0046", "train-0047",
)
WAVE3_TRAINING_IDS = (
    "train-0003", "train-0007", "train-0011", "train-0013", "train-0019",
    "train-0023", "train-0027", "train-0029", "train-0031", "train-0039",
    "train-0041", "train-0043", "train-0047",
)
ELIGIBLE = {"PRECISION_TARGET_MET", "PRECISION_ACCEPTED"}
EXHAUSTED = {
    "PRECISION_CONTINUATION_EXHAUSTED",
    "PRECISION_CONTINUATION_EXHAUSTED_ZERO_HIT",
}
CIE = [0.09098, 0.13902, 0.20802, 0.323, 0.503, 0.71, 0.862, 0.954, 0.995, 0.87, 0.757, 0.631, 0.503, 0.175, 0.061]

if len(TRAINING_IDS) != 39 or len(HOLDOUT_IDS) != 9:
    raise RuntimeError("frozen 39/9 role map changed")


class Refusal(RuntimeError):
    pass


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise Refusal(f"expected object: {path}")
    return value


def module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise Refusal(f"module unavailable: {path}")
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def _photopic(nodes: list[float]) -> float:
    if len(nodes) != 15:
        raise Refusal("selected-node vector must contain 15 values")
    return 683.002 * 10.0 * sum((value / 1000.0) * weight for value, weight in zip(nodes, CIE, strict=True))


def _close(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=1e-11, abs_tol=1e-30)


def _extract_object_array(text: str, key: str) -> list[str]:
    match = re.search(rf'"{re.escape(key)}"\s*:\s*\[', text)
    if match is None:
        raise Refusal(f"array missing: {key}")
    index = match.end()
    objects: list[str] = []
    in_string = False
    escaped = False
    depth = 0
    start: int | None = None
    while index < len(text):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        else:
            if char == '"':
                in_string = True
            elif char == "{":
                if depth == 0:
                    start = index
                depth += 1
            elif char == "}":
                depth -= 1
                if depth < 0:
                    raise Refusal(f"malformed array: {key}")
                if depth == 0:
                    if start is None:
                        raise Refusal(f"malformed object: {key}")
                    objects.append(text[start:index + 1])
                    start = None
            elif char == "]" and depth == 0:
                return objects
        index += 1
    raise Refusal(f"unterminated array: {key}")
