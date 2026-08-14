#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
CONTRACT = HERE / 'contract-v1.json'
MODEL_RESULT = ROOT / 'review/level-b-v2-training-fit-result-v3-densified58/result-v3.json'
PREFIT = ROOT / 'review/level-b-v2-training-prefit-freeze-v3-densified58/protocol-v3.json'
OLD_STAGE2 = ROOT / 'review/tier2-stage2-protected-holdout-v1/contract-v1.json'
CORE = ROOT / 'review/tier2-core-campaign-contract-v1/tier2-core-campaign-contract-v1.json'
REF_ADAPTER = ROOT / 'experiments/tier2-stage2-execution-v1/adapter_v1.py'
FEATURES = ('sunDepressionDeg','targetAltitudeDeg','relativeAzimuthDeg','observerElevationM','aod550')
DATASET_FILE_SHA256 = '1cf31f1a80ce4ae1f39b9e750616093f6cfa927d10e258f81fe9fc0e58f0ea69'
DATASET_CANONICAL_SHA256 = '58c977acf84b6ce17717765c2052f7f9fd64e2965e5bf447eba5cc4accb30435'


def req(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit('REFUSED: ' + message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding='utf-8'))
    req(isinstance(value, dict), f'object required: {path}')
    return value


def canonical_sha(value: Any, drop: str | None = None) -> str:
    if drop is not None:
        value = dict(value)
        value.pop(drop, None)
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def blob(path: Path) -> str:
    return subprocess.check_output(['git','rev-parse','HEAD:' + str(path.relative_to(ROOT))], cwd=ROOT, text=True).strip()


def coord(geometry: dict[str, Any]) -> tuple[float, float, float, float, float]:
    return (
        (float(geometry['sunDepressionDeg']) - 2.0) / 8.5,
        (float(geometry['targetAltitudeDeg']) - 5.0) / 75.0,
        (math.cos(math.radians(float(geometry['relativeAzimuthDeg']))) + 1.0) / 2.0,
        float(geometry['observerElevationM']) / 2500.0,
        (float(geometry['aod550']) - 0.05) / 0.35,
    )


def dist(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    return math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))


def physical(p: tuple[float, float, float, float, float]) -> dict[str, float]:
    s,a,c,e,o = p
    return {
        'sunDepressionDeg': 2.0 + 8.5*s,
        'targetAltitudeDeg': 5.0 + 75.0*a,
        'relativeAzimuthDeg': math.degrees(math.acos(2.0*c - 1.0)),
        'observerElevationM': 2500.0*e,
        'aod550': 0.05 + 0.35*o,
    }


