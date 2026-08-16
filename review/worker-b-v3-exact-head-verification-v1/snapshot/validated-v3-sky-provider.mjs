import { SKY_STATUS, availableChannel, unavailableChannel } from './sky-provider.mjs';

export const LEVEL_B_V3_PACKAGE_ARTIFACT_ID = 9259468043;
export const LEVEL_B_V3_PACKAGE_DIGEST = 'sha256:ed7c62c3efea525c531ab6587108320f5be5546d210af5054a5304ed07939a39';
export const LEVEL_B_V3_PACKAGE_MANIFEST_SHA256 = '2df88b800483127d565e66b03a5773920dd6a687f9afb0ace43f3cc93b2635aa';
export const LEVEL_B_V3_MODEL_CANONICAL_SHA256 = 'c4902eb3c2ba67b12dc4ef2b9cefb67c5963a6abc104708a73b2aab5dd0163b9';
export const LEVEL_B_V3_REPRESENTATION_SHA256 = '2491ac91ed924f2ba69b37ea20f48d63f51d41146cd9fe50e0bd63bfb315a763';
export const LEVEL_B_V3_VALIDATION_BINDING_SHA256 = '120a4649ad61159c4d4edc13f10dd8ca335408dc2dcc3b9c0889bbced2485c57';
export const LEVEL_B_V3_RUNTIME_DATA_SHA256 = '6a927bd702ebbf1b1913ebe51731f3b92f967f2ae95edf090280b8370ea091e4';
export const LEVEL_B_V3_VALIDATION_STATUS = 'PASS_FROZEN_FRESH_DOD';
export const LEVEL_B_V3_PROVIDER_ID = 'level-b-v3-validated-primary';
export const LEVEL_B_V3_SUPPORT_DISTANCE_MAX = 0.60;

const DESIGN_BOX = Object.freeze({
  sunDepressionDeg: Object.freeze([2.0, 10.5]),
  targetAltitudeDeg: Object.freeze([5.0, 80.0]),
  relativeAzimuthDeg: Object.freeze([0.0, 180.0]),
  observerElevationM: Object.freeze([0.0, 2500.0]),
  aod550: Object.freeze([0.05, 0.40]),
});

function finiteNumber(v) { return typeof v === 'number' && Number.isFinite(v); }
function assertFiniteArray(v, length, label) {
  if (!Array.isArray(v) || v.length !== length || v.some(x => !finiteNumber(x))) throw new RangeError(`${label} drift`);
}
function assertMatrix(v, rows, cols, label) {
  if (!Array.isArray(v) || v.length !== rows) throw new RangeError(`${label} row drift`);
  for (const row of v) assertFiniteArray(row, cols, label);
}

export function validateValidatedV3RuntimeData(data) {
  if (!data || typeof data !== 'object' || Array.isArray(data)) throw new TypeError('validated-v3 runtime data object required');
  if (data.schemaVersion !== 1) throw new RangeError('runtime data schema drift');
  if (data.sourceModelCanonicalSha256 !== LEVEL_B_V3_MODEL_CANONICAL_SHA256) throw new RangeError('runtime data model hash drift');
  if (data.primaryBasis !== 'PHYSICAL_COMPACT_16_TERMS') throw new RangeError('primary basis drift');
  if (data.residualCoordinateSystem !== 'V1_IDW_COS_COORDINATES') throw new RangeError('residual coordinate system drift');
  if (data.residualNeighbors !== 6 || data.residualPower !== 1 || data.residualShrinkage !== 1) throw new RangeError('residual hyperparameter drift');
  assertMatrix(data.primaryCoefficients, 16, 3, 'primary coefficients');
  assertMatrix(data.supportCoordinates, 58, 5, 'support coordinates');
  assertMatrix(data.residualCoordinates, 58, 5, 'residual coordinates');
  assertMatrix(data.residualTargets, 58, 3, 'residual targets');
  return data;
}

