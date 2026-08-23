from __future__ import annotations

import hashlib
import importlib.util
import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
STAGE = Path(__file__).resolve().parent
SOURCE_R8 = ROOT / "experiments/aerosol-family-challenge-v2-r8"
SOURCE_ANALYSIS_BLOB = "50b64b5c8a7a9d28a1c7174c1a1fda8d7380799d"
SOURCE_DERIVED_BLOB = "ccfd04d4c21188966351f4257e92893d7ce340c7"
PROTOCOL_BLOB = "083b66177e35a25c4441da6fa3bd5ec68c75a4a5"
ANALYSIS_CONTRACT_BLOB = "8a78b32feb88c0838abd73472fb31ca1b59b7c38"

PRIMARY_CHANNELS = (
    "photopicLuminanceCdM2",
    "scotopicLuminanceScotCdM2",
    "johnsonVEffectiveRadiance_mW_m2_nm_sr",
)
STATE_IDS = (
    "native-rural-ss",
    "opac-continental-average",
    "opac-maritime-clean",
    "opac-desert",
    "opac-desert-spheroids",
)
CONTRASTS = (
    ("continental_vs_native", "opac-continental-average", "native-rural-ss"),
    ("maritime_vs_native", "opac-maritime-clean", "native-rural-ss"),
    ("desert_vs_native", "opac-desert", "native-rural-ss"),
    ("desert_spheroids_vs_native", "opac-desert-spheroids", "native-rural-ss"),
    ("maritime_vs_continental", "opac-maritime-clean", "opac-continental-average"),
    ("desert_vs_continental", "opac-desert", "opac-continental-average"),
    ("desert_spheroids_vs_desert", "opac-desert-spheroids", "opac-desert"),
)
CONTRAST_IDS = tuple(row[0] for row in CONTRASTS)
EXPECTED_STATES = frozenset(STATE_IDS)


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


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except Exception as exc:  # pragma: no cover - defensive refusal path
        raise AnalysisRefusal(f"cannot parse {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise AnalysisRefusal(f"expected JSON object: {path}")
    return value


def assert_frozen_contract_bindings() -> dict[str, Any]:
    protocol_path = STAGE / "protocol.review.json"
    contract_path = STAGE / "analysis-contract.v1.json"
    if git_blob_sha1(protocol_path) != PROTOCOL_BLOB:
        raise AnalysisRefusal("frozen protocol bytes changed")
    if git_blob_sha1(contract_path) != ANALYSIS_CONTRACT_BLOB:
        raise AnalysisRefusal("frozen analysis contract bytes changed")
    protocol = _load_json(protocol_path)
    contract = _load_json(contract_path)
    if protocol.get("status") != "REVIEW_ONLY_PREREGISTRATION_EXECUTION_DISABLED_RESULTS_NOT_OPENED":
        raise AnalysisRefusal("protocol review boundary drift")
    if contract.get("status") != "FROZEN_REVIEW_ONLY_ANALYSIS_CONTRACT_RESULTS_NOT_OPENED":
        raise AnalysisRefusal("analysis contract boundary drift")
    if protocol.get("scientificExecutionAuthorized") is not False or protocol.get("resultOpeningAuthorized") is not False:
        raise AnalysisRefusal("protocol crossed scientific/result boundary")
    if contract.get("scientificExecutionAuthorized") is not False or contract.get("resultOpeningAuthorized") is not False:
        raise AnalysisRefusal("analysis contract crossed scientific/result boundary")
    contract_states = tuple(contract.get("caseUniverse", {}).get("exactStateIds", []))
    if contract_states != STATE_IDS:
        raise AnalysisRefusal("analysis state order/set drift")
    contract_contrasts = tuple(
        (row.get("contrastId"), row.get("alternative"), row.get("reference"))
        for row in contract.get("contrasts", [])
    )
    if contract_contrasts != CONTRASTS:
        raise AnalysisRefusal("analysis contrast set/order drift")
    if tuple(contract.get("primaryChannels", [])) != PRIMARY_CHANNELS:
        raise AnalysisRefusal("primary-channel contract drift")
    return {"protocol": protocol, "contract": contract}


def source_analysis():
    path = SOURCE_R8 / "analysis.py"
    if git_blob_sha1(path) != SOURCE_ANALYSIS_BLOB:
        raise AnalysisRefusal("bound R8 analysis bytes changed")
    if git_blob_sha1(SOURCE_R8 / "derived_channels.py") != SOURCE_DERIVED_BLOB:
        raise AnalysisRefusal("bound R8 derived-channel bytes changed")
    return _load("afpf_bound_r8_analysis", path)


def _validate_exact_state_universe(values_by_state: dict[str, Any], label: str) -> None:
    if set(values_by_state) != EXPECTED_STATES:
        raise AnalysisRefusal(f"exact five-state {label} universe required")


def scalar_replicate_contrasts(records_by_state: dict[str, dict[str, Any]], channel: str) -> dict[str, float | None]:
    assert_frozen_contract_bindings()
    if channel not in PRIMARY_CHANNELS:
        raise AnalysisRefusal(f"unsupported primary channel: {channel}")
    _validate_exact_state_universe(records_by_state, "scalar replicate")
    base = source_analysis()
    values = {state: records_by_state[state].get(channel) for state in STATE_IDS}
    return {
        contrast_id: base.paired_log(values[alternative], values[reference])
        for contrast_id, alternative, reference in CONTRASTS
    }


def summarize_three(values: list[float | None]) -> dict[str, Any]:
    return source_analysis().summarize_three(values)


def aggregate_three_replicates(replicates: list[dict[str, dict[str, float | None]]]) -> dict[str, Any]:
    if len(replicates) != 3:
        raise AnalysisRefusal("exactly three paired replicates required")
    keys = set(replicates[0])
    if any(set(row) != keys for row in replicates[1:]):
        raise AnalysisRefusal("replicate channel set drift")
    if keys != set(PRIMARY_CHANNELS):
        raise AnalysisRefusal("exact primary channel set required")
    out: dict[str, Any] = {}
    for channel in PRIMARY_CHANNELS:
        if any(tuple(row[channel]) != CONTRAST_IDS for row in replicates):
            raise AnalysisRefusal("replicate contrast set/order drift")
        out[channel] = {
            name: summarize_three([row[channel][name] for row in replicates])
            for name in CONTRAST_IDS
        }
    return out


def spectral_replicate_contrasts(spectra_by_state: dict[str, list[float]]) -> dict[str, list[float | None]]:
    assert_frozen_contract_bindings()
    _validate_exact_state_universe(spectra_by_state, "spectral replicate")
    lengths = {len(v) for v in spectra_by_state.values()}
    if lengths != {8001}:
        raise AnalysisRefusal("every spectrum must contain exactly 8001 nodes")
    base = source_analysis()
    out = {contrast_id: [] for contrast_id in CONTRAST_IDS}
    for i in range(8001):
        values = {state: spectra_by_state[state][i] for state in STATE_IDS}
        for contrast_id, alternative, reference in CONTRASTS:
            out[contrast_id].append(base.paired_log(values[alternative], values[reference]))
    return out


def summarize_spectral_three(replicates: list[dict[str, list[float | None]]]) -> dict[str, Any]:
    if len(replicates) != 3:
        raise AnalysisRefusal("exactly three spectral paired replicates required")
    if any(tuple(row) != CONTRAST_IDS for row in replicates):
        raise AnalysisRefusal("spectral contrast set/order drift")
    out: dict[str, Any] = {}
    for contrast_id in CONTRAST_IDS:
        if any(len(row[contrast_id]) != 8001 for row in replicates):
            raise AnalysisRefusal("spectral contrast node-count drift")
        mean: list[float | None] = []
        sd: list[float | None] = []
        se: list[float | None] = []
        unresolved: list[int] = []
        for i in range(8001):
            summary = summarize_three([row[contrast_id][i] for row in replicates])
            mean.append(summary["mean"])
            sd.append(summary["sampleStd"])
            se.append(summary["standardError"])
            if summary["status"] != "FINITE_THREE_REPLICATES":
                unresolved.append(i)
        out[contrast_id] = {
            "meanLogRatio": mean,
            "sampleStdLogRatio": sd,
            "standardErrorLogRatio": se,
            "unresolvedNodeIndices": unresolved,
            "wavelengthGrid": {"startNm": 380.0, "stopNm": 780.0, "stepNm": 0.05, "nodeCount": 8001},
            "inferentialPValueOrConfidenceIntervalPermitted": False,
            "epsilonSubstitutionPermitted": False,
        }
    return out


def review_summary() -> dict[str, Any]:
    assert_frozen_contract_bindings()
    base = source_analysis()
    return {
        "status": "PASS_AFPF_ANALYSIS_IMPLEMENTATION_BINDINGS",
        "stateCount": len(STATE_IDS),
        "contrastCount": len(CONTRASTS),
        "primaryChannels": list(PRIMARY_CHANNELS),
        "r8PrimaryChannelsMatch": tuple(base.PRIMARY_CHANNELS) == PRIMARY_CHANNELS,
        "rawSpectrumNodeCount": 8001,
        "pValuesPermitted": False,
        "confidenceIntervalsPermitted": False,
        "epsilonSubstitutionPermitted": False,
        "scientificExecutionAuthorized": False,
        "resultOpeningAuthorized": False,
    }


if __name__ == "__main__":
    print(json.dumps(review_summary(), sort_keys=True))
