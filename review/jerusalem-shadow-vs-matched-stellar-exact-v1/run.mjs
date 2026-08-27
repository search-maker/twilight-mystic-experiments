import { readFile, readdir, mkdir, writeFile } from 'node:fs/promises';
import { resolve, join } from 'node:path';
import { pathToFileURL } from 'node:url';

const APP_SHA = 'e2d5b761206b6223526f6f79fcb0af5f6de3ba06';
const FAMILIES = Object.freeze([
  'opac-continental-average',
  'opac-maritime-clean',
  'opac-desert',
  'opac-desert-spheroids',
]);
const SITE = Object.freeze({ latitudeDeg: 31.778, longitudeDeg: 35.235 });
const observerCriterion = Object.freeze({
  id: 'jerusalem-exact-shadow-vs-matched-f-3-14',
  fieldFactor: 3.14,
  branch: 'full',
  factorBasis: Object.freeze({ mediumFactor: 1, source: 'frozen-project-criterion' }),
  uncertainty: Object.freeze({ empiricallyCalibratedForTwilight: false }),
});

function parseArgs(argv) {
  const args = { appRoot: null, output: 'stellar-transport-isolation.json' };
  for (let i = 2; i < argv.length; i += 1) {
    if (argv[i] === '--app-root') args.appRoot = argv[++i];
    else if (argv[i] === '--output') args.output = argv[++i];
    else throw new Error(`unknown argument: ${argv[i]}`);
  }
  if (!args.appRoot) throw new Error('--app-root is required');
  return args;
}

function finite(value, label) {
  const n = Number(value);
  if (!Number.isFinite(n)) throw new Error(`${label} must be finite`);
  return n;
}

function hrNumber(catalogId) {
  const m = String(catalogId ?? '').match(/HR\s*(\d+)/i);
  if (!m) throw new Error(`cannot parse HR from ${catalogId}`);
  return Number(m[1]);
}

function rowHasExactHr(row, hr) {
  if (!row || typeof row !== 'object' || Array.isArray(row)) return false;
  const namedKeys = ['hr', 'HR', 'hrNumber', 'harvardRevised', 'harvardRevisedNumber'];
  for (const key of namedKeys) if (key in row && Number(row[key]) === hr) return true;
  for (const [key, value] of Object.entries(row)) {
    if (/(^|_)(hr|harvard)(_|$)/i.test(key) && Number(value) === hr) return true;
  }
  return false;
}

function findCatalogRow(rows, hr) {
  let hits = rows.filter(row => rowHasExactHr(row, hr));
  if (hits.length === 0) {
    hits = rows.filter(row => row && typeof row === 'object' && !Array.isArray(row)
      && Object.values(row).some(value => (typeof value === 'number' || typeof value === 'string') && Number(value) === hr));
  }
  if (hits.length !== 1) throw new Error(`HR ${hr}: expected exactly one catalog row, got ${hits.length}`);
  return hits[0];
}

function commonKeys(rows) {
  if (!rows.length) return [];
  return Object.keys(rows[0]).filter(key => rows.every(row => Object.prototype.hasOwnProperty.call(row, key)));
}

function inferCatalogKeys(tammuzEvidence, tammuzRows) {
  const expectedBv = tammuzEvidence.stars.map(star => finite(star.transformedRow?.bMinusVJohnson, `${star.catalogId} B-V`));
  const expectedSp = tammuzEvidence.stars.map(star => String(star.transformedRow?.spectralType ?? '').trim());
  const keys = commonKeys(tammuzRows);
  const bvCandidates = keys.filter(key => tammuzRows.every((row, i) => {
    const n = Number(row[key]);
    return Number.isFinite(n) && Math.abs(n - expectedBv[i]) < 1e-12;
  }));
  const spCandidates = keys.filter(key => tammuzRows.every((row, i) => {
    const actual = String(row[key] ?? '').trim().replace(/\s+/g, '').toUpperCase();
    const expected = expectedSp[i].replace(/\s+/g, '').toUpperCase();
    return actual === expected || actual.startsWith(expected) || expected.startsWith(actual);
  }));
  if (bvCandidates.length !== 1) throw new Error(`could not uniquely infer B-V catalog key: ${bvCandidates.join(',')}`);
  if (spCandidates.length !== 1) throw new Error(`could not uniquely infer spectral-type catalog key: ${spCandidates.join(',')}`);
  return Object.freeze({ bvKey: bvCandidates[0], spectralTypeKey: spCandidates[0] });
}

