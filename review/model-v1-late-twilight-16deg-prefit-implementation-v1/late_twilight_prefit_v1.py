#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

import numpy as np

OPEN_LABEL_PATH = "review/full-spectrum-estimator-pilot-v2/full-spectrum-training-admission-complete-v1.json"
OPEN_LABEL_BLOB = "c136f23f7df68b1481cb5ff939646198a3e336fe"
GEOMETRY_GENERATOR_PATH = "review/tier2-core-campaign-contract-v1/validate_tier2_core_campaign_contract_v1.py"
GEOMETRY_GENERATOR_BLOB = "0b6aa0bf18b85ee270d2c6c459eb5779a0cfdb40"
CHANNELS = (
    "photopicLuminanceCdM2",
    "scotopicLuminanceScotCdM2",
    "johnsonVEffectiveRadiance_mW_m2_nm_sr",
)
ADMITTED_IDS = frozenset(("train-0009", "train-0021"))
UNCERTAINTY_CANDIDATE_IDS = frozenset((
    "train-0003", "train-0007", "train-0011", "train-0013", "train-0019",
    "train-0027", "train-0029", "train-0037", "train-0041", "train-0043",
))
EXPECTED_LATE_REPORT_IDS = ADMITTED_IDS | UNCERTAINTY_CANDIDATE_IDS
ADMITTED_NU = {"train-0009": 5, "train-0021": 1}
MODEL_DISCREPANCY_SIGMA_LOG = 0.12
RIDGE_VALUES = (1e-5, 1e-4, 1e-3, 1e-2, 1e-1)
OOD_THRESHOLD_CAP = 0.6
LATE_MIN_EXCLUSIVE = 10.5
LATE_MAX_INCLUSIVE = 16.0


class Refusal(RuntimeError):
    pass


def req(condition: bool, message: str) -> None:
    if not condition:
        raise Refusal(message)


def git_blob_sha(raw: bytes) -> str:
    header = f"blob {len(raw)}\0".encode("ascii")
    return hashlib.sha1(header + raw).hexdigest()


def _finite(x: Any) -> float:
    y = float(x)
    req(math.isfinite(y), "nonfinite numeric value")
    return y


def radical_inverse(index: int, base: int) -> float:
    req(index >= 0 and base >= 2, "invalid radical inverse arguments")
    result = 0.0
    factor = 1.0 / base
    i = int(index)
    while i:
        i, digit = divmod(i, base)
        result += digit * factor
        factor /= base
    return result


def geometry_from_id(geometry_id: str) -> dict[str, float | int | str]:
    m = re.fullmatch(r"train-(\d{4})", str(geometry_id))
    req(m is not None, f"invalid geometry id: {geometry_id}")
    source_index = int(m.group(1))
    req(source_index % 5 != 0, f"protected geometry id refused: {geometry_id}")
    specs = (
        ("sunDepressionDeg", 2, 2.0, 18.0),
        ("targetAltitudeDeg", 3, 5.0, 80.0),
        ("relativeAzimuthDeg", 5, 0.0, 180.0),
        ("observerElevationM", 7, 0.0, 2500.0),
        ("aod550", 11, 0.05, 0.4),
    )
    out: dict[str, float | int | str] = {"geometryId": geometry_id, "sourceIndex": source_index}
    for key, base, lo, hi in specs:
        out[key] = round(lo + (hi - lo) * radical_inverse(source_index, base), 6)
    return out


def distance_coordinates(g: dict[str, Any]) -> np.ndarray:
    sun = _finite(g["sunDepressionDeg"])
    alt = _finite(g["targetAltitudeDeg"])
    az = _finite(g["relativeAzimuthDeg"])
    elev = _finite(g["observerElevationM"])
    aod = _finite(g["aod550"])
    return np.asarray((
        (sun - 2.0) / 14.0,
        (alt - 5.0) / 75.0,
        (math.cos(math.radians(az)) + 1.0) / 2.0,
        elev / 2500.0,
        (aod - 0.05) / 0.35,
    ), dtype=np.float64)


