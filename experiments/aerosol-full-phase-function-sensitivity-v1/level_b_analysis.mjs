export const AFPF_LEVEL_B_SCHEMA_VERSION = 1;
export const AFPF_FIELD_FACTOR = 2.4;

export const AFPF_STATE_IDS = Object.freeze([
  'native-rural-ss',
  'opac-continental-average',
  'opac-maritime-clean',
  'opac-desert',
  'opac-desert-spheroids',
]);

export const AFPF_LEVEL_B_CONTRASTS = Object.freeze([
  Object.freeze({ contrastId: 'continental_vs_native', alternative: 'opac-continental-average', reference: 'native-rural-ss' }),
  Object.freeze({ contrastId: 'maritime_vs_native', alternative: 'opac-maritime-clean', reference: 'native-rural-ss' }),
  Object.freeze({ contrastId: 'desert_vs_native', alternative: 'opac-desert', reference: 'native-rural-ss' }),
  Object.freeze({ contrastId: 'desert_spheroids_vs_native', alternative: 'opac-desert-spheroids', reference: 'native-rural-ss' }),
  Object.freeze({ contrastId: 'maritime_vs_continental', alternative: 'opac-maritime-clean', reference: 'opac-continental-average' }),
  Object.freeze({ contrastId: 'desert_vs_continental', alternative: 'opac-desert', reference: 'opac-continental-average' }),
  Object.freeze({ contrastId: 'desert_spheroids_vs_desert', alternative: 'opac-desert-spheroids', reference: 'opac-desert' }),
]);

function finiteNumber(value) {
  return typeof value === 'number' && Number.isFinite(value);
}

function finitePositive(value) {
  return finiteNumber(value) && value > 0;
}

function delta(alternative, reference) {
  if (!finiteNumber(alternative) || !finiteNumber(reference)) return null;
  return alternative - reference;
}

export function summarizeThree(values) {
  if (!Array.isArray(values) || values.length !== 3) {
    throw new Error('exactly three preregistered paired replicate values required');
  }
  if (values.some(value => !finiteNumber(value))) {
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

export function limitingMagnitudeByState(recordsByState, limitingVMagnitude, fieldFactor = AFPF_FIELD_FACTOR) {
  if (typeof limitingVMagnitude !== 'function') {
    throw new Error('exact bound limitingVMagnitude function required');
  }
  if (!finitePositive(fieldFactor)) {
    throw new Error('fieldFactor must be finite positive');
  }
  const keys = Object.keys(recordsByState ?? {}).sort();
  const expected = [...AFPF_STATE_IDS].sort();
  if (JSON.stringify(keys) !== JSON.stringify(expected)) {
    throw new Error('exact five-state Level-B replicate universe required');
  }
  const out = {};
  for (const stateId of AFPF_STATE_IDS) {
    const background = recordsByState[stateId]?.photopicLuminanceCdM2;
    if (!finitePositive(background)) {
      out[stateId] = null;
      continue;
    }
    const value = limitingVMagnitude({
      backgroundLuminanceCdM2: background,
      fieldFactor,
      branch: 'full',
    });
    out[stateId] = finiteNumber(value) ? value : null;
  }
  return out;
}

export function replicateLevelBContrasts(recordsByState, limitingVMagnitude, fieldFactor = AFPF_FIELD_FACTOR) {
  const limitingByState = limitingMagnitudeByState(recordsByState, limitingVMagnitude, fieldFactor);
  const pairedLimitingMagnitudeDelta = {};
  for (const { contrastId, alternative, reference } of AFPF_LEVEL_B_CONTRASTS) {
    pairedLimitingMagnitudeDelta[contrastId] = delta(limitingByState[alternative], limitingByState[reference]);
  }
  return {
    limitingVMagnitudeByState: limitingByState,
    pairedLimitingMagnitudeDelta,
    fieldFactor,
    branch: 'full',
    universalSunDepressionToMinutesConversionPermitted: false,
  };
}

export function summarizeLevelBThreeReplicates(replicates) {
  if (!Array.isArray(replicates) || replicates.length !== 3) {
    throw new Error('exactly three Level-B replicate records required');
  }
  const contrasts = {};
  for (const { contrastId } of AFPF_LEVEL_B_CONTRASTS) {
    contrasts[contrastId] = summarizeThree(
      replicates.map(row => row?.pairedLimitingMagnitudeDelta?.[contrastId] ?? null),
    );
  }
  return {
    schemaVersion: AFPF_LEVEL_B_SCHEMA_VERSION,
    status: 'COMPLETED_PREREGISTERED_AFPF_LEVEL_B_SUMMARY',
    fieldFactor: AFPF_FIELD_FACTOR,
    humanModel: 'Crumey 2014 eq.34 full branch via separately byte-bound human-threshold.mjs',
    contrastCount: AFPF_LEVEL_B_CONTRASTS.length,
    priorityShapeContrast: 'desert_spheroids_vs_desert',
    contrasts,
    pValuesPermitted: false,
    confidenceIntervalsPermitted: false,
    epsilonSubstitutionPermitted: false,
    universalSunDepressionToMinutesConversionPermitted: false,
    timeConversionRequiresActualDateLocationSolarDepressionRate: true,
  };
}
