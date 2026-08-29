import assert from 'node:assert/strict';

export const SF_A_BINDINGS = Object.freeze({
  protocolHead: '87eef45a95de96466f3f8e0d10ba44d46cfbd492',
  sourceReproductionHead: '83979360a21e3e9aa3a85a2dda0f4808ab821018',
  applicationSha: 'e0da52eb0a2d5bac333da6572f51df52ea7e676e',
  validatedProviderBlob: 'da8c5995559020865118220d939e58d89e6b98e4',
  validatedRuntimeBlob: '5790ccb2c289de082a2851d96e4c3c660a1c4985',
});

export const PROVIDER_DESIGN_BOX = Object.freeze({
  sunDepressionDeg: Object.freeze([2, 10.5]),
  targetAltitudeDeg: Object.freeze([5, 80]),
  relativeAzimuthDeg: Object.freeze([0, 180]),
  observerElevationM: Object.freeze([0, 2500]),
  aod550: Object.freeze([0.05, 0.40]),
});

export const SUN_DEPRESSION_DEG = Object.freeze(Array.from({ length: 35 }, (_, i) => 2 + 0.25 * i));
export const TARGET_ALTITUDE_DEG = Object.freeze([30, 45, 60]);
export const TARGET_RELATIVE_AZIMUTH_DEG = Object.freeze([0, 45, 90, 135, 180]);
export const AOD550 = Object.freeze([0.05, 0.15, 0.30]);
export const TAU_SECONDS = Object.freeze([20, 30, 45, 60]);
export const FIXATION_ECCENTRICITY_DEG = Object.freeze([8, 11, 14]);
export const FIXATION_ORIENTATIONS = Object.freeze(['toward_sun', 'away_from_sun', 'cross_plus90', 'cross_minus90']);
export const MAPPING_ELIGIBLE_CHANNEL = 'photopic';
export const DIAGNOSTIC_ONLY_CHANNELS = Object.freeze(['scotopic']);
export const MESOPIC_STATUS = 'UNAVAILABLE_NO_BOUND_NORMATIVE_RECEPTOR_TO_THRESHOLD_MAPPING';

export const SPATIAL_ARMS = Object.freeze({
  S0_POINT: Object.freeze({ id: 'S0_POINT', radiusDeg: 0, kernel: 'point' }),
  S1_WHOLE_CAP: Object.freeze({ id: 'S1_WHOLE_CAP', radiusDeg: 20, kernel: 'uniform' }),
  S2_ALF: Object.freeze({ id: 'S2_ALF', radiusDeg: 20, kernel: 'alf' }),
  S3_UCHIDA_LOCAL: Object.freeze({ id: 'S3_UCHIDA_LOCAL', radiusDeg: 12.4, kernel: 'uniform' }),
});

const DEG = Math.PI / 180;
const RAD = 180 / Math.PI;

function finite(v) { return typeof v === 'number' && Number.isFinite(v); }
export function degToRad(v) { return v * DEG; }
export function radToDeg(v) { return v * RAD; }
export function wrap360Deg(v) {
  const w = ((v % 360) + 360) % 360;
  return Object.is(w, -0) ? 0 : w;
}
export function foldRelativeAzimuthDeg(v) {
  const w = wrap360Deg(v);
  return w <= 180 ? w : 360 - w;
}

export function angularSeparationDeg(a, b) {
  const lat1 = degToRad(a.altitudeDeg);
  const lat2 = degToRad(b.altitudeDeg);
  const dlon = degToRad(wrap360Deg(b.azimuthDeg - a.azimuthDeg));
  const c = Math.sin(lat1) * Math.sin(lat2)
    + Math.cos(lat1) * Math.cos(lat2) * Math.cos(dlon);
  return radToDeg(Math.acos(Math.max(-1, Math.min(1, c))));
}

export function initialBearingDeg(from, to) {
  const lat1 = degToRad(from.altitudeDeg);
  const lat2 = degToRad(to.altitudeDeg);
  let dlon = degToRad(to.azimuthDeg - from.azimuthDeg);
  dlon = Math.atan2(Math.sin(dlon), Math.cos(dlon));
  const y = Math.sin(dlon) * Math.cos(lat2);
  const x = Math.cos(lat1) * Math.sin(lat2)
    - Math.sin(lat1) * Math.cos(lat2) * Math.cos(dlon);
  if (Math.abs(x) < 1e-15 && Math.abs(y) < 1e-15) return 0;
  return wrap360Deg(radToDeg(Math.atan2(y, x)));
}

