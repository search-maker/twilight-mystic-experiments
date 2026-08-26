#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import tempfile
from pathlib import Path
from typing import Any

PACKAGE = Path("experiments/jerusalem-tishrei-direct-mystic-v1")
MANIFEST_REL = PACKAGE / "manifest.proposal.json"
WRAPPER_REL = PACKAGE / "execution_adapter.py"
PROPOSAL_ADAPTER_REL = Path("experiments/mystic-batch-v1/cross_geometry_adapter.py")
ELEVATION_REL = Path("experiments/mystic-batch-v1/twilight_surrogate_tier1_execution_adapter.py")
EXPECTED_CASES = 12
EXPECTED_ELEVATION_M = 800.0
EXPECTED_AOD550 = 0.22


class ValidationError(RuntimeError):
    pass


def req(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    req(isinstance(value, dict), f"JSON object required: {path}")
    return value


def module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    req(spec is not None and spec.loader is not None, f"cannot load module: {path}")
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def synthetic_runtime_report(manifest: dict[str, Any]) -> dict[str, Any]:
    runtime = manifest.get("runtime") or {}
    return {
        "schemaVersion": 1,
        "stageId": "mystic-batch-v1",
        "scientificSolverExecuted": False,
        "syntaxCheckExecuted": False,
        "uvspecSha256": runtime.get("uvspecSha256"),
        "uvspecHelpSha256": runtime.get("uvspecHelpSha256"),
        "libRadtranDataTreeSha256": runtime.get("libRadtranDataTreeSha256"),
        "atmosphereSha256": runtime.get("atmosphereSha256"),
        "runtimeLockRawSha256": runtime.get("runtimeLockRawSha256"),
    }


def validate_case(
    root: Path,
    data_dir: Path,
    manifest_path: Path,
    runtime_path: Path,
    case_id: str,
) -> dict[str, Any]:
    proposal_adapter = module("repair_proposal_adapter", root / PROPOSAL_ADAPTER_REL)
    elevation = module("repair_elevation_adapter", root / ELEVATION_REL)
    wrapper = module("repair_tishrei_wrapper", root / WRAPPER_REL)
    manifest = load_json(manifest_path)
    case, geometry = proposal_adapter.resolve_case(manifest, case_id)
    inputs = proposal_adapter.normalized_inputs(manifest, case, geometry)
    req(abs(float(inputs["observerElevationM"]) - EXPECTED_ELEVATION_M) <= 1e-12, f"{case_id}: elevation drift")
    req(abs(float(inputs["aod550"]) - EXPECTED_AOD550) <= 1e-12, f"{case_id}: AOD drift")

    with tempfile.TemporaryDirectory(prefix="tishrei-repair-wrapped-") as wrapped_tmp:
        prepared = wrapper.prepare_case(
            manifest_path,
            runtime_path,
            case_id,
            data_dir,
            root,
            Path(wrapped_tmp),
        )
        actual_path = Path(prepared["inputPath"])
        actual_text = actual_path.read_text(encoding="utf-8")

        # Re-render the pre-repair baseline into the exact same case directory so
        # path-bearing directives such as mc_basename are identical. The only
        # allowed text change is then the reviewed elevation transformation.
        base_text = proposal_adapter.render_input(inputs, data_dir, root, actual_path.parent)
        expected_text, expected_site_km, expected_grid = elevation.apply_ground_site_atm_z_grid(
            base_text,
            inputs["observerElevationM"],
        )

        req(actual_text == expected_text, f"{case_id}: wrapper output differs from reviewed elevation helper")
        req(base_text.splitlines().count("zout 0.800000") == 1, f"{case_id}: old failure representation not reproduced exactly once")
        req(actual_text.splitlines().count("zout 0.000000") == 1, f"{case_id}: local-surface zout missing")
        req(actual_text.count("atm_z_grid ") == 1, f"{case_id}: atm_z_grid count mismatch")
        req("zout 0.800000" not in actual_text, f"{case_id}: absolute zout survived")
        req("\naltitude " not in "\n" + actual_text, f"{case_id}: forbidden altitude shortcut")
        req("mc_elevation_file" not in actual_text, f"{case_id}: forbidden mc_elevation_file shortcut")
        req(actual_text.count("aerosol_set_tau_at_wvl 550 0.220000") == 1, f"{case_id}: AOD550 binding changed")
        req(abs(float(prepared["siteAltitudeKm"]) - 0.8) <= 1e-12, f"{case_id}: site altitude metadata drift")
        req(float(prepared["zoutKmAboveLocalSurface"]) == 0.0, f"{case_id}: local zout metadata drift")
        req(prepared["observerElevationMechanism"] == "atm_z_grid", f"{case_id}: mechanism metadata drift")
        req(prepared["atmosphereGridKm"] == expected_grid, f"{case_id}: atmosphere grid metadata mismatch")
        req(abs(expected_site_km - 0.8) <= 1e-12 and abs(float(expected_grid[0]) - 0.8) <= 1e-12, f"{case_id}: helper grid bottom drift")
        req(prepared["baseInputResolvedSha256BeforeElevationRepair"] == sha(base_text), f"{case_id}: base input hash mismatch")
        req(prepared["inputResolvedSha256"] == sha(actual_text), f"{case_id}: corrected input hash mismatch")
        persisted = load_json(actual_path.parent / "cross-geometry-prepared.json")
        req(persisted["inputResolvedSha256"] == prepared["inputResolvedSha256"], f"{case_id}: persisted prepared hash stale")

        old_lines = base_text.splitlines()
        new_lines = actual_text.splitlines()
        old_without_zout = [line for line in old_lines if not line.startswith("zout ")]
        new_without_elevation = [line for line in new_lines if not line.startswith("zout ") and not line.startswith("atm_z_grid ")]
        req(old_without_zout == new_without_elevation, f"{case_id}: non-elevation directive changed")

        return {
            "caseId": case_id,
            "method": inputs["method"],
            "block": inputs["block"],
            "observerElevationM": inputs["observerElevationM"],
            "aod550": inputs["aod550"],
            "baseInputSha256": sha(base_text),
            "correctedInputSha256": sha(actual_text),
            "siteAltitudeKm": prepared["siteAltitudeKm"],
            "zoutKmAboveLocalSurface": prepared["zoutKmAboveLocalSurface"],
            "atmosphereGridLevelCount": len(expected_grid),
            "atmosphereGridBottomKm": expected_grid[0],
            "atmosphereGridTopKm": expected_grid[-1],
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, default=Path("."))
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.repository_root.resolve()
    data_dir = args.data_dir.resolve()
    manifest_path = root / MANIFEST_REL
    manifest = load_json(manifest_path)
    cases = manifest.get("cases") or []
    req(isinstance(cases, list) and len(cases) == EXPECTED_CASES, "expected exact 12-case Tishrei manifest")

    with tempfile.TemporaryDirectory(prefix="tishrei-repair-runtime-") as runtime_tmp:
        runtime_path = Path(runtime_tmp) / "runtime-report.json"
        runtime_path.write_text(json.dumps(synthetic_runtime_report(manifest), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        records = [validate_case(root, data_dir, manifest_path, runtime_path, case["caseId"]) for case in cases]

    req({r["method"] for r in records} == {"alis", "reference-vroom"}, "both methods were not validated")
    req(len(records) == EXPECTED_CASES, "case validation count mismatch")
    report = {
        "schemaVersion": 1,
        "status": "ELEVATION_REPAIR_VALIDATED_NO_UVSPEC_NO_SOLVER",
        "caseCount": len(records),
        "configuredPhotonHistoriesRepresented": sum(int(case["photonHistories"]) for case in cases),
        "observerElevationM": EXPECTED_ELEVATION_M,
        "aod550": EXPECTED_AOD550,
        "scientificSyntaxCheckExecuted": False,
        "scientificSolverExecuted": False,
        "repair": "replace absolute zout 0.8 km with reviewed AFGLUS atm_z_grid site-bottom representation and zout 0 km above local surface",
        "cases": records,
        "boundary": "representation-only repair validation; no uvspec process, syntax check, MYSTIC solver, parameter tuning, or production authorization",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
