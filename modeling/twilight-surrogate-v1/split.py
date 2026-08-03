#!/usr/bin/env python3
from __future__ import annotations

import hashlib
from typing import Any

STAGE_ID = "twilight-surrogate-v1"


class SplitRefusal(RuntimeError):
    pass


def stable_fraction(salt: str, group_id: str) -> float:
    digest = hashlib.sha256(f"{salt}\0{group_id}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


def assign_groups(
    rows: list[dict[str, Any]],
    salt: str,
    validation_fraction: float,
    withheld_fraction: float,
) -> list[dict[str, Any]]:
    if not isinstance(salt, str) or not salt:
        raise SplitRefusal("salt must be non-empty")
    if (
        not 0 < validation_fraction < 1
        or not 0 < withheld_fraction < 1
        or validation_fraction + withheld_fraction >= 1
    ):
        raise SplitRefusal("invalid split fractions")
    group_assignments: dict[str, str] = {}
    output: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            raise SplitRefusal("rows must contain objects")
        group_id = row.get("groupId")
        if not isinstance(group_id, str) or not group_id:
            raise SplitRefusal("every row requires groupId")
        if group_id not in group_assignments:
            value = stable_fraction(salt, group_id)
            if value < withheld_fraction:
                split = "withheld"
            elif value < withheld_fraction + validation_fraction:
                split = "validation"
            else:
                split = "train"
            group_assignments[group_id] = split
        output.append({**row, "split": group_assignments[group_id]})
    return output


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {"train": 0, "validation": 0, "withheld": 0}
    groups: dict[str, set[str]] = {key: set() for key in counts}
    for row in rows:
        split = row["split"]
        counts[split] += 1
        groups[split].add(row["groupId"])
    overlap = (
        (groups["train"] & groups["validation"])
        | (groups["train"] & groups["withheld"])
        | (groups["validation"] & groups["withheld"])
    )
    if overlap:
        raise SplitRefusal(f"group leakage detected: {sorted(overlap)}")
    return {
        "rowCounts": counts,
        "groupCounts": {key: len(value) for key, value in groups.items()},
        "groupLeakage": False,
    }