def raw_cos_coordinates(g: dict[str, Any]) -> np.ndarray:
    d = distance_coordinates(g)
    return np.asarray((d[0], d[1], 2.0 * d[2] - 1.0, d[3], d[4]), dtype=np.float64)


def physical_coordinates(g: dict[str, Any]) -> np.ndarray:
    sun = _finite(g["sunDepressionDeg"])
    alt = _finite(g["targetAltitudeDeg"])
    az = _finite(g["relativeAzimuthDeg"])
    elev = _finite(g["observerElevationM"])
    aod = _finite(g["aod550"])
    req(aod > 0.0, "positive AOD required")
    return np.asarray((
        (sun - 2.0) / 14.0,
        math.sin(math.radians(alt)),
        math.cos(math.radians(az)),
        elev / 2500.0,
        math.log(aod / 0.05) / math.log(8.0),
    ), dtype=np.float64)


def _poly2(v: np.ndarray) -> np.ndarray:
    out = [1.0, *v.tolist()]
    for i in range(len(v)):
        for j in range(i, len(v)):
            out.append(float(v[i] * v[j]))
    return np.asarray(out, dtype=np.float64)


def basis(g: dict[str, Any], basis_name: str) -> np.ndarray:
    if basis_name == "COS_COMPACT_13_TERMS":
        s, a, c, e, o = raw_cos_coordinates(g)
        return np.asarray((1, s, a, c, e, o, s*s, a*a, c*c, s*a, s*c, s*o, a*c), dtype=np.float64)
    if basis_name == "PHYSICAL_COMPACT_16_TERMS":
        s, a, c, e, o = physical_coordinates(g)
        return np.asarray((1, s, a, c, e, o, s*s, a*a, c*c, o*o, s*a, s*c, s*o, a*c, a*o, c*o), dtype=np.float64)
    if basis_name == "FULL_DEGREE2_ON_FIVE_COS_COORDINATES_21_TERMS":
        return _poly2(raw_cos_coordinates(g))
    raise Refusal(f"unknown basis: {basis_name}")


@dataclass(frozen=True)
class ChannelLabel:
    mean: float
    log_mean: float
    measurement_sigma_log: float
    total_training_sigma_log: float
    degrees_of_freedom: int
    relative_standard_error: float


@dataclass(frozen=True)
class TrainingRow:
    geometry_id: str
    geometry: dict[str, Any]
    source_class: str
    channels: dict[str, ChannelLabel]


def _mean_rsem(values: Sequence[float]) -> tuple[float, float]:
    xs = np.asarray([_finite(x) for x in values], dtype=np.float64)
    req(len(xs) >= 2, "at least two blocks required")
    req(np.all(xs > 0.0), "strictly positive block values required; zero/nonpositive refused")
    mean = float(np.mean(xs))
    sample_sd = float(np.std(xs, ddof=1))
    sem = sample_sd / math.sqrt(len(xs))
    req(math.isfinite(mean) and mean > 0.0 and math.isfinite(sem) and sem >= 0.0, "invalid block statistics")
    rsem = sem / abs(mean)
    req(math.isfinite(rsem) and rsem >= 0.0, "invalid RSEM")
    return mean, rsem


