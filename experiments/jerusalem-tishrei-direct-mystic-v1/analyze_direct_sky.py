#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any

PURPOSE = "jerusalem-tishrei-direct-mystic-v1"
EXPECTED_ALIS_GRID = (380.0, 780.0, 0.05, 8001)
VROOM_NODES = [470.0,480.0,490.0,500.0,510.0,520.0,530.0,540.0,560.0,580.0,590.0,600.0,610.0,640.0,660.0]


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("frozen_derived_channels", path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_spectrum(path: Path) -> tuple[list[float], list[float]]:
    wl: list[float] = []
    rad: list[float] = []
    for line in path.read_text(errors="replace").splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            w = float(parts[0]); r = float(parts[-1])
        except ValueError:
            continue
        if math.isfinite(w) and math.isfinite(r):
            wl.append(w); rad.append(r)
    if not wl:
        raise ValueError(f"no spectrum rows parsed: {path}")
    return wl, rad


def mean(values: list[float]) -> float:
    if not values:
        raise ValueError("empty mean")
    return statistics.fmean(values)


def spread(values: list[float]) -> dict[str, Any]:
    m = mean(values)
    sd = statistics.stdev(values) if len(values) > 1 else 0.0
    pair_rel = None
    if len(values) == 2 and m != 0:
        pair_rel = abs(values[0] - values[1]) / abs(m)
    return {"mean": m, "sampleStd": sd, "coefficientOfVariation": None if m == 0 else sd / abs(m), "pairwiseRelativeDifference": pair_rel}


def relative(direct: float, reference: float) -> dict[str, Any]:
    return {
        "absoluteDifference": direct - reference,
        "ratio": None if reference == 0 else direct / reference,
        "percentDifference": None if reference == 0 else 100.0 * (direct - reference) / reference,
    }


def find_case_dirs(cases_root: Path) -> dict[str, Path]:
    out: dict[str, Path] = {}
    for result_path in cases_root.rglob("case-result.json"):
        record = load_json(result_path)
        case_id = record.get("caseId")
        if not isinstance(case_id, str):
            continue
        if case_id in out:
            raise ValueError(f"duplicate case result: {case_id}")
        if record.get("status") != "COMPLETED" or record.get("syntaxCheckCount") != 1 or record.get("solverExecutionCount") != 1:
            raise ValueError(f"case not structurally complete: {case_id}")
        out[case_id] = result_path.parent
    return out


def spectrum_map(wl: list[float], rad: list[float], tolerance: float = 5e-5) -> dict[float, float]:
    result: dict[float, float] = {}
    for node in VROOM_NODES:
        matches = [r for w, r in zip(wl, rad) if abs(w - node) <= tolerance]
        if len(matches) != 1:
            raise ValueError(f"expected one spectral sample at {node}, got {len(matches)}")
        result[node] = matches[0]
    return result


def analyze(manifest_path: Path, evidence_path: Path, contract_path: Path, cases_root: Path, derived_path: Path) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    evidence = load_json(evidence_path)
    contract = load_json(contract_path)
    derived = load_module(derived_path)
    case_dirs = find_case_dirs(cases_root)
    cases = manifest.get("cases") or []
    if len(cases) != 12 or set(case_dirs) != {c["caseId"] for c in cases}:
        raise ValueError("exact 12-case artifact universe not present")
    if contract.get("analysisId") != "jerusalem-tishrei-direct-mystic-level-b-comparison-v1":
        raise ValueError("wrong analysis contract")

    geometry_by_group = {g["groupId"]: g for g in manifest["geometries"]}
    evidence_by_catalog = {s["catalogId"]: s for s in evidence["stars"]}
    results = []
    for group_id, geometry in geometry_by_group.items():
        group_cases = [c for c in cases if c["groupId"] == group_id]
        alis_cases = sorted((c for c in group_cases if c["method"] == "alis"), key=lambda c: c["block"])
        vroom_cases = sorted((c for c in group_cases if c["method"] == "reference-vroom"), key=lambda c: c["block"])
        if len(alis_cases) != 2 or len(vroom_cases) != 2:
            raise ValueError(f"wrong replicate set for {group_id}")

        alis_reps = []
        alis_node_maps = []
        for case in alis_cases:
            d = case_dirs[case["caseId"]]
            wl, rad = parse_spectrum(d / "mc.rad.spc")
            swl, srad = parse_spectrum(d / "mc.rad.std.spc")
            start, stop, step, count = EXPECTED_ALIS_GRID
            if len(wl) != count or len(swl) != count:
                raise ValueError(f"ALIS grid count mismatch: {case['caseId']} {len(wl)}/{len(swl)}")
            derived.validate_raw_grid(wl, rad)
            derived.validate_raw_grid(swl, srad)
            channels = derived.derive_channels(wl, rad)
            mc_std = derived.marginal_mc_std_diagnostics(wl, rad, srad)
            alis_reps.append({"caseId": case["caseId"], "block": case["block"], "channels": channels, "marginalMcStd": mc_std})
            alis_node_maps.append(spectrum_map(wl, rad))

        channel_keys = ["photopicLuminanceCdM2", "scotopicLuminanceScotCdM2", "johnsonVEffectiveRadiance_mW_m2_nm_sr"]
        channel_summary = {k: spread([float(rep["channels"][k]) for rep in alis_reps]) for k in channel_keys}
        alis_mean_nodes = {node: mean([m[node] for m in alis_node_maps]) for node in VROOM_NODES}

        vroom_reps = []
        vroom_node_maps = []
        for case in vroom_cases:
            d = case_dirs[case["caseId"]]
            wl, rad = parse_spectrum(d / "mc.rad.spc")
            m = spectrum_map(wl, rad)
            vroom_node_maps.append(m)
            vroom_reps.append({"caseId": case["caseId"], "block": case["block"], "parsedWavelengthCount": len(wl)})
        vroom_mean_nodes = {node: mean([m[node] for m in vroom_node_maps]) for node in VROOM_NODES}
        cross = []
        for node in VROOM_NODES:
            a = alis_mean_nodes[node]; v = vroom_mean_nodes[node]
            cross.append({"wavelengthNm": node, "alisMeanRadiance": a, "vroomMeanRadiance": v, **relative(v, a)})

        catalog_id = geometry["target"]["catalogId"]
        frozen = evidence_by_catalog[catalog_id]
        levelb = {
            "photopicLuminanceCdM2": float(frozen["skyChannels"]["photopic"]["value"]),
            "scotopicLuminanceScotCdM2": float(frozen["skyChannels"]["scotopic"]["value"]),
            "johnsonVEffectiveRadiance_mW_m2_nm_sr": float(frozen["skyChannels"]["johnsonV"]["value"]),
        }
        direct_mean = {k: channel_summary[k]["mean"] for k in channel_keys}
        comparison = {k: relative(direct_mean[k], levelb[k]) for k in channel_keys}
        results.append({
            "groupId": group_id,
            "catalogId": catalog_id,
            "name": frozen["name"],
            "geometry": frozen["eventGeometry"],
            "levelB": {"channels": levelb, "apparentVMagAtEye": frozen["stellar"]["apparentVMagAtEye"], "limitingVMagnitude": frozen["visibility"]["limitingVMagnitude"], "visibilityMarginMag": frozen["visibility"]["visibilityMarginMag"]},
            "directALIS": {"replicates": alis_reps, "channelSummary": channel_summary, "meanChannels": direct_mean},
            "directMinusLevelB": comparison,
            "referenceVroomCrossCheck": {"replicates": vroom_reps, "nodes": cross, "channelDerivationForbidden": True},
        })

    return {
        "schemaVersion": 1,
        "status": "DIRECT_MYSTIC_SKY_COMPARISON_COMPLETE",
        "scientificPurpose": PURPOSE,
        "batchId": manifest["batchId"],
        "geometryCount": len(results),
        "caseCount": len(cases),
        "configuredMcPhotonsSum": sum(int(c["photonHistories"]) for c in cases),
        "perGeometry": results,
        "claimBoundary": {
            "computationalDiagnosticOnly": True,
            "levelBSpectralRuntimeAvailable": False,
            "fullSpectrumLevelBValidationClaimAllowed": False,
            "measuredRealSkyValidated": False,
            "humanFirstSeeingValidated": False,
            "productionAuthorized": False,
            "noParameterTuning": True,
        },
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--evidence", type=Path, required=True)
    p.add_argument("--analysis-contract", type=Path, required=True)
    p.add_argument("--cases-root", type=Path, required=True)
    p.add_argument("--derived-channels", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    try:
        report = analyze(args.manifest, args.evidence, args.analysis_contract, args.cases_root, args.derived_channels)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump(report))
        print(dump(report), end="")
        return 0
    except Exception as exc:
        refusal = {"schemaVersion": 1, "status": "REFUSED", "scientificPurpose": PURPOSE, "reason": str(exc)}
        print(dump(refusal), end="", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
