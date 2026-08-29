export const SF_A_TIMING_LATITUDE_DEG = Object.freeze([0, 30, 45, 60]);
export const SF_A_TIMING_DECLINATION_DEG = Object.freeze([-23.44, 0, 23.44]);
export const SF_A_TIMING_SUN_DEPRESSION_DEG = Object.freeze(Array.from({ length: 35 }, (_, i) => 2 + 0.25 * i));

const DEG = Math.PI / 180;
const RAD = 180 / Math.PI;
const SIDEREAL_RATE_DEG_PER_HOUR = 15;
const SECONDS_PER_HOUR = 3600;

function finite(v) { return typeof v === 'number' && Number.isFinite(v); }

export function eveningHourAngleDeg({ latitudeDeg, declinationDeg, sunDepressionDeg }) {
  if (![latitudeDeg, declinationDeg, sunDepressionDeg].every(finite)) throw new TypeError('finite timing geometry required');
  const phi = latitudeDeg * DEG;
  const dec = declinationDeg * DEG;
  const h = -sunDepressionDeg * DEG;
  const denom = Math.cos(phi) * Math.cos(dec);
  if (Math.abs(denom) < 1e-15) return null;
  const cosH = (Math.sin(h) - Math.sin(phi) * Math.sin(dec)) / denom;
  if (cosH < -1 - 1e-12 || cosH > 1 + 1e-12) return null;
  return Math.acos(Math.max(-1, Math.min(1, cosH))) * RAD;
}

export function buildTimingArm({ latitudeDeg, declinationDeg }) {
  const hourAngleDeg = [];
  for (const sunDepressionDeg of SF_A_TIMING_SUN_DEPRESSION_DEG) {
    const H = eveningHourAngleDeg({ latitudeDeg, declinationDeg, sunDepressionDeg });
    if (H == null) {
      return Object.freeze({
        status: 'REFUSED_SUN_DOES_NOT_TRAVERSE_COMPLETE_SF_A_DEPRESSION_RANGE',
        latitudeDeg,
        declinationDeg,
      });
    }
    hourAngleDeg.push(H);
  }
  const secondsPerHourAngleDeg = SECONDS_PER_HOUR / SIDEREAL_RATE_DEG_PER_HOUR;
  const t0 = hourAngleDeg[0];
  const timeSeconds = hourAngleDeg.map(H => (H - t0) * secondsPerHourAngleDeg);
  for (let i = 1; i < timeSeconds.length; i += 1) {
    if (!(timeSeconds[i] > timeSeconds[i - 1])) throw new Error('non-increasing evening SF-A timing path');
  }
  return Object.freeze({
    status: 'SUPPORTED',
    latitudeDeg,
    declinationDeg,
    sunDepressionDeg: SF_A_TIMING_SUN_DEPRESSION_DEG,
    hourAngleDeg: Object.freeze(hourAngleDeg),
    timeSeconds: Object.freeze(timeSeconds),
    durationSeconds: timeSeconds.at(-1),
    minStepSeconds: Math.min(...timeSeconds.slice(1).map((t, i) => t - timeSeconds[i])),
    maxStepSeconds: Math.max(...timeSeconds.slice(1).map((t, i) => t - timeSeconds[i])),
  });
}

export function buildFrozenTimingArmLedger() {
  const rows = [];
  for (const latitudeDeg of SF_A_TIMING_LATITUDE_DEG) {
    for (const declinationDeg of SF_A_TIMING_DECLINATION_DEG) {
      rows.push(buildTimingArm({ latitudeDeg, declinationDeg }));
    }
  }
  return Object.freeze(rows);
}

export function controlledEquilibriumPreludeStateLog10(backgroundCdM2) {
  if (!finite(backgroundCdM2) || !(backgroundCdM2 > 0)) throw new RangeError('positive finite split-field background required');
  return Math.log10(backgroundCdM2);
}
