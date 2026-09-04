#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
CLAIM_CLASSES = {"quantitative-validation", "diagnostic"}
OBSERVABLE_CLASSES = {
    "point-direction",
    "finite-aperture",
    "wide-field",
    "hemispheric",
    "other-explicit",
    "unknown-explicit",
}
STATUS_VALUES = {"complete", "partial", "unknown"}
MATERIAL_COMPONENTS = (
    "observableClass",
    "angularResponse",
    "pointing",
    "spectralResponse",
    "calibration",
    "temporalResponse",
    "units",
    "geometryConvention",
)
SPEC_KEYS = {
    "observableClass",
    "angularResponse",
    "pointing",
    "spectralResponse",
    "calibration",
    "temporalResponse",
    "units",
    "geometryConvention",
}


class MeasurementOperatorRefusal(RuntimeError):
    pass


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise MeasurementOperatorRefusal(f"{name} must be an object")
    return value


def _nonempty_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MeasurementOperatorRefusal(f"{name} must be a non-empty string")
    return value.strip()


def _canonical_json(value: Any, name: str) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise MeasurementOperatorRefusal(f"{name} is not canonical JSON data") from exc


def _deep_copy_json(value: Any, name: str) -> Any:
    return json.loads(_canonical_json(value, name))


def _contains_null(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, dict):
        return any(_contains_null(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_null(item) for item in value)
    return False


def _fingerprint(spec: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(spec, "operatorSpec").encode("utf-8")).hexdigest()


def validate_operator(record: dict[str, Any], name: str = "operator") -> dict[str, Any]:
    record = _mapping(record, name)
    if record.get("schemaVersion") != SCHEMA_VERSION:
        raise MeasurementOperatorRefusal(f"{name}.schemaVersion must be {SCHEMA_VERSION}")

    operator_id = _nonempty_text(record.get("operatorId"), f"{name}.operatorId")
    status = _mapping(record.get("status"), f"{name}.status")
    if set(status) != set(MATERIAL_COMPONENTS):
        missing = sorted(set(MATERIAL_COMPONENTS) - set(status))
        extra = sorted(set(status) - set(MATERIAL_COMPONENTS))
        raise MeasurementOperatorRefusal(
            f"{name}.status must explicitly contain every material component; "
            f"missing={missing}, extra={extra}"
        )
    for component in MATERIAL_COMPONENTS:
        if status[component] not in STATUS_VALUES:
            raise MeasurementOperatorRefusal(
                f"{name}.status.{component} must be one of {sorted(STATUS_VALUES)}"
            )

    spec = _mapping(record.get("operatorSpec"), f"{name}.operatorSpec")
    if set(spec) != SPEC_KEYS:
        missing = sorted(SPEC_KEYS - set(spec))
        extra = sorted(set(spec) - SPEC_KEYS)
        raise MeasurementOperatorRefusal(
            f"{name}.operatorSpec must explicitly contain every v1 field; "
            f"missing={missing}, extra={extra}"
        )

    observable_class = spec.get("observableClass")
    if observable_class not in OBSERVABLE_CLASSES:
        raise MeasurementOperatorRefusal(
            f"{name}.operatorSpec.observableClass must be one of "
            f"{sorted(OBSERVABLE_CLASSES)}"
        )
    if observable_class == "unknown-explicit" and status["observableClass"] != "unknown":
        raise MeasurementOperatorRefusal(
            f"{name} with unknown-explicit observableClass must mark that component unknown"
        )
    if observable_class != "unknown-explicit" and status["observableClass"] == "unknown":
        raise MeasurementOperatorRefusal(
            f"{name} may not mark a known observableClass as unknown"
        )

    for section in SPEC_KEYS - {"observableClass"}:
        section_value = _mapping(spec.get(section), f"{name}.operatorSpec.{section}")
        if not section_value:
            raise MeasurementOperatorRefusal(
                f"{name}.operatorSpec.{section} must be explicit and non-empty"
            )
        if status[section] == "complete" and _contains_null(section_value):
            raise MeasurementOperatorRefusal(
                f"{name}.status.{section}=complete is inconsistent with explicit null/unknown data"
            )

    provenance = _mapping(record.get("provenance"), f"{name}.provenance")
    if set(provenance) != set(MATERIAL_COMPONENTS):
        missing = sorted(set(MATERIAL_COMPONENTS) - set(provenance))
        extra = sorted(set(provenance) - set(MATERIAL_COMPONENTS))
        raise MeasurementOperatorRefusal(
            f"{name}.provenance must explicitly cover every material component; "
            f"missing={missing}, extra={extra}"
        )
    for component in MATERIAL_COMPONENTS:
        _nonempty_text(provenance[component], f"{name}.provenance.{component}")

    normalized_spec = _deep_copy_json(spec, f"{name}.operatorSpec")
    normalized = {
        "schemaVersion": SCHEMA_VERSION,
        "operatorId": operator_id,
        "status": {component: status[component] for component in MATERIAL_COMPONENTS},
        "operatorSpec": normalized_spec,
        "provenance": {
            component: _nonempty_text(
                provenance[component], f"{name}.provenance.{component}"
            )
            for component in MATERIAL_COMPONENTS
        },
        "operatorFingerprintSha256": _fingerprint(normalized_spec),
    }
    return normalized


def _incomplete(operator: dict[str, Any]) -> list[str]:
    return [
        component
        for component in MATERIAL_COMPONENTS
        if operator["status"][component] != "complete"
    ]


def _mismatched_sections(measured: dict[str, Any], synthetic: dict[str, Any]) -> list[str]:
    measured_spec = measured["operatorSpec"]
    synthetic_spec = synthetic["operatorSpec"]
    return sorted(
        section
        for section in SPEC_KEYS
        if _canonical_json(measured_spec[section], f"measured.{section}")
        != _canonical_json(synthetic_spec[section], f"synthetic.{section}")
    )


def compare_operators(
    *,
    measured_operator: dict[str, Any],
    synthetic_operator: dict[str, Any],
    claim_class: str,
    synthetic_operator_applied: bool,
) -> dict[str, Any]:
    if claim_class not in CLAIM_CLASSES:
        raise MeasurementOperatorRefusal(
            f"claimClass must be one of {sorted(CLAIM_CLASSES)}"
        )
    if not isinstance(synthetic_operator_applied, bool):
        raise MeasurementOperatorRefusal("syntheticOperatorApplied must be boolean")

    measured = validate_operator(measured_operator, "measuredOperator")
    synthetic = validate_operator(synthetic_operator, "syntheticOperator")
    incomplete_measured = _incomplete(measured)
    incomplete_synthetic = _incomplete(synthetic)
    mismatched = _mismatched_sections(measured, synthetic)
    same_spec = not mismatched

    if claim_class == "quantitative-validation":
        if not synthetic_operator_applied:
            raise MeasurementOperatorRefusal(
                "quantitative validation refused: synthetic measurement operator was not applied"
            )
        if incomplete_measured or incomplete_synthetic:
            raise MeasurementOperatorRefusal(
                "quantitative validation refused: material operator provenance is incomplete; "
                f"measured={incomplete_measured}, synthetic={incomplete_synthetic}"
            )
        if not same_spec:
            raise MeasurementOperatorRefusal(
                "quantitative validation refused: measured and synthetic operators differ in "
                + ", ".join(mismatched)
            )
        status = "VALID_OPERATOR_MATCH"
    else:
        status = "DIAGNOSTIC_ONLY"

    return {
        "schemaVersion": SCHEMA_VERSION,
        "status": status,
        "claimClass": claim_class,
        "syntheticOperatorApplied": synthetic_operator_applied,
        "sameOperatorSpec": same_spec,
        "mismatchedSections": mismatched,
        "incompleteMeasuredComponents": incomplete_measured,
        "incompleteSyntheticComponents": incomplete_synthetic,
        "measuredOperatorId": measured["operatorId"],
        "syntheticOperatorId": synthetic["operatorId"],
        "measuredOperatorFingerprintSha256": measured["operatorFingerprintSha256"],
        "syntheticOperatorFingerprintSha256": synthetic["operatorFingerprintSha256"],
        "boundary": (
            "VALID_OPERATOR_MATCH establishes operator/provenance compatibility only; it does "
            "not establish atmospheric, radiative-transfer, calibration-accuracy, or physical "
            "model validity. DIAGNOSTIC_ONLY must not be promoted to quantitative validation."
        ),
    }


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise MeasurementOperatorRefusal(f"cannot read JSON: {path}") from exc
    return _mapping(value, str(path))


def _dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fail-closed measured-vs-synthetic measurement-operator provenance check"
    )
    parser.add_argument("--comparison", type=Path, required=True)
    args = parser.parse_args()
    try:
        payload = _load(args.comparison)
        result = compare_operators(
            measured_operator=payload.get("measuredOperator"),
            synthetic_operator=payload.get("syntheticOperator"),
            claim_class=payload.get("claimClass"),
            synthetic_operator_applied=payload.get("syntheticOperatorApplied"),
        )
        print(_dump(result), end="")
        return 0
    except Exception as exc:
        print(
            _dump({"status": "REFUSED", "reason": str(exc)}),
            end="",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
