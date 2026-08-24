import hashlib
import itertools
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "review" / "aerosol-scenario-transport-validation-v1" / "protocol-v1.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def git_blob_sha1(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(f"blob {len(raw)}\0".encode("ascii") + raw).hexdigest()


def radical_inverse(index: int, base: int) -> float:
    result = 0.0
    factor = 1.0 / base
    while index:
        index, digit = divmod(index, base)
        result += digit * factor
        factor /= base
    return result


def idw_coords(g):
    return (
        (g["sunDepressionDeg"] - 2.0) / 8.5,
        (g["targetAltitudeDeg"] - 5.0) / 75.0,
        (math.cos(math.radians(g["relativeAzimuthDeg"])) + 1.0) / 2.0,
        g["observerElevationM"] / 2500.0,
        (g["aod550"] - 0.05) / 0.35,
    )


def distance(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def row_dicts(protocol):
    design = protocol["exactNewGeometryDesign"]
    columns = [
        "geometryId", "haltonIndex", "role", "sunDepressionDeg",
        "targetAltitudeDeg", "relativeAzimuthDeg", "observerElevationM",
        "aod550", "photonHistoriesPerCase",
        "baseLevelBNearestTrainingDistance",
        "nearestAerosolTransferTrainingDistance",
    ]
    rows = design["geometryRows"]
    assert design["geometryRowColumns"] == columns
    return [dict(zip(columns, row)) for row in rows]


def historical_afpf_geometries():
    out = []
    for sun in (2.0, 4.0, 6.0, 8.0):
        for aod in (0.10, 0.30):
            for alt, az in ((10.0, 30.0), (30.0, 90.0), (45.0, 180.0)):
                out.append({
                    "sunDepressionDeg": sun,
                    "targetAltitudeDeg": alt,
                    "relativeAzimuthDeg": az,
                    "observerElevationM": 0.0,
                    "aod550": aod,
                })
    return out


def boundary_flags(gs):
    return (
        any(g["sunDepressionDeg"] <= 4.0 for g in gs),
        any(8.5 <= g["sunDepressionDeg"] <= 10.5 for g in gs),
        any(g["relativeAzimuthDeg"] <= 60.0 for g in gs),
        any(g["relativeAzimuthDeg"] >= 150.0 for g in gs),
        any(g["targetAltitudeDeg"] <= 20.0 for g in gs),
        any(g["targetAltitudeDeg"] >= 65.0 for g in gs),
        any(g["aod550"] <= 0.10 for g in gs),
        any(g["aod550"] >= 0.35 for g in gs),
        any(g["observerElevationM"] <= 500.0 for g in gs),
        any(g["observerElevationM"] >= 2000.0 for g in gs),
    )


def test_astv_v1_preregistration_is_exact_geometry_only_and_fail_closed():
    p = load(PROTOCOL)
    assert p["status"] == "REVIEW_ONLY_PREREGISTRATION_NO_SCIENTIFIC_ALLOCATION_NO_RESULT_OPENING"
    assert p["sourceMainAtFreeze"] == "a8c9c2deca7754ce3cdff51cccc3a1780f4b79c1"

    # Every repository-local source identity is byte-bound.
    for key, binding in p["sourceBindings"].items():
        if not isinstance(binding, dict) or "path" not in binding:
            continue
        assert git_blob_sha1(ROOT / binding["path"]) == binding["gitBlobSha1"], key

    design = p["exactNewGeometryDesign"]
    rows = row_dicts(p)
    assert len(rows) == 24
    assert [r["haltonIndex"] for r in rows] == list(range(1, 25))

    # Reproduce the exact first-24 Halton geometry matrix from geometry only.
    dims = ("sunDepressionDeg", "targetAltitudeDeg", "relativeAzimuthDeg", "observerElevationM", "aod550")
    bases = tuple(design["haltonBases"])
    assert bases == (2, 3, 5, 7, 11)
    for row in rows:
        idx = row["haltonIndex"]
        for dim, base in zip(dims, bases):
            lo, hi = design["targetRanges"][dim]
            expected = round(lo + (hi - lo) * radical_inverse(idx, base), design["roundDecimals"])
            assert row[dim] == expected, (row["geometryId"], dim, row[dim], expected)
        expected_photons = 20_000_000 if row["sunDepressionDeg"] <= 8.0 else 50_000_000
        assert row["photonHistoriesPerCase"] == expected_photons
        assert row["baseLevelBNearestTrainingDistance"] <= 0.60

    training = [r for r in rows if r["role"] == "transport-training"]
    holdout = [r for r in rows if r["role"] == "fresh-validation-holdout"]
    assert len(training) == 18
    assert len(holdout) == 6
    assert [r["haltonIndex"] for r in holdout] == [1, 6, 8, 21, 23, 24]
    assert all(boundary_flags(holdout))
    assert all(r["nearestAerosolTransferTrainingDistance"] <= 0.60 for r in holdout)
    assert all(r["nearestAerosolTransferTrainingDistance"] is None for r in training)

    # Recompute the geometry-only holdout objective. No MYSTIC/model result enters it.
    coords = [idw_coords(r) for r in rows]
    hist = [idw_coords(g) for g in historical_afpf_geometries()]
    best_score = None
    best_combo = None
    for combo in itertools.combinations(range(24), 6):
        hs = [rows[i] for i in combo]
        if not all(boundary_flags(hs)):
            continue
        remaining = [j for j in range(24) if j not in combo]
        nearest_training = []
        feasible = True
        for h in combo:
            d = min(
                min(distance(coords[h], x) for x in hist),
                min(distance(coords[h], coords[j]) for j in remaining),
            )
            if d > 0.60 + 1e-12:
                feasible = False
                break
            nearest_training.append(d)
        if not feasible:
            continue
        pair = [distance(coords[a], coords[b]) for a, b in itertools.combinations(combo, 2)]
        score = (min(pair), sum(pair) / len(pair), -max(nearest_training))
        ids = tuple(rows[i]["geometryId"] for i in combo)
        if best_score is None or score > best_score or (score == best_score and ids < best_combo[1]):
            best_score = score
            best_combo = (combo, ids)
    assert tuple(i + 1 for i in best_combo[0]) == (1, 6, 8, 21, 23, 24)

    # Cardinalities and photon budget are frozen before any scientific identity exists.
    assert p["newSciencePlan"]["trainingStageCaseCount"] == 18 * 5 * 3 == 270
    assert p["newSciencePlan"]["holdoutStageCaseCount"] == 6 * 5 * 3 == 90
    assert p["newSciencePlan"]["maximumNewCaseCount"] == 360
    train_hist = sum(r["photonHistoriesPerCase"] * 15 for r in training)
    hold_hist = sum(r["photonHistoriesPerCase"] * 15 for r in holdout)
    assert train_hist == p["newSciencePlan"]["trainingStageConfiguredPhotonHistories"] == 7_650_000_000
    assert hold_hist == p["newSciencePlan"]["holdoutStageConfiguredPhotonHistories"] == 2_250_000_000
    assert train_hist + hold_hist == p["newSciencePlan"]["maximumConfiguredPhotonHistories"] == 9_900_000_000
    assert p["newSciencePlan"]["holdoutExecutionConditionalOnFrozenTrainingReadinessPass"] is True
    assert p["newSciencePlan"]["holdoutValuesMayNotBeOpenedForTrainingReadiness"] is True

    # The interpolation family is fixed, not selected from outcomes.
    interp = p["interpolator"]
    assert interp["kind"] == "VECTOR_VALUED_IDW"
    assert interp["coordinateSystem"] == "V1_IDW_COS_COORDINATES"
    assert interp["neighbors"] == 6
    assert interp["power"] == 1.0
    assert interp["hyperparameterSelectionFromNewValuesAllowed"] is False
    assert interp["modelFamilySelectionAllowed"] is False
    assert interp["supportNearestTrainingDistanceMaxInclusive"] == 0.60

    # Acceptance limits must be exactly inherited from the pre-existing Level-B v3 fresh-validation contract.
    levelb = load(ROOT / p["sourceBindings"]["levelBV3FreshValidationThresholdContract"]["path"])["modelAndEvaluation"]
    gates = p["trainingReadinessBeforeHoldoutExecution"]
    assert gates["positiveChannelGatesAppliedSeparatelyToEachOfThreeChannels"] == {
        "absoluteMeanSignedLogBiasMax": levelb["positiveChannelAbsoluteMeanSignedLogBiasMax"],
        "medianAbsoluteLogErrorMax": levelb["positiveChannelMedianAbsoluteLogErrorMax"],
        "worstAbsoluteLogErrorMax": levelb["positiveChannelWorstAbsoluteLogErrorMax"],
    }
    assert gates["shapeGates"] == {
        "medianPerCaseNrmseMax": levelb["shapeMedianPerCaseNrmseMax"],
        "worstPerCaseNrmseMax": levelb["shapeWorstPerCaseNrmseMax"],
        "worstSingleCoefficientNormalizedErrorMax": levelb["shapeWorstSingleCoefficientNormalizedErrorMax"],
    }
    assert gates["trainingOnlyInterpolationPadding"]["mustNotExceed"] == levelb["positiveChannelWorstAbsoluteLogErrorMax"]
    assert p["freshHoldoutEvaluation"]["trainingCalibratedPrimaryEnvelopeContainment"]["requiredDirectHoldoutStateContainmentFraction"] == 1.0
    assert p["freshHoldoutEvaluation"]["levelBLimitingMagnitude"]["newNumericalMagnitudeToleranceIntroduced"] is False

    # Absolute closed boundary: review cannot allocate or execute ordinal 39.
    identity = p["candidateScientificIdentity"]
    assert identity["candidateOrdinal"] == 39
    assert identity["scientificOrdinalAllocated"] is False
    assert identity["authorizationCreated"] is False
    assert identity["dispatchCreated"] is False
    assert identity["automaticDispatch"] is False
    assert identity["solverExecutionAuthorized"] is False
    assert identity["resultOpeningAuthorized"] is False
    assert p["newSciencePlan"]["seedValuesFrozenOrAllocatedNow"] is False
    assert p["newSciencePlan"]["githubRerunAllowed"] is False
    assert p["newSciencePlan"]["retryAllowed"] is False
    assert p["newSciencePlan"]["resumeAllowed"] is False
    assert p["transferRepresentation"]["epsilonSubstitutionAllowed"] is False
    assert p["successBoundary"]["successDoesNotAuthorizeProduction"] is True
    assert p["successBoundary"]["successDoesNotAuthorizeStarsvisibilityMutation"] is True
