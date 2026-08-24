/**
 * Human point-source visibility reference model.
 *
 * Scientific basis:
 * - Crumey (2014), MNRAS 442, 2600-2619, eqs. 28, 34, 53.
 * - Blackwell laboratory threshold data as re-fit by Crumey.
 *
 * IMPORTANT: this module deliberately separates physical stimulus from observer
 * criterion. Sky luminance and stellar extinction should be computed by the
 * atmosphere/sky model. The field factor multiplies the human threshold only.
 */

export const V_BAND_ZERO_POINT_LUX = 2.54e-6;

export const CRUMEY_POINT_SOURCE_COEFFICIENTS = Object.freeze({
  a1: 5.949e-8,
  a2: -2.389e-7,
  a3: 2.459e-7,
  a4: 4.120e-4,
  a5: -4.225e-4,
  r1: 6.505e-4,
  r2: -8.461e-4,
  scotopicPhotopicSplitCdM2: 7.08e-2,
});

/**
 * Observer/detection-criterion presets.
 * These are threshold multipliers, not magnitude bonuses.
 *
 * forcedChoice50: Blackwell statistical normalization, NOT ordinary conscious seeing.
 * confident90: Blackwell observers generally reported confidence at >=90% detection.
 * commonSenseSeeing: Blackwell & Blackwell conversion to ordinary 'just visible'.
 * typicalAstronomical: Crumey's illustrative notional field factor.
 *
 * Expert known-position mode must be calibrated from actual expert observations;
 * no invented constant is provided here.
 */
export const FIELD_FACTOR_PRESETS = Object.freeze({
  forcedChoice50: 1.0,
  confident90: 1.62,
  typicalAstronomical: 2.0,
  commonSenseSeeing: 2.4,
});

function requirePositiveFinite(name, value) {
  if (!Number.isFinite(value) || value <= 0) {
    throw new RangeError(`${name} must be a finite number > 0; got ${value}`);
  }
}

function requireFinite(name, value) {
  if (!Number.isFinite(value)) {
    throw new RangeError(`${name} must be finite; got ${value}`);
  }
}

/**
 * Crumey 2014 eq. 34, point-source threshold across the achromatic range.
 * B is local background luminance in cd/m^2. Return value is threshold point-source
 * illuminance at the eye in lux for the Blackwell 50% forced-choice normalization.
 */
export function crumeyBasePointSourceThresholdLux(backgroundLuminanceCdM2) {
  const B = backgroundLuminanceCdM2;
  requirePositiveFinite('backgroundLuminanceCdM2', B);
  const { a1, a2, a3, a4, a5 } = CRUMEY_POINT_SOURCE_COEFFICIENTS;
  const radicand = a1 * B ** 0.5 + a2 * B ** 0.75 + a3 * B;
  if (radicand < -1e-18) {
    throw new RangeError(`Crumey eq.34 radicand became negative (${radicand}) at B=${B}`);
  }
  const term = Math.sqrt(Math.max(0, radicand)) + a4 * B ** 0.25 + a5 * B ** 0.5;
  return term * term;
}

/** Crumey 2014 eq. 53, scotopic point-source threshold branch. */
export function crumeyScotopicBasePointSourceThresholdLux(backgroundLuminanceCdM2) {
  const B = backgroundLuminanceCdM2;
  requirePositiveFinite('backgroundLuminanceCdM2', B);
  const { r1, r2 } = CRUMEY_POINT_SOURCE_COEFFICIENTS;
  const term = r1 * B ** 0.25 + r2 * B ** 0.5;
  return term * term;
}

export function thresholdLux({
  backgroundLuminanceCdM2,
  fieldFactor = FIELD_FACTOR_PRESETS.commonSenseSeeing,
  branch = 'full',
}) {
  requirePositiveFinite('fieldFactor', fieldFactor);
  const base = branch === 'scotopic'
    ? crumeyScotopicBasePointSourceThresholdLux(backgroundLuminanceCdM2)
    : branch === 'full'
      ? crumeyBasePointSourceThresholdLux(backgroundLuminanceCdM2)
      : (() => { throw new RangeError(`unknown branch: ${branch}`); })();
  return fieldFactor * base;
}

export function vMagnitudeToIlluminanceLux(vMagnitude) {
  requireFinite('vMagnitude', vMagnitude);
  return V_BAND_ZERO_POINT_LUX * 10 ** (-0.4 * vMagnitude);
}

