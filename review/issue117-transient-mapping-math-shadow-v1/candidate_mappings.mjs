const LOCAL_MAX_B = 0.021567318651181808;

function finitePositive(name, value) {
  if (!Number.isFinite(value) || value <= 0) throw new RangeError(`${name} must be > 0`);
  return value;
}

function ordered(name0, b0, name1, b1) {
  finitePositive(name0, b0); finitePositive(name1, b1);
  if (b1 < b0) throw new RangeError(`${name1} must be >= ${name0}`);
}

export function currentDirectDebtThreshold({ physicalDetectionB, effectiveB, thresholdLux }) {
  ordered('physicalDetectionB', physicalDetectionB, 'effectiveB', effectiveB);
  return thresholdLux(effectiveB);
}

export function endpointFloorThreshold({ physicalDetectionB, effectiveB, thresholdLux }) {
  ordered('physicalDetectionB', physicalDetectionB, 'effectiveB', effectiveB);
  return Math.max(thresholdLux(physicalDetectionB), thresholdLux(effectiveB));
}

export function pathEnvelopeThreshold({ physicalDetectionB, effectiveB, thresholdLux, localMaximumB = LOCAL_MAX_B }) {
  ordered('physicalDetectionB', physicalDetectionB, 'effectiveB', effectiveB);
  finitePositive('localMaximumB', localMaximumB);
  let out = Math.max(thresholdLux(physicalDetectionB), thresholdLux(effectiveB));
  if (physicalDetectionB <= localMaximumB && localMaximumB <= effectiveB) {
    out = Math.max(out, thresholdLux(localMaximumB));
  }
  return out;
}

export function adaptationThresholdRatio({
  adaptationFieldB,
  laggedAdaptationB,
  physicalDetectionB,
  thresholdLux,
  localMaximumB = LOCAL_MAX_B,
}) {
  ordered('adaptationFieldB', adaptationFieldB, 'laggedAdaptationB', laggedAdaptationB);
  finitePositive('physicalDetectionB', physicalDetectionB);
  const adaptationEnvelope = pathEnvelopeThreshold({
    physicalDetectionB: adaptationFieldB,
    effectiveB: laggedAdaptationB,
    thresholdLux,
    localMaximumB,
  });
  const equilibriumAdaptation = thresholdLux(adaptationFieldB);
  const ratio = adaptationEnvelope / equilibriumAdaptation;
  if (!Number.isFinite(ratio) || ratio < 1 - 1e-12) throw new Error('adaptation desensitisation ratio fell below 1');
  return thresholdLux(physicalDetectionB) * Math.max(1, ratio);
}

export const ISSUE117_MAPPING_CONSTANTS = Object.freeze({
  localMaximumBackgroundCdM2: LOCAL_MAX_B,
});
