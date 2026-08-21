from __future__ import annotations

import hashlib
import importlib.util
import json
import math
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
NATIVE = "native-rural-ss"
FACTORIAL = {
    (0.85, 0.60): "ssa085-g060",
    (0.85, 0.80): "ssa085-g080",
    (0.98, 0.60): "ssa098-g060",
    (0.98, 0.80): "ssa098-g080",
}
EXPECTED_STATES = {NATIVE, *FACTORIAL.values()}


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
    spec.loader.exec_module(mod)
    return mod


def source_analysis():
    path = SOURCE_R8 / "analysis.py"
    if git_blob_sha1(path) != SOURCE_ANALYSIS_BLOB:
        raise AnalysisRefusal("bound R8 analysis bytes changed")
    if git_blob_sha1(SOURCE_R8 / "derived_channels.py") != SOURCE_DERIVED_BLOB:
        raise AnalysisRefusal("bound R8 derived-channel bytes changed")
    return _load("aops_bound_r8_analysis", path)


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _difference(a: float | None, b: float | None) -> float | None:
    if a is None or b is None or not _finite(a) or not _finite(b):
        return None
    return float(a) - float(b)


def scalar_replicate_contrasts(records_by_state: dict[str, dict[str, Any]], channel: str) -> dict[str, float | None]:
    if channel not in PRIMARY_CHANNELS:
        raise AnalysisRefusal(f"unsupported primary channel: {channel}")
    if set(records_by_state) != EXPECTED_STATES:
        raise AnalysisRefusal("exact five-state replicate universe required")
    base = source_analysis()
    values = {state: records_by_state[state].get(channel) for state in EXPECTED_STATES}
    native = values[NATIVE]
    native_logs = {state: base.paired_log(values[state], native) for state in FACTORIAL.values()}
    ssa_g060 = base.paired_log(values[FACTORIAL[(0.98, 0.60)]], values[FACTORIAL[(0.85, 0.60)]])
    ssa_g080 = base.paired_log(values[FACTORIAL[(0.98, 0.80)]], values[FACTORIAL[(0.85, 0.80)]])
    g_ssa085 = base.paired_log(values[FACTORIAL[(0.85, 0.80)]], values[FACTORIAL[(0.85, 0.60)]])
    g_ssa098 = base.paired_log(values[FACTORIAL[(0.98, 0.80)]], values[FACTORIAL[(0.98, 0.60)]])
    return {
        "native_vs_ssa085_g060": native_logs[FACTORIAL[(0.85, 0.60)]],
        "native_vs_ssa085_g080": native_logs[FACTORIAL[(0.85, 0.80)]],
        "native_vs_ssa098_g060": native_logs[FACTORIAL[(0.98, 0.60)]],
        "native_vs_ssa098_g080": native_logs[FACTORIAL[(0.98, 0.80)]],
        "ssa_high_vs_low_at_g060": ssa_g060,
        "ssa_high_vs_low_at_g080": ssa_g080,
        "g_high_vs_low_at_ssa085": g_ssa085,
        "g_high_vs_low_at_ssa098": g_ssa098,
        "ssa_x_g_interaction": _difference(ssa_g080, ssa_g060),
    }


def summarize_three(values: list[float | None]) -> dict[str, Any]:
    return source_analysis().summarize_three(values)


def aggregate_three_replicates(replicates: list[dict[str, dict[str, float | None]]]) -> dict[str, Any]:
    if len(replicates) != 3:
        raise AnalysisRefusal("exactly three paired replicates required")
    keys = set(replicates[0])
    if any(set(row) != keys for row in replicates[1:]):
        raise AnalysisRefusal("replicate channel set drift")
    out: dict[str, Any] = {}
    for channel in sorted(keys):
        contrast_keys = set(replicates[0][channel])
        if any(set(row[channel]) != contrast_keys for row in replicates[1:]):
            raise AnalysisRefusal("replicate contrast set drift")
        out[channel] = {name: summarize_three([row[channel][name] for row in replicates]) for name in sorted(contrast_keys)}
    return out