def _channel_label(report: dict[str, Any], channel: str, admitted: bool) -> ChannelLabel:
    ch = (report.get("channels") or {}).get(channel) or {}
    values = ch.get("values") or []
    req(isinstance(values, list), f"values missing for {report.get('geometryId')} {channel}")
    if admitted:
        mean, recomputed_rsem = _mean_rsem(values)
        stored_rsem = _finite(ch.get("relativeStandardErrorOfMean"))
        req(stored_rsem >= 0.0, "negative stored RSEM")
        # The exact open source stores block values plus admitted RSEM, not a separate mean.
        # Preserve the admitted RSEM and arithmetic block mean; the recomputation is only a consistency check.
        req(abs(stored_rsem - recomputed_rsem) <= 5e-13 * max(1.0, abs(stored_rsem)), "admitted RSEM/source blocks inconsistent")
        rsem = stored_rsem
        nu = ADMITTED_NU[str(report["geometryId"])]
    else:
        block_count = int(report.get("blockCount", 0))
        req(block_count >= 4, f"blockCount={block_count} < frozen minimum 4")
        req(len(values) == block_count, "channel block count drift")
        mean, rsem = _mean_rsem(values)
        nu = block_count - 1
    measurement_sigma_log = math.log1p(rsem)
    total_sigma = math.sqrt(measurement_sigma_log**2 + MODEL_DISCREPANCY_SIGMA_LOG**2)
    return ChannelLabel(
        mean=mean,
        log_mean=math.log(mean),
        measurement_sigma_log=measurement_sigma_log,
        total_training_sigma_log=total_sigma,
        degrees_of_freedom=nu,
        relative_standard_error=rsem,
    )


def load_open_training(repo_root: Path) -> tuple[list[TrainingRow], dict[str, Any]]:
    root = Path(repo_root)
    label_raw = (root / OPEN_LABEL_PATH).read_bytes()
    generator_raw = (root / GEOMETRY_GENERATOR_PATH).read_bytes()
    req(git_blob_sha(label_raw) == OPEN_LABEL_BLOB, "open-label source blob drift")
    req(git_blob_sha(generator_raw) == GEOMETRY_GENERATOR_BLOB, "geometry-generator source blob drift")

    text = label_raw.decode("utf-8")
    raw_ids = re.findall(r"train-(\d{4})", text)
    req(raw_ids, "no geometry ids in open-label source")
    protected = sorted({f"train-{int(s):04d}" for s in raw_ids if int(s) % 5 == 0})
    req(not protected, f"protected geometry id present before JSON decode: {protected}")

    payload = json.loads(text)
    reports = payload.get("geometryReports") or []
    req(isinstance(reports, list), "geometryReports missing")
    ids = [str(x.get("geometryId")) for x in reports]
    req(len(ids) == 39 and len(set(ids)) == 39, "open-label geometry universe drift")

    late_reports: list[dict[str, Any]] = []
    for report in reports:
        gid = str(report.get("geometryId"))
        g = geometry_from_id(gid)
        sun = float(g["sunDepressionDeg"])
        if LATE_MIN_EXCLUSIVE < sun <= LATE_MAX_INCLUSIVE:
            late_reports.append(report)
    req(len(late_reports) == 12, "late-twilight report count drift")
    req({str(x.get("geometryId")) for x in late_reports} == EXPECTED_LATE_REPORT_IDS, "late-twilight report identity drift")

    rows: list[TrainingRow] = []
    refused: list[dict[str, str]] = []
    for report in sorted(late_reports, key=lambda x: str(x.get("geometryId"))):
        gid = str(report.get("geometryId"))
        admitted = gid in ADMITTED_IDS
        req(admitted or gid in UNCERTAINTY_CANDIDATE_IDS, f"unexpected late geometry: {gid}")
        try:
            labels = {ch: _channel_label(report, ch, admitted) for ch in CHANNELS}
            rows.append(TrainingRow(gid, geometry_from_id(gid), "ADMITTED" if admitted else "FINITE_UNDERPRECISION", labels))
        except Refusal as exc:
            refused.append({"geometryId": gid, "reason": str(exc)})
    req([x["geometryId"] for x in refused] == ["train-0037"], f"unexpected refused rows: {refused}")
    req(len(rows) == 11, "usable late-row count drift")
    audit = {
        "openLabelBlob": git_blob_sha(label_raw),
        "geometryGeneratorBlob": git_blob_sha(generator_raw),
        "lateReportCount": len(late_reports),
        "usableGeometryIds": [r.geometry_id for r in rows],
        "refused": refused,
    }
    return rows, audit


