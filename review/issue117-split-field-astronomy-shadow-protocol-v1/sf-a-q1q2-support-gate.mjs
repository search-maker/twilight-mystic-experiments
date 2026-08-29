import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

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
  supportFixtureBlob: '1f8518132e29075e9a26131a2e346b14d1054bc4',
  supportDistanceMax: 0.60,
  q1StepDeg: 0.5,
  q2StepDeg: 0.25,
  refinementSunDepressionDeg: Object.freeze([2, 4, 6, 8, 10.5]),
  expectedQ1Complete: Object.freeze({ S1_WHOLE_CAP: 222, S2_ALF: 222, S3_UCHIDA_LOCAL: 353 }),
});

const root = process.env.GITHUB_WORKSPACE ?? process.cwd();
const outputPath = process.argv[2] ?? path.join(root, 'sf-a-q1q2-support-result.json');
const supportFixturePath = new URL('./SF_A_BOUND_SUPPORT_COORDINATES_v1.json', import.meta.url);
const supportFixture = JSON.parse(fs.readFileSync(supportFixturePath, 'utf8'));

assert.equal(supportFixture.schema, 'SF_A_BOUND_LEVEL_B_SUPPORT_COORDINATES_V1');
assert.equal(supportFixture.sourceApplicationSha, EXPECTED.applicationSha);
assert.equal(supportFixture.sourceProviderBlob, EXPECTED.providerBlob);
assert.equal(supportFixture.sourceRuntimeBlob, EXPECTED.runtimeBlob);
assert.equal(supportFixture.sourceRuntimeRawSha256, EXPECTED.runtimeSha256);
assert.equal(supportFixture.coordinateSystem, 'V1_IDW_COS_COORDINATES');
assert.equal(supportFixture.supportDistanceMax, EXPECTED.supportDistanceMax);
assert.equal(supportFixture.supportCoordinates.length, 58);
for (const row of supportFixture.supportCoordinates) {
  assert.equal(row.length, 5);
  assert.ok(row.every(Number.isFinite));
}

const DEG = Math.PI / 180;
const maxSq = EXPECTED.supportDistanceMax ** 2;
const supportCoordinates = supportFixture.supportCoordinates;

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

// Exact local-row regression against the already frozen support-only preflight.
const expectedUnsupportedLocal = [
  [0.05,45,135,2.0,0.6219943324111769],
  [0.05,45,135,2.25,0.6142974675329287],
  [0.05,45,135,2.5,0.6079275544744964],
  [0.05,45,135,2.75,0.6029266523944207],
  [0.05,45,180,2.0,0.6054627283339193],
  [0.05,60,135,2.0,0.6113606292607162],
  [0.30,45,0,6.25,0.6027022555028397],
];
const actualUnsupportedLocal = [];
for (const aod550 of AOD550) {
  for (const targetAltitudeDeg of TARGET_ALTITUDE_DEG) {
    for (const targetRelativeAzimuthDeg of TARGET_RELATIVE_AZIMUTH_DEG) {
      const direction = targetDirection(targetAltitudeDeg, targetRelativeAzimuthDeg);
      for (const sunDepressionDeg of SUN_DEPRESSION_DEG) {
        const s = fastSupport({ sunDepressionDeg, direction, aod550 });
        if (!s.supported) actualUnsupportedLocal.push([aod550,targetAltitudeDeg,targetRelativeAzimuthDeg,sunDepressionDeg,s.nearestTrainingDistance]);
      }
    }
  }
}
assert.equal(actualUnsupportedLocal.length, expectedUnsupportedLocal.length, 'local support-regression count drift');
for (let i = 0; i < expectedUnsupportedLocal.length; i += 1) {
  assert.deepEqual(actualUnsupportedLocal[i].slice(0,4), expectedUnsupportedLocal[i].slice(0,4), `local support identity drift at ${i}`);
  assert.ok(Math.abs(actualUnsupportedLocal[i][4] - expectedUnsupportedLocal[i][4]) <= 1e-14, `local nearest-distance drift at ${i}`);
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
      const s = rowSupport({ ...h, armId, gaze: h.gaze, sunDepressionDeg, stepDeg: EXPECTED.q2StepDeg, captureFailure: true });
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

const uniqueS1GapKey = new Set(gaps.filter(g => g.armId === 'S1_WHOLE_CAP').map(g => `${g.historyId.replace('arm=S1_WHOLE_CAP','arm=SHARED_20')}|sun=${g.sunDepressionDeg}`));
for (const g of gaps.filter(g => g.armId === 'S2_ALF')) {
  assert.ok(uniqueS1GapKey.has(`${g.historyId.replace('arm=S2_ALF','arm=SHARED_20')}|sun=${g.sunDepressionDeg}`), 'S1/S2 Q2 support gap mismatch');
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
  supportFixture: {
    schema: supportFixture.schema,
    sourceRuntimeRawSha256: supportFixture.sourceRuntimeRawSha256,
    supportCoordinateCount: supportCoordinates.length,
    localRegressionUnsupportedRows: actualUnsupportedLocal.length,
  },
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
