import assert from 'node:assert/strict';
import test from 'node:test';

import {
  AVPS_ALTERNATIVE_STATES,
  AVPS_FIELD_FACTOR,
  AVPS_LEVEL_B_CONTRASTS,
  AVPS_REFERENCE_STATE,
  AVPS_STATE_IDS,
  replicateLevelBContrasts,
  summarizeLevelBThreeReplicates,
  summarizeThree,
} from '../experiments/aerosol-vertical-profile-sensitivity-v1/level_b_analysis.mjs';

const records = Object.fromEntries(AVPS_STATE_IDS.map((stateId, index) => [stateId, {
  photopicLuminanceCdM2: [1, 2, 4, 8, 16][index],
}]));

function fakeLimiting({ backgroundLuminanceCdM2, fieldFactor, branch }) {
  assert.equal(fieldFactor, 3.14);
  assert.equal(branch, 'full');
  return 10 - Math.log10(backgroundLuminanceCdM2);
}

test('AVPS Level-B freezes F=3.14 and exactly four alt-vs-reference contrasts', () => {
  assert.equal(AVPS_FIELD_FACTOR, 3.14);
  assert.equal(AVPS_REFERENCE_STATE, 'opac-profile-continental-average');
  assert.equal(AVPS_ALTERNATIVE_STATES.length, 4);
  assert.equal(AVPS_LEVEL_B_CONTRASTS.length, 4);
  const out = replicateLevelBContrasts(records, fakeLimiting);
  assert.equal(Object.keys(out.pairedLimitingMagnitudeDelta).length, 4);
  assert.equal(out.fieldFactor, 3.14);
  assert.equal(out.branch, 'full');
  assert.equal(out.universalSunDepressionToMinutesConversionPermitted, false);
});

test('AVPS Level-B refuses any field factor other than 3.14', () => {
  assert.throws(() => replicateLevelBContrasts(records, fakeLimiting, 2.4), /frozen at 3.14/);
});

test('three-replicate summary uses mean/sample-SD/SE and fail-closed unresolved semantics', () => {
  const finite = summarizeThree([1, 2, 3]);
  assert.equal(finite.status, 'FINITE_THREE_REPLICATES');
  assert.equal(finite.mean, 2);
  assert.equal(finite.sampleStd, 1);
  assert.ok(Math.abs(finite.standardError - 1 / Math.sqrt(3)) < 1e-15);
  const unresolved = summarizeThree([1, null, 3]);
  assert.equal(unresolved.status, 'NUMERICALLY_UNRESOLVED');
  assert.equal(unresolved.mean, null);
});

test('final Level-B summary contains exactly the preregistered contrast universe', () => {
  const reps = [0, 1, 2].map(() => replicateLevelBContrasts(records, fakeLimiting));
  const out = summarizeLevelBThreeReplicates(reps);
  assert.equal(out.status, 'COMPLETED_PREREGISTERED_AVPS_LEVEL_B_SUMMARY');
  assert.deepEqual(Object.keys(out.contrasts).sort(), [...AVPS_LEVEL_B_CONTRASTS].sort());
  assert.equal(out.fieldFactor, 3.14);
  assert.equal(out.pValuesPermitted, false);
  assert.equal(out.confidenceIntervalsPermitted, false);
  assert.equal(out.epsilonSubstitutionPermitted, false);
  assert.equal(out.universalSunDepressionToMinutesConversionPermitted, false);
});