def late_physical_box(g: dict[str, Any], *, seam_probe: bool = False) -> bool:
    sun = _finite(g["sunDepressionDeg"])
    alt = _finite(g["targetAltitudeDeg"])
    az = _finite(g["relativeAzimuthDeg"])
    elev = _finite(g["observerElevationM"])
    aod = _finite(g["aod550"])
    sun_ok = (LATE_MIN_EXCLUSIVE < sun <= LATE_MAX_INCLUSIVE) or (seam_probe and sun == LATE_MIN_EXCLUSIVE)
    return sun_ok and 5.0 <= alt <= 80.0 and 0.0 <= az <= 180.0 and 0.0 <= elev <= 2500.0 and 0.05 <= aod <= 0.4


def calibrate_ood_threshold(rows: Sequence[TrainingRow]) -> tuple[float, float]:
    req(len(rows) >= 2, "at least two rows required")
    dists: list[float] = []
    for i, row in enumerate(rows):
        c = distance_coordinates(row.geometry)
        others = [float(np.linalg.norm(c - distance_coordinates(r.geometry))) for j, r in enumerate(rows) if j != i]
        req(others, "leave-one-out neighbors missing")
        dists.append(min(others))
    max_loo = max(dists)
    threshold = min(OOD_THRESHOLD_CAP, max_loo + 0.03)
    req(threshold <= OOD_THRESHOLD_CAP, "OOD threshold cap violated")
    return float(max_loo), float(threshold)


def support(g: dict[str, Any], rows: Sequence[TrainingRow], threshold: float, *, seam_probe: bool = False) -> tuple[bool, float, list[str]]:
    req(threshold <= OOD_THRESHOLD_CAP, "OOD threshold exceeds frozen cap")
    if not late_physical_box(g, seam_probe=seam_probe):
        return False, math.inf, []
    c = distance_coordinates(g)
    ds = [(float(np.linalg.norm(c - distance_coordinates(r.geometry))), r.geometry_id) for r in rows]
    req(ds, "training geometry required")
    nearest = min(d for d, _ in ds)
    tied = sorted(gid for d, gid in ds if abs(d - nearest) <= 1e-15)
    return nearest <= threshold, nearest, tied


FAMILIES = (
    {"familyId": "ridge-cos-compact", "basis": "COS_COMPACT_13_TERMS", "complexityRank": 1},
    {"familyId": "ridge-physical-compact", "basis": "PHYSICAL_COMPACT_16_TERMS", "complexityRank": 2},
    {"familyId": "ridge-poly2-cos", "basis": "FULL_DEGREE2_ON_FIVE_COS_COORDINATES_21_TERMS", "complexityRank": 3},
)


def _weighted_ridge(X: np.ndarray, y: np.ndarray, weights: np.ndarray, ridge: float) -> np.ndarray:
    req(X.ndim == 2 and y.ndim == 1 and weights.ndim == 1 and len(y) == X.shape[0] == len(weights), "ridge dimensions")
    req(np.all(np.isfinite(X)) and np.all(np.isfinite(y)) and np.all(np.isfinite(weights)) and np.all(weights > 0.0), "ridge nonfinite")
    sw = np.sqrt(weights)
    Xw = X * sw[:, None]
    yw = y * sw
    gram = Xw.T @ Xw
    penalty = np.eye(gram.shape[0], dtype=np.float64)
    penalty[0, 0] = 0.0
    beta = np.linalg.solve(gram + float(ridge) * penalty, Xw.T @ yw)
    req(np.all(np.isfinite(beta)), "nonfinite ridge coefficients")
    return beta


