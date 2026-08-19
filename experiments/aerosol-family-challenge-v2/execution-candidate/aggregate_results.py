from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
from typing import Any

CASE_PREFIX = "aerosol-family-v2-case-"
BASELINE = ("rural", "spring-summer")
RAW_MEMBER_NAMES = (
    "case.inp", "prepared.json", "runtime-report.json", "randomseed",
    "syntax-stdout.txt", "syntax-stderr.txt", "solver-stdout.txt", "solver-stderr.txt",
    "wavelength-grid-1nm.dat", "mc.flx.spc", "mc.flx.std.spc", "mc.rad.spc", "mc.rad.std.spc",
)


class AggregateRefusal(RuntimeError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_sha(value: Any) -> str:
    return sha256_bytes(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode())


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AggregateRefusal(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def find_one(root: Path, basename: str) -> Path:
    rows = [p for p in root.rglob(basename) if p.is_file()]
    if len(rows) != 1:
        raise AggregateRefusal(f"{root}: expected exactly one {basename}, got {len(rows)}")
    return rows[0]


def parse_spectrum(path: Path) -> tuple[list[float], list[float]]:
    wavelengths: list[float] = []
    values: list[float] = []
    for raw in path.read_text().splitlines():
        parts = raw.split()
        if len(parts) < 2:
            continue
        try:
            wavelengths.append(float(parts[0]))
            values.append(float(parts[-1]))
        except ValueError:
            continue
    return wavelengths, values


def summarize_three(values: list[float | None]) -> dict[str, Any]:
    import statistics
    if len(values) != 3:
        raise AggregateRefusal("exactly three preregistered replicates required")
    if any(v is None or not math.isfinite(float(v)) for v in values):
        return {"status": "NUMERICALLY_UNRESOLVED", "replicateValues": values, "mean": None, "sampleStd": None, "standardError": None}
    vals = [float(v) for v in values]
    sd = statistics.stdev(vals)
    return {"status": "FINITE_THREE_REPLICATES", "replicateValues": vals, "mean": statistics.mean(vals), "sampleStd": sd, "standardError": sd / math.sqrt(3.0)}


def compact_spectral(replicates: list[dict[str, Any]]) -> dict[str, Any]:
    spectra = [row["spectralLogRatio"] for row in replicates]
    if any(len(s) != 8001 for s in spectra):
        raise AggregateRefusal("spectral contrast must have 8001 nodes")
    mean: list[float | None] = []
    sd: list[float | None] = []
    se: list[float | None] = []
    unresolved: list[int] = []
    for i in range(8001):
        summary = summarize_three([s[i] for s in spectra])
        mean.append(summary["mean"])
        sd.append(summary["sampleStd"])
        se.append(summary["standardError"])
        if summary["status"] != "FINITE_THREE_REPLICATES":
            unresolved.append(i)
    return {
        "wavelengthGrid": {"startNm": 380.0, "stopNm": 780.0, "stepNm": 0.05, "nodeCount": 8001},
        "meanLogRatio": mean,
        "sampleStdLogRatio": sd,
        "standardErrorLogRatio": se,
        "unresolvedNodeIndices": unresolved,
        "inferentialPValueOrConfidenceIntervalPermitted": False,
    }


def aggregate(
    repository_root: Path,
    artifact_root: Path,
    artifact_metadata_path: Path,
    manifest_path: Path,
    analysis_contract_path: Path,
    freeze_record_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, dict[str, Any]]]:
    base = repository_root / "experiments/aerosol-family-challenge-v2"
    analysis = load_module("afc2_analysis", base / "analysis.py")
    derived = load_module("afc2_derived", base / "derived_channels.py")
    manifest = json.loads(manifest_path.read_text())
    freeze = json.loads(freeze_record_path.read_text())
    frozen_bindings = {
        "manifestRawSha256": sha256_file(manifest_path),
        "analysisContractRawSha256": sha256_file(analysis_contract_path),
        "analysisImplementationRawSha256": sha256_file(base / "analysis.py"),
        "derivedChannelsRawSha256": sha256_file(base / "derived_channels.py"),
    }
    for key, observed in frozen_bindings.items():
        if freeze.get(key) != observed:
            raise AggregateRefusal(f"frozen analysis binding drift: {key}")
    cases = manifest.get("cases")
    if not isinstance(cases, list) or len(cases) != 576:
        raise AggregateRefusal("frozen manifest must contain exactly 576 cases")
    expected = {str(row["caseId"]): row for row in cases}
    if len(expected) != 576:
        raise AggregateRefusal("manifest caseId uniqueness failure")

    metadata = json.loads(artifact_metadata_path.read_text())
    rows = metadata.get("artifacts", metadata if isinstance(metadata, list) else [])
    if not isinstance(rows, list):
        raise AggregateRefusal("artifact metadata missing list")
    case_meta = [row for row in rows if str(row.get("name") or "").startswith(CASE_PREFIX)]
    if len(case_meta) != 576:
        raise AggregateRefusal(f"expected exactly 576 current-run case artifacts, got {len(case_meta)}")
    names = [str(row.get("name") or "") for row in case_meta]
    if len(set(names)) != 576:
        raise AggregateRefusal("duplicate case artifact name")

    records: dict[str, dict[str, Any]] = {}
    acquisition_rows: list[dict[str, Any]] = []
    for meta in sorted(case_meta, key=lambda row: str(row.get("name") or "")):
        name = str(meta.get("name") or "")
        case_id = name[len(CASE_PREFIX):]
        if case_id not in expected:
            raise AggregateRefusal(f"unexpected case artifact {name}")
        root = artifact_root / name
        if not root.is_dir():
            raise AggregateRefusal(f"downloaded artifact directory missing: {name}")
        result_path = find_one(root, "case-result.json")
        result = json.loads(result_path.read_text())
        expected_row = expected[case_id]
        for key in ("caseId", "groupId", "analysisCellId", "replicate", "seed", "photonHistories", "aerosolFamily", "aerosolSeason"):
            if result.get(key) != expected_row.get(key):
                raise AggregateRefusal(f"{case_id}: result/manifest drift for {key}")
        if result.get("status") != "COMPLETED" or result.get("workflowRunAttempt") != 1:
            raise AggregateRefusal(f"{case_id}: execution status/attempt drift")
        if result.get("syntaxCheckCount") != 1 or result.get("solverExecutionCount") != 1:
            raise AggregateRefusal(f"{case_id}: execution count drift")
        if any(result.get(key) is not False for key in ("retryPerformed", "resumePerformed", "githubRerun")):
            raise AggregateRefusal(f"{case_id}: retry/resume/rerun drift")
        stored = result.get("contentSha256")
        check = dict(result)
        check.pop("contentSha256", None)
        if stored != canonical_sha(check):
            raise AggregateRefusal(f"{case_id}: case-result content hash mismatch")

        raw_hashes = result.get("rawMemberSha256ByBasename")
        if not isinstance(raw_hashes, dict):
            raise AggregateRefusal(f"{case_id}: raw member hash map missing")
        for basename in RAW_MEMBER_NAMES:
            path = find_one(root, basename)
            if raw_hashes.get(basename) != sha256_file(path):
                raise AggregateRefusal(f"{case_id}: raw member hash mismatch: {basename}")

        rad_path = find_one(root, "mc.rad.spc")
        wl, rad = parse_spectrum(rad_path)
        derived.validate_raw_grid(wl, rad)
        channels = derived.derive_channels(wl, rad)
        if result.get("channels") != channels:
            raise AggregateRefusal(f"{case_id}: derived-channel recomputation mismatch")
        record = dict(channels)
        record["radianceSpectrum"] = rad
        records[case_id] = record
        acquisition_rows.append({
            "caseId": case_id,
            "artifactId": meta.get("id"),
            "artifactName": name,
            "artifactDigest": meta.get("digest"),
            "artifactSizeBytes": meta.get("size_in_bytes"),
            "caseResultRawSha256": sha256_file(result_path),
            "caseResultContentSha256": stored,
            "rawMemberSha256ByBasename": raw_hashes,
        })

    if set(records) != set(expected):
        raise AggregateRefusal("case artifact universe does not equal frozen manifest")

    cells: dict[str, list[dict[str, Any]]] = {}
    for row in cases:
        cells.setdefault(str(row["analysisCellId"]), []).append(row)
    if len(cells) != 24:
        raise AggregateRefusal("expected 24 preregistered analysis cells")

    scalar_cells: list[dict[str, Any]] = []
    spectral_by_state: dict[str, dict[str, Any]] = {}
    for cell_id in sorted(cells):
        rows = cells[cell_id]
        by_state_rep: dict[tuple[str, str, int], dict[str, Any]] = {}
        for row in rows:
            key = (str(row["aerosolFamily"]), str(row["aerosolSeason"]), int(row["replicate"]))
            if key in by_state_rep:
                raise AggregateRefusal(f"{cell_id}: duplicate state/replicate")
            by_state_rep[key] = row
        states = sorted({(k[0], k[1]) for k in by_state_rep})
        baseline_rows = [by_state_rep.get((BASELINE[0], BASELINE[1], rep)) for rep in (1, 2, 3)]
        if any(row is None for row in baseline_rows):
            raise AggregateRefusal(f"{cell_id}: missing baseline replicate")
        state_outputs: list[dict[str, Any]] = []
        for family, season in states:
            contrasts: list[dict[str, Any]] = []
            for rep in (1, 2, 3):
                state_row = by_state_rep.get((family, season, rep))
                base_row = by_state_rep.get((BASELINE[0], BASELINE[1], rep))
                if state_row is None or base_row is None:
                    raise AggregateRefusal(f"{cell_id}: missing paired replicate")
                contrasts.append(analysis.paired_replicate_contrast(records[state_row["caseId"]], records[base_row["caseId"]]))
            primary: dict[str, Any] = {}
            for channel in analysis.PRIMARY_CHANNELS:
                values = [row["primaryLogContrasts"][channel] for row in contrasts]
                summary = analysis.summarize_three(values)
                summary["replicateInterpretationLabels"] = [analysis.interpretation_label(v) for v in values]
                summary["meanInterpretationLabel"] = analysis.interpretation_label(summary["mean"])
                summary["replicateStrongRatioFlags"] = [analysis.strong_ratio_flag(v) for v in values]
                summary["meanStrongRatioFlag"] = analysis.strong_ratio_flag(summary["mean"])
                labels = [x for x in summary["replicateInterpretationLabels"] if x != "NUMERICALLY_UNRESOLVED"]
                if len(labels) != 3:
                    summary["magnitudeStability"] = "UNRESOLVED"
                elif len(set(labels)) == 1:
                    summary["magnitudeStability"] = "STABLE_SAME_BAND_ALL_REPLICATES"
                else:
                    summary["magnitudeStability"] = "MIXED_BANDS_ACROSS_REPLICATES"
                summary["magnitudeInterpretationUncertain"] = summary["magnitudeStability"] in {"UNRESOLVED", "MIXED_BANDS_ACROSS_REPLICATES"}
                finite = [v for v in values if v is not None]
                summary["signConsistency"] = (
                    "UNRESOLVED" if len(finite) != 3 else
                    "CONSISTENT_NONNEGATIVE" if all(v >= 0 for v in finite) else
                    "CONSISTENT_NONPOSITIVE" if all(v <= 0 for v in finite) else
                    "MIXED_SIGN"
                )
                primary[channel] = summary
            spectral_key = f"{cell_id}__{family}__{season}"
            spectral_by_state[spectral_key] = compact_spectral(contrasts)
            state_outputs.append({
                "aerosolFamily": family,
                "aerosolSeason": season,
                "primary": primary,
                "spDifference": analysis.summarize_three([row["spDifference"] for row in contrasts]),
                "spLogRatio": analysis.summarize_three([row["spLogRatio"] for row in contrasts]),
                "spectralKey": spectral_key,
            })
        sample = rows[0]
        scalar_cells.append({
            "analysisCellId": cell_id,
            "sunDepressionDeg": sample.get("sunDepressionDeg"),
            "geometryId": sample.get("geometryId"),
            "geometryTag": sample.get("geometryTag"),
            "aod550": sample.get("aod550"),
            "states": state_outputs,
        })

    acquisition = {
        "schemaVersion": 1,
        "stageId": "aerosol-family-challenge-v2-acquisition",
        "status": "COMPLETE_EXACT_576_CASE_ARTIFACT_UNIVERSE",
        "manifestRawSha256": sha256_file(manifest_path),
        "caseArtifactCount": 576,
        "cases": acquisition_rows,
    }
    analysis_out = {
        "schemaVersion": 1,
        "stageId": "aerosol-family-challenge-v2-preregistered-analysis",
        "status": "COMPLETED_PREREGISTERED_ANALYSIS",
        "manifestRawSha256": sha256_file(manifest_path),
        "analysisContractRawSha256": sha256_file(analysis_contract_path),
        "caseCount": 576,
        "comparisonGroupCount": 72,
        "analysisCellCount": 24,
        "baseline": {"aerosolFamily": BASELINE[0], "aerosolSeason": BASELINE[1]},
        "nonpositiveHandling": "NUMERICALLY_UNRESOLVED_NO_EPSILON",
        "pairedContrastUncertaintyUsePermitted": False,
        "inferentialPValueOrConfidenceIntervalPermitted": False,
        "spotlightRule": {"sunDepressionDeg": [2, 4], "geometryTag": "cross-solar", "description": "early-twilight cross-solar"},
        "cells": scalar_cells,
        "spectralKeys": sorted(spectral_by_state),
    }
    return acquisition, analysis_out, spectral_by_state


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--artifact-metadata", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--analysis-contract", type=Path, required=True)
    parser.add_argument("--freeze-record", type=Path, required=True)
    parser.add_argument("--output-acquisition", type=Path, required=True)
    parser.add_argument("--output-analysis", type=Path, required=True)
    parser.add_argument("--output-spectral-dir", type=Path, required=True)
    args = parser.parse_args()
    acquisition, analysis_out, spectral = aggregate(
        args.repository_root, args.artifact_root, args.artifact_metadata, args.manifest, args.analysis_contract, args.freeze_record
    )
    args.output_acquisition.write_text(json.dumps(acquisition, indent=2, sort_keys=True) + "\n")
    args.output_analysis.write_text(json.dumps(analysis_out, indent=2, sort_keys=True) + "\n")
    args.output_spectral_dir.mkdir(parents=True, exist_ok=False)
    for key, value in spectral.items():
        (args.output_spectral_dir / f"{key}.json").write_text(json.dumps(value, separators=(",", ":"), allow_nan=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
