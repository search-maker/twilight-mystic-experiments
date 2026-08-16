import { evaluatePointSourceVisibility } from './human-threshold.mjs';
import { evaluateSky, SKY_STATUS } from './sky-provider.mjs';
import { solveVisibilityMarginTimeline } from './visibility-event-timeline.mjs';

export const VISIBILITY_RUNTIME_STATUS = Object.freeze({
  SUPPORTED: 'SUPPORTED',
  SKY_UNSUPPORTED: 'SKY_UNSUPPORTED',
  STELLAR_UNSUPPORTED: 'STELLAR_UNSUPPORTED',
  ATMOSPHERE_MISMATCH: 'ATMOSPHERE_MISMATCH',
  CHANNEL_UNAVAILABLE: 'CHANNEL_UNAVAILABLE',
  INVALID_OBSERVER_CRITERION: 'INVALID_OBSERVER_CRITERION',
  INVALID_INPUT: 'INVALID_INPUT',
  UNSUPPORTED_INTERVAL: 'UNSUPPORTED_INTERVAL',
});

function invalidResult(status, reason, extra = {}) {
  return Object.freeze({ status, reason, visibility: null, ...extra });
}

function validateObserverCriterion(observerCriterion) {
  if (!observerCriterion || typeof observerCriterion !== 'object') {
    return { ok: false, reason: 'OBSERVER_CRITERION_REQUIRED' };
  }
  if (!Number.isFinite(observerCriterion.fieldFactor) || observerCriterion.fieldFactor <= 0) {
    return { ok: false, reason: 'FIELD_FACTOR_REQUIRED' };
  }
  if (typeof observerCriterion.id !== 'string' || !observerCriterion.id) {
    return { ok: false, reason: 'OBSERVER_CRITERION_ID_REQUIRED' };
  }
  const factorBasis = observerCriterion.factorBasis;
  if (!factorBasis || typeof factorBasis !== 'object') {
    return { ok: false, reason: 'FACTOR_BASIS_REQUIRED' };
  }
  if (factorBasis.mediumFactor !== 1) {
    return { ok: false, reason: 'PHYSICAL_MEDIUM_ALREADY_MODELED_REQUIRES_MEDIUM_FACTOR_1' };
  }
  return { ok: true };
}

function normalizedUncertainty({ sky, stellar, observerCriterion }) {
  return Object.freeze({
    probabilityModelApplied: false,
    sky: sky.uncertainty ?? null,
    atmosphere: stellar?.uncertainty?.atmosphere ?? null,
    stellar: stellar?.uncertainty ?? null,
    human: observerCriterion.uncertainty ?? null,
  });
}

/**
 * Evaluate one geometry using a provider-neutral sky result, a caller-supplied
 * physical stellar-signal evaluator, and the existing Crumey reference helper.
 *
 * stellarSignalEvaluator must return an apparent Johnson-V magnitude at the eye
 * AFTER physical atmospheric transmission plus the atmosphere identity used.
 * The human helper then receives extinctionMagV=0 so physical attenuation is not
 * applied twice. No colour/"expert" magnitude bonus is accepted here.
 */