def fit_student_t_irls(rows: Sequence[TrainingRow], channel: str, basis_name: str, ridge: float) -> np.ndarray:
    req(channel in CHANNELS and ridge in RIDGE_VALUES, "unfrozen channel or ridge")
    X = np.vstack([basis(r.geometry, basis_name) for r in rows])
    y = np.asarray([r.channels[channel].log_mean for r in rows], dtype=np.float64)
    sigma = np.asarray([r.channels[channel].total_training_sigma_log for r in rows], dtype=np.float64)
    nu = np.asarray([r.channels[channel].degrees_of_freedom for r in rows], dtype=np.float64)
    beta = _weighted_ridge(X, y, 1.0 / np.square(sigma), ridge)
    for _ in range(50):
        residual = X @ beta - y
        z2 = np.square(residual / sigma)
        weights = (nu + 1.0) / (nu + z2) / np.square(sigma)
        new_beta = _weighted_ridge(X, y, weights, ridge)
        denom = max(float(np.linalg.norm(beta)), 1e-30)
        rel = float(np.linalg.norm(new_beta - beta)) / denom
        beta = new_beta
        if rel <= 1e-10:
            return beta
    raise Refusal("Student-t IRLS did not converge")


def predict_log(beta: np.ndarray, g: dict[str, Any], basis_name: str) -> float:
    y = float(basis(g, basis_name) @ beta)
    req(math.isfinite(y), "nonfinite prediction")
    return y


def student_t_nll(residual: float, sigma: float, nu: int) -> float:
    req(math.isfinite(residual) and math.isfinite(sigma) and sigma > 0 and nu > 0, "invalid Student-t term")
    return 0.5 * (nu + 1.0) * math.log1p((residual / sigma) ** 2 / nu)


def balanced_folds(rows: Sequence[TrainingRow]) -> list[tuple[str, list[int], list[int]]]:
    order = sorted(range(len(rows)), key=lambda i: rows[i].geometry_id)
    out = []
    for k in range(5):
        val = [idx for pos, idx in enumerate(order) if pos % 5 == k]
        vset = set(val)
        fit = [i for i in range(len(rows)) if i not in vset]
        out.append((f"balanced-{k}", fit, val))
    return out


def depth_folds(rows: Sequence[TrainingRow]) -> list[tuple[str, list[int], list[int], bool]]:
    bins = (
        ("depth-10p5-12p5", lambda s: 10.5 < s <= 12.5),
        ("depth-12p5-14", lambda s: 12.5 < s <= 14.0),
        ("depth-14-16", lambda s: 14.0 < s <= 16.0),
    )
    out = []
    for name, pred in bins:
        val = [i for i, r in enumerate(rows) if pred(float(r.geometry["sunDepressionDeg"]))]
        vset = set(val)
        fit = [i for i in range(len(rows)) if i not in vset]
        out.append((name, fit, val, len(val) >= 2))
    return out


def _baseline_log_mean(fit_rows: Sequence[TrainingRow], channel: str) -> float:
    ys = np.asarray([r.channels[channel].log_mean for r in fit_rows], dtype=np.float64)
    sigmas = np.asarray([r.channels[channel].total_training_sigma_log for r in fit_rows], dtype=np.float64)
    weights = 1.0 / np.square(sigmas)
    return float(np.sum(weights * ys) / np.sum(weights))