def close(a: float, b: float, tol: float = 1e-12) -> bool:
    return abs(float(a)-float(b)) <= tol


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--dataset', type=Path, required=True)
    args = ap.parse_args()

    c = load(CONTRACT)
    model_result = load(MODEL_RESULT)
    prefit = load(PREFIT)
    old = load(OLD_STAGE2)

    req(c['schemaVersion'] == 1, 'schema')
    req(c['contractId'] == 'level-b-v2-densified58-fresh-protected-validation-v1', 'contract id')
    req(c['status'] == 'REVIEW_ONLY_FRESH_PROTECTED_VALIDATION_PREREGISTRATION_NO_AUTHORIZATION_NO_VALUES_OPENED', 'status')
    req(c['governance'] == 'MYSTIC-STATE-0070', 'governance')
    req(canonical_sha(c, 'contractSha256') == c['contractSha256'] == '5a769740c196540079700a2665dafe278769677e262466be254978b6ee9dc1f6', 'contract self hash')
    req(c['sourceMainAtFreeze'] == '147eaca24e51fe7e2e0d8c3fb329055f28d1c586', 'source main')

    bindings = c['sourceBindings']
    expected_blobs = {
        MODEL_RESULT: '28ff90afa0de1734aa0b6718bc93ebdce1ded54a',
        PREFIT: '42a3e1cc6974c03e1f659d5f886b664cfa23cf6a',
        OLD_STAGE2: '21201753329261c4fa5df41b6593434a0b04f6c3',
        CORE: 'dc69f67829cf7412e8e9374f005d92842bd500ca',
        REF_ADAPTER: '3b6c5f84dcc9948b1e02271c8469bcc5c461af97',
    }
    for path, expected in expected_blobs.items():
        req(blob(path) == expected, f'git blob drift: {path}')
    req(bindings['trainingModelResultGitBlobSha'] == expected_blobs[MODEL_RESULT], 'model result binding')
    req(bindings['trainingPrefitProtocolGitBlobSha'] == expected_blobs[PREFIT], 'prefit binding')
    req(bindings['originalStage2ContractGitBlobSha'] == expected_blobs[OLD_STAGE2], 'old stage2 binding')
    req(bindings['tier2CoreCampaignContractGitBlobSha'] == expected_blobs[CORE], 'core campaign binding')
    req(bindings['stage2ReferenceAdapterGitBlobSha'] == expected_blobs[REF_ADAPTER], 'adapter binding')

    req(model_result['status'] == 'TRAINING_ONLY_DENSIFIED58_MODEL_FROZEN_PENDING_FRESH_VALIDATION_SOURCE', 'model result status')
    req(model_result['selectionOutcome']['modelArtifactWritten'] is True, 'frozen model missing')
    req(model_result['selectionOutcome']['modelSha256'] == bindings['modelCanonicalSha256'] == '91ae5811e55b3d4ef872ab672f006c4b383c6581a53de67cd018b6eb2666f9a7', 'model hash')
    req(model_result['selectionOutcome']['eligibleCandidateCount'] == 9 and model_result['selectionOutcome']['candidateCount'] == 230 and model_result['selectionOutcome']['cvFoldCount'] == 73, 'selection outcome drift')
    req(model_result['datasetOutcome']['ordinal22ValuesRead'] is False and model_result['scientificBoundaries']['protectedValidationOpened'] is False, 'historical protected boundary drift')
    req(prefit['protocolSha256'] == bindings['trainingPrefitProtocolSha256'], 'prefit protocol hash')

    raw = args.dataset.read_bytes()
    req(hashlib.sha256(raw).hexdigest() == DATASET_FILE_SHA256 == bindings['expandedDatasetFileSha256'], 'expanded dataset file hash')
    dataset = json.loads(raw)
    req(dataset['datasetSha256'] == DATASET_CANONICAL_SHA256 == bindings['expandedDatasetCanonicalSha256'], 'expanded dataset canonical hash')
    body = dict(dataset)
    body.pop('datasetSha256', None)
    req(canonical_sha(body) == dataset['datasetSha256'], 'expanded dataset self hash')
    req(dataset['geometryCount'] == 58 and len(dataset['records']) == 58 and dataset['protectedHoldoutRecordCount'] == 0 and dataset['ordinal22ValuesRead'] is False, 'expanded dataset role drift')

    training = [coord(r['geometry']) for r in dataset['records']]
    req(len(set(tuple(round(x,15) for x in p) for p in training)) == 58, 'training geometry duplicate')

    opened_rows = old['stage2Scope']['geometries']
    req([x['geometryId'] for x in opened_rows] == c['geometrySelection']['openedOrdinal22GeometryIds'], 'opened geometry identity drift')
    opened = [coord(x) for x in opened_rows]

    gs = c['geometrySelection']
    req(gs['targetValuesMayInfluenceSelection'] is False and gs['modelPredictionsMayInfluenceSelection'] is False and gs['openedOrdinal22TargetValuesMayInfluenceSelection'] is False and gs['trainingTargetFieldsUsed'] is False, 'geometry-only boundary opened')
    levels = tuple(float(x) for x in gs['latticeLevels'])
    req(levels == (0.1,0.3,0.5,0.7,0.9) and gs['candidateLatticeSize'] == 3125, 'lattice drift')
    candidates = []
    for p in itertools.product(levels, repeat=5):
        td = min(dist(p, q) for q in training)
        hd = min(dist(p, q) for q in opened)
        if gs['nearestTrainingDistanceMinInclusive'] <= td <= gs['nearestTrainingDistanceMaxInclusive'] and hd >= gs['nearestOpenedOrdinal22GeometryDistanceMinInclusive']:
            candidates.append((p, td, hd))
    req(len(candidates) == 2114, 'eligible lattice candidate count drift')

    selected: list[tuple[float, ...]] = []
    computed = []
    while len(selected) < 6:
        best = None
        for p, td, hd in candidates:
            if p in selected:
                continue
            sd = min((dist(p, q) for q in selected), default=math.inf)
            score = min(td, sd)
            key = (score, td, hd, tuple(-x for x in p))
            if best is None or key > best[0]:
                best = (key, p, td, hd)
        req(best is not None, 'selection exhausted')
        _, p, td, hd = best
        selected.append(p)
        computed.append((p, td, hd, physical(p)))

    frozen = gs['selectedGeometries']
    req(len(frozen) == 6, 'frozen selected count')
    for i, ((p, td, hd, mapped), row) in enumerate(zip(computed, frozen), start=1):
        req(row['geometryId'] == f'v0070-holdout-{i:02d}', f'geometry id {i}')
        req(all(close(x,y) for x,y in zip(p, row['normalizedCoordinates'])), f'normalized point {i}')
        req(close(td, row['nearestTrainingDistance']) and close(hd, row['nearestOpenedOrdinal22GeometryDistance']), f'distance binding {i}')
        for feature in FEATURES:
            req(close(mapped[feature], row['geometry'][feature]), f'physical mapping {i} {feature}')
        req(td <= 0.6 and td >= 0.30 and hd >= 0.20, f'geometry filter {i}')

    runtime = c['runtimeIdentityRequired']
    req(runtime == old['runtimeIdentityRequired'], 'runtime identity changed from original Stage2')
    env = c['executionEnvelope']
    req((env['geometryCount'],env['blocksPerGeometry'],env['caseCount'],env['photonHistoriesPerBlock'],env['configuredPhotonHistories']) == (6,4,24,40000000,960000000), 'execution accounting')
    req(env['alisSpectralImportanceSamplingNm'] == 550.0, 'ALIS wavelength')
    req(env['expectedOutputGrid'] == old['stage2Scope']['expectedOutputGrid'], 'output grid drift')
    req(env['candidateScientificOrdinal'] == 24 and env['scientificOrdinalAllocated'] is False, 'ordinal allocation boundary')
    req(env['reservedSeeds'] == list(range(2101000001,2101000025)), 'seed range/order')
    for key in ('githubRerunAllowed','retryAllowed','resumeAllowed','adaptiveExtraBlocksAllowed','adaptivePointReplacementAllowed'):
        req(env[key] is False, f'execution continuation opened: {key}')

    me = c['modelAndEvaluation']
    oldme = old['modelAndEvaluation']
    identical = [
        'validatedSupportNearestDistanceMaxInclusive',
        'positiveChannelAbsoluteMeanSignedLogBiasMax',
        'positiveChannelMedianAbsoluteLogErrorMax',
        'positiveChannelWorstAbsoluteLogErrorMax',
        'positiveChannelWorstUncertaintyNormalizedErrorMax',
        'surrogateLogErrorBudgetOneSigma',
        'aggregatePrimaryMeanAbsoluteLogErrorMustBeAtMostFractionOfFrozenTrainingMeanBaseline',
        'shapeMedianPerCaseNrmseMax',
        'shapeWorstPerCaseNrmseMax',
        'shapeWorstSingleCoefficientNormalizedErrorMax',
        'p90OrP95PrincipalMetricAllowed',
        'noRetuningAfterHoldoutOpening',
    ]
    for key in identical:
        req(me[key] == oldme[key], f'DoD threshold drift: {key}')
    req(me['frozenTrainingMeanBaselinePrimaryMale'] == 2.5719584663680646, 'training baseline drift')
    req(me['aggregatePrimaryMeanAbsoluteLogErrorMax'] == 1.800370926457645, 'aggregate max drift')
    req(close(me['aggregatePrimaryMeanAbsoluteLogErrorMax'], 0.7 * me['frozenTrainingMeanBaselinePrimaryMale']), 'aggregate fraction arithmetic')
    req(me['epsilonSubstitutionAllowed'] is False and me['exactZeroSemanticsPreserved'] is True, 'zero/epsilon semantics')
    req(me['selectedFamilyId'] == 'ridge-primary-physical-compact-shape-idw-cos' and me['selectedPrimaryRidge'] == 1e-05 and me['selectedShapeNeighbors'] == 4 and me['selectedShapePower'] == 1.0, 'selected model spec drift')

    auth = c['authorization']
    req(auth['freshOrdinalAndSeedCollisionProofRequiredAtReview'] is True and auth['freshOrdinalAndSeedCollisionProofRequiredAgainAtAuthorizationAndDispatch'] is True, 'collision proof boundary')
    req(auth['automaticDispatch'] is False and auth['separateOneFileAuthorizationCommitRequired'] is True and auth['authorizationPrMustRemainDraftDuringReviewAndDispatch'] is True, 'authorization boundary')

    for key, value in c['boundaries'].items():
        req(value is False, f'prereg boundary opened: {key}')
    req(c['failureSemantics']['openedValuesBecomeDiagnosticOnlyOnFailure'] is True and c['failureSemantics']['futureRetunedGenerationRequiresAnotherCompletelyFreshUntouchedValidationSource'] is True, 'failure semantics drift')

    print(json.dumps({'status':'PASS','contractSha256':c['contractSha256'],'eligibleGeometryOnlyCandidateCount':len(candidates),'selectedGeometryCount':len(frozen),'candidateScientificOrdinal':24,'reservedSeedCount':24,'protectedValuesRead':False,'scientificSolverExecutionAuthorized':False}, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
