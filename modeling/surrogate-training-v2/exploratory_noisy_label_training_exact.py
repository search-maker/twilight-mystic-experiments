#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path

BASE_PATH = Path(__file__).with_name("exploratory_noisy_label_training.py")
spec = importlib.util.spec_from_file_location("exploratory_noisy_label_training_legacy", BASE_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(BASE_PATH)
_base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_base)

TRAINING_GEOMETRY_IDS = tuple(
    f"train-{index:04d}" for index in range(1, 49) if index % 5 != 0
)
HOLDOUT_GEOMETRY_IDS = tuple(
    f"train-{index:04d}" for index in range(1, 49) if index % 5 == 0
)
ALL_GEOMETRY_IDS = frozenset(TRAINING_GEOMETRY_IDS + HOLDOUT_GEOMETRY_IDS)
SOURCE_MANIFEST_SHA256 = "822fc607d4418835074d53b5990163a46a3d7969d499dcbe5d601c9952aa0958"

if len(TRAINING_GEOMETRY_IDS) != 39 or len(HOLDOUT_GEOMETRY_IDS) != 9:
    raise RuntimeError("frozen 39/9 role map changed")

_base.TRAINING_GEOMETRY_IDS = TRAINING_GEOMETRY_IDS
_base.HOLDOUT_GEOMETRY_IDS = HOLDOUT_GEOMETRY_IDS
_base.ALL_GEOMETRY_IDS = ALL_GEOMETRY_IDS
_base.SOURCE_MANIFEST_SHA256 = SOURCE_MANIFEST_SHA256

Refusal = _base.Refusal
dump = _base.dump
canonical_sha256 = _base.canonical_sha256
load = _base.load
is_sha256 = _base.is_sha256
validate_source_binding = _base.validate_source_binding
solve = _base.solve
feature = _base.feature
target = _base.target
observation_weight = _base.observation_weight
normalizer = _base.normalizer
normalize = _base.normalize
basis = _base.basis
fit = _base.fit
predict = _base.predict
cross_validate = _base.cross_validate
validate_training_dataset = _base.validate_training_dataset
run = _base.run
main = _base.main

if __name__ == "__main__":
    raise SystemExit(main())
