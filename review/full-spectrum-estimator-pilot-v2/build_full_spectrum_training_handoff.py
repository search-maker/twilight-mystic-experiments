#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import statistics
import zipfile
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
STAGE_ID = "public-tier1-full-spectrum-training-handoff-v1"
PROTOCOL_ID = "public-tier1-full-spectrum-derived-channel-handoff-v1"

TRAINING_IDS = tuple(f"train-{i:04d}" for i in range(1, 49) if i % 5 != 0)
HOLDOUT_IDS = tuple(f"train-{i:04d}" for i in range(1, 49) if i % 5 == 0)
WAVE1_TRAINING_IDS = (
    "train-0003", "train-0007", "train-0009", "train-0011", "train-0013",
    "train-0017", "train-0019", "train-0023", "train-0027", "train-0029",
    "train-0031", "train-0033", "train-0039", "train-0041", "train-0043",
    "train-0046", "train-0047",
)
WAVE2_TRAINING_IDS = (
    "train-0003", "train-0007", "train-0009", "train-0011", "train-0013",
    "train-0019", "train-0023", "train-0027", "train-0029", "train-0031",
    "train-0039", "train-0041", "train-0043", "train-0047",
)
WAVE3_TRAINING_IDS = (
    "train-0003", "train-0007", "train-0011", "train-0013", "train-0019",
    "train-0023", "train-0027", "train-0029", "train-0031", "train-0039",
    "train-0041", "train-0043", "train-0047",
)

KM_PHOTOPIC = 683.002
KM_SCOTOPIC = 1700.06
CIE_WL = tuple(float(w) for w in range(380, 781, 10))
V_PHOT = (
    0.00004, 0.00012, 0.0004, 0.0012, 0.0040, 0.0116, 0.023, 0.038,
    0.060, 0.09098, 0.13902, 0.20802, 0.323, 0.503, 0.710, 0.862,
    0.954, 0.99495, 0.995, 0.952, 0.870, 0.757, 0.631, 0.503, 0.381,
    0.265, 0.175, 0.107, 0.061, 0.032, 0.017, 0.00821, 0.004102,
    0.002091, 0.001047, 0.00052, 0.000249, 0.00012, 0.00006, 0.00003,
    0.000015,
)
V_SCOT = (
    0.000589, 0.002209, 0.00929, 0.03484, 0.0966, 0.1998, 0.3281,
    0.455, 0.567, 0.676, 0.793, 0.904, 0.982, 0.997, 0.935, 0.811,
    0.650, 0.481, 0.3288, 0.2076, 0.1212, 0.0655, 0.03315, 0.01593,
    0.00737, 0.003335, 0.001497, 0.000677, 0.0003129, 0.000148,
    0.0000715, 0.00003533, 0.0000178, 0.00000914, 0.00000478,
    0.000002546, 0.000001379, 0.00000076, 0.000000425, 0.000000241,
    0.000000139,
)
BESSELL_V = (
    (470.0, 0.0), (480.0, 0.03), (490.0, 0.163), (500.0, 0.458),
    (510.0, 0.78), (520.0, 0.967), (530.0, 1.0), (540.0, 0.973),
    (550.0, 0.898), (560.0, 0.792), (570.0, 0.684), (580.0, 0.574),
    (590.0, 0.461), (600.0, 0.359), (610.0, 0.27), (620.0, 0.197),
    (630.0, 0.135), (640.0, 0.081), (650.0, 0.045), (660.0, 0.025),
    (670.0, 0.017), (680.0, 0.013), (690.0, 0.009), (700.0, 0.0),
)
OMEGA_ARCSEC2_SR = (math.pi / 180.0 / 3600.0) ** 2
F_LAMBDA_V0_MW = 3.63e-8
CASE_RE = re.compile(r"^(train-\d{4}).*-b([1-8])$")


def canonical_sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def raw_sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def expected_blocks(geometry_id: str) -> tuple[int, ...]:
    blocks = [1, 2]
    if geometry_id in WAVE1_TRAINING_IDS:
        blocks += [3, 4]
    if geometry_id in WAVE2_TRAINING_IDS:
        blocks += [5, 6]
    if geometry_id in WAVE3_TRAINING_IDS:
        blocks += [7, 8]
    return tuple(blocks)


def expected_case_keys() -> tuple[tuple[str, int], ...]:
    return tuple((gid, block) for gid in TRAINING_IDS for block in expected_blocks(gid))


