export const AOPS_LEVEL_B_SCHEMA_VERSION = 1;
export const AOPS_FIELD_FACTOR = 2.4;
export const AOPS_STATE_IDS = Object.freeze([
  'native-rural-ss',
  'ssa085-g060',
  'ssa085-g080',
  'ssa098-g060',
  'ssa098-g080',
]);

export const AOPS_LEVEL_B_CONTRASTS = Object.freeze([
  'native_vs_ssa085_g060',
  'native_vs_ssa085_g080',
  'native_vs_ssa098_g060',
  'native_vs_ssa098_g080',
  'ssa_high_vs_low_at_g060',
  'ssa_high_vs_low_at_g080',
  'g_high_vs_low_at_ssa085',
  'g_high_vs_low_at_ssa098',
  'ssa_x_g_interaction',
]);

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

function interaction(aHighG, aLowG, bHighG, bLowG) {
  const high = delta(aHighG, bHighG);
  const low = delta(aLowG, bLowG);
  return delta(high, low);
}

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

export function limitingMagnitudeByState(recordsByState, limitingVMagnitude, fieldFactor = AOPS_FIELD_FACTOR) {
  if (typeof limitingVMagnitude !== 'function') {
    throw new Error('exact bound limitingVMagnitude function required');
  }
  if (!finitePositive(fieldFactor)) {
    throw new Error('fieldFactor must be finite positive');
  }
  const keys = Object.keys(recordsByState ?? {}).sort();
  const expected = [...AOPS_STATE_IDS].sort();
  if (JSON.stringify(keys) !== JSON.stringify(expected)) {
    throw new Error('exact five-state Level-B replicate universe required');
  }
  const out = {};
  for (const stateId of AOPS_STATE_IDS) {
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

export function replicateLevelBContrasts(recordsByState, limitingVMagnitude, fieldFactor = AOPS_FIELD_FACTOR) {
  const m = limitingMagnitudeByState(recordsByState, limitingVMagnitude, fieldFactor);
  const n = m['native-rural-ss'];
  const s85g60 = m['ssa085-g060'];
  const s85g80 = m['ssa085-g080'];
  const s98g60 = m['ssa098-g060'];
  const s98g80 = m['ssa098-g080'];
  return {
    limitingVMagnitudeByState: m,
    pairedLimitingMagnitudeDelta: {
      native_vs_ssa085_g060: delta(s85g60, n),
      native_vs_ssa085_g080: delta(s85g80, n),
      native_vs_ssa098_g060: delta(s98g60, n),
      native_vs_ssa098_g080: delta(s98g80, n),
      ssa_high_vs_low_at_g060: delta(s98g60, s85g60),
      ssa_high_vs_low_at_g080: delta(s98g80, s85g80),
      g_high_vs_low_at_ssa085: delta(s85g80, s85g60),
      g_high_vs_low_at_ssa098: delta(s98g80, s98g60),
      ssa_x_g_interaction: interaction(s98g80, s98g60, s85g80, s85g60),
    },
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
  for (const name of AOPS_LEVEL_B_CONTRASTS) {
    summaries[name] = summarizeThree(replicates.map(r => r?.pairedLimitingMagnitudeDelta?.[name] ?? null));
  }
  return {
    schemaVersion: AOPS_LEVEL_B_SCHEMA_VERSION,
    status: 'COMPLETED_PREREGISTERED_LEVEL_B_SUMMARY',
    fieldFactor: AOPS_FIELD_FACTOR,
    humanModel: 'Crumey 2014 eq.34 full branch via separately byte-bound human-threshold.mjs',
    contrasts: summaries,
    pValuesPermitted: false,
    confidenceIntervalsPermitted: false,
    epsilonSubstitutionPermitted: false,
    universalSunDepressionToMinutesConversionPermitted: false,
    timeConversionRequiresActualDateLocationSolarDepressionRate: true,
  };
}