def evaluate_candidate(rows: Sequence[TrainingRow], channel: str, family: dict[str, Any], ridge: float) -> dict[str, Any]:
    fold_specs: list[tuple[str, list[int], list[int], bool, str]] = []
    for name, fit, val in balanced_folds(rows):
        fold_specs.append((name, fit, val, True, "balanced"))
    for name, fit, val, scored in depth_folds(rows):
        fold_specs.append((name, fit, val, scored, "depth"))
    fold_results = []
    oof_balanced: dict[int, float] = {}
    for name, fit_idx, val_idx, scored, kind in fold_specs:
        req(fit_idx, f"empty fit fold: {name}")
        fit_rows = [rows[i] for i in fit_idx]
        val_rows = [rows[i] for i in val_idx]
        if not val_rows:
            fold_results.append({"fold": name, "kind": kind, "count": 0, "scored": False, "nll": None, "baselineNll": None, "worstStandardizedAbsResidual": None})
            continue
        beta = fit_student_t_irls(fit_rows, channel, str(family["basis"]), float(ridge))
        baseline = _baseline_log_mean(fit_rows, channel)
        nlls = []
        bnlls = []
        std_abs = []
        for idx, row in zip(val_idx, val_rows):
            lab = row.channels[channel]
            pred = predict_log(beta, row.geometry, str(family["basis"]))
            resid = pred - lab.log_mean
            nlls.append(student_t_nll(resid, lab.total_training_sigma_log, lab.degrees_of_freedom))
            bnlls.append(student_t_nll(baseline - lab.log_mean, lab.total_training_sigma_log, lab.degrees_of_freedom))
            std_abs.append(abs(resid) / lab.total_training_sigma_log)
            if kind == "balanced":
                req(idx not in oof_balanced, "duplicate balanced OOF prediction")
                oof_balanced[idx] = resid
        fold_results.append({
            "fold": name,
            "kind": kind,
            "count": len(val_rows),
            "scored": bool(scored),
            "nll": float(np.mean(nlls)),
            "baselineNll": float(np.mean(bnlls)),
            "worstStandardizedAbsResidual": max(std_abs),
        })
    req(set(oof_balanced) == set(range(len(rows))), "balanced OOF coverage must be exactly one prediction per row")
    scored_rows = [f for f in fold_results if f["scored"] and f["nll"] is not None]
    req(scored_rows, "no scored folds")
    mean_nll = float(np.mean([f["nll"] for f in scored_rows]))
    worst_nll = max(float(f["nll"]) for f in scored_rows)
    mean_baseline = float(np.mean([f["baselineNll"] for f in scored_rows]))
    worst_std = max(float(f["worstStandardizedAbsResidual"]) for f in scored_rows)
    score = mean_nll + 0.25 * worst_nll + 0.05 * worst_std
    improvement = (mean_baseline - mean_nll) / mean_baseline if mean_baseline > 0 else -math.inf
    pooled_balanced_rms_log = math.sqrt(sum(v*v for v in oof_balanced.values()) / len(oof_balanced))
    return {
        "familyId": family["familyId"],
        "basis": family["basis"],
        "complexityRank": int(family["complexityRank"]),
        "ridge": float(ridge),
        "selectionScore": float(score),
        "meanScoredFoldNll": mean_nll,
        "worstScoredFoldNll": worst_nll,
        "meanScoredFoldBaselineNll": mean_baseline,
        "improvementFractionVsBaseline": float(improvement),
        "worstSingleStandardizedAbsResidual": worst_std,
        "balancedOofRmsLogResidual": float(pooled_balanced_rms_log),
        "folds": fold_results,
        "ready": bool(math.isfinite(score) and improvement >= 0.10),
    }