export function offsetDirection({ altitudeDeg, azimuthDeg }, distanceDeg, bearingDeg) {
  if (!finite(altitudeDeg) || !finite(azimuthDeg) || !finite(distanceDeg) || !finite(bearingDeg)) {
    throw new TypeError('finite spherical direction required');
  }
  if (distanceDeg < 0 || distanceDeg > 180) throw new RangeError('distanceDeg outside [0,180]');
  const lat1 = degToRad(altitudeDeg);
  const lon1 = degToRad(azimuthDeg);
  const d = degToRad(distanceDeg);
  const b = degToRad(bearingDeg);
  const sinLat2 = Math.sin(lat1) * Math.cos(d) + Math.cos(lat1) * Math.sin(d) * Math.cos(b);
  const lat2 = Math.asin(Math.max(-1, Math.min(1, sinLat2)));
  const y = Math.sin(b) * Math.sin(d) * Math.cos(lat1);
  const x = Math.cos(d) - Math.sin(lat1) * Math.sin(lat2);
  const lon2 = lon1 + Math.atan2(y, x);
  return Object.freeze({ altitudeDeg: radToDeg(lat2), azimuthDeg: wrap360Deg(radToDeg(lon2)) });
}

export function sunDirection(sunDepressionDeg) {
  return Object.freeze({ altitudeDeg: -sunDepressionDeg, azimuthDeg: 0 });
}

export function targetDirection(targetAltitudeDeg, targetRelativeAzimuthDeg) {
  return Object.freeze({ altitudeDeg: targetAltitudeDeg, azimuthDeg: targetRelativeAzimuthDeg });
}

export function fixationCenter({ sunDepressionDeg, targetAltitudeDeg, targetRelativeAzimuthDeg, eccentricityDeg = 0, orientation = 'target' }) {
  const target = targetDirection(targetAltitudeDeg, targetRelativeAzimuthDeg);
  if (orientation === 'target' || eccentricityDeg === 0) return target;
  if (!FIXATION_ORIENTATIONS.includes(orientation)) throw new RangeError(`unknown orientation: ${orientation}`);
  const bearingToSun = initialBearingDeg(target, sunDirection(sunDepressionDeg));
  const bearing = orientation === 'toward_sun' ? bearingToSun
    : orientation === 'away_from_sun' ? bearingToSun + 180
      : orientation === 'cross_plus90' ? bearingToSun + 90
        : bearingToSun - 90;
  const center = offsetDirection(target, eccentricityDeg, bearing);
  const actual = angularSeparationDeg(target, center);
  if (Math.abs(actual - eccentricityDeg) > 1e-9) throw new Error('fixation offset distance drift');
  return center;
}

export function providerRelativeAzimuthDeg(direction) {
  return foldRelativeAzimuthDeg(direction.azimuthDeg);
}

export function alfWeight(thetaDeg) {
  const a = 0.9935 * Math.exp(-(thetaDeg * thetaDeg) / (2 * 0.67 * 0.67));
  const b = 0.0065 * Math.exp(-(thetaDeg * thetaDeg) / (2 * 3.9 * 3.9));
  return a + b;
}

export function buildSphericalCapQuadrature({ capDeg, radialStepDeg = 1 }) {
  if (!(capDeg > 0 && capDeg <= 90)) throw new RangeError('capDeg must be in (0,90]');
  if (!(radialStepDeg > 0 && radialStepDeg <= capDeg)) throw new RangeError('invalid radialStepDeg');
  const rows = [];
  const stepRad = degToRad(radialStepDeg);
  for (let lo = 0; lo < capDeg - 1e-12; lo += radialStepDeg) {
    const hi = Math.min(capDeg, lo + radialStepDeg);
    const mid = (lo + hi) / 2;
    const midRad = degToRad(mid);
    const nPhi = Math.max(1, Math.ceil((2 * Math.PI * Math.sin(midRad)) / stepRad));
    const ringSolidAngle = 2 * Math.PI * (Math.cos(degToRad(lo)) - Math.cos(degToRad(hi)));
    const cellSolidAngle = ringSolidAngle / nPhi;
    for (let j = 0; j < nPhi; j += 1) {
      rows.push(Object.freeze({
        thetaDeg: mid,
        bearingDeg: (j + 0.5) * 360 / nPhi,
        solidAngleSr: cellSolidAngle,
      }));
    }
  }
  const expected = 2 * Math.PI * (1 - Math.cos(degToRad(capDeg)));
  const actual = rows.reduce((s, r) => s + r.solidAngleSr, 0);
  if (Math.abs(actual - expected) > 1e-12) throw new Error('spherical cap solid-angle accounting drift');
  return Object.freeze(rows);
}

export function spatialKernelWeight(armId, thetaDeg) {
  const arm = SPATIAL_ARMS[armId];
  if (!arm) throw new RangeError(`unknown spatial arm: ${armId}`);
  if (arm.kernel === 'uniform') return 1;
  if (arm.kernel === 'alf') return alfWeight(thetaDeg);
  if (arm.kernel === 'point') return thetaDeg === 0 ? 1 : 0;
  throw new Error('kernel drift');
}

export function nominalFootprintWithinProviderAltitude({ centerAltitudeDeg, radiusDeg }) {
  const [lo, hi] = PROVIDER_DESIGN_BOX.targetAltitudeDeg;
  return centerAltitudeDeg - radiusDeg >= lo - 1e-12 && centerAltitudeDeg + radiusDeg <= hi + 1e-12;
}