function inputFrom({ geometry, atmosphere }) {
  return {
    sunDepressionDeg: Number(geometry?.sunDepressionDeg),
    targetAltitudeDeg: Number(geometry?.targetAltitudeDeg),
    relativeAzimuthDeg: Number(geometry?.relativeAzimuthDeg),
    observerElevationM: Number(atmosphere?.observerElevationM),
    aod550: Number(atmosphere?.aod550),
  };
}

function inputIssue(input) {
  for (const key of Object.keys(DESIGN_BOX)) if (!finiteNumber(input[key])) return `NONFINITE_${key}`;
  if (!(input.aod550 > 0)) return 'AOD550_NOT_POSITIVE';
  return null;
}

function insideDesignBox(input) {
  return Object.entries(DESIGN_BOX).every(([key, [lo, hi]]) => input[key] >= lo && input[key] <= hi);
}

function physicalBasis16(input) {
  const s = (input.sunDepressionDeg - 2.0) / 8.5;
  const a = Math.sin(input.targetAltitudeDeg * Math.PI / 180.0);
  const c = Math.cos(input.relativeAzimuthDeg * Math.PI / 180.0);
  const e = input.observerElevationM / 2500.0;
  const o = Math.log(input.aod550 / 0.05) / Math.log(8.0);
  return [1, s, a, c, e, o, s*s, a*a, c*c, o*o, s*a, s*c, s*o, a*c, a*o, c*o];
}

export function v1IdwCosCoordinates(input) {
  return [
    (input.sunDepressionDeg - 2.0) / 8.5,
    (input.targetAltitudeDeg - 5.0) / 75.0,
    (Math.cos(input.relativeAzimuthDeg * Math.PI / 180.0) + 1.0) / 2.0,
    input.observerElevationM / 2500.0,
    (input.aod550 - 0.05) / 0.35,
  ];
}

function distance5(a, b) {
  let sum = 0;
  for (let i = 0; i < 5; i += 1) { const d = a[i] - b[i]; sum += d*d; }
  return Math.sqrt(sum);
}

export function classifyValidatedV3Support(input, runtimeData) {
  validateValidatedV3RuntimeData(runtimeData);
  const issue = inputIssue(input);
  if (issue) return Object.freeze({ validInput: false, nominalDesignBox: false, validatedSupport: false, nearestTrainingDistance: null, reasons: Object.freeze([issue]) });
  const nominalDesignBox = insideDesignBox(input);
  if (!nominalDesignBox) return Object.freeze({ validInput: true, nominalDesignBox: false, validatedSupport: false, nearestTrainingDistance: null, reasons: Object.freeze(['OUTSIDE_VALIDATED_PHYSICAL_DESIGN_BOX']) });
  const q = v1IdwCosCoordinates(input);
  let nearest = Infinity;
  for (const x of runtimeData.supportCoordinates) nearest = Math.min(nearest, distance5(x, q));
  const validatedSupport = nearest <= LEVEL_B_V3_SUPPORT_DISTANCE_MAX;
  return Object.freeze({
    validInput: true,
    nominalDesignBox: true,
    validatedSupport,
    nearestTrainingDistance: nearest,
    reasons: Object.freeze(validatedSupport ? [] : ['NEAREST_FROZEN_TRAINING_DISTANCE_EXCEEDS_0.60']),
  });
}

function dotPrimary(basis, coefficients) {
  const out = [0, 0, 0];
  for (let i = 0; i < 16; i += 1) for (let j = 0; j < 3; j += 1) out[j] += basis[i] * coefficients[i][j];
  return out;
}

function residualIdw(query, runtimeData) {
  const ordered = runtimeData.residualCoordinates.map((x, index) => ({ index, distance: distance5(x, query) }));
  ordered.sort((a, b) => a.distance - b.distance || a.index - b.index);
  const first = ordered[0];
  if (first.distance === 0) return [...runtimeData.residualTargets[first.index]];
  const chosen = ordered.slice(0, runtimeData.residualNeighbors);
  let weightSum = 0;
  const out = [0, 0, 0];
  for (const row of chosen) {
    const weight = 1 / (row.distance ** runtimeData.residualPower);
    weightSum += weight;
    const target = runtimeData.residualTargets[row.index];
    for (let j = 0; j < 3; j += 1) out[j] += weight * target[j];
  }
  for (let j = 0; j < 3; j += 1) out[j] /= weightSum;
  return out;
}

