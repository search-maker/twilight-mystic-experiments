import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

import {
  AOD550,
  SUN_DEPRESSION_DEG,
  TARGET_ALTITUDE_DEG,
  TARGET_RELATIVE_AZIMUTH_DEG,
  SPATIAL_ARMS,
  buildSphericalCapQuadrature,
  fixationCenter,
  frozenGazeArmsForSpatialArm,
  nominalFootprintWithinProviderAltitude,
  offsetDirection,
  providerRelativeAzimuthDeg,
  targetDirection,
} from './sf-a-spatial-input-audit.mjs';

const EXPECTED = Object.freeze({
  preregParent: '941994b9f6a343656bdbb310ad0d2edbdfe601c8',
  applicationSha: 'e0da52eb0a2d5bac333da6572f51df52ea7e676e',
  providerBlob: 'da8c5995559020865118220d939e58d89e6b98e4',
  runtimeBlob: '5790ccb2c289de082a2851d96e4c3c660a1c4985',
  runtimeSha256: '6a927bd702ebbf1b1913ebe51731f3b92f967f2ae95edf090280b8370ea091e4',
  supportDistanceMax: 0.60,
  q1StepDeg: 0.5,
  q2StepDeg: 0.25,
  refinementSunDepressionDeg: Object.freeze([2, 4, 6, 8, 10.5]),
  expectedQ1Complete: Object.freeze({ S1_WHOLE_CAP: 222, S2_ALF: 222, S3_UCHIDA_LOCAL: 353 }),
});

const root = process.env.GITHUB_WORKSPACE ?? process.cwd();
const starsRoot = process.env.STARSVISIBILITY_ROOT ?? path.join(root, 'external', 'starsvisibility');
const providerPath = path.join(starsRoot, 'scientific-tools', 'visibility-v3', 'validated-v3-sky-provider.mjs');
const runtimePath = path.join(starsRoot, 'scientific-tools', 'visibility-v3', 'validated-v3-primary-runtime-v1.json');
const outputPath = process.argv[2] ?? path.join(root, 'sf-a-q1q2-support-result.json');

for (const p of [providerPath, runtimePath]) assert.ok(fs.existsSync(p), `missing bound starsvisibility file: ${p}`);
const runtimeRaw = fs.readFileSync(runtimePath);
const runtimeSha256 = crypto.createHash('sha256').update(runtimeRaw).digest('hex');
assert.equal(runtimeSha256, EXPECTED.runtimeSha256, 'bound runtime raw SHA-256 drift');
const runtimeData = JSON.parse(runtimeRaw.toString('utf8'));
assert.equal(runtimeData.schemaVersion, 1);
assert.equal(runtimeData.supportCoordinates.length, 58);

const provider = await import(pathToFileURL(providerPath).href);
assert.equal(provider.LEVEL_B_V3_RUNTIME_DATA_SHA256, EXPECTED.runtimeSha256);
assert.equal(provider.LEVEL_B_V3_SUPPORT_DISTANCE_MAX, EXPECTED.supportDistanceMax);
provider.validateValidatedV3RuntimeData(runtimeData);

const DEG = Math.PI / 180;
const maxSq = EXPECTED.supportDistanceMax ** 2;
const supportCoordinates = runtimeData.supportCoordinates;

function fastSupport({ sunDepressionDeg, direction, aod550 }) {
  const targetAltitudeDeg = direction.altitudeDeg;
  const relativeAzimuthDeg = providerRelativeAzimuthDeg(direction);
  if (!(sunDepressionDeg >= 2 && sunDepressionDeg <= 10.5
      && targetAltitudeDeg >= 5 && targetAltitudeDeg <= 80
      && relativeAzimuthDeg >= 0 && relativeAzimuthDeg <= 180
      && aod550 >= 0.05 && aod550 <= 0.40)) {
    return { supported: false, reason: 'OUTSIDE_VALIDATED_PHYSICAL_DESIGN_BOX', nearestTrainingDistance: null };
  }
  const q0 = (sunDepressionDeg - 2) / 8.5;
  const q1 = (targetAltitudeDeg - 5) / 75;
  const q2 = (Math.cos(relativeAzimuthDeg * DEG) + 1) / 2;
  const q3 = 0;
  const q4 = (aod550 - 0.05) / 0.35;
  let nearestSq = Infinity;
  for (const x of supportCoordinates) {
    const d0 = q0 - x[0];
    const d3 = q3 - x[3];
    const d4 = q4 - x[4];
    const base = d0*d0 + d3*d3 + d4*d4;
    if (base >= nearestSq) continue;
    const d1 = q1 - x[1];
    const d2 = q2 - x[2];
    const d = base + d1*d1 + d2*d2;
    if (d < nearestSq) nearestSq = d;
  }
  return {
    supported: nearestSq <= maxSq,
    reason: nearestSq <= maxSq ? null : 'NEAREST_FROZEN_TRAINING_DISTANCE_EXCEEDS_0.60',
    nearestTrainingDistance: Math.sqrt(nearestSq),
  };
}