async function loadBuiltCatalog(appRoot) {
  const assetsDir = join(appRoot, 'dist', 'assets');
  const names = (await readdir(assetsDir)).filter(name => /^stars-builtin-catalog-[0-9a-f]+\.js$/.test(name)).sort();
  if (names.length < 1) throw new Error('externalized built-in catalog asset not found after build');
  globalThis.__STARS_BUILT_IN_STARS__ = [];
  globalThis.__STARS_BUILT_IN_CATALOG_RESOLVE__ = () => {};
  globalThis.__STARS_BUILT_IN_CATALOG_REJECT__ = error => { throw error; };
  await import(pathToFileURL(join(assetsDir, names[0])).href);
  const rows = globalThis.__STARS_BUILT_IN_STARS__;
  if (!Array.isArray(rows) || rows.length !== 9090) throw new Error(`built catalog row count drift: ${rows?.length}`);
  return { rows, assetName: names[0] };
}

async function loadJson(path) {
  return JSON.parse(await readFile(path, 'utf8'));
}

function buildTarget(starEvidence, rawRow, keys) {
  const catalogMagnitudeV = finite(starEvidence.catalogMagnitudeV, `${starEvidence.catalogId} catalog V`);
  const bv = finite(rawRow[keys.bvKey], `${starEvidence.catalogId} catalog B-V`);
  const spectralType = String(rawRow[keys.spectralTypeKey] ?? '').trim();
  if (!spectralType) throw new Error(`${starEvidence.catalogId}: missing spectral type`);
  return Object.freeze({
    name: starEvidence.name,
    catalogId: starEvidence.catalogId,
    magOriginal: catalogMagnitudeV,
    magUsed: catalogMagnitudeV,
    magSource: 'Johnson V',
    catalogSource: 'BSC5/Yale Bright Star processed local catalog',
    bv,
    spectralType,
  });
}

function makeAtmosphere(createAtmosphereState, season, evidence) {
  const validTime = new Date(Number(evidence.event.eventSampleTimestampMs)).toISOString();
  return createAtmosphereState({
    provider: `frozen-jerusalem-${season}-event-evidence`,
    dataset: `issue-107-${season}-exact-event`,
    validTime,
    fetchTime: validTime,
    staleAfterSeconds: 86400,
    latitudeDeg: SITE.latitudeDeg,
    longitudeDeg: SITE.longitudeDeg,
    observerElevationM: finite(evidence.event.observerElevationM, `${season} elevation`),
    aod550: finite(evidence.event.aod550, `${season} AOD550`),
    qualityClass: 'modeled-live',
  }, { now: new Date(validTime) });
}

function eventGeometry(evidence, star) {
  return Object.freeze({
    sunDepressionDeg: finite(evidence.event.sunDepressionDeg, 'sun depression'),
    targetAltitudeDeg: finite(star.eventGeometry.targetAltitudeDeg, `${star.catalogId} altitude`),
    relativeAzimuthDeg: finite(star.eventGeometry.relativeAzimuthDeg, `${star.catalogId} relative azimuth`),
  });
}

const { appRoot: appRootArg, output } = parseArgs(process.argv);
const appRoot = resolve(appRootArg);
const v3 = join(appRoot, 'scientific-tools', 'visibility-v3');
const scientificRoot = resolve('.');

const [
  { createAtmosphereState },
  { createValidatedV3SkyProvider },
  { createAerosolScenarioSkyProvider },
  { compareAerosolScenarioShadowVsMatchedSample },
  { createBrowserSameAtmosphereVBandStellarSignalEvaluator },
  { createPackagedMatchedAerosolStellarSignalEvaluatorV2 },
] = await Promise.all([
  import(pathToFileURL(join(v3, 'atmosphere-state.mjs')).href),
  import(pathToFileURL(join(v3, 'validated-v3-sky-provider.mjs')).href),
  import(pathToFileURL(join(v3, 'aerosol-scenario-sky-provider.mjs')).href),
  import(pathToFileURL(join(v3, 'matched-aerosol-visibility-comparison.mjs')).href),
  import(pathToFileURL(join(v3, 'level-b-browser-stellar-signal.mjs')).href),
  import(pathToFileURL(join(v3, 'matched-aerosol-stellar-runtime-loader-v2.mjs')).href),
]);