export function illuminanceLuxToVMagnitude(illuminanceLux) {
  requirePositiveFinite('illuminanceLux', illuminanceLux);
  return 2.5 * Math.log10(V_BAND_ZERO_POINT_LUX / illuminanceLux);
}

export function backgroundLuminanceToVSurfaceBrightness(backgroundLuminanceCdM2) {
  requirePositiveFinite('backgroundLuminanceCdM2', backgroundLuminanceCdM2);
  return -2.5 * Math.log10(backgroundLuminanceCdM2) + 12.58;
}

export function limitingVMagnitude({
  backgroundLuminanceCdM2,
  fieldFactor = FIELD_FACTOR_PRESETS.commonSenseSeeing,
  branch = 'full',
}) {
  return illuminanceLuxToVMagnitude(thresholdLux({
    backgroundLuminanceCdM2,
    fieldFactor,
    branch,
  }));
}

/** Crumey 2014 eq. 14: approximate scotopic-photopic stellar magnitude offset. */
export function scotopicMinusPhotopicMagnitudeFromBV(bMinusV) {
  requireFinite('bMinusV', bMinusV);
  if (bMinusV < -0.17 || bMinusV > 1.65) {
    throw new RangeError('B-V outside Crumey linear-approximation range [-0.17, 1.65]');
  }
  return 0.27 * bMinusV - 0.10;
}

/** Crumey 2014 eq. 12: stellar S/P ratio estimate from B-V. */
export function stellarScotopicToPhotopicRatioFromBV(bMinusV) {
  requireFinite('bMinusV', bMinusV);
  const c = bMinusV;
  if (c < -0.17 || c > 1.65) {
    throw new RangeError('B-V outside validated stellar S/P colour range [-0.17, 1.65]');
  }
  const log10rho =
    -0.05905 * c ** 6 +
    0.1674 * c ** 5 -
    0.06563 * c ** 4 -
    0.1843 * c ** 3 +
    0.2031 * c ** 2 -
    0.1802 * c +
    0.4447;
  return 10 ** log10rho;
}

/**
 * End-to-end point-source decision once the physical sky and stellar extinction
 * have already been evaluated.
 */
export function evaluatePointSourceVisibility({
  backgroundLuminanceCdM2,
  starTopOfAtmosphereVMag,
  extinctionMagV = 0,
  colorSignalOffsetMag = 0,
  fieldFactor = FIELD_FACTOR_PRESETS.commonSenseSeeing,
  branch = 'full',
}) {
  requireFinite('starTopOfAtmosphereVMag', starTopOfAtmosphereVMag);
  requireFinite('extinctionMagV', extinctionMagV);
  requireFinite('colorSignalOffsetMag', colorSignalOffsetMag);

  const apparentVMagAtEye = starTopOfAtmosphereVMag + extinctionMagV + colorSignalOffsetMag;
  const starIlluminanceLux = vMagnitudeToIlluminanceLux(apparentVMagAtEye);
  const thresholdIlluminanceLux = thresholdLux({
    backgroundLuminanceCdM2,
    fieldFactor,
    branch,
  });
  const visibilityRatio = starIlluminanceLux / thresholdIlluminanceLux;
  const visibilityMarginMag = 2.5 * Math.log10(visibilityRatio);

  return {
    visible: visibilityRatio >= 1,
    visibilityRatio,
    visibilityMarginMag,
    limitingVMagnitude: illuminanceLuxToVMagnitude(thresholdIlluminanceLux),
    apparentVMagAtEye,
    starIlluminanceLux,
    thresholdIlluminanceLux,
    backgroundLuminanceCdM2,
    fieldFactor,
    branch,
  };
}

/**
 * Infer F from a real first-seeing event. This is the calibration primitive for
 * expert known-position observations; it avoids guessing an additive mag bonus.
 */
export function inferFieldFactorFromThresholdObservation({
  backgroundLuminanceCdM2,
  apparentVMagAtEye,
  branch = 'full',
}) {
  requireFinite('apparentVMagAtEye', apparentVMagAtEye);
  const starIlluminanceLux = vMagnitudeToIlluminanceLux(apparentVMagAtEye);
  const base = branch === 'scotopic'
    ? crumeyScotopicBasePointSourceThresholdLux(backgroundLuminanceCdM2)
    : branch === 'full'
      ? crumeyBasePointSourceThresholdLux(backgroundLuminanceCdM2)
      : (() => { throw new RangeError(`unknown branch: ${branch}`); })();
  return starIlluminanceLux / base;
}
