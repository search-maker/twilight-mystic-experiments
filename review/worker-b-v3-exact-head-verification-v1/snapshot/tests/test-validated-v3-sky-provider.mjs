import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { createAtmosphereState } from '../atmosphere-state.mjs';
import { limitingVMagnitude } from '../human-threshold.mjs';
import { evaluateSky, SKY_STATUS } from '../sky-provider.mjs';
import {
  evaluateVisibilitySample,
  solveVisibilityRuntimeTimeline,
  VISIBILITY_RUNTIME_STATUS,
} from '../visibility-runtime.mjs';
import {
  LEVEL_B_V3_MODEL_CANONICAL_SHA256,
  LEVEL_B_V3_PACKAGE_ARTIFACT_ID,
  LEVEL_B_V3_PACKAGE_MANIFEST_SHA256,
  LEVEL_B_V3_RUNTIME_DATA_SHA256,
  LEVEL_B_V3_VALIDATION_STATUS,
  classifyValidatedV3Support,
  createValidatedV3SkyProvider,
  predictValidatedV3PrimaryLogs,
  validateValidatedV3RuntimeData,
} from '../validated-v3-sky-provider.mjs';

const runtimeUrl = new URL('../validated-v3-primary-runtime-v1.json', import.meta.url);
const runtimeBytes = readFileSync(runtimeUrl);
assert.equal(createHash('sha256').update(runtimeBytes).digest('hex'), LEVEL_B_V3_RUNTIME_DATA_SHA256, 'frozen runtime extraction byte hash drift');
const runtimeText = runtimeBytes.toString('utf8');
assert.ok(!runtimeText.includes('holdout'), 'protected holdout identity leaked into runtime data');
assert.ok(!runtimeText.includes('2110000001'), 'protected ordinal28 seed leaked into runtime data');
const runtimeData = JSON.parse(runtimeText);
validateValidatedV3RuntimeData(runtimeData);
assert.equal(runtimeData.sourceModelCanonicalSha256, LEVEL_B_V3_MODEL_CANONICAL_SHA256);

// Fixed known answers from the exact frozen Python reference predictor on
// synthetic/non-protected geometries. No protected truth is present here.
const parityFixtures = [
  {
    geometry: { sunDepressionDeg: 6.8, targetAltitudeDeg: 42, relativeAzimuthDeg: 90, observerElevationM: 1200, aod550: 0.18 },
    primaryLogs: [-1.1249305940293668, 0.324771122179437, -5.367843958116066],
  },
  {
    geometry: { sunDepressionDeg: 3.2, targetAltitudeDeg: 60, relativeAzimuthDeg: 45, observerElevationM: 800, aod550: 0.12 },
    primaryLogs: [2.835510347689478, 4.126481022021563, -1.4133115415540634],
  },
  {
    geometry: { sunDepressionDeg: 9.8, targetAltitudeDeg: 68, relativeAzimuthDeg: 120, observerElevationM: 2100, aod550: 0.10 },
    primaryLogs: [-4.704491757778857, -3.1425082124463564, -8.948438254514432],
  },
  {
    geometry: { sunDepressionDeg: 2, targetAltitudeDeg: 5, relativeAzimuthDeg: 0, observerElevationM: 0, aod550: 0.05 },
    primaryLogs: [6.799879137976099, 7.678655224352634, 2.5381582332238692],
  },
];
for (const fixture of parityFixtures) {
  const got = predictValidatedV3PrimaryLogs(fixture.geometry, runtimeData);
  for (let i = 0; i < 3; i += 1) {
    assert.ok(Math.abs(got[i] - fixture.primaryLogs[i]) <= 1e-12, `Python/JS primary parity drift at channel ${i}: ${got[i]} vs ${fixture.primaryLogs[i]}`);
  }
}

const supportedInput = { sunDepressionDeg: 6.8, targetAltitudeDeg: 42, relativeAzimuthDeg: 90, observerElevationM: 1200, aod550: 0.18 };
const supported = classifyValidatedV3Support(supportedInput, runtimeData);
assert.equal(supported.validatedSupport, true);
assert.ok(Math.abs(supported.nearestTrainingDistance - 0.31778591525120586) <= 1e-12);

