import assert from 'node:assert/strict';
import {
  buildFrozenTimingArmLedger,
  buildTimingArm,
  controlledEquilibriumPreludeStateLog10,
} from './sf-a-temporal-axis-audit.mjs';

const ledger = buildFrozenTimingArmLedger();
assert.equal(ledger.length, 12);
const supported = ledger.filter(row => row.status === 'SUPPORTED');
const refused = ledger.filter(row => row.status !== 'SUPPORTED');
assert.equal(supported.length, 11);
assert.equal(refused.length, 1);
assert.equal(refused[0].latitudeDeg, 60);
assert.equal(refused[0].declinationDeg, 23.44);

for (const row of supported) {
  assert.equal(row.timeSeconds.length, 35);
  assert.equal(row.sunDepressionDeg.length, 35);
  assert.equal(row.timeSeconds[0], 0);
  assert.ok(row.durationSeconds > 0);
  assert.ok(row.minStepSeconds > 0);
  assert.ok(row.maxStepSeconds >= row.minStepSeconds);
  for (let i = 1; i < row.timeSeconds.length; i += 1) assert.ok(row.timeSeconds[i] > row.timeSeconds[i - 1]);
}

const equatorEquinox = buildTimingArm({ latitudeDeg: 0, declinationDeg: 0 });
assert.equal(equatorEquinox.status, 'SUPPORTED');
assert.ok(Math.abs(equatorEquinox.durationSeconds - 2040) < 1e-9);
assert.ok(Math.abs(equatorEquinox.minStepSeconds - 60) < 1e-9);
assert.ok(Math.abs(equatorEquinox.maxStepSeconds - 60) < 1e-9);

const equatorSouth = buildTimingArm({ latitudeDeg: 0, declinationDeg: -23.44 });
const equatorNorth = buildTimingArm({ latitudeDeg: 0, declinationDeg: 23.44 });
assert.ok(Math.abs(equatorSouth.durationSeconds - equatorNorth.durationSeconds) < 1e-9);

assert.equal(controlledEquilibriumPreludeStateLog10(1), 0);
assert.equal(controlledEquilibriumPreludeStateLog10(0.01), -2);
assert.throws(() => controlledEquilibriumPreludeStateLog10(0), /positive finite/);

console.log(JSON.stringify({
  schema: 'SF_A_TEMPORAL_AXIS_AUDIT_V1',
  supportedTimingArms: supported.length,
  refusedTimingArms: refused.length,
  equatorEquinoxDurationSeconds: equatorEquinox.durationSeconds,
  refusedArm: refused[0],
}, null, 2));