def select_candidate(rows: Sequence[TrainingRow], channel: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    evaluated: list[dict[str, Any]] = []
    for fam in FAMILIES:
        for ridge in RIDGE_VALUES:
            try:
                evaluated.append(evaluate_candidate(rows, channel, fam, ridge))
            except Refusal as exc:
                evaluated.append({
                    "familyId": fam["familyId"],
                    "basis": fam["basis"],
                    "complexityRank": int(fam["complexityRank"]),
                    "ridge": float(ridge),
                    "selectionScore": math.inf,
                    "ready": False,
                    "refused": True,
                    "refusalReason": str(exc),
                })
    evaluated.sort(key=lambda x: (x["selectionScore"], x["complexityRank"], x["familyId"], x["ridge"]))
    selected = evaluated[0]
    req(math.isfinite(float(selected["selectionScore"])) and selected.get("ready") is True, "selected candidate fails frozen readiness")
    return selected, evaluated


def fit_selected_all_rows(rows: Sequence[TrainingRow], channel: str, selected: dict[str, Any]) -> np.ndarray:
    req(selected.get("ready") is True, "all-row fit forbidden before readiness")
    family = next((f for f in FAMILIES if f["familyId"] == selected.get("familyId")), None)
    req(family is not None and selected.get("ridge") in RIDGE_VALUES, "selected candidate identity drift")
    return fit_student_t_irls(rows, channel, str(family["basis"]), float(selected["ridge"]))


def nearest_label_sigma(g: dict[str, Any], rows: Sequence[TrainingRow], channel: str) -> tuple[float, list[str]]:
    c = distance_coordinates(g)
    ds = [(float(np.linalg.norm(c - distance_coordinates(r.geometry))), r) for r in rows]
    nearest = min(d for d, _ in ds)
    tied = [r for d, r in ds if abs(d - nearest) <= 1e-15]
    # Conservative deterministic tie handling: never select a smaller sigma because of row ordering.
    sigma = max(r.channels[channel].total_training_sigma_log for r in tied)
    return float(sigma), sorted(r.geometry_id for r in tied)


def preliminary_uncertainty(g: dict[str, Any], rows: Sequence[TrainingRow], channel: str, selected: dict[str, Any]) -> dict[str, Any]:
    cv = _finite(selected["balancedOofRmsLogResidual"])
    near, tied = nearest_label_sigma(g, rows, channel)
    sigma = max(MODEL_DISCREPANCY_SIGMA_LOG, cv, near)
    return {"channelSigmaLog": sigma, "halfWidthLog": 2.0 * sigma, "nearestGeometryIds": tied}


def frozen_seam_grid() -> list[dict[str, float]]:
    return [
        {"sunDepressionDeg": 10.5, "targetAltitudeDeg": alt, "relativeAzimuthDeg": az, "observerElevationM": elev, "aod550": aod}
        for alt in (10.0, 30.0, 60.0, 80.0)
        for az in (0.0, 90.0, 180.0)
        for elev in (0.0, 1250.0, 2500.0)
        for aod in (0.05, 0.15, 0.4)
    ]


def seam_support_partition(rows: Sequence[TrainingRow], threshold: float) -> dict[str, Any]:
    supported = []
    ood = []
    for g in frozen_seam_grid():
        ok, dist, nearest = support(g, rows, threshold, seam_probe=True)
        rec = {"geometry": g, "nearestDistance": dist, "nearestGeometryIds": nearest}
        (supported if ok else ood).append(rec)
    worst = max(supported + ood, key=lambda x: x["nearestDistance"])
    return {"supported": supported, "localOod": ood, "worst": worst}


def seam_continuity(
    rows: Sequence[TrainingRow],
    threshold: float,
    late_log_predictor: Callable[[dict[str, Any], str], float],
    core_log_predictor: Callable[[dict[str, Any], str], float],
    half_width_log: Callable[[dict[str, Any], str], float],
) -> dict[str, Any]:
    part = seam_support_partition(rows, threshold)
    results = []
    for item in part["supported"]:
        g = item["geometry"]
        for channel in CHANNELS:
            late = _finite(late_log_predictor(g, channel))
            core = _finite(core_log_predictor(g, channel))
            half = _finite(half_width_log(g, channel))
            req(half >= 0.0, "negative seam envelope")
            diff = abs(late - core)
            overlap = (late - half) <= (core + MODEL_DISCREPANCY_SIGMA_LOG) and (core - MODEL_DISCREPANCY_SIGMA_LOG) <= (late + half)
            results.append({"geometry": g, "channel": channel, "absoluteLogDifference": diff, "envelopeOverlap": overlap, "pass": diff <= 0.24 and overlap})
    return {
        "supportedPointCount": len(part["supported"]),
        "localOodPointCount": len(part["localOod"]),
        "localOodDisposition": "EXPLICIT_LOCAL_OOD__NO_CONTINUITY_SCORE__NO_SUPPORT_PROMOTION",
        "results": results,
        "pass": bool(results) and all(x["pass"] for x in results),
    }