// Exact parity check against the bound provider support implementation on a deterministic probe set.
for (const probe of [
  { sunDepressionDeg: 2, altitudeDeg: 45, azimuthDeg: 135, aod550: 0.05 },
  { sunDepressionDeg: 6.25, altitudeDeg: 45, azimuthDeg: 0, aod550: 0.30 },
  { sunDepressionDeg: 8, altitudeDeg: 60, azimuthDeg: 90, aod550: 0.15 },
  { sunDepressionDeg: 10.5, altitudeDeg: 30, azimuthDeg: 180, aod550: 0.30 },
]) {
  const direction = { altitudeDeg: probe.altitudeDeg, azimuthDeg: probe.azimuthDeg };
  const input = {
    sunDepressionDeg: probe.sunDepressionDeg,
    targetAltitudeDeg: probe.altitudeDeg,
    relativeAzimuthDeg: providerRelativeAzimuthDeg(direction),
    observerElevationM: 0,
    aod550: probe.aod550,
  };
  const canonical = provider.classifyValidatedV3Support(input, runtimeData);
  const fast = fastSupport({ sunDepressionDeg: probe.sunDepressionDeg, direction, aod550: probe.aod550 });
  assert.equal(fast.supported, canonical.validatedSupport, 'fast support parity drift');
  if (canonical.nearestTrainingDistance !== null) {
    assert.ok(Math.abs(fast.nearestTrainingDistance - canonical.nearestTrainingDistance) <= 1e-14, 'nearest-distance parity drift');
  }
}

const quadratureCache = new Map();
function quadrature(capDeg, stepDeg) {
  const key = `${capDeg}:${stepDeg}`;
  if (!quadratureCache.has(key)) quadratureCache.set(key, buildSphericalCapQuadrature({ capDeg, radialStepDeg: stepDeg }));
  return quadratureCache.get(key);
}

function historyId({ aod550, targetAltitudeDeg, targetRelativeAzimuthDeg, armId, gazeId }) {
  return `aod=${aod550}|alt=${targetAltitudeDeg}|az=${targetRelativeAzimuthDeg}|arm=${armId}|gaze=${gazeId}`;
}

function rowSupport({ aod550, targetAltitudeDeg, targetRelativeAzimuthDeg, armId, gaze, sunDepressionDeg, stepDeg, captureFailure = false }) {
  const target = targetDirection(targetAltitudeDeg, targetRelativeAzimuthDeg);
  const bd = fastSupport({ sunDepressionDeg, direction: target, aod550 });
  if (!bd.supported) return { supported: false, reason: 'BD_SUPPORT', detail: captureFailure ? { direction: target, ...bd } : undefined };

  const arm = SPATIAL_ARMS[armId];
  const center = fixationCenter({
    sunDepressionDeg,
    targetAltitudeDeg,
    targetRelativeAzimuthDeg,
    eccentricityDeg: gaze.eccentricityDeg,
    orientation: gaze.orientation,
  });
  if (!nominalFootprintWithinProviderAltitude({ centerAltitudeDeg: center.altitudeDeg, radiusDeg: arm.radiusDeg })) {
    return { supported: false, reason: 'NOMINAL_ALTITUDE', detail: captureFailure ? { center, radiusDeg: arm.radiusDeg } : undefined };
  }

  const q = quadrature(arm.radiusDeg, stepDeg);
  for (let i = 0; i < q.length; i += 1) {
    const cell = q[i];
    const direction = offsetDirection(center, cell.thetaDeg, cell.bearingDeg);
    const s = fastSupport({ sunDepressionDeg, direction, aod550 });
    if (!s.supported) {
      return {
        supported: false,
        reason: 'FOOTPRINT_SUPPORT',
        detail: captureFailure ? { quadratureIndex: i, thetaDeg: cell.thetaDeg, bearingDeg: cell.bearingDeg, direction, ...s } : undefined,
      };
    }
  }
  return { supported: true };
}

function q1CompleteHistories(armId) {
  const out = [];
  for (const aod550 of AOD550) {
    for (const targetAltitudeDeg of TARGET_ALTITUDE_DEG) {
      for (const targetRelativeAzimuthDeg of TARGET_RELATIVE_AZIMUTH_DEG) {
        for (const gaze of frozenGazeArmsForSpatialArm(armId)) {
          let complete = true;
          for (const sunDepressionDeg of SUN_DEPRESSION_DEG) {
            const s = rowSupport({ aod550, targetAltitudeDeg, targetRelativeAzimuthDeg, armId, gaze, sunDepressionDeg, stepDeg: EXPECTED.q1StepDeg });
            if (!s.supported) { complete = false; break; }
          }
          if (complete) out.push({ aod550, targetAltitudeDeg, targetRelativeAzimuthDeg, armId, gazeId: gaze.id, gaze });
        }
      }
    }
  }
  return out;
}

