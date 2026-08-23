from __future__ import annotations

import importlib.util
import json
import math
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "experiments/aerosol-full-phase-function-sensitivity-v1"
ANALYSIS_PATH = STAGE / "analysis.py"
LEVEL_B_PATH = STAGE / "level_b_analysis.mjs"


def load_analysis():
    spec = importlib.util.spec_from_file_location("afpf_analysis_review", ANALYSIS_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def records(values: dict[str, float]) -> dict[str, dict[str, float]]:
    return {
        state: {
            "photopicLuminanceCdM2": value,
            "scotopicLuminanceScotCdM2": value,
            "johnsonVEffectiveRadiance_mW_m2_nm_sr": value,
        }
        for state, value in values.items()
    }


def canonical_values() -> dict[str, float]:
    return {
        "native-rural-ss": 1.0,
        "opac-continental-average": 2.0,
        "opac-maritime-clean": 4.0,
        "opac-desert": 8.0,
        "opac-desert-spheroids": 16.0,
    }


def test_analysis_binds_frozen_preregistration_and_contract() -> None:
    m = load_analysis()
    summary = m.review_summary()
    assert summary["status"] == "PASS_AFPF_ANALYSIS_IMPLEMENTATION_BINDINGS"
    assert summary["stateCount"] == 5
    assert summary["contrastCount"] == 7
    assert summary["rawSpectrumNodeCount"] == 8001
    assert summary["r8PrimaryChannelsMatch"] is True
    assert summary["pValuesPermitted"] is False
    assert summary["confidenceIntervalsPermitted"] is False
    assert summary["epsilonSubstitutionPermitted"] is False
    assert summary["scientificExecutionAuthorized"] is False
    assert summary["resultOpeningAuthorized"] is False


def test_scalar_contrasts_are_exact_preregistered_log_ratios() -> None:
    m = load_analysis()
    got = m.scalar_replicate_contrasts(records(canonical_values()), "photopicLuminanceCdM2")
    expected = {
        "continental_vs_native": math.log(2.0),
        "maritime_vs_native": math.log(4.0),
        "desert_vs_native": math.log(8.0),
        "desert_spheroids_vs_native": math.log(16.0),
        "maritime_vs_continental": math.log(2.0),
        "desert_vs_continental": math.log(4.0),
        "desert_spheroids_vs_desert": math.log(2.0),
    }
    assert tuple(got) == m.CONTRAST_IDS
    for key, value in expected.items():
        assert got[key] == pytest.approx(value)


def test_nonpositive_required_response_is_unresolved_without_epsilon() -> None:
    m = load_analysis()
    values = canonical_values()
    values["opac-desert"] = 0.0
    got = m.scalar_replicate_contrasts(records(values), "photopicLuminanceCdM2")
    assert got["desert_vs_native"] is None
    assert got["desert_vs_continental"] is None
    assert got["desert_spheroids_vs_desert"] is None
    assert math.isfinite(got["desert_spheroids_vs_native"])
    summary = m.summarize_three([got["desert_vs_native"]] * 3)
    assert summary["status"] == "NUMERICALLY_UNRESOLVED"
    assert summary["mean"] is None
    assert summary["sampleStd"] is None
    assert summary["standardError"] is None


def test_exact_five_state_universe_is_required() -> None:
    m = load_analysis()
    bad = records(canonical_values())
    bad.pop("opac-maritime-clean")
    with pytest.raises(m.AnalysisRefusal, match="exact five-state"):
        m.scalar_replicate_contrasts(bad, "photopicLuminanceCdM2")


def test_spectral_contrasts_and_three_replicate_summary_keep_8001_nodes() -> None:
    m = load_analysis()
    values = canonical_values()
    spectra = {state: [value] * 8001 for state, value in values.items()}
    one = m.spectral_replicate_contrasts(spectra)
    assert tuple(one) == m.CONTRAST_IDS
    assert all(len(nodes) == 8001 for nodes in one.values())
    assert one["desert_spheroids_vs_desert"][0] == pytest.approx(math.log(2.0))
    summary = m.summarize_spectral_three([one, one, one])
    shape = summary["desert_spheroids_vs_desert"]
    assert shape["meanLogRatio"][0] == pytest.approx(math.log(2.0))
    assert shape["sampleStdLogRatio"][0] == pytest.approx(0.0)
    assert shape["standardErrorLogRatio"][0] == pytest.approx(0.0)
    assert shape["unresolvedNodeIndices"] == []
    assert shape["wavelengthGrid"]["nodeCount"] == 8001
    assert shape["inferentialPValueOrConfidenceIntervalPermitted"] is False
    assert shape["epsilonSubstitutionPermitted"] is False


def test_three_replicate_scalar_summary_retains_all_values() -> None:
    m = load_analysis()
    base = records(canonical_values())
    reps = []
    for multiplier in (1.0, 1.0, 1.0):
        by_channel = {}
        for channel in m.PRIMARY_CHANNELS:
            scaled = {
                state: {**row, channel: row[channel] * multiplier}
                for state, row in base.items()
            }
            by_channel[channel] = m.scalar_replicate_contrasts(scaled, channel)
        reps.append(by_channel)
    out = m.aggregate_three_replicates(reps)
    shape = out["photopicLuminanceCdM2"]["desert_spheroids_vs_desert"]
    assert shape["status"] == "FINITE_THREE_REPLICATES"
    assert shape["replicateValues"] == pytest.approx([math.log(2.0)] * 3)
    assert shape["sampleStd"] == pytest.approx(0.0)
    assert shape["standardError"] == pytest.approx(0.0)


def test_level_b_uses_exact_seven_deltas_and_no_time_conversion() -> None:
    script = r'''
import {
  AFPF_LEVEL_B_CONTRASTS,
  replicateLevelBContrasts,
  summarizeLevelBThreeReplicates,
} from './experiments/aerosol-full-phase-function-sensitivity-v1/level_b_analysis.mjs';

const records = {
  'native-rural-ss': { photopicLuminanceCdM2: 1 },
  'opac-continental-average': { photopicLuminanceCdM2: 10 },
  'opac-maritime-clean': { photopicLuminanceCdM2: 100 },
  'opac-desert': { photopicLuminanceCdM2: 1000 },
  'opac-desert-spheroids': { photopicLuminanceCdM2: 10000 },
};
const limiter = ({backgroundLuminanceCdM2}) => -2.5 * Math.log10(backgroundLuminanceCdM2);
const one = replicateLevelBContrasts(records, limiter);
const summary = summarizeLevelBThreeReplicates([one, one, one]);
const zero = structuredClone(records);
zero['opac-desert'].photopicLuminanceCdM2 = 0;
const unresolved = replicateLevelBContrasts(zero, limiter);
console.log(JSON.stringify({
  contrasts: AFPF_LEVEL_B_CONTRASTS,
  one,
  summary,
  unresolved: unresolved.pairedLimitingMagnitudeDelta,
}));
'''
    proc = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert [row["contrastId"] for row in payload["contrasts"]] == [
        "continental_vs_native",
        "maritime_vs_native",
        "desert_vs_native",
        "desert_spheroids_vs_native",
        "maritime_vs_continental",
        "desert_vs_continental",
        "desert_spheroids_vs_desert",
    ]
    deltas = payload["one"]["pairedLimitingMagnitudeDelta"]
    assert deltas["continental_vs_native"] == pytest.approx(-2.5)
    assert deltas["maritime_vs_native"] == pytest.approx(-5.0)
    assert deltas["desert_vs_native"] == pytest.approx(-7.5)
    assert deltas["desert_spheroids_vs_native"] == pytest.approx(-10.0)
    assert deltas["maritime_vs_continental"] == pytest.approx(-2.5)
    assert deltas["desert_vs_continental"] == pytest.approx(-5.0)
    assert deltas["desert_spheroids_vs_desert"] == pytest.approx(-2.5)
    summary = payload["summary"]
    assert summary["status"] == "COMPLETED_PREREGISTERED_AFPF_LEVEL_B_SUMMARY"
    assert summary["contrastCount"] == 7
    assert summary["priorityShapeContrast"] == "desert_spheroids_vs_desert"
    assert summary["contrasts"]["desert_spheroids_vs_desert"]["replicateValues"] == pytest.approx([-2.5, -2.5, -2.5])
    assert summary["contrasts"]["desert_spheroids_vs_desert"]["sampleStd"] == pytest.approx(0.0)
    assert summary["pValuesPermitted"] is False
    assert summary["confidenceIntervalsPermitted"] is False
    assert summary["epsilonSubstitutionPermitted"] is False
    assert summary["universalSunDepressionToMinutesConversionPermitted"] is False
    assert payload["unresolved"]["desert_spheroids_vs_desert"] is None
