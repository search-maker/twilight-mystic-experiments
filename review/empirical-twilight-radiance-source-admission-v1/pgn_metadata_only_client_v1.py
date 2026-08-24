#!/usr/bin/env python3
"""Metadata-only PGN API helper for the blinded real-sky validation lane.

This module intentionally refuses PGN download/data endpoints. It discovers the
actual path and parameter contract from PGN's live OpenAPI document before any
metadata query is allowed, so the validation package does not guess or silently
drift with API route/parameter names.

Allowed OpenAPI path families:
- /v1/calibrationfiles...
- /v1/operationfiles...
- /v1/metadata...
- /v1/files... only for metadata/file-identity listing

Forbidden:
- /v1/download and descendants
- every path outside the four metadata/file-identity families

The CLI is discovery-only until exact current PGN routes and filters are frozen.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Any, Iterable, Mapping
from urllib.parse import urlencode, urljoin, urlparse
from urllib.request import Request, urlopen

BASE_URL = "https://api.pandonia-global-network.org/"
OPENAPI_PATH = "/openapi.json"
ALLOWED_PATH_PREFIXES = (
    "/v1/calibrationfiles",
    "/v1/operationfiles",
    "/v1/metadata",
    "/v1/files",
)
FORBIDDEN_PATH_PREFIXES = ("/v1/download",)


class MetadataOnlyViolation(RuntimeError):
    """Raised when a request would cross the target-value boundary."""


@dataclass(frozen=True)
class ParameterSpec:
    name: str
    location: str
    required: bool
    schema_type: str | None
    description: str | None


def _normalized_path(path: str) -> str:
    parsed = urlparse(path)
    raw = parsed.path if parsed.scheme else path.split("?", 1)[0]
    if not raw.startswith("/"):
        raw = "/" + raw
    return raw.rstrip("/") or "/"


def _belongs_to_prefix(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(prefix + "/")


def assert_metadata_only_path(path: str) -> str:
    normalized = _normalized_path(path)
    if any(_belongs_to_prefix(normalized, prefix) for prefix in FORBIDDEN_PATH_PREFIXES):
        raise MetadataOnlyViolation(f"PGN download endpoint is forbidden: {normalized}")
    if not any(_belongs_to_prefix(normalized, prefix) for prefix in ALLOWED_PATH_PREFIXES):
        raise MetadataOnlyViolation(f"PGN endpoint is outside metadata allow-listed families: {normalized}")
    return normalized


def fetch_json(url: str, *, timeout_s: float = 30.0) -> Any:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "starsvisibility-blind-metadata-admission-v1",
        },
        method="GET",
    )
    with urlopen(request, timeout=timeout_s) as response:  # nosec B310 - official HTTPS host is enforced by callers
        if response.status != 200:
            raise RuntimeError(f"PGN request failed with HTTP {response.status}: {url}")
        return json.loads(response.read().decode("utf-8"))


def fetch_openapi(*, base_url: str = BASE_URL, timeout_s: float = 30.0) -> Mapping[str, Any]:
    parsed = urlparse(base_url)
    if parsed.scheme != "https" or parsed.netloc != "api.pandonia-global-network.org":
        raise MetadataOnlyViolation("OpenAPI discovery is restricted to the official PGN HTTPS API host")
    document = fetch_json(urljoin(base_url, OPENAPI_PATH.lstrip("/")), timeout_s=timeout_s)
    if not isinstance(document, Mapping):
        raise RuntimeError("PGN OpenAPI document is not a JSON object")
    return document


def discover_metadata_paths(openapi: Mapping[str, Any]) -> tuple[str, ...]:
    paths = openapi.get("paths")
    if not isinstance(paths, Mapping):
        raise RuntimeError("PGN OpenAPI has no paths object")
    discovered: list[str] = []
    for raw_path, path_item in paths.items():
        if not isinstance(raw_path, str) or not isinstance(path_item, Mapping):
            continue
        normalized = _normalized_path(raw_path)
        if any(_belongs_to_prefix(normalized, prefix) for prefix in FORBIDDEN_PATH_PREFIXES):
            continue
        if not any(_belongs_to_prefix(normalized, prefix) for prefix in ALLOWED_PATH_PREFIXES):
            continue
        if isinstance(path_item.get("get"), Mapping):
            discovered.append(normalized)
    if not discovered:
        raise RuntimeError("PGN OpenAPI exposes no GET paths in the frozen metadata-only families")
    return tuple(sorted(set(discovered)))


def endpoint_parameters(openapi: Mapping[str, Any], path: str) -> tuple[ParameterSpec, ...]:
    normalized = assert_metadata_only_path(path)
    paths = openapi.get("paths")
    if not isinstance(paths, Mapping) or normalized not in paths:
        raise RuntimeError(f"PGN OpenAPI does not expose exact path {normalized}")
    path_item = paths[normalized]
    if not isinstance(path_item, Mapping):
        raise RuntimeError(f"PGN OpenAPI path item is malformed for {normalized}")
    operation = path_item.get("get")
    if not isinstance(operation, Mapping):
        raise RuntimeError(f"PGN OpenAPI path {normalized} has no GET operation")

    merged: list[Mapping[str, Any]] = []
    for source in (path_item.get("parameters", []), operation.get("parameters", [])):
        if source is None:
            continue
        if not isinstance(source, list):
            raise RuntimeError(f"PGN OpenAPI parameters are malformed for {normalized}")
        for item in source:
            if not isinstance(item, Mapping):
                raise RuntimeError(f"PGN OpenAPI parameter entry is malformed for {normalized}")
            if "$ref" in item:
                raise RuntimeError(
                    f"PGN OpenAPI uses unresolved parameter $ref for {normalized}; "
                    "freeze a reviewed resolver before querying"
                )
            merged.append(item)

    result: list[ParameterSpec] = []
    seen: set[tuple[str, str]] = set()
    for item in merged:
        name = item.get("name")
        location = item.get("in")
        if not isinstance(name, str) or not isinstance(location, str):
            raise RuntimeError(f"PGN OpenAPI parameter lacks name/in for {normalized}")
        key = (name, location)
        if key in seen:
            continue
        seen.add(key)
        schema = item.get("schema")
        schema_type = schema.get("type") if isinstance(schema, Mapping) else None
        description = item.get("description")
        result.append(
            ParameterSpec(
                name=name,
                location=location,
                required=bool(item.get("required", False)),
                schema_type=schema_type if isinstance(schema_type, str) else None,
                description=description if isinstance(description, str) else None,
            )
        )
    return tuple(result)


def query_parameter_names(openapi: Mapping[str, Any], path: str) -> frozenset[str]:
    return frozenset(
        parameter.name
        for parameter in endpoint_parameters(openapi, path)
        if parameter.location == "query"
    )


def validate_query_against_openapi(
    openapi: Mapping[str, Any],
    path: str,
    query: Mapping[str, str | int | float | bool | None],
) -> dict[str, str | int | float | bool]:
    normalized = assert_metadata_only_path(path)
    specs = endpoint_parameters(openapi, normalized)
    query_specs = {spec.name: spec for spec in specs if spec.location == "query"}
    unsupported = sorted(set(query) - set(query_specs))
    if unsupported:
        raise MetadataOnlyViolation(
            f"Query uses parameters not declared by live PGN OpenAPI for {normalized}: {unsupported}"
        )

    cleaned: dict[str, str | int | float | bool] = {
        key: value for key, value in query.items() if value is not None
    }
    missing = sorted(
        spec.name
        for spec in query_specs.values()
        if spec.required and spec.name not in cleaned
    )
    if missing:
        raise MetadataOnlyViolation(
            f"Query omits required PGN parameters for {normalized}: {missing}"
        )
    return cleaned


def build_metadata_url(
    openapi: Mapping[str, Any],
    path: str,
    query: Mapping[str, str | int | float | bool | None],
    *,
    base_url: str = BASE_URL,
) -> str:
    normalized = assert_metadata_only_path(path)
    if "{" in normalized or "}" in normalized:
        raise MetadataOnlyViolation(
            "OpenAPI path templates with path parameters must be separately resolved and reviewed before live query"
        )
    cleaned = validate_query_against_openapi(openapi, normalized, query)
    base = urljoin(base_url, normalized.lstrip("/"))
    return base if not cleaned else f"{base}?{urlencode(cleaned, doseq=False)}"


def request_metadata(
    openapi: Mapping[str, Any],
    path: str,
    query: Mapping[str, str | int | float | bool | None],
    *,
    base_url: str = BASE_URL,
    timeout_s: float = 30.0,
) -> Any:
    url = build_metadata_url(openapi, path, query, base_url=base_url)
    return fetch_json(url, timeout_s=timeout_s)


def describe_contract(openapi: Mapping[str, Any], paths: Iterable[str] | None = None) -> dict[str, Any]:
    selected_paths = discover_metadata_paths(openapi) if paths is None else tuple(paths)
    output: dict[str, Any] = {}
    for path in sorted(selected_paths):
        specs = endpoint_parameters(openapi, path)
        output[path] = [
            {
                "name": spec.name,
                "in": spec.location,
                "required": spec.required,
                "schemaType": spec.schema_type,
                "description": spec.description,
            }
            for spec in specs
        ]
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--describe",
        action="store_true",
        help="Fetch live OpenAPI and print discovered GET paths/parameters only inside frozen metadata families.",
    )
    args = parser.parse_args()

    if not args.describe:
        parser.error("This review helper currently permits only --describe; exact query routes/filters must be reviewed after live discovery.")
    openapi = fetch_openapi()
    print(json.dumps(describe_contract(openapi), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