const q1ByArm = {};
// S1/S2 share the same exact footprint and gaze geometry; compute support once and clone the identities.
const q1S1 = q1CompleteHistories('S1_WHOLE_CAP');
q1ByArm.S1_WHOLE_CAP = q1S1;
q1ByArm.S2_ALF = q1S1.map(h => ({ ...h, armId: 'S2_ALF' }));
q1ByArm.S3_UCHIDA_LOCAL = q1CompleteHistories('S3_UCHIDA_LOCAL');

for (const [armId, expectedCount] of Object.entries(EXPECTED.expectedQ1Complete)) {
  assert.equal(q1ByArm[armId].length, expectedCount, `Q1 complete-history count drift for ${armId}`);
}

const refinementRows = [];
const gaps = [];
for (const armId of ['S1_WHOLE_CAP', 'S2_ALF', 'S3_UCHIDA_LOCAL']) {
  for (const h of q1ByArm[armId]) {
    for (const sunDepressionDeg of EXPECTED.refinementSunDepressionDeg) {
      const s = rowSupport({
        ...h,
        armId,
        gaze: h.gaze,
        sunDepressionDeg,
        stepDeg: EXPECTED.q2StepDeg,
        captureFailure: true,
      });
      const row = {
        historyId: historyId(h),
        aod550: h.aod550,
        targetAltitudeDeg: h.targetAltitudeDeg,
        targetRelativeAzimuthDeg: h.targetRelativeAzimuthDeg,
        armId,
        gazeId: h.gazeId,
        sunDepressionDeg,
        q2Supported: s.supported,
        reason: s.reason ?? null,
      };
      refinementRows.push(row);
      if (!s.supported) gaps.push({ ...row, detail: s.detail ?? null });
    }
  }
}

const uniqueS1S2GapKey = new Set(gaps.filter(g => g.armId === 'S1_WHOLE_CAP').map(g => `${g.historyId.replace('arm=S1_WHOLE_CAP','arm=SHARED_20')}|sun=${g.sunDepressionDeg}`));
for (const g of gaps.filter(g => g.armId === 'S2_ALF')) {
  assert.ok(uniqueS1S2GapKey.has(`${g.historyId.replace('arm=S2_ALF','arm=SHARED_20')}|sun=${g.sunDepressionDeg}`), 'S1/S2 Q2 support gap mismatch');
}

const byArm = {};
for (const armId of ['S1_WHOLE_CAP', 'S2_ALF', 'S3_UCHIDA_LOCAL']) {
  const rows = refinementRows.filter(r => r.armId === armId);
  const armGaps = gaps.filter(r => r.armId === armId);
  byArm[armId] = {
    q1CompleteHistoryCount: q1ByArm[armId].length,
    refinementRowCount: rows.length,
    q2SupportCompleteRows: rows.length - armGaps.length,
    q2SupportGapRows: armGaps.length,
  };
}

const result = {
  schema: 'SF_A_Q1_Q2_SUPPORT_GATE_V1',
  status: gaps.length === 0 ? 'Q1_Q2_SUPPORT_COMPLETE_LUMINANCE_GATE_MAY_PROCEED' : 'REFINEMENT_SET_FINE_GRID_SUPPORT_INCOMPLETE_NO_LUMINANCE_OPENED',
  boundary: {
    noSkyLuminanceEvaluated: true,
    noAdaptationStateEvaluated: true,
    noCandidateThresholdEvaluated: true,
    noTaylorJerusalemUsed: true,
    noProtectedHoldoutOpened: true,
  },
  bindings: EXPECTED,
  q1CompleteHistoryCounts: Object.fromEntries(Object.entries(q1ByArm).map(([k, v]) => [k, v.length])),
  q1CompleteHistories: Object.fromEntries(Object.entries(q1ByArm).map(([k, v]) => [k, v.map(h => historyId(h))])),
  refinementRowCount: refinementRows.length,
  q2SupportCompleteRows: refinementRows.length - gaps.length,
  q2SupportGapRows: gaps.length,
  byArm,
  q2SupportGaps: gaps,
};

fs.writeFileSync(outputPath, `${JSON.stringify(result, null, 2)}\n`);
console.log(JSON.stringify({
  status: result.status,
  q1CompleteHistoryCounts: result.q1CompleteHistoryCounts,
  refinementRowCount: result.refinementRowCount,
  q2SupportGapRows: result.q2SupportGapRows,
  byArm: result.byArm,
}, null, 2));
