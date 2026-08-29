import assert from 'node:assert/strict';
import {
  AOD550,
  SUN_DEPRESSION_DEG,
  TARGET_ALTITUDE_DEG,
  TARGET_RELATIVE_AZIMUTH_DEG,
  SPATIAL_ARMS,
  MAPPING_ELIGIBLE_CHANNEL,
  DIAGNOSTIC_ONLY_CHANNELS,
  MESOPIC_STATUS,
  alfWeight,
  angularSeparationDeg,
  auditFrozenInputGeometry,
  buildSphericalCapQuadrature,
  fixationCenter,
  foldRelativeAzimuthDeg,
  integrateSpatialArm,
  offsetDirection,
  providerRelativeAzimuthDeg,
  targetDirection,
} from './sf-a-spatial-input-audit.mjs';

assert.equal(SUN_DEPRESSION_DEG.length, 35);
assert.deepEqual([SUN_DEPRESSION_DEG[0], SUN_DEPRESSION_DEG.at(-1)], [2, 10.5]);
assert.equal(AOD550.length * TARGET_ALTITUDE_DEG.length * TARGET_RELATIVE_AZIMUTH_DEG.length, 45);
assert.equal(MAPPING_ELIGIBLE_CHANNEL, 'photopic');
assert.deepEqual(DIAGNOSTIC_ONLY_CHANNELS, ['scotopic']);
assert.match(MESOPIC_STATUS, /^UNAVAILABLE_/);

for (const az of [-720, -181, -180, -1, 0, 1, 179, 180, 181, 359, 360, 541]) {
  const f = foldRelativeAzimuthDeg(az);
  assert.ok(f >= 0 && f <= 180);
}

const t = targetDirection(45, 90);
for (const d of [1, 8, 11, 14, 20]) {
  for (const b of [0, 45, 90, 180, 270]) {
    const p = offsetDirection(t, d, b);
    assert.ok(Math.abs(angularSeparationDeg(t, p) - d) < 1e-9);
    assert.ok(providerRelativeAzimuthDeg(p) >= 0 && providerRelativeAzimuthDeg(p) <= 180);
  }
}

for (const e of [8, 11, 14]) {
  for (const orientation of ['toward_sun', 'away_from_sun', 'cross_plus90', 'cross_minus90']) {
    const c = fixationCenter({ sunDepressionDeg: 6, targetAltitudeDeg: 45, targetRelativeAzimuthDeg: 90, eccentricityDeg: e, orientation });
    assert.ok(Math.abs(angularSeparationDeg(t, c) - e) < 1e-9);
  }
}

for (const capDeg of [12.4, 16, 20]) {
  const q = buildSphericalCapQuadrature({ capDeg, radialStepDeg: 1 });
  const sum = q.reduce((s, x) => s + x.solidAngleSr, 0);
  const expected = 2 * Math.PI * (1 - Math.cos(capDeg * Math.PI / 180));
  assert.ok(Math.abs(sum - expected) < 1e-12);
}
assert.ok(alfWeight(0) > alfWeight(1));
assert.ok(alfWeight(1) > alfWeight(5));
assert.ok(alfWeight(5) > alfWeight(20));

const constantSampler = (_direction, channel) => ({ supported: true, value: channel === 'photopic' ? 7.25 : 9.5 });
for (const armId of Object.keys(SPATIAL_ARMS)) {
  const center = { altitudeDeg: 45, azimuthDeg: 90 };
  const p = integrateSpatialArm({ armId, center, sampleDirection: constantSampler, channel: 'photopic' });
  assert.equal(p.status, 'SUPPORTED');
  assert.equal(p.mappingEligible, true);
  assert.ok(Math.abs(p.value - 7.25) < 1e-12);
  const s = integrateSpatialArm({ armId, center, sampleDirection: constantSampler, channel: 'scotopic' });
  assert.equal(s.status, 'SUPPORTED');
  assert.equal(s.mappingEligible, false);
  assert.ok(Math.abs(s.value - 9.5) < 1e-12);
}

let calls = 0;
const refusal = integrateSpatialArm({
  armId: 'S2_ALF',
  center: { altitudeDeg: 45, azimuthDeg: 90 },
  sampleDirection: () => {
    calls += 1;
    if (calls === 7) return { supported: false, value: null };
    return { supported: true, value: 1 };
  },
});
assert.equal(refusal.status, 'REFUSED_UNSUPPORTED_OR_NONPOSITIVE_SAMPLE');
assert.equal(refusal.sampleCountBeforeRefusal, 6);

const audit = auditFrozenInputGeometry();
assert.equal(audit.baseHistoryCount, 45);
assert.equal(audit.timeRowsPerHistory, 35);
assert.equal(audit.totalSpatialGazeRows, 63000);
assert.equal(audit.nominalAltitudeCompleteRows, 53184);
assert.equal(audit.nominalAltitudeIncompleteRows, 9816);
assert.equal(audit.nominalAltitudeCompleteRows + audit.nominalAltitudeIncompleteRows, 63000);

const summary = {
  schema: audit.schema,
  baseHistoryCount: audit.baseHistoryCount,
  timeRowsPerHistory: audit.timeRowsPerHistory,
  totalSpatialGazeRows: audit.totalSpatialGazeRows,
  nominalAltitudeCompleteRows: audit.nominalAltitudeCompleteRows,
  nominalAltitudeIncompleteRows: audit.nominalAltitudeIncompleteRows,
  nominalAltitudeCompleteFraction: audit.nominalAltitudeCompleteRows / audit.totalSpatialGazeRows,
  byArm: {},
};
for (const armId of Object.keys(SPATIAL_ARMS)) {
  const rows = audit.rows.filter(r => r.armId === armId);
  const complete = rows.filter(r => r.nominalAltitudeComplete).length;
  summary.byArm[armId] = { rows: rows.length, complete, incomplete: rows.length - complete };
}
console.log(JSON.stringify(summary, null, 2));
