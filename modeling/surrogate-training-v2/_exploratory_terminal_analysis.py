from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path
from typing import Any

def _load(name: str):
    path = Path(__file__).with_name(name + ".py")
    spec = importlib.util.spec_from_file_location("exploratory_terminal_" + name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

core = _load("_exploratory_terminal_core")
Refusal = core.Refusal
raw_sha256 = core.raw_sha256
TRAINING_IDS = core.TRAINING_IDS
CONTINUATION_IDS = core.CONTINUATION_IDS
_extract_object_array = core._extract_object_array

def load_training_points(path: Path, source_binding: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if raw_sha256(path) != source_binding.get("analysisRawSha256"):
        raise Refusal("terminal analysis raw hash changed")
    text = path.read_text(encoding="utf-8")
    objects = _extract_object_array(text, "points")
    ids: list[str] = []
    selected: dict[str, dict[str, Any]] = {}
    for raw in objects:
        match = re.search(r'"geometryId"\s*:\s*"([^"]+)"', raw)
        if match is None:
            raise Refusal("terminal analysis point identity missing")
        geometry_id = match.group(1)
        ids.append(geometry_id)
        if geometry_id in TRAINING_IDS:
            point = json.loads(raw)
            if not isinstance(point, dict):
                raise Refusal("terminal training point malformed")
            selected[geometry_id] = point
    if tuple(ids) != CONTINUATION_IDS or len(set(ids)) != len(ids):
        raise Refusal("terminal continuation point order or universe changed")
    expected_training = tuple(gid for gid in CONTINUATION_IDS if gid in TRAINING_IDS)
    if tuple(selected) != expected_training:
        raise Refusal("terminal training point subset changed")
    return selected
