import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const CASES = {
  tishrei: {
    date: '2025-09-23',
    sunsetMs: 1758641660932,
    expectedAod550: 0.22,
    baselineEventMs: 1758642904994.5,
  },
  tammuz: {
    date: '2026-06-16',
    sunsetMs: 1781628380546,
    expectedAod550: 0.18,
    baselineEventMs: 1781629701483.5,
  },
};

const caseId = process.env.CASE_ID;
const frozen = CASES[caseId];
if (!frozen) throw new Error(`unknown CASE_ID ${caseId}`);

const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage();
  const browserConsole = [];
  page.on('console', m => browserConsole.push(`[${m.type()}] ${m.text()}`));
  page.on('pageerror', e => browserConsole.push(`[pageerror] ${e.stack || e.message}`));
  await page.goto('http://127.0.0.1:4173/work-in-progress/', { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForSelector('#visibilityEngineMode', { timeout: 120000 });

  const audit = await page.evaluate(async ({ caseId, frozen }) => {
    const spec = {
      latitudeDeg: 31.778,
      longitudeDeg: 35.235,
      observerElevationM: 800,
      date: frozen.date,
      timeZone: 'Asia/Jerusalem',
      engineMode: 'level-b-v3-crumey-blackwell-equilibrium',
      threshold: 1.7,
      requiredCount: 3,
      stabilityMs: 60000,
      scanStepMs: 30000,
      fieldFactor: 3.14,
    };
    const set = (id, v) => {
      const e = document.getElementById(id);
      if (!e) throw new Error(`missing #${id}`);
      e.value = String(v);
      e.dispatchEvent(new Event('input', { bubbles: true }));
      e.dispatchEvent(new Event('change', { bubbles: true }));
    };
    try { localStorage.clear(); } catch (_) {}
    set('calculatorFeature', 'three-star');
    set('lat', spec.latitudeDeg);
    set('lon', spec.longitudeDeg);
    set('date', spec.date);
    set('timezone', spec.timeZone);
    set('observerElevationM', spec.observerElevationM);
    set('visibilityEngineMode', spec.engineMode);
    set('threeStarCount', spec.requiredCount);
    set('threeStarMagnitudeBasis', 'effective');
    set('threeStarMagnitudeThreshold', spec.threshold);
    globalThis.__STAR_VISIBILITY_ENGINE_MODE__ = spec.engineMode;
    globalThis.__SKY_MAP_REQUEST__ = false;
    if (typeof eval('ensureBuiltInCatalogReady') === 'function') await eval('ensureBuiltInCatalogReady()');
    const rawCount = Array.isArray(globalThis.__STARS_BUILT_IN_STARS__) ? globalThis.__STARS_BUILT_IN_STARS__.length : -1;
    if (rawCount !== 9090) throw new Error(`raw catalog ${rawCount}`);

    const input = {
      latitudeDeg: spec.latitudeDeg,
      longitudeDeg: spec.longitudeDeg,
      observerElevationM: spec.observerElevationM,
      date: spec.date,
      timeZone: spec.timeZone,
    };
    const hooks = eval('__levelBSitewideGeometryHooks')(input, Number(frozen.sunsetMs));
    const adapter = await import('/scientific-tools/visibility-v3/level-b-current-main-adapter.mjs');
    const resolver = await import('/scientific-tools/visibility-v3/level-b-preview-atmosphere-resolver.mjs');
    const engine = await import('/scientific-tools/visibility-v3/level-b-sitewide-engine.mjs');
    const sedSelector = await import('/scientific-tools/visibility-v3/stellar-sed-selector.mjs');
    const spectralRuntime = await import('/scientific-tools/visibility-v3/stellar-spectral-runtime.mjs');
    const mesopic = await import('/scientific-tools/visibility-v3/review/mesopic-star-sky-sensitivity-v1.mjs');

    const [sedBundle, stellarRuntimeData] = await Promise.all([
      fetch('/scientific-tools/visibility-v3/generated/pickles-sed-1nm.json').then(r => {
        if (!r.ok) throw new Error(`SED fetch ${r.status}`);
        return r.json();
      }),
      fetch('/scientific-tools/visibility-v3/generated/stellar-transport-v2-lut.json').then(r => {
        if (!r.ok) throw new Error(`stellar runtime fetch ${r.status}`);
        return r.json();
      }),
    ]);
    const spectralTransmission = spectralRuntime.createLevelBStellarSpectralTransmissionProvider({
      spectralRuntimeData: stellarRuntimeData,
    });

    const runtimeData = await adapter.loadValidatedV3RuntimeData({ fetchImpl: globalThis.fetch });
    const referenceTimeMs = hooks.timeAtSunDepression(6.0);
    const atmosphereResolution = await resolver.resolvePreviewLevelBAtmosphere({
      latitudeDeg: spec.latitudeDeg,
      longitudeDeg: spec.longitudeDeg,
      observerElevationM: spec.observerElevationM,
      validTimeMs: referenceTimeMs,
      fetchImpl: globalThis.fetch,
    });
    if (atmosphereResolution.status !== 'RESOLVED') throw new Error(`atmosphere ${atmosphereResolution.status}`);
    if (Math.abs(Number(atmosphereResolution.atmosphere?.aod550) - Number(frozen.expectedAod550)) > 1e-12) {
      throw new Error(`AOD changed: ${atmosphereResolution.atmosphere?.aod550} expected ${frozen.expectedAod550}`);
    }
    const atmosphere = atmosphereResolution.atmosphere;

    delete globalThis.__DIAG_LEVEL_B_DIRECT_CATALOG_ROWS__;
    await eval('__levelBSitewideRunUsingLegacyScaffold(globalThis.__STAR_VISIBILITY_ENGINE_MODE__)');
    const uiBaseline = JSON.parse(JSON.stringify(eval('threeStarResultData')));
    const snapshot = globalThis.__DIAG_LEVEL_B_DIRECT_CATALOG_ROWS__;
    if (!Array.isArray(snapshot) || snapshot.length !== 7653) throw new Error(`instrumented transformed-row snapshot ${snapshot?.length}`);
    const rows = snapshot.map(r => ({ ...r }));
    if (globalThis.__LEVEL_B_SITEWIDE_DIRECT_CATALOG_ROWS__ !== undefined) throw new Error('temporary direct catalog handoff should be deleted after scaffold');

    const point = engine.createSitewidePointEvaluator({
      runtimeData,
      atmosphereResolution,
      geometryAtSunDepression: hooks.geometryAtSunDepression,
    });
    const catalogId = row => row?.isPlanet
      ? (row.planetKey ? `PLANET:${row.planetKey}` : `PLANET:${row.name}`)
      : row?.hip != null && row.hip !== '' ? `HIP ${row.hip}`
        : row?.hr != null && row.hr !== '' ? `HR ${row.hr}`
          : row?.hd != null && row.hd !== '' ? `HD ${row.hd}`
            : (row?.name ?? row?.id ?? 'target');
    const candidates = rows
      .map(row => ({ key: catalogId(row), row, target: engine.normalizeSitewideTarget(row) }))
      .filter(e => e.target);

    const depressionAt = t => -Number(eval('sunAltitude')(t, spec.latitudeDeg, spec.longitudeDeg));
    const endMs = hooks.timeAtSunDepression(10.5);
    if (!Number.isFinite(endMs)) throw new Error('10.5-degree end unavailable');

    const sampleCache = new Map();
    const sedCache = new Map();
    const mesopicCache = new Map();
    const sampleAt = (entry, t) => {
      const key = `${entry.key}|${Math.round(Number(t) / 250)}`;
      if (!sampleCache.has(key)) {
        const d = depressionAt(t);
        sampleCache.set(key, d >= 2 && d <= 10.5 ? point(entry.target, d) : null);
      }
      return sampleCache.get(key);
    };
    const sedFor = entry => {
      if (sedCache.has(entry.key)) return sedCache.get(entry.key);
      let result;
      try {
        result = sedSelector.selectCatalogStellarSed({
          catalogStar: entry.target,
          sedBundle,
          rejectKnownComposite: false,
        });
      } catch (error) {
        result = { error: String(error?.message ?? error), code: error?.code ?? 'SED_REJECTED' };
      }
      sedCache.set(entry.key, result);
      return result;
    };
    const mesopicAt = (entry, t) => {
      const cacheKey = `${entry.key}|${Math.round(Number(t) / 250)}`;
      if (mesopicCache.has(cacheKey)) return mesopicCache.get(cacheKey);
      const d = depressionAt(t);
      const base = sampleAt(entry, t);
      if (!base || base.status !== 'SUPPORTED'
          || base.sky?.channels?.photopic?.available !== true
          || base.sky?.channels?.scotopic?.available !== true) {
        const out = { status: 'BASE_UNSUPPORTED', deltaMarginMag: null };
        mesopicCache.set(cacheKey, out);
        return out;
      }
      const sed = sedFor(entry);
      if (!sed || sed.error) {
        const out = { status: 'SED_UNSUPPORTED', reason: sed?.code ?? null, deltaMarginMag: null };
        mesopicCache.set(cacheKey, out);
        return out;
      }
      try {
        const geometry = hooks.geometryAtSunDepression(d, entry.target);
        const transmission = spectralTransmission({ geometry, atmosphere, catalogStar: entry.target });
        const sp = mesopic.stellarScotopicPhotopicRatioFromSpectrum({
          wavelengthNm: sed.wavelengthNm,
          stellarSpectralWeight: sed.stellarSpectralWeight,
          directTransmittance: transmission.spectrum.lineOfSightDirectTransmission,
        });
        const diag = mesopic.diagnoseMesopicSpectralVisibilityShift({
          backgroundPhotopicLuminanceCdM2: base.sky.channels.photopic.value,
          backgroundScotopicLuminanceScotCdM2: base.sky.channels.scotopic.value,
          stellarScotopicPhotopicRatio: sp.scotopicPhotopicRatio,
        });
        const out = {
          status: 'SUPPORTED',
          deltaMarginMag: diag.mesopicMinusCurrentVisibilityMarginMag,
          m: diag.adaptation.m,
          regime: diag.adaptation.regime,
          skyPhotopicCdM2: base.sky.channels.photopic.value,
          skyScotopicCdM2: base.sky.channels.scotopic.value,
          stellarScotopicPhotopicRatio: sp.scotopicPhotopicRatio,
          sedTemplateId: sed.templateId,
          sedSelectionBasis: sed.selectionBasis,
        };
        mesopicCache.set(cacheKey, out);
        return out;
      } catch (error) {
        const out = { status: 'MESOPIC_REJECTED', reason: error?.code ?? String(error?.message ?? error), deltaMarginMag: null };
        mesopicCache.set(cacheKey, out);
        return out;
      }
    };

    const baselineQualifiesAt = (entry, t) => {
      const d = depressionAt(t);
      if (!Number.isFinite(d) || d < 2 || d > 10.5) return false;
      const s = sampleAt(entry, t);
      const margin = Number(s?.visibility?.visibilityMarginMag);
      const apparent = Number(s?.stellar?.apparentVMagAtEye);
      return s?.status === 'SUPPORTED'
        && Number.isFinite(margin) && margin >= -1e-10
        && Number.isFinite(apparent) && apparent >= spec.threshold - 1e-10;
    };
    const mesopicQualifiesAt = (entry, t) => {
      const d = depressionAt(t);
      if (!Number.isFinite(d) || d < 2 || d > 10.5) return false;
      const s = sampleAt(entry, t);
      const baseMargin = Number(s?.visibility?.visibilityMarginMag);
      const apparent = Number(s?.stellar?.apparentVMagAtEye);
      if (s?.status !== 'SUPPORTED' || !Number.isFinite(baseMargin)
          || !Number.isFinite(apparent) || apparent < spec.threshold - 1e-10) return false;
      const m = mesopicAt(entry, t);
      return m.status === 'SUPPORTED'
        && Number.isFinite(m.deltaMarginMag)
        && baseMargin + m.deltaMarginMag >= -1e-10;
    };

    const solverOptions = {
      requiredCount: spec.requiredCount,
      stabilityMs: spec.stabilityMs,
      startMs: Number(frozen.sunsetMs),
      endMs,
      scanStepMs: spec.scanStepMs,
    };
    const baselineEvent = engine.findStableSimultaneousQualifiedEvent(candidates, {
      ...solverOptions,
      qualifiesAt: baselineQualifiesAt,
    });
    if (!baselineEvent.found) throw new Error('baseline expected event missing');
    if (Math.abs(baselineEvent.eventTimeMs - Number(frozen.baselineEventMs)) > 500) {
      throw new Error(`baseline event mismatch ${baselineEvent.eventTimeMs} vs ${frozen.baselineEventMs}`);
    }
    const mesopicEvent = engine.findStableSimultaneousQualifiedEvent(candidates, {
      ...solverOptions,
      qualifiesAt: mesopicQualifiesAt,
    });

    const describeSelected = (event, useMesopic) => event.found ? event.selected.map(entry => {
      const s = sampleAt(entry, event.eventTimeMs);
      const m = mesopicAt(entry, event.eventTimeMs);
      const baseMargin = Number(s?.visibility?.visibilityMarginMag);
      return {
        key: entry.key,
        name: entry.row?.name,
        catalogMagnitude: Number(entry.row?.mag),
        apparentVMagAtEye: Number(s?.stellar?.apparentVMagAtEye),
        baseVisibilityMarginMag: baseMargin,
        mesopicDeltaMarginMag: m.status === 'SUPPORTED' ? m.deltaMarginMag : null,
        resultingVisibilityMarginMag: useMesopic && m.status === 'SUPPORTED' ? baseMargin + m.deltaMarginMag : baseMargin,
        mesopicM: m.status === 'SUPPORTED' ? m.m : null,
        mesopicRegime: m.status === 'SUPPORTED' ? m.regime : null,
        stellarSedTemplateId: m.status === 'SUPPORTED' ? m.sedTemplateId : null,
        geometry: hooks.geometryAtSunDepression(depressionAt(event.eventTimeMs), entry.target),
        completing: event.completingKeys?.includes(entry.key) ?? false,
      };
    }) : [];

    const baseline = {
      found: baselineEvent.found,
      eventTimeMs: baselineEvent.eventTimeMs,
      minutesAfterSunset: (baselineEvent.eventTimeMs - Number(frozen.sunsetMs)) / 60000,
      sunDepressionDeg: depressionAt(baselineEvent.eventTimeMs),
      completingKeys: baselineEvent.completingKeys ?? [],
      selected: describeSelected(baselineEvent, false),
    };
    const mesopicResult = mesopicEvent.found ? {
      found: true,
      eventTimeMs: mesopicEvent.eventTimeMs,
      minutesAfterSunset: (mesopicEvent.eventTimeMs - Number(frozen.sunsetMs)) / 60000,
      sunDepressionDeg: depressionAt(mesopicEvent.eventTimeMs),
      completingKeys: mesopicEvent.completingKeys ?? [],
      selected: describeSelected(mesopicEvent, true),
    } : {
      found: false,
      eventTimeMs: null,
      minutesAfterSunset: null,
      sunDepressionDeg: null,
      completingKeys: [],
      selected: [],
    };
    const shift = mesopicEvent.found ? {
      milliseconds: mesopicEvent.eventTimeMs - baselineEvent.eventTimeMs,
      seconds: (mesopicEvent.eventTimeMs - baselineEvent.eventTimeMs) / 1000,
      minutes: (mesopicEvent.eventTimeMs - baselineEvent.eventTimeMs) / 60000,
      depressionDeg: depressionAt(mesopicEvent.eventTimeMs) - depressionAt(baselineEvent.eventTimeMs),
      signConvention: 'positive = CIE MES2 sensitivity predicts later Three-Star event than current photopic convention',
    } : null;

    const uiEventMs = Number(uiBaseline?.eventTime ?? uiBaseline?.eventTimeMs);
    if (Number.isFinite(uiEventMs) && Math.abs(uiEventMs - Number(frozen.baselineEventMs)) > 500) {
      throw new Error(`UI baseline event mismatch ${uiEventMs} vs ${frozen.baselineEventMs}`);
    }
    return {
      caseId,
      spec,
      frozen,
      rawCatalogCount: rawCount,
      directCatalogRowCount: rows.length,
      atmosphereResolution,
      referenceTimeMs,
      baseline,
      mesopic: mesopicResult,
      shift,
      cacheAudit: {
        baseSampleCount: sampleCache.size,
        mesopicSampleCount: mesopicCache.size,
        sedSelectionCount: sedCache.size,
      },
    };
  }, { caseId, frozen });

  const out = path.join(process.env.RUNNER_TEMP, 'jerusalem-full-event-mesopic');
  fs.mkdirSync(out, { recursive: true });
  fs.writeFileSync(path.join(out, `${caseId}.json`), JSON.stringify({
    schemaVersion: 1,
    status: 'JERUSALEM_FULL_EVENT_MESOPIC_SENSITIVITY_COMPLETE',
    applicationSha: process.env.APPLICATION_SHA,
    mesopicSourceSha: process.env.MESOPIC_SHA,
    audit,
    browserConsole,
    claimBoundary: {
      sensitivityOnly: true,
      CIE191ValidatedForFovealStarDetection: false,
      humanFirstSeeingValidated: false,
      productionDefaultChanged: false,
      F314Unchanged: true,
      noTuning: true,
      noMYSTIC: true,
      noPandora: true,
    },
  }, null, 2) + '\n');
  console.log('MESOPIC_EVENT=' + JSON.stringify({ caseId, baseline: audit.baseline, mesopic: audit.mesopic, shift: audit.shift }));
} finally {
  await browser.close();
}
