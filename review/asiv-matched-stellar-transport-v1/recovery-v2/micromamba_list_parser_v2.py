#!/usr/bin/env python3
"""Fail-closed parser for micromamba list --json across bare/enveloped outputs.

Micromamba 2.9 changed JSON output framing. This helper changes only metadata
parsing; it does not alter package selection, runtime hashes, solver inputs, or
scientific execution semantics.
"""
from __future__ import annotations

from typing import Any


class MicromambaListParserRefusal(RuntimeError):
    pass


def _dict_lists(value: Any, path: tuple[str, ...] = ()):  # yields nested arrays of records
    if isinstance(value, list):
        yield path, value
        return
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _dict_lists(child, path + (str(key),))


def extract_unique_package_record(payload: Any, package_name: str) -> dict[str, Any]:
    if not isinstance(package_name, str) or not package_name:
        raise MicromambaListParserRefusal("package name must be non-empty")

    candidates: list[tuple[tuple[str, ...], list[Any], list[dict[str, Any]]]] = []
    for path, rows in _dict_lists(payload):
        if not isinstance(rows, list) or not rows:
            continue
        if not all(isinstance(row, dict) for row in rows):
            continue
        hits = [row for row in rows if row.get("name") == package_name]
        if hits:
            candidates.append((path, rows, hits))

    if len(candidates) != 1:
        paths = ["/".join(path) or "<root>" for path, _, _ in candidates]
        raise MicromambaListParserRefusal(
            f"expected exactly one package-record array containing {package_name!r}; got {len(candidates)} at {paths}"
        )

    _, _, hits = candidates[0]
    if len(hits) != 1:
        raise MicromambaListParserRefusal(
            f"expected exactly one {package_name!r} record; got {len(hits)}"
        )
    record = hits[0]
    for key in ("name", "version"):
        if not isinstance(record.get(key), str) or not record[key]:
            raise MicromambaListParserRefusal(f"package record missing non-empty {key}")
    build = record.get("build_string") or record.get("build")
    if not isinstance(build, str) or not build:
        raise MicromambaListParserRefusal("package record missing non-empty build/build_string")
    return record


def exact_package_spec(record: dict[str, Any]) -> str:
    build = record.get("build_string") or record.get("build")
    return f"{record['name']}={record['version']}={build}"
