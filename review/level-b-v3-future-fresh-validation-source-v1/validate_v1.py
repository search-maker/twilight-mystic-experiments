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
RESULT_BINDING = ROOT / 'review/level-b-v3-training-only-materialization-result-v1/result-v1.json'
FEATURES = ('sunDepressionDeg','targetAltitudeDeg','relativeAzimuthDeg','observerElevationM','aod550')
DATASET_FILE_SHA256 = '1cf31f1a80ce4ae1f39b9e750616093f6cfa927d10e258f81fe9fc0e58f0ea69'
DATASET_CANONICAL_SHA256 = '58c977acf84b6ce17717765c2052f7f9fd64e2965e5bf447eba5cc4accb30435'
REPRESENTATION_SHA256 = '2491ac91ed924f2ba69b37ea20f48d63f51d41146cd9fe50e0bd63bfb315a763'
RESULT_BINDING_BLOB = '1cc183c20a28f1652fac1412988e82b7c2e56179'
PRIOR_SOURCE_DESIGN_PATH = ROOT / 'review/level-b-v2-densified58-fresh-validation-v1/contract-v1.json'
PRIOR_SOURCE_DESIGN_BLOB = 'aad11350311ce3768488e64ed72edc3e48646ff9'
MODEL_SHA256 = 'c4902eb3c2ba67b12dc4ef2b9cefb67c5963a6abc104708a73b2aab5dd0163b9'
SELECTED_CANDIDATE = 'resid-V1_IDW_COS_COORDINATES-r1e-05-k6-p1-a1'


def req(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit('REFUSED: ' + message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding='utf-8'))
    req(isinstance(value, dict), f'object required: {path}')
    return value