export function predictValidatedV3PrimaryLogs(input, runtimeData) {
  validateValidatedV3RuntimeData(runtimeData);
  const issue = inputIssue(input);
  if (issue) throw new RangeError(issue);
  const base = dotPrimary(physicalBasis16(input), runtimeData.primaryCoefficients);
  const corr = residualIdw(v1IdwCosCoordinates(input), runtimeData);
  return Object.freeze(base.map((value, j) => value + runtimeData.residualShrinkage * corr[j]));
}

export function createValidatedV3SkyProvider({ runtimeData, id = LEVEL_B_V3_PROVIDER_ID } = {}) {
  validateValidatedV3RuntimeData(runtimeData);
  return Object.freeze({
    id,
    evaluateSky({ geometry, atmosphere }) {
      const input = inputFrom({ geometry, atmosphere });
      const support = classifyValidatedV3Support(input, runtimeData);
      const common = {
        support: {
          nominalDesignBox: support.nominalDesignBox,
          validatedSupport: support.validatedSupport,
          nearestTrainingDistance: support.nearestTrainingDistance,
          maxNearestTrainingDistance: LEVEL_B_V3_SUPPORT_DISTANCE_MAX,
          supportRule: 'PHYSICAL_DESIGN_BOX_AND_NEAREST_V1_IDW_COS_TRAINING_DISTANCE_LE_0.60',
          reasons: [...support.reasons],
        },
        provenance: {
          version: 'level-b-v3-computationally-validated-primary-v1',
          modelHash: LEVEL_B_V3_MODEL_CANONICAL_SHA256,
          packageArtifactId: LEVEL_B_V3_PACKAGE_ARTIFACT_ID,
          packageDigest: LEVEL_B_V3_PACKAGE_DIGEST,
          packageManifestSha256: LEVEL_B_V3_PACKAGE_MANIFEST_SHA256,
          representationSha256: LEVEL_B_V3_REPRESENTATION_SHA256,
          validationBindingSha256: LEVEL_B_V3_VALIDATION_BINDING_SHA256,
          validationStatus: LEVEL_B_V3_VALIDATION_STATUS,
          atmosphereIdentity: atmosphere?.identity ?? null,
          fallbackPath: null,
          computationallyValidatedAgainstFreshMystic: true,
          measuredRealSkyValidated: false,
          humanFirstSeeingValidated: false,
          productionAuthorized: false,
        },
      };
      if (!support.validInput) return { status: SKY_STATUS.INVALID_INPUT, ...common };
      if (!support.validatedSupport) return { status: SKY_STATUS.OOD, ...common };
      if (atmosphere?.cloud?.directionalClear === false) {
        return { status: SKY_STATUS.CLOUD_UNSUPPORTED, ...common, support: { ...common.support, validatedSupport: false, reasons: ['DIRECTIONAL_CLOUD'] } };
      }
      const logs = predictValidatedV3PrimaryLogs(input, runtimeData);
      const values = logs.map(Math.exp);
      if (values.some(v => !Number.isFinite(v) || !(v > 0))) return { status: SKY_STATUS.PROVIDER_UNAVAILABLE, ...common, support: { ...common.support, reasons: ['NONFINITE_PRIMARY_PREDICTION'] } };
      return {
        status: SKY_STATUS.SUPPORTED,
        channels: {
          photopic: availableChannel(values[0], 'cd/m2'),
          scotopic: availableChannel(values[1], 'scotopic-cd/m2'),
          johnsonV: availableChannel(values[2], 'mW/m2/nm/sr'),
          spectral: unavailableChannel('VALIDATED_V3_PRIMARY_PROVIDER_SPECTRAL_RUNTIME_NOT_IMPLEMENTED'),
        },
        uncertainty: {
          kind: 'frozen-computational-surrogate-budget-not-empirical-coverage',
          surrogateLogErrorBudgetOneSigma: 0.12,
          empiricalCoverageCalibrated: false,
        },
        ...common,
      };
    },
  });
}
