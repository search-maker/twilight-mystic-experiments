import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const env = process.env;
const spec = Object.freeze({
  label: env.CASE_LABEL,
  civilDate: env.CASE_DATE,
  hebrewLabel: env.HEBREW_LABEL,
  engineMode: env.ENGINE_MODE,
  latitudeDeg: Number(env.LATITUDE_DEG),
  longitudeDeg: Number(env.LONGITUDE_DEG),
  observerElevationM: Number(env.OBSERVER_ELEVATION_M),
  timeZone: env.TIME_ZONE,
  magnitudeBasis: env.MAGNITUDE_BASIS,
  magnitudeThreshold: Number(env.MAGNITUDE_THRESHOLD),
  requiredCount: Number(env.REQUIRED_COUNT),
});

const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage();
  const browserConsole = [];
  page.on('console', m => browserConsole.push(`[${m.type()}] ${m.text()}`));
  page.on('pageerror', e => browserConsole.push(`[pageerror] ${e.stack || e.message}`));
  await page.goto('http://127.0.0.1:4173/work-in-progress/', { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForSelector('#visibilityEngineMode', { timeout: 120000 });

  const payload = await page.evaluate(async (spec) => {
    const set = (id, value) => {
      const el = document.getElementById(id);
      if (!el) throw new Error(`missing #${id}`);
      el.value = String(value);
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
    };
    try { localStorage.clear(); } catch (_) {}
    set('calculatorFeature', 'three-star');
    set('lat', spec.latitudeDeg);
    set('lon', spec.longitudeDeg);
    set('date', spec.civilDate);
    set('timezone', spec.timeZone);
    set('observerElevationM', spec.observerElevationM);
    set('visibilityEngineMode', spec.engineMode);
    set('threeStarCount', spec.requiredCount);
    set('threeStarMagnitudeBasis', spec.magnitudeBasis);
    set('threeStarMagnitudeThreshold', spec.magnitudeThreshold);
    globalThis.__STAR_VISIBILITY_ENGINE_MODE__ = spec.engineMode;
    globalThis.__SKY_MAP_REQUEST__ = false;
    if (typeof eval('ensureBuiltInCatalogReady') === 'function') await eval('ensureBuiltInCatalogReady()');
    const catalog = globalThis.__STARS_BUILT_IN_STARS__;
    if (!Array.isArray(catalog) || catalog.length !== 9090) throw new Error(`catalog count ${catalog?.length}`);

    await eval('__levelBSitewideRunUsingLegacyScaffold(globalThis.__STAR_VISIBILITY_ENGINE_MODE__)');
    const result = JSON.parse(JSON.stringify(eval('threeStarResultData')));
    const catalogId = row => {
      if (row?.isPlanet) return row.planetKey ? `PLANET:${row.planetKey}` : `PLANET:${row.name}`;
      if (row?.hip != null && row.hip !== '') return `HIP ${row.hip}`;
      if (row?.hr != null && row.hr !== '') return `HR ${row.hr}`;
      if (row?.hd != null && row.hd !== '') return `HD ${row.hd}`;
      return row?.name ?? row?.id ?? 'target';
    };

    let detailed = null;
    if (result?.found) {
      const selectedRows = result.stars.map(star => {
        const row = catalog.find(r => catalogId(r) === star.catalogId) || catalog.find(r => r.name === star.name);
        if (!row) throw new Error(`selected catalog row missing: ${star.catalogId}/${star.name}`);
        return row;
      });
      const sunsetMs = Number(result.sunsetTime);
      const eventTimeMs = Number(result.eventTime);
      if (!Number.isFinite(sunsetMs) || !Number.isFinite(eventTimeMs)) throw new Error('invalid event/sunset time');
      const input = {
        latitudeDeg: spec.latitudeDeg,
        longitudeDeg: spec.longitudeDeg,
        observerElevationM: spec.observerElevationM,
        date: spec.civilDate,
        timeZone: spec.timeZone,
      };
      const hooks = eval('__levelBSitewideGeometryHooks')(input, sunsetMs);
      const engine = await import('/scientific-tools/visibility-v3/level-b-sitewide-engine.mjs');
      const evaluation = await engine.evaluateSitewideRows({
        rows: selectedRows,
        latitudeDeg: spec.latitudeDeg,
        longitudeDeg: spec.longitudeDeg,
        observerElevationM: spec.observerElevationM,
        sunsetMs,
        geometryAtSunDepression: hooks.geometryAtSunDepression,
        timeAtSunDepression: hooks.timeAtSunDepression,
        engineMode: spec.engineMode,
        fetchImpl: globalThis.fetch,
      });
      const sunDepressionDeg = -Number(eval('sunAltitude')(eventTimeMs, spec.latitudeDeg, spec.longitudeDeg));
      let detailStars = [];
      if (evaluation.status === 'COMPLETE') {
        const point = engine.createSitewidePointEvaluator({
          runtimeData: evaluation.runtimeData,
          atmosphereResolution: evaluation.atmosphereResolution,
          geometryAtSunDepression: hooks.geometryAtSunDepression,
        });
        const byId = new Map(evaluation.results.map(entry => [catalogId(entry.row), entry]));
        detailStars = result.stars.map(star => {
          const entry = byId.get(star.catalogId);
          if (!entry) throw new Error(`detail row missing: ${star.catalogId}`);
          return {
            name: star.name,
            catalogId: star.catalogId,
            catalogMagnitude: star.catalogMagnitude,
            effectiveMagnitudeAtUiEvent: star.effectiveMagnitude,
            firstVisibleTime: star.firstVisibleTime,
            completing: star.completing,
            intervalsMs: entry.intervalsMs,
            timelineResult: entry.result,
            normalizedTarget: entry.target,
            eventGeometry: hooks.geometryAtSunDepression(sunDepressionDeg, entry.target),
            eventSample: point(entry.target, sunDepressionDeg),
          };
        });
      }
      detailed = {
        evaluationStatus: evaluation.status,
        atmosphereResolution: evaluation.atmosphereResolution,
        sunsetMs,
        eventTimeMs,
        sunDepressionDeg,
        stars: detailStars,
      };
    }

    return {
      catalogCount: catalog.length,
      result,
      detailed,
      directCatalogGlobalAfterFinally: globalThis.__LEVEL_B_SITEWIDE_DIRECT_CATALOG_ROWS__ === undefined ? 'deleted' : 'present',
      catalogOnlyFlagAfterFinally: globalThis.__LEVEL_B_SITEWIDE_CATALOG_ONLY_SCAFFOLD__ === undefined ? 'deleted' : 'present',
    };
  }, spec);

  if (payload.catalogCount !== 9090) throw new Error(`Expected 9090 catalog rows, got ${payload.catalogCount}`);
  if (payload.result?.evaluatedTargetCount != null && Number(payload.result.evaluatedTargetCount) < 1000) {
    throw new Error(`Level-B evaluated only ${payload.result.evaluatedTargetCount} targets`);
  }
  if (payload.directCatalogGlobalAfterFinally !== 'deleted' || payload.catalogOnlyFlagAfterFinally !== 'deleted') {
    throw new Error('temporary Level-B catalog handoff state leaked after scaffold');
  }

  const output = {
    schemaVersion: 5,
    status: 'PREREGISTERED_EXACT_JERUSALEM_THREE_STAR_V2',
    applicationRepo: env.APPLICATION_REPO,
    applicationSha: env.APPLICATION_SHA,
    preregisteredCase: spec,
    payload,
    claimBoundary: {
      computationalDiagnosticOnly: true,
      baselineFieldFactor314Unchanged: true,
      measuredRealSkyValidated: false,
      humanFirstSeeingValidated: false,
      productionAuthorized: false,
      pandoraOpened: false,
      noTuning: true,
    },
    browserConsole,
  };
  const outDir = path.join(env.RUNNER_TEMP, 'jerusalem-three-star-exact-events-v2');
  fs.mkdirSync(outDir, { recursive: true });
  fs.writeFileSync(path.join(outDir, `${spec.label}.json`), JSON.stringify(output, null, 2) + '\n');
  console.log('JERUSALEM_EVENT_V2=' + JSON.stringify({
    label: spec.label,
    found: payload.result?.found ?? null,
    reason: payload.result?.reason ?? null,
    evaluatedTargetCount: payload.result?.evaluatedTargetCount ?? null,
    candidateCount: payload.result?.candidateCount ?? null,
    eventTime: payload.result?.eventTime ?? null,
    sunsetTime: payload.result?.sunsetTime ?? null,
    minutesAfterSunset: payload.result?.minutesAfterSunset ?? null,
    sunAltitude: payload.result?.sunAltitude ?? null,
    sunDepressionDeg: payload.detailed?.sunDepressionDeg ?? null,
    atmosphere: payload.detailed?.atmosphereResolution ?? null,
    stars: payload.detailed?.stars?.map(s => ({ name:s.name, catalogId:s.catalogId, intervalsMs:s.intervalsMs, eventGeometry:s.eventGeometry, eventSample:s.eventSample })) ?? [],
  }));
} finally {
  await browser.close();
}