const [tishreiEvidence, tammuzEvidence, validatedRuntime, asivRuntimeData, sedBundle, rawJohnsonV] = await Promise.all([
  loadJson(join(scientificRoot, 'experiments', 'jerusalem-tishrei-direct-mystic-v1', 'level-b-event-evidence.json')),
  loadJson(join(scientificRoot, 'experiments', 'jerusalem-tammuz-direct-mystic-v1', 'level-b-event-evidence.json')),
  loadJson(join(v3, 'validated-v3-primary-runtime-v1.json')),
  loadJson(join(v3, 'aerosol-scenario-interpolator-runtime-v1.json')),
  loadJson(join(v3, 'generated', 'pickles-sed-1nm.json')),
  loadJson(join(v3, 'generated', 'johnson-v-1nm.json')),
]);

for (const evidence of [tishreiEvidence, tammuzEvidence]) {
  if (evidence.applicationMainSha !== APP_SHA) throw new Error(`evidence/app SHA mismatch: ${evidence.applicationMainSha}`);
  if (Number(evidence.event.fieldFactor) !== 3.14) throw new Error('frozen F is not 3.14');
}

const johnsonVBandpass = Object.freeze({
  ...rawJohnsonV,
  wavelengthNm: Object.freeze([...rawJohnsonV.wavelengthNm]),
  response: Object.freeze(rawJohnsonV.response.slice(0, rawJohnsonV.wavelengthNm.length)),
});
if (johnsonVBandpass.wavelengthNm.length !== 401 || johnsonVBandpass.response.length !== 401) {
  throw new Error('Johnson-V canonicalized runtime shape drift');
}

const { rows: catalogRows, assetName: catalogAssetName } = await loadBuiltCatalog(appRoot);
const tammuzRawRows = tammuzEvidence.stars.map(star => findCatalogRow(catalogRows, hrNumber(star.catalogId)));
const catalogKeys = inferCatalogKeys(tammuzEvidence, tammuzRawRows);

const baselineProvider = createValidatedV3SkyProvider({ runtimeData: validatedRuntime });
const shadowStellar = createBrowserSameAtmosphereVBandStellarSignalEvaluator();
const matchedByFamily = new Map();
for (const family of FAMILIES) {
  matchedByFamily.set(family, await createPackagedMatchedAerosolStellarSignalEvaluatorV2({
    aerosolFamily: family,
    sedBundle,
    johnsonVBandpass,
  }));
}

