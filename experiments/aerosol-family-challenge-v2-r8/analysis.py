from __future__ import annotations

import math
import statistics
from typing import Any

PRIMARY_CHANNELS = (
    "photopicLuminanceCdM2",
    "scotopicLuminanceScotCdM2",
    "johnsonVEffectiveRadiance_mW_m2_nm_sr",
)
SP_CHANNEL = "scotopicPhotopicRatio"
BASELINE = ("rural", "spring-summer")


class AnalysisRefusal(RuntimeError):
    pass


def _finite_positive(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value)) and float(value) > 0.0


def paired_log(state: Any, baseline: Any) -> float | None:
    if not _finite_positive(state) or not _finite_positive(baseline):
        return None
    return math.log(float(state) / float(baseline))


def interpretation_label(log_ratio: float | None) -> str:
    if log_ratio is None or not math.isfinite(log_ratio):
        return "NUMERICALLY_UNRESOLVED"
    frac = abs(math.exp(log_ratio) - 1.0)
    if frac < 0.10:
        return "SMALL_BELOW_10_PERCENT"
    if frac < 0.30:
        return "TENS_OF_PERCENT_10_TO_30"
    if frac < 0.50:
        return "SUBSTANTIAL_30_TO_50"
    return "STRONG_AT_LEAST_50_PERCENT"


def strong_ratio_flag(log_ratio: float | None) -> str:
    if log_ratio is None or not math.isfinite(log_ratio):
        return "NUMERICALLY_UNRESOLVED"
    ratio = math.exp(log_ratio)
    if ratio >= 2.0 or ratio <= 0.5:
        return "VERY_LARGE_RATIO_AT_LEAST_2X_OR_AT_MOST_HALF"
    if ratio >= 1.5 or ratio <= (2.0 / 3.0):
        return "STRONG_RATIO_AT_LEAST_1P5X_OR_AT_MOST_TWO_THIRDS"
    return "NOT_STRONG_RATIO_FLAG"


def summarize_three(values: list[float | None]) -> dict[str, Any]:
    if len(values) != 3:
        raise AnalysisRefusal("exactly three preregistered replicate contrasts required")
    if any(v is None or not math.isfinite(float(v)) for v in values):
        return {
            "status": "NUMERICALLY_UNRESOLVED",
            "replicateValues": values,
            "mean": None,
            "sampleStd": None,
            "standardError": None,
        }
    finite = [float(v) for v in values]
    sd = statistics.stdev(finite)
    return {
        "status": "FINITE_THREE_REPLICATES",
        "replicateValues": finite,
        "mean": statistics.mean(finite),
        "sampleStd": sd,
        "standardError": sd / math.sqrt(3.0),
    }


def paired_replicate_contrast(state: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {"primaryLogContrasts": {}}
    for channel in PRIMARY_CHANNELS:
        out["primaryLogContrasts"][channel] = paired_log(state.get(channel), baseline.get(channel))
    sp_state = state.get(SP_CHANNEL)
    sp_base = baseline.get(SP_CHANNEL)
    out["spDifference"] = None if not all(isinstance(x, (int, float)) and math.isfinite(float(x)) for x in (sp_state, sp_base)) else float(sp_state) - float(sp_base)
    out["spLogRatio"] = paired_log(sp_state, sp_base)
    state_spectrum = state.get("radianceSpectrum")
    base_spectrum = baseline.get("radianceSpectrum")
    if not isinstance(state_spectrum, list) or not isinstance(base_spectrum, list) or len(state_spectrum) != 8001 or len(base_spectrum) != 8001:
        raise AnalysisRefusal("each record must contain exact 8001-node radianceSpectrum")
    out["spectralLogRatio"] = [paired_log(s, b) for s, b in zip(state_spectrum, base_spectrum)]
    return out


def aggregate_state_replicates(replicates: list[dict[str, Any]]) -> dict[str, Any]:
    if len(replicates) != 3:
        raise AnalysisRefusal("exactly three paired-seed replicate records required")
    primary = {}
    for channel in PRIMARY_CHANNELS:
        vals = [r["primaryLogContrasts"][channel] for r in replicates]
        summary = summarize_three(vals)
        summary["replicateInterpretationLabels"] = [interpretation_label(v) for v in vals]
        summary["meanInterpretationLabel"] = interpretation_label(summary["mean"])
        summary["replicateStrongRatioFlags"] = [strong_ratio_flag(v) for v in vals]
        summary["meanStrongRatioFlag"] = strong_ratio_flag(summary["mean"])
        finite_labels = [x for x in summary["replicateInterpretationLabels"] if x != "NUMERICALLY_UNRESOLVED"]
        if len(finite_labels) != 3:
            summary["magnitudeStability"] = "UNRESOLVED"
        elif len(set(finite_labels)) == 1:
            summary["magnitudeStability"] = "STABLE_SAME_BAND_ALL_REPLICATES"
        else:
            summary["magnitudeStability"] = "MIXED_BANDS_ACROSS_REPLICATES"
        summary["magnitudeInterpretationUncertain"] = summary["magnitudeStability"] in {"MIXED_BANDS_ACROSS_REPLICATES", "UNRESOLVED"}
        finite_vals = [v for v in vals if v is not None]
        summary["signConsistency"] = (
            "UNRESOLVED" if len(finite_vals) != 3 else
            "CONSISTENT_NONNEGATIVE" if all(v >= 0 for v in finite_vals) else
            "CONSISTENT_NONPOSITIVE" if all(v <= 0 for v in finite_vals) else
            "MIXED_SIGN"
        )
        primary[channel] = summary

    spectral = []
    for i in range(8001):
        spectral.append(summarize_three([r["spectralLogRatio"][i] for r in replicates]))
    return {
        "primary": primary,
        "spDifference": summarize_three([r["spDifference"] for r in replicates]),
        "spLogRatio": summarize_three([r["spLogRatio"] for r in replicates]),
        "spectralLogRatioByWavelength": spectral,
        "wavelengthGrid": {"startNm": 380.0, "stopNm": 780.0, "stepNm": 0.05, "nodeCount": 8001},
        "inferentialPValueOrConfidenceIntervalPermitted": False,
    }
