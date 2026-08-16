import { requireAtmosphereForLevelB } from './atmosphere-state.mjs';

export const SKY_STATUS = Object.freeze({
  SUPPORTED: 'SUPPORTED', OOD: 'OOD', ATMOSPHERE_INCOMPLETE: 'ATMOSPHERE_INCOMPLETE',
  CLOUD_UNSUPPORTED: 'CLOUD_UNSUPPORTED', PROVIDER_UNAVAILABLE: 'PROVIDER_UNAVAILABLE', INVALID_INPUT: 'INVALID_INPUT',
});
export const SKY_CHANNELS = Object.freeze(['photopic', 'scotopic', 'johnsonV', 'spectral']);
export function unavailableChannel(reason='UNAVAILABLE') { return Object.freeze({ available: false, value: null, unit: null, reason }); }
export function availableChannel(value, unit) {
  if (!Number.isFinite(value)) throw new RangeError('channel value must be finite');
  return Object.freeze({ available: true, value, unit, reason: null });
}
function normalizeChannels(channels={}) {
  return Object.freeze(Object.fromEntries(SKY_CHANNELS.map(k => [k, channels[k] ?? unavailableChannel()] )));
}
export function normalizeSkyResult(result, { atmosphere, providerId='unknown-provider' } = {}) {
  if (!result || typeof result !== 'object') throw new TypeError('sky provider result must be an object');
  if (!Object.values(SKY_STATUS).includes(result.status)) throw new RangeError(`invalid sky status: ${result.status}`);
  return Object.freeze({
    status: result.status,
    channels: normalizeChannels(result.channels),
    uncertainty: result.uncertainty ?? null,
    support: Object.freeze({ nominalDesignBox: false, validatedSupport: false, reasons: [], ...(result.support ?? {}) }),
    provenance: Object.freeze({ provider: providerId, version: null, modelHash: null, atmosphereIdentity: atmosphere?.identity ?? null, fallbackPath: null, ...(result.provenance ?? {}) }),
  });
}
export function evaluateSky({ provider, geometry, atmosphere }) {
  if (!provider || typeof provider.evaluateSky !== 'function') return normalizeSkyResult({ status: SKY_STATUS.PROVIDER_UNAVAILABLE }, { atmosphere });
  const a = requireAtmosphereForLevelB(atmosphere);
  if (!a.supported) {
    const invalid = a.reasons.includes('AOD550_NEGATIVE') || a.reasons.includes('AOD550_INVALID');
    return normalizeSkyResult({ status: invalid ? SKY_STATUS.INVALID_INPUT : SKY_STATUS.ATMOSPHERE_INCOMPLETE, support: { reasons: a.reasons } }, { atmosphere, providerId: provider.id });
  }
  try { return normalizeSkyResult(provider.evaluateSky({ geometry, atmosphere }), { atmosphere, providerId: provider.id }); }
  catch (error) {
    return normalizeSkyResult({ status: SKY_STATUS.PROVIDER_UNAVAILABLE, support: { reasons: [error?.code ?? 'PROVIDER_ERROR'] }, provenance: { errorMessage: String(error?.message ?? error) } }, { atmosphere, providerId: provider.id });
  }
}
