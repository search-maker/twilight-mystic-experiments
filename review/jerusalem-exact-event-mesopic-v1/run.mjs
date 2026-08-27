import { readFile, readdir, mkdir, writeFile } from 'node:fs/promises';
import { resolve, join } from 'node:path';
import { pathToFileURL } from 'node:url';

const APP_SHA = '80110c8cb4575c7be3c91b4817be5126c40b2b15';
const MESOPIC_SHA = 'c1de484b9dfe5e91f569be02debea3c214d67d11';
const FAMILIES = Object.freeze([
  'opac-continental-average',
  'opac-maritime-clean',
  'opac-desert',
  'opac-desert-spheroids',
]);
const FROZEN_EVIDENCE = Object.freeze([
  Object.freeze({ season: 'Tishrei', path: 'experiments/jerusalem-tishrei-direct-mystic-v1/level-b-event-evidence.json' }),
  Object.freeze({ season: 'Tammuz', path: 'experiments/jerusalem-tammuz-direct-mystic-v1/level-b-event-evidence.json' }),
]);

function parseArgs(argv) {
  const out = { appRoot: null, mesopicRoot: null, repoRoot: '.', output: 'diagnostic-output/jerusalem-exact-event-mesopic-v1.json' };
  for (let i = 2; i < argv.length; i += 1) {
    const key = argv[i];
    if (key === '--app-root') out.appRoot = argv[++i];
    else if (key === '--mesopic-root') out.mesopicRoot = argv[++i];
    else if (key === '--repo-root') out.repoRoot = argv[++i];
    else if (key === '--output') out.output = argv[++i];
    else throw new Error(`unknown argument ${key}`);
  }
  if (!out.appRoot || !out.mesopicRoot) throw new Error('--app-root and --mesopic-root are required');
  return out;
}

function finite(v, label) {
  const n = Number(v);
  if (!Number.isFinite(n)) throw new Error(`${label} must be finite`);
  return n;
}

function closeEnough(a, b, rel = 2e-10, abs = 1e-12) {
  return Math.abs(a - b) <= Math.max(abs, rel * Math.max(1, Math.abs(a), Math.abs(b)));
}

function rowHasExactHr(row, hr) {
  if (!row || typeof row !== 'object' || Array.isArray(row)) return false;
  for (const key of ['hr', 'HR', 'hrNumber', 'harvardRevised', 'harvardRevisedNumber']) {
    if (key in row && Number(row[key]) === hr) return true;
  }
  for (const [key, value] of Object.entries(row)) {
    if (/(^|_)(hr|harvard)(_|$)/i.test(key) && Number(value) === hr) return true;
  }
  return false;
}