def interp(table: tuple[float, ...], wavelength: float) -> float:
    if wavelength <= CIE_WL[0]:
        return table[0] if wavelength >= CIE_WL[0] else 0.0
    if wavelength >= CIE_WL[-1]:
        return table[-1] if wavelength <= CIE_WL[-1] else 0.0
    x = (wavelength - 380.0) / 10.0
    i = int(math.floor(x))
    f = x - i
    return table[i] * (1.0 - f) + table[i + 1] * f


def bessell_response(wavelength: float) -> float:
    if wavelength < BESSELL_V[0][0] or wavelength > BESSELL_V[-1][0]:
        return 0.0
    x = (wavelength - 470.0) / 10.0
    i = int(math.floor(x))
    if i >= len(BESSELL_V) - 1:
        return BESSELL_V[-1][1]
    f = x - i
    return BESSELL_V[i][1] * (1.0 - f) + BESSELL_V[i + 1][1] * f


def parse_spc(raw: bytes) -> tuple[list[float], list[float]]:
    wl: list[float] = []
    rad: list[float] = []
    for line in raw.decode(errors="strict").splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            wavelength = float(parts[0])
            value = float(parts[-1])
        except ValueError:
            continue
        if not math.isfinite(wavelength) or not math.isfinite(value) or value < 0:
            raise ValueError("raw spectrum contains invalid wavelength/radiance")
        wl.append(wavelength)
        rad.append(value)
    if len(wl) != 8001 or abs(wl[0] - 380.0) > 1e-6 or abs(wl[-1] - 780.0) > 1e-6:
        raise ValueError(f"expected exact 8001-point 380..780 spectrum, got {len(wl)} {wl[:1]} {wl[-1:]}")
    if any(wl[i + 1] <= wl[i] for i in range(len(wl) - 1)):
        raise ValueError("wavelength grid is not strictly increasing")
    return wl, rad


def trap_weighted(wl: list[float], rad: list[float], weight_at, km: float) -> float:
    total = 0.0
    for i in range(len(wl) - 1):
        dl = wl[i + 1] - wl[i]
        total += 0.5 * (weight_at(wl[i]) * rad[i] + weight_at(wl[i + 1]) * rad[i + 1]) * dl
    return km * total * 1e-3


def johnson_effective(wl: list[float], rad: list[float]) -> float:
    num = den = 0.0
    for i in range(len(wl) - 1):
        dl = wl[i + 1] - wl[i]
        a = bessell_response(wl[i]) * wl[i]
        b = bessell_response(wl[i + 1]) * wl[i + 1]
        num += 0.5 * (a * rad[i] + b * rad[i + 1]) * dl
        den += 0.5 * (a + b) * dl
    if den <= 0:
        raise ValueError("Johnson V passband has zero support")
    return num / den


def find_one(names: list[str], suffix: str) -> str:
    matches = [name for name in names if name.endswith(suffix)]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {suffix}, found {matches}")
    return matches[0]


def find_prepared(names: list[str]) -> str:
    matches = [name for name in names if name.endswith("tier1-prepared.json") or name.endswith("prepared.json")]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one prepared metadata file, found {matches}")
    return matches[0]


def parse_rendered_input(raw: bytes) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for line in raw.decode(errors="strict").splitlines():
        parts = line.split()
        if not parts:
            continue
        key = parts[0]
        if key == "sza" and len(parts) >= 2:
            values["sunDepressionDeg"] = float(parts[1]) - 90.0
        elif key == "umu" and len(parts) >= 2:
            mu = max(-1.0, min(1.0, abs(float(parts[1]))))
            values["targetAltitudeDeg"] = math.degrees(math.asin(mu))
        elif key == "phi" and len(parts) >= 2:
            values["relativeAzimuthDeg"] = float(parts[1])
        elif key == "aerosol_set_tau_at_wvl" and len(parts) >= 3 and abs(float(parts[1]) - 550.0) < 1e-9:
            values["aod550"] = float(parts[2])
        elif key == "atm_z_grid" and len(parts) >= 2:
            values["observerElevationM"] = float(parts[1]) * 1000.0
        elif key == "albedo" and len(parts) >= 2:
            values["albedo"] = float(parts[1])
        elif key == "mc_spectral_is" and len(parts) >= 2:
            values["alisSpectralImportanceSamplingNm"] = float(parts[1])
        elif key == "mc_photons" and len(parts) >= 2:
            values["photonHistories"] = int(parts[1])
        elif key == "mc_randomseed" and len(parts) >= 2:
            values["seed"] = int(parts[1])
        elif key == "wavelength" and len(parts) >= 3:
            values["wavelengthDomainNm"] = [float(parts[1]), float(parts[2])]
        elif key == "mc_spherical" and len(parts) >= 2:
            values["mcSpherical"] = parts[1]
    required = {
        "sunDepressionDeg", "targetAltitudeDeg", "relativeAzimuthDeg",
        "aod550", "observerElevationM", "albedo",
        "alisSpectralImportanceSamplingNm", "photonHistories", "seed",
        "wavelengthDomainNm", "mcSpherical",
    }
    missing = sorted(required - set(values))
    if missing:
        raise ValueError(f"rendered input is missing required physical fields: {missing}")
    values["method"] = "alis"
    return values


