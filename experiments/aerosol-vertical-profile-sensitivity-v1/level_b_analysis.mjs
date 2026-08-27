export const AVPS_LEVEL_B_SCHEMA_VERSION = 1;
export const AVPS_FIELD_FACTOR = 3.14;
export const AVPS_REFERENCE_STATE = 'opac-profile-continental-average';
export const AVPS_ALTERNATIVE_STATES = Object.freeze([
  'opac-profile-maritime-clean',
  'opac-profile-desert',
  'opac-profile-arctic',
  'opac-profile-antarctic',
]);
export const AVPS_STATE_IDS = Object.freeze([AVPS_REFERENCE_STATE, ...AVPS_ALTERNATIVE_STATES]);

function finiteNumber(value) {
  return typeof value === 'number' && Number.isFinite(value);
}

function finitePositive(value) {
  return finiteNumber(value) && value > 0;
}

function delta(a, b) {
  if (!finiteNumber(a) || !finiteNumber(b)) return null;
  return a - b;
}

export function contrastName(stateId) {
  if (!AVPS_ALTERNATIVE_STATES.includes(stateId)) {
    throw new Error(`not a preregistered AVPS alternative state: ${stateId}`);
  }
  return `${stateId}_vs_${AVPS_REFERENCE_STATE}`;
}

export const AVPS_LEVEL_B_CONTRASTS = Object.freeze(AVPS_ALTERNATIVE_STATES.map(contrastName));

export function summarizeThree(values) {
  if (!Array.isArray(values) || values.length !== 3) {
    throw new Error('exactly three preregistered paired replicate values required');
  }
  if (values.some(v => !finiteNumber(v))) {
    return {
      status: 'NUMERICALLY_UNRESOLVED',
      replicateValues: values,
      mean: null,
      sampleStd: null,
      standardError: null,
    };
  }
  const mean = values.reduce((a, b) => a + b, 0) / 3;
  const sampleVariance = values.reduce((a, b) => a + (b - mean) ** 2, 0) / 2;
  const sampleStd = Math.sqrt(sampleVariance);
  return {
    status: 'FINITE_THREE_REPLICATES',
    replicateValues: values,
    mean,
    sampleStd,
    standardError: sampleStd / Math.sqrt(3),
  };
}

export function limitingMagnitudeByState(recordsByState, limitingVMagnitude, fieldFactor = AVPS_FIELD_FACTOR) {
  if (typeof limitingVMagnitude !== 'function') {
    throw new Error('exact bound limitingVMagnitude function required');
  }
  if (!finitePositive(fieldFactor) || fieldFactor !== AVPS_FIELD_FACTOR) {
    throw new Error('AVPS fieldFactor is frozen at 3.14');
  }
  const keys = Object.keys(recordsByState ?? {}).sort();
  const expected = [...AVPS_STATE_IDS].sort();
  if (JSON.stringify(keys) !== JSON.stringify(expected)) {
    throw new Error('exact five-state AVPS Level-B replicate universe required');
  }
  const out = {};
  for (const stateId of AVPS_STATE_IDS) {
    const B = recordsByState[stateId]?.photopicLuminanceCdM2;
    if (!finitePositive(B)) {
      out[stateId] = null;
      continue;
    }
    const value = limitingVMagnitude({
      backgroundLuminanceCdM2: B,
      fieldFactor,
      branch: 'full',
    });
    out[stateId] = finiteNumber(value) ? value : null;
  }
  return out;
}

export function replicateLevelBContrasts(recordsByState, limitingVMagnitude, fieldFactor = AVPS_FIELD_FACTOR) {
  const magnitudes = limitingMagnitudeByState(recordsByState, limitingVMagnitude, fieldFactor);
  const reference = magnitudes[AVPS_REFERENCE_STATE];
  const paired = {};
  for (const stateId of AVPS_ALTERNATIVE_STATES) {
    paired[contrastName(stateId)] = delta(magnitudes[stateId], reference);
  }
  return {
    limitingVMagnitudeByState: magnitudes,
    pairedLimitingMagnitudeDelta: paired,
    fieldFactor,
    branch: 'full',
    universalSunDepressionToMinutesConversionPermitted: false,
  };
}

export function summarizeLevelBThreeReplicates(replicates) {
  if (!Array.isArray(replicates) || replicates.length !== 3) {
    throw new Error('exactly three Level-B replicate records required');
  }
  const summaries = {};
  for (const name of AVPS_LEVEL_B_CONTRASTS) {
    summaries[name] = summarizeThree(replicates.map(r => r?.pairedLimitingMagnitudeDelta?.[name] ?? null));
  }
  return {
    schemaVersion: AVPS_LEVEL_B_SCHEMA_VERSION,
    status: 'COMPLETED_PREREGISTERED_AVPS_LEVEL_B_SUMMARY',
    fieldFactor: AVPS_FIELD_FACTOR,
    humanModel: 'Crumey 2014 eq.34 full branch via separately byte-bound human-threshold.mjs',
    contrasts: summaries,
    pValuesPermitted: false,
    confidenceIntervalsPermitted: false,
    epsilonSubstitutionPermitted: false,
    universalSunDepressionToMinutesConversionPermitted: false,
    timeConversionRequiresActualDateLocationSolarDepressionRate: true,
  };
}