function hrFromCatalogId(text) {
  const m = String(text ?? '').match(/HR\s*(\d+)/i);
  if (!m) throw new Error(`cannot parse HR from ${text}`);
  return Number(m[1]);
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

async function loadBuiltCatalog(appRoot) {
  const assetsDir = join(appRoot, 'dist', 'assets');
  const names = (await readdir(assetsDir)).filter(name => /^stars-builtin-catalog-[0-9a-f]+\.js$/.test(name)).sort();
  if (!names.length) throw new Error('built catalog asset missing');
  globalThis.__STARS_BUILT_IN_STARS__ = [];
  globalThis.__STARS_BUILT_IN_CATALOG_RESOLVE__ = () => {};
  globalThis.__STARS_BUILT_IN_CATALOG_REJECT__ = error => { throw error; };
  await import(pathToFileURL(join(assetsDir, names[0])).href + `?mesopic=${Date.now()}`);
  const rows = globalThis.__STARS_BUILT_IN_STARS__;
  if (!Array.isArray(rows) || rows.length !== 9090) throw new Error(`catalog row-count drift ${rows?.length}`);
  return { rows, assetName: names[0] };
}

function atmosphere(aod550, season, family = 'baseline') {
  return Object.freeze({
    identity: `jerusalem-exact-mesopic:${season}:${family}:aod-${aod550}`,
    aod550,
    observerElevationM: 800,
    cloud: Object.freeze({ directionalClear: true }),
  });
}

function criterion() {
  return Object.freeze({
    id: 'jerusalem-exact-mesopic-F3.14-review-only',
    fieldFactor: 3.14,
    branch: 'full',
    factorBasis: Object.freeze({ mediumFactor: 1, source: 'configured-current-model' }),
    uncertainty: Object.freeze({ empiricallyCalibratedForTwilight: false }),
  });
}

const args = parseArgs(process.argv);
const appRoot = resolve(args.appRoot);
const mesopicRoot = resolve(args.mesopicRoot);
const repoRoot = resolve(args.repoRoot);
const v3 = join(appRoot, 'scientific-tools', 'visibility-v3');

const [
  { createValidatedV3SkyProvider },
  { createAerosolScenarioSkyProvider },
  { loadPackagedMatchedAerosolStellarAssetV2 },
  { createMatchedAerosolStellarSpectralTransmissionProvider },
  { selectCatalogStellarSed },
  { stellarScotopicPhotopicRatioFromSpectrum, diagnoseMesopicSpectralVisibilityShift },
] = await Promise.all([
  import(pathToFileURL(join(v3, 'validated-v3-sky-provider.mjs')).href),
  import(pathToFileURL(join(v3, 'aerosol-scenario-sky-provider.mjs')).href),
  import(pathToFileURL(join(v3, 'matched-aerosol-stellar-assets-v2.mjs')).href),
  import(pathToFileURL(join(v3, 'matched-aerosol-stellar-runtime-v2.mjs')).href),
  import(pathToFileURL(join(v3, 'stellar-sed-selector.mjs')).href),
  import(pathToFileURL(join(mesopicRoot, 'scientific-tools', 'visibility-v3', 'review', 'mesopic-star-sky-sensitivity-v1.mjs')).href),
]);

const loadJson = async p => JSON.parse(await readFile(p, 'utf8'));
const [runtimeData, asivRuntimeData, sedBundle] = await Promise.all([
  loadJson(join(v3, 'validated-v3-primary-runtime-v1.json')),
  loadJson(join(v3, 'aerosol-scenario-interpolator-runtime-v1.json')),
  loadJson(join(v3, 'generated', 'pickles-sed-1nm.json')),
]);
const { rows: catalogRows, assetName } = await loadBuiltCatalog(appRoot);
const baselineProvider = createValidatedV3SkyProvider({ runtimeData });
const observerCriterion = criterion();

const familyRuntimes = new Map();
for (const family of FAMILIES) {
  const spectralRuntimeData = await loadPackagedMatchedAerosolStellarAssetV2({ aerosolFamily: family });
  familyRuntimes.set(family, createMatchedAerosolStellarSpectralTransmissionProvider({ aerosolFamily: family, spectralRuntimeData }));
}

const seasons = [];
for (const frozen of FROZEN_EVIDENCE) {
  const evidence = await loadJson(join(repoRoot, frozen.path));
  const d = finite(evidence.event?.sunDepressionDeg, `${frozen.season} sun depression`);
  const aod = finite(evidence.event?.aod550, `${frozen.season} AOD`);
  if (Number(evidence.event?.observerElevationM) !== 800) throw new Error(`${frozen.season}: observer elevation drift`);

  const stars = [];
  for (const star of evidence.stars) {
    const hr = hrFromCatalogId(star.catalogId);
    const catalog = findCatalogRow(catalogRows, hr);
    const catalogForSed = Object.freeze({
      ...catalog,
      bMinusV: star.transformedRow?.bMinusVJohnson ?? catalog.bMinusV ?? catalog.bv,
      bMinusVJohnson: star.transformedRow?.bMinusVJohnson ?? catalog.bMinusVJohnson,
      spectralType: star.transformedRow?.spectralType ?? catalog.spectralType,
    });
    const sed = selectCatalogStellarSed({ catalogStar: catalogForSed, sedBundle, rejectKnownComposite: false });
    const geometry = Object.freeze({
      sunDepressionDeg: d,
      targetAltitudeDeg: finite(star.eventGeometry?.targetAltitudeDeg, `${star.name} altitude`),
      relativeAzimuthDeg: finite(star.eventGeometry?.relativeAzimuthDeg, `${star.name} relative azimuth`),
    });

    // Hard parity check: current baseline provider must reproduce the frozen event sky.
    const baseSky = baselineProvider.evaluateSky({ geometry, atmosphere: atmosphere(aod, frozen.season) });
    if (baseSky.status !== 'SUPPORTED') throw new Error(`${frozen.season}/${star.name}: current baseline sky unsupported`);
    for (const channel of ['photopic', 'scotopic']) {
      const actual = finite(baseSky.channels?.[channel]?.value, `${star.name} current ${channel}`);
      const expected = finite(star.skyChannels?.[channel]?.value, `${star.name} frozen ${channel}`);
      if (!closeEnough(actual, expected)) {
        throw new Error(`${frozen.season}/${star.name}: frozen/current ${channel} drift ${actual} vs ${expected}`);
      }
    }

    const familyRows = [];
    for (const family of FAMILIES) {
      const atm = atmosphere(aod, frozen.season, family);
      const familySkyProvider = createAerosolScenarioSkyProvider({
        baselineProvider,
        asivRuntimeData,
        observerCriterion,
        stateId: family,
      });
      const sky = familySkyProvider.evaluateSky({ geometry, atmosphere: atm });
      if (sky.status !== 'SUPPORTED') {
        familyRows.push({ family, status: sky.status, reasons: sky.support?.reasons ?? [] });
        continue;
      }
      const transmission = familyRuntimes.get(family)({ geometry, atmosphere: atm });
      const sp = stellarScotopicPhotopicRatioFromSpectrum({
        wavelengthNm: sed.wavelengthNm,
        stellarSpectralWeight: sed.stellarSpectralWeight,
        directTransmittance: transmission.spectrum.lineOfSightDirectTransmission,
      });
      const diagnostic = diagnoseMesopicSpectralVisibilityShift({
        backgroundPhotopicLuminanceCdM2: sky.channels.photopic.value,
        backgroundScotopicLuminanceScotCdM2: sky.channels.scotopic.value,
        stellarScotopicPhotopicRatio: sp.scotopicPhotopicRatio,
      });
      familyRows.push(Object.freeze({
        family,
        status: 'SUPPORTED',
        skyPhotopicCdM2: sky.channels.photopic.value,
        skyScotopicCdM2: sky.channels.scotopic.value,
        skyScotopicPhotopicRatio: sky.channels.scotopic.value / sky.channels.photopic.value,
        mesopicM: diagnostic.adaptation.m,
        mesopicRegime: diagnostic.adaptation.regime,
        mesopicLuminanceCdM2: diagnostic.adaptation.mesopicLuminanceCdM2,
        stellarScotopicPhotopicRatio: sp.scotopicPhotopicRatio,
        deltaVisibilityMarginMag: diagnostic.mesopicMinusCurrentVisibilityMarginMag,
        interpretation: diagnostic.interpretation,
      }));
    }
    const supported = familyRows.filter(row => row.status === 'SUPPORTED');
    if (supported.length !== FAMILIES.length) throw new Error(`${frozen.season}/${star.name}: not all matched families supported`);
    const deltas = supported.map(row => row.deltaVisibilityMarginMag);
    stars.push(Object.freeze({
      catalogId: star.catalogId,
      name: star.name,
      completingStar: star.completingStar === true,
      frozenCurrentMarginMag: star.visibility?.visibilityMarginMag ?? null,
      geometry,
      selectedSed: Object.freeze({
        templateId: sed.templateId,
        spectralType: sed.spectralType,
        selectionBasis: sed.selectionBasis,
        catalogBMinusV: sed.catalogBMinusV,
        templateBMinusV: sed.templateBMinusVLandoltBmVc,
        colorResidualMag: sed.colorResidualMag,
        warnings: sed.warnings,
      }),
      familyRows: Object.freeze(familyRows),
      deltaSummaryMag: Object.freeze({ min: Math.min(...deltas), max: Math.max(...deltas), maxAbs: Math.max(...deltas.map(Math.abs)) }),
    }));
  }
  seasons.push(Object.freeze({
    season: frozen.season,
    evidencePath: frozen.path,
    sunDepressionDeg: d,
    aod550: aod,
    stars: Object.freeze(stars),
  }));
}

const all = seasons.flatMap(s => s.stars.flatMap(star => star.familyRows.map(row => ({ season: s.season, star: star.name, completingStar: star.completingStar, ...row }))));
const deltas = all.map(row => row.deltaVisibilityMarginMag);
const result = Object.freeze({
  schemaVersion: 1,
  status: 'EXACT_JERUSALEM_MESOPIC_SENSITIVITY_COMPLETE',
  applicationSha: APP_SHA,
  mesopicSourceSha: MESOPIC_SHA,
  builtCatalogAsset: assetName,
  method: 'CIE MES2 review-only; exact frozen Jerusalem event sky geometry; same-family ASIV photopic/scotopic sky; exact Pickles SED selected from current catalog; matched-stellar-v2 wavelength-resolved direct transmission',
  fieldFactorUsedForScenarioPlumbing: 3.14,
  fieldFactorCancelsFromMesopicDelta: true,
  noParameterFit: true,
  noMysticSolverExecution: true,
  overallDeltaVisibilityMarginMag: Object.freeze({ min: Math.min(...deltas), max: Math.max(...deltas), maxAbs: Math.max(...deltas.map(Math.abs)) }),
  seasons: Object.freeze(seasons),
  claimBoundary: Object.freeze({
    reviewOnlySensitivity: true,
    CIE191ValidatedForFovealStarDetection: false,
    humanFirstSeeingValidated: false,
    productionAuthorized: false,
    FChanged: false,
    skyRetuned: false,
    stellarTransportRetuned: false,
    pandoraOpened: false,
  }),
});
await mkdir(resolve(args.output, '..'), { recursive: true });
await writeFile(resolve(args.output), JSON.stringify(result, null, 2) + '\n');
console.log(JSON.stringify(result, null, 2));