def expected_result_stage(block: int) -> str:
    if block in (1, 2):
        return "mystic-batch-v1"
    if block in (3, 4):
        return "tier1-precision-continuation-wave1-ordinal11-execution-v5"
    if block in (5, 6):
        return "tier1-precision-continuation-wave2-ordinal12-execution-v1"
    if block in (7, 8):
        return "tier1-precision-continuation-wave3-ordinal13-execution-v1"
    raise ValueError(f"unsupported block: {block}")


def parse_case(zip_path: Path) -> dict[str, Any]:
    zip_bytes = zip_path.read_bytes()
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        result_name = find_one(names, "case-result.json")
        prepared_name = find_prepared(names)
        input_name = find_one(names, "input-resolved.txt")
        spectrum_name = find_one(names, "mc.rad.spc")
        std_name = find_one(names, "mc.rad.std.spc")
        result_raw = zf.read(result_name)
        prepared_raw = zf.read(prepared_name)
        input_raw = zf.read(input_name)
        spectrum_raw = zf.read(spectrum_name)
        std_raw = zf.read(std_name)
    result = json.loads(result_raw)
    prepared = json.loads(prepared_raw)
    case_id = result.get("caseId") or prepared.get("caseId")
    match = CASE_RE.match(str(case_id))
    if not match:
        raise ValueError(f"unsupported case identity: {case_id}")
    geometry_id, block_text = match.groups()
    block = int(block_text)
    if prepared.get("groupId") != geometry_id or int(prepared.get("block")) != block:
        raise ValueError(f"prepared identity mismatch: {case_id}")
    role = result.get("role", prepared.get("role"))
    if role != "surrogate-training":
        raise ValueError(f"non-training case refused: {case_id} role={role}")
    if geometry_id not in TRAINING_IDS or block not in expected_blocks(geometry_id):
        raise ValueError(f"case outside frozen training/block plan: {case_id}")
    if result.get("status") != "COMPLETED":
        raise ValueError(f"case not completed: {case_id}")
    if result.get("stageId") != expected_result_stage(block):
        raise ValueError(f"unexpected result stage for {case_id}: {result.get('stageId')}")
    if result.get("syntaxCheckCount") != 1 or result.get("solverExecutionCount") != 1:
        raise ValueError(f"case execution-count contract changed: {case_id}")
    if block >= 3 and (result.get("retryAllowed") is not False or result.get("resumeAllowed") is not False):
        raise ValueError(f"continuation retry/resume boundary changed: {case_id}")
    if result.get("contentSha256") is not None:
        payload = {key: value for key, value in result.items() if key != "contentSha256"}
        if result["contentSha256"] != canonical_sha(payload):
            raise ValueError(f"case-result content hash mismatch: {case_id}")
    expected_rad_hash = result.get("radianceOutputSha256")
    expected_std_hash = result.get("stdOutputSha256")
    if expected_rad_hash and raw_sha_bytes(spectrum_raw) != expected_rad_hash:
        raise ValueError(f"radiance hash mismatch: {case_id}")
    if expected_std_hash and raw_sha_bytes(std_raw) != expected_std_hash:
        raise ValueError(f"std radiance hash mismatch: {case_id}")
    actual_input_hash = raw_sha_bytes(input_raw)
    prepared_input_hash = prepared.get("inputResolvedSha256")
    result_input_hash = result.get("inputResolvedSha256", result.get("inputSha256"))
    if prepared_input_hash and actual_input_hash != prepared_input_hash:
        raise ValueError(f"prepared/input hash mismatch: {case_id}")
    if result_input_hash and actual_input_hash != result_input_hash:
        raise ValueError(f"result/input hash mismatch: {case_id}")
    rendered_inputs = parse_rendered_input(input_raw)
    if int(prepared.get("seed", rendered_inputs["seed"])) != rendered_inputs["seed"]:
        raise ValueError(f"prepared seed differs from rendered input: {case_id}")
    if int(prepared.get("photonHistories", rendered_inputs["photonHistories"])) != rendered_inputs["photonHistories"]:
        raise ValueError(f"prepared photon count differs from rendered input: {case_id}")

    wl, rad = parse_spc(spectrum_raw)
    phot = trap_weighted(wl, rad, lambda x: interp(V_PHOT, x), KM_PHOTOPIC)
    scot = trap_weighted(wl, rad, lambda x: interp(V_SCOT, x), KM_SCOTOPIC)
    jv = johnson_effective(wl, rad)
    raw_all_zero = all(value == 0.0 for value in rad)
    positive = phot > 0 and scot > 0 and jv > 0
    synthetic_v = None if jv <= 0 else -2.5 * math.log10(jv * OMEGA_ARCSEC2_SR / F_LAMBDA_V0_MW)
    std_wl, std_rad = parse_spc(std_raw)
    std_nonzero = sum(value != 0.0 for value in std_rad)
    return {
        "caseId": case_id,
        "geometryId": geometry_id,
        "block": block,
        "zipFileName": zip_path.name,
        "zipSha256": raw_sha_bytes(zip_bytes),
        "caseResultSha256": raw_sha_bytes(result_raw),
        "preparedSha256": raw_sha_bytes(prepared_raw),
        "radianceSha256": raw_sha_bytes(spectrum_raw),
        "stdRadianceSha256": raw_sha_bytes(std_raw),
        "inputs": rendered_inputs,
        "channels": {
            "photopicLuminanceCdM2": phot,
            "scotopicLuminanceScotCdM2": scot,
            "johnsonVEffectiveRadiance_mW_m2_nm_sr": jv,
            "scotopicPhotopicRatio": (scot / phot) if phot > 0 else None,
            "syntheticJohnsonVMagArcsec2": synthetic_v,
        },
        "rawAllZero": raw_all_zero,
        "positivePrimaryChannels": positive,
        "mcStdSpectrumNonzeroSampleCount": std_nonzero,
        "mcStdSpectrumUsableForFullChannelUncertainty": False,
    }