def canonical_sha(value: Any) -> str:
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
    req(c['schemaVersion'] == 1, 'schema')
    req(c['protocolId'] == 'level-b-v3-future-fresh-validation-source-v1', 'protocol id')
    req(c['status'] == 'REVIEW_ONLY_FUTURE_FRESH_VALIDATION_SOURCE_PREREGISTRATION_NO_AUTHORIZATION_NO_VALUES_OPENED', 'status')
    req(c['governance'] == 'MYSTIC-STATE-0071', 'governance')
    req(c['sourceMainAtFreeze'] == 'f76657872299cfef13fd3ae1dca7361edf973af6', 'source main')
    req('contractSha256' not in c, 'unsupported self hash field')

    bindings = c['sourceBindings']
    req(blob(RESULT_BINDING) == RESULT_BINDING_BLOB == bindings['modelResultBindingGitBlobSha'], 'model result binding blob drift')
    req(blob(PRIOR_SOURCE_DESIGN_PATH) == PRIOR_SOURCE_DESIGN_BLOB == bindings['priorFreshSourceDesignGitBlobSha'], 'prior source design blob drift')
    result = load(RESULT_BINDING)
    req(result['status'] == 'TRAINING_ONLY_CHANGED_MODEL_FROZEN_PENDING_SEPARATE_FRESH_VALIDATION_GOVERNANCE', 'current model is not frozen training-only')
    req(result['governance'] == 'MYSTIC-STATE-0071', 'result governance drift')
    req(result['frozenModel']['modelCanonicalSha256'] == MODEL_SHA256 == bindings['modelCanonicalSha256'], 'model canonical hash drift')
    req(result['frozenModel']['selectedSpec']['candidateId'] == SELECTED_CANDIDATE == bindings['selectedCandidateId'], 'selected candidate drift')
    req(result['resultBindingSha256'] == bindings['modelResultBindingSelfSha256'], 'result binding self hash drift')
    req(result['materializationExecution']['workflowRunId'] == bindings['materializationRunId'] == 31927414786, 'materialization run drift')
    req(result['artifact']['id'] == bindings['materializationArtifactId'] == 9258264586, 'materialization artifact id drift')
    req(result['artifact']['digest'] == bindings['materializationArtifactDigest'], 'materialization artifact digest drift')
    req(result['scientificBoundaries']['protectedValidationAuthorized'] is False, 'current result unexpectedly authorizes protected validation')
    req(result['scientificBoundaries']['ordinal27ValuesRead'] is False, 'current model materialization read ordinal27')
    req(result['scientificBoundaries']['futureValidationMustUseCompletelyFreshUntouchedSource'] is True, 'future source freshness boundary drift')

    raw = args.dataset.read_bytes()
    req(hashlib.sha256(raw).hexdigest() == DATASET_FILE_SHA256 == bindings['trainingDatasetFileSha256'], 'dataset file hash')
    dataset = json.loads(raw)
    req(dataset['datasetSha256'] == DATASET_CANONICAL_SHA256 == bindings['trainingDatasetCanonicalSha256'], 'dataset canonical hash')
    body = dict(dataset)
    body.pop('datasetSha256', None)
    req(canonical_sha(body) == dataset['datasetSha256'], 'dataset self hash')
    req(dataset['geometryCount'] == 58 and len(dataset['records']) == 58, 'training geometry count')
    req(dataset['protectedHoldoutRecordCount'] == 0 and dataset['ordinal22ValuesRead'] is False, 'training dataset protected boundary')
    req(dataset['frozenRepresentationPackageSha256'] == REPRESENTATION_SHA256 == bindings['frozenRepresentationPackageSha256'], 'representation hash drift')

    gs = c['geometrySelection']
    req(gs['trainingTargetFieldsUsed'] is False and gs['modelPredictionsMayInfluenceSelection'] is False, 'selection uses target/model data')
    req(gs['priorProtectedTargetValuesRead'] is False and gs['priorSelectedGeometryIdentitiesRead'] is False and gs['priorSelectedGeometryCoordinatesRead'] is False, 'prior protected source leakage')
    new_levels = tuple(float(x) for x in gs['newLatticeLevels'])
    prior_levels = tuple(float(x) for x in gs['priorPublicCandidateLatticeLevels'])
    req(new_levels == (0.2,0.4,0.6,0.8) and gs['newCandidateLatticeSize'] == 1024, 'new lattice drift')
    req(prior_levels == (0.1,0.3,0.5,0.7,0.9), 'prior public design level binding drift')
    req(set(new_levels).isdisjoint(prior_levels), 'new lattice not structurally disjoint from prior public lattice')

    training = [(str(r['geometryId']), coord(r['geometry'])) for r in dataset['records']]
    req(len({tuple(round(x,15) for x in p) for _,p in training}) == 58, 'duplicate training geometry')
    candidates = []
    for p in itertools.product(new_levels, repeat=5):
        td, gid = min((dist(p,q), gid) for gid,q in training)
        if gs['nearestTrainingDistanceMinInclusive'] <= td <= gs['nearestTrainingDistanceMaxInclusive']:
            candidates.append((p,td,gid))
    req(len(candidates) == gs['eligibleCandidateCount'] == 601, 'eligible candidate count drift')

    selected: list[tuple[float, float, float, float, float]] = []
    computed = []
    while len(selected) < gs['selectedGeometryCount']:
        best = None
        for p,td,gid in candidates:
            if p in selected:
                continue
            sd = min((dist(p,q) for q in selected), default=math.inf)
            diversity = min(td,sd)
            key = (diversity,td,tuple(-x for x in p))
            if best is None or key > best[0]:
                best = (key,p,td,gid,physical(p))
        req(best is not None, 'selection exhausted')
        _,p,td,gid,mapped = best
        selected.append(p)
        computed.append((p,td,gid,mapped))

    frozen = gs['selectedGeometries']
    req(len(frozen) == 6, 'selected count')
    for i, ((p,td,gid,mapped), row) in enumerate(zip(computed,frozen), start=1):
        req(row['sourceId'] == f'future-fresh-source-{i:02d}', f'source id {i}')
        req(all(close(x,y) for x,y in zip(p,row['normalizedCoordinates'])), f'normalized coordinates {i}')
        req(close(td,row['nearestTrainingDistance']) and gid == row['nearestTrainingGeometryId'], f'nearest training binding {i}')
        req(gs['nearestTrainingDistanceMinInclusive'] <= td <= gs['nearestTrainingDistanceMaxInclusive'], f'training support band {i}')
        for feature in FEATURES:
            req(close(mapped[feature],row['geometry'][feature]), f'physical mapping {i} {feature}')
        req(tuple(p) not in {q for _,q in training}, f'selected point equals training geometry {i}')
        req(all(x not in prior_levels for x in p), f'selected point violates structural prior-lattice disjointness {i}')

    fresh = c['freshnessSemantics']
    req(fresh['selectedPointsAreDistinctFromAll58TrainingGeometriesByConstruction'] is True, 'training freshness flag')
    req(fresh['selectedPointsAreStructurallyDistinctFromEveryPriorV0070CandidateByLatticeParity'] is True, 'prior source structural freshness flag')
    req(fresh['priorV0070SelectedGeometryIdentityOrCoordinatesRequiredForProof'] is False, 'prior selected geometry leakage required')
    req(fresh['futureIndependentRepositoryWideGeometryCollisionAuditRequiredBeforeAnyAuthorization'] is True, 'future repository-wide freshness audit not required')
    req(fresh['individualPointReplacementAfterCollisionAudit'] is False and fresh['protectedOutcomeDependentReplacement'] is False, 'replacement after protected audit opened')

    activation = c['futureActivationRequirements']
    for key in ('newGovernanceDirectiveRequired','futureGovernanceMustSeparatelyFreezeExecutionEnvelope','futureGovernanceMustSeparatelyFreezeRuntimeIdentity','futureGovernanceMustSeparatelyFreezeScientificOrdinalAndSeeds','futureGovernanceMustSeparatelyFreezeDefinitionOfDoneAndEvaluator','futureGovernanceMustSeparatelyFreezeSupportAndBaselineSemantics','futureGovernanceMustRepeatFreshnessAndCollisionProofImmediatelyBeforeAuthorization'):
        req(activation[key] is True, f'future activation requirement closed: {key}')
    req(activation['sourceProtocolMergeMayAuthorizeExecution'] is False and activation['protectedValuesMayBeOpenedUnderThisProtocolAlone'] is False and activation['automaticDispatch'] is False, 'source protocol accidentally authorizes activation')

    for key,value in c['boundaries'].items():
        req(value is False, f'boundary opened: {key}')

    print(json.dumps({
        'status':'PASS',
        'eligibleTrainingOnlyCandidateCount':len(candidates),
        'selectedGeometryCount':len(frozen),
        'selectedSourceIds':[x['sourceId'] for x in frozen],
        'priorSelectedGeometryIdentitiesRead':False,
        'priorSelectedGeometryCoordinatesRead':False,
        'protectedValuesRead':False,
        'scientificSolverExecutionAuthorized':False,
        'newGovernanceRequiredBeforeAnyActivation':True
    },sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