const seasons = [];
for (const [season, evidence] of [['tishrei', tishreiEvidence], ['tammuz', tammuzEvidence]]) {
  const atmosphere = makeAtmosphere(createAtmosphereState, season, evidence);
  const seasonRows = [];
  for (const star of evidence.stars) {
    const rawRow = findCatalogRow(catalogRows, hrNumber(star.catalogId));
    const target = buildTarget(star, rawRow, catalogKeys);
    const geometry = eventGeometry(evidence, star);
    const nativeSignal = shadowStellar({ geometry, atmosphere, target });
    if (nativeSignal.status !== 'SUPPORTED') throw new Error(`${season}/${star.catalogId}: native stellar unsupported: ${nativeSignal.reason}`);
    const frozenExtinction = finite(star.stellar.extinctionMagV, `${star.catalogId} frozen extinction`);
    const frozenApparent = finite(star.stellar.apparentVMagAtEye, `${star.catalogId} frozen apparent V`);
    const nativeConsistency = {
      extinctionDeltaMag: nativeSignal.extinctionMagV - frozenExtinction,
      apparentVDeltaMag: nativeSignal.apparentVMagAtEye - frozenApparent,
    };
    if (Math.abs(nativeConsistency.extinctionDeltaMag) > 2e-6 || Math.abs(nativeConsistency.apparentVDeltaMag) > 2e-6) {
      throw new Error(`${season}/${star.catalogId}: native evaluator does not reproduce frozen evidence: ${JSON.stringify(nativeConsistency)}`);
    }

    const familyRows = [];
    for (const family of FAMILIES) {
      const scenarioSkyProvider = createAerosolScenarioSkyProvider({
        baselineProvider,
        asivRuntimeData,
        observerCriterion,
        stateId: family,
      });
      const sample = compareAerosolScenarioShadowVsMatchedSample({
        geometry,
        atmosphere,
        scenarioSkyProvider,
        shadowStellarSignalEvaluator: shadowStellar,
        matchedStellarSignalEvaluator: matchedByFamily.get(family),
        target,
        observerCriterion,
      });
      if (sample.status !== 'SUPPORTED') throw new Error(`${season}/${star.catalogId}/${family}: ${sample.reason}`);
      familyRows.push({
        aerosolFamily: family,
        scenarioSkyPhotopicCdM2: sample.sky.photopicLuminanceCdM2,
        shadow: {
          extinctionMagV: sample.shadow.stellar.extinctionMagV,
          apparentVMagAtEye: sample.shadow.stellar.apparentVMagAtEye,
          limitingVMagnitude: sample.shadow.limitingVMagnitude,
          visibilityMarginMag: sample.shadow.visibilityMarginMag,
          visible: sample.shadow.visible,
        },
        matched: {
          extinctionMagV: sample.matched.stellar.extinctionMagV,
          apparentVMagAtEye: sample.matched.stellar.apparentVMagAtEye,
          limitingVMagnitude: sample.matched.limitingVMagnitude,
          visibilityMarginMag: sample.matched.visibilityMarginMag,
          visible: sample.matched.visible,
        },
        delta: sample.delta,
        isolation: sample.isolation,
      });
    }
    seasonRows.push({
      catalogId: star.catalogId,
      name: star.name,
      completingStar: star.completingStar === true,
      catalogMagnitudeV: star.catalogMagnitudeV,
      catalogColorAndType: { bv: target.bv, spectralType: target.spectralType },
      geometry,
      frozenNativeEvidence: {
        extinctionMagV: frozenExtinction,
        apparentVMagAtEye: frozenApparent,
        visibilityMarginMag: star.visibility.visibilityMarginMag,
      },
      nativeConsistency,
      families: familyRows,
    });
  }
  seasons.push({
    season,
    civilDate: evidence.event.civilDate,
    eventTimeMs: evidence.event.eventTimeMsFromThreeStarResult,
    sunDepressionDeg: evidence.event.sunDepressionDeg,
    aod550: evidence.event.aod550,
    observerElevationM: evidence.event.observerElevationM,
    fieldFactor: evidence.event.fieldFactor,
    stars: seasonRows,
  });
}

const allDeltas = seasons.flatMap(season => season.stars.flatMap(star => star.families.map(row => row.delta.matchedMinusShadowExtinctionMagV)));
const result = {
  schemaVersion: 1,
  status: 'EXACT_JERUSALEM_SHADOW_VS_MATCHED_STELLAR_ISOLATION_COMPLETE',
  applicationSha: APP_SHA,
  scientificRepositoryHeadAtPreparation: '78fae53bab58e8e0645a5a0ab27b8cf414dd5eb2',
  frozenEvidence: {
    tishrei: { runId: 32982830256, artifactId: 9612259358 },
    tammuz: { runId: 33025015603, artifactId: 9628151845 },
  },
  catalog: { rowCount: catalogRows.length, assetName: catalogAssetName, inferredKeys: catalogKeys },
  method: {
    comparator: 'SHADOW_NATIVE_STAR_VS_MATCHED_FAMILY_STAR_REVIEW_ONLY',
    sameSelectedFamilyScenarioSkyOnBothSides: true,
    shadowStarTransport: 'active frozen MYSTIC-STATE-0081 native stellar v2',
    matchedStarTransport: 'fresh-validated matched-stellar v2 per OPAC family',
    families: FAMILIES,
    fieldFactorUnchanged: 3.14,
    noParameterTuning: true,
    noMysticSolverExecution: true,
    noFamilyInferenceFromVisibility: true,
  },
  aggregate: {
    comparisonCount: allDeltas.length,
    minMatchedMinusShadowExtinctionMagV: Math.min(...allDeltas),
    maxMatchedMinusShadowExtinctionMagV: Math.max(...allDeltas),
    maxAbsMatchedMinusShadowExtinctionMagV: Math.max(...allDeltas.map(Math.abs)),
  },
  seasons,
  claimBoundary: {
    productionAuthorized: false,
    measuredRealSkyValidated: false,
    humanFirstSeeingValidated: false,
    fullSpectrumSkyValidated: false,
    pandoraOpened: false,
  },
};

await mkdir(resolve(output, '..'), { recursive: true });
await writeFile(output, `${JSON.stringify(result, null, 2)}\n`, 'utf8');
console.log(JSON.stringify({ status: result.status, comparisonCount: result.aggregate.comparisonCount, aggregate: result.aggregate }, null, 2));