export function integrateSpatialArm({ armId, center, sampleDirection, radialStepDeg = 1, channel = MAPPING_ELIGIBLE_CHANNEL }) {
  const arm = SPATIAL_ARMS[armId];
  if (!arm) throw new RangeError(`unknown spatial arm: ${armId}`);
  if (channel !== 'photopic' && channel !== 'scotopic') throw new RangeError('unsupported channel');
  const mappingEligible = channel === MAPPING_ELIGIBLE_CHANNEL;
  if (arm.kernel === 'point') {
    const sample = sampleDirection(center, channel);
    if (!sample || sample.supported !== true || !finite(sample.value) || !(sample.value > 0)) {
      return Object.freeze({ status: 'REFUSED_UNSUPPORTED_OR_NONPOSITIVE_SAMPLE', armId, channel, mappingEligible });
    }
    return Object.freeze({ status: 'SUPPORTED', armId, channel, mappingEligible, value: sample.value, sampleCount: 1, normalizationMass: 1 });
  }
  const q = buildSphericalCapQuadrature({ capDeg: arm.radiusDeg, radialStepDeg });
  const sampled = [];
  for (const cell of q) {
    const direction = offsetDirection(center, cell.thetaDeg, cell.bearingDeg);
    const sample = sampleDirection(direction, channel);
    if (!sample || sample.supported !== true || !finite(sample.value) || !(sample.value > 0)) {
      return Object.freeze({
        status: 'REFUSED_UNSUPPORTED_OR_NONPOSITIVE_SAMPLE',
        armId,
        channel,
        mappingEligible,
        sampleCountBeforeRefusal: sampled.length,
        refusedDirection: direction,
      });
    }
    sampled.push({ cell, sample });
  }
  let numerator = 0;
  let mass = 0;
  for (const { cell, sample } of sampled) {
    const w = spatialKernelWeight(armId, cell.thetaDeg) * cell.solidAngleSr;
    numerator += w * sample.value;
    mass += w;
  }
  if (!(mass > 0)) throw new Error('non-positive normalization mass');
  return Object.freeze({
    status: 'SUPPORTED',
    armId,
    channel,
    mappingEligible,
    value: numerator / mass,
    sampleCount: sampled.length,
    normalizationMass: mass,
  });
}

export function frozenGazeArmsForSpatialArm(armId) {
  if (armId === 'S0_POINT') return Object.freeze([{ id: 'G_TARGET', eccentricityDeg: 0, orientation: 'target' }]);
  const out = [{ id: 'G_TARGET', eccentricityDeg: 0, orientation: 'target' }];
  for (const e of FIXATION_ECCENTRICITY_DEG) {
    for (const orientation of FIXATION_ORIENTATIONS) {
      out.push({ id: `G_FIX_${e}_${orientation}`, eccentricityDeg: e, orientation });
    }
  }
  return Object.freeze(out.map(Object.freeze));
}

export function auditFrozenInputGeometry() {
  const rows = [];
  for (const aod550 of AOD550) {
    for (const targetAltitudeDeg of TARGET_ALTITUDE_DEG) {
      for (const targetRelativeAzimuthDeg of TARGET_RELATIVE_AZIMUTH_DEG) {
        for (const sunDepressionDeg of SUN_DEPRESSION_DEG) {
          const target = targetDirection(targetAltitudeDeg, targetRelativeAzimuthDeg);
          assert.ok(targetAltitudeDeg >= 5 && targetAltitudeDeg <= 80);
          assert.ok(targetRelativeAzimuthDeg >= 0 && targetRelativeAzimuthDeg <= 180);
          for (const arm of Object.values(SPATIAL_ARMS)) {
            for (const gaze of frozenGazeArmsForSpatialArm(arm.id)) {
              const center = fixationCenter({ sunDepressionDeg, targetAltitudeDeg, targetRelativeAzimuthDeg, eccentricityDeg: gaze.eccentricityDeg, orientation: gaze.orientation });
              const nominalAltitudeComplete = nominalFootprintWithinProviderAltitude({ centerAltitudeDeg: center.altitudeDeg, radiusDeg: arm.radiusDeg });
              rows.push(Object.freeze({
                aod550,
                sunDepressionDeg,
                targetAltitudeDeg,
                targetRelativeAzimuthDeg,
                armId: arm.id,
                gazeId: gaze.id,
                centerAltitudeDeg: center.altitudeDeg,
                centerRelativeAzimuthDeg: providerRelativeAzimuthDeg(center),
                radiusDeg: arm.radiusDeg,
                nominalAltitudeComplete,
              }));
            }
          }
        }
      }
    }
  }
  const complete = rows.filter(r => r.nominalAltitudeComplete).length;
  return Object.freeze({
    schema: 'SF_A_INPUT_SPATIAL_AUDIT_V1',
    baseHistoryCount: AOD550.length * TARGET_ALTITUDE_DEG.length * TARGET_RELATIVE_AZIMUTH_DEG.length,
    timeRowsPerHistory: SUN_DEPRESSION_DEG.length,
    totalSpatialGazeRows: rows.length,
    nominalAltitudeCompleteRows: complete,
    nominalAltitudeIncompleteRows: rows.length - complete,
    note: 'Nominal altitude containment only. Nearest-training-distance support is not inferred without the exact bound private runtime data.',
    rows: Object.freeze(rows),
  });
}