// Inside every nominal physical bound but beyond the frozen nearest-training
// radius: explicit OOD, never silent extrapolation.
const sparseBoundaryInput = { sunDepressionDeg: 10.5, targetAltitudeDeg: 80, relativeAzimuthDeg: 180, observerElevationM: 2500, aod550: 0.40 };
const sparse = classifyValidatedV3Support(sparseBoundaryInput, runtimeData);
assert.equal(sparse.nominalDesignBox, true);
assert.equal(sparse.validatedSupport, false);
assert.ok(sparse.nearestTrainingDistance > 0.60);
assert.ok(sparse.reasons.includes('NEAREST_FROZEN_TRAINING_DISTANCE_EXCEEDS_0.60'));

const provider = createValidatedV3SkyProvider({ runtimeData });
const now = new Date('2026-08-16T00:00:00Z');
const atmosphere = createAtmosphereState({
  provider: 'validated-v3-test-fixture', dataset: 'synthetic-non-protected',
  validTime: '2026-08-16T00:00:00Z', fetchTime: '2026-08-16T00:00:00Z', staleAfterSeconds: 1800,
  latitudeDeg: 40, longitudeDeg: -75, observerElevationM: 1200, aod550: 0.18,
  qualityClass: 'modeled-live',
}, { now });
const sky = evaluateSky({
  provider,
  geometry: { sunDepressionDeg: 6.8, targetAltitudeDeg: 42, relativeAzimuthDeg: 90 },
  atmosphere,
});
assert.equal(sky.status, SKY_STATUS.SUPPORTED);
assert.equal(sky.provenance.modelHash, LEVEL_B_V3_MODEL_CANONICAL_SHA256);
assert.equal(sky.provenance.packageArtifactId, LEVEL_B_V3_PACKAGE_ARTIFACT_ID);
assert.equal(sky.provenance.packageManifestSha256, LEVEL_B_V3_PACKAGE_MANIFEST_SHA256);
assert.equal(sky.provenance.validationStatus, LEVEL_B_V3_VALIDATION_STATUS);
assert.equal(sky.provenance.atmosphereIdentity, atmosphere.identity);
assert.equal(sky.provenance.productionAuthorized, false);
assert.equal(sky.provenance.measuredRealSkyValidated, false);
assert.equal(sky.provenance.humanFirstSeeingValidated, false);
assert.equal(sky.support.validatedSupport, true);
assert.equal(sky.channels.photopic.unit, 'cd/m2');
assert.equal(sky.channels.scotopic.unit, 'scotopic-cd/m2');
assert.equal(sky.channels.johnsonV.unit, 'mW/m2/nm/sr');
assert.equal(sky.channels.spectral.available, false);
assert.equal(sky.channels.spectral.reason, 'VALIDATED_V3_PRIMARY_PROVIDER_SPECTRAL_RUNTIME_NOT_IMPLEMENTED');
const expectedPhysical = [0.3246750009599394, 1.3837139083114034, 0.004664176637503361];
for (const [i, channel] of ['photopic', 'scotopic', 'johnsonV'].entries()) {
  assert.ok(Math.abs(sky.channels[channel].value - expectedPhysical[i]) <= 1e-12, `physical channel parity drift: ${channel}`);
}

const oodAtmosphere = createAtmosphereState({
  provider: 'validated-v3-test-fixture', dataset: 'synthetic-non-protected',
  validTime: '2026-08-16T00:00:00Z', fetchTime: '2026-08-16T00:00:00Z', staleAfterSeconds: 1800,
  observerElevationM: 2500, aod550: 0.40, qualityClass: 'modeled-live',
}, { now });
const ood = evaluateSky({
  provider,
  geometry: { sunDepressionDeg: 10.5, targetAltitudeDeg: 80, relativeAzimuthDeg: 180 },
  atmosphere: oodAtmosphere,
});
assert.equal(ood.status, SKY_STATUS.OOD);
assert.equal(ood.support.nominalDesignBox, true);
assert.equal(ood.support.validatedSupport, false);

