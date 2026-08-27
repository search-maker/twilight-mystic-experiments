import { readFile, readdir, mkdir, writeFile } from 'node:fs/promises';
import { resolve, join } from 'node:path';
import { pathToFileURL } from 'node:url';

const APP_SHA = '80110c8cb4575c7be3c91b4817be5126c40b2b15';
const FIXTURE_SHA = 'e676056d8c896a72bf37dd803becdf07a8cc71da';
const AOD_SWEEP = Object.freeze([0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40]);
const FIELD_FACTORS = Object.freeze([3.14, 2.4]);
const FAMILIES = Object.freeze([
  'opac-continental-average',
  'opac-maritime-clean',
  'opac-desert',
  'opac-desert-spheroids',
]);
const HR_BY_OBJECT = Object.freeze({ Capella: 1708, Aldebaran: 1457, Polaris: 424, Vega: 7001 });
const D_MIN = 2.0;
const D_MAX = 10.5;
const STEP = 0.01;

function parseArgs(argv) {
  const out = { appRoot: null, fixture: null, output: 'diagnostic-output/tousey-current-level-b.json' };
  for (let i = 2; i < argv.length; i += 1) {
    if (argv[i] === '--app-root') out.appRoot = argv[++i];
    else if (argv[i] === '--fixture') out.fixture = argv[++i];
    else if (argv[i] === '--output') out.output = argv[++i];
    else throw new Error(`unknown arg ${argv[i]}`);
  }
  if (!out.appRoot || !out.fixture) throw new Error('--app-root and --fixture required');
  return out;
}