export function evaluateVisibilitySample({
  geometry,
  atmosphere,
  skyProvider,
  stellarSignalEvaluator,
  target,
  observerCriterion,
  humanBranch = 'full',
}) {
  const criterion = validateObserverCriterion(observerCriterion);
  if (!criterion.ok) {
    return invalidResult(VISIBILITY_RUNTIME_STATUS.INVALID_OBSERVER_CRITERION, criterion.reason);
  }
  if (!atmosphere?.identity || typeof stellarSignalEvaluator !== 'function') {
    return invalidResult(VISIBILITY_RUNTIME_STATUS.INVALID_INPUT, 'ATMOSPHERE_AND_STELLAR_EVALUATOR_REQUIRED');
  }

  const sky = evaluateSky({ provider: skyProvider, geometry, atmosphere });
  if (sky.status !== SKY_STATUS.SUPPORTED) {
    return invalidResult(VISIBILITY_RUNTIME_STATUS.SKY_UNSUPPORTED, sky.status, {
      sky,
      atmosphereIdentity: atmosphere.identity,
      support: sky.support,
      provenance: { atmosphere: atmosphere.provenance, sky: sky.provenance },
    });
  }
  const photopic = sky.channels.photopic;
  if (!photopic?.available || photopic.unit !== 'cd/m2') {
    return invalidResult(VISIBILITY_RUNTIME_STATUS.CHANNEL_UNAVAILABLE, 'PHOTOPIC_CD_M2_REQUIRED_FOR_CRUMEY_REFERENCE', {
      sky,
      atmosphereIdentity: atmosphere.identity,
    });
  }

  let stellar;
  try {
    stellar = stellarSignalEvaluator({ geometry, atmosphere, target });
  } catch (error) {
    return invalidResult(VISIBILITY_RUNTIME_STATUS.STELLAR_UNSUPPORTED, error?.code ?? 'STELLAR_EVALUATOR_ERROR', {
      sky,
      atmosphereIdentity: atmosphere.identity,
      stellarError: String(error?.message ?? error),
    });
  }
  if (!stellar || stellar.status === 'UNSUPPORTED' || !Number.isFinite(stellar.apparentVMagAtEye)) {
    return invalidResult(VISIBILITY_RUNTIME_STATUS.STELLAR_UNSUPPORTED, stellar?.reason ?? 'STELLAR_SIGNAL_UNAVAILABLE', {
      sky,
      stellar: stellar ?? null,
      atmosphereIdentity: atmosphere.identity,
    });
  }
  if (stellar.atmosphereIdentity !== atmosphere.identity || sky.provenance.atmosphereIdentity !== atmosphere.identity) {
    return invalidResult(VISIBILITY_RUNTIME_STATUS.ATMOSPHERE_MISMATCH, 'SKY_STAR_ATMOSPHERE_IDENTITY_MISMATCH', {
      sky,
      stellar,
      atmosphereIdentity: atmosphere.identity,
    });
  }

  const visibility = evaluatePointSourceVisibility({
    backgroundLuminanceCdM2: photopic.value,
    starTopOfAtmosphereVMag: stellar.apparentVMagAtEye,
    extinctionMagV: 0,
    colorSignalOffsetMag: 0,
    fieldFactor: observerCriterion.fieldFactor,
    branch: humanBranch,
  });

  return Object.freeze({
    status: VISIBILITY_RUNTIME_STATUS.SUPPORTED,
    reason: null,
    visibility,
    visibilityMarginMag: visibility.visibilityMarginMag,
    sky,
    stellar,
    observerCriterion: Object.freeze({ ...observerCriterion }),
    atmosphereIdentity: atmosphere.identity,
    uncertainty: normalizedUncertainty({ sky, stellar, observerCriterion }),
    support: Object.freeze({
      sky: sky.support,
      humanModel: 'crumey-blackwell-reference',
      humanModelProductionCalibrated: false,
    }),
    provenance: Object.freeze({
      atmosphere: atmosphere.provenance,
      sky: sky.provenance,
      stellar: stellar.provenance ?? null,
      humanCriterionId: observerCriterion.id,
    }),
  });
}

/**
 * Canonical chronological event orchestration. The callback is pure: every
 * queried depression is independently evaluated from the same AtmosphereState.
 * If any sampled/refined point is unsupported, the event fails closed rather
 * than substituting a finite margin or extrapolating through the gap.
 */
export function solveVisibilityRuntimeTimeline({
  minSunDepressionDeg,
  maxSunDepressionDeg,
  geometryAtSunDepression,
  scanStepDeg,
  ...sampleInput
}) {
  if (typeof geometryAtSunDepression !== 'function') {
    return invalidResult(VISIBILITY_RUNTIME_STATUS.INVALID_INPUT, 'GEOMETRY_CALLBACK_REQUIRED');
  }
  if (!Number.isFinite(scanStepDeg) || scanStepDeg <= 0) {
    return invalidResult(VISIBILITY_RUNTIME_STATUS.INVALID_INPUT, 'EXPLICIT_SCAN_STEP_REQUIRED');
  }
  const unsupported = [];
  try {
    const timeline = solveVisibilityMarginTimeline({
      minSunDepressionDeg,
      maxSunDepressionDeg,
      scanStepDeg,
      visibilityMarginMagAtDepression: sunDepressionDeg => {
        const sample = evaluateVisibilitySample({
          ...sampleInput,
          geometry: geometryAtSunDepression(sunDepressionDeg),
        });
        if (sample.status !== VISIBILITY_RUNTIME_STATUS.SUPPORTED) {
          unsupported.push({ sunDepressionDeg, status: sample.status, reason: sample.reason });
          const error = new Error(`unsupported visibility sample at d=${sunDepressionDeg}: ${sample.status}/${sample.reason}`);
          error.code = 'VISIBILITY_RUNTIME_UNSUPPORTED_SAMPLE';
          throw error;
        }
        return sample.visibilityMarginMag;
      },
    });
    return Object.freeze({
      status: VISIBILITY_RUNTIME_STATUS.SUPPORTED,
      reason: null,
      timeline,
      unsupportedSamples: Object.freeze([]),
      uncertainty: Object.freeze({ probabilityModelApplied: false }),
      productionDefaultChanged: false,
    });
  } catch (error) {
    if (error?.code === 'VISIBILITY_RUNTIME_UNSUPPORTED_SAMPLE') {
      return invalidResult(VISIBILITY_RUNTIME_STATUS.UNSUPPORTED_INTERVAL, 'EVENT_DOMAIN_CONTAINS_UNSUPPORTED_SAMPLE', {
        unsupportedSamples: Object.freeze([...unsupported]),
        productionDefaultChanged: false,
      });
    }
    throw error;
  }
}