const cloudyAtmosphere = createAtmosphereState({
  provider: 'validated-v3-test-fixture', dataset: 'synthetic-non-protected',
  validTime: '2026-08-16T00:00:00Z', fetchTime: '2026-08-16T00:00:00Z', staleAfterSeconds: 1800,
  observerElevationM: 1200, aod550: 0.18, qualityClass: 'modeled-live', cloud: { directionalClear: false },
}, { now });
const cloudy = evaluateSky({
  provider,
  geometry: { sunDepressionDeg: 6.8, targetAltitudeDeg: 42, relativeAzimuthDeg: 90 },
  atmosphere: cloudyAtmosphere,
});
assert.equal(cloudy.status, SKY_STATUS.CLOUD_UNSUPPORTED);
assert.ok(cloudy.support.reasons.includes('DIRECTIONAL_CLOUD'));

// Exercise the actual Worker-B visibility orchestration with this provider while
// keeping the stellar side synthetic and atmosphere-identical. The new sky
// adapter must not modify the human threshold or chronological solver.
const observerCriterion = Object.freeze({
  id: 'validated-v3-integration-test-only',
  fieldFactor: 2.4,
  factorBasis: Object.freeze({ mediumFactor: 1, observerFactor: 2.4 }),
  uncertainty: { kind: 'not-calibrated' },
});
function stellarFromDesiredMargin(desiredMargin) {
  return ({ geometry, atmosphere: sameAtmosphere }) => {
    const evaluatedSky = evaluateSky({ provider, geometry, atmosphere: sameAtmosphere });
    if (!evaluatedSky.channels.photopic.available) return { status: 'UNSUPPORTED', reason: 'NO_PHOTOPIC' };
    const limit = limitingVMagnitude({
      backgroundLuminanceCdM2: evaluatedSky.channels.photopic.value,
      fieldFactor: observerCriterion.fieldFactor,
      branch: 'full',
    });
    return {
      status: 'SUPPORTED',
      apparentVMagAtEye: limit - desiredMargin(geometry.sunDepressionDeg),
      atmosphereIdentity: sameAtmosphere.identity,
      provenance: { method: 'synthetic-non-protected-validated-v3-integration-test' },
      uncertainty: { kind: 'synthetic-test' },
    };
  };
}
const runtimeSample = evaluateVisibilitySample({
  geometry: { sunDepressionDeg: 6.8, targetAltitudeDeg: 42, relativeAzimuthDeg: 90 },
  atmosphere,
  skyProvider: provider,
  stellarSignalEvaluator: stellarFromDesiredMargin(() => 0.35),
  observerCriterion,
});
assert.equal(runtimeSample.status, VISIBILITY_RUNTIME_STATUS.SUPPORTED);
assert.ok(Math.abs(runtimeSample.visibilityMarginMag - 0.35) <= 1e-10);
assert.equal(runtimeSample.sky.provenance.modelHash, LEVEL_B_V3_MODEL_CANONICAL_SHA256);
assert.equal(runtimeSample.sky.provenance.atmosphereIdentity, runtimeSample.stellar.atmosphereIdentity);
assert.equal(runtimeSample.uncertainty.probabilityModelApplied, false);

const timeline = solveVisibilityRuntimeTimeline({
  minSunDepressionDeg: 2,
  maxSunDepressionDeg: 10,
  scanStepDeg: 0.05,
  geometryAtSunDepression: sunDepressionDeg => ({ sunDepressionDeg, targetAltitudeDeg: 42, relativeAzimuthDeg: 90 }),
  atmosphere,
  skyProvider: provider,
  stellarSignalEvaluator: stellarFromDesiredMargin(d => 0.25 - (d - 6) ** 2),
  observerCriterion,
});
assert.equal(timeline.status, VISIBILITY_RUNTIME_STATUS.SUPPORTED);
assert.equal(timeline.timeline.crossingCount, 2);
assert.equal(timeline.timeline.visibilityIntervals.length, 1);
assert.equal(timeline.productionDefaultChanged, false);

const corrupted = structuredClone(runtimeData);
corrupted.sourceModelCanonicalSha256 = 'corrupted';
assert.throws(() => createValidatedV3SkyProvider({ runtimeData: corrupted }), /runtime data model hash drift/);

console.log('validated-v3 sky provider parity/support/provenance/runtime: PASS');
