import assert from 'node:assert/strict';

export const FIELD_HALF_SIZE_DEG = 10;
export const DARK_BASE_CD_M2 = 0.0065;
export const TARGET_X_DEG = 4.3;
export const TARGET_Y_DEG = 0;
export const SOURCE_TARGET_VEILING_CD_M2 = 0.07;
export const UCHIDA_LOCAL_RADIUS_DEG = 12.4;

const BACKGROUNDS = Object.freeze({
  Bar9: Object.freeze({ kind: 'bars', offsetDeg: 9, widthDeg: 2, luminanceCdM2: 42 }),
  'Bar2.7': Object.freeze({ kind: 'bars', offsetDeg: 2.7, widthDeg: 2, luminanceCdM2: 5.1 }),
  Square: Object.freeze({ kind: 'square', sizeDeg: 2, centerXDeg: 0, centerYDeg: 0, luminanceCdM2: 101 }),
});

function luminanceAt(name, x, y) {
  const cfg = BACKGROUNDS[name];
  if (cfg.kind === 'bars') {
    // The source's two horizontal bars span the 20-degree visible field; their 2-degree
    // width is vertical. This geometry reproduces the reported ~20% bright-area fraction.
    const inBar = Math.abs(Math.abs(y) - cfg.offsetDeg) <= cfg.widthDeg / 2;
    return inBar ? cfg.luminanceCdM2 : DARK_BASE_CD_M2;
  }
  const half = cfg.sizeDeg / 2;
  const inSquare = Math.abs(x - cfg.centerXDeg) <= half && Math.abs(y - cfg.centerYDeg) <= half;
  return inSquare ? cfg.luminanceCdM2 : DARK_BASE_CD_M2;
}

function alfRawWeight(r2) {
  const narrowSd = 0.67;
  const broadSd = 3.9;
  return 0.9935 * Math.exp(-r2 / (2 * narrowSd ** 2))
    + 0.0065 * Math.exp(-r2 / (2 * broadSd ** 2));
}

export function calculateSpatialArms(stepDeg = 0.02) {
  assert.ok(stepDeg > 0 && Number.isFinite(stepDeg));
  const n = Math.round((2 * FIELD_HALF_SIZE_DEG) / stepDeg);
  assert.ok(Math.abs(n * stepDeg - 2 * FIELD_HALF_SIZE_DEG) < 1e-12,
    'step must tile the 20-degree source field exactly');

  const accum = Object.fromEntries(Object.keys(BACKGROUNDS).map((name) => [name, {
    sum: 0,
    localSum: 0,
    localCount: 0,
    alfWeightedSum: 0,
  }]));
  let alfWeightSum = 0;
  let pixelCount = 0;

  for (let iy = 0; iy < n; iy += 1) {
    const y = -FIELD_HALF_SIZE_DEG + (iy + 0.5) * stepDeg;
    for (let ix = 0; ix < n; ix += 1) {
      const x = -FIELD_HALF_SIZE_DEG + (ix + 0.5) * stepDeg;
      const dx = x - TARGET_X_DEG;
      const dy = y - TARGET_Y_DEG;
      const r2 = dx * dx + dy * dy;
      const inUchida = r2 <= UCHIDA_LOCAL_RADIUS_DEG ** 2;
      const w = alfRawWeight(r2);
      alfWeightSum += w;
      pixelCount += 1;
      for (const name of Object.keys(BACKGROUNDS)) {
        const L = luminanceAt(name, x, y);
        const a = accum[name];
        a.sum += L;
        a.alfWeightedSum += w * L;
        if (inUchida) {
          a.localSum += L;
          a.localCount += 1;
        }
      }
    }
  }

  const result = {};
  for (const name of Object.keys(BACKGROUNDS)) {
    const a = accum[name];
    result[name] = Object.freeze({
      S0_POINT: luminanceAt(name, TARGET_X_DEG, TARGET_Y_DEG),
      S1_SOURCE_VISIBLE_AREA: a.sum / pixelCount,
      S2_ALF: a.alfWeightedSum / alfWeightSum,
      S3_UCHIDA_LOCAL: a.localSum / a.localCount,
      sourceTargetVeilingCdM2Separate: SOURCE_TARGET_VEILING_CD_M2,
    });
  }
  return Object.freeze(result);
}

