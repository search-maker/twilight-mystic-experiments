export const CRUMEY_EQ34_LOCAL_MAX_B = 0.021567318651181808;

function positive(name, value) {
  const number = Number(value);
  if (!Number.isFinite(number) || number <= 0) throw new RangeError(`${name} must be finite and > 0`);
  return number;
}

function ordered(aName, a, bName, b) {
  const left = positive(aName, a);
  const right = positive(bName, b);
  if (right < left) throw new RangeError(`${bName} must be >= ${aName}`);
  return [left, right];
}

export function anchoredPathEnvelopeThreshold({ anchorB, endB, thresholdLux, localMaximumB = CRUMEY_EQ34_LOCAL_MAX_B }) {
  const [anchor, end] = ordered('anchorB', anchorB, 'endB', endB);
  if (typeof thresholdLux !== 'function') throw new TypeError('thresholdLux function required');
  const localMax = positive('localMaximumB', localMaximumB);
  let value = Math.max(thresholdLux(anchor), thresholdLux(end));
  if (anchor <= localMax && localMax <= end) value = Math.max(value, thresholdLux(localMax));
  if (!Number.isFinite(value) || value <= 0) throw new RangeError('path-envelope threshold invalid');
  return value;
}

export function leftGeneralizedInverseAnchoredEnvelope({
  anchorB,
  upperB,
  targetThresholdLux,
  thresholdLux,
  localMaximumB = CRUMEY_EQ34_LOCAL_MAX_B,
  relativeThresholdTolerance = 1e-12,
  maxIterations = 160,
}) {
  const [anchor, upper] = ordered('anchorB', anchorB, 'upperB', upperB);
  const target = positive('targetThresholdLux', targetThresholdLux);
  const rtol = Number(relativeThresholdTolerance);
  if (!Number.isFinite(rtol) || rtol <= 0 || rtol >= 1e-6) throw new RangeError('relativeThresholdTolerance out of frozen numerical range');
  if (!Number.isInteger(maxIterations) || maxIterations < 64 || maxIterations > 256) throw new RangeError('maxIterations out of frozen range');
  const atAnchor = anchoredPathEnvelopeThreshold({ anchorB: anchor, endB: anchor, thresholdLux, localMaximumB });
  const atUpper = anchoredPathEnvelopeThreshold({ anchorB: anchor, endB: upper, thresholdLux, localMaximumB });
  const tol = Math.max(Number.MIN_VALUE, target * rtol);
  if (target < atAnchor - tol || target > atUpper + tol) throw new RangeError('target threshold outside attained anchored-envelope range');
  if (Math.abs(target - atAnchor) <= tol) {
    return Object.freeze({ backgroundCdM2: anchor, forwardThresholdLux: atAnchor, iterations: 0, relativeThresholdTolerance: rtol });
  }
  let lo = anchor;
  let hi = upper;
  // Seek the left boundary of {B: M_anchor(B) >= target - tol}.
  for (let i = 0; i < maxIterations; i += 1) {
    const mid = lo + (hi - lo) / 2;
    if (mid === lo || mid === hi) break;
    const value = anchoredPathEnvelopeThreshold({ anchorB: anchor, endB: mid, thresholdLux, localMaximumB });
    if (value >= target - tol) hi = mid;
    else lo = mid;
  }
  const forward = anchoredPathEnvelopeThreshold({ anchorB: anchor, endB: hi, thresholdLux, localMaximumB });
  if (Math.abs(forward - target) > Math.max(tol * 2, target * 5e-12)) {
    throw new Error(`generalized-inverse forward check failed: ${forward} vs ${target}`);
  }
  return Object.freeze({ backgroundCdM2: hi, forwardThresholdLux: forward, iterations: maxIterations, relativeThresholdTolerance: rtol });
}

export function thresholdDerivedEquivalentBackground({ adaptationFieldB, laggedAdaptationB, thresholdLux }) {
  const [adaptationB, laggedB] = ordered('adaptationFieldB', adaptationFieldB, 'laggedAdaptationB', laggedAdaptationB);
  const adaptationThresholdLux = anchoredPathEnvelopeThreshold({ anchorB: adaptationB, endB: laggedB, thresholdLux });
  const inverse = leftGeneralizedInverseAnchoredEnvelope({
    anchorB: adaptationB,
    upperB: laggedB,
    targetThresholdLux: adaptationThresholdLux,
    thresholdLux,
  });
  const equivalentBackgroundCdM2 = Math.max(0, inverse.backgroundCdM2 - adaptationB);
  return Object.freeze({
    adaptationFieldB: adaptationB,
    laggedAdaptationB: laggedB,
    adaptationThresholdLux,
    inferredTotalAdaptationBackgroundCdM2: inverse.backgroundCdM2,
    equivalentBackgroundCdM2,
    inverseForwardThresholdLux: inverse.forwardThresholdLux,
  });
}

export function candidate4Threshold({ adaptationFieldB, laggedAdaptationB, physicalDetectionB, thresholdLux }) {
  const detectionB = positive('physicalDetectionB', physicalDetectionB);
  const derived = thresholdDerivedEquivalentBackground({ adaptationFieldB, laggedAdaptationB, thresholdLux });
  const effectiveDetectionEndB = detectionB + derived.equivalentBackgroundCdM2;
  const thresholdIlluminanceLux = anchoredPathEnvelopeThreshold({ anchorB: detectionB, endB: effectiveDetectionEndB, thresholdLux });
  return Object.freeze({ ...derived, physicalDetectionB: detectionB, effectiveDetectionEndB, thresholdIlluminanceLux });
}
