from __future__ import annotations

import hashlib
import importlib.util
import math
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SOURCE_R8 = ROOT / "experiments/aerosol-family-challenge-v2-r8"
SOURCE_ANALYSIS_BLOB = "50b64b5c8a7a9d28a1c7174c1a1fda8d7380799d"
SOURCE_DERIVED_BLOB = "ccfd04d4c21188966351f4257e92893d7ce340c7"

PRIMARY_CHANNELS = (
    "photopicLuminanceCdM2",
    "scotopicLuminanceScotCdM2",
    "johnsonVEffectiveRadiance_mW_m2_nm_sr",
)
REFERENCE = "opac-profile-continental-average"
ALTERNATIVES = (
    "opac-profile-maritime-clean",
    "opac-profile-desert",
    "opac-profile-arctic",
    "opac-profile-antarctic",
)
EXPECTED_STATES = {REFERENCE, *ALTERNATIVES}


class AnalysisRefusal(RuntimeError):
    pass


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AnalysisRefusal(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def source_analysis():
    path = SOURCE_R8 / "analysis.py"
    if git_blob_sha1(path) != SOURCE_ANALYSIS_BLOB:
        raise AnalysisRefusal("bound R8 analysis bytes changed")
    if git_blob_sha1(SOURCE_R8 / "derived_channels.py") != SOURCE_DERIVED_BLOB:
        raise AnalysisRefusal("bound R8 derived-channel bytes changed")
    return _load("avps_bound_r8_analysis", path)


def contrast_name(state_id: str) -> str:
    if state_id not in ALTERNATIVES:
        raise AnalysisRefusal(f"not a preregistered alternative state: {state_id}")
    return f"{state_id}_vs_{REFERENCE}"


def scalar_replicate_contrasts(records_by_state: dict[str, dict[str, Any]], channel: str) -> dict[str, float | None]:
    if channel not in PRIMARY_CHANNELS:
        raise AnalysisRefusal(f"unsupported primary channel: {channel}")
    if set(records_by_state) != EXPECTED_STATES:
        raise AnalysisRefusal("exact five-state replicate universe required")
    base = source_analysis()
    reference_value = records_by_state[REFERENCE].get(channel)
    return {
        contrast_name(state): base.paired_log(records_by_state[state].get(channel), reference_value)
        for state in ALTERNATIVES
    }


def summarize_three(values: list[float | None]) -> dict[str, Any]:
    return source_analysis().summarize_three(values)


def aggregate_three_replicates(replicates: list[dict[str, dict[str, float | None]]]) -> dict[str, Any]:
    if len(replicates) != 3:
        raise AnalysisRefusal("exactly three paired replicates required")
    keys = set(replicates[0])
    if keys != set(PRIMARY_CHANNELS) or any(set(row) != keys for row in replicates[1:]):
        raise AnalysisRefusal("replicate channel set drift")
    expected_contrasts = {contrast_name(state) for state in ALTERNATIVES}
    out: dict[str, Any] = {}
    for channel in PRIMARY_CHANNELS:
        if any(set(row[channel]) != expected_contrasts for row in replicates):
            raise AnalysisRefusal("replicate contrast set drift")
        out[channel] = {
            name: summarize_three([row[channel][name] for row in replicates])
            for name in sorted(expected_contrasts)
        }
    return out


def spectral_replicate_contrasts(spectra_by_state: dict[str, list[float]]) -> dict[str, list[float | None]]:
    if set(spectra_by_state) != EXPECTED_STATES:
        raise AnalysisRefusal("exact five-state spectral replicate universe required")
    if {len(v) for v in spectra_by_state.values()} != {8001}:
        raise AnalysisRefusal("every spectrum must contain exactly 8001 nodes")
    base = source_analysis()
    reference = spectra_by_state[REFERENCE]
    return {
        contrast_name(state): [base.paired_log(s, r) for s, r in zip(spectra_by_state[state], reference)]
        for state in ALTERNATIVES
    }


def summarize_spectral_three(replicates: list[dict[str, list[float | None]]]) -> dict[str, Any]:
    if len(replicates) != 3:
        raise AnalysisRefusal("exactly three spectral paired replicates required")
    expected = {contrast_name(state) for state in ALTERNATIVES}
    if any(set(row) != expected for row in replicates):
        raise AnalysisRefusal("spectral contrast key drift")
    out: dict[str, Any] = {}
    for key in sorted(expected):
        if any(len(row[key]) != 8001 for row in replicates):
            raise AnalysisRefusal("spectral node-count drift")
        mean: list[float | None] = []
        sd: list[float | None] = []
        se: list[float | None] = []
        unresolved: list[int] = []
        for i in range(8001):
            summary = summarize_three([row[key][i] for row in replicates])
            mean.append(summary["mean"])
            sd.append(summary["sampleStd"])
            se.append(summary["standardError"])
            if summary["status"] != "FINITE_THREE_REPLICATES":
                unresolved.append(i)
        out[key] = {
            "meanLogRatio": mean,
            "sampleStdLogRatio": sd,
            "standardErrorLogRatio": se,
            "unresolvedNodeIndices": unresolved,
            "wavelengthGrid": {"startNm": 380.0, "stopNm": 780.0, "stepNm": 0.05, "nodeCount": 8001},
            "inferentialPValueOrConfidenceIntervalPermitted": False,
        }
    return out


def validate_numeric_policy(summary: dict[str, Any]) -> None:
    for channel in PRIMARY_CHANNELS:
        for contrast in summary.get(channel, {}).values():
            if contrast.get("status") == "FINITE_THREE_REPLICATES":
                for key in ("mean", "sampleStd", "standardError"):
                    if not isinstance(contrast.get(key), (int, float)) or not math.isfinite(float(contrast[key])):
                        raise AnalysisRefusal("finite summary contains nonfinite statistic")
            elif contrast.get("status") != "NUMERICALLY_UNRESOLVED":
                raise AnalysisRefusal("unexpected numeric status")
