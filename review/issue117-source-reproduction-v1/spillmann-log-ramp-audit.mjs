import assert from 'node:assert/strict';

export const LOG_DROP_DECADES = 7;
export const SOURCE_DURATIONS_SECONDS = Object.freeze([210, 420, 840, 1260]);
export const TAU_SENSITIVITY_SECONDS = Object.freeze([20, 30, 45, 60]);

// Exact production-v0 step for a log10-linear adaptation-field ramp.
export function advanceAdaptedLog10LinearRamp({
  adaptedStart,
  fieldStart,
  fieldEnd,
  dtSeconds,
  tauSeconds,
}) {
  const slope = (fieldEnd - fieldStart) / dtSeconds;
  const decay = Math.exp(-dtSeconds / tauSeconds);
  return fieldEnd
    - slope * tauSeconds
    + (adaptedStart - fieldStart + slope * tauSeconds) * decay;
}

// Closed-form lag delta=a-x for x(t)=x0-r*t, with delta(0)=initialLag.
export function closedFormLagLog10({
  elapsedSeconds,
  declineRateLog10PerSecond,
  tauSeconds,
  initialLagLog10 = 0,
}) {
  const decay = Math.exp(-elapsedSeconds / tauSeconds);
  return declineRateLog10PerSecond * tauSeconds * (1 - decay)
    + initialLagLog10 * decay;
}

export function runSpillmannRampAudit() {
  const rows = [];
  for (const durationSeconds of SOURCE_DURATIONS_SECONDS) {
    const rate = LOG_DROP_DECADES / durationSeconds;
    for (const tauSeconds of TAU_SENSITIVITY_SECONDS) {
      const fieldStart = 0;
      const fieldEnd = -LOG_DROP_DECADES;
      const adaptedEnd = advanceAdaptedLog10LinearRamp({
        adaptedStart: fieldStart,
        fieldStart,
        fieldEnd,
        dtSeconds: durationSeconds,
        tauSeconds,
      });
      const lag = adaptedEnd - fieldEnd;
      const closed = closedFormLagLog10({
        elapsedSeconds: durationSeconds,
        declineRateLog10PerSecond: rate,
        tauSeconds,
      });
      assert.ok(Math.abs(lag - closed) < 1e-12, 'closed form must match production-v0 ramp solution');
      assert.ok(lag >= 0, 'waning ramp must not produce negative maladaptation lag');
      rows.push(Object.freeze({
        durationMinutes: durationSeconds / 60,
        tauSeconds,
        declineRateLog10PerSecond: rate,
        endLagLog10: lag,
        endLagLuminanceRatio: 10 ** lag,
      }));
    }
  }

  // Source-level qualitative rate ordering: faster 7-decade descents must leave more lag.
  for (const tauSeconds of TAU_SENSITIVITY_SECONDS) {
    const series = rows.filter((row) => row.tauSeconds === tauSeconds);
    for (let i = 1; i < series.length; i += 1) {
      assert.ok(series[i - 1].endLagLog10 > series[i].endLagLog10,
        `lag ordering must follow faster>slower decline at tau=${tauSeconds}`);
    }
  }

  // Sensitivity-only tau ordering, not a fit target.
  for (const durationSeconds of SOURCE_DURATIONS_SECONDS) {
    const durationMinutes = durationSeconds / 60;
    const series = rows.filter((row) => row.durationMinutes === durationMinutes);
    for (let i = 1; i < series.length; i += 1) {
      assert.ok(series[i - 1].endLagLog10 < series[i].endLagLog10,
        `larger tau must leave more lag at duration=${durationMinutes} min`);
    }
  }

  // Stationary equilibrium identity.
  const stationary = advanceAdaptedLog10LinearRamp({
    adaptedStart: -2,
    fieldStart: -2,
    fieldEnd: -2,
    dtSeconds: 300,
    tauSeconds: 30,
  });
  assert.ok(Math.abs(stationary - (-2)) < 1e-15, 'stationary equilibrium must be an identity');

  // Pre-exposure/history distinguishability: an initial positive lag remains an additive decaying term.
  const historyChecks = TAU_SENSITIVITY_SECONDS.map((tauSeconds) => {
    const durationSeconds = 420;
    const rate = LOG_DROP_DECADES / durationSeconds;
    const noPreexposure = closedFormLagLog10({
      elapsedSeconds: durationSeconds,
      declineRateLog10PerSecond: rate,
      tauSeconds,
      initialLagLog10: 0,
    });
    const withPreexposure = closedFormLagLog10({
      elapsedSeconds: durationSeconds,
      declineRateLog10PerSecond: rate,
      tauSeconds,
      initialLagLog10: 1,
    });
    const expectedDifference = Math.exp(-durationSeconds / tauSeconds);
    assert.ok(withPreexposure > noPreexposure, 'preexposure history must remain distinguishable');
    assert.ok(Math.abs((withPreexposure - noPreexposure) - expectedDifference) < 1e-12,
      'history difference must decay exactly as exp(-t/tau)');
    return Object.freeze({ tauSeconds, noPreexposure, withPreexposure, survivingInitialLagLog10: expectedDifference });
  });

  return Object.freeze({
    modelEquation: 'da/dt=(x-a)/tau with x=log10(B_a)',
    sourceRamp: '7 log10 units over 3.5, 7, 14, or 21 minutes',
    rows: Object.freeze(rows),
    historyChecks: Object.freeze(historyChecks),
    interpretation: Object.freeze({
      temporalStateRateOrderPass: true,
      exactMagnitudeFitPerformed: false,
      tauFitPerformed: false,
      mappingCandidateDiscriminated: false,
      reasonMappingNotDiscriminated: 'Spillmann uses a spatially uniform adapting field; under B_a=B_d, surviving path-safe candidates collapse in the preregistered same-field geometry.',
    }),
  });
}

if (import.meta.url === `file://${process.argv[1]}`) {
  process.stdout.write(`${JSON.stringify(runSpillmannRampAudit(), null, 2)}\n`);
}