function finite(v, label) {
  const n = Number(v);
  if (!Number.isFinite(n)) throw new Error(`${label} must be finite`);
  return n;
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

function findCatalogRow(rows, hr) {
  let hits = rows.filter(row => rowHasExactHr(row, hr));
  if (hits.length === 0) {
    hits = rows.filter(row => row && typeof row === 'object' && !Array.isArray(row)
      && Object.values(row).some(value => (typeof value === 'number' || typeof value === 'string') && Number(value) === hr));
  }
  if (hits.length !== 1) throw new Error(`HR ${hr}: expected exactly one row, got ${hits.length}`);
  return hits[0];
}

async function loadBuiltCatalog(appRoot) {
  const assetsDir = join(appRoot, 'dist', 'assets');
  const names = (await readdir(assetsDir)).filter(name => /^stars-builtin-catalog-[0-9a-f]+\.js$/.test(name)).sort();
  if (!names.length) throw new Error('built catalog asset missing');
  globalThis.__STARS_BUILT_IN_STARS__ = [];
  globalThis.__STARS_BUILT_IN_CATALOG_RESOLVE__ = () => {};
  globalThis.__STARS_BUILT_IN_CATALOG_REJECT__ = error => { throw error; };
  await import(pathToFileURL(join(assetsDir, names[0])).href);
  const rows = globalThis.__STARS_BUILT_IN_STARS__;
  if (!Array.isArray(rows) || rows.length !== 9090) throw new Error(`catalog row-count drift ${rows?.length}`);
  return { rows, assetName: names[0] };
}

function targetFrom(star, raw) {
  const bv = finite(raw.bv, `${star.object} B-V`);
  const spectralType = String(raw.spectralType ?? '').trim();
  if (!spectralType) throw new Error(`${star.object}: spectralType missing`);
  const mag = finite(star.catalogMagnitudeV, `${star.object} V`);
  return Object.freeze({
    name: star.object,
    catalogId: `HR ${HR_BY_OBJECT[star.object]}`,
    magOriginal: mag,
    magUsed: mag,
    magSource: 'Tousey-Koomen Table III catalog V',
    catalogSource: 'Tousey-Koomen Table III V with current BSC color/type only',
    bv,
    spectralType,
  });
}

function observerCriterion(F) {
  return Object.freeze({
    id: `tousey-current-level-b-F-${F}`,
    fieldFactor: F,
    branch: 'full',
    factorBasis: Object.freeze({ mediumFactor: 1, source: 'frozen-diagnostic' }),
    uncertainty: Object.freeze({ empiricallyCalibratedForTwilight: false }),
  });
}

function atmosphereFor(createAtmosphereState, aod550) {
  const validTime = '1952-01-11T22:30:00Z';
  return createAtmosphereState({
    provider: 'tousey-koomen-historical-aod-sweep',
    dataset: 'NO_MATCHED_HISTORICAL_AOD_DIAGNOSTIC_SWEEP',
    validTime,
    fetchTime: validTime,
    staleAfterSeconds: 86400,
    latitudeDeg: 38.9,
    longitudeDeg: -77.0,
    observerElevationM: 0,
    aod550,
    qualityClass: 'modeled-live',
  }, { now: new Date(validTime) });
}

function geometry(star, d) {
  return Object.freeze({
    sunDepressionDeg: d,
    targetAltitudeDeg: finite(star.starAltitudeDeg, `${star.object} altitude`),
    relativeAzimuthDeg: finite(star.relativeAzimuthFromSunDeg, `${star.object} rel azimuth`),
  });
}

function sunRateDegPerMin(star) {
  const first = star.observations[0];
  const last = star.observations.at(-1);
  const toMin = s => { const [h, m] = s.split(':').map(Number); return h * 60 + m; };
  return (-last.sunAltitudeDeg + first.sunAltitudeDeg) / (toMin(last.localTime) - toMin(first.localTime));
}

function intervalsFromTimeline(timeline) {
  const intervals = [];
  let open = null;
  const supported = row => row.status === 'SUPPORTED';
  for (let i = 0; i < timeline.length; i += 1) {
    const row = timeline[i];
    if (!supported(row)) {
      if (open != null) { intervals.push({ startDepressionDeg: open, endDepressionDeg: timeline[i - 1]?.d ?? null, terminatedBy: 'SUPPORT_GAP' }); open = null; }
      continue;
    }
    const visible = row.marginMag >= 0;
    if (visible && open == null) {
      if (i > 0 && supported(timeline[i - 1]) && timeline[i - 1].marginMag < 0) {
        const a = timeline[i - 1], b = row;
        const u = -a.marginMag / (b.marginMag - a.marginMag);
        open = a.d + u * (b.d - a.d);
      } else open = row.d;
    }
    if (!visible && open != null) {
      const a = timeline[i - 1], b = row;
      const u = a.marginMag / (a.marginMag - b.marginMag);
      intervals.push({ startDepressionDeg: open, endDepressionDeg: a.d + u * (b.d - a.d), terminatedBy: 'VISIBILITY_EXIT' });
      open = null;
    }
  }
  if (open != null) intervals.push({ startDepressionDeg: open, endDepressionDeg: timeline.at(-1).d, terminatedBy: 'DOMAIN_END' });
  return intervals;
}

const args = parseArgs(process.argv);
const appRoot = resolve(args.appRoot);
const fixture = JSON.parse(await readFile(resolve(args.fixture), 'utf8'));
if (fixture.source !== 'Tousey & Koomen, JOSA 43 (1953) 177-183, Table III') throw new Error('fixture source drift');
if (fixture.rows?.length !== 4) throw new Error('fixture star count drift');
for (const name of Object.keys(HR_BY_OBJECT)) if (!fixture.rows.some(r => r.object === name)) throw new Error(`fixture missing ${name}`);

const v3 = join(appRoot, 'scientific-tools', 'visibility-v3');
const [
  { createAtmosphereState },
  { createValidatedV3SkyProvider },
  { createAerosolScenarioSkyProvider },
  { createBrowserSameAtmosphereVBandStellarSignalEvaluator },
  { createPackagedMatchedAerosolStellarSignalEvaluatorV2 },
  { limitingVMagnitude },
] = await Promise.all([
  import(pathToFileURL(join(v3, 'atmosphere-state.mjs')).href),
  import(pathToFileURL(join(v3, 'validated-v3-sky-provider.mjs')).href),
  import(pathToFileURL(join(v3, 'aerosol-scenario-sky-provider.mjs')).href),
  import(pathToFileURL(join(v3, 'level-b-browser-stellar-signal.mjs')).href),
  import(pathToFileURL(join(v3, 'matched-aerosol-stellar-runtime-loader-v2.mjs')).href),
  import(pathToFileURL(join(v3, 'human-threshold.mjs')).href),
]);

const loadJson = async p => JSON.parse(await readFile(p, 'utf8'));
const [runtimeData, asivRuntimeData, sedBundle, rawJohnsonV] = await Promise.all([
  loadJson(join(v3, 'validated-v3-primary-runtime-v1.json')),
  loadJson(join(v3, 'aerosol-scenario-interpolator-runtime-v1.json')),
  loadJson(join(v3, 'generated', 'pickles-sed-1nm.json')),
  loadJson(join(v3, 'generated', 'johnson-v-1nm.json')),
]);
const johnsonVBandpass = Object.freeze({
  ...rawJohnsonV,
  wavelengthNm: Object.freeze([...rawJohnsonV.wavelengthNm]),
  response: Object.freeze(rawJohnsonV.response.slice(0, rawJohnsonV.wavelengthNm.length)),
});
if (johnsonVBandpass.wavelengthNm.length !== 401 || johnsonVBandpass.response.length !== 401) throw new Error('Johnson-V shape drift');

const { rows: catalogRows, assetName } = await loadBuiltCatalog(appRoot);
const baselineProvider = createValidatedV3SkyProvider({ runtimeData });
const nativeStellar = createBrowserSameAtmosphereVBandStellarSignalEvaluator();
const matchedStellar = new Map();
for (const family of FAMILIES) {
  matchedStellar.set(family, await createPackagedMatchedAerosolStellarSignalEvaluatorV2({ aerosolFamily: family, sedBundle, johnsonVBandpass }));
}

const outputStars = [];
for (const star of fixture.rows) {
  const hr = HR_BY_OBJECT[star.object];
  const raw = findCatalogRow(catalogRows, hr);
  const target = targetFrom(star, raw);
  const rate = sunRateDegPerMin(star);
  const earliestD = -finite(star.observations[0].sunAltitudeDeg, `${star.object} earliest sun alt`);
  const byF = {};

  for (const F of FIELD_FACTORS) {
    const criterion = observerCriterion(F);
    const variants = [{ id: 'native', family: null, skyProvider: baselineProvider, stellarEvaluator: nativeStellar }];
    for (const family of FAMILIES) {
      variants.push({
        id: `matched:${family}`,
        family,
        skyProvider: createAerosolScenarioSkyProvider({ baselineProvider, asivRuntimeData, observerCriterion: criterion, stateId: family }),
        stellarEvaluator: matchedStellar.get(family),
      });
    }

    const variantResults = [];
    for (const variant of variants) {
      const aodResults = [];
      for (const aod550 of AOD_SWEEP) {
        const atmosphere = atmosphereFor(createAtmosphereState, aod550);
        const stellar = variant.stellarEvaluator({ geometry: geometry(star, earliestD), atmosphere, target });
        if (stellar.status !== 'SUPPORTED') {
          aodResults.push({ aod550, status: 'STELLAR_UNSUPPORTED', reason: stellar.reason ?? null });
          continue;
        }

        const evaluate = d => {
          const sky = variant.skyProvider.evaluateSky({ geometry: geometry(star, d), atmosphere });
          if (sky.status !== 'SUPPORTED') return { d, status: sky.status, reasons: sky.support?.reasons ?? [] };
          const B = Number(sky.channels?.photopic?.value);
          if (!(B > 0)) return { d, status: 'INVALID_SKY_PHOTOPIC' };
          const limit = limitingVMagnitude({ backgroundLuminanceCdM2: B, fieldFactor: F, branch: 'full' });
          return {
            d,
            status: 'SUPPORTED',
            backgroundLuminanceCdM2: B,
            apparentVMagAtEye: stellar.apparentVMagAtEye,
            extinctionMagV: stellar.extinctionMagV,
            limitingVMagnitude: limit,
            marginMag: limit - stellar.apparentVMagAtEye,
          };
        };

        const timeline = [];
        const steps = Math.round((D_MAX - D_MIN) / STEP);
        for (let i = 0; i <= steps; i += 1) timeline.push(evaluate(Number((D_MIN + i * STEP).toFixed(8))));
        const intervals = intervalsFromTimeline(timeline);
        const observations = star.observations.map(obs => {
          const d = -finite(obs.sunAltitudeDeg, `${star.object} obs sun alt`);
          const x = evaluate(d);
          return { localTime: obs.localTime, sunDepressionDeg: d, qualitativeVisibility: obs.visibility, ...x };
        });
        const first = intervals[0]?.startDepressionDeg ?? null;
        aodResults.push({
          aod550,
          status: 'SUPPORTED_DIAGNOSTIC',
          stellar: { apparentVMagAtEye: stellar.apparentVMagAtEye, extinctionMagV: stellar.extinctionMagV },
          supportedSampleCount: timeline.filter(x => x.status === 'SUPPORTED').length,
          unsupportedSampleCount: timeline.filter(x => x.status !== 'SUPPORTED').length,
          visibilityIntervals: intervals,
          firstVisibleDepressionDeg: first,
          firstVisibleVsEarliestRecorded: first == null ? null : {
            deltaDepressionDeg: first - earliestD,
            approximateMinutes: (first - earliestD) / rate,
            signConvention: 'positive=model first-visible later than an already-recorded visible observation; negative=model earlier',
          },
          observations,
        });
      }
      variantResults.push({ id: variant.id, family: variant.family, aodResults });
    }
    byF[String(F)] = variantResults;
  }

  outputStars.push({
    object: star.object,
    hr,
    sourceCatalogMagnitudeV: star.catalogMagnitudeV,
    currentCatalogColorAndType: { bv: target.bv, spectralType: target.spectralType },
    geometryHeldAtPublishedTableValue: { targetAltitudeDeg: star.starAltitudeDeg, relativeAzimuthDeg: star.relativeAzimuthFromSunDeg },
    earliestRecordedVisible: { ...star.observations[0], sunDepressionDeg: earliestD },
    allPublishedObservations: star.observations,
    observedSunDepressionRateDegPerMin: rate,
    byFieldFactor: byF,
  });
}

const result = {
  schemaVersion: 1,
  status: 'TOUSEY_KOOMEN_TABLE_III_CURRENT_LEVEL_B_DIAGNOSTIC_COMPLETE',
  applicationSha: APP_SHA,
  sourceFixtureSha: FIXTURE_SHA,
  fixtureSource: fixture.source,
  catalog: { rowCount: catalogRows.length, assetName },
  frozenDesign: {
    aodSweep: AOD_SWEEP,
    fieldFactors: FIELD_FACTORS,
    configuredFieldFactorPrimary: 3.14,
    historicalBlackwellSensitivityFieldFactor: 2.4,
    sunDepressionDomainDeg: [D_MIN, D_MAX],
    timelineStepDeg: STEP,
    variants: ['native', ...FAMILIES.map(x => `matched:${x}`)],
    noAodSelectionOrFitting: true,
    noFieldFactorFitting: true,
    noSkyScaling: true,
    noExtinctionScaling: true,
    noMysticSolverExecution: true,
    earliestRecordedVisibleIsNotClaimedExactFirstSeeing: true,
  },
  interpretationBoundary: {
    evidenceClass: 'historical-real-naked-eye-diagnostic-not-independent-modern-holdout',
    historicalAodUnknown: true,
    matchedAerosolFamilyUnknown: true,
    geometryHeldAtPublishedTableValues: true,
    sourcePaperSeaLevelPlusOneMagCorrectionNotUsed: true,
    currentPhysicalStellarTransportUsedInstead: true,
    productionAuthorized: false,
    humanFirstSeeingValidated: false,
    measuredRealSkyValidatedByThisDiagnostic: false,
  },
  stars: outputStars,
};

await mkdir(resolve(args.output, '..'), { recursive: true });
await writeFile(resolve(args.output), `${JSON.stringify(result, null, 2)}\n`);
console.log(JSON.stringify({ status: result.status, stars: result.stars.map(s => s.object), aods: AOD_SWEEP, F: FIELD_FACTORS }, null, 2));
