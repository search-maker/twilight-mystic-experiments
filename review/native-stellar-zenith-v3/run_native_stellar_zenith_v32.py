#!/usr/bin/env python3
"""One-shot controller for native stellar zenith v3.2.

This controller exists so a protected-holdout scientific FAIL is preserved as
structured evidence before the process exits nonzero.  It does not change any
coordinate, solver input, interpolation rule, or acceptance threshold.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
METHOD_PATH = HERE / "native_stellar_zenith_v32.py"


def _load_method():
    spec = importlib.util.spec_from_file_location("native_stellar_zenith_v32_for_controller", METHOD_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load native stellar zenith v3.2 method")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


v32 = _load_method()


def decorate_validation_result(result: dict[str, Any]) -> dict[str, Any]:
    result = dict(result)
    result["stageId"] = v32.STAGE_ID
    result["methodVersion"] = v32.METHOD_VERSION
    result["interpolation"] = "v3-csc-altitude-trilinear-direct-optical-depth-with-exact-vertical-90deg-endpoint"
    result["exactVerticalTrainingSpectrumCount"] = v32.EXPECTED_EXACT_VERTICAL_TRAINING_SPECTRA
    result["belowZenithSdisortTrainingSpectrumCount"] = v32.EXPECTED_SDISORT_TRAINING_SPECTRA
    result["protectedHoldoutSdisortSpectrumCount"] = v32.EXPECTED_PROTECTED_HOLDOUT_SPECTRA
    result["exactVerticalEndpointProof"] = {
        "analysisRunId": v32.EXACT_VERTICAL_ANALYSIS_RUN_ID,
        "analysisArtifactId": v32.EXACT_VERTICAL_ANALYSIS_ARTIFACT_ID,
        "analysisArtifactDigest": v32.EXACT_VERTICAL_ANALYSIS_ARTIFACT_DIGEST,
        "maxAbsDeltaOpticalDepth": v32.EXACT_VERTICAL_PROOF_MAX_ABS_DELTA_TAU,
        "maxAbsDeltaOpticalDepthLimit": v32.EXACT_VERTICAL_PROOF_TAU_LIMIT,
        "maxAbsDeltaAvMag": v32.EXACT_VERTICAL_PROOF_MAX_ABS_DELTA_AV_MAG,
        "maxAbsDeltaAvMagLimit": v32.EXACT_VERTICAL_PROOF_AV_LIMIT,
        "passed": True,
    }
    result["claimBoundary"] = {
        **(result.get("claimBoundary") or {}),
        "computationalReferenceValidationOnly": True,
        "exactVerticalEndpointComputationallyValidated": True,
        "positiveEpsilonSubstitutionUsed": False,
        "oldV2DomainChanged": False,
        "empiricalRealSkyValidated": False,
        "humanFirstSeeingValidated": False,
        "productionAuthorized": False,
    }
    return result


def extract_validation_failure(exc: BaseException) -> dict[str, Any] | None:
    try:
        payload = json.loads(str(exc))
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    result = payload.get("validationFailed")
    if not isinstance(result, dict):
        return None
    return decorate_validation_result(result)


def preserve_validation_failure(output_dir: Path, result: dict[str, Any]) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "native-stellar-zenith-v32-validation.json"
    if path.exists():
        raise RuntimeError("refusing to overwrite existing v3.2 validation evidence")
    path.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return path


def execute_from_args(args: argparse.Namespace) -> int:
    try:
        result = v32.execute_campaign(
            root=args.root,
            source_runtime_path=args.source_runtime,
            uvspec=args.uvspec,
            data_dir=args.data_dir,
            atmosphere_file=args.atmosphere_file,
            wavelength_grid_file=args.wavelength_grid_file,
            sed_bundle_path=args.sed_bundle,
            johnson_v_path=args.johnson_v,
            output_dir=args.output_dir,
            allow_execution=True,
        )
    except v32.ZenithV32Refusal as exc:
        failure = extract_validation_failure(exc)
        if failure is not None:
            preserve_validation_failure(args.output_dir, failure)
            print(json.dumps({"stageId": v32.STAGE_ID, "status": failure.get("status"), "overall": failure.get("overall")}, sort_keys=True))
        raise
    print(json.dumps({"stageId": result["stageId"], "status": result["status"], "overall": result["overall"]}, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--source-runtime", type=Path, required=True)
    parser.add_argument("--uvspec", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--atmosphere-file", type=Path, required=True)
    parser.add_argument("--wavelength-grid-file", type=Path, required=True)
    parser.add_argument("--sed-bundle", type=Path, required=True)
    parser.add_argument("--johnson-v", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return execute_from_args(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
