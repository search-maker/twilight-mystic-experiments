export const ATMOSPHERE_QUALITY = Object.freeze({
  MEASURED: 'measured',
  MODELED_LIVE: 'modeled-live',
  CLIMATOLOGICAL: 'climatological',
  PRESET_FALLBACK: 'preset-fallback',
});

function finiteOrNull(v) { if (v === null || v === undefined || v === '') return null; const n = Number(v); return Number.isFinite(n) ? n : null; }
function isoOrNull(v) { if (!v) return null; const d = new Date(v); return Number.isFinite(d.getTime()) ? d.toISOString() : null; }
function stableObject(value) {
  if (Array.isArray(value)) return value.map(stableObject);
  if (!value || typeof value !== 'object') return value;
  return Object.fromEntries(Object.keys(value).sort().map(k => [k, stableObject(value[k])]));
}
export function atmosphereFingerprint(state) {
  const basis = stableObject({
    provider: state.provenance.provider,
    dataset: state.provenance.dataset,
    validTime: state.provenance.validTime,
    sourceElevation: state.provenance.sourceElevation,
    site: state.site,
    observerElevationM: state.observerElevationM,
    aod550: state.aod550,
    angstromExponent: state.angstromExponent,
    modelInputs: state.modelInputs,
  });
  return JSON.stringify(basis);
}

export function createAtmosphereState(input, { now = new Date() } = {}) {
  if (!input || typeof input !== 'object' || Array.isArray(input)) throw new TypeError('atmosphere input must be an object');
  const validTime = isoOrNull(input.validTime);
  const fetchTime = isoOrNull(input.fetchTime);
  const nowMs = new Date(now).getTime();
  const validMs = validTime ? new Date(validTime).getTime() : NaN;
  const dataAgeSeconds = Number.isFinite(validMs) ? Math.max(0, (nowMs - validMs) / 1000) : null;
  const staleAfterSeconds = finiteOrNull(input.staleAfterSeconds);
  const aod550 = finiteOrNull(input.aod550);
  const observerElevationM = finiteOrNull(input.observerElevationM);
  const sourceElevationM = finiteOrNull(input.sourceElevationM);
  const maxSourceElevationDeltaM = finiteOrNull(input.maxSourceElevationDeltaM);
  const sourceElevationDeltaM = sourceElevationM !== null && observerElevationM !== null
    ? observerElevationM - sourceElevationM
    : null;
  const sourceElevationDeltaAbsM = sourceElevationDeltaM === null ? null : Math.abs(sourceElevationDeltaM);
  const qualityClass = input.qualityClass ?? ATMOSPHERE_QUALITY.MODELED_LIVE;
  if (!Object.values(ATMOSPHERE_QUALITY).includes(qualityClass)) throw new RangeError(`unknown atmosphere qualityClass: ${qualityClass}`);
  if (aod550 !== null && aod550 < 0) throw new RangeError(`aod550 must be >= 0 when present; got ${aod550}`);
  if (maxSourceElevationDeltaM !== null && maxSourceElevationDeltaM <= 0) {
    throw new RangeError('maxSourceElevationDeltaM must be > 0 when configured');
  }
  if (input.verticalAodCorrectionApplied === true) {
    throw new RangeError('vertical AOD correction is not supported by AtmosphereState');
  }

  const flags = new Set(Array.isArray(input.qualityFlags) ? input.qualityFlags : []);
  if (aod550 === null) flags.add('AOD550_MISSING');
  if (observerElevationM === null) flags.add('OBSERVER_ELEVATION_MISSING');
  if (!validTime) flags.add('VALID_TIME_MISSING');
  if (staleAfterSeconds !== null && dataAgeSeconds !== null && dataAgeSeconds > staleAfterSeconds) flags.add('STALE');
  if (maxSourceElevationDeltaM !== null && sourceElevationM === null) flags.add('SOURCE_ELEVATION_MISSING');
  if (maxSourceElevationDeltaM !== null && sourceElevationDeltaAbsM !== null && sourceElevationDeltaAbsM > maxSourceElevationDeltaM) {
    flags.add('SOURCE_ELEVATION_DELTA_EXCEEDED');
  }
  if (input.fallbackReason) flags.add('FALLBACK');

  const state = {
    schemaVersion: 1,
    provenance: {
      provider: input.provider ?? null,
      dataset: input.dataset ?? null,
      providerVersion: input.providerVersion ?? null,
      validTime,
      fetchTime,
      dataAgeSeconds,
      sourceQualityClass: qualityClass,
      fallbackReason: input.fallbackReason ?? null,
      sourceElevation: Object.freeze({
        kind: input.sourceElevationKind ?? null,
        elevationM: sourceElevationM,
        observerMinusSourceM: sourceElevationDeltaM,
        absoluteDifferenceM: sourceElevationDeltaAbsM,
        maxAbsoluteDifferenceM: maxSourceElevationDeltaM,
        verticalAodCorrectionApplied: false,
      }),
    },
    site: {
      latitudeDeg: finiteOrNull(input.latitudeDeg),
      longitudeDeg: finiteOrNull(input.longitudeDeg),
    },
    observerElevationM,
    aod550,
    aod550Uncertainty: finiteOrNull(input.aod550Uncertainty),
    angstromExponent: finiteOrNull(input.angstromExponent),
    cloud: input.cloud ?? null,
    weather: input.weather ?? null,
    modelInputs: input.modelInputs && typeof input.modelInputs === 'object' ? stableObject(input.modelInputs) : {},
    qualityFlags: [...flags].sort(),
    stale: flags.has('STALE'),
    missingAod: flags.has('AOD550_MISSING'),
    fallback: flags.has('FALLBACK'),
  };
  state.identity = atmosphereFingerprint(state);
  return Object.freeze(state);
}

export function requireAtmosphereForLevelB(state) {
  if (!state || typeof state !== 'object') return { supported: false, reasons: ['ATMOSPHERE_MISSING'] };
  const reasons = [];
  if (state.aod550 === null || state.aod550 === undefined) reasons.push('AOD550_MISSING');
  else if (!Number.isFinite(state.aod550)) reasons.push('AOD550_INVALID');
  else if (state.aod550 < 0) reasons.push('AOD550_NEGATIVE');
  if (!Number.isFinite(state.observerElevationM)) reasons.push('OBSERVER_ELEVATION_MISSING');
  if (state.stale) reasons.push('ATMOSPHERE_STALE');
  if (state.qualityFlags?.includes('SOURCE_ELEVATION_MISSING')) reasons.push('SOURCE_ELEVATION_MISSING');
  if (state.qualityFlags?.includes('SOURCE_ELEVATION_DELTA_EXCEEDED')) reasons.push('SOURCE_ELEVATION_DELTA_EXCEEDED');
  return { supported: reasons.length === 0, reasons };
}