def channel_stats(values: list[float], zero_present: bool) -> dict[str, Any]:
    mean = statistics.fmean(values)
    sample_std = statistics.stdev(values) if len(values) >= 2 else None
    if zero_present:
        rsem = None
        status = "NOT_COMPUTED_ZERO_HIT_PRESENT"
    elif sample_std is None or mean <= 0:
        rsem = None
        status = "NOT_COMPUTED"
    else:
        rsem = sample_std / math.sqrt(len(values)) / mean
        status = "COMPUTED_FROM_INDEPENDENT_BLOCK_SCATTER"
    return {
        "blockCount": len(values),
        "mean": mean,
        "sampleStd": sample_std,
        "relativeStandardErrorOfMean": rsem,
        "relativeStandardErrorStatus": status,
    }


def aggregate(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for case in cases:
        grouped.setdefault(case["geometryId"], []).append(case)
    output: list[dict[str, Any]] = []
    for geometry_id in sorted(grouped):
        rows = sorted(grouped[geometry_id], key=lambda row: row["block"])
        blocks = tuple(row["block"] for row in rows)
        if blocks != expected_blocks(geometry_id):
            raise ValueError(f"incomplete block set for {geometry_id}: {blocks}")
        first_inputs = rows[0]["inputs"]
        invariant_keys = (
            "sunDepressionDeg", "targetAltitudeDeg", "relativeAzimuthDeg",
            "observerElevationM", "aod550", "albedo", "method",
        )
        for row in rows[1:]:
            if any(row["inputs"].get(key) != first_inputs.get(key) for key in invariant_keys):
                raise ValueError(f"physical geometry changed across blocks: {geometry_id}")
        zero_present = any(row["rawAllZero"] for row in rows)
        phot_values = [row["channels"]["photopicLuminanceCdM2"] for row in rows]
        scot_values = [row["channels"]["scotopicLuminanceScotCdM2"] for row in rows]
        jv_values = [row["channels"]["johnsonVEffectiveRadiance_mW_m2_nm_sr"] for row in rows]
        phot = channel_stats(phot_values, zero_present)
        scot = channel_stats(scot_values, zero_present)
        jv = channel_stats(jv_values, zero_present)
        sp = scot["mean"] / phot["mean"] if phot["mean"] > 0 else None
        output.append({
            "geometryId": geometry_id,
            "role": "surrogate-training",
            "geometry": {key: first_inputs.get(key) for key in invariant_keys},
            "caseIds": [row["caseId"] for row in rows],
            "blocks": list(blocks),
            "zeroHitCaseIds": [row["caseId"] for row in rows if row["rawAllZero"]],
            "channels": {
                "photopicLuminanceCdM2": phot,
                "scotopicLuminanceScotCdM2": scot,
                "johnsonVEffectiveRadiance_mW_m2_nm_sr": jv,
                "scotopicPhotopicRatioDerivedFromMeans": sp,
            },
            "caseEvidenceSha256": canonical_sha([
                {
                    "caseId": row["caseId"],
                    "zipSha256": row["zipSha256"],
                    "radianceSha256": row["radianceSha256"],
                    "preparedSha256": row["preparedSha256"],
                }
                for row in rows
            ]),
        })
    return output


def build(paths: list[Path], protocol_sha256: str, allow_partial_smoke: bool) -> dict[str, Any]:
    cases = [parse_case(path) for path in paths]
    keys = [(case["geometryId"], case["block"]) for case in cases]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate geometry/block artifact")
    expected = set(expected_case_keys())
    present = set(keys)
    if not allow_partial_smoke and present != expected:
        missing = sorted(expected - present)
        extra = sorted(present - expected)
        raise ValueError(f"training handoff must contain exact 166-case universe; missing={missing[:10]} extra={extra[:10]}")
    if allow_partial_smoke:
        records = []
        # For partial smoke, aggregate only geometries whose complete planned block set
        # is present in the supplied subset. This never sets trainingHandoffComplete.
        by_gid = {gid for gid, _ in present}
        complete_paths: list[dict[str, Any]] = []
        for gid in by_gid:
            if set((gid, b) for b in expected_blocks(gid)).issubset(present):
                complete_paths.extend(case for case in cases if case["geometryId"] == gid)
        records = aggregate(complete_paths) if complete_paths else []
    else:
        records = aggregate(cases)
    value: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "stageId": STAGE_ID,
        "status": "COMPLETE_TRAINING_ONLY_HANDOFF" if not allow_partial_smoke else "PARTIAL_SMOKE_ONLY",
        "protocolId": PROTOCOL_ID,
        "protocolSha256": protocol_sha256,
        "trainingGeometryIds": list(TRAINING_IDS),
        "internalHoldoutGeometryIdsExcluded": list(HOLDOUT_IDS),
        "holdoutValuesRead": False,
        "holdoutRecordCount": 0,
        "expectedTrainingCaseArtifactCount": len(expected),
        "observedCaseArtifactCount": len(cases),
        "trainingHandoffComplete": not allow_partial_smoke and len(records) == 39,
        "fullSpectrumPrimary": True,
        "fittedChannelsAuthorized": False,
        "modelSelectionAuthorized": False,
        "scientificExecutionPerformed": False,
        "productionAuthorization": False,
        "mcStdSpectrumPolicy": (
            "retain for audit only; ALIS std spectrum is not treated as a complete full-channel covariance estimator; "
            "primary geometry label uncertainty is independent block-to-block scatter"
        ),
        "records": records,
        "caseEvidence": cases,
    }
    value["datasetSha256"] = canonical_sha(value)
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-partial-smoke", action="store_true")
    parser.add_argument("artifacts", nargs="+", type=Path)
    args = parser.parse_args()
    protocol = json.loads(args.protocol.read_text())
    supplied = protocol.get("protocolSha256")
    payload = {k: v for k, v in protocol.items() if k != "protocolSha256"}
    if supplied != canonical_sha(payload):
        raise SystemExit("protocol self-hash mismatch")
    result = build(args.artifacts, supplied, args.allow_partial_smoke)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({
        "status": result["status"],
        "observedCaseArtifactCount": result["observedCaseArtifactCount"],
        "recordCount": len(result["records"]),
        "datasetSha256": result["datasetSha256"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