def spectral_replicate_contrasts(spectra_by_state: dict[str, list[float]]) -> dict[str, list[float | None]]:
    if set(spectra_by_state) != EXPECTED_STATES:
        raise AnalysisRefusal("exact five-state spectral replicate universe required")
    lengths = {len(v) for v in spectra_by_state.values()}
    if lengths != {8001}:
        raise AnalysisRefusal("every spectrum must contain exactly 8001 nodes")
    base = source_analysis()
    out = {name: [] for name in (
        "native_vs_ssa085_g060", "native_vs_ssa085_g080", "native_vs_ssa098_g060", "native_vs_ssa098_g080",
        "ssa_high_vs_low_at_g060", "ssa_high_vs_low_at_g080", "g_high_vs_low_at_ssa085", "g_high_vs_low_at_ssa098", "ssa_x_g_interaction",
    )}
    for i in range(8001):
        values = {state: spectra_by_state[state][i] for state in EXPECTED_STATES}
        native = values[NATIVE]
        n1 = base.paired_log(values[FACTORIAL[(0.85, 0.60)]], native)
        n2 = base.paired_log(values[FACTORIAL[(0.85, 0.80)]], native)
        n3 = base.paired_log(values[FACTORIAL[(0.98, 0.60)]], native)
        n4 = base.paired_log(values[FACTORIAL[(0.98, 0.80)]], native)
        s60 = base.paired_log(values[FACTORIAL[(0.98, 0.60)]], values[FACTORIAL[(0.85, 0.60)]])
        s80 = base.paired_log(values[FACTORIAL[(0.98, 0.80)]], values[FACTORIAL[(0.85, 0.80)]])
        g85 = base.paired_log(values[FACTORIAL[(0.85, 0.80)]], values[FACTORIAL[(0.85, 0.60)]])
        g98 = base.paired_log(values[FACTORIAL[(0.98, 0.80)]], values[FACTORIAL[(0.98, 0.60)]])
        vals = (n1, n2, n3, n4, s60, s80, g85, g98, _difference(s80, s60))
        for name, value in zip(out, vals):
            out[name].append(value)
    return out


def summarize_spectral_three(replicates: list[dict[str, list[float | None]]]) -> dict[str, Any]:
    if len(replicates) != 3:
        raise AnalysisRefusal("exactly three spectral paired replicates required")
    keys = set(replicates[0])
    if any(set(r) != keys for r in replicates[1:]):
        raise AnalysisRefusal("spectral contrast key drift")
    out: dict[str, Any] = {}
    for key in sorted(keys):
        if any(len(r[key]) != 8001 for r in replicates):
            raise AnalysisRefusal("spectral contrast node-count drift")
        mean: list[float | None] = []
        sd: list[float | None] = []
        se: list[float | None] = []
        unresolved: list[int] = []
        for i in range(8001):
            s = summarize_three([r[key][i] for r in replicates])
            mean.append(s["mean"]); sd.append(s["sampleStd"]); se.append(s["standardError"])
            if s["status"] != "FINITE_THREE_REPLICATES": unresolved.append(i)
        out[key] = {
            "meanLogRatio": mean,
            "sampleStdLogRatio": sd,
            "standardErrorLogRatio": se,
            "unresolvedNodeIndices": unresolved,
            "wavelengthGrid": {"startNm": 380.0, "stopNm": 780.0, "stepNm": 0.05, "nodeCount": 8001},
            "inferentialPValueOrConfidenceIntervalPermitted": False,
        }
    return out


if __name__ == "__main__":
    base = source_analysis()
    print(json.dumps({
        "status": "PASS_AOPS_ANALYSIS_REVIEW_BINDINGS",
        "primaryChannels": list(PRIMARY_CHANNELS),
        "r8PrimaryChannelsMatch": tuple(base.PRIMARY_CHANNELS) == PRIMARY_CHANNELS,
        "stateCount": len(EXPECTED_STATES),
    }, sort_keys=True))