function compatibleWithSourceOrdering(results, arm) {
  return results['Bar2.7'][arm] > results.Bar9[arm]
    && results.Square[arm] > results.Bar9[arm];
}

export function runStokkermansSpatialAudit() {
  const fine = calculateSpatialArms(0.02);
  const coarse = calculateSpatialArms(0.04);
  const arms = ['S0_POINT', 'S1_SOURCE_VISIBLE_AREA', 'S2_ALF', 'S3_UCHIDA_LOCAL'];
  const classifications = Object.fromEntries(arms.map((arm) => [arm, Object.freeze({
    fineCompatible: compatibleWithSourceOrdering(fine, arm),
    coarseCompatible: compatibleWithSourceOrdering(coarse, arm),
  })]));

  // Source target: both near-structure backgrounds must imply greater adaptation load than far Bar9.
  assert.equal(classifications.S2_ALF.fineCompatible, true, 'source-defined ALF must pass the frozen qualitative ordering');
  assert.equal(classifications.S2_ALF.coarseCompatible, true, 'ALF ordering must be grid-resolution stable');

  // Preserve failures rather than tuning them away.
  assert.equal(classifications.S0_POINT.fineCompatible, false, 'point-only control should preserve its source-order failure');
  assert.equal(classifications.S1_SOURCE_VISIBLE_AREA.fineCompatible, false, 'visible-area average should preserve its source-order failure');
  assert.equal(classifications.S3_UCHIDA_LOCAL.fineCompatible, false, 'unweighted 12.4-degree local circle should preserve its source-order failure in this different source geometry');

  // ALF normalization is explicit: a spatially uniform field is an identity under unit-mass normalization.
  const uniform = 3.7;
  let wsum = 0;
  let weighted = 0;
  const step = 0.04;
  const n = Math.round(20 / step);
  for (let iy = 0; iy < n; iy += 1) {
    const y = -10 + (iy + 0.5) * step;
    for (let ix = 0; ix < n; ix += 1) {
      const x = -10 + (ix + 0.5) * step;
      const r2 = (x - TARGET_X_DEG) ** 2 + (y - TARGET_Y_DEG) ** 2;
      const w = alfRawWeight(r2);
      wsum += w;
      weighted += w * uniform;
    }
  }
  assert.ok(Math.abs(weighted / wsum - uniform) < 1e-12, 'ALF unit-mass normalization must preserve uniform luminance');

  return Object.freeze({
    angularMeasure: 'degrees on the source 20deg x 20deg visible display field',
    integrationRule: 'equal-angular-area midpoint grid; source-order classification checked at 0.02deg and 0.04deg',
    alfNormalization: 'raw target-centred two-Gaussian kernel normalized to unit discrete mass over the visible field',
    intraocularVeilingHandling: 'reported separately as source target condition 0.07 cd/m^2; not added to external physical luminance in this first spatial check',
    fine,
    coarse,
    classifications,
    interpretation: Object.freeze({
      S2_ALF_sourceCompatible: true,
      S0_POINT_sourceCompatible: false,
      S1_SOURCE_VISIBLE_AREA_sourceCompatible: false,
      S3_UCHIDA_LOCAL_sourceCompatibleInThisGeometry: false,
      astronomyTransferValidated: false,
      note: 'Failure of S3 here does not refute Uchida-Ohno in its own peripheral-task geometry; it rejects treating an unweighted 12.4-degree circle as a universal transferable operator for the Stokkermans E2 geometry.',
    }),
  });
}

if (import.meta.url === `file://${process.argv[1]}`) {
  process.stdout.write(`${JSON.stringify(runStokkermansSpatialAudit(), null, 2)}\n`);
}
